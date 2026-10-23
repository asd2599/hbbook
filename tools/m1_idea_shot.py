"""M1 아이디어 기획서 실습 — 완성본 예시 그림(assets/img/m1-idea-done.png)을 만든다.

H Chat 이 Worksheet 양식대로 채워 준 기획서 HTML 을 흉내 낸 가짜 예시다.
내용은 지어낸 것이고, 이름 칸은 마스킹(M1 14p)에 맞춰 ○○○ 로 둔다.
고친 뒤에는 python tools/m1_idea_shot.py → python tools/build-single.py.
"""
import pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'img' / 'm1-idea-done.png'

ROWS = [
    ('01', '문제 정의',
     '『교육 만족도 설문 결과 정리』를 매 『차수』마다 하는 데 『120분』이 걸린다 &mdash; 응답을 엑셀로 옮기고 평균과 코멘트를 손으로 모은다.'),
    ('02', 'AI 활용 방식',
     '설문 CSV 를 넣으면 AI 가 차수별 평균을 계산하고 낮은 점수 코멘트를 묶어, 한 화면 대시보드로 보여 주게 한다.'),
    ('03', '기대 결과물',
     '결과물 1종 &mdash; 교육 만족도 대시보드(웹 화면 한 장) &middot; 시간 절감 약 100분 (120분 &rarr; 20분)'),
    ('04', '검증 방법',
     '첫 3개 차수는 손으로 낸 평균과 AI 결과를 맞춰 보고, 보고 전에 팀장이 코멘트 요약을 직접 검토한다(사람 검토).'),
]

HTML = '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
body{margin:0;font-family:"Malgun Gothic","Pretendard",sans-serif;background:#F7F8FA;color:#1A1A1A}
.top{background:#164194;color:#fff;padding:22px 34px;font-size:30px;font-weight:700;letter-spacing:-.02em}
.top small{font-size:24px;font-weight:600;opacity:.9}
.who{display:flex;gap:40px;padding:18px 34px 10px;font-size:19px;color:#164194;font-weight:700;border-bottom:1px solid #D8DEE9;margin:0 20px}
.who span b{color:#1A1A1A;font-weight:600;margin-left:8px}
.row{display:flex;gap:18px;padding:16px 34px 10px;align-items:flex-start}
.no{font-size:34px;font-weight:800;color:#164194;width:52px;line-height:1}
.t{font-size:20px;font-weight:700;margin:2px 0 8px}
.v{font-size:17px;line-height:1.6;background:#fff;border:1px solid #D8DEE9;border-left:5px solid #70AD47;border-radius:6px;padding:10px 14px}
</style></head><body>
<div class="top">M5. 나만의 업무 혁신 PoC_<small>아이디어기획서 Worksheet</small></div>
<div class="who"><span>본부 :<b>경영지원본부</b></span><span>팀 :<b>인사팀</b></span><span>이름 :<b>○○○</b></span></div>
''' + ''.join('<div class="row"><div class="no">%s</div><div style="flex:1"><p class="t">%s</p><div class="v">%s</div></div></div>' % r for r in ROWS) + '''
</body></html>'''

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 960, 'height': 640}, device_scale_factor=1.5)
    pg.set_content(HTML)
    h = pg.evaluate('document.body.scrollHeight')
    pg.set_viewport_size({'width': 960, 'height': h})
    pg.screenshot(path=str(OUT), full_page=True)
    b.close()
print('saved', OUT)
