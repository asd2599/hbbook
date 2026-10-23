# -*- coding: utf-8 -*-
"""보안 심의 진행 현황판 M4 — 실습용 가짜 심의 요청 CSV 3개(절차마다 Jira 프로젝트 하나)를 만들고, 심의기준대로 걸리는지 검증한다.

    python tools/review_data.py

시드를 고정해 몇 번을 돌려도 같은 파일이 나온다. 요청번호 · 부서 · 제목 · 날짜 · 코멘트는 모두 교육용으로 지어낸 것이다.
한 줄이 요청 한 건이다 — Jira 에서 내려받은 모양으로 요청번호 · 절차 · 기술분야 · 요청부서 · 요청제목 · 접수일 · 현재단계 ·
최근갱신일 · 완료일 · 최근 코멘트가 있다. 자료를 뽑은 날(기준일)은 2026-09-30 이다.

심의기준.md 의 두 기준(진행 중인데 경과일이 처리기한을 넘김 · 진행 중인데 최근갱신 뒤 14일 이상 멈춤)에
PLANTED 의 여섯 건만 걸려야 한다 — 끝에서 확인하고, 어긋나면 멈춘다.
멈춤 기준을 14일에서 7일로 줄이면 여덟 건이 걸린다(기준 한 줄 바꾸기 실습 — PLANTED7 의 두 건이 더해진다).
"""
import csv, datetime as dt, random, pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / '심의현황판'
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(20261019)

BASE = dt.date(2026, 9, 30)          # 기준일 — 자료를 뽑은 날
START = dt.date(2026, 7, 1)
SR, TP, GA = '보안성검토', '기술보호 사내심의', '정부 승인 신청'
LIMIT = {SR: 14, TP: 30, GA: 45}     # 처리기한(일)
KEY = {SR: 'SR', TP: 'TP', GA: 'GA'}
FILE = {SR: '심의요청_보안성검토.csv', TP: '심의요청_기술보호심의.csv', GA: '심의요청_정부승인.csv'}
FIELDS = ['전동화', '자율주행', '커넥티비티', '파워트레인', '차체·소재']
DEPT = {'전동화': ['전동화개발팀', '배터리설계팀'], '자율주행': ['자율주행SW팀', '센서융합팀'],
        '커넥티비티': ['커넥티드서비스팀', '차량네트워크팀'], '파워트레인': ['파워트레인설계팀', '변속기개발팀'],
        '차체·소재': ['차체설계팀', '소재개발팀']}

# 절차마다 접수 건수(월별)와 분야 비중
COUNT = {SR: [18, 20, 27], TP: [14, 15, 15], GA: [6, 7, 7]}   # 9월 보안성검토가 늘었다 (외부 클라우드 · SaaS 도입 요청)
WEIGHT = {SR: [3, 3, 4, 2, 2], TP: [3, 4, 2, 2, 2], GA: [4, 2, 1, 2, 1]}
# 완료 건의 소요일 범위 — 가끔 기한을 넘겨 끝난 건도 있다 (지난 일이라 주의에는 걸리지 않는다)
DUR = {SR: (5, 13, .10, 15, 19), TP: (15, 28, .15, 31, 38), GA: (24, 43, .12, 46, 54)}

TITLE = {
    SR: ['{f} 협업툴 외부 SaaS 도입', '협력사 원격접속 계정 발급', '{f} 시험 데이터 클라우드 저장소 사용', '개발 서버 외부망 연결',
         '{f} 모바일 앱 외부 API 연동', '외부 메신저 업무 사용 신청', '{f} 분석 도구 클라우드 버전 도입'],
    TP: ['{f} 설계 자료 협력사 제공', '{f} 공동개발 자료 해외 연구소 공유', '{f} 학회 발표 자료 사전 심의', '{f} 산학과제 결과물 외부 공개',
         '{f} 시험 성적서 고객사 제공'],
    GA: ['{f} 기술 해외 이전 승인 신청', '{f} 기술자료 해외법인 제공 신고', '{f} 정부 과제 결과 수출 승인'],
}
DONE_NOTE = ['검토 완료 — 승인', '승인 — 조건 없음', '조건부 승인 — 접속 기록 보관', '심의 통과', '승인 — 제공 범위 축소',
             '반려 — 대체 방안 안내', '승인 — 사후 점검 예정']
