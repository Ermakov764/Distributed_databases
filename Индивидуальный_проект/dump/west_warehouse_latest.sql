--
-- PostgreSQL database dump
--

\restrict JI29HgZm8J8PkVFkH0c4yY53O7epDGGw8ymLpEo5DQHepJCnfDaqqX59z2xtQ3c

-- Dumped from database version 16.15 (Debian 16.15-1.pgdg13+2)
-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg13+2)

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

ALTER TABLE IF EXISTS ONLY public.warehouses DROP CONSTRAINT IF EXISTS warehouses_region_id_fkey;
ALTER TABLE IF EXISTS ONLY public.stock_balances DROP CONSTRAINT IF EXISTS stock_balances_warehouse_id_fkey;
ALTER TABLE IF EXISTS ONLY public.stock_balances DROP CONSTRAINT IF EXISTS stock_balances_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.shipment_orders DROP CONSTRAINT IF EXISTS shipment_orders_warehouse_id_fkey;
ALTER TABLE IF EXISTS ONLY public.shipment_items DROP CONSTRAINT IF EXISTS shipment_items_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.shipment_items DROP CONSTRAINT IF EXISTS shipment_items_order_id_fkey;
ALTER TABLE IF EXISTS ONLY public.shipment_events DROP CONSTRAINT IF EXISTS shipment_events_order_id_fkey;
DROP INDEX IF EXISTS public.idx_shipment_orders_status;
DROP INDEX IF EXISTS public.idx_shipment_orders_region;
ALTER TABLE IF EXISTS ONLY public.warehouses DROP CONSTRAINT IF EXISTS warehouses_region_id_code_key;
ALTER TABLE IF EXISTS ONLY public.warehouses DROP CONSTRAINT IF EXISTS warehouses_pkey;
ALTER TABLE IF EXISTS ONLY public.stock_balances DROP CONSTRAINT IF EXISTS stock_balances_warehouse_id_product_id_key;
ALTER TABLE IF EXISTS ONLY public.stock_balances DROP CONSTRAINT IF EXISTS stock_balances_pkey;
ALTER TABLE IF EXISTS ONLY public.shipment_orders DROP CONSTRAINT IF EXISTS shipment_orders_pkey;
ALTER TABLE IF EXISTS ONLY public.shipment_items DROP CONSTRAINT IF EXISTS shipment_items_pkey;
ALTER TABLE IF EXISTS ONLY public.shipment_items DROP CONSTRAINT IF EXISTS shipment_items_order_id_product_id_key;
ALTER TABLE IF EXISTS ONLY public.shipment_events DROP CONSTRAINT IF EXISTS shipment_events_pkey;
ALTER TABLE IF EXISTS ONLY public.regions DROP CONSTRAINT IF EXISTS regions_pkey;
ALTER TABLE IF EXISTS ONLY public.regions DROP CONSTRAINT IF EXISTS regions_code_key;
ALTER TABLE IF EXISTS ONLY public.products DROP CONSTRAINT IF EXISTS products_sku_key;
ALTER TABLE IF EXISTS ONLY public.products DROP CONSTRAINT IF EXISTS products_pkey;
ALTER TABLE IF EXISTS public.warehouses ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.stock_balances ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.shipment_orders ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.shipment_items ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.shipment_events ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.regions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.products ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.warehouses_id_seq;
DROP TABLE IF EXISTS public.warehouses;
DROP SEQUENCE IF EXISTS public.stock_balances_id_seq;
DROP TABLE IF EXISTS public.stock_balances;
DROP SEQUENCE IF EXISTS public.shipment_orders_id_seq;
DROP TABLE IF EXISTS public.shipment_orders;
DROP SEQUENCE IF EXISTS public.shipment_items_id_seq;
DROP TABLE IF EXISTS public.shipment_items;
DROP SEQUENCE IF EXISTS public.shipment_events_id_seq;
DROP TABLE IF EXISTS public.shipment_events;
DROP SEQUENCE IF EXISTS public.regions_id_seq;
DROP TABLE IF EXISTS public.regions;
DROP SEQUENCE IF EXISTS public.products_id_seq;
DROP TABLE IF EXISTS public.products;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    id integer NOT NULL,
    sku character varying(64) NOT NULL,
    title character varying(256) NOT NULL
);


--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: regions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.regions (
    id smallint NOT NULL,
    code character varying(16) NOT NULL,
    name character varying(128) NOT NULL
);


--
-- Name: regions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.regions_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: regions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.regions_id_seq OWNED BY public.regions.id;


