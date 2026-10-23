# -*- coding: utf-8 -*-
"""교육 만족도 현황판 M4 — 실습용 가짜 교육 설문 CSV 6개(2과정 × 3차수)를 만들고, 교육기준대로 걸리는지 검증한다.

    python tools/hrd_data.py

시드를 고정해 몇 번을 돌려도 같은 파일이 나온다. 과정 · 소속 · 점수 · 코멘트는 모두 교육용으로 지어낸 것이다.
한 줄이 응답자 한 명이고, 점수 네 개(만족도 · 이해도 · 추천도 · 현업적용도, 10점 만점)와 코멘트 두 칸이 있다.
차수마다 만족도 분포(HIST)를 정해 두고 섞는다 — 평균과 7점 이하 비율이 정확히 그 값으로 나온다.

교육기준.md 의 두 기준(차수 평균 만족도 8.0점 미만 · 만족도 7점 이하 응답이 20% 이상)에
PLANTED 의 세 차수만 걸려야 한다 — 끝에서 확인하고, 어긋나면 멈춘다.
8.0 을 8.5 로 올리면 넷이 걸린다(기준 한 줄 바꾸기 실습 — 신임 팀장 리더십 3차가 더해진다).
"""
import csv, random, pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / '교육현황판'
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(20261015)

LEAD, AI = '신임 팀장 리더십', 'AI 업무 활용'
FILE = {LEAD: '신임팀장리더십', AI: 'AI업무활용'}
DEPTS = ['경영지원본부', '재무본부', '국내영업본부', '생산본부', '연구개발본부', '품질본부', '구매본부', '인사본부']

# 차수마다 만족도 분포 — {점수: 명}
HIST = {
    (LEAD, '1차'): {10: 6, 9: 9, 8: 8, 7: 1},                 # 8.83 · 7점 이하 4%
    (LEAD, '2차'): {10: 2, 9: 5, 8: 10, 7: 4, 6: 3, 5: 2},    # 7.73 · 34.6% → 두 기준 다 걸림 (롤플레이 실습이 빠졌다)
    (LEAD, '3차'): {10: 3, 9: 8, 8: 10, 7: 3, 6: 1},          # 8.36 · 16%   → 8.0 기준에서는 정상, 8.5 로 올리면 걸림
    (AI, '1차'):   {10: 1, 9: 4, 8: 18, 7: 3, 6: 2},          # 7.96 · 17.9% → 평균만 걸림 (진도가 빨랐다)
    (AI, '2차'):   {10: 5, 9: 9, 8: 12, 7: 1},                # 8.67 · 3.7%  → 1차 뒤 진도를 고쳤다
    (AI, '3차'):   {10: 9, 9: 7, 8: 3, 7: 2, 6: 2, 5: 1, 4: 1},   # 8.48 · 24% → 평균은 괜찮은데 둘로 갈림 (실습 PC 접속)
}
DATE = {(LEAD, '1차'): '2026-07-08', (LEAD, '2차'): '2026-08-12', (LEAD, '3차'): '2026-09-09',
        (AI, '1차'): '2026-07-15', (AI, '2차'): '2026-08-19', (AI, '3차'): '2026-09-16'}
PLANTED = {(LEAD, '2차'), (AI, '1차'), (AI, '3차')}

# ---- 코멘트 ------------------------------------------------------------------
GOOD = {
    LEAD: ['1:1 면담 롤플레이가 실제로 도움이 됐다', '피드백 대화 순서가 정리되어 좋았다', '다른 팀장들과 고민을 나눌 수 있었다',
           '사례 토의가 현실적이었다', '강사님이 현장 경험을 많이 들려주셨다', '팀원 유형별 대응법이 유용했다',
           '바로 써먹을 수 있는 질문 목록을 얻었다', '동기 팀장들과 네트워크가 생겼다'],
    AI: ['프롬프트 예시를 바로 써 볼 수 있었다', '내 업무에 적용할 아이디어를 얻었다', '실습 위주라 좋았다',
         '강사님 설명이 쉬웠다', '회의록 정리 실습이 유용했다', '보고서 초안 만들기가 인상적이었다',
         '반복 업무를 줄일 방법이 보였다', '질문에 하나하나 답해 주셨다'],
}
GOOD_LEAD2 = ['이론 정리가 체계적이었다', '자료가 깔끔했다', '다른 팀장들과 고민을 나눌 수 있었다', '리더십 유형 진단이 흥미로웠다']
BAD_COMMON = ['교육 시간이 조금 짧았다', '자료를 미리 받았으면 좋겠다', '쉬는 시간이 더 있었으면 한다', '교육장이 조금 추웠다',
              '교육 후 자료 공유를 부탁드린다', '다른 부서 사례도 더 듣고 싶다', '']