OPEN_NOTE = {
    '접수': ['담당자 배정 완료', '접수 확인 — 검토 예정'],
    '검토': ['검토 중', '요청부서와 범위 협의 중', '보완 자료 접수 — 검토 재개', '기술 검토 의견 취합 중'],
    '보완 요청': ['보완 자료 요청 — 이번 주 회신 예정', '보완 자료 일부 접수'],
    '심의': ['위원회 상정 예정', '심의 안건 등록 완료', '정부 검토 진행 중'],
}

# ---- 심어 두는 건 ---------------------------------------------------------------
# (절차, 분야, 접수일, 단계, 최근갱신일, 코멘트)
PLANTED = [
    (TP, '자율주행', '2026-08-14', '보완 요청', '2026-09-05', '협력사 NDA 서명본 미제출 — 요청부서에 재요청'),   # 기한 초과 · 멈춤
    (TP, '자율주행', '2026-08-20', '보완 요청', '2026-09-12', '협력사 NDA 서명본 미제출 — 회신 없음'),           # 기한 초과 · 멈춤
    (TP, '자율주행', '2026-08-27', '심의',     '2026-09-25', '위원회 심의 일정 미확정 — 10월 첫 주 예정'),       # 기한 초과
    (GA, '전동화',   '2026-08-05', '보완 요청', '2026-09-22', '정부 보완 요구 회신 대기 — 공정 자료 영문 번역 중'),  # 기한 초과
    (GA, '파워트레인', '2026-08-29', '검토',    '2026-09-10', '요청부서 담당자 변경 — 인수인계 후 회신 예정'),       # 멈춤 (기한 안)
    (SR, '커넥티비티', '2026-09-08', '검토',    '2026-09-26', '외부 클라우드 계약서 보안 조항 검토 중'),           # 기한 초과
]
PLANTED7 = [   # 멈춤 기준을 7일로 줄이면 더해지는 두 건
    (TP, '전동화',   '2026-09-10', '보완 요청', '2026-09-20', '심의 자료 보완 요청 — 회신 대기'),
    (SR, '자율주행', '2026-09-22', '접수',     '2026-09-22', '담당자 배정 대기'),
]
D = dt.date.fromisoformat


def month_days(m):
    first = dt.date(2026, m, 1)
    nxt = dt.date(2026, m + 1, 1) if m < 12 else dt.date(2027, 1, 1)
    return [first + dt.timedelta(d) for d in range((nxt - first).days)]


def stage_of(proc, frac):
    stages = ['접수', '검토', '보완 요청'] + (['심의'] if proc != SR else [])
    return stages[min(len(stages) - 1, int(frac * len(stages)))]


rows = {p: [] for p in LIMIT}
for proc in LIMIT:
    for mi, m in enumerate((7, 8, 9)):
        days = month_days(m)
        for _ in range(COUNT[proc][mi]):
            f = rnd.choices(FIELDS, WEIGHT[proc])[0]
            recv = rnd.choice(days)
            lo, hi, over_p, olo, ohi = DUR[proc]
            dur = rnd.randint(olo, ohi) if rnd.random() < over_p else rnd.randint(lo, hi)
            if proc == TP and f == '자율주행':
                dur = min(dur + 5, 38)                 # 자율주행 기술보호 심의는 끝난 건도 오래 걸렸다
            row = dict(절차=proc, 기술분야=f, 요청부서=rnd.choice(DEPT[f]), 요청제목=rnd.choice(TITLE[proc]).format(f=f), 접수일=recv)
            elapsed = (BASE - recv).days
            if recv + dt.timedelta(dur) <= BASE or elapsed > LIMIT[proc]:
                # 끝난 건 — 진행 중으로 두면 기한을 넘길 건은 기준일 무렵 끝난 것으로 둔다 (심은 건 말고는 걸리지 않게)
                end = recv + dt.timedelta(dur) if recv + dt.timedelta(dur) <= BASE else BASE - dt.timedelta(rnd.randint(0, 4))
                row.update(현재단계='완료', 최근갱신일=end, 완료일=end, 최근코멘트=rnd.choice(DONE_NOTE))
            else:
                st = stage_of(proc, elapsed / dur)
                upd = BASE - dt.timedelta(min(elapsed, rnd.randint(0, 6)))      # 최근 6일 안에 움직였다
                row.update(현재단계=st, 최근갱신일=upd, 완료일='', 최근코멘트=rnd.choice(OPEN_NOTE[st]))
            rows[proc].append(row)
    for p in (PLANTED + PLANTED7):
        if p[0] != proc:
            continue
        rows[proc].append(dict(절차=proc, 기술분야=p[1], 요청부서=rnd.choice(DEPT[p[1]]), 요청제목=rnd.choice(TITLE[proc]).format(f=p[1]),
                               접수일=D(p[2]), 현재단계=p[3], 최근갱신일=D(p[4]), 완료일='', 최근코멘트=p[5]))

