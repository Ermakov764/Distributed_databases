#!/usr/bin/env python3
"""Демонстрационный клиент — Задание 2 (MongoDB)."""

from __future__ import annotations

import json
import os
from datetime import datetime

from pymongo import MongoClient
from tabulate import tabulate

# Переопределение: export MONGO_URI=mongodb://host:27017
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://192.168.122.59:27017")
DB_NAME = os.environ.get("MONGO_DB", "university_db")


def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[DB_NAME]


def show_input(params=None):
    print("\n📥 ВВЕЛИ:")
    if not params:
        print("  (параметров нет — запрос без ввода)")
        return
    for k, v in params.items():
        print(f"  • {k} = {v}")


def show_query(title: str, obj):
    print(f"\n📝 ЗАПРОС К БД ({title}):")
    if isinstance(obj, str):
        print(obj)
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def show(rows, headers=None):
    print("\n📤 ОТВЕТ БД:")
    if not rows:
        print("  (пусто — 0 строк)")
        return
    if headers is None and isinstance(rows[0], dict):
        headers = list(rows[0].keys())
        rows = [[r.get(h) for h in headers] for r in rows]
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print(f"  строк: {len(rows)}")


def fio(s):
    return f"{s.get('last_name', '')} {s.get('first_name', '')} {s.get('middle_name') or ''}".strip()


def fio_io(s):
    fn = (s.get("first_name") or " ")[0]
    mn = (s.get("middle_name") or " ")[0]
    return f"{s.get('last_name', '')} {fn}.{mn}."


# ========== БЛОК 1 ==========

def query_1(db):
    print("\n📋 Запрос 1: Списки групп по направлению")
    direction = input("Введите направление (например, Информатика и вычислительная техника): ").strip()
    show_input({"направление": direction})
    show_query("find", {
        "directions.find_one": {"name": direction},
        "groups.find": {"direction_id": "<id направления>"},
        "students.find": {"group_id": {"$in": "<id групп>"}},
    })
    d = db.directions.find_one({"name": direction})
    if not d:
        print("\n📤 ОТВЕТ БД:\n  направление не найдено")
        return
    groups = {g["_id"]: g["name"] for g in db.groups.find({"direction_id": d["_id"]})}
    students = list(db.students.find({"group_id": {"$in": list(groups.keys())}}).sort(
        [("last_name", 1), ("first_name", 1)]
    ))
    rows = []
    for s in sorted(students, key=lambda x: (groups[x["group_id"]], x["last_name"], x["first_name"])):
        rows.append({
            "Группа": groups[s["group_id"]],
            "ФИО": fio(s),
            "Тип обучения": "Бюджет" if s.get("is_budget") else "Внебюджет",
        })
    show(rows)


