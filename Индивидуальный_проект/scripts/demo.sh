#!/usr/bin/env bash
# Сразу пишем в терминал — чтобы было видно, что скрипт реально стартовал
echo "=== demo.sh: старт $(date '+%H:%M:%S') ==="
echo "=== если дальше пусто — смотри screenshots/json/last_demo.log ==="

# Полный демо-прогон API: оба региона, CRUD, статусы, отказы, failover
# По умолчанию: пояснения + краткий итог (не простыня JSON).
# Полный JSON: VERBOSE_JSON=1 ./scripts/demo.sh
set -euo pipefail
trap 'echo ""; echo "ОШИБКА demo.sh: строка $LINENO, команда: $BASH_COMMAND (код $?)"; echo "Если API не запущен: cd Индивидуальный_проект && source .venv/bin/activate && uvicorn client.app.main:app --port 8000"' ERR

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
BASE="${BASE_URL:-http://127.0.0.1:8000}"
OUT_DIR="${OUT_DIR:-$ROOT/screenshots/json}"
mkdir -p "$OUT_DIR"
VERBOSE_JSON="${VERBOSE_JSON:-0}"
LOG="$OUT_DIR/last_demo.log"
: >"$LOG"
log() { echo "$*" | tee -a "$LOG"; }

log "Лог: $LOG"
log "PWD=$(pwd)  bash=$BASH_VERSION  api=$BASE"

TAG="DEMO-$(date +%H%M%S)"

# ---- оформление ----
BOLD=$'\033[1m'
DIM=$'\033[2m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
RED=$'\033[31m'
CYAN=$'\033[36m'
RESET=$'\033[0m'
PYTHON="${PYTHON:-/usr/bin/python3}"

step() {
  local num="$1" title="$2"; shift 2
  echo ""
  echo "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo "${BOLD}${CYAN} ШАГ $num. $title${RESET}"
  echo "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  for line in "$@"; do
    echo "  ${DIM}▸${RESET} $line"
  done
  echo ""
}

section() {
  echo ""
  echo "${BOLD}${GREEN}████████████████████████████████████████████████████${RESET}"
  echo "${BOLD}${GREEN}  $*${RESET}"
  echo "${BOLD}${GREEN}████████████████████████████████████████████████████${RESET}"
  echo ""
}

expect()  { echo "  ${YELLOW}ожидаем:${RESET} $*"; }
got()     { echo "  ${GREEN}получили:${RESET} $*"; }
explain() { echo "  ${CYAN}смысл:${RESET} $*"; }
warn()    { echo "  ${RED}!${RESET} $*"; }

banner_ok() {
  local http_code="$1"; shift
  echo ""
  echo "${GREEN}${BOLD}╔════════════════════════════════════════════════════════╗${RESET}"
  echo "${GREEN}${BOLD}║  ✓ УСПЕХ — запрос выполнен нормально                   ║${RESET}"
  echo "${GREEN}${BOLD}╚════════════════════════════════════════════════════════╝${RESET}"
  echo "  ${GREEN}${BOLD}HTTP $http_code${RESET}${GREEN} — $*${RESET}"
  echo ""
}

banner_expected_fail() {
  local http_code="$1"; shift
  echo ""
  echo "${RED}${BOLD}╔════════════════════════════════════════════════════════╗${RESET}"
  echo "${RED}${BOLD}║  ★ ОЖИДАЕМЫЙ ОТКАЗ — это НЕ баг, а демонстрация ★      ║${RESET}"
  echo "${RED}${BOLD}║  Система правильно НЕ пропустила операцию              ║${RESET}"
  echo "${RED}${BOLD}╚════════════════════════════════════════════════════════╝${RESET}"
  echo "  ${RED}${BOLD}HTTP $http_code${RESET}${RED} — $*${RESET}"
  echo ""
}

show_request() {
  local method="$1" url="$2" body="${3:-}"
  echo "  ${BOLD}запрос:${RESET}  ${CYAN}${method}${RESET} ${url}"
  if [[ -n "$body" ]]; then
    echo "  ${BOLD}тело:${RESET}    ${body}"
  else
    echo "  ${BOLD}тело:${RESET}    ${DIM}(нет)${RESET}"
  fi
}

