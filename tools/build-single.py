# -*- coding: utf-8 -*-
"""
배포용 단일 HTML 빌드

목차(index.html)와 모듈 교안(ot / m1 / m2 …)을 한 파일로 합치고,
CSS · JS · 이미지를 모두 본문에 넣어 파일 하나만으로 열리게 만든다.

    python tools/build-single.py

결과물 : dist/AX중급과정_교안.html          교육생용 (그대로 나눠 주는 파일)
        dist/AX중급과정_교안(강사용).html   강사용 — 위에 [실습 시작] · [쉬는 시간] 버튼이 더 붙는다
        dist/감사실/                        감사실판 한 벌 — M4 만 m4-audit.html 로 바꿔 끼운다 (VARIANTS)
        dist/뉴스분석/                      뉴스 동향 분석판 한 벌 — M4 만 m4-news.html 로 바꿔 끼운다
        dist/설비현황판/                    설비 가동률 현황판 한 벌 — M4 만 m4-equip.html 로 바꿔 끼운다
        dist/판매현황판/                    판매 실적 현황판 한 벌 — M4 만 m4-sales.html 로 바꿔 끼운다
        dist/교육현황판/                    교육 만족도 현황판 한 벌 — M4 만 m4-hrd.html 로 바꿔 끼운다
        dist/심의현황판/                    보안 심의 진행 현황판 한 벌 — M4 만 m4-review.html 로 바꿔 끼운다
        dist/VOC현황판/                     고객 VOC 현황판 한 벌 — M4 만 m4-voc.html 로 바꿔 끼운다
        dist/예산현황판/                    예산 집행 현황판 한 벌 — M4 만 m4-budget.html 로 바꿔 끼운다
        dist/계약현황판/                    계약 만료 관리 현황판 한 벌 — M4 만 m4-contract.html 로 바꿔 끼운다

강사용에만 assets/css/teacher.css · assets/js/teacher.js 가 실린다.
교육생용 파일에는 그 코드가 한 줄도 들어가지 않는다.

- 원본 파일은 건드리지 않는다. 슬라이드를 고친 뒤 이 스크립트를 다시 돌리면 된다.
- 목차에서 모듈 카드를 누르면 그 교안이 열리고, `← 목차` 또는 Esc 로 돌아온다.
- 주소 해시는 `#m1/3` 형태 — 새로고침해도 그 장에서 시작한다.
"""
import base64
import os
import mimetypes
import shutil
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'

# 목차에 실을 순서. (파일, 덱 id, 목차 카드 링크 대상 — index.html 의 href)
MODULES = [
    ('m1.html', 'm1', 'm1.html'),
    ('m2.html', 'm2', 'm2.html'),
    ('m3.html', 'm3', 'm3.html'),
    ('m4.html', 'm4', 'm4.html'),
    ('m5.html', 'm5', 'm5.html'),
]

# dist/강의자료 — 교육생에게 폴더째 주는 「강의자료」.
# assets/실습자료 의 작업용 폴더 이름을 모듈 번호로 바꿔 담는다.
#   (강의자료 안 경로, 원본 폴더, 담을 파일 - 비우면 폴더째)
GUIDE_TREE = [
    # M1 프로젝트 실습은 아이디어 기획서 브레인스토밍(2026-10-16) — 설문 CSV · 업무보고서 양식은 더 쓰지 않는다.
    # Worksheet PDF 는 docs/M5자료 의 pptx 를 PowerPoint 로 내보낸 것이다(pptx 를 고치면 다시 내보낸다).
    ('M1',               'assets/실습자료/M1 프로젝트 실습자료',
                         ['복리후생 규정.pdf', '아이디어 기획서 Worksheet.pdf']),
    ('M2/consolidate',     'assets/실습자료/M2 데스크탑 실습자료/consolidate', None),
    ('M2/주간업무메모',    'assets/실습자료/주간업무메모',                     None),
    ('M3/회의메모',       'assets/실습자료/회의메모',                         None),
    # 실행.bat 은 강사 예비본이라 주지 않는다 (교육생은 M4 배포 실습에서 직접 만든다).
    ('M4/base',          'assets/실습자료/base',   ['app.html', 'server.js', '샘플 보고서.pdf']),
    # M5 는 목업만 만든다 — PDF 도 실행.bat 도 필요 없다.
    ('M5/poc',           'assets/실습자료/base',   ['app.html', 'server.js']),
    # docs/ 원본은 읽기 전용이라 이름을 그대로 두고, 강의자료에 담을 때 「Worksheet」 로 바꿔 담는다 — (원본 이름, 담을 이름)
    ('M5',               'docs/M5자료',            [('M5. 나만의_업무_혁신_PoC_아이디어기획서 Work Sheet.pptx',
                                                    'M5. 나만의_업무_혁신_PoC_아이디어기획서 Worksheet.pptx')]),
    # 우수사례 폴더는 넣지 않는다(2026-10-16) — 교육생용 교안에는 사례 링크가 없고, 원본은 강사용 교안 곁에만 둔다.
]


