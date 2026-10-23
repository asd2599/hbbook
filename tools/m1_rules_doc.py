# -*- coding: utf-8 -*-
"""M1 커스텀 챗봇 실습 — 리소스로 넣을 가짜 사내 규정 문서(복리후생 규정.pdf)를 만든다.

    python tools/m1_rules_doc.py

교육용으로 지어낸 규정이다 — 실제 회사 규정과 무관하다.
교안 M1 커스텀 챗봇 장의 질문 · 답 예시(경조사 휴가 5일 · 경조금 100만 원 · 서울 숙박 10만 원 ·
주차비는 규정에 없음)가 이 문서와 맞아야 한다. 고치면 교안의 대화 예시도 같이 고친다.
HTML 로 쓴 뒤 Playwright(크로미엄) 로 A4 PDF 를 인쇄한다 — 글자가 그대로 살아 있는 PDF 라 AI 가 읽을 수 있다.
"""
import html, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).resolve().parent.parent / 'assets' / '실습자료' / 'M1 프로젝트 실습자료' / '복리후생 규정.pdf'

ARTICLES = [
    ('제1조 (목적)', [
        '이 규정은 임직원의 복리후생에 관한 기준과 절차를 정한다.']),
    ('제2조 (적용 대상)', [
        '이 규정은 정규직 · 계약직 임직원에게 적용한다. 수습 기간 중인 사람도 포함한다.']),
    ('제3조 (경조사 휴가)', [
        '① 경조사 휴가는 아래와 같이 준다. 휴가 일수는 근무일 기준이며 휴일은 세지 않는다.',
        '- 본인 결혼 : 5일',
        '- 자녀 결혼 : 1일',
        '- 배우자 출산 : 10일 (출산일로부터 90일 안에 나누어 쓸 수 있다)',
        '② 사망의 경우는 아래와 같다.',
        '- 부모 · 배우자 · 배우자의 부모 : 5일',
        '- 자녀 : 5일',
        '- 조부모 · 외조부모 : 3일',
        '- 형제자매 : 1일',
        '③ 경조사 휴가는 경조사가 생긴 날부터 30일 안에 써야 한다.']),
    ('제4조 (경조금)', [
        '① 경조금은 아래와 같이 지급한다.',
        '- 본인 결혼 : 50만 원',
        '- 자녀 결혼 : 30만 원',
        '- 부모 · 배우자 · 배우자의 부모 사망 : 100만 원',
        '- 조부모 · 외조부모 사망 : 30만 원',
        '② 경조금은 신청한 달의 다음 달 급여와 함께 지급한다.']),
    ('제5조 (국내 출장비)', [
        '① 숙박비는 1박에 아래 금액까지 실비로 지급한다.',
        '- 서울 · 광역시 : 10만 원',
        '- 그 밖의 지역 : 8만 원',
        '② 일비는 하루 2만 5천 원을 정액으로 지급한다.',
        '③ 교통비는 대중교통 실비로 지급한다. 회사가 승인한 경우에만 자가용을 쓸 수 있으며, 이때는 1km에 250원을 지급한다.',
        '④ 출장비는 출장을 마친 날부터 14일 안에 영수증을 붙여 정산한다.']),
    ('제6조 (자기계발비)', [
        '① 임직원 한 사람에게 1년에 120만 원까지 지원한다.',
        '② 어학 강좌, 자격증 응시료, 업무 관련 도서 구입에 쓸 수 있다.',
        '③ 분기마다 한 번, 영수증을 붙여 신청한다. 쓰지 않은 금액은 다음 해로 넘어가지 않는다.']),
    ('제7조 (건강검진)', [
        '① 임직원은 매년 1회 종합 건강검진을 받을 수 있다.',
        '② 만 40세 이상 임직원은 배우자도 함께 받을 수 있다.']),
    ('제8조 (신청 방법)', [
        '① 경조사 휴가와 경조금은 그룹웨어 [근태 · 복리후생] 메뉴에서 신청한다.',
        '② 청첩장 · 부고 · 가족관계증명서 등 증빙 서류를 함께 올린다.',
        '③ 이 규정에 대한 문의는 인사팀으로 한다.']),
    ('부칙', [
        '이 규정은 2026년 1월 1일부터 시행한다.']),
]

CSS = '''
@page { size: A4; margin: 22mm 20mm; }
body { font-family: "Malgun Gothic", "맑은 고딕", sans-serif; font-size: 10.5pt; line-height: 1.7; color: #222; }
h1 { font-size: 20pt; margin: 0 0 4pt; letter-spacing: -.02em; }
.note { font-size: 9pt; color: #777; margin: 0 0 14pt; padding-bottom: 8pt; border-bottom: 1.5px solid #222; }
h2 { font-size: 12pt; margin: 14pt 0 3pt; break-after: avoid; }
p { margin: 0 0 2pt; }
p.item { padding-left: 14pt; }
'''


def build_html():
    body = ['<h1>복리후생 규정</h1>',
            '<p class="note">※ 교육용으로 지어낸 규정입니다. 실제 회사 규정과 다릅니다.</p>']
    for head, lines in ARTICLES:
        body.append('<h2>%s</h2>' % html.escape(head))
        for line in lines:
            cls = ' class="item"' if line.startswith('- ') else ''
            body.append('<p%s>%s</p>' % (cls, html.escape(line)))
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>복리후생 규정</title>'
            '<style>%s</style></head><body>%s</body></html>' % (CSS, '\n'.join(body)))


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.set_content(build_html())
    pg.pdf(path=str(OUT), format='A4', print_background=True, prefer_css_page_size=True)
    b.close()
old = OUT.with_suffix('.docx')
if old.exists():
    old.unlink()
    print('  -', old.name)
print('  +', OUT.name)