--
-- Name: shipment_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipment_events (
    id integer NOT NULL,
    order_id integer NOT NULL,
    from_status character varying(32),
    to_status character varying(32) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    note text
);


--
-- Name: shipment_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipment_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipment_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipment_events_id_seq OWNED BY public.shipment_events.id;


--
-- Name: shipment_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipment_items (
    id integer NOT NULL,
    order_id integer NOT NULL,
    product_id integer NOT NULL,
    qty integer NOT NULL,
    CONSTRAINT shipment_items_qty_check CHECK ((qty > 0))
);


--
-- Name: shipment_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipment_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipment_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipment_items_id_seq OWNED BY public.shipment_items.id;


--
-- Name: shipment_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipment_orders (
    id integer NOT NULL,
    warehouse_id integer NOT NULL,
    region_code character varying(16) NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT shipment_orders_status_check CHECK (((status)::text = ANY ((ARRAY['CREATED'::character varying, 'RESERVED'::character varying, 'PICKING'::character varying, 'SHIPPED'::character varying, 'DELIVERED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: shipment_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipment_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipment_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipment_orders_id_seq OWNED BY public.shipment_orders.id;


--
-- Name: stock_balances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stock_balances (
    id integer NOT NULL,
    warehouse_id integer NOT NULL,
    product_id integer NOT NULL,
    qty_available integer NOT NULL,
    qty_reserved integer DEFAULT 0 NOT NULL,
    CONSTRAINT stock_balances_qty_available_check CHECK ((qty_available >= 0)),
    CONSTRAINT stock_balances_qty_reserved_check CHECK ((qty_reserved >= 0)),
    CONSTRAINT stock_balances_qty_reserved_check1 CHECK ((qty_reserved >= 0))
);


--
-- Name: stock_balances_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stock_balances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stock_balances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stock_balances_id_seq OWNED BY public.stock_balances.id;


--
-- Name: warehouses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.warehouses (
    id integer NOT NULL,
    region_id smallint NOT NULL,
    code character varying(32) NOT NULL,
    name character varying(128) NOT NULL
);


--
-- Name: warehouses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.warehouses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: warehouses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.warehouses_id_seq OWNED BY public.warehouses.id;


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: regions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions ALTER COLUMN id SET DEFAULT nextval('public.regions_id_seq'::regclass);


--
-- Name: shipment_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_events ALTER COLUMN id SET DEFAULT nextval('public.shipment_events_id_seq'::regclass);


--
-- Name: shipment_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_items ALTER COLUMN id SET DEFAULT nextval('public.shipment_items_id_seq'::regclass);


--
-- Name: shipment_orders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_orders ALTER COLUMN id SET DEFAULT nextval('public.shipment_orders_id_seq'::regclass);


--
-- Name: stock_balances id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_balances ALTER COLUMN id SET DEFAULT nextval('public.stock_balances_id_seq'::regclass);


--
-- Name: warehouses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouses ALTER COLUMN id SET DEFAULT nextval('public.warehouses_id_seq'::regclass);


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.products (id, sku, title) FROM stdin;
1	SKU-100	Кабель оптический 1м
2	SKU-200	Блок питания ИБП
3	SKU-300	Коммутатор 24p
7	SKU-DEMO-1	Демо-товар стенда (upd)
8	SKU-SCR-1	Товар для скрина
\.


--
-- Data for Name: regions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.regions (id, code, name) FROM stdin;
1	WEST	Западный регион
\.


--
-- Data for Name: shipment_events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shipment_events (id, order_id, from_status, to_status, created_at, note) FROM stdin;
1	1	\N	CREATED	2026-09-16 21:02:00.482169+00	order created
2	1	CREATED	RESERVED	2026-09-16 21:02:00.560929+00	demo RESERVED
3	1	RESERVED	PICKING	2026-09-16 21:02:00.595572+00	demo PICKING
4	1	PICKING	SHIPPED	2026-09-16 21:02:00.631543+00	demo SHIPPED
5	1	SHIPPED	DELIVERED	2026-09-16 21:02:00.67015+00	demo DELIVERED
6	2	\N	CREATED	2026-09-16 21:09:24.419345+00	order created
7	3	\N	CREATED	2026-09-17 05:47:33.787509+00	order created
\.


--
-- Data for Name: shipment_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shipment_items (id, order_id, product_id, qty) FROM stdin;
1	1	7	3
2	2	1	1
3	3	1	1
\.


--
-- Data for Name: shipment_orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shipment_orders (id, warehouse_id, region_code, status, created_at, updated_at) FROM stdin;
1	3	WEST	DELIVERED	2026-09-16 21:02:00.482169+00	2026-09-16 21:02:00.67015+00
2	1	WEST	CREATED	2026-09-16 21:09:24.419345+00	2026-09-16 21:09:24.419345+00
3	1	WEST	CREATED	2026-09-17 05:47:33.787509+00	2026-09-17 05:47:33.787509+00
\.


--
-- Data for Name: stock_balances; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.stock_balances (id, warehouse_id, product_id, qty_available, qty_reserved) FROM stdin;
1	1	1	100	0
2	1	2	50	0
3	1	3	20	0
7	3	7	22	0
8	4	1	100	0
9	3	1	100	0
11	4	2	50	0
12	3	2	50	0
14	4	3	20	0
15	3	3	20	0
\.


--
-- Data for Name: warehouses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.warehouses (id, region_id, code, name) FROM stdin;
1	1	WH-WEST-1	Склад Запад-1
3	1	WH-WEST-DEMO	Склад Запад DEMO (upd)
4	1	WH-WEST-SCR	Склад для скрина
\.


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.products_id_seq', 14, true);


--
-- Name: regions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.regions_id_seq', 2, true);


--
-- Name: shipment_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shipment_events_id_seq', 7, true);


--
-- Name: shipment_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shipment_items_id_seq', 3, true);


--
-- Name: shipment_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shipment_orders_id_seq', 3, true);


--
-- Name: stock_balances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.stock_balances_id_seq', 25, true);


--
-- Name: warehouses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.warehouses_id_seq', 6, true);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: products products_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_sku_key UNIQUE (sku);


--
-- Name: regions regions_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT regions_code_key UNIQUE (code);


--
-- Name: regions regions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT regions_pkey PRIMARY KEY (id);


--
-- Name: shipment_events shipment_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_events
    ADD CONSTRAINT shipment_events_pkey PRIMARY KEY (id);


--
-- Name: shipment_items shipment_items_order_id_product_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_items
    ADD CONSTRAINT shipment_items_order_id_product_id_key UNIQUE (order_id, product_id);


--
-- Name: shipment_items shipment_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_items
    ADD CONSTRAINT shipment_items_pkey PRIMARY KEY (id);


--
-- Name: shipment_orders shipment_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_orders
    ADD CONSTRAINT shipment_orders_pkey PRIMARY KEY (id);


--
-- Name: stock_balances stock_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_balances
    ADD CONSTRAINT stock_balances_pkey PRIMARY KEY (id);


--
-- Name: stock_balances stock_balances_warehouse_id_product_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_balances
    ADD CONSTRAINT stock_balances_warehouse_id_product_id_key UNIQUE (warehouse_id, product_id);


--
-- Name: warehouses warehouses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouses
    ADD CONSTRAINT warehouses_pkey PRIMARY KEY (id);


--
-- Name: warehouses warehouses_region_id_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouses
    ADD CONSTRAINT warehouses_region_id_code_key UNIQUE (region_id, code);


--
-- Name: idx_shipment_orders_region; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipment_orders_region ON public.shipment_orders USING btree (region_code);


--
-- Name: idx_shipment_orders_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipment_orders_status ON public.shipment_orders USING btree (status);


--
-- Name: shipment_events shipment_events_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_events
    ADD CONSTRAINT shipment_events_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.shipment_orders(id) ON DELETE CASCADE;


--
-- Name: shipment_items shipment_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_items
    ADD CONSTRAINT shipment_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.shipment_orders(id) ON DELETE CASCADE;


--
-- Name: shipment_items shipment_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_items
    ADD CONSTRAINT shipment_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: shipment_orders shipment_orders_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_orders
    ADD CONSTRAINT shipment_orders_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses(id);


--
-- Name: stock_balances stock_balances_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_balances
    ADD CONSTRAINT stock_balances_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: stock_balances stock_balances_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_balances
    ADD CONSTRAINT stock_balances_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouses(id);


--
-- Name: warehouses warehouses_region_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouses
    ADD CONSTRAINT warehouses_region_id_fkey FOREIGN KEY (region_id) REFERENCES public.regions(id);


--
-- PostgreSQL database dump complete
--

\unrestrict JI29HgZm8J8PkVFkH0c4yY53O7epDGGw8ymLpEo5DQHepJCnfDaqqX59z2xtQ3c

