#!/usr/bin/env bash
# Демо задания 1 → и в терминал, и в файл lab1_demo_output.txt
# Запуск:
#   export PGPASSWORD=1
#   bash run_all.sh
#
# Если в терминале «пусто» — откройте lab1_demo_output.txt в редакторе.

set -u
cd "$(dirname "$0")"
OUT="$(pwd)/lab1_demo_output.txt"
export PGPASSWORD="${PGPASSWORD:-1}"
export PAGER=cat
export LESS='-F -X'

{
  echo "========== lab1 demo $(date '+%F %T') =========="
  echo "cwd=$(pwd)"
  echo "user=$(id -un)  bash=$BASH_VERSION"
  echo "psql=$(command -v psql || echo NOT_FOUND)"
  echo "host=${PGHOST:-192.168.122.59}  db=${PGDATABASE:-university_db}"
  echo
  /usr/bin/bash ./показать_все_sql.sh
  echo
  echo "========== done exit=$? =========="
} 2>&1 | tee "$OUT"

echo
echo "Готово. Полный вывод также в файле:"
echo "  $OUT"
