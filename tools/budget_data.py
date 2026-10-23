# -*- coding: utf-8 -*-
"""예산 집행 현황판 M4 — 실습용 가짜 예산 · 집행 CSV 를 만들고, 예산기준대로 걸리는지 검증한다.

    python tools/budget_data.py

시드를 고정해 몇 번을 돌려도 같은 파일이 나온다. 팀 · 프로젝트 · 거래처 · 적요 · 금액은 모두 교육용으로 지어낸 것이다.
수소 충전소 · 연료전지 · 수전해 같은 사업 이름만 빌렸고, 실제 사업 · 예산과 무관하다.

  연간예산_2026.csv          팀 · 프로젝트 · 계정 · 연간예산 · 비고 (한 줄이 프로젝트 × 계정 하나)
  예산집행_<팀>.csv  × 4     전표번호 · 집행일 · 팀 · 프로젝트 · 계정 · 거래처 · 적요 · 금액 (한 줄이 집행 한 건)

자료는 2026-09-30 마감 기준이다(9개월 경과 → 정상 페이스 75%).
예산기준.md 의 두 기준(정상 페이스보다 15%p 이상 빠름 · 30%p 이상 느림)에 PLANTED 의 다섯 항목만 걸려야 한다.
과속 기준을 10%p 로 좁히면 PLANTED10 의 두 항목이 더해진다(기준 한 줄 바꾸기 실습). 끝에서 확인하고, 어긋나면 멈춘다.
"""
import csv, datetime as dt, random, pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / '예산현황판'
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(20261021)

BASE = dt.date(2026, 9, 30)
PACE = 9 / 12 * 100                 # 정상 페이스(%)
FAST, SLOW = 15, 30                 # 주의 — 정상 페이스보다 이만큼(%p) 빠르거나 느리면
ACC = ['설비투자', '인허가·안전', '수소 구매·운영', '용역·연구', '대외협력·출장']

# 팀 → 프로젝트 → 계정별 연간예산(백만원). 0 이면 그 계정은 예산이 없다.
TEAMS = {
    '충전인프라팀': {
        '평택 수소충전소 구축':  [2400, 180, 120, 150, 30],
        '상용차 충전소 증설':    [1800, 220,   0, 120, 20],
    },
    '연료전지사업팀': {
        '발전용 연료전지 실증':  [1500,  90, 640, 200, 30],
        '건물용 연료전지 시범':  [ 600,  60, 150, 140, 20],
    },
    '수소생산팀': {
        '그린수소 수전해 실증':  [2200, 120, 180, 260, 30],
        '부생수소 공급망 검토':  [   0,   0,   0, 300, 40],
    },
    '사업기획팀': {
        '수소 밸류체인 전략 수립': [0,   0,   0, 420, 60],
        '국제 수소 박람회 참가':  [0,   0,   0,  80, 260],
    },
}
TEAM_OF = {p: t for t, ps in TEAMS.items() for p in ps}
FILE = {'충전인프라팀': '예산집행_충전인프라팀.csv', '연료전지사업팀': '예산집행_연료전지사업팀.csv',
        '수소생산팀': '예산집행_수소생산팀.csv', '사업기획팀': '예산집행_사업기획팀.csv'}
NO_KEY = {'충전인프라팀': 'CI', '연료전지사업팀': 'FC', '수소생산팀': 'HP', '사업기획팀': 'BP'}

# 예산표 비고 — 팀이 적어 둔 사정. AI 가 적요와 함께 읽는다.
NOTE = {
    ('평택 수소충전소 구축', '설비투자'): '압축기 · 저장용기 계약금 상반기 선지급 (계약 조건)',
    ('상용차 충전소 증설', '인허가·안전'): '부지 인허가 지자체 협의 지연 — 10월 심의 예정',
    ('그린수소 수전해 실증', '설비투자'): '수전해 스택 공급사 납기 지연 — 본 발주 4분기로 연기',
    ('국제 수소 박람회 참가', '대외협력·출장'): '부스 규모 확대 (8월 본부 결정) — 예산 조정 요청 예정',
    ('부생수소 공급망 검토', '용역·연구'): '공급망 검토 용역 11월 최종보고 — 잔금 12월',
    ('발전용 연료전지 실증', '설비투자'): '연료전지 모듈 2차분 10월 입고 예정',
}

