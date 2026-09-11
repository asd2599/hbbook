# -*- coding: utf-8 -*-
"""
배포용 단일 HTML 빌드

목차(index.html)와 모듈 교안(ot / m1 / m2 …)을 한 파일로 합치고,
CSS · JS · 이미지를 모두 본문에 넣어 파일 하나만으로 열리게 만든다.

    python tools/build-single.py

결과물 : dist/AX중급과정_교안.html

- 원본 파일은 건드리지 않는다. 슬라이드를 고친 뒤 이 스크립트를 다시 돌리면 된다.
- 목차에서 모듈 카드를 누르면 그 교안이 열리고, `← 목차` 또는 Esc 로 돌아온다.
- 주소 해시는 `#m1/3` 형태 — 새로고침해도 그 장에서 시작한다.
"""
import base64
import mimetypes
import shutil
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
OUT = DIST / 'AX중급과정_교안.html'

# 목차에 실을 순서. (파일, 덱 id, 목차 카드 링크 대상)
MODULES = [
    ('m1.html', 'm1'),
    ('m2.html', 'm2'),
    ('m3.html', 'm3'),
    ('m4.html', 'm4'),
    ('m5.html', 'm5'),
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
    html = re.sub(r'(url\()(assets/img/[^)]+)(\))', sub, html)
    return html


def body_of(html):
    return html.split('<body>', 1)[1].rsplit('</body>', 1)[0]


def style_of(html):
    m = re.search(r'<style>(.*?)</style>', html, re.S)
    return m.group(1) if m else ''


def build_deck(fname, deck_id):
    """모듈 교안 한 편을 <div class="deck" data-deck="…"> 로 감싼다.

    모듈 고유 스타일(<head> 안의 <style>)도 함께 돌려준다.
    이걸 빠뜨리면 배포본에서 그 모듈의 레이아웃만 조용히 무너진다.
    """
    html = read(fname)
    body = body_of(html)
    css = inline_images(style_of(html))

    # 스크립트 태그 제거 (공용 JS는 마지막에 한 번만 넣는다)
    body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.S)

    # id 는 문서 안에서 하나뿐이어야 하므로 클래스로 바꾼다
    body = body.replace('class="deck-arrow" id="prev"', 'class="deck-arrow js-prev"')
    body = body.replace('class="deck-arrow" id="next"', 'class="deck-arrow js-next"')
    body = body.replace('class="deck-count" id="count"', 'class="deck-count js-count"')

    body = inline_images(body)
    deck = '<div class="deck" data-deck="%s" hidden>\n%s\n</div>\n' % (deck_id, body.strip())
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


def main():
    index_html = read('index.html')
    deck_css = read('assets/css/deck.css')
    deck_js = read('assets/js/deck.js')

    # 모듈 고유 스타일을 먼저 모은다 (head 의 <style> 에 함께 넣기 위해)
    decks, module_css = [], []
    for fname, deck_id in MODULES:
        print('  + %s → data-deck="%s"' % (fname, deck_id))
        css, deck = build_deck(fname, deck_id)
        if css.strip():
            module_css.append('/* ---- %s 고유 스타일 ---- */\n%s' % (fname, css.strip()))
        decks.append(deck)

    # 목차 — 모듈 카드 링크를 덱 전환으로 바꾼다
    home = body_of(index_html)
    for fname, deck_id in MODULES:
        home = home.replace('href="%s"' % fname, 'href="#%s" data-go="%s"' % (deck_id, deck_id))
    home = inline_images(home)

    parts = [
        '<!DOCTYPE html>',
        '<html lang="ko">',
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>AX 중급과정 강의 교안</title>',
        '<style>',
        deck_css,
        style_of(index_html),
        '\n'.join(module_css),
        EXTRA_CSS,
        '</style>',
        '</head>',
        '<body>',
        '',
        '<div id="home">',
        home.strip(),
        '</div>',
        '',
    ]

    parts += decks

    parts += [
        '<script>',
        deck_js,
        ROUTER,
        '</script>',
        '</body>',
        '</html>',
        '',
    ]

    DIST.mkdir(exist_ok=True)
    OUT.write_text('\n'.join(parts), encoding='utf-8')
    size = OUT.stat().st_size / 1024 / 1024
    print('완료 : %s (%.1f MB)' % (OUT.relative_to(ROOT), size))

    # 우수사례 원본 HTML 은 본문에 넣지 않고 파일째 함께 둔다 (M4 사례 슬라이드의 링크 대상).
    cases_src = ROOT / 'assets' / '우수사례'
    if cases_src.is_dir():
        cases_dst = DIST / 'assets' / '우수사례'
        cases_dst.mkdir(parents=True, exist_ok=True)
        total = 0
        for f in sorted(cases_src.glob('*.html')):
            shutil.copy2(f, cases_dst / f.name)
            total += f.stat().st_size
        print('  . 우수사례 : %d개 (%.1f MB) → dist/assets/우수사례/' %
              (len(list(cases_src.glob('*.html'))), total / 1024 / 1024))
        print('  > 배포할 때 HTML 과 assets 폴더를 함께 전달해야 사례 링크가 열립니다.')

    # 실습자료도 함께 넣는다 — 배포본 폴더가 그대로 '강의자료' 가 된다.
    # 교육생은 dist/실습자료/M4 실습3 Base 에서 바로 `code .` 로 실습을 시작한다.
    prac_src = ROOT / 'assets' / '실습자료'
    if prac_src.is_dir():
        prac_dst = DIST / '실습자료'
        if prac_dst.exists():
            shutil.rmtree(prac_dst)
        shutil.copytree(prac_src, prac_dst)
        files = [f for f in prac_dst.rglob('*') if f.is_file()]
        print('  . 실습자료 : %d개 파일 (%.1f MB) → dist/실습자료/' %
              (len(files), sum(f.stat().st_size for f in files) / 1024 / 1024))

    # 영상은 경로 없이 파일 이름으로만 참조한다 (본문에 넣지 않는다).
    # dist/ 안에 mp4 가 함께 있어야 재생된다.
    videos = sorted(DIST.glob('*.mp4'))
    for mp4 in videos:
        print('  . 영상 : %s (%.0f MB)' % (mp4.name, mp4.stat().st_size / 1024 / 1024))
    if videos:
        print('  > 배포할 때 HTML 과 mp4 를 같은 폴더에 함께 전달하세요.')
    else:
        print('  ! dist 안에 mp4 가 없습니다 - OT 4p 영상이 재생되지 않습니다.')


if __name__ == '__main__':
    sys.exit(main())
