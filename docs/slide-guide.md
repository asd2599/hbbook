# 슬라이드 구현 가이드

AX 중급과정 HTML 교안의 **화면 구조·조작·마크업 규칙**을 정리한 문서입니다.
새 모듈 교안(`m1.html` ~ `m5.html`)을 만들 때 이 문서를 그대로 따릅니다.

- 교안 **내용**의 기준은 [`curriculum.md`](curriculum.md)
- 교안 **구현**의 기준은 이 문서

---

## 1. 파일 구조

```
index.html            목차 — 스크롤 없이 한 화면. OT·M1~M5 카드에서 각 교안으로 진입
ot.html               OT 교안 (9장)
m1.html               M1 교안 (20장)
m2.html               M2 교안 (25장)
m3.html               M3 교안 (37장)
m4.html               M4 교안 (44장)
m5.html               M5 교안 (16장)
timer.html            실습 타이머 — 강사가 직접 여는 작은 창 (`?m=분`)
assets/css/deck.css   공통 슬라이드 스타일 (전 모듈 공유)
assets/js/deck.js     슬라이드 이동 · 화면 맞춤 스케일 · 해시 동기화
assets/img/           화면 캡처 · 로고
```

- 교안 HTML은 **프로젝트 루트**에 둡니다. 이미지·CSS·JS 경로가 `assets/...` 상대경로이므로 하위 폴더로 옮기면 깨집니다.
- 새 교안은 `ot.html`을 복제해 만듭니다. CSS·JS는 공통 파일을 그대로 링크하고,
  모듈 고유 스타일이 필요하면 해당 HTML의 `<style>`에만 둡니다. **`deck.css`는 전 모듈 공용**이므로
  한 모듈만을 위한 규칙을 넣지 않습니다.

---

## 2. 화면 구조

```
┌─────────────────────────────────────────────────┐
│  .deck-bar   (fixed, 높이 56px)                  │  ← 목차 · ‹ · 제목 n/N · › · 조작 안내
├─────────────────────────────────────────────────┤
│  .stage      (fixed, inset: 56px 0 0 0)          │
│                                                  │
│        ┌───────────────────────────┐             │
│        │  .slide  1280 × 720 고정   │  ← 통째로   │
│        │                            │     스케일  │
│        └───────────────────────────┘             │
└─────────────────────────────────────────────────┘
```

### 스케일 방식

슬라이드는 **1280×720 (16:9) 고정 크기**로 작성하고,
`deck.js`가 창 크기에 맞춰 `--scale` 변수를 계산해 `transform: scale()`로 통째로 축소·확대합니다.

```js
scale = min((innerWidth - 48) / 1280, (innerHeight - 128) / 720)   // 최대 1.35배
```

- 비율이 유지되므로 어떤 창 크기에서도 잘리거나 일그러지지 않습니다.
- 반대로 **본문이 720px를 넘으면 그 부분은 그냥 잘립니다.** 넘치면 자동으로 줄어들지 않습니다.
- 따라서 슬라이드를 추가·수정하면 **반드시 렌더링을 확인**합니다 (§7).

### 본문 영역 실측

| 영역 | 크기 |
|---|---|
| 슬라이드 전체 | 1280 × 720 |
| `.slide-head` (제목 바) | 높이 77 |
| `.slide-body` 바깥 여백 | 상 46 · 좌우 84 · 하 56 |
| **`.slide-body` 실사용 폭** | **1112** |
| **`.slide-body` 실사용 높이** | **약 541** |

가로로 이미지를 나열할 때는 `이미지 폭 합 + gap 합 ≤ 1112` 을 지켜야 합니다.

### 본문 세로 정렬

`.slide-body` 는 `display:flex; flex-direction:column; justify-content: safe center` 입니다.
내용이 적은 슬라이드는 **세로 가운데**에 놓여 위아래 여백이 균등해지고,
내용이 541px를 넘으면 `safe` 키워드 덕분에 위쪽 정렬로 자동 복귀해 **위가 잘리지 않습니다.**

