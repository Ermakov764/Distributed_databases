"""
══════════════════════════════════════════════════════════════════════════════
 ГЛАВНЫЙ ФАЙЛ КЛИЕНТА API — вся питоновская логика здесь.

 Файл:  client/app/main.py
 Запуск: uvicorn client.app.main:app --port 8000
 Swagger: http://127.0.0.1:8000/docs

 ЧТО ЭТОТ ФАЙЛ ДЕЛАЕТ (скажи преподавателю):
   1) Принимает HTTP-запросы (FastAPI) — это то, что видно в Swagger.
   2) Сам выбирает, к КАКОЙ БД подключиться:
        • запись (POST/PUT/DELETE, смена статуса) → primary региона
        • чтение (GET) → сначала replica, если она мертва → primary
   3) Выполняет SQL через psycopg (драйвер PostgreSQL).
   4) Следит за критерием контура: WEST-операции только на узлах WEST,
      EAST — только на EAST. Чужой регион → 403.
   5) Ведёт жизненный цикл заявки (статусы) и журнал shipment_events.

 СХЕМА БД (таблицы) живёт отдельно: db/init/01_schema.sql
 Этот файл — только клиент/маршрутизация/бизнес-правила над уже готовой схемой.
══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

import psycopg
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

# ---------------------------------------------------------------------------
# 1. КОНФИГУРАЦИЯ: какие регионы есть и куда стучаться
# ---------------------------------------------------------------------------

# Допустимые значения {region} в URL: /api/WEST/... или /api/EAST/...
REGIONS = ("WEST", "EAST")

# Адреса четырёх PostgreSQL из docker-compose.
# Можно переопределить переменными окружения (WEST_PRIMARY и т.д.).
# Порты: WEST primary 15432, replica 15433 | EAST primary 15434, replica 15435
NODES = {
    "WEST": {
        "primary": os.getenv("WEST_PRIMARY", "postgresql://warehouse:warehouse@127.0.0.1:15432/warehouse"),
        "replica": os.getenv("WEST_REPLICA", "postgresql://warehouse:warehouse@127.0.0.1:15433/warehouse"),
    },
    "EAST": {
        "primary": os.getenv("EAST_PRIMARY", "postgresql://warehouse:warehouse@127.0.0.1:15434/warehouse"),
        "replica": os.getenv("EAST_REPLICA", "postgresql://warehouse:warehouse@127.0.0.1:15435/warehouse"),
    },
}

# Автомат статусов заявки (shipment_orders.status).
# Ключ = текущий статус, значение = КУДА можно перейти.
# Пустое множество = конец (дальше нельзя).
# Объяснение: CREATED→RESERVED или CANCELLED; из PICKING только SHIPPED и т.д.
TRANSITIONS = {
    "CREATED": {"RESERVED", "CANCELLED"},
    "RESERVED": {"PICKING", "CANCELLED"},
    "PICKING": {"SHIPPED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": set(),   # финал успеха
    "CANCELLED": set(),   # финал отмены
}

# Создаём приложение FastAPI — по нему строится Swagger UI (/docs)
app = FastAPI(
    title="RDB Warehouse Client",
    description="CRUD + lifecycle отгрузки с учётом регионального периметра",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# 2. МОДЕЛИ ТЕЛА ЗАПРОСА (Pydantic)
#    Swagger берёт отсюда поля JSON. Если поле не то — FastAPI сам вернёт 422.
# ---------------------------------------------------------------------------

class NodeResult(BaseModel):
    """Один узел в ответе /health."""
    region: str
    role: str
    dsn_host: str
    ok: bool
    detail: str = ""


class WarehouseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)


class WarehouseUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=128)


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=256)


class StockCreate(BaseModel):
    warehouse_id: int
    product_id: int
    qty_available: int = Field(ge=0)  # ge=0 → нельзя отрицательный остаток


class StockUpdate(BaseModel):
    qty_available: int = Field(ge=0)


class OrderCreate(BaseModel):
    warehouse_id: int
    product_id: int
    qty: int = Field(gt=0)  # gt=0 → количество должно быть > 0


class StatusChange(BaseModel):
    to_status: str   # например "RESERVED"
    note: str = ""   # произвольная пометка в журнал


# ---------------------------------------------------------------------------
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ: регион, подключение, «конверт» ответа
#    Это «сердце» распределённости — сюда тыкают при жёсткой проверке кода.
# ---------------------------------------------------------------------------

def _host_from_dsn(dsn: str) -> str:
    """Вытащить host:port из строки подключения — чтобы показать в routing.host."""
    # postgresql://user:pass@host:port/db
    try:
        return dsn.split("@", 1)[1].split("/", 1)[0]
    except Exception:
        return dsn


def _require_region(region: str) -> str:
    """
    Проверка критерия контура на входе:
    если в URL написали /api/NORTH/... — сразу 400, до БД даже не ходим.
    """
    region = region.upper()
    if region not in REGIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неизвестный регион '{region}'. Допустимо: {list(REGIONS)}. "
            "Операция отклонена по критерию контура.",
        )
    return region


@contextmanager
def connect(region: str, role: str) -> Generator[psycopg.Connection, None, None]:
    """
    Подключение для ЗАПИСИ (и вообще когда явно указали role).

    Как объяснить:
      • берём DSN из NODES[регион][primary|replica]
      • открываем соединение
      • внутри with делаем SQL
      • при успехе — commit (сохранить), при ошибке — rollback (откатить)
      • если узел лежит (docker stop) — HTTP 503 «Узел недоступен»
    """
    region = _require_region(region)
    dsn = NODES[region][role]
    try:
        conn = psycopg.connect(dsn, row_factory=dict_row, connect_timeout=3)
    except Exception as exc:
        # Primary умер → запись невозможна. Это демонстрация отказа узла.
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"Узел недоступен: region={region}, role={role}",
                "host": _host_from_dsn(dsn),
                "error": str(exc),
                "hint": "При отказе primary запись запрещена; попробуйте чтение с replica "
                "или восстановите узел (docker start / promote).",
            },
        ) from exc
    try:
        yield conn
        conn.commit()      # всё прошло — фиксируем транзакцию
    except HTTPException:
        conn.rollback()    # наша бизнес-ошибка (400/403/409) — откат
        raise
    except Exception:
        conn.rollback()    # любая другая ошибка — тоже откат
        raise
    finally:
        conn.close()


def read_conn(region: str) -> tuple[str, Any]:
    """
    Подключение для ЧТЕНИЯ (все GET).

    Политика:
      1) пробуем replica (разгружаем primary, читаем с копии)
      2) если replica недоступна — fallback на primary
      3) если оба мертвы — 503 «фрагмент недоступен»

    Возвращает пару: (какую роль реально взяли, соединение).
    Роль потом попадает в routing.role ответа — видно в Swagger.
    """
    region = _require_region(region)
    errors: list[str] = []
    for role in ("replica", "primary"):
        dsn = NODES[region][role]
        try:
            conn = psycopg.connect(dsn, row_factory=dict_row, connect_timeout=3)
            return role, conn
        except Exception as exc:
            errors.append(f"{role}@{_host_from_dsn(dsn)}: {exc}")
    raise HTTPException(
        status_code=503,
        detail={
            "message": f"Фрагмент региона {region} недоступен для чтения",
            "errors": errors,
        },
    )


def envelope(region: str, role: str, data: Any, **extra: Any) -> dict[str, Any]:
    """
    Единый формат ответа API.
    Всегда есть:
      routing — КУДА реально ходили (регион, primary/replica, host)
      data    — полезные данные (строки таблиц / созданный объект)
    Это важно для защиты: видно, что чтение шло на replica, запись — на primary.
    """
    dsn = NODES[region][role]
    return {
        "routing": {
            "region": region,
            "role": role,
            "host": _host_from_dsn(dsn),
            "criterion": "horizontal fragment by region_code; writes→primary, reads→replica",
        },
        "data": data,
        **extra,
    }


# ===========================================================================
# 4. ЭНДПОИНТЫ API (= то, что в Swagger списком)
#    @app.get / @app.post / @app.put / @app.delete — декораторы FastAPI:
#    «когда придёт такой HTTP-запрос — вызови эту функцию».
# ===========================================================================

@app.get("/health")
def health() -> dict[str, Any]:
    """
    Живость стенда: по очереди пингуем все 4 узла.
    pg_is_in_recovery() = true  → это replica (только чтение)
                       = false → это primary (можно писать)
    Бизнес-таблицы не меняем.
    """
    results: list[NodeResult] = []
    for region, roles in NODES.items():
        for role, dsn in roles.items():
            try:
                with psycopg.connect(dsn, connect_timeout=2) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT pg_is_in_recovery()")
                        in_recovery = cur.fetchone()[0]
                results.append(
                    NodeResult(
                        region=region,
                        role=role,
                        dsn_host=_host_from_dsn(dsn),
                        ok=True,
                        detail=f"in_recovery={in_recovery}",
                    )
                )
            except Exception as exc:
                results.append(
                    NodeResult(
                        region=region,
                        role=role,
                        dsn_host=_host_from_dsn(dsn),
                        ok=False,
                        detail=str(exc),
                    )
                )
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "nodes": results}


# ----- Склады (warehouses) -------------------------------------------------

@app.get("/api/{region}/warehouses")
def list_warehouses(region: str) -> dict[str, Any]:
    """ЧТЕНИЕ списка складов региона → read_conn (replica first)."""
    role, conn = read_conn(region)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT w.id, w.code, w.name, r.code AS region_code
                FROM warehouses w
                JOIN regions r ON r.id = w.region_id
                WHERE r.code = %s
                ORDER BY w.id
                """,
                (region.upper(),),
            )
            rows = cur.fetchall()
        return envelope(region, role, rows)
    finally:
        conn.close()


