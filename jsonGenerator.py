# ██╗  ██╗██████╗ ███╗   ███╗███████╗ █████╗ ██╗
# ██║  ██║██╔══██╗████╗ ████║██╔════╝██╔══██╗██║
# ███████║██║  ██║██╔████╔██║█████╗  ███████║██║
# ██╔══██║██║  ██║██║╚██╔╝██║██╔══╝  ██╔══██║██║
# ██║  ██║██████╔╝██║ ╚═╝ ██║███████╗██║  ██║███████╗
# ╚═╝  ╚═╝╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝
# Copyright 2019-2020, Hyungyo Seo
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
school_name = "흥덕고등학교"
# 학교코드와 학교종류를 정확히 입력
school_code = "J100005677"
school_kind = 4  # 1 유치원, 2 초등학교, 3 중학교, 4 고등학교
# 학급수를 정확히 입력
num_of_classes = 9
# 컴시간알리미 웹사이트 URL
url = "http://xn--s39aj90b0nb2xw6xh.kr/"
# 기타 옵션 입력
headers = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
}

print("Deployment Started with Configs - [%s(%s, %s, %d), Classes: %d]"
      % (school_name, school_region, school_code, school_kind, num_of_classes))


today = datetime.datetime.now(pytz.timezone('Asia/Seoul')).date()
# 오늘 전후로 나흘씩 조회
days = [today + datetime.timedelta(days=i) for i in [-3, -2, -1, 0, 1, 2, 3]]
# NEIS 요청 수를 최적화하기 위해 조회날짜가 걸쳐 있는 주의 일요일 날짜를 구함
sundays = sorted(list({i - datetime.timedelta(days=i.weekday() + 1) if not i.weekday() == 6 else i for i in days}))
# NEIS 요청 수를 최적화하기 위해 조회날짜가 걸쳐 있는 달을 구함, 학년도 기준이므로 이듬해 2월까지 전년도로 취급
sy_months = sorted(list({datetime.date(i.year, i.month, 1) if i.month >= 3 else datetime.date(i.year - 1, i.month, 1) for i in days}))
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)


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

    neis_urls = ["%s%04d.%02d.%02d" % (neis_baseurl, i.year, i.month, i.day) for i in sundays]
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
            if not menu or not menu[0]:
                menu = None
            menus.append(menu)
        if not menus:
            menus = [None, None, None, None, None, None, None]

        # 칼로리 파싱
        calories_raw = data[51].find_all("td")
        for calorie_raw in calories_raw:
            calorie = calorie_raw.get_text().strip()
            try:
                calorie = float(calorie)
            except ValueError:
                calorie = None
            calories.append(calorie)
        if not calories:
            calories = [None, None, None, None, None, None, None]

    for i in days:
        loc = dates.index(i)
        try:
            meals[i] = [menus[loc], calories[loc]]
        except Exception:
            meals[i] = [None, None]