# 감사실판 (2026-10-01 현대차 감사실 회차) — M4 실습을 사전 설문에 맞춰
# 「법인카드 이상징후 대시보드」로 바꾼 한 벌. 기존 배포본은 그대로 두고 dist/감사실/ 에 따로 만든다.
AUDIT_MODULES = [m if m[1] != 'm4' else ('m4-audit.html', 'm4', 'm4.html') for m in MODULES]
AUDIT_GUIDE_TREE = []
for _dest, _src, _names in GUIDE_TREE:
    if _dest == 'M4/base':
        AUDIT_GUIDE_TREE += [('M4/base', 'assets/실습자료/base', ['app.html', 'server.js']),
                             ('M4/base', 'assets/실습자료/감사실', None)]      # 경비내역 CSV 3개 · 점검기준.md
    else:
        AUDIT_GUIDE_TREE.append((_dest, _src, _names))

# 목차(index.html) 에서 감사실판만 바꿔 쓰는 글귀. M4 장수는 빌드 때 세어 넣는다.
AUDIT_INDEX = [
    ('<p class="home-eyebrow">HYUNDAI · AX</p>', '<p class="home-eyebrow">HYUNDAI · AX · 감사실</p>'),
    ('<h1 class="home-title">AX 중급과정 강의 교안</h1>', '<h1 class="home-title">AX 중급과정 강의 교안 · 감사실</h1>'),
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> 경비 내역에서 점검기준에 걸린 건을 찾고 AI가 요약하는 대시보드를 만들어'),
]

# 뉴스 동향 분석판 — M4 실습을 「키워드로 최근 뉴스를 모아 비교 · AI 분석 · 보고서 출력」으로 바꾼 한 벌.
# 재료 파일이 없다 (뉴스는 실습 중에 검색한다) — 강의자료 M4/base 는 기본 두 파일뿐이다.
NEWS_MODULES = [m if m[1] != 'm4' else ('m4-news.html', 'm4', 'm4.html') for m in MODULES]
NEWS_GUIDE_TREE = [(d, s, ['app.html', 'server.js'] if d == 'M4/base' else n) for d, s, n in GUIDE_TREE]
NEWS_INDEX = [
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> 키워드로 최근 뉴스를 모아 비교하고 AI가 보고서로 정리하는 앱을 만들어'),
]

# 설비 가동률 현황판 — M4 실습을 「설비가동 CSV 여섯 개를 합쳐 가동률 · 주의 설비 · AI 요약 · 월간 보고서」로 바꾼 한 벌.
EQUIP_MODULES = [m if m[1] != 'm4' else ('m4-equip.html', 'm4', 'm4.html') for m in MODULES]
EQUIP_GUIDE_TREE = []
for _dest, _src, _names in GUIDE_TREE:
    if _dest == 'M4/base':
        EQUIP_GUIDE_TREE += [('M4/base', 'assets/실습자료/base', ['app.html', 'server.js']),
                             ('M4/base', 'assets/실습자료/설비현황판', None)]     # 설비가동 CSV 6개
    else:
        EQUIP_GUIDE_TREE.append((_dest, _src, _names))
EQUIP_INDEX = [
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> 설비가동 기록을 합쳐 가동률을 계산하고 AI가 주의 설비를 요약하는 현황판을 만들어'),
]

# 판매 실적 현황판 — M4 실습을 「판매실적 CSV 3개(목표대수 포함)를 합쳐 지역 × 차종 달성률 · 주의 · AI 요약 · 월간 보고서」로 바꾼 한 벌.
SALES_MODULES = [m if m[1] != 'm4' else ('m4-sales.html', 'm4', 'm4.html') for m in MODULES]
SALES_GUIDE_TREE = []
for _dest, _src, _names in GUIDE_TREE:
    if _dest == 'M4/base':
        SALES_GUIDE_TREE += [('M4/base', 'assets/실습자료/base', ['app.html', 'server.js']),
                             ('M4/base', 'assets/실습자료/판매현황판', None)]     # 판매실적 CSV 3개 (목표대수 · 전년동월이 같은 줄에)
    else:
        SALES_GUIDE_TREE.append((_dest, _src, _names))