- 위쪽부터 채워야 하는 슬라이드는 `.slide-body slide-body--top` 을 씁니다.
- **주의** — flex 컨테이너라 자식 간 마진이 상쇄(margin collapsing)되지 않습니다.
  앞 요소의 `margin-bottom` 과 뒤 요소의 `margin-top` 이 **그대로 더해집니다.**
  일반 문서 흐름 기준으로 여백을 계산하면 예상보다 커지므로, 한쪽 마진만 쓰는 편이 안전합니다.

---

## 3. 조작 방법

| 동작 | 방법 |
|---|---|
| 다음 | `→` · `PageDown` · `Space` · 마우스 휠 아래 · 상단 `›` · 왼쪽 스와이프 |
| 이전 | `←` · `PageUp` · 마우스 휠 위 · 상단 `‹` · 오른쪽 스와이프 |
| 처음 / 끝 | `Home` / `End` |
| 목차로 | `Esc` · 상단 `← 목차` |

### 마우스 휠 처리

휠 한 번에 여러 장이 넘어가지 않도록 **450ms 잠금**을 겁니다.
트랙패드 관성 스크롤은 이벤트가 연속으로 들어오므로, 잠금 중에 들어오는 이벤트는
무시하면서 타이머만 연장합니다. 손을 뗀 뒤 450ms가 지나야 다음 이동이 가능합니다.

상수는 `deck.js` 상단에 있습니다.

| 상수 | 기본값 | 의미 |
|---|---|---|
| `WHEEL_LOCK_MS` | `450` | 이동 후 잠금 시간 (ms) |
| `WHEEL_MIN` | `12` | 무시할 미세 델타 |
| `CHROME_H` / `CHROME_W` | `128` / `48` | 스케일 계산 시 빼는 UI 여백 |

### 외부 링크

교안 안에서 바깥 사이트로 나가는 링크는 **항상 새 탭**에서 열립니다.
`deck.js` 가 로드 시점에 `a[href]` 를 훑어 외부 링크(프로토콜이 `http/https` 이고 호스트가 다른 것)에만
`target="_blank" rel="noopener noreferrer"` 를 붙이므로, **HTML에 직접 쓰지 않아도 자동 적용**됩니다.

- 교안을 띄워둔 채로 자료를 열 수 있어 진행이 끊기지 않습니다.
- `← 목차` 같은 상대경로 링크는 대상에서 제외되어 같은 탭에서 이동합니다.
- JS가 동작하지 않는 환경까지 고려한다면 HTML에도 `target="_blank"` 를 함께 적어둡니다.

### 넘기는 방법

키보드(`← →` · `PageUp/Down` · `Space` · `Home/End`), 마우스 휠, 상단 화살표, 터치 스와이프,
그리고 상단 바의 **번호 칸에 숫자를 넣고 Enter** 로 넘깁니다.

- **번호 칸을 클릭한 상태에서도 화살표는 그대로 장을 넘깁니다.** 숫자만 넣는 칸이라,
  한 번 눌러 둔 채로 넘김이 막히지 않도록 `deck.js` 가 따로 처리합니다
  (2026-09-12 — 예전에는 이 칸에 포커스가 있으면 화살표가 전혀 안 먹었습니다).
- **마우스 휠**은 한 칸마다 넘어갑니다. 잠금은 `LOCK_STEP`(150ms) 로 짧아, 연달아 굴려도 따라옵니다.
  **트랙패드 관성**(작은 델타가 연달아 오는 구간)은 `LOCK_INERTIA`(450ms) 로 길게 잠가
  한 번에 여러 장이 넘어가지 않습니다. 구분 기준은 `STEP_DELTA`(80) 와 `deltaMode` 입니다.
- 글을 쓰는 입력칸(퀴즈 답 칸 등)에 포커스가 있을 때는 화살표가 **글자 이동**으로 쓰입니다.

### 주소 해시

현재 장 번호가 `#3` 형태로 주소에 반영됩니다. 새로고침하거나 링크를 공유하면 그 장에서 시작합니다.

---

## 4. 슬라이드 마크업

### 뼈대

