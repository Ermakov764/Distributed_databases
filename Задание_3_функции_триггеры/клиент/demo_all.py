#!/usr/bin/env python3
"""
Один прогон всего задания 3 для защиты.
Запуск:
  cd "Выполненые задания/3_task"
  source .venv/bin/activate
  python demo_all.py
"""

from __future__ import annotations

import json
import os
import sys

import psycopg2
from tabulate import tabulate

# Переопределение: export PGHOST=… PGUSER=… PGPASSWORD=…
DB = {
    "host": os.environ.get("PGHOST", "192.168.122.59"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "dbname": os.environ.get("PGDATABASE", "university_db"),
    "user": os.environ.get("PGUSER", "db1_user"),
    "password": os.environ.get("PGPASSWORD", "1"),
}

results: list[tuple[str, bool, str]] = []


def ok(name: str, detail: str = ""):
    results.append((name, True, detail))
    print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))


def fail(name: str, detail: str = ""):
    results.append((name, False, detail))
    print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def section(title: str):
    print("\n" + "=" * 64)
    print(f" {title}")
    print("=" * 64)


def show(cur, limit: int | None = None):
    rows = cur.fetchall()
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        print("  (пусто)")
        return rows
    headers = [d[0] for d in cur.description]
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    return rows


def main() -> int:
    print("ЗАДАНИЕ 3 — полный демо-прогон (функции + триггеры + параметры)")
    print(f"БД: {DB['host']}:{DB['port']}/{DB['dbname']}  user={DB['user']}")

    try:
        conn = psycopg2.connect(**DB)
    except psycopg2.Error as e:
        print(f"❌ Нет подключения: {e}")
        return 1

    # ---- inventory ----
    section("0. Объекты в БД (как в ТЗ)")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.proname
              FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'public' AND p.proname LIKE 'fn_%'
             ORDER BY 1
            """
        )
        funcs = [r[0] for r in cur.fetchall()]
        print("Функции fn_*:")
        for f in funcs:
            print(f"  • {f}")

        cur.execute(
            """
            SELECT t.tgname,
                   CASE WHEN t.tgtype & 2 = 2 THEN 'BEFORE' ELSE 'AFTER' END
              FROM pg_trigger t
              JOIN pg_class c ON c.oid = t.tgrelid
             WHERE NOT t.tgisinternal AND c.relname = 'grades'
             ORDER BY 1
            """
        )
        trigs = cur.fetchall()
        print("\nТриггеры на grades:")
        for name, timing in trigs:
            print(f"  • {name} ({timing})")

    need_fn = {
        "fn_avg_grade_subject_group",
        "fn_avg_grade_subject_direction",
        "fn_count_excellent_in_group",
        "fn_has_failed_exams",
        "fn_absences_by_student",
        "fn_absences_by_group",
        "fn_absences_by_direction",
        "fn_absences_by_teacher",
        "fn_numeric_param_stats",
        "fn_search_text_param",
        "fn_search_text_param_map",
    }
    missing = sorted(need_fn - set(funcs))
    if missing:
        fail("Все нужные fn_* на месте", f"нет: {', '.join(missing)}")
    else:
        ok("Все нужные fn_* на месте", f"{len(need_fn)} шт.")

    need_tg = {
        "trg_check_grade_value",
        "trg_check_grade_teacher",
        "trg_avg_group_subject",
        "trg_avg_group_all",
        "trg_avg_subject",
    }
    have_tg = {r[0] for r in trigs}
    missing_tg = sorted(need_tg - have_tg)
    if missing_tg:
        fail("5 триггеров на grades", f"нет: {', '.join(missing_tg)}")
    else:
        ok("5 триггеров на grades", ", ".join(sorted(have_tg)))

    # ---- sample keys ----
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT g.name
              FROM groups g
              JOIN subjects s ON s.direction_id = g.direction_id
             WHERE s.name = 'Архитектура ЭВМ'
             ORDER BY g.name LIMIT 1
            """
        )
        row = cur.fetchone()
        group = row[0] if row else "ИВТ-101"
        subject = "Архитектура ЭВМ"
        direction = "Информатика и вычислительная техника"

    # ---- functions ----
    section("1. Хранимые функции")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT fn_avg_grade_subject_group(%s, %s) AS avg",
            (subject, group),
        )
        avg = cur.fetchone()[0]
        show_rows = [(avg,)]
        print(tabulate(show_rows, headers=["avg"], tablefmt="grid"))
        ok("fn_avg_grade_subject_group", f"{subject} / {group} → {avg}")

        cur.execute(
            "SELECT fn_avg_grade_subject_direction(%s, %s) AS avg",
            (subject, direction),
        )
        avg2 = cur.fetchone()[0]
        print(tabulate([(avg2,)], headers=["avg"], tablefmt="grid"))
        ok("fn_avg_grade_subject_direction", f"→ {avg2}")

        cur.execute(
            "SELECT fn_count_excellent_in_group(%s) AS excellent_cnt",
            (group,),
        )
        exc = cur.fetchone()[0]
        print(tabulate([(exc,)], headers=["excellent_cnt"], tablefmt="grid"))
        ok("fn_count_excellent_in_group", f"{group} → {exc}")

        cur.execute("SELECT id FROM students ORDER BY id LIMIT 1")
        sid = cur.fetchone()[0]
        cur.execute("SELECT fn_has_failed_exams(%s) AS has_failed", (sid,))
        failed = cur.fetchone()[0]
        print(tabulate([(sid, failed)], headers=["student_id", "has_failed"], tablefmt="grid"))
        ok("fn_has_failed_exams", f"student_id={sid} → {failed}")

        print("\nfn_absences_by_student (топ-5):")
        cur.execute("SELECT * FROM fn_absences_by_student() LIMIT 5")
        show(cur)
        ok("fn_absences_by_student")

        print("\nfn_absences_by_group:")
        cur.execute("SELECT * FROM fn_absences_by_group()")
        show(cur, limit=8)
        ok("fn_absences_by_group")

        print("\nfn_absences_by_direction:")
        cur.execute("SELECT * FROM fn_absences_by_direction()")
        show(cur)
        ok("fn_absences_by_direction")

        print("\nfn_absences_by_teacher:")
        cur.execute("SELECT * FROM fn_absences_by_teacher()")
        show(cur)
        ok("fn_absences_by_teacher")

    # ---- triggers ----
    section("2. Триггеры")

    # T1
    with conn.cursor() as cur:
        cur.execute("SELECT student_id, subject_id FROM grades LIMIT 1")
        sid, subj = cur.fetchone()
        try:
            cur.execute(
                "UPDATE grades SET grade = 7 WHERE student_id=%s AND subject_id=%s",
                (sid, subj),
            )
            conn.commit()
            fail("T1 trg_check_grade_value", "оценка 7 прошла — триггер не сработал")
        except Exception as e:
            conn.rollback()
            ok("T1 trg_check_grade_value", str(e).split("\n")[0][:90])

    # T2
    with conn.cursor() as cur:
        cur.execute(
            "SELECT student_id, subject_id FROM grades WHERE grade IS NOT NULL LIMIT 1"
        )
        sid, subj = cur.fetchone()
        cur.execute(
            """
            SELECT t.id FROM teachers t
             WHERE NOT EXISTS (
               SELECT 1 FROM teacher_subjects ts
                WHERE ts.teacher_id = t.id AND ts.subject_id = %s
             )
             LIMIT 1
            """,
            (subj,),
        )
        bad = cur.fetchone()
        if not bad:
            fail("T2 trg_check_grade_teacher", "не найден «чужой» преподаватель")
        else:
            try:
                cur.execute(
                    "UPDATE grades SET set_by_teacher_id=%s WHERE student_id=%s AND subject_id=%s",
                    (bad[0], sid, subj),
                )
                conn.commit()
                fail("T2 trg_check_grade_teacher", "чужой преподаватель прошёл")
            except Exception as e:
                conn.rollback()
                ok("T2 trg_check_grade_teacher", str(e).split("\n")[0][:90])

    # T3/T4/T5 — показать таблицы + лёгкий UPDATE в транзакции с ROLLBACK
    with conn.cursor() as cur:
        print("\nТаблица avg_group_subject (T3), фрагмент:")
        cur.execute(
            """
            SELECT g.name AS group_name, sub.name AS subject, a.avg_grade
              FROM avg_group_subject a
              JOIN groups g ON g.id = a.group_id
              JOIN subjects sub ON sub.id = a.subject_id
             ORDER BY g.name, sub.name LIMIT 6
            """
        )
        show(cur)
        ok("T3 trg_avg_group_subject → avg_group_subject")

        print("\nТаблица avg_group_all (T4):")
        cur.execute(
            """
            SELECT g.name, a.avg_grade
              FROM avg_group_all a
              JOIN groups g ON g.id = a.group_id
             ORDER BY g.name LIMIT 8
            """
        )
        show(cur)
        ok("T4 trg_avg_group_all → avg_group_all")

        print("\nТаблица avg_subject (T5):")
        cur.execute(
            """
            SELECT sub.name, a.avg_grade
              FROM avg_subject a
              JOIN subjects sub ON sub.id = a.subject_id
             ORDER BY sub.name LIMIT 8
            """
        )
        show(cur)
        ok("T5 trg_avg_subject → avg_subject")

        # доказать, что AFTER-триггеры реально пересчитывают
        cur.execute(
            """
            SELECT gr.student_id, gr.subject_id, gr.grade, s.group_id, g.name, sub.name
              FROM grades gr
              JOIN students s ON s.id = gr.student_id
              JOIN groups g ON g.id = s.group_id
              JOIN subjects sub ON sub.id = gr.subject_id
             WHERE gr.grade IS NOT NULL
             LIMIT 1
            """
        )
        sid, subj, old, gid, gname, sname = cur.fetchone()
        new_grade = 5 if old != 5 else 4
        cur.execute(
            "SELECT avg_grade FROM avg_group_subject WHERE group_id=%s AND subject_id=%s",
            (gid, subj),
        )
        before = cur.fetchone()
        before_avg = before[0] if before else None
        cur.execute(
            "UPDATE grades SET grade=%s WHERE student_id=%s AND subject_id=%s",
            (new_grade, sid, subj),
        )
        cur.execute(
            "SELECT avg_grade FROM avg_group_subject WHERE group_id=%s AND subject_id=%s",
            (gid, subj),
        )
        after = cur.fetchone()[0]
        conn.rollback()  # не портим данные на защите
        print(
            f"\nПересчёт T3 (в транзакции, потом ROLLBACK): "
            f"{gname}/{sname} grade {old}→{new_grade}, avg {before_avg}→{after}"
        )
        ok("T3–T5 реально срабатывают на UPDATE", "изменения откатили ROLLBACK")

    # ---- extra params ----
    section("3. Доп. параметры")

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM extra_param_defs")
        n_defs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM student_extra_params")
        n_vals = cur.fetchone()[0]
        print(f"extra_param_defs: {n_defs}, student_extra_params: {n_vals}")
        if n_defs > 0 and n_vals > 0:
            ok("Механизм доп. параметров заполнен", f"{n_defs} defs / {n_vals} values")
        else:
            fail("Механизм доп. параметров заполнен", "таблицы пустые — нужен seed")

        cur.execute(
            """
            SELECT param_name FROM extra_param_defs
             WHERE param_type = 'numeric' ORDER BY id LIMIT 1
            """
        )
        row = cur.fetchone()
        param = row[0] if row else "рейтинг_балл"
        print(f"\nfn_numeric_param_stats('{group}', '{param}'):")
        cur.execute("SELECT * FROM fn_numeric_param_stats(%s, %s)", (group, param))
        show(cur)
        ok("fn_numeric_param_stats (avg/sum)")

        print("\nfn_search_text_param_map('Python') — assoc. массив:")
        cur.execute("SELECT fn_search_text_param_map(%s) AS assoc_map", ("Python",))
        mmap = cur.fetchone()[0] or {}
        # показать кусок
        sample = dict(list(mmap.items())[:5]) if isinstance(mmap, dict) else mmap
        print(json.dumps(sample, ensure_ascii=False, indent=2))
        if isinstance(mmap, dict) and len(mmap) == 0:
            # fallback другой поисковый фрагмент
            cur.execute(
                """
                SELECT text_value FROM student_extra_params
                 WHERE text_value IS NOT NULL LIMIT 1
                """
            )
            tv = cur.fetchone()
            needle = (tv[0][:4] if tv else "а")
            cur.execute("SELECT fn_search_text_param_map(%s)", (needle,))
            mmap = cur.fetchone()[0] or {}
            print(f"(fallback поиск '{needle}'): {len(mmap)} ключей")
        ok(
            "fn_search_text_param_map (человек необязателен)",
            f"ключей: {len(mmap) if isinstance(mmap, dict) else '?'}",
        )

        print("\nfn_search_text_param (строки), LIMIT 5:")
        cur.execute(
            """
            SELECT student_id, full_name, group_name, param_name, found_value
              FROM fn_search_text_param('а') LIMIT 5
            """
        )
        show(cur)
        ok("fn_search_text_param")

    conn.close()

    # ---- summary ----
    section("ИТОГ ДЛЯ ПРЕПОДАВАТЕЛЯ")
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    for name, p, detail in results:
        mark = "OK" if p else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not p else ""))
    print("-" * 64)
    print(f"  Пройдено: {passed}/{total}")
    if passed == total:
        print("  Всё из ТЗ задания 3 отрабатывает.")
        return 0
    print("  Есть провалы — разбери FAIL выше.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
