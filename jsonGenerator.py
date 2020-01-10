# ██╗  ██╗██████╗ ███╗   ███╗███████╗ █████╗ ██╗
# ██║  ██║██╔══██╗████╗ ████║██╔════╝██╔══██╗██║
# ███████║██║  ██║██╔████╔██║█████╗  ███████║██║
# ██╔══██║██║  ██║██║╚██╔╝██║██╔══╝  ██╔══██║██║
# ██║  ██║██████╔╝██║ ╚═╝ ██║███████╗██║  ██║███████╗
# ╚═╝  ╚═╝╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝
# Copyright 2019, Hyungyo Seo
# jsonGenerator.py - 어제, 오늘 내일의 학사정보를 JSON 파일로 만들어주는 스크립트입니다.


import ast
import base64
import datetime
import html
import json
import re
from threading import Thread
import urllib.parse as urlparse
import urllib.request
import urllib.request
import pytz
from bs4 import BeautifulSoup

# 학교가 속한 지역과 학교의 이름을 정확히 입력
# 컴시간알리미 검색 결과가 1개로 특정되도록 해주세요.
# 검색 결과가 2건 이상일 경우, 첫 번째 학교를 선택합니다.
school_region = "경기"
school_name = "흥덕중학교"
# 학교코드와 학교종류를 정확히 입력
school_code = "J100005775"
school_kind = 3  # 1 유치원, 2 초등학교, 3 중학교, 4 고등학교
# 학급수를 정확히 입력
num_of_classes = 12

today = datetime.datetime.now(pytz.timezone('Asia/Seoul')).date()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)

if today.weekday() == 6:  # 만약 오늘이 일요일이라면
    sunday = today
else:
    sunday = today - datetime.timedelta(days=today.weekday() + 1)
saturday = sunday + datetime.timedelta(days=6)

meals = {}
def meal():
    dates = []
    dates_text = []
    menus = []
    calories = []
    neis_baseurl = ("http://stu.goe.go.kr/sts_sci_md01_001.do?"
                    "schulCode=%s"
                    "&schulCrseScCode=%s"
                    "&schulKndScCode=%02d"
                    "&schMmealScCode=2"
                    "&schYmd=" % (school_code, school_kind, school_kind))

    neis_urls = ["%s%04d.%02d.%02d" % (neis_baseurl, sunday.year, sunday.month, sunday.day)]
    if yesterday < sunday:  # 만약 어제가 이번 주 일요일보다 과거라면
        neis_urls.insert(0, "%s%04d.%02d.%02d" % (neis_baseurl, yesterday.year, yesterday.month, yesterday.day))
    if saturday < tomorrow:  # 만약 내일이 이번 주 토요일보다 미래라면
        neis_urls.append("%s%04d.%02d.%02d" % (neis_baseurl, tomorrow.year, tomorrow.month, tomorrow.day))
    for url in neis_urls:
        req = urllib.request.urlopen(url)

        data = BeautifulSoup(req, 'html.parser')
        data = data.find_all("tr")

        # 날짜 파싱
        dates_text_raw = data[0].find_all("th")
        for date_text_raw in dates_text_raw:
            date_text = date_text_raw.get_text().strip().replace(".", "-")
            if not date_text:
                continue
            date = datetime.datetime.strptime(date_text[:-3], "%Y-%m-%d").date()
            dates_text.append(date_text)
            dates.append(date)

        # 알레르기정보 선언
        allergy_filter = ["1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.",
                          "9.", "10.", "11.", "12.", "13.", "14.", "15.", "16.",
                          "17.", "18."]
        allergy_string = ["[난류]", "[우유]", "[메밀]", "[땅콩]", "[대두]", "[밀]", "[고등어]", "[게]",
                          "[새우]", "[돼지고기]", "[복숭아]", "[토마토]", "[아황산류]", "[호두]", "[닭고기]", "[쇠고기]",
                          "[오징어]", "[조개류]"]
        allergy_filter.reverse()
        allergy_string.reverse()  # 역순으로 정렬 - 오류방지

        # 메뉴 파싱
        menus_raw = data[2].find_all("td")
        for menu_raw in menus_raw:
            menu = str(menu_raw).replace('<br/>', '.\n')  # 줄바꿈 처리
            menu = html.unescape(re.sub('<.+?>', '', menu).strip())  # 태그 및 HTML 엔티티 처리
            for i in range(18):
                menu = menu.replace(allergy_filter[i], allergy_string[i]).replace('.\n', ',\n')
            menu = menu.split('\n')  # 한 줄씩 자르기
            if not menu:
                menu = None
            menus.append(menu)

        # 칼로리 파싱
        calories_raw = data[45].find_all("td")
        for calorie_raw in calories_raw:
            calorie = calorie_raw.get_text().strip()
            if not calorie:
                calorie = None
            calories.append(calorie)

        for loc in range(7):
            meals[dates[loc]] = [dates_text[loc], menus[loc], calories[loc]]

    wdays = ["월", "화", "수", "목", "금", "토", "일"]
    if not today in meals:
        meals[today] = ["%s(%s)" % (today, wdays[today.weekday()]), [''], None]
    if not yesterday in meals:
        meals[yesterday] = ["%s(%s)" % (yesterday, wdays[yesterday.weekday()]), [''], None]
    if not tomorrow in meals:
        meals[tomorrow] = ["%s(%s)" % (tomorrow, wdays[tomorrow.weekday()]), [''], None]

