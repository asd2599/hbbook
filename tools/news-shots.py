# -*- coding: utf-8 -*-
"""뉴스 분석 M4 — 실습 앱 화면 캡처 (교안 assets/img/m4n-*.png)

실습을 Playwright 로 그대로 따라 하며 찍는다 — 키워드 세 개로 검색하고, 관계없는 기사의 체크를 빼고,
연결하고, 분석을 받고, 질문하고, 보고서기준.md 를 한 줄 바꿔 다시 분석하고, 보고서를 출력한다.

    python tools/news-shots.py            # 검색은 예비 결과, AI 응답은 자리표시(tools/news_stub.js)
    python tools/news-shots.py --live     # 완성본 server.js 로 — 실제 구글 뉴스 + 실제 Claude 응답

검색 결과는 tools/news_snapshot.py 로 받아 둔 예비_검색결과.json 을 쓴다 — 몇 번을 찍어도 같은 기사가 나온다.
--live 는 환경변수 HCHAT_API_KEY 에 H Chat Personal API Key 를 넣어 두고 실행한다.
키는 화면의 비밀번호 칸에만 들어가고 캡처에는 점(●)으로만 찍힌다.
찍고 나면 python tools/build-single.py 로 배포본을 다시 만든다.
"""
import os, pathlib, re, shutil, subprocess, sys, tempfile, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / 'assets/img'
DONE = ROOT / 'assets/실습자료/뉴스분석_완성본'
LIVE = '--live' in sys.argv
VIEW = {'width': 1440, 'height': 900}
KEYWORDS = '현대차 마케팅, 기아 마케팅, 제네시스 마케팅'
# 마케팅과 관계없이 걸려 온 기사 — 사람이 체크를 빼는 것 (야구단 · 기부 단체 · 주가 · 다른 회사 소식)
NOISE = ['KIA ', '타이거즈', '한우', '카지노', '토토', '앤트로픽', '뷰익', '코웨이', '노조', '하락', '인사평가', '투자분석']
IDEA_LINE = '5. 목차 끝에 「우리가 해 볼 만한 아이디어 3개」를 더한다.\n'


def start(folder):
    """앱 폴더를 띄우고 주소를 돌려준다."""
    if LIVE:
        cmd = ['node', 'server.js']
    else:
        cmd = ['node', str(ROOT / 'tools/news_stub.js'), str(folder), '8791']
    p = subprocess.Popen(cmd, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding='utf-8')
    t0 = time.time()
    while time.time() - t0 < 15:
        m = re.search(r'READY (http://\S+)', p.stdout.readline() or '')
        if m:
            return p, m.group(1)
    p.kill()
    raise SystemExit('서버가 뜨지 않았습니다')


def do_search(pg, uncheck=True):
    pg.fill('#kw', KEYWORDS)
    pg.select_option('#days', '30')
    pg.click('#searchBtn')
    pg.wait_for_selector('#dash:not([hidden])', timeout=60000)
    pg.wait_for_function("!document.querySelector('#searchBtn').disabled")
    if uncheck:
        # 사람이 하듯 체크박스를 하나씩 눌러 뺀다
        ns = pg.evaluate('(noise) => arts.filter(a => noise.some(p => a.title.includes(p))).map(a => a.n)', NOISE)
        for n in ns:
            pg.click('#tbody input[data-n="%d"]' % n)
        print('  . 체크 해제 %d건 : %s' % (len(ns), ns))
    pg.wait_for_timeout(200)


def connect(pg):
    key = os.environ.get('HCHAT_API_KEY', '') if LIVE else 'sk-demo-placeholder-key'
    if not key:
        raise SystemExit('--live 는 HCHAT_API_KEY 환경변수가 필요합니다')
    pg.fill('#apiKey', key)
    pg.click('#connectBtn')
    pg.wait_for_selector('#keyStatus.ok, #keyStatus.err', state='attached', timeout=90000)
    if 'err' in pg.get_attribute('#keyStatus', 'class'):
        raise SystemExit('연결 실패: ' + pg.inner_text('#keyStatus')[:200])


def analyze(pg):
    pg.click('#anaBtn')
    pg.wait_for_function("!document.querySelector('#analysis .loading')", timeout=180000)
    pg.wait_for_timeout(300)


def ask(pg, q):
    pg.fill('#chatIn', q)
    pg.press('#chatIn', 'Enter')
    pg.wait_for_function("!document.querySelector('#chatlog .loading')", timeout=180000)
    pg.wait_for_timeout(300)


def box(pg, sel, pad=6):
    b = pg.locator(sel).first.bounding_box()
    return {'x': b['x'] - pad, 'y': b['y'] - pad, 'width': b['width'] + pad * 2, 'height': b['height'] + pad * 2}


