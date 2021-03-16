# ██╗  ██╗██████╗ ███╗   ███╗███████╗ █████╗ ██╗
# ██║  ██║██╔══██╗████╗ ████║██╔════╝██╔══██╗██║
# ███████║██║  ██║██╔████╔██║█████╗  ███████║██║
# ██╔══██║██║  ██║██║╚██╔╝██║██╔══╝  ██╔══██║██║
# ██║  ██║██████╔╝██║ ╚═╝ ██║███████╗██║  ██║███████╗
# ╚═╝  ╚═╝╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝
# Copyright 2019-2020, Hyungyo Seo
# jsonGenerator.py - 어제, 오늘 내일의 학사정보를 JSON 파일로 만들어주는 스크립트입니다.

import brotli
import collections
import datetime
import json
import os
import re
import urllib.request
from itertools import groupby
from threading import Thread
import pytz as pytz


SUPPORTED_API_VERSIONS = ["v2", "v3", "v4"]

try:
    NEIS_OPENAPI_TOKEN = os.environ["NEIS_OPENAPI_TOKEN"]  # NEUS 오픈API 인증 토큰
    ATPT_OFCDC_SC_CODE = os.environ["ATPT_OFCDC_SC_CODE"]  # 시도교육청코드
    SD_SCHUL_CODE = os.environ["SD_SCHUL_CODE"]  # 표준학교코드
    NUM_OF_GRADES = int(os.environ["NUM_OF_GRADES"])  # 학년의 수
    NUM_OF_CLASSES = int(
        os.environ["NUM_OF_CLASSES"]
    )  # 학년당 학급의 수, 학년별로 다를 경우 제일 큰 수 기준
except KeyError:
    raise KeyError("환경변수 설정이 올바르지 않습니다.")
except ValueError:
    raise ValueError("환경변수에 올바르지 않은 값이 들어 있습니다.")

print("Deployment Started")

TODAY = datetime.datetime.now(pytz.timezone("Asia/Seoul")).date()
# 오늘 전후로 나흘씩 조회
DAYS = [TODAY + datetime.timedelta(days=i) for i in [-3, -2, -1, 0, 1, 2, 3]]
DATE_FROM = DAYS[0].strftime("%Y%m%d")
DATE_TO = DAYS[-1].strftime("%Y%m%d")


class Meal:
    def __init__(self):
        self.v2 = {}
        self._default = {}

    def __getattr__(self, _):
        return self._default

    def parse(self):
        menus = collections.defaultdict(dict)
        calories = {}

        req = urllib.request.urlopen(
            f"https://open.neis.go.kr/hub/mealServiceDietInfo?KEY={NEIS_OPENAPI_TOKEN}"
            f"&Type=json&ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}&SD_SCHUL_CODE={SD_SCHUL_CODE}"
            f"&MMEAL_SC_CODE=2&MLSV_FROM_YMD={DATE_FROM}&MLSV_TO_YMD={DATE_TO}"
        )
        data = json.loads(req.read())

        try:
            for item in data["mealServiceDietInfo"][1]["row"]:
                date = datetime.datetime.strptime(item["MLSV_YMD"], "%Y%m%d").date()

                # 메뉴 파싱
                menu = item["DDISH_NM"].replace("<br/>", ".\n")  # 줄바꿈 처리
                menu = menu.split("\n")  # 한 줄씩 자르기
                menu_cleaned_v2 = []
                menu_cleaned = []
                for i in menu:
                    allergy_info = [int(x[:-1]) for x in re.findall(r"[0-9]+\.", i)]
                    i = i.replace(".", "").replace(
                        "".join(str(x) for x in allergy_info), ""
                    )
                    menu_cleaned_v2.append(i)
                    menu_cleaned.append([i, allergy_info])
                menus["v2"][date] = menu_cleaned_v2
                menus["default"][date] = menu_cleaned

                # 칼로리 파싱
                calories[date] = float(item["CAL_INFO"].replace(" Kcal", ""))
        except KeyError:
            pass

        for i in DAYS:
            self.v2[i] = [menus.get("v2", menus["default"]).get(i), calories.get(i)]
            self._default[i] = [
                menus.get("default", menus["default"]).get(i),
                calories.get(i),
            ]


