#!/usr/bin/env python3
"""Часть 2 через sudo postgres: promote + split."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ssh_util import VM1, VM2, connect, sudo_ok


def main() -> None:
    print("=== Promote VM2 ===")
    c2 = connect(VM2)
    sudo_ok(
        c2,
        """
        set -e
        sudo -u postgres psql -c "SELECT pg_promote();" || true
        rm -f /var/lib/postgresql/16/main/standby.signal
        systemctl restart postgresql
        sleep 3
        sudo -u postgres psql -tAc "SELECT pg_is_in_recovery();"
        """,
    )
    c2.close()

    c1 = connect(VM1)
    sudo_ok(c1, "sudo -u postgres psql -c \"SELECT pg_drop_replication_slot('slot_lab4');\" || true")
    c1.close()

    print("=== Split on VM2 (personal only) ===")
    c2 = connect(VM2)
    sudo_ok(
        c2,
        """
        set -e
        sudo -u postgres psql -d university_db -v ON_ERROR_STOP=1 <<'SQL'
DROP TABLE IF EXISTS _personal_students CASCADE;
CREATE TABLE _personal_students AS
SELECT id, last_name, first_name, middle_name, birth_date, city, street, house_number, email
FROM students;

DROP TABLE IF EXISTS _personal_phones CASCADE;
CREATE TABLE _personal_phones AS SELECT id, student_id, phone_number FROM phones;

DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS teacher_subjects CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;
DROP TABLE IF EXISTS time_slots CASCADE;
DROP TABLE IF EXISTS avg_group_subject CASCADE;
DROP TABLE IF EXISTS avg_group_all CASCADE;
DROP TABLE IF EXISTS avg_subject CASCADE;
DROP TABLE IF EXISTS student_extra_params CASCADE;
DROP TABLE IF EXISTS extra_param_defs CASCADE;
DROP TABLE IF EXISTS phones CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS groups CASCADE;
DROP TABLE IF EXISTS directions CASCADE;

CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    last_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    birth_date DATE NOT NULL,
    city VARCHAR(100) NOT NULL,
    street VARCHAR(100) NOT NULL,
    house_number VARCHAR(20) NOT NULL,
    email VARCHAR(100) UNIQUE
);
INSERT INTO students SELECT * FROM _personal_students;

CREATE TABLE phones (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL
);
INSERT INTO phones SELECT * FROM _personal_phones;
CREATE SEQUENCE IF NOT EXISTS phones_id_seq;
SELECT setval('phones_id_seq', COALESCE((SELECT MAX(id) FROM phones), 1));
ALTER TABLE phones ALTER COLUMN id SET DEFAULT nextval('phones_id_seq');

DROP TABLE _personal_students;
DROP TABLE _personal_phones;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO db1_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO db1_user;

SELECT 'students', COUNT(*) FROM students
UNION ALL SELECT 'phones', COUNT(*) FROM phones;
SQL
        """,
    )
    c2.close()

    print("=== Split on VM1 (university, anonymize personal) ===")
    c1 = connect(VM1)
    sudo_ok(
        c1,
        """
        set -e
        sudo -u postgres psql -d university_db -v ON_ERROR_STOP=1 <<'SQL'
DROP TABLE IF EXISTS phones CASCADE;

ALTER TABLE students
  ALTER COLUMN last_name DROP NOT NULL,
  ALTER COLUMN first_name DROP NOT NULL,
  ALTER COLUMN birth_date DROP NOT NULL,
  ALTER COLUMN city DROP NOT NULL,
  ALTER COLUMN street DROP NOT NULL,
  ALTER COLUMN house_number DROP NOT NULL;

UPDATE students SET
  last_name = NULL,
  first_name = NULL,
  middle_name = NULL,
  birth_date = NULL,
  city = NULL,
  street = NULL,
  house_number = NULL,
  email = NULL;

SELECT 'anon_students', COUNT(*) FROM students WHERE last_name IS NULL
UNION ALL SELECT 'grades', COUNT(*) FROM grades
UNION ALL SELECT 'groups', COUNT(*) FROM groups;
SQL
        """,
    )
    c1.close()
    print("PART2_OK")


if __name__ == "__main__":
    main()