def shot(pg, name, **kw):
    pg.evaluate('document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0);'
                " const w = document.getElementById('tblWrap'); if (w) w.scrollTop = 0")
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
<div class="r"><i class="i" style="background:#6A9E3B">JS</i>server.js<span>심부름꾼 (AI · 뉴스 검색)</span></div>
<div class="r"><i class="i" style="background:#4A6FA5">MD</i>보고서기준.md<span>분석 목차</span></div>
<div class="r"><i class="i" style="background:#7C8698">BAT</i>실행.bat<span>더블클릭 · Node 확인까지</span></div></div>
<div class="z"><i class="i" style="background:#C28A2C">ZIP</i><b>뉴스동향리포트.zip</b><span>0.1 MB · 메일로 그냥 전달</span></div>
</body></html>"""


def main():
    work = pathlib.Path(tempfile.mkdtemp(prefix='news-m4-'))
    try:
        for name in ['app.html', 'server.js', '보고서기준.md', '예비_검색결과.json']:
            shutil.copy2(DONE / name, work)
        for f in (DONE / '단계별').glob('*.html'):
            shutil.copy2(f, work)
        proc, url = start(work)
        print('서버 :', url, '(실제 검색 · Claude)' if LIVE else '(예비 검색 결과 · 자리표시 응답)')
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
        ctx = b.new_context(viewport=VIEW)
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        # Phase 1 — 가짜 데이터 초안
        pg.goto(url + '/phase1.html'); pg.wait_for_timeout(300)
        shot(pg, 'm4n-phase1.png')

        # Phase 2 — 실제 기사로 채운 화면 (AI 없음)
        pg.goto(url + '/phase2.html'); pg.wait_for_timeout(200)
        do_search(pg, uncheck=False)
        shot(pg, 'm4n-phase2.png')

        # Phase 4 완성본 — 빈 화면 · 대시보드 · 체크 빼기 · 분석 · 보고서
        pg.goto(url + '/app.html'); pg.wait_for_timeout(300)
        shot(pg, 'm4n-empty.png')
        do_search(pg)
        shot(pg, 'm4n-dash.png')
        # 체크를 뺀 기사가 보이는 자리 — 목록 카드만
        first_off = pg.evaluate('arts.find(a => !a.on).n')
        pg.evaluate('(n) => { const w = document.getElementById("tblWrap"); const r = w.querySelector(`tr[data-n="${n}"]`);'
                    ' w.scrollTop = r.previousElementSibling.previousElementSibling.offsetTop - w.querySelector("thead").offsetHeight; }', first_off)
        pg.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        pg.wait_for_timeout(150)
        pg.screenshot(path=str(IMG / 'm4n-pick.png'), clip=box(pg, '#dash > .card', 4))
        print('  + m4n-pick.png')

        connect(pg); analyze(pg)
        shot(pg, 'm4n-ai.png')
        pg.set_viewport_size({'width': 1440, 'height': 1200})   # 분석 칸이 넉넉히 보이게
        pg.wait_for_timeout(200)
        shot(pg, 'm4n-ai-crop.png', clip=box(pg, 'aside.ai .card'))

        # 보고서 출력 — 새 창
        with ctx.expect_page() as info:
            pg.click('#reportBtn')
        rp = info.value
        rp.set_viewport_size({'width': 900, 'height': 900})
        rp.wait_for_load_state(); rp.wait_for_timeout(300)
        rp.screenshot(path=str(IMG / 'm4n-report.png'), full_page=True)
        print('  + m4n-report.png')
        rp.close()

        # 보고서기준.md 를 한 줄 바꾸고 다시 분석 (파일을 고치면 누를 때 바로 반영된다)
        # 전후 모두 분석 칸의 끝을 찍는다 — 바꾼 뒤에는 맨 끝에 덩어리 하나가 새로 붙는다
        pg.set_viewport_size({'width': 1440, 'height': 1100})
        tail = "document.getElementById('analysis').scrollTop = 1e6"
        pg.evaluate(tail); pg.wait_for_timeout(150)
        pg.screenshot(path=str(IMG / 'm4n-rule-before.png'), clip=box(pg, '#analysis', 8))
        print('  + m4n-rule-before.png')
        md = work / '보고서기준.md'
        md.write_text(md.read_text(encoding='utf-8') + IDEA_LINE, encoding='utf-8')
        analyze(pg)
        pg.evaluate(tail); pg.wait_for_timeout(150)
        pg.screenshot(path=str(IMG / 'm4n-rule-after.png'), clip=box(pg, '#analysis', 8))
        print('  + m4n-rule-after.png')
        pg.set_viewport_size(VIEW)

        # 대화는 새로 열어 찍는다 — 분석과 같이 두면 대화 칸이 좁다
        pg.goto(url + '/app.html'); pg.wait_for_timeout(200)
        do_search(pg); connect(pg)
        ask(pg, '제네시스는 무엇을 했어?')
        shot(pg, 'm4n-chat.png')
        shot(pg, 'm4n-chat-crop.png', clip=box(pg, 'aside.ai .card--chat'))

        # 배포 폴더 그림
        dp = b.new_page(device_scale_factor=2)
        dp.set_content(DIST_CARD)
        dp.screenshot(path=str(IMG / 'm4n-dist-zip.png'), clip=box(dp, 'body', 0))
        print('  + m4n-dist-zip.png')

        b.close()
        if errs:
            print('  ! 화면 오류:', errs)


if __name__ == '__main__':
    main()
