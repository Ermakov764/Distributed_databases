#!/usr/bin/env python3
"""
Один прогон задания 4 для защиты (текущее состояние: части 2–3).
Часть 1 (streaming) историческая — после promote уже не активна;
скрипт это отмечает и проверяет следы + живые части 2 и 3.

Запуск:
  cd "Выполненые задания/4_task"
  source .venv/bin/activate
  python demo_all.py

Примечание: ниже VM_UNI=.61 (VM11), VM_PERSONAL=.60 (VM2) —
как в итоговой сдаче (VM1 .59 для лаб 1–3 не трогаем).
"""

from __future__ import annotations

import sys

import psycopg2
from tabulate import tabulate

# university-контур (после split / FDW) и personal-контур
VM_UNI = dict(host="192.168.122.61", port=5432, dbname="university_db", user="db1_user", password="1")
VM_PERSONAL = dict(host="192.168.122.60", port=5432, dbname="university_db", user="db1_user", password="1")

# копим (название, ok?, деталь) → сводка в конце для преподавателя
results: list[tuple[str, bool, str]] = []


def ok(name: str, detail: str = ""):
    """Отметить успешную проверку."""
    results.append((name, True, detail))
    print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))


def fail(name: str, detail: str = ""):
    """Отметить провал (не прерываем прогон — дойдём до итога)."""
    results.append((name, False, detail))
    print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def section(title: str):
    """Визуальный разделитель блоков части 1 / 2 / 3."""
    print("\n" + "=" * 66)
    print(f" {title}")
    print("=" * 66)


def show(rows, headers):
    """Короткая таблица (до 12 строк), чтобы не засорять вывод на защите."""
    if not rows:
        print("  (пусто)")
        return
    print(tabulate(rows[:12], headers=headers, tablefmt="grid"))


def connect(cfg):
    """Простой connect без меню — для автопроверки."""
    return psycopg2.connect(**cfg)


