#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec > >(tee -a /tmp/rdb_run_everything.log) 2>&1
echo "=== $(date) START ==="
unset COMPOSE_PROJECT_NAME
unset DOCKER_HOST

# start docker if needed
if ! docker info >/dev/null 2>&1; then
  systemctl start docker || sudo systemctl start docker || true
  sleep 3
fi
docker info | head -8

docker compose up -d
for i in $(seq 1 60); do
  ok=0
  docker exec rdb-west-primary pg_isready -U warehouse -d warehouse >/dev/null 2>&1 && \
  docker exec rdb-east-primary pg_isready -U warehouse -d warehouse >/dev/null 2>&1 && ok=1
  [[ $ok -eq 1 ]] && break
  sleep 2
done
docker compose ps

source .venv/bin/activate
python scripts/bootstrap_schema.py

# kill old uvicorn
pkill -f 'uvicorn client.app.main:app' 2>/dev/null || true
sleep 1
uvicorn client.app.main:app --host 127.0.0.1 --port 8000 > /tmp/rdb_uvicorn.log 2>&1 &
echo $! > /tmp/rdb_uvicorn.pid
for i in $(seq 1 30); do
  curl -sf http://127.0.0.1:8000/health >/dev/null && break
  sleep 1
done

./scripts/demo.sh

# screenshots if playwright available
pip install -q playwright 2>/dev/null || true
playwright install chromium 2>/dev/null || true
python scripts/capture_screenshots.py || echo "capture failed: $?"

echo "=== $(date) DONE ==="
ls -la screenshots/ | head -40
