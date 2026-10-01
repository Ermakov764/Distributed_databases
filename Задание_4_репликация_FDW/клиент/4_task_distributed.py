#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Задание 4 · часть 2 — распределённый клиент (две БД).

Смысл по ТЗ
-----------
После разреза данных:
  • VM11 (.61) — университет (группы, направления, оценки…), ФИО обнулены;
  • VM2  (.60) — только личное (students с ФИО + phones).

Клиент лабы 1 «в лоб» на одну БД больше не работает. Этот скрипт делает то же
по смыслу, но сам ходит в ДВА PostgreSQL и склеивает строки в Python по students.id.

Запуск (на хосте Pop!_OS, обе ВМ включены, часть 2 уже выполнена)::

    cd "Выполненые задания/4_task"
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python 4_task_distributed.py

Переопределение хостов (необязательно)::

    export PGHOST_UNI=192.168.122.61
    export PGHOST_PERSONAL=192.168.122.60

Автор: Ермаков Л., М09-КИИ26
"""

from __future__ import annotations

import os
import sys
from datetime import date

import psycopg2
from psycopg2.extras import RealDictCursor  # строки как dict: row["id"]
from tabulate import tabulate  # красивая таблица в терминале

# --- подключения -------------------------------------------------------------
# UNI = университетский контур (VM11), PERSONAL = личный (VM2).
# Пароли учебные (db1_user / 1) — как во всех лабах курса.
# os.environ.get — можно сменить IP без правки кода (удобно на защите).

VM_UNI = {
    "host": os.environ.get("PGHOST_UNI", "192.168.122.61"),  # primary / university
    "port": int(os.environ.get("PGPORT_UNI", "5432")),
    "dbname": "university_db",
    "user": "db1_user",
    "password": "1",
}
VM_PERSONAL = {
    "host": os.environ.get("PGHOST_PERSONAL", "192.168.122.60"),  # personal после split
    "port": int(os.environ.get("PGPORT_PERSONAL", "5432")),
    "dbname": "university_db",
    "user": "db1_user",
    "password": "1",
}


def connect(cfg: dict):
    """Открыть соединение; при ошибке — понятное сообщение и выход."""
    try:
        return psycopg2.connect(**cfg)  # **cfg → host=, port=, …
    except psycopg2.OperationalError as exc:
        # Частые причины: ВМ выключена, postgres не слушает, неверный IP/пароль
        print(f"Не удалось подключиться к {cfg.get('host')}: {exc}", file=sys.stderr)
        print("Проверьте: ВМ запущена, PostgreSQL работает, IP/пароль верны.", file=sys.stderr)
        sys.exit(1)


def show(rows, headers=None) -> None:
    """Красивая таблица в терминале (как сетка Data Editor)."""
    if not rows:
        print("\nДанные не найдены.")
        return
    # если пришли dict-строки — сами вытащим имена колонок
    if headers is None and isinstance(rows[0], dict):
        headers = list(rows[0].keys())
        rows = [[r.get(h) for h in headers] for r in rows]
    print(tabulate(rows, headers=headers, tablefmt="grid"))


def personal_map(pers, ids=None) -> dict:
    """
    Словарь id → личная карточка с VM2.
    Если ids задан — тянем только нужных студентов (меньше трафика).
    Ключ словаря = students.id — по нему потом склеиваем с university.
    """
    cur = pers.cursor(cursor_factory=RealDictCursor)
    if ids is not None:
        ids = list(ids)
        if not ids:
            return {}  # пустой ANY(%) в PostgreSQL неудобен — просто выходим
        # ANY(%s) — список id одним параметром (не N отдельных запросов)
        cur.execute(
            """
            SELECT id, last_name, first_name, middle_name, birth_date, email
              FROM students WHERE id = ANY(%s)
            """,
            (ids,),
        )
    else:
        # без фильтра — вся personal-таблица (для возраста и т.п.)
        cur.execute(
            """
            SELECT id, last_name, first_name, middle_name, birth_date, email
              FROM students
            """
        )
    return {r["id"]: r for r in cur.fetchall()}


def fio(p) -> str:
    """Собрать строку ФИО; если карточки нет — '?' (разрыв id между ВМ)."""
    if not p:
        return "?"
    return f"{p.get('last_name') or ''} {p.get('first_name') or ''} {p.get('middle_name') or ''}".strip() or "?"


def ask(prompt: str, default: str, examples: list[str] | None = None) -> str:
    """Ввод с подсказками: Enter оставляет значение по умолчанию."""
    print(f"\n  → {prompt}")
    if examples:
        print("    примеры:", " | ".join(examples))
    print(f"    [Enter = «{default}»]")
    value = input("  ввод: ").strip()
    return value or default  # пустой ввод → default


def list_directions(uni) -> list[str]:
    """Список направлений с VM11 (нужен для меню запроса 1)."""
    cur = uni.cursor()
    cur.execute("SELECT name FROM directions ORDER BY name")
    return [r[0] for r in cur.fetchall()]


# --- запросы (номера как в лабе 1) ------------------------------------------
# Общий приём части 2: учёба ↔ UNI, ФИО ↔ PERSONAL, склейка по id в Python.


def query_1(uni, pers) -> None:
    """Группы по направлению: учёба с .61, ФИО с .60."""
    print("\n1. Списки групп по направлению (distributed)")
    dirs = list_directions(uni)
    if dirs:
        print("  Доступные направления:")
        for i, name in enumerate(dirs, 1):
            print(f"    {i}. {name}")
    default = dirs[0] if dirs else "Информатика и вычислительная техника"
    direction = ask("Направление (скопируй строку целиком)", default, dirs[:3] or None)

    # шаг 1: с university берём group / student_id / бюджет (ФИО там NULL)
    cur = uni.cursor()
    cur.execute(
        """
        SELECT g.name, s.id, s.is_budget
          FROM students s
          JOIN groups g ON g.id = s.group_id
          JOIN directions d ON d.id = g.direction_id
         WHERE d.name = %s
         ORDER BY g.name, s.id
        """,
        (direction,),
    )
    rows = cur.fetchall()

    # шаг 2: те же id → ФИО с personal (один SELECT, не по одному)
    pmap = personal_map(pers, [r[1] for r in rows])

    # шаг 3: склейка в Python (это и есть «распределённый клиент»)
    out = []
    for gname, sid, budget in rows:
        out.append(
            {
                "Группа": gname,
                "ФИО": fio(pmap.get(sid)),
                "Тип": "Бюджет" if budget else "Внебюджет",
            }
        )
    out.sort(key=lambda x: (x["Группа"], x["ФИО"]))
    show(out)


def query_2(uni, pers) -> None:
    """Сначала фильтр по фамилии на VM2, потом группы/направления с VM11."""
    print("\n2. Студенты по букве фамилии (personal → uni)")
    letter = ask("Первая буква фамилии", "И", ["А", "Е", "И", "К", "П", "С"]).upper()[:1]
    if not letter:
        print("  пустая буква — отмена")
        return

    # personal: WHERE по last_name (на .61 фамилии уже NULL — фильтр там бессмысленен)
    cur = pers.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM students WHERE UPPER(last_name) LIKE %s ORDER BY last_name",
        (f"{letter}%",),
    )
    people = cur.fetchall()
    ids = [p["id"] for p in people]
    if not ids:
        show([])
        return

    # university: дотягиваем группу и направление по тем же id
    curu = uni.cursor()
    curu.execute(
        """
        SELECT s.id, g.name, d.name
          FROM students s
          JOIN groups g ON g.id = s.group_id
          JOIN directions d ON d.id = g.direction_id
         WHERE s.id = ANY(%s)
        """,
        (ids,),
    )
    uni_map = {r[0]: (r[1], r[2]) for r in curu.fetchall()}
    out = []
    for p in people:
        g, dname = uni_map.get(p["id"], ("?", "?"))  # "?" если id нет на uni
        out.append({"ФИО": fio(p), "Группа": g, "Направление": dname})
    show(out)


def query_4(uni, pers) -> None:
    """Возраст считается на клиенте из birth_date с personal-БД."""
    print("\n4. Возраст студентов (personal)")
    # uni здесь не нужен: даты рождения только на .60
    pmap = personal_map(pers)
    out = []
    today = date.today()
    for _sid, p in pmap.items():
        if not p.get("birth_date"):
            continue  # пропуск, если дата пустая
        bd = p["birth_date"]
        # классический расчёт возраста: год − год, минус 1 если ДР ещё не был
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        out.append({"ФИО": fio(p), "Дата рождения": bd, "Возраст": age})
    out.sort(key=lambda x: x["ФИО"])
    show(out[:40])  # в терминал не вываливаем всех сразу
    print(f"(показано до 40 из {len(out)})")


def query_6(uni, pers) -> None:
    """Только university: ФИО не нужны."""
    print("\n6. Количество студентов по направлениям (uni)")
    # pers не используем — счётчики живут в учебном контуре
    cur = uni.cursor()
    cur.execute(
        """
        SELECT d.name, COUNT(s.id)
          FROM directions d
          LEFT JOIN groups g ON g.direction_id = d.id
          LEFT JOIN students s ON s.group_id = g.id
         GROUP BY d.name
         ORDER BY COUNT(s.id) DESC
        """
    )
    show([{"Направление": n, "Количество": c} for n, c in cur.fetchall()])


def query_12(uni, pers) -> None:
    """Средние оценки — только university (таблица grades на .61)."""
    print("\n12. Средняя оценка по предметам (uni)")
    cur = uni.cursor()
    cur.execute(
        """
        SELECT sub.name, ROUND(AVG(gr.grade)::NUMERIC, 2)
          FROM subjects sub
          JOIN grades gr ON gr.subject_id = sub.id
         WHERE gr.grade > 2
         GROUP BY sub.name
         ORDER BY AVG(gr.grade) DESC
        """
    )
    show([{"Предмет": n, "Средняя": a} for n, a in cur.fetchall()])


def query_14(uni, pers) -> None:
    """Отличники: id с VM11, ФИО с VM2."""
    print("\n14. Отличники (distributed)")
    # HAVING MIN=5 → все оценки пятёрки (нет двоек/троек/…)
    cur = uni.cursor()
    cur.execute(
        """
        SELECT s.id, g.name
          FROM students s
          JOIN groups g ON g.id = s.group_id
          JOIN grades gr ON gr.student_id = s.id
         GROUP BY s.id, g.name
        HAVING MIN(gr.grade) = 5 AND COUNT(gr.id) > 0
        """
    )
    rows = cur.fetchall()
    pmap = personal_map(pers, [r[0] for r in rows])  # ФИО только для отличников
    show([{"ФИО": fio(pmap.get(i)), "Группа": g} for i, g in rows])


# ключ меню → (подпись, функция); номера совпадают с лабой 1
MENU = {
    "1": ("Списки групп по направлению (distributed)", query_1),
    "2": ("Студенты по букве фамилии (personal→uni)", query_2),
    "4": ("Возраст (personal)", query_4),
    "6": ("Кол-во по направлениям (uni)", query_6),
    "12": ("Средняя оценка (uni)", query_12),
    "14": ("Отличники (distributed)", query_14),
    "0": ("Выход", None),
}


def main() -> None:
    # два независимых TCP-соединения — суть части 2
    uni = connect(VM_UNI)
    pers = connect(VM_PERSONAL)
    print("Подключено: UNI=", VM_UNI["host"], " PERSONAL=", VM_PERSONAL["host"])
    try:
        while True:
            print("\n" + "=" * 60)
            print(" ЗАДАНИЕ 4 · РАСПРЕДЕЛЁННЫЙ КЛИЕНТ (часть 2)")
            for k, (title, _) in MENU.items():
                print(f"  [{k}] {title}")
            print("  примеры выбора: 1 | 2 | 14 | 0")
            choice = input("Выбор: ").strip()
            if choice == "0":
                break
            if choice in MENU and MENU[choice][1]:
                try:
                    MENU[choice][1](uni, pers)  # вызываем выбранный query_*
                except psycopg2.Error as exc:
                    # SQL-ошибка не роняет весь клиент — можно выбрать другой пункт
                    print(f"Ошибка SQL: {exc}", file=sys.stderr)
                input("Enter — вернуться в меню...")
            else:
                print("  нет такого пункта, примеры: 1, 2, 4, 6, 12, 14, 0")
    finally:
        # всегда закрываем оба соединения (даже при Ctrl+C / ошибке)
        uni.close()
        pers.close()


if __name__ == "__main__":
    main()
