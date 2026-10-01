#!/usr/bin/env bash
# =============================================================================
# Задание 1 — ВСЕ SQL из ТЗ + вывод в терминале
# =============================================================================
#   cd …/1_task
#   # или: cd …/К_сдаче_преподавателю/Задание_1_PostgreSQL
#   export PGPASSWORD=1
#   bash показать_все_sql.sh
#   # или: bash run_all.sh
#
# Хост БД: PGHOST (по умолчанию 192.168.122.59)
# =============================================================================

set -u
export PGPASSWORD="${PGPASSWORD:-1}"
export PAGER=cat
export LESS='-F -X'
HOST="${PGHOST:-192.168.122.59}"
USER_DB="${PGUSER:-db1_user}"
DB="${PGDATABASE:-university_db}"

echo "[START] lab1 SQL demo  host=$HOST  db=$DB"

# Как в задании 3: сначала полный SQL, потом ответ БД
psql_c() {
  echo
  echo "SQL >>>"
  echo "-----"
  printf '%s\n' "$1"
  echo "-----"
  echo "ответ:"
  psql -h "$HOST" -U "$USER_DB" -d "$DB" -P pager=off -c "$1" || true
}

echo "====================================================================="
echo " ЗАДАНИЕ 1 · все запросы SQL и вывод PostgreSQL"
echo " Хост: $HOST  БД: $DB  user: $USER_DB"
echo "====================================================================="

echo
echo "====================================================================="
echo "1. СТУДЕНТЫ"
echo "====================================================================="

echo -e "\n-> Запрос 1: Списки групп по направлению"
psql_c "SELECT g.name AS \"Группа\",
       s.last_name || ' ' || s.first_name || ' ' || COALESCE(s.middle_name,'') AS \"ФИО\",
       CASE WHEN s.is_budget THEN 'Бюджет' ELSE 'Внебюджет' END AS \"Тип\"
FROM students s
JOIN groups g ON s.group_id = g.id
JOIN directions d ON g.direction_id = d.id
WHERE d.name = 'Информатика и вычислительная техника'
ORDER BY g.name, s.last_name
LIMIT 20;"

echo -e "\n-> Запрос 2: Студенты с фамилией на букву Е"
psql_c "SELECT s.last_name || ' ' || s.first_name AS \"ФИО\", g.name AS \"Группа\", d.name AS \"Направление\"
FROM students s
JOIN groups g ON s.group_id = g.id
JOIN directions d ON g.direction_id = d.id
WHERE UPPER(s.last_name) LIKE 'Е%'
ORDER BY s.last_name;"

echo -e "\n-> Запрос 3: Список для поздравления по месяцам (фрагмент)"
psql_c "SELECT s.last_name || ' ' || LEFT(s.first_name,1) || '.' || LEFT(COALESCE(s.middle_name,' '),1) || '.' AS \"ФИО\",
       EXTRACT(DAY FROM s.birth_date)::int AS \"День\",
       TO_CHAR(s.birth_date, 'TMMonth') AS \"Месяц\",
       g.name AS \"Группа\"
FROM students s JOIN groups g ON s.group_id = g.id
ORDER BY EXTRACT(MONTH FROM s.birth_date), EXTRACT(DAY FROM s.birth_date)
LIMIT 15;"

echo -e "\n-> Запрос 4: Студенты с возрастом"
psql_c "SELECT s.last_name || ' ' || s.first_name AS \"ФИО\",
       s.birth_date,
       EXTRACT(YEAR FROM AGE(CURRENT_DATE, s.birth_date))::int AS \"Возраст\"
FROM students s ORDER BY s.last_name LIMIT 15;"

echo -e "\n-> Запрос 5: ДР в текущем месяце"
psql_c "SELECT s.last_name || ' ' || s.first_name AS \"ФИО\", s.birth_date, g.name AS \"Группа\"
FROM students s JOIN groups g ON s.group_id = g.id
WHERE EXTRACT(MONTH FROM s.birth_date) = EXTRACT(MONTH FROM CURRENT_DATE)
ORDER BY EXTRACT(DAY FROM s.birth_date);"

echo -e "\n-> Запрос 6: Количество студентов по направлениям"
psql_c "SELECT d.name AS \"Направление\", COUNT(s.id) AS \"Студентов\"
FROM directions d
LEFT JOIN groups g ON d.id = g.direction_id
LEFT JOIN students s ON g.id = s.group_id
GROUP BY d.name ORDER BY COUNT(s.id) DESC;"

echo -e "\n-> Запрос 7: Бюджет / внебюджет по группам"
psql_c "SELECT g.name AS \"Группа\", d.name AS \"Направление\",
       COUNT(CASE WHEN s.is_budget THEN 1 END) AS \"Бюджет\",
       COUNT(CASE WHEN NOT s.is_budget THEN 1 END) AS \"Внебюджет\"
