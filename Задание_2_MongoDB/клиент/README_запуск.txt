Клиент задания 2 (MongoDB) — портативный пакет

Все запросы + вывод (из корня пакета или клиент/):
  bash показать_все_запросы.sh

Интерактивно:
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  python seed_db.py   # если БД пустая
  python 2_task.py

URI по умолчанию: mongodb://192.168.122.59:27017 / university_db
Переопределение: export MONGO_URI=…  MONGO_DB=…
Пути к домашнему каталогу автора не зашиты.
