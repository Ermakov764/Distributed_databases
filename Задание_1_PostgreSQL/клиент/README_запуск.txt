Клиент задания 1 (PostgreSQL) — портативный пакет

Все SQL + вывод:
  export PGPASSWORD=1
  bash run_all.sh
  # или: bash показать_все_sql.sh

Интерактивно:
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  python 1_task.py

Подключение по умолчанию: 192.168.122.59 / university_db / db1_user / 1
Переопределение: export PGHOST=… PGPORT=… PGDATABASE=… PGUSER=… PGPASSWORD=…
Пути к вашему домашнему каталогу в скриптах не зашиты — запуск из этой папки.