SALES_INDEX = [
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> 판매실적을 합쳐 BP 달성률을 계산하고 AI가 지역 · 차종별로 요약하는 현황판을 만들어'),
]

# 교육 만족도 현황판 — M4 실습을 「교육 설문 CSV 6개(2과정 × 3차수)를 합쳐 차수별 만족도 · 주의 차수 · AI 코멘트 요약 · 결과 보고서」로 바꾼 한 벌.
HRD_MODULES = [m if m[1] != 'm4' else ('m4-hrd.html', 'm4', 'm4.html') for m in MODULES]
HRD_GUIDE_TREE = []
for _dest, _src, _names in GUIDE_TREE:
    if _dest == 'M4/base':
        HRD_GUIDE_TREE += [('M4/base', 'assets/실습자료/base', ['app.html', 'server.js']),
                           ('M4/base', 'assets/실습자료/교육현황판', None)]     # 교육 설문 CSV 6개 (응답 한 줄 · 코멘트 포함)
    else:
        HRD_GUIDE_TREE.append((_dest, _src, _names))
HRD_INDEX = [
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> 교육 설문을 합쳐 차수별 만족도를 계산하고 AI가 코멘트를 요약하는 현황판을 만들어'),
]

# 보안 심의 진행 현황판 — M4 실습을 「Jira 심의 요청 CSV 3개(절차마다 하나)를 합쳐 절차별 · 기술분야별 건수 · 소요일 · 주의 요청 · AI 지연 사유 요약 · 현황 보고서」로 바꾼 한 벌.
REVIEW_MODULES = [m if m[1] != 'm4' else ('m4-review.html', 'm4', 'm4.html') for m in MODULES]
REVIEW_GUIDE_TREE = []
for _dest, _src, _names in GUIDE_TREE:
    if _dest == 'M4/base':
        REVIEW_GUIDE_TREE += [('M4/base', 'assets/실습자료/base', ['app.html', 'server.js']),
                              ('M4/base', 'assets/실습자료/심의현황판', None)]     # 심의 요청 CSV 3개 (요청 한 줄 · 최근 코멘트 포함)
    else:
        REVIEW_GUIDE_TREE.append((_dest, _src, _names))
REVIEW_INDEX = [
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> 심의 요청을 합쳐 절차별 건수와 소요일을 계산하고 AI가 지연 사유를 요약하는 현황판을 만들어'),
]

# 고객 VOC 현황판 — M4 실습을 「주간 VOC CSV 4개를 합쳐 차종 × 유형별 건수 · 급증 · 처리 지연 · AI 원문 분류(긍정 · 부정) · 요약 · 주간 보고서」로 바꾼 한 벌.
VOC_MODULES = [m if m[1] != 'm4' else ('m4-voc.html', 'm4', 'm4.html') for m in MODULES]
VOC_GUIDE_TREE = []
for _dest, _src, _names in GUIDE_TREE:
    if _dest == 'M4/base':
        VOC_GUIDE_TREE += [('M4/base', 'assets/실습자료/base', ['app.html', 'server.js']),
                           ('M4/base', 'assets/실습자료/VOC현황판', None)]     # VOC CSV 4개 (문의 한 줄 · 원문 포함, 고객명은 가린 모양)
    else:
        VOC_GUIDE_TREE.append((_dest, _src, _names))
VOC_INDEX = [
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> VOC를 합쳐 차종 × 유형별로 세고 AI가 원문을 긍정 · 부정으로 나누어 요약하는 현황판을 만들어'),
]

# 예산 집행 현황판 — M4 실습을 「연간예산 CSV + 팀별 집행 CSV 4개를 합쳐 프로젝트 × 계정 집행률 · 정상 페이스 비교 · 과속 · 저조 · AI 사정 요약 · 현황 보고서」로 바꾼 한 벌.
BUDGET_MODULES = [m if m[1] != 'm4' else ('m4-budget.html', 'm4', 'm4.html') for m in MODULES]
BUDGET_GUIDE_TREE = []
for _dest, _src, _names in GUIDE_TREE:
    if _dest == 'M4/base':
        BUDGET_GUIDE_TREE += [('M4/base', 'assets/실습자료/base', ['app.html', 'server.js']),
                              ('M4/base', 'assets/실습자료/예산현황판', None)]     # 연간예산 CSV 1개 + 팀별 집행 CSV 4개
    else:
        BUDGET_GUIDE_TREE.append((_dest, _src, _names))