# ---- 심어 두는 항목 — (프로젝트, 계정) : 집행률 · 굵직한 집행 (월-일, 거래처, 적요, 백만원) ------------------
PLANTED = {
    ('평택 수소충전소 구축', '설비투자'): (96, [
        ('03-16', '청솔엔지니어링', '충전소 상세설계 착수금', 180),
        ('05-20', '수성압력기기', '저장용기 제작 계약금 (30%)', 420),
        ('07-08', '대성압축기', '고압 압축기 계약금 (30%)', 780),
        ('08-26', '누리플랜트', '부지 토목공사 기성 (1차)', 520),
        ('09-18', '미래하이텍', '디스펜서 선급금', 330)]),                                          # 과속
    ('발전용 연료전지 실증', '수소 구매·운영'): (95, [
        ('04-10', '동해에너지서비스', '수소 구매 단가 인상 소급 정산 (1~3월분)', 42)]),          # 과속 — 아래에서 월별 구매가 커진다
    ('국제 수소 박람회 참가', '대외협력·출장'): (104, [
        ('06-12', '가온이벤트', '박람회 부스 임차 계약금', 90),
        ('08-21', '가온이벤트', '부스 디자인 · 시공 (규모 확대)', 85),
        ('07-02', '한결여행', '해외 출장 — 박람회 사전 협의 (2회)', 38),
        ('09-04', '새빛미디어', '홍보물 · 영상 제작', 32),
        ('09-15', '가온이벤트', '바이어 미팅 행사장 대관', 25)]),                                 # 과속 (이미 초과)
    ('그린수소 수전해 실증', '설비투자'): (28, [
        ('04-14', '청솔엔지니어링', '수전해 설비 기본설계 (1차)', 220),
        ('06-23', '누리플랜트', '부지 전력 인입 설계', 140)]),                                    # 저조
    ('상용차 충전소 증설', '인허가·안전'): (38, [
        ('02-25', '한빛인허가컨설팅', '인허가 대행 용역 착수금', 40)]),                           # 저조
}
PLANTED10 = {   # 과속 기준을 10%p 로 좁히면 더해지는 두 항목
    ('건물용 연료전지 시범', '용역·연구'): (87, [('08-19', '미래시험연구원', '건물용 연료전지 성능 시험 의뢰 (추가)', 38)]),
    ('수소 밸류체인 전략 수립', '용역·연구'): (86, [('07-15', '새빛컨설팅', '수소 밸류체인 전략 컨설팅 (2차 중도금)', 126)]),
}

# 계정별 평소 적요 · 거래처
MEMO = {
    '설비투자': {
        '_': ['배관 · 전기 공사 기성', '안전설비(가스감지기) 구매', '계측장비 구매', '설비 시운전 지원', '제어반 개조'],
        '연료전지': ['연료전지 모듈 구매 (1차분)', 'BOP 설비 설치 기성', '열회수 설비 구매', '계통연계 설비 공사'],
        '수전해': ['전력 변환장치 사양 검토', '수전해 스택 공급사 기술 실사', '냉각수 설비 설계'],
    },
    '인허가·안전': ['고압가스 안전검사 수수료', '가스시설 기술검토 수수료', '방폭 인증 수수료', '안전관리자 법정 교육', '정기 안전점검'],
    '수소 구매·운영': ['시운전용 수소 구매 ({m}월분)', '튜브트레일러 운송비 ({m}월분)', '설비 유지보수 ({m}월)', '운영 위탁비 ({m}월)'],
    '용역·연구': ['타당성 검토 용역 ({k}차)', '경제성 분석 용역', '시험 · 성능 평가 의뢰', '기술 자문료', '시장 조사 용역'],
    '대외협력·출장': ['지자체 협의 출장', '국내 수소 세미나 참가', '협력사 기술 회의', '해외 출장 — 수소 협의체 회의', '업무 협약식 행사'],
}
VENDOR = {
    '설비투자': ['누리플랜트', '미래하이텍', '청솔엔지니어링', '수성압력기기', '한결테크'],
    '인허가·안전': ['한빛인허가컨설팅', '가스안전기술원', '세진안전', '한결테크'],
    '수소 구매·운영': ['동해에너지서비스', '하나로물류', '세진안전', '누리플랜트'],
    '용역·연구': ['새빛컨설팅', '미래시험연구원', '한빛경제연구소', '청솔엔지니어링'],
    '대외협력·출장': ['한결여행', '가온이벤트', '새빛미디어', '사내 출장정산'],
}
# 계정별 월 비중(1~9월) — 설비는 들쭉날쭉, 나머지는 고르게
MONTH_W = {'설비투자': [1, 1, 2, 2, 2, 3, 2, 3, 3], '인허가·안전': [1, 1, 2, 1, 2, 1, 1, 2, 1],
           '수소 구매·운영': [1] * 9, '용역·연구': [1, 1, 1, 2, 1, 2, 1, 2, 2], '대외협력·출장': [1, 1, 2, 1, 2, 1, 1, 1, 2]}


