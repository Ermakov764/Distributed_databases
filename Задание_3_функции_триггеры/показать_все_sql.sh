#!/usr/bin/env bash
# =============================================================================
# Задание 3 — ВСЕ SQL из ТЗ + вывод в терминале
# =============================================================================
# Запуск из папки задания (рабочей или из пакета сдачи):
#
#   cd …/3_task
#   # или: cd …/К_сдаче_преподавателю/Задание_3_функции_триггеры
#   export PGPASSWORD=1
#   bash показать_все_sql.sh
#
# Хост БД по умолчанию 192.168.122.59 (учебная ВМ).
# Другой хост:  export PGHOST=127.0.0.1
# =============================================================================

set -u
export PGPASSWORD="${PGPASSWORD:-1}"
export PAGER=cat
export LESS='-F -X'
HOST="${PGHOST:-192.168.122.59}"
USER_DB="${PGUSER:-db1_user}"
DB="${PGDATABASE:-university_db}"

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
echo " ЗАДАНИЕ 3 · все запросы SQL и вывод PostgreSQL"
echo " Хост: $HOST  БД: $DB  user: $USER_DB"
echo "====================================================================="

echo
echo "0) Список функций и триггеров в БД"
psql_c "SELECT p.proname AS function FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'fn_%' ORDER BY 1;"
psql_c "SELECT tgname AS trigger, CASE WHEN tgtype & 2 = 2 THEN 'BEFORE' ELSE 'AFTER' END AS timing FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE NOT tgisinternal AND c.relname='grades' ORDER BY 1;"

echo
echo "====================================================================="
echo "1. ФУНКЦИИ: СРЕДНИЕ / ОТЛИЧНИКИ / НЕСДАННЫЕ"
echo "====================================================================="

psql_c "SELECT fn_avg_grade_subject_group('Архитектура ЭВМ', 'ИВТ-101') AS avg_grade;"
psql_c "SELECT fn_avg_grade_subject_direction('Архитектура ЭВМ', 'Информатика и вычислительная техника') AS avg_grade;"
psql_c "SELECT fn_count_excellent_in_group('ИВТ-101') AS excellent_cnt;"
psql_c "SELECT id, last_name, first_name, fn_has_failed_exams(id) AS has_failed FROM students ORDER BY id LIMIT 12;"

echo
echo "====================================================================="
echo "2. ФУНКЦИИ: ПРОПУСКИ"
echo "====================================================================="

psql_c "SELECT * FROM fn_absences_by_student() LIMIT 20;"
psql_c "SELECT * FROM fn_absences_by_group();"
psql_c "SELECT * FROM fn_absences_by_direction();"
psql_c "SELECT * FROM fn_absences_by_teacher();"

echo
echo "====================================================================="
echo "3. ТРИГГЕРЫ T1 и T2 (ожидается ERROR — так видно, что триггер сработал)"
echo "====================================================================="

psql_c "UPDATE grades SET grade = 7 WHERE student_id = (SELECT student_id FROM grades LIMIT 1) AND subject_id = (SELECT subject_id FROM grades LIMIT 1);"

# Чужой, но СУЩЕСТВУЮЩИЙ преподаватель (не FK-ошибка, а именно T2)
psql_c "UPDATE grades g SET set_by_teacher_id = (SELECT t.id FROM teachers t WHERE NOT EXISTS (SELECT 1 FROM teacher_subjects ts WHERE ts.teacher_id=t.id AND ts.subject_id=g.subject_id) LIMIT 1) WHERE ctid = (SELECT ctid FROM grades WHERE grade IS NOT NULL LIMIT 1);"

echo
echo "====================================================================="
echo "4. ТРИГГЕРЫ T3 / T4 / T5 — таблицы средних avg_*"
echo "====================================================================="

psql_c "SELECT g.name AS group_name, sub.name AS subject, a.avg_grade FROM avg_group_subject a JOIN groups g ON g.id=a.group_id JOIN subjects sub ON sub.id=a.subject_id ORDER BY g.name, sub.name LIMIT 10;"
psql_c "SELECT g.name AS group_name, a.avg_grade FROM avg_group_all a JOIN groups g ON g.id=a.group_id ORDER BY g.name;"
psql_c "SELECT sub.name AS subject, a.avg_grade FROM avg_subject a JOIN subjects sub ON sub.id=a.subject_id ORDER BY sub.name;"

echo
echo "====================================================================="
echo "5. ДОП. ПАРАМЕТРЫ"
echo "====================================================================="

psql_c "SELECT d.name AS direction, e.param_name, e.param_type FROM extra_param_defs e JOIN directions d ON d.id=e.direction_id ORDER BY d.name, e.param_type, e.param_name;"

# Берём реальный numeric-параметр для ИВТ-101 (если рейтинг_балл нет — часы_практики и т.п.)
NUM_PARAM=$(psql -h "$HOST" -U "$USER_DB" -d "$DB" -Atc "SELECT e.param_name FROM extra_param_defs e JOIN directions d ON d.id=e.direction_id JOIN groups g ON g.direction_id=d.id WHERE g.name='ИВТ-101' AND e.param_type='numeric' ORDER BY e.id LIMIT 1;" 2>/dev/null || true)
NUM_PARAM="${NUM_PARAM:-рейтинг_балл}"
echo "(числовой параметр для демо: $NUM_PARAM)"
psql_c "SELECT * FROM fn_numeric_param_stats('ИВТ-101', '${NUM_PARAM}');"
psql_c "SELECT student_id, full_name, group_name, param_name, found_value FROM fn_search_text_param('Python') LIMIT 10;"
psql_c "SELECT fn_search_text_param_map('Python') AS assoc_map;"

echo
echo "====================================================================="
echo " ГОТОВО: все SQL задания 3 показаны с выводом"
echo "====================================================================="