```html
<div class="stage">

  <!-- 표지 -->
  <section class="slide slide--cover is-active">
    <img class="cover-logo" src="assets/img/mincoding-logo.png" alt="mincoding">
    <div class="cover-text">
      <p class="cover-eyebrow">Module 1.</p>
      <h1 class="cover-title">모듈 제목</h1>
      <p class="cover-meta">AX 중급과정 · 08:10~09:10</p>
    </div>
  </section>

  <!-- 본문 -->
  <section class="slide">
    <div class="slide-head"><h2>슬라이드 제목</h2></div>
    <div class="slide-body">
      <p class="lead">도입 문장</p>
      ...
    </div>
  </section>

</div>
```

규칙

- 슬라이드 1장 = `<section class="slide">`
- **첫 슬라이드에만** `is-active`. 나머지는 붙이지 않습니다.
- 표지·마무리는 `slide slide--cover`, 본문은 `slide-head` + `slide-body`
- 페이지 번호(`.slide-no`)는 `deck.js`가 자동으로 붙입니다. 직접 쓰지 않습니다. 표지에는 붙지 않습니다.
- **표지에는 제목만** 둡니다. `AX 중급과정 · 08:10~09:10` 같은 부제(`.cover-meta`)를 붙이지 않습니다.
  마무리 표지의 “이어서 M2 …” 같은 연결 안내는 예외로 남깁니다.
- **슬라이드 어디에도 구체적인 시간을 쓰지 않습니다.**
  시각(`08:10~09:10`)·소요시간(`60분`, `15분`) 표기를 넣지 않습니다.
  진행 순서를 보여줄 때는 시간 열을 빼고 **구분(개념/실습/공유)과 내용만** 남깁니다.
  `.head-tag` 도 `M1-2 · 실습` 처럼 세션 번호와 유형만 씁니다.
  시간 정보는 `docs/curriculum.md` 와 목차(`index.html`)에만 둡니다.

### 챕터 표지 (`.slide--chapter`)

모듈은 **챕터**로 나눕니다. 챕터가 시작되는 자리마다 표지 슬라이드를 한 장 둡니다.

```html
<section class="slide slide--chapter" data-chapter="첫 웹페이지 만들기">
  <div class="chapter">
    <p class="ch-eyebrow">CHAPTER 2</p>
    <h2 class="ch-title">첫 웹페이지 만들기</h2>
    <div class="ch-rule"></div>
    <p class="ch-desc">말로 부탁해 웹페이지를 만들고, 미리보기로 확인하고, 말로 고칩니다.</p>
    <ul class="ch-keys"><li>HTML 한 장</li><li>미리보기</li><li>Before &rarr; After</li></ul>
  </div>
</section>
```

- 네이비 전면 슬라이드입니다. `slide-head` · `slide-body` 를 쓰지 않습니다.
- **`data-chapter` 가 왼쪽 챕터 서랍의 목차 항목**이 됩니다. 제목과 같게 적습니다.
- `.ch-desc` 는 **한 줄**, `.ch-keys` 는 **2~4개**로 끊습니다. 슬라이드 목록을 그대로 옮기지 않습니다.
- 모듈 **정리 슬라이드**에도 `data-chapter="M1 정리"` 를 답니다.
  챕터 표지가 아니므로 서랍에서는 번호 대신 `·` 로 표시됩니다.
- `.head-tag` 의 챕터 번호(`M1-3 · 개념`)를 **새 챕터 번호와 일치**시킵니다.

### 왼쪽 챕터 서랍

`deck.js` 가 `data-chapter` 를 단 슬라이드를 모아 **상단 바의 [챕터] 버튼**과
**왼쪽 서랍**(`.deck-side`)을 자동으로 만듭니다. HTML 에 따로 쓸 것은 없습니다.

- **기본값은 열린 상태**입니다. 강의 중에 지금 어디쯤인지 늘 보이게 하려는 것입니다.
- **슬라이드를 가리지 않습니다.** 서랍이 열리면 `:root` 의 `--side-w` 가 `--side-open-w`(282px)로
  바뀌고, `.stage` 가 `inset: 56px 0 0 var(--side-w)` 로 그만큼 오른쪽에서 시작합니다.
  `fit()` 의 스케일 계산에서도 이 폭을 빼므로 슬라이드가 조금 작아질 뿐 잘리지 않습니다.
