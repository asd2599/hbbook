# -*- coding: utf-8 -*-
"""뉴스 분석 M4 — 완성본(app.html)에서 Phase 2 · 3 단계별 스냅샷을 만든다.

    python tools/news_phases.py

Phase 4 에서 하는 것(보고서 출력 · 색 · 글씨 · 빈 화면 안내)을 걷어 내고,
Phase 2 는 AI 분석 칸까지 걷어 낸다. 결과는 뉴스분석_완성본/단계별/ 에 쌓인다.
강사가 실습 중 막힌 교육생에게 그 단계 파일을 건네는 대체 경로로도 쓴다.
"""
import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'assets/실습자료/뉴스분석_완성본/app.html'
OUT = ROOT / 'assets/실습자료/뉴스분석_완성본/단계별'

PLAIN = """
  /* ---- Phase 4 전 — 아직 다듬지 않은 모습 ---- */
  header { background: #fff; color: var(--ink); border-bottom: 1px solid var(--line); }
  header .sub { display: none; }
  .searchrow input { border-width: 1px; border-color: var(--line); }
  .kpi.is-key { background: #fff; border-color: var(--line); }
  .kpi.is-key .v { color: var(--ink); }
  .empty { min-height: 180px; border-style: solid; border-width: 1px; }
"""
SIMPLE_EMPTY = """    <section class="empty" id="empty">
      <p class="hint">키워드를 넣고 검색하세요</p>
    </section>"""


def sub1(pattern, repl, s):
    s2, n = re.subn(pattern, repl, s, count=1, flags=re.S)
    assert n == 1, pattern[:60]
    return s2


def phase3(src):
    s = src.replace('</style>', PLAIN + '</style>', 1)
    s = sub1(r'    <section class="empty" id="empty">.*?</section>', SIMPLE_EMPTY, s)
    s = sub1(r'      <p class="search-note">.*?</p>\n', '', s)
    s = sub1(r'\s*<button class="btn btn--ghost" id="reportBtn".*?<!-- 보고서 버튼 -->', '', s)
    s = sub1(r'// ---- 보고서 출력.*?(?=// ---- 이벤트)', 'function updateReportBtn() {}\n\n', s)
    s = s.replace(' [번호]를 누르면 그 기사가 열립니다.', '')
    return s.replace('<title>뉴스 동향 분석 리포트</title>', '<title>뉴스 동향 분석 리포트 (Phase 3)</title>')


def phase2(src):
    s = phase3(src).replace('(Phase 3)', '(Phase 2)')
    s = sub1(r'  <!-- AI 분석 도우미 -->\s*<aside class="ai">.*?</aside>\n', '', s)
    s = sub1(r'// ---- AI \(server\.js.*?(?=function updateReportBtn)', 'function updateAiButtons() {}\nfunction resetAi() {}\n', s)
    return s.replace('grid-template-columns: minmax(0, 1fr) 390px;', 'grid-template-columns: minmax(0, 1fr);')


src = SRC.read_text(encoding='utf-8')
OUT.mkdir(parents=True, exist_ok=True)
for name, fn in (('phase2.html', phase2), ('phase3.html', phase3)):
    (OUT / name).write_text(fn(src), encoding='utf-8')
    print('  +', name)