# Краткое резюме JSON (routing + id/status), чтобы не заливать экран
summarize_json() {
  local file="$1"
  "$PYTHON" - "$file" <<'PY' 2>/dev/null || echo "  (полный ответ в файле)"
import json, sys
p = sys.argv[1]
try:
    d = json.load(open(p, encoding="utf-8"))
except Exception as e:
    print(f"  не разобрать JSON: {e}")
    raise SystemExit(0)
if isinstance(d, dict) and "routing" in d:
    r = d["routing"]
    print(f"  routing: region={r.get('region')}  role={r.get('role')}  host={r.get('host')}")
    print(f"  → запись идёт на primary, чтение обычно с replica (смотри role)")
    data = d.get("data")
    if isinstance(data, dict):
        bits = []
        if "id" in data: bits.append(f"id={data['id']}")
        if "status" in data: bits.append(f"status={data['status']}")
        if "order" in data and isinstance(data["order"], dict):
            o = data["order"]
            bits.append(f"order.id={o.get('id')} status={o.get('status')}")
        if "code" in data: bits.append(f"code={data['code']}")
        if "sku" in data: bits.append(f"sku={data['sku']}")
        if "qty_available" in data: bits.append(f"available={data['qty_available']} reserved={data.get('qty_reserved')}")
        if bits:
            print("  data: " + ", ".join(bits))
        else:
            keys = ", ".join(list(data.keys())[:8])
            print(f"  data.keys: {keys}")
    elif isinstance(data, list):
        print(f"  data: список из {len(data)} элементов")
elif isinstance(d, dict) and "detail" in d:
    print(f"  detail: {d['detail']}")
elif isinstance(d, dict) and "nodes" in d:
    for n in d["nodes"]:
        mark = "ok" if n.get("ok") else "DOWN"
        print(f"  [{mark}] {n.get('region')}/{n.get('role')} @ {n.get('dsn_host')} — {n.get('detail')}")
else:
    print(f"  keys: {', '.join(list(d.keys())[:10]) if isinstance(d, dict) else type(d).__name__}")
PY
}

show_response() {
  local file="$1"
  echo "  ${DIM}полный JSON сохранён: $file${RESET}"
  summarize_json "$file"
  if [[ "$VERBOSE_JSON" == "1" ]]; then
    echo "  ${DIM}--- VERBOSE_JSON ---${RESET}"
    "$PYTHON" -m json.tool <"$file" 2>/dev/null || cat "$file" || true
  fi
}

json() { "$PYTHON" -m json.tool 2>/dev/null || cat; }

_parse_curl_args() {
  _METHOD="GET"
  _URL=""
  _BODY=""
  local prev=""
  for a in "$@"; do
    if [[ "$prev" == "-X" ]]; then
      _METHOD="$a"
    elif [[ "$prev" == "-d" ]]; then
      _BODY="$a"
    elif [[ "$a" == http://* || "$a" == https://* ]]; then
      _URL="$a"
    fi
    prev="$a"
  done
  if [[ -z "$_URL" ]]; then
    _URL="(?)"
  fi
}

# usage: save <name> [curl args...]
# optional env MEANING="..." for green banner text
save() {
  local name="$1"; shift
  local meaning="${MEANING:-операция выполнена}"
  _parse_curl_args "$@"
  show_request "$_METHOD" "$_URL" "$_BODY"

  local tmp code
  tmp="$(mktemp)"
  code=$(curl -s --connect-timeout 5 -o "$tmp" -w "%{http_code}" "$@" || echo "000")
  code="${code:0:3}"
  if [[ -z "$code" ]]; then code="000"; fi
  if [[ "$code" == "000" ]]; then
    warn "Нет ответа от API (HTTP $code)."
    warn "Сначала запусти API в другом терминале:"
    warn "  cd \"$ROOT\" && source .venv/bin/activate && uvicorn client.app.main:app --port 8000"
    rm -f "$tmp"
    exit 1
  fi

  cp "$tmp" "$OUT_DIR/${name}.json"
  echo "$code" >"$OUT_DIR/${name}.http"
  case "$code" in
    2*)
      banner_ok "$code" "$meaning"
      show_response "$OUT_DIR/${name}.json"
      ;;
    *)
      warn "неожиданный код $code (ждали успех 2xx)"
      show_response "$OUT_DIR/${name}.json"
      ;;
  esac
  rm -f "$tmp"
  LAST_HTTP="$code"
  MEANING=""  # сброс, чтобы не протекло на следующий save
}

