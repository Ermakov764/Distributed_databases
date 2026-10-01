#!/usr/bin/env python3
"""Задание 2 — демо всех запросов ТЗ в терминале.

Как показать_все_sql.sh в заданиях 1/3:
  заголовок → полный текст запроса (как в PDF) → таблица ответа.

Важно: MongoDB говорит не на SQL, а на своём языке (find / aggregate).
Текст ниже — тот же MQL, что в Отчет_Задание_2_РБД.pdf.

Запуск:  bash показать_все_запросы.sh
"""

from __future__ import annotations

from datetime import datetime

from pymongo import MongoClient
from tabulate import tabulate

import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://192.168.122.59:27017")
DB_NAME = os.environ.get("MONGO_DB", "university_db")

DIR_NAME = "Информатика и вычислительная техника"
LETTER = "Е"
SUBJECT = "Архитектура ЭВМ"
TEACHER_LN = "Смирнов"


def sep(title: str = ""):
    line = "=" * 69
    print()
    print(line)
    if title:
        print(title)
        print(line)


def show_table(rows, headers=None):
    if not rows:
        print("  (пусто — 0 строк)")
        return
    if headers is None and isinstance(rows[0], dict):
        headers = list(rows[0].keys())
        rows = [[r.get(h) for h in headers] for r in rows]
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print(f"  строк: {len(rows)}")


def demo(qid: int, title: str, code: str, rows):
    """Печать полного запроса (как в PDF) + результат."""
    print()
    print(f"-> Запрос {qid}: {title}")
    print()
    print("MONGO >>>")
    print("-----")
    print(code.strip())
    print("-----")
    print("ответ:")
    show_table(rows)


def slot_hours_expr(prefix: str = "ts"):
    def mins(field: str):
        return {
            "$add": [
                {"$multiply": [{"$toInt": {"$substrBytes": [f"${prefix}.{field}", 0, 2]}}, 60]},
                {"$toInt": {"$substrBytes": [f"${prefix}.{field}", 3, 2]}},
            ]
        }

    return {"$divide": [{"$subtract": [mins("end_time"), mins("start_time")]}, 60.0]}


