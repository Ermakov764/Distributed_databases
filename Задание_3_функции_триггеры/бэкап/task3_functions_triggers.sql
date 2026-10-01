-- =============================================================================
-- Задание 3: хранимые функции, триггеры, доп. параметры групп
-- БД: university_db (PostgreSQL)
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- Служебные таблицы для триггеров (средние значения)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS avg_group_subject (
    group_id    INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    avg_grade   NUMERIC(5,2),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, subject_id)
);

CREATE TABLE IF NOT EXISTS avg_group_all (
    group_id    INTEGER PRIMARY KEY REFERENCES groups(id) ON DELETE CASCADE,
    avg_grade   NUMERIC(5,2),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS avg_subject (
    subject_id  INTEGER PRIMARY KEY REFERENCES subjects(id) ON DELETE CASCADE,
    avg_grade   NUMERIC(5,2),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Кто выставил оценку (для триггера проверки преподавателя)
ALTER TABLE grades
    ADD COLUMN IF NOT EXISTS set_by_teacher_id INTEGER REFERENCES teachers(id);

-- -----------------------------------------------------------------------------
-- 1. Средняя оценка по предмету для группы
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_avg_grade_subject_group(
    p_subject_name TEXT,
    p_group_name   TEXT
) RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_avg NUMERIC;
BEGIN
    SELECT ROUND(AVG(gr.grade)::NUMERIC, 2)
      INTO v_avg
      FROM grades gr
      JOIN students s ON s.id = gr.student_id
      JOIN groups g ON g.id = s.group_id
      JOIN subjects sub ON sub.id = gr.subject_id
     WHERE sub.name = p_subject_name
       AND g.name = p_group_name
       AND gr.grade IS NOT NULL;

    RETURN v_avg;
END;
$$;

-- -----------------------------------------------------------------------------
-- 2. Средняя оценка по предмету для направления
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_avg_grade_subject_direction(
    p_subject_name   TEXT,
    p_direction_name TEXT
) RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
DECLARE
    v_avg NUMERIC;
BEGIN
    SELECT ROUND(AVG(gr.grade)::NUMERIC, 2)
      INTO v_avg
      FROM grades gr
      JOIN students s ON s.id = gr.student_id
      JOIN groups g ON g.id = s.group_id
      JOIN directions d ON d.id = g.direction_id
      JOIN subjects sub ON sub.id = gr.subject_id
     WHERE sub.name = p_subject_name
       AND d.name = p_direction_name
       AND gr.grade IS NOT NULL;

    RETURN v_avg;
END;
$$;

-- -----------------------------------------------------------------------------
-- 3. Количество отличников в группе
--    (отсутствие оценки = неудовлетворительно)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_count_excellent_in_group(
    p_group_name TEXT
) RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_cnt INTEGER;
BEGIN
    -- Отличник: есть хотя бы одна оценка и все его оценки = 5,
    -- и по всем предметам направления группы есть оценка 5
    -- (нет оценки по нужному предмету ⇒ не отличник)
    WITH grp AS (
        SELECT g.id AS group_id, g.direction_id
          FROM groups g
         WHERE g.name = p_group_name
    ),
    needed AS (
        SELECT s.id AS student_id, sub.id AS subject_id
          FROM students s
          JOIN grp ON s.group_id = grp.group_id
          JOIN subjects sub ON sub.direction_id = grp.direction_id
    ),
    per_student AS (
        SELECT n.student_id,
               BOOL_AND(gr.grade = 5) AS all_five,
               COUNT(gr.id) AS graded_cnt,
               COUNT(*) AS needed_cnt
          FROM needed n
          LEFT JOIN grades gr
            ON gr.student_id = n.student_id
           AND gr.subject_id = n.subject_id
         GROUP BY n.student_id
    )
    SELECT COUNT(*)::INTEGER
      INTO v_cnt
      FROM per_student
     WHERE all_five
       AND graded_cnt = needed_cnt
       AND needed_cnt > 0;

    RETURN COALESCE(v_cnt, 0);
END;
$$;

-- -----------------------------------------------------------------------------
-- 4. Логическая: есть ли несданные экзамены (2 или NULL по предмету направления)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_has_failed_exams(
    p_student_id INTEGER
) RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_fail BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
          FROM students s
          JOIN groups g ON g.id = s.group_id
          JOIN subjects sub ON sub.direction_id = g.direction_id
          LEFT JOIN grades gr
            ON gr.student_id = s.id
           AND gr.subject_id = sub.id
         WHERE s.id = p_student_id
           AND (gr.grade IS NULL OR gr.grade = 2 OR gr.id IS NULL)
    ) INTO v_fail;

    RETURN COALESCE(v_fail, FALSE);
END;
$$;

-- Удобная обёртка по ФИО
CREATE OR REPLACE FUNCTION fn_has_failed_exams_by_name(
    p_last_name  TEXT,
    p_first_name TEXT DEFAULT NULL
) RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    SELECT id INTO v_id
      FROM students
     WHERE last_name = p_last_name
       AND (p_first_name IS NULL OR first_name = p_first_name)
     ORDER BY id
     LIMIT 1;

    IF v_id IS NULL THEN
        RAISE EXCEPTION 'Студент не найден: % %', p_last_name, COALESCE(p_first_name, '');
    END IF;

    RETURN fn_has_failed_exams(v_id);
END;
$$;

-- -----------------------------------------------------------------------------
-- 5. Пропуски по каждому студенту
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_absences_by_student()
RETURNS TABLE(
    student_id INTEGER,
    full_name  TEXT,
    group_name TEXT,
    absences   BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT s.id,
           s.last_name || ' ' || s.first_name || ' ' || COALESCE(s.middle_name, ''),
           g.name,
           COUNT(*) FILTER (WHERE a.is_present = FALSE)
      FROM students s
      JOIN groups g ON g.id = s.group_id
      LEFT JOIN attendance a ON a.student_id = s.id
     GROUP BY s.id, s.last_name, s.first_name, s.middle_name, g.name
     ORDER BY COUNT(*) FILTER (WHERE a.is_present = FALSE) DESC, s.last_name;
$$;

-- -----------------------------------------------------------------------------
-- 6. Пропуски по каждой группе
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_absences_by_group()
RETURNS TABLE(
    group_id   INTEGER,
    group_name TEXT,
    absences   BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT g.id,
           g.name,
           COUNT(*) FILTER (WHERE a.is_present = FALSE)
      FROM groups g
      LEFT JOIN students s ON s.group_id = g.id
      LEFT JOIN attendance a ON a.student_id = s.id
     GROUP BY g.id, g.name
     ORDER BY g.name;
$$;

-- -----------------------------------------------------------------------------
-- 7. Пропуски по каждому направлению
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_absences_by_direction()
RETURNS TABLE(
    direction_id   INTEGER,
    direction_name TEXT,
    absences       BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT d.id,
           d.name,
           COUNT(*) FILTER (WHERE a.is_present = FALSE)
      FROM directions d
      LEFT JOIN groups g ON g.direction_id = d.id
      LEFT JOIN students s ON s.group_id = g.id
      LEFT JOIN attendance a ON a.student_id = s.id
     GROUP BY d.id, d.name
     ORDER BY d.name;
$$;

-- -----------------------------------------------------------------------------
-- 8. Пропуски по каждому преподавателю
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_absences_by_teacher()
RETURNS TABLE(
    teacher_id INTEGER,
    full_name  TEXT,
    absences   BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT t.id,
           t.last_name || ' ' || t.first_name || ' ' || COALESCE(t.middle_name, ''),
           COUNT(*) FILTER (WHERE a.is_present = FALSE)
      FROM teachers t
      LEFT JOIN attendance a ON a.teacher_id = t.id
     GROUP BY t.id, t.last_name, t.first_name, t.middle_name
     ORDER BY COUNT(*) FILTER (WHERE a.is_present = FALSE) DESC;
$$;

-- =============================================================================
-- ТРИГГЕРЫ
-- =============================================================================

-- -----------------------------------------------------------------------------
-- T1. Корректность оценки: только 2,3,4,5 (NULL допускается как «нет оценки»)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_fn_check_grade_value()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.grade IS NOT NULL AND NEW.grade NOT IN (2, 3, 4, 5) THEN
        RAISE EXCEPTION 'Недопустимая оценка: %. Допустимы 2, 3, 4, 5 или NULL', NEW.grade;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_check_grade_value ON grades;
CREATE TRIGGER trg_check_grade_value
    BEFORE INSERT OR UPDATE OF grade ON grades
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_check_grade_value();

-- -----------------------------------------------------------------------------
-- T2. Оценку может выставлять только преподаватель, назначенный на предмет,
--     и предмет должен относиться к направлению группы студента
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_fn_check_grade_teacher()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_dir_subj INTEGER;
    v_dir_stud INTEGER;
BEGIN
    -- Если преподаватель не указан — пропускаем (старые записи);
    -- при явной установке set_by_teacher_id — проверяем
    IF NEW.set_by_teacher_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM teacher_subjects ts
         WHERE ts.teacher_id = NEW.set_by_teacher_id
           AND ts.subject_id = NEW.subject_id
    ) THEN
        RAISE EXCEPTION
            'Преподаватель id=% не назначен на предмет id=%',
            NEW.set_by_teacher_id, NEW.subject_id;
    END IF;

    SELECT direction_id INTO v_dir_subj FROM subjects WHERE id = NEW.subject_id;
    SELECT g.direction_id INTO v_dir_stud
      FROM students s
      JOIN groups g ON g.id = s.group_id
     WHERE s.id = NEW.student_id;

    IF v_dir_subj IS DISTINCT FROM v_dir_stud THEN
        RAISE EXCEPTION
            'Предмет не относится к направлению группы студента (subj_dir=%, stud_dir=%)',
            v_dir_subj, v_dir_stud;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_check_grade_teacher ON grades;
CREATE TRIGGER trg_check_grade_teacher
    BEFORE INSERT OR UPDATE ON grades
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_check_grade_teacher();

-- -----------------------------------------------------------------------------
-- T3 / T4 / T5 — отдельные AFTER-триггеры (как в ТЗ: три разных триггера)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_fn_avg_group_subject()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_student_id INTEGER;
    v_subject_id INTEGER;
    v_group_id   INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_student_id := OLD.student_id;
        v_subject_id := OLD.subject_id;
    ELSE
        v_student_id := NEW.student_id;
        v_subject_id := NEW.subject_id;
    END IF;

    SELECT group_id INTO v_group_id FROM students WHERE id = v_student_id;

    INSERT INTO avg_group_subject (group_id, subject_id, avg_grade, updated_at)
    SELECT v_group_id,
           v_subject_id,
           ROUND(AVG(gr.grade)::NUMERIC, 2),
           NOW()
      FROM grades gr
      JOIN students s ON s.id = gr.student_id
     WHERE s.group_id = v_group_id
       AND gr.subject_id = v_subject_id
       AND gr.grade IS NOT NULL
    ON CONFLICT (group_id, subject_id) DO UPDATE
       SET avg_grade = EXCLUDED.avg_grade,
           updated_at = NOW();

    IF NOT EXISTS (
        SELECT 1 FROM grades gr
          JOIN students s ON s.id = gr.student_id
         WHERE s.group_id = v_group_id
           AND gr.subject_id = v_subject_id
           AND gr.grade IS NOT NULL
    ) THEN
        INSERT INTO avg_group_subject (group_id, subject_id, avg_grade, updated_at)
        VALUES (v_group_id, v_subject_id, NULL, NOW())
        ON CONFLICT (group_id, subject_id) DO UPDATE
           SET avg_grade = NULL, updated_at = NOW();
    END IF;

    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_avg_group_all()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_student_id INTEGER;
    v_group_id   INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_student_id := OLD.student_id;
    ELSE
        v_student_id := NEW.student_id;
    END IF;

    SELECT group_id INTO v_group_id FROM students WHERE id = v_student_id;

    INSERT INTO avg_group_all (group_id, avg_grade, updated_at)
    SELECT v_group_id,
           ROUND(AVG(gr.grade)::NUMERIC, 2),
           NOW()
      FROM grades gr
      JOIN students s ON s.id = gr.student_id
     WHERE s.group_id = v_group_id
       AND gr.grade IS NOT NULL
    ON CONFLICT (group_id) DO UPDATE
       SET avg_grade = EXCLUDED.avg_grade,
           updated_at = NOW();

    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION trg_fn_avg_subject()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_subject_id INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_subject_id := OLD.subject_id;
    ELSE
        v_subject_id := NEW.subject_id;
    END IF;

    INSERT INTO avg_subject (subject_id, avg_grade, updated_at)
    SELECT v_subject_id,
           ROUND(AVG(grade)::NUMERIC, 2),
           NOW()
      FROM grades
     WHERE subject_id = v_subject_id
       AND grade IS NOT NULL
    ON CONFLICT (subject_id) DO UPDATE
       SET avg_grade = EXCLUDED.avg_grade,
           updated_at = NOW();

    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;

-- убрать старый «объединённый» триггер, если был
DROP TRIGGER IF EXISTS trg_recalc_averages ON grades;
DROP FUNCTION IF EXISTS trg_fn_recalc_averages();

DROP TRIGGER IF EXISTS trg_avg_group_subject ON grades;
CREATE TRIGGER trg_avg_group_subject
    AFTER INSERT OR UPDATE OR DELETE ON grades
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_avg_group_subject();

DROP TRIGGER IF EXISTS trg_avg_group_all ON grades;
CREATE TRIGGER trg_avg_group_all
    AFTER INSERT OR UPDATE OR DELETE ON grades
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_avg_group_all();

DROP TRIGGER IF EXISTS trg_avg_subject ON grades;
CREATE TRIGGER trg_avg_subject
    AFTER INSERT OR UPDATE OR DELETE ON grades
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_avg_subject();

-- =============================================================================
-- ДОП. ПАРАМЕТРЫ ГРУПП / СПЕЦИАЛЬНОСТЕЙ
-- =============================================================================

CREATE TABLE IF NOT EXISTS extra_param_defs (
    id            SERIAL PRIMARY KEY,
    direction_id  INTEGER NOT NULL REFERENCES directions(id) ON DELETE CASCADE,
    param_name    VARCHAR(100) NOT NULL,
    param_type    VARCHAR(20) NOT NULL CHECK (param_type IN ('numeric', 'text')),
    description   TEXT,
    UNIQUE (direction_id, param_name)
);

CREATE TABLE IF NOT EXISTS student_extra_params (
    id            SERIAL PRIMARY KEY,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    param_def_id  INTEGER NOT NULL REFERENCES extra_param_defs(id) ON DELETE CASCADE,
    num_value     NUMERIC,
    text_value    TEXT,
    UNIQUE (student_id, param_def_id),
    CONSTRAINT chk_param_value CHECK (
        (num_value IS NOT NULL AND text_value IS NULL)
        OR (num_value IS NULL AND text_value IS NOT NULL)
    )
);

-- Среднее и сумма числовых параметров (по группе и имени параметра)
CREATE OR REPLACE FUNCTION fn_numeric_param_stats(
    p_group_name TEXT,
    p_param_name TEXT
) RETURNS TABLE(
    param_name TEXT,
    group_name TEXT,
    avg_value  NUMERIC,
    sum_value  NUMERIC,
    cnt        BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT epd.param_name::TEXT,
           g.name::TEXT,
           ROUND(AVG(sep.num_value)::NUMERIC, 2),
           ROUND(SUM(sep.num_value)::NUMERIC, 2),
           COUNT(sep.id)
      FROM student_extra_params sep
      JOIN extra_param_defs epd ON epd.id = sep.param_def_id
      JOIN students s ON s.id = sep.student_id
      JOIN groups g ON g.id = s.group_id
     WHERE g.name = p_group_name
       AND epd.param_name = p_param_name
       AND epd.param_type = 'numeric'
     GROUP BY epd.param_name, g.name;
$$;

-- Текстовый поиск. Человек (student_id) необязателен.
-- Если student_id IS NULL → jsonb-объект { "student_id": "value", ... }
CREATE OR REPLACE FUNCTION fn_search_text_param(
    p_search_value TEXT,
    p_param_name   TEXT DEFAULT NULL,
    p_group_name   TEXT DEFAULT NULL,
    p_student_id   INTEGER DEFAULT NULL
) RETURNS TABLE(
    student_id   INTEGER,
    full_name    TEXT,
    group_name   TEXT,
    param_name   TEXT,
    found_value  TEXT,
    result_map   JSONB
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_map JSONB := '{}'::JSONB;
BEGIN
    -- Если человек не указан — собираем ассоциированный массив и возвращаем строки + map
    IF p_student_id IS NULL THEN
        SELECT COALESCE(jsonb_object_agg(sep.student_id::TEXT, sep.text_value), '{}'::JSONB)
          INTO v_map
          FROM student_extra_params sep
          JOIN extra_param_defs epd ON epd.id = sep.param_def_id
          JOIN students s ON s.id = sep.student_id
          JOIN groups g ON g.id = s.group_id
         WHERE epd.param_type = 'text'
           AND sep.text_value ILIKE '%' || p_search_value || '%'
           AND (p_param_name IS NULL OR epd.param_name = p_param_name)
           AND (p_group_name IS NULL OR g.name = p_group_name);

        RETURN QUERY
        SELECT s.id,
               (s.last_name || ' ' || s.first_name || ' ' || COALESCE(s.middle_name, ''))::TEXT,
               g.name::TEXT,
               epd.param_name::TEXT,
               sep.text_value::TEXT,
               v_map
          FROM student_extra_params sep
          JOIN extra_param_defs epd ON epd.id = sep.param_def_id
          JOIN students s ON s.id = sep.student_id
          JOIN groups g ON g.id = s.group_id
         WHERE epd.param_type = 'text'
           AND sep.text_value ILIKE '%' || p_search_value || '%'
           AND (p_param_name IS NULL OR epd.param_name = p_param_name)
           AND (p_group_name IS NULL OR g.name = p_group_name)
         ORDER BY g.name, s.last_name;
    ELSE
        RETURN QUERY
        SELECT s.id,
               (s.last_name || ' ' || s.first_name || ' ' || COALESCE(s.middle_name, ''))::TEXT,
               g.name::TEXT,
               epd.param_name::TEXT,
               sep.text_value::TEXT,
               jsonb_build_object(s.id::TEXT, sep.text_value)
          FROM student_extra_params sep
          JOIN extra_param_defs epd ON epd.id = sep.param_def_id
          JOIN students s ON s.id = sep.student_id
          JOIN groups g ON g.id = s.group_id
         WHERE epd.param_type = 'text'
           AND s.id = p_student_id
           AND sep.text_value ILIKE '%' || p_search_value || '%'
           AND (p_param_name IS NULL OR epd.param_name = p_param_name)
           AND (p_group_name IS NULL OR g.name = p_group_name)
         ORDER BY epd.param_name;
    END IF;
END;
$$;

-- Функция только ассоциативного массива (удобно для клиента)
CREATE OR REPLACE FUNCTION fn_search_text_param_map(
    p_search_value TEXT,
    p_param_name   TEXT DEFAULT NULL,
    p_group_name   TEXT DEFAULT NULL
) RETURNS JSONB
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(jsonb_object_agg(sep.student_id::TEXT, sep.text_value), '{}'::JSONB)
      FROM student_extra_params sep
      JOIN extra_param_defs epd ON epd.id = sep.param_def_id
      JOIN students s ON s.id = sep.student_id
      JOIN groups g ON g.id = s.group_id
     WHERE epd.param_type = 'text'
       AND sep.text_value ILIKE '%' || p_search_value || '%'
       AND (p_param_name IS NULL OR epd.param_name = p_param_name)
       AND (p_group_name IS NULL OR g.name = p_group_name);
$$;

COMMIT;

-- Начальный пересчёт средних по текущим данным
INSERT INTO avg_group_subject (group_id, subject_id, avg_grade, updated_at)
SELECT g.id, gr.subject_id, ROUND(AVG(gr.grade)::NUMERIC, 2), NOW()
  FROM grades gr
  JOIN students s ON s.id = gr.student_id
  JOIN groups g ON g.id = s.group_id
 WHERE gr.grade IS NOT NULL
 GROUP BY g.id, gr.subject_id
ON CONFLICT (group_id, subject_id) DO UPDATE
   SET avg_grade = EXCLUDED.avg_grade, updated_at = NOW();

INSERT INTO avg_group_all (group_id, avg_grade, updated_at)
SELECT g.id, ROUND(AVG(gr.grade)::NUMERIC, 2), NOW()
  FROM grades gr
  JOIN students s ON s.id = gr.student_id
  JOIN groups g ON g.id = s.group_id
 WHERE gr.grade IS NOT NULL
 GROUP BY g.id
ON CONFLICT (group_id) DO UPDATE
   SET avg_grade = EXCLUDED.avg_grade, updated_at = NOW();

INSERT INTO avg_subject (subject_id, avg_grade, updated_at)
SELECT subject_id, ROUND(AVG(grade)::NUMERIC, 2), NOW()
  FROM grades
 WHERE grade IS NOT NULL
 GROUP BY subject_id
ON CONFLICT (subject_id) DO UPDATE
   SET avg_grade = EXCLUDED.avg_grade, updated_at = NOW();
