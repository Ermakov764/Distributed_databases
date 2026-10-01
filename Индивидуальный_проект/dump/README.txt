Выгрузка базы индивидуального проекта РБД
========================================
Дата: 2026-09-18 00:48:59
Узлы: rdb-west-primary, rdb-east-primary (PostgreSQL 16)
Формат: pg_dump plain SQL (--clean --if-exists)

Файлы:
  west_warehouse.sql  — фрагмент WEST (схема + данные)
  east_warehouse.sql  — фрагмент EAST (схема + данные)
  warehouse_dumps_*.tar.gz — архив обеих выгрузок

Восстановление на чистый PostgreSQL:
  psql -U warehouse -d warehouse -f west_warehouse.sql
  psql -U warehouse -d warehouse -f east_warehouse.sql

На стенде проекта схема также поднимается из db/init/ + seed.