def vendor_of(acc, memo):
    """적요에 어울리는 거래처를 고른다."""
    for word, v in (('출장', ['사내 출장정산', '한결여행']), ('세미나', ['수소산업 세미나 사무국']), ('협약', ['가온이벤트']),
                    ('수소 구매', ['동해에너지서비스']), ('운송', ['하나로물류']), ('유지보수', ['세진안전', '누리플랜트']),
                    ('위탁', ['동해에너지서비스']), ('시험', ['미래시험연구원']), ('교육', ['가스안전기술원']), ('인증', ['세진안전'])):
        if word in memo:
            return rnd.choice(v)
    return rnd.choice(VENDOR[acc])


def memo_of(proj, acc, m, k):
    if acc == '설비투자':
        key = '연료전지' if '연료전지' in proj else '수전해' if '수전해' in proj else '_'
        return rnd.choice(MEMO['설비투자'][key])
    return rnd.choice(MEMO[acc]).format(m=m, k=k)


def day_in(m):
    return dt.date(2026, m, rnd.randint(2, 27))


def split(total, n):
    """total(만원)을 n 개로 나눈다 — 10만원 단위."""
    w = [rnd.uniform(.6, 1.6) for _ in range(n)]
    parts = [max(10, round(total * x / sum(w) / 10) * 10) for x in w]
    parts[-1] += total - sum(parts)
    return parts


