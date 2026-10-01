#!/usr/bin/env python3
"""Демонстрационный клиент — Задание 3 (функции, триггеры, доп. параметры)."""

from __future__ import annotations

import json
import os

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


def connect():
    try:
        return psycopg2.connect(**DB)
    except psycopg2.Error as e:
        print(f"❌ Ошибка подключения: {e}")
        return None


def banner(title: str) -> None:
    print(f"\n{'─' * 64}")
    print(f" {title}")
    print(f"{'─' * 64}")


def show_input(params: dict) -> None:
    print("\n📥 ВВЕЛИ (параметры запроса):")
    if not params:
        print("  (параметров нет — функция без аргументов)")
        return
    for k, v in params.items():
        shown = "«пусто / не задано»" if v is None or v == "" else v
        print(f"  • {k} = {shown}")


def show_sql(sql: str, params=None) -> None:
    print("\n📝 ЗАПРОС К БД (SQL):")
    print(sql.strip())
    if params is not None:
        print(f"  плейсхолдеры %s ← {params}")
        filled = sql.strip()
        for p in params:
            if p is None:
                lit = "NULL"
            elif isinstance(p, str):
                lit = "'" + p.replace("'", "''") + "'"
            else:
                lit = str(p)
            filled = filled.replace("%s", lit, 1)
        print("\n📝 Тот же запрос с подставленными значениями:")
        print(filled)


def show_rows(cur, title: str = "ОТВЕТ БД") -> list:
    rows = cur.fetchall()
    print(f"\n📤 {title}:")
    if not rows:
        print("  (пусто — 0 строк)")
        return []
    headers = [d[0] for d in cur.description]
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print(f"  строк: {len(rows)}")
    return rows


def show_scalar_msg(msg: str) -> None:
    print(f"\n📤 ОТВЕТ БД:\n  {msg}")


def ask(prompt: str, default: str) -> str:
    raw = input(f"{prompt} [{default}]: ").strip()
    return raw if raw else default


def q_avg_group(conn):
    banner("Средняя оценка: предмет + группа")
    subj = ask("Предмет", "Архитектура ЭВМ")
    group = ask("Группа", "ИВТ-101")
    show_input({"предмет": subj, "группа": group})
    sql = "SELECT fn_avg_grade_subject_group(%s, %s) AS avg_grade"
    show_sql(sql, (subj, group))
    with conn.cursor() as cur:
        cur.execute(sql, (subj, group))
        show_rows(cur)


def q_avg_dir(conn):
    banner("Средняя оценка: предмет + направление")
    subj = ask("Предмет", "Архитектура ЭВМ")
    direction = ask("Направление", "Информатика и вычислительная техника")
    show_input({"предмет": subj, "направление": direction})
    sql = "SELECT fn_avg_grade_subject_direction(%s, %s) AS avg_grade"
    show_sql(sql, (subj, direction))
    with conn.cursor() as cur:
        cur.execute(sql, (subj, direction))
        show_rows(cur)


def q_excellent(conn):
    banner("Число отличников в группе")
    group = ask("Группа", "ИВТ-101")
    show_input({"группа": group})
    sql = "SELECT fn_count_excellent_in_group(%s) AS excellent_cnt"
    show_sql(sql, (group,))
    with conn.cursor() as cur:
        cur.execute(sql, (group,))
        show_rows(cur)


def q_failed(conn):
    banner("Есть ли несданные у студента")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, last_name, first_name FROM students ORDER BY id LIMIT 5"
        )
        show_rows(cur, "Подсказка — примеры студентов")
    sid = ask("student_id", "1")
    show_input({"student_id": sid})
    sql = "SELECT fn_has_failed_exams(%s) AS has_failed"
    show_sql(sql, (int(sid),))
    with conn.cursor() as cur:
        cur.execute(sql, (int(sid),))
        show_rows(cur)


def q_abs_student(conn):
    banner("Пропуски по студентам")
    show_input({})
    sql = "SELECT * FROM fn_absences_by_student() LIMIT 30"
    show_sql(sql)
    with conn.cursor() as cur:
        cur.execute(sql)
        show_rows(cur)


def q_abs_group(conn):
    banner("Пропуски по группам")
    show_input({})
    sql = "SELECT * FROM fn_absences_by_group()"
    show_sql(sql)
    with conn.cursor() as cur:
        cur.execute(sql)
        show_rows(cur)


def q_abs_dir(conn):
    banner("Пропуски по направлениям")
    show_input({})
    sql = "SELECT * FROM fn_absences_by_direction()"
    show_sql(sql)
    with conn.cursor() as cur:
        cur.execute(sql)
        show_rows(cur)


def q_abs_teacher(conn):
    banner("Пропуски по преподавателям")
    show_input({})
    sql = "SELECT * FROM fn_absences_by_teacher()"
    show_sql(sql)
    with conn.cursor() as cur:
        cur.execute(sql)
        show_rows(cur)