timetables = {}
def tt():
    # 학교명으로 검색해 학교코드 알아내기
    search_req = urllib.request.Request(
        'http://comci.kr:4081/98372?92744l%s' % urlparse.quote(school_name.encode("EUC-KR")),
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/78.0.3904.70 Safari/537.36'
        }
    )

    search_url = urllib.request.urlopen(search_req)

    # 학교 검색결과 가져오기
    school_list = ast.literal_eval(search_url.read().decode('utf-8').replace('\x00', ''))["학교검색"]

    # 검색결과를 지역으로 구분하고 학교코드 가져오기
    part_code = ""
    for i in school_list:
        if i[1] == school_region:
            part_code = i[3]
            break

    # 이번 주 시간표와 다음 주 시간표 가져오기
    fetch_req_1 = urllib.request.Request(
        'http://comci.kr:4081/98372?' + base64.b64encode(bytes("34739_%s_0_1" % part_code, 'utf-8')).decode(
            "utf-8"),
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/78.0.3904.70 Safari/537.36'
        }
    )

    fetch_req_2 = urllib.request.Request(
        'http://comci.kr:4081/98372?' + base64.b64encode(bytes("34739_%s_0_2" % part_code, 'utf-8')).decode(
            "utf-8"),
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/78.0.3904.70 Safari/537.36'
        }
    )

    # 시간표 디코딩
    url_1 = urllib.request.urlopen(fetch_req_1).read().decode('utf-8').replace('\x00', '')
    url_2 = urllib.request.urlopen(fetch_req_2).read().decode('utf-8').replace('\x00', '')

    # JSON 파싱
    raw_0 = json.loads(url_1)
    raw_1 = json.loads(url_2)

    date_0 = datetime.datetime.strptime(raw_0["시작일"], "%Y-%m-%d").date()
    date_1 = datetime.datetime.strptime(raw_1["시작일"], "%Y-%m-%d").date()
    if date_0 < date_1:
        raw_data = [raw_0, raw_1]
        start_date = date_0
        end_date = date_1 + datetime.timedelta(days=7)
    else:
        raw_data = [raw_1, raw_0]
        start_date = date_1
        end_date = date_0 + datetime.timedelta(days=7)

    dates = [[], []]
    for i in range(((start_date + datetime.timedelta(days=7)) - start_date).days):
        date = start_date + datetime.timedelta(days=i)
        dates[0].append(date)
    for i in range((end_date - (end_date - datetime.timedelta(days=7))).days + 1):
        date = start_date + datetime.timedelta(days=7 + i)
        dates[1].append(date)

    for i in [0, 1]:
        teacher_list = raw_data[i]["자료46"]  # 교사명단
        subject_list = raw_data[i]["자료92"]  # 2글자로 축약한 과목명단 - 전체 명칭은 긴자료92에 담겨있음
        for grade in range(1, 4):
            for class_ in range(1, num_of_classes + 1):
                tt = raw_data[i]["자료14"][grade][class_]  # 자료14에 각 반의 일일시간표 정보가 담겨있음
                og_tt = raw_data[i]["자료81"][grade][class_]  # 자료81에 각 반의 원본시간표 정보가 담겨있음
                for wday in range(6):
                    if not dates[i][wday] in timetables:
                        timetables[dates[i][wday]] = {}
                    if not grade in timetables[dates[i][wday]]:
                        timetables[dates[i][wday]][grade] = {}
                    if not class_ in timetables[dates[i][wday]][grade]:
                        timetables[dates[i][wday]][grade][class_] = []
                    if wday == 6:
                        comci_wday = 0
                    else:
                        comci_wday = wday + 1
                    for day in range(len(tt[comci_wday])):
                        if tt[comci_wday][day] != 0:
                            subject = subject_list[int(str(tt[comci_wday][day])[-2:])]  # 뒤의 2자리는 과목명을 나타냄
                            teacher = teacher_list[int(str(tt[comci_wday][day])[:-2])]  # 나머지 숫자는 교사명을 나타냄
                            if not tt[comci_wday][day] == og_tt[comci_wday][day]:
                                timetables[dates[i][wday]][grade][class_].append(
                                    "⭐%s(%s)" % (subject, teacher))  # 시간표 변경사항 표시
                            else:
                                timetables[dates[i][wday]][grade][class_].append("%s(%s)" % (subject, teacher))

    if not today in timetables:
        timetables[today] = None
    if not yesterday in timetables:
        timetables[yesterday] = None
    if not tomorrow in timetables:
        timetables[tomorrow] = None


