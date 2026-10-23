# -*- coding: utf-8 -*-
"""보안 심의 진행 현황판 M4 — 완성본(app.html)에서 Phase 2 · 3 단계별 스냅샷을 만든다.

    python tools/review_phases.py

Phase 4 에서 하는 것(현황 보고서 · 통합 요청표 내려받기 · 색 · 빈 화면 안내)을 걷어 내고,
Phase 2 는 AI 도우미까지 걷어 낸다. 결과는 심의현황판_완성본/단계별/ 에 쌓인다.
강사가 실습 중 막힌 교육생에게 그 단계 파일을 건네는 대체 경로로도 쓴다.
"""
import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'assets/실습자료/심의현황판_완성본/app.html'
OUT = ROOT / 'assets/실습자료/심의현황판_완성본/단계별'

PLAIN = """
  /* ---- Phase 4 전 — 아직 다듬지 않은 모습 ---- */
  header { background: #fff; color: var(--ink); border-bottom: 1px solid var(--line); }
  header .sub { display: none; }
  #pickBtn { background: var(--navy); color: #fff; }
  .kpi.is-alert { background: #fff; border-color: var(--line); }
  .empty { min-height: 180px; border-style: solid; border-width: 1px; }
"""
SIMPLE_EMPTY = """    <section class="empty" id="empty">
      <p class="hint">CSV 파일을 선택하세요</p>
      <button class="btn btn--navy" id="pickBtn2">파일 선택</button>
    </section>"""


def sub1(pattern, repl, s):
    s2, n = re.subn(pattern, repl, s, count=1, flags=re.S)
    assert n == 1, pattern[:60]
    return s2


def phase3(src):
    s = src.replace('</style>', PLAIN + '</style>', 1)
    s = sub1(r'    <section class="empty" id="empty">.*?</section>', SIMPLE_EMPTY, s)
    s = sub1(r'\s*<button class="btn btn--ghost" id="csvBtn".*?<!-- 통합표 -->', '', s)
    s = sub1(r'\s*<button class="btn btn--ghost" id="reportBtn".*?<!-- 보고서 버튼 -->', '', s)
    s = sub1(r'// ---- 현황 보고서 · 통합표.*?(?=// ---- 이벤트)', 'function updateReportBtn() {}\n\n', s)
    return s.replace('<title>보안 심의 진행 현황판</title>', '<title>보안 심의 진행 현황판 (Phase 3)</title>')


def phase2(src):
    s = phase3(src).replace('(Phase 3)', '(Phase 2)')
    s = sub1(r'  <!-- AI 심의 도우미 -->\s*<aside class="ai">.*?</aside>\n', '', s)
    s = sub1(r'// ---- AI \(server\.js.*?(?=function updateReportBtn)', 'function updateAiButtons() {}\n', s)
    s = s.replace('grid-template-columns: minmax(0, 1fr) 390px;', 'grid-template-columns: minmax(0, 1fr);')
    s = sub1(r"  \$\('summary'\)\.innerHTML = .*?render\(\); \};", 'render(); };', s)
    return s


src = SRC.read_text(encoding='utf-8')
OUT.mkdir(parents=True, exist_ok=True)
for name, fn in (('phase2.html', phase2), ('phase3.html', phase3)):
    (OUT / name).write_text(fn(src), encoding='utf-8')
    print('  +', name)
