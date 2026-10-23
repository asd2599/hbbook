# -*- coding: utf-8 -*-
"""계약 만료 관리 현황판 M4 — 실습용 가짜 계약 대장 CSV 4개(부서마다 하나)를 만들고, 계약기준대로 걸리는지 검증한다.

    python tools/contract_data.py

시드를 고정해 몇 번을 돌려도 같은 파일이 나온다. 계약명 · 상대방 · 금액 · 날짜 · 비고는 모두 교육용으로 지어낸 것이다.
한 줄이 계약 하나다 — 계약번호 · 부서 · 계약명 · 분류 · 상대방 · 시작일 · 종료일 · 연간금액 · 전년금액 · 자동연장 ·
해지통보기한(일) · 갱신상태 · 비고. 자료를 뽑은 날(기준일)은 2026-09-30 이다.

결정 마감일 = 자동연장 계약은 종료일 − 해지통보기한, 아니면 종료일.
계약기준.md 의 두 기준(결정 마감일까지 60일 이하인데 갱신상태가 「미착수」 · 연간금액이 전년보다 15% 이상 오름)에
PLANTED 의 여섯 계약만 걸려야 한다. 60일을 90일로 늘리면 PLANTED90 의 두 계약이 더해진다(기준 한 줄 바꾸기 실습).
끝에서 확인하고, 어긋나면 멈춘다.
"""
import csv, datetime as dt, random, pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / '계약현황판'
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(20261022)

BASE = dt.date(2026, 9, 30)
WINDOW, JUMP = 60, 15
D = dt.date.fromisoformat
DEPTS = ['총무팀', '시설관리팀', '인사팀', 'IT지원팀']
FILE = {d: '계약대장_%s.csv' % d for d in DEPTS}
KEY = {'총무팀': 'GA', '시설관리팀': 'FM', '인사팀': 'HR', 'IT지원팀': 'IT'}

# ---- 심어 두는 계약 — (부서, 계약명, 분류, 종료일, 자동연장, 통보기한, 상태, 연간금액(만원), 전년금액(만원), 비고) ----------
PLANTED = [
    ('시설관리팀', '본사 사옥 청소 · 미화 용역', '용역', '2026-11-15', 'N', '', '미착수', 86400, 84000, '담당자 교체 — 재입찰 일정 미정'),   # 준비 늦음 (46일)
    ('총무팀', '법인차량 장기렌터카 (42대)', '임차', '2027-01-31', 'Y', 90, '미착수', 110880, 108000, '자동연장 — 차량 대수 축소 검토 중'),    # 준비 늦음 (마감 11-02, 33일)
    ('총무팀', '복합기 · 프린터 임대', '임차', '2027-03-31', 'Y', 60, '협의 중', 5856, 4800, '장비 교체로 단가 인상 통보 받음'),           # 금액 급증 (+22%)
    ('인사팀', '임직원 건강검진 위탁', '용역', '2027-02-28', 'N', '', '협의 중', 41300, 35000, '위내시경 전원 추가 반영'),                 # 금액 급증 (+18%)
    ('IT지원팀', '그룹웨어 · 협업툴 라이선스', '라이선스', '2026-11-28', 'N', '', '미착수', 31250, 25000, '사용자 수 증가 · 단가 인상 예고'),  # 둘 다 (59일 · +25%)
    ('시설관리팀', '승강기 유지보수', '유지보수', '2026-10-31', 'N', '', '미착수', 9600, 9360, '기존 업체 단순 갱신 예정 — 품의 미작성'),     # 준비 늦음 (31일)
]
PLANTED90 = [   # 60일을 90일로 늘리면 더해지는 두 계약
    ('시설관리팀', '사옥 경비 · 보안 용역', '용역', '2026-12-20', 'N', '', '미착수', 72100, 70000, ''),
    ('인사팀', '임직원 휴양소 법인회원권', '구매', '2026-12-28', 'N', '', '미착수', 15600, 15000, '이용률 낮은 지역 교체 검토'),
]
# 곧 끝나지만 이미 움직이고 있는 계약 — 「곧 끝난다 ≠ 주의」 를 보여 준다 (상태를 고정)
BUSY = {
    '사내식당 위탁운영': ('2026-11-30', '협의 중', '식단가 협의 중 — 10월 중순 품의'),
    '공기청정기 렌탈': ('2026-10-20', '품의 완료', '동일 조건 1년 연장'),
    'PC 장기 리스': ('2027-01-15', '갱신 완료', '자동연장 확정 — 노후 30대만 교체'),
    '백신 · 보안 SW 라이선스': ('2026-12-10', '협의 중', '사용자 수 반영 견적 대기'),
}

