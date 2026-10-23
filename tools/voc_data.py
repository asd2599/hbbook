# -*- coding: utf-8 -*-
"""고객 VOC 현황판 M4 — 실습용 가짜 VOC 접수 CSV 4개(9월 1~4주, 주마다 하나)를 만들고, VOC기준대로 걸리는지 검증한다.

    python tools/voc_data.py

시드를 고정해 몇 번을 돌려도 같은 파일이 나온다. 접수번호 · 고객명 · 문의 원문은 모두 교육용으로 지어낸 것이고,
차종 이름만 현대자동차 국내 판매 차종에서 빌렸다. 고객명은 처음부터 가려 둔 모양(김*수)이다.
한 줄이 문의 한 건이다 — 접수번호 · 접수일 · 채널 · 차종 · 유형 · 고객명 · 처리상태 · 고객 문의.
주는 1~7일 · 8~14일 · 15~21일 · 22~28일로 나누고, 자료를 뽑은 날(기준일)은 2026-09-28 이다.

VOC기준.md 의 두 기준 —
  급증 : 이번 주(4주) 10건 이상이면서 전주보다 50% 이상 늘어난 차종 × 유형
  지연 : 처리 중인데 접수 후 7일 이상 지난 문의
에 SURGE 의 두 곳 · DELAY 의 네 건만 걸려야 한다 — 끝에서 확인하고, 어긋나면 멈춘다.
급증 기준을 50% 에서 30% 로 낮추면 한 곳(그랜저 · 판매·계약)이 더해진다(기준 한 줄 바꾸기 실습).
"""
import csv, datetime as dt, random, pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / 'VOC현황판'
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(20261020)

BASE = dt.date(2026, 9, 28)
WEEKS = [(dt.date(2026, 9, 1 + 7 * i), dt.date(2026, 9, 7 + 7 * i)) for i in range(4)]
CARS = ['캐스퍼', '아반떼', '쏘나타', '그랜저', '코나', '투싼', '싼타페', '팰리세이드', '아이오닉 5']
CAR_W = [.7, 1.3, .9, 1.2, .8, 1.1, 1.0, .9, 1.0]
QUAL, SERV, SPEC, SALE = '품질', '서비스', '사양 문의', '판매·계약'
TYPES = [QUAL, SERV, SPEC, SALE]
TYPE_W = {QUAL: 3.2, SERV: 2.6, SPEC: 3.6, SALE: 2.4}       # 주당 차종 하나의 평균 건수
CHANNELS = ['콜센터', '홈페이지', '앱', '지점']
CH_W = [5, 3, 3, 1]
SURNAME = '김이박최정강조윤장임한오서신권황안송류홍'
GIVEN = '수진민현영준서지우호은경성훈희연아철'

# ---- 심어 두는 것 ---------------------------------------------------------------
FIXED = {   # (차종, 유형): 1~4주 건수
    ('투싼', QUAL):      [5, 6, 8, 18],    # 급증 +125% — 9월 소프트웨어 업데이트 뒤 화면 멈춤 · 블루투스 끊김
    ('아이오닉 5', SERV): [5, 6, 7, 12],    # 급증 +71%  — EV 정비 예약이 밀림
    ('그랜저', SALE):     [7, 8, 9, 13],    # +44% — 50% 기준에서는 정상, 30% 로 낮추면 걸림 (출고 지연)
    ('쏘나타', QUAL):     [3, 3, 4, 8],     # +100% 지만 10건이 안 돼 빠진다 — 「주의 ≠ 늘어난 곳」
}
SURGE = {('투싼', QUAL), ('아이오닉 5', SERV)}
SURGE30 = {('그랜저', SALE)}
DELAY = [   # 처리 중으로 남은 지난주 문의 — (차종, 유형, 접수일, 채널, 문의)
    ('팰리세이드', SERV, '2026-09-15', '콜센터', '수리 후에도 같은 소음이 계속 납니다. 재입고 일정을 아직 못 받았습니다'),
    ('투싼', QUAL, '2026-09-17', '앱', '주행 중 계기판 화면이 꺼졌다 켜집니다. 점검 예약을 했는데 연락이 없습니다'),
    ('투싼', QUAL, '2026-09-19', '콜센터', '블루투스 연결이 자꾸 끊깁니다. 원인 확인을 요청드렸는데 답이 없습니다'),
    ('코나', QUAL, '2026-09-20', '홈페이지', '후방 카메라 화면이 가끔 안 나옵니다. 지난주 문의했는데 처리가 안 됐습니다'),
]

