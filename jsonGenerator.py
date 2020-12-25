# ██╗  ██╗██████╗ ███╗   ███╗███████╗ █████╗ ██╗
# ██║  ██║██╔══██╗████╗ ████║██╔════╝██╔══██╗██║
# ███████║██║  ██║██╔████╔██║█████╗  ███████║██║
# ██╔══██║██║  ██║██║╚██╔╝██║██╔══╝  ██╔══██║██║
# ██║  ██║██████╔╝██║ ╚═╝ ██║███████╗██║  ██║███████╗
# ╚═╝  ╚═╝╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝
# Copyright 2019-2020, Hyungyo Seo
# jsonGenerator.py - 어제, 오늘 내일의 학사정보를 JSON 파일로 만들어주는 스크립트입니다.


import datetime
import json
import os
import re
import urllib.request
from itertools import groupby
from threading import Thread

import pytz as pytz


try:
    NEIS_OPENAPI_TOKEN = os.environ["NEIS_OPENAPI_TOKEN"]  # NEUS 오픈API 인증 토큰
    ATPT_OFCDC_SC_CODE = os.environ["ATPT_OFCDC_SC_CODE"]  # 시도교육청코드
    SD_SCHUL_CODE = os.environ["SD_SCHUL_CODE"]  # 표준학교코드
    NUM_OF_GRADES = int(os.environ["NUM_OF_GRADES"])  # 학년의 수
    NUM_OF_CLASSES = int(os.environ["NUM_OF_CLASSES"])  # 학년당 학급의 수, 학년별로 다를 경우 제일 큰 수 기준
except KeyError:
    raise KeyError("환경변수 설정이 올바르지 않습니다.")
except ValueError:
    raise ValueError("환경변수에 올바르지 않은 값이 들어 있습니다.")

print("Deployment Started")

TODAY = datetime.datetime.now(pytz.timezone('Asia/Seoul')).date()
# 오늘 전후로 나흘씩 조회
DAYS = [TODAY + datetime.timedelta(days=i) for i in [-3, -2, -1, 0, 1, 2, 3]]
DATE_FROM = DAYS[0].strftime("%Y%m%d")
DATE_TO = DAYS[-1].strftime("%Y%m%d")


meals_v2 = {}
meals = {}
def meal():
    menus_v2 = {}
    menus = {}
    calories = {}

    req = urllib.request.urlopen("https://open.neis.go.kr/hub/mealServiceDietInfo?KEY=%s&Type=json&ATPT_OFCDC_SC_CODE"
                                 "=%s&SD_SCHUL_CODE=%s&MMEAL_SC_CODE=2&MLSV_FROM_YMD=%s&MLSV_TO_YMD=%s"
                                 % (NEIS_OPENAPI_TOKEN, ATPT_OFCDC_SC_CODE, SD_SCHUL_CODE, DATE_FROM, DATE_TO))
    data = json.loads(req.read())

    try:
        for item in data["mealServiceDietInfo"][1]["row"]:
            date = datetime.datetime.strptime(item["MLSV_YMD"], "%Y%m%d").date()

            # 메뉴 파싱
            menu = item["DDISH_NM"].replace('<br/>', '.\n')  # 줄바꿈 처리
            menu = menu.split('\n')  # 한 줄씩 자르기
            menu_cleaned_v2 = []
            menu_cleaned = []
            for i in menu:
                allergy_info = [int(x[:-1]) for x in re.findall(r'[0-9]+\.', i)]
                i = i[:-1].replace(".", "").replace(''.join(str(x) for x in allergy_info), '')
                menu_cleaned_v2.append(i)
                menu_cleaned.append([i, allergy_info])
            menus_v2[date] = menu_cleaned_v2
            menus[date] = menu_cleaned

            # 칼로리 파싱
            calories[date] = float(item["CAL_INFO"].replace(" Kcal", ""))
    except KeyError:
        pass

    for i in DAYS:
        meals_v2[i] = [menus_v2.get(i), calories.get(i)]
        meals[i] = [menus.get(i), calories.get(i)]