- **창이 좁으면 접힌 채로 시작합니다** — 너비 1180px 미만. 열려 있다가 좁아져도 접힙니다.
- 여닫기는 **[챕터] 버튼**과 `Esc` 로만 합니다 (`Esc` 는 서랍이 열려 있으면 목차로 나가지 않습니다).
  **항목을 눌러도 닫히지 않습니다** — 가리지 않으므로 열어 둔 채 계속 넘겨 볼 수 있습니다.
- 지금 보고 있는 장이 속한 챕터가 파랗게 표시됩니다.
- 배포본(단일 HTML)에서는 모듈을 바꿀 때 `deckAPI.setActive` 가 그 덱의 서랍 상태로 맞춥니다.

### 상단 바

`ot.html` 하단의 `<nav class="deck-bar">` 블록을 그대로 복사하고 두 곳만 바꿉니다.

- `.deck-title` — 모듈 제목
- `#count` 초기값 — `1 / 총장수`

`id="prev"` `id="next"` `id="count"` 는 `deck.js`가 찾는 값이므로 바꾸지 않습니다.

`#count` 안의 `n / N` 은 `deck.js` 가 **번호 입력칸**(`.deck-jump`)으로 바꿔 놓습니다.
숫자를 넣고 `Enter` 면 그 장으로 이동하고, `Esc` 면 원래 번호로 되돌아옵니다.
범위를 벗어난 숫자는 처음·마지막 장으로 맞춰집니다. HTML은 그대로 두면 됩니다.

---

## 5. 공통 클래스

### 글자 크기 바닥 (2026-09-10)

강의장 프로젝터에서 “글씨가 작아 안 보인다”는 지적이 있어 **작은 글씨의 바닥을 올렸습니다.**

- **슬라이드 안의 모든 글자는 16px 이상**입니다 (페이지 번호 제외). 새 슬라이드도 이 선을 지킵니다.
- 본문 보조 글(`.side-d` · `.steps small` · `.kv-like` · `.flow-desc`)은 **19px**,
  캡션(`.shot-cap`)과 상자 제목(`.side-t`)은 **16~17px**, 프롬프트 상자(`.pbox p`)는 **20px** 입니다.
- **인라인 SVG 라벨은 16px 이상**으로 씁니다. `viewBox` 보다 `width` 를 작게 주면 그만큼 글자도 줄어드니,
  `width ÷ viewBox` 비율을 곱한 **실제 크기**로 판단합니다 (예: viewBox 1040 · width 790 → 16px 이 12.2px 로 보임).
- 글자를 키우면 자리가 모자랍니다. **설명을 늘리지 말고 줄이세요** — 그림이 이미 말하는 문장,
  옆 상자와 겹치는 문장부터 뺍니다.

검증은 §7 의 스크립트로 합니다. `넘침 0장 · 16px 미만 0장` 이 기준입니다.

### 텍스트

| 클래스 | 용도 |
|---|---|
| `.lead` | 슬라이드 도입 문장 (네이비 27px). `.lead--lg` 는 31px |
| `.sub` | 본문 보조 문장 (22px) |
| `.block-title` | 본문 안 소제목 (네이비 25px) |
| `.dash-list` | 하이픈 목록. `<li>` 안의 `<small>` 은 회색 부연 |
| `.hl` | 빨강 강조 — 계정·비밀번호·경고 |
| `.navy` | 네이비 강조 |
| `.grn` | 초록 강조 |
| `.mono` | 고정폭 — URL·아이디·명령어 |

### 이미지

| 클래스 | 용도 |
|---|---|
| `.shots` / `.shot` / `.shot-cap` | 화면 캡처 나열 / 테두리 박스 / 캡션 |
| `.figure` | 이미지 1장 가운데 정렬 |

### 구조 컴포넌트