HEAD = ['요청번호', '절차', '기술분야', '요청부서', '요청제목', '접수일', '현재단계', '최근갱신일', '완료일', '최근 코멘트']
START_NO = {SR: 1201, TP: 341, GA: 87}
for f in OUT.glob('심의요청_*.csv'):
    f.unlink()
for proc, rs in rows.items():
    rs.sort(key=lambda r: (r['접수일'], r['기술분야']))
    with (OUT / FILE[proc]).open('w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp, lineterminator='\r\n')
        w.writerow(HEAD)
        for i, r in enumerate(rs):
            w.writerow(['%s-%04d' % (KEY[proc], START_NO[proc] + i), r['절차'], r['기술분야'], r['요청부서'], r['요청제목'],
                        r['접수일'].isoformat(), r['현재단계'], r['최근갱신일'].isoformat(),
                        r['완료일'].isoformat() if r['완료일'] else '', r['최근코멘트']])
    print('  +', FILE[proc], len(rs), '건')


# ---- 검증 — 심의기준.md 를 그대로 적용해 본다 ----------------------------------
def load():
    out = []
    for f in sorted(OUT.glob('심의요청_*.csv')):
        out += list(csv.DictReader(f.open(encoding='utf-8-sig')))
    return out


def check(stall=14):
    hit = {}
    for r in load():
        if r['완료일']:
            continue
        el = (BASE - D(r['접수일'])).days
        st = (BASE - D(r['최근갱신일'])).days
        why = []
        if el > LIMIT[r['절차']]:
            why.append('기한 초과')
        if st >= stall:
            why.append('%d일 이상 멈춤' % stall)
        if why:
            hit[r['요청번호']] = (r['절차'], r['기술분야'], el, LIMIT[r['절차']], st, why, r['최근 코멘트'])
    return hit


all_ = load()
done = [r for r in all_ if r['완료일']]
openr = [r for r in all_ if not r['완료일']]
print('  = 요청 %d건 · 완료 %d · 진행 중 %d · 완료율 %.1f%%' % (len(all_), len(done), len(openr), len(done) / len(all_) * 100))
for proc in LIMIT:
    ds = [(D(r['완료일']) - D(r['접수일'])).days for r in done if r['절차'] == proc]
    n = sum(1 for r in all_ if r['절차'] == proc)
    print('    %-10s 접수 %3d · 완료 %3d · 평균 소요 %.1f일 (기한 %d일) · 기한 내 %.1f%%' % (
        proc, n, len(ds), sum(ds) / len(ds), LIMIT[proc], sum(1 for x in ds if x <= LIMIT[proc]) / len(ds) * 100))
for f in FIELDS:
    ds = [(D(r['완료일']) - D(r['접수일'])).days for r in done if r['절차'] == TP and r['기술분야'] == f]
    print('    기술보호 · %-6s 완료 %d · 평균 소요 %.1f일' % (f, len(ds), sum(ds) / max(1, len(ds))))
for m in ('07', '08', '09'):
    print('    2026-%s 접수 %d' % (m, sum(1 for r in all_ if r['접수일'][5:7] == m)))
hit = check()
print('  = 걸린 건 %d' % len(hit))
for k, v in sorted(hit.items()):
    print('    %s %s %s  경과 %d일/기한 %d일  멈춤 %d일  %s  — %s' % (k, v[0], v[1], v[2], v[3], v[4], ' · '.join(v[5]), v[6]))
want = {(p[0], p[1], p[2]) for p in PLANTED}
got = {(v[0], v[1], next(r['접수일'] for r in all_ if r['요청번호'] == k)) for k, v in hit.items()}
if got != want:
    sys.exit('  ! 심은 여섯 건과 걸린 것이 다릅니다 : %s' % sorted(got ^ want))
hit7 = check(stall=7)
print('  = 멈춤 기준을 7일로 줄이면 %d건 : %s' % (len(hit7), sorted(set(hit7) - set(hit))))
want7 = {(p[0], p[1], p[2]) for p in PLANTED7}
got7 = {(hit7[k][0], hit7[k][1], next(r['접수일'] for r in all_ if r['요청번호'] == k)) for k in set(hit7) - set(hit)}
if got7 != want7:
    sys.exit('  ! 7일 기준에서 더해지는 것이 심은 두 건이 아닙니다 : %s' % sorted(got7 ^ want7))