# usage: CODE=$(fail_save name "400|409" "пояснение" curl...)
fail_save() {
  local name="$1" want="$2" why="$3"; shift 3
  _parse_curl_args "$@"
  show_request "$_METHOD" "$_URL" "$_BODY"
  expect "отказ HTTP ${want}"
  explain "$why"

  local code
  code=$(curl -s --connect-timeout 5 -o "$OUT_DIR/${name}.json" -w "%{http_code}" "$@" || echo "000")
  code="${code:0:3}"
  if [[ -z "$code" ]]; then code="000"; fi
  echo "$code" >"$OUT_DIR/${name}.http"

  banner_expected_fail "$code" "$why"

  if [[ "$want" == *"$code"* ]]; then
    echo "  ${RED}${BOLD}✓ код $code совпал с ожидаемым ($want) — отказ сработал как надо${RESET}"
  else
    echo "  ${YELLOW}⚠ получили $code, ждали один из: $want${RESET}"
  fi
  show_response "$OUT_DIR/${name}.json"
  printf '%s\n' "$code"
}

jid() {
  "$PYTHON" -c "import sys,json; d=json.load(open(sys.argv[1])); print($2)" "$1"
}

preflight() {
  echo "${BOLD}==========================================${RESET}"
  echo "${BOLD} DEMO — полный прогон API складского стенда${RESET}"
  echo " TAG=$TAG"
  echo " BASE=$BASE"
  echo " OUT=$OUT_DIR"
  echo "${BOLD}==========================================${RESET}"
  echo ""
  echo "Легенда цветов:"
  echo "  ${GREEN}зелёный блок УСПЕХ${RESET}  — операция прошла (CRUD, статусы, чтение)"
  echo "  ${RED}красный блок ОТКАЗ${RESET}  — специально ломаем/запрещаем (это НЕ баг)"
  echo "  ${CYAN}смысл${RESET}               — зачем шаг нужен на защите"
  echo "  Полный JSON на экран: ${BOLD}VERBOSE_JSON=1 ./scripts/demo.sh${RESET}"
  echo "  (по умолчанию — краткое резюме; файлы всё равно пишутся в OUT)"
  echo ""
  echo "Проверяю, что FastAPI слушает $BASE ..."
  local code
  code=$(curl -s --connect-timeout 3 -o "$OUT_DIR/_preflight_health.json" -w "%{http_code}" \
    "$BASE/health" 2>/dev/null || echo "000")
  code="${code:0:3}"
  if [[ -z "$code" ]]; then code="000"; fi
  if [[ "$code" != "200" ]]; then
    cat <<EOF

${RED}${BOLD}ОШИБКА: API не отвечает${RESET} на ${BOLD}$BASE/health${RESET} (код: $code).

  cd "$ROOT"
  docker compose up -d
  source .venv/bin/activate
  uvicorn client.app.main:app --port 8000

Swagger: ${CYAN}http://127.0.0.1:8000/docs${RESET}
Потом: ./scripts/demo.sh

EOF
    exit 1
  fi
  banner_ok "$code" "API доступен, можно гонять сценарии"
  show_request "GET" "$BASE/health"
  show_response "$OUT_DIR/_preflight_health.json"
}

# =============================================================================
log "=== demo.sh инициализирован, начинаем preflight ==="
preflight

section "ЧАСТЬ A. Успешные сценарии (зелёные блоки) — так и должно работать"

# ---------- 00 ----------
step "00" "HEALTH — живость узлов" \
  "Зачем: показать преподу, что 4 PostgreSQL живы." \
  "Смотри: у каждого узла ok=true; replica → in_recovery=True."
MEANING="все узлы WEST/EAST primary+replica отвечают" \
save 00_health "$BASE/health"
explain "Это не ошибка и не отказ — просто проверка стенда перед демо."

# ---------- WEST warehouses ----------
section "ЧАСТЬ A1. CRUD на WEST (чтение с replica, запись на primary)"

step "01" "LIST warehouses WEST (чтение)" \
  "Зачем: чтение идёт на replica (routing.role обычно replica)."
MEANING="список складов WEST прочитан (скорее всего с replica)" \
save 01_west_warehouses_list "$BASE/api/WEST/warehouses"
explain "В резюме смотри role=replica — чтение не трогает primary."

step "02" "CREATE warehouse WEST (запись → primary)" \
  "Зачем: запись всегда на primary своего региона." \
  "Смотри: data.id — сохраняем как WH_W."
MEANING="склад WEST создан на primary" \
save 02_west_warehouse_create -X POST "$BASE/api/WEST/warehouses" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"WH-W-$TAG\",\"name\":\"Склад Запад $TAG\"}"
WH_W=$(jid "$OUT_DIR/02_west_warehouse_create.json" "d['data']['id']")
got "WH_W=$WH_W — этот id дальше в stock/orders"
explain "routing.role здесь должен быть primary (мы писали)."