# ---- 문의 원문 ------------------------------------------------------------------
TEXT = {
    QUAL: ['{c} 주행 중 하부에서 소음이 납니다', '{c} 에어컨을 켜면 냄새가 심합니다', '{c} 트렁크가 가끔 안 열립니다',
           '{c} 타이어 공기압 경고등이 자주 뜹니다', '{c} 와이퍼 작동이 불규칙합니다', '{c} 창문을 올릴 때 덜컹거리는 소리가 납니다',
           '{c} 경고등이 하나 켜졌는데 무슨 뜻인지 궁금합니다', '{c} 시동을 걸 때 떨림이 있습니다',
           '{c} 리콜 대상인지 확인하고 싶습니다', '{c} 정기 점검 주기가 궁금합니다', '{c} 무상 보증 기간이 언제까지인지 문의합니다'],
    SERV: ['서비스센터 예약이 너무 늦게 잡힙니다', '수리 후 같은 증상이 다시 생겼습니다', '상담 연결이 오래 걸렸습니다',
           '상담사분이 친절하게 안내해 주셨습니다', '수리를 빠르게 해 주셔서 감사합니다', '정비 비용 안내가 달라 불편했습니다',
           '블루핸즈 위치와 영업시간을 알고 싶습니다', '픽업 서비스가 편리해서 만족합니다'],
    SPEC: ['{c} 하이브리드 모델 연비가 궁금합니다', '{c} 트림별 옵션 차이를 알고 싶습니다', '{c} 루프랙 장착이 가능한지 문의합니다',
           '{c} 실내 공간과 트렁크 크기가 궁금합니다', '{c} 내비게이션 업데이트 방법을 알려주세요', '{c} 원격 시동 기능이 있는지 궁금합니다',
           '{c} 시승 신청 방법을 알고 싶습니다'],
    SALE: ['{c} 출고 일정이 궁금합니다', '계약 후 색상 변경이 가능한지 문의합니다', '{c} 이번 달 구매 혜택이 궁금합니다',
           '카마스터분 안내가 자세해서 좋았습니다', '{c} 계약금 환불 절차를 알고 싶습니다', '{c} 출고가 예정보다 늦어지고 있습니다'],
}
PLANT_TEXT = {
    ('투싼', QUAL, 3): ['9월 소프트웨어 업데이트 뒤로 내비게이션 화면이 멈춥니다', '업데이트 후 블루투스가 자주 끊깁니다',
                       '업데이트를 받은 뒤 화면이 갑자기 재부팅됩니다', '업데이트 이후 휴대폰 연결이 안 됩니다',
                       '무선 업데이트 후 화면이 검게 멈췄다 돌아옵니다', '업데이트 뒤로 음악이 끊기고 화면이 먹통입니다',
                       '내비 업데이트 후 터치가 안 먹힙니다', '업데이트하고 나서 블루투스 통화가 끊깁니다',
                       '업데이트 후 후방 카메라 화면이 늦게 뜹니다', '9월 업데이트 받은 뒤 화면 멈춤이 잦습니다',
                       '업데이트 후 계기판과 화면이 같이 꺼졌다 켜집니다'],
    ('아이오닉 5', SERV, 3): ['EV 전문 정비 예약이 2주 넘게 밀려 있습니다', '가까운 서비스센터에서 전기차 정비가 안 된다고 합니다',
                            '배터리 점검 예약을 잡기가 너무 어렵습니다', 'EV 정비 대기가 길어 차를 못 쓰고 있습니다',
                            '전기차 수리 가능한 곳을 찾느라 세 군데에 전화했습니다', '충전구 수리 예약이 다음 달로 잡혔습니다'],
    ('그랜저', SALE, 3): ['그랜저 출고가 또 미뤄졌다는 연락을 받았습니다', '그랜저 계약했는데 출고 일정을 아무도 모릅니다',
                        '그랜저 하이브리드 출고가 두 달째 지연 중입니다', '그랜저 출고 지연 보상이 있는지 궁금합니다'],
}


def week_of(d):
    return next(i for i, (a, b) in enumerate(WEEKS) if a <= d <= b)


counts = {}
for car, cw in zip(CARS, CAR_W):
    for t in TYPES:
        base = cw * TYPE_W[t]
        counts[(car, t)] = FIXED.get((car, t)) or [max(0, int(round(base + rnd.uniform(-1.2, 1.2)))) for _ in WEEKS]