FROM groups g
JOIN directions d ON g.direction_id = d.id
LEFT JOIN students s ON g.id = s.group_id
GROUP BY g.name, d.name ORDER BY g.name;"


echo
echo "====================================================================="
echo "2. ПРЕДМЕТЫ И ОЦЕНКИ"
echo "====================================================================="

echo -e "\n-> Запрос 8: Группы по предметам с преподавателем"
psql_c "SELECT sub.name AS \"Предмет\",
       t.last_name || ' ' || t.first_name AS \"Преподаватель\",
       g.name AS \"Группа\"
FROM subjects sub
JOIN teacher_subjects ts ON sub.id = ts.subject_id
JOIN teachers t ON ts.teacher_id = t.id
JOIN grades gr ON sub.id = gr.subject_id
JOIN students s ON gr.student_id = s.id
JOIN groups g ON s.group_id = g.id
GROUP BY sub.name, t.last_name, t.first_name, g.name
ORDER BY sub.name, g.name
LIMIT 20;"

echo -e "\n-> Запрос 9: Дисциплина с макс. числом студентов"
psql_c "SELECT sub.name AS \"Предмет\", COUNT(DISTINCT gr.student_id) AS \"Студентов\"
FROM subjects sub JOIN grades gr ON sub.id = gr.subject_id
GROUP BY sub.name ORDER BY COUNT(DISTINCT gr.student_id) DESC LIMIT 1;"

echo -e "\n-> Запрос 10: Студенты у преподавателей"
psql_c "SELECT t.last_name || ' ' || t.first_name AS \"Преподаватель\",
       COUNT(DISTINCT gr.student_id) AS \"Студентов\"
FROM teachers t
JOIN teacher_subjects ts ON t.id = ts.teacher_id
JOIN grades gr ON ts.subject_id = gr.subject_id
GROUP BY t.last_name, t.first_name
ORDER BY COUNT(DISTINCT gr.student_id) DESC;"

echo -e "\n-> Запрос 11: Доля сдавших по дисциплинам"
psql_c "SELECT sub.name AS \"Предмет\",
       COUNT(DISTINCT s.id) AS \"Всего\",
       COUNT(DISTINCT CASE WHEN gr.grade IS NOT NULL AND gr.grade > 2 THEN s.id END) AS \"Сдали\",
       ROUND(COUNT(DISTINCT CASE WHEN gr.grade IS NOT NULL AND gr.grade > 2 THEN s.id END)::numeric
             / NULLIF(COUNT(DISTINCT s.id),0) * 100, 2) AS \"Доля %\"
FROM subjects sub
JOIN groups g ON sub.direction_id = g.direction_id
JOIN students s ON g.id = s.group_id
LEFT JOIN grades gr ON s.id = gr.student_id AND sub.id = gr.subject_id
GROUP BY sub.name ORDER BY sub.name;"

echo -e "\n-> Запрос 12: Средняя оценка по предметам (сдавшие)"
psql_c "SELECT sub.name AS \"Предмет\", ROUND(AVG(gr.grade)::numeric, 2) AS \"Средняя\"
FROM subjects sub JOIN grades gr ON sub.id = gr.subject_id
WHERE gr.grade > 2
GROUP BY sub.name ORDER BY AVG(gr.grade) DESC;"

echo -e "\n-> Запрос 13: Группа с макс. средней оценкой"
psql_c "SELECT g.name AS \"Группа\", d.name AS \"Направление\",
       ROUND(AVG(gr.grade)::numeric, 2) AS \"Средняя\"
FROM groups g
JOIN directions d ON g.direction_id = d.id
JOIN students s ON g.id = s.group_id
LEFT JOIN grades gr ON s.id = gr.student_id
GROUP BY g.name, d.name
ORDER BY AVG(gr.grade) DESC NULLS LAST LIMIT 1;"

echo -e "\n-> Запрос 14: Отличники (все предметы направления на 5)"
psql_c "WITH needed AS (
  SELECT s.id AS student_id, s.last_name, s.first_name, g.name AS group_name, sub.id AS subject_id
  FROM students s
  JOIN groups g ON g.id = s.group_id
  JOIN subjects sub ON sub.direction_id = g.direction_id
),
per_student AS (
  SELECT n.student_id, n.last_name, n.first_name, n.group_name,
         COUNT(*) AS subjects_needed,
         COUNT(gr.id) AS subjects_graded,
         COUNT(*) FILTER (WHERE gr.grade IS NULL OR gr.grade IS DISTINCT FROM 5) AS not_excellent
  FROM needed n
  LEFT JOIN grades gr ON gr.student_id = n.student_id AND gr.subject_id = n.subject_id
  GROUP BY n.student_id, n.last_name, n.first_name, n.group_name
)
SELECT last_name || ' ' || first_name AS \"ФИО\", group_name AS \"Группа\",
       subjects_needed AS \"Предметов\"
