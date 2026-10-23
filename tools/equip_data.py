# -*- coding: utf-8 -*-
"""설비 가동률 현황판 M4 — 실습용 가짜 설비가동 CSV 6개(2라인 × 3개월)를 만들고, 설비기준대로 걸리는지 검증한다.

    python tools/equip_data.py

시드를 고정해 몇 번을 돌려도 같은 파일이 나온다. 설비 이름 · 숫자는 모두 교육용으로 지어낸 것이다.
PLANTED 에 심은 (설비, 월) 넷만 기준(가동률 85% 미만 · 전월 대비 5%p 이상 하락)에 걸려야 한다 —
끝에서 확인하고, 어긋나면 멈춘다. 기준을 90% 로 올리면 여섯이 걸린다(기준 한 줄 바꾸기 실습).
"""
import collections, csv, datetime as dt, random, pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / '설비현황판'
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(20261008)

PLAN = 960   # 하루 계획가동 — 2교대 16시간
LINES = {
    '엔진가공': ['블록 CNC #1', '블록 CNC #2', '헤드 CNC #1', '헤드 CNC #2',
              '크랭크 연삭기 #1', '크랭크 연삭기 #2', '캠 연삭기', '세척기'],
    '변속기조립': ['케이스 압입기', '기어 압입기', '볼트 체결기 #1', '볼트 체결기 #2',
               '리크테스터 #1', '리크테스터 #2', '엔드 검사기', '이송 로봇'],
}
# 「주축 과열」 · 「센서 오작동」 은 심어 둔 설비에만 쓴다 — AI 가 「한 원인이 반복된다」를 짚을 수 있게
CAUSES = {
    'CNC': ['공구 파손', '쿨런트 부족', '척 클램프 불량', '스핀들 알람'],
    '연삭기': ['숫돌 드레싱 불량', '치수 측정 이상', '쿨런트 부족'],
    '세척기': ['필터 막힘', '펌프 압력 저하'],
    '압입기': ['압입력 이상', '지그 마모'],
    '체결기': ['너트러너 토크 이상', '소켓 마모'],
    '리크테스터': ['리크 오판정', '에어 압력 저하'],
    '검사기': ['비전 카메라 오류', '조명 불량'],
    '로봇': ['그리퍼 오류', '위치 이탈'],
}


def kind(eq):
    for k in CAUSES:
        if k in eq:
            return k
    return '로봇'


def workdays(m):
    d = dt.date(2026, m, 1)
    while d.month == m:
        if d.weekday() < 5 and d not in (dt.date(2026, 8, 17), dt.date(2026, 9, 24), dt.date(2026, 9, 25)):
            yield d   # 8/17 광복절 대체휴일 · 9/24~25 추석
        d += dt.timedelta(days=1)


# 심어 둔 패턴 — (설비, 월): (목표 가동률 %, 고장 원인 고정, 고장 횟수)
PLANTED = {
    ('크랭크 연삭기 #2', 7): (91.6, '주축 과열', 3),     # 석 달째 같은 원인으로 떨어진다
    ('크랭크 연삭기 #2', 8): (85.9, '주축 과열', 5),     # 85% 위지만 전월보다 5.7%p 하락 → 걸림
    ('크랭크 연삭기 #2', 9): (79.4, '주축 과열', 8),     # 85% 미만 + 하락 → 걸림
    ('리크테스터 #2', 9): (83.2, '센서 오작동', 6),       # 9월에 갑자기 → 걸림
    ('블록 CNC #2', 8): (84.1, '공구 파손', 5),          # 8월만 → 걸림, 9월에 회복
    ('세척기', 7): (94.0, None, 1),                     # 세척기는 천천히 내려온다 — 한 달에 5%p 씩은 아니다
    ('세척기', 8): (91.5, '필터 막힘', 2),
    ('세척기', 9): (88.3, '필터 막힘', 4),               # 85% 기준에서는 정상, 90% 로 올리면 걸림
    ('이송 로봇', 7): (89.2, '그리퍼 오류', 4),           # 〃
}
EXPECT_85 = {('크랭크 연삭기 #2', 8), ('크랭크 연삭기 #2', 9), ('리크테스터 #2', 9), ('블록 CNC #2', 8)}


