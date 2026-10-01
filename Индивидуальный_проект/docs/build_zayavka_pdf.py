#!/usr/bin/env python3
"""Сборка PDF-описания индивидуального проекта (без просьбы «принять тему»)."""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage,
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
ASSETS = BASE / "assets"
SHOTS = ROOT / "screenshots"
PDF_OUT = BASE / "Заявка_индивидуальный_проект_РБД.pdf"
PDF_ROOT = ROOT.parent / "Заявка_индивидуальный_проект_РБД.pdf"

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def fnt(path: str, size: int):
    return ImageFont.truetype(path, size)


def _arrow(d, x1, y1, x2, y2, color=(80, 80, 120), width=2):
    d.line([(x1, y1), (x2, y2)], fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 10
    d.polygon(
        [
            (x2, y2),
            (x2 - L * math.cos(ang - 0.4), y2 - L * math.sin(ang - 0.4)),
            (x2 - L * math.cos(ang + 0.4), y2 - L * math.sin(ang + 0.4)),
        ],
        fill=color,
    )


def draw_er(path: Path) -> Path:
    """Чистая ER: без пересечений стрелок, явные подписи FK (откуда order_id)."""
    W, H = 1680, 1180
    img = Image.new("RGB", (W, H), (245, 247, 252))
    d = ImageDraw.Draw(img)
    title = fnt(FONT_BOLD, 22)
    ent = fnt(FONT_BOLD, 13)
    attr = fnt(FONT_MONO, 11)
    small = fnt(FONT_REG, 12)
    tiny = fnt(FONT_REG, 11)

    d.text((30, 16), "ER-диаграмма контура отгрузок (3НФ) — связи через внешние ключи FK", font=title, fill=(20, 40, 80))
    d.text(
        (30, 48),
        "Стрелка 1→N: ОДИН родитель → МНОГО дочерних. Красный текст = FK (ссылка на PK другой таблицы).",
        font=small,
        fill=(60, 70, 90),
    )

    boxes = {
        "regions": (
            40, 90, "regions — регионы",
            ["id PK  — номер региона", "code UK — WEST / EAST", "name — название"],
        ),
        "warehouses": (
            40, 280, "warehouses — склады",
            ["id PK", "region_id FK → regions.id", "code / name", "UNIQUE(region_id, code)"],
        ),
        "orders": (
            40, 520, "shipment_orders — заявки",
            [
                "id PK  — номер заявки",
                "warehouse_id FK → warehouses.id",
                "region_code — ключ фрагмента",
                "status — ТЕКУЩИЙ статус",
                "created_at / updated_at",
            ],
        ),
        "products": (
            560, 90, "products — товары (справочник)",
            ["id PK  — номер товара", "sku UK — артикул", "title — название", "копия каталога на каждом шарде"],
        ),
        "stock": (
            560, 300, "stock_balances — остатки",
            [
                "id PK",
                "warehouse_id FK → warehouses.id",
                "product_id FK → products.id",
                "qty_available — доступно",
                "qty_reserved — в резерве",
                "UNIQUE(warehouse, product)",
            ],
        ),
        "items": (
            560, 560, "shipment_items — позиции заявки",
            [
                "id PK",
                "order_id FK → shipment_orders.id",
                "product_id FK → products.id",
                "qty — сколько штук в заявке",
                "UNIQUE(order_id, product_id)",
            ],
        ),
        "events": (
            1100, 560, "shipment_events — ЖУРНАЛ",
            [
                "id PK",
                "order_id FK → shipment_orders.id",
                "from_status → to_status",
                "created_at — когда сменили",
                "note — комментарий / контроль",
                "история ВСЕХ шагов заявки",
            ],
        ),
    }

    coords = {}
    for key, (x, y, title_t, attrs) in boxes.items():
        head_h = 36
        bw, bh = 420, head_h + 18 * len(attrs) + 16
        coords[key] = (x, y, bw, bh, head_h)
        d.rounded_rectangle([x + 3, y + 3, x + bw + 3, y + bh + 3], 8, fill=(200, 208, 220))
        d.rounded_rectangle([x, y, x + bw, y + bh], 8, fill=(255, 255, 255), outline=(35, 70, 130), width=2)
        d.rectangle([x, y, x + bw, y + head_h], fill=(35, 70, 130))
        d.text((x + 10, y + 9), title_t, font=ent, fill=(255, 255, 255))
        for i, a in enumerate(attrs):
            if "FK" in a:
                col = (160, 30, 30)
            elif "PK" in a or "UK" in a:
                col = (15, 110, 40)
            else:
                col = (35, 40, 50)
            d.text((x + 12, y + head_h + 8 + i * 18), a, font=attr, fill=col)

    def elbow(a, b, label, route="vh", color=(55, 80, 140)):
        ax, ay, aw, ah, _ = coords[a]
        bx, by, bw, bh, _ = coords[b]
        if route == "down":
            x1, y1 = ax + aw // 2, ay + ah
            x2, y2 = bx + bw // 2, by
            mid_y = (y1 + y2) // 2
            pts = [(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)]
        elif route == "right":
            x1, y1 = ax + aw, ay + ah // 2
            x2, y2 = bx, by + bh // 2
            mid_x = (x1 + x2) // 2
            pts = [(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)]
        else:  # vh
            x1, y1 = ax + aw // 2, ay + ah
            x2, y2 = bx, by + bh // 2
            pts = [(x1, y1), (x1, y2), (x2, y2)]
        for i in range(len(pts) - 2):
            d.line([pts[i], pts[i + 1]], fill=color, width=2)
        _arrow(d, pts[-2][0], pts[-2][1], pts[-1][0], pts[-1][1], color=color, width=2)
        mx = (pts[0][0] + pts[-1][0]) // 2
        my = (pts[0][1] + pts[-1][1]) // 2 - 8
        lines = label.split("\n")
        tw = max(len(ln) for ln in lines) * 6 + 14
        th = 14 * len(lines) + 6
        d.rounded_rectangle([mx - tw // 2, my - 2, mx + tw // 2, my + th], 5, fill=(255, 252, 235), outline=(190, 130, 40))
        for i, ln in enumerate(lines):
            d.text((mx - tw // 2 + 6, my + 2 + i * 14), ln, font=tiny, fill=(120, 50, 10))

    elbow("regions", "warehouses", "1:N\nFK warehouses.region_id\n→ regions.id", "down")
    elbow("warehouses", "stock", "1:N\nFK stock.warehouse_id\n→ warehouses.id", "right")
    elbow("products", "stock", "1:N\nFK stock.product_id\n→ products.id", "down")
    elbow("warehouses", "orders", "1:N\nFK orders.warehouse_id\n→ warehouses.id", "down")
    elbow("orders", "items", "1:N\nFK items.order_id\n→ orders.id", "right")
    # orders → events: вниз от orders, затем вправо к events (не через items)
    ax, ay, aw, ah, _ = coords["orders"]
    bx, by, bw, bh, _ = coords["events"]
    x1, y1 = ax + aw // 2, ay + ah
    y_rail = 860
    x2, y2 = bx + 40, by + bh
    pts = [(x1, y1), (x1, y_rail), (x2, y_rail), (x2, y2)]
    for i in range(len(pts) - 2):
        d.line([pts[i], pts[i + 1]], fill=(55, 80, 140), width=2)
    _arrow(d, pts[-2][0], pts[-2][1], pts[-1][0], pts[-1][1], color=(55, 80, 140), width=2)
    d.rounded_rectangle([x1 + 20, y_rail - 48, x1 + 320, y_rail - 4], 5, fill=(255, 252, 235), outline=(190, 130, 40))
    d.text((x1 + 28, y_rail - 44), "1:N  FK events.order_id → orders.id", font=tiny, fill=(120, 50, 10))
    d.text((x1 + 28, y_rail - 28), "(журнал ссылается на ЗАЯВКУ, не на items)", font=tiny, fill=(120, 50, 10))

    # products → items: вниз справа от products/stock, вход в items сверху — без пересечений
    ax, ay, aw, ah, _ = coords["products"]
    bx, by, bw, bh, _ = coords["items"]
    x1, y1 = ax + aw // 2 + 80, ay + ah
    # drop along right edge of products column, then into top of items
    rail_x = ax + aw + 30
    pts = [(ax + aw, ay + ah // 2), (rail_x, ay + ah // 2), (rail_x, by - 20), (bx + bw // 2, by - 20), (bx + bw // 2, by)]
    for i in range(len(pts) - 2):
        d.line([pts[i], pts[i + 1]], fill=(55, 80, 140), width=2)
    _arrow(d, pts[-2][0], pts[-2][1], pts[-1][0], pts[-1][1], color=(55, 80, 140), width=2)
    d.rounded_rectangle([rail_x + 6, (ay + by) // 2 - 18, rail_x + 220, (ay + by) // 2 + 24], 5, fill=(255, 252, 235), outline=(190, 130, 40))
    d.text((rail_x + 12, (ay + by) // 2 - 14), "1:N FK items.product_id", font=tiny, fill=(120, 50, 10))
    d.text((rail_x + 12, (ay + by) // 2 + 2), "→ products.id", font=tiny, fill=(120, 50, 10))

    d.rounded_rectangle([1100, 90, 1640, 300], 10, fill=(255, 255, 255), outline=(35, 70, 130), width=2)
    d.text((1115, 105), "Как читать order_id и журнал", font=fnt(FONT_BOLD, 14), fill=(20, 40, 80))
    for i, t in enumerate([
        "• order_id в items и events = номер заявки",
        "  shipment_orders.id (родитель — ЗАЯВКА).",
        "• Журнал НЕ берёт ключ из позиции items:",
        "  events.order_id → orders.id напрямую.",
        "• orders.status = только ТЕКУЩИЙ статус.",
        "• events = история всех переходов",
        "  NULL→CREATED→RESERVED→…→DELIVERED.",
        "• Пример: заявка id=5 ⇒ items.order_id=5",
        "  и events.order_id=5 на том же регионе.",
    ]):
        d.text((1115, 132 + i * 17), t, font=tiny, fill=(40, 45, 55))

    d.rounded_rectangle([40, 920, 1640, 1145], 10, fill=(255, 255, 255), outline=(35, 70, 130), width=2)
    d.text((55, 935), "Легенда и смысл связей", font=fnt(FONT_BOLD, 14), fill=(20, 40, 80))
    d.text((55, 965), "PK / UK — зелёным  ·  FK — красным (внешний ключ лежит в таблице «многих»).  1:N — один ко многим.", font=small, fill=(40, 45, 55))
    d.text((55, 995), "Регион 1──<N Склад 1──<N Остаток >N──1 Товар     Склад 1──<N Заявка 1──<N Позиция >N──1 Товар", font=fnt(FONT_MONO, 12), fill=(30, 40, 60))
    d.text((55, 1025), "                                                              └──<N Журнал (история статусов заявки)", font=fnt(FONT_MONO, 12), fill=(30, 40, 60))
    d.text((55, 1060), "Ключ фрагментации: region_code на заявке; позиции и журнал — производные (тот же шард, что заявка).", font=small, fill=(40, 45, 55))
    d.text((55, 1090), "products — реплика справочника (одинаковая копия на WEST и EAST), не отдельный оперативный фрагмент.", font=small, fill=(40, 45, 55))
    d.text((55, 1120), "status в orders — «сейчас»; строки events — «как шли шаги». Это разные таблицы.", font=small, fill=(20, 90, 40))

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    try:
        img.save(path.parent.parent.parent / "схема_ER_понятно.png")
    except Exception:
        pass
    return path


def draw_dist(path: Path) -> Path:
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (245, 247, 252))
    d = ImageDraw.Draw(img)
    title = fnt(FONT_BOLD, 20)
    body = fnt(FONT_REG, 12)
    bold = fnt(FONT_BOLD, 13)
    mono = fnt(FONT_MONO, 11)
    d.text((28, 14), "UML / deployment: фрагменты регионов и реплики (Docker Compose)", font=title, fill=(20, 40, 80))

    def panel(x, y, w, h, header, fill, outline=(60, 90, 140)):
        d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=fill, outline=outline, width=2)
        d.text((x + 16, y + 12), header, font=bold, fill=(20, 40, 80))

    panel(30, 55, 590, 380, "Регион WEST — фрагмент оперативки", (228, 238, 255))
    panel(660, 55, 590, 380, "Регион EAST — фрагмент оперативки", (228, 250, 235))

    def node(x, y, w, h, name, lines, color):
        d.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=(255, 255, 255), outline=color, width=2)
        d.rectangle([x, y, x + w, y + 28], fill=color)
        d.text((x + 10, y + 6), name, font=bold, fill=(255, 255, 255))
        for i, line in enumerate(lines):
            d.text((x + 10, y + 38 + i * 18), line, font=mono if i == 0 else body, fill=(40, 40, 40))

    node(55, 100, 250, 120, "west-primary :15432", ["роль: писатель / фрагмент", "stock, orders, items, events", "WAL → replica"], (35, 90, 160))
    node(340, 100, 250, 120, "west-replica :15433", ["роль: читатель / реплика", "hot standby (read-only)", "лаг: секунды (async)"], (110, 55, 150))
    node(685, 100, 250, 120, "east-primary :15434", ["роль: писатель / фрагмент", "stock, orders, items, events", "WAL → replica"], (35, 90, 160))
    node(970, 100, 250, 120, "east-replica :15435", ["роль: читатель / реплика", "hot standby (read-only)", "лаг: секунды (async)"], (110, 55, 150))

    _arrow(d, 305, 160, 340, 160, color=(200, 90, 30), width=3)
    d.text((250, 168), "async streaming", font=body, fill=(180, 70, 20))
    _arrow(d, 935, 160, 970, 160, color=(200, 90, 30), width=3)
    d.text((880, 168), "async streaming", font=body, fill=(180, 70, 20))

    # data note
    d.rounded_rectangle([55, 250, 590, 410], 8, fill=(255, 255, 255), outline=(100, 130, 180))
    d.text((70, 262), "Что лежит только на WEST", font=bold, fill=(20, 40, 80))
    for i, t in enumerate([
        "• warehouses / stock с region=WEST",
        "• shipment_* с region_code=WEST",
        "• products — копия справочника (реплика)",
        "• чужой EAST сюда не пишется",
    ]):
        d.text((70, 290 + i * 22), t, font=body, fill=(40, 40, 40))

    d.rounded_rectangle([685, 250, 1220, 410], 8, fill=(255, 255, 255), outline=(100, 160, 120))
    d.text((700, 262), "Что лежит только на EAST", font=bold, fill=(20, 40, 80))
    for i, t in enumerate([
        "• warehouses / stock с region=EAST",
        "• shipment_* с region_code=EAST",
        "• products — копия справочника (реплика)",
        "• чужой WEST сюда не пишется",
    ]):
        d.text((700, 290 + i * 22), t, font=body, fill=(40, 40, 40))

    panel(30, 460, 1220, 230, "Клиент FastAPI :8000 — роутинг по region_code", (255, 255, 255), (35, 70, 130))
    d.text((50, 505), "запись  →  primary региона          чтение  →  replica (fallback primary)", font=bold, fill=(30, 60, 110))
    d.text((50, 535), "критерий: горизонтальная фрагментация + режим доступа (периметр площадки)", font=body, fill=(50, 50, 50))
    d.text((50, 560), "отказ: POST статуса заявки WEST через /api/EAST/... → 403 (контур)", font=body, fill=(140, 40, 40))
    d.text((50, 585), "отказ узла: docker stop west-primary → запись WEST недоступна, чтение с west-replica", font=body, fill=(140, 40, 40))
    _arrow(d, 200, 460, 180, 220, color=(35, 90, 160), width=2)
    _arrow(d, 400, 460, 465, 220, color=(110, 55, 150), width=2)
    _arrow(d, 880, 460, 810, 220, color=(35, 90, 160), width=2)
    _arrow(d, 1080, 460, 1095, 220, color=(110, 55, 150), width=2)
    d.text((55, 640), "полнота: WEST∪EAST = весь контур · непересечение: одна заявка — один регион", font=body, fill=(60, 60, 60))

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def draw_lifecycle(path: Path) -> Path:
    W, H = 1280, 420
    img = Image.new("RGB", (W, H), (245, 247, 252))
    d = ImageDraw.Draw(img)
    d.text((24, 14), "UML state: жизненный цикл заявки (shipment_orders.status)", font=fnt(FONT_BOLD, 18), fill=(20, 40, 80))
    steps = [
        ("CREATED", "создана", "событие в journal"),
        ("RESERVED", "резерв", "avail− / reserved+"),
        ("PICKING", "сборка", "резерв держится"),
        ("SHIPPED", "отгружена", "reserved−"),
        ("DELIVERED", "доставлена", "терминал OK"),
    ]
    x0 = 30
    for i, (en, ru, note) in enumerate(steps):
        x = x0 + i * 230
        d.rounded_rectangle([x, 70, x + 200, 175], 10, fill=(255, 255, 255), outline=(35, 70, 130), width=2)
        d.rectangle([x, 70, x + 200, 100], fill=(35, 70, 130))
        d.text((x + 14, 76), en, font=fnt(FONT_BOLD, 13), fill=(255, 255, 255))
        d.text((x + 14, 112), ru, font=fnt(FONT_REG, 13), fill=(40, 40, 40))
        d.text((x + 14, 138), note, font=fnt(FONT_MONO, 11), fill=(80, 80, 80))
        if i < len(steps) - 1:
            _arrow(d, x + 200, 120, x + 230, 120, color=(200, 90, 30), width=3)
    d.rounded_rectangle([260, 220, 520, 320], 10, fill=(255, 240, 230), outline=(180, 80, 20), width=2)
    d.text((280, 240), "CANCELLED — отмена", font=fnt(FONT_BOLD, 13), fill=(140, 50, 20))
    d.text((280, 265), "из CREATED / RESERVED", font=fnt(FONT_REG, 12), fill=(80, 40, 20))
    d.text((280, 290), "откат резерва → events", font=fnt(FONT_MONO, 11), fill=(100, 50, 20))
    _arrow(d, 360, 175, 360, 220, color=(180, 80, 20), width=2)
    d.text((30, 350), "Каждый переход → INSERT в shipment_events (from_status → to_status). Чужой region_code → отказ 403.", font=fnt(FONT_REG, 12), fill=(50, 50, 50))
    d.text((30, 375), "Это предметный сценарий сверх CRUD: резерв, цепочка статусов, фиксация контроля.", font=fnt(FONT_REG, 12), fill=(50, 50, 50))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def draw_sequence(path: Path) -> Path:
    """UML sequence: клиент → FastAPI → primary/replica (отгрузка + отказ)."""
    W, H = 1400, 900
    img = Image.new("RGB", (W, H), (245, 247, 252))
    d = ImageDraw.Draw(img)
    title = fnt(FONT_BOLD, 18)
    bold = fnt(FONT_BOLD, 12)
    body = fnt(FONT_REG, 11)
    mono = fnt(FONT_MONO, 10)
    d.text((24, 12), "UML sequence: сценарий отгрузки WEST + отказ по критерию / отказ primary", font=title, fill=(20, 40, 80))

    actors = [
        (80, "Оператор\n/ curl"),
        (320, "FastAPI\nроутер"),
        (560, "west-\nprimary"),
        (800, "west-\nreplica"),
        (1040, "east-\nprimary"),
        (1280, "events\nжурнал"),
    ]
    lifeline_top = 120
    lifeline_bot = 860
    xs = []
    for x, name in actors:
        xs.append(x)
        d.rounded_rectangle([x - 70, 50, x + 70, 110], 8, fill=(255, 255, 255), outline=(35, 70, 130), width=2)
        for i, line in enumerate(name.split("\n")):
            d.text((x - 55, 60 + i * 18), line, font=bold, fill=(20, 40, 80))
        # dashed lifeline
        y = lifeline_top
        while y < lifeline_bot:
            d.line([(x, y), (x, min(y + 10, lifeline_bot))], fill=(160, 170, 190), width=1)
            y += 16

    def msg(y, x1, x2, text, color=(35, 70, 130), dashed=False):
        if dashed:
            # simple dash
            step = 8
            x = x1
            direction = 1 if x2 > x1 else -1
            while (direction > 0 and x < x2) or (direction < 0 and x > x2):
                d.line([(x, y), (x + direction * step, y)], fill=color, width=2)
                x += direction * (step + 6)
            # arrow tip
            tip = x2
            d.polygon([(tip, y), (tip - direction * 10, y - 5), (tip - direction * 10, y + 5)], fill=color)
        else:
            _arrow(d, x1, y, x2, y, color=color, width=2)
        # label above
        mx = (x1 + x2) // 2
        tw = min(len(text) * 6 + 8, abs(x2 - x1) - 10)
        d.text((mx - tw // 2, y - 18), text, font=mono, fill=color)

    def note(y, text, color=(100, 50, 20)):
        d.text((40, y), text, font=body, fill=color)

    y = 145
    note(y - 5, "1. Создание заявки и цепочка статусов (запись только на primary WEST)")
    y = 170
    msg(y, xs[0], xs[1], "POST /api/WEST/orders")
    y = 205
    msg(y, xs[1], xs[2], "INSERT order+item")
    y = 240
    msg(y, xs[2], xs[5], "INSERT event CREATED", color=(20, 120, 60))
    y = 275
    msg(y, xs[2], xs[1], "201 + routing.primary", color=(20, 120, 60), dashed=True)
    y = 310
    msg(y, xs[1], xs[0], "JSON (region=WEST)", color=(20, 120, 60), dashed=True)

    y = 350
    note(y - 5, "2. RESERVED → PICKING → SHIPPED → DELIVERED (каждая смена → events)")
    y = 375
    msg(y, xs[0], xs[1], "POST .../status RESERVED")
    y = 410
    msg(y, xs[1], xs[2], "UPDATE stock + status")
    y = 445
    msg(y, xs[2], xs[5], "event RESERVED", color=(20, 120, 60))
    y = 480
    msg(y, xs[0], xs[1], "… PICKING / SHIPPED / DELIVERED")
    y = 515
    msg(y, xs[1], xs[2], "списание reserved / финал")

    y = 555
    note(y - 5, "3. Чтение журнала — с replica")
    y = 580
    msg(y, xs[0], xs[1], "GET .../events", color=(110, 55, 150))
    y = 615
    msg(y, xs[1], xs[3], "SELECT events", color=(110, 55, 150))
    y = 650
    msg(y, xs[3], xs[1], "rows + role=replica", color=(110, 55, 150), dashed=True)

    y = 690
    note(y - 5, "4. Нарушение критерия контура")
    y = 715
    msg(y, xs[0], xs[1], "POST /api/EAST/orders/{WEST_id}/status", color=(160, 40, 40))
    y = 750
    msg(y, xs[1], xs[4], "проверка region_code", color=(160, 40, 40))
    y = 785
    msg(y, xs[1], xs[0], "403 отказ по критерию контура", color=(160, 40, 40), dashed=True)

    y = 825
    note(y - 5, "5. Отказ узла: primary DOWN → запись запрещена, чтение с replica")
    y = 850
    msg(y, xs[1], xs[2], "write FAIL", color=(160, 40, 40))
    msg(y, xs[1], xs[3], "read OK (fallback)", color=(110, 55, 150))

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def build_pdf(er: Path, dist: Path, life: Path):
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_REG))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_BOLD))
    pdfmetrics.registerFont(TTFont("DejaVuMono", FONT_MONO))
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="TitleRU", fontName="DejaVu-Bold", fontSize=16, alignment=TA_CENTER, leading=20, spaceAfter=8))
    ss.add(ParagraphStyle(name="H1RU", fontName="DejaVu-Bold", fontSize=12, textColor=colors.HexColor("#1a3a6b"), spaceBefore=10, spaceAfter=5, leading=15))
    ss.add(ParagraphStyle(name="H2RU", fontName="DejaVu-Bold", fontSize=11, textColor=colors.HexColor("#2a4a7a"), spaceBefore=8, spaceAfter=4, leading=14))
    ss.add(ParagraphStyle(name="BodyRU", fontName="DejaVu", fontSize=10, alignment=TA_JUSTIFY, leading=13, spaceAfter=5))
    ss.add(ParagraphStyle(name="CenterRU", fontName="DejaVu", fontSize=10, alignment=TA_CENTER, leading=13, spaceAfter=4))
    ss.add(ParagraphStyle(name="BulletRU", fontName="DejaVu", fontSize=10, leftIndent=8, leading=13, spaceAfter=2))
    ss.add(ParagraphStyle(name="CodeRU", fontName="DejaVuMono", fontSize=8, leading=10, backColor=colors.HexColor("#f4f6f8"), spaceAfter=6))

    def fit(p: Path, mw=17 * cm, mh=9.5 * cm):
        im = RLImage(str(p))
        sc = min(mw / im.imageWidth, mh / im.imageHeight, 1)
        im.drawWidth = im.imageWidth * sc
        im.drawHeight = im.imageHeight * sc
        return im

    def tbl(data, widths):
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a6b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#99aacc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fa")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    story = []
    story.append(Paragraph("ОПИСАНИЕ ИНДИВИДУАЛЬНОГО ПРОЕКТА", ss["TitleRU"]))
    story.append(Paragraph("Дисциплина: «Распределённые и облачные базы данных»", ss["CenterRU"]))
    story.append(Spacer(1, 6))
    story.append(tbl([
        ["Поле", "Значение"],
        ["ФИО", "Ермаков Лаврентий"],
        ["Группа", "М09-КИИ26"],
        ["Дата", datetime.now().strftime("%d.%m.%Y")],
    ], [4 * cm, 12.5 * cm]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Тема проекта", ss["H1RU"]))
    story.append(Paragraph(
        "<b>«Горизонтально фрагментированная СУБД контура исполнения отгрузок "
        "на распределённых складских площадках»</b>.",
        ss["BodyRU"],
    ))
    story.append(Paragraph(
        "Простыми словами: нужно сделать учебный стенд, где склады в разных регионах "
        "ведут <b>остатки и заявки на отгрузку</b> на своих узлах PostgreSQL. "
        "Это не интернет-магазин и не витрина для покупателя — в центре внимание "
        "оператора площадки: что есть на складе, что зарезервировано, что собрали и отправили.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("2. Зачем такой проект (идея)", ss["H1RU"]))
    story.append(Paragraph(
        "В реальной логистике оперативные данные «привязаны» к площадке: склад WEST не должен "
        "писать в остатки EAST. Распределение здесь нужно не «для балансировки ради скорости», "
        "а чтобы соблюсти <b>периметр региона</b>, дать <b>автономность</b> при обрыве канала "
        "и разделить роли узлов (запись / чтение) внутри региона.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("3. Что будет в базе (контур данных)", ss["H1RU"]))
    story.append(Paragraph(
        "В учебном стенде два региона — <b>WEST</b> и <b>EAST</b> (контейнеры Docker). "
        "Ниже — сущности предметной области и их английские имена в схеме БД.",
        ss["BodyRU"],
    ))
    story.append(tbl([
        ["Таблица (EN)", "По-русски", "Что хранит"],
        ["regions", "регионы", "Периметр площадки: код WEST/EAST, название"],
        ["warehouses", "склады", "Склад внутри региона (code, name)"],
        ["products", "товары / номенклатура", "Общий справочник: sku, title"],
        ["stock_balances", "остатки", "Сколько доступно (qty_available) и в резерве (qty_reserved)"],
        ["shipment_orders", "заявки на отгрузку", "Наряд: склад, region_code, status, дата"],
        ["shipment_items", "позиции заявки", "Какие товары и в каком количестве (qty)"],
        ["shipment_events", "журнал событий", "Смена статуса: from→to, время, кто"],
    ], [4.2 * cm, 4.3 * cm, 8 * cm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("3.1. Словарь ключевых полей", ss["H2RU"]))
    story.append(tbl([
        ["Поле (EN)", "Перевод / смысл"],
        ["region_code", "код региона — ключ горизонтальной фрагментации"],
        ["sku", "артикул товара (Stock Keeping Unit)"],
        ["qty_available / qty_reserved", "доступно к продаже / уже зарезервировано"],
        ["status", "статус жизненного цикла заявки"],
        ["from_status / to_status", "предыдущий и новый статус в журнале"],
        ["primary / replica", "узел записи / узел чтения (реплика)"],
        ["async streaming", "асинхронная потоковая репликация WAL"],
    ], [5.5 * cm, 11 * cm]))

    story.append(PageBreak())
    story.append(Paragraph("4. Почему база именно распределённая", ss["H1RU"]))
    for b in [
        "<b>Периметр площадки.</b> Остатки и заявки WEST не лежат и не меняются вместе с EAST.",
        "<b>Автономность.</b> При потере канала до другого региона площадка продолжает локальные операции на своём primary.",
        "<b>Роли узлов.</b> Primary пишет, replica читает. Второй регион — другой <i>фрагмент</i> данных, а не копия «для балансировки».",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))
    story.append(Paragraph(
        "Критерий распределения: <b>по контуру / площадке</b> (+ режим доступа: оперативка не покидает периметр), "
        "ключ размещения — <font face=\"DejaVuMono\">region_code</font>.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("5. Как данные режутся между узлами", ss["H1RU"]))
    story.append(Paragraph(
        "Строка оперативных таблиц с <font face=\"DejaVuMono\">region_code = WEST</font> существует "
        "только на узлах WEST; то же для EAST. Позиции и события — <b>производная</b> фрагментация: "
        "следуют за заявкой своего региона. Справочник <font face=\"DejaVuMono\">products</font> "
        "копируется на оба региона (реплика справочника).",
        ss["BodyRU"],
    ))
    story.append(tbl([
        ["Параметр", "Значение"],
        ["Критерий", "по контуру / площадке + режим доступа (region_code)"],
        ["Фрагментация", "горизонтальная; items/events — производные от заявки"],
        ["Репликация", "async streaming primary → replica внутри региона"],
        ["Узлы стенда", "≥ 4 PostgreSQL (2 региона × primary + replica)"],
        ["Полнота / непересечение", "WEST+EAST = весь контур; одна заявка — один регион"],
    ], [4.5 * cm, 12 * cm]))
    story.append(Paragraph("5.1. Если узел упал", ss["H2RU"]))
    for b in [
        "упал primary региона → запись в этот регион нельзя, чтение — с replica;",
        "упал replica → запись на primary продолжается, чтение можно с primary;",
        "запрос «сменить статус заявки чужого региона» → отказ, даже если другой узел жив.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    story.append(Paragraph("6. Операции сверх обычного CRUD", ss["H1RU"]))
    story.append(Paragraph(
        "CRUD по складам/товарам/остаткам/заявкам будет. Главное — предметный сценарий отгрузки "
        "с резервом остатка и журналом контроля:",
        ss["BodyRU"],
    ))
    story.append(fit(life, mh=6.2 * cm))
    story.append(Paragraph("Рисунок — жизненный цикл shipment_orders.status", ss["CenterRU"]))
    for b in [
        "<b>RESERVED</b> — резерв под заявку (нельзя зарезервировать больше qty_available);",
        "<b>PICKING → SHIPPED → DELIVERED</b> — сборка, отправка, подтверждение;",
        "<b>CANCELLED</b> — отмена из CREATED/RESERVED с откатом резерва;",
        "каждая смена статуса → запись в <font face=\"DejaVuMono\">shipment_events</font>;",
        "попытка трогать чужой регион → отказ с понятной причиной;",
        "в логе/UI видно: регион операции и узел (primary / replica).",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    story.append(PageBreak())
    story.append(Paragraph("7. UML / ER предметной области", ss["H1RU"]))
    story.append(Paragraph(
        "Модель в 3НФ: связи через FK, без дублирования названия региона в каждой строке остатка. "
        "На диаграмме английские имена таблиц подписаны по-русски.",
        ss["BodyRU"],
    ))
    story.append(fit(er, mh=11 * cm))
    story.append(Paragraph("Рисунок 1 — ER-диаграмма (EN + перевод)", ss["CenterRU"]))
    story.append(Preformatted(
        "Регион 1──<N Склад 1──<N Остаток >N──1 Товар\n"
        "                 │\n"
        "                 └──<N Заявка 1──<N Позиция >N──1 Товар\n"
        "                           │\n"
        "                           └──<N Событие (смена статуса)",
        ss["CodeRU"],
    ))

    story.append(Paragraph("8. UML распределения по узлам", ss["H1RU"]))
    story.append(fit(dist, mh=8.5 * cm))
    story.append(Paragraph("Рисунок 2 — фрагменты регионов и реплики", ss["CenterRU"]))
    story.append(tbl([
        ["Узел", "Роль", "Что хранит", "Кто пишет"],
        ["west-primary", "писатель", "оперативка WEST", "клиент"],
        ["west-replica", "читатель", "реплика WEST", "никто"],
        ["east-primary", "писатель", "оперативка EAST", "клиент"],
        ["east-replica", "читатель", "реплика EAST", "никто"],
    ], [3.5 * cm, 3 * cm, 5.5 * cm, 4.5 * cm]))

    story.append(Paragraph("9. Стенд и результат работы", ss["H1RU"]))
    story.append(Paragraph(
        "Docker Compose: 4 × PostgreSQL + клиент FastAPI. Запись → primary региона; "
        "чтение → replica. Артефакты: docker-compose, SQL/seed, клиент, зависимости, "
        "скрипты демо и реальные скриншоты Swagger/API. "
        "Каталог реализации: <b>Индивидуальный_проект/</b>.",
        ss["BodyRU"],
    ))
    for b in [
        "схема БД (3НФ + FK) и тестовые данные;",
        "стенд из четырёх узлов (2 региона × primary + replica);",
        "клиент: полный CRUD warehouses/products/stock/orders + цепочка статусов + отказ узла / отказ по периметру;",
        "отчёт/описание: UML, схема распределения, демо, скриншоты.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    # Реальные скриншоты демо (если есть)
    shot_specs = [
        ("00_docker_compose_ps.png", "Стенд: docker compose ps — 4 узла PostgreSQL"),
        ("01_swagger_home.png", "Swagger UI: полный список API (включая warehouses/products)"),
        ("05_swagger_warehouse_post.png", "CRUD складов: POST /warehouses → primary WEST"),
        ("06_swagger_product_post.png", "CRUD товаров: POST /products → primary WEST"),
        ("08_swagger_order_post.png", "Создание заявки на отгрузку"),
        ("api_10_status_DELIVERED.png", "Цепочка статусов до DELIVERED"),
        ("api_11_events.png", "Журнал shipment_events"),
        ("api_12_cross_region.png", "Отказ по критерию контура (чужой регион)"),
        ("api_13_write_fail.png", "Отказ записи при docker stop west-primary"),
        ("api_13_read_replica.png", "Чтение с replica при недоступном primary"),
    ]
    existing = [(SHOTS / n, cap) for n, cap in shot_specs if (SHOTS / n).exists()]
    if existing:
        story.append(PageBreak())
        story.append(Paragraph("10. Демонстрация стенда (реальные скриншоты)", ss["H1RU"]))
        story.append(Paragraph(
            "Ниже — снимки живого стенда (Swagger UI и JSON-ответы клиента), "
            "снятые Playwright после прогона <font face=\"DejaVuMono\">scripts/demo.sh</font>.",
            ss["BodyRU"],
        ))
        for i, (path, cap) in enumerate(existing, 1):
            story.append(Paragraph(f"10.{i}. {cap}", ss["H2RU"]))
            story.append(fit(path, mw=16.5 * cm, mh=10.5 * cm))
            story.append(Paragraph(f"Рисунок 10.{i} — {path.name}", ss["CenterRU"]))
            if i % 2 == 0 and i < len(existing):
                story.append(PageBreak())

    def footer(c, doc):
        c.saveState()
        c.setFont("DejaVu", 8)
        c.setFillColor(colors.HexColor("#666"))
        c.drawString(1.8 * cm, 1 * cm, "Ермаков Л. · М09-КИИ26 · индивидуальный проект РБД")
        c.drawRightString(A4[0] - 1.8 * cm, 1 * cm, f"стр. {doc.page}")
        c.restoreState()

    doc = SimpleDocTemplate(
        str(PDF_OUT), pagesize=A4,
        leftMargin=1.7 * cm, rightMargin=1.7 * cm, topMargin=1.4 * cm, bottomMargin=1.5 * cm,
        title="Описание индивидуального проекта РБД", author="Ермаков Лаврентий",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("PDF:", PDF_OUT)
    try:
        import shutil
        shutil.copy2(PDF_OUT, PDF_ROOT)
        print("PDF copy:", PDF_ROOT)
    except Exception as exc:  # noqa: BLE001
        print("copy skip:", exc)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    er = draw_er(ASSETS / "uml_er.png")
    dist = draw_dist(ASSETS / "uml_distribution.png")
    life = draw_lifecycle(ASSETS / "uml_lifecycle.png")
    build_pdf(er, dist, life)


if __name__ == "__main__":
    main()