BAD_PLANT = {
    (LEAD, '2차'): ['롤플레이 실습이 빠지고 이론 강의만 이어졌다', '1차 후기에서 들은 면담 실습이 없어 아쉬웠다',
                   '직접 해 보는 시간이 없어 현업에 쓰기 어렵다', '강의가 일방적이라 집중이 어려웠다',
                   '사례 토의 시간이 너무 짧았다', '실습 없이 듣기만 해서 지루했다', '롤플레이를 기대했는데 없었다',
                   '이론은 책으로도 볼 수 있을 것 같다', '면담 연습을 꼭 넣어 주셨으면 한다'],
    (AI, '1차'):   ['진도가 너무 빨라 따라가기 어려웠다', '화면 전환이 빨라 놓친 부분이 많다', '기초 설명 없이 바로 실습으로 들어갔다',
                   '처음 쓰는 사람에게는 어려웠다', '따라가느라 내용을 이해할 틈이 없었다', '속도를 조금 늦춰 주셨으면 한다'],
    (AI, '3차'):   ['실습 PC 사내망 접속이 안 돼 실습 절반을 못 했다', '로그인 오류로 한참 기다렸다', '실습 PC가 느려 따라가지 못했다',
                   '접속 문제로 실습을 거의 못 했다', '옆 사람 화면을 보며 따라 했다', 'PC 문제만 없었으면 좋았을 것 같다'],
}
MID_EXTRA = {   # 7점 이하는 아니지만 같은 이야기를 하는 사람 — 코멘트에서 흐름이 보이게
    (LEAD, '2차'): ['실습이 조금 더 있었으면 한다', '토의 시간이 짧았다'],
    (AI, '1차'):   ['진도가 조금 빨랐다', '중간에 놓친 부분이 있었다'],
    (AI, '2차'):   ['진도가 적당해서 따라가기 좋았다'],      # 1차 뒤 고친 것 — 좋았던 점에 들어간다
    (AI, '3차'):   ['초반에 PC 접속 문제가 있었다'],
}


def clip(x):
    return max(1, min(10, int(round(x))))


rows_by = {}
for (course, cha), hist in HIST.items():
    scores = [s for s, n in sorted(hist.items(), reverse=True) for _ in range(n)]
    rnd.shuffle(scores)
    plant_bad = list(BAD_PLANT.get((course, cha), []))
    rnd.shuffle(plant_bad)
    mids = list(MID_EXTRA.get((course, cha), []))
    rows = []
    for i, s in enumerate(scores, 1):
        und = s + rnd.uniform(-1.0, .8)
        rec = s + rnd.uniform(-.8, .8)
        app = s + rnd.uniform(-1.2, .6)
        if (course, cha) == (AI, '1차'):
            und -= 1.0                       # 진도가 빨라 이해도가 특히 낮다
        if (course, cha) == (LEAD, '2차'):
            app -= .8                        # 실습이 빠져 현업 적용도가 낮다
        if (course, cha) == (AI, '3차') and s <= 7:
            und -= 1.0
        if (course, cha) == (LEAD, '2차'):
            good = rnd.choice(GOOD_LEAD2)
        else:
            good = rnd.choice(GOOD[course]) if rnd.random() < .85 else ''
        if s <= 7:
            bad = plant_bad.pop() if plant_bad else rnd.choice([b for b in BAD_COMMON if b])
        elif mids and s == 8 and (course, cha) != (AI, '2차'):
            bad = mids.pop()
        elif mids and (course, cha) == (AI, '2차') and s >= 9:
            good, bad = mids.pop(), rnd.choice(BAD_COMMON)
        else:
            bad = rnd.choice(BAD_COMMON) if rnd.random() < .6 else ''
        rows.append([course, cha, DATE[(course, cha)], i, rnd.choice(DEPTS), s, clip(und), clip(rec), clip(app), good, bad])
    rows_by[(course, cha)] = rows

HEAD = ['과정', '차수', '교육일', '응답번호', '소속', '만족도', '이해도', '추천도', '현업적용도', '좋았던 점', '아쉬운 점']
for f in OUT.glob('교육설문_*.csv'):
    f.unlink()
for (course, cha), rows in rows_by.items():
    f = OUT / ('교육설문_%s_%s.csv' % (FILE[course], cha))
    with f.open('w', encoding='utf-8-sig', newline='') as fp:
        w = csv.writer(fp, lineterminator='\r\n')
        w.writerow(HEAD)
        w.writerows(rows)
    print('  +', f.name, len(rows), '명')


# ---- 검증 — 교육기준.md 를 그대로 적용해 본다 ----------------------------------
def check(low_avg=8.0, low_score=7, low_share=20):
    by = {}
    for f in sorted(OUT.glob('교육설문_*.csv')):
        for r in csv.DictReader(f.open(encoding='utf-8-sig')):
            by.setdefault((r['과정'], r['차수']), []).append(int(r['만족도']))
    res = {}
    for k, v in by.items():
        avg = sum(v) / len(v)
        share = sum(1 for x in v if x <= low_score) / len(v) * 100
        res[k] = (len(v), avg, share, sum(1 for x in v if x <= low_score))
    hit = {k for k, (n, avg, share, lo) in res.items() if avg < low_avg or share >= low_share}
    return res, hit


res, hit = check()
total = sum(r[0] for r in res.values())
lows = sum(r[3] for r in res.values())
print('  = 응답 %d명 · 차수 %d · 7점 이하 %d명 · 걸린 차수 %d : %s' % (total, len(res), lows, len(hit), sorted(hit)))
for k in sorted(res):
    n, avg, share, lo = res[k]
    print('    %s %s  %d명  평균 %.2f점 (달성률 %.1f%%)  7점 이하 %d명 %.1f%%' % (k[0], k[1], n, avg, avg / 8.5 * 100, lo, share))
if hit != PLANTED:
    sys.exit('  ! 심은 셋과 걸린 것이 다릅니다 : %s' % sorted(hit ^ PLANTED))
hit85 = check(low_avg=8.5)[1]
print('  = 평균 기준을 8.5점으로 올리면 %d : %s' % (len(hit85), sorted(hit85 - hit)))
if hit85 - hit != {(LEAD, '3차')}:
    sys.exit('  ! 8.5 기준에서 더해지는 것이 신임 팀장 리더십 3차 하나가 아닙니다')
