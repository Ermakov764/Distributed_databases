#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Задание 4 · часть 3 — FDW-клиент (одно подключение).

Смысл по ТЗ
-----------
На VM11 уже настроен postgres_fdw:
  SERVER personal_server → 192.168.122.60
  FOREIGN TABLE students_personal / phones_personal
  VIEW v_students_full = students ⋈ students_personal

Клиент подключается ТОЛЬКО к VM11 (.61). ФИО PostgreSQL сам читает с VM2
через FDW — второго connect в Python нет (в отличие от части 2).

Запуск (на хосте, часть 3 уже настроена)::

    cd "Выполненые задания/4_task"
    source .venv/bin/activate
    python 4_task_fdw.py

Хост по умолчанию 192.168.122.61, можно переопределить::

    export PGHOST=192.168.122.61

Автор: Ермаков Л., М09-КИИ26
"""

from __future__ import annotations

import os
import sys

import psycopg2
from tabulate import tabulate

# одно подключение: только VM11; .60 «прячется» за FDW на сервере
DB = {
    "host": os.environ.get("PGHOST", "192.168.122.61"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "dbname": "university_db",
    "user": "db1_user",
    "password": "1",
}


def connect():
    """Connect к .61; если ВМ/FDW не готовы — сразу понятная ошибка."""
    try:
        return psycopg2.connect(**DB)
    except psycopg2.OperationalError as exc:
        print(f"Не удалось подключиться к {DB['host']}: {exc}", file=sys.stderr)
        print("Проверьте VM11, PostgreSQL и что FDW настроен (часть 3).", file=sys.stderr)
        sys.exit(1)


def show(cur) -> None:
    """Печать результата текущего курсора (заголовки из description)."""
    rows = cur.fetchall()
    if not rows:
        print("пусто")
        return
    # cur.description[i][0] — имя колонки из SELECT … AS "…"
    print(tabulate(rows, headers=[d[0] for d in cur.description], tablefmt="grid"))


def ask(prompt: str, default: str, examples: list[str] | None = None) -> str:
    """Интерактивный ввод; Enter → default."""
    print(f"\n  → {prompt}")
    if examples:
        print("    примеры:", " | ".join(examples))
    print(f"    [Enter = «{default}»]")
    value = input("  ввод: ").strip()
    return value or default


def list_directions(conn) -> list[str]:
    """Локальная таблица directions на .61 (FDW тут не нужен)."""
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM directions ORDER BY name")
        return [r[0] for r in cur.fetchall()]


# пункты меню = номера запросов лабы 1 (где нужны ФИО — через FDW)
QUERIES = {
    "1": "Группы по направлению (FDW)",
    "2": "Фамилия на букву (FDW)",
    "4": "Возраст (FDW)",
    "6": "Кол-во по направлениям",
    "12": "Средняя оценка",
    "14": "Отличники (FDW ФИО)",
}


def run_query(conn, ch: str) -> None:
    """
    Все запросы идут в один хост (.61).
    Где нужны ФИО — JOIN на students_personal (внешняя таблица → VM2).
    Склейку делает PostgreSQL, не Python (отличие от 4_task_distributed.py).
    """
    title = QUERIES[ch]
    print("\n", title)

    if ch == "1":
        # local students + remote ФИО через FOREIGN TABLE
        dirs = list_directions(conn)
        if dirs:
            print("  Доступные направления:")
            for i, name in enumerate(dirs, 1):
                print(f"    {i}. {name}")
        default = dirs[0] if dirs else "Информатика и вычислительная техника"
        direction = ask("Направление (скопируй строку целиком)", default, dirs[:3] or None)
        sql = """
        SELECT g.name AS "Группа",
               sp.last_name || ' ' || sp.first_name || ' '
                 || COALESCE(sp.middle_name, '') AS "ФИО",
               CASE WHEN s.is_budget THEN 'Бюджет' ELSE 'Внебюджет' END AS "Тип"
          FROM students s
          JOIN students_personal sp ON sp.id = s.id   -- FDW → VM2
          JOIN groups g ON g.id = s.group_id
          JOIN directions d ON d.id = g.direction_id
         WHERE d.name = %s
         ORDER BY g.name, sp.last_name
        """
        params: tuple | None = (direction,)
    elif ch == "2":
        # фильтр по фамилии сразу на внешней таблице (данные с .60)
        letter = ask("Первая буква фамилии", "И", ["А", "Е", "И", "К", "П", "С"]).upper()[:1]
        if not letter:
            print("  пустая буква — отмена")
            return
        sql = """
        SELECT sp.last_name || ' ' || sp.first_name AS "ФИО",
               g.name AS "Группа", d.name AS "Направление"
          FROM students_personal sp
          JOIN students s ON s.id = sp.id
          JOIN groups g ON g.id = s.group_id
          JOIN directions d ON d.id = g.direction_id
         WHERE UPPER(sp.last_name) LIKE %s
         ORDER BY sp.last_name
        """
        params = (f"{letter}%",)
    elif ch == "4":
        # возраст считает уже PostgreSQL (AGE), birth_date читается с VM2 через FDW
        sql = """
        SELECT sp.last_name || ' ' || sp.first_name AS "ФИО",
               sp.birth_date,
               EXTRACT(YEAR FROM AGE(CURRENT_DATE, sp.birth_date))::INT AS "Возраст"
          FROM students_personal sp
         ORDER BY sp.last_name
         LIMIT 30
        """
        params = None
    elif ch == "6":
        # только локальные таблицы — FDW не участвует
        sql = """
        SELECT d.name, COUNT(s.id)
          FROM directions d
          LEFT JOIN groups g ON g.direction_id = d.id
          LEFT JOIN students s ON s.group_id = g.id
         GROUP BY d.name ORDER BY 2 DESC
        """
        params = None
    elif ch == "12":
        # grades / subjects локально на university (.61)
        sql = """
        SELECT sub.name, ROUND(AVG(gr.grade)::NUMERIC, 2)
          FROM subjects sub
          JOIN grades gr ON gr.subject_id = sub.id
         WHERE gr.grade > 2
         GROUP BY sub.name
         ORDER BY 2 DESC
        """
        params = None
    elif ch == "14":
        # отличники локально по grades, ФИО — через students_personal
        sql = """
        SELECT sp.last_name || ' ' || sp.first_name AS "ФИО", g.name
          FROM students s
          JOIN students_personal sp ON sp.id = s.id
          JOIN groups g ON g.id = s.group_id
          JOIN grades gr ON gr.student_id = s.id
         GROUP BY s.id, sp.last_name, sp.first_name, g.name
        HAVING MIN(gr.grade) = 5 AND COUNT(gr.id) > 0
         ORDER BY sp.last_name
        """
        params = None
    else:
        return

    with conn.cursor() as cur:
        # params=None → запрос без плейсхолдеров %s
        cur.execute(sql, params)
        show(cur)


def main() -> None:
    conn = connect()
    print("FDW-клиент →", DB["host"], "(личные данные тянутся с .60 через FDW)")
    try:
        while True:
            print("\n" + "=" * 50)
            print(" ЗАДАНИЕ 4 · FDW-КЛИЕНТ (часть 3, одно подключение)")
            for k, t in QUERIES.items():
                print(f"  [{k}] {t}")
            print("  [0] Выход")
            print("  примеры выбора: 1 | 2 | 14 | 0")
            ch = input("Выбор: ").strip()
            if ch == "0":
                break
            if ch not in QUERIES:
                print("  нет такого пункта, примеры: 1, 2, 4, 6, 12, 14, 0")
                continue
            try:
                run_query(conn, ch)
            except psycopg2.Error as exc:
                # типично: нет FOREIGN TABLE / SERVER / user mapping
                print(f"Ошибка SQL (проверьте FDW / students_personal): {exc}", file=sys.stderr)
            input("Enter — вернуться в меню...")
    finally:
        conn.close()  # одно соединение — закрываем в finally


if __name__ == "__main__":
    main()
