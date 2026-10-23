// 뉴스 분석 M4 — 스크린샷용 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
//   /search      — 예비_검색결과.json (tools/news_snapshot.py 가 실제 구글 뉴스에서 받아 둔 것)을 돌려준다
//   /v1/messages — 미리 적어 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
// 답 속 기사 번호는 화면이 보낸 기사 목록에서 제목으로 찾아 채운다 — 체크를 뺀 기사는 인용되지 않는다.
// 진짜 응답으로 다시 찍으려면 tools/news-shots.py 를 --live 로 돌린다.
//
//   node tools/news_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8791);

const ANALYSIS = `■ 한눈에
현대차는 고객 참여형 디지털 서비스, 제네시스는 영화 · 스포츠 속 노출, 기아는 신차 · 해외 시장 소식이 중심입니다 {{창밖동화}}{{영화 ‘인턴’ 타고}}{{PV7}}
분석한 기사 {{on}}건 가운데 현대차가 {{kw:현대차 마케팅}}건으로 가장 많고, '플레오스 커넥트' 앱 공모전 기사가 한꺼번에 몰렸습니다 {{플레오스 커넥트 앱 공모전' 대상에 아반떼}}
제네시스는 {{kw:제네시스 마케팅}}건으로 적지만, 브랜드를 보여 주는 자리를 넓히는 기사가 이어집니다 {{빅텐}}
■ 키워드별 비교
**현대차** — 고객 아이디어 공모전 대상 '창밖동화' {{자동차 AI가 들려주는 동화}}, UEFA 챔피언스리그 공식 파트너 {{챔피언스리그 공식 파트너}}, 미국 딜러망 'AI 영업사원' {{AI 영업사원}}. 고객 · 스포츠 · AI 를 함께 엮습니다.
**기아** — 대형 PBV 'PV7' 공개 {{PV7}}, EV3 · EV4 · EV5 GT 유럽 출시 {{유럽 출격}}, 인도 판매 증가 {{인도 8월}} 등 제품 · 시장 소식이 많고, 브랜드 캠페인 기사는 드뭅니다.
**제네시스** — 영화 '인턴' 속 GV80 {{신스틸러}}, 美 대학스포츠 '빅텐' 공식 차량 {{빅텐}}, 현대카드 PLCC 확장 {{PLCC}} 처럼 생활 · 문화 속 노출이 중심입니다.
■ 눈여겨볼 기사 3건
1. 현대차 '창밖동화' — 고객이 낸 아이디어를 차량 앱으로 검토합니다. 기사가 가장 많이 몰린 소식입니다 {{내년 서비스 적용 검토}}
2. 제네시스 GV80, 영화 '인턴' 등장 — 영화를 '달리는 쇼룸'으로 쓰고 아시아 관객까지 노립니다 {{영화가 달리는 쇼룸}}
3. 현대차, 美 딜러망에 'AI 영업사원' — 판매 현장의 마케팅에 AI 를 넣은 사례입니다 {{AI 영업사원}}
■ 시사점
세 브랜드 모두 스포츠 · 영화처럼 '남의 무대'에 브랜드를 올리고 있습니다 {{UEFA 챔피언스리그 공식 파트너 선정}}{{신스틸러}}{{빅텐}}
고객 참여형 공모전은 발표 하루에 기사가 한꺼번에 나는 효과가 큽니다 {{플레오스 커넥트 공모전 대상에}}
제목만 보고 정리한 내용이라, 성과나 규모는 원문으로 확인해야 합니다.`;

const IDEAS = `
■ 우리가 해 볼 만한 아이디어 3개
1. 고객 아이디어 공모전 — 뽑힌 아이디어를 실제 서비스로 검토한다는 것까지 함께 알리기 {{내년 서비스 적용 검토}}
2. 영화 · 드라마 속 노출을 지역 확장 전략과 묶어 발표하기 {{아시아 정복}}
3. 스포츠 파트너십 현장에서 전시 · 시승을 함께 열어 '쇼룸'으로 쓰기 {{글로벌 쇼룸}}{{빅텐}}`;