def query_2(db):
    print("\n📋 Запрос 2: Студенты по первой букве фамилии")
    letter = input("Введите первую букву фамилии (например, Е): ").strip().upper()
    show_input({"первая буква фамилии": letter})
    pipeline = [
        {"$match": {"last_name": {"$regex": f"^{letter}", "$options": "i"}}},
        {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": "$g"},
        {"$lookup": {"from": "directions", "localField": "g.direction_id", "foreignField": "_id", "as": "d"}},
        {"$unwind": "$d"},
        {"$sort": {"last_name": 1}},
        {"$project": {
            "_id": 0,
            "ФИО": {"$concat": ["$last_name", " ", "$first_name", " ", {"$ifNull": ["$middle_name", ""]}]},
            "Группа": "$g.name",
            "Направление": "$d.name",
        }},
    ]
    show_query("students.aggregate", pipeline)
    show(list(db.students.aggregate(pipeline)))


def query_3(db):
    print("\n📋 Запрос 3: Список для поздравления по месяцам")
    show_input()
    months = {
        1: "январь", 2: "февраль", 3: "март", 4: "апрель", 5: "май", 6: "июнь",
        7: "июль", 8: "август", 9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
    }
    pipeline = [
        {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": "$g"},
        {"$lookup": {"from": "directions", "localField": "g.direction_id", "foreignField": "_id", "as": "d"}},
        {"$unwind": "$d"},
        {"$addFields": {"m": {"$month": "$birth_date"}, "day": {"$dayOfMonth": "$birth_date"}}},
        {"$sort": {"m": 1, "day": 1}},
    ]
    rows = []
    for s in db.students.aggregate(pipeline):
        rows.append({
            "ФИО": fio_io(s),
            "День": s["day"],
            "Месяц": months[s["m"]],
            "Группа": s["g"]["name"],
            "Направление": s["d"]["name"],
        })
    show(rows)


def query_4(db):
    print("\n Запрос 4: Студенты с указанием возраста")
    show_input()
    pipeline = [
        {"$addFields": {
            "Возраст": {
                "$dateDiff": {"startDate": "$birth_date", "endDate": "$$NOW", "unit": "year"}
            }
        }},
        {"$sort": {"last_name": 1}},
        {"$project": {
            "_id": 0,
            "ФИО": {"$concat": ["$last_name", " ", "$first_name", " ", {"$ifNull": ["$middle_name", ""]}]},
            "Дата рождения": {"$dateToString": {"format": "%Y-%m-%d", "date": "$birth_date"}},
            "Возраст": 1,
        }},
    ]
    show(list(db.students.aggregate(pipeline)))


def query_5(db):
    print("\n Запрос 5: ДР в текущем месяце")
    show_input()
    cur_month = datetime.now().month
    pipeline = [
        {"$match": {"$expr": {"$eq": [{"$month": "$birth_date"}, cur_month]}}},
        {"$lookup": {"from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g"}},
        {"$unwind": "$g"},
        {"$addFields": {"day": {"$dayOfMonth": "$birth_date"}}},
        {"$sort": {"day": 1}},
        {"$project": {
            "_id": 0,
            "ФИО": {"$concat": ["$last_name", " ", "$first_name", " ", {"$ifNull": ["$middle_name", ""]}]},
            "Дата рождения": {"$dateToString": {"format": "%Y-%m-%d", "date": "$birth_date"}},
            "Группа": "$g.name",
        }},
    ]
    show_query("students.aggregate", pipeline)
    show(list(db.students.aggregate(pipeline)))


def query_6(db):
    print("\n📋 Запрос 6: Количество студентов по направлениям")
    show_input()
    pipeline = [
        {"$lookup": {"from": "groups", "localField": "_id", "foreignField": "direction_id", "as": "g"}},
        {"$unwind": {"path": "$g", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "students", "localField": "g._id", "foreignField": "group_id", "as": "s"}},
        {"$group": {
            "_id": "$name",
            "Количество студентов": {"$sum": {"$size": "$s"}},
        }},
        {"$sort": {"Количество студентов": -1}},
        {"$project": {"_id": 0, "Направление": "$_id", "Количество студентов": 1}},
    ]
    show_query("directions.aggregate", pipeline)
    show(list(db.directions.aggregate(pipeline)))


def query_7(db):
    print("\n📋 Запрос 7: Бюджет / внебюджет по группам")
    show_input()
    pipeline = [
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
    show_query("groups.aggregate", pipeline)
    show(list(db.groups.aggregate(pipeline)))


# ========== БЛОК 2 ==========

def query_8(db):
    print("\n Запрос 8: Группы по предметам с преподавателем")
    show_input()
    pipeline = [
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
        {"$group": {
            "_id": {
                "subj": "$name",
                "teacher": {"$concat": ["$t.last_name", " ", "$t.first_name", " ", {"$ifNull": ["$t.middle_name", ""]}]},
                "group": "$g.name",
            }
        }},
        {"$project": {
            "_id": 0,
            "Предмет": "$_id.subj",
            "Преподаватель": "$_id.teacher",
            "Группа": "$_id.group",
        }},
        {"$sort": {"Предмет": 1, "Группа": 1}},
    ]
    show_query("subjects.aggregate", pipeline)
    show(list(db.subjects.aggregate(pipeline)))


def query_9(db):
    print("\n📋 Запрос 9: Дисциплина с макс. числом студентов")
    show_input()
    pipeline = [
        {"$lookup": {"from": "grades", "localField": "_id", "foreignField": "subject_id", "as": "gr"}},
        {"$project": {
            "Предмет": "$name",
            "Количество студентов": {"$size": {"$setUnion": ["$gr.student_id", []]}},
        }},
        {"$sort": {"Количество студентов": -1}},
        {"$limit": 1},
        {"$project": {"_id": 0, "Предмет": 1, "Количество студентов": 1}},
    ]
    show_query("subjects.aggregate", pipeline)
    show(list(db.subjects.aggregate(pipeline)))


def query_10(db):
    print("\n Запрос 10: Студенты у преподавателей")
    show_input()
    pipeline = [
        {"$lookup": {"from": "teacher_subjects", "localField": "_id", "foreignField": "teacher_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$lookup": {"from": "grades", "localField": "ts.subject_id", "foreignField": "subject_id", "as": "gr"}},
        {"$project": {
            "Преподаватель": {"$concat": ["$last_name", " ", "$first_name", " ", {"$ifNull": ["$middle_name", ""]}]},
            "Количество студентов": {"$size": {"$setUnion": ["$gr.student_id", []]}},
        }},
        {"$group": {
            "_id": "$Преподаватель",
            "Количество студентов": {"$sum": "$Количество студентов"},
        }},
        {"$project": {"_id": 0, "Преподаватель": "$_id", "Количество студентов": 1}},
        {"$sort": {"Количество студентов": -1}},
    ]
    # Более корректный подсчёт distinct по всем предметам преподавателя:
    pipeline = [
        {"$lookup": {"from": "teacher_subjects", "localField": "_id", "foreignField": "teacher_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$lookup": {"from": "grades", "localField": "ts.subject_id", "foreignField": "subject_id", "as": "gr"}},
        {"$unwind": {"path": "$gr", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": {
                "t": "$_id",
                "name": {"$concat": ["$last_name", " ", "$first_name", " ", {"$ifNull": ["$middle_name", ""]}]},
            },
            "students": {"$addToSet": "$gr.student_id"},
        }},
        {"$project": {
            "_id": 0,
            "Преподаватель": "$_id.name",
            "Количество студентов": {
                "$size": {"$filter": {"input": "$students", "as": "x", "cond": {"$ne": ["$$x", None]}}}
            },
        }},
        {"$sort": {"Количество студентов": -1}},
    ]
    show_query("teachers.aggregate", pipeline)
    show(list(db.teachers.aggregate(pipeline)))


def query_11(db):
    print("\n📋 Запрос 11: Доля сдавших по дисциплинам")
    show_input()
    rows = []
    for sub in db.subjects.find().sort("name", 1):
        groups = list(db.groups.find({"direction_id": sub["direction_id"]}, {"_id": 1}))
        gids = [g["_id"] for g in groups]
        studs = list(db.students.find({"group_id": {"$in": gids}}, {"_id": 1}))
        total = len(studs)
        passed = 0
        for s in studs:
            gr = db.grades.find_one({"student_id": s["_id"], "subject_id": sub["_id"]})
            if gr and gr.get("grade") is not None and gr["grade"] > 2:
                passed += 1
        pct = round(passed / total * 100, 2) if total else 0
        rows.append({
            "Предмет": sub["name"],
            "Всего студентов": total,
            "Сдали": passed,
            "Доля сдавших (%)": pct,
        })
    show(rows)


def query_12(db):
    print("\n📋 Запрос 12: Средняя оценка по предметам (сдавшие)")
    show_input()
    pipeline = [
        {"$match": {"grade": {"$gt": 2}}},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
        {"$unwind": "$sub"},
        {"$group": {"_id": "$sub.name", "avg": {"$avg": "$grade"}}},
        {"$project": {"_id": 0, "Предмет": "$_id", "Средняя оценка": {"$round": ["$avg", 2]}}},
        {"$sort": {"Средняя оценка": -1}},
    ]
    show_query("grades.aggregate", pipeline)
    show(list(db.grades.aggregate(pipeline)))


def query_13(db):
    print("\n📋 Запрос 13: Группа с макс. средней оценкой")
    show_input()
    pipeline = [
        {"$lookup": {"from": "directions", "localField": "direction_id", "foreignField": "_id", "as": "d"}},
        {"$unwind": "$d"},
        {"$lookup": {"from": "students", "localField": "_id", "foreignField": "group_id", "as": "s"}},
        {"$unwind": "$s"},
        {"$lookup": {"from": "grades", "localField": "s._id", "foreignField": "student_id", "as": "gr"}},
        {"$unwind": {"path": "$gr", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": {"g": "$name", "d": "$d.name"},
            "avg": {"$avg": "$gr.grade"},
        }},
        {"$sort": {"avg": -1}},
        {"$limit": 1},
        {"$project": {
            "_id": 0,
            "Группа": "$_id.g",
            "Направление": "$_id.d",
            "Средняя оценка": {"$round": ["$avg", 2]},
        }},
    ]
    show_query("groups.aggregate", pipeline)
    show(list(db.groups.aggregate(pipeline)))


def query_14(db):
    print("\n📋 Запрос 14: Студенты-отличники")
    print("   Отличник = по КАЖДОМУ предмету направления есть оценка ровно 5.")
    print("   Нет документа оценки / NULL / 0 / 2 / 3 / 4 → не отличник.")
    print("   (сравнение множеств subject_id, не цикл Python)")
    show_input()
    # needed_ids — все предметы направления.
    # five_ids — subject_id, по которым реально стоит grade == 5.
    # Отличник ⇔ needed_ids ⊆ five_ids (нет «дыры»: ни отсутствующей записи, ни не-пятёрки).
    pipeline = [
        {"$lookup": {
            "from": "groups", "localField": "group_id", "foreignField": "_id", "as": "g",
        }},
        {"$unwind": "$g"},
        {"$lookup": {
            "from": "subjects",
            "localField": "g.direction_id",
            "foreignField": "direction_id",
            "as": "needed",
        }},
        {"$lookup": {
            "from": "grades",
            "localField": "_id",
            "foreignField": "student_id",
            "as": "grades",
        }},
        {"$addFields": {
            "needed_ids": {"$map": {"input": "$needed", "as": "s", "in": "$$s._id"}},
            "needed_cnt": {"$size": "$needed"},
            "five_ids": {
                "$setUnion": [
                    {
                        "$map": {
                            "input": {
                                "$filter": {
                                    "input": "$grades",
                                    "as": "gr",
                                    "cond": {"$eq": ["$$gr.grade", 5]},
                                }
                            },
                            "as": "gr",
                            "in": "$$gr.subject_id",
                        }
                    },
                    [],
                ]
            },
        }},
        {"$addFields": {
            # предметы направления без пятёрки (нет записи / не 5 / NULL)
            "missing_or_not_five": {
                "$setDifference": ["$needed_ids", "$five_ids"]
            },
            "fives_cnt": {
                "$size": {
                    "$setIntersection": ["$needed_ids", "$five_ids"]
                }
            },
        }},
        {"$match": {
            "$expr": {
                "$and": [
                    {"$gt": ["$needed_cnt", 0]},
                    {"$eq": [{"$size": "$missing_or_not_five"}, 0]},
                ]
            }
        }},
        {"$project": {
            "_id": 0,
            "ФИО": {
                "$trim": {
                    "input": {
                        "$concat": [
                            "$last_name", " ", "$first_name", " ",
                            {"$ifNull": ["$middle_name", ""]},
                        ]
                    }
                }
            },
            "Группа": "$g.name",
            "Предметов направления": "$needed_cnt",
            "Сдано на 5": "$fives_cnt",
        }},
        {"$sort": {"ФИО": 1}},
    ]
    show_query("students.aggregate", pipeline)
    show(list(db.students.aggregate(pipeline)))


def query_15(db):
    print("\n📋 Запрос 15: Кандидаты на отчисление")
    print("   Несданный предмет направления = нет записи оценки / NULL / ≤2.")
    print("   Порог: ≥ 2 таких предметов; логика на сервере")
    show_input()
    # Раньше считали только существующие документы grade∈{2,null} —
    # если преподаватель вообще не ставил оценку (нет документа), предмет
    # не попадал в «несданные». Теперь: для каждого предмета направления.
    pipeline = [
        {"$lookup": {
            "from": "groups",
            "localField": "group_id",
            "foreignField": "_id",
            "as": "g",
        }},
        {"$unwind": {"path": "$g", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "subjects",
            "localField": "g.direction_id",
            "foreignField": "direction_id",
            "as": "needed",
        }},
        {"$lookup": {
            "from": "grades",
            "localField": "_id",
            "foreignField": "student_id",
            "as": "grades",
        }},
        {"$addFields": {
            "failed": {
                "$size": {
                    "$filter": {
                        "input": "$needed",
                        "as": "subj",
                        "cond": {
                            # нет успешной оценки (>2) по этому предмету
                            "$eq": [
                                {
                                    "$size": {
                                        "$filter": {
                                            "input": "$grades",
                                            "as": "gr",
                                            "cond": {
                                                "$and": [
                                                    {"$eq": ["$$gr.subject_id", "$$subj._id"]},
                                                    {"$gt": ["$$gr.grade", 2]},
                                                ]
                                            },
                                        }
                                    }
                                },
                                0,
                            ]
                        },
                    }
                }
            }
        }},
        {"$match": {"failed": {"$gte": 2}}},
        {"$project": {
            "_id": 0,
            "ФИО": {
                "$trim": {
                    "input": {
                        "$concat": [
                            "$last_name", " ", "$first_name", " ",
                            {"$ifNull": ["$middle_name", ""]},
                        ]
                    }
                }
            },
            "Группа": {"$ifNull": ["$g.name", "?"]},
            "Несданных предметов": "$failed",
        }},
        {"$sort": {"Несданных предметов": -1, "ФИО": 1}},
    ]
    show_query("students.aggregate", pipeline)
    show(list(db.students.aggregate(pipeline)))


# ========== БЛОК 3 ==========

def query_16(db):
    print("\n📋 Запрос 16: Посещенные занятия по предмету")
    subject = input("Введите предмет (например, Архитектура ЭВМ): ").strip()
    show_input({"предмет": subject})
    show_query("find + count_documents", {
        "subjects.find_one": {"name": subject},
        "attendance.count_documents": {"subject_id": "<id>", "is_present": True},
    })
    sub = db.subjects.find_one({"name": subject})
    if not sub:
        print("\n📤 ОТВЕТ БД:\n  предмет не найден")
        return
    present = db.attendance.count_documents({"subject_id": sub["_id"], "is_present": True})
    show([{"Предмет": subject, "Посещено": present}])


def query_17(db):
    print("\n📋 Запрос 17: Пропущенные занятия по предмету")
    subject = input("Введите предмет (например, Архитектура ЭВМ): ").strip()
    show_input({"предмет": subject})
    show_query("find + count_documents", {
        "subjects.find_one": {"name": subject},
        "attendance.count_documents": {"subject_id": "<id>", "is_present": False},
    })
    sub = db.subjects.find_one({"name": subject})
    if not sub:
        print("\n📤 ОТВЕТ БД:\n  предмет не найден")
        return
    absent = db.attendance.count_documents({"subject_id": sub["_id"], "is_present": False})
    show([{"Предмет": subject, "Пропущено": absent}])


def query_18(db):
    print("\n📋 Запрос 18: Студенты на занятиях у преподавателя")
    teacher = input("Введите фамилию преподавателя (например, Смирнов): ").strip()
    show_input({"фамилия преподавателя": teacher})
    show_query("find", {
        "teachers.find_one": {"last_name": teacher},
        "attendance.find": {"teacher_id": "<id преподавателя>"},
    })
    t = db.teachers.find_one({"last_name": teacher})
    if not t:
        print("\n📤 ОТВЕТ БД:\n  преподаватель не найден")
        return
    pipeline = [
        {"$match": {"teacher_id": t["_id"]}},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
        {"$unwind": "$sub"},
        {"$lookup": {"from": "time_slots", "localField": "time_slot_id", "foreignField": "_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$group": {
            "_id": {
                "date": "$date",
                "pair": "$ts.pair_number",
                "start": "$ts.start_time",
                "end": "$ts.end_time",
                "subj": "$sub.name",
            },
            "present": {"$sum": {"$cond": ["$is_present", 1, 0]}},
        }},
        {"$sort": {"_id.date": 1, "_id.pair": 1}},
        {"$project": {
            "_id": 0,
            "Преподаватель": f"{t['last_name']} {t['first_name']} {t.get('middle_name') or ''}".strip(),
            "Предмет": "$_id.subj",
            "Дата": {"$dateToString": {"format": "%Y-%m-%d", "date": "$_id.date"}},
            "Пара": "$_id.pair",
            "Начало": "$_id.start",
            "Конец": "$_id.end",
            "Присутствовало": "$present",
        }},
    ]
    show_query("attendance.aggregate", pipeline)
    show(list(db.attendance.aggregate(pipeline)))


def _slot_hours_expr(prefix="ts"):
    """Часы пары из start_time/end_time ('HH:MM'), не фиксированные 1.5."""
    def mins(field):
        return {
            "$add": [
                {"$multiply": [{"$toInt": {"$substrBytes": [f"${prefix}.{field}", 0, 2]}}, 60]},
                {"$toInt": {"$substrBytes": [f"${prefix}.{field}", 3, 2]}},
            ]
        }
    return {"$divide": [{"$subtract": [mins("end_time"), mins("start_time")]}, 60.0]}


def query_19(db):
    print("\n📋 Запрос 19: Время на изучение предмета")
    print("   (сумма реальных длительностей пар из time_slots.start_time/end_time)")
    print("   часы считаются в aggregate на сервере MongoDB, не в Python")
    show_input()
    pipeline = [
        {"$match": {"is_present": True}},
        {"$lookup": {"from": "students", "localField": "student_id", "foreignField": "_id", "as": "s"}},
        {"$unwind": "$s"},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
        {"$unwind": "$sub"},
        {"$lookup": {"from": "time_slots", "localField": "time_slot_id", "foreignField": "_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$addFields": {"slot_hours": _slot_hours_expr("ts")}},
        {"$group": {
            "_id": {
                "sid": "$s._id",
                "subj": "$sub.name",
                "fio": {
                    "$concat": [
                        "$s.last_name", " ", "$s.first_name", " ",
                        {"$ifNull": ["$s.middle_name", ""]},
                    ]
                },
            },
            "hours": {"$sum": "$slot_hours"},
        }},
        {"$project": {
            "_id": 0,
            "ФИО": "$_id.fio",
            "Предмет": "$_id.subj",
            "Часов изучено": {"$round": ["$hours", 2]},
        }},
        {"$sort": {"ФИО": 1, "Предмет": 1}},
    ]
    show_query("attendance.aggregate", pipeline)
    show(list(db.attendance.aggregate(pipeline)))


def query_20(db):
    print("\n📋 Запрос 20: Расписание пар (time_slots)")
    print("   длительность пары = end−start, считается в aggregate на сервере")
    show_input()
    pipeline = [
        {"$addFields": {
            "Часов": {
                "$round": [
                    {
                        "$divide": [
                            {
                                "$subtract": [
                                    {
                                        "$add": [
                                            {"$multiply": [
                                                {"$toInt": {"$substrBytes": ["$end_time", 0, 2]}}, 60
                                            ]},
                                            {"$toInt": {"$substrBytes": ["$end_time", 3, 2]}},
                                        ]
                                    },
                                    {
                                        "$add": [
                                            {"$multiply": [
                                                {"$toInt": {"$substrBytes": ["$start_time", 0, 2]}}, 60
                                            ]},
                                            {"$toInt": {"$substrBytes": ["$start_time", 3, 2]}},
                                        ]
                                    },
                                ]
                            },
                            60.0,
                        ]
                    },
                    2,
                ]
            }
        }},
        {"$project": {
            "_id": 0,
            "Пара": "$pair_number",
            "Начало": "$start_time",
            "Конец": "$end_time",
            "Часов": 1,
        }},
        {"$sort": {"Пара": 1}},
    ]
    show_query("time_slots.aggregate", pipeline)
    show(list(db.time_slots.aggregate(pipeline)))


def query_21(db):
    print("\n📋 Запрос 21: Журнал посещений (дата, предмет, преподаватель, пара)")
    show_input()
    pipeline = [
        {"$lookup": {"from": "students", "localField": "student_id", "foreignField": "_id", "as": "s"}},
        {"$unwind": "$s"},
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "sub"}},
        {"$unwind": "$sub"},
        {"$lookup": {"from": "teachers", "localField": "teacher_id", "foreignField": "_id", "as": "t"}},
        {"$unwind": "$t"},
        {"$lookup": {"from": "time_slots", "localField": "time_slot_id", "foreignField": "_id", "as": "ts"}},
        {"$unwind": "$ts"},
        {"$sort": {"date": 1, "ts.pair_number": 1, "s.last_name": 1}},
        {"$limit": 40},
        {"$project": {
            "_id": 0,
            "Дата": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
            "Студент": {"$concat": ["$s.last_name", " ", "$s.first_name"]},
            "Предмет": "$sub.name",
            "Преподаватель": {"$concat": ["$t.last_name", " ", "$t.first_name"]},
            "Пара": "$ts.pair_number",
            "Начало": "$ts.start_time",
            "Конец": "$ts.end_time",
            "Статус": {"$cond": ["$is_present", "был", "не был"]},
        }},
    ]
    show_query("attendance.aggregate", pipeline)
    show(list(db.attendance.aggregate(pipeline)))


MENU = {
    "1": ("Списки групп по направлению", query_1),
    "2": ("Студенты по первой букве фамилии", query_2),
    "3": ("Список студентов для поздравления по месяцам", query_3),
    "4": ("Студенты с указанием возраста", query_4),
    "5": ("Студенты с ДР в текущем месяце", query_5),
    "6": ("Количество студентов по направлениям", query_6),
    "7": ("Бюджетные/внебюджетные места по группам", query_7),
    "8": ("Группы по предметам с преподавателем", query_8),
    "9": ("Дисциплина с макс. количеством студентов", query_9),
    "10": ("Количество студентов у преподавателя", query_10),
    "11": ("Доля сдавших студентов по дисциплинам", query_11),
    "12": ("Средняя оценка по предметам", query_12),
    "13": ("Группа с максимальной средней оценкой", query_13),
    "14": ("Студенты-отличники (все предметы на 5)", query_14),
    "15": ("Кандидаты на отчисление", query_15),
    "16": ("Посещенные занятия по предмету", query_16),
    "17": ("Пропущенные занятия по предмету", query_17),
    "18": ("Студенты на занятиях у преподавателя", query_18),
    "19": ("Время на изучение предмета (из длительности пар)", query_19),
    "20": ("Расписание пар (начало/конец, разная длина)", query_20),
    "21": ("Журнал посещений (дата+предмет+преподаватель+пара)", query_21),
    "0": ("Выход", None),
}


def print_menu():
    print("\n" + "=" * 60)
    print(" ДЕМОНСТРАЦИОННЫЙ КЛИЕНТ — ЗАДАНИЕ 2 (MongoDB)")
    print("=" * 60)
    print("\n📌 БЛОК 1: СТУДЕНТЫ")
    for key in ["1", "2", "3", "4", "5", "6", "7"]:
        print(f"  [{key}] {MENU[key][0]}")
    print("\n📌 БЛОК 2: ПРЕДМЕТЫ И ОЦЕНКИ")
    for key in ["8", "9", "10", "11", "12", "13", "14", "15"]:
        print(f"  [{key}] {MENU[key][0]}")
    print("\n📌 БЛОК 3: ПОСЕЩАЕМОСТЬ")
    for key in ["16", "17", "18", "19", "20", "21"]:
        print(f"  [{key}] {MENU[key][0]}")
    print("\n  [0] Выход")
    print("=" * 60)


def main():
    try:
        db = get_db()
    except Exception as e:
        print(f"❌ Ошибка подключения к MongoDB: {e}")
        return
    print("\n✅ Подключение к MongoDB установлено!")
    print("   Каждый пункт: ВВЕЛИ → ЗАПРОС → ОТВЕТ БД")
    while True:
        print_menu()
        choice = input("\nВыберите номер запроса: ").strip()
        if choice == "0":
            print("\n👋 До свидания!")
            break
        if choice in MENU and MENU[choice][1]:
            print("\n" + "─" * 60)
            MENU[choice][1](db)
            print("─" * 60)
            input("\nНажмите Enter для продолжения...")
        else:
            print("\nНеверный выбор.")


if __name__ == "__main__":
    main()
