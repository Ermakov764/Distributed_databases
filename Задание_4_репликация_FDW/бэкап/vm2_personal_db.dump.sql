--
-- PostgreSQL database dump
--

\restrict XfUlCf2lZwxoi69jrf4PJV8hek9uY9saWWbLlpEt3dmUgffK33c8K5UPOM70eVG

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
-- Name: trg_fn_recalc_averages(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_fn_recalc_averages() RETURNS trigger
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

    -- T3: среднее группы по предмету
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

    -- если оценок не осталось — обнуляем
    IF NOT FOUND AND NOT EXISTS (
        SELECT 1 FROM grades gr
          JOIN students s ON s.id = gr.student_id
         WHERE s.group_id = v_group_id AND gr.subject_id = v_subject_id AND gr.grade IS NOT NULL
    ) THEN
        INSERT INTO avg_group_subject (group_id, subject_id, avg_grade, updated_at)
        VALUES (v_group_id, v_subject_id, NULL, NOW())
        ON CONFLICT (group_id, subject_id) DO UPDATE
           SET avg_grade = NULL, updated_at = NOW();
    END IF;

    -- T4: среднее группы по всем оценкам
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

    -- T5: среднее по предмету
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

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: phones_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.phones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: phones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phones (
    id integer DEFAULT nextval('public.phones_id_seq'::regclass) NOT NULL,
    student_id integer NOT NULL,
    phone_number character varying(20) NOT NULL
);


--
-- Name: students; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.students (
    id integer NOT NULL,
    last_name character varying(100) NOT NULL,
    first_name character varying(100) NOT NULL,
    middle_name character varying(100),
    birth_date date NOT NULL,
    city character varying(100) NOT NULL,
    street character varying(100) NOT NULL,
    house_number character varying(20) NOT NULL,
    email character varying(100)
);


--
-- Data for Name: phones; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.phones (id, student_id, phone_number) FROM stdin;
\.


--
-- Data for Name: students; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.students (id, last_name, first_name, middle_name, birth_date, city, street, house_number, email) FROM stdin;
1	Иванов	Иван	Иванович	2003-01-15	Москва	Ленина	10	ivanov@mail.ru
2	Петров	Петр	Петрович	2003-02-20	Москва	Пушкина	5	petrov@mail.ru
3	Сидоров	Сидор	Сидорович	2003-03-10	Москва	Гагарина	12	sidorov@mail.ru
4	Кузнецов	Алексей	Дмитриевич	2003-04-05	Санкт-Петербург	Невский	25	kuznetsov@mail.ru
5	Смирнов	Дмитрий	Александрович	2003-05-18	Москва	Тверская	8	smirnov@mail.ru
6	Волков	Андрей	Сергеевич	2003-06-22	Казань	Баумана	15	volkov@mail.ru
7	Зайцев	Михаил	Олегович	2003-07-30	Москва	Арбат	3	zaitsev@mail.ru
8	Павлов	Николай	Викторович	2003-08-14	Новосибирск	Красный	42	pavlov@mail.ru
9	Семенов	Евгений	Андреевич	2003-09-25	Москва	Садовая	7	semenov@mail.ru
10	Голубев	Сергей	Павлович	2003-10-11	Екатеринбург	Мира	19	golubev@mail.ru
11	Виноградов	Артём	Игоревич	2003-11-03	Москва	Ленина	33	vinogradov@mail.ru
12	Богданов	Роман	Денисович	2003-12-17	Самара	Московская	11	bogdanov@mail.ru
13	Воробьев	Максим	Александрович	2003-01-28	Москва	Пушкина	22	vorobiev@mail.ru
14	Федоров	Даниил	Сергеевич	2003-02-14	Ростов-на-Дону	Большая	6	fedorov@mail.ru
15	Михайлов	Тимофей	Андреевич	2003-03-21	Москва	Гагарина	14	mikhailov@mail.ru
16	Новиков	Кирилл	Владимирович	2003-04-12	Москва	Ленина	1	novikov@mail.ru
17	Морозов	Глеб	Антонович	2003-05-08	Казань	Пушкина	9	morozov@mail.ru
18	Петров	Александр	Николаевич	2003-06-19	Москва	Гагарина	4	petrov2@mail.ru
19	Волков	Дмитрий	Павлович	2003-07-23	Санкт-Петербург	Невский	17	volkov2@mail.ru
20	Соловьев	Матвей	Романович	2003-08-01	Москва	Тверская	12	soloviev@mail.ru
21	Васильев	Лев	Денисович	2003-09-15	Новосибирск	Красный	28	vasiliev@mail.ru
22	Зайцев	Илья	Михайлович	2003-10-27	Москва	Арбат	5	zaitsev2@mail.ru
23	Павлов	Марк	Александрович	2003-11-09	Екатеринбург	Мира	31	pavlov2@mail.ru
24	Семенов	Тихон	Сергеевич	2003-12-02	Москва	Садовая	18	semenov2@mail.ru
25	Голубев	Егор	Владимирович	2003-01-06	Самара	Московская	23	golubev2@mail.ru
26	Виноградов	Данил	Игоревич	2003-02-11	Москва	Ленина	41	vinogradov2@mail.ru
27	Богданов	Арсений	Денисович	2003-03-29	Ростов-на-Дону	Большая	13	bogdanov2@mail.ru
28	Воробьев	Степан	Александрович	2003-04-18	Москва	Пушкина	7	vorobiev2@mail.ru
29	Федоров	Филипп	Сергеевич	2003-05-24	Казань	Баумана	26	fedorov2@mail.ru
30	Михайлов	Ярослав	Андреевич	2003-06-30	Москва	Гагарина	19	mikhailov2@mail.ru
31	Кузнецов	Демьян	Дмитриевич	2003-07-07	Санкт-Петербург	Невский	34	kuznetsov2@mail.ru
32	Смирнов	Никита	Александрович	2003-08-16	Москва	Тверская	2	smirnov2@mail.ru
33	Иванов	Артём	Иванович	2003-09-21	Новосибирск	Красный	11	ivanov2@mail.ru
34	Петров	Михаил	Петрович	2003-10-05	Москва	Арбат	8	petrov3@mail.ru
35	Сидоров	Даниил	Сидорович	2003-11-13	Екатеринбург	Мира	22	sidorov2@mail.ru
36	Кузнецов	Родион	Дмитриевич	2003-12-28	Москва	Садовая	15	kuznetsov3@mail.ru
37	Смирнов	Владислав	Александрович	2003-01-09	Самара	Московская	9	smirnov3@mail.ru
38	Волков	Константин	Сергеевич	2003-02-17	Москва	Ленина	27	volkov3@mail.ru
39	Зайцев	Платон	Олегович	2003-03-04	Ростов-на-Дону	Большая	16	zaitsev3@mail.ru
40	Павлов	Захар	Викторович	2003-04-22	Москва	Пушкина	31	pavlov3@mail.ru
41	Семенов	Савелий	Андреевич	2003-05-11	Казань	Баумана	4	semenov3@mail.ru
42	Голубев	Герман	Павлович	2003-06-26	Москва	Гагарина	13	golubev3@mail.ru
43	Виноградов	Лука	Игоревич	2003-07-15	Санкт-Петербург	Невский	29	vinogradov3@mail.ru
44	Богданов	Марк	Денисович	2003-08-03	Москва	Тверская	36	bogdanov3@mail.ru
45	Воробьев	Демид	Александрович	2003-09-19	Новосибирск	Красный	7	vorobiev3@mail.ru
46	Федоров	Тимофей	Сергеевич	2003-10-31	Москва	Арбат	21	fedorov3@mail.ru
47	Михайлов	Елисей	Андреевич	2003-11-24	Екатеринбург	Мира	18	mikhailov3@mail.ru
48	Новиков	Макар	Владимирович	2003-12-07	Москва	Садовая	44	novikov2@mail.ru
49	Алексеев	Александр	Петрович	2003-01-10	Москва	Ленина	5	alekseev@mail.ru
50	Белов	Борис	Иванович	2003-02-15	Казань	Пушкина	12	belov@mail.ru
51	Васильев	Виктор	Сергеевич	2003-03-20	Москва	Гагарина	8	vasiliev2@mail.ru
52	Григорьев	Глеб	Андреевич	2003-04-25	Санкт-Петербург	Невский	15	grigoriev@mail.ru
53	Дмитриев	Даниил	Михайлович	2003-05-30	Москва	Тверская	3	dmitriev@mail.ru
54	Егоров	Евгений	Павлович	2003-06-05	Новосибирск	Красный	22	egorov@mail.ru
55	Жуков	Захар	Олегович	2003-07-10	Москва	Арбат	11	zhukov@mail.ru
56	Зотов	Зиновий	Викторович	2003-08-15	Екатеринбург	Мира	7	zotov@mail.ru
57	Ильин	Илья	Андреевич	2003-09-20	Москва	Садовая	19	ilyin@mail.ru
58	Козлов	Кирилл	Павлович	2003-10-25	Самара	Московская	14	kozlov@mail.ru
59	Лебедев	Лев	Игоревич	2003-11-30	Москва	Ленина	28	lebedev@mail.ru
60	Макаров	Максим	Денисович	2003-12-05	Ростов-на-Дону	Большая	9	makarov@mail.ru
61	Николаев	Никита	Александрович	2003-01-12	Москва	Пушкина	16	nikolaev@mail.ru
62	Орлов	Олег	Сергеевич	2003-02-18	Казань	Баумана	21	orlov@mail.ru
63	Поляков	Павел	Андреевич	2003-03-25	Москва	Гагарина	33	polyakov@mail.ru
64	Романов	Роман	Петрович	2003-04-02	Санкт-Петербург	Невский	6	romanov@mail.ru
65	Соколов	Степан	Иванович	2003-05-08	Москва	Тверская	13	sokolov@mail.ru
66	Тихонов	Тимофей	Сергеевич	2003-06-14	Новосибирск	Красный	18	tikhonov@mail.ru
67	Ульянов	Устин	Андреевич	2003-07-20	Екатеринбург	Мира	24	ulyanov@mail.ru
68	Филиппов	Федор	Михайлович	2003-08-26	Москва	Арбат	10	filippov@mail.ru
69	Харитонов	Харитон	Павлович	2003-09-02	Самара	Московская	17	kharitonov@mail.ru
70	Цветков	Цезарь	Олегович	2003-10-08	Москва	Садовая	23	tsvetkov@mail.ru
71	Чернов	Черн	Викторович	2003-11-14	Ростов-на-Дону	Большая	29	chernov@mail.ru
72	Шестаков	Шест	Андреевич	2003-12-20	Москва	Ленина	35	shestakov@mail.ru
73	Щукин	Щук	Павлович	2003-01-26	Казань	Пушкина	41	shchukin@mail.ru
74	Юдин	Юд	Игоревич	2003-02-02	Москва	Гагарина	47	yudin@mail.ru
75	Яковлев	Як	Денисович	2003-03-08	Санкт-Петербург	Невский	53	yakovlev@mail.ru
76	Абрамов	Абр	Александрович	2003-04-14	Москва	Тверская	59	abramov@mail.ru
77	Бобров	Бобр	Сергеевич	2003-05-20	Новосибирск	Красный	65	bobrov@mail.ru
78	Власов	Влас	Андреевич	2003-06-26	Екатеринбург	Мира	71	vlasov@mail.ru
79	Громов	Гром	Петрович	2003-07-02	Москва	Арбат	77	gromov@mail.ru
80	Давыдов	Дав	Иванович	2003-08-08	Самара	Московская	83	davydov@mail.ru
81	Ершов	Ерш	Сергеевич	2003-09-14	Москва	Садовая	89	ershov@mail.ru
82	Жданов	Ждан	Андреевич	2003-10-20	Ростов-на-Дону	Большая	95	zhdanov@mail.ru
83	Зимин	Зим	Михайлович	2003-11-26	Москва	Ленина	101	zimin@mail.ru
84	Исаев	Иса	Павлович	2003-12-02	Казань	Пушкина	107	isaev@mail.ru
85	Калинин	Кал	Олегович	2003-01-08	Санкт-Петербург	Невский	113	kalinin@mail.ru
86	Лазарев	Лаз	Викторович	2003-02-14	Москва	Гагарина	119	lazarev@mail.ru
87	Медведев	Мед	Андреевич	2003-03-20	Новосибирск	Красный	125	medvedev@mail.ru
88	Наумов	Наум	Павлович	2003-04-26	Екатеринбург	Мира	131	naumov@mail.ru
89	Осипов	Осип	Игоревич	2003-05-02	Москва	Тверская	137	osipov@mail.ru
90	Панов	Пан	Денисович	2003-06-08	Самара	Московская	143	panov@mail.ru
91	Рыбаков	Рыб	Александрович	2003-07-14	Москва	Арбат	149	rybakov@mail.ru
92	Савельев	Сав	Сергеевич	2003-08-20	Ростов-на-Дону	Большая	155	saveliev@mail.ru
93	Тарасов	Тар	Андреевич	2003-09-26	Москва	Садовая	161	tarasov@mail.ru
94	Успенский	Усп	Петрович	2003-10-02	Казань	Баумана	167	uspensky@mail.ru
95	Фролов	Фро	Иванович	2003-11-08	Санкт-Петербург	Невский	173	frolov@mail.ru
96	Хохлов	Хох	Сергеевич	2003-12-14	Москва	Гагарина	179	khokhlov@mail.ru
97	Антонов	Антон	Александрович	2003-01-05	Москва	Ленина	1	antonov@mail.ru
98	Борисов	Борис	Борисович	2003-02-10	Казань	Пушкина	2	borisov@mail.ru
99	Викторов	Виктор	Викторович	2003-03-15	Москва	Гагарина	3	victorov@mail.ru
100	Геннадьев	Геннадий	Геннадьевич	2003-04-20	Санкт-Петербург	Невский	4	gennadiev@mail.ru
101	Денисов	Денис	Денисович	2003-05-25	Москва	Тверская	5	denisov@mail.ru
102	Ефимов	Ефим	Ефимович	2003-06-30	Новосибирск	Красный	6	efimov@mail.ru
103	Жданов	Ждан	Жданович	2003-07-05	Москва	Арбат	7	zhdanov2@mail.ru
104	Зиновьев	Зиновий	Зиновьевич	2003-08-10	Екатеринбург	Мира	8	zinoviev@mail.ru
105	Игнатьев	Игнат	Игнатьевич	2003-09-15	Москва	Садовая	9	ignatiev@mail.ru
106	Кириллов	Кирилл	Кириллович	2003-10-20	Самара	Московская	10	kirillov@mail.ru
107	Лаврентьев	Лаврентий	Лаврентьевич	2003-11-25	Москва	Ленина	11	lavrentiev@mail.ru
108	Матвеев	Матвей	Матвеевич	2003-12-30	Ростов-на-Дону	Большая	12	matveev@mail.ru
109	Нестеров	Нестор	Нестерович	2003-01-15	Москва	Пушкина	13	nesterov@mail.ru
110	Олегов	Олег	Олегович	2003-02-20	Казань	Баумана	14	olegov@mail.ru
111	Прохоров	Прохор	Прохорович	2003-03-25	Москва	Гагарина	15	prokhorov@mail.ru
112	Родионов	Родион	Родионович	2003-04-01	Санкт-Петербург	Невский	16	rodionov@mail.ru
113	Степанов	Степан	Степанович	2003-05-06	Москва	Тверская	17	stepanov@mail.ru
114	Трофимов	Трофим	Трофимович	2003-06-11	Новосибирск	Красный	18	trofimov@mail.ru
115	Уваров	Увар	Уварович	2003-07-16	Екатеринбург	Мира	19	uvarov@mail.ru
116	Фадеев	Фаддей	Фадеевич	2003-08-21	Москва	Арбат	20	fadeev@mail.ru
117	Харламов	Харлам	Харламович	2003-09-26	Самара	Московская	21	kharlamov@mail.ru
118	Цветков	Цвет	Цветкович	2003-10-01	Москва	Садовая	22	tsvetkov2@mail.ru
119	Черкасов	Черкас	Черкасович	2003-11-06	Ростов-на-Дону	Большая	23	cherkasov@mail.ru
120	Шаров	Шар	Шарович	2003-12-11	Москва	Ленина	24	sharov@mail.ru
121	Щеглов	Щегл	Щеглович	2003-01-16	Казань	Пушкина	25	shcheglov@mail.ru
122	Юрьев	Юр	Юрьевич	2003-02-21	Москва	Гагарина	26	yurev@mail.ru
123	Яшин	Яш	Яшинович	2003-03-26	Санкт-Петербург	Невский	27	yashin@mail.ru
124	Агапов	Агап	Агапович	2003-04-01	Москва	Тверская	28	agapov@mail.ru
125	Беляев	Бел	Беляевич	2003-05-06	Новосибирск	Красный	29	belyaev@mail.ru
126	Воронин	Ворон	Воронинович	2003-06-11	Екатеринбург	Мира	30	voronin@mail.ru
127	Гусев	Гус	Гусевич	2003-07-16	Москва	Арбат	31	gusev@mail.ru
128	Дорохов	Дор	Дорохович	2003-08-21	Самара	Московская	32	dorokhov@mail.ru
129	Ермолаев	Ерм	Ермолаевич	2003-09-26	Москва	Садовая	33	ermolaev@mail.ru
130	Журавлев	Жур	Журавлевич	2003-10-01	Ростов-на-Дону	Большая	34	zhuravlev@mail.ru
131	Зубов	Зуб	Зубович	2003-11-06	Москва	Ленина	35	zubov@mail.ru
132	Игнатов	Игн	Игнатович	2003-12-11	Казань	Баумана	36	ignatov@mail.ru
133	Киселев	Кис	Киселевич	2003-01-16	Санкт-Петербург	Невский	37	kiselev@mail.ru
134	Лобанов	Лоб	Лобанович	2003-02-21	Москва	Гагарина	38	lobanov@mail.ru
135	Мельников	Мел	Мельникович	2003-03-26	Новосибирск	Красный	39	melnikov@mail.ru
136	Назаров	Наз	Назарович	2003-04-01	Екатеринбург	Мира	40	nazarov@mail.ru
137	Орехов	Орех	Орехович	2003-05-06	Москва	Тверская	41	orekhov@mail.ru
138	Пименов	Пим	Пименович	2003-06-11	Самара	Московская	42	pimenov@mail.ru
139	Рябов	Ряб	Рябович	2003-07-16	Москва	Арбат	43	ryabov@mail.ru
140	Сафонов	Саф	Сафонович	2003-08-21	Ростов-на-Дону	Большая	44	safonov@mail.ru
141	Титов	Тит	Титович	2003-09-26	Москва	Садовая	45	titov@mail.ru
142	Устинов	Уст	Устинович	2003-10-01	Казань	Пушкина	46	ustinov@mail.ru
143	Фомин	Фом	Фомич	2003-11-06	Санкт-Петербург	Невский	47	fomin@mail.ru
144	Хромов	Хром	Хромович	2003-12-11	Москва	Гагарина	48	khromov@mail.ru
145	Царев	Цар	Царевич	2003-01-01	Москва	Ленина	49	tsarev@mail.ru
146	Чесноков	Чес	Чеснокович	2003-02-06	Казань	Пушкина	50	chesnokov@mail.ru
147	Ширяев	Шир	Ширяевич	2003-03-11	Москва	Гагарина	51	shiryaev@mail.ru
148	Щукин	Щук	Щукинович	2003-04-16	Санкт-Петербург	Невский	52	shchukin2@mail.ru
149	Яблоков	Ябл	Яблокович	2003-05-21	Москва	Тверская	53	yablokov@mail.ru
150	Авдеев	Авд	Авдеевич	2003-06-26	Новосибирск	Красный	54	avdeev@mail.ru
151	Баженов	Баж	Баженович	2003-07-01	Москва	Арбат	55	bazhenov@mail.ru
152	Варламов	Варл	Варламович	2003-08-06	Екатеринбург	Мира	56	varlamov@mail.ru
153	Галкин	Галк	Галкинович	2003-09-11	Москва	Садовая	57	galkin@mail.ru
154	Демидов	Дем	Демидович	2003-10-16	Самара	Московская	58	demidov@mail.ru
155	Евсеев	Евс	Евсеевич	2003-11-21	Москва	Ленина	59	evseev@mail.ru
156	Жилин	Жил	Жилинович	2003-12-26	Ростов-на-Дону	Большая	60	zhilin@mail.ru
157	Зотов	Зот	Зотович	2003-01-11	Москва	Пушкина	61	zotov2@mail.ru
158	Исаков	Исак	Исакович	2003-02-16	Казань	Баумана	62	isakov@mail.ru
159	Казаков	Каз	Казакович	2003-03-21	Москва	Гагарина	63	kazakov@mail.ru
160	Лихачев	Лих	Лихачевич	2003-04-26	Санкт-Петербург	Невский	64	likhachev@mail.ru
161	Мишин	Миш	Мишинович	2003-05-01	Москва	Тверская	65	mishin@mail.ru
162	Некрасов	Некр	Некрасович	2003-06-06	Новосибирск	Красный	66	nekrasov@mail.ru
163	Овчинников	Овч	Овчинникович	2003-07-11	Екатеринбург	Мира	67	ovchinnikov@mail.ru
164	Потапов	Пот	Потапович	2003-08-16	Москва	Арбат	68	potapov@mail.ru
165	Рогов	Рог	Рогович	2003-09-21	Самара	Московская	69	rogov@mail.ru
166	Сурков	Сурк	Суркович	2003-10-26	Москва	Садовая	70	surkov@mail.ru
167	Тихомиров	Тих	Тихомирович	2003-11-01	Ростов-на-Дону	Большая	71	tikhomirov@mail.ru
168	Усов	Ус	Усович	2003-12-06	Москва	Ленина	72	usov@mail.ru
169	Филатов	Фил	Филатович	2003-01-11	Казань	Пушкина	73	filatov@mail.ru
170	Хохлов	Хох	Хохлович	2003-02-16	Москва	Гагарина	74	khokhlov2@mail.ru
171	Цыганов	Цыг	Цыганович	2003-03-21	Санкт-Петербург	Невский	75	tsyganov@mail.ru
172	Чистяков	Чист	Чистякович	2003-04-26	Москва	Тверская	76	chistyakov@mail.ru
173	Шестаков	Шест	Шестакович	2003-05-01	Новосибирск	Красный	77	shestakov2@mail.ru
174	Щербаков	Щерб	Щербакович	2003-06-06	Екатеринбург	Мира	78	shcherbakov@mail.ru
175	Яковлев	Як	Яковлевич	2003-07-11	Москва	Арбат	79	yakovlev2@mail.ru
176	Аксенов	Акс	Аксенович	2003-08-16	Самара	Московская	80	aksenov@mail.ru
177	Белозеров	Бел	Белозерович	2003-09-21	Москва	Садовая	81	belozerov@mail.ru
178	Власов	Влас	Власович	2003-10-26	Ростов-на-Дону	Большая	82	vlasov2@mail.ru
179	Гришин	Гриш	Гришинович	2003-11-01	Москва	Ленина	83	grishin@mail.ru
180	Дроздов	Дроз	Дроздович	2003-12-06	Казань	Баумана	84	drozdov@mail.ru
181	Ермаков	Ерм	Ермакович	2003-01-11	Санкт-Петербург	Невский	85	ermakov@mail.ru
182	Журавлев	Жур	Журавлевич	2003-02-16	Москва	Гагарина	86	zhuravlev2@mail.ru
183	Зайцев	Зай	Зайцевич	2003-03-21	Новосибирск	Красный	87	zaitsev4@mail.ru
184	Ильин	Иль	Ильинич	2003-04-26	Екатеринбург	Мира	88	ilyin2@mail.ru
185	Ковалев	Ков	Ковалевич	2003-05-01	Москва	Тверская	89	kovalev@mail.ru
186	Литвинов	Лит	Литвинович	2003-06-06	Самара	Московская	90	litvinov@mail.ru
187	Миронов	Мир	Миронович	2003-07-11	Москва	Арбат	91	mironov@mail.ru
188	Никитин	Ник	Никитинич	2003-08-16	Ростов-на-Дону	Большая	92	nikitin@mail.ru
189	Осипов	Осип	Осипович	2003-09-21	Москва	Садовая	93	osipov2@mail.ru
190	Павлов	Пав	Павлович	2003-10-26	Казань	Пушкина	94	pavlov4@mail.ru
191	Романов	Ром	Романович	2003-11-01	Санкт-Петербург	Невский	95	romanov2@mail.ru
192	Соловьев	Сол	Соловьевич	2003-12-06	Москва	Гагарина	96	soloviev2@mail.ru
193	Тарасов	Тар	Тарасович	2003-01-21	Москва	Ленина	97	tarasov2@mail.ru
194	Ульянов	Уль	Ульянович	2003-02-26	Казань	Пушкина	98	ulyanov2@mail.ru
195	Федотов	Фед	Федотович	2003-03-01	Москва	Гагарина	99	fedotov@mail.ru
196	Харитонов	Хар	Харитонович	2003-04-06	Санкт-Петербург	Невский	100	kharitonov2@mail.ru
197	Цветков	Цв	Цветкович	2003-05-11	Москва	Тверская	101	tsvetkov3@mail.ru
198	Чернов	Чер	Чернович	2003-06-16	Новосибирск	Красный	102	chernov2@mail.ru
199	Шаров	Шар	Шарович	2003-07-21	Москва	Арбат	103	sharov2@mail.ru
200	Щукин	Щук	Щукинович	2003-08-26	Екатеринбург	Мира	104	shchukin3@mail.ru
201	Яшин	Яш	Яшинович	2003-09-01	Москва	Садовая	105	yashin2@mail.ru
202	Абрамов	Абр	Абрамович	2003-10-06	Самара	Московская	106	abramov2@mail.ru
203	Беляев	Бел	Беляевич	2003-11-11	Москва	Ленина	107	belyaev2@mail.ru
204	Волков	Вол	Волкович	2003-12-16	Ростов-на-Дону	Большая	108	volkov4@mail.ru
205	Голубев	Гол	Голубевич	2003-01-21	Москва	Пушкина	109	golubev4@mail.ru
206	Дмитриев	Дм	Дмитриевич	2003-02-26	Казань	Баумана	110	dmitriev2@mail.ru
207	Егоров	Ег	Егорович	2003-03-01	Москва	Гагарина	111	egorov2@mail.ru
208	Жуков	Жук	Жукович	2003-04-06	Санкт-Петербург	Невский	112	zhukov2@mail.ru
209	Зайцев	Зай	Зайцевич	2003-05-11	Москва	Тверская	113	zaitsev5@mail.ru
210	Иванов	Ив	Иванович	2003-06-16	Новосибирск	Красный	114	ivanov3@mail.ru
211	Козлов	Коз	Козлович	2003-07-21	Екатеринбург	Мира	115	kozlov2@mail.ru
212	Лебедев	Леб	Лебедевич	2003-08-26	Москва	Арбат	116	lebedev2@mail.ru
213	Михайлов	Мих	Михайлович	2003-09-01	Самара	Московская	117	mikhailov4@mail.ru
214	Новиков	Нов	Новикович	2003-10-06	Москва	Садовая	118	novikov3@mail.ru
215	Орлов	Орл	Орлович	2003-11-11	Ростов-на-Дону	Большая	119	orlov2@mail.ru
216	Павлов	Пав	Павлович	2003-12-16	Москва	Ленина	120	pavlov5@mail.ru
217	Романов	Ром	Романович	2003-01-21	Казань	Пушкина	121	romanov3@mail.ru
218	Соколов	Сок	Соколович	2003-02-26	Москва	Гагарина	122	sokolov2@mail.ru
219	Тихонов	Тих	Тихонович	2003-03-01	Санкт-Петербург	Невский	123	tikhonov2@mail.ru
220	Ульянов	Уль	Ульянович	2003-04-06	Москва	Тверская	124	ulyanov3@mail.ru
221	Федоров	Фед	Федорович	2003-05-11	Новосибирск	Красный	125	fedorov4@mail.ru
222	Харитонов	Хар	Харитонович	2003-06-16	Екатеринбург	Мира	126	kharitonov3@mail.ru
223	Цветков	Цв	Цветкович	2003-07-21	Москва	Арбат	127	tsvetkov4@mail.ru
224	Чернов	Чер	Чернович	2003-08-26	Самара	Московская	128	chernov3@mail.ru
225	Шестаков	Шест	Шестакович	2003-09-01	Москва	Садовая	129	shestakov3@mail.ru
226	Щукин	Щук	Щукинович	2003-10-06	Ростов-на-Дону	Большая	130	shchukin4@mail.ru
227	Яковлев	Як	Яковлевич	2003-11-11	Москва	Ленина	131	yakovlev3@mail.ru
228	Абрамов	Абр	Абрамович	2003-12-16	Казань	Баумана	132	abramov3@mail.ru
229	Беляев	Бел	Беляевич	2003-01-21	Санкт-Петербург	Невский	133	belyaev3@mail.ru
230	Волков	Вол	Волкович	2003-02-26	Москва	Гагарина	134	volkov5@mail.ru
231	Голубев	Гол	Голубевич	2003-03-01	Новосибирск	Красный	135	golubev5@mail.ru
232	Дмитриев	Дм	Дмитриевич	2003-04-06	Екатеринбург	Мира	136	dmitriev3@mail.ru
233	Егоров	Ег	Егорович	2003-05-11	Москва	Тверская	137	egorov3@mail.ru
234	Жуков	Жук	Жукович	2003-06-16	Самара	Московская	138	zhukov3@mail.ru
235	Зайцев	Зай	Зайцевич	2003-07-21	Москва	Арбат	139	zaitsev6@mail.ru
236	Иванов	Ив	Иванович	2003-08-26	Ростов-на-Дону	Большая	140	ivanov4@mail.ru
237	Козлов	Коз	Козлович	2003-09-01	Москва	Садовая	141	kozlov3@mail.ru
238	Лебедев	Леб	Лебедевич	2003-10-06	Казань	Пушкина	142	lebedev3@mail.ru
239	Михайлов	Мих	Михайлович	2003-11-11	Санкт-Петербург	Невский	143	mikhailov5@mail.ru
240	Новиков	Нов	Новикович	2003-12-16	Москва	Гагарина	144	novikov4@mail.ru
\.


--
-- Name: phones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.phones_id_seq', 1, true);


--
-- Name: phones phones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phones
    ADD CONSTRAINT phones_pkey PRIMARY KEY (id);


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
-- Name: phones phones_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phones
    ADD CONSTRAINT phones_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict XfUlCf2lZwxoi69jrf4PJV8hek9uY9saWWbLlpEt3dmUgffK33c8K5UPOM70eVG