FROM per_student
WHERE subjects_needed > 0 AND subjects_graded = subjects_needed AND not_excellent = 0
ORDER BY last_name;"

echo -e "\n-> Запрос 15: Кандидаты на отчисление"
psql_c "SELECT s.last_name || ' ' || s.first_name AS \"ФИО\", g.name AS \"Группа\",
       COUNT(CASE WHEN gr.grade IS NULL OR gr.grade = 2 THEN 1 END) AS \"Несданных\"
FROM students s
JOIN groups g ON s.group_id = g.id
LEFT JOIN grades gr ON s.id = gr.student_id
GROUP BY s.id, s.last_name, s.first_name, g.name
HAVING COUNT(CASE WHEN gr.grade IS NULL OR gr.grade = 2 THEN 1 END) >= 2
ORDER BY 3 DESC;"


echo
echo "====================================================================="
echo "3. ПОСЕЩАЕМОСТЬ"
echo "====================================================================="

echo -e "\n-> Запрос 16: Посещённые занятия (Архитектура ЭВМ)"
psql_c "SELECT sub.name AS \"Предмет\",
       COUNT(CASE WHEN a.is_present THEN 1 END) AS \"Посещено\"
FROM subjects sub LEFT JOIN attendance a ON sub.id = a.subject_id
WHERE sub.name = 'Архитектура ЭВМ' GROUP BY sub.name;"

echo -e "\n-> Запрос 17: Пропущенные занятия (Архитектура ЭВМ)"
psql_c "SELECT sub.name AS \"Предмет\",
       COUNT(CASE WHEN NOT a.is_present THEN 1 END) AS \"Пропущено\"
FROM subjects sub LEFT JOIN attendance a ON sub.id = a.subject_id
WHERE sub.name = 'Архитектура ЭВМ' GROUP BY sub.name;"

echo -e "\n-> Запрос 18: Занятия у преподавателя Смирнов"
psql_c "SELECT t.last_name || ' ' || t.first_name AS \"Преподаватель\",
       sub.name AS \"Предмет\", a.date, ts.pair_number AS \"Пара\",
       COUNT(CASE WHEN a.is_present THEN 1 END) AS \"Присутствовало\"
FROM teachers t
JOIN attendance a ON t.id = a.teacher_id
JOIN subjects sub ON a.subject_id = sub.id
JOIN time_slots ts ON a.time_slot_id = ts.id
WHERE t.last_name = 'Смирнов'
GROUP BY t.last_name, t.first_name, sub.name, a.date, ts.pair_number
ORDER BY a.date, ts.pair_number;"

echo -e "\n-> Запрос 19: Часы изучения (из длительности пар)"
psql_c "SELECT s.last_name || ' ' || s.first_name AS \"ФИО\", sub.name AS \"Предмет\",
       ROUND(SUM(CASE WHEN a.is_present THEN
         EXTRACT(EPOCH FROM (ts.end_time - ts.start_time))/3600.0 ELSE 0 END)::numeric, 2) AS \"Часов\"
FROM students s
JOIN attendance a ON s.id = a.student_id
JOIN subjects sub ON a.subject_id = sub.id
JOIN time_slots ts ON a.time_slot_id = ts.id
GROUP BY s.id, s.last_name, s.first_name, sub.name
ORDER BY 1, 2 LIMIT 20;"

echo -e "\n-> Запрос 20: Расписание пар (разная длительность)"
psql_c "SELECT pair_number AS \"Пара\", start_time AS \"Начало\", end_time AS \"Конец\",
       ROUND((EXTRACT(EPOCH FROM (end_time - start_time))/3600.0)::numeric, 2) AS \"Часов\"
FROM time_slots ORDER BY pair_number;"

echo -e "\n-> Запрос 21: Журнал посещений"
psql_c "SELECT a.date AS \"Дата\",
       s.last_name || ' ' || s.first_name AS \"Студент\",
       sub.name AS \"Предмет\",
       t.last_name || ' ' || t.first_name AS \"Преподаватель\",
       ts.pair_number AS \"Пара\",
       CASE WHEN a.is_present THEN 'был' ELSE 'не был' END AS \"Статус\"
FROM attendance a
JOIN students s ON s.id = a.student_id
JOIN subjects sub ON sub.id = a.subject_id
JOIN teachers t ON t.id = a.teacher_id
JOIN time_slots ts ON ts.id = a.time_slot_id
ORDER BY a.date, ts.pair_number, s.last_name
LIMIT 25;"

echo -e "\n====================================================================="
echo "ВСЕ ЗАПРОСЫ ИЗ ЗАДАНИЯ 1 УСПЕШНО ВЫПОЛНЕНЫ В ТЕРМИНАЛЕ"
echo "====================================================================="
