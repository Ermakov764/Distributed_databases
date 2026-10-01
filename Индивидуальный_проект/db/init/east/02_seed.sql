-- Seed for EAST primary only
INSERT INTO regions (code, name) VALUES ('EAST', 'Восточный регион')
ON CONFLICT (code) DO NOTHING;

INSERT INTO warehouses (region_id, code, name)
SELECT r.id, 'WH-EAST-1', 'Склад Восток-1'
FROM regions r WHERE r.code = 'EAST'
ON CONFLICT (region_id, code) DO NOTHING;

INSERT INTO products (sku, title) VALUES
    ('SKU-100', 'Кабель оптический 1м'),
    ('SKU-200', 'Блок питания ИБП'),
    ('SKU-300', 'Коммутатор 24p')
ON CONFLICT (sku) DO NOTHING;

INSERT INTO stock_balances (warehouse_id, product_id, qty_available, qty_reserved)
SELECT w.id, p.id, q.qty, 0
FROM warehouses w
JOIN regions r ON r.id = w.region_id AND r.code = 'EAST'
CROSS JOIN (VALUES
    ('SKU-100', 80),
    ('SKU-200', 40),
    ('SKU-300', 15)
) AS q(sku, qty)
JOIN products p ON p.sku = q.sku
ON CONFLICT (warehouse_id, product_id) DO NOTHING;
