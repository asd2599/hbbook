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
| `.cards` / `.card` | 파란 그라데이션 카드 (3분할 등) |
| `.agenda` | 일정 표. 모듈 셀에 `class="m"`, 빈칸은 `class="blank"` |
| `.note` / `.note--warn` | 안내 박스 / 주의 박스(빨강) |
| `.pbox` / `.pbox-t` | 그대로 붙여넣는 프롬프트 상자. **[복사] 버튼은 `deck.js`가 자동으로 붙인다** |
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

- 본문이 슬라이드 아래로 잘리지 않는가
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
- `deck.js` 는 한 문서에 덱이 여러 개 있어도 동작합니다.
  `[data-deck]` 요소가 있으면 그 안을 각각 덱으로 다루고, 없으면 문서 전체를 덱 하나로 다룹니다.
- 새 모듈을 만들면 `tools/build-single.py` 의 `MODULES` 목록에 추가합니다.

---

## 9. 인쇄

`@media print` 에서 상단 바를 숨기고 슬라이드를 모두 펼쳐 **1장 = 1페이지**로 출력합니다.
브라우저 인쇄에서 **가로 방향 · 배경 그래픽 켜기**로 설정하면 PDF 배포본을 만들 수 있습니다.
