/* ==========================================================================
   강사용 전용 동작 — 실습 타이머 · 쉬는 시간
   이 파일은 **강사용 배포본에만** 실린다 (tools/build-single.py).
   deck.js 다음에 실행된다.

   [실습 시작]  분을 넣고 시작 → 화면 위쪽에 남은 시간 카드가 뜨고 음악이 흐른다.
   [쉬는 시간]  끝낼 시각(14:00)을 넣으면 전체 화면으로 덮고 그 시각까지 센다.
   [진행 순서]  M5 「실습 진행 순서」 장에서 스텝을 누르면 「현재 실습 중」 표시가 옮겨 간다.

   음악은 실습 시간과 쉬는 시간이 **같은 한 곡을 나눠 쓴다**.
   긴 곡(세 시간짜리)을 전제로, 멈춘 자리에서 **이어서** 튼다 — 새로고침해도 이어진다.

   음악은 **로컬 mp3 우선**이다.
     1. HTML 과 같은 폴더에 `음악.mp3` 가 있으면 그걸 튼다 (오프라인 · 사내망 안전)
     2. 없거나 못 열면 유튜브 임베드로 넘어간다 (인터넷 필요 · 이어듣기는 안 된다)
   ========================================================================== */
(function () {

  var MUSIC_FILE = '음악.mp3';              // HTML 과 같은 폴더에 두면 이걸 먼저 쓴다
  var MUSIC_YT   = 'tqVWOz7ZfRE';           // 위 파일이 없을 때 쓰는 유튜브 영상
  var VOLUME     = 0.28;                    // 기본 크기 (강의 목소리를 덮지 않게) — 바꾸면 기억한다

  /* 배포본은 모듈마다 상단 바가 따로 있다 — 모든 바에 버튼을 붙이고,
     타이머 · 쉬는 시간 화면은 하나만 두고 함께 쓴다. */
  var bars = [].slice.call(document.querySelectorAll('.deck-bar'));
  if (!bars.length) return;

  /* ---- 작은 도구들 ------------------------------------------------------ */

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function mmss(ms) {                        // 남은 밀리초 → "07:42" / "1:02:30"
    var s = Math.max(0, Math.ceil(ms / 1000));
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    return h ? h + ':' + pad(m) + ':' + pad(r) : pad(m) + ':' + pad(r);
  }

  function hhmm(d) {
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    return pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  function store(key, val) {                 // file:// 에서는 막힐 수 있다
    try {
      if (val === undefined) return localStorage.getItem('ax.' + key);
      localStorage.setItem('ax.' + key, val);
    } catch (e) { /* 저장 못 해도 그냥 넘어간다 */ }
    return null;
  }

  /* 위쪽 타이머 카드가 차지하는 높이를 알려 준다 (deck.js 의 fit 과 teacher.css 가 읽는다) */
  var chromeNow = -1;
  function chrome(px) {
    px = Math.round(px);
    if (px === chromeNow) return;
    chromeNow = px;
    document.documentElement.style.setProperty('--chrome-extra', px + 'px');
    window.dispatchEvent(new Event('resize'));
  }

  /* ---- 알림음 (파일 없이 만든다) ---------------------------------------- */

  function ding(times) {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    try {
      var ctx = new Ctx();
      for (var i = 0; i < (times || 3); i++) {
        var t = ctx.currentTime + i * 0.42;
        var osc = ctx.createOscillator(), g = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, t);
        g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(0.22, t + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, t + 0.35);
        osc.connect(g); g.connect(ctx.destination);
        osc.start(t); osc.stop(t + 0.4);
      }
      setTimeout(function () { try { ctx.close(); } catch (e) {} }, (times || 3) * 500 + 600);
    } catch (e) { /* 소리를 못 내도 타이머는 그대로 돈다 */ }
  }

  /* ---- 음악 ------------------------------------------------------------- */
  /* 로컬 mp3 를 먼저 시도하고, 실패하면 유튜브 임베드로 넘어간다.
     한 번 판정하면 그 뒤로는 같은 방법만 쓴다.

     하루 종일 같은 곡 하나를 실습 · 쉬는 시간이 나눠 쓰므로,
     멈출 때 자리를 적어 두었다가 **다음에 그 자리부터** 튼다.
     새로고침하거나 다른 모듈로 옮겨도 이어지도록 자리를 저장해 둔다.        */

  var music = (function () {
    var audio = null, frame = null, mode = null, want = false;
    var vol = parseFloat(store('vol'));
    if (isNaN(vol) || vol < 0 || vol > 1) vol = VOLUME;

    var onFallback = null;                           // 유튜브로 넘어갈 때 알려 준다

    function useYouTube() {
      if (!want || frame) return;
      mode = 'yt';
      if (onFallback) onFallback();                  // 크기 조절은 유튜브에선 안 먹는다
      frame = el('iframe', 'tt-yt');
      frame.allow = 'autoplay';
      frame.setAttribute('title', '실습 배경음악');
      frame.src = 'https://www.youtube.com/embed/' + MUSIC_YT +
                  '?autoplay=1&loop=1&playlist=' + MUSIC_YT + '&controls=0&rel=0&modestbranding=1';
      document.body.appendChild(frame);
    }

    function make() {
      audio = new Audio(MUSIC_FILE);
      audio.loop = true;                               // 곡이 끝나면 처음부터 다시
      audio.volume = vol;
      audio.addEventListener('error', useYouTube);     // 파일이 없으면 여기로 온다

      /* 지난번에 멈춘 자리부터 — 길이를 알아야 자리를 옮길 수 있다 */
      var from = parseFloat(store('at') || '0');
      audio.addEventListener('loadedmetadata', function () {
        if (from > 0 && from < audio.duration - 1) audio.currentTime = from;
      });

      /* 재생 중에도 5초에 한 번씩 적어 둔다 — 새로고침 · 창을 닫아도 이어진다 */
      var last = 0;
      audio.addEventListener('timeupdate', function () {
        if (Date.now() - last < 5000) return;
        last = Date.now();
        store('at', audio.currentTime);
      });
    }

    function start() {
      want = true;
      if (mode === 'yt') { useYouTube(); return; }

      if (!audio) make();
      var p = audio.play();
      if (p && p.then) p.then(function () { mode = 'file'; }, useYouTube);
      else mode = 'file';
    }

    function stop() {
      want = false;
      if (audio) {
        try { audio.pause(); store('at', audio.currentTime); } catch (e) {}
      }
      if (frame) { frame.parentNode.removeChild(frame); frame = null; }
    }

    return {
      start: start,
      stop: stop,
      on: function () { return want; },

      /* 크기 — 인자가 없으면 지금 값(0~1)을 돌려준다. 바꾸면 기억한다. */
      vol: function (v) {
        if (v === undefined) return vol;
        vol = Math.max(0, Math.min(1, v));
        if (audio) audio.volume = vol;
        store('vol', vol);
        return vol;
      },
      /* 유튜브로 재생 중이면 크기를 못 바꾼다 (임베드는 소리 크기를 열어 주지 않는다) */
      canVol: function () { return mode !== 'yt'; },
      whenFallback: function (fn) { onFallback = fn; }
    };
  })();

  /* 창을 닫기 직전에도 자리를 남긴다 */
  window.addEventListener('pagehide', function () { if (music.on()) music.stop(); });

  /* ---- 팝오버 공통 ------------------------------------------------------ */

  var pops = [];
  function makePop(btns) {
    var pop = el('div', 'tt-pop');
    pop.hidden = true;
    document.body.appendChild(pop);
    pops.push({ pop: pop, btns: btns });

    btns.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = pop.hidden;
        closePops();
        if (open) {
          pop.hidden = false;
          btn.classList.add('is-on');
          var r = btn.getBoundingClientRect();
          pop.style.left = Math.max(12, Math.min(r.left, window.innerWidth - 308)) + 'px';
          var first = pop.querySelector('.tt-in');
          if (first) { first.focus(); first.select(); }
        }
      });
    });
    pop.addEventListener('click', function (e) { e.stopPropagation(); });
    return pop;
  }

  function closePops() {
    pops.forEach(function (p) {
      p.pop.hidden = true;
      p.btns.forEach(function (b) { b.classList.remove('is-on'); });
    });
  }
  document.addEventListener('click', closePops);

  /* ---- 상단 바 버튼 ----------------------------------------------------- */

  var ICON_PLAY =
    '<span class="tt-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="9"></circle><polyline points="10 8 16 12 10 16"></polyline>' +
    '</svg></span>';
  var ICON_COFFEE =
    '<span class="tt-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M4 9h13v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V9z"></path>' +
    '<path d="M17 10h2a2 2 0 0 1 0 4h-2"></path><path d="M8 3v3M12 3v3"></path>' +
    '</svg></span>';

  var runBtns = [], breakBtns = [];
  bars.forEach(function (bar) {
    var a = el('button', 'tt-open', ICON_PLAY + '실습 시작');
    var b = el('button', 'tt-open', ICON_COFFEE + '쉬는 시간');
    a.type = b.type = 'button';

    var hint = bar.querySelector('.deck-hint');      // 조작 안내 바로 앞 = 오른쪽 끝
    if (hint) { bar.insertBefore(a, hint); bar.insertBefore(b, hint); }
    else { bar.appendChild(a); bar.appendChild(b); }

    runBtns.push(a);
    breakBtns.push(b);
  });

  /* ---- 실습 타이머 ------------------------------------------------------ */

  var runPop = makePop(runBtns);
  runPop.innerHTML =
    '<h3>실습 시간</h3>' +
    '<p class="tt-sub">분 단위로 넣고 시작하세요. 남은 시간이 화면 위쪽에 크게 뜹니다.</p>' +
    '<div class="tt-row">' +
      '<input class="tt-in tt-min" type="text" inputmode="numeric" value="10" aria-label="실습 시간(분)">' +
      '<span class="tt-unit">분</span>' +
    '</div>' +
    '<div class="tt-quick">' +
      '<button type="button" data-min="5">5분</button>' +
      '<button type="button" data-min="10">10분</button>' +
      '<button type="button" data-min="15">15분</button>' +
      '<button type="button" data-min="20">20분</button>' +
      '<button type="button" data-min="30">30분</button>' +
    '</div>' +
    '<label class="tt-check"><input type="checkbox" class="tt-music" checked>실습 중 음악 틀기</label>' +
    '<p class="tt-err" hidden>1 ~ 240 사이의 숫자를 넣어 주세요.</p>' +
    '<button type="button" class="tt-go">시작</button>';

  var minIn    = runPop.querySelector('.tt-min');
  var musicChk = runPop.querySelector('.tt-music');
  var runErr   = runPop.querySelector('.tt-err');

  minIn.value = store('min') || '10';
  if (store('music') === '0') musicChk.checked = false;

  [].forEach.call(runPop.querySelectorAll('.tt-quick button'), function (b) {
    b.addEventListener('click', function () { minIn.value = b.getAttribute('data-min'); startRun(); });
  });
  runPop.querySelector('.tt-go').addEventListener('click', startRun);
  minIn.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); startRun(); }
  });

  var timerBar = el('div', 'tt-bar',
    '<span class="tt-state">실습 중</span>' +
    '<div class="tt-track"><i class="tt-fill"></i></div>' +
    '<span class="tt-left">00:00</span>' +
    '<span class="tt-of"></span>' +
    '<button type="button" class="tt-btn tt-pause">일시정지</button>' +
    '<button type="button" class="tt-btn tt-plus">+1분</button>' +
    '<span class="tt-vol">' +
      '<button type="button" class="tt-btn tt-snd">음악 끄기</button>' +
      '<input type="range" class="tt-range" min="0" max="100" step="1" aria-label="음악 크기">' +
      '<span class="tt-pct">0</span>' +
    '</span>' +
    '<button type="button" class="tt-btn tt-stop">종료</button>');
  timerBar.hidden = true;
  document.body.appendChild(timerBar);

  var elState = timerBar.querySelector('.tt-state');
  var elFill  = timerBar.querySelector('.tt-fill');
  var elLeft  = timerBar.querySelector('.tt-left');
  var elOf    = timerBar.querySelector('.tt-of');
  var btnPause = timerBar.querySelector('.tt-pause');
  var btnPlus  = timerBar.querySelector('.tt-plus');
  var btnSnd   = timerBar.querySelector('.tt-snd');

  var run = { end: 0, total: 0, left: 0, paused: false, done: false, tick: null };

  function startRun() {
    var m = parseInt(String(minIn.value).replace(/[^\d]/g, ''), 10);
    if (isNaN(m) || m < 1 || m > 240) { runErr.hidden = false; minIn.focus(); return; }
    runErr.hidden = true;
    store('min', m);
    store('music', musicChk.checked ? '1' : '0');
    closePops();

    run.total  = m * 60000;
    run.end    = Date.now() + run.total;
    run.paused = false;
    run.done   = false;

    timerBar.hidden = false;
    timerBar.classList.remove('is-paused', 'is-done');
    elState.textContent = '실습 중';
    elOf.textContent = m + '분';
    btnPause.textContent = '일시정지';
    document.body.classList.add('tt-run');
    fitBar();

    if (musicChk.checked) music.start(); else music.stop();
    setSndLabel();

    clearInterval(run.tick);
    run.tick = setInterval(drawRun, 250);
    drawRun();
  }

  function drawRun() {
    var left = run.paused ? run.left : run.end - Date.now();
    if (left <= 0 && !run.done) {
      left = 0;
      run.done = true;
      timerBar.classList.add('is-done');
      elState.textContent = '실습 종료';
      music.stop();
      setSndLabel();
      ding(3);
    }
    elLeft.textContent = mmss(left);
    elFill.style.width = (run.total ? Math.max(0, left) / run.total * 100 : 0) + '%';
  }

  function stopRun() {
    clearInterval(run.tick);
    run.tick = null;
    run.done = false;
    timerBar.hidden = true;
    timerBar.classList.remove('is-paused', 'is-done');
    document.body.classList.remove('tt-run');
    music.stop();
    chrome(0);
  }

  /* 카드가 실제로 차지하는 높이만큼 위쪽 자리를 비운다
     — 창이 좁아져 카드가 두 줄로 접혀도 슬라이드를 가리지 않는다. */
  function fitBar() {
    if (timerBar.hidden) return;
    chrome(timerBar.offsetHeight + 22);
  }
  window.addEventListener('resize', fitBar);

  btnPause.addEventListener('click', function () {
    if (run.done) return;
    if (run.paused) {
      run.end = Date.now() + run.left;
      run.paused = false;
      btnPause.textContent = '일시정지';
      timerBar.classList.remove('is-paused');
      if (musicChk.checked) music.start();
    } else {
      run.left = run.end - Date.now();
      run.paused = true;
      btnPause.textContent = '이어서';
      timerBar.classList.add('is-paused');
      music.stop();
    }
    setSndLabel();
    drawRun();
  });

  btnPlus.addEventListener('click', function () {
    run.total += 60000;
    if (run.paused) run.left += 60000; else run.end += 60000;
    if (run.done) {                       // 끝난 뒤에도 1분 더 줄 수 있게 되살린다
      run.done = false;
      run.end = Date.now() + 60000;
      timerBar.classList.remove('is-done');
      elState.textContent = '실습 중';
      if (musicChk.checked) music.start();
    }
    elOf.textContent = Math.round(run.total / 60000) + '분';
    drawRun();
  });

  btnSnd.addEventListener('click', function () {
    if (music.on()) music.stop(); else music.start();
    setSndLabel();
  });
  function setSndLabel() { btnSnd.textContent = music.on() ? '음악 끄기' : '음악 켜기'; }

  timerBar.querySelector('.tt-stop').addEventListener('click', stopRun);

  /* ---- 쉬는 시간 -------------------------------------------------------- */

  var breakPop = makePop(breakBtns);
  breakPop.innerHTML =
    '<h3>쉬는 시간</h3>' +
    '<p class="tt-sub">수업을 다시 시작할 시각을 넣으세요. 그때까지 화면 가득 남은 시간을 띄웁니다.</p>' +
    '<div class="tt-row">' +
      '<input class="tt-in tt-at" type="text" inputmode="numeric" placeholder="14:00" aria-label="수업 재개 시각">' +
    '</div>' +
    '<div class="tt-quick">' +
      '<button type="button" data-add="5">5분 뒤</button>' +
      '<button type="button" data-add="10">10분 뒤</button>' +
      '<button type="button" data-add="15">15분 뒤</button>' +
      '<button type="button" data-add="20">20분 뒤</button>' +
    '</div>' +
    '<label class="tt-check"><input type="checkbox" class="tt-bmusic" checked>쉬는 동안 음악 틀기</label>' +
    '<p class="tt-err" hidden>14:00 처럼 시:분 으로 넣어 주세요.</p>' +
    '<button type="button" class="tt-go">시작</button>';

  var atIn     = breakPop.querySelector('.tt-at');
  var bMusic   = breakPop.querySelector('.tt-bmusic');
  var breakErr = breakPop.querySelector('.tt-err');

  /* 팝오버를 열 때마다 '지금부터 10분 뒤' 를 기본값으로 채워 둔다 */
  breakBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (breakPop.hidden) return;
      var d = new Date(Date.now() + 10 * 60000);
      d.setSeconds(0, 0);
      atIn.value = hhmm(d);
      atIn.select();
      breakErr.hidden = true;
    });
  });

  [].forEach.call(breakPop.querySelectorAll('.tt-quick button'), function (b) {
    b.addEventListener('click', function () {
      var d = new Date(Date.now() + parseInt(b.getAttribute('data-add'), 10) * 60000);
      d.setSeconds(0, 0);
      atIn.value = hhmm(d);
      startBreak();
    });
  });
  breakPop.querySelector('.tt-go').addEventListener('click', startBreak);
  atIn.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); startBreak(); }
  });

  /* "14:00" · "1400" · "14시" 모두 받는다. 이미 지난 시각이면 다음 날로 본다. */
  function parseAt(text) {
    var s = String(text).replace(/[^\d]/g, '');
    var h, m;
    if (s.length === 3) { h = +s.slice(0, 1); m = +s.slice(1); }
    else if (s.length === 4) { h = +s.slice(0, 2); m = +s.slice(2); }
    else if (s.length === 2) { h = +s; m = 0; }
    else if (s.length === 1) { h = +s; m = 0; }
    else return null;
    if (h > 23 || m > 59) return null;

    var d = new Date();
    d.setHours(h, m, 0, 0);
    if (d.getTime() <= Date.now()) d.setDate(d.getDate() + 1);
    return d;
  }

  var overlay = el('div', 'tt-break',
    '<div class="tt-break-in">' +
      '<p class="tb-eyebrow">BREAK</p>' +
      '<h2 class="tb-title">쉬는 시간</h2>' +
      '<p class="tb-clock">00:00</p>' +
      '<p class="tb-note"></p>' +
      '<p class="tb-now"></p>' +
      '<div class="tb-acts">' +
        '<button type="button" class="tb-btn tb-plus">+5분</button>' +
        '<span class="tb-vol">' +
          '<button type="button" class="tb-btn tb-snd">음악 끄기</button>' +
          '<input type="range" class="tb-range" min="0" max="100" step="1" aria-label="음악 크기">' +
          '<span class="tb-pct">0</span>' +
        '</span>' +
        '<button type="button" class="tb-btn tb-btn--go tb-close">수업 시작</button>' +
      '</div>' +
    '</div>');
  overlay.hidden = true;
  document.body.appendChild(overlay);

  var bEye   = overlay.querySelector('.tb-eyebrow');
  var bClock = overlay.querySelector('.tb-clock');
  var bNote  = overlay.querySelector('.tb-note');
  var bNow   = overlay.querySelector('.tb-now');
  var bTitle = overlay.querySelector('.tb-title');
  var bSnd   = overlay.querySelector('.tb-snd');

  var brk = { at: null, done: false, tick: null };

  function startBreak() {
    var d = parseAt(atIn.value);
    if (!d) { breakErr.hidden = false; atIn.focus(); return; }
    breakErr.hidden = true;
    closePops();

    brk.at = d;
    brk.done = false;
    overlay.hidden = false;
    overlay.classList.remove('is-done');
    bEye.textContent = 'BREAK';
    bTitle.textContent = '쉬는 시간';
    bNote.textContent = hhmm(d) + ' 에 수업을 시작합니다';

    if (bMusic.checked) music.start(); else music.stop();
    setBSnd();

    clearInterval(brk.tick);
    brk.tick = setInterval(drawBreak, 250);
    drawBreak();
  }

  function drawBreak() {
    var left = brk.at.getTime() - Date.now();
    if (left <= 0 && !brk.done) {
      left = 0;
      brk.done = true;
      overlay.classList.add('is-done');
      bEye.textContent = 'TIME';
      bTitle.textContent = '수업을 시작합니다';
      bNote.textContent = '자리로 돌아와 주세요';
      music.stop();
      setBSnd();
      ding(4);
    }
    bClock.textContent = mmss(left);
    bNow.textContent = '지금 ' + hhmm(new Date());
  }

  function endBreak() {
    clearInterval(brk.tick);
    brk.tick = null;
    brk.done = false;
    overlay.hidden = true;
    overlay.classList.remove('is-done');
    music.stop();
  }

  overlay.querySelector('.tb-close').addEventListener('click', endBreak);
  overlay.querySelector('.tb-plus').addEventListener('click', function () {
    brk.at = new Date((brk.done ? Date.now() : brk.at.getTime()) + 5 * 60000);
    brk.done = false;
    overlay.classList.remove('is-done');
    bEye.textContent = 'BREAK';
    bTitle.textContent = '쉬는 시간';
    bNote.textContent = hhmm(brk.at) + ' 에 수업을 시작합니다';
    if (bMusic.checked) music.start();
    setBSnd();
    drawBreak();
  });
  bSnd.addEventListener('click', function () {
    if (music.on()) music.stop(); else music.start();
    setBSnd();
  });
  function setBSnd() { bSnd.textContent = music.on() ? '음악 끄기' : '음악 켜기'; }

  /* ---- 음악 크기 -------------------------------------------------------- */
  /* 실습 막대와 쉬는 시간 화면에 같은 조절기를 두고, 한쪽을 움직이면 둘 다 따라간다.
     값은 기억해 두므로 다음 실습 · 다음날에도 그대로다.                       */

  var ranges = [timerBar.querySelector('.tt-range'), overlay.querySelector('.tb-range')];
  var pcts   = [timerBar.querySelector('.tt-pct'),   overlay.querySelector('.tb-pct')];

  function showVol() {
    var pct = Math.round(music.vol() * 100);
    var ok  = music.canVol();
    ranges.forEach(function (r) {
      if (document.activeElement !== r) r.value = pct;
      r.disabled = !ok;
      r.title = ok ? '음악 크기 ' + pct + '%'
                   : '유튜브로 재생 중입니다 — 크기는 윈도우 볼륨으로 조절하세요';
    });
    pcts.forEach(function (p) { p.textContent = ok ? pct : '—'; });
  }

  ranges.forEach(function (r) {
    r.addEventListener('input', function () {
      music.vol(parseInt(r.value, 10) / 100);
      showVol();
    });
    r.addEventListener('click', function (e) { e.stopPropagation(); });
  });

  music.whenFallback(showVol);      // 유튜브로 넘어가면 조절기를 잠근다
  showVol();

  /* 쉬는 시간 화면 위에서는 슬라이드가 넘어가지 않는다 */
  function swallow(e) { e.stopPropagation(); e.preventDefault(); }
  overlay.addEventListener('wheel', swallow, { passive: false });
  overlay.addEventListener('touchstart', function (e) { e.stopPropagation(); }, { passive: true });
  overlay.addEventListener('touchend', function (e) { e.stopPropagation(); }, { passive: true });

  /* ---- 키보드 ----------------------------------------------------------- */
  /* deck.js 보다 먼저(캡처 단계) 받아서, 쉬는 시간 중에는 슬라이드를 잠근다.   */

  document.addEventListener('keydown', function (e) {
    if (!overlay.hidden) {
      if (e.key === 'Escape') { endBreak(); e.stopPropagation(); e.preventDefault(); return; }
      var t = e.target;
      if (t && (t.tagName === 'BUTTON' || t.tagName === 'INPUT')) return;
      e.stopPropagation();
      e.preventDefault();
      return;
    }
    if (e.key === 'Escape') {
      var open = pops.some(function (p) { return !p.pop.hidden; });
      if (open) { closePops(); e.stopPropagation(); e.preventDefault(); }
    }
  }, true);

  /* ---- 실습 진행 순서 (M5) ---------------------------------------------- */
  /* 스텝을 누르면 「현재 실습 중」 표시가 그 스텝으로 옮겨 간다.
     교육생용 파일에는 이 파일이 실리지 않으므로 눌러도 아무 일이 없다.        */

  [].forEach.call(document.querySelectorAll('.plan'), function (plan) {
    var steps = [].slice.call(plan.querySelectorAll('.plan-step'));
    steps.forEach(function (step) {
      step.classList.add('is-clickable');
      step.addEventListener('click', function () {
        steps.forEach(function (o) { o.classList.remove('is-now'); });
        step.classList.add('is-now');
      });
    });
  });

})();
