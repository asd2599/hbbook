# -*- coding: utf-8 -*-
"""감사실 M4 실습용 가짜 경비내역 CSV 3개를 만들고, 점검기준대로 걸리는 행을 검증한다.

    python tools/audit_data.py

시드를 고정해 몇 번을 돌려도 같은 파일이 나온다. 이름 · 가맹점은 모두 지어낸 것이다.
PLANTED 에 심은 12행만 점검기준에 걸려야 한다 — 끝에서 확인하고, 어긋나면 멈춘다.
"""
import collections, csv, datetime as dt, random, pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / '감사실'
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(20261001)

PEOPLE = {
    '영업1팀': ['최지훈', '김민서', '이태호'],
    '영업2팀': ['한도윤', '서예린'],
    '구매팀': ['박준형', '임수아', '장우진'],
    '품질팀': ['윤서진', '조현우'],
    '생산기술팀': ['배성민', '신지아'],
    '인사팀': ['강하늘', '문채원'],
    '재무팀': ['오세영', '황민규'],
    '연구기획팀': ['정유나', '노승현'],
}
# 업종: (가맹점 목록, 금액 범위, 적요 후보, 가중치)
CATS = {
    '일반음식점': (['소담 한정식', '명동칼국수 본점', '바른돈까스 역삼', '청솔 설렁탕', '화로구이 양재',
                   '하늘정원 중식당', '마포 생선구이', '담소 쌈밥'], (12000, 180000),
                  ['팀 점심', '부서 회의 식대', '협력사 미팅 식대', '신입사원 환영 식사', '프로젝트 회의 식대'], 34),
    '커피전문점': (['브루잉랩 강남', '카페 온도', '빈스토리 양재'], (4500, 45000),
                  ['회의 음료', '방문객 음료', '팀 회의 다과'], 18),
    '택시': (['시티택시', '서울개인택시'], (7800, 34000), ['외근 이동', '고객사 방문 이동', '현장 점검 이동'], 10),
    '문구·사무용품': (['오피스디포 강남', '알파문구 역삼', '모닝글로리 양재'], (5000, 120000),
                   ['사무용품 구입', '교육 자료 인쇄', '회의용 소모품'], 8),
    '서점': (['교보문고 강남', '영풍문고 종로'], (15000, 60000), ['업무 참고 도서', '직무 교육 교재'], 4),
    '주유소': (['에이원주유소', '한빛주유소 양재'], (40000, 90000), ['업무 차량 주유'], 5),
    '숙박': (['비즈니스호텔 울산', '스테이 아산', '호텔 여수항'], (80000, 160000), ['공장 출장 숙박', '현장 점검 출장 숙박'], 5),
    '철도·항공': (['코레일', '에어부산'], (48000, 130000), ['울산 공장 출장', '아산 공장 출장', '협력사 방문 출장'], 6),
}
BIG_DINNER = ['화로구이 양재', '하늘정원 중식당', '소담 한정식']

def weekdays(y, m):
    d = dt.date(y, m, 1)
    while d.month == m:
        if d.weekday() < 5 and not (m == 8 and d.day == 17):  # 8/17 광복절 대체휴일
            yield d
        d += dt.timedelta(days=1)

def normal_rows(y, m, n):
    days = list(weekdays(y, m))
    cats = list(CATS)
    weights = [CATS[c][3] for c in cats]
    rows = []
    seen = set()
    while len(rows) < n:
        c = rnd.choices(cats, weights)[0]
        shops, (lo, hi), memos, _ = CATS[c]
        dept = rnd.choice(list(PEOPLE))
        who = rnd.choice(PEOPLE[dept])
        day = rnd.choice(days)
        shop = rnd.choice(shops)
        if (who, day, shop) in seen:
            continue
        seen.add((who, day, shop))
        if c == '일반음식점':
            h = rnd.choice([11, 12, 12, 12, 13, 18, 19, 19, 20])
        elif c == '커피전문점':
            h = rnd.choice([9, 10, 13, 14, 15, 16])
        else:
            h = rnd.randint(8, 18)
        t = dt.datetime.combine(day, dt.time(h, rnd.randint(0, 59)))
        amt = rnd.randint(lo, hi) // 100 * 100
        rows.append([t, dept, who, shop, c, amt, rnd.choice(memos)])
    return rows

# 회식 — 30만 원대 (기준을 30만으로 낮추면 새로 걸리는 정상 건)
def big_dinners(y, m, k):
    rows = []
    days = list(weekdays(y, m))
    for _ in range(k):
        dept = rnd.choice(list(PEOPLE))
        who = PEOPLE[dept][0]
        day = rnd.choice(days)
        t = dt.datetime.combine(day, dt.time(19, rnd.randint(0, 50)))
        rows.append([t, dept, who, rnd.choice(BIG_DINNER), '일반음식점',
                     rnd.randint(3050, 3480) * 100, '부서 회식'])
    return rows

