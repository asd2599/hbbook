# -*- coding: utf-8 -*-
"""
배포용 단일 HTML 빌드

목차(index.html)와 모듈 교안(ot / m1 / m2 …)을 한 파일로 합치고,
CSS · JS · 이미지를 모두 본문에 넣어 파일 하나만으로 열리게 만든다.

    python tools/build-single.py

결과물 : dist/AX중급과정_교안.html          교육생용 (그대로 나눠 주는 파일)
        dist/AX중급과정_교안(강사용).html   강사용 — 위에 [실습 시작] · [쉬는 시간] 버튼이 더 붙는다

강사용에만 assets/css/teacher.css · assets/js/teacher.js 가 실린다.
교육생용 파일에는 그 코드가 한 줄도 들어가지 않는다.

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
OUT         = DIST / 'AX중급과정_교안.html'
OUT_TEACHER = DIST / 'AX중급과정_교안(강사용).html'

# 목차에 실을 순서. (파일, 덱 id, 목차 카드 링크 대상)
MODULES = [
    ('m1.html', 'm1'),
    ('m2.html', 'm2'),
    ('m3.html', 'm3'),
    ('m4.html', 'm4'),
    ('m5.html', 'm5'),
]

# dist/강의자료 — 교육생에게 폴더째 주는 「강의자료」.
# assets/실습자료 의 작업용 폴더 이름을 모듈 번호로 바꿔 담는다.
#   (강의자료 안 경로, 원본 폴더, 담을 파일 - 비우면 폴더째)
GUIDE_TREE = [
    ('M1',               'assets/실습자료/M1 프로젝트 실습자료',              None),
    ('M2/9월 2주차 실적',  'assets/실습자료/M2 데스크탑 실습자료/9월 2주차 실적', None),
    ('M2/주간업무메모',    'assets/실습자료/주간업무메모',                     None),
    ('M3/회의메모',       'assets/실습자료/회의메모',                         None),
    # 실행.bat 은 강사 예비본이라 주지 않는다 (교육생은 M4 배포 실습에서 직접 만든다).
    ('M4/base',          'assets/실습자료/base',   ['app.html', 'server.js', '샘플 보고서.pdf']),
    # M5 는 목업만 만든다 — PDF 도 실행.bat 도 필요 없다.
    ('M5/poc',           'assets/실습자료/base',   ['app.html', 'server.js']),
    ('M5',               'docs/M5자료',            ['M5. 나만의_업무_혁신_PoC_아이디어기획서 Work Sheet.pptx']),
    ('우수사례',          '우수사례',                None),
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


def page(home, decks, css_parts, teacher):
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
        '<title>AX 중급과정 강의 교안%s</title>' % (' (강사용)' if teacher else ''),
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


def main():
    index_html = read('index.html')
    deck_css = read('assets/css/deck.css')

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
    home = inline_images(home).strip()

    css_parts = [deck_css, style_of(index_html), '\n'.join(module_css), EXTRA_CSS]

    DIST.mkdir(exist_ok=True)
    for out, teacher in ((OUT, False), (OUT_TEACHER, True)):
        out.write_text(page(home, decks, css_parts, teacher), encoding='utf-8')
        print('완료 : %s (%.1f MB)   %s' % (
            out.name, out.stat().st_size / 1024 / 1024,
            '← 강사용 : [실습 시작] · [쉬는 시간] 포함' if teacher else '← 교육생 배포용'))

    # 우수사례 원본 HTML 은 본문에 넣지 않고 파일째 함께 둔다 (M4 사례 슬라이드의 링크 대상).
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
        print('  > 배포할 때 HTML 과 우수사례 폴더를 함께 전달해야 사례 링크가 열립니다.')

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

    # 강의자료 — 교육생에게 폴더째 주는 그 폴더다. 손으로 맞추면 반드시 어긋나므로 여기서 함께 만든다.
    guide = DIST / '강의자료'
    if guide.exists():
        shutil.rmtree(guide)
    guide.mkdir(parents=True)
    shutil.copy2(OUT, guide / OUT.name)          # 교육생용 교안 (강사용은 넣지 않는다)
    missing = []
    for dest, src, names in GUIDE_TREE:
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
                f = src_dir / name
                if f.is_file():
                    shutil.copy2(f, dst_dir / name)
                else:
                    missing.append('%s/%s' % (src, name))
    gfiles = [f for f in guide.rglob('*') if f.is_file()]
    print('  . 강의자료 : %d개 파일 (%.1f MB) → dist/강의자료/' %
          (len(gfiles), sum(f.stat().st_size for f in gfiles) / 1024 / 1024))
    print('  > 이 폴더를 그대로 압축해 교육생에게 줍니다 (강사용 교안은 들어 있지 않습니다).')
    for m in missing:
        print('  ! 강의자료에 넣을 원본을 찾지 못했습니다 : %s' % m)

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


if __name__ == '__main__':
    sys.exit(main())
