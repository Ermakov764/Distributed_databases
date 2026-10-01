#!/usr/bin/env python3
"""Заполнение MongoDB university_db данными для задания 2."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from random import Random

from pymongo import ASCENDING, MongoClient

import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://192.168.122.59:27017")
DB_NAME = os.environ.get("MONGO_DB", "university_db")
SEED = 42


DIRECTIONS = [
    "Информатика и вычислительная техника",
    "Программная инженерия",
    "Прикладная математика и информатика",
    "Информационная безопасность",
    "Системный анализ и управление",
]

GROUP_PREFIX = {
    "Информатика и вычислительная техника": "ИВТ",
    "Программная инженерия": "ПИ",
    "Прикладная математика и информатика": "ПМИ",
    "Информационная безопасность": "ИБ",
    "Системный анализ и управление": "САУ",
}

SUBJECTS_BY_DIR = {
    "Информатика и вычислительная техника": [
        "Архитектура ЭВМ",
        "Операционные системы",
        "Компьютерные сети",
    ],
    "Программная инженерия": [
        "Базы данных",
        "Объектно-ориентированное программирование",
        "Тестирование ПО",
    ],
    "Прикладная математика и информатика": [
        "Дискретная математика",
        "Теория вероятностей",
        "Численные методы",
    ],
    "Информационная безопасность": [
        "Криптография",
        "Защита информации",
        "Сетевая безопасность",
    ],
    "Системный анализ и управление": [
        "Теория управления",
        "Моделирование систем",
        "Исследование операций",
    ],
}

# 7 «уникальных» названий для отчёта (фактически 15 по направлениям —
# в ТЗ: 7 различных предметов минимум, у нас больше)
TEACHERS = [
    ("Смирнов", "Алексей", "Иванович"),
    ("Петрова", "Елена", "Сергеевна"),
    ("Иванов", "Дмитрий", "Петрович"),
    ("Козлова", "Анна", "Владимировна"),
    ("Волков", "Сергей", "Николаевич"),
]

LAST = [
    "Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Васильев",
    "Соколов", "Михайлов", "Новиков", "Фёдоров", "Морозов", "Волков", "Алексеев",
    "Лебедев", "Семёнов", "Егоров", "Павлов", "Козлов", "Степанов", "Николаев",
    "Орлов", "Андреев", "Макаров", "Никитин", "Захаров", "Зайцев", "Соловьёв",
    "Борисов", "Яковлев", "Григорьев", "Романов", "Воробьёв", "Сергеев",
    "Абрамов", "Авдеев", "Агапов", "Аксёнов", "Антонов", "Виноградов",
    "Ермаков", "Ершов", "Лаврентьев", "Тихонов", "Белов", "Комаров",
]
FIRST = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", "Артём",
    "Илья", "Кирилл", "Михаил", "Никита", "Егор", "Иван", "Роман", "Владимир",
    "Анна", "Мария", "Елена", "Ольга", "Наталья", "Екатерина", "Дарья",
    "Полина", "Алина", "Виктория",
]
MIDDLE = [
    "Александрович", "Дмитриевич", "Сергеевич", "Андреевич", "Алексеевич",
    "Иванович", "Петрович", "Николаевич", "Владимирович", "Михайлович",
    "Александровна", "Дмитриевна", "Сергеевна", "Андреевна", "Алексеевна",
    "Ивановна", "Петровна", "Николаевна", "Владимировна", "Михайловна",
]
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург", "Нижний Новгород"]
STREETS = ["Ленина", "Пушкина", "Гагарина", "Мира", "Советская", "Центральная", "Садовая"]


def daterange_birth(rng: Random) -> datetime:
    start = date(1998, 1, 1)
    end = date(2005, 12, 28)
    delta = (end - start).days
    d = start + timedelta(days=rng.randint(0, delta))
    return datetime(d.year, d.month, d.day)


def main() -> None:
    rng = Random(SEED)
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    db = client[DB_NAME]

    # Полная пересборка
    client.drop_database(DB_NAME)
    db = client[DB_NAME]

    # --- directions ---
    dir_ids = {}
    for name in DIRECTIONS:
        _id = db.directions.insert_one({"name": name}).inserted_id
        dir_ids[name] = _id

    # --- groups (3 на направление, разные размеры групп студентов) ---
    group_docs = []
    sizes = [15, 16, 17, 18, 15, 16, 20, 15, 16, 17, 15, 18, 16, 15, 16]  # 15 групп
    gi = 0
    for year_base, (dname, prefix) in enumerate(GROUP_PREFIX.items(), start=1):
        for k in range(3):
            gname = f"{prefix}-{year_base}0{k + 1}"
            gid = db.groups.insert_one(
                {"name": gname, "direction_id": dir_ids[dname]}
            ).inserted_id
            group_docs.append((gid, gname, dname, sizes[gi]))
            gi += 1

    # --- students + phones ---
    student_by_group: dict = {g[0]: [] for g in group_docs}
    all_students = []
    sn = 0
    for gid, gname, dname, n_stud in group_docs:
        for i in range(n_stud):
            ln = LAST[(sn + i * 3) % len(LAST)]
            fn = FIRST[(sn + i * 5) % len(FIRST)]
            mn = MIDDLE[(sn + i * 7) % len(MIDDLE)]
            email = f"s{sn}.{ln.lower()}@uni.local".replace("ё", "e")
            doc = {
                "last_name": ln,
                "first_name": fn,
                "middle_name": mn,
                "birth_date": daterange_birth(rng),
                "city": rng.choice(CITIES),
                "street": rng.choice(STREETS),
                "house_number": str(rng.randint(1, 120)),
                "email": email,
                "group_id": gid,
                "is_budget": rng.random() < 0.65,
            }
            sid = db.students.insert_one(doc).inserted_id
            student_by_group[gid].append(sid)
            all_students.append((sid, gid, dname))
            # 1–2 телефона
            phones = [{"student_id": sid, "phone_number": f"+7900{1000000 + sn:07d}"}]
            if sn % 3 == 0:
                phones.append(
                    {"student_id": sid, "phone_number": f"+7980{2000000 + sn:07d}"}
                )
            db.phones.insert_many(phones)
            sn += 1

    # --- teachers ---
    teacher_ids = []
    for ln, fn, mn in TEACHERS:
        teacher_ids.append(
            db.teachers.insert_one(
                {"last_name": ln, "first_name": fn, "middle_name": mn}
            ).inserted_id
        )

    # --- subjects + teacher_subjects ---
    subject_ids_by_dir: dict = {d: [] for d in DIRECTIONS}
    all_subjects = []  # (sid, dname, tid)
    ti = 0
    for dname, subj_list in SUBJECTS_BY_DIR.items():
        for sname in subj_list:
            sid = db.subjects.insert_one(
                {"name": sname, "direction_id": dir_ids[dname]}
            ).inserted_id
            tid = teacher_ids[ti % len(teacher_ids)]
            ti += 1
            db.teacher_subjects.insert_one({"teacher_id": tid, "subject_id": sid})
            subject_ids_by_dir[dname].append(sid)
            all_subjects.append((sid, dname, tid))

    # --- grades: ≥80% студентов по предметам своего направления ---
    grade_vals = [2, 3, 3, 4, 4, 4, 5, 5, None]
    for sid, gid, dname in all_students:
        for subj_id in subject_ids_by_dir[dname]:
            if rng.random() < 0.85:  # ~85% имеют запись
                g = rng.choice(grade_vals)
                db.grades.insert_one(
                    {"student_id": sid, "subject_id": subj_id, "grade": g}
                )

    # --- time_slots (длительность любая: не только 1.5 ч) ---
    slots = [
        (1, time(8, 0), time(9, 30)),    # 1.50 ч
        (2, time(9, 40), time(11, 10)),  # 1.50 ч
        (3, time(11, 20), time(12, 5)),  # 0.75 ч
        (4, time(13, 0), time(15, 0)),   # 2.00 ч
        (5, time(15, 10), time(16, 40)), # 1.50 ч
        (6, time(16, 50), time(18, 20)), # 1.50 ч
    ]
    slot_ids = []
    for num, st, et in slots:
        slot_ids.append(
            db.time_slots.insert_one(
                {
                    "pair_number": num,
                    "start_time": f"{st.hour:02d}:{st.minute:02d}",
                    "end_time": f"{et.hour:02d}:{et.minute:02d}",
                }
            ).inserted_id
        )

    # --- attendance: 3 группы из разных направлений ---
    chosen_groups = [group_docs[0], group_docs[3], group_docs[6]]  # ИВТ, ПИ, ПМИ
    base_day = date(2025, 9, 1)
    for gid, gname, dname, _ in chosen_groups:
        subj_id = subject_ids_by_dir[dname][0]
        # преподаватель предмета
        ts = db.teacher_subjects.find_one({"subject_id": subj_id})
        tid = ts["teacher_id"]
        studs = student_by_group[gid]
        for day_off in range(5):  # 5 занятий
            day = base_day + timedelta(days=day_off)
            slot = slot_ids[day_off % len(slot_ids)]
            for sid in studs:
                db.attendance.insert_one(
                    {
                        "student_id": sid,
                        "subject_id": subj_id,
                        "teacher_id": tid,
                        "date": datetime(day.year, day.month, day.day),
                        "time_slot_id": slot,
                        "is_present": rng.random() < 0.82,
                    }
                )

    # индексы
    db.directions.create_index("name", unique=True)
    db.groups.create_index("name", unique=True)
    db.students.create_index("email", unique=True)
    db.students.create_index("group_id")
    db.students.create_index("last_name")
    db.phones.create_index("student_id")
    db.subjects.create_index([("name", ASCENDING), ("direction_id", ASCENDING)], unique=True)
    db.grades.create_index([("student_id", ASCENDING), ("subject_id", ASCENDING)], unique=True)
    db.teacher_subjects.create_index(
        [("teacher_id", ASCENDING), ("subject_id", ASCENDING)], unique=True
    )
    db.attendance.create_index([("subject_id", ASCENDING), ("date", ASCENDING)])

    print("=== university_db заполнена ===")
    for col in [
        "directions", "groups", "students", "phones", "teachers",
        "subjects", "teacher_subjects", "grades", "time_slots", "attendance",
    ]:
        print(f"  {col}: {db[col].count_documents({})}")


if __name__ == "__main__":
    main()