BUDGET_INDEX = [
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> 예산과 집행 내역을 합쳐 집행률을 정상 페이스와 비교하고 AI가 과속 · 저조 사정을 요약하는 현황판을 만들어'),
]

# 계약 만료 관리 현황판 — M4 실습을 「부서별 계약 대장 CSV 4개를 합쳐 결정 마감일(자동연장은 해지 통보 마감) · 금액 변화 · 준비 늦음 · 금액 급증 · AI 갱신 우선순위 요약 · 현황 보고서」로 바꾼 한 벌.
CONTRACT_MODULES = [m if m[1] != 'm4' else ('m4-contract.html', 'm4', 'm4.html') for m in MODULES]
CONTRACT_GUIDE_TREE = []
for _dest, _src, _names in GUIDE_TREE:
    if _dest == 'M4/base':
        CONTRACT_GUIDE_TREE += [('M4/base', 'assets/실습자료/base', ['app.html', 'server.js']),
                                ('M4/base', 'assets/실습자료/계약현황판', None)]     # 부서별 계약 대장 CSV 4개
    else:
        CONTRACT_GUIDE_TREE.append((_dest, _src, _names))
CONTRACT_INDEX = [
    ('계획서(PHASE.md)대로 한 단계씩</strong> PDF 분석 대시보드와 챗봇을 만들어',
     '계획서(PHASE.md)대로 한 단계씩</strong> 계약 대장을 합쳐 결정 마감과 금액 변화를 계산하고 AI가 먼저 결정할 계약을 요약하는 현황판을 만들어'),
]

VARIANTS = [
    dict(name='기본', dist=DIST, out='AX중급과정_교안.html', out_t='AX중급과정_교안(강사용).html',
         modules=MODULES, guide=GUIDE_TREE, index=[], suffix=''),
    dict(name='감사실', dist=DIST / '감사실', out='AX중급과정_교안_감사실.html',
         out_t='AX중급과정_교안_감사실(강사용).html',
         modules=AUDIT_MODULES, guide=AUDIT_GUIDE_TREE, index=AUDIT_INDEX, suffix=' · 감사실',
         done='assets/실습자료/감사실_완성본', data='assets/실습자료/감사실'),
    dict(name='뉴스분석', dist=DIST / '뉴스분석', out='AX중급과정_교안_뉴스분석.html',
         out_t='AX중급과정_교안_뉴스분석(강사용).html',
         modules=NEWS_MODULES, guide=NEWS_GUIDE_TREE, index=NEWS_INDEX, suffix='',
         done='assets/실습자료/뉴스분석_완성본', data=None),
    dict(name='설비현황판', dist=DIST / '설비현황판', out='AX중급과정_교안_설비현황판.html',
         out_t='AX중급과정_교안_설비현황판(강사용).html',
         modules=EQUIP_MODULES, guide=EQUIP_GUIDE_TREE, index=EQUIP_INDEX, suffix='',
         done='assets/실습자료/설비현황판_완성본', data='assets/실습자료/설비현황판'),
    dict(name='판매현황판', dist=DIST / '판매현황판', out='AX중급과정_교안_판매현황판.html',
         out_t='AX중급과정_교안_판매현황판(강사용).html',
         modules=SALES_MODULES, guide=SALES_GUIDE_TREE, index=SALES_INDEX, suffix='',
         done='assets/실습자료/판매현황판_완성본', data='assets/실습자료/판매현황판'),
    dict(name='교육현황판', dist=DIST / '교육현황판', out='AX중급과정_교안_교육현황판.html',
         out_t='AX중급과정_교안_교육현황판(강사용).html',
         modules=HRD_MODULES, guide=HRD_GUIDE_TREE, index=HRD_INDEX, suffix='',
         done='assets/실습자료/교육현황판_완성본', data='assets/실습자료/교육현황판'),
    dict(name='심의현황판', dist=DIST / '심의현황판', out='AX중급과정_교안_심의현황판.html',
         out_t='AX중급과정_교안_심의현황판(강사용).html',
         modules=REVIEW_MODULES, guide=REVIEW_GUIDE_TREE, index=REVIEW_INDEX, suffix='',
         done='assets/실습자료/심의현황판_완성본', data='assets/실습자료/심의현황판'),
    dict(name='VOC현황판', dist=DIST / 'VOC현황판', out='AX중급과정_교안_VOC현황판.html',
         out_t='AX중급과정_교안_VOC현황판(강사용).html',
         modules=VOC_MODULES, guide=VOC_GUIDE_TREE, index=VOC_INDEX, suffix='',
         done='assets/실습자료/VOC현황판_완성본', data='assets/실습자료/VOC현황판'),
    dict(name='예산현황판', dist=DIST / '예산현황판', out='AX중급과정_교안_예산현황판.html',
         out_t='AX중급과정_교안_예산현황판(강사용).html',
         modules=BUDGET_MODULES, guide=BUDGET_GUIDE_TREE, index=BUDGET_INDEX, suffix='',
         done='assets/실습자료/예산현황판_완성본', data='assets/실습자료/예산현황판'),
    dict(name='계약현황판', dist=DIST / '계약현황판', out='AX중급과정_교안_계약현황판.html',
         out_t='AX중급과정_교안_계약현황판(강사용).html',
         modules=CONTRACT_MODULES, guide=CONTRACT_GUIDE_TREE, index=CONTRACT_INDEX, suffix='',
         done='assets/실습자료/계약현황판_완성본', data='assets/실습자료/계약현황판'),
]