budget, ledger = [], []
for team, ps in TEAMS.items():
    for proj, amounts in ps.items():
        for acc, b in zip(ACC, amounts):
            if not b:
                continue
            budget.append((team, proj, acc, b * 1_000_000, NOTE.get((proj, acc), '')))
            key = (proj, acc)
            rate, big = (PLANTED.get(key) or PLANTED10.get(key) or (rnd.uniform(57, 81), []))
            total = round(b * 100 * rate / 100)                     # 만원
            rows = [(dt.date.fromisoformat('2026-' + d), v, memo, a * 100) for d, v, memo, a in big]
            rest = total - sum(r[3] for r in rows)
            if key == ('발전용 연료전지 실증', '수소 구매·운영'):
                # 매달 수소를 사는데 4월부터 단가가 올라 금액이 커진다
                w = [1, 1, 1, 1.18, 1.2, 1.22, 1.24, 1.26, 1.28]
                mon = [round(rest * x / sum(w) / 10) * 10 for x in w]
                mon[-1] += rest - sum(mon)
                for m, a in enumerate(mon, 1):
                    rows.append((day_in(m), '동해에너지서비스',
                                 '실증용 수소 구매 (%d월분)%s' % (m, ' — 단가 인상분 반영' if m >= 4 else ''), a))
            elif rest > 0:
                n = max(3, min(11, round(b / 70)))
                if key in PLANTED or key in PLANTED10:
                    n = max(2, n // 3)                               # 심은 항목은 굵직한 집행 위주
                months = rnd.choices(range(1, 10), MONTH_W[acc], k=n)
                for i, (m, a) in enumerate(zip(sorted(months), split(rest, n))):
                    memo = memo_of(proj, acc, m, i + 1)
                    rows.append((day_in(m), vendor_of(acc, memo), memo, a))
            for d, v, memo, a in rows:
                ledger.append(dict(day=d, team=team, proj=proj, acc=acc, vendor=v, memo=memo, amt=a * 10_000))

# ---- 쓰기 ------------------------------------------------------------------------
for f in list(OUT.glob('예산집행_*.csv')) + list(OUT.glob('연간예산_*.csv')):
    f.unlink()
with (OUT / '연간예산_2026.csv').open('w', encoding='utf-8-sig', newline='') as fp:
    w = csv.writer(fp, lineterminator='\r\n')
    w.writerow(['팀', '프로젝트', '계정', '연간예산', '비고'])
    for r in budget:
        w.writerow(r)
print('  + 연간예산_2026.csv', len(budget), '줄')
for team in TEAMS:
    rs = sorted([r for r in ledger if r['team'] == team], key=lambda r: (r['day'], r['proj'], r['acc']))
    with (OUT / FILE[team]).open('w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp, lineterminator='\r\n')
        w.writerow(['전표번호', '집행일', '팀', '프로젝트', '계정', '거래처', '적요', '금액'])
        for i, r in enumerate(rs, 1):
            w.writerow(['%s-26-%04d' % (NO_KEY[team], i), r['day'].isoformat(), team, r['proj'], r['acc'], r['vendor'], r['memo'], r['amt']])
    print('  +', FILE[team], len(rs), '건')


# ---- 검증 — 예산기준.md 를 그대로 적용해 본다 ----------------------------------------
def load():
    b = list(csv.DictReader((OUT / '연간예산_2026.csv').open(encoding='utf-8-sig')))
    l = []
    for f in sorted(OUT.glob('예산집행_*.csv')):
        l += list(csv.DictReader(f.open(encoding='utf-8-sig')))
    return b, l


def check(fast=FAST, slow=SLOW):
    b, l = load()
    spent = {}
    for r in l:
        spent[(r['프로젝트'], r['계정'])] = spent.get((r['프로젝트'], r['계정']), 0) + int(r['금액'])
    hit = {}
    for r in b:
        k = (r['프로젝트'], r['계정'])
        rate = spent.get(k, 0) / int(r['연간예산']) * 100
        if rate - PACE >= fast:
            hit[k] = (rate, '과속')
        elif PACE - rate >= slow:
            hit[k] = (rate, '저조')
    return hit, b, l, spent


hit, b, l, spent = check()
tb = sum(int(r['연간예산']) for r in b)
ts = sum(int(r['금액']) for r in l)
print('  = 연간예산 %.1f억 · 집행 %.1f억 · 집행률 %.1f%% (정상 페이스 %.0f%%) · 집행 %d건' % (tb / 1e8, ts / 1e8, ts / tb * 100, PACE, len(l)))
for team in TEAMS:
    bt = sum(int(r['연간예산']) for r in b if r['팀'] == team)
    st = sum(int(r['금액']) for r in l if r['팀'] == team)
    print('    %-8s 예산 %6.1f억 · 집행 %6.1f억 · %.1f%%' % (team, bt / 1e8, st / 1e8, st / bt * 100))
for m in range(1, 10):
    c = sum(int(r['금액']) for r in l if int(r['집행일'][5:7]) <= m)
    print('    ~%d월 누적 %.1f%% (정상 %.1f%%)' % (m, c / tb * 100, m / 12 * 100))
print('  = 걸린 항목 %d' % len(hit))
for k, v in sorted(hit.items(), key=lambda x: -abs(x[1][0] - PACE)):
    print('    %-14s %-8s %5.1f%% (%+.1f%%p) %s' % (k[0], k[1], v[0], v[0] - PACE, v[1]))
if set(hit) != set(PLANTED):
    sys.exit('  ! 심은 다섯 항목과 걸린 것이 다릅니다 : %s' % sorted(set(hit) ^ set(PLANTED)))
hit10, *_ = check(fast=10)
print('  = 과속 기준을 10%%p 로 좁히면 %d항목 : %s' % (len(hit10), sorted(set(hit10) - set(hit))))
if set(hit10) - set(hit) != set(PLANTED10):
    sys.exit('  ! 10%%p 기준에서 더해지는 것이 심은 두 항목이 아닙니다 : %s' % sorted((set(hit10) - set(hit)) ^ set(PLANTED10)))
near = sorted((spent.get((r['프로젝트'], r['계정']), 0) / int(r['연간예산']) * 100, r['프로젝트'], r['계정']) for r in b
              if (r['프로젝트'], r['계정']) not in PLANTED and (r['프로젝트'], r['계정']) not in PLANTED10)
print('  . 나머지 항목 집행률 %.1f%% ~ %.1f%%' % (near[0][0], near[-1][0]))
