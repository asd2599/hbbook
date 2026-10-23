// 판매 실적 현황판 M4 — 스크린샷용 AI 응답 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
// /v1/messages 에는 미리 적어 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
// 답 속 숫자는 화면이 보낸 집계(JSON)에서 채운다 — 화면과 숫자가 어긋나지 않는다.
// 진짜 응답으로 다시 찍으려면 tools/sales-shots.py 를 --live 로 돌린다.
//
//   node tools/sales_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8793);
const E5 = '아이오닉 5', M9 = '2026-09', M8 = '2026-08', M7 = '2026-07';

const SUMMARY = `■ 한눈에
9월 전국 판매는 {{nat:판매|${M9}}}대로 BP 대비 **{{nat:달성률|${M9}}}%**, 전년 동월보다 {{nat:전년비|${M9}}}% 입니다.
석 달 동안 판매기준에 걸린 곳은 **{{flag}}건**이고, 그중 네 곳이 9월입니다.
9월에는 **서울 · 경기의 ${E5}** 가 함께 꺾인 것이 가장 큽니다.
■ 먼저 볼 곳
1. 서울 · ${E5} — 달성률 {{c:서울|${E5}|${M9}|달성률}}%, 전년비 {{c:서울|${E5}|${M9}|전년비}}% (두 기준 모두 걸림)
2. 경기 · ${E5} — 8월 {{c:경기|${E5}|${M8}|달성률}}% 에서 9월 {{c:경기|${E5}|${M9}|달성률}}% 로 급락
3. 부산경남 · 그랜저 — 7월 {{c:부산경남|그랜저|${M7}|달성률}}% → 8월 {{c:부산경남|그랜저|${M8}|달성률}}% → 9월 **{{c:부산경남|그랜저|${M9}|달성률}}%** 로 석 달째 내려가고 있습니다
■ 눈에 띄는 흐름
${E5} 는 수도권 두 곳만 떨어졌고, 다른 지역은 목표 수준입니다 — 전국으로는 {{mdl:${E5}|${M9}|달성률}}% 입니다.
강원 · 쏘나타는 달성률 {{c:강원|쏘나타|${M9}|달성률}}% 로 목표는 넘었지만 전년보다 **{{c:강원|쏘나타|${M9}|전년비}}%** 줄었습니다. 목표가 낮게 잡혔는지 확인이 필요합니다.
■ 다음 달 할 일
수도권 ${E5} 는 재고 배정 · 출고 일정 · 판촉 조건에 변화가 있었는지 확인이 필요합니다.
부산경남 그랜저는 석 달 추세라 지점별로 나눠 보는 것이 좋겠습니다.`;

const Q_EV = `데이터에는 원인이 없어 **왜** 떨어졌는지는 단정할 수 없습니다. 숫자로 보이는 것은 이렇습니다.
- 서울 8월 {{c:서울|${E5}|${M8}|달성률}}% → 9월 **{{c:서울|${E5}|${M9}|달성률}}%** (전년비 {{c:서울|${E5}|${M9}|전년비}}%)
- 경기 8월 {{c:경기|${E5}|${M8}|달성률}}% → 9월 **{{c:경기|${E5}|${M9}|달성률}}%** (전년비 {{c:경기|${E5}|${M9}|전년비}}%)
- 같은 9월 다른 지역은 충청 {{c:충청|${E5}|${M9}|달성률}}% · 호남 {{c:호남|${E5}|${M9}|달성률}}% · 부산경남 {{c:부산경남|${E5}|${M9}|달성률}}% 로 목표 수준입니다.
두 지역이 **같은 달에 함께** 꺾였으므로, 수도권에만 해당하는 변화(재고 배정 · 출고 일정 · 판촉 조건 등)가 있었는지 확인이 필요합니다.`;

const Q_GR = `부산경남 · 그랜저는 7월 {{c:부산경남|그랜저|${M7}|달성률}}% → 8월 {{c:부산경남|그랜저|${M8}|달성률}}% → 9월 **{{c:부산경남|그랜저|${M9}|달성률}}%** 로 석 달째 내려가, 9월에 판매기준(85% 미만)에 걸렸습니다.
전년비도 7월 {{c:부산경남|그랜저|${M7}|전년비}}% → 8월 {{c:부산경남|그랜저|${M8}|전년비}}% → 9월 {{c:부산경남|그랜저|${M9}|전년비}}% 로 점점 커지고 있습니다.
같은 그랜저라도 9월 서울은 {{c:서울|그랜저|${M9}|달성률}}% · 경기는 {{c:경기|그랜저|${M9}|달성률}}% 로 목표 수준이라, **부산경남 지점들을 나눠 보는 것**이 좋겠습니다.`;

function fill(text, ctx) {
  const cells = ctx.지역차종월집계 || [];
  const fmt = (field, v) => {
    if (v === undefined || v === null) return '?';
    if (field === '전년비' || field === '전월비') return (v >= 0 ? '+' : '') + Number(v).toFixed(1);
    if (field === '달성률') return Number(v).toFixed(1);
    return Number(v).toLocaleString();
  };
  return text.replace(/\{\{(.+?)\}\}/g, (_, k) => {
    if (k === 'flag') return String(ctx.주의건수);
    const kind = k.slice(0, k.indexOf(':')), a = k.slice(k.indexOf(':') + 1).split('|');
    if (kind === 'nat') return fmt(a[0], ((ctx.전국월별 || {})[a[1]] || {})[a[0]]);
    if (kind === 'reg') return fmt(a[2], (((ctx.지역월별 || {})[a[0]] || {})[a[1]] || {})[a[2]]);
    if (kind === 'mdl') return fmt(a[2], (((ctx.차종월별 || {})[a[0]] || {})[a[1]] || {})[a[2]]);
    if (kind === 'c') return fmt(a[3], (cells.find(c => c.지역 === a[0] && c.차종 === a[1] && c.월 === a[2]) || {})[a[3]]);
    return '?';
  });
}

function answer(body) {
  const last = [...(body.messages || [])].reverse().find(m => m.role === 'user');
  const q = String((last && last.content) || '');
  if (/^ping$/i.test(q.trim())) return 'pong';
  const sys = String(body.system || '');
  const ctx = JSON.parse(sys.slice(sys.indexOf('{')) || '{}');
  if (q.includes('■')) return fill(SUMMARY, ctx);
  if (q.includes('아이오닉')) return fill(Q_EV, ctx);
  if (q.includes('그랜저')) return fill(Q_GR, ctx);
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
