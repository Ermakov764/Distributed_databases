-- =============================================================================
-- Задание 3: все демо-SQL для защиты (вводить в psql по очереди)
-- Запуск файла целиком:
--   export PGPASSWORD=1
--   psql -h 192.168.122.59 -U db1_user -d university_db -f sql/05_all_demo_queries.sql
-- Или открыть psql и копировать блоки по одному.
-- =============================================================================

\echo '========== ФУНКЦИИ =========='

\echo '--- 1. Средняя оценка: предмет + группа ---'
SELECT fn_avg_grade_subject_group('Архитектура ЭВМ', 'ИВТ-101') AS avg_grade;

\echo '--- 2. Средняя оценка: предмет + направление ---'
SELECT fn_avg_grade_subject_direction(
  'Архитектура ЭВМ',
  'Информатика и вычислительная техника'
) AS avg_grade;

\echo '--- 3. Число отличников в группе ---'
SELECT fn_count_excellent_in_group('ИВТ-101') AS excellent_cnt;

\echo '--- 4. Есть ли несданные у студента ---'
SELECT s.id,
       s.last_name || ' ' || s.first_name AS fio,
       fn_has_failed_exams(s.id) AS has_failed
  FROM students s
 ORDER BY s.id
 LIMIT 12;

\echo '--- 5. Пропуски по студентам ---'
SELECT * FROM fn_absences_by_student() LIMIT 20;

\echo '--- 6. Пропуски по группам ---'
SELECT * FROM fn_absences_by_group();

\echo '--- 7. Пропуски по направлениям ---'
SELECT * FROM fn_absences_by_direction();

\echo '--- 8. Пропуски по преподавателям ---'
SELECT * FROM fn_absences_by_teacher();

\echo '========== ТРИГГЕРЫ =========='

\echo '--- T1: оценка 7 (ожидается ERROR) ---'
BEGIN;
UPDATE grades SET grade = 7
 WHERE student_id = (SELECT student_id FROM grades LIMIT 1)
   AND subject_id = (SELECT subject_id FROM grades LIMIT 1);
-- если ERROR — триггер сработал; откат:
ROLLBACK;

\echo '--- T2: чужой преподаватель (ожидается ERROR) ---'
BEGIN;
UPDATE grades g
   SET set_by_teacher_id = (
         SELECT t.id FROM teachers t
          WHERE NOT EXISTS (
            SELECT 1 FROM teacher_subjects ts
             WHERE ts.teacher_id = t.id AND ts.subject_id = g.subject_id
          )
          LIMIT 1
       )
 WHERE ctid = (SELECT ctid FROM grades WHERE grade IS NOT NULL LIMIT 1);
ROLLBACK;

\echo '--- T3/T4/T5: таблицы средних (кэш) ---'
SELECT g.name AS group_name, sub.name AS subject, a.avg_grade
  FROM avg_group_subject a
  JOIN groups g ON g.id = a.group_id
  JOIN subjects sub ON sub.id = a.subject_id
 ORDER BY a.updated_at DESC NULLS LAST
 LIMIT 10;

SELECT g.name AS group_name, a.avg_grade
  FROM avg_group_all a
  JOIN groups g ON g.id = a.group_id
 ORDER BY g.name
 LIMIT 10;

SELECT sub.name AS subject, a.avg_grade
  FROM avg_subject a
  JOIN subjects sub ON sub.id = a.subject_id
 ORDER BY sub.name
 LIMIT 10;

\echo '========== ДОП. ПАРАМЕТРЫ =========='

\echo '--- defs по специальностям ---'
SELECT d.name AS direction, e.param_name, e.param_type, e.description
  FROM extra_param_defs e
  JOIN directions d ON d.id = e.direction_id
 ORDER BY d.name, e.param_type, e.param_name;

\echo '--- numeric avg/sum ---'
SELECT * FROM fn_numeric_param_stats('ИВТ-101', 'рейтинг_балл');

\echo '--- текстовый поиск (строки) ---'
SELECT student_id, full_name, group_name, param_name, found_value
  FROM fn_search_text_param('Python')
 LIMIT 15;

\echo '--- текстовый поиск (JSONB map) ---'
SELECT fn_search_text_param_map('Python') AS assoc_map;

\echo '========== ГОТОВО =========='