def month_rows(line, eq, m):
    days = list(workdays(m))
    plan = PLAN * len(days)
    if (eq, m) in PLANTED:
        target, fixed, n_fail = PLANTED[(eq, m)]
    else:
        target, fixed, n_fail = rnd.uniform(93.6, 98.4), None, rnd.choice([0, 1, 1, 2, 2, 3])
    down_total = round(plan * (1 - target / 100))
    # 고장 외 정지(금형 · 공구 교체, 자재 대기)를 먼저 깔고, 남는 만큼을 고장으로 나눈다
    other = [rnd.randint(0, 18) for _ in days]
    fail_total = max(0, down_total - sum(other))
    if n_fail == 0:
        other = [round(o * down_total / max(1, sum(other))) for o in other]
        fail_total = 0
    fail_days = sorted(rnd.sample(range(len(days)), n_fail)) if n_fail else []
    cuts = sorted(rnd.sample(range(1, fail_total), n_fail - 1)) if n_fail > 1 and fail_total > n_fail else []
    parts = [b - a for a, b in zip([0] + cuts, cuts + [fail_total])] if n_fail else []
    rows = []
    for i, d in enumerate(days):
        ft = parts[fail_days.index(i)] if i in fail_days else 0
        cause = (fixed or rnd.choice(CAUSES[kind(eq)])) if ft else '-'
        rows.append([d.isoformat(), line, eq, PLAN, other[i] + ft, 1 if ft else 0, ft, cause])
    return rows


for line, eqs in LINES.items():
    for m in (7, 8, 9):
        rows = [r for eq in eqs for r in month_rows(line, eq, m)]
        rows.sort(key=lambda r: (r[0], eqs.index(r[2])))
        f = OUT / ('설비가동_%s_2026-%02d.csv' % (line, m))
        with f.open('w', encoding='utf-8-sig', newline='') as fp:
            w = csv.writer(fp, lineterminator='\r\n')
            w.writerow(['일자', '라인', '설비', '계획가동(분)', '비가동(분)', '고장건수', '고장시간(분)', '주요원인'])
            w.writerows(rows)
        print('  +', f.name, len(rows), '행')


# ---- 검증 — 설비기준.md 를 그대로 적용해 본다 ----------------------------------
def check(low=85, drop=5):
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    n = 0
    for f in sorted(OUT.glob('설비가동_*.csv')):
        for r in csv.DictReader(f.open(encoding='utf-8-sig')):
            a = agg[(r['설비'], int(r['일자'][5:7]))]
            a[0] += int(r['계획가동(분)']); a[1] += int(r['비가동(분)']); a[2] += int(r['고장건수']); a[3] += int(r['고장시간(분)'])
            n += 1
    rate = {k: (v[0] - v[1]) / v[0] * 100 for k, v in agg.items()}
    hit = set()
    for (eq, m), r in rate.items():
        prev = rate.get((eq, m - 1))
        if r < low or (prev is not None and prev - r >= drop):
            hit.add((eq, m))
    return n, rate, hit


n, rate, hit = check()
print('  = %d행 · 설비 %d대 · 걸린 (설비, 월) %d : %s' % (n, len({k[0] for k in rate}), len(hit), sorted(hit)))
for k in sorted(PLANTED):
    print('    %s %d월 %.1f%%' % (k[0], k[1], rate[k]))
if hit != EXPECT_85:
    sys.exit('  ! 심은 넷과 걸린 것이 다릅니다 : %s' % sorted(hit ^ EXPECT_85))
hit90 = check(low=90)[2]
print('  = 기준을 90%% 로 올리면 %d : %s' % (len(hit90), sorted(hit90 - hit)))
if len(hit90) != 6:
    sys.exit('  ! 90% 기준에서 여섯이 아닙니다')
