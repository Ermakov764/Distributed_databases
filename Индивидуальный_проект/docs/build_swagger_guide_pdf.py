#!/usr/bin/env python3
"""Шпаргалка для защиты: Swagger + сценарии + SQL + отказы → PDF."""

from __future__ import annotations

import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
PDF_OUT = ROOT / "Swagger_шпаргалка_для_защиты.pdf"
PDF_DOCS = BASE / "Swagger_шпаргалка_для_защиты.pdf"

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

NAVY = colors.HexColor("#1a3a6b")
RED = colors.HexColor("#8b1a1a")
GREEN = colors.HexColor("#1a5c2e")
LIGHT = colors.HexColor("#f4f6f8")
LIGHT_RED = colors.HexColor("#fde8e8")
LIGHT_GREEN = colors.HexColor("#e8f5ec")


def styles():
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_REG))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_BOLD))
    pdfmetrics.registerFont(TTFont("DejaVuMono", FONT_MONO))
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="TitleRU", fontName="DejaVu-Bold", fontSize=14, alignment=TA_CENTER, leading=18, spaceAfter=4))
    ss.add(ParagraphStyle(name="SubRU", fontName="DejaVu", fontSize=9.5, alignment=TA_CENTER, leading=12, spaceAfter=8, textColor=colors.HexColor("#444")))
    ss.add(ParagraphStyle(name="H1RU", fontName="DejaVu-Bold", fontSize=11.5, textColor=NAVY, spaceBefore=10, spaceAfter=5, leading=14))
    ss.add(ParagraphStyle(name="H2RU", fontName="DejaVu-Bold", fontSize=10, textColor=colors.HexColor("#2a4a7a"), spaceBefore=7, spaceAfter=3, leading=12.5))
    ss.add(ParagraphStyle(name="H2Fail", fontName="DejaVu-Bold", fontSize=10, textColor=RED, spaceBefore=7, spaceAfter=3, leading=12.5))
    ss.add(ParagraphStyle(name="BodyRU", fontName="DejaVu", fontSize=9, alignment=TA_JUSTIFY, leading=12, spaceAfter=3))
    ss.add(ParagraphStyle(name="BulletRU", fontName="DejaVu", fontSize=9, leftIndent=6, leading=11.5, spaceAfter=1.5))
    ss.add(ParagraphStyle(name="CodeRU", fontName="DejaVuMono", fontSize=7, leading=9, backColor=LIGHT, spaceBefore=1, spaceAfter=4, leftIndent=1, rightIndent=1))
    ss.add(ParagraphStyle(name="CodeFail", fontName="DejaVuMono", fontSize=7, leading=9, backColor=LIGHT_RED, spaceBefore=1, spaceAfter=4, leftIndent=1, rightIndent=1))
    ss.add(ParagraphStyle(name="CodeOk", fontName="DejaVuMono", fontSize=7, leading=9, backColor=LIGHT_GREEN, spaceBefore=1, spaceAfter=4, leftIndent=1, rightIndent=1))
    ss.add(ParagraphStyle(name="SmallRU", fontName="DejaVu", fontSize=8, leading=10.5, spaceAfter=2))
    ss.add(ParagraphStyle(name="Label", fontName="DejaVu-Bold", fontSize=8.5, textColor=NAVY, spaceBefore=3, spaceAfter=1, leading=11))
    ss.add(ParagraphStyle(name="LabelFail", fontName="DejaVu-Bold", fontSize=8.5, textColor=RED, spaceBefore=3, spaceAfter=1, leading=11))
    ss.add(ParagraphStyle(name="CenterRU", fontName="DejaVu", fontSize=8, alignment=TA_CENTER, leading=10, spaceAfter=2, textColor=colors.HexColor("#555")))
    return ss


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def tbl(data, widths, fontsize=7.5):
    cell = ParagraphStyle(name=f"c{id(data)}", fontName="DejaVu", fontSize=fontsize, leading=fontsize + 2.5)
    head = ParagraphStyle(name=f"h{id(data)}", fontName="DejaVu-Bold", fontSize=fontsize, leading=fontsize + 2.5, textColor=colors.white)
    wrapped = []
    for i, row in enumerate(data):
        st = head if i == 0 else cell
        wrapped.append([Paragraph(_esc(c), st) for c in row])
    t = Table(wrapped, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#99a")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
    ]))
    return t