step "03" "UPDATE warehouse WEST" \
  "Зачем: проверить PUT CRUD — имя склада обновилось."
MEANING="склад WEST обновлён" \
save 03_west_warehouse_update -X PUT "$BASE/api/WEST/warehouses/$WH_W" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"Склад Запад $TAG (upd)\"}"

# ---------- EAST warehouses ----------
section "ЧАСТЬ A2. То же на EAST — другой фрагмент, не копия WEST"

step "04" "LIST warehouses EAST" \
  "Зачем: EAST — отдельный шард. Склада WH-W с WEST здесь не будет."
MEANING="список складов EAST (свой фрагмент)" \
save 04_east_warehouses_list "$BASE/api/EAST/warehouses"
explain "Горизонтальная фрагментация: данные WEST физически не на EAST."

step "05" "CREATE warehouse EAST" \
  "Зачем: запись на primary EAST."
MEANING="склад EAST создан" \
save 05_east_warehouse_create -X POST "$BASE/api/EAST/warehouses" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"WH-E-$TAG\",\"name\":\"Склад Восток $TAG\"}"
WH_E=$(jid "$OUT_DIR/05_east_warehouse_create.json" "d['data']['id']")
got "WH_E=$WH_E"

step "06" "UPDATE warehouse EAST" \
  "Зачем: CRUD работает одинаково на втором регионе."
MEANING="склад EAST обновлён" \
save 06_east_warehouse_update -X PUT "$BASE/api/EAST/warehouses/$WH_E" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"Склад Восток $TAG (upd)\"}"

# ---------- products ----------
section "ЧАСТЬ A3. Товары — на каждом фрагменте своя копия каталога"

step "07" "LIST products WEST" \
  "Зачем: каталог читается с replica WEST."
MEANING="список товаров WEST" \
save 07_west_products_list "$BASE/api/WEST/products"

step "08" "CREATE product WEST" \
  "Зачем: товар создаётся только на WEST (не «общая таблица на весь мир»)."
MEANING="товар WEST создан локально на шарде" \
save 08_west_product_create -X POST "$BASE/api/WEST/products" \
  -H 'Content-Type: application/json' \
  -d "{\"sku\":\"SKU-W-$TAG\",\"title\":\"Товар WEST $TAG\"}"
PR_W=$(jid "$OUT_DIR/08_west_product_create.json" "d['data']['id']")
got "PR_W=$PR_W"

step "09" "UPDATE product WEST" \
  "Зачем: PUT товара."
MEANING="товар WEST обновлён" \
save 09_west_product_update -X PUT "$BASE/api/WEST/products/$PR_W" \
  -H 'Content-Type: application/json' \
  -d "{\"title\":\"Товар WEST $TAG (upd)\"}"

step "10" "CREATE product EAST" \
  "Зачем: своя копия каталога на EAST."
MEANING="товар EAST создан на своём шарде" \
save 10_east_product_create -X POST "$BASE/api/EAST/products" \
  -H 'Content-Type: application/json' \
  -d "{\"sku\":\"SKU-E-$TAG\",\"title\":\"Товар EAST $TAG\"}"
PR_E=$(jid "$OUT_DIR/10_east_product_create.json" "d['data']['id']")
got "PR_E=$PR_E"

step "11" "LIST products EAST" \
  "Зачем: SKU-W с WEST на EAST не появится — фрагменты независимы."
MEANING="каталог EAST независим от WEST" \
save 11_east_products_list "$BASE/api/EAST/products"

# ---------- stock ----------
section "ЧАСТЬ A4. Остатки (available / reserved)"

step "12" "CREATE stock WEST (available=30)" \
  "Зачем: заводим остаток; reserved стартует с 0." \
  "Смотри: data.id → ST_W."
MEANING="остаток WEST: available=30, reserved=0" \
save 12_west_stock_create -X POST "$BASE/api/WEST/stock" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_W,\"product_id\":$PR_W,\"qty_available\":30}"
ST_W=$(jid "$OUT_DIR/12_west_stock_create.json" "d['data']['id']")
got "ST_W=$ST_W"

step "13" "UPDATE stock WEST → available=28" \
  "Зачем: ручная правка остатка (как инвентаризация)."