class Schedule:
    def __init__(self):
        self.v4 = collections.defaultdict(list)
        self._default = collections.defaultdict(list)

    def __getattr__(self, _):
        return self._default

    def parse(self):
        schedule_raw_data = []
        req = urllib.request.urlopen(
            f"https://open.neis.go.kr/hub/SchoolSchedule?KEY={NEIS_OPENAPI_TOKEN}&Type=json"
            f"&ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}&SD_SCHUL_CODE={SD_SCHUL_CODE}"
            f"&AA_FROM_YMD={DATE_FROM}&AA_TO_YMD={DATE_TO}"
        )
        data = json.loads(req.read())

        for i in data["SchoolSchedule"][1]["row"]:
            date = datetime.datetime.strptime(i["AA_YMD"], "%Y%m%d").date()

            related_grade = []
            if i["ONE_GRADE_EVENT_YN"] == "Y":
                related_grade.append(1)
            if i["TW_GRADE_EVENT_YN"] == "Y":
                related_grade.append(2)
            if i["THREE_GRADE_EVENT_YN"] == "Y":
                related_grade.append(3)
            if i["FR_GRADE_EVENT_YN"] == "Y":
                related_grade.append(4)
            if i["FIV_GRADE_EVENT_YN"] == "Y":
                related_grade.append(5)
            if i["SIX_GRADE_EVENT_YN"] == "Y":
                related_grade.append(6)

            schedule_raw_data.append([date, i["EVENT_NM"].strip(), related_grade])

        for date, x in groupby(schedule_raw_data, lambda i: i[0]):
            for schedule in x:
                if schedule[1] != "토요휴업일":
                    schedule_text = (
                        f'{schedule[1]}({", ".join(f"{i}학년" for i in schedule[2])})'
                    )
                    schedule_text = schedule_text.replace("()", "")
                    self.v4[date].append([schedule[1], schedule[2]])
                    self._default[date].append(schedule_text)
            if not self._default[date]:
                self.v4[date] = None
                self._default[date] = None


class Timetable:
    def __init__(self):
        self.default = {}
        self._default = {}

    def __getattr__(self, _):
        return self._default

    def parse(self):
        timetable_raw_data = []
        for grade in range(1, NUM_OF_GRADES + 1):
            classes = {}
            for class_ in range(1, NUM_OF_CLASSES + 1):
                classes[str(class_)] = []
            self.default[str(grade)] = classes

        page_index = 1
        while True:
            req = urllib.request.urlopen(
                f"https://open.neis.go.kr/hub/hisTimetable?KEY={NEIS_OPENAPI_TOKEN}&Type=json"
                f"&pIndex={page_index}&pSize=1000&ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}"
                f"&SD_SCHUL_CODE={SD_SCHUL_CODE}&TI_FROM_YMD={DATE_FROM}&TI_TO_YMD={DATE_TO}"
            )
            data = json.loads(req.read())

            try:
                for i in data["hisTimetable"][1]["row"]:
                    date = datetime.datetime.strptime(i["ALL_TI_YMD"], "%Y%m%d").date()

                    timetable_raw_data.append(
                        [date, i["GRADE"], i["CLASS_NM"], i["ITRT_CNTNT"]]
                    )
                if len(data["hisTimetable"][1]["row"]) < 1000:
                    break
            except KeyError:
                break
            page_index += 1

        for date, x in groupby(timetable_raw_data, lambda i: i[0]):
            self._default[date] = {}
            for grade, y in groupby(x, lambda i: i[1]):
                self._default[date][grade] = {}
                for class_, z in groupby(y, lambda i: i[2]):
                    self._default[date][grade][class_] = [
                        i[3] for i in z if i[3] != "토요휴업일"
                    ]


meal = Meal()
schedule = Schedule()
timetable = Timetable()

thread_meal = Thread(target=meal.parse)
thread_schedule = Thread(target=schedule.parse)
thread_timetable = Thread(target=timetable.parse)

thread_meal.start()
thread_schedule.start()
thread_timetable.start()

thread_meal.join()
thread_schedule.join()
thread_timetable.join()

api_data = collections.defaultdict(dict)
for version in SUPPORTED_API_VERSIONS:
    for day in DAYS:
        api_data[version][f"{day:%Y-%m-%d}"] = {
            "Meal": getattr(meal, version).get(day, [None, None]),
            "Schedule": getattr(schedule, version).get(day),
            "Timetable": getattr(timetable, version).get(day, timetable.default),
        }
for version in api_data:
    with open(f"dist/data.{version}.json", "w", encoding="utf-8") as make_file:
        json.dump(api_data[version], make_file, ensure_ascii=False)
        print(f"File Created({version})")
    with open(f"dist/data.{version}.json.br", "wb") as make_file:
        make_file.write(brotli.compress(json.dumps(api_data[version], ensure_ascii=False).encode("utf-8")))
        print(f"File Created({version}, w/ Brotli)")
