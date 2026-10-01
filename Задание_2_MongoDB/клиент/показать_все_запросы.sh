#!/usr/bin/env bash
# =============================================================================
# Задание 2 — ВСЕ запросы MongoDB + вывод в терминале
# =============================================================================
# Из корня пакета сдачи:
#   bash показать_все_запросы.sh
#
# Из папки клиент/:
#   bash показать_все_запросы.sh
#
# Из рабочей папки 2_task:
#   bash показать_все_запросы.sh
#
# Скрипт сам найдёт .py / requirements и при необходимости создаст .venv.
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Рабочая папка: где лежит показать_все_запросы.py и (желательно) requirements.txt
if [ -f "$ROOT/показать_все_запросы.py" ] && [ -f "$ROOT/requirements.txt" ]; then
  WORK="$ROOT"
elif [ -f "$ROOT/клиент/показать_все_запросы.py" ]; then
  WORK="$ROOT/клиент"
elif [ -f "$ROOT/показать_все_запросы.py" ]; then
  WORK="$ROOT"
else
  echo "Не найден показать_все_запросы.py рядом со скриптом: $ROOT"
  exit 1
fi

cd "$WORK"
echo "Каталог: $WORK"

REQ="$WORK/requirements.txt"
if [ ! -f "$REQ" ] && [ -f "$ROOT/клиент/requirements.txt" ]; then
  REQ="$ROOT/клиент/requirements.txt"
fi

# Ищем готовый venv: локальный → клиент → _агент_сборка → старый 2_task
activate_venv() {
  local cand
  for cand in \
    "$WORK/.venv/bin/activate" \
    "$ROOT/.venv/bin/activate" \
    "$ROOT/клиент/.venv/bin/activate" \
    "$ROOT/_агент_сборка/2_task/.venv/bin/activate" \
    "$ROOT/../_агент_сборка/2_task/.venv/bin/activate" \
    "$ROOT/../2_task/.venv/bin/activate" \
    "$ROOT/../../2_task/.venv/bin/activate" \
    "$ROOT/../../../2_task/.venv/bin/activate"
  do
    if [ -f "$cand" ]; then
      # shellcheck disable=SC1090
      source "$cand"
      echo "venv: $cand"
      return 0
    fi
  done
  return 1
}

if ! activate_venv; then
  echo "venv нет — создаю в $WORK/.venv …"
  python3 -m venv "$WORK/.venv"
  # shellcheck disable=SC1091
  source "$WORK/.venv/bin/activate"
fi

if ! python -c "import pymongo, tabulate" 2>/dev/null; then
  if [ ! -f "$REQ" ]; then
    echo "Нет requirements.txt и не установлены pymongo/tabulate."
    exit 1
  fi
  echo "Ставлю зависимости из $REQ …"
  pip install -q -r "$REQ"
fi

python показать_все_запросы.py
