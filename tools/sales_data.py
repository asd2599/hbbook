# -*- coding: utf-8 -*-
"""판매 실적 현황판 M4 — 실습용 가짜 판매실적 CSV 3개(7 · 8 · 9월)를 만들고, 판매기준대로 걸리는지 검증한다.

    python tools/sales_data.py

시드를 고정해 몇 번을 돌려도 같은 파일이 나온다. 차종 이름은 현대자동차 국내 판매 차종을 빌렸지만
지점 · 숫자는 모두 교육용으로 지어낸 것이다 — 실제 판매 실적과 무관하다.
한 줄이 지점 하나의 한 차종이고, 목표대수(BP)도 같은 줄에 있다 — 지역 × 차종 × 월로 합쳐야 달성률이 나온다.
(2026-10-12 목표를 따로 두던 파일을 없앴다. 지점별 목표는 rnd_plan 으로 나눠 판매 숫자는 그대로다.)
PLANTED 에 심은 (지역, 차종, 월) 다섯만 기준(달성률 85% 미만 · 전년 동월보다 10% 이상 감소)에 걸려야 한다 —
끝에서 확인하고, 어긋나면 멈춘다. 기준을 90% 로 올리면 일곱이 걸린다(기준 한 줄 바꾸기 실습).
"""
import collections, csv, random, pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / '판매현황판'
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(20261013)
rnd_plan = random.Random(20261014)   # 지역 목표를 지점으로 나눌 때만 쓴다 — rnd 의 순서를 건드리지 않게

# 지역 — (지역별 비중, 지점)
REGIONS = {
    '서울':     (.20, ['강남', '송파', '마포', '노원']),
    '경기':     (.27, ['수원', '분당', '일산', '안산', '의정부']),
    '강원':     (.04, ['춘천', '원주']),
    '충청':     (.11, ['대전', '청주', '천안']),
    '호남':     (.10, ['광주', '전주', '순천']),
    '대구경북': (.11, ['대구', '포항', '구미']),
    '부산경남': (.14, ['부산', '창원', '울산', '김해']),
}
# 차종 — 전국 한 달 목표의 바탕 (지어낸 값)
MODELS = {'캐스퍼': 2600, '아반떼': 5600, '쏘나타': 4200, '그랜저': 7200, '코나': 3000,
          '투싼': 4600, '싼타페': 6400, '팰리세이드': 4200, '아이오닉 5': 2400}
MONTHS = {7: 1.00, 8: 0.92, 9: 1.04}     # 8월은 휴가철

# 심어 둔 패턴 — (지역, 차종, 월): (달성률 %, 전년비 %)
PLANTED = {
    ('서울', '아이오닉 5', 8): (93.0, -4.0),
    ('서울', '아이오닉 5', 9): (72.4, -21.0),       # 9월에 수도권 둘이 같이 꺾인다 → 두 기준 다 걸림
    ('경기', '아이오닉 5', 8): (95.1, -3.0),
    ('경기', '아이오닉 5', 9): (79.6, -14.0),       # 〃
    ('부산경남', '그랜저', 7): (93.1, -2.0),         # 석 달째 조금씩 내려온다
    ('부산경남', '그랜저', 8): (88.4, -6.0),         # 85% 기준에서는 정상, 90% 로 올리면 걸림
    ('부산경남', '그랜저', 9): (83.7, -9.0),         # 85% 미만 → 걸림 (전년비는 -9% 라 안 걸림)
    ('강원', '쏘나타', 9): (96.2, -13.5),            # 목표는 넘었지만 작년보다 크게 줄었다 → 전년비만 걸림
    ('호남', '싼타페', 8): (81.5, -5.0),             # 8월만 → 걸림, 9월에 회복
    ('호남', '싼타페', 9): (99.0, 2.0),
    ('충청', '투싼', 9): (87.6, -3.0),               # 85% 기준에서는 정상, 90% 로 올리면 걸림
}
EXPECT_85 = {('서울', '아이오닉 5', 9), ('경기', '아이오닉 5', 9), ('부산경남', '그랜저', 9),
             ('강원', '쏘나타', 9), ('호남', '싼타페', 8)}