def main() -> int:
    print("ЗАДАНИЕ 4 — демо-прогон (split + FDW; зеркало — по истории/дампам)")
    print(f"UNI={VM_UNI['host']}  PERSONAL={VM_PERSONAL['host']}")

    try:
        c_uni = connect(VM_UNI)
        c_pers = connect(VM_PERSONAL)
    except Exception as e:
        print(f"❌ Подключение: {e}")
        return 1

    # ---- Часть 1: зеркало уже не живо, но ключи students должны совпадать ----
    section("Часть 1 · Зеркало (исторически)")
    print(
        "  После части 2 standby промоутнут — streaming уже не активен.\n"
        "  На защите: скрины part1 / dump/part1_status.txt / отчёт §3.\n"
        "  Проверка «сейчас»: обе БД живы, students.id согласованы."
    )
    with c_uni.cursor() as cur:
        # pg_is_in_recovery()=false → primary (не standby)
        cur.execute("SELECT pg_is_in_recovery(), COUNT(*) FROM students")
        rec, n1 = cur.fetchone()
    with c_pers.cursor() as cur:
        cur.execute("SELECT pg_is_in_recovery(), COUNT(*) FROM students")
        rec2, n2 = cur.fetchone()
    print(f"  UNI  recovery={rec}, students={n1}")
    print(f"  PERS recovery={rec2}, students={n2}")
    # 240=240 — след того, что когда-то было полное зеркало, потом split
    if n1 == n2 == 240:
        ok("Согласованность ключей students (240=240)", "следствие бывшего зеркала + split")
    else:
        fail("Согласованность ключей students", f"{n1} vs {n2}")

    # ---- Часть 2: разрез personal / university ----
    section("Часть 2 · Распределение personal / university")
    with c_uni.cursor() as cur:
        # на university ФИО должны быть NULL, phones — удалены
        cur.execute("SELECT COUNT(*) FILTER (WHERE last_name IS NULL), COUNT(*) FROM students")
        null_fio, n = cur.fetchone()
        cur.execute(
            "SELECT to_regclass('public.phones'), to_regclass('public.grades'), to_regclass('public.directions')"
        )
        phones_uni, grades, dirs = cur.fetchone()
    with c_pers.cursor() as cur:
        # на personal ФИО заполнены, phones есть, учебных таблиц нет
        cur.execute("SELECT COUNT(*) FILTER (WHERE last_name IS NOT NULL), COUNT(*) FROM students")
        named, n2 = cur.fetchone()
        cur.execute(
            "SELECT to_regclass('public.phones'), to_regclass('public.grades'), to_regclass('public.directions')"
        )
        phones_pers, grades2, dirs2 = cur.fetchone()

    print(f"  UNI:  ФИО NULL = {null_fio}/{n}, phones={phones_uni}, grades={grades}")
    print(f"  PERS: ФИО заполнено = {named}/{n2}, phones={phones_pers}, grades={grades2}")

    if null_fio == n and n > 0:
        ok("UNI university: ФИО обнулены")
    else:
        fail("UNI university: ФИО обнулены", f"null={null_fio}/{n}")

    if phones_uni is None and grades is not None:
        ok("UNI: phones удалены, учебные таблицы на месте")
    else:
        fail("UNI схема university", f"phones={phones_uni}, grades={grades}")

    if named == n2 and phones_pers is not None and grades2 is None:
        ok("PERS personal: ФИО+phones, без grades")
    else:
        fail("PERS схема personal", f"named={named}, phones={phones_pers}, grades={grades2}")

    # мини-аналог 4_task_distributed.py: фильтр на .60 → группы с .61
    with c_pers.cursor() as cur:
        cur.execute(
            """
            SELECT id, last_name, first_name
              FROM students
             WHERE UPPER(last_name) LIKE 'Е%'
             ORDER BY last_name LIMIT 15
            """
        )
        people = cur.fetchall()
    ids = [p[0] for p in people]
    with c_uni.cursor() as cur:
        cur.execute(
            """
            SELECT s.id, g.name, d.name
              FROM students s
              JOIN groups g ON g.id = s.group_id
              JOIN directions d ON d.id = g.direction_id
             WHERE s.id = ANY(%s)
            """,
            (ids,),
        )
        umap = {r[0]: (r[1], r[2]) for r in cur.fetchall()}  # id → (группа, направление)
    # склейка в Python — как в distributed-клиенте
    rows = [[f"{ln} {fn}", *umap.get(i, ("?", "?"))] for i, ln, fn in people]
    print("\n  Distributed-запрос «фамилия на Е» (personal@.60 + uni@.61):")
    show(rows, ["ФИО", "Группа", "Направление"])
    if rows and all(r[1] != "?" for r in rows):
        ok("Клиент части 2: JOIN по id через два подключения", f"строк: {len(rows)}")
    else:
        fail("Клиент части 2: JOIN по id", "нет строк или не склеилось")

    # ---- Часть 3: FDW на university (.61) ----
    section("Часть 3 · FDW (один хост .61)")
    with c_uni.cursor() as cur:
        # что видит каталог внешних таблиц
        cur.execute("SELECT foreign_table_name FROM information_schema.foreign_tables ORDER BY 1")
        fts = [r[0] for r in cur.fetchall()]
        print(f"  Foreign tables: {fts}")
        if set(fts) >= {"students_personal", "phones_personal"}:
            ok("Foreign tables students_personal / phones_personal")
        else:
            fail("Foreign tables", str(fts))

        # VIEW поверх FDW — «одна БД» для клиента
        cur.execute("SELECT to_regclass('public.v_students_full')")
        view = cur.fetchone()[0]
        if view:
            cur.execute("SELECT COUNT(*) FROM v_students_full")
            cnt = cur.fetchone()[0]
            ok("VIEW v_students_full", f"карточек: {cnt}")
        else:
            fail("VIEW v_students_full", "нет")

        print("\n  FDW: группы ИВТ (локальный JOIN + students_personal):")
        cur.execute(
            """
            SELECT g.name AS group_name,
                   sp.last_name || ' ' || sp.first_name AS fio,
                   CASE WHEN s.is_budget THEN 'Бюджет' ELSE 'Внебюджет' END AS typ
              FROM students s
              JOIN students_personal sp ON sp.id = s.id
              JOIN groups g ON g.id = s.group_id
              JOIN directions d ON d.id = g.direction_id
             WHERE d.name = 'Информатика и вычислительная техника'
             ORDER BY g.name, sp.last_name
             LIMIT 10
            """
        )
        show(cur.fetchall(), [d[0] for d in cur.description])
        ok("FDW-запрос групп направления")

        print("\n  FDW: фамилия на «Е» (только подключение к .61):")
        cur.execute(
            """
            SELECT sp.last_name || ' ' || sp.first_name AS fio, g.name, d.name
              FROM students_personal sp
              JOIN students s ON s.id = sp.id
              JOIN groups g ON g.id = s.group_id
              JOIN directions d ON d.id = g.direction_id
             WHERE UPPER(sp.last_name) LIKE 'Е%'
             ORDER BY sp.last_name
             LIMIT 10
            """
        )
        rows_e = cur.fetchall()
        show(rows_e, [d[0] for d in cur.description])
        if rows_e:
            ok("FDW-запрос буква «Е»", f"строк: {len(rows_e)}")
        else:
            fail("FDW-запрос буква «Е»", "пусто")

        # телефоны тоже через FDW (phones локально на .61 нет)
        cur.execute("SELECT COUNT(*) FROM phones_personal")
        ph = cur.fetchone()[0]
        ok("phones_personal через FDW", f"телефонов: {ph}")

    c_uni.close()
    c_pers.close()

    # ---- сводка ----
    section("ИТОГ ДЛЯ ПРЕПОДАВАТЕЛЯ")
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    for name, p, detail in results:
        mark = "OK" if p else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not p else ""))
    print("-" * 66)
    print(f"  Пройдено: {passed}/{total}")
    print("  Меню клиентов:")
    print("    python 4_task_distributed.py   # часть 2, два хоста")
    print("    python 4_task_fdw.py           # часть 3, только .61")
    if passed == total:
        print("  Текущее состояние (части 2–3) работает.")
        return 0
    print("  Есть провалы — смотри FAIL выше.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
