#!/usr/bin/env bash
# Выгрузка БД со стенда (pg_dump с primary WEST и EAST).
# Запуск при поднятом compose:
#   ./scripts/make_dump.sh
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${DUMP_DIR:-dump}"
mkdir -p "$OUT"
STAMP="$(date +%Y%m%d_%H%M%S)"

need() {
  if ! docker ps --format '{{.Names}}' | grep -qx "$1"; then
    echo "ERROR: контейнер $1 не запущен. Сначала: docker compose up -d && ./scripts/bootstrap_schema.sh" >&2
    exit 1
  fi
}

need rdb-west-primary
need rdb-east-primary

echo "==> dump WEST primary → $OUT/west_warehouse.sql"
docker exec rdb-west-primary pg_dump -U warehouse -d warehouse \
  --no-owner --no-privileges --clean --if-exists \
  > "$OUT/west_warehouse.sql"

echo "==> dump EAST primary → $OUT/east_warehouse.sql"
docker exec rdb-east-primary pg_dump -U warehouse -d warehouse \
  --no-owner --no-privileges --clean --if-exists \
  > "$OUT/east_warehouse.sql"

# архив для сдачи
ARCHIVE="$OUT/warehouse_dumps_${STAMP}.tar.gz"
tar -czf "$ARCHIVE" -C "$OUT" west_warehouse.sql east_warehouse.sql
cp -f "$OUT/west_warehouse.sql" "$OUT/west_warehouse_latest.sql"
cp -f "$OUT/east_warehouse.sql" "$OUT/east_warehouse_latest.sql"

# краткий README
cat > "$OUT/README.txt" << EOF
Выгрузка базы индивидуального проекта РБД
========================================
Дата: $(date '+%Y-%m-%d %H:%M:%S')
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
EOF

echo "OK: $OUT/west_warehouse.sql"
echo "OK: $OUT/east_warehouse.sql"
echo "OK: $ARCHIVE"
wc -l "$OUT/west_warehouse.sql" "$OUT/east_warehouse.sql"
