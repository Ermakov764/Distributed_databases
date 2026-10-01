#!/bin/bash
set -euo pipefail

# Runs once on primary first init (docker-entrypoint-initdb.d).

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replicator') THEN
            CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicator';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_slot') THEN
            PERFORM pg_create_physical_replication_slot('replica_slot');
        END IF;
    END
    \$\$;
EOSQL

{
  echo "host replication replicator 0.0.0.0/0 md5"
  echo "host all all 0.0.0.0/0 md5"
} >> "$PGDATA/pg_hba.conf"