rows = []
for (car, t), cs in counts.items():
    for wi, n in enumerate(cs):
        a, b = WEEKS[wi]
        planted = list(PLANT_TEXT.get((car, t, wi), []))
        rnd.shuffle(planted)
        for k in range(n):
            d = a + dt.timedelta(rnd.randint(0, 6))
            text = planted.pop() if planted else rnd.choice(TEXT[t]).format(c=car)
            done = wi < 3 or rnd.random() < .6
            rows.append(dict(d=d, ch=rnd.choices(CHANNELS, CH_W)[0], car=car, type=t, text=text,
                             st='완료' if done else '처리 중'))
for car, t, d, ch, text in DELAY:
    rows.append(dict(d=dt.date.fromisoformat(d), ch=ch, car=car, type=t, text=text, st='처리 중'))
    counts[(car, t)][week_of(dt.date.fromisoformat(d))] += 1

rows.sort(key=lambda r: (r['d'], CARS.index(r['car']), TYPES.index(r['type'])))
HEAD = ['접수번호', '접수일', '채널', '차종', '유형', '고객명', '처리상태', '고객 문의']
for f in OUT.glob('VOC_*.csv'):
    f.unlink()
by_week = [[] for _ in WEEKS]
for i, r in enumerate(rows, 1):
    by_week[week_of(r['d'])].append(['VOC-%04d' % (2600 + i), r['d'].isoformat(), r['ch'], r['car'], r['type'],
                                     rnd.choice(SURNAME) + '*' + rnd.choice(GIVEN), r['st'], r['text']])
for wi, rs in enumerate(by_week):
    f = OUT / ('VOC_9월%d주.csv' % (wi + 1))
    with f.open('w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp, lineterminator='\r\n')
        w.writerow(HEAD)
        w.writerows(rs)
    print('  +', f.name, len(rs), '건')


# ---- 검증 — VOC기준.md 를 그대로 적용해 본다 ------------------------------------
def load():
    out = []
    for f in sorted(OUT.glob('VOC_*.csv')):
        out += list(csv.DictReader(f.open(encoding='utf-8-sig')))
    return out


def check(rise=50, least=10, late=7):
    data = load()
    cnt = {}
    for r in data:
        w = week_of(dt.date.fromisoformat(r['접수일']))
        cnt.setdefault((r['차종'], r['유형']), [0] * 4)[w] += 1
    surge = {k: v for k, v in cnt.items() if v[3] >= least and v[2] and (v[3] - v[2]) / v[2] * 100 >= rise}
    delay = [r for r in data if r['처리상태'] == '처리 중' and (BASE - dt.date.fromisoformat(r['접수일'])).days >= late]
    return data, cnt, surge, delay


data, cnt, surge, delay = check()
wk = [sum(v[i] for v in cnt.values()) for i in range(4)]
print('  = 문의 %d건 · 주별 %s · 이번 주 처리 중 %d' % (len(data), wk, sum(1 for r in data if r['처리상태'] == '처리 중')))
for k in sorted(cnt, key=lambda k: -cnt[k][3])[:8]:
    v = cnt[k]
    print('    %-6s %-6s %s  전주 대비 %+.0f%%' % (k[0], k[1], v, (v[3] - v[2]) / v[2] * 100 if v[2] else 0))
print('  = 급증 %d곳 : %s' % (len(surge), sorted(surge)))
print('  = 지연 %d건 : %s' % (len(delay), [(r['접수번호'], r['차종'], r['유형'], r['접수일']) for r in delay]))
if set(surge) != SURGE:
    sys.exit('  ! 심은 급증 두 곳과 걸린 것이 다릅니다 : %s' % sorted(set(surge) ^ SURGE))
if sorted((r['차종'], r['접수일']) for r in delay) != sorted((d[0], d[2]) for d in DELAY):
    sys.exit('  ! 심은 지연 네 건과 걸린 것이 다릅니다')
s30 = check(rise=30)[2]
print('  = 급증 기준을 30%% 로 낮추면 %d곳 : 더해지는 것 %s' % (len(s30), sorted(set(s30) - set(surge))))
if set(s30) - set(surge) != SURGE30:
    sys.exit('  ! 30% 기준에서 더해지는 것이 그랜저 · 판매·계약 하나가 아닙니다')
