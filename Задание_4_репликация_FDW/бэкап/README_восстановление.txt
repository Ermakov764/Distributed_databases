Дампы задания 4 (после split):

  vm1_university_db.dump.sql  — university-контур (VM11 .61; имя файла историческое)
  vm2_personal_db.dump.sql    — personal-контур (VM2 .60)

Восстановление (пример):
  export PGPASSWORD=1
  createdb -h 192.168.122.61 -U db1_user university_db   # если пусто
  psql -h 192.168.122.61 -U db1_user -d university_db -f vm1_university_db.dump.sql
  psql -h 192.168.122.60 -U db1_user -d university_db -f vm2_personal_db.dump.sql

FDW настраивается отдельно (см. отчёт §5 / скрипты/part3_fdw.py).