def main():
    print("=" * 69)
    print(" ЗАДАНИЕ 2 · все запросы MongoDB (текст как в PDF) + вывод")
    print(f" URI: {MONGO_URI}  БД: {DB_NAME}")
    print(" Язык запросов: MongoDB (find / aggregate), не SQL PostgreSQL")
    print("=" * 69)

    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)[DB_NAME]
    db.command("ping")
    stats = {c: db[c].count_documents({}) for c in sorted(db.list_collection_names())}
    print(f"коллекций: {len(stats)}, документов: {sum(stats.values())}")

    # ------------------------------------------------------------------
    sep("1. СТУДЕНТЫ")
    # ------------------------------------------------------------------

    d = db.directions.find_one({"name": DIR_NAME})
    if not d:
        raise SystemExit(f"Направление не найдено: {DIR_NAME}")
    groups = {g["_id"]: g["name"] for g in db.groups.find({"direction_id": d["_id"]})}
    rows = []
    for s in db.students.find({"group_id": {"$in": list(groups)}}).sort(
        [("last_name", 1), ("first_name", 1)]
    ):
        rows.append({
            "Группа": groups[s["group_id"]],
            "ФИО": f"{s.get('last_name', '')} {s.get('first_name', '')}".strip(),
            "Тип": "Бюджет" if s.get("is_budget") else "Внебюджет",
        })
    demo(1, f"группы по направлению «{DIR_NAME}»", f'''
d = db.directions.find_one({{"name": "{DIR_NAME}"}})
groups = {{g["_id"]: g["name"] for g in db.groups.find({{"direction_id": d["_id"]}})}}
list(db.students.find({{"group_id": {{"$in": list(groups.keys())}}}}).sort([
  ("last_name", 1), ("first_name", 1)
]))
''', rows[:20])

    pipe = [
        {"$match": {"last_name": {"$regex": f"^{LETTER}", "$options": "i"}}},
        {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": "$g"},
        {"$lookup": {"from": "directions", "localField": "g.direction_id", "foreignField": "_id", "as": "d"}},
        {"$unwind": "$d"},
        {"$sort": {"last_name": 1}},
        {"$project": {
            "_id": 0,
            "ФИО": {"$concat": ["$last_name", " ", "$first_name"]},
            "Группа": "$g.name",
            "Направление": "$d.name",
        }},
    ]
    demo(2, f"фамилия на «{LETTER}»", f'''
db.students.aggregate([
  {{"$match": {{"last_name": {{"$regex": "^{LETTER}", "$options": "i"}}}}}},
  {{"$lookup": {{"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}}}},
  {{"$unwind": "$g"}},
  {{"$lookup": {{"from": "directions", "localField": "g.direction_id",
               "foreignField": "_id", "as": "d"}}}},
  {{"$unwind": "$d"}},
  {{"$sort": {{"last_name": 1}}}},
  {{"$project": {{
    "ФИО": {{"$concat": ["$last_name", " ", "$first_name"]}},
    "Группа": "$g.name", "Направление": "$d.name"
  }}}}
])
''', list(db.students.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": "$g"},
        {"$addFields": {"m": {"$month": "$birth_date"}, "day": {"$dayOfMonth": "$birth_date"}}},
        {"$sort": {"m": 1, "day": 1}},
        {"$limit": 15},
        {"$project": {
            "_id": 0,
            "ФИО": {"$concat": ["$last_name", " ", "$first_name"]},
            "День": "$day",
            "Месяц": "$m",
            "Группа": "$g.name",
        }},
    ]
    demo(3, "поздравления по месяцам (фрагмент)", '''
db.students.aggregate([
  {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
  {"$unwind": "$g"},
  {"$addFields": {"m": {"$month": "$birth_date"}, "day": {"$dayOfMonth": "$birth_date"}}},
  {"$sort": {"m": 1, "day": 1}}
])
''', list(db.students.aggregate(pipe)))

    pipe = [
        {"$addFields": {
            "Возраст": {"$dateDiff": {"startDate": "$birth_date", "endDate": "$$NOW", "unit": "year"}}
        }},
        {"$sort": {"last_name": 1}},
        {"$limit": 15},
        {"$project": {
            "_id": 0,
            "ФИО": {"$concat": ["$last_name", " ", "$first_name"]},
            "Дата рождения": {"$dateToString": {"format": "%Y-%m-%d", "date": "$birth_date"}},
            "Возраст": 1,
        }},
    ]
    demo(4, "студенты с возрастом", '''
db.students.aggregate([
  {"$addFields": {
    "Возраст": {"$dateDiff": {"startDate": "$birth_date", "endDate": "$$NOW", "unit": "year"}}
  }},
  {"$sort": {"last_name": 1}},
  {"$project": {
    "ФИО": {"$concat": ["$last_name", " ", "$first_name"]},
    "Дата рождения": {"$dateToString": {"format": "%Y-%m-%d", "date": "$birth_date"}},
    "Возраст": 1
  }}
])
''', list(db.students.aggregate(pipe)))

    cur_m = datetime.now().month
    pipe = [
        {"$match": {"$expr": {"$eq": [{"$month": "$birth_date"}, cur_m]}}},
        {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": "$g"},
        {"$project": {
            "_id": 0,
            "ФИО": {"$concat": ["$last_name", " ", "$first_name"]},
            "Дата рождения": {"$dateToString": {"format": "%Y-%m-%d", "date": "$birth_date"}},
            "Группа": "$g.name",
        }},
    ]
    demo(5, "ДР в текущем месяце", f'''
db.students.aggregate([
  {{"$match": {{"$expr": {{"$eq": [{{"$month": "$birth_date"}}, {cur_m}]}}}}}},
  {{"$lookup": {{"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}}}},
  {{"$unwind": "$g"}},
  {{"$sort": {{"day": 1}}}}
])
''', list(db.students.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "groups", "localField": "_id", "foreignField": "direction_id", "as": "g"}},
        {"$unwind": {"path": "$g", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "students", "localField": "g._id", "foreignField": "group_id", "as": "s"}},
        {"$group": {"_id": "$name", "Студентов": {"$sum": {"$size": "$s"}}}},
        {"$sort": {"Студентов": -1}},
        {"$project": {"_id": 0, "Направление": "$_id", "Студентов": 1}},
    ]
    demo(6, "студенты по направлениям", '''
db.directions.aggregate([
  {"$lookup": {"from": "groups", "localField": "_id", "foreignField": "direction_id", "as": "g"}},
  {"$unwind": {"path": "$g", "preserveNullAndEmptyArrays": True}},
  {"$lookup": {"from": "students", "localField": "g._id", "foreignField": "group_id", "as": "s"}},
  {"$group": {"_id": "$name", "Количество студентов": {"$sum": {"$size": "$s"}}}},
  {"$sort": {"Количество студентов": -1}}
])
''', list(db.directions.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "directions", "localField": "direction_id", "foreignField": "_id", "as": "d"}},
        {"$unwind": "$d"},
        {"$lookup": {"from": "students", "localField": "_id", "foreignField": "group_id", "as": "s"}},
        {"$project": {
            "_id": 0,
            "Группа": "$name",
            "Направление": "$d.name",
            "Бюджет": {"$size": {"$filter": {"input": "$s", "as": "x", "cond": "$$x.is_budget"}}},
            "Внебюджет": {"$size": {"$filter": {"input": "$s", "as": "x", "cond": {"$not": "$$x.is_budget"}}}},
        }},
        {"$sort": {"Группа": 1}},
    ]
    demo(7, "бюджет / внебюджет", '''
db.groups.aggregate([
  {"$lookup": {"from": "directions", "localField": "direction_id", "foreignField": "_id", "as": "d"}},
  {"$unwind": "$d"},
  {"$lookup": {"from": "students", "localField": "_id", "foreignField": "group_id", "as": "s"}},
  {"$project": {
    "Группа": "$name", "Направление": "$d.name",
    "Бюджет": {"$size": {"$filter": {"input": "$s", "as": "x", "cond": "$$x.is_budget"}}},
    "Внебюджет": {"$size": {"$filter": {"input": "$s", "as": "x", "cond": {"$not": "$$x.is_budget"}}}}
  }},
  {"$sort": {"Группа": 1}}
])
''', list(db.groups.aggregate(pipe)))

    # ------------------------------------------------------------------
    sep("2. ПРЕДМЕТЫ И ОЦЕНКИ")
    # ------------------------------------------------------------------

    pipe = [
        {"$lookup": {"from": "teacher_subjects", "localField": "_id", "foreignField": "subject_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$lookup": {"from": "teachers", "localField": "ts.teacher_id", "foreignField": "_id", "as": "t"}},
        {"$unwind": "$t"},
        {"$lookup": {"from": "grades", "localField": "_id", "foreignField": "subject_id", "as": "gr"}},
        {"$unwind": "$gr"},
        {"$lookup": {"from": "students", "localField": "gr.student_id", "foreignField": "_id", "as": "s"}},
        {"$unwind": "$s"},
        {"$lookup": {"from": "groups", "localField": "s.group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": "$g"},
        {"$group": {"_id": {
            "subj": "$name",
            "teacher": {"$concat": ["$t.last_name", " ", "$t.first_name"]},
            "group": "$g.name",
        }}},
        {"$project": {"_id": 0, "Предмет": "$_id.subj", "Преподаватель": "$_id.teacher", "Группа": "$_id.group"}},
        {"$sort": {"Предмет": 1, "Группа": 1}},
        {"$limit": 20},
    ]
    demo(8, "группы по предметам с преподавателем", '''
db.subjects.aggregate([
  {"$lookup": {"from": "teacher_subjects", "localField": "_id", "foreignField": "subject_id", "as": "ts"}},
  {"$unwind": "$ts"},
  {"$lookup": {"from": "teachers", "localField": "ts.teacher_id", "foreignField": "_id", "as": "t"}},
  {"$unwind": "$t"},
  {"$lookup": {"from": "grades", "localField": "_id", "foreignField": "subject_id", "as": "gr"}},
  {"$unwind": "$gr"},
  {"$lookup": {"from": "students", "localField": "gr.student_id", "foreignField": "_id", "as": "s"}},
  {"$unwind": "$s"},
  {"$lookup": {"from": "groups", "localField": "s.group_id", "foreignField": "_id", "as": "g"}},
  {"$unwind": "$g"},
  {"$group": {"_id": {"subj": "$name",
                      "teacher": {"$concat": ["$t.last_name", " ", "$t.first_name"]},
                      "group": "$g.name"}}},
  {"$project": {"Предмет": "$_id.subj", "Преподаватель": "$_id.teacher", "Группа": "$_id.group"}}
])
''', list(db.subjects.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "grades", "localField": "_id", "foreignField": "subject_id", "as": "gr"}},
        {"$project": {"_id": 0, "Предмет": "$name", "Студентов": {"$size": {"$setUnion": ["$gr.student_id", []]}}}},
        {"$sort": {"Студентов": -1}},
        {"$limit": 1},
    ]
    demo(9, "дисциплина с макс. числом студентов", '''
db.subjects.aggregate([
  {"$lookup": {"from": "grades", "localField": "_id", "foreignField": "subject_id", "as": "gr"}},
  {"$project": {
    "Предмет": "$name",
    "Студентов": {"$size": {"$setUnion": ["$gr.student_id", []]}}
  }},
  {"$sort": {"Студентов": -1}},
  {"$limit": 1}
])
''', list(db.subjects.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "teacher_subjects", "localField": "_id", "foreignField": "teacher_id", "as": "ts"}},
        {"$lookup": {"from": "grades", "localField": "ts.subject_id", "foreignField": "subject_id", "as": "gr"}},
        {"$project": {
            "_id": 0,
            "Преподаватель": {"$concat": ["$last_name", " ", "$first_name"]},
            "Студентов": {"$size": {"$setUnion": ["$gr.student_id", []]}},
        }},
        {"$sort": {"Студентов": -1}},
    ]
    demo(10, "студенты у преподавателей", '''
db.teachers.aggregate([
  {"$lookup": {"from": "teacher_subjects", "localField": "_id", "foreignField": "teacher_id", "as": "ts"}},
  {"$lookup": {"from": "grades", "localField": "ts.subject_id", "foreignField": "subject_id", "as": "gr"}},
  {"$project": {
    "Преподаватель": {"$concat": ["$last_name", " ", "$first_name"]},
    "Студентов": {"$size": {"$setUnion": ["$gr.student_id", []]}}
  }},
  {"$sort": {"Студентов": -1}}
])
''', list(db.teachers.aggregate(pipe)))

    rows = []
    for sub in db.subjects.find():
        gids = [g["_id"] for g in db.groups.find({"direction_id": sub["direction_id"]})]
        stud_ids = [s["_id"] for s in db.students.find({"group_id": {"$in": gids}})]
        total = len(stud_ids) or 1
        passed = db.grades.count_documents({
            "subject_id": sub["_id"], "student_id": {"$in": stud_ids}, "grade": {"$gt": 2},
        })
        rows.append({
            "Предмет": sub["name"],
            "Всего": len(stud_ids),
            "Сдали": passed,
            "Доля %": round(100.0 * passed / total, 2),
        })
    demo(11, "доля сдавших", '''
# доля сдавших = сдавшие (grade > 2) / все студенты направления предмета
sub = db.subjects.find_one({"name": subject})
stud_ids = [s["_id"] for s in db.students.find({
  "group_id": {"$in": [g["_id"] for g in db.groups.find({"direction_id": sub["direction_id"]})]}
})]
passed = db.grades.count_documents({
  "subject_id": sub["_id"], "student_id": {"$in": stud_ids}, "grade": {"$gt": 2}
})
доля = passed / len(stud_ids)
''', rows)

    pipe = [
        {"$match": {"grade": {"$gt": 2}}},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
        {"$unwind": "$sub"},
        {"$group": {"_id": "$sub.name", "avg": {"$avg": "$grade"}}},
        {"$project": {"_id": 0, "Предмет": "$_id", "Средняя": {"$round": ["$avg", 2]}}},
        {"$sort": {"Средняя": -1}},
    ]
    demo(12, "средняя оценка (сдавшие)", '''
db.grades.aggregate([
  {"$match": {"grade": {"$gt": 2}}},
  {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
  {"$unwind": "$sub"},
  {"$group": {"_id": "$sub.name", "avg": {"$avg": "$grade"}}},
  {"$project": {"Предмет": "$_id", "Средняя оценка": {"$round": ["$avg", 2]}}}
])
''', list(db.grades.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "directions", "localField": "direction_id", "foreignField": "_id", "as": "d"}},
        {"$unwind": "$d"},
        {"$lookup": {"from": "students", "localField": "_id", "foreignField": "group_id", "as": "s"}},
        {"$unwind": "$s"},
        {"$lookup": {"from": "grades", "localField": "s._id", "foreignField": "student_id", "as": "gr"}},
        {"$unwind": {"path": "$gr", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": {"g": "$name", "d": "$d.name"}, "avg": {"$avg": "$gr.grade"}}},
        {"$sort": {"avg": -1}},
        {"$limit": 1},
        {"$project": {
            "_id": 0,
            "Группа": "$_id.g",
            "Направление": "$_id.d",
            "Средняя": {"$round": ["$avg", 2]},
        }},
    ]
    demo(13, "группа с макс. средней", '''
db.groups.aggregate([
  {"$lookup": {"from": "directions", "localField": "direction_id", "foreignField": "_id", "as": "d"}},
  {"$unwind": "$d"},
  {"$lookup": {"from": "students", "localField": "_id", "foreignField": "group_id", "as": "s"}},
  {"$unwind": "$s"},
  {"$lookup": {"from": "grades", "localField": "s._id", "foreignField": "student_id", "as": "gr"}},
  {"$unwind": {"path": "$gr", "preserveNullAndEmptyArrays": True}},
  {"$group": {"_id": {"g": "$name", "d": "$d.name"}, "avg": {"$avg": "$gr.grade"}}},
  {"$sort": {"avg": -1}},
  {"$limit": 1}
])
''', list(db.groups.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": "$g"},
        {"$lookup": {
            "from": "subjects", "localField": "g.direction_id",
            "foreignField": "direction_id", "as": "needed",
        }},
        {"$lookup": {"from": "grades", "localField": "_id", "foreignField": "student_id", "as": "grades"}},
        {"$addFields": {
            "needed_ids": {"$map": {"input": "$needed", "as": "s", "in": "$$s._id"}},
            "needed_cnt": {"$size": "$needed"},
            "five_ids": {
                "$setUnion": [
                    {"$map": {
                        "input": {"$filter": {
                            "input": "$grades", "as": "gr",
                            "cond": {"$eq": ["$$gr.grade", 5]},
                        }},
                        "as": "gr", "in": "$$gr.subject_id",
                    }},
                    [],
                ]
            },
        }},
        {"$addFields": {
            "missing_or_not_five": {"$setDifference": ["$needed_ids", "$five_ids"]},
            "fives_cnt": {"$size": {"$setIntersection": ["$needed_ids", "$five_ids"]}},
        }},
        {"$match": {"$expr": {"$and": [
            {"$gt": ["$needed_cnt", 0]},
            {"$eq": [{"$size": "$missing_or_not_five"}, 0]},
        ]}}},
        {"$project": {
            "_id": 0,
            "ФИО": {"$trim": {"input": {"$concat": [
                "$last_name", " ", "$first_name", " ", {"$ifNull": ["$middle_name", ""]},
            ]}}},
            "Группа": "$g.name",
            "Предметов": "$needed_cnt",
            "Сдано на 5": "$fives_cnt",
        }},
        {"$sort": {"ФИО": 1}},
    ]
    demo(14, "отличники (нет записи/не 5 → не отличник)", '''
db.students.aggregate([
  ...
  # five_ids = subject_id с grade==5
  # missing_or_not_five = needed_ids - five_ids
  # отличник ⇔ missing_or_not_five пуст
  # нет документа оценки / NULL / 0 / 2..4 → предмет в missing → не отличник
])
''', list(db.students.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": {"path": "$g", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "subjects", "localField": "g.direction_id",
            "foreignField": "direction_id", "as": "needed",
        }},
        {"$lookup": {"from": "grades", "localField": "_id", "foreignField": "student_id", "as": "grades"}},
        {"$addFields": {
            "failed": {"$size": {"$filter": {
                "input": "$needed", "as": "subj",
                "cond": {"$eq": [
                    {"$size": {"$filter": {
                        "input": "$grades", "as": "gr",
                        "cond": {"$and": [
                            {"$eq": ["$$gr.subject_id", "$$subj._id"]},
                            {"$gt": ["$$gr.grade", 2]},
                        ]},
                    }}},
                    0,
                ]},
            }}},
        }},
        {"$match": {"failed": {"$gte": 2}}},
        {"$project": {
            "_id": 0,
            "ФИО": {"$trim": {"input": {"$concat": [
                "$last_name", " ", "$first_name", " ", {"$ifNull": ["$middle_name", ""]},
            ]}}},
            "Группа": {"$ifNull": ["$g.name", "?"]},
            "Несданных": "$failed",
        }},
        {"$sort": {"Несданных": -1, "ФИО": 1}},
    ]
    demo(15, "отчисление (нет записи оценки = несдан)", '''
db.students.aggregate([
  ...
  # по каждому предмету направления:
  # несдан = нет оценки > 2 (нет документа / NULL / ≤2)
  # кандидат при failed >= 2
])
''', list(db.students.aggregate(pipe)))

    # ------------------------------------------------------------------
    sep("3. ПОСЕЩАЕМОСТЬ И РАСПИСАНИЕ")
    # ------------------------------------------------------------------

    sub = db.subjects.find_one({"name": SUBJECT})
    if not sub:
        raise SystemExit(f"Предмет не найден: {SUBJECT}")
    present = db.attendance.count_documents({"subject_id": sub["_id"], "is_present": True})
    absent = db.attendance.count_documents({"subject_id": sub["_id"], "is_present": False})
    demo(16, "посещённые занятия", f'''
sub = db.subjects.find_one({{"name": "{SUBJECT}"}})
db.attendance.count_documents({{
  "subject_id": sub["_id"],
  "is_present": True
}})
''', [{"Предмет": SUBJECT, "Посещено": present}])
    demo(17, "пропущенные занятия", f'''
sub = db.subjects.find_one({{"name": "{SUBJECT}"}})
db.attendance.count_documents({{
  "subject_id": sub["_id"],
  "is_present": False
}})
''', [{"Предмет": SUBJECT, "Пропущено": absent}])

    t = db.teachers.find_one({"last_name": TEACHER_LN})
    if not t:
        raise SystemExit(f"Преподаватель не найден: {TEACHER_LN}")
    pipe = [
        {"$match": {"teacher_id": t["_id"]}},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
        {"$unwind": "$sub"},
        {"$lookup": {"from": "time_slots", "localField": "time_slot_id", "foreignField": "_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$group": {
            "_id": {"date": "$date", "pair": "$ts.pair_number", "subj": "$sub.name"},
            "present": {"$sum": {"$cond": ["$is_present", 1, 0]}},
        }},
        {"$sort": {"_id.date": 1, "_id.pair": 1}},
        {"$project": {
            "_id": 0,
            "Предмет": "$_id.subj",
            "Дата": {"$dateToString": {"format": "%Y-%m-%d", "date": "$_id.date"}},
            "Пара": "$_id.pair",
            "Присутствовало": "$present",
        }},
    ]
    demo(18, f"занятия у {TEACHER_LN}", f'''
db.attendance.aggregate([
  {{"$match": {{"teacher_id": ObjectId("…")}}}},  # преподаватель {TEACHER_LN}
  {{"$lookup": {{"from": "subjects", "localField": "subject_id",
               "foreignField": "_id", "as": "sub"}}}},
  {{"$unwind": "$sub"}},
  {{"$lookup": {{"from": "time_slots", "localField": "time_slot_id",
               "foreignField": "_id", "as": "ts"}}}},
  {{"$unwind": "$ts"}},
  {{"$group": {{
     "_id": {{"date": "$date", "pair": "$ts.pair_number",
             "start": "$ts.start_time", "end": "$ts.end_time",
             "subj": "$sub.name"}},
     "present": {{"$sum": {{"$cond": ["$is_present", 1, 0]}}}}
  }}}},
  {{"$sort": {{"_id.date": 1, "_id.pair": 1}}}}
])
''', list(db.attendance.aggregate(pipe)))

    pipe = [
        {"$match": {"is_present": True}},
        {"$lookup": {"from": "students", "localField": "student_id", "foreignField": "_id", "as": "s"}},
        {"$unwind": "$s"},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
        {"$unwind": "$sub"},
        {"$lookup": {"from": "time_slots", "localField": "time_slot_id", "foreignField": "_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$addFields": {"slot_hours": slot_hours_expr("ts")}},
        {"$group": {
            "_id": {
                "fio": {"$concat": [
                    "$s.last_name", " ", "$s.first_name", " ", {"$ifNull": ["$s.middle_name", ""]},
                ]},
                "subj": "$sub.name",
            },
            "hours": {"$sum": "$slot_hours"},
        }},
        {"$project": {
            "_id": 0,
            "ФИО": "$_id.fio",
            "Предмет": "$_id.subj",
            "Часов": {"$round": ["$hours", 2]},
        }},
        {"$sort": {"ФИО": 1, "Предмет": 1}},
        {"$limit": 20},
    ]
    demo(19, "часы изучения (из длительности пар)", '''
db.attendance.aggregate([
  {"$match": {"is_present": True}},
  {"$lookup": {"from": "students", "localField": "student_id",
               "foreignField": "_id", "as": "s"}}, {"$unwind": "$s"},
  {"$lookup": {"from": "subjects", "localField": "subject_id",
               "foreignField": "_id", "as": "sub"}}, {"$unwind": "$sub"},
  {"$lookup": {"from": "time_slots", "localField": "time_slot_id",
               "foreignField": "_id", "as": "ts"}}, {"$unwind": "$ts"},
  {"$addFields": {
     "slot_hours": {"$divide": [
       {"$subtract": [
         {"$add": [{"$multiply": [{"$toInt": {"$substrBytes": ["$ts.end_time", 0, 2]}}, 60]},
                   {"$toInt": {"$substrBytes": ["$ts.end_time", 3, 2]}}]},
         {"$add": [{"$multiply": [{"$toInt": {"$substrBytes": ["$ts.start_time", 0, 2]}}, 60]},
                   {"$toInt": {"$substrBytes": ["$ts.start_time", 3, 2]}}]}
       ]}, 60.0]
     }
  }},
  {"$group": {
     "_id": {"fio": {"$concat": ["$s.last_name", " ", "$s.first_name"]},
             "subj": "$sub.name"},
     "hours": {"$sum": "$slot_hours"}
  }},
  {"$project": {"ФИО": "$_id.fio", "Предмет": "$_id.subj",
                "Часов изучено": {"$round": ["$hours", 2]}}}
])
''', list(db.attendance.aggregate(pipe)))

    pipe = [
        {"$addFields": {
            "Часов": {"$round": [{
                "$divide": [
                    {"$subtract": [
                        {"$add": [
                            {"$multiply": [{"$toInt": {"$substrBytes": ["$end_time", 0, 2]}}, 60]},
                            {"$toInt": {"$substrBytes": ["$end_time", 3, 2]}},
                        ]},
                        {"$add": [
                            {"$multiply": [{"$toInt": {"$substrBytes": ["$start_time", 0, 2]}}, 60]},
                            {"$toInt": {"$substrBytes": ["$start_time", 3, 2]}},
                        ]},
                    ]},
                    60.0,
                ]
            }, 2]},
        }},
        {"$project": {"_id": 0, "Пара": "$pair_number", "Начало": "$start_time", "Конец": "$end_time", "Часов": 1}},
        {"$sort": {"Пара": 1}},
    ]
    demo(20, "расписание пар (разная длительность)", '''
db.time_slots.aggregate([
  {"$addFields": {
     "Часов": {"$round": [{
       "$divide": [
         {"$subtract": [
           {"$add": [{"$multiply": [{"$toInt": {"$substrBytes": ["$end_time", 0, 2]}}, 60]},
                     {"$toInt": {"$substrBytes": ["$end_time", 3, 2]}}]},
           {"$add": [{"$multiply": [{"$toInt": {"$substrBytes": ["$start_time", 0, 2]}}, 60]},
                     {"$toInt": {"$substrBytes": ["$start_time", 3, 2]}}]}
         ]}, 60.0]
     }, 2]}
  }},
  {"$project": {"Пара": "$pair_number", "Начало": "$start_time",
                "Конец": "$end_time", "Часов": 1}},
  {"$sort": {"Пара": 1}}
])
# длительность пары считается на сервере
''', list(db.time_slots.aggregate(pipe)))

    pipe = [
        {"$lookup": {"from": "students", "localField": "student_id", "foreignField": "_id", "as": "s"}},
        {"$unwind": "$s"},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
        {"$unwind": "$sub"},
        {"$lookup": {"from": "teachers", "localField": "teacher_id", "foreignField": "_id", "as": "t"}},
        {"$unwind": "$t"},
        {"$lookup": {"from": "time_slots", "localField": "time_slot_id", "foreignField": "_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$sort": {"date": 1}},
        {"$limit": 25},
        {"$project": {
            "_id": 0,
            "Дата": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
            "Студент": {"$concat": ["$s.last_name", " ", "$s.first_name"]},
            "Предмет": "$sub.name",
            "Преподаватель": {"$concat": ["$t.last_name", " ", "$t.first_name"]},
            "Пара": "$ts.pair_number",
            "Статус": {"$cond": ["$is_present", "был", "не был"]},
        }},
    ]
    demo(21, "журнал посещений", '''
db.attendance.aggregate([
  {"$lookup": {"from": "students", "localField": "student_id",
               "foreignField": "_id", "as": "s"}}, {"$unwind": "$s"},
  {"$lookup": {"from": "subjects", "localField": "subject_id",
               "foreignField": "_id", "as": "sub"}}, {"$unwind": "$sub"},
  {"$lookup": {"from": "teachers", "localField": "teacher_id",
               "foreignField": "_id", "as": "t"}}, {"$unwind": "$t"},
  {"$lookup": {"from": "time_slots", "localField": "time_slot_id",
               "foreignField": "_id", "as": "ts"}}, {"$unwind": "$ts"},
  {"$sort": {"date": 1, "ts.pair_number": 1}},
  {"$limit": 40},
  {"$project": {
     "Дата": 1,
     "Студент": {"$concat": ["$s.last_name", " ", "$s.first_name"]},
     "Предмет": "$sub.name",
     "Преподаватель": {"$concat": ["$t.last_name", " ", "$t.first_name"]},
     "Пара": "$ts.pair_number",
     "Начало": "$ts.start_time", "Конец": "$ts.end_time",
     "Статус": {"$cond": ["$is_present", "был", "не был"]}
  }}
])
''', list(db.attendance.aggregate(pipe)))

    sep("ВСЕ ЗАПРОСЫ ИЗ ЗАДАНИЯ 2 УСПЕШНО ВЫПОЛНЕНЫ В ТЕРМИНАЛЕ")


if __name__ == "__main__":
    main()