def read(p):
    return (ROOT / p).read_text(encoding='utf-8')


def data_uri(path):
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    b64 = base64.b64encode(path.read_bytes()).decode('ascii')
    return 'data:%s;base64,%s' % (mime, b64)


def inline_images(html):
    """assets/img/... 참조를 data URI 로 바꾼다."""
    def sub(m):
        rel = m.group(2)
        f = ROOT / rel
        if not f.exists():
            print('  ! 이미지 없음:', rel)
            return m.group(0)
        return '%s%s%s' % (m.group(1), data_uri(f), m.group(3))

    html = re.sub(r'(src=")(assets/img/[^"]+)(")', sub, html)
    html = re.sub(r'(data-zoom=")(assets/img/[^"]+)(")', sub, html)   # 누르면 크게 보는 그림
    html = re.sub(r'(url\()(assets/img/[^)]+)(\))', sub, html)
    return html


def body_of(html):
    m = re.search(r'<body[^>]*>', html)
    return html[m.end():].rsplit('</body>', 1)[0]


def body_attrs(html):
    """<body data-app="…"> 처럼 body 에 달린 속성을 그대로 돌려준다.

    배포본은 body 가 하나뿐이라, 덱을 감싸는 div 로 옮겨야 덱마다 값이 산다.
    """
    m = re.search(r'<body([^>]*)>', html)
    return (m.group(1) or '').strip()


def style_of(html):
    m = re.search(r'<style>(.*?)</style>', html, re.S)
    return m.group(1) if m else ''


ROADMAP_M4 = re.compile(r'(<div class="rm-pic">)(<img [^>]*>)(</div>\s*<p class="rm-mod">M4</p>\s*<p class="rm-out">)(.*?)(</p>)', re.S)


def roadmap_m4(fname):
    """교안 2p 진행 맵에서 M4 칸의 (그림 태그, 결과물 이름)을 꺼낸다."""
    m = ROADMAP_M4.search(read(fname))
    return (m.group(2), m.group(4)) if m else None


def build_deck(fname, deck_id, m4_step=None):
    """모듈 교안 한 편을 <div class="deck" data-deck="…"> 로 감싼다.

    모듈 고유 스타일(<head> 안의 <style>)도 함께 돌려준다.
    이걸 빠뜨리면 배포본에서 그 모듈의 레이아웃만 조용히 무너진다.

    m4_step 을 주면 진행 맵의 M4 칸(그림 · 결과물 이름)을 그것으로 바꾼다 —
    변형판에서 M1 · M2 · M3 · M5 의 맵이 「PDF 분석 대시보드」로 남지 않게.
    """
    html = read(fname)
    if m4_step:
        html = ROADMAP_M4.sub(lambda m: m.group(1) + m4_step[0] + m.group(3) + m4_step[1] + m.group(5), html)
    body = body_of(html)
    css = inline_images(style_of(html))

    # 스크립트 태그 제거 (공용 JS는 마지막에 한 번만 넣는다)
    body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.S)

    # id 는 문서 안에서 하나뿐이어야 하므로 클래스로 바꾼다
    body = body.replace('class="deck-arrow" id="prev"', 'class="deck-arrow js-prev"')
    body = body.replace('class="deck-arrow" id="next"', 'class="deck-arrow js-next"')
    body = body.replace('class="deck-count" id="count"', 'class="deck-count js-count"')

    body = inline_images(body)
    attrs = body_attrs(html)
    deck = '<div class="deck" data-deck="%s"%s hidden>\n%s\n</div>\n' % (
        deck_id, (' ' + attrs) if attrs else '', body.strip())
    return css, deck