| 클래스 | 용도 |
|---|---|
| `.head-tag` | 제목 바 우측의 세션 표시 — `M1-2 · 실습` |
| `.flow` / `.flow-step` / `.flow-arrow` | 단계 흐름 `A → B → C`. 강조할 칸에 `.is-now` |
| `.kv` / `.kv-item` | 개념 카드 4개. 3개면 `.kv .kv--3`. 안에 `.kv-name` `.kv-like` `.kv-when` |
| `.steps` | 번호 절차 목록 (①②③ 원형 번호 자동). `<small>` 은 회색 부연 |
| `.split` / `.split-main` / `.split-side` | 2단 — 왼쪽 절차, 오른쪽 상자 |
| `.side-box` / `.side-t` / `.side-d` | 옆 상자. 주의용은 `.side-box--warn` |
| `.ba` / `.ba-col` | Before → After 2단. `.ba--before` `.ba--after`, 안에 `.ba-head` `.ba-body` `.ba-quote` |
| `.costar` / `.costar-cell` | 4열 개념 격자. 마지막 요약 칸은 `.costar-cell--sum` |
| `.recap` / `.recap-row` | 모듈 정리 — `.recap-k` (용어) + `.recap-v` (업무상 쓰임) |
| `.roadmap` / `.rm-step` | **모듈 2p 진행 맵** — 도구 이름이 아니라 **결과물 썸네일**로 보여준다. 칸마다 `.rm-pic`(이미지) · `.rm-mod`(M1~M5) · `.rm-out`(결과물 이름). 상태는 `.is-done`(✓) · `.is-now`(지금 여기) · `.is-next`(흐리게). 사이에 `.rm-arrow` |
| `.cards` / `.card` | 파란 그라데이션 카드 (3분할 등) |
| `.agenda` | 일정 표. 모듈 셀에 `class="m"`, 빈칸은 `class="blank"` |
| `.note` / `.note--warn` | 안내 박스 / 주의 박스(빨강) |
| `.pbox` / `.pbox-t` | 그대로 붙여넣는 프롬프트 상자. **검은 바탕 · 노란 글씨**로 실제 도구 화면처럼 보인다. **[복사] 버튼과 도구 이름표(`.pbox-app`)는 `deck.js`가 자동으로 붙인다** |
| `.steps--lg` / `.side-lg` | 큰 글씨 변형. 항목이 적어 여백이 남는 실습 슬라이드에서 `.steps` · `.split-side` 에 덧붙인다 |
| `.btn-link` | 외부 자료(영상·문서)로 나가는 네이비 알약 버튼. `deck.js`가 새 탭으로 열어준다 |
| `.quiz` | 답을 적고 [확인]을 눌러 정답을 여는 문제 상자. `data-answer="99 : 1"` 처럼 정답을 적어 두면 **숫자만 뽑아** 비교한다 (`.quiz-q` `.quiz-row` `.quiz-in` `.quiz-btn` `.quiz-ans`). 동작은 `deck.js` 가 붙인다 |

### 프롬프트 상자 (`.pbox`)

교육생이 화면의 문장을 받아 적지 않도록, 프롬프트는 **복사 버튼이 달린 상자**로 싣습니다.

```html
<div class="pbox">
  <p class="pbox-t">그대로 붙여넣는 문장</p>
  <p>나를 소개하는 웹페이지를 <b>HTML 파일 하나로</b> 만들어줘.</p>
  <p>디자인도 같은 파일 안에 넣고, <b>코드 전체</b>를 한 번에 보여줘.</p>
</div>
```

상자는 **Claude Code 화면처럼 검은 바탕에 노란 글씨**이고, 첫 문장 앞에 `>` 가 붙습니다.
왼쪽 위 테두리에는 **어느 도구에 넣는 프롬프트인지** 이름표가 달립니다.

- 이름표는 `<body data-app="...">` 의 값을 기본으로 씁니다 —
  **M1 · M5 `H Chat Pro` / M2 `H Chat 데스크탑` / M3 · M4 `Claude Code`**.
- 상자 하나만 다르면 그 상자에 `data-app="폴더 지침"` 처럼 직접 답니다
  (프롬프트가 아니라 *어딘가에 적어 두는 글* 인 상자 — 폴더 지침 · 프로젝트 지시사항 · 내가 적는 한 줄).
- 이름표에 `Claude Code` 가 들어가면 테두리가 **살구색**, 아니면 **파란색**이 됩니다
  (`data-kind` 를 직접 달아 바꿀 수도 있습니다).