# 평소 계약 — (부서, 계약명, 분류, 연간금액 범위(만원), 자동연장 확률)
NORMAL = [
    ('총무팀', '본사 별관 사무실 임차', '임차', (230000, 250000), .6), ('총무팀', '지방 사업소 사무실 임차', '임차', (28000, 36000), .6),
    ('총무팀', '사무용품 단가계약', '구매', (4000, 6000), 0), ('총무팀', '택배 · 우편 발송 대행', '용역', (2400, 3600), .5),
    ('총무팀', '법인 주차장 임차', '임차', (9000, 12000), .7), ('총무팀', '사내 행사 대행', '용역', (6000, 9000), 0),
    ('총무팀', '생수 · 커피 공급', '구매', (2000, 3000), .8), ('총무팀', '문서 보관 · 파쇄 용역', '용역', (1500, 2500), .6),
    ('총무팀', '의전 차량 임차', '임차', (7000, 9000), .5), ('총무팀', '회의실 예약 시스템 유지보수', '유지보수', (1200, 1800), .7),
    ('시설관리팀', '냉난방 설비 유지보수', '유지보수', (18000, 24000), .4), ('시설관리팀', '소방 설비 점검', '용역', (3000, 4500), .3),
    ('시설관리팀', '전기 안전관리 대행', '용역', (2400, 3200), .6), ('시설관리팀', '사옥 조경 관리', '용역', (2000, 3000), .4),
    ('시설관리팀', '방역 · 소독 용역', '용역', (1200, 1800), .7), ('시설관리팀', '주차관제 시스템 유지보수', '유지보수', (1500, 2200), .7),
    ('시설관리팀', '공기청정기 렌탈', '임차', (2600, 3200), .8), ('시설관리팀', '출입통제 시스템 유지보수', '유지보수', (2800, 3600), .6),
    ('인사팀', '사내식당 위탁운영', '용역', (120000, 140000), 0), ('인사팀', '채용 대행', '용역', (8000, 12000), 0),
    ('인사팀', '인적성 검사 플랫폼', '라이선스', (3000, 4200), .5), ('인사팀', '임직원 단체보험', '구매', (60000, 70000), 0),
    ('인사팀', '사내 어린이집 위탁운영', '용역', (38000, 44000), 0), ('인사팀', '외국어 교육 위탁', '용역', (5000, 7000), 0),
    ('인사팀', '복지몰 운영', '용역', (2500, 3500), .6), ('인사팀', '심리상담 프로그램', '용역', (1800, 2600), .5),
    ('IT지원팀', 'PC 장기 리스', '임차', (42000, 48000), 1), ('IT지원팀', '백신 · 보안 SW 라이선스', '라이선스', (9000, 11000), 0),
    ('IT지원팀', '오피스 SW 라이선스', '라이선스', (26000, 30000), 0), ('IT지원팀', '화상회의 솔루션', '라이선스', (4000, 5500), .5),
    ('IT지원팀', '네트워크 장비 유지보수', '유지보수', (7000, 9000), .5), ('IT지원팀', '전자결재 시스템 유지보수', '유지보수', (5000, 6500), .6),
    ('IT지원팀', '데이터 백업 서비스', '용역', (3500, 4500), .6), ('IT지원팀', '모바일 단말 관리', '라이선스', (1500, 2200), .5),
]
VENDOR = {
    '임차': ['한빛자산관리', '동서리스', '새한렌탈', '나래오토리스', '바른부동산신탁'],
    '구매': ['미래상사', '한결유통', '가온물산', '다온보험중개'],
    '용역': ['세진종합관리', '청솔서비스', '누리이엔지', '한마음푸드', '바른HR컨설팅', '새빛에듀'],
    '유지보수': ['대한기술서비스', '동양설비', '한결시스템', '미래네트웍스'],
    '라이선스': ['클라우드원코리아', '세이프소프트', '오피스링크', '한빛솔루션'],
}
NOTE_POOL = ['', '', '', '', '동일 조건 갱신 예정', '물가 상승분 반영', '다년 계약 검토', '사용량 기준 단가', '하반기 재입찰 예정']


def vendor_of(name, cat):
    """계약명에 어울리는 상대방을 고른다."""
    for word, v in (('차량', ['나래오토리스', '새한렌탈']), ('사무실', ['한빛자산관리', '바른부동산신탁']), ('주차장', ['바른부동산신탁']),
                    ('식당', ['한마음푸드']), ('채용', ['바른HR컨설팅']), ('교육', ['새빛에듀']), ('보험', ['다온보험중개']),
                    ('PC', ['동서리스']), ('렌탈', ['새한렌탈'])):
        if word in name:
            return rnd.choice(v)
    pool = [x for x in VENDOR[cat] if x not in ('나래오토리스', '바른부동산신탁', '한마음푸드', '바른HR컨설팅', '새빛에듀', '다온보험중개')]
    return rnd.choice(pool)


def deadline(end, auto, notice):
    return end - dt.timedelta(int(notice)) if auto == 'Y' and notice != '' else end