ROUTER = """
(function () {
  var home  = document.getElementById('home');
  var decks = [].slice.call(document.querySelectorAll('[data-deck]'));

  function show(id, n) {
    home.hidden = !!id;
    decks.forEach(function (d) { d.hidden = d.getAttribute('data-deck') !== id; });
    if (id) {
      window.deckAPI.setActive(id, n);
    } else if (history.replaceState) {
      history.replaceState(null, '', location.pathname + location.search);
    }
    document.documentElement.classList.toggle('is-home', !id);
  }

  window.deckHome   = function () { show(null); };
  window.deckIsHome = function () { return !home.hidden; };

  document.addEventListener('click', function (e) {
    var go = e.target.closest ? e.target.closest('a[data-go]') : null;
    if (go) { e.preventDefault(); show(go.getAttribute('data-go')); return; }
    var back = e.target.closest ? e.target.closest('a.deck-home') : null;
    if (back) { e.preventDefault(); show(null); }
  });

  var parts = (location.hash || '').slice(1).split('/');
  var id = parts[0];
  var n  = parseInt(parts[1], 10);
  if (id && document.querySelector('[data-deck="' + id + '"]')) show(id, isNaN(n) ? 1 : n);
  else show(null);
})();
"""

EXTRA_CSS = """
/* ---- 단일 파일 배포본 전용 ------------------------------------------------ */
[hidden] { display: none !important; }
html, body { height: 100%; }
#home { height: 100%; }
"""

# 교육생용 교안에서는 M5 우수 사례 장의 「원본 결과물 열어 보기」 링크를 지운다 —
# 우수사례 원본 HTML 은 강사만 갖는다(2026-10-16). 장 자체는 그대로 보인다.
CASE_LINK = re.compile(r'\s*<p class="case-link"[^>]*>.*?</p>', re.S)


def student_decks(decks):
    return [CASE_LINK.sub('', d) for d in decks]


# 교육생에게는 mp4 를 나눠 주지 않으므로, M3 3p 의 영상 자리에
# 「앞 화면을 함께 봐 주세요」 안내판을 대신 띄운다 (markup 은 m3.html 에 이미 있다).
STUDENT_CSS = """
/* ---- 교육생용 전용 -------------------------------------------------------- */
.m3-video  { display: none; }
.m3-screen { display: flex; }

/* M5 「실습 진행 순서」 — 「현재 실습 중」 표시는 강사용에서만 보인다.
   교육생 파일에서는 배지도 강조도 없이 네 단계가 나란히 보이기만 한다. */
.plan-now { display: none !important; }
.plan-step.is-now { border-left-color: #C3CBD8; background: #F5F7FB; }
.plan-step.is-now .plan-t { color: var(--navy); }
.plan-step.is-now .plan-time { color: #8A94A6; }
"""


def page(home, decks, css_parts, teacher, suffix=''):
    """머리부터 발끝까지 한 파일로 엮는다.

    teacher=True 면 강사용 CSS · JS 를 더 싣는다.
    [실습 시작] · [쉬는 시간] 버튼은 teacher.js 가 상단 바(.deck-bar)에 스스로 붙이므로
    교안 HTML 은 손대지 않는다 — 교육생용 파일에는 그 코드가 한 줄도 들어가지 않는다.
    """
    parts = [
        '<!DOCTYPE html>',
        '<html lang="ko">',
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>AX 중급과정 강의 교안%s%s</title>' % (suffix, ' (강사용)' if teacher else ''),
        '<style>',
    ]
    parts += css_parts
    parts.append(read('assets/css/teacher.css') if teacher else STUDENT_CSS)
    parts += [
        '</style>',
        '</head>',
        '<body>',
        '',
        '<div id="home">',
        home,
        '</div>',
        '',
    ]

    parts += decks

    parts += [
        '<script>',
        read('assets/js/deck.js'),
        ROUTER,
    ]
    if teacher:
        parts.append(read('assets/js/teacher.js'))
    parts += [
        '</script>',
        '</body>',
        '</html>',
        '',
    ]
    return '\n'.join(parts)


