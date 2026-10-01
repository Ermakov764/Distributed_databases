#!/usr/bin/env bash
# Надёжный bootstrap через docker exec (если python-скрипт зависает).
set -euo pipefail
cd "$(dirname "$0")/.."

docker exec -i rdb-west-primary psql -U warehouse -d warehouse < db/init/01_schema.sql
docker exec -i rdb-west-primary psql -U warehouse -d warehouse < db/init/west/02_seed.sql
docker exec -i rdb-east-primary psql -U warehouse -d warehouse < db/init/01_schema.sql
docker exec -i rdb-east-primary psql -U warehouse -d warehouse < db/init/east/02_seed.sql

echo "OK: schema+seed on WEST/EAST primary (replicas catch up via streaming)"