- 줄이 많아 넘칠 것 같으면 `class="pbox pbox--tight"` 로 글씨를 18px 로 줄입니다.
- `[복사]` 버튼은 **`deck.js`가 로드 시점에 자동으로 붙입니다.** HTML에 직접 쓰지 않습니다.
- 복사되는 것은 `.pbox-t`(제목)를 뺀 **`<p>` 문장 전체**이며, 줄바꿈이 그대로 유지됩니다.
- 누르면 버튼이 `복사됨`(초록)으로 1.6초간 바뀝니다. 클립보드 API를 못 쓰는 환경에서는 `execCommand` 로 대체합니다.
- 인쇄(`@media print`)에서는 버튼이 숨겨집니다.
- 상자 오른쪽 위를 버튼이 차지하므로 **문장은 한 줄에 너무 길게 쓰지 않습니다.**

### 실습 시간 재기

**슬라이드에는 시작 버튼을 두지 않습니다.** 시간이 필요한 실습은 강사가
`timer.html?m=10` 을 직접 열어 카운트합니다 (`Space` 일시정지, `R` 다시 시작).

### 실습 슬라이드 표준 구성

실습·시연 슬라이드는 `.split` 으로 **왼쪽 절차 / 오른쪽 맥락**을 나눕니다.
오른쪽 상자 3개는 커리큘럼 설계 원칙 2번(“왜 하는가 / 무엇을 해결하는가 / 무엇이 남는가”)을 그대로 옮긴 것입니다.

```html
<div class="split">
  <div class="split-main">
    <ol class="steps"> … 커리큘럼의 '실습 상세 절차' … </ol>
  </div>
  <div class="split-side">
    <div class="side-box"><p class="side-t">왜 하는가</p><p class="side-d">…실습 목적…</p></div>
    <div class="side-box"><p class="side-t">준비물</p><p class="side-d">…사용 도구·데이터…</p></div>
    <div class="side-box side-box--warn"><p class="side-t">무엇이 남는가</p><p class="side-d">…현업 적용 포인트…</p></div>
  </div>
</div>
```

### 이미지 넣는 법

```html
<div class="shots">
  <div>
    <div class="shot" style="width:512px"><img src="assets/img/xxx.png" alt="설명"></div>
    <p class="shot-cap">① 캡션</p>
  </div>
  <div>
    <div class="shot" style="width:512px"><img src="assets/img/yyy.png" alt="설명"></div>
    <p class="shot-cap">② 캡션</p>
  </div>
</div>
```

- 폭은 `.shot` 에 인라인 `style="width:…"` 로 지정합니다. `<img>` 는 `width:100%` 로 따라갑니다.
- 기본 `gap` 은 22px. 3장을 나열할 때는 `style="gap:18px"` 정도로 줄여야 1112px 안에 들어갑니다.
- 캡처는 기존 PDF 교안에서 추출해 `assets/img/` 에 둡니다 (§6).

---

## 6. 색상과 이미지

### 색상 토큰

기존 PPT 교안(`docs/old/*.pdf`)에서 실제 픽셀값을 추출한 값입니다. **임의로 다른 색을 추가하지 않습니다.**

| 토큰 | 값 | 쓰임 |
|---|---|---|
| `--navy` | `#164194` | 헤더 바 · 제목 · 본문 강조 |
| `--navy-deep` | `#204273` | 표지 하단 블롭 |
| `--green` | `#70AD47` | 표지 액센트 |
| `--red` | `#FF0000` | 중요 표시 |
| `--gray-shape` | `#F2F2F2` | 표지 좌상단 도형 |

### PDF에서 캡처 추출

```bash
python - <<'PY'
from pypdf import PdfReader
import warnings; warnings.filterwarnings('ignore')
r = PdfReader('docs/old/M1_....pdf')
for i, p in enumerate(r.pages):
    for k, im in enumerate(p.images, 1):
        w, h = im.image.size
        if w < 200 or h < 100:      # PPT 도형 채우기용 2×2 이미지 걸러내기
            continue
        im.image.save('assets/img/m1_p%02d_%d.png' % (i + 1, k))
PY
```