def ep(story, ss, method: str, path: str, what: str, node: str, example: str, sql: str, note: str = ""):
    """Один эндпоинт: описание + пример Swagger + SQL."""
    block = []
    block.append(Paragraph(f"{method}  {path}", ss["H2RU"]))
    block.append(Paragraph(f"<b>Что делает:</b> {what}", ss["BodyRU"]))
    block.append(Paragraph(f"<b>Куда идёт:</b> {node}", ss["SmallRU"]))
    if note:
        block.append(Paragraph(note, ss["SmallRU"]))
    block.append(Paragraph("Пример в Swagger (Try it out → Execute)", ss["Label"]))
    block.append(Preformatted(example, ss["CodeRU"]))
    block.append(Paragraph("SQL на фрагменте (то, что реально уходит в PostgreSQL)", ss["Label"]))
    block.append(Preformatted(sql.strip(), ss["CodeOk"]))
    story.append(KeepTogether(block))
    story.append(Spacer(1, 4))


def fail_box(story, ss, title: str, swagger: str, why: str, sql_or_note: str, http: str):
    block = []
    block.append(Paragraph(f"✗ {title}", ss["H2Fail"]))
    block.append(Paragraph(f"<b>Ожидаемый HTTP:</b> {http}", ss["LabelFail"]))
    block.append(Paragraph(f"<b>Почему ломается / не пускает:</b> {why}", ss["BodyRU"]))
    block.append(Paragraph("Что нажать в Swagger", ss["LabelFail"]))
    block.append(Preformatted(swagger.strip(), ss["CodeFail"]))
    block.append(Paragraph("Что происходит в БД / SQL", ss["LabelFail"]))
    block.append(Preformatted(sql_or_note.strip(), ss["CodeFail"]))
    story.append(KeepTogether(block))
    story.append(Spacer(1, 4))


def scenario(story, ss, title: str, steps: list[tuple[str, str, str]]):
    """steps: (swagger action, explanation, sql check)"""
    story.append(Paragraph(title, ss["H2RU"]))
    for i, (action, expl, sql) in enumerate(steps, 1):
        story.append(Paragraph(f"<b>Шаг {i}.</b> {expl}", ss["BodyRU"]))
        story.append(Paragraph("Swagger", ss["Label"]))
        story.append(Preformatted(action.strip(), ss["CodeRU"]))
        if sql:
            story.append(Paragraph("Проверка в psql (на primary того же региона)", ss["Label"]))
            story.append(Preformatted(sql.strip(), ss["CodeOk"]))
    story.append(Spacer(1, 3))