def q_trig_bad_grade(conn):
    banner("Триггер T1: недопустимая оценка (ожидается ошибка)")
    with conn.cursor() as cur:
        cur.execute("SELECT student_id, subject_id, grade FROM grades LIMIT 1")
        sid, subj, old = cur.fetchone()
    show_input({
        "student_id": sid,
        "subject_id": subj,
        "старая оценка": old,
        "новая оценка (недопустимая)": 7,
    })
    sql = "UPDATE grades SET grade = 7 WHERE student_id=%s AND subject_id=%s"
    show_sql(sql, (sid, subj))
    with conn.cursor() as cur:
        try:
            cur.execute(sql, (sid, subj))
            conn.commit()
            show_scalar_msg("Неожиданно: обновление прошло (триггер не сработал)")
        except Exception as e:
            conn.rollback()
            show_scalar_msg(f"Триггер отклонил операцию → {e}")


def q_trig_bad_teacher(conn):
    banner("Триггер T2: преподаватель не назначен на предмет")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT student_id, subject_id, grade FROM grades WHERE grade IS NOT NULL LIMIT 1"
        )
        sid, subj, grade = cur.fetchone()
        cur.execute(
            """
            SELECT t.id, t.last_name FROM teachers t
            WHERE NOT EXISTS (
                SELECT 1 FROM teacher_subjects ts
                WHERE ts.teacher_id = t.id AND ts.subject_id = %s
            )
            LIMIT 1
            """,
            (subj,),
        )
        row = cur.fetchone()
        if not row:
            show_scalar_msg("Не найден «чужой» преподаватель для демо")
            return
        bad_tid, bad_name = row
    show_input({
        "student_id": sid,
        "subject_id": subj,
        "set_by_teacher_id (чужой)": f"{bad_tid} ({bad_name})",
        "grade": grade,
    })
    sql = (
        "UPDATE grades SET set_by_teacher_id = %s, grade = %s "
        "WHERE student_id=%s AND subject_id=%s"
    )
    show_sql(sql, (bad_tid, grade, sid, subj))
    with conn.cursor() as cur:
        try:
            cur.execute(sql, (bad_tid, grade, sid, subj))
            conn.commit()
            show_scalar_msg("Неожиданно: обновление прошло (триггер не сработал)")
        except Exception as e:
            conn.rollback()
            show_scalar_msg(f"Триггер отклонил операцию → {e}")


def q_trig_averages(conn):
    banner("Триггеры T3–T5: таблицы средних")
    with conn.cursor() as cur:
        print("\n📤 Состояние ДО изменения:")
        cur.execute(
            """
            SELECT g.name AS group, sub.name AS subject, a.avg_grade, a.updated_at
              FROM avg_group_subject a
              JOIN groups g ON g.id = a.group_id
              JOIN subjects sub ON sub.id = a.subject_id
             ORDER BY a.updated_at DESC NULLS LAST
             LIMIT 5
            """
        )
        show_rows(cur, "avg_group_subject (T3), топ-5")

        cur.execute(
            """
            SELECT gr.student_id, gr.subject_id, gr.grade, g.name, sub.name, ts.teacher_id
              FROM grades gr
              JOIN students s ON s.id = gr.student_id
              JOIN groups g ON g.id = s.group_id
              JOIN subjects sub ON sub.id = gr.subject_id
              JOIN teacher_subjects ts ON ts.subject_id = sub.id
             WHERE gr.grade IS NOT NULL
             LIMIT 1
            """
        )
        sid, subj, old, gname, sname, tid = cur.fetchone()
        new_grade = 5 if old != 5 else 4

        show_input({
            "группа": gname,
            "предмет": sname,
            "student_id": sid,
            "оценка было": old,
            "оценка станет": new_grade,
            "set_by_teacher_id": tid,
        })
        sql = (
            "UPDATE grades SET grade = %s, set_by_teacher_id = %s "
            "WHERE student_id = %s AND subject_id = %s"
        )
        show_sql(sql, (new_grade, tid, sid, subj))
        cur.execute(sql, (new_grade, tid, sid, subj))
        conn.commit()

        cur.execute(
            """
            SELECT g.name, sub.name, a.avg_grade, a.updated_at
              FROM avg_group_subject a
              JOIN groups g ON g.id = a.group_id
              JOIN subjects sub ON sub.id = a.subject_id
             WHERE g.name = %s AND sub.name = %s
            """,
            (gname, sname),
        )
        show_rows(cur, "ПОСЛЕ UPDATE — avg_group_subject (T3)")

        cur.execute(
            """
            SELECT g.name AS group, a.avg_grade, a.updated_at
              FROM avg_group_all a
              JOIN groups g ON g.id = a.group_id
             WHERE g.name = %s
            """,
            (gname,),
        )
        show_rows(cur, "ПОСЛЕ UPDATE — avg_group_all (T4)")

        cur.execute(
            """
            SELECT sub.name AS subject, a.avg_grade, a.updated_at
              FROM avg_subject a
              JOIN subjects sub ON sub.id = a.subject_id
             WHERE sub.name = %s
            """,
            (sname,),
        )
        show_rows(cur, "ПОСЛЕ UPDATE — avg_subject (T5)")