rows = {d: [] for d in DEPTS}
for dept, name, cat, (lo, hi), p_auto in NORMAL:
    amt = rnd.randrange(lo, hi + 1, 10)
    auto = 'Y' if rnd.random() < p_auto else 'N'
    notice = rnd.choice([30, 60, 90]) if auto == 'Y' else ''
    if name == '공기청정기 렌탈':
        auto, notice = 'N', ''                               # 「곧 끝나도 이미 움직이는 계약」 예시 — 결정 마감 = 종료일
    if name in BUSY:
        e, status, note = BUSY[name]
        end = D(e)
    else:
        note = rnd.choice(NOTE_POOL)
        while True:   # 미착수 계약은 결정 마감이 90일보다 뒤에 오게 — 심은 것 말고는 걸리지 않게
            end = BASE + dt.timedelta(rnd.randint(95, 360))
            if (deadline(end, auto, notice) - BASE).days > 90:
                break
        status = rnd.choices(['미착수', '협의 중', '품의 완료'], [6, 2, 1])[0]
    if name == '백신 · 보안 SW 라이선스':
        prev = round(amt / 1.13 / 10) * 10                  # +13% — 기준(15%) 바로 아래
    elif name in ('채용 대행', '심리상담 프로그램'):
        prev = ''                                            # 신규 계약 — 전년금액 없음
    else:
        prev = round(amt / (1 + rnd.uniform(-.06, .11)) / 10) * 10
    start = end.replace(year=end.year - 1) + dt.timedelta(1)
    rows[dept].append(dict(name=name, cat=cat, vendor=vendor_of(name, cat), start=start, end=end, amt=amt, prev=prev,
                           auto=auto, notice=notice, status=status, note=note))
for dept, name, cat, e, auto, notice, status, amt, prev, note in PLANTED + PLANTED90:
    end = D(e)
    rows[dept].append(dict(name=name, cat=cat, vendor=vendor_of(name, cat), start=end.replace(year=end.year - 1) + dt.timedelta(1),
                           end=end, amt=amt, prev=prev, auto=auto, notice=notice, status=status, note=note))

HEAD = ['계약번호', '부서', '계약명', '분류', '상대방', '시작일', '종료일', '연간금액', '전년금액', '자동연장', '해지통보기한(일)', '갱신상태', '비고']
for f in OUT.glob('계약대장_*.csv'):
    f.unlink()
for dept, rs in rows.items():
    rs.sort(key=lambda r: r['end'])
    with (OUT / FILE[dept]).open('w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp, lineterminator='\r\n')
        w.writerow(HEAD)
        for i, r in enumerate(rs, 1):
            w.writerow(['%s-%03d' % (KEY[dept], i), dept, r['name'], r['cat'], r['vendor'], r['start'].isoformat(), r['end'].isoformat(),
                        r['amt'] * 10_000, r['prev'] * 10_000 if r['prev'] != '' else '', r['auto'], r['notice'], r['status'], r['note']])
    print('  +', FILE[dept], len(rs), '건')


# ---- 검증 — 계약기준.md 를 그대로 적용해 본다 ----------------------------------
def load():
    out = []
    for f in sorted(OUT.glob('계약대장_*.csv')):
        out += list(csv.DictReader(f.open(encoding='utf-8-sig')))
    return out


def check(window=WINDOW):
    hit = {}
    for r in load():
        dl = deadline(D(r['종료일']), r['자동연장'], r['해지통보기한(일)'])
        left = (dl - BASE).days
        why = []
        if left <= window and r['갱신상태'] == '미착수':
            why.append('준비 늦음')
        if r['전년금액'] and (int(r['연간금액']) / int(r['전년금액']) - 1) * 100 >= JUMP:
            why.append('금액 급증')
        if why:
            hit[r['계약명']] = (r['계약번호'], left, why, r['갱신상태'], r['비고'])
    return hit


all_ = load()
tot, totp = sum(int(r['연간금액']) for r in all_), sum(int(r['연간금액']) for r in all_ if r['전년금액'])
prevs = sum(int(r['전년금액']) for r in all_ if r['전년금액'])
print('  = 계약 %d건 · 연간 %.1f억 · 전년 대비 %+.1f%% (전년 금액 있는 %d건)' % (len(all_), tot / 1e8, (totp / prevs - 1) * 100,
                                                                    sum(1 for r in all_ if r['전년금액'])))
near = [r for r in all_ if (deadline(D(r['종료일']), r['자동연장'], r['해지통보기한(일)']) - BASE).days <= 90]
print('  . 결정 마감 90일 안 %d건 — 상태: %s' % (len(near), ', '.join(sorted(r['계약명'] + '(' + r['갱신상태'] + ')' for r in near))))
hit = check()
print('  = 걸린 계약 %d' % len(hit))
for k, v in sorted(hit.items(), key=lambda x: x[1][1]):
    print('    %s %-18s 마감까지 %4d일 · %s · %s — %s' % (v[0], k, v[1], ' · '.join(v[2]), v[3], v[4]))
if set(hit) != {p[1] for p in PLANTED}:
    sys.exit('  ! 심은 여섯 계약과 걸린 것이 다릅니다 : %s' % sorted(set(hit) ^ {p[1] for p in PLANTED}))
hit90 = check(window=90)
print('  = 90일로 늘리면 %d건 : %s' % (len(hit90), sorted(set(hit90) - set(hit))))
if set(hit90) - set(hit) != {p[1] for p in PLANTED90}:
    sys.exit('  ! 90일 기준에서 더해지는 것이 심은 두 계약이 아닙니다')