def build():
    ss = styles()
    story: list = []

    # ---- титул ----
    story.append(Paragraph("Swagger-шпаргалка для защиты", ss["TitleRU"]))
    story.append(Paragraph(
        "Индивидуальный проект РБД · Ермаков Л. · М09-КИИ26<br/>"
        "Как показывать работу стенда в Swagger UI: эндпоинты, сценарии, SQL, отказы",
        ss["SubRU"],
    ))

    story.append(Paragraph("0. Как пользоваться этим документом на защите", ss["H1RU"]))
    for b in [
        "Откройте Swagger: <font face=\"DejaVuMono\">http://127.0.0.1:8000/docs</font>",
        "Держите рядом этот PDF: справа — что нажать, ниже — какой SQL уйдёт в БД.",
        "После каждого шага можете открыть psql и показать строки в таблицах.",
        "Красные блоки §4 — это <b>намеренные отказы</b> (не баг): автомат статусов, контур, нехватка остатка, отказ primary.",
        "Параметр <font face=\"DejaVuMono\">{region}</font> в URL — всегда <b>WEST</b> или <b>EAST</b> (регистр не важен).",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    story.append(Paragraph("0.1. Маршрутизация (скажите преподавателю вслух)", ss["H2RU"]))
    story.append(tbl([
        ["Тип запроса", "Узел", "Пример"],
        ["GET (чтение)", "сначала replica, иначе primary", "GET /api/WEST/stock"],
        ["POST/PUT/DELETE (запись)", "только primary региона", "POST /api/WEST/orders"],
        ["Смена статуса", "primary + журнал shipment_events", "POST .../orders/{id}/status"],
        ["Чужой регион в URL", "отказ 403 (критерий контура)", "EAST + id заявки WEST"],
    ], [4.2 * cm, 6.5 * cm, 6 * cm], fontsize=7.5))
    story.append(Paragraph(
        "В каждом успешном ответе смотрите блок <font face=\"DejaVuMono\">routing</font>: "
        "<font face=\"DejaVuMono\">region</font>, <font face=\"DejaVuMono\">role</font> (primary|replica), "
        "<font face=\"DejaVuMono\">host</font>.",
        ss["BodyRU"],
    ))

    # ---- подключения ----
    story.append(Paragraph("1. Как зайти в каждую базу (терминал)", ss["H1RU"]))
    story.append(Paragraph(
        "Учётка учебная: пользователь/пароль/БД = <font face=\"DejaVuMono\">warehouse</font>. "
        "Два способа: через <font face=\"DejaVuMono\">psql</font> с хоста или через <font face=\"DejaVuMono\">docker exec</font>.",
        ss["BodyRU"],
    ))
    story.append(Paragraph("1.1. С хоста (порты Docker)", ss["H2RU"]))
    story.append(Preformatted(
        "# WEST primary  (запись WEST)\n"
        "PGPASSWORD=warehouse psql -h 127.0.0.1 -p 15432 -U warehouse -d warehouse\n\n"
        "# WEST replica  (чтение WEST, только SELECT)\n"
        "PGPASSWORD=warehouse psql -h 127.0.0.1 -p 15433 -U warehouse -d warehouse\n\n"
        "# EAST primary  (запись EAST)\n"
        "PGPASSWORD=warehouse psql -h 127.0.0.1 -p 15434 -U warehouse -d warehouse\n\n"
        "# EAST replica  (чтение EAST)\n"
        "PGPASSWORD=warehouse psql -h 127.0.0.1 -p 15435 -U warehouse -d warehouse",
        ss["CodeRU"],
    ))
    story.append(Paragraph("1.2. Через docker exec (если psql не установлен)", ss["H2RU"]))
    story.append(Preformatted(
        "docker exec -it rdb-west-primary psql -U warehouse -d warehouse\n"
        "docker exec -it rdb-west-replica  psql -U warehouse -d warehouse\n"
        "docker exec -it rdb-east-primary  psql -U warehouse -d warehouse\n"
        "docker exec -it rdb-east-replica  psql -U warehouse -d warehouse",
        ss["CodeRU"],
    ))
    story.append(Paragraph("1.3. Полезные SELECT «что смотреть после Swagger»", ss["H2RU"]))
    story.append(Preformatted(
        "-- заявки и статусы\n"
        "SELECT id, warehouse_id, region_code, status, updated_at\n"
        "FROM shipment_orders ORDER BY id;\n\n"
        "-- журнал переходов\n"
        "SELECT id, order_id, from_status, to_status, note, created_at\n"
        "FROM shipment_events ORDER BY id;\n\n"
        "-- остатки (available / reserved)\n"
        "SELECT sb.id, w.code, p.sku, sb.qty_available, sb.qty_reserved\n"
        "FROM stock_balances sb\n"
        "JOIN warehouses w ON w.id = sb.warehouse_id\n"
        "JOIN products p ON p.id = sb.product_id\n"
        "ORDER BY sb.id;\n\n"
        "-- реплика ли я? (на replica = true, на primary = false)\n"
        "SELECT pg_is_in_recovery();",
        ss["CodeRU"],
    ))
    story.append(tbl([
        ["Узел", "Контейнер", "Порт хоста", "Роль"],
        ["WEST primary", "rdb-west-primary", "15432", "запись WEST"],
        ["WEST replica", "rdb-west-replica", "15433", "чтение WEST"],
        ["EAST primary", "rdb-east-primary", "15434", "запись EAST"],
        ["EAST replica", "rdb-east-replica", "15435", "чтение EAST"],
    ], [3.5 * cm, 4.5 * cm, 3.5 * cm, 5 * cm]))

    # ---- каталог API ----
    story.append(PageBreak())
    story.append(Paragraph("2. Каталог эндпоинтов Swagger (каждый запрос)", ss["H1RU"]))
    story.append(Paragraph(
        "Ниже — все операции клиента. В Swagger: найдите метод → Try it out → подставьте "
        "region / id / JSON → Execute. Ответ смотрите в Response body.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("2.1. Служебное", ss["H2RU"]))
    ep(
        story, ss,
        "GET", "/health",
        "Проверка всех 4 узлов: WEST/EAST × primary/replica. Не пишет в БД бизнес-данные.",
        "по очереди все DSN; на каждом SELECT pg_is_in_recovery()",
        "просто Execute (параметров нет)",
        "SELECT pg_is_in_recovery();  -- на каждом узле",
        "Смотрите nodes[].ok и detail=in_recovery=true/false.",
    )

    story.append(Paragraph("2.2. Склады (warehouses)", ss["H1RU"]))
    ep(story, ss, "GET", "/api/{region}/warehouses",
       "Список складов региона (чтение).",
       "чтение → replica региона",
       "region = WEST",
       """SELECT w.id, w.code, w.name, r.code AS region_code
FROM warehouses w
JOIN regions r ON r.id = w.region_id
WHERE r.code = 'WEST'
ORDER BY w.id;""")
    ep(story, ss, "POST", "/api/{region}/warehouses",
       "Создать склад на primary региона.",
       "запись → primary",
       'region=WEST\nBody:\n{\n  "code": "WH-WEST-DEMO",\n  "name": "Склад Запад DEMO"\n}',
       """INSERT INTO warehouses (region_id, code, name)
VALUES (<id региона WEST>, 'WH-WEST-DEMO', 'Склад Запад DEMO')
RETURNING id, region_id, code, name;""")
    ep(story, ss, "PUT", "/api/{region}/warehouses/{warehouse_id}",
       "Обновить code и/или name склада.",
       "запись → primary; сначала проверка, что склад этого региона",
       'region=WEST, warehouse_id=<id>\nBody:\n{\n  "name": "Склад Запад DEMO (upd)"\n}',
       """UPDATE warehouses
SET code = COALESCE(NULL, code),
    name = COALESCE('Склад Запад DEMO (upd)', name)
WHERE id = <id>
RETURNING id, region_id, code, name;""")
    ep(story, ss, "DELETE", "/api/{region}/warehouses/{warehouse_id}",
       "Удалить склад (если нет зависимостей / или каскад по схеме).",
       "запись → primary",
       "region=WEST, warehouse_id=<id> → Execute",
       "DELETE FROM warehouses WHERE id = <id> RETURNING id;")

    story.append(Paragraph("2.3. Товары (products)", ss["H1RU"]))
    story.append(Paragraph(
        "Каталог <b>не общий физически</b>: на WEST и EAST свои копии таблицы products. "
        "Создали на WEST — на EAST этой строки нет.",
        ss["BodyRU"],
    ))
    ep(story, ss, "GET", "/api/{region}/products",
       "Список товаров фрагмента.",
       "чтение → replica",
       "region=WEST",
       "SELECT id, sku, title FROM products ORDER BY id;")
    ep(story, ss, "POST", "/api/{region}/products",
       "Создать товар на primary региона.",
       "запись → primary",
       'region=WEST\nBody:\n{\n  "sku": "SKU-100",\n  "title": "Кабель 1м"\n}',
       """INSERT INTO products (sku, title)
VALUES ('SKU-100', 'Кабель 1м')
RETURNING id, sku, title;""")
    ep(story, ss, "PUT", "/api/{region}/products/{product_id}",
       "Обновить sku/title.",
       "запись → primary",
       'region=WEST, product_id=<id>\nBody: {"title": "Кабель 1м (upd)"}',
       """UPDATE products
SET sku = COALESCE(NULL, sku),
    title = COALESCE('Кабель 1м (upd)', title)
WHERE id = <id>
RETURNING id, sku, title;""")
    ep(story, ss, "DELETE", "/api/{region}/products/{product_id}",
       "Удалить товар с фрагмента.",
       "запись → primary",
       "region=WEST, product_id=<id>",
       "DELETE FROM products WHERE id = <id> RETURNING id;")

    story.append(PageBreak())
    story.append(Paragraph("2.4. Остатки (stock)", ss["H1RU"]))
    ep(story, ss, "GET", "/api/{region}/stock",
       "Список остатков: available и reserved.",
       "чтение → replica",
       "region=WEST",
       """SELECT sb.id, w.code AS warehouse, p.sku, p.title,
       sb.qty_available, sb.qty_reserved
FROM stock_balances sb
JOIN warehouses w ON w.id = sb.warehouse_id
JOIN products p ON p.id = sb.product_id
ORDER BY sb.id;""")
    ep(story, ss, "POST", "/api/{region}/stock",
       "Завести остаток на складе (qty_reserved стартует с 0).",
       "запись → primary; склад должен принадлежать region",
       'region=WEST\nBody:\n{\n  "warehouse_id": 1,\n  "product_id": 1,\n  "qty_available": 25\n}',
       """INSERT INTO stock_balances (warehouse_id, product_id, qty_available, qty_reserved)
VALUES (1, 1, 25, 0)
RETURNING *;""")
    ep(story, ss, "PUT", "/api/{region}/stock/{stock_id}",
       "Поставить новое значение qty_available (ручная правка).",
       "запись → primary",
       'region=WEST, stock_id=<id>\nBody: {"qty_available": 20}',
       "UPDATE stock_balances SET qty_available = 20 WHERE id = <id> RETURNING *;")
    ep(story, ss, "DELETE", "/api/{region}/stock/{stock_id}",
       "Удалить строку остатка.",
       "запись → primary",
       "region=WEST, stock_id=<id>",
       "DELETE FROM stock_balances WHERE id = <id> RETURNING id;")

    story.append(Paragraph("2.5. Заявки на отгрузку (orders)", ss["H1RU"]))
    story.append(Paragraph(
        "Текущий статус лежит в колонке <font face=\"DejaVuMono\">shipment_orders.status</font> "
        "(не отдельная таблица). История — в <font face=\"DejaVuMono\">shipment_events</font>.",
        ss["BodyRU"],
    ))
    ep(story, ss, "GET", "/api/{region}/orders",
       "Список заявок региона.",
       "чтение → replica",
       "region=WEST",
       """SELECT o.*, w.code AS warehouse_code
FROM shipment_orders o
JOIN warehouses w ON w.id = o.warehouse_id
WHERE o.region_code = 'WEST'
ORDER BY o.id;""")
    ep(story, ss, "POST", "/api/{region}/orders",
       "Создать заявку: status=CREATED + позиция + первая строка журнала. Остатки ещё НЕ трогает.",
       "запись → primary",
       'region=WEST\nBody:\n{\n  "warehouse_id": 1,\n  "product_id": 1,\n  "qty": 3\n}',
       """INSERT INTO shipment_orders (warehouse_id, region_code, status)
VALUES (1, 'WEST', 'CREATED') RETURNING *;

INSERT INTO shipment_items (order_id, product_id, qty)
VALUES (<order_id>, 1, 3) RETURNING *;

INSERT INTO shipment_events (order_id, from_status, to_status, note)
VALUES (<order_id>, NULL, 'CREATED', 'order created');""")
    ep(story, ss, "POST", "/api/{region}/orders/{order_id}/status",
       "Сменить статус по автомату. При RESERVED/SHIPPED/CANCELLED(from RESERVED) меняет остатки.",
       "запись → primary + FOR UPDATE на заявке",
       'region=WEST, order_id=<id>\nBody:\n{\n  "to_status": "RESERVED",\n  "note": "резерв"\n}',
       """SELECT * FROM shipment_orders WHERE id = <id> FOR UPDATE;
-- проверка region_code == WEST, иначе 403
-- проверка to_status ∈ TRANSITIONS[current], иначе 400

-- если RESERVED:
UPDATE stock_balances
SET qty_available = qty_available - <qty>,
    qty_reserved  = qty_reserved  + <qty>
WHERE warehouse_id = ... AND product_id = ...;

UPDATE shipment_orders SET status = 'RESERVED', updated_at = NOW() WHERE id = <id>;
INSERT INTO shipment_events (order_id, from_status, to_status, note)
VALUES (<id>, 'CREATED', 'RESERVED', 'резерв');""")
    ep(story, ss, "GET", "/api/{region}/orders/{order_id}/events",
       "Журнал переходов одной заявки (аудит).",
       "чтение → replica; чужой region → 403",
       "region=WEST, order_id=<id>",
       """SELECT region_code FROM shipment_orders WHERE id = <id>;
-- если region_code != WEST → 403
SELECT * FROM shipment_events WHERE order_id = <id> ORDER BY id;""")

    story.append(Paragraph("2.6. Учебный отказ контура", ss["H2RU"]))
    ep(story, ss, "POST", "/api/cross-region-denied",
       "Всегда отвечает 403 — явная демонстрация критерия контура (без записи в БД).",
       "БД не трогает — сразу HTTPException 403",
       "Query: from_region=WEST, to_region=EAST, order_id=1 → Execute",
       "-- SQL нет: отказ на уровне API до обращения к таблицам.")

    story.append(Paragraph("2.7. Автомат статусов (шпаргалка)", ss["H2RU"]))
    story.append(Preformatted(
        "CREATED  → RESERVED | CANCELLED\n"
        "RESERVED → PICKING  | CANCELLED\n"
        "PICKING  → SHIPPED\n"
        "SHIPPED  → DELIVERED\n"
        "DELIVERED → (конец)\n"
        "CANCELLED → (конец)\n\n"
        "RESERVED: available − qty, reserved + qty\n"
        "CANCELLED из RESERVED: available + qty, reserved − qty\n"
        "SHIPPED: reserved − qty (товар ушёл)\n"
        "CREATED / CANCELLED из CREATED: остатки не трогаем",
        ss["CodeRU"],
    ))

    # ---- сценарии ----
    story.append(PageBreak())
    story.append(Paragraph("3. Сценарии для показа в Swagger", ss["H1RU"]))
    story.append(Paragraph(
        "Идите по сценариям сверху вниз. После Create сохраняйте id из Response "
        "(warehouse_id, product_id, order.id) — они нужны в следующих шагах. "
        "Параллельно можно держать psql на WEST primary.",
        ss["BodyRU"],
    ))

    scenario(story, ss, "Сценарий A. Подготовка WEST (склад → товар → остаток)", [
        (
            "GET /health → Execute",
            "Показать, что 4 узла ok=true (стенд жив).",
            "SELECT pg_is_in_recovery();  -- на primary false, на replica true",
        ),
        (
            "POST /api/{region}/warehouses\nregion=WEST\n"
            '{"code":"WH-W-SHOW","name":"Склад показа WEST"}',
            "Создаём склад. В ответе routing.role=primary. Запомните data.id → WH.",
            "SELECT * FROM warehouses ORDER BY id DESC LIMIT 3;",
        ),
        (
            "POST /api/{region}/products\nregion=WEST\n"
            '{"sku":"SKU-SHOW","title":"Товар для показа"}',
            "Создаём товар только на WEST. Запомните data.id → PR.",
            "SELECT * FROM products WHERE sku='SKU-SHOW';",
        ),
        (
            "POST /api/{region}/stock\nregion=WEST\n"
            '{"warehouse_id":WH,"product_id":PR,"qty_available":20}',
            "Заводим остаток 20. reserved должен быть 0.",
            "SELECT * FROM stock_balances WHERE warehouse_id=WH AND product_id=PR;",
        ),
        (
            "GET /api/{region}/stock\nregion=WEST",
            "Чтение: в routing.role обычно replica — подчеркните это преподавателю.",
            "-- на replica (порт 15433):\nSELECT * FROM stock_balances;",
        ),
    ])

    scenario(story, ss, "Сценарий B. Полный успешный путь WEST → DELIVERED", [
        (
            "POST /api/{region}/orders\nregion=WEST\n"
            '{"warehouse_id":WH,"product_id":PR,"qty":3}',
            "Заявка CREATED. Остатки пока те же (резерва ещё нет). Запомните order.id → ORD.",
            "SELECT id, status FROM shipment_orders WHERE id=ORD;\n"
            "SELECT * FROM shipment_events WHERE order_id=ORD;",
        ),
        (
            "POST .../orders/{ORD}/status\n"
            '{"to_status":"RESERVED","note":"резерв 3"}',
            "Резерв: available 20→17, reserved 0→3.",
            "SELECT qty_available, qty_reserved FROM stock_balances\n"
            "WHERE warehouse_id=WH AND product_id=PR;",
        ),
        (
            "POST .../status  → PICKING\n"
            '{"to_status":"PICKING","note":"сборка"}',
            "Статус сменился, остатки не меняются.",
            "SELECT status FROM shipment_orders WHERE id=ORD;",
        ),
        (
            "POST .../status  → SHIPPED\n"
            '{"to_status":"SHIPPED","note":"отгружено"}',
            "Списание резерва: reserved 3→0 (товар ушёл со склада).",
            "SELECT qty_available, qty_reserved FROM stock_balances\n"
            "WHERE warehouse_id=WH AND product_id=PR;",
        ),
        (
            "POST .../status  → DELIVERED\n"
            '{"to_status":"DELIVERED","note":"доставлено"}',
            "Финал. Дальше статус менять нельзя.",
            "SELECT from_status, to_status FROM shipment_events\n"
            "WHERE order_id=ORD ORDER BY id;",
        ),
        (
            "GET .../orders/{ORD}/events\nregion=WEST",
            "Показать журнал всей цепочки в Swagger (и при желании в psql).",
            "SELECT * FROM shipment_events WHERE order_id=ORD ORDER BY id;",
        ),
    ])

    scenario(story, ss, "Сценарий C. Тот же контур на EAST (другой фрагмент)", [
        (
            "POST warehouses / products / stock на region=EAST\n"
            '(свои code/sku, свои id!)',
            "Подчеркните: id на EAST свои; данные WEST сюда не «просвечивают».",
            "-- в psql EAST primary (15434):\nSELECT code FROM warehouses;\n"
            "SELECT sku FROM products;",
        ),
        (
            "POST /api/EAST/orders + статусы до SHIPPED или DELIVERED",
            "Показать, что автомат тот же, но БД другая.",
            "SELECT id, region_code, status FROM shipment_orders;",
        ),
        (
            "GET /api/WEST/orders и GET /api/EAST/orders",
            "Списки разные: горизонтальная фрагментация по region_code.",
            "-- WEST primary vs EAST primary — сравнить глазами",
        ),
    ])

    scenario(story, ss, "Сценарий D. Отмена из CREATED (остатки не трогаем)", [
        (
            "POST /api/WEST/orders  qty=1  → запомнить ORD2",
            "Новая заявка в CREATED.",
            "SELECT status FROM shipment_orders WHERE id=ORD2;",
        ),
        (
            "POST .../status\n"
            '{"to_status":"CANCELLED","note":"клиент передумал"}',
            "Отмена до резерва. available/reserved не меняются.",
            "SELECT qty_available, qty_reserved FROM stock_balances\n"
            "WHERE warehouse_id=WH AND product_id=PR;\n"
            "-- сравнить с значениями до отмены — те же",
        ),
        (
            "GET .../events ORD2",
            "В журнале: NULL→CREATED, затем CREATED→CANCELLED.",
            "SELECT from_status, to_status FROM shipment_events WHERE order_id=ORD2;",
        ),
    ])

    scenario(story, ss, "Сценарий E. Отмена из RESERVED (возврат остатка)", [
        (
            "POST order qty=4 → status RESERVED",
            "Сначала зарезервировать: available−4, reserved+4.",
            "SELECT qty_available, qty_reserved FROM stock_balances\n"
            "WHERE warehouse_id=WH AND product_id=PR;",
        ),
        (
            "POST .../status\n"
            '{"to_status":"CANCELLED","note":"сняли резерв"}',
            "Unreserve: available+4, reserved−4. Товар снова свободен.",
            "SELECT qty_available, qty_reserved FROM stock_balances\n"
            "WHERE warehouse_id=WH AND product_id=PR;",
        ),
    ])

    scenario(story, ss, "Сценарий F. CRUD-чтение после записи (primary vs replica)", [
        (
            "POST /api/WEST/products  (запись)",
            "В ответе routing.role=primary, host с портом primary.",
            "--",
        ),
        (
            "сразу GET /api/WEST/products",
            "Обычно role=replica. Если репликация чуть отстаёт — подождите 1–2 с и повторите GET.",
            "-- на replica:\nSELECT * FROM products ORDER BY id DESC LIMIT 5;",
        ),
    ])

    scenario(story, ss, "Сценарий G. Правка остатка без заявки", [
        (
            "PUT /api/WEST/stock/{stock_id}\n"
            '{"qty_available": 15}',
            "Ручная инвентаризация: меняем только available.",
            "SELECT id, qty_available, qty_reserved FROM stock_balances WHERE id=<stock_id>;",
        ),
    ])

    scenario(story, ss, "Сценарий H. Список заявок и фильтрация взглядом", [
        (
            "GET /api/WEST/orders",
            "Показать CREATED / RESERVED / DELIVERED / CANCELLED рядом.",
            "SELECT status, count(*) FROM shipment_orders GROUP BY status;",
        ),
        (
            "GET /api/EAST/orders",
            "На EAST своих заявок меньше/другие id — фрагменты независимы.",
            "-- EAST primary",
        ),
    ])

    # ---- отказы ----
    story.append(PageBreak())
    story.append(Paragraph("4. Случаи, где «ломается» / не пускает (ожидаемо)", ss["H1RU"]))
    story.append(Paragraph(
        "На защите специально покажите 2–3 красных кейса: «система правильно отказала». "
        "Это не падение стенда, а демонстрация правил.",
        ss["BodyRU"],
    ))

    fail_box(
        story, ss,
        "Запрещённый переход статуса (400)",
        "POST /api/WEST/orders/{id}/status\n"
        "для заявки в CREATED:\n"
        '{"to_status":"SHIPPED","note":"прыжок"}',
        "Автомат TRANSITIONS не содержит CREATED→SHIPPED. Разрешены только RESERVED и CANCELLED.",
        "SELECT * FROM shipment_orders WHERE id=<id> FOR UPDATE;\n"
        "-- дальше UPDATE status НЕ выполняется\n"
        "-- клиент: HTTP 400 «Переход CREATED → SHIPPED запрещён»",
        "400",
    )
    fail_box(
        story, ss,
        "Отмена из PICKING (400)",
        "Довести заявку до PICKING, затем:\n"
        '{"to_status":"CANCELLED"}',
        "После начала сборки отмена запрещена. CANCELLED только из CREATED или RESERVED.",
        "-- status остаётся PICKING\n"
        "-- новая строка в shipment_events НЕ добавляется",
        "400",
    )
    fail_box(
        story, ss,
        "Недостаточно остатка для резерва (409)",
        "POST order с qty=9999, затем:\n"
        '{"to_status":"RESERVED"}',
        "Заявка в CREATED создаётся, но при RESERVED проверка available < qty → конфликт.",
        "SELECT qty_available FROM stock_balances ... FOR UPDATE;\n"
        "-- if available < qty → HTTP 409 «Недостаточно остатка для резерва»\n"
        "-- status заявки остаётся CREATED; reserved не растёт",
        "409",
    )
    fail_box(
        story, ss,
        "Критерий контура: чужой регион в URL (403)",
        "Взять order_id заявки WEST.\n"
        "POST /api/EAST/orders/{WEST_id}/status\n"
        '{"to_status":"CANCELLED"}',
        "Строка заявки WEST существует только на фрагменте WEST. Через EAST её менять нельзя.",
        "-- на EAST: SELECT * FROM shipment_orders WHERE id=<WEST_id>;\n"
        "-- часто пусто → 404 «не найдена на этом фрагменте»\n"
        "-- либо (если id случайно совпал) проверка region_code → 403\n"
        "Альтернатива без БД: POST /api/cross-region-denied?from_region=WEST&to_region=EAST&order_id=1",
        "403 (или 404 на пустом фрагменте)",
    )
    fail_box(
        story, ss,
        "Отказ primary: запись невозможна (503)",
        "В терминале: docker stop rdb-west-primary\n"
        "Затем в Swagger: POST /api/WEST/orders ...",
        "Запись идёт только на primary. Узел лежит → клиент не может записать.",
        "-- connect(WEST, primary) → ошибка сети\n"
        "-- HTTP 503 «Узел недоступен: region=WEST, role=primary»\n\n"
        "Сразу покажите контраст:\n"
        "GET /api/WEST/stock  → 200 с replica (чтение живо)\n"
        "GET /api/EAST/stock  → 200 (другой фрагмент не затронут)\n\n"
        "Восстановление:\n"
        "docker start rdb-west-primary\n"
        "# подождать healthy, снова POST orders",
        "503 на записи; 200 на чтении с replica",
    )
    fail_box(
        story, ss,
        "Переход из DELIVERED назад (400)",
        "Для заявки уже в DELIVERED:\n"
        '{"to_status":"PICKING"}',
        "DELIVERED — терминальный статус, множество переходов пустое.",
        "-- UPDATE не выполняется; events без новой строки",
        "400",
    )

    story.append(Paragraph("4.1. Мини-скрипт отказа узла (терминал рядом со Swagger)", ss["H2Fail"]))
    story.append(Preformatted(
        "docker stop rdb-west-primary          # «убили» primary WEST\n"
        "# Swagger: POST /api/WEST/orders        → отказ (красно)\n"
        "# Swagger: GET  /api/WEST/stock         → OK с replica\n"
        "# Swagger: GET  /api/EAST/warehouses    → OK (EAST жив)\n"
        "docker start rdb-west-primary          # вернули\n"
        "docker exec rdb-west-primary pg_isready -U warehouse -d warehouse",
        ss["CodeFail"],
    ))

    # ---- чеклист защиты ----
    story.append(Paragraph("5. Короткий чек-лист показа (5–7 минут)", ss["H1RU"]))
    for b in [
        "1) /health — 4 узла зелёные.",
        "2) POST warehouse + product + stock на WEST; GET stock → role=replica.",
        "3) POST order → RESERVED (показать available/reserved в psql) → … → DELIVERED → events.",
        "4) На EAST создать свой склад/товар — «это другой фрагмент».",
        "5) Красный: CREATED→SHIPPED → 400.",
        "6) Красный: статус WEST-заявки через EAST → 403 (или cross-region-denied).",
        "7) По желанию: docker stop west-primary → запись падает, чтение с replica живо → start.",
    ]:
        story.append(Paragraph(b, ss["BulletRU"]))

    story.append(Paragraph("6. Подъём стенда одной командой", ss["H1RU"]))
    story.append(Paragraph(
        "Чтобы сразу показать преподавателю живой стенд (Docker + схема + API + демо):",
        ss["BodyRU"],
    ))
    story.append(Preformatted(
        "cd ~/Рабочий\\ стол/РБД/Индивидуальный_проект && bash scripts/run_everything.sh\n\n"
        "# потом браузер:\n"
        "# http://127.0.0.1:8000/docs",
        ss["CodeRU"],
    ))
    story.append(Paragraph("6.1. Что лежит в scripts/", ss["H2RU"]))
    story.append(tbl([
        ["Скрипт", "Назначение"],
        ["run_everything.sh", "Всё сразу: compose, схема, uvicorn, demo, скрины"],
        ["bootstrap_schema.sh / .py", "Накатить схему и seed на WEST/EAST primary"],
        ["demo.sh", "Прогон API с пояснениями (нужен uvicorn)"],
        ["capture_screenshots.py", "PNG Swagger для отчёта"],
        ["make_dump.sh", "pg_dump → папка dump/ к сдаче"],
    ], [5 * cm, 11.5 * cm], fontsize=7.5))
    story.append(Paragraph(
        "Логика API — в <font face=\"DejaVuMono\">client/app/main.py</font> "
        "(не в scripts). Скрипты только поднимают окружение и дергают HTTP.",
        ss["BodyRU"],
    ))
    story.append(Paragraph("6.2. По шагам (если одна команда не нужна)", ss["H2RU"]))
    story.append(Preformatted(
        "docker compose up -d\n"
        "./scripts/bootstrap_schema.sh\n"
        "source .venv/bin/activate\n"
        "uvicorn client.app.main:app --port 8000\n"
        "./scripts/demo.sh",
        ss["CodeRU"],
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Файл сгенерирован скриптом docs/build_swagger_guide_pdf.py · "
        "пересборка: python docs/build_swagger_guide_pdf.py",
        ss["CenterRU"],
    ))

    def footer(c, doc):
        c.saveState()
        c.setFont("DejaVu", 8)
        c.setFillColor(colors.HexColor("#666"))
        c.drawString(1.8 * cm, 1 * cm, "Ермаков Л. · Swagger-шпаргалка · индивидуальный проект РБД")
        c.drawRightString(A4[0] - 1.8 * cm, 1 * cm, f"стр. {doc.page}")
        c.restoreState()

    doc = SimpleDocTemplate(
        str(PDF_OUT),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.5 * cm,
        title="Swagger-шпаргалка для защиты",
        author="Ермаков Л.",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    shutil.copy2(PDF_OUT, PDF_DOCS)
    print(f"PDF: {PDF_OUT}")
    print(f"PDF copy: {PDF_DOCS}")


if __name__ == "__main__":
    build()
