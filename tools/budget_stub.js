// 예산 집행 현황판 M4 — 스크린샷용 AI 응답 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
// /v1/messages 에는 미리 적어 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
// 답 속 숫자는 화면이 보낸 집계(JSON)에서 채운다 — 화면과 숫자가 어긋나지 않는다.
// 진짜 응답으로 다시 찍으려면 tools/budget-shots.py 를 --live 로 돌린다.
//
//   node tools/budget_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8796);

const f1 = x => Number(x).toFixed(1);
const mil = x => Number(x).toLocaleString('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const eok = x => (x / 100).toFixed(1) + '억';   // 백만원 → 억
const gap = x => (x > 0 ? '+' : '−') + Math.abs(x).toFixed(1);

function pick(ctx) {
  const items = ctx.항목 || [];
  const it = (p, a) => items.find(x => x.프로젝트 === p && x.계정 === a) || {};
  const flagged = items.filter(x => (x.걸린기준 || []).length);
  const big = (p, a) => ((ctx.주의항목_주요집행 || []).find(x => x.프로젝트 === p && x.계정 === a) || {}).집행 || [];
  const team = t => (ctx.팀별 || []).find(x => x.팀 === t) || {};
  return { all: ctx.전체 || {}, it, flagged, big, team, teams: ctx.팀별 || [] };
}

function summary(ctx) {
  const d = pick(ctx), a = d.all;
  const fast = d.flagged.filter(x => x.걸린기준.includes('과속')), slow = d.flagged.filter(x => x.걸린기준.includes('저조'));
  const teams = d.teams.slice().sort((x, y) => x.집행률 - y.집행률);
  const expo = d.it('국제 수소 박람회 참가', '대외협력·출장'), ely = d.it('그린수소 수전해 실증', '설비투자'),
        fc = d.it('발전용 연료전지 실증', '수소 구매·운영'), pt = d.it('평택 수소충전소 구축', '설비투자'), cv = d.it('상용차 충전소 증설', '인허가·안전');
  return `■ 한눈에
9월 말 집행률 **${f1(a.집행률)}%** — 정상 페이스(75%)보다 ${f1(Math.abs(a.페이스차이_p))}%p 늦습니다.
${teams[0].팀}(${f1(teams[0].집행률)}%)이 가장 느리고 ${teams[teams.length - 1].팀}(${f1(teams[teams.length - 1].집행률)}%)이 가장 빠릅니다.
예산기준에 걸린 항목은 **${d.flagged.length}개**(과속 ${fast.length} · 저조 ${slow.length})입니다.
■ 먼저 챙길 항목
1. 국제 수소 박람회 · 대외협력·출장 — ${f1(expo.집행률)}%, **이미 예산 초과**. 조정 요청이 필요합니다.
2. 그린수소 수전해 · 설비투자 — ${f1(ely.집행률)}%. 스택 납기 지연으로 발주가 4분기로 밀려 이월 판단이 필요합니다.
3. 발전용 연료전지 · 수소 구매·운영 — ${f1(fc.집행률)}%. 잔액 ${mil(fc.잔액_백만원)}백만원으로 석 달을 버티기 어렵습니다.
■ 적요 · 비고에서 보이는 것
평택 충전소 설비투자(${f1(pt.집행률)}%)는 **계약금 선지급**이라 시점 차이일 가능성이 크지만, 4분기 기성을 낼 잔액이 있는지 **확인이 필요합니다.**
연료전지 수소 구매는 4월분부터 적요에 **「단가 인상분 반영」** — 실제로 넘칠 수 있는 과속입니다.
상용차 충전소 인허가(${f1(cv.집행률)}%)는 지자체 협의 지연으로 10월 심의를 기다리는 중입니다.
■ 4분기 운영 제안
박람회 초과분은 조정 요청, 수소 구매비는 증액 또는 전용을 검토하고, 수전해 설비는 연내 발주가 어려우면 이월 계획을 미리 세우는 것이 좋겠습니다.`;
}

function askPyeongtaek(ctx) {
  const d = pick(ctx), it = d.it('평택 수소충전소 구축', '설비투자');
  const rows = d.big('평택 수소충전소 구축', '설비투자').slice(0, 3);
  return `평택 수소충전소 구축 · 설비투자는 연간예산 ${mil(it.연간예산_백만원)}백만원 중 **${mil(it.집행_백만원)}백만원**을 써 집행률 **${f1(it.집행률)}%**(정상 페이스 ${gap(it.페이스차이_p)}%p)라 과속으로 표시됐습니다.
큰 집행을 보면
${rows.map(r => `- ${r.집행일} ${r.적요} — ${mil(r.금액_백만원)}백만원`).join('\n')}
비고에도 「${it.비고}」라고 적혀 있어, **계약금이 앞당겨 나간 시점 차이**일 가능성이 큽니다.
다만 잔액이 **${mil(it.잔액_백만원)}백만원**뿐이라 4분기에 나갈 기성 · 잔금이 올해 예산에 잡혀 있는지는 **확인이 필요합니다.**`;
}

function answer(body) {
  const last = [...(body.messages || [])].reverse().find(m => m.role === 'user');
  const q = String((last && last.content) || '');
  if (/^ping$/i.test(q.trim())) return 'pong';
  const sys = String(body.system || '');
  const ctx = JSON.parse(sys.slice(sys.indexOf('{')) || '{}');
  if (q.includes('■')) return summary(ctx);
  if (q.includes('평택')) return askPyeongtaek(ctx);
  if (q.includes('먼저') || q.includes('챙길')) return summary(ctx).split('■ 적요')[0].split('■ 먼저 챙길 항목\n')[1];
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
