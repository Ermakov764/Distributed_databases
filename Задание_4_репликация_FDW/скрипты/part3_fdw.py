#!/usr/bin/env python3
"""Часть 3: postgres_fdw — личные данные VM2 как внешние таблицы на VM1."""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ssh_util import VM1, VM2, connect, sudo_ok


def setup_fdw() -> None:
    print("=== FDW on VM1 → personal from VM2 ===")
    c = connect(VM1)
    # нужны права суперпользователя для CREATE EXTENSION / USER MAPPING
    sudo_ok(
        c,
        f"""
        set -e
        sudo -u postgres psql -d university_db -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

DROP USER MAPPING IF EXISTS FOR db1_user SERVER personal_server;
DROP USER MAPPING IF EXISTS FOR postgres SERVER personal_server;
DROP SERVER IF EXISTS personal_server CASCADE;

CREATE SERVER personal_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host '{VM2}', port '5432', dbname 'university_db');

CREATE USER MAPPING FOR db1_user
  SERVER personal_server
  OPTIONS (user 'db1_user', password '1');

CREATE USER MAPPING FOR postgres
  SERVER personal_server
  OPTIONS (user 'db1_user', password '1');

DROP FOREIGN TABLE IF EXISTS students_personal CASCADE;
DROP FOREIGN TABLE IF EXISTS phones_personal CASCADE;

CREATE FOREIGN TABLE students_personal (
    id INTEGER,
    last_name VARCHAR(100),
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    birth_date DATE,
    city VARCHAR(100),
    street VARCHAR(100),
    house_number VARCHAR(20),
    email VARCHAR(100)
) SERVER personal_server
  OPTIONS (schema_name 'public', table_name 'students');

CREATE FOREIGN TABLE phones_personal (
    id INTEGER,
    student_id INTEGER,
    phone_number VARCHAR(20)
) SERVER personal_server
  OPTIONS (schema_name 'public', table_name 'phones');

-- представление «полная карточка студента» для скриптов 1-й лабы
CREATE OR REPLACE VIEW v_students_full AS
SELECT
    s.id,
    sp.last_name,
    sp.first_name,
    sp.middle_name,
    sp.birth_date,
    sp.city,
    sp.street,
    sp.house_number,
    sp.email,
    s.group_id,
    s.is_budget
FROM students s
JOIN students_personal sp ON sp.id = s.id;

GRANT SELECT ON students_personal TO db1_user;
GRANT SELECT ON phones_personal TO db1_user;
GRANT SELECT ON v_students_full TO db1_user;
SQL
        """
    )
    c.close()

    # smoke test as db1_user
    conn = psycopg2.connect(
        host=VM1, dbname="university_db", user="db1_user", password="1"
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT g.name, sp.last_name, sp.first_name, s.is_budget
          FROM students s
          JOIN students_personal sp ON sp.id = s.id
          JOIN groups g ON g.id = s.group_id
         ORDER BY sp.last_name
         LIMIT 5
        """
    )
    print("sample FDW join:")
    for row in cur.fetchall():
        print(" ", row)
    cur.execute("SELECT COUNT(*) FROM v_students_full")
    print("v_students_full count:", cur.fetchone()[0])
    conn.close()
    print("PART3_FDW_OK")


if __name__ == "__main__":
    setup_fdw()