def q_param_defs(conn):
    banner("Определения доп. параметров по направлениям")
    show_input({})
    sql = """
SELECT d.name AS direction, e.param_name, e.param_type, e.description
  FROM extra_param_defs e
  JOIN directions d ON d.id = e.direction_id
 ORDER BY d.name, e.param_type, e.param_name
"""
    show_sql(sql)
    with conn.cursor() as cur:
        cur.execute(sql)
        show_rows(cur)


def q_num_stats(conn):
    banner("Среднее и сумма числового параметра группы")
    group = ask("Группа", "ИВТ-101")
    param = ask("Параметр", "рейтинг_балл")
    show_input({"группа": group, "параметр": param})
    sql = "SELECT * FROM fn_numeric_param_stats(%s, %s)"
    show_sql(sql, (group, param))
    with conn.cursor() as cur:
        cur.execute(sql, (group, param))
        show_rows(cur)


def q_text_search(conn):
    banner("Текстовый поиск доп. параметров")
    value = ask("Искомое значение", "Python")
    param_raw = input("Имя параметра (Enter = любой): ").strip()
    group_raw = input("Группа (Enter = любая): ").strip()
    sid_raw = input("student_id (Enter = все): ").strip()
    param = param_raw or None
    group = group_raw or None
    sid = int(sid_raw) if sid_raw else None
    show_input({
        "искомое значение": value,
        "имя параметра": param,
        "группа": group,
        "student_id": sid,
    })
    sql1 = (
        "SELECT student_id, full_name, group_name, param_name, found_value "
        "FROM fn_search_text_param(%s,%s,%s,%s)"
    )
    show_sql(sql1, (value, param, group, sid))
    with conn.cursor() as cur:
        cur.execute(sql1, (value, param, group, sid))
        show_rows(cur, "ОТВЕТ БД — найденные строки")

        sql2 = "SELECT fn_search_text_param_map(%s,%s,%s) AS assoc_map"
        show_sql(sql2, (value, param, group))
        cur.execute(sql2, (value, param, group))
        (mmap,) = cur.fetchone()
        print("\n📤 ОТВЕТ БД — ассоциативный массив (student_id → value):")
        print(json.dumps(mmap, ensure_ascii=False, indent=2))


MENU = {
    "1": ("Средняя оценка: предмет + группа", q_avg_group),
    "2": ("Средняя оценка: предмет + направление", q_avg_dir),
    "3": ("Число отличников в группе", q_excellent),
    "4": ("Есть ли несданные у студента", q_failed),
    "5": ("Пропуски по студентам", q_abs_student),
    "6": ("Пропуски по группам", q_abs_group),
    "7": ("Пропуски по направлениям", q_abs_dir),
    "8": ("Пропуски по преподавателям", q_abs_teacher),
    "9": ("Триггер T1: недопустимая оценка", q_trig_bad_grade),
    "10": ("Триггер T2: чужой преподаватель", q_trig_bad_teacher),
    "11": ("Триггеры T3/T4/T5: три таблицы средних", q_trig_averages),
    "12": ("Список доп. параметров специальностей", q_param_defs),
    "13": ("Числовые параметры: avg/sum", q_num_stats),
    "14": ("Текстовый поиск + assoc. map", q_text_search),
    "0": ("Выход", None),
}


def print_menu():
    print("\n" + "=" * 64)
    print(" ДЕМОНСТРАЦИОННЫЙ КЛИЕНТ — ЗАДАНИЕ 3 (PostgreSQL)")
    print("=" * 64)
    print("\n📌 ФУНКЦИИ")
    for k in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        print(f"  [{k}] {MENU[k][0]}")
    print("\n📌 ТРИГГЕРЫ")
    for k in ["9", "10", "11"]:
        print(f"  [{k}] {MENU[k][0]}")
    print("\n📌 ДОП. ПАРАМЕТРЫ")
    for k in ["12", "13", "14"]:
        print(f"  [{k}] {MENU[k][0]}")
    print("\n  [0] Выход")
    print("=" * 64)


def main():
    conn = connect()
    if not conn:
        return
    print("\n✅ Подключение к PostgreSQL установлено!")
    print("   Каждый пункт: ВВЕЛИ → SQL (с значениями) → ОТВЕТ БД")
    while True:
        print_menu()
        choice = input("\nВыберите пункт: ").strip()
        if choice == "0":
            print("\n👋 До свидания!")
            break
        if choice in MENU and MENU[choice][1]:
            try:
                MENU[choice][1](conn)
            except Exception as e:
                conn.rollback()
                print(f"\n❌ Ошибка: {e}")
            input("\nEnter для продолжения...")
        else:
            print("Неверный выбор.")
    conn.close()


if __name__ == "__main__":
    main()
