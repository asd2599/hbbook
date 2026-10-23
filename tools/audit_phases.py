# -*- coding: utf-8 -*-
"""감사실 M4 — 완성본(app.html)에서 Phase 2 · 3 단계별 스냅샷을 만든다.

    python tools/audit_phases.py

Phase 4 에서 다듬는 것(색 · 글씨 · 빈 화면 안내)을 걷어 내고,
Phase 2 는 AI 도우미까지 걷어 낸다. 결과는 감사실_완성본/단계별/ 에 쌓인다.
강사가 실습 중 막힌 교육생에게 그 단계 파일을 건네는 대체 경로로도 쓴다.
"""
import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'assets/실습자료/감사실_완성본/app.html'
OUT = ROOT / 'assets/실습자료/감사실_완성본/단계별'

PLAIN = """
  /* ---- Phase 4 전 — 아직 다듬지 않은 모습 ---- */
  header { background: #fff; color: var(--ink); border-bottom: 1px solid var(--line); }
  header .sub { display: none; }
  #pickBtn { background: var(--navy); color: #fff; }
  .kpi.is-alert { background: #fff; border-color: var(--line); }
  .bar .fill { background: #b8c0cc; }
  .empty { min-height: 180px; border-style: solid; border-width: 1px; }
"""
SIMPLE_EMPTY = """    <section class="empty" id="empty">
      <p class="hint">CSV 파일을 선택하세요</p>
      <button class="btn btn--navy" id="pickBtn2">파일 선택</button>
    </section>"""

def phase3(src):
    s = src.replace('</style>', PLAIN + '</style>', 1)
    s = re.sub(r'    <section class="empty" id="empty">.*?</section>', SIMPLE_EMPTY, s, count=1, flags=re.S)
    return s.replace('<title>법인카드 이상징후 대시보드</title>', '<title>법인카드 이상징후 대시보드 (Phase 3)</title>')

def phase2(src):
    s = phase3(src).replace('(Phase 3)', '(Phase 2)')
    s = re.sub(r'  <!-- AI 점검 도우미 -->\s*<aside class="ai">.*?</aside>\n', '', s, count=1, flags=re.S)
    s = re.sub(r'// ---- AI \(server\.js.*?(?=// ---- 이벤트)', 'function updateAiButtons() {}\n\n', s, count=1, flags=re.S)
    s = s.replace('grid-template-columns: minmax(0, 1fr) 390px;', 'grid-template-columns: minmax(0, 1fr);')
    s = s.replace("chat = [];\n  $('summary').innerHTML = '<span class=\"muted\">CSV를 올리고 연결하면 누를 수 있습니다</span>';\n  $('chatlog').innerHTML = '<div class=\"muted\">예) 주말에 쓴 건은 누가 썼어? · 구매팀은 왜 많이 걸렸어?</div>'; render(); };",
                  "render(); };")
    s = s.replace("오른쪽에 API 키를 넣으면 AI가 걸린 건을 <b>요약</b>하고 <b>질문</b>에 답합니다", "")
    return s

src = SRC.read_text(encoding='utf-8')
OUT.mkdir(parents=True, exist_ok=True)
for name, fn in (('phase2.html', phase2), ('phase3.html', phase3)):
    (OUT / name).write_text(fn(src), encoding='utf-8')
    print('  +', name)
