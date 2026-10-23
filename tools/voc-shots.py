# -*- coding: utf-8 -*-
"""고객 VOC 현황판 M4 — 실습 앱 화면 캡처 (교안 assets/img/m4v-*.png)

실습을 Playwright 로 그대로 따라 하며 찍는다 — VOC CSV 네 개를 올리고, 연결하고, 이번 주 원문을 AI 로 분류하고, 요약을 받고, 질문하고,
주간 보고서를 띄우고, 통합 VOC표를 내려받는다.

    python tools/voc-shots.py              # AI 응답은 자리표시(tools/voc_stub.js) — 키 없이 찍힌다
    python tools/voc-shots.py --live       # 진짜 server.js + Claude 응답으로 찍는다

--live 는 환경변수 HCHAT_API_KEY 에 H Chat Personal API Key 를 넣어 두고 실행한다.
키는 화면의 비밀번호 칸에만 들어가고 캡처에는 점(●)으로만 찍힌다.
찍고 나면 python tools/build-single.py 로 배포본을 다시 만든다.
"""
import csv, io, os, pathlib, re, shutil, subprocess, sys, tempfile, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / 'assets/img'
DATA = ROOT / 'assets/실습자료/VOC현황판'
DONE = ROOT / 'assets/실습자료/VOC현황판_완성본'
LIVE = '--live' in sys.argv
VIEW = {'width': 1440, 'height': 900}


def start(folder):
    """앱 폴더를 띄우고 주소를 돌려준다."""
    if LIVE:
        cmd = ['node', 'server.js']
    else:
        cmd = ['node', str(ROOT / 'tools/voc_stub.js'), str(folder), '8796']
    p = subprocess.Popen(cmd, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding='utf-8')
    t0 = time.time()
    while time.time() - t0 < 15:
        m = re.search(r'READY (http://\S+)', p.stdout.readline() or '')
        if m:
            return p, m.group(1)
    p.kill()
    raise SystemExit('서버가 뜨지 않았습니다')


def load(pg, folder):
    pg.set_input_files('#fileInput', [str(f) for f in sorted(folder.glob('VOC_*.csv'))])
    pg.wait_for_selector('#dash:not([hidden])')
    pg.wait_for_timeout(300)


def connect(pg):
    key = os.environ.get('HCHAT_API_KEY', '') if LIVE else 'sk-demo-placeholder-key'
    if not key:
        raise SystemExit('--live 는 HCHAT_API_KEY 환경변수가 필요합니다')
    pg.fill('#apiKey', key)
    pg.click('#connectBtn')
    pg.wait_for_selector('#keyStatus.ok, #keyStatus.err', state='attached', timeout=90000)
    if 'err' in pg.get_attribute('#keyStatus', 'class'):
        raise SystemExit('연결 실패: ' + pg.inner_text('#keyStatus')[:200])


def summary(pg):
    pg.click('#sumBtn')
    pg.wait_for_function("!document.querySelector('#summary .loading')", timeout=180000)
    pg.wait_for_timeout(300)


def ask(pg, q):
    pg.fill('#chatIn', q)
    pg.press('#chatIn', 'Enter')
    pg.wait_for_function("!document.querySelector('#chatlog .loading')", timeout=180000)
    pg.wait_for_timeout(300)


def tag(pg):
    pg.click('#tagBtn')
    pg.wait_for_function("!document.querySelector('#tagRes .loading')", timeout=600000)
    pg.wait_for_timeout(300)


def box(pg, sel, pad=6):
    b = pg.locator(sel).first.bounding_box()
    return {'x': b['x'] - pad, 'y': b['y'] - pad, 'width': b['width'] + pad * 2, 'height': b['height'] + pad * 2}


def shot(pg, name, **kw):
    pg.evaluate('document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0)')
    pg.wait_for_timeout(150)
    pg.screenshot(path=str(IMG / name), **kw)
    print('  +', name)


