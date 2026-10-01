--
-- PostgreSQL database dump
--

\restrict V6XBV7Ougc2rPlpWGl4DX085rPuDLqFVqIct57RrcAnbq2Fd8qScQnoYynHSTlE

-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgres_fdw; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;


--
-- Name: EXTENSION postgres_fdw; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION postgres_fdw IS 'foreign-data wrapper for remote PostgreSQL servers';


--
-- Name: fn_absences_by_direction(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_absences_by_direction() RETURNS TABLE(direction_id integer, direction_name text, absences bigint)
    LANGUAGE sql STABLE
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


--
-- Name: fn_absences_by_group(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_absences_by_group() RETURNS TABLE(group_id integer, group_name text, absences bigint)
    LANGUAGE sql STABLE
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


--
-- Name: fn_absences_by_student(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_absences_by_student() RETURNS TABLE(student_id integer, full_name text, group_name text, absences bigint)
    LANGUAGE sql STABLE
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


--
-- Name: fn_absences_by_teacher(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_absences_by_teacher() RETURNS TABLE(teacher_id integer, full_name text, absences bigint)
    LANGUAGE sql STABLE
    AS $$
    SELECT t.id,
           t.last_name || ' ' || t.first_name || ' ' || COALESCE(t.middle_name, ''),
           COUNT(*) FILTER (WHERE a.is_present = FALSE)
      FROM teachers t
      LEFT JOIN attendance a ON a.teacher_id = t.id
     GROUP BY t.id, t.last_name, t.first_name, t.middle_name
     ORDER BY COUNT(*) FILTER (WHERE a.is_present = FALSE) DESC;
$$;


--
-- Name: fn_avg_grade_subject_direction(text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_avg_grade_subject_direction(p_subject_name text, p_direction_name text) RETURNS numeric
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


--
-- Name: fn_avg_grade_subject_group(text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_avg_grade_subject_group(p_subject_name text, p_group_name text) RETURNS numeric
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


--
-- Name: fn_count_excellent_in_group(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_count_excellent_in_group(p_group_name text) RETURNS integer
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


--
-- Name: fn_has_failed_exams(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_has_failed_exams(p_student_id integer) RETURNS boolean
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


--
-- Name: fn_has_failed_exams_by_name(text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_has_failed_exams_by_name(p_last_name text, p_first_name text DEFAULT NULL::text) RETURNS boolean
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


--
-- Name: fn_numeric_param_stats(text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_numeric_param_stats(p_group_name text, p_param_name text) RETURNS TABLE(param_name text, group_name text, avg_value numeric, sum_value numeric, cnt bigint)
    LANGUAGE sql STABLE
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


--
-- Name: fn_search_text_param(text, text, text, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_search_text_param(p_search_value text, p_param_name text DEFAULT NULL::text, p_group_name text DEFAULT NULL::text, p_student_id integer DEFAULT NULL::integer) RETURNS TABLE(student_id integer, full_name text, group_name text, param_name text, found_value text, result_map jsonb)
    LANGUAGE plpgsql STABLE
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


--
-- Name: fn_search_text_param_map(text, text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_search_text_param_map(p_search_value text, p_param_name text DEFAULT NULL::text, p_group_name text DEFAULT NULL::text) RETURNS jsonb
    LANGUAGE sql STABLE
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


--
-- Name: trg_fn_avg_group_all(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_fn_avg_group_all() RETURNS trigger
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


--
-- Name: trg_fn_avg_group_subject(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_fn_avg_group_subject() RETURNS trigger
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


--
-- Name: trg_fn_avg_subject(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_fn_avg_subject() RETURNS trigger
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


--
-- Name: trg_fn_check_grade_teacher(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_fn_check_grade_teacher() RETURNS trigger
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


--
-- Name: trg_fn_check_grade_value(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_fn_check_grade_value() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.grade IS NOT NULL AND NEW.grade NOT IN (2, 3, 4, 5) THEN
        RAISE EXCEPTION 'Недопустимая оценка: %. Допустимы 2, 3, 4, 5 или NULL', NEW.grade;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: personal_server; Type: SERVER; Schema: -; Owner: -
--

CREATE SERVER personal_server FOREIGN DATA WRAPPER postgres_fdw OPTIONS (
    dbname 'university_db',
    host '192.168.122.60',
    port '5432'
);


--
-- Name: USER MAPPING db1_user SERVER personal_server; Type: USER MAPPING; Schema: -; Owner: -
--

CREATE USER MAPPING FOR db1_user SERVER personal_server;


--
-- Name: USER MAPPING postgres SERVER personal_server; Type: USER MAPPING; Schema: -; Owner: -
--

CREATE USER MAPPING FOR postgres SERVER personal_server;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: attendance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attendance (
    id integer NOT NULL,
    student_id integer NOT NULL,
    subject_id integer NOT NULL,
    teacher_id integer NOT NULL,
    date date NOT NULL,
    time_slot_id integer NOT NULL,
    is_present boolean DEFAULT true NOT NULL
);


--
-- Name: attendance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.attendance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: attendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.attendance_id_seq OWNED BY public.attendance.id;


--
-- Name: avg_group_all; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.avg_group_all (
    group_id integer NOT NULL,
    avg_grade numeric(5,2),
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: avg_group_subject; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.avg_group_subject (
    group_id integer NOT NULL,
    subject_id integer NOT NULL,
    avg_grade numeric(5,2),
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: avg_subject; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.avg_subject (
    subject_id integer NOT NULL,
    avg_grade numeric(5,2),
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: directions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.directions (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);


--
-- Name: directions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.directions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.directions_id_seq OWNED BY public.directions.id;


--
-- Name: extra_param_defs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extra_param_defs (
    id integer NOT NULL,
    direction_id integer NOT NULL,
    param_name character varying(100) NOT NULL,
    param_type character varying(20) NOT NULL,
    description text,
    CONSTRAINT extra_param_defs_param_type_check CHECK (((param_type)::text = ANY ((ARRAY['numeric'::character varying, 'text'::character varying])::text[])))
);


--
-- Name: extra_param_defs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.extra_param_defs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: extra_param_defs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.extra_param_defs_id_seq OWNED BY public.extra_param_defs.id;


--
-- Name: grades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grades (
    id integer NOT NULL,
    student_id integer NOT NULL,
    subject_id integer NOT NULL,
    grade integer,
    set_by_teacher_id integer,
    CONSTRAINT grades_grade_check CHECK ((grade = ANY (ARRAY[2, 3, 4, 5])))
);


--
-- Name: grades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grades_id_seq OWNED BY public.grades.id;


--
-- Name: groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.groups (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    direction_id integer NOT NULL
);


--
-- Name: groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.groups_id_seq OWNED BY public.groups.id;


--
-- Name: phones_personal; Type: FOREIGN TABLE; Schema: public; Owner: -
--

CREATE FOREIGN TABLE public.phones_personal (
    id integer,
    student_id integer,
    phone_number character varying(20)
)
SERVER personal_server
OPTIONS (
    schema_name 'public',
    table_name 'phones'
);


--
-- Name: student_extra_params; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_extra_params (
    id integer NOT NULL,
    student_id integer NOT NULL,
    param_def_id integer NOT NULL,
    num_value numeric,
    text_value text,
    CONSTRAINT chk_param_value CHECK ((((num_value IS NOT NULL) AND (text_value IS NULL)) OR ((num_value IS NULL) AND (text_value IS NOT NULL))))
);


--
-- Name: student_extra_params_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_extra_params_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_extra_params_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_extra_params_id_seq OWNED BY public.student_extra_params.id;


--
-- Name: students; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.students (
    id integer NOT NULL,
    last_name character varying(100),
    first_name character varying(100),
    middle_name character varying(100),
    birth_date date,
    city character varying(100),
    street character varying(100),
    house_number character varying(20),
    email character varying(100),
    group_id integer NOT NULL,
    is_budget boolean DEFAULT true NOT NULL
);


--
-- Name: students_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.students_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: students_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.students_id_seq OWNED BY public.students.id;


--
-- Name: students_personal; Type: FOREIGN TABLE; Schema: public; Owner: -
--

CREATE FOREIGN TABLE public.students_personal (
    id integer,
    last_name character varying(100),
    first_name character varying(100),
    middle_name character varying(100),
    birth_date date,
    city character varying(100),
    street character varying(100),
    house_number character varying(20),
    email character varying(100)
)
SERVER personal_server
OPTIONS (
    schema_name 'public',
    table_name 'students'
);


--
-- Name: subjects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subjects (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    direction_id integer NOT NULL
);


--
-- Name: subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.subjects_id_seq OWNED BY public.subjects.id;


--
-- Name: teacher_subjects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_subjects (
    id integer NOT NULL,
    teacher_id integer NOT NULL,
    subject_id integer NOT NULL
);


--
-- Name: teacher_subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_subjects_id_seq OWNED BY public.teacher_subjects.id;


--
-- Name: teachers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teachers (
    id integer NOT NULL,
    last_name character varying(100) NOT NULL,
    first_name character varying(100) NOT NULL,
    middle_name character varying(100)
);


--
-- Name: teachers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teachers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teachers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teachers_id_seq OWNED BY public.teachers.id;


--
-- Name: time_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.time_slots (
    id integer NOT NULL,
    pair_number integer NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL
);


--
-- Name: time_slots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.time_slots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: time_slots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.time_slots_id_seq OWNED BY public.time_slots.id;


--
-- Name: v_students_full; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_students_full AS
 SELECT s.id,
    sp.last_name,
    sp.first_name,
    sp.middle_name,
    sp.birth_date,
    sp.city,
    sp.street,
    sp.house_number,
    sp.email,
    s.group_id,
    s.is_budget
   FROM (public.students s
     JOIN public.students_personal sp ON ((sp.id = s.id)));


--
-- Name: attendance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance ALTER COLUMN id SET DEFAULT nextval('public.attendance_id_seq'::regclass);


--
-- Name: directions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.directions ALTER COLUMN id SET DEFAULT nextval('public.directions_id_seq'::regclass);


--
-- Name: extra_param_defs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extra_param_defs ALTER COLUMN id SET DEFAULT nextval('public.extra_param_defs_id_seq'::regclass);


--
-- Name: grades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades ALTER COLUMN id SET DEFAULT nextval('public.grades_id_seq'::regclass);


--
-- Name: groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups ALTER COLUMN id SET DEFAULT nextval('public.groups_id_seq'::regclass);


--
-- Name: student_extra_params id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_extra_params ALTER COLUMN id SET DEFAULT nextval('public.student_extra_params_id_seq'::regclass);


--
-- Name: students id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students ALTER COLUMN id SET DEFAULT nextval('public.students_id_seq'::regclass);


--
-- Name: subjects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects ALTER COLUMN id SET DEFAULT nextval('public.subjects_id_seq'::regclass);


--
-- Name: teacher_subjects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_subjects ALTER COLUMN id SET DEFAULT nextval('public.teacher_subjects_id_seq'::regclass);


--
-- Name: teachers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teachers ALTER COLUMN id SET DEFAULT nextval('public.teachers_id_seq'::regclass);


--
-- Name: time_slots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.time_slots ALTER COLUMN id SET DEFAULT nextval('public.time_slots_id_seq'::regclass);


--
-- Data for Name: attendance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.attendance (id, student_id, subject_id, teacher_id, date, time_slot_id, is_present) FROM stdin;
1	1	1	1	2024-09-01	1	t
2	1	1	1	2024-09-02	1	t
3	1	1	1	2024-09-03	1	f
4	1	2	2	2024-09-01	2	t
5	1	2	2	2024-09-02	2	t
6	1	2	2	2024-09-03	2	t
7	1	3	3	2024-09-01	3	t
8	1	3	3	2024-09-02	3	f
9	1	3	3	2024-09-03	3	t
10	2	1	1	2024-09-01	1	t
11	2	1	1	2024-09-02	1	f
12	2	1	1	2024-09-03	1	t
13	2	2	2	2024-09-01	2	t
14	2	2	2	2024-09-02	2	t
15	2	2	2	2024-09-03	2	f
16	2	3	3	2024-09-01	3	t
17	2	3	3	2024-09-02	3	t
18	2	3	3	2024-09-03	3	t
19	3	1	1	2024-09-01	1	f
20	3	1	1	2024-09-02	1	t
21	3	1	1	2024-09-03	1	t
22	3	2	2	2024-09-01	2	t
23	3	2	2	2024-09-02	2	f
24	3	2	2	2024-09-03	2	t
25	3	3	3	2024-09-01	3	t
26	3	3	3	2024-09-02	3	t
27	3	3	3	2024-09-03	3	f
28	4	1	1	2024-09-01	1	t
29	4	1	1	2024-09-02	1	t
30	4	1	1	2024-09-03	1	t
31	4	2	2	2024-09-01	2	t
32	4	2	2	2024-09-02	2	t
33	4	2	2	2024-09-03	2	t
34	4	3	3	2024-09-01	3	t
35	4	3	3	2024-09-02	3	t
36	4	3	3	2024-09-03	3	t
37	5	1	1	2024-09-01	1	t
38	5	1	1	2024-09-02	1	t
39	5	1	1	2024-09-03	1	f
40	5	2	2	2024-09-01	2	f
41	5	2	2	2024-09-02	2	t
42	5	2	2	2024-09-03	2	t
43	5	3	3	2024-09-01	3	t
44	5	3	3	2024-09-02	3	t
45	5	3	3	2024-09-03	3	t
46	6	1	1	2024-09-01	1	f
47	6	1	1	2024-09-02	1	f
48	6	1	1	2024-09-03	1	t
49	6	2	2	2024-09-01	2	t
50	6	2	2	2024-09-02	2	t
51	6	2	2	2024-09-03	2	f
52	6	3	3	2024-09-01	3	f
53	6	3	3	2024-09-02	3	t
54	6	3	3	2024-09-03	3	t
55	7	1	1	2024-09-01	1	t
56	7	1	1	2024-09-02	1	t
57	7	1	1	2024-09-03	1	t
58	7	2	2	2024-09-01	2	t
59	7	2	2	2024-09-02	2	f
60	7	2	2	2024-09-03	2	t
61	7	3	3	2024-09-01	3	t
62	7	3	3	2024-09-02	3	t
63	7	3	3	2024-09-03	3	f
64	8	1	1	2024-09-01	1	t
65	8	1	1	2024-09-02	1	f
66	8	1	1	2024-09-03	1	t
67	8	2	2	2024-09-01	2	t
68	8	2	2	2024-09-02	2	t
69	8	2	2	2024-09-03	2	t
70	8	3	3	2024-09-01	3	t
71	8	3	3	2024-09-02	3	f
72	8	3	3	2024-09-03	3	t
73	9	1	1	2024-09-01	1	f
74	9	1	1	2024-09-02	1	t
75	9	1	1	2024-09-03	1	t
76	9	2	2	2024-09-01	2	t
77	9	2	2	2024-09-02	2	t
78	9	2	2	2024-09-03	2	t
79	9	3	3	2024-09-01	3	t
80	9	3	3	2024-09-02	3	t
81	9	3	3	2024-09-03	3	t
82	10	1	1	2024-09-01	1	t
83	10	1	1	2024-09-02	1	t
84	10	1	1	2024-09-03	1	t
85	10	2	2	2024-09-01	2	t
86	10	2	2	2024-09-02	2	t
87	10	2	2	2024-09-03	2	f
88	10	3	3	2024-09-01	3	f
89	10	3	3	2024-09-02	3	t
90	10	3	3	2024-09-03	3	t
91	11	1	1	2024-09-01	1	t
92	11	1	1	2024-09-02	1	t
93	11	1	1	2024-09-03	1	f
94	11	2	2	2024-09-01	2	f
95	11	2	2	2024-09-02	2	t
96	11	2	2	2024-09-03	2	t
97	11	3	3	2024-09-01	3	t
98	11	3	3	2024-09-02	3	t
99	11	3	3	2024-09-03	3	t
100	12	1	1	2024-09-01	1	t
101	12	1	1	2024-09-02	1	f
102	12	1	1	2024-09-03	1	t
103	12	2	2	2024-09-01	2	t
104	12	2	2	2024-09-02	2	t
105	12	2	2	2024-09-03	2	t
106	12	3	3	2024-09-01	3	t
107	12	3	3	2024-09-02	3	f
108	12	3	3	2024-09-03	3	t
109	13	1	1	2024-09-01	1	f
110	13	1	1	2024-09-02	1	t
111	13	1	1	2024-09-03	1	t
112	13	2	2	2024-09-01	2	t
113	13	2	2	2024-09-02	2	t
114	13	2	2	2024-09-03	2	f
115	13	3	3	2024-09-01	3	t
116	13	3	3	2024-09-02	3	t
117	13	3	3	2024-09-03	3	t
118	14	1	1	2024-09-01	1	t
119	14	1	1	2024-09-02	1	t
120	14	1	1	2024-09-03	1	t
121	14	2	2	2024-09-01	2	t
122	14	2	2	2024-09-02	2	f
123	14	2	2	2024-09-03	2	t
124	14	3	3	2024-09-01	3	f
125	14	3	3	2024-09-02	3	t
126	14	3	3	2024-09-03	3	t
127	15	1	1	2024-09-01	1	t
128	15	1	1	2024-09-02	1	t
129	15	1	1	2024-09-03	1	f
130	15	2	2	2024-09-01	2	t
131	15	2	2	2024-09-02	2	t
132	15	2	2	2024-09-03	2	t
133	15	3	3	2024-09-01	3	t
134	15	3	3	2024-09-02	3	t
135	15	3	3	2024-09-03	3	t
136	49	4	1	2024-09-01	1	t
137	49	4	1	2024-09-02	1	t
138	49	4	1	2024-09-03	1	f
139	49	5	2	2024-09-01	2	t
140	49	5	2	2024-09-02	2	t
141	49	5	2	2024-09-03	2	t
142	49	6	3	2024-09-01	3	t
143	49	6	3	2024-09-02	3	f
144	49	6	3	2024-09-03	3	t
145	50	4	1	2024-09-01	1	t
146	50	4	1	2024-09-02	1	f
147	50	4	1	2024-09-03	1	t
148	50	5	2	2024-09-01	2	t
149	50	5	2	2024-09-02	2	t
150	50	5	2	2024-09-03	2	f
151	50	6	3	2024-09-01	3	t
152	50	6	3	2024-09-02	3	t
153	50	6	3	2024-09-03	3	t
154	51	4	1	2024-09-01	1	f
155	51	4	1	2024-09-02	1	t
156	51	4	1	2024-09-03	1	t
157	51	5	2	2024-09-01	2	t
158	51	5	2	2024-09-02	2	f
159	51	5	2	2024-09-03	2	t
160	51	6	3	2024-09-01	3	t
161	51	6	3	2024-09-02	3	t
162	51	6	3	2024-09-03	3	f
163	52	4	1	2024-09-01	1	t
164	52	4	1	2024-09-02	1	t
165	52	4	1	2024-09-03	1	t
166	52	5	2	2024-09-01	2	t
167	52	5	2	2024-09-02	2	t
168	52	5	2	2024-09-03	2	t
169	52	6	3	2024-09-01	3	t
170	52	6	3	2024-09-02	3	t
171	52	6	3	2024-09-03	3	t
172	53	4	1	2024-09-01	1	t
173	53	4	1	2024-09-02	1	t
174	53	4	1	2024-09-03	1	f
175	53	5	2	2024-09-01	2	f
176	53	5	2	2024-09-02	2	t
177	53	5	2	2024-09-03	2	t
178	53	6	3	2024-09-01	3	t
179	53	6	3	2024-09-02	3	t
180	53	6	3	2024-09-03	3	t
181	54	4	1	2024-09-01	1	f
182	54	4	1	2024-09-02	1	f
183	54	4	1	2024-09-03	1	t
184	54	5	2	2024-09-01	2	t
185	54	5	2	2024-09-02	2	t
186	54	5	2	2024-09-03	2	f
187	54	6	3	2024-09-01	3	f
188	54	6	3	2024-09-02	3	t
189	54	6	3	2024-09-03	3	t
190	55	4	1	2024-09-01	1	t
191	55	4	1	2024-09-02	1	t
192	55	4	1	2024-09-03	1	t
193	55	5	2	2024-09-01	2	t
194	55	5	2	2024-09-02	2	f
195	55	5	2	2024-09-03	2	t
196	55	6	3	2024-09-01	3	t
197	55	6	3	2024-09-02	3	t
198	55	6	3	2024-09-03	3	f
199	56	4	1	2024-09-01	1	t
200	56	4	1	2024-09-02	1	f
201	56	4	1	2024-09-03	1	t
202	56	5	2	2024-09-01	2	t
203	56	5	2	2024-09-02	2	t
204	56	5	2	2024-09-03	2	t
205	56	6	3	2024-09-01	3	t
206	56	6	3	2024-09-02	3	f
207	56	6	3	2024-09-03	3	t
208	57	4	1	2024-09-01	1	f
209	57	4	1	2024-09-02	1	t
210	57	4	1	2024-09-03	1	t
211	57	5	2	2024-09-01	2	t
212	57	5	2	2024-09-02	2	t
213	57	5	2	2024-09-03	2	t
214	57	6	3	2024-09-01	3	t
215	57	6	3	2024-09-02	3	t
216	57	6	3	2024-09-03	3	t
217	58	4	1	2024-09-01	1	t
218	58	4	1	2024-09-02	1	t
219	58	4	1	2024-09-03	1	t
220	58	5	2	2024-09-01	2	t
221	58	5	2	2024-09-02	2	t
222	58	5	2	2024-09-03	2	f
223	58	6	3	2024-09-01	3	f
224	58	6	3	2024-09-02	3	t
225	58	6	3	2024-09-03	3	t
226	59	4	1	2024-09-01	1	t
227	59	4	1	2024-09-02	1	t
228	59	4	1	2024-09-03	1	f
229	59	5	2	2024-09-01	2	f
230	59	5	2	2024-09-02	2	t
231	59	5	2	2024-09-03	2	t
232	59	6	3	2024-09-01	3	t
233	59	6	3	2024-09-02	3	t
234	59	6	3	2024-09-03	3	t
235	60	4	1	2024-09-01	1	t
236	60	4	1	2024-09-02	1	f
237	60	4	1	2024-09-03	1	t
238	60	5	2	2024-09-01	2	t
239	60	5	2	2024-09-02	2	t
240	60	5	2	2024-09-03	2	t
241	60	6	3	2024-09-01	3	t
242	60	6	3	2024-09-02	3	f
243	60	6	3	2024-09-03	3	t
244	61	4	1	2024-09-01	1	f
245	61	4	1	2024-09-02	1	t
246	61	4	1	2024-09-03	1	t
247	61	5	2	2024-09-01	2	t
248	61	5	2	2024-09-02	2	t
249	61	5	2	2024-09-03	2	f
250	61	6	3	2024-09-01	3	t
251	61	6	3	2024-09-02	3	t
252	61	6	3	2024-09-03	3	t
253	62	4	1	2024-09-01	1	t
254	62	4	1	2024-09-02	1	t
255	62	4	1	2024-09-03	1	t
256	62	5	2	2024-09-01	2	t
257	62	5	2	2024-09-02	2	f
258	62	5	2	2024-09-03	2	t
259	62	6	3	2024-09-01	3	f
260	62	6	3	2024-09-02	3	t
261	62	6	3	2024-09-03	3	t
262	63	4	1	2024-09-01	1	t
263	63	4	1	2024-09-02	1	t
264	63	4	1	2024-09-03	1	f
265	63	5	2	2024-09-01	2	t
266	63	5	2	2024-09-02	2	t
267	63	5	2	2024-09-03	2	t
268	63	6	3	2024-09-01	3	t
269	63	6	3	2024-09-02	3	t
270	63	6	3	2024-09-03	3	t
271	97	7	1	2024-09-01	1	t
272	97	7	1	2024-09-02	1	t
273	97	7	1	2024-09-03	1	f
274	97	8	2	2024-09-01	2	t
275	97	8	2	2024-09-02	2	t
276	97	8	2	2024-09-03	2	t
277	97	9	3	2024-09-01	3	t
278	97	9	3	2024-09-02	3	f
279	97	9	3	2024-09-03	3	t
280	98	7	1	2024-09-01	1	t
281	98	7	1	2024-09-02	1	f
282	98	7	1	2024-09-03	1	t
283	98	8	2	2024-09-01	2	t
284	98	8	2	2024-09-02	2	t
285	98	8	2	2024-09-03	2	f
286	98	9	3	2024-09-01	3	t
287	98	9	3	2024-09-02	3	t
288	98	9	3	2024-09-03	3	t
289	99	7	1	2024-09-01	1	f
290	99	7	1	2024-09-02	1	t
291	99	7	1	2024-09-03	1	t
292	99	8	2	2024-09-01	2	t
293	99	8	2	2024-09-02	2	f
294	99	8	2	2024-09-03	2	t
295	99	9	3	2024-09-01	3	t
296	99	9	3	2024-09-02	3	t
297	99	9	3	2024-09-03	3	f
298	100	7	1	2024-09-01	1	t
299	100	7	1	2024-09-02	1	t
300	100	7	1	2024-09-03	1	t
301	100	8	2	2024-09-01	2	t
302	100	8	2	2024-09-02	2	t
303	100	8	2	2024-09-03	2	t
304	100	9	3	2024-09-01	3	t
305	100	9	3	2024-09-02	3	t
306	100	9	3	2024-09-03	3	t
307	101	7	1	2024-09-01	1	t
308	101	7	1	2024-09-02	1	t
309	101	7	1	2024-09-03	1	f
310	101	8	2	2024-09-01	2	f
311	101	8	2	2024-09-02	2	t
312	101	8	2	2024-09-03	2	t
313	101	9	3	2024-09-01	3	t
314	101	9	3	2024-09-02	3	t
315	101	9	3	2024-09-03	3	t
316	102	7	1	2024-09-01	1	f
317	102	7	1	2024-09-02	1	f
318	102	7	1	2024-09-03	1	t
319	102	8	2	2024-09-01	2	t
320	102	8	2	2024-09-02	2	t
321	102	8	2	2024-09-03	2	f
322	102	9	3	2024-09-01	3	f
323	102	9	3	2024-09-02	3	t
324	102	9	3	2024-09-03	3	t
325	103	7	1	2024-09-01	1	t
326	103	7	1	2024-09-02	1	t
327	103	7	1	2024-09-03	1	t
328	103	8	2	2024-09-01	2	t
329	103	8	2	2024-09-02	2	f
330	103	8	2	2024-09-03	2	t
331	103	9	3	2024-09-01	3	t
332	103	9	3	2024-09-02	3	t
333	103	9	3	2024-09-03	3	f
334	104	7	1	2024-09-01	1	t
335	104	7	1	2024-09-02	1	f
336	104	7	1	2024-09-03	1	t
337	104	8	2	2024-09-01	2	t
338	104	8	2	2024-09-02	2	t
339	104	8	2	2024-09-03	2	t
340	104	9	3	2024-09-01	3	t
341	104	9	3	2024-09-02	3	f
342	104	9	3	2024-09-03	3	t
343	105	7	1	2024-09-01	1	f
344	105	7	1	2024-09-02	1	t
345	105	7	1	2024-09-03	1	t
346	105	8	2	2024-09-01	2	t
347	105	8	2	2024-09-02	2	t
348	105	8	2	2024-09-03	2	t
349	105	9	3	2024-09-01	3	t
350	105	9	3	2024-09-02	3	t
351	105	9	3	2024-09-03	3	t
352	106	7	1	2024-09-01	1	t
353	106	7	1	2024-09-02	1	t
354	106	7	1	2024-09-03	1	t
355	106	8	2	2024-09-01	2	t
356	106	8	2	2024-09-02	2	t
357	106	8	2	2024-09-03	2	f
358	106	9	3	2024-09-01	3	f
359	106	9	3	2024-09-02	3	t
360	106	9	3	2024-09-03	3	t
361	107	7	1	2024-09-01	1	t
362	107	7	1	2024-09-02	1	t
363	107	7	1	2024-09-03	1	f
364	107	8	2	2024-09-01	2	f
365	107	8	2	2024-09-02	2	t
366	107	8	2	2024-09-03	2	t
367	107	9	3	2024-09-01	3	t
368	107	9	3	2024-09-02	3	t
369	107	9	3	2024-09-03	3	t
370	108	7	1	2024-09-01	1	t
371	108	7	1	2024-09-02	1	f
372	108	7	1	2024-09-03	1	t
373	108	8	2	2024-09-01	2	t
374	108	8	2	2024-09-02	2	t
375	108	8	2	2024-09-03	2	t
376	108	9	3	2024-09-01	3	t
377	108	9	3	2024-09-02	3	f
378	108	9	3	2024-09-03	3	t
379	109	7	1	2024-09-01	1	f
380	109	7	1	2024-09-02	1	t
381	109	7	1	2024-09-03	1	t
382	109	8	2	2024-09-01	2	t
383	109	8	2	2024-09-02	2	t
384	109	8	2	2024-09-03	2	f
385	109	9	3	2024-09-01	3	t
386	109	9	3	2024-09-02	3	t
387	109	9	3	2024-09-03	3	t
388	110	7	1	2024-09-01	1	t
389	110	7	1	2024-09-02	1	t
390	110	7	1	2024-09-03	1	t
391	110	8	2	2024-09-01	2	t
392	110	8	2	2024-09-02	2	f
393	110	8	2	2024-09-03	2	t
394	110	9	3	2024-09-01	3	f
395	110	9	3	2024-09-02	3	t
396	110	9	3	2024-09-03	3	t
397	111	7	1	2024-09-01	1	t
398	111	7	1	2024-09-02	1	t
399	111	7	1	2024-09-03	1	f
400	111	8	2	2024-09-01	2	t
401	111	8	2	2024-09-02	2	t
402	111	8	2	2024-09-03	2	t
403	111	9	3	2024-09-01	3	t
404	111	9	3	2024-09-02	3	t
405	111	9	3	2024-09-03	3	t
\.


--
-- Data for Name: avg_group_all; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.avg_group_all (group_id, avg_grade, updated_at) FROM stdin;
4	4.18	2026-09-17 05:44:38.19587
10	4.21	2026-09-17 05:44:38.19587
6	4.08	2026-09-17 05:44:38.19587
13	4.21	2026-09-17 05:44:38.19587
2	4.13	2026-09-17 05:44:38.19587
11	4.12	2026-09-17 05:44:38.19587
9	4.09	2026-09-17 05:44:38.19587
3	4.08	2026-09-17 05:44:38.19587
12	4.09	2026-09-17 05:44:38.19587
15	4.09	2026-09-17 05:44:38.19587
5	4.13	2026-09-17 05:44:38.19587
14	4.12	2026-09-17 05:44:38.19587
7	4.18	2026-09-17 05:44:38.19587
1	4.18	2026-09-17 05:44:38.19587
8	4.13	2026-09-17 05:44:38.19587
\.


--
-- Data for Name: avg_group_subject; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.avg_group_subject (group_id, subject_id, avg_grade, updated_at) FROM stdin;
1	1	4.07	2026-09-17 05:44:38.190461
7	7	4.07	2026-09-17 05:44:38.190461
14	15	4.29	2026-09-17 05:44:38.190461
6	5	4.06	2026-09-17 05:44:38.190461
4	5	4.20	2026-09-17 05:44:38.190461
12	12	4.20	2026-09-17 05:44:38.190461
11	11	4.07	2026-09-17 05:44:38.190461
6	6	4.12	2026-09-17 05:44:38.190461
10	12	4.38	2026-09-17 05:44:38.190461
13	15	4.38	2026-09-17 05:44:38.190461
6	4	4.06	2026-09-17 05:44:38.190461
5	4	4.06	2026-09-17 05:44:38.190461
14	13	4.00	2026-09-17 05:44:38.190461
9	9	4.20	2026-09-17 05:44:38.190461
3	2	4.06	2026-09-17 05:44:38.190461
1	2	4.20	2026-09-17 05:44:38.190461
8	7	4.06	2026-09-17 05:44:38.190461
12	11	4.07	2026-09-17 05:44:38.190461
15	13	4.00	2026-09-17 05:44:38.190461
12	10	4.00	2026-09-17 05:44:38.190461
9	8	4.07	2026-09-17 05:44:38.190461
15	14	4.07	2026-09-17 05:44:38.190461
7	8	4.20	2026-09-17 05:44:38.190461
9	7	4.00	2026-09-17 05:44:38.190461
14	14	4.07	2026-09-17 05:44:38.190461
2	2	4.13	2026-09-17 05:44:38.190461
3	1	4.06	2026-09-17 05:44:38.190461
5	6	4.19	2026-09-17 05:44:38.190461
10	11	4.15	2026-09-17 05:44:38.190461
13	14	4.15	2026-09-17 05:44:38.190461
2	3	4.19	2026-09-17 05:44:38.190461
3	3	4.12	2026-09-17 05:44:38.190461
1	3	4.27	2026-09-17 05:44:38.190461
8	8	4.13	2026-09-17 05:44:38.190461
11	12	4.29	2026-09-17 05:44:38.190461
5	5	4.13	2026-09-17 05:44:38.190461
4	6	4.27	2026-09-17 05:44:38.190461
8	9	4.19	2026-09-17 05:44:38.190461
4	4	4.07	2026-09-17 05:44:38.190461
10	10	4.08	2026-09-17 05:44:38.190461
13	13	4.08	2026-09-17 05:44:38.190461
2	1	4.06	2026-09-17 05:44:38.190461
11	10	4.00	2026-09-17 05:44:38.190461
7	9	4.27	2026-09-17 05:44:38.190461
15	15	4.20	2026-09-17 05:44:38.190461
\.


--
-- Data for Name: avg_subject; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.avg_subject (subject_id, avg_grade, updated_at) FROM stdin;
4	4.06	2026-09-17 05:44:38.198996
14	4.10	2026-09-17 05:44:38.198996
3	4.19	2026-09-17 05:44:38.198996
13	4.02	2026-09-17 05:44:38.198996
10	4.02	2026-09-17 05:44:38.198996
9	4.22	2026-09-17 05:44:38.198996
7	4.04	2026-09-17 05:44:38.198996
1	4.06	2026-09-17 05:44:38.198996
5	4.13	2026-09-17 05:44:38.198996
2	4.13	2026-09-17 05:44:38.198996
15	4.29	2026-09-17 05:44:38.198996
6	4.19	2026-09-17 05:44:38.198996
12	4.29	2026-09-17 05:44:38.198996
11	4.10	2026-09-17 05:44:38.198996
8	4.13	2026-09-17 05:44:38.198996
\.


--
-- Data for Name: directions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.directions (id, name) FROM stdin;
1	Информатика и вычислительная техника
2	Программная инженерия
3	Прикладная математика и информатика
4	Информационная безопасность
5	Системный анализ и управление
\.


--
-- Data for Name: extra_param_defs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.extra_param_defs (id, direction_id, param_name, param_type, description) FROM stdin;
18	1	язык_программирования	text	Основной язык
19	1	тема_проекта	text	Тема курсового проекта
20	1	часы_практики	numeric	Часы производственной практики
21	1	рейтинг_балл	numeric	Текущий рейтинг студента
22	2	роль_в_команде	text	Роль в учебном проекте
23	2	стек	text	Технологический стек
24	2	закрытых_багов	numeric	Закрыто багов в трекере
25	2	рейтинг_балл	numeric	Текущий рейтинг
26	3	научный_интерес	text	Научный интерес
27	3	олимпиады	numeric	Число олимпиад
28	3	рейтинг_балл	numeric	Рейтинг
29	4	сертификат	text	Сертификат/курс
30	4	ctf_очки	numeric	Очки CTF
31	4	рейтинг_балл	numeric	Рейтинг
32	5	кейс	text	Анализируемый кейс
33	5	kpi_балл	numeric	KPI учебного проекта
34	5	рейтинг_балл	numeric	Рейтинг
\.


--
-- Data for Name: grades; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.grades (id, student_id, subject_id, grade, set_by_teacher_id) FROM stdin;
1	1	1	5	\N
2	1	2	4	\N
3	1	3	5	\N
4	2	1	4	\N
5	2	2	5	\N
6	2	3	4	\N
7	3	1	3	\N
8	3	2	3	\N
9	3	3	4	\N
10	4	1	5	\N
11	4	2	5	\N
12	4	3	5	\N
13	5	1	4	\N
14	5	2	4	\N
15	5	3	5	\N
16	6	1	2	\N
17	6	2	3	\N
18	6	3	3	\N
19	7	1	5	\N
20	7	2	4	\N
21	7	3	4	\N
22	8	1	4	\N
23	8	2	5	\N
24	8	3	5	\N
25	9	1	3	\N
26	9	2	4	\N
27	9	3	4	\N
28	10	1	5	\N
29	10	2	5	\N
30	10	3	4	\N
31	11	1	4	\N
32	11	2	3	\N
33	11	3	5	\N
34	12	1	5	\N
35	12	2	4	\N
36	12	3	4	\N
37	13	1	4	\N
38	13	2	5	\N
39	13	3	5	\N
40	14	1	3	\N
41	14	2	4	\N
42	14	3	3	\N
43	15	1	5	\N
44	15	2	5	\N
45	15	3	4	\N
46	16	1	4	\N
47	16	2	5	\N
48	16	3	4	\N
49	17	1	5	\N
50	17	2	4	\N
51	17	3	5	\N
52	18	1	3	\N
53	18	2	3	\N
54	18	3	4	\N
55	19	1	4	\N
56	19	2	4	\N
57	19	3	5	\N
58	20	1	5	\N
59	20	2	5	\N
60	20	3	4	\N
61	21	1	4	\N
62	21	2	3	\N
63	21	3	3	\N
64	22	1	5	\N
65	22	2	4	\N
66	22	3	5	\N
67	23	1	3	\N
68	23	2	5	\N
69	23	3	4	\N
70	24	1	4	\N
71	24	2	4	\N
72	24	3	4	\N
73	25	1	5	\N
74	25	2	5	\N
75	25	3	5	\N
76	26	1	2	\N
77	26	2	3	\N
78	26	3	3	\N
79	27	1	4	\N
80	27	2	4	\N
81	27	3	5	\N
82	28	1	5	\N
83	28	2	3	\N
84	28	3	4	\N
85	29	1	3	\N
86	29	2	5	\N
87	29	3	5	\N
88	30	1	4	\N
89	30	2	4	\N
90	30	3	4	\N
91	31	1	5	\N
92	31	2	5	\N
93	31	3	3	\N
94	32	1	4	\N
95	32	2	4	\N
96	32	3	5	\N
97	33	1	5	\N
98	33	2	5	\N
99	33	3	4	\N
100	34	1	3	\N
101	34	2	3	\N
102	34	3	3	\N
103	35	1	4	\N
104	35	2	5	\N
105	35	3	5	\N
106	36	1	5	\N
107	36	2	4	\N
108	36	3	4	\N
109	37	1	4	\N
110	37	2	3	\N
111	37	3	5	\N
112	38	1	5	\N
113	38	2	5	\N
114	38	3	4	\N
115	39	1	3	\N
116	39	2	4	\N
117	39	3	3	\N
118	40	1	4	\N
119	40	2	5	\N
120	40	3	5	\N
121	41	1	5	\N
122	41	2	4	\N
123	41	3	4	\N
124	42	1	2	\N
125	42	2	2	\N
126	42	3	3	\N
127	43	1	4	\N
128	43	2	4	\N
129	43	3	5	\N
130	44	1	5	\N
131	44	2	5	\N
132	44	3	4	\N
133	45	1	3	\N
134	45	2	3	\N
135	45	3	4	\N
136	46	1	4	\N
137	46	2	5	\N
138	46	3	5	\N
139	47	1	5	\N
140	47	2	4	\N
141	47	3	4	\N
142	48	1	4	\N
143	48	2	4	\N
144	48	3	3	\N
145	49	4	5	\N
146	49	5	4	\N
147	49	6	5	\N
148	50	4	4	\N
149	50	5	5	\N
150	50	6	4	\N
151	51	4	3	\N
152	51	5	3	\N
153	51	6	4	\N
154	52	4	5	\N
155	52	5	5	\N
156	52	6	5	\N
157	53	4	4	\N
158	53	5	4	\N
159	53	6	5	\N
160	54	4	2	\N
161	54	5	3	\N
162	54	6	3	\N
163	55	4	5	\N
164	55	5	4	\N
165	55	6	4	\N
166	56	4	4	\N
167	56	5	5	\N
168	56	6	5	\N
169	57	4	3	\N
170	57	5	4	\N
171	57	6	4	\N
172	58	4	5	\N
173	58	5	5	\N
174	58	6	4	\N
175	59	4	4	\N
176	59	5	3	\N
177	59	6	5	\N
178	60	4	5	\N
179	60	5	4	\N
180	60	6	4	\N
181	61	4	4	\N
182	61	5	5	\N
183	61	6	5	\N
184	62	4	3	\N
185	62	5	4	\N
186	62	6	3	\N
187	63	4	5	\N
188	63	5	5	\N
189	63	6	4	\N
190	64	4	4	\N
191	64	5	5	\N
192	64	6	4	\N
193	65	4	5	\N
194	65	5	4	\N
195	65	6	5	\N
196	66	4	3	\N
197	66	5	3	\N
198	66	6	4	\N
199	67	4	4	\N
200	67	5	4	\N
201	67	6	5	\N
202	68	4	5	\N
203	68	5	5	\N
204	68	6	4	\N
205	69	4	4	\N
206	69	5	3	\N
207	69	6	3	\N
208	70	4	5	\N
209	70	5	4	\N
210	70	6	5	\N
211	71	4	3	\N
212	71	5	5	\N
213	71	6	4	\N
214	72	4	4	\N
215	72	5	4	\N
216	72	6	4	\N
217	73	4	5	\N
218	73	5	5	\N
219	73	6	5	\N
220	74	4	2	\N
221	74	5	3	\N
222	74	6	3	\N
223	75	4	4	\N
224	75	5	4	\N
225	75	6	5	\N
226	76	4	5	\N
227	76	5	3	\N
228	76	6	4	\N
229	77	4	3	\N
230	77	5	5	\N
231	77	6	5	\N
232	78	4	4	\N
233	78	5	4	\N
234	78	6	4	\N
235	79	4	5	\N
236	79	5	5	\N
237	79	6	3	\N
238	80	4	4	\N
239	80	5	4	\N
240	80	6	5	\N
241	81	4	5	\N
242	81	5	5	\N
243	81	6	4	\N
244	82	4	3	\N
245	82	5	3	\N
246	82	6	3	\N
247	83	4	4	\N
248	83	5	5	\N
249	83	6	5	\N
250	84	4	5	\N
251	84	5	4	\N
252	84	6	4	\N
253	85	4	4	\N
254	85	5	3	\N
255	85	6	5	\N
256	86	4	5	\N
257	86	5	5	\N
258	86	6	4	\N
259	87	4	3	\N
260	87	5	4	\N
261	87	6	3	\N
262	88	4	4	\N
263	88	5	5	\N
264	88	6	5	\N
265	89	4	5	\N
266	89	5	4	\N
267	89	6	4	\N
268	90	4	2	\N
269	90	5	2	\N
270	90	6	3	\N
271	91	4	4	\N
272	91	5	4	\N
273	91	6	5	\N
274	92	4	5	\N
275	92	5	5	\N
276	92	6	4	\N
277	93	4	3	\N
278	93	5	3	\N
279	93	6	4	\N
280	94	4	4	\N
281	94	5	5	\N
282	94	6	5	\N
283	95	4	5	\N
284	95	5	4	\N
285	95	6	4	\N
286	96	4	4	\N
287	96	5	4	\N
288	96	6	3	\N
289	97	7	5	\N
290	97	8	4	\N
291	97	9	5	\N
292	98	7	4	\N
293	98	8	5	\N
294	98	9	4	\N
295	99	7	3	\N
296	99	8	3	\N
297	99	9	4	\N
298	100	7	5	\N
299	100	8	5	\N
300	100	9	5	\N
301	101	7	4	\N
302	101	8	4	\N
303	101	9	5	\N
304	102	7	2	\N
305	102	8	3	\N
306	102	9	3	\N
307	103	7	5	\N
308	103	8	4	\N
309	103	9	4	\N
310	104	7	4	\N
311	104	8	5	\N
312	104	9	5	\N
313	105	7	3	\N
314	105	8	4	\N
315	105	9	4	\N
316	106	7	5	\N
317	106	8	5	\N
318	106	9	4	\N
319	107	7	4	\N
320	107	8	3	\N
321	107	9	5	\N
322	108	7	5	\N
323	108	8	4	\N
324	108	9	4	\N
325	109	7	4	\N
326	109	8	5	\N
327	109	9	5	\N
328	110	7	3	\N
329	110	8	4	\N
330	110	9	3	\N
331	111	7	5	\N
332	111	8	5	\N
333	111	9	4	\N
334	112	7	4	\N
335	112	8	5	\N
336	112	9	4	\N
337	113	7	5	\N
338	113	8	4	\N
339	113	9	5	\N
340	114	7	3	\N
341	114	8	3	\N
342	114	9	4	\N
343	115	7	4	\N
344	115	8	4	\N
345	115	9	5	\N
346	116	7	5	\N
347	116	8	5	\N
348	116	9	4	\N
349	117	7	4	\N
350	117	8	3	\N
351	117	9	3	\N
352	118	7	5	\N
353	118	8	4	\N
354	118	9	5	\N
355	119	7	3	\N
356	119	8	5	\N
357	119	9	4	\N
358	120	7	4	\N
359	120	8	4	\N
360	120	9	4	\N
361	121	7	5	\N
362	121	8	5	\N
363	121	9	5	\N
364	122	7	2	\N
365	122	8	3	\N
366	122	9	3	\N
367	123	7	4	\N
368	123	8	4	\N
369	123	9	5	\N
370	124	7	5	\N
371	124	8	3	\N
372	124	9	4	\N
373	125	7	3	\N
374	125	8	5	\N
375	125	9	5	\N
376	126	7	4	\N
377	126	8	4	\N
378	126	9	4	\N
379	127	7	5	\N
380	127	8	5	\N
381	127	9	3	\N
382	128	7	4	\N
383	128	8	4	\N
384	128	9	5	\N
385	129	7	5	\N
386	129	8	5	\N
387	129	9	4	\N
388	130	7	3	\N
389	130	8	3	\N
390	130	9	3	\N
391	131	7	4	\N
392	131	8	5	\N
393	131	9	5	\N
394	132	7	5	\N
395	132	8	4	\N
396	132	9	4	\N
397	133	7	4	\N
398	133	8	3	\N
399	133	9	5	\N
400	134	7	5	\N
401	134	8	5	\N
402	134	9	4	\N
403	135	7	3	\N
404	135	8	4	\N
405	135	9	3	\N
406	136	7	4	\N
407	136	8	5	\N
408	136	9	5	\N
409	137	7	5	\N
410	137	8	4	\N
411	137	9	4	\N
412	138	7	2	\N
413	138	8	2	\N
414	138	9	3	\N
415	139	7	4	\N
416	139	8	4	\N
417	139	9	5	\N
418	140	7	5	\N
419	140	8	5	\N
420	140	9	4	\N
421	141	7	3	\N
422	141	8	3	\N
423	141	9	4	\N
424	142	7	4	\N
425	142	8	5	\N
426	142	9	5	\N
427	145	10	5	\N
428	145	11	4	\N
429	145	12	5	\N
430	146	10	4	\N
431	146	11	5	\N
432	146	12	4	\N
433	147	10	3	\N
434	147	11	3	\N
435	147	12	4	\N
436	148	10	5	\N
437	148	11	5	\N
438	148	12	5	\N
439	149	10	4	\N
440	149	11	4	\N
441	149	12	5	\N
442	150	10	2	\N
443	150	11	3	\N
444	150	12	3	\N
445	151	10	5	\N
446	151	11	4	\N
447	151	12	4	\N
448	152	10	4	\N
449	152	11	5	\N
450	152	12	5	\N
451	153	10	3	\N
452	153	11	4	\N
453	153	12	4	\N
454	154	10	5	\N
455	154	11	5	\N
456	154	12	4	\N
457	155	10	4	\N
458	155	11	3	\N
459	155	12	5	\N
460	156	10	5	\N
461	156	11	4	\N
462	156	12	4	\N
463	157	10	4	\N
464	157	11	5	\N
465	157	12	5	\N
466	160	10	4	\N
467	160	11	5	\N
468	160	12	4	\N
469	161	10	5	\N
470	161	11	4	\N
471	161	12	5	\N
472	162	10	3	\N
473	162	11	3	\N
474	162	12	4	\N
475	163	10	4	\N
476	163	11	4	\N
477	163	12	5	\N
478	164	10	5	\N
479	164	11	5	\N
480	164	12	4	\N
481	165	10	4	\N
482	165	11	3	\N
483	165	12	3	\N
484	166	10	5	\N
485	166	11	4	\N
486	166	12	5	\N
487	167	10	3	\N
488	167	11	5	\N
489	167	12	4	\N
490	168	10	4	\N
491	168	11	4	\N
492	168	12	4	\N
493	169	10	5	\N
494	169	11	5	\N
495	169	12	5	\N
496	170	10	2	\N
497	170	11	3	\N
498	170	12	3	\N
499	171	10	4	\N
500	171	11	4	\N
501	171	12	5	\N
502	172	10	5	\N
503	172	11	3	\N
504	172	12	4	\N
505	173	10	3	\N
506	173	11	5	\N
507	173	12	5	\N
508	176	10	4	\N
509	176	11	4	\N
510	176	12	5	\N
511	177	10	5	\N
512	177	11	5	\N
513	177	12	4	\N
514	178	10	3	\N
515	178	11	3	\N
516	178	12	3	\N
517	179	10	4	\N
518	179	11	5	\N
519	179	12	5	\N
520	180	10	5	\N
521	180	11	4	\N
522	180	12	4	\N
523	181	10	4	\N
524	181	11	3	\N
525	181	12	5	\N
526	182	10	5	\N
527	182	11	5	\N
528	182	12	4	\N
529	183	10	3	\N
530	183	11	4	\N
531	183	12	3	\N
532	184	10	4	\N
533	184	11	5	\N
534	184	12	5	\N
535	185	10	5	\N
536	185	11	4	\N
537	185	12	4	\N
538	186	10	2	\N
539	186	11	2	\N
540	186	12	3	\N
541	187	10	4	\N
542	187	11	4	\N
543	187	12	5	\N
544	188	10	5	\N
545	188	11	5	\N
546	188	12	4	\N
547	189	10	3	\N
548	189	11	3	\N
549	189	12	4	\N
550	190	10	4	\N
551	190	11	5	\N
552	190	12	5	\N
553	193	13	5	\N
554	193	14	4	\N
555	193	15	5	\N
556	194	13	4	\N
557	194	14	5	\N
558	194	15	4	\N
559	195	13	3	\N
560	195	14	3	\N
561	195	15	4	\N
562	196	13	5	\N
563	196	14	5	\N
564	196	15	5	\N
565	197	13	4	\N
566	197	14	4	\N
567	197	15	5	\N
568	198	13	2	\N
569	198	14	3	\N
570	198	15	3	\N
571	199	13	5	\N
572	199	14	4	\N
573	199	15	4	\N
574	200	13	4	\N
575	200	14	5	\N
576	200	15	5	\N
577	201	13	3	\N
578	201	14	4	\N
579	201	15	4	\N
580	202	13	5	\N
581	202	14	5	\N
582	202	15	4	\N
583	203	13	4	\N
584	203	14	3	\N
585	203	15	5	\N
586	204	13	5	\N
587	204	14	4	\N
588	204	15	4	\N
589	205	13	4	\N
590	205	14	5	\N
591	205	15	5	\N
592	208	13	4	\N
593	208	14	5	\N
594	208	15	4	\N
595	209	13	5	\N
596	209	14	4	\N
597	209	15	5	\N
598	210	13	3	\N
599	210	14	3	\N
600	210	15	4	\N
601	211	13	4	\N
602	211	14	4	\N
603	211	15	5	\N
604	212	13	5	\N
605	212	14	5	\N
606	212	15	4	\N
607	213	13	4	\N
608	213	14	3	\N
609	213	15	3	\N
610	214	13	5	\N
611	214	14	4	\N
612	214	15	5	\N
613	215	13	3	\N
614	215	14	5	\N
615	215	15	4	\N
616	216	13	4	\N
617	216	14	4	\N
618	216	15	4	\N
619	217	13	5	\N
620	217	14	5	\N
621	217	15	5	\N
622	218	13	2	\N
623	218	14	3	\N
624	218	15	3	\N
625	219	13	4	\N
626	219	14	4	\N
627	219	15	5	\N
628	220	13	5	\N
629	220	14	3	\N
630	220	15	4	\N
631	221	13	3	\N
632	221	14	5	\N
633	221	15	5	\N
634	224	13	4	\N
635	224	14	4	\N
636	224	15	5	\N
637	225	13	5	\N
638	225	14	5	\N
639	225	15	4	\N
640	226	13	3	\N
641	226	14	3	\N
642	226	15	3	\N
643	227	13	4	\N
644	227	14	5	\N
645	227	15	5	\N
646	228	13	5	\N
647	228	14	4	\N
648	228	15	4	\N
649	229	13	4	\N
650	229	14	3	\N
651	229	15	5	\N
652	230	13	5	\N
653	230	14	5	\N
654	230	15	4	\N
655	231	13	3	\N
656	231	14	4	\N
657	231	15	3	\N
658	232	13	4	\N
659	232	14	5	\N
660	232	15	5	\N
661	233	13	5	\N
662	233	14	4	\N
663	233	15	4	\N
664	234	13	2	\N
665	234	14	2	\N
666	234	15	3	\N
667	235	13	4	\N
668	235	14	4	\N
669	235	15	5	\N
670	236	13	5	\N
671	236	14	5	\N
672	236	15	4	\N
673	237	13	3	\N
674	237	14	3	\N
675	237	15	4	\N
676	238	13	4	\N
677	238	14	5	\N
678	238	15	5	\N
\.


--
-- Data for Name: groups; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.groups (id, name, direction_id) FROM stdin;
1	ИВТ-101	1
2	ИВТ-102	1
3	ИВТ-103	1
4	ПИ-201	2
5	ПИ-202	2
6	ПИ-203	2
7	ПМИ-301	3
8	ПМИ-302	3
9	ПМИ-303	3
10	ИБ-401	4
11	ИБ-402	4
12	ИБ-403	4
13	САУ-501	5
14	САУ-502	5
15	САУ-503	5
\.


--
-- Data for Name: student_extra_params; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.student_extra_params (id, student_id, param_def_id, num_value, text_value) FROM stdin;
817	1	21	52.00	\N
818	1	20	51.00	\N
819	1	19	\N	Мобильный клиент
820	1	18	\N	C++
821	2	21	53.00	\N
822	2	20	52.00	\N
823	2	19	\N	Аналитика логов
824	2	18	\N	Java
825	18	21	69.00	\N
826	18	20	68.00	\N
827	18	19	\N	IoT-шлюз
828	18	18	\N	Go
829	55	25	60.00	\N
830	55	24	59.00	\N
831	55	23	\N	Django+React
832	55	22	\N	backend
833	66	25	71.00	\N
834	66	24	70.00	\N
835	66	23	\N	Spring
836	66	22	\N	frontend
837	67	25	72.00	\N
838	67	24	71.00	\N
839	67	23	\N	Node.js
840	67	22	\N	QA
841	68	25	73.00	\N
842	68	24	72.00	\N
843	68	23	\N	Flutter
844	68	22	\N	DevOps
845	69	25	74.00	\N
846	69	24	73.00	\N
847	69	23	\N	.NET
848	69	22	\N	аналитик
849	70	25	75.00	\N
850	70	24	74.00	\N
851	70	23	\N	Django+React
852	70	22	\N	backend
853	71	25	76.00	\N
854	71	24	75.00	\N
855	71	23	\N	Spring
856	71	22	\N	frontend
857	72	25	77.00	\N
858	72	24	76.00	\N
859	72	23	\N	Node.js
860	72	22	\N	QA
861	73	25	78.00	\N
862	73	24	77.00	\N
863	73	23	\N	Flutter
864	73	22	\N	DevOps
865	74	25	79.00	\N
866	74	24	78.00	\N
867	74	23	\N	.NET
868	74	22	\N	аналитик
869	75	25	80.00	\N
870	75	24	79.00	\N
871	75	23	\N	Django+React
872	75	22	\N	backend
873	76	25	81.00	\N
874	76	24	80.00	\N
875	76	23	\N	Spring
876	76	22	\N	frontend
877	77	25	82.00	\N
878	77	24	81.00	\N
879	77	23	\N	Node.js
880	77	22	\N	QA
881	78	25	83.00	\N
882	78	24	82.00	\N
883	78	23	\N	Flutter
884	78	22	\N	DevOps
885	79	25	84.00	\N
886	79	24	83.00	\N
887	79	23	\N	.NET
888	79	22	\N	аналитик
889	80	25	85.00	\N
890	80	24	84.00	\N
891	80	23	\N	Django+React
892	80	22	\N	backend
893	81	25	86.00	\N
894	81	24	85.00	\N
895	81	23	\N	Spring
896	81	22	\N	frontend
897	82	25	87.00	\N
898	82	24	86.00	\N
899	82	23	\N	Node.js
900	82	22	\N	QA
901	83	25	88.00	\N
902	83	24	87.00	\N
903	83	23	\N	Flutter
904	83	22	\N	DevOps
905	84	25	89.00	\N
906	84	24	88.00	\N
907	84	23	\N	.NET
908	84	22	\N	аналитик
909	85	25	90.00	\N
910	85	24	89.00	\N
911	85	23	\N	Django+React
912	85	22	\N	backend
913	86	25	91.00	\N
914	86	24	90.00	\N
915	86	23	\N	Spring
916	86	22	\N	frontend
917	87	25	92.00	\N
918	87	24	91.00	\N
919	87	23	\N	Node.js
920	87	22	\N	QA
921	88	25	93.00	\N
922	88	24	92.00	\N
923	88	23	\N	Flutter
924	88	22	\N	DevOps
925	89	25	94.00	\N
926	89	24	93.00	\N
927	89	23	\N	.NET
928	89	22	\N	аналитик
929	90	25	95.00	\N
930	90	24	94.00	\N
931	90	23	\N	Django+React
932	90	22	\N	backend
933	91	25	96.00	\N
934	91	24	95.00	\N
935	91	23	\N	Spring
936	91	22	\N	frontend
937	92	25	97.00	\N
938	92	24	96.00	\N
939	92	23	\N	Node.js
940	92	22	\N	QA
941	93	25	98.00	\N
942	93	24	97.00	\N
943	93	23	\N	Flutter
944	93	22	\N	DevOps
945	94	25	99.00	\N
946	94	24	98.00	\N
947	94	23	\N	.NET
948	94	22	\N	аналитик
949	95	25	100.00	\N
950	95	24	99.00	\N
951	95	23	\N	Django+React
952	95	22	\N	backend
953	96	25	101.00	\N
954	96	24	100.00	\N
955	96	23	\N	Spring
956	96	22	\N	frontend
957	97	28	105.00	\N
958	97	27	104.00	\N
959	97	26	\N	графы
960	98	28	106.00	\N
961	98	27	105.00	\N
962	98	26	\N	численный анализ
963	99	28	107.00	\N
964	99	27	106.00	\N
965	99	26	\N	статистика
966	100	28	58.00	\N
967	100	27	57.00	\N
968	100	26	\N	ML
969	101	28	59.00	\N
970	101	27	58.00	\N
971	101	26	\N	оптимизация
972	102	28	60.00	\N
973	102	27	59.00	\N
974	102	26	\N	графы
975	103	28	61.00	\N
976	103	27	60.00	\N
977	103	26	\N	численный анализ
978	104	28	62.00	\N
979	104	27	61.00	\N
980	104	26	\N	статистика
981	105	28	63.00	\N
982	105	27	62.00	\N
983	105	26	\N	ML
984	106	28	64.00	\N
985	106	27	63.00	\N
986	106	26	\N	оптимизация
987	107	28	65.00	\N
988	107	27	64.00	\N
989	107	26	\N	графы
990	108	28	66.00	\N
991	108	27	65.00	\N
992	108	26	\N	численный анализ
993	109	28	67.00	\N
994	109	27	66.00	\N
995	109	26	\N	статистика
996	110	28	68.00	\N
997	110	27	67.00	\N
998	110	26	\N	ML
999	111	28	69.00	\N
1000	111	27	68.00	\N
1001	111	26	\N	оптимизация
1002	112	28	70.00	\N
1003	112	27	69.00	\N
1004	112	26	\N	графы
1005	113	28	71.00	\N
1006	113	27	70.00	\N
1007	113	26	\N	численный анализ
1008	114	28	72.00	\N
1009	114	27	71.00	\N
1010	114	26	\N	статистика
1011	115	28	73.00	\N
1012	115	27	72.00	\N
1013	115	26	\N	ML
1014	116	28	74.00	\N
1015	116	27	73.00	\N
1016	116	26	\N	оптимизация
1017	129	28	87.00	\N
1018	129	27	86.00	\N
1019	129	26	\N	статистика
1020	130	28	88.00	\N
1021	130	27	87.00	\N
1022	130	26	\N	ML
1023	131	28	89.00	\N
1024	131	27	88.00	\N
1025	131	26	\N	оптимизация
1026	132	28	90.00	\N
1027	132	27	89.00	\N
1028	132	26	\N	графы
1029	133	28	91.00	\N
1030	133	27	90.00	\N
1031	133	26	\N	численный анализ
1032	134	28	92.00	\N
1033	134	27	91.00	\N
1034	134	26	\N	статистика
1035	135	28	93.00	\N
1036	135	27	92.00	\N
1037	135	26	\N	ML
1038	136	28	94.00	\N
1039	136	27	93.00	\N
1040	136	26	\N	оптимизация
1041	137	28	95.00	\N
1042	137	27	94.00	\N
1043	137	26	\N	графы
1044	138	28	96.00	\N
1045	138	27	95.00	\N
1046	138	26	\N	численный анализ
1047	139	28	97.00	\N
1048	139	27	96.00	\N
1049	139	26	\N	статистика
1050	140	28	98.00	\N
1051	140	27	97.00	\N
1052	140	26	\N	ML
1053	141	28	99.00	\N
1054	141	27	98.00	\N
1055	141	26	\N	оптимизация
1056	142	28	100.00	\N
1057	142	27	99.00	\N
1058	142	26	\N	графы
1059	143	28	101.00	\N
1060	143	27	100.00	\N
1061	143	26	\N	численный анализ
1062	144	28	102.00	\N
1063	144	27	101.00	\N
1064	144	26	\N	статистика
1065	145	31	96.00	\N
1066	145	30	95.00	\N
1067	145	29	\N	OSCP prep
1068	146	31	97.00	\N
1069	146	30	96.00	\N
1070	146	29	\N	CompTIA Security+
1071	147	31	98.00	\N
1072	147	30	97.00	\N
1073	147	29	\N	Cisco CCNA
1074	148	31	99.00	\N
1075	148	30	98.00	\N
1076	148	29	\N	нет
1077	149	31	100.00	\N
1078	149	30	99.00	\N
1079	149	29	\N	CEH intro
1080	150	31	51.00	\N
1081	150	30	50.00	\N
1082	150	29	\N	OSCP prep
1083	151	31	52.00	\N
1084	151	30	51.00	\N
1085	151	29	\N	CompTIA Security+
1086	152	31	53.00	\N
1087	152	30	52.00	\N
1088	152	29	\N	Cisco CCNA
1089	153	31	54.00	\N
1090	153	30	53.00	\N
1091	153	29	\N	нет
1092	154	31	55.00	\N
1093	154	30	54.00	\N
1094	154	29	\N	CEH intro
1095	155	31	56.00	\N
1096	155	30	55.00	\N
1097	155	29	\N	OSCP prep
1098	156	31	57.00	\N
1099	156	30	56.00	\N
1100	156	29	\N	CompTIA Security+
1101	157	31	58.00	\N
1102	157	30	57.00	\N
1103	157	29	\N	Cisco CCNA
1104	158	31	59.00	\N
1105	158	30	58.00	\N
1106	158	29	\N	нет
1107	159	31	60.00	\N
1108	159	30	59.00	\N
1109	159	29	\N	CEH intro
1110	160	31	61.00	\N
1111	160	30	60.00	\N
1112	160	29	\N	OSCP prep
1113	161	31	62.00	\N
1114	161	30	61.00	\N
1115	161	29	\N	CompTIA Security+
1116	162	31	63.00	\N
1117	162	30	62.00	\N
1118	162	29	\N	Cisco CCNA
1119	163	31	64.00	\N
1120	163	30	63.00	\N
1121	163	29	\N	нет
1122	164	31	65.00	\N
1123	164	30	64.00	\N
1124	164	29	\N	CEH intro
1125	165	31	66.00	\N
1126	165	30	65.00	\N
1127	165	29	\N	OSCP prep
1128	166	31	67.00	\N
1129	166	30	66.00	\N
1130	166	29	\N	CompTIA Security+
1131	167	31	68.00	\N
1132	167	30	67.00	\N
1133	167	29	\N	Cisco CCNA
1134	185	31	86.00	\N
1135	185	30	85.00	\N
1136	185	29	\N	OSCP prep
1137	186	31	87.00	\N
1138	186	30	86.00	\N
1139	186	29	\N	CompTIA Security+
1140	187	31	88.00	\N
1141	187	30	87.00	\N
1142	187	29	\N	Cisco CCNA
1143	188	31	89.00	\N
1144	188	30	88.00	\N
1145	188	29	\N	нет
1146	189	31	90.00	\N
1147	189	30	89.00	\N
1148	189	29	\N	CEH intro
1149	190	31	91.00	\N
1150	190	30	90.00	\N
1151	190	29	\N	OSCP prep
1152	191	31	92.00	\N
1153	191	30	91.00	\N
1154	191	29	\N	CompTIA Security+
1155	192	31	93.00	\N
1156	192	30	92.00	\N
1157	192	29	\N	Cisco CCNA
1158	193	34	97.00	\N
1159	193	33	96.00	\N
1160	193	32	\N	энергетика
1161	194	34	98.00	\N
1162	194	33	97.00	\N
1163	194	32	\N	ритейл
1164	195	34	99.00	\N
1165	195	33	98.00	\N
1166	195	32	\N	логистика
1167	196	34	100.00	\N
1168	196	33	99.00	\N
1169	196	32	\N	банк
1170	197	34	101.00	\N
1171	197	33	100.00	\N
1172	197	32	\N	медицина
1173	198	34	102.00	\N
1174	198	33	101.00	\N
1175	198	32	\N	энергетика
1176	199	34	103.00	\N
1177	199	33	102.00	\N
1178	199	32	\N	ритейл
1179	200	34	54.00	\N
1180	200	33	53.00	\N
1181	200	32	\N	логистика
1182	201	34	55.00	\N
1183	201	33	54.00	\N
1184	201	32	\N	банк
1185	202	34	56.00	\N
1186	202	33	55.00	\N
1187	202	32	\N	медицина
1188	203	34	57.00	\N
1189	203	33	56.00	\N
1190	203	32	\N	энергетика
1191	204	34	58.00	\N
1192	204	33	57.00	\N
1193	204	32	\N	ритейл
1194	205	34	59.00	\N
1195	205	33	58.00	\N
1196	205	32	\N	логистика
1197	206	34	60.00	\N
1198	206	33	59.00	\N
1199	206	32	\N	банк
1200	207	34	61.00	\N
1201	207	33	60.00	\N
1202	207	32	\N	медицина
1203	208	34	62.00	\N
1204	208	33	61.00	\N
1205	208	32	\N	энергетика
1206	209	34	63.00	\N
1207	209	33	62.00	\N
1208	209	32	\N	ритейл
1209	210	34	64.00	\N
1210	210	33	63.00	\N
1211	210	32	\N	логистика
1212	211	34	65.00	\N
1213	211	33	64.00	\N
1214	211	32	\N	банк
1215	212	34	66.00	\N
1216	212	33	65.00	\N
1217	212	32	\N	медицина
1218	213	34	67.00	\N
1219	213	33	66.00	\N
1220	213	32	\N	энергетика
1221	214	34	68.00	\N
1222	214	33	67.00	\N
1223	214	32	\N	ритейл
1224	215	34	69.00	\N
1225	215	33	68.00	\N
1226	215	32	\N	логистика
1227	216	34	70.00	\N
1228	216	33	69.00	\N
1229	216	32	\N	банк
1230	217	34	71.00	\N
1231	217	33	70.00	\N
1232	217	32	\N	медицина
1233	218	34	72.00	\N
1234	218	33	71.00	\N
1235	218	32	\N	энергетика
1236	219	34	73.00	\N
1237	219	33	72.00	\N
1238	219	32	\N	ритейл
1239	220	34	74.00	\N
1240	220	33	73.00	\N
1241	220	32	\N	логистика
1242	221	34	75.00	\N
1243	221	33	74.00	\N
1244	221	32	\N	банк
1245	222	34	76.00	\N
1246	222	33	75.00	\N
1247	222	32	\N	медицина
1248	223	34	77.00	\N
1249	223	33	76.00	\N
1250	223	32	\N	энергетика
1251	224	34	78.00	\N
1252	224	33	77.00	\N
1253	224	32	\N	ритейл
1254	225	34	79.00	\N
1255	225	33	78.00	\N
1256	225	32	\N	логистика
1257	226	34	80.00	\N
1258	226	33	79.00	\N
1259	226	32	\N	банк
1260	227	34	81.00	\N
1261	227	33	80.00	\N
1262	227	32	\N	медицина
1263	228	34	82.00	\N
1264	228	33	81.00	\N
1265	228	32	\N	энергетика
1266	229	34	83.00	\N
1267	229	33	82.00	\N
1268	229	32	\N	ритейл
1269	230	34	84.00	\N
1270	230	33	83.00	\N
1271	230	32	\N	логистика
1272	231	34	85.00	\N
1273	231	33	84.00	\N
1274	231	32	\N	банк
1275	232	34	86.00	\N
1276	232	33	85.00	\N
1277	232	32	\N	медицина
1278	233	34	87.00	\N
1279	233	33	86.00	\N
1280	233	32	\N	энергетика
1281	234	34	88.00	\N
1282	234	33	87.00	\N
1283	234	32	\N	ритейл
1284	235	34	89.00	\N
1285	235	33	88.00	\N
1286	235	32	\N	логистика
1287	236	34	90.00	\N
1288	236	33	89.00	\N
1289	236	32	\N	банк
1290	237	34	91.00	\N
1291	237	33	90.00	\N
1292	237	32	\N	медицина
1293	238	34	92.00	\N
1294	238	33	91.00	\N
1295	238	32	\N	энергетика
1296	239	34	93.00	\N
1297	239	33	92.00	\N
1298	239	32	\N	ритейл
1299	240	34	94.00	\N
1300	240	33	93.00	\N
1301	240	32	\N	логистика
1302	3	21	54.00	\N
1303	3	20	53.00	\N
1304	3	19	\N	IoT-шлюз
1305	3	18	\N	Go
1306	4	21	55.00	\N
1307	4	20	54.00	\N
1308	4	19	\N	Чат-бот
1309	4	18	\N	Rust
1310	5	21	56.00	\N
1311	5	20	55.00	\N
1312	5	19	\N	Система учёта
1313	5	18	\N	Python
1314	6	21	57.00	\N
1315	6	20	56.00	\N
1316	6	19	\N	Мобильный клиент
1317	6	18	\N	C++
1318	7	21	58.00	\N
1319	7	20	57.00	\N
1320	7	19	\N	Аналитика логов
1321	7	18	\N	Java
1322	8	21	59.00	\N
1323	8	20	58.00	\N
1324	8	19	\N	IoT-шлюз
1325	8	18	\N	Go
1326	9	21	60.00	\N
1327	9	20	59.00	\N
1328	9	19	\N	Чат-бот
1329	9	18	\N	Rust
1330	10	21	61.00	\N
1331	10	20	60.00	\N
1332	10	19	\N	Система учёта
1333	10	18	\N	Python
1334	11	21	62.00	\N
1335	11	20	61.00	\N
1336	11	19	\N	Мобильный клиент
1337	11	18	\N	C++
1338	12	21	63.00	\N
1339	12	20	62.00	\N
1340	12	19	\N	Аналитика логов
1341	12	18	\N	Java
1342	13	21	64.00	\N
1343	13	20	63.00	\N
1344	13	19	\N	IoT-шлюз
1345	13	18	\N	Go
1346	14	21	65.00	\N
1347	14	20	64.00	\N
1348	14	19	\N	Чат-бот
1349	14	18	\N	Rust
1350	15	21	66.00	\N
1351	15	20	65.00	\N
1352	15	19	\N	Система учёта
1353	15	18	\N	Python
1354	16	21	67.00	\N
1355	16	20	66.00	\N
1356	16	19	\N	Мобильный клиент
1357	16	18	\N	C++
1358	17	21	68.00	\N
1359	17	20	67.00	\N
1360	17	19	\N	Аналитика логов
1361	17	18	\N	Java
1362	117	28	75.00	\N
1363	117	27	74.00	\N
1364	117	26	\N	графы
1365	118	28	76.00	\N
1366	118	27	75.00	\N
1367	118	26	\N	численный анализ
1368	119	28	77.00	\N
1369	119	27	76.00	\N
1370	119	26	\N	статистика
1371	19	21	70.00	\N
1372	19	20	69.00	\N
1373	19	19	\N	Чат-бот
1374	19	18	\N	Rust
1375	20	21	71.00	\N
1376	20	20	70.00	\N
1377	20	19	\N	Система учёта
1378	20	18	\N	Python
1379	21	21	72.00	\N
1380	21	20	71.00	\N
1381	21	19	\N	Мобильный клиент
1382	21	18	\N	C++
1383	22	21	73.00	\N
1384	22	20	72.00	\N
1385	22	19	\N	Аналитика логов
1386	22	18	\N	Java
1387	23	21	74.00	\N
1388	23	20	73.00	\N
1389	23	19	\N	IoT-шлюз
1390	23	18	\N	Go
1391	24	21	75.00	\N
1392	24	20	74.00	\N
1393	24	19	\N	Чат-бот
1394	24	18	\N	Rust
1395	25	21	76.00	\N
1396	25	20	75.00	\N
1397	25	19	\N	Система учёта
1398	25	18	\N	Python
1399	26	21	77.00	\N
1400	26	20	76.00	\N
1401	26	19	\N	Мобильный клиент
1402	26	18	\N	C++
1403	27	21	78.00	\N
1404	27	20	77.00	\N
1405	27	19	\N	Аналитика логов
1406	27	18	\N	Java
1407	28	21	79.00	\N
1408	28	20	78.00	\N
1409	28	19	\N	IoT-шлюз
1410	28	18	\N	Go
1411	29	21	80.00	\N
1412	29	20	79.00	\N
1413	29	19	\N	Чат-бот
1414	29	18	\N	Rust
1415	30	21	81.00	\N
1416	30	20	80.00	\N
1417	30	19	\N	Система учёта
1418	30	18	\N	Python
1419	31	21	82.00	\N
1420	31	20	81.00	\N
1421	31	19	\N	Мобильный клиент
1422	31	18	\N	C++
1423	32	21	83.00	\N
1424	32	20	82.00	\N
1425	32	19	\N	Аналитика логов
1426	32	18	\N	Java
1427	33	21	84.00	\N
1428	33	20	83.00	\N
1429	33	19	\N	IoT-шлюз
1430	33	18	\N	Go
1431	34	21	85.00	\N
1432	34	20	84.00	\N
1433	34	19	\N	Чат-бот
1434	34	18	\N	Rust
1435	35	21	86.00	\N
1436	35	20	85.00	\N
1437	35	19	\N	Система учёта
1438	35	18	\N	Python
1439	36	21	87.00	\N
1440	36	20	86.00	\N
1441	36	19	\N	Мобильный клиент
1442	36	18	\N	C++
1443	37	21	88.00	\N
1444	37	20	87.00	\N
1445	37	19	\N	Аналитика логов
1446	37	18	\N	Java
1447	38	21	89.00	\N
1448	38	20	88.00	\N
1449	38	19	\N	IoT-шлюз
1450	38	18	\N	Go
1451	39	21	90.00	\N
1452	39	20	89.00	\N
1453	39	19	\N	Чат-бот
1454	39	18	\N	Rust
1455	40	21	91.00	\N
1456	40	20	90.00	\N
1457	40	19	\N	Система учёта
1458	40	18	\N	Python
1459	41	21	92.00	\N
1460	41	20	91.00	\N
1461	41	19	\N	Мобильный клиент
1462	41	18	\N	C++
1463	42	21	93.00	\N
1464	42	20	92.00	\N
1465	42	19	\N	Аналитика логов
1466	42	18	\N	Java
1467	43	21	94.00	\N
1468	43	20	93.00	\N
1469	43	19	\N	IoT-шлюз
1470	43	18	\N	Go
1471	44	21	95.00	\N
1472	44	20	94.00	\N
1473	44	19	\N	Чат-бот
1474	44	18	\N	Rust
1475	45	21	96.00	\N
1476	45	20	95.00	\N
1477	45	19	\N	Система учёта
1478	45	18	\N	Python
1479	46	21	97.00	\N
1480	46	20	96.00	\N
1481	46	19	\N	Мобильный клиент
1482	46	18	\N	C++
1483	47	21	98.00	\N
1484	47	20	97.00	\N
1485	47	19	\N	Аналитика логов
1486	47	18	\N	Java
1487	48	21	99.00	\N
1488	48	20	98.00	\N
1489	48	19	\N	IoT-шлюз
1490	48	18	\N	Go
1491	49	25	104.00	\N
1492	49	24	103.00	\N
1493	49	23	\N	.NET
1494	49	22	\N	аналитик
1495	120	28	78.00	\N
1496	120	27	77.00	\N
1497	120	26	\N	ML
1498	121	28	79.00	\N
1499	121	27	78.00	\N
1500	121	26	\N	оптимизация
1501	122	28	80.00	\N
1502	122	27	79.00	\N
1503	122	26	\N	графы
1504	123	28	81.00	\N
1505	123	27	80.00	\N
1506	123	26	\N	численный анализ
1507	124	28	82.00	\N
1508	124	27	81.00	\N
1509	124	26	\N	статистика
1510	125	28	83.00	\N
1511	125	27	82.00	\N
1512	125	26	\N	ML
1513	126	28	84.00	\N
1514	126	27	83.00	\N
1515	126	26	\N	оптимизация
1516	127	28	85.00	\N
1517	127	27	84.00	\N
1518	127	26	\N	графы
1519	128	28	86.00	\N
1520	128	27	85.00	\N
1521	128	26	\N	численный анализ
1522	50	25	55.00	\N
1523	50	24	54.00	\N
1524	50	23	\N	Django+React
1525	50	22	\N	backend
1526	51	25	56.00	\N
1527	51	24	55.00	\N
1528	51	23	\N	Spring
1529	51	22	\N	frontend
1530	52	25	57.00	\N
1531	52	24	56.00	\N
1532	52	23	\N	Node.js
1533	52	22	\N	QA
1534	53	25	58.00	\N
1535	53	24	57.00	\N
1536	53	23	\N	Flutter
1537	53	22	\N	DevOps
1538	54	25	59.00	\N
1539	54	24	58.00	\N
1540	54	23	\N	.NET
1541	54	22	\N	аналитик
1542	56	25	61.00	\N
1543	56	24	60.00	\N
1544	56	23	\N	Spring
1545	56	22	\N	frontend
1546	57	25	62.00	\N
1547	57	24	61.00	\N
1548	57	23	\N	Node.js
1549	57	22	\N	QA
1550	58	25	63.00	\N
1551	58	24	62.00	\N
1552	58	23	\N	Flutter
1553	58	22	\N	DevOps
1554	59	25	64.00	\N
1555	59	24	63.00	\N
1556	59	23	\N	.NET
1557	59	22	\N	аналитик
1558	60	25	65.00	\N
1559	60	24	64.00	\N
1560	60	23	\N	Django+React
1561	60	22	\N	backend
1562	61	25	66.00	\N
1563	61	24	65.00	\N
1564	61	23	\N	Spring
1565	61	22	\N	frontend
1566	62	25	67.00	\N
1567	62	24	66.00	\N
1568	62	23	\N	Node.js
1569	62	22	\N	QA
1570	63	25	68.00	\N
1571	63	24	67.00	\N
1572	63	23	\N	Flutter
1573	63	22	\N	DevOps
1574	64	25	69.00	\N
1575	64	24	68.00	\N
1576	64	23	\N	.NET
1577	64	22	\N	аналитик
1578	65	25	70.00	\N
1579	65	24	69.00	\N
1580	65	23	\N	Django+React
1581	65	22	\N	backend
1582	168	31	69.00	\N
1583	168	30	68.00	\N
1584	168	29	\N	нет
1585	169	31	70.00	\N
1586	169	30	69.00	\N
1587	169	29	\N	CEH intro
1588	170	31	71.00	\N
1589	170	30	70.00	\N
1590	170	29	\N	OSCP prep
1591	171	31	72.00	\N
1592	171	30	71.00	\N
1593	171	29	\N	CompTIA Security+
1594	172	31	73.00	\N
1595	172	30	72.00	\N
1596	172	29	\N	Cisco CCNA
1597	173	31	74.00	\N
1598	173	30	73.00	\N
1599	173	29	\N	нет
1600	174	31	75.00	\N
1601	174	30	74.00	\N
1602	174	29	\N	CEH intro
1603	175	31	76.00	\N
1604	175	30	75.00	\N
1605	175	29	\N	OSCP prep
1606	176	31	77.00	\N
1607	176	30	76.00	\N
1608	176	29	\N	CompTIA Security+
1609	177	31	78.00	\N
1610	177	30	77.00	\N
1611	177	29	\N	Cisco CCNA
1612	178	31	79.00	\N
1613	178	30	78.00	\N
1614	178	29	\N	нет
1615	179	31	80.00	\N
1616	179	30	79.00	\N
1617	179	29	\N	CEH intro
1618	180	31	81.00	\N
1619	180	30	80.00	\N
1620	180	29	\N	OSCP prep
1621	181	31	82.00	\N
1622	181	30	81.00	\N
1623	181	29	\N	CompTIA Security+
1624	182	31	83.00	\N
1625	182	30	82.00	\N
1626	182	29	\N	Cisco CCNA
1627	183	31	84.00	\N
1628	183	30	83.00	\N
1629	183	29	\N	нет
1630	184	31	85.00	\N
1631	184	30	84.00	\N
1632	184	29	\N	CEH intro
\.


--
-- Data for Name: students; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.students (id, last_name, first_name, middle_name, birth_date, city, street, house_number, email, group_id, is_budget) FROM stdin;
1	\N	\N	\N	\N	\N	\N	\N	\N	1	t
2	\N	\N	\N	\N	\N	\N	\N	\N	1	t
18	\N	\N	\N	\N	\N	\N	\N	\N	2	f
106	\N	\N	\N	\N	\N	\N	\N	\N	7	t
67	\N	\N	\N	\N	\N	\N	\N	\N	5	t
32	\N	\N	\N	\N	\N	\N	\N	\N	3	t
33	\N	\N	\N	\N	\N	\N	\N	\N	3	t
34	\N	\N	\N	\N	\N	\N	\N	\N	3	f
35	\N	\N	\N	\N	\N	\N	\N	\N	3	t
36	\N	\N	\N	\N	\N	\N	\N	\N	3	t
37	\N	\N	\N	\N	\N	\N	\N	\N	3	t
38	\N	\N	\N	\N	\N	\N	\N	\N	3	f
39	\N	\N	\N	\N	\N	\N	\N	\N	3	t
40	\N	\N	\N	\N	\N	\N	\N	\N	3	t
41	\N	\N	\N	\N	\N	\N	\N	\N	3	t
42	\N	\N	\N	\N	\N	\N	\N	\N	3	f
43	\N	\N	\N	\N	\N	\N	\N	\N	3	t
44	\N	\N	\N	\N	\N	\N	\N	\N	3	t
45	\N	\N	\N	\N	\N	\N	\N	\N	3	t
46	\N	\N	\N	\N	\N	\N	\N	\N	3	f
47	\N	\N	\N	\N	\N	\N	\N	\N	3	t
48	\N	\N	\N	\N	\N	\N	\N	\N	3	t
49	\N	\N	\N	\N	\N	\N	\N	\N	4	t
120	\N	\N	\N	\N	\N	\N	\N	\N	8	t
188	\N	\N	\N	\N	\N	\N	\N	\N	12	t
189	\N	\N	\N	\N	\N	\N	\N	\N	12	t
190	\N	\N	\N	\N	\N	\N	\N	\N	12	f
191	\N	\N	\N	\N	\N	\N	\N	\N	12	t
192	\N	\N	\N	\N	\N	\N	\N	\N	12	t
193	\N	\N	\N	\N	\N	\N	\N	\N	13	t
194	\N	\N	\N	\N	\N	\N	\N	\N	13	t
95	\N	\N	\N	\N	\N	\N	\N	\N	6	t
96	\N	\N	\N	\N	\N	\N	\N	\N	6	t
97	\N	\N	\N	\N	\N	\N	\N	\N	7	t
98	\N	\N	\N	\N	\N	\N	\N	\N	7	t
99	\N	\N	\N	\N	\N	\N	\N	\N	7	f
100	\N	\N	\N	\N	\N	\N	\N	\N	7	t
101	\N	\N	\N	\N	\N	\N	\N	\N	7	t
102	\N	\N	\N	\N	\N	\N	\N	\N	7	t
103	\N	\N	\N	\N	\N	\N	\N	\N	7	f
104	\N	\N	\N	\N	\N	\N	\N	\N	7	t
121	\N	\N	\N	\N	\N	\N	\N	\N	8	t
122	\N	\N	\N	\N	\N	\N	\N	\N	8	f
105	\N	\N	\N	\N	\N	\N	\N	\N	7	t
107	\N	\N	\N	\N	\N	\N	\N	\N	7	f
123	\N	\N	\N	\N	\N	\N	\N	\N	8	t
124	\N	\N	\N	\N	\N	\N	\N	\N	8	t
125	\N	\N	\N	\N	\N	\N	\N	\N	8	t
126	\N	\N	\N	\N	\N	\N	\N	\N	8	f
127	\N	\N	\N	\N	\N	\N	\N	\N	8	t
128	\N	\N	\N	\N	\N	\N	\N	\N	9	t
50	\N	\N	\N	\N	\N	\N	\N	\N	4	t
51	\N	\N	\N	\N	\N	\N	\N	\N	4	f
52	\N	\N	\N	\N	\N	\N	\N	\N	4	t
55	\N	\N	\N	\N	\N	\N	\N	\N	4	f
206	\N	\N	\N	\N	\N	\N	\N	\N	13	t
207	\N	\N	\N	\N	\N	\N	\N	\N	13	f
22	\N	\N	\N	\N	\N	\N	\N	\N	2	f
23	\N	\N	\N	\N	\N	\N	\N	\N	2	t
53	\N	\N	\N	\N	\N	\N	\N	\N	4	t
54	\N	\N	\N	\N	\N	\N	\N	\N	4	t
56	\N	\N	\N	\N	\N	\N	\N	\N	4	t
57	\N	\N	\N	\N	\N	\N	\N	\N	4	t
58	\N	\N	\N	\N	\N	\N	\N	\N	4	t
59	\N	\N	\N	\N	\N	\N	\N	\N	4	f
60	\N	\N	\N	\N	\N	\N	\N	\N	4	t
61	\N	\N	\N	\N	\N	\N	\N	\N	4	t
62	\N	\N	\N	\N	\N	\N	\N	\N	4	t
63	\N	\N	\N	\N	\N	\N	\N	\N	4	f
64	\N	\N	\N	\N	\N	\N	\N	\N	5	t
65	\N	\N	\N	\N	\N	\N	\N	\N	5	t
168	\N	\N	\N	\N	\N	\N	\N	\N	11	t
169	\N	\N	\N	\N	\N	\N	\N	\N	11	t
170	\N	\N	\N	\N	\N	\N	\N	\N	11	f
171	\N	\N	\N	\N	\N	\N	\N	\N	11	t
172	\N	\N	\N	\N	\N	\N	\N	\N	11	t
173	\N	\N	\N	\N	\N	\N	\N	\N	11	t
174	\N	\N	\N	\N	\N	\N	\N	\N	11	f
175	\N	\N	\N	\N	\N	\N	\N	\N	11	t
176	\N	\N	\N	\N	\N	\N	\N	\N	12	t
177	\N	\N	\N	\N	\N	\N	\N	\N	12	t
178	\N	\N	\N	\N	\N	\N	\N	\N	12	f
179	\N	\N	\N	\N	\N	\N	\N	\N	12	t
180	\N	\N	\N	\N	\N	\N	\N	\N	12	t
181	\N	\N	\N	\N	\N	\N	\N	\N	12	t
182	\N	\N	\N	\N	\N	\N	\N	\N	12	f
183	\N	\N	\N	\N	\N	\N	\N	\N	12	t
184	\N	\N	\N	\N	\N	\N	\N	\N	12	t
66	\N	\N	\N	\N	\N	\N	\N	\N	5	f
71	\N	\N	\N	\N	\N	\N	\N	\N	5	t
72	\N	\N	\N	\N	\N	\N	\N	\N	5	t
73	\N	\N	\N	\N	\N	\N	\N	\N	5	t
74	\N	\N	\N	\N	\N	\N	\N	\N	5	f
75	\N	\N	\N	\N	\N	\N	\N	\N	5	t
76	\N	\N	\N	\N	\N	\N	\N	\N	5	t
77	\N	\N	\N	\N	\N	\N	\N	\N	5	t
108	\N	\N	\N	\N	\N	\N	\N	\N	7	t
109	\N	\N	\N	\N	\N	\N	\N	\N	7	t
110	\N	\N	\N	\N	\N	\N	\N	\N	7	t
111	\N	\N	\N	\N	\N	\N	\N	\N	7	f
112	\N	\N	\N	\N	\N	\N	\N	\N	8	t
113	\N	\N	\N	\N	\N	\N	\N	\N	8	t
114	\N	\N	\N	\N	\N	\N	\N	\N	8	f
115	\N	\N	\N	\N	\N	\N	\N	\N	8	t
116	\N	\N	\N	\N	\N	\N	\N	\N	8	t
129	\N	\N	\N	\N	\N	\N	\N	\N	9	t
68	\N	\N	\N	\N	\N	\N	\N	\N	5	t
69	\N	\N	\N	\N	\N	\N	\N	\N	5	t
70	\N	\N	\N	\N	\N	\N	\N	\N	5	f
133	\N	\N	\N	\N	\N	\N	\N	\N	9	t
134	\N	\N	\N	\N	\N	\N	\N	\N	9	f
135	\N	\N	\N	\N	\N	\N	\N	\N	9	t
136	\N	\N	\N	\N	\N	\N	\N	\N	9	t
4	\N	\N	\N	\N	\N	\N	\N	\N	1	t
5	\N	\N	\N	\N	\N	\N	\N	\N	1	t
137	\N	\N	\N	\N	\N	\N	\N	\N	9	t
138	\N	\N	\N	\N	\N	\N	\N	\N	9	f
140	\N	\N	\N	\N	\N	\N	\N	\N	9	t
141	\N	\N	\N	\N	\N	\N	\N	\N	9	t
142	\N	\N	\N	\N	\N	\N	\N	\N	9	f
143	\N	\N	\N	\N	\N	\N	\N	\N	9	t
144	\N	\N	\N	\N	\N	\N	\N	\N	9	t
145	\N	\N	\N	\N	\N	\N	\N	\N	10	t
146	\N	\N	\N	\N	\N	\N	\N	\N	10	t
147	\N	\N	\N	\N	\N	\N	\N	\N	10	f
148	\N	\N	\N	\N	\N	\N	\N	\N	10	t
149	\N	\N	\N	\N	\N	\N	\N	\N	10	t
150	\N	\N	\N	\N	\N	\N	\N	\N	10	t
151	\N	\N	\N	\N	\N	\N	\N	\N	10	f
219	\N	\N	\N	\N	\N	\N	\N	\N	14	t
220	\N	\N	\N	\N	\N	\N	\N	\N	14	t
221	\N	\N	\N	\N	\N	\N	\N	\N	14	t
240	\N	\N	\N	\N	\N	\N	\N	\N	15	t
3	\N	\N	\N	\N	\N	\N	\N	\N	1	f
25	\N	\N	\N	\N	\N	\N	\N	\N	2	t
26	\N	\N	\N	\N	\N	\N	\N	\N	2	f
27	\N	\N	\N	\N	\N	\N	\N	\N	2	t
28	\N	\N	\N	\N	\N	\N	\N	\N	2	t
29	\N	\N	\N	\N	\N	\N	\N	\N	2	t
30	\N	\N	\N	\N	\N	\N	\N	\N	2	f
31	\N	\N	\N	\N	\N	\N	\N	\N	2	t
152	\N	\N	\N	\N	\N	\N	\N	\N	10	t
153	\N	\N	\N	\N	\N	\N	\N	\N	10	t
154	\N	\N	\N	\N	\N	\N	\N	\N	10	t
155	\N	\N	\N	\N	\N	\N	\N	\N	10	f
156	\N	\N	\N	\N	\N	\N	\N	\N	10	t
157	\N	\N	\N	\N	\N	\N	\N	\N	10	t
158	\N	\N	\N	\N	\N	\N	\N	\N	10	t
159	\N	\N	\N	\N	\N	\N	\N	\N	10	f
6	\N	\N	\N	\N	\N	\N	\N	\N	1	f
7	\N	\N	\N	\N	\N	\N	\N	\N	1	t
8	\N	\N	\N	\N	\N	\N	\N	\N	1	t
9	\N	\N	\N	\N	\N	\N	\N	\N	1	f
10	\N	\N	\N	\N	\N	\N	\N	\N	1	t
11	\N	\N	\N	\N	\N	\N	\N	\N	1	t
12	\N	\N	\N	\N	\N	\N	\N	\N	1	t
13	\N	\N	\N	\N	\N	\N	\N	\N	1	f
14	\N	\N	\N	\N	\N	\N	\N	\N	1	t
15	\N	\N	\N	\N	\N	\N	\N	\N	1	t
16	\N	\N	\N	\N	\N	\N	\N	\N	2	t
17	\N	\N	\N	\N	\N	\N	\N	\N	2	t
117	\N	\N	\N	\N	\N	\N	\N	\N	8	t
118	\N	\N	\N	\N	\N	\N	\N	\N	8	f
119	\N	\N	\N	\N	\N	\N	\N	\N	8	t
19	\N	\N	\N	\N	\N	\N	\N	\N	2	t
20	\N	\N	\N	\N	\N	\N	\N	\N	2	t
21	\N	\N	\N	\N	\N	\N	\N	\N	2	t
24	\N	\N	\N	\N	\N	\N	\N	\N	2	t
160	\N	\N	\N	\N	\N	\N	\N	\N	11	t
161	\N	\N	\N	\N	\N	\N	\N	\N	11	t
162	\N	\N	\N	\N	\N	\N	\N	\N	11	f
163	\N	\N	\N	\N	\N	\N	\N	\N	11	t
164	\N	\N	\N	\N	\N	\N	\N	\N	11	t
165	\N	\N	\N	\N	\N	\N	\N	\N	11	t
166	\N	\N	\N	\N	\N	\N	\N	\N	11	f
167	\N	\N	\N	\N	\N	\N	\N	\N	11	t
185	\N	\N	\N	\N	\N	\N	\N	\N	12	t
186	\N	\N	\N	\N	\N	\N	\N	\N	12	f
187	\N	\N	\N	\N	\N	\N	\N	\N	12	t
195	\N	\N	\N	\N	\N	\N	\N	\N	13	f
196	\N	\N	\N	\N	\N	\N	\N	\N	13	t
197	\N	\N	\N	\N	\N	\N	\N	\N	13	t
198	\N	\N	\N	\N	\N	\N	\N	\N	13	t
199	\N	\N	\N	\N	\N	\N	\N	\N	13	f
200	\N	\N	\N	\N	\N	\N	\N	\N	13	t
201	\N	\N	\N	\N	\N	\N	\N	\N	13	t
202	\N	\N	\N	\N	\N	\N	\N	\N	13	t
203	\N	\N	\N	\N	\N	\N	\N	\N	13	f
204	\N	\N	\N	\N	\N	\N	\N	\N	13	t
205	\N	\N	\N	\N	\N	\N	\N	\N	13	t
85	\N	\N	\N	\N	\N	\N	\N	\N	6	t
86	\N	\N	\N	\N	\N	\N	\N	\N	6	f
87	\N	\N	\N	\N	\N	\N	\N	\N	6	t
88	\N	\N	\N	\N	\N	\N	\N	\N	6	t
89	\N	\N	\N	\N	\N	\N	\N	\N	6	t
90	\N	\N	\N	\N	\N	\N	\N	\N	6	f
91	\N	\N	\N	\N	\N	\N	\N	\N	6	t
92	\N	\N	\N	\N	\N	\N	\N	\N	6	t
93	\N	\N	\N	\N	\N	\N	\N	\N	6	t
94	\N	\N	\N	\N	\N	\N	\N	\N	6	f
130	\N	\N	\N	\N	\N	\N	\N	\N	9	f
131	\N	\N	\N	\N	\N	\N	\N	\N	9	t
132	\N	\N	\N	\N	\N	\N	\N	\N	9	t
139	\N	\N	\N	\N	\N	\N	\N	\N	9	t
208	\N	\N	\N	\N	\N	\N	\N	\N	14	t
209	\N	\N	\N	\N	\N	\N	\N	\N	14	t
210	\N	\N	\N	\N	\N	\N	\N	\N	14	f
211	\N	\N	\N	\N	\N	\N	\N	\N	14	t
212	\N	\N	\N	\N	\N	\N	\N	\N	14	t
213	\N	\N	\N	\N	\N	\N	\N	\N	14	t
214	\N	\N	\N	\N	\N	\N	\N	\N	14	f
215	\N	\N	\N	\N	\N	\N	\N	\N	14	t
216	\N	\N	\N	\N	\N	\N	\N	\N	14	t
217	\N	\N	\N	\N	\N	\N	\N	\N	14	t
218	\N	\N	\N	\N	\N	\N	\N	\N	14	f
222	\N	\N	\N	\N	\N	\N	\N	\N	14	f
223	\N	\N	\N	\N	\N	\N	\N	\N	14	t
224	\N	\N	\N	\N	\N	\N	\N	\N	15	t
225	\N	\N	\N	\N	\N	\N	\N	\N	15	t
226	\N	\N	\N	\N	\N	\N	\N	\N	15	f
227	\N	\N	\N	\N	\N	\N	\N	\N	15	t
228	\N	\N	\N	\N	\N	\N	\N	\N	15	t
229	\N	\N	\N	\N	\N	\N	\N	\N	15	t
230	\N	\N	\N	\N	\N	\N	\N	\N	15	f
231	\N	\N	\N	\N	\N	\N	\N	\N	15	t
232	\N	\N	\N	\N	\N	\N	\N	\N	15	t
233	\N	\N	\N	\N	\N	\N	\N	\N	15	t
234	\N	\N	\N	\N	\N	\N	\N	\N	15	f
235	\N	\N	\N	\N	\N	\N	\N	\N	15	t
236	\N	\N	\N	\N	\N	\N	\N	\N	15	t
237	\N	\N	\N	\N	\N	\N	\N	\N	15	t
238	\N	\N	\N	\N	\N	\N	\N	\N	15	f
239	\N	\N	\N	\N	\N	\N	\N	\N	15	t
78	\N	\N	\N	\N	\N	\N	\N	\N	5	f
79	\N	\N	\N	\N	\N	\N	\N	\N	5	t
80	\N	\N	\N	\N	\N	\N	\N	\N	6	t
81	\N	\N	\N	\N	\N	\N	\N	\N	6	t
82	\N	\N	\N	\N	\N	\N	\N	\N	6	f
83	\N	\N	\N	\N	\N	\N	\N	\N	6	t
84	\N	\N	\N	\N	\N	\N	\N	\N	6	t
\.


--
-- Data for Name: subjects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.subjects (id, name, direction_id) FROM stdin;
1	Архитектура ЭВМ	1
2	Операционные системы	1
3	Компьютерные сети	1
4	Базы данных	2
5	Объектно-ориентированное программирование	2
6	Тестирование ПО	2
7	Дискретная математика	3
8	Теория вероятностей	3
9	Численные методы	3
10	Криптография	4
11	Сетевая безопасность	4
12	Защита информации	4
13	Теория систем	5
14	Системное моделирование	5
15	Управление проектами	5
\.


--
-- Data for Name: teacher_subjects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teacher_subjects (id, teacher_id, subject_id) FROM stdin;
1	1	1
2	1	4
3	1	7
4	2	2
5	2	5
6	2	8
7	3	3
8	3	6
9	3	9
10	4	10
11	4	11
12	4	13
13	5	12
14	5	14
15	5	15
\.


--
-- Data for Name: teachers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teachers (id, last_name, first_name, middle_name) FROM stdin;
1	Смирнов	Александр	Владимирович
2	Петрова	Елена	Сергеевна
3	Иванов	Дмитрий	Николаевич
4	Козлова	Мария	Андреевна
5	Волков	Сергей	Петрович
\.


--
-- Data for Name: time_slots; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.time_slots (id, pair_number, start_time, end_time) FROM stdin;
1	1	08:00:00	09:30:00
2	2	09:40:00	11:10:00
3	3	11:20:00	12:05:00
4	4	13:00:00	15:00:00
5	5	15:10:00	16:40:00
6	6	16:50:00	18:20:00
\.


--
-- Name: attendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.attendance_id_seq', 405, true);


--
-- Name: directions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.directions_id_seq', 5, true);


--
-- Name: extra_param_defs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.extra_param_defs_id_seq', 34, true);


--
-- Name: grades_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.grades_id_seq', 678, true);


--
-- Name: groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.groups_id_seq', 15, true);


--
-- Name: student_extra_params_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.student_extra_params_id_seq', 1632, true);


--
-- Name: students_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.students_id_seq', 240, true);


--
-- Name: subjects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.subjects_id_seq', 15, true);


--
-- Name: teacher_subjects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teacher_subjects_id_seq', 15, true);


--
-- Name: teachers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teachers_id_seq', 5, true);


--
-- Name: time_slots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.time_slots_id_seq', 6, true);


--
-- Name: attendance attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_pkey PRIMARY KEY (id);


--
-- Name: avg_group_all avg_group_all_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avg_group_all
    ADD CONSTRAINT avg_group_all_pkey PRIMARY KEY (group_id);


--
-- Name: avg_group_subject avg_group_subject_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avg_group_subject
    ADD CONSTRAINT avg_group_subject_pkey PRIMARY KEY (group_id, subject_id);


--
-- Name: avg_subject avg_subject_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avg_subject
    ADD CONSTRAINT avg_subject_pkey PRIMARY KEY (subject_id);


--
-- Name: directions directions_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.directions
    ADD CONSTRAINT directions_name_key UNIQUE (name);


--
-- Name: directions directions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.directions
    ADD CONSTRAINT directions_pkey PRIMARY KEY (id);


--
-- Name: extra_param_defs extra_param_defs_direction_id_param_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extra_param_defs
    ADD CONSTRAINT extra_param_defs_direction_id_param_name_key UNIQUE (direction_id, param_name);


--
-- Name: extra_param_defs extra_param_defs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extra_param_defs
    ADD CONSTRAINT extra_param_defs_pkey PRIMARY KEY (id);


--
-- Name: grades grades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_pkey PRIMARY KEY (id);


--
-- Name: grades grades_student_id_subject_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_student_id_subject_id_key UNIQUE (student_id, subject_id);


--
-- Name: groups groups_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_name_key UNIQUE (name);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: student_extra_params student_extra_params_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_extra_params
    ADD CONSTRAINT student_extra_params_pkey PRIMARY KEY (id);


--
-- Name: student_extra_params student_extra_params_student_id_param_def_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_extra_params
    ADD CONSTRAINT student_extra_params_student_id_param_def_id_key UNIQUE (student_id, param_def_id);


--
-- Name: students students_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_email_key UNIQUE (email);


--
-- Name: students students_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_pkey PRIMARY KEY (id);


--
-- Name: subjects subjects_name_direction_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_name_direction_id_key UNIQUE (name, direction_id);


--
-- Name: subjects subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_pkey PRIMARY KEY (id);


--
-- Name: teacher_subjects teacher_subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_subjects
    ADD CONSTRAINT teacher_subjects_pkey PRIMARY KEY (id);


--
-- Name: teacher_subjects teacher_subjects_teacher_id_subject_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_subjects
    ADD CONSTRAINT teacher_subjects_teacher_id_subject_id_key UNIQUE (teacher_id, subject_id);


--
-- Name: teachers teachers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teachers
    ADD CONSTRAINT teachers_pkey PRIMARY KEY (id);


--
-- Name: time_slots time_slots_pair_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.time_slots
    ADD CONSTRAINT time_slots_pair_number_key UNIQUE (pair_number);


--
-- Name: time_slots time_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.time_slots
    ADD CONSTRAINT time_slots_pkey PRIMARY KEY (id);


--
-- Name: grades trg_avg_group_all; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_avg_group_all AFTER INSERT OR DELETE OR UPDATE ON public.grades FOR EACH ROW EXECUTE FUNCTION public.trg_fn_avg_group_all();


--
-- Name: grades trg_avg_group_subject; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_avg_group_subject AFTER INSERT OR DELETE OR UPDATE ON public.grades FOR EACH ROW EXECUTE FUNCTION public.trg_fn_avg_group_subject();


--
-- Name: grades trg_avg_subject; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_avg_subject AFTER INSERT OR DELETE OR UPDATE ON public.grades FOR EACH ROW EXECUTE FUNCTION public.trg_fn_avg_subject();


--
-- Name: grades trg_check_grade_teacher; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_check_grade_teacher BEFORE INSERT OR UPDATE ON public.grades FOR EACH ROW EXECUTE FUNCTION public.trg_fn_check_grade_teacher();


--
-- Name: grades trg_check_grade_value; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_check_grade_value BEFORE INSERT OR UPDATE OF grade ON public.grades FOR EACH ROW EXECUTE FUNCTION public.trg_fn_check_grade_value();


--
-- Name: attendance attendance_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: attendance attendance_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: attendance attendance_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.teachers(id) ON DELETE CASCADE;


--
-- Name: attendance attendance_time_slot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_time_slot_id_fkey FOREIGN KEY (time_slot_id) REFERENCES public.time_slots(id) ON DELETE CASCADE;


--
-- Name: avg_group_all avg_group_all_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avg_group_all
    ADD CONSTRAINT avg_group_all_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: avg_group_subject avg_group_subject_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avg_group_subject
    ADD CONSTRAINT avg_group_subject_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: avg_group_subject avg_group_subject_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avg_group_subject
    ADD CONSTRAINT avg_group_subject_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: avg_subject avg_subject_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.avg_subject
    ADD CONSTRAINT avg_subject_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: extra_param_defs extra_param_defs_direction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extra_param_defs
    ADD CONSTRAINT extra_param_defs_direction_id_fkey FOREIGN KEY (direction_id) REFERENCES public.directions(id) ON DELETE CASCADE;


--
-- Name: grades grades_set_by_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_set_by_teacher_id_fkey FOREIGN KEY (set_by_teacher_id) REFERENCES public.teachers(id);


--
-- Name: grades grades_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: grades grades_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: groups groups_direction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_direction_id_fkey FOREIGN KEY (direction_id) REFERENCES public.directions(id) ON DELETE CASCADE;


--
-- Name: student_extra_params student_extra_params_param_def_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_extra_params
    ADD CONSTRAINT student_extra_params_param_def_id_fkey FOREIGN KEY (param_def_id) REFERENCES public.extra_param_defs(id) ON DELETE CASCADE;


--
-- Name: student_extra_params student_extra_params_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_extra_params
    ADD CONSTRAINT student_extra_params_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- Name: students students_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: subjects subjects_direction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_direction_id_fkey FOREIGN KEY (direction_id) REFERENCES public.directions(id) ON DELETE CASCADE;


--
-- Name: teacher_subjects teacher_subjects_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_subjects
    ADD CONSTRAINT teacher_subjects_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: teacher_subjects teacher_subjects_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_subjects
    ADD CONSTRAINT teacher_subjects_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.teachers(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict V6XBV7Ougc2rPlpWGl4DX085rPuDLqFVqIct57RrcAnbq2Fd8qScQnoYynHSTlE

