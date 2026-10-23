# -*- coding: utf-8 -*-
"""뉴스 분석 M4 — 실제 구글 뉴스 검색 결과를 예비 파일로 저장한다.

    python tools/news_snapshot.py

완성본 server.js 를 그대로 띄워 /search 를 불러 보고, 결과를
assets/실습자료/뉴스분석_완성본/예비_검색결과.json 에 적는다. 이 파일은 두 군데에 쓴다.

- 교안 캡처 (tools/news-shots.py) — 같은 결과로 몇 번이고 다시 찍을 수 있다
- 사내망 예비 — 교육장에서 바깥 접속이 막히면, 완성본 server.js 가 이 파일의 같은 검색어를 대신 돌려준다

수업 전날 다시 돌려 두면 예비 결과도 최신이 된다.
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DONE = ROOT / 'assets/실습자료/뉴스분석_완성본'
OUT = DONE / '예비_검색결과.json'
# 빈 화면의 예시 버튼 두 줄과 같은 검색어
QUERIES = ['현대차 마케팅', '기아 마케팅', '제네시스 마케팅', '현대차 팝업스토어', '기아 팝업스토어']
DAYS = [30, 7]


def main():
    work = pathlib.Path(tempfile.mkdtemp(prefix='news-snap-'))
    shutil.copy2(DONE / 'server.js', work)          # 예비 파일 없이 띄운다 — 진짜 검색만
    p = subprocess.Popen(['node', 'server.js'], cwd=work, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    try:
        url = None
        t0 = time.time()
        while time.time() - t0 < 15 and not url:
            m = re.search(r'READY (http://\S+)', p.stdout.readline() or '')
            url = m and m.group(1)
        if not url:
            sys.exit('server.js 가 뜨지 않았습니다')
        results, saved = {}, None
        for d in DAYS:
            for q in QUERIES:
                with urllib.request.urlopen('%s/search?q=%s&days=%d' % (url, urllib.parse.quote(q), d), timeout=30) as r:
                    data = json.load(r)
                if data.get('backup'):
                    sys.exit('바깥 접속이 안 돼 예비 결과가 돌아왔습니다 — 인터넷이 되는 곳에서 다시 돌리세요')
                results['%s|%d' % (q, d)] = data
                saved = saved or data['fetchedAt']
                print('  + %s (%d일) %d건' % (q, d, len(data['items'])))
        OUT.write_text(json.dumps({'savedAt': saved, 'results': results}, ensure_ascii=False, indent=1), encoding='utf-8')
        print('  = %s (%.0f KB)' % (OUT.relative_to(ROOT).as_posix(), OUT.stat().st_size / 1024))
    finally:
        p.kill()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