DIST_CARD = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><style>
body{margin:0;padding:14px;background:#fff;font-family:"Malgun Gothic",sans-serif;width:470px}
.f{border:1px solid #D8DEE9;border-radius:9px;overflow:hidden}
.h{padding:9px 14px;background:#F2F2F2;border-bottom:1px solid #D8DEE9;font-size:15px;color:#7C8698}
.h b{color:#1A1A1A;margin-right:8px}.r{display:flex;align-items:center;gap:10px;padding:8px 14px;border-bottom:1px solid #EEF1F5;font-size:15.5px}
.r:last-child{border-bottom:0}.r span{margin-left:auto;font-size:13px;color:#7C8698}
.i{width:24px;height:24px;border-radius:5px;color:#fff;font-size:10.5px;font-weight:800;font-style:italic;display:flex;align-items:center;justify-content:center}
.z{margin-top:10px;display:flex;align-items:center;gap:10px;padding:11px 14px;border:2px solid #164194;border-radius:9px;background:#F5F7FB}
.z b{font-size:17px;color:#164194}.z span{margin-left:auto;font-size:13px;color:#7C8698}
</style></head><body>
<div class="f"><div class="h"><b>📁 dist</b>&gt; 동료에게 줄 폴더</div>
<div class="r"><i class="i" style="background:#164194">H</i>app.html<span>화면</span></div>
<div class="r"><i class="i" style="background:#6A9E3B">JS</i>server.js<span>중계 서버</span></div>
<div class="r"><i class="i" style="background:#4A6FA5">MD</i>VOC기준.md<span>급증 · 지연 기준</span></div>
<div class="r"><i class="i" style="background:#7C8698">BAT</i>실행.bat<span>더블클릭 · Node 확인까지</span></div></div>
<div class="z"><i class="i" style="background:#C28A2C">ZIP</i><b>고객VOC현황판.zip</b><span>0.1 MB · 메일로 그냥 전달</span></div>
</body></html>"""


def main():
    work = pathlib.Path(tempfile.mkdtemp(prefix='voc-m4-'))
    try:
        shutil.copy2(ROOT / 'assets/실습자료/base/server.js', work)
        for f in DATA.iterdir():
            shutil.copy2(f, work)
        for f in (DONE / '단계별').glob('*.html'):
            shutil.copy2(f, work)
        shutil.copy2(DONE / 'app.html', work)
        # 기준 한 줄 바꾸기(급증 50% → 30%) 결과 화면용
        src = (DONE / 'app.html').read_text(encoding='utf-8')
        assert 'rise: 50,' in src
        (work / 'app30.html').write_text(src.replace('rise: 50,', 'rise: 30,', 1), encoding='utf-8')

        proc, url = start(work)
        print('서버 :', url, '(실제 Claude)' if LIVE else '(자리표시 응답)')
        try:
            capture(url, work)
        finally:
            proc.kill()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if not LIVE:
        print('  > AI 응답 칸은 자리표시입니다. 실제 응답으로 바꾸려면 --live 로 다시 찍습니다.')


def capture(url, work):
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport=VIEW, accept_downloads=True)
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        # Phase 1 — 가짜 데이터 초안
        pg.goto(url + '/phase1.html'); pg.wait_for_timeout(300)
        shot(pg, 'm4v-phase1.png')

        # Phase 2 — CSV 네 개를 올린 현황판 (AI 없음)
        pg.goto(url + '/phase2.html'); pg.wait_for_timeout(200)
        load(pg, work)
        shot(pg, 'm4v-phase2.png')

        # Phase 4 완성본 — 빈 화면 · 현황판 · 요약 · 보고서 · 통합표
        pg.goto(url + '/app.html'); pg.wait_for_timeout(300)
        shot(pg, 'm4v-upload.png')
        load(pg, work)
        shot(pg, 'm4v-dash.png')
        # 숫자 카드 + 기준 칩 (기준을 바꾸기 전)
        k = pg.locator('.kpis').bounding_box(); r = pg.locator('#rules').bounding_box()
        clip = {'x': k['x'] - 8, 'y': k['y'] - 8, 'width': k['width'] + 16, 'height': r['y'] + r['height'] - k['y'] + 16}
        shot(pg, 'm4v-rule50.png', clip=clip)
        # 차종 × 유형 표 · 원문 목록 — 빨간 칸이 보이는 자리
        for i, name in ((0, 'm4v-table.png'), (1, 'm4v-list.png')):
            b_ = pg.locator('#dash > .card').nth(i).bounding_box()
            pg.screenshot(path=str(IMG / name), clip={'x': b_['x'] - 4, 'y': b_['y'] - 4, 'width': b_['width'] + 8, 'height': min(b_['height'] + 8, 900)}, full_page=True)
            print('  +', name)

        # 통합 VOC표 내려받기 — 실제로 받아서 행 수를 확인한다
        with pg.expect_download() as dl:
            pg.click('#csvBtn')
        text = pathlib.Path(dl.value.path()).read_text(encoding='utf-8-sig')
        got = list(csv.reader(io.StringIO(text)))
        print('  . 통합표 %s — %d행 (머리글 제외), 열: %s' % (dl.value.suggested_filename, len(got) - 1, ' · '.join(got[0][:6]) + ' …'))

        connect(pg); tag(pg)
        # AI 분류 뒤 — 원문 목록의 「AI 분류」 열 · 표의 「부정 비율」
        pg.select_option('#pickSel', 'g:투싼 · 품질'); pg.wait_for_timeout(200)
        # 교안에서 크게 보이게 — 차종 · 유형 · AI 분류 · 원문만 남기고 폭을 줄여 찍는다
        css = pg.add_style_tag(content='.lst th:nth-child(-n+3), .lst td:nth-child(-n+3), .lst th:nth-child(6), .lst td:nth-child(6), .lst th:nth-child(7), .lst td:nth-child(7) { display: none; }')
        pg.evaluate("document.querySelectorAll('#dash > .card')[1].style.maxWidth = '640px'"); pg.wait_for_timeout(200)
        b_ = pg.locator('#dash > .card').nth(1).bounding_box()
        pg.screenshot(path=str(IMG / 'm4v-tagged.png'), clip={'x': b_['x'] - 4, 'y': b_['y'] - 4, 'width': b_['width'] + 8, 'height': min(b_['height'] + 8, 470)}, full_page=True)
        print('  + m4v-tagged.png')
        css.evaluate('el => el.remove()')
        pg.evaluate("document.querySelectorAll('#dash > .card')[1].style.maxWidth = ''")
        pg.select_option('#pickSel', 'flag')
        pg.select_option('#metricSel', 'neg'); pg.wait_for_timeout(200)
        b_ = pg.locator('#dash > .card').nth(0).bounding_box()
        pg.screenshot(path=str(IMG / 'm4v-neg.png'), clip={'x': b_['x'] - 4, 'y': b_['y'] - 4, 'width': b_['width'] + 8, 'height': b_['height'] + 8}, full_page=True)
        print('  + m4v-neg.png')
        pg.select_option('#metricSel', 'now')
        summary(pg)
        shot(pg, 'm4v-ai.png')
        pg.set_viewport_size({'width': 1440, 'height': 1600})   # 요약 네 덩어리가 다 보이게 — 요약 칸 높이 제한도 푼다
        pg.evaluate("document.getElementById('summary').style.maxHeight = 'none'")
        pg.wait_for_timeout(200)
        shot(pg, 'm4v-summary-crop.png', clip=box(pg, '#summary', 8))   # 요약 글만 — 교안에서 크게 보이게
        pg.evaluate("document.getElementById('summary').style.maxHeight = ''")
        pg.set_viewport_size(VIEW)

        # 주간 보고서 — 새 창
        with ctx.expect_page() as info:
            pg.click('#reportBtn')
        rp = info.value
        rp.set_viewport_size({'width': 900, 'height': 900})
        rp.wait_for_load_state(); rp.wait_for_timeout(300)
        rp.screenshot(path=str(IMG / 'm4v-report.png'), full_page=True)
        print('  + m4v-report.png')
        rp.close()

        # 대화는 새로 열어 찍는다 — 요약과 같이 두면 대화 칸이 좁다
        pg.goto(url + '/app.html'); pg.wait_for_timeout(200)
        load(pg, work); connect(pg); tag(pg)
        ask(pg, '투싼 품질 문의는 왜 늘었어?')
        shot(pg, 'm4v-chat.png')
        shot(pg, 'm4v-chat-crop.png', clip=box(pg, 'aside.ai .card--chat'))

        # 급증 기준을 30% 로 바꾼 뒤
        pg.goto(url + '/app30.html'); pg.wait_for_timeout(200)
        load(pg, work)
        shot(pg, 'm4v-rule30.png', clip=clip)

        # 배포 폴더 그림
        dp = b.new_page(device_scale_factor=2)
        dp.set_content(DIST_CARD)
        dp.screenshot(path=str(IMG / 'm4v-dist-zip.png'), clip=box(dp, 'body', 0))
        print('  + m4v-dist-zip.png')

        b.close()
        if errs:
            print('  ! 화면 오류:', errs)


if __name__ == '__main__':
    main()