timetables = {}
timetables_default = {}
def tt():
    for grade in [1, 2, 3]:
        classes = {}
        for class_ in range(1, num_of_classes + 1):
            classes[str(class_)] = []
        timetables_default[str(grade)] = classes
    try:
        # BaseURL 알아내기
        baseurl_req = urllib.request.Request(url, data=None, headers=headers)
        baseurl_respns = urllib.request.urlopen(baseurl_req).read().decode('EUC-KR')
        baseurl_pattern = re.compile("src='.*?/st'")
        baseurl_matches = baseurl_pattern.findall(baseurl_respns)
        if baseurl_matches:
            base_url = baseurl_matches[0].split("'")[1][:-2]
        else:
            raise Exception

        # school_ra, sc_data, 자료위치 알아내기
        init_req = urllib.request.Request(base_url + 'st', data=None, headers=headers)
        init_respns = urllib.request.urlopen(init_req).read().decode('EUC-KR')
        # school_ra
        school_ra_pattern = re.compile("url:'.?(.*?)'")
        school_ra_matches = school_ra_pattern.findall(init_respns)
        if school_ra_matches:
            school_ra = school_ra_matches[0][1:]
            school_ra_code = school_ra.split('?')[0]
        else:
            raise Exception
        # sc_data
        sc_data_pattern = re.compile("sc_data\('[0-9].*?\);")
        sc_data_matches = sc_data_pattern.findall(init_respns)
        if sc_data_matches:
            sc_data = sc_data_matches[0].split("'")[1]
        else:
            raise Exception
        # 일일시간표
        daily_timetable_pattern = re.compile("일일자료=자료.*?\[")
        daily_timetable_matches = daily_timetable_pattern.findall(init_respns)
        if daily_timetable_matches:
            daily_timetable = daily_timetable_matches[0].split('자료.')[1][:-1]
        else:
            raise Exception
        # 원본시간표
        original_timetable_pattern = re.compile("원자료=자료.*?\[")
        original_timetable_matches = original_timetable_pattern.findall(init_respns)
        if original_timetable_matches:
            original_timetable = original_timetable_matches[0].split('자료.')[1][:-1]
        else:
            raise Exception
        # 교사명
        teachers_list_pattern = re.compile("성명=자료.*?\[th")
        teachers_list_matches = teachers_list_pattern.findall(init_respns)
        if teachers_list_matches:
            teachers_list = teachers_list_matches[0].split('자료.')[1][:-3]
        else:
            raise Exception
        # 과목명
        subjects_list_pattern = re.compile('"\'>"\+자료.*?\[sb')
        subjects_list_matches = subjects_list_pattern.findall(init_respns)
        if subjects_list_matches:
            subjects_list = subjects_list_matches[0].split('자료.')[1][:-3]
        else:
            raise Exception

        # 학교명으로 검색해 학교코드 알아내기
        search_req = urllib.request.Request(
            base_url + school_ra + urlparse.quote(school_name.encode("EUC-KR")),
            data=None, headers=headers
        )

        search_url = urllib.request.urlopen(search_req)

        # 학교 검색결과 가져오기
        school_list = ast.literal_eval(search_url.read().decode('utf-8').replace('\x00', ''))["학교검색"]

        # 검색결과를 지역으로 구분하고 학교코드 가져오기
        for i in school_list:
            if i[1] == school_region:
                part_code = i[3]
                break

        # 이번 주 시간표와 다음 주 시간표 가져오기
        fetch_req_1 = urllib.request.Request(
            base_url + school_ra_code + '?' + base64.b64encode(
                bytes(sc_data + str(part_code) + "_0_1", 'utf-8'))
            .decode("utf-8"),
            data=None, headers=headers
        )

        fetch_req_2 = urllib.request.Request(
            base_url + school_ra_code + '?' + base64.b64encode(
                bytes(sc_data + str(part_code) + "_0_2", 'utf-8'))
            .decode("utf-8"),
            data=None, headers=headers
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
            teacher_list = raw_data[i][teachers_list]  # 교사명단
            subject_list = raw_data[i][subjects_list]  # 2글자로 축약한 과목명단 - 전체 명칭은 긴자료92에 담겨있음
            for grade in range(1, 4):
                for class_ in range(1, num_of_classes + 1):
                    tt = raw_data[i][daily_timetable][grade][class_]  # 자료14에 각 반의 일일시간표 정보가 담겨있음
                    og_tt = raw_data[i][original_timetable][grade][class_]  # 자료81에 각 반의 원본시간표 정보가 담겨있음
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
    except Exception as e:
        print(e)


schdls = {}
def schdl():
    neis_baseurl = ("http://stu.goe.go.kr/sts_sci_sf01_001.do?"
                    "schulCode=%s"
                    "&schulCrseScCode=%d"
                    "&schulKndScCode=%02d"
                    % (school_code, school_kind, school_kind))

    neis_urls = [("&ay=%04d&mm=%02d" % (i.year, i.month), i) for i in sy_months]

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

final = {}
for i in days:
    final['%04d-%02d-%02d' % (i.year, i.month, i.day)] = {
        'Schedule': schdls.get(i),
        'Meal': meals.get(i, [None, None]),
        "Timetable": timetables.get(i, timetables_default)
    }
with open('dist/data.v2.json', 'w', encoding="utf-8") as make_file:
    json.dump(final, make_file, ensure_ascii=False)
    print("File Created")
