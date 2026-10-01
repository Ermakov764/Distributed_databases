import os
import psycopg2
from tabulate import tabulate
from datetime import datetime
import textwrap

# Подключение: по умолчанию учебная ВМ. Можно переопределить:
#   export PGHOST=… PGPORT=… PGDATABASE=… PGUSER=… PGPASSWORD=…
DB_CONFIG = {
    "host": os.environ.get("PGHOST", "192.168.122.59"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "dbname": os.environ.get("PGDATABASE", "university_db"),
    "user": os.environ.get("PGUSER", "db1_user"),
    "password": os.environ.get("PGPASSWORD", "1"),
}


def get_connection():
    """Подключение к базе данных."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"\n❌ Ошибка подключения к БД: {e}")
        return None


def _sql_literal(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def show_input(params=None):
    """Показать, что пользователь ввёл."""
    print("\n📥 ВВЕЛИ:")
    if not params:
        print("  (параметров нет — запрос без ввода)")
        return
    for k, v in params.items():
        print(f"  • {k} = {v}")


def execute_query(conn, query, params=None, inputs=None):
    """Показать ввод → SQL → ответ БД."""
    show_input(inputs)
    sql = textwrap.dedent(query).strip()
    print("\n📝 ЗАПРОС К БД (SQL):")
    print(sql)
    if params is not None:
        print(f"  плейсхолдеры %s ← {params}")
        filled = sql
        for p in params:
            filled = filled.replace("%s", _sql_literal(p), 1)
        print("\n📝 Тот же запрос с подставленными значениями:")
        print(filled)
    print("\n📤 ОТВЕТ БД:")
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        if rows:
            headers = [desc[0] for desc in cursor.description]
            print(tabulate(rows, headers=headers, tablefmt="grid"))
            print(f"  строк: {len(rows)}")
        else:
            print("  (пусто — 0 строк)")
        cursor.close()
    except psycopg2.Error as e:
        print(f"  ❌ Ошибка: {e}")


# ============================================
# ЗАПРОСЫ БЛОКА 1: СТУДЕНТЫ
# ============================================

def query_1(conn):
    """Вывести списки групп по заданному направлению."""
    print("\n📋 Запрос 1: Списки групп по направлению")
    direction = input("Введите название направления (например, Информатика и вычислительная техника): ").strip()
    query = """
        SELECT g.name AS "Группа",
               s.last_name || ' ' || s.first_name || ' ' || s.middle_name AS "ФИО",
               CASE WHEN s.is_budget THEN 'Бюджет' ELSE 'Внебюджет' END AS "Тип обучения"
        FROM students s
        JOIN groups g ON s.group_id = g.id
        JOIN directions d ON g.direction_id = d.id
        WHERE d.name = %s
        ORDER BY g.name, s.last_name, s.first_name;
    """
    execute_query(conn, query, (direction,), inputs={"направление": direction})


def query_2(conn):
    """Вывести студентов с фамилией на заданную букву."""
    print("\n📋 Запрос 2: Студенты по первой букве фамилии")
    letter = input("Введите первую букву фамилии (например, И): ").strip().upper()
    query = """
        SELECT s.last_name || ' ' || s.first_name || ' ' || s.middle_name AS "ФИО",
               g.name AS "Группа",
               d.name AS "Направление"
        FROM students s
        JOIN groups g ON s.group_id = g.id
        JOIN directions d ON g.direction_id = d.id
        WHERE UPPER(s.last_name) LIKE %s
        ORDER BY s.last_name;
    """
    execute_query(conn, query, (f"{letter}%",), inputs={"первая буква фамилии": letter})


def query_3(conn):
    """Вывести список студентов для поздравления по месяцам."""
    print("\n📋 Запрос 3: Список студентов для поздравления по месяцам")
    query = """
        SELECT s.last_name || ' ' || LEFT(s.first_name, 1) || '.' || LEFT(s.middle_name, 1) || '.' AS "ФИО",
               EXTRACT(DAY FROM s.birth_date) AS "День",
               TO_CHAR(s.birth_date, 'TMMonth') AS "Месяц",
               g.name AS "Группа",
               d.name AS "Направление"
        FROM students s
        JOIN groups g ON s.group_id = g.id
        JOIN directions d ON g.direction_id = d.id
        ORDER BY EXTRACT(MONTH FROM s.birth_date), EXTRACT(DAY FROM s.birth_date);
    """
    execute_query(conn, query)


def query_4(conn):
    """Вывести студентов с указанием возраста."""
    print("\n📋 Запрос 4: Студенты с указанием возраста")
    query = """
        SELECT s.last_name || ' ' || s.first_name || ' ' || s.middle_name AS "ФИО",
               s.birth_date AS "Дата рождения",
               EXTRACT(YEAR FROM AGE(CURRENT_DATE, s.birth_date))::INT AS "Возраст"
        FROM students s
        ORDER BY s.last_name;
    """
    execute_query(conn, query)


def query_5(conn):
    """Вывести студентов с днем рождения в текущем месяце."""
    print("\n📋 Запрос 5: Студенты с ДР в текущем месяце")
    query = """
        SELECT s.last_name || ' ' || s.first_name || ' ' || s.middle_name AS "ФИО",
               s.birth_date AS "Дата рождения",
               g.name AS "Группа"
        FROM students s
        JOIN groups g ON s.group_id = g.id
        WHERE EXTRACT(MONTH FROM s.birth_date) = EXTRACT(MONTH FROM CURRENT_DATE)
        ORDER BY EXTRACT(DAY FROM s.birth_date);
    """
    execute_query(conn, query)


def query_6(conn):
    """Вывести количество студентов по каждому направлению."""
    print("\n📋 Запрос 6: Количество студентов по направлениям")
    query = """
        SELECT d.name AS "Направление",
               COUNT(s.id) AS "Количество студентов"
        FROM directions d
        LEFT JOIN groups g ON d.id = g.direction_id
        LEFT JOIN students s ON g.id = s.group_id
        GROUP BY d.name
        ORDER BY COUNT(s.id) DESC;
    """
    execute_query(conn, query)


def query_7(conn):
    """Вывести количество бюджетных и внебюджетных мест по группам."""
    print("\n📋 Запрос 7: Бюджетные и внебюджетные места по группам")
    query = """
        SELECT g.name AS "Группа",
               d.name AS "Направление",
               COUNT(CASE WHEN s.is_budget THEN 1 END) AS "Бюджет",
               COUNT(CASE WHEN NOT s.is_budget THEN 1 END) AS "Внебюджет"
        FROM groups g
        JOIN directions d ON g.direction_id = d.id
        LEFT JOIN students s ON g.id = s.group_id
        GROUP BY g.name, d.name
        ORDER BY g.name;
    """
    execute_query(conn, query)


# ============================================
# ЗАПРОСЫ БЛОКА 2: ПРЕДМЕТЫ И ОЦЕНКИ
# ============================================

def query_8(conn):
    """Вывести списки групп по каждому предмету с преподавателем."""
    print("\n📋 Запрос 8: Группы по предметам с преподавателем")
    query = """
        SELECT sub.name AS "Предмет",
               t.last_name || ' ' || t.first_name || ' ' || t.middle_name AS "Преподаватель",
               g.name AS "Группа"
        FROM subjects sub
        JOIN teacher_subjects ts ON sub.id = ts.subject_id
        JOIN teachers t ON ts.teacher_id = t.id
        JOIN grades gr ON sub.id = gr.subject_id
        JOIN students s ON gr.student_id = s.id
        JOIN groups g ON s.group_id = g.id
        GROUP BY sub.name, t.last_name, t.first_name, t.middle_name, g.name
        ORDER BY sub.name, g.name;
    """
    execute_query(conn, query)


def query_9(conn):
    """Определить дисциплину с максимальным количеством студентов."""
    print("\n📋 Запрос 9: Дисциплина с максимальным количеством студентов")
    query = """
        SELECT sub.name AS "Предмет",
               COUNT(DISTINCT gr.student_id) AS "Количество студентов"
        FROM subjects sub
        JOIN grades gr ON sub.id = gr.subject_id
        GROUP BY sub.name
        ORDER BY COUNT(DISTINCT gr.student_id) DESC
        LIMIT 1;
    """
    execute_query(conn, query)


def query_10(conn):
    """Определить сколько студентов у каждого преподавателя."""
    print("\n📋 Запрос 10: Количество студентов у каждого преподавателя")
    query = """
        SELECT t.last_name || ' ' || t.first_name || ' ' || t.middle_name AS "Преподаватель",
               COUNT(DISTINCT gr.student_id) AS "Количество студентов"
        FROM teachers t
        JOIN teacher_subjects ts ON t.id = ts.teacher_id
        JOIN grades gr ON ts.subject_id = gr.subject_id
        GROUP BY t.last_name, t.first_name, t.middle_name
        ORDER BY COUNT(DISTINCT gr.student_id) DESC;
    """
    execute_query(conn, query)


def query_11(conn):
    """Определить долю сдавших студентов по каждой дисциплине."""
    print("\n📋 Запрос 11: Доля сдавших студентов по дисциплинам")
    query = """
        SELECT sub.name AS "Предмет",
               COUNT(DISTINCT s.id) AS "Всего студентов",
               COUNT(DISTINCT CASE WHEN gr.grade IS NOT NULL AND gr.grade > 2 THEN s.id END) AS "Сдали",
               ROUND(
                   COUNT(DISTINCT CASE WHEN gr.grade IS NOT NULL AND gr.grade > 2 THEN s.id END)::NUMERIC /
                   NULLIF(COUNT(DISTINCT s.id), 0) * 100, 2
               ) AS "Доля сдавших (%)"
        FROM subjects sub
        JOIN groups g ON sub.direction_id = g.direction_id
        JOIN students s ON g.id = s.group_id
        LEFT JOIN grades gr ON s.id = gr.student_id AND sub.id = gr.subject_id
        GROUP BY sub.name
        ORDER BY sub.name;
    """
    execute_query(conn, query)


def query_12(conn):
    """Определить среднюю оценку по предметам (для сдавших)."""
    print("\n📋 Запрос 12: Средняя оценка по предметам")
    query = """
        SELECT sub.name AS "Предмет",
               ROUND(AVG(gr.grade)::NUMERIC, 2) AS "Средняя оценка"
        FROM subjects sub
        JOIN grades gr ON sub.id = gr.subject_id
        WHERE gr.grade > 2
        GROUP BY sub.name
        ORDER BY AVG(gr.grade) DESC;
    """
    execute_query(conn, query)


def query_13(conn):
    """Определить группу с максимальной средней оценкой."""
    print("\n📋 Запрос 13: Группа с максимальной средней оценкой")
    query = """
        SELECT g.name AS "Группа",
               d.name AS "Направление",
               ROUND(AVG(gr.grade)::NUMERIC, 2) AS "Средняя оценка"
        FROM groups g
        JOIN directions d ON g.direction_id = d.id
        JOIN students s ON g.id = s.group_id
        LEFT JOIN grades gr ON s.id = gr.student_id
        GROUP BY g.name, d.name
        ORDER BY AVG(gr.grade) DESC
        LIMIT 1;
    """
    execute_query(conn, query)


def query_14(conn):
    """Отличник: по ВСЕМ предметам направления оценка = 5 (нет пропуска / несданных)."""
    print("\n📋 Запрос 14: Студенты-отличники")
    print("   (все предметы направления сданы на 5; нет оценки или не 5 → не отличник)")
    query = """
        WITH needed AS (
            SELECT s.id AS student_id,
                   s.last_name, s.first_name, s.middle_name,
                   g.name AS group_name,
                   sub.id AS subject_id
              FROM students s
              JOIN groups g ON g.id = s.group_id
              JOIN subjects sub ON sub.direction_id = g.direction_id
        ),
        per_student AS (
            SELECT n.student_id,
                   n.last_name, n.first_name, n.middle_name, n.group_name,
                   COUNT(*) AS subjects_needed,
                   COUNT(gr.id) AS subjects_graded,
                   COUNT(*) FILTER (WHERE gr.grade = 5) AS subjects_five,
                   COUNT(*) FILTER (WHERE gr.grade IS NULL OR gr.grade IS DISTINCT FROM 5)
                       AS not_excellent
              FROM needed n
              LEFT JOIN grades gr
                ON gr.student_id = n.student_id
               AND gr.subject_id = n.subject_id
             GROUP BY n.student_id, n.last_name, n.first_name, n.middle_name, n.group_name
        )
        SELECT last_name || ' ' || first_name || ' ' || COALESCE(middle_name, '') AS "ФИО",
               group_name AS "Группа",
               subjects_needed AS "Предметов направления",
               subjects_five AS "Сдано на 5"
          FROM per_student
         WHERE subjects_needed > 0
           AND subjects_graded = subjects_needed
           AND not_excellent = 0
         ORDER BY last_name, first_name;
    """
    execute_query(conn, query)


def query_15(conn):
    """Вывести кандидатов на отчисление."""
    print("\n📋 Запрос 15: Кандидаты на отчисление")
    query = """
        SELECT s.last_name || ' ' || s.first_name || ' ' || s.middle_name AS "ФИО",
               g.name AS "Группа",
               COUNT(CASE WHEN gr.grade IS NULL OR gr.grade = 2 THEN 1 END) AS "Несданных предметов"
        FROM students s
        JOIN groups g ON s.group_id = g.id
        LEFT JOIN grades gr ON s.id = gr.student_id
        GROUP BY s.id, s.last_name, s.first_name, s.middle_name, g.name
        HAVING COUNT(CASE WHEN gr.grade IS NULL OR gr.grade = 2 THEN 1 END) >= 2
        ORDER BY COUNT(CASE WHEN gr.grade IS NULL OR gr.grade = 2 THEN 1 END) DESC;
    """
    execute_query(conn, query)


# ============================================
# ЗАПРОСЫ БЛОКА 3: ПОСЕЩАЕМОСТЬ
# ============================================

def query_16(conn):
    """Вывести количество посещенных занятий по предмету."""
    print("\n📋 Запрос 16: Количество посещенных занятий по предмету")
    subject = input("Введите название предмета (например, Архитектура ЭВМ): ").strip()
    query = """
        SELECT sub.name AS "Предмет",
               COUNT(CASE WHEN a.is_present = TRUE THEN 1 END) AS "Посещено"
        FROM subjects sub
        LEFT JOIN attendance a ON sub.id = a.subject_id
        WHERE sub.name = %s
        GROUP BY sub.name;
    """
    execute_query(conn, query, (subject,), inputs={"предмет": subject})


def query_17(conn):
    """Вывести количество пропущенных занятий по предмету."""
    print("\n📋 Запрос 17: Количество пропущенных занятий по предмету")
    subject = input("Введите название предмета (например, Архитектура ЭВМ): ").strip()
    query = """
        SELECT sub.name AS "Предмет",
               COUNT(CASE WHEN a.is_present = FALSE THEN 1 END) AS "Пропущено"
        FROM subjects sub
        LEFT JOIN attendance a ON sub.id = a.subject_id
        WHERE sub.name = %s
        GROUP BY sub.name;
    """
    execute_query(conn, query, (subject,), inputs={"предмет": subject})


def query_18(conn):
    """Вывести количество студентов на каждом занятии у преподавателя."""
    print("\n📋 Запрос 18: Студенты на занятиях у преподавателя")
    teacher = input("Введите фамилию преподавателя (например, Смирнов): ").strip()
    query = """
        SELECT t.last_name || ' ' || t.first_name || ' ' || t.middle_name AS "Преподаватель",
               sub.name AS "Предмет",
               a.date AS "Дата",
               ts.pair_number AS "Номер пары",
               ts.start_time AS "Начало",
               ts.end_time AS "Конец",
               COUNT(CASE WHEN a.is_present = TRUE THEN 1 END) AS "Студентов присутствовало"
        FROM teachers t
        JOIN attendance a ON t.id = a.teacher_id
        JOIN subjects sub ON a.subject_id = sub.id
        JOIN time_slots ts ON a.time_slot_id = ts.id
        WHERE t.last_name = %s
        GROUP BY t.last_name, t.first_name, t.middle_name, sub.name, a.date,
                 ts.pair_number, ts.start_time, ts.end_time
        ORDER BY a.date, ts.pair_number;
    """
    execute_query(conn, query, (teacher,), inputs={"фамилия преподавателя": teacher})


def query_19(conn):
    """Время изучения предмета: длительность пары из time_slots (не фиксированные 1.5 ч)."""
    print("\n📋 Запрос 19: Время, потраченное на изучение предмета")
    print("   (сумма реальных длительностей пар из time_slots.start_time/end_time)")
    query = """
        SELECT s.last_name || ' ' || s.first_name || ' ' || s.middle_name AS "ФИО",
               sub.name AS "Предмет",
               ROUND(
                   SUM(
                       CASE WHEN a.is_present THEN
                           EXTRACT(EPOCH FROM (ts.end_time - ts.start_time)) / 3600.0
                       ELSE 0 END
                   )::numeric,
                   2
               ) AS "Часов изучено"
        FROM students s
        JOIN attendance a ON s.id = a.student_id
        JOIN subjects sub ON a.subject_id = sub.id
        JOIN time_slots ts ON a.time_slot_id = ts.id
        GROUP BY s.id, s.last_name, s.first_name, s.middle_name, sub.name
        ORDER BY s.last_name, sub.name;
    """
    execute_query(conn, query)


def query_20(conn):
    """Справочник пар: время начала и конца (длительность может отличаться)."""
    print("\n📋 Запрос 20: Расписание пар (time_slots)")
    query = """
        SELECT pair_number AS "Пара",
               start_time AS "Начало",
               end_time AS "Конец",
               ROUND(
                   (EXTRACT(EPOCH FROM (end_time - start_time)) / 3600.0)::numeric,
                   2
               ) AS "Часов"
        FROM time_slots
        ORDER BY pair_number;
    """
    execute_query(conn, query)


def query_21(conn):
    """Журнал посещений: дата + предмет + преподаватель + пара."""
    print("\n📋 Запрос 21: Посещённые занятия (дата, предмет, преподаватель, пара)")
    query = """
        SELECT a.date AS "Дата",
               s.last_name || ' ' || s.first_name AS "Студент",
               sub.name AS "Предмет",
               t.last_name || ' ' || t.first_name AS "Преподаватель",
               ts.pair_number AS "Пара",
               ts.start_time AS "Начало",
               ts.end_time AS "Конец",
               CASE WHEN a.is_present THEN 'был' ELSE 'не был' END AS "Статус"
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        JOIN subjects sub ON sub.id = a.subject_id
        JOIN teachers t ON t.id = a.teacher_id
        JOIN time_slots ts ON ts.id = a.time_slot_id
        ORDER BY a.date, ts.pair_number, s.last_name
        LIMIT 40;
    """
    execute_query(conn, query)


# ============================================
# МЕНЮ И ГЛАВНАЯ ФУНКЦИЯ
# ============================================

MENU = {
    "1": ("Списки групп по направлению", query_1),
    "2": ("Студенты по первой букве фамилии", query_2),
    "3": ("Список студентов для поздравления по месяцам", query_3),
    "4": ("Студенты с указанием возраста", query_4),
    "5": ("Студенты с ДР в текущем месяце", query_5),
    "6": ("Количество студентов по направлениям", query_6),
    "7": ("Бюджетные/внебюджетные места по группам", query_7),
    "8": ("Группы по предметам с преподавателем", query_8),
    "9": ("Дисциплина с макс. количеством студентов", query_9),
    "10": ("Количество студентов у преподавателя", query_10),
    "11": ("Доля сдавших студентов по дисциплинам", query_11),
    "12": ("Средняя оценка по предметам", query_12),
    "13": ("Группа с максимальной средней оценкой", query_13),
    "14": ("Студенты-отличники (все предметы на 5)", query_14),
    "15": ("Кандидаты на отчисление", query_15),
    "16": ("Посещенные занятия по предмету", query_16),
    "17": ("Пропущенные занятия по предмету", query_17),
    "18": ("Студенты на занятиях у преподавателя", query_18),
    "19": ("Время на изучение предмета (из длительности пар)", query_19),
    "20": ("Расписание пар (начало/конец, разная длина)", query_20),
    "21": ("Журнал посещений (дата+предмет+преподаватель+пара)", query_21),
    "0": ("Выход", None),
}


def print_menu():
    """Вывод меню."""
    print("\n" + "=" * 60)
    print(" ДЕМОНСТРАЦИОННЫЙ КЛИЕНТ — ЗАДАНИЕ 1 (PostgreSQL)")
    print("=" * 60)
    print("\n📌 БЛОК 1: СТУДЕНТЫ")
    for key in ["1", "2", "3", "4", "5", "6", "7"]:
        print(f"  [{key}] {MENU[key][0]}")
    print("\n📌 БЛОК 2: ПРЕДМЕТЫ И ОЦЕНКИ")
    for key in ["8", "9", "10", "11", "12", "13", "14", "15"]:
        print(f"  [{key}] {MENU[key][0]}")
    print("\n📌 БЛОК 3: ПОСЕЩАЕМОСТЬ")
    for key in ["16", "17", "18", "19", "20", "21"]:
        print(f"  [{key}] {MENU[key][0]}")
    print("\n  [0] Выход")
    print("=" * 60)


def main():
    """Главная функция."""
    conn = get_connection()
    if not conn:
        print("Не удалось подключиться к базе данных. Завершение работы.")
        return

    print("\n✅ Подключение к базе данных установлено!")
    print("   Каждый пункт показывает: ВВЕЛИ → SQL → ОТВЕТ БД")

    while True:
        print_menu()
        choice = input("\n Выберите номер запроса: ").strip()

        if choice == "0":
            print("\n👋 До свидания!")
            break

        if choice in MENU and MENU[choice][1]:
            print("\n" + "─" * 60)
            MENU[choice][1](conn)
            print("─" * 60)
            input("\nНажмите Enter для продолжения...")
        else:
            print("\n️  Неверный выбор. Попробуйте снова.")

    conn.close()


if __name__ == "__main__":
    main()
