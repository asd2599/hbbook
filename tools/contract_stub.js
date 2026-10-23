// 계약 만료 관리 현황판 M4 — 스크린샷용 AI 응답 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
// /v1/messages 에는 미리 적어 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
// 답 속 날짜 · 숫자는 화면이 보낸 집계(JSON)에서 채운다 — 화면과 숫자가 어긋나지 않는다.
// 진짜 응답으로 다시 찍으려면 tools/contract-shots.py 를 --live 로 돌린다.
//
//   node tools/contract_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8797);

const sg = x => x == null ? '신규' : (x > 0 ? '+' : '−') + Math.abs(x).toFixed(1) + '%';
const eok = x => (x / 100).toFixed(1) + '억';   // 백만원 → 억

function pick(ctx) {
  const cs = ctx.계약 || [];
  const c = w => cs.find(x => x.계약명.includes(w)) || {};
  const flagged = cs.filter(x => (x.걸린기준 || []).length);
  return { all: ctx.전체 || {}, c, flagged };
}

function summary(ctx) {
  const d = pick(ctx), a = d.all;
  const late = d.flagged.filter(x => x.걸린기준.includes('준비 늦음')), up = d.flagged.filter(x => x.걸린기준.includes('금액 급증'));
  const el = d.c('승강기'), car = d.c('렌터카'), gw = d.c('그룹웨어'), cl = d.c('청소');
  return `■ 한눈에
계약 ${a.계약}건 · 연간 ${eok(a.연간금액_백만원)} — 전년 대비 ${sg(a.전년대비)}입니다.
결정 마감이 90일 안에 오는 계약이 ${a.마감90일안}건이고, 그중 ${a.그중미착수}건은 아직 갱신 준비를 시작하지 않았습니다.
계약기준에 걸린 계약은 **${d.flagged.length}건**(준비 늦음 ${late.length} · 금액 급증 ${up.length})입니다.
■ 먼저 결정할 계약
1. 승강기 유지보수 — 결정 마감 D-${el.마감까지일수}. 비고대로 단순 갱신이면 **품의만 올리면 됩니다.**
2. 법인차량 장기렌터카 — 종료는 ${car.종료일}이지만 **자동연장이라 해지 통보 마감이 ${String(car.결정마감일).slice(5)}(D-${car.마감까지일수})** 입니다.
3. 그룹웨어 · 협업툴 라이선스 — D-${gw.마감까지일수}에 금액도 ${sg(gw.전년대비)}. **재입찰 또는 단가 협상**을 검토할 만합니다.
■ 비고에서 보이는 것
청소 · 미화 용역은 담당자 교체로 재입찰 일정이 없습니다 — 마감 D-${cl.마감까지일수}라 **이번 달 안에 일정을 잡아야** 합니다.
금액이 오른 세 건은 이유가 다릅니다 — 복합기는 **장비 교체 단가 인상**, 건강검진은 **검진 항목 추가**, 그룹웨어는 **사용자 수 증가**. 건강검진은 항목을 늘린 결정이라 인상이 자연스러울 수 있어 **확인이 필요합니다.**
■ 다음 달 할 일
렌터카 해지 통보 마감 전에 차량 대수를 확정하고, 승강기 · 청소 용역 품의와 재입찰 일정을 10월 안에 잡는 것이 좋겠습니다.`;
}

function askCar(ctx) {
  const car = pick(ctx).c('렌터카');
  return `${car.계약명}는 종료일이 **${car.종료일}**이라 넉 달이 남은 것처럼 보이지만, **자동연장 계약**이고 해지 통보기한이 **${car.해지통보기한}일 전**입니다.
그래서 결정 마감일은 **${car.결정마감일} (D-${car.마감까지일수})** 이고, 갱신상태가 아직 「${car.갱신상태}」라 「준비 늦음」에 걸렸습니다.
비고에는 「${car.비고}」라고 적혀 있습니다. 대수를 줄이려면 그 날짜 전에 변경 · 해지를 통보해야 하고, 지나면 **같은 조건으로 1년 자동연장**될 수 있습니다 — 계약서의 통보 조건은 **확인이 필요합니다.**`;
}

function answer(body) {
  const last = [...(body.messages || [])].reverse().find(m => m.role === 'user');
  const q = String((last && last.content) || '');
  if (/^ping$/i.test(q.trim())) return 'pong';
  const sys = String(body.system || '');
  const ctx = JSON.parse(sys.slice(sys.indexOf('{')) || '{}');
  if (q.includes('■')) return summary(ctx);
  if (q.includes('렌터카') || q.includes('법인차량')) return askCar(ctx);
  if (q.includes('먼저') || q.includes('결정할')) return summary(ctx).split('■ 비고')[0].split('■ 먼저 결정할 계약\n')[1];
  return '(자리표시 응답) 실제 응답은 API 키를 넣고 다시 찍어야 나옵니다.';
}

const MIME = { '.html': 'text/html; charset=utf-8', '.csv': 'text/csv; charset=utf-8', '.md': 'text/markdown; charset=utf-8' };

http.createServer((req, res) => {
  if (req.method === 'POST' && req.url.startsWith('/v1/messages')) {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => {
      const body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
      const text = answer(body);
      setTimeout(() => {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ model: 'claude-sonnet-5', content: [{ type: 'text', text }] }));
      }, 400);
    });
    return;
  }
  let rel = decodeURIComponent(req.url.split('?')[0]);
  if (rel === '/') rel = '/app.html';
  const f = path.join(ROOT, path.normalize(rel));
  if (!f.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(PORT, () => console.log('READY http://localhost:' + PORT + '  (자리표시 응답 — 실제 Claude 아님)'));