@app.post("/api/{region}/warehouses")
def create_warehouse(region: str, body: WarehouseCreate) -> dict[str, Any]:
    """ЗАПИСЬ нового склада → только primary."""
    region = _require_region(region)
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            region_id = _region_id(cur, region)  # id строки в таблице regions
            cur.execute(
                """
                INSERT INTO warehouses (region_id, code, name)
                VALUES (%s, %s, %s)
                RETURNING id, region_id, code, name
                """,
                (region_id, body.code, body.name),
            )
            row = cur.fetchone()
    return envelope(region, "primary", row)


@app.put("/api/{region}/warehouses/{warehouse_id}")
def update_warehouse(region: str, warehouse_id: int, body: WarehouseUpdate) -> dict[str, Any]:
    """Обновить склад. COALESCE: если поле не прислали (None) — старое значение остаётся."""
    region = _require_region(region)
    if body.code is None and body.name is None:
        raise HTTPException(400, "Укажите code и/или name")
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            # Критерий контура: склад должен принадлежать этому region
            _assert_warehouse_region(cur, warehouse_id, region)
            cur.execute(
                """
                UPDATE warehouses
                SET code = COALESCE(%s, code),
                    name = COALESCE(%s, name)
                WHERE id = %s
                RETURNING id, region_id, code, name
                """,
                (body.code, body.name, warehouse_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Склад не найден на этом фрагменте")
    return envelope(region, "primary", row)


@app.delete("/api/{region}/warehouses/{warehouse_id}")
def delete_warehouse(region: str, warehouse_id: int) -> dict[str, Any]:
    """Удалить склад на primary своего региона."""
    region = _require_region(region)
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            _assert_warehouse_region(cur, warehouse_id, region)
            cur.execute(
                "DELETE FROM warehouses WHERE id = %s RETURNING id",
                (warehouse_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Склад не найден на этом фрагменте")
    return envelope(region, "primary", {"deleted_id": row["id"]})


# ----- Товары (products) ---------------------------------------------------
# Важно: это НЕ одна общая таблица на весь мир.
# На WEST и на EAST — свои копии products (горизонтальная фрагментация стенда).

@app.get("/api/{region}/products")
def list_products(region: str) -> dict[str, Any]:
    """Список товаров фрагмента (чтение с replica)."""
    role, conn = read_conn(region)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, sku, title FROM products ORDER BY id"
            )
            rows = cur.fetchall()
        return envelope(region, role, rows)
    finally:
        conn.close()


@app.post("/api/{region}/products")
def create_product(region: str, body: ProductCreate) -> dict[str, Any]:
    """
    Создать товар на primary ЭТОГО региона.
    На другом регионе этой строки не будет — пока сами не создадите там.
    """
    region = _require_region(region)
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO products (sku, title)
                VALUES (%s, %s)
                RETURNING id, sku, title
                """,
                (body.sku, body.title),
            )
            row = cur.fetchone()
    return envelope(region, "primary", row)


@app.put("/api/{region}/products/{product_id}")
def update_product(region: str, product_id: int, body: ProductUpdate) -> dict[str, Any]:
    """Обновить sku/title товара на primary."""
    region = _require_region(region)
    if body.sku is None and body.title is None:
        raise HTTPException(400, "Укажите sku и/или title")
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE products
                SET sku = COALESCE(%s, sku),
                    title = COALESCE(%s, title)
                WHERE id = %s
                RETURNING id, sku, title
                """,
                (body.sku, body.title, product_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Товар не найден на этом фрагменте")
    return envelope(region, "primary", row)


@app.delete("/api/{region}/products/{product_id}")
def delete_product(region: str, product_id: int) -> dict[str, Any]:
    """Удалить товар с фрагмента."""
    region = _require_region(region)
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM products WHERE id = %s RETURNING id",
                (product_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Товар не найден на этом фрагменте")
    return envelope(region, "primary", {"deleted_id": row["id"]})


# ----- Остатки (stock_balances) --------------------------------------------
# qty_available — свободно можно взять в заказ
# qty_reserved  — уже зарезервировано заявками в статусе RESERVED (ещё на складе)

@app.get("/api/{region}/stock")
def list_stock(region: str) -> dict[str, Any]:
    """Чтение остатков с replica."""
    role, conn = read_conn(region)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sb.id, w.code AS warehouse, p.sku, p.title,
                       sb.qty_available, sb.qty_reserved
                FROM stock_balances sb
                JOIN warehouses w ON w.id = sb.warehouse_id
                JOIN products p ON p.id = sb.product_id
                ORDER BY sb.id
                """
            )
            rows = cur.fetchall()
        return envelope(region, role, rows)
    finally:
        conn.close()


@app.post("/api/{region}/stock")
def create_stock(region: str, body: StockCreate) -> dict[str, Any]:
    """Завести остаток. Склад обязан быть этого региона (_assert_warehouse_region)."""
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            _assert_warehouse_region(cur, body.warehouse_id, region)
            cur.execute(
                """
                INSERT INTO stock_balances (warehouse_id, product_id, qty_available, qty_reserved)
                VALUES (%s, %s, %s, 0)
                RETURNING *
                """,
                (body.warehouse_id, body.product_id, body.qty_available),
            )
            row = cur.fetchone()
    return envelope(region, "primary", row)


@app.put("/api/{region}/stock/{stock_id}")
def update_stock(region: str, stock_id: int, body: StockUpdate) -> dict[str, Any]:
    """Ручная правка qty_available (как инвентаризация)."""
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE stock_balances SET qty_available = %s WHERE id = %s RETURNING *",
                (body.qty_available, stock_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Остаток не найден на этом фрагменте")
    return envelope(region, "primary", row)


@app.delete("/api/{region}/stock/{stock_id}")
def delete_stock(region: str, stock_id: int) -> dict[str, Any]:
    """Удалить строку остатка."""
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM stock_balances WHERE id = %s RETURNING id", (stock_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Остаток не найден на этом фрагменте")
    return envelope(region, "primary", {"deleted_id": row["id"]})


# ----- Заявки на отгрузку (shipment_orders) --------------------------------
# Текущий статус = колонка shipment_orders.status (не отдельная таблица!).
# История переходов = таблица shipment_events (журнал).

@app.get("/api/{region}/orders")
def list_orders(region: str) -> dict[str, Any]:
    """Список заявок только своего region_code (фрагмент)."""
    role, conn = read_conn(region)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT o.*, w.code AS warehouse_code
                FROM shipment_orders o
                JOIN warehouses w ON w.id = o.warehouse_id
                WHERE o.region_code = %s
                ORDER BY o.id
                """,
                (region.upper(),),
            )
            rows = cur.fetchall()
        return envelope(region, role, rows)
    finally:
        conn.close()


@app.post("/api/{region}/orders")
def create_order(region: str, body: OrderCreate) -> dict[str, Any]:
    """
    Создать заявку. В одной транзакции три INSERT:
      1) shipment_orders  — шапка, status='CREATED', region_code=WEST|EAST
      2) shipment_items   — что и сколько отгрузить
      3) shipment_events  — первая запись журнала (NULL → CREATED)

    Остатки (stock) здесь ЕЩЁ НЕ трогаем — резерв будет при статусе RESERVED.
    """
    region = _require_region(region)
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            _assert_warehouse_region(cur, body.warehouse_id, region)
            cur.execute(
                """
                INSERT INTO shipment_orders (warehouse_id, region_code, status)
                VALUES (%s, %s, 'CREATED')
                RETURNING *
                """,
                (body.warehouse_id, region),
            )
            order = cur.fetchone()
            cur.execute(
                """
                INSERT INTO shipment_items (order_id, product_id, qty)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (order["id"], body.product_id, body.qty),
            )
            item = cur.fetchone()
            cur.execute(
                """
                INSERT INTO shipment_events (order_id, from_status, to_status, note)
                VALUES (%s, NULL, 'CREATED', 'order created')
                """,
                (order["id"],),
            )
    return envelope(region, "primary", {"order": order, "item": item})


@app.post("/api/{region}/orders/{order_id}/status")
def change_status(region: str, order_id: int, body: StatusChange) -> dict[str, Any]:
    """
    ★ ГЛАВНАЯ БИЗНЕС-ЛОГИКА ПРОЕКТА — смена статуса заявки.

    Порядок (объясняй сверху вниз):
      1) Подключаемся к primary региона (запись).
      2) SELECT ... FOR UPDATE — блокируем строку заявки до конца транзакции
         (два параллельных запроса не испортят остатки).
      3) Если заявки нет на этом фрагменте → 404.
      4) Если region_code заявки ≠ регион из URL → 403 (критерий контура).
      5) Смотрим TRANSITIONS: можно ли текущий → to_status? Нет → 400.
      6) Побочные эффекты на остатках:
           RESERVED              → _reserve   (available−, reserved+)
           CANCELLED из RESERVED → _unreserve (available+, reserved−)
           SHIPPED               → _ship      (reserved−, товар ушёл)
      7) UPDATE shipment_orders.status
      8) INSERT в журнал shipment_events (from → to)
    """
    region = _require_region(region)
    to_status = body.to_status.upper()
    with connect(region, "primary") as conn:
        with conn.cursor() as cur:
            # --- шаг 2: читаем заявку с блокировкой ---
            cur.execute(
                "SELECT * FROM shipment_orders WHERE id = %s FOR UPDATE",
                (order_id,),
            )
            order = cur.fetchone()
            if not order:
                raise HTTPException(404, "Заявка не найдена на этом фрагменте")

            # --- шаг 4: критерий контура ---
            if order["region_code"] != region:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "message": "Отказ по критерию контура: заявка принадлежит другому региону",
                        "order_region": order["region_code"],
                        "requested_region": region,
                    },
                )

            # --- шаг 5: автомат статусов ---
            current = order["status"]
            allowed = TRANSITIONS.get(current, set())
            if to_status not in allowed:
                raise HTTPException(
                    400,
                    detail=f"Переход {current} → {to_status} запрещён. Допустимо: {sorted(allowed)}",
                )

            # --- шаг 6: движение остатков (если нужно) ---
            if to_status == "RESERVED":
                _reserve(cur, order)
            elif to_status == "CANCELLED" and current == "RESERVED":
                _unreserve(cur, order)  # вернуть товар на полку
            elif to_status == "SHIPPED":
                _ship(cur, order)

            # --- шаг 7: новый статус в заявке ---
            cur.execute(
                """
                UPDATE shipment_orders
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (to_status, order_id),
            )
            updated = cur.fetchone()

            # --- шаг 8: строка в журнале ---
            cur.execute(
                """
                INSERT INTO shipment_events (order_id, from_status, to_status, note)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (order_id, current, to_status, body.note or f"{current}->{to_status}"),
            )
            event = cur.fetchone()
    return envelope(region, "primary", {"order": updated, "event": event})


@app.get("/api/{region}/orders/{order_id}/events")
def order_events(region: str, order_id: int) -> dict[str, Any]:
    """
    Журнал одной заявки (чтение).
    Сначала проверяем, что заявка на этом фрагменте и region совпадает — иначе 403.
    """
    role, conn = read_conn(region)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT region_code FROM shipment_orders WHERE id = %s",
                (order_id,),
            )
            order = cur.fetchone()
            if not order:
                raise HTTPException(404, "Заявка не найдена")
            if order["region_code"] != region.upper():
                raise HTTPException(403, "Отказ по критерию контура")
            cur.execute(
                "SELECT * FROM shipment_events WHERE order_id = %s ORDER BY id",
                (order_id,),
            )
            rows = cur.fetchall()
        return envelope(region, role, rows)
    finally:
        conn.close()


@app.post("/api/cross-region-denied")
def cross_region_denied(
    from_region: str = Query(...),
    to_region: str = Query(...),
    order_id: int = Query(...),
) -> None:
    """
    Учебный эндпоинт: ВСЕГДА 403.
    Нужен, чтобы на защите одним кликом показать «отказ по критерию контура»
    без возни с id чужой заявки. В БД ничего не пишет.
    """
    raise HTTPException(
        status_code=403,
        detail={
            "message": "Операция нарушает критерий контура",
            "from_region": from_region,
            "to_region": to_region,
            "order_id": order_id,
            "rule": "shipment_orders строкa с region_code=X существует только на фрагменте X",
        },
    )


# ===========================================================================
# 5. ВНУТРЕННИЕ ХЕЛПЕРЫ (не видны в Swagger напрямую)
# ===========================================================================

def _region_id(cur: Any, region: str) -> int:
    """Найти id региона в таблице regions на ЭТОМ фрагменте (для FK склада)."""
    cur.execute("SELECT id FROM regions WHERE code = %s", (region.upper(),))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"Регион {region} не найден на этом фрагменте")
    return int(row["id"])


def _assert_warehouse_region(cur: Any, warehouse_id: int, region: str) -> None:
    """
    Критерий контура для склада:
    нельзя создать заявку WEST на склад, который числится за EAST (и наоборот).
    """
    cur.execute(
        """
        SELECT r.code
        FROM warehouses w
        JOIN regions r ON r.id = w.region_id
        WHERE w.id = %s
        """,
        (warehouse_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Склад не найден на этом фрагменте")
    if row["code"] != region.upper():
        raise HTTPException(
            403,
            detail={
                "message": "Склад принадлежит другому региону — отказ по критерию контура",
                "warehouse_region": row["code"],
                "requested_region": region.upper(),
            },
        )


def _reserve(cur: Any, order: dict) -> None:
    """
    RESERVED: «забронировать» товар под заявку.
      qty_available -= qty
      qty_reserved  += qty
    Если свободного остатка мало → 409 (конфликт), статус заявки не меняется
    (транзакция откатится в connect()).
    """
    cur.execute(
        "SELECT product_id, qty FROM shipment_items WHERE order_id = %s",
        (order["id"],),
    )
    items = cur.fetchall()
    for item in items:
        cur.execute(
            """
            SELECT id, qty_available, qty_reserved
            FROM stock_balances
            WHERE warehouse_id = %s AND product_id = %s
            FOR UPDATE
            """,
            (order["warehouse_id"], item["product_id"]),
        )
        bal = cur.fetchone()
        if not bal or bal["qty_available"] < item["qty"]:
            raise HTTPException(409, "Недостаточно остатка для резерва")
        cur.execute(
            """
            UPDATE stock_balances
            SET qty_available = qty_available - %s,
                qty_reserved = qty_reserved + %s
            WHERE id = %s
            """,
            (item["qty"], item["qty"], bal["id"]),
        )


def _unreserve(cur: Any, order: dict) -> None:
    """
    CANCELLED из RESERVED: вернуть товар на полку.
      qty_available += qty
      qty_reserved  -= qty
    """
    cur.execute(
        "SELECT product_id, qty FROM shipment_items WHERE order_id = %s",
        (order["id"],),
    )
    for item in cur.fetchall():
        cur.execute(
            """
            UPDATE stock_balances
            SET qty_available = qty_available + %s,
                qty_reserved = qty_reserved - %s
            WHERE warehouse_id = %s AND product_id = %s
            """,
            (item["qty"], item["qty"], order["warehouse_id"], item["product_id"]),
        )


def _ship(cur: Any, order: dict) -> None:
    """
    SHIPPED: товар физически ушёл — снимаем только резерв
    (available уже уменьшили на RESERVED, повторно не трогаем).
      qty_reserved -= qty
    """
    cur.execute(
        "SELECT product_id, qty FROM shipment_items WHERE order_id = %s",
        (order["id"],),
    )
    for item in cur.fetchall():
        cur.execute(
            """
            UPDATE stock_balances
            SET qty_reserved = qty_reserved - %s
            WHERE warehouse_id = %s AND product_id = %s
              AND qty_reserved >= %s
            """,
            (item["qty"], order["warehouse_id"], item["product_id"], item["qty"]),
        )
        if cur.rowcount != 1:
            raise HTTPException(409, "Не удалось списать резерв при отгрузке")