def split(total, n, r=rnd):
    """total 을 n 개의 정수로 나눈다 (합이 정확히 total)."""
    w = [r.uniform(.7, 1.3) for _ in range(n)]
    parts = [int(total * x / sum(w)) for x in w]
    for i in range(total - sum(parts)):
        parts[i % n] += 1
    return parts


def split_like(total, ref):
    """total 을 ref(지점별 판매) 비중대로 조금씩 흔들어 나눈다 — 지점 달성률이 지역과 크게 어긋나지 않게."""
    w = [max(1, x) * rnd_plan.uniform(.92, 1.08) for x in ref]
    parts = [int(total * x / sum(w)) for x in w]
    for i in range(total - sum(parts)):
        parts[i % len(ref)] += 1
    return parts


sales = collections.defaultdict(list)
for m, mf in MONTHS.items():
    for reg, (rw, branches) in REGIONS.items():
        for mdl, base in MODELS.items():
            plan = round(base * rw * mf / 10) * 10
            if (reg, mdl, m) in PLANTED:
                rate, yoy = PLANTED[(reg, mdl, m)]
            else:
                rate, yoy = rnd.uniform(91.5, 108.0), rnd.uniform(-7.0, 12.0)
            act = round(plan * rate / 100)
            prev = round(act / (1 + yoy / 100))
            acts, prevs = split(act, len(branches)), split(prev, len(branches))
            plans = split_like(plan, acts)
            for br, a, t, p in zip(branches, acts, plans, prevs):
                sales[m].append(['2026-%02d' % m, reg, br + '지점', mdl, a, t, p])


def write(name, head, rows):
    f = OUT / name
    with f.open('w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp, lineterminator='\r\n')
        w.writerow(head)
        w.writerows(rows)
    print('  +', f.name, len(rows), '행')


for m in MONTHS:
    write('판매실적_2026-%02d.csv' % m, ['월', '지역', '지점', '차종', '판매대수', '목표대수', '전년동월'], sales[m])


# ---- 검증 — 판매기준.md 를 그대로 적용해 본다 ----------------------------------
def check(low=85, yoy_drop=10):
    act = collections.defaultdict(lambda: [0, 0, 0])
    n = 0
    for f in sorted(OUT.glob('판매실적_*.csv')):
        for r in csv.DictReader(f.open(encoding='utf-8-sig')):
            a = act[(r['지역'], r['차종'], int(r['월'][5:7]))]
            a[0] += int(r['판매대수']); a[1] += int(r['전년동월']); a[2] += int(r['목표대수'])
            n += 1
    rate = {k: v[0] / v[2] * 100 for k, v in act.items()}
    yoy = {k: (v[0] / v[1] - 1) * 100 for k, v in act.items()}
    hit = {k for k in act if rate[k] < low or yoy[k] <= -yoy_drop}
    return n, rate, yoy, hit


n, rate, yoy, hit = check()
print('  = 실적 %d행 · 지역 %d · 차종 %d · 걸린 (지역, 차종, 월) %d : %s' %
      (n, len(REGIONS), len(MODELS), len(hit), sorted(hit)))
for k in sorted(PLANTED):
    print('    %s %s %d월 달성률 %.1f%% · 전년비 %+.1f%%' % (k[0], k[1], k[2], rate[k], yoy[k]))
if hit != EXPECT_85:
    sys.exit('  ! 심은 다섯과 걸린 것이 다릅니다 : %s' % sorted(hit ^ EXPECT_85))
hit90 = check(low=90)[3]
print('  = 기준을 90%% 로 올리면 %d : %s' % (len(hit90), sorted(hit90 - hit)))
if len(hit90) != 7:
    sys.exit('  ! 90% 기준에서 일곱이 아닙니다')