const Q_GENESIS = `제네시스 기사 {{kw:제네시스 마케팅}}건은 크게 세 갈래입니다.
- **영화 속 노출** — 영화 '인턴'에 GV80 이 등장했고, 아시아 관객까지 넓히는 기회로 소개됩니다 {{신스틸러}}{{영화가 달리는 쇼룸}}
- **스포츠 · 고성능** — 美 대학스포츠 '빅텐' 공식 럭셔리 차량 {{빅텐}}, 르망을 달린 경주차 국내 첫 공개 {{르망 달린}}
- **제휴** — 현대카드와 PLCC 를 차 밖 일상까지 확장 {{PLCC}}
제목만 본 정리라, 계약 규모나 성과는 원문을 확인해야 합니다.`;

const Q_COMMON = `세 브랜드 모두 **스포츠 · 영화 같은 큰 무대**에 브랜드를 올리고 있습니다.
- 현대차 — UEFA 챔피언스리그 공식 파트너 {{UEFA 챔피언스리그 공식 파트너 선정}}
- 제네시스 — 영화 '인턴' {{신스틸러}} · 美 '빅텐' {{빅텐}}
- 기아 — 이번 기사에서는 제품 공개 소식이 더 많습니다 {{PV7}}
다만 기아는 브랜드 캠페인 기사가 드물어, 같은 기준으로 비교하려면 검색어를 바꿔 다시 찾아보는 것이 좋겠습니다.`;

// {{제목 일부}} → 그 제목을 가진 기사 번호, {{kw:키워드}} → 화면이 센 수, {{on}} → 분석에 쓸 기사 수
function fill(text, ctx) {
  const list = ctx.기사목록 || [];
  return text.replace(/\{\{(.+?)\}\}/g, (_, k) => {
    if (k === 'on') return String(ctx.화면이센숫자.분석에쓸기사);
    if (k.startsWith('kw:')) {
      const v = ctx.화면이센숫자.키워드별[k.slice(3)];
      return v ? String(v.분석에쓸기사) : '?';
    }
    const a = list.find((x) => x.제목.includes(k));
    return a ? ` [${a.번호}]` : '';
  }).replace(/ \[(\d+)\] \[/g, ' [$1][');
}

function answer(body) {
  const last = [...(body.messages || [])].reverse().find((m) => m.role === 'user');
  const q = String((last && last.content) || '');
  if (/^ping$/i.test(q.trim())) return 'pong';
  const sys = String(body.system || '');
  const ctx = JSON.parse(sys.split('[화면이 정리한 자료]\n')[1] || '{}');
  if (q.includes('목차대로')) return fill(ANALYSIS + (sys.includes('해 볼 만한 아이디어') ? IDEAS : ''), ctx);
  if (q.includes('제네시스')) return fill(Q_GENESIS, ctx);
  if (q.includes('공통')) return fill(Q_COMMON, ctx);
  return '(자리표시 응답) 실제 응답은 API 키를 넣고 다시 찍어야 나옵니다.';
}

function backup() {
  try { return JSON.parse(fs.readFileSync(path.join(ROOT, '예비_검색결과.json'), 'utf8')); } catch (e) { return { results: {} }; }
}

const MIME = { '.html': 'text/html; charset=utf-8', '.md': 'text/markdown; charset=utf-8', '.json': 'application/json; charset=utf-8' };
const send = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(obj)); };

http.createServer((req, res) => {
  const u = new URL(req.url, 'http://localhost');
  if (req.method === 'POST' && u.pathname === '/v1/messages') {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => {
      const body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
      const text = answer(body);
      setTimeout(() => send(res, 200, { model: 'claude-sonnet-5', content: [{ type: 'text', text }] }), 400);
    });
    return;
  }
  if (u.pathname === '/search') {
    const key = (u.searchParams.get('q') || '').trim() + '|' + (parseInt(u.searchParams.get('days'), 10) || 30);
    const hit = backup().results[key];
    return hit ? setTimeout(() => send(res, 200, hit), 250)
      : send(res, 502, { error: { type: 'search_error', message: '예비 결과에 없는 검색어입니다: ' + key } });
  }
  let rel = decodeURIComponent(u.pathname);
  if (rel === '/') rel = '/app.html';
  const f = path.join(ROOT, path.normalize(rel));
  if (!f.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    res.end(data);
  });
}).listen(PORT, () => console.log('READY http://localhost:' + PORT + '  (자리표시 응답 — 실제 Claude 아님)'));
