Клиенты задания 4 — портативный пакет

Часть 2 (два хоста, склейка в Python):
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  python 4_task_distributed.py
  # UNI=.61  PERSONAL=.60  (export PGHOST_UNI / PGHOST_PERSONAL)

Часть 3 (одно подключение + FDW на .61):
  python 4_task_fdw.py
  # export PGHOST=192.168.122.61

Автопроверка split+FDW:
  python demo_all.py

Учётка БД: db1_user / 1, база university_db.
