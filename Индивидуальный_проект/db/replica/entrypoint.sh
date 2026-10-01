#!/bin/bash
set -euo pipefail

PRIMARY_HOST="${PRIMARY_HOST:?PRIMARY_HOST required}"
PGUSER="${POSTGRES_USER:-warehouse}"
export PGPASSWORD="${POSTGRES_PASSWORD:-warehouse}"
SLOT_NAME="${SLOT_NAME:-replica_slot}"
DATA_DIR="${PGDATA:-/var/lib/postgresql/data}"

mkdir -p "$DATA_DIR"
chmod 700 "$DATA_DIR" || true

if [ -f "$DATA_DIR/standby.signal" ] || [ -f "$DATA_DIR/postgresql.conf" ]; then
  # Already bootstrapped as replica (or leftover volume) — start postgres as standby if signal exists
  if [ ! -f "$DATA_DIR/standby.signal" ] && [ -f "$DATA_DIR/PG_VERSION" ]; then
    # Dirty volume that isn't a standby — wipe and re-basebackup
    rm -rf "${DATA_DIR:?}/"*
  else
    exec docker-entrypoint.sh postgres \
      -c hot_standby=on \
      -c listen_addresses=* \
      -c primary_conninfo="host=${PRIMARY_HOST} port=5432 user=replicator password=replicator" \
      -c primary_slot_name="${SLOT_NAME}"
  fi
fi

until pg_isready -h "$PRIMARY_HOST" -p 5432 -U "$PGUSER"; do
  echo "Waiting for primary ${PRIMARY_HOST}..."
  sleep 2
done
sleep 3

rm -rf "${DATA_DIR:?}/"*

export PGPASSWORD=replicator
pg_basebackup \
  -h "$PRIMARY_HOST" \
  -p 5432 \
  -U replicator \
  -D "$DATA_DIR" \
  -Fp -Xs -P -R \
  -S "$SLOT_NAME"

chown -R postgres:postgres "$DATA_DIR" 2>/dev/null || true
chmod 700 "$DATA_DIR"

unset PGPASSWORD
export PGPASSWORD="${POSTGRES_PASSWORD:-warehouse}"

exec docker-entrypoint.sh postgres \
  -c hot_standby=on \
  -c listen_addresses=* \
  -c primary_conninfo="host=${PRIMARY_HOST} port=5432 user=replicator password=replicator" \
  -c primary_slot_name="${SLOT_NAME}"