페이지 안의 좌→우 순서는 `pdfplumber` 의 `page.images` 좌표(`x0`)로 확인합니다.
추출 후에는 `m1-login-site.png` 처럼 **내용을 알 수 있는 이름**으로 바꿉니다.

---

## 7. 렌더링 확인 (필수)

슬라이드를 추가·수정하면 반드시 스크린샷으로 확인합니다. 본문이 720px를 넘으면 **경고 없이 잘립니다.**

```python
import pathlib
from playwright.sync_api import sync_playwright

root = pathlib.Path(r'C:\work\hdbook')
out  = pathlib.Path('shots'); out.mkdir(exist_ok=True)

with sync_playwright() as p:
    b  = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={'width': 1440, 'height': 900})
    pg.goto((root / 'ot.html').as_uri())
    pg.wait_for_load_state('networkidle')
    n = pg.locator('.slide').count()
    for i in range(n):
        pg.screenshot(path=str(out / ('%02d.png' % (i + 1))))
        if i < n - 1:
            pg.keyboard.press('ArrowRight')
            pg.wait_for_timeout(260)
    b.close()
```

확인 항목

- 본문이 슬라이드 아래로 잘리지 않는가 (**넘침 0장**)
- 슬라이드 안에 **16px 미만 글자가 없는가** — SVG 라벨은 `width ÷ viewBox` 를 곱해 실제 크기로 잰다
- 가로 이미지 나열이 좌우 여백(84px)을 침범하지 않는가
- 상단 바의 `n / N` 과 실제 장수가 맞는가
- `index.html` 카드의 "슬라이드 N장" 표기가 맞는가

---

## 8. 배포용 단일 HTML

```bash
python tools/build-single.py     # → dist/AX중급과정_교안.html (약 8MB)
```

목차와 모든 모듈 교안을 한 파일로 합치고 CSS·JS·이미지를 본문에 넣습니다.
받는 사람은 파일 하나만 더블클릭하면 되고, 설치도 인터넷 연결도 필요 없습니다.

- 원본 파일은 그대로 두고 `dist/` 에만 결과물을 만듭니다. **`dist/` 를 직접 고치지 않습니다.**
- 목차 카드 → 해당 교안, `← 목차` 또는 `Esc` → 목차로 복귀. 주소 해시는 `#m1/3` 형태입니다.
- **영상은 본문에 넣지 않습니다.** `<video src="파일이름.mp4" controls preload="metadata">` 처럼
  **경로 없이 파일 이름만** 쓰고, 그 mp4 를 **HTML 과 같은 폴더**에 둡니다 (배포본은 `dist/` 안).
  빌드는 영상 경로를 건드리지 않으므로 원본 교안과 배포본이 같은 참조를 씁니다.
  → 배포할 때 **HTML 과 mp4 를 함께** 전달합니다. 구현 예: `ot.html` 5p.
  루트에서 `ot.html` 을 직접 열어 영상까지 확인하려면 mp4 를 **프로젝트 루트에도** 한 벌 두면 됩니다 (`.gitignore` 처리됨).
  `<video>` 에 포커스가 있을 때는 `deck.js` 가 방향키·Space 를 가로채지 않으므로 영상 탐색에 그대로 씁니다.
- 모듈 HTML `<head>` 안의 **`<style>` 블록도 함께 실립니다.** 모듈 고유 스타일을 `deck.css` 로 옮기지 마세요.
  (2026-09-10 이전 빌드는 이걸 빠뜨려서 배포본에서 그 모듈의 레이아웃만 조용히 무너졌습니다.)
- `deck.js` 는 한 문서에 덱이 여러 개 있어도 동작합니다.
  `[data-deck]` 요소가 있으면 그 안을 각각 덱으로 다루고, 없으면 문서 전체를 덱 하나로 다룹니다.
- 새 모듈을 만들면 `tools/build-single.py` 의 `MODULES` 목록에 추가합니다.

---

## 9. 인쇄

`@media print` 에서 상단 바를 숨기고 슬라이드를 모두 펼쳐 **1장 = 1페이지**로 출력합니다.
브라우저 인쇄에서 **가로 방향 · 배경 그래픽 켜기**로 설정하면 PDF 배포본을 만들 수 있습니다.