def build_pair(v):
    """변형 하나의 교육생용 · 강사용 두 파일을 만든다. 교육생용 파일 경로를 돌려준다."""
    index_html = read('index.html')
    deck_css = read('assets/css/deck.css')

    # 모듈 고유 스타일을 먼저 모은다 (head 의 <style> 에 함께 넣기 위해)
    decks, module_css = [], []
    m4_file = next(f for f, d, h in v['modules'] if d == 'm4')
    m4_step = roadmap_m4(m4_file) if m4_file != 'm4.html' else None
    for fname, deck_id, href in v['modules']:
        print('  + %s → data-deck="%s"' % (fname, deck_id))
        css, deck = build_deck(fname, deck_id, m4_step if deck_id != 'm4' else None)
        if css.strip():
            module_css.append('/* ---- %s 고유 스타일 ---- */\n%s' % (fname, css.strip()))
        decks.append(deck)

    # 목차 — 모듈 카드 링크를 덱 전환으로 바꾼다
    home = body_of(index_html)
    for a, b in v['index']:
        if a not in home:
            print('  ! 목차에서 바꿀 글귀를 찾지 못했습니다 :', a[:40])
        home = home.replace(a, b)
    for fname, deck_id, href in v['modules']:
        if fname != href:   # 바꿔 끼운 모듈 — 목차 카드의 장수도 맞춘다
            n_new = read(fname).count('<section class="slide')
            n_old = read(href).count('<section class="slide')
            card = re.search(r'<a class="mod" href="%s">.*?</a>' % re.escape(href), home, re.S).group(0)
            home = home.replace(card, card.replace('슬라이드 %d장' % n_old, '슬라이드 %d장' % n_new))
        home = home.replace('href="%s"' % href, 'href="#%s" data-go="%s"' % (deck_id, deck_id))
    home = inline_images(home).strip()

    css_parts = [deck_css, style_of(index_html), '\n'.join(module_css), EXTRA_CSS]

    dist = v['dist']
    dist.mkdir(parents=True, exist_ok=True)
    out = dist / v['out']
    for path, teacher in ((out, False), (dist / v['out_t'], True)):
        path.write_text(page(home, decks if teacher else student_decks(decks), css_parts, teacher, v['suffix']), encoding='utf-8')
        print('완료 : %s (%.1f MB)   %s' % (
            path.relative_to(DIST).as_posix(), path.stat().st_size / 1024 / 1024,
            '← 강사용 : [실습 시작] · [쉬는 시간] 포함' if teacher else '← 교육생 배포용'))
    return out


def build_guide(guide, student_html, tree):
    """강의자료 — 교육생에게 폴더째 주는 그 폴더. 손으로 맞추면 반드시 어긋나므로 여기서 함께 만든다."""
    if guide.exists():
        shutil.rmtree(guide)
    guide.mkdir(parents=True)
    shutil.copy2(student_html, guide / student_html.name)     # 교육생용 교안 (강사용은 넣지 않는다)
    missing = []
    for dest, src, names in tree:
        src_dir = ROOT / src
        if not src_dir.is_dir():
            missing.append(src)
            continue
        dst_dir = guide / dest
        dst_dir.mkdir(parents=True, exist_ok=True)
        if names is None:
            for f in sorted(src_dir.rglob('*')):
                if f.is_file():
                    t = dst_dir / f.relative_to(src_dir)
                    t.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, t)
        else:
            for name in names:
                name, as_name = name if isinstance(name, tuple) else (name, name)   # (원본 이름, 담을 이름)
                f = src_dir / name
                if f.is_file():
                    shutil.copy2(f, dst_dir / as_name)
                else:
                    missing.append('%s/%s' % (src, name))
    gfiles = [f for f in guide.rglob('*') if f.is_file()]
    print('  . 강의자료 : %d개 파일 (%.1f MB) → %s/' %
          (len(gfiles), sum(f.stat().st_size for f in gfiles) / 1024 / 1024,
           guide.relative_to(ROOT).as_posix()))
    for m in missing:
        print('  ! 강의자료에 넣을 원본을 찾지 못했습니다 : %s' % m)