T = lambda s: dt.datetime.strptime(s, '%Y-%m-%d %H:%M')
PLANTED = {
    7: [
        [T('2026-07-16 19:40'), '영업1팀', '최지훈', '라온 한정식', '일반음식점', 684000, '거래처 접대'],
        [T('2026-07-25 07:10'), '구매팀', '박준형', '그린힐CC', '골프장', 420000, '협력사 미팅'],
        [T('2026-07-09 23:52'), '품질팀', '윤서진', '시티택시', '택시', 32400, '야근 후 귀가'],
    ],
    8: [
        [T('2026-08-12 20:15'), '구매팀', '박준형', '르블랑 와인바', '일반음식점', 290000, '업무협의'],
        [T('2026-08-12 20:17'), '구매팀', '박준형', '르블랑 와인바', '일반음식점', 275000, '업무협의'],
        [T('2026-08-20 01:35'), '구매팀', '박준형', '블루문', '유흥주점', 380000, '기타'],
        [T('2026-08-22 14:20'), '인사팀', '강하늘', '해피마트 분당점', '대형마트', 187000, '사무실 비품'],
    ],
    9: [
        [T('2026-09-03 11:05'), '연구기획팀', '정유나', '에이스컴퓨터', '전자제품', 1250000, '노트북 구입'],
        [T('2026-09-18 16:40'), '구매팀', '박준형', '상품권나라', '상품권', 500000, '명절 선물'],
        [T('2026-09-27 23:10'), '영업2팀', '한도윤', '청담 포차', '일반음식점', 164000, '팀 회식'],
        [T('2026-09-24 13:10'), '재무팀', '오세영', '오피스디포 강남', '문구·사무용품', 260000, '사무용품 구입'],
        [T('2026-09-24 13:12'), '재무팀', '오세영', '오피스디포 강남', '문구·사무용품', 260000, '사무용품 구입'],
    ],
}
COUNTS = {7: 96, 8: 88, 9: 102}
BIG = {7: 1, 8: 1, 9: 2}

for m in (7, 8, 9):
    rows = normal_rows(2026, m, COUNTS[m]) + big_dinners(2026, m, BIG[m]) + PLANTED[m]
    rows.sort(key=lambda r: r[0])
    f = OUT / ('경비내역_2026-%02d.csv' % m)
    with f.open('w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp, lineterminator='\r\n')
        w.writerow(['승인일시', '부서', '사용자', '가맹점', '업종', '금액', '적요'])
        for r in rows:
            w.writerow([r[0].strftime('%Y-%m-%d %H:%M')] + r[1:])
    print('  +', f.name, len(rows), '건')


# ---- 검증 — 점검기준.md 다섯 줄을 그대로 적용해 본다 -------------------------
def check(limit=500000):
    rows = []
    for f in sorted(OUT.glob('경비내역_*.csv')):
        rows += list(csv.DictReader(f.open(encoding='utf-8-sig')))
    grp = collections.defaultdict(list)
    for r in rows:
        r['t'] = dt.datetime.strptime(r['승인일시'], '%Y-%m-%d %H:%M'); r['금액'] = int(r['금액'])
        grp[(r['사용자'], r['t'].date(), r['가맹점'])].append(r)
    cnt, hit = collections.Counter(), []
    for r in rows:
        f = []
        if r['금액'] > limit: f.append('한도 초과')
        if r['t'].hour >= 22 or r['t'].hour < 6: f.append('심야 사용')
        if r['t'].weekday() >= 5: f.append('주말 사용')
        g = grp[(r['사용자'], r['t'].date(), r['가맹점'])]
        if len(g) >= 2 and sum(x['금액'] for x in g) > 500000: f.append('분할 결제 의심')
        if r['업종'] in ('유흥주점', '골프장', '상품권'): f.append('제한 업종')
        if f: hit.append(r); cnt.update(f)
    return len(rows), sum(r['금액'] for r in rows), hit, cnt


n, total, hit, cnt = check()
print('  = %d건 · %s원 · 걸린 행 %d · %s' % (n, format(total, ','), len(hit), dict(cnt)))
planted = sum(len(v) for v in PLANTED.values())
if len(hit) != planted:
    sys.exit('  ! 심은 %d행과 걸린 %d행이 다릅니다 — 정상 데이터가 기준에 걸렸습니다' % (planted, len(hit)))
print('  = 한도를 30만 원으로 내리면 걸린 행 %d' % len(check(300000)[2]))