schdls = {}


def schdl():
    # 학년도 기준, 다음해 2월까지 전년도로 조회
    if today.month < 3:
        sy_today = today - datetime.timedelta(days=365)
    else:
        sy_today = today
    if yesterday.month < 3:
        sy_yesterday = yesterday - datetime.timedelta(days=365)
    else:
        sy_yesterday = yesterday
    if tomorrow.month < 3:
        sy_tomorrow = tomorrow - datetime.timedelta(days=365)
    else:
        sy_tomorrow = tomorrow

    neis_baseurl = ("http://stu.goe.go.kr/sts_sci_sf01_001.do?"
                    "schulCode=%s"
                    "&schulCrseScCode=%d"
                    "&schulKndScCode=%02d"
                    % (school_code, school_kind, school_kind))

    neis_urls = [("&ay=%04d&mm=%02d" % (sy_today.year, sy_today.month), today)]
    if sy_yesterday < sy_today.replace(day=1):  # 만약 어제가 지난 달이라면
        neis_urls.insert(0, ("&ay=%04d&mm=%02d" % (sy_yesterday.year, sy_yesterday.month), yesterday))
    sy_today_nextmonth = sy_today
    if sy_today.month == 12:
        sy_today_nextmonth.replace(month=1, day=1)
    else:
        sy_today_nextmonth.replace(month=sy_today_nextmonth.month + 1, day=1)
    if sy_today_nextmonth <= sy_tomorrow:  # 만약 내일이 다음 달이라면
        neis_urls.append(("&ay=%04d&mm=%02d" % (sy_tomorrow.year, sy_tomorrow.month), tomorrow))

    for url in neis_urls:
        req = urllib.request.urlopen(neis_baseurl + url[0])

        data = BeautifulSoup(req, 'html.parser')
        data = data.find_all('div', class_='textL')

        def pstpr(cal):
            return cal.replace("토요휴업일", "").strip().replace('\n\n\n', '\n')

        for i in range(len(data)):
            string = data[i].get_text().strip()
            if string[2:].replace('\n', '') and pstpr(string[2:]):
                schdls[url[1].replace(day=int(string[:2]))] = pstpr(string[2:]).split('\n')  # 한 줄씩 자르기

    if not today in schdls:
        schdls[today] = None
    if not yesterday in schdls:
        schdls[yesterday] = None
    if not tomorrow in schdls:
        schdls[tomorrow] = None

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

final = {
    "Today": {
        "Date": meals[today][0],
        "Schedule": schdls[today],
        "Meal": {
            "Menu": meals[today][1],
            "Calories": meals[today][2]
        },
        "Timetable": timetables[today]
    },
    "Yesterday": {
        "Date": meals[yesterday][0],
        "Schedule": schdls[yesterday],
        "Meal": {
            "Menu": meals[yesterday][1],
            "Calories": meals[yesterday][2]
        },
        "Timetable": timetables[yesterday]
    },
    "Tomorrow": {
        "Date": meals[tomorrow][0],
        "Schedule": schdls[tomorrow],
        "Meal": {
            "Menu": meals[tomorrow][1],
            "Calories": meals[tomorrow][2]
        },
        "Timetable": timetables[tomorrow]
    }
}

with open('dist/data.json', 'w', encoding="utf-8") as make_file:
    json.dump(final, make_file, ensure_ascii=False, indent="\t")
    print("File Created")
