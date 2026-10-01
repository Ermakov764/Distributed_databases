#!/usr/bin/env python3
"""Отчёт о выполнении индивидуального проекта РБД (PDF по чек-листу задания)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
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

from build_zayavka_pdf import draw_er, draw_lifecycle, draw_sequence

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
ASSETS = BASE / "assets"
SHOTS = ROOT / "screenshots"
PDF_OUT = ROOT / "Отчёт_индивидуальный_проект_РБД.pdf"
PDF_DOCS = BASE / "Отчёт_индивидуальный_проект_РБД.pdf"

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def styles():
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_REG))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_BOLD))
    pdfmetrics.registerFont(TTFont("DejaVuMono", FONT_MONO))
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="TitleRU", fontName="DejaVu-Bold", fontSize=15, alignment=TA_CENTER, leading=19, spaceAfter=6))
    ss.add(ParagraphStyle(name="H1RU", fontName="DejaVu-Bold", fontSize=12, textColor=colors.HexColor("#1a3a6b"), spaceBefore=10, spaceAfter=5, leading=15))
    ss.add(ParagraphStyle(name="H2RU", fontName="DejaVu-Bold", fontSize=10.5, textColor=colors.HexColor("#2a4a7a"), spaceBefore=7, spaceAfter=3, leading=13))
    ss.add(ParagraphStyle(name="BodyRU", fontName="DejaVu", fontSize=9.5, alignment=TA_JUSTIFY, leading=12.5, spaceAfter=4))
    ss.add(ParagraphStyle(name="CenterRU", fontName="DejaVu", fontSize=9, alignment=TA_CENTER, leading=12, spaceAfter=3))
    ss.add(ParagraphStyle(name="BulletRU", fontName="DejaVu", fontSize=9.5, leftIndent=8, leading=12.5, spaceAfter=2))
    ss.add(ParagraphStyle(name="CodeRU", fontName="DejaVuMono", fontSize=7.5, leading=9.5, backColor=colors.HexColor("#f4f6f8"), spaceBefore=2, spaceAfter=5, leftIndent=2, rightIndent=2))
    ss.add(ParagraphStyle(name="SmallRU", fontName="DejaVu", fontSize=8.5, alignment=TA_LEFT, leading=11, spaceAfter=2))
    return ss


def fit(path: Path, mw=16.5 * cm, mh=9.5 * cm):
    im = RLImage(str(path))
    sc = min(mw / im.imageWidth, mh / im.imageHeight, 1)
    im.drawWidth = im.imageWidth * sc
    im.drawHeight = im.imageHeight * sc
    return im


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def tbl(data, widths, fontsize=8):
    """Таблица с переносом текста в ячейках (иначе ReportLab рисует поверх соседей)."""
    cell_style = ParagraphStyle(
        name=f"TblCell_{fontsize}_{id(data)}",
        fontName="DejaVu",
        fontSize=fontsize,
        leading=fontsize + 3,
        alignment=TA_LEFT,
    )
    head_style = ParagraphStyle(
        name=f"TblHead_{fontsize}_{id(data)}",
        fontName="DejaVu-Bold",
        fontSize=fontsize,
        leading=fontsize + 3,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    wrapped = []
    for r_i, row in enumerate(data):
        style = head_style if r_i == 0 else cell_style
        wrapped.append([Paragraph(_esc(c), style) for c in row])

    t = Table(wrapped, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a6b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#99aacc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t



def build_pdf(er: Path, dist: Path, life: Path, seq: Path) -> Path:
    ss = styles()
    story = []

    # --- Титул ---
    story.append(Paragraph("ОТЧЁТ О ВЫПОЛНЕНИИ ИНДИВИДУАЛЬНОГО ПРОЕКТА", ss["TitleRU"]))
    story.append(Paragraph("Дисциплина: «Распределённые и облачные базы данных»", ss["CenterRU"]))
    story.append(Spacer(1, 4))
    story.append(tbl([
        ["Поле", "Значение"],
        ["ФИО", "Ермаков Лаврентий"],
        ["Группа", "М09-КИИ26"],
        ["Дата", datetime.now().strftime("%d.%m.%Y")],
        ["Каталог", "Индивидуальный_проект/"],
    ], [3.5 * cm, 13 * cm]))

    # --- 1. ТЗ ---
    story.append(Paragraph("1. Описание ТЗ и связь с темой работы", ss["H1RU"]))
    story.append(Paragraph(
        "<b>Тема проекта:</b> «Горизонтально фрагментированная СУБД контура исполнения "
        "отгрузок на распределённых складских площадках».",
        ss["BodyRU"],
    ))
    story.append(Paragraph(
        "Предметная область — <b>операционный контур площадок</b>: остатки, резерв, сборка, "
        "отгрузка, подтверждение доставки. Это не интернет-магазин и не витрина для покупателя. "
        "Учебное упрощение контура: два региона (WEST/EAST), синтетические данные, имитация "
        "площадок контейнерами Docker; критерий распределения и смысл операций сохранены.",
        ss["BodyRU"],
    ))
    story.append(Paragraph("Требования задания, закрытые в проекте:", ss["BodyRU"]))
    for b in [
        "распределённая БД с явным критерием размещения (не «балансировка»);",
        "инфологическая и даталогическая модели в 3НФ с внешними ключами;",
        "стенд ≥ 2 процессов PostgreSQL (реализовано 4: 2 региона × primary + replica);",
        "клиент: CRUD ключевых сущностей + учёт распределения + предметный сценарий сверх CRUD;",
        "отказ узла, чтение с реплики, отказ при нарушении критерия контура;",
        "электронно: docker-compose, SQL/seed, клиент, зависимости, скрипты демо.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    story.append(Paragraph("1.1. Контур данных", ss["H2RU"]))
    story.append(tbl([
        ["Таблица", "По-русски", "Назначение"],
        ["regions", "регионы", "Периметр площадки (WEST/EAST)"],
        ["warehouses", "склады", "Склад внутри региона"],
        ["products", "товары", "Справочник номенклатуры (реплика на шардах)"],
        ["stock_balances", "остатки", "qty_available / qty_reserved"],
        ["shipment_orders", "заявки", "Наряд: склад, region_code, ТЕКУЩИЙ status"],
        ["shipment_items", "позиции", "Товар и количество в заявке (order_id → orders.id)"],
        ["shipment_events", "журнал", "История смен статусов: from→to, время, note"],
    ], [3.5 * cm, 3.2 * cm, 9.8 * cm]))
    story.append(Paragraph(
        "<b>Журнал vs статус заявки.</b> Поле <font face=\"DejaVuMono\">shipment_orders.status</font> "
        "хранит только <b>текущий</b> статус. Таблица <font face=\"DejaVuMono\">shipment_events</font> — "
        "это журнал: каждая строка = один переход "
        "(<font face=\"DejaVuMono\">from_status → to_status</font>), плюс "
        "<font face=\"DejaVuMono\">created_at</font>, <font face=\"DejaVuMono\">note</font>, "
        "<font face=\"DejaVuMono\">order_id</font> (= <font face=\"DejaVuMono\">shipment_orders.id</font>). "
        "Примеры: NULL→CREATED, CREATED→RESERVED, … → DELIVERED / CANCELLED. "
        "Журнал лежит на том же фрагменте, что и заявка (производная фрагментация).",
        ss["BodyRU"],
    ))
    story.append(Paragraph("1.1.1. Как работает журнал (подробно)", ss["H2RU"]))
    story.append(Paragraph(
        "Журнал фиксирует <b>каждое действие смены статуса</b> заявки в пределах "
        "<b>своего фрагмента</b> (WEST — только заявки WEST, EAST — только EAST). "
        "Это не общий лог на всю систему и не «лог сервера PostgreSQL», а предметная "
        "таблица истории исполнения наряда.",
        ss["BodyRU"],
    ))
    story.append(tbl([
        ["Поле строки events", "Что означает"],
        ["order_id", "Какая заявка (FK → shipment_orders.id)"],
        ["from_status", "Какой статус был до перехода (для создания заявки — NULL)"],
        ["to_status", "Какой статус стал после перехода"],
        ["created_at", "Когда зафиксировали переход"],
        ["note", "Комментарий / зачем сменили (контроль)"],
    ], [4.5 * cm, 12 * cm], fontsize=8))
    story.append(Paragraph(
        "<b>Запись журнала</b> выполняется <b>только на primary</b> региона вместе со "
        "сменой статуса (один и тот же запрос к primary: UPDATE orders + INSERT events). "
        "Потом async replication копирует новые строки events на replica.",
        ss["BodyRU"],
    ))
    story.append(Paragraph(
        "<b>Чтение журнала</b> (<font face=\"DejaVuMono\">GET …/orders/{id}/events</font>) "
        "идёт <b>предпочтительно с replica</b> того же региона; если replica недоступна — "
        "клиент читает с primary. Одновременно с primary и replica клиент <b>не</b> читает: "
        "выбирается один узел. Небольшой лаг replica возможен сразу после записи.",
        ss["BodyRU"],
    ))
    story.append(Preformatted(
        "CREATE → INSERT event (NULL → CREATED)           // на primary\n"
        "RESERVED → INSERT event (CREATED → RESERVED)     // на primary\n"
        "PICKING / SHIPPED / DELIVERED — тоже по одной строке events\n"
        "GET events → SELECT с replica (fallback primary) // только чтение",
        ss["CodeRU"],
    ))

    story.append(Paragraph("1.2. Профиль запросов", ss["H2RU"]))
    story.append(tbl([
        ["Где", "Операции"],
        ["Узел региона (площадка)", "CRUD остатков/складов; создание заявки; резерв; статусы; события"],
        ["Replica региона", "Только чтение остатков, заявок, событий"],
        ["Межрегионно / «центр»", "Справочник products; запрещены кросс-региональные UPDATE остатков"],
        ["Несколько узлов", "Только при ошибочном запросе чужого региона → отказ по критерию"],
    ], [4.5 * cm, 12 * cm], fontsize=7.5))

    story.append(Paragraph("1.3. Безопасность и надёжность (контекст объекта КИИ)", ss["H2RU"]))
    story.append(Paragraph(
        "Профиль направления — объекты <b>критической информационной инфраструктуры (КИИ)</b>. "
        "В учебном стенде это отражено не «магазином с паролями», а правилами размещения "
        "и отказоустойчивости оперативных данных обеспечения площадок.",
        ss["BodyRU"],
    ))
    story.append(Paragraph("<b>Безопасность (режим доступа / периметр)</b>", ss["BodyRU"]))
    for b in [
        "Оперативка региона <b>не покидает периметр</b> своего фрагмента: "
        "строка с <font face=\"DejaVuMono\">region_code=WEST</font> существует только на узлах WEST.",
        "Клиент <b>отказывает</b> в записи/смене статуса чужого региона (HTTP 403), "
        "даже если другой шард жив — это контроль нарушения контура, а не «фолбэк на соседний сервер».",
        "Роли узлов разделены: на replica писать нельзя (hot standby read-only); "
        "приложение направляет запись только на primary.",
        "Журнал <font face=\"DejaVuMono\">shipment_events</font> фиксирует каждую смену статуса "
        "(аналог контроля/квитирования) — кто/когда перевёл заявку, для аудита исполнения.",
        "Учётные данные стенда учебные; в отчёт боевые секреты не включаются "
        "(требование задания).",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))
    story.append(Paragraph("<b>Надёжность (доступность при отказах)</b>", ss["BodyRU"]))
    for b in [
        "Внутри региона — <b>primary + async replica</b>: при падении primary чтение "
        "продолжается с replica; при падении replica запись на primary сохраняется.",
        "<b>Автономность площадки:</b> потеря канала до другого региона не останавливает "
        "локальные отгрузки на своём primary.",
        "Другой регион — <b>другой фрагмент</b>, а не «запасная копия для балансировки»: "
        "гибель WEST не подменяет данные EAST и наоборот (нет скрытого смешения периметров).",
        "Цепочка статусов с проверками остатка (нельзя зарезервировать больше available) "
        "снижает риск некорректного исполнения наряда при сбоях/повторных запросах.",
        "Модель отказа и демо <font face=\"DejaVuMono\">docker stop</font> primary описаны "
        "в §5; сбор глобальной картины без нарушения периметра — в §3.2.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))
    story.append(Paragraph(
        "Итого для КИИ-логики стенда: <b>безопасность</b> = резидентность оперативки "
        "и запрет кросс-контурных операций; <b>надёжность</b> = реплика на чтение, "
        "автономность региона и предсказуемое поведение при отказе узла. "
        "Полный контур аттестации КИИ (СЗИ, криптография каналов, ИБ-политики) "
        "в учебном проекте намеренно упрощён — сохранены критерий и смысл операций.",
        ss["BodyRU"],
    ))

    # --- 2. UML ---
    story.append(PageBreak())
    story.append(Paragraph("2. UML структуры данных (ER)", ss["H1RU"]))
    story.append(Paragraph(
        "Модель в <b>третьей нормальной форме</b>: связи через FK, без дублирования названия "
        "региона в каждой строке остатка.",
        ss["BodyRU"],
    ))
    story.append(fit(er, mh=11.5 * cm))
    story.append(Paragraph("Рисунок 1 — UML / ER: структура данных (3НФ, PK/FK, 1:N)", ss["CenterRU"]))
    story.append(Preformatted(
        "Region 1──<N Warehouse 1──<N StockBalance >N──1 Product\n"
        "                 │\n"
        "                 └──<N ShipmentOrder 1──<N ShipmentItem >N──1 Product\n"
        "                              │\n"
        "                              └──<N ShipmentEvent",
        ss["CodeRU"],
    ))

    # --- 2.1 Sequence UML (новая) ---
    story.append(PageBreak())
    story.append(Paragraph("2.1. UML sequence — сценарий отгрузки и отказы", ss["H1RU"]))
    story.append(Paragraph(
        "Диаграмма последовательностей показывает, как клиент взаимодействует с роутером "
        "и узлами: запись идёт на <b>primary</b>, чтение событий — с <b>replica</b>, "
        "попытка трогать чужой регион даёт отказ по критерию, при падении primary "
        "запись запрещена, а чтение остаётся через replica.",
        ss["BodyRU"],
    ))
    story.append(fit(seq, mw=17 * cm, mh=14 * cm))
    story.append(Paragraph("Рисунок 1а — UML sequence: отгрузка WEST + отказ контура / primary", ss["CenterRU"]))

    # --- 3. Распределение ---
    story.append(PageBreak())
    story.append(Paragraph("3. Схема распределения и критерий", ss["H1RU"]))
    story.append(Paragraph(
        "<b>Критерий:</b> по контуру / площадке + по режиму доступа. Ключ размещения — "
        "<font face=\"DejaVuMono\">region_code</font>. Оперативка региона существует только "
        "на узлах этого региона. Ответ «распределили для балансировки» не используется.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("3.0. Что означают термины фрагментации и репликации", ss["H2RU"]))
    story.append(Paragraph(
        "Ниже — те же понятия простыми словами (как отвечать на защите).",
        ss["BodyRU"],
    ))
    for b in [
        "<b>Горизонтальная первичная фрагментация.</b> Таблица «режется по строкам», "
        "а не по столбцам. Правило: все строки оперативки с "
        "<font face=\"DejaVuMono\">region_code = WEST</font> лежат только на узлах WEST; "
        "с EAST — только на EAST. «Первичная» значит: это основной разрез предметных "
        "таблиц (<font face=\"DejaVuMono\">stock_balances</font>, "
        "<font face=\"DejaVuMono\">shipment_orders</font>), от которого дальше "
        "зависят связанные таблицы.",
        "<b>Производная фрагментация (items / events).</b> "
        "<font face=\"DejaVuMono\">shipment_items</font> и "
        "<font face=\"DejaVuMono\">shipment_events</font> сами по себе не режутся "
        "отдельным ключом: они <b>следуют за заявкой</b>. Если заявка WEST, то её "
        "позиции и журнал событий тоже только на WEST. Иначе связь order→items "
        "разъехалась бы по разным серверам.",
        "<b>Async streaming primary → replica.</b> Внутри региона PostgreSQL "
        "передаёт журнал WAL с primary на replica <b>потоком и асинхронно</b>: "
        "запись подтверждается на primary, реплика догоняет с лагом в секунды. "
        "Replica — <b>только чтение</b> (hot standby). Это не второй фрагмент данных, "
        "а копия того же фрагмента для надёжности чтения.",
        "<b>products — реплика справочника.</b> Номенклатура нужна и WEST, и EAST, "
        "но это не «ещё один кусок оперативки». На оба шарда кладётся <b>одинаковая "
        "копия</b> справочника (при bootstrap/seed). Менять остатки чужого региона "
        "через products нельзя: products не содержит qty и не является шардом "
        "оперативного контура.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    story.append(tbl([
        ["Параметр", "Значение"],
        ["Фрагментация", "горизонтальная первичная по region_code"],
        ["Производная", "shipment_items / shipment_events следуют за заявкой"],
        ["Репликация", "async streaming WAL: primary → hot standby внутри региона"],
        ["Справочник", "products — реплика справочника на обоих шардах"],
    ], [4 * cm, 12.5 * cm]))

    story.append(Paragraph("3.0.1. Полнота, непересечение, восстановимость — явно", ss["H2RU"]))
    story.append(Paragraph(
        "Это три условия <b>корректности</b> горизонтальной фрагментации "
        "(проверка, что разрез сделан правильно, а не «просто два сервера»).",
        ss["BodyRU"],
    ))
    story.append(tbl([
        ["Условие", "Что это значит", "Как у нас выполняется"],
        [
            "Полнота",
            "Если сложить все фрагменты, получится весь набор данных контура — ничего не «потерялось между серверами».",
            "WEST ∪ EAST = все склады, остатки и заявки стенда. Нет третьего скрытого шарда.",
        ],
        [
            "Непересечение",
            "Одна и та же оперативная строка не лежит сразу на двух фрагментах (нет дублей «и WEST, и EAST»).",
            "Заявка/остаток с region_code=X существует только на узлах X. Клиент запрещает писать чужой регион (403).",
        ],
        [
            "Восстановимость",
            "По фрагментам можно снова понять глобальную картину без потери смысла (собрать ответ «по всей системе»).",
            "Опрос GET WEST + GET EAST на стороне клиента + общий справочник products. Межшардовый JOIN оперативки не нужен.",
        ],
    ], [3.2 * cm, 6.5 * cm, 6.8 * cm], fontsize=7))
    story.append(Paragraph(
        "Кратко на защите: <b>полнота</b> — «всё на месте в сумме»; "
        "<b>непересечение</b> — «нет двойных копий оперативки»; "
        "<b>восстановимость</b> — «можем снова собрать общую картину, опросив фрагменты».",
        ss["BodyRU"],
    ))

    story.append(Spacer(1, 4))
    story.append(fit(dist, mw=17 * cm, mh=12.5 * cm))
    story.append(Paragraph(
        "Рисунок 2 — схема распределения: фрагменты WEST/EAST, primary/replica, справочник products",
        ss["CenterRU"],
    ))
    story.append(Paragraph(
        "По смыслу это та же схема «фрагмент + реплика», что и UML deployment: "
        "два независимых куска оперативки, запись на primary, чтение с replica, "
        "между WEST и EAST копирования оперативки нет; products — одинаковая копия каталога на обоих.",
        ss["BodyRU"],
    ))
    story.append(Paragraph("3.1. Фрагмент vs реплика", ss["H2RU"]))
    story.append(tbl([
        ["Объект", "Классификация"],
        ["west-primary / east-primary", "фрагмент оперативных данных своего региона"],
        ["west-replica / east-replica", "реплика своего фрагмента (только чтение)"],
        ["копия products на шардах", "реплика справочника, не отдельный оперативный фрагмент"],
    ], [6 * cm, 10.5 * cm]))

    story.append(Paragraph("3.2. Как данные «собираются воедино» (глобальная картина)", ss["H2RU"]))
    story.append(Paragraph(
        "Оперативные данные <b>не сливаются в одну физическую БД</b> и не требуют "
        "межшардового JOIN остатков/заявок. Глобальная картина получается логически "
        "за счёт трёх условий выше:",
        ss["BodyRU"],
    ))
    for b in [
        "<b>Полнота на практике.</b> Объединение ответов WEST и EAST даёт весь контур.",
        "<b>Непересечение на практике.</b> В склейке нет двух одинаковых order_id "
        "из разных регионов как «одной» заявки — у каждого свой периметр.",
        "<b>Восстановимость на практике.</b> Клиент вызывает "
        "<font face=\"DejaVuMono\">GET /api/WEST/orders</font> и "
        "<font face=\"DejaVuMono\">GET /api/EAST/orders</font> и склеивает списки; "
        "справочник products уже согласован на обоих шардах.",
        "<b>Что не делается.</b> Нет единого центрального primary для всей оперативки "
        "и нет FDW-JOIN остатков WEST↔EAST — иначе нарушился бы периметр.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))
    story.append(Paragraph(
        "Внутри региона согласованность primary и replica даёт async streaming: "
        "после записи на primary реплика догоняет за секунды (допустимый лаг).",
        ss["BodyRU"],
    ))

    # --- 4. Техника ---
    story.append(PageBreak())
    story.append(Paragraph("4. Техническая реализация стенда", ss["H1RU"]))
    story.append(Paragraph(
        "Стенд: Docker Compose, четыре независимых процесса PostgreSQL 16. "
        "Техника: <b>шардинг по region</b> (клиентский роутинг) + "
        "<b>асинхронная потоковая репликация</b> primary→replica внутри региона. "
        "Имитация площадок контейнерами допускается заданием.",
        ss["BodyRU"],
    ))
    story.append(tbl([
        ["Узел", "Порт", "Роль", "Фрагмент", "Кто пишет", "Канал", "Лог"],
        ["west-primary", "15432", "писатель", "WEST", "клиент", "Docker net", "—"],
        ["west-replica", "15433", "читатель", "реплика WEST", "никто", "streaming async", "секунды"],
        ["east-primary", "15434", "писатель", "EAST", "клиент", "Docker net", "—"],
        ["east-replica", "15435", "читатель", "реплика EAST", "никто", "streaming async", "секунды"],
        ["FastAPI", "8000", "роутер", "—", "—", "localhost", "—"],
    ], [3.2 * cm, 1.6 * cm, 2.2 * cm, 3 * cm, 2 * cm, 2.5 * cm, 1.8 * cm], fontsize=7))
    story.append(Paragraph("Артефакты поставки:", ss["BodyRU"]))
    for b in [
        "<font face=\"DejaVuMono\">docker-compose.yml</font> — 4 узла + healthcheck;",
        "<font face=\"DejaVuMono\">db/init/01_schema.sql</font> + seed WEST/EAST;",
        "<font face=\"DejaVuMono\">db/primary/00_replication.sh</font>, <font face=\"DejaVuMono\">db/replica/entrypoint.sh</font>;",
        "<font face=\"DejaVuMono\">client/app/main.py</font> + <font face=\"DejaVuMono\">requirements.txt</font>;",
        "<font face=\"DejaVuMono\">scripts/bootstrap_schema.sh</font>, <font face=\"DejaVuMono\">demo.sh</font>, захват скриншотов.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    story.append(Paragraph("4.1. Подъём стенда (кратко)", ss["H2RU"]))
    story.append(Preformatted(
        "unset COMPOSE_PROJECT_NAME\n"
        "docker compose up -d\n"
        "source .venv/bin/activate && pip install -r client/requirements.txt\n"
        "./scripts/bootstrap_schema.sh\n"
        "uvicorn client.app.main:app --port 8000\n"
        "./scripts/demo.sh",
        ss["CodeRU"],
    ))

    # --- 5. Отказ ---
    story.append(Paragraph("5. Модель отказа узла", ss["H1RU"]))
    story.append(Paragraph(
        "Ниже — ответ на вопрос задания: <b>что будет, если один из серверов «умрёт»</b>. "
        "В стенде «сервер» = контейнер PostgreSQL (primary или replica региона).",
        ss["BodyRU"],
    ))
    story.append(tbl([
        ["Событие", "Поведение"],
        ["Отказ primary региона", "Запись в регион запрещена; чтение — с replica; другой регион работает"],
        ["Отказ replica", "Запись на primary сохраняется; чтение переключается на primary"],
        ["Потеря канала до чужого региона", "Локальные операции на своём primary продолжаются"],
        ["Запись / смена статуса чужого региона", "Отказ по критерию контура (даже если другой узел жив)"],
        ["Восстановление primary", "docker start; запись возобновляется после healthy"],
    ], [5.5 * cm, 11 * cm], fontsize=7.5))
    story.append(Paragraph("5.1. Разбор по ролям узлов", ss["H2RU"]))
    for b in [
        "<b>Умер west-primary.</b> Клиент не может создать заявку / сменить статус WEST "
        "(ошибка «узел недоступен»). GET остатков и events WEST всё ещё возможны с "
        "<font face=\"DejaVuMono\">west-replica</font>. EAST при этом работает как обычно — "
        "это другой фрагмент, не копия WEST.",
        "<b>Умер west-replica.</b> Запись на west-primary продолжается. Чтение WEST "
        "клиент переключает на primary (в ответе routing.role = primary).",
        "<b>Умер весь регион WEST (оба узла).</b> Фрагмент WEST недоступен: операции "
        "с region=WEST отклоняются. Фрагмент EAST жив. Глобальную картину «собрать» "
        "полностью нельзя, пока WEST не восстановлен — это ожидаемо при горизонтальной "
        "фрагментации (нет второй копии оперативки WEST на EAST).",
        "<b>Потеря канала «между регионами».</b> Каждый регион автономен: локальные "
        "отгрузки на своём primary идут дальше. Нет требования держать связь с чужим "
        "шардом для оперативки.",
        "<b>Демо на стенде.</b> <font face=\"DejaVuMono\">docker stop rdb-west-primary</font> → "
        "POST заявки WEST падает, GET stock WEST читает с replica; затем "
        "<font face=\"DejaVuMono\">docker start rdb-west-primary</font> — запись снова доступна "
        "(скрины в §8).",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))
    story.append(Paragraph(
        "Promote replica в новый primary в учебном стенде не автоматизирован: достаточно "
        "показать отказ записи и чтение с replica, затем поднять primary обратно. "
        "В боевой схеме после гибели primary replica повышают (pg_promote) и "
        "перенастраивают клиента на новый писатель.",
        ss["BodyRU"],
    ))

    # --- 6. Демо ---
    story.append(Paragraph("6. Сценарий демонстрации клиента", ss["H1RU"]))
    story.append(Paragraph(
        "Клиент — веб-API на FastAPI. Интерфейс для ручной проверки — "
        "<b>Swagger UI</b>: откройте в браузере "
        "<font face=\"DejaVuMono\">http://127.0.0.1:8000/docs</font> "
        "(клиент должен быть запущен через uvicorn). "
        "Каждый ответ содержит блок <font face=\"DejaVuMono\">routing</font>: "
        "region, role (primary/replica), host — куда реально ушёл запрос.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("6.0. Как пользоваться кнопками в Swagger (общий порядок)", ss["H2RU"]))
    for b in [
        "Слева/сверху список операций с цветными метками: <b>GET</b> (зелёный) — чтение, "
        "<b>POST</b> (синий) — создать / сменить статус, <b>PUT</b> (оранжевый) — изменить, "
        "<b>DELETE</b> (красный) — удалить.",
        "Нажмите на строку операции — раскроется описание и поля.",
        "Кнопка <b>Try it out</b> — включает режим ввода (иначе поля только для просмотра).",
        "В пути почти везде параметр <font face=\"DejaVuMono\">region</font>: "
        "впишите <b>WEST</b> или <b>EAST</b> (регистр не важен, клиент приведёт к верхнему).",
        "Если есть <b>Request body</b> — отредактируйте JSON-пример под свои id/значения.",
        "Кнопка <b>Execute</b> — отправить запрос. Ниже появятся <b>Code</b> (200/403/…) и Response body.",
        "Кнопка <b>Clear</b> / свернуть операцию — сбросить ввод. "
        "Справа от пути можно скопировать curl — то же самое из терминала.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))
    story.append(Paragraph(
        "Важно: запись всегда идёт на <b>primary</b> выбранного региона, чтение (GET) — "
        "предпочтительно с <b>replica</b>. Нельзя через WEST менять заявку EAST (будет 403).",
        ss["BodyRU"],
    ))

    story.append(Paragraph("6.0.1. Служебная проверка узлов", ss["H2RU"]))
    story.append(tbl([
        ["Кнопка / метод", "Что делает", "Как пользоваться"],
        [
            "GET /health",
            "Проверяет доступность всех 4 узлов (WEST/EAST × primary/replica)",
            "Try it out → Execute. Смотрите ok: true/false по каждому узлу. Перед демо убедитесь, что все true.",
        ],
    ], [4 * cm, 5 * cm, 7.5 * cm], fontsize=7))

    story.append(Paragraph("6.0.2. Склады (warehouses)", ss["H2RU"]))
    story.append(tbl([
        ["Кнопка / метод", "Что делает", "Как пользоваться"],
        [
            "GET …/warehouses",
            "Список складов региона (чтение с replica)",
            "region=WEST или EAST → Execute. В ответе data[] с id, code, name.",
        ],
        [
            "POST …/warehouses",
            "Создать склад (запись на primary)",
            "region=WEST. Body: {\"code\":\"WH-WEST-2\",\"name\":\"Склад Запад-2\"}. Запомните data.id.",
        ],
        [
            "PUT …/warehouses/{id}",
            "Изменить код/название склада",
            "region + warehouse_id из GET. Body: {\"name\":\"Новое имя\"} (code можно не трогать).",
        ],
        [
            "DELETE …/warehouses/{id}",
            "Удалить склад",
            "region + id. Не удаляйте склад, если на нём есть остатки/заявки (БД может отказать по FK).",
        ],
    ], [4 * cm, 5 * cm, 7.5 * cm], fontsize=7))

    story.append(PageBreak())
    story.append(Paragraph("6.0.3. Товары (products)", ss["H2RU"]))
    story.append(tbl([
        ["Кнопка / метод", "Что делает", "Как пользоваться"],
        [
            "GET …/products",
            "Список номенклатуры на шарде региона",
            "region → Execute. Справочник копируется на оба региона (реплика справочника).",
        ],
        [
            "POST …/products",
            "Добавить товар",
            "Body: {\"sku\":\"SKU-400\",\"title\":\"Кабель 3м\"}. sku должен быть уникальным.",
        ],
        [
            "PUT …/products/{id}",
            "Изменить sku/title",
            "product_id из GET. Body: {\"title\":\"Новое название\"}.",
        ],
        [
            "DELETE …/products/{id}",
            "Удалить товар",
            "Только если на него нет ссылок в stock/items.",
        ],
    ], [4 * cm, 5 * cm, 7.5 * cm], fontsize=7))

    story.append(Paragraph("6.0.4. Остатки (stock)", ss["H2RU"]))
    story.append(tbl([
        ["Кнопка / метод", "Что делает", "Как пользоваться"],
        [
            "GET …/stock",
            "Остатки складов региона (available / reserved)",
            "region → Execute. Смотрите qty_available и qty_reserved.",
        ],
        [
            "POST …/stock",
            "Завести остаток товара на складе",
            "Body: {\"warehouse_id\":1,\"product_id\":1,\"qty_available\":40}. id склада и товара — из предыдущих GET/POST.",
        ],
        [
            "PUT …/stock/{id}",
            "Изменить доступное количество",
            "stock_id из GET. Body: {\"qty_available\":50}. Резерв меняется сценарием статусов, не вручную.",
        ],
        [
            "DELETE …/stock/{id}",
            "Удалить строку остатка",
            "region + stock_id. Используйте осторожно на демо-данных.",
        ],
    ], [4 * cm, 5 * cm, 7.5 * cm], fontsize=7))

    story.append(Paragraph("6.0.5. Заявки на отгрузку (orders) — главный сценарий", ss["H2RU"]))
    story.append(tbl([
        ["Кнопка / метод", "Что делает", "Как пользоваться"],
        [
            "GET …/orders",
            "Список заявок региона",
            "region=WEST → Execute. Видны id и status (CREATED, RESERVED, …).",
        ],
        [
            "POST …/orders",
            "Создать заявку + позицию (статус CREATED) и первую запись в events",
            "Body: {\"warehouse_id\":1,\"product_id\":1,\"qty\":3}. Склад должен быть этого же региона. Запомните data.order.id.",
        ],
        [
            "POST …/orders/{id}/status",
            "Сменить статус (предметный сценарий сверх CRUD)",
            "order_id + Body: {\"to_status\":\"RESERVED\",\"note\":\"резерв\"}. Дальше по цепочке: PICKING → SHIPPED → DELIVERED. Или CANCELLED из CREATED/RESERVED.",
        ],
        [
            "GET …/orders/{id}/events",
            "Журнал смен статусов заявки (чтение с replica)",
            "Тот же region и order_id → Execute. Каждая смена = строка from_status → to_status.",
        ],
        [
            "POST /api/cross-region-denied",
            "Демонстрация отказа по критерию контура (без реальной записи)",
            "Query: from_region=WEST, to_region=EAST, order_id=<id заявки WEST>. Execute → всегда 403 с пояснением правила периметра. Альтернатива: POST /api/EAST/orders/{WEST_id}/status.",
        ],
    ], [4 * cm, 5 * cm, 7.5 * cm], fontsize=7))

    story.append(Paragraph("6.0.6. Рекомендуемый порядок нажатий «с нуля»", ss["H2RU"]))
    story.append(Preformatted(
        "1) GET /health                         — все узлы ok\n"
        "2) POST /api/WEST/warehouses           — создать склад, взять id\n"
        "3) POST /api/WEST/products             — создать товар, взять id\n"
        "4) POST /api/WEST/stock                — остаток (warehouse_id + product_id)\n"
        "5) POST /api/WEST/orders               — заявка qty=3 → order.id\n"
        "6) POST .../orders/{id}/status         — RESERVED\n"
        "7) POST .../status                     — PICKING → SHIPPED → DELIVERED\n"
        "8) GET  .../orders/{id}/events         — журнал контроля\n"
        "9) POST /api/EAST/orders/{WEST_id}/status  — должен вернуть 403 (чужой регион)",
        ss["CodeRU"],
    ))
    story.append(Paragraph(
        "Допустимые переходы статусов: CREATED→RESERVED|CANCELLED; "
        "RESERVED→PICKING|CANCELLED; PICKING→SHIPPED; SHIPPED→DELIVERED. "
        "Любой другой переход Swagger покажет ошибку 400.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("6.1. CRUD ключевых сущностей (сводка)", ss["H2RU"]))
    story.append(tbl([
        ["Сущность", "Create", "Read", "Update", "Delete"],
        ["warehouses", "POST", "GET (replica)", "PUT", "DELETE"],
        ["products", "POST", "GET", "PUT", "DELETE"],
        ["stock", "POST", "GET", "PUT", "DELETE"],
        ["orders", "POST", "GET", "через status", "CANCELLED (отмена)"],
    ], [3 * cm, 3.2 * cm, 3.5 * cm, 3.3 * cm, 3.5 * cm], fontsize=7.5))

    story.append(PageBreak())
    story.append(Paragraph("6.2. Предметный сценарий: жизненный цикл заявки (статусы)", ss["H1RU"]))
    story.append(Paragraph(
        "Это главный сценарий <b>сверх обычного CRUD</b>: заявка на отгрузку проходит "
        "цепочку состояний. Статус — не «просто строка в интерфейсе», а правило склада: "
        "когда товар резервируется, когда списывается, когда отгрузка завершена или отменена.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("6.2.1. Где это лежит", ss["H2RU"]))
    story.append(tbl([
        ["Что", "Где физически", "Как меняется"],
        [
            "Текущий статус заявки",
            "Таблица shipment_orders, поле status (на primary/replica своего региона)",
            "UPDATE при каждом успешном POST …/status",
        ],
        [
            "История всех шагов",
            "Таблица shipment_events (журнал) на том же фрагменте",
            "INSERT новой строки на каждый переход",
        ],
        [
            "Остатки под резерв",
            "Таблица stock_balances: qty_available / qty_reserved",
            "Меняются при RESERVED / CANCELLED / SHIPPED",
        ],
        [
            "Логика переходов",
            "Клиент client/app/main.py: словарь TRANSITIONS + функции _reserve/_ship/_unreserve",
            "API: POST /api/{region}/orders/{id}/status",
        ],
        [
            "Ограничение в БД",
            "CHECK status IN (CREATED, RESERVED, PICKING, SHIPPED, DELIVERED, CANCELLED)",
            "Невалидный статус БД не примет",
        ],
    ], [3.5 * cm, 7 * cm, 6 * cm], fontsize=7))

    story.append(Paragraph("6.2.2. Что означает каждый статус", ss["H2RU"]))
    story.append(Paragraph(
        "Сначала три слова, без которых таблица непонятна:",
        ss["BodyRU"],
    ))
    for b in [
        "<b>qty</b> — сколько штук товара заказали в заявке "
        "(поле в <font face=\"DejaVuMono\">shipment_items</font>). Пример: заявка на 3 кабеля → qty = 3.",
        "<b>qty_available</b> (available) — сколько сейчас свободно на складе, можно отдать под новые заявки "
        "(поле в <font face=\"DejaVuMono\">stock_balances</font>).",
        "<b>qty_reserved</b> (reserved) — сколько уже «забронировано» под существующие заявки "
        "и пока нельзя отдать другим.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))
    story.append(Paragraph(
        "<b>Числовой пример.</b> На складе было available = 10, reserved = 0. "
        "Создали заявку qty = 3. При переходе в RESERVED: available становится 7, reserved становится 3. "
        "Если попытаться зарезервировать qty = 15 при available = 10 — отказ: свободного товара не хватает.",
        ss["BodyRU"],
    ))
    story.append(tbl([
        ["Статус", "По-русски", "Смысл для склада", "Что с остатком (простыми словами)"],
        [
            "CREATED",
            "создана",
            "Заявку оформили, товар ещё не держат",
            "Ничего: available и reserved как были",
        ],
        [
            "RESERVED",
            "зарезервирована",
            "Забронировали qty штук под эту заявку",
            "Свободных меньше на qty, в резерве больше на qty. Нельзя, если свободных меньше, чем qty",
        ],
        [
            "PICKING",
            "сборка",
            "Собирают заказ; бронь ещё держится",
            "Цифры остатка не трогаем",
        ],
        [
            "SHIPPED",
            "отгружена",
            "Товар уехал со склада",
            "Из резерва убираем qty (товар уже не на складе)",
        ],
        [
            "DELIVERED",
            "доставлена",
            "Успешный конец; дальше статус не меняют",
            "Цифры остатка не трогаем",
        ],
        [
            "CANCELLED",
            "отменена",
            "Отменили до отгрузки",
            "Если успели зарезервировать — вернуть qty обратно в свободные",
        ],
    ], [2.4 * cm, 2.6 * cm, 5.2 * cm, 6.3 * cm], fontsize=7))

    story.append(Paragraph("6.2.3. CANCELLED — отдельно (чтобы объяснить на защите)", ss["H2RU"]))
    story.append(Paragraph(
        "<b>CANCELLED</b> — это не «удалить заявку из таблицы», а <b>статус отмены</b>: "
        "наряд остаётся в БД (для аудита), но жизненный цикл закончен неудачей/отменой. "
        "После CANCELLED переходов дальше нет (как и после DELIVERED).",
        ss["BodyRU"],
    ))
    for b in [
        "Отменить можно только из <b>CREATED</b> или <b>RESERVED</b> "
        "(пока товар не ушёл в сборку/отгрузку).",
        "Из <b>PICKING / SHIPPED / DELIVERED</b> в CANCELLED перейти нельзя — "
        "клиент вернёт ошибку 400 «переход запрещён».",
        "Если отмена из <b>RESERVED</b>: резерв снимается "
        "(<font face=\"DejaVuMono\">qty_reserved −</font>, "
        "<font face=\"DejaVuMono\">qty_available +</font>) — товар снова свободен.",
        "Если отмена из <b>CREATED</b>: остатки не трогали, меняется только status + строка в журнале.",
        "В журнале появится, например: CREATED→CANCELLED или RESERVED→CANCELLED.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    story.append(Paragraph("6.2.4. Какие переходы разрешены (логика автомата)", ss["H2RU"]))
    story.append(fit(life, mh=7 * cm))
    story.append(Paragraph("Рисунок 3 — UML state: жизненный цикл shipment_orders.status", ss["CenterRU"]))
    story.append(Preformatted(
        "CREATED  → RESERVED | CANCELLED\n"
        "RESERVED → PICKING  | CANCELLED\n"
        "PICKING  → SHIPPED\n"
        "SHIPPED  → DELIVERED\n"
        "DELIVERED → (конец)\n"
        "CANCELLED → (конец)",
        ss["CodeRU"],
    ))
    story.append(Paragraph(
        "Успешный путь: CREATED → RESERVED → PICKING → SHIPPED → DELIVERED. "
        "Боковой путь отмены: … → CANCELLED. Реализовано словарём "
        "<font face=\"DejaVuMono\">TRANSITIONS</font> в <font face=\"DejaVuMono\">client/app/main.py</font>: "
        "перед UPDATE клиент проверяет, есть ли <font face=\"DejaVuMono\">to_status</font> "
        "в множестве допустимых из текущего статуса.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("6.2.5. Как это вызывается и что происходит по шагам", ss["H2RU"]))
    story.append(Paragraph(
        "Эндпоинт: <font face=\"DejaVuMono\">POST /api/{region}/orders/{order_id}/status</font> "
        "с телом <font face=\"DejaVuMono\">{\"to_status\":\"RESERVED\",\"note\":\"…\"}</font>. "
        "Всегда на <b>primary</b> выбранного региона.",
        ss["BodyRU"],
    ))
    for i, b in enumerate([
        "Найти заявку <font face=\"DejaVuMono\">FOR UPDATE</font> на фрагменте region.",
        "Проверить <font face=\"DejaVuMono\">order.region_code == region</font>, иначе <b>403</b> (периметр).",
        "Проверить переход по TRANSITIONS, иначе <b>400</b>.",
        "При необходимости изменить остатки (_reserve / _unreserve / _ship).",
        "UPDATE shipment_orders.status = новый статус.",
        "INSERT в shipment_events (from_status, to_status, note) — фиксация контроля.",
        "Async replication копирует изменения на replica региона.",
    ], 1):
        story.append(Paragraph(f"{i}. {b}", ss["BulletRU"]))

    story.append(Paragraph(
        "Чужой регион → HTTP 403. Нельзя зарезервировать больше available → ошибка при RESERVED. "
        "Это и есть предметный сценарий задания: не просто INSERT/SELECT, а цепочка состояний + контроль.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("6.3. Шаги demo.sh (полный прогон API)", ss["H2RU"]))
    for b in [
        "health; CRUD warehouses/products/stock на <b>WEST и EAST</b> (list/create/update);",
        "заявка WEST → цепочка до DELIVERED; заявка EAST → до SHIPPED; чтение events;",
        "CANCELLED из CREATED и из RESERVED (с проверкой возврата остатка);",
        "негативы: запрещённый переход (400), отмена из PICKING (400), нехватка остатка (409);",
        "критерий контура: статус/events чужого региона + <font face=\"DejaVuMono\">/api/cross-region-denied</font> → 403;",
        "docker stop west-primary → отказ записи WEST, чтение с replica, EAST жив; "
        "docker start → запись снова работает;",
        "опционально <font face=\"DejaVuMono\">CLEANUP=1</font> — удаление демо stock/warehouse/product.",
    ]:
        story.append(Paragraph(f"• {b}", ss["BulletRU"]))

    # --- 7. Код ---
    story.append(PageBreak())
    story.append(Paragraph("7. Код запросов (фрагменты)", ss["H1RU"]))
    story.append(Paragraph("7.1. Создание заявки (запись → primary)", ss["H2RU"]))
    story.append(Preformatted(
        "INSERT INTO shipment_orders (warehouse_id, region_code, status)\n"
        "VALUES (%s, %s, 'CREATED') RETURNING *;\n"
        "INSERT INTO shipment_items (order_id, product_id, qty)\n"
        "VALUES (%s, %s, %s);\n"
        "INSERT INTO shipment_events (order_id, from_status, to_status, note)\n"
        "VALUES (%s, NULL, 'CREATED', 'order created');",
        ss["CodeRU"],
    ))
    story.append(Paragraph("7.2. Смена статуса + журнал (контроль)", ss["H2RU"]))
    story.append(Preformatted(
        "SELECT * FROM shipment_orders WHERE id = %s FOR UPDATE;\n"
        "-- проверка region_code == запрошенный регион, иначе 403\n"
        "-- RESERVED: qty_available -= qty; qty_reserved += qty\n"
        "-- SHIPPED:  qty_reserved -= qty\n"
        "UPDATE shipment_orders SET status = %s, updated_at = NOW() WHERE id = %s;\n"
        "INSERT INTO shipment_events (order_id, from_status, to_status, note)\n"
        "VALUES (%s, %s, %s, %s);",
        ss["CodeRU"],
    ))
    story.append(Paragraph("7.3. Маршрутизация клиента", ss["H2RU"]))
    story.append(Preformatted(
        "запись:  connect(region, 'primary')\n"
        "чтение:  сначала replica, при недоступности — primary\n"
        "ответ:   { routing: { region, role, host, criterion }, data: ... }",
        ss["CodeRU"],
    ))

    # --- 8. Скриншоты ---
    story.append(Paragraph("8. Результаты выполнения (скриншоты)", ss["H1RU"]))
    story.append(Paragraph(
        "Снимки живого стенда после прогона <font face=\"DejaVuMono\">scripts/demo.sh</font> "
        "и <font face=\"DejaVuMono\">scripts/capture_screenshots.py</font>.",
        ss["BodyRU"],
    ))

    shot_specs = [
        ("00_docker_compose_ps.png", "Стенд: docker compose ps — 4 узла PostgreSQL"),
        ("01_swagger_home.png", "Swagger UI: список API"),
        ("05_swagger_warehouse_post.png", "CRUD: создание склада → primary WEST"),
        ("06_swagger_product_post.png", "CRUD: создание товара → primary WEST"),
        ("api_07_stock_create.png", "CRUD: создание остатка"),
        ("08_swagger_order_post.png", "Создание заявки на отгрузку"),
        ("api_10_status_DELIVERED.png", "Цепочка статусов → DELIVERED"),
        ("api_11_events.png", "Журнал shipment_events"),
        ("api_12_cross_region.png", "Отказ по критерию контура (чужой регион)"),
        ("api_13_write_fail.png", "Отказ записи при docker stop west-primary"),
        ("api_13_read_replica.png", "Чтение с replica при недоступном primary"),
        ("api_14_health_after_restart.png", "Восстановление после docker start primary"),
    ]
    existing = [(SHOTS / n, cap) for n, cap in shot_specs if (SHOTS / n).exists()]
    for i, (path, cap) in enumerate(existing, 1):
        if i > 1 and (i - 1) % 2 == 0:
            story.append(PageBreak())
            story.append(Paragraph("8. Результаты выполнения (продолжение)", ss["H1RU"]))
        story.append(Paragraph(f"8.{i}. {cap}", ss["H2RU"]))
        story.append(fit(path, mw=16.5 * cm, mh=10 * cm))
        story.append(Paragraph(f"Рисунок 8.{i} — {path.name}", ss["CenterRU"]))

    # --- 9. Электронно ---
    story.append(PageBreak())
    story.append(Paragraph("9. Электронные материалы", ss["H1RU"]))
    story.append(Preformatted(
        "Индивидуальный_проект/\n"
        "├── docker-compose.yml\n"
        "├── db/init/01_schema.sql, west|east/02_seed.sql\n"
        "├── dump/west_warehouse.sql, east_warehouse.sql   ← выгрузка pg_dump\n"
        "├── db/primary/, db/replica/\n"
        "├── client/app/main.py, requirements.txt\n"
        "├── scripts/bootstrap_schema.sh, demo.sh, make_dump.sh\n"
        "├── screenshots/\n"
        "├── docs/Заявка_….pdf\n"
        "└── Отчёт_индивидуальный_проект_РБД.pdf  ← этот файл",
        ss["CodeRU"],
    ))
    story.append(Paragraph(
        "Выгрузка базы: каталог <font face=\"DejaVuMono\">dump/</font> "
        "(<font face=\"DejaVuMono\">west_warehouse.sql</font>, "
        "<font face=\"DejaVuMono\">east_warehouse.sql</font>, архив tar.gz). "
        "Переснять: <font face=\"DejaVuMono\">./scripts/make_dump.sh</font>. "
        "Секреты подключений учебные (warehouse/warehouse), только для локального Docker.",
        ss["BodyRU"],
    ))

    story.append(Paragraph("10. Заключение", ss["H1RU"]))
    story.append(Paragraph(
        "Реализован распределённый учебный стенд с горизонтальной фрагментацией по "
        "<font face=\"DejaVuMono\">region_code</font>, асинхронными репликами на чтение, "
        "клиентом FastAPI (CRUD + цепочка статусов отгрузки + журнал событий) и демонстрацией "
        "отказов (узел primary, критерий контура). Критерий распределения обоснован "
        "периметром площадки и режимом доступа, а не балансировкой нагрузки.",
        ss["BodyRU"],
    ))

    def footer(c, doc):
        c.saveState()
        c.setFont("DejaVu", 8)
        c.setFillColor(colors.HexColor("#666"))
        c.drawString(1.8 * cm, 1 * cm, "Ермаков Л. · М09-КИИ26 · отчёт · индивидуальный проект РБД")
        c.drawRightString(A4[0] - 1.8 * cm, 1 * cm, f"стр. {doc.page}")
        c.restoreState()

    doc = SimpleDocTemplate(
        str(PDF_OUT),
        pagesize=A4,
        leftMargin=1.7 * cm,
        rightMargin=1.7 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.5 * cm,
        title="Отчёт о выполнении индивидуального проекта РБД",
        author="Ермаков Лаврентий",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    shutil.copy2(PDF_OUT, PDF_DOCS)
    return PDF_OUT


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    er = draw_er(ASSETS / "uml_er.png")
    # понятная схема WEST/EAST (идентична по смыслу прежнему UML deployment)
    dist = ROOT / "схема_WEST_EAST_понятно.png"
    if not dist.exists():
        dist = ASSETS / "schema_ponyatno_west_east.png"
    life = draw_lifecycle(ASSETS / "uml_lifecycle.png")
    seq = draw_sequence(ASSETS / "uml_sequence.png")
    out = build_pdf(er, dist, life, seq)
    print("PDF:", out)
    print("PDF copy:", PDF_DOCS)


if __name__ == "__main__":
    main()