MEANING="available вручную поставлен в 28" \
save 13_west_stock_update -X PUT "$BASE/api/WEST/stock/$ST_W" \
  -H 'Content-Type: application/json' \
  -d '{"qty_available":28}'

step "14" "LIST stock WEST" \
  "Зачем: чтение остатков с replica."
MEANING="остатки WEST прочитаны" \
save 14_west_stock_list "$BASE/api/WEST/stock"

step "15" "CREATE stock EAST (available=20)" \
  "Зачем: остаток EAST живёт отдельно."
MEANING="остаток EAST: available=20" \
save 15_east_stock_create -X POST "$BASE/api/EAST/stock" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_E,\"product_id\":$PR_E,\"qty_available\":20}"
ST_E=$(jid "$OUT_DIR/15_east_stock_create.json" "d['data']['id']")
got "ST_E=$ST_E"

step "16" "LIST stock EAST" \
  "Зачем: список остатков EAST."
MEANING="остатки EAST прочитаны" \
save 16_east_stock_list "$BASE/api/EAST/stock"

# ---------- orders before ----------
step "17" "LIST orders WEST и EAST (до демо-заявок)" \
  "Зачем: снимок «до» — потом сравним, что наши заявки появились."
MEANING="список заявок WEST до демо" \
save 17_west_orders_list_before "$BASE/api/WEST/orders"
MEANING="список заявок EAST до демо" \
save 17_east_orders_list_before "$BASE/api/EAST/orders"

# ---------- happy path WEST ----------
section "ЧАСТЬ A5. Заявка WEST: CREATED → … → DELIVERED (счастливый путь)"

step "18" "CREATE order WEST qty=3" \
  "Зачем: заявка status=CREATED + позиция + первая строка журнала." \
  "Остатки пока НЕ меняются — резерв только на RESERVED."
MEANING="заявка WEST создана, status=CREATED" \
save 18_west_order_create -X POST "$BASE/api/WEST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_W,\"product_id\":$PR_W,\"qty\":3}"
ORD_W=$(jid "$OUT_DIR/18_west_order_create.json" "d['data']['order']['id']")
got "ORD_W=$ORD_W"
explain "В БД: INSERT shipment_orders + items + events(NULL→CREATED)."

step "19" "Цепочка статусов WEST → DELIVERED" \
  "Зачем: полный успешный жизненный цикл автомата." \
  "RESERVED: available−3, reserved+3 | SHIPPED: reserved−3 | DELIVERED: конец."
for S in RESERVED PICKING SHIPPED DELIVERED; do
  echo "  ${BOLD}→ переход в $S${RESET}"
  case "$S" in
    RESERVED)
      expect "available уменьшится, reserved увеличится"
      MEANING="RESERVED: товар забронирован на складе"
      ;;
    PICKING)
      expect "только статус; остатки те же"
      MEANING="PICKING: идёт сборка, остатки без изменений"
      ;;
    SHIPPED)
      expect "reserved уменьшится (товар ушёл)"
      MEANING="SHIPPED: резерв списан — товар отгружен"
      ;;
    DELIVERED)
      expect "финал; дальше переходов нет"
      MEANING="DELIVERED: успешный конец жизненного цикла"
      ;;
  esac
  save "19_west_status_$S" -X POST "$BASE/api/WEST/orders/$ORD_W/status" \
    -H 'Content-Type: application/json' \
    -d "{\"to_status\":\"$S\",\"note\":\"demo $S\"}"
  explain "Каждый переход пишется в журнал shipment_events (from→to)."
done

step "20" "EVENTS + stock после DELIVERED (WEST)" \
  "Зачем: показать журнал всей цепочки и что reserved вернулся/обнулился по qty."
MEANING="журнал заявки: вся цепочка статусов" \
save 20_west_events "$BASE/api/WEST/orders/$ORD_W/events"
MEANING="остатки после доставки" \
save 20_west_stock_after_deliver "$BASE/api/WEST/stock"
explain "На защите: открой events в Swagger и скажи «это аудит переходов»."

# ---------- EAST path ----------
section "ЧАСТЬ A6. Тот же автомат на EAST (другой шард)"

step "21" "CREATE order EAST qty=2" \
  "Зачем: заявка на другом фрагменте — свой ORD_E."
MEANING="заявка EAST создана" \
save 21_east_order_create -X POST "$BASE/api/EAST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_E,\"product_id\":$PR_E,\"qty\":2}"
ORD_E=$(jid "$OUT_DIR/21_east_order_create.json" "d['data']['order']['id']")
got "ORD_E=$ORD_E"

