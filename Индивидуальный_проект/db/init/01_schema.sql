-- Schema for regional warehouse perimeter (3NF + FK)
-- Applied on each regional primary. Seed differs by REGION_CODE env via separate seed files.

CREATE TABLE IF NOT EXISTS regions (
    id          SMALLSERIAL PRIMARY KEY,
    code        VARCHAR(16) NOT NULL UNIQUE,
    name        VARCHAR(128) NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouses (
    id          SERIAL PRIMARY KEY,
    region_id   SMALLINT NOT NULL REFERENCES regions(id),
    code        VARCHAR(32) NOT NULL,
    name        VARCHAR(128) NOT NULL,
    UNIQUE (region_id, code)
);

CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    sku         VARCHAR(64) NOT NULL UNIQUE,
    title       VARCHAR(256) NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_balances (
    id              SERIAL PRIMARY KEY,
    warehouse_id    INT NOT NULL REFERENCES warehouses(id),
    product_id      INT NOT NULL REFERENCES products(id),
    qty_available   INT NOT NULL CHECK (qty_available >= 0),
    qty_reserved    INT NOT NULL DEFAULT 0 CHECK (qty_reserved >= 0),
    UNIQUE (warehouse_id, product_id),
    CHECK (qty_reserved >= 0)
);

CREATE TABLE IF NOT EXISTS shipment_orders (
    id              SERIAL PRIMARY KEY,
    warehouse_id    INT NOT NULL REFERENCES warehouses(id),
    region_code     VARCHAR(16) NOT NULL,
    status          VARCHAR(32) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN (
        'CREATED', 'RESERVED', 'PICKING', 'SHIPPED', 'DELIVERED', 'CANCELLED'
    ))
);

CREATE INDEX IF NOT EXISTS idx_shipment_orders_region ON shipment_orders(region_code);
CREATE INDEX IF NOT EXISTS idx_shipment_orders_status ON shipment_orders(status);

CREATE TABLE IF NOT EXISTS shipment_items (
    id          SERIAL PRIMARY KEY,
    order_id    INT NOT NULL REFERENCES shipment_orders(id) ON DELETE CASCADE,
    product_id  INT NOT NULL REFERENCES products(id),
    qty         INT NOT NULL CHECK (qty > 0),
    UNIQUE (order_id, product_id)
);

CREATE TABLE IF NOT EXISTS shipment_events (
    id          SERIAL PRIMARY KEY,
    order_id    INT NOT NULL REFERENCES shipment_orders(id) ON DELETE CASCADE,
    from_status VARCHAR(32),
    to_status   VARCHAR(32) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note        TEXT
);