timetable = {}
timetable_default = {}
def tt():
    timetable_raw_data = []
    for grade in range(1, NUM_OF_GRADES + 1):
        classes = {}
        for class_ in range(1, NUM_OF_CLASSES + 1):
            classes[str(class_)] = []
        timetable_default[str(grade)] = classes

    page_index = 1
    while True:
        req = urllib.request.urlopen("https://open.neis.go.kr/hub/hisTimetable?KEY=%s&Type=json&pIndex=%d&pSize=1000"
                                     "&ATPT_OFCDC_SC_CODE=%s&SD_SCHUL_CODE=%s&TI_FROM_YMD=%s&TI_TO_YMD=%s "
                                     % (NEIS_OPENAPI_TOKEN, page_index, ATPT_OFCDC_SC_CODE, SD_SCHUL_CODE,
                                        DATE_FROM, DATE_TO))
        data = json.loads(req.read())

        try:
            for i in data["hisTimetable"][1]["row"]:
                date = datetime.datetime.strptime(i["ALL_TI_YMD"], "%Y%m%d").date()

                timetable_raw_data.append([date, i["GRADE"], i["CLASS_NM"], i["ITRT_CNTNT"]])
            if len(data["hisTimetable"][1]["row"]) < 1000:
                break
        except KeyError:
            break
        page_index += 1

    for date, x in groupby(timetable_raw_data, lambda i: i[0]):
        timetable[date] = {}
        for grade, y in groupby(x, lambda i: i[1]):
            timetable[date][grade] = {}
            for class_, z in groupby(y, lambda i: i[2]):
                timetable[date][grade][class_] = [i[3] for i in z if i[3] != "토요휴업일"]


schdls = {}
def schdl():
    schedule_raw_data = []
    req = urllib.request.urlopen("https://open.neis.go.kr/hub/SchoolSchedule?KEY=%s&Type=json&ATPT_OFCDC_SC_CODE"
                                 "=%s&SD_SCHUL_CODE=%s&AA_FROM_YMD=%s&AA_TO_YMD=%s"
                                 % (NEIS_OPENAPI_TOKEN, ATPT_OFCDC_SC_CODE, SD_SCHUL_CODE, DATE_FROM, DATE_TO))
    data = json.loads(req.read())

    for i in data["SchoolSchedule"][1]["row"]:
        date = datetime.datetime.strptime(i["AA_YMD"], "%Y%m%d").date()

        related_grade = []
        if i["ONE_GRADE_EVENT_YN"] == "Y": related_grade.append(1)
        if i["TW_GRADE_EVENT_YN"] == "Y": related_grade.append(2)
        if i["THREE_GRADE_EVENT_YN"] == "Y": related_grade.append(3)
        if i["FR_GRADE_EVENT_YN"] == "Y": related_grade.append(4)
        if i["FIV_GRADE_EVENT_YN"] == "Y": related_grade.append(5)
        if i["SIX_GRADE_EVENT_YN"] == "Y": related_grade.append(6)

        schedule_raw_data.append([date, i["EVENT_NM"], related_grade])

    for date, x in groupby(schedule_raw_data, lambda i: i[0]):
        schdls[date] = []
        for schedule in x:
            if schedule[1] != "토요휴업일":
                schedule_text = "%s(%s)" % (schedule[1], ", ".join("%s학년" % i for i in schedule[2]))
                schedule_text = schedule_text.replace("()", "")
                schdls[date].append(schedule_text)

th_meal = Thread(target=meal)
th_tt = Thread(target=tt)
th_schdl = Thread(target=schdl)
# 쓰레드 실행
th_meal.start()
th_tt.start()
th_schdl.start()
# 전 쓰레드 종료 시까지 기다리기
th_meal.join()
th_tt.join()
th_schdl.join()

final_v2 = {}
final = {}
for i in DAYS:
    final_v2['%04d-%02d-%02d' % (i.year, i.month, i.day)] = {
        'Schedule': schdls.get(i),
        'Meal': meals_v2.get(i, [None, None]),
        "Timetable": timetable.get(i, timetable_default)
    }
for i in DAYS:
    final['%04d-%02d-%02d' % (i.year, i.month, i.day)] = {
        'Schedule': schdls.get(i),
        'Meal': meals.get(i, [None, None]),
        "Timetable": timetable.get(i, timetable_default)
    }
with open('dist/data.v2.json', 'w', encoding="utf-8") as make_file:
    json.dump(final_v2, make_file, ensure_ascii=False)
    print("File Created(v2)")
with open('dist/data.v3.json', 'w', encoding="utf-8") as make_file:
    json.dump(final, make_file, ensure_ascii=False)
    print("File Created")