step "22" "Статусы EAST → RESERVED → PICKING → SHIPPED" \
  "Зачем: доказываем, что правила статусов те же на EAST."
for S in RESERVED PICKING SHIPPED; do
  echo "  ${BOLD}EAST → $S${RESET}"
  MEANING="EAST: успешный переход в $S" \
  save "22_east_status_$S" -X POST "$BASE/api/EAST/orders/$ORD_E/status" \
    -H 'Content-Type: application/json' \
    -d "{\"to_status\":\"$S\",\"note\":\"east demo $S\"}"
done
MEANING="журнал заявки EAST" \
save 22_east_events "$BASE/api/EAST/orders/$ORD_E/events"

# ---------- CANCELLED ----------
section "ЧАСТЬ A7. Отмены CANCELLED (тоже успех, не ошибка API)"

step "23" "CANCELLED из CREATED (WEST)" \
  "Зачем: отмена до резерва — остатки не трогаем." \
  "В журнале: CREATED → CANCELLED."
MEANING="новая заявка для отмены из CREATED" \
save 23_west_order_for_cancel_created -X POST "$BASE/api/WEST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_W,\"product_id\":$PR_W,\"qty\":1}"
ORD_C1=$(jid "$OUT_DIR/23_west_order_for_cancel_created.json" "d['data']['order']['id']")
MEANING="CANCELLED из CREATED — остатки не менялись" \
save 23_west_cancel_from_created -X POST "$BASE/api/WEST/orders/$ORD_C1/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"CANCELLED","note":"cancel from CREATED"}'
MEANING="журнал отмены из CREATED" \
save 23_west_cancel_created_events "$BASE/api/WEST/orders/$ORD_C1/events"
got "ORD_C1=$ORD_C1"
explain "Это успешный сценарий отмены, не «падение» системы."

step "24" "CANCELLED из RESERVED + возврат остатка (WEST)" \
  "Зачем: после RESERVED отмена делает unreserve: available+, reserved−."
MEANING="остатки ДО резерва/отмены" \
save 24_west_stock_before_reserve_cancel "$BASE/api/WEST/stock"
MEANING="заявка для отмены из RESERVED" \
save 24_west_order_for_cancel_reserved -X POST "$BASE/api/WEST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_W,\"product_id\":$PR_W,\"qty\":4}"
ORD_C2=$(jid "$OUT_DIR/24_west_order_for_cancel_reserved.json" "d['data']['order']['id']")
MEANING="RESERVED перед отменой (available−4, reserved+4)" \
save 24_west_reserve_before_cancel -X POST "$BASE/api/WEST/orders/$ORD_C2/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"RESERVED","note":"reserve before cancel"}'
MEANING="остатки ПОСЛЕ резерва — reserved вырос" \
save 24_west_stock_after_reserve "$BASE/api/WEST/stock"
explain "Сравни available/reserved с предыдущим шагом."
MEANING="CANCELLED из RESERVED — товар вернулся на полку" \
save 24_west_cancel_from_reserved -X POST "$BASE/api/WEST/orders/$ORD_C2/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"CANCELLED","note":"cancel from RESERVED → unreserve"}'
MEANING="остатки ПОСЛЕ отмены — available вернулся" \
save 24_west_stock_after_unreserve "$BASE/api/WEST/stock"
MEANING="журнал отмены из RESERVED" \
save 24_west_cancel_reserved_events "$BASE/api/WEST/orders/$ORD_C2/events"
got "ORD_C2=$ORD_C2"
explain "Вот доказательство unreserve для препода."

section "ЧАСТЬ B. Намеренные отказы (красные блоки) — система правильно НЕ пускает"
explain "Ниже HTTP 4xx/5xx — это ХОРОШО для защиты: правила работают. Не путай с поломкой стенда."

step "25" "НЕГАТИВ: прыжок CREATED → SHIPPED" \
  "Зачем: автомат статусов запрещает перескакивать этапы." \
  "Ожидаем красный блок и HTTP 400."
