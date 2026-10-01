#!/usr/bin/env bash
# Надёжный запуск демо с логом (обход «пустого» терминала)
set -euo pipefail
cd "$(dirname "$0")"
LOG="screenshots/json/last_demo.log"
mkdir -p screenshots/json

echo "=========================================="
echo " Запуск демо индивидуального проекта"
echo "=========================================="
echo ""
echo "1) Проверка API..."
if ! curl -sf --connect-timeout 3 http://127.0.0.1:8000/health >/dev/null; then
  echo ""
  echo "ОШИБКА: API не отвечает на :8000"
  echo "Открой ДРУГОЙ терминал и выполни:"
  echo "  cd \"$PWD\""
  echo "  source .venv/bin/activate"
  echo "  uvicorn client.app.main:app --host 127.0.0.1 --port 8000"
  echo ""
  echo "Оставь его открытым, потом снова: ./запуск_демо.sh"
  exit 1
fi
echo "   API OK"
echo ""
echo "2) Демо идёт ~1–2 мин. Вывод дублируется в:"
echo "   $PWD/$LOG"
echo ""

bash ./scripts/demo.sh 2>&1 | tee "$LOG"
ec=${PIPESTATUS[0]}

echo ""
echo "=========================================="
echo " Код выхода: $ec"
echo " Лог: $LOG"
echo " Смотреть: less -R $LOG"
echo "=========================================="
exit "$ec"