def link_or_copy(src, dst):
    """영상 · 음악은 용량이 커서 하드링크로 둔다 (안 되면 복사)."""
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def build_variant(v):
    """M4 만 바꿔 끼운 한 벌 — dist/<이름>/ 에 교안 두 벌 · 강의자료 · 우수사례 · 강사용 완성본 · 영상과 음악."""
    print('\n[%s]' % (v['name'] if v['name'].endswith('판') else v['name'] + '판'))
    dist = v['dist']
    here = dist.relative_to(DIST).as_posix()
    student = build_pair(v)
    build_guide(dist / '강의자료', student, v['guide'])

    cases_src = ROOT / '우수사례'
    if cases_src.is_dir():
        (dist / '우수사례').mkdir(exist_ok=True)
        for f in sorted(cases_src.glob('*.html')):
            shutil.copy2(f, dist / '우수사례' / f.name)

    # 강사용 완성본 — 실습이 막히면 그 단계 파일로 갈아 끼운다. 교육생 강의자료에는 넣지 않는다.
    done = dist / '강사용_완성본'
    if done.exists():
        shutil.rmtree(done)
    shutil.copytree(ROOT / v['done'], done)
    if not (done / 'server.js').exists():          # 완성본이 server.js 를 고치지 않았으면 기본 그대로
        shutil.copy2(ROOT / 'assets/실습자료/base/server.js', done)
    if v['data']:
        for f in (ROOT / v['data']).iterdir():
            shutil.copy2(f, done / f.name)
    print('  . 강사용 완성본 → dist/%s/강사용_완성본/ (단계별 phase1~3 포함)' % here)

    for name in ['AI실리콘밸리.mp4', '음악.mp3']:
        if (DIST / name).exists():
            link_or_copy(DIST / name, dist / name)
            print('  . %s → dist/%s/ (하드링크)' % (name, here))
        else:
            print('  ! dist 에 %s 가 없어 dist/%s 에도 넣지 못했습니다' % (name, here))
    print('  > 교육생에게는 dist/%s/강의자료 만 줍니다. 강사용 교안 · 완성본은 강사만 갖습니다.' % here)


def main():
    print('[기본판]')
    OUT = build_pair(VARIANTS[0])

    # 우수사례 원본 HTML 은 본문에 넣지 않고 파일째 함께 둔다 (M5 사례 슬라이드의 링크 대상 — 강사용 교안에서만 링크가 있다).
    cases_src = ROOT / '우수사례'
    if cases_src.is_dir():
        cases_dst = DIST / '우수사례'
        cases_dst.mkdir(parents=True, exist_ok=True)
        total = 0
        for f in sorted(cases_src.glob('*.html')):
            shutil.copy2(f, cases_dst / f.name)
            total += f.stat().st_size
        print('  . 우수사례 : %d개 (%.1f MB) → dist/우수사례/' %
              (len(list(cases_src.glob('*.html'))), total / 1024 / 1024))
        print('  > 우수사례 폴더는 강사용 교안 곁에만 둡니다 (교육생용 교안 · 강의자료에는 사례 링크 · 폴더가 없습니다).')

    # 실습자료도 함께 넣는다 — 배포본 폴더가 그대로 '강의자료' 가 된다.
    # 교육생은 dist/실습자료/M4 실습3 Base 에서 바로 `code .` 로 실습을 시작한다.
    prac_src = ROOT / 'assets' / '실습자료'
    if prac_src.is_dir():
        prac_dst = DIST / '실습자료'
        if prac_dst.exists():
            shutil.rmtree(prac_dst)
        shutil.copytree(prac_src, prac_dst, ignore=shutil.ignore_patterns('감사실*', '뉴스분석*', '설비현황판*', '판매현황판*', '교육현황판*', '심의현황판*', 'VOC현황판*', '예산현황판*', '계약현황판*'))
        files = [f for f in prac_dst.rglob('*') if f.is_file()]
        print('  . 실습자료 : %d개 파일 (%.1f MB) → dist/실습자료/' %
              (len(files), sum(f.stat().st_size for f in files) / 1024 / 1024))

    build_guide(DIST / '강의자료', OUT, GUIDE_TREE)
    print('  > 이 폴더를 그대로 압축해 교육생에게 줍니다 (강사용 교안은 들어 있지 않습니다).')

    # 영상은 경로 없이 파일 이름으로만 참조한다 (본문에 넣지 않는다).
    # dist/ 안에 mp4 가 함께 있어야 재생된다.
    videos = sorted(DIST.glob('*.mp4'))
    for mp4 in videos:
        print('  . 영상 : %s (%.0f MB)' % (mp4.name, mp4.stat().st_size / 1024 / 1024))
    if videos:
        print('  > 배포할 때 HTML 과 mp4 를 같은 폴더에 함께 전달하세요.')
    else:
        print('  ! dist 안에 mp4 가 없습니다 - M3 3p 영상이 재생되지 않습니다.')

    # 배경음악도 영상과 같은 방식이다 — 파일 이름으로만 참조한다 (강사용 전용).
    music = DIST / '음악.mp3'
    if music.exists():
        print('  . 음악 : %s (%.0f MB) - 실습 · 쉬는 시간이 이 한 곡을 이어서 씁니다.' %
              (music.name, music.stat().st_size / 1024 / 1024))
    else:
        print('  . 음악 : dist 안에 음악.mp3 가 없어 유튜브로 재생됩니다 (인터넷 필요).')

    for v in VARIANTS[1:]:
        build_variant(v)


if __name__ == '__main__':
    sys.exit(main())