MEANING="создали заявку, сейчас нарочно сделаем запрещённый переход" \
save 25_west_order_bad_transition -X POST "$BASE/api/WEST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_W,\"product_id\":$PR_W,\"qty\":1}"
ORD_BAD=$(jid "$OUT_DIR/25_west_order_bad_transition.json" "d['data']['order']['id']")
CODE=$(fail_save 25_bad_transition_SHIPPED "400" \
  "запрещённый переход CREATED→SHIPPED (автомат статусов)" \
  -X POST "$BASE/api/WEST/orders/$ORD_BAD/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"SHIPPED","note":"should fail"}')
got "факт: HTTP $CODE — заявка осталась в CREATED"
explain "Скажи преподу: «переход не из TRANSITIONS → 400»."

step "26" "НЕГАТИВ: DELIVERED → PICKING" \
  "Зачем: из финала назад нельзя." \
  "Ожидаем HTTP 400."
CODE=$(fail_save 26_bad_from_DELIVERED "400" \
  "запрещённый переход DELIVERED→PICKING (финал, назад нельзя)" \
  -X POST "$BASE/api/WEST/orders/$ORD_W/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"PICKING","note":"should fail"}')
got "факт: HTTP $CODE"

step "27" "НЕГАТИВ: CANCELLED из PICKING" \
  "Зачем: отмена только из CREATED/RESERVED." \
  "Сначала доведём заявку EAST до PICKING (это успех), потом запрещённая отмена."
MEANING="заявка EAST для негатива" \
save 27_east_order_picking -X POST "$BASE/api/EAST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_E,\"product_id\":$PR_E,\"qty\":1}"
ORD_P=$(jid "$OUT_DIR/27_east_order_picking.json" "d['data']['order']['id']")
MEANING="EAST → RESERVED (успех)" \
save 27_east_to_reserved -X POST "$BASE/api/EAST/orders/$ORD_P/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"RESERVED"}'
MEANING="EAST → PICKING (успех)" \
save 27_east_to_picking -X POST "$BASE/api/EAST/orders/$ORD_P/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"PICKING"}'
CODE=$(fail_save 27_bad_cancel_from_picking "400" \
  "запрещена отмена из PICKING (только CREATED/RESERVED)" \
  -X POST "$BASE/api/EAST/orders/$ORD_P/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"CANCELLED","note":"should fail"}')
got "факт: HTTP $CODE"

step "28" "НЕГАТИВ: RESERVED при qty=9999" \
  "Зачем: нехватка остатка — заявка создаётся, резерв отклоняется 409."
MEANING="заявка с огромным qty (ещё CREATED — это ок)" \
save 28_west_order_huge -X POST "$BASE/api/WEST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_W,\"product_id\":$PR_W,\"qty\":9999}"
ORD_HUGE=$(jid "$OUT_DIR/28_west_order_huge.json" "d['data']['order']['id']")
CODE=$(fail_save 28_insufficient_stock "409" \
  "недостаточно остатка для резерва (qty=9999)" \
  -X POST "$BASE/api/WEST/orders/$ORD_HUGE/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"RESERVED","note":"should 409"}')
got "факт: HTTP $CODE — status остался CREATED"

# ---------- perimeter ----------
section "ЧАСТЬ B2. Критерий контура (чужой регион)"

step "29" "КОНТУР: статус WEST-заявки через URL EAST" \
  "Зачем: нельзя менять чужой фрагмент." \
  "Ожидаем 403 или 404 (на EAST этой строки нет)."
CODE=$(fail_save 29_cross_region_status "403|404" \
  "критерий контура: заявка WEST недоступна через /api/EAST/..." \
  -X POST "$BASE/api/EAST/orders/$ORD_W/status" \
  -H 'Content-Type: application/json' \
  -d '{"to_status":"CANCELLED"}')
got "факт: HTTP $CODE"
explain "Скажи: «строка с region_code=WEST живёт только на WEST»."

step "30" "КОНТУР: events WEST-заявки через EAST" \
  "Зачем: журнал тоже привязан к фрагменту."
CODE=$(fail_save 30_cross_region_events "403|404" \
  "критерий контура: events чужой заявки на EAST" \
  "$BASE/api/EAST/orders/$ORD_W/events")
got "факт: HTTP $CODE"

step "31" "POST /api/cross-region-denied" \
  "Зачем: учебный эндпоинт всегда 403 — удобно показать одним кликом."
CODE=$(fail_save 31_cross_region_denied "403" \
  "учебный эндпоинт всегда отвечает отказом по контуру" \
  -X POST \
  "$BASE/api/cross-region-denied?from_region=WEST&to_region=EAST&order_id=$ORD_W")
got "факт: HTTP $CODE"

step "32" "LIST orders WEST/EAST после всех операций" \
  "Зачем: итоговые списки — снова успешное чтение."
MEANING="итоговый список заявок WEST" \
save 32_west_orders_list_after "$BASE/api/WEST/orders"
MEANING="итоговый список заявок EAST" \
save 32_east_orders_list_after "$BASE/api/EAST/orders"

# ---------- failover ----------
section "ЧАСТЬ C. Отказ primary WEST (failover) — запись падает, чтение с replica живо"

step "33" "ОТКАЗ УЗЛА: docker stop west-primary" \
  "Зачем: запись WEST должна упасть; чтение stock — с replica (зелёный успех)." \
  "EAST при этом не трогаем."
docker stop rdb-west-primary
sleep 3
explain "Сейчас primary WEST выключен. Следующий POST — ожидаемый отказ."
CODE_W=$(fail_save 33_write_fail "500|503|502|400|409" \
  "запись на WEST primary невозможна (узел остановлен) — демонстрация отказа узла" \
  -X POST "$BASE/api/WEST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_W,\"product_id\":$PR_W,\"qty\":1}")
got "запись: HTTP $CODE_W — так и должно быть при мёртвом primary"

echo ""
explain "А чтение ниже — УСПЕХ с replica (зелёный блок), не ошибка:"
MEANING="чтение WEST stock с replica при мёртвом primary" \
save 33_read_replica "$BASE/api/WEST/stock"
explain "Скажи: «primary умер → писать нельзя, читать с replica можно»."

step "34" "EAST жив, пока WEST primary лежит" \
  "Зачем: фрагменты независимы — EAST продолжает работать."
MEANING="EAST жив во время аварии WEST" \
save 34_east_alive_during_west_outage "$BASE/api/EAST/stock"

step "35" "ВОССТАНОВЛЕНИЕ: docker start west-primary" \
  "Зачем: после healthy запись WEST снова доступна."
docker start rdb-west-primary
echo "  ждём pg_isready..."
for i in $(seq 1 40); do
  if docker exec rdb-west-primary pg_isready -U warehouse -d warehouse >/dev/null 2>&1; then
    got "primary ready через ${i}с"
    break
  fi
  sleep 1
done
sleep 2
MEANING="health после рестарта primary" \
save 35_health_after_restart "$BASE/health"

step "36" "WRITE после восстановления" \
  "Зачем: создать заявку WEST снова — доказательство, что primary ожил."
MEANING="запись WEST снова работает после docker start" \
save 36_west_order_after_recovery -X POST "$BASE/api/WEST/orders" \
  -H 'Content-Type: application/json' \
  -d "{\"warehouse_id\":$WH_W,\"product_id\":$PR_W,\"qty\":1}"
explain "Круг замкнули: stop → отказ записи → start → запись снова OK."

# ---------- cleanup ----------
step "37" "CLEANUP (опционально)" \
  "По умолчанию демо-строки оставляем для Swagger." \
  "Удалить: CLEANUP=1 ./scripts/demo.sh"
if [[ "${CLEANUP:-0}" == "1" ]]; then
  save 37_west_stock_delete -X DELETE "$BASE/api/WEST/stock/$ST_W" || true
  save 37_east_stock_delete -X DELETE "$BASE/api/EAST/stock/$ST_E" || true
  save 37_west_warehouse_delete -X DELETE "$BASE/api/WEST/warehouses/$WH_W" || true
  save 37_east_warehouse_delete -X DELETE "$BASE/api/EAST/warehouses/$WH_E" || true
  save 37_west_product_delete -X DELETE "$BASE/api/WEST/products/$PR_W" || true
  save 37_east_product_delete -X DELETE "$BASE/api/EAST/products/$PR_E" || true
  got "cleanup выполнен"
else
  echo "  ${DIM}пропуск (CLEANUP=0)${RESET}"
fi

echo ""
echo "${BOLD}${GREEN}==========================================${RESET}"
echo "${BOLD}${GREEN} Готово.${RESET} JSON → $OUT_DIR"
echo " WH_W=$WH_W  PR_W=$PR_W  ST_W=$ST_W  ORD_W=$ORD_W"
echo " WH_E=$WH_E  PR_E=$PR_E  ST_E=$ST_E  ORD_E=$ORD_E"
echo " ORD_C1(cancel CREATED)=$ORD_C1  ORD_C2(cancel RESERVED)=$ORD_C2"
echo ""
echo " ${RED}Красные блоки${RESET} в логе = намеренные отказы (400/403/409/падение primary)."
echo " Swagger: $BASE/docs"
echo "${BOLD}${GREEN}==========================================${RESET}"
