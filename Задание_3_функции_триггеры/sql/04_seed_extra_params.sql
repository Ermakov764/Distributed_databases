-- Демо-данные доп. параметров по специальностям (направлениям)
BEGIN;

DELETE FROM student_extra_params;
DELETE FROM extra_param_defs;

-- Определения параметров по направлениям
INSERT INTO extra_param_defs (direction_id, param_name, param_type, description)
SELECT d.id, v.param_name, v.param_type, v.description
  FROM directions d
  JOIN (VALUES
    ('Информатика и вычислительная техника', 'рейтинг_балл', 'numeric', 'Текущий рейтинг студента'),
    ('Информатика и вычислительная техника', 'часы_практики', 'numeric', 'Часы производственной практики'),
    ('Информатика и вычислительная техника', 'тема_проекта', 'text', 'Тема курсового проекта'),
    ('Информатика и вычислительная техника', 'язык_программирования', 'text', 'Основной язык'),

    ('Программная инженерия', 'рейтинг_балл', 'numeric', 'Текущий рейтинг'),
    ('Программная инженерия', 'закрытых_багов', 'numeric', 'Закрыто багов в трекере'),
    ('Программная инженерия', 'стек', 'text', 'Технологический стек'),
    ('Программная инженерия', 'роль_в_команде', 'text', 'Роль в учебном проекте'),

    ('Прикладная математика и информатика', 'рейтинг_балл', 'numeric', 'Рейтинг'),
    ('Прикладная математика и информатика', 'олимпиады', 'numeric', 'Число олимпиад'),
    ('Прикладная математика и информатика', 'научный_интерес', 'text', 'Научный интерес'),

    ('Информационная безопасность', 'рейтинг_балл', 'numeric', 'Рейтинг'),
    ('Информационная безопасность', 'ctf_очки', 'numeric', 'Очки CTF'),
    ('Информационная безопасность', 'сертификат', 'text', 'Сертификат/курс'),

    ('Системный анализ и управление', 'рейтинг_балл', 'numeric', 'Рейтинг'),
    ('Системный анализ и управление', 'kpi_балл', 'numeric', 'KPI учебного проекта'),
    ('Системный анализ и управление', 'кейс', 'text', 'Анализируемый кейс')
  ) AS v(direction_name, param_name, param_type, description)
    ON d.name = v.direction_name;

-- Заполнение значений для студентов (по направлению их группы)
INSERT INTO student_extra_params (student_id, param_def_id, num_value, text_value)
SELECT s.id,
       epd.id,
       CASE WHEN epd.param_type = 'numeric'
            THEN ROUND((50 + (s.id % 50) + (epd.id % 10))::NUMERIC, 2)
            ELSE NULL END,
       CASE WHEN epd.param_type = 'text' THEN
            CASE epd.param_name
                WHEN 'тема_проекта' THEN
                    (ARRAY['Система учёта','Мобильный клиент','Аналитика логов','IoT-шлюз','Чат-бот'])[1 + (s.id % 5)]
                WHEN 'язык_программирования' THEN
                    (ARRAY['Python','C++','Java','Go','Rust'])[1 + (s.id % 5)]
                WHEN 'стек' THEN
                    (ARRAY['Django+React','Spring','Node.js','Flutter','.NET'])[1 + (s.id % 5)]
                WHEN 'роль_в_команде' THEN
                    (ARRAY['backend','frontend','QA','DevOps','аналитик'])[1 + (s.id % 5)]
                WHEN 'научный_интерес' THEN
                    (ARRAY['ML','оптимизация','графы','численный анализ','статистика'])[1 + (s.id % 5)]
                WHEN 'сертификат' THEN
                    (ARRAY['OSCP prep','CompTIA Security+','Cisco CCNA','нет','CEH intro'])[1 + (s.id % 5)]
                WHEN 'кейс' THEN
                    (ARRAY['логистика','банк','медицина','энергетика','ритейл'])[1 + (s.id % 5)]
                ELSE 'значение_' || s.id::TEXT
            END
            ELSE NULL END
  FROM students s
  JOIN groups g ON g.id = s.group_id
  JOIN extra_param_defs epd ON epd.direction_id = g.direction_id;

COMMIT;

SELECT 'param_defs' AS t, COUNT(*) FROM extra_param_defs
UNION ALL
SELECT 'student_params', COUNT(*) FROM student_extra_params;
