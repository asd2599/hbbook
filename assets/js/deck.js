/* ==========================================================================
   슬라이드 덱 공통 동작
   - 이동 : 키보드(← →, PageUp/Down, Space, Home/End) · 마우스 휠 · 상단 화살표 · 터치 스와이프
   - 화면 : 창 크기에 맞춰 슬라이드(1280×720)를 통째로 스케일
   - 주소 : 현재 장 번호를 해시(#3)로 동기화 → 새로고침·북마크 시 그 장으로 복귀

   한 문서에 덱이 여러 개 들어갈 수 있다 (배포용 단일 HTML).
   `[data-deck]` 요소가 있으면 그 안을 각각 하나의 덱으로 다루고,
   없으면 문서 전체를 덱 하나로 다룬다. 바깥에서는 `window.deckAPI` 로 제어한다.
   ========================================================================== */
(function () {

  /* ---- 외부 링크는 새 탭으로 (문서 전체에 1회) -------------------------- */
  /* 교안을 띄워둔 채로 자료를 열 수 있도록, 바깥 사이트로 나가는 링크는
     모두 새 탭에서 연다. 목차로 돌아가는 상대경로 링크는 그대로 둔다.       */
  [].forEach.call(document.querySelectorAll('a[href]'), function (a) {
    var external = (a.protocol === 'http:' || a.protocol === 'https:') && a.host !== location.host;
    if (!external) return;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
  });

  /* ---- 프롬프트 복사 버튼 (문서 전체에 1회) ------------------------------ */
  /* 화면의 문장을 받아 적지 않도록, .pbox 상자마다 [복사] 버튼을 붙인다.
     복사 대상은 제목(.pbox-t)을 뺀 상자 안의 문장 전체다.                   */
  function copyFallback(text) {          // clipboard API를 못 쓰는 환경 대비
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;top:-1000px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  /* 상자마다 '어느 도구에 넣는 프롬프트인지' 이름표를 붙인다.
     상자에 data-app 이 있으면 그것을, 없으면 <body data-app> 의 값을 쓴다. */
  [].forEach.call(document.querySelectorAll('.pbox'), function (box) {
    var holder = box.closest ? box.closest('[data-app]') : null;   // 배포본은 덱마다 다르다
    var app = (holder && holder.getAttribute('data-app'))
              || document.body.getAttribute('data-app') || '';
    if (app) {
      var tag = document.createElement('span');
      tag.className = 'pbox-app';
      tag.textContent = app;
      box.appendChild(tag);          // 위치는 absolute — 맨 앞에 넣으면 p:first-child 가 깨진다
      if (!box.getAttribute('data-kind')) {
        box.setAttribute('data-kind', /claude\s*code/i.test(app) ? 'code' : 'chat');
      }
    }
  });

  [].forEach.call(document.querySelectorAll('.pbox'), function (box) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pbox-copy';
    btn.textContent = '복사';

    function flash(ok) {
      btn.textContent = ok ? '복사됨' : '복사 실패';
      btn.classList.toggle('is-done', ok);
      setTimeout(function () {
        btn.textContent = '복사';
        btn.classList.remove('is-done');
      }, 1600);
    }

    btn.addEventListener('click', function () {
      var text = [].map.call(box.querySelectorAll('p:not(.pbox-t)'), function (p) {
        return p.textContent.trim();
      }).join('\n');

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () { flash(true); },
          function () { flash(copyFallback(text)); }
        );
      } else {
        flash(copyFallback(text));
      }
    });

    box.appendChild(btn);
  });

  /* ---- 정답 확인 상자 (문서 전체에 1회) ---------------------------------- */
  /* .quiz 상자에 답을 적고 [확인]을 누르면 맞는지 알려주고 정답을 펼친다.
     비교는 숫자만 뽑아서 한다 — "99:1", "99 대 1", "99/1" 모두 같은 답으로 본다. */
  [].forEach.call(document.querySelectorAll('.quiz'), function (box) {
    var input = box.querySelector('.quiz-in');
    var btn   = box.querySelector('.quiz-btn');
    var ans   = box.querySelector('.quiz-ans');

    var mark = document.createElement('span');
    mark.className = 'quiz-mark';
    if (btn && btn.parentNode) btn.parentNode.appendChild(mark);

    function nums(text) {
      return (String(text).match(/\d+/g) || []).map(Number);
    }

    function check() {
      var want = nums(box.getAttribute('data-answer') || '');
      var got  = nums(input ? input.value : '');
      var ok = want.length > 0 && got.length === want.length &&
               want.every(function (n, i) { return n === got[i]; });

      box.classList.toggle('is-ok', ok);
      box.classList.toggle('is-no', !ok);
      mark.textContent = ok ? '정답입니다' : '아쉽네요, 다시 한번';
      if (ans && ok) ans.hidden = false;      // 정답일 때만 해설을 연다
    }

    if (btn) btn.addEventListener('click', check);
    if (input) input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); check(); }
    });
  });

  /* ---- 덱 하나 ------------------------------------------------------------ */
  function makeDeck(root, id) {
    var slides = [].slice.call(root.querySelectorAll('.slide'));
    if (!slides.length) return null;

    var idx     = 0;
    var prevBtn = root.querySelector('#prev, .js-prev');
    var nextBtn = root.querySelector('#next, .js-next');
    var countEl = root.querySelector('#count, .js-count');

    /* 상단 바의 'n / N' 을 번호 입력칸으로 바꾼다 — 숫자를 넣고 Enter 면 그 장으로 */
    var jumpEl = null, totalEl = null;
    if (countEl) {
      countEl.textContent = '';
      jumpEl = document.createElement('input');
      jumpEl.type = 'text';
      jumpEl.className = 'deck-jump';
      jumpEl.setAttribute('inputmode', 'numeric');
      jumpEl.setAttribute('aria-label', '슬라이드 번호로 이동');
      jumpEl.title = '번호를 입력하고 Enter';
      totalEl = document.createElement('span');
      totalEl.className = 'deck-total';
      countEl.appendChild(jumpEl);
      countEl.appendChild(totalEl);
    }

    /* 슬라이드 우하단 페이지 번호 (표지 제외) */
    slides.forEach(function (s, i) {
      if (s.classList.contains('slide--cover')) return;
      var n = document.createElement('div');
      n.className = 'slide-no';
      n.textContent = (i + 1) + ' / ' + slides.length;
      s.appendChild(n);
    });

    function render(writeHash) {
      slides.forEach(function (s, i) { s.classList.toggle('is-active', i === idx); });
      if (jumpEl) {
        if (document.activeElement !== jumpEl) jumpEl.value = idx + 1;
        totalEl.textContent = '/ ' + slides.length;
      } else if (countEl) {
        countEl.textContent = (idx + 1) + ' / ' + slides.length;
      }
      if (prevBtn) prevBtn.disabled = idx === 0;
      if (nextBtn) nextBtn.disabled = idx === slides.length - 1;
      markNow();
      if (writeHash !== false && history.replaceState) {
        history.replaceState(null, '', '#' + (id ? id + '/' : '') + (idx + 1));
      }
    }

    function go(n) {
      var next = Math.max(0, Math.min(slides.length - 1, n));
      if (next === idx) return false;
      idx = next;
      render();
      return true;
    }

    if (prevBtn) prevBtn.addEventListener('click', function () { go(idx - 1); });
    if (nextBtn) nextBtn.addEventListener('click', function () { go(idx + 1); });

    if (jumpEl) {
      jumpEl.addEventListener('focus', function () { jumpEl.select(); });
      jumpEl.addEventListener('blur',  function () { jumpEl.value = idx + 1; });
      jumpEl.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          var n = parseInt(jumpEl.value, 10);
          if (!isNaN(n)) { go(n - 1); render(); }
          jumpEl.blur();
          e.preventDefault();
        } else if (e.key === 'Escape') {
          jumpEl.value = idx + 1;
          jumpEl.blur();
          e.preventDefault();
        } else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' ||
                   e.key === 'PageDown'   || e.key === 'PageUp') {
          /* 숫자만 넣는 칸이라 화살표를 쓸 일이 없다.
             이 칸을 한 번 눌렀다는 이유로 넘김이 막히지 않도록 그대로 넘긴다. */
          jumpEl.blur();
          go(idx + (e.key === 'ArrowLeft' || e.key === 'PageUp' ? -1 : 1));
          e.preventDefault();
        }
      });
    }

    /* ---- 왼쪽 챕터 서랍 --------------------------------------------- */
    /* data-chapter 를 단 슬라이드(챕터 표지 · 정리)를 모아 목차를 만든다.
       상단 바의 [챕터] 버튼으로 열고 닫고, 항목을 누르면 그 장으로 간다.   */
    var marks = [];
    slides.forEach(function (s, i) {
      var t = s.getAttribute('data-chapter');
      if (t) marks.push({ i: i, t: t, end: !s.classList.contains('slide--chapter') });
    });

    var side = null, sideBtn = null, items = [];

    if (marks.length) {
      var bar  = root.querySelector('.deck-bar');
      var home = root.querySelector('.deck-home');

      sideBtn = document.createElement('button');
      sideBtn.type = 'button';
      sideBtn.className = 'deck-chapters';
      sideBtn.setAttribute('aria-expanded', 'false');
      sideBtn.innerHTML = '<span class="dc-bars"><i></i><i></i><i></i></span>챕터';

      side = document.createElement('aside');
      side.className = 'deck-side';
      side.setAttribute('aria-label', '챕터 목록');

      var head = document.createElement('p');
      head.className = 'ds-head';
      head.textContent = '챕터';
      side.appendChild(head);

      var list = document.createElement('ol');
      list.className = 'ds-list';

      var no = 0;
      marks.forEach(function (m) {
        var li = document.createElement('li');
        var b  = document.createElement('button');
        b.type = 'button';
        b.className = 'ds-item';
        if (!m.end) no += 1;
        b.innerHTML =
          '<span class="ds-no' + (m.end ? ' ds-no--end' : '') + '">' + (m.end ? '·' : no) + '</span>' +
          '<span class="ds-t"></span>' +
          '<span class="ds-page">' + (m.i + 1) + '</span>';
        b.querySelector('.ds-t').textContent = m.t;
        b.addEventListener('click', function () { go(m.i); });
        li.appendChild(b);
        list.appendChild(li);
        items.push(b);
      });

      side.appendChild(list);

      if (bar && home && home.parentNode === bar) bar.insertBefore(sideBtn, home.nextSibling);
      else if (bar) bar.insertBefore(sideBtn, bar.firstChild);
      (root === document ? document.body : root).appendChild(side);

      sideBtn.addEventListener('click', function () {
        toggleSide(!side.classList.contains('is-open'));
      });
      /* 창이 좁으면 슬라이드가 너무 작아지므로 접어 둔 채로 시작한다 */
      toggleSide(window.innerWidth >= 1180);
    }

    function toggleSide(open) {
      if (!side) return;
      side.classList.toggle('is-open', open);
      sideBtn.classList.toggle('is-open', open);
      sideBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      syncSide();
    }
    function closeSide() { toggleSide(false); }
    function sideOpen() { return !!side && side.classList.contains('is-open'); }

    /* 서랍이 차지하는 폭을 무대에 알려 준다 — 슬라이드가 그만큼 비켜 앉는다 */
    function syncSide() {
      var css = getComputedStyle(document.documentElement);
      var w = (css.getPropertyValue('--side-open-w') || '282px').trim();
      document.documentElement.style.setProperty('--side-w', sideOpen() ? w : '0px');
      fit();
    }

    /* 지금 보고 있는 장이 속한 챕터를 표시한다 */
    function markNow() {
      if (!items.length) return;
      var cur = -1;
      for (var k = 0; k < marks.length; k++) if (marks[k].i <= idx) cur = k;
      items.forEach(function (b, k) { b.classList.toggle('is-now', k === cur); });
    }

    return {
      id: id,
      root: root,
      count: slides.length,
      go: go,
      render: render,
      markNow: markNow,
      closeSide: closeSide,
      sideOpen: sideOpen,
      syncSide: syncSide,
      at: function () { return idx; },
      set: function (n) { idx = Math.max(0, Math.min(slides.length - 1, n)); }
    };
  }

  var nodes = [].slice.call(document.querySelectorAll('[data-deck]'));
  var decks = [];

  if (nodes.length) {
    nodes.forEach(function (n) {
      var d = makeDeck(n, n.getAttribute('data-deck'));
      if (d) decks.push(d);
    });
  } else {
    var only = makeDeck(document, '');
    if (only) decks.push(only);
  }
  if (!decks.length) return;

  var active = decks[0];

  window.deckAPI = {
    decks: decks,
    current: function () { return active; },
    setActive: function (id, n) {
      for (var i = 0; i < decks.length; i++) {
        if (decks[i].id === id) {
          active = decks[i];
          if (typeof n === 'number') active.set(n - 1);
          active.render();
          if (active.syncSide) active.syncSide(); else fit();
          return active;
        }
      }
      return null;
    }
  };

  /* ---- 화면 맞춤 스케일 -------------------------------------------------- */
  /* 상·하 바 높이와 여백을 뺀 영역에 슬라이드가 통째로 들어가도록 축소/확대한다.
     비율을 유지하므로 어떤 창 크기에서도 잘리지 않는다.                      */
  var CHROME_H = 128;   // 상단 바 56 + 하단 여백 + 상하 마진
  var CHROME_W = 48;

  function fit() {
    var cs = getComputedStyle(document.documentElement);
    var w = parseFloat(cs.getPropertyValue('--slide-w'));
    var h = parseFloat(cs.getPropertyValue('--slide-h'));
    var side = parseFloat(cs.getPropertyValue('--side-w')) || 0;
    var scale = Math.min(
      (window.innerWidth  - CHROME_W - side) / w,
      (window.innerHeight - CHROME_H) / h
    );
    document.documentElement.style.setProperty('--scale', Math.min(scale, 1.35));
  }

  /* ---- 키보드 ------------------------------------------------------------ */
  document.addEventListener('keydown', function (e) {
    if (e.defaultPrevented || e.ctrlKey || e.altKey || e.metaKey) return;
    var t = e.target;                       // 입력칸에 글을 쓰는 중이면 슬라이드를 넘기지 않는다
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'VIDEO' ||
              t.isContentEditable)) return;
    switch (e.key) {
      case 'ArrowRight': case 'PageDown': case ' ': active.go(active.at() + 1); e.preventDefault(); break;
      case 'ArrowLeft':  case 'PageUp':          active.go(active.at() - 1); e.preventDefault(); break;
      case 'Home':                               active.go(0); e.preventDefault(); break;
      case 'End':                                active.go(active.count - 1); e.preventDefault(); break;
      case 'Escape':
        if (active.sideOpen && active.sideOpen()) { active.closeSide(); e.preventDefault(); break; }
        if (typeof window.deckHome === 'function') window.deckHome();
        else location.href = 'index.html';
        break;
    }
  });

  /* ---- 마우스 휠 ---------------------------------------------------------- */
  /* 휠 한 번에 여러 장이 넘어가지 않도록 잠금을 건다.
     관성 스크롤(트랙패드)은 이벤트가 연속으로 오므로, 잠금이 풀리는 동안
     계속 들어오는 이벤트는 무시하고 타이머를 연장한다.                        */
  var LOCK_INERTIA = 450;    // 트랙패드 관성 — 길게 잠그고, 계속 들어오면 연장한다
  var LOCK_STEP    = 150;    // 마우스 휠 한 칸 — 짧게만 잠근다 (연달아 굴려도 넘어가게)
  var WHEEL_MIN    = 12;     // 무시할 미세 델타
  var STEP_DELTA   = 80;     // 이만큼 크면 '뚜렷한 한 칸' 으로 본다
  var wheelLocked = false;
  var wheelTimer  = null;

  window.addEventListener('wheel', function (e) {
    if (typeof window.deckIsHome === 'function' && window.deckIsHome()) return;
    var d = Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
    if (Math.abs(d) < WHEEL_MIN) return;
    e.preventDefault();

    /* 마우스 휠 한 칸은 델타가 크고 뚝뚝 끊긴다. 트랙패드 관성은 작은 델타가 연달아 온다. */
    var step = e.deltaMode !== 0 || Math.abs(d) >= STEP_DELTA;

    if (wheelLocked) {
      if (!step) {                           // 관성 구간 — 타이머만 연장하고 흘려보낸다
        clearTimeout(wheelTimer);
        wheelTimer = setTimeout(function () { wheelLocked = false; }, LOCK_INERTIA);
      }
      return;
    }

    active.go(d > 0 ? active.at() + 1 : active.at() - 1);
    wheelLocked = true;
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(function () { wheelLocked = false; },
                            step ? LOCK_STEP : LOCK_INERTIA);
  }, { passive: false });

  /* ---- 터치 스와이프 ------------------------------------------------------ */
  var touchX = null;
  window.addEventListener('touchstart', function (e) {
    touchX = e.changedTouches[0].clientX;
  }, { passive: true });

  window.addEventListener('touchend', function (e) {
    if (touchX === null) return;
    var dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 60) active.go(dx < 0 ? active.at() + 1 : active.at() - 1);
    touchX = null;
  }, { passive: true });

  /* ---- 리사이즈 ----------------------------------------------------------- */
  window.addEventListener('resize', function () {
    // 창이 좁아지면 서랍을 접어 슬라이드를 살린다
    if (active.sideOpen && active.sideOpen() && window.innerWidth < 1180) active.closeSide();
    else fit();
  });

  /* ---- 시작 --------------------------------------------------------------- */
  fit();

  var hash  = (location.hash || '').slice(1).split('/');
  var deckId = hash.length > 1 ? hash[0] : '';
  var start  = parseInt(hash[hash.length - 1], 10);

  if (deckId) {
    for (var i = 0; i < decks.length; i++) if (decks[i].id === deckId) active = decks[i];
  }
  if (!isNaN(start)) active.set(start - 1);

  // 여러 덱 문서에서는 라우터가 보여줄 덱을 정하므로 해시를 덮어쓰지 않는다.
  active.render(nodes.length === 0);
})();
