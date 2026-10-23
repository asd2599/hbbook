// 설비 가동률 현황판 M4 — 스크린샷용 AI 응답 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
// /v1/messages 에는 미리 적어 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
// 답 속 숫자는 화면이 보낸 집계(JSON)에서 채운다 — 화면과 숫자가 어긋나지 않는다.
// 진짜 응답으로 다시 찍으려면 tools/equip-shots.py 를 --live 로 돌린다.
//
//   node tools/equip_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8792);
const C2 = '크랭크 연삭기 #2', LK = '리크테스터 #2';

const SUMMARY = `■ 한눈에
9월 가동률은 엔진가공 {{line:엔진가공|2026-09}}% · 변속기조립 {{line:변속기조립|2026-09}}% 입니다.
석 달 동안 설비기준에 걸린 것은 **{{flag}}건**이고, 9월에는 **${C2} · ${LK}** 두 대가 걸렸습니다.
${C2} 는 7월 {{rate:${C2}|2026-07}}% → 8월 {{rate:${C2}|2026-08}}% → 9월 **{{rate:${C2}|2026-09}}%** 로 석 달째 떨어지고 있습니다.
■ 먼저 볼 설비
1. ${C2} — 9월 {{rate:${C2}|2026-09}}%, 고장 {{cnt:${C2}|2026-09}}건이 모두 「주축 과열」
2. ${LK} — 8월 {{rate:${LK}|2026-08}}% 에서 9월 {{rate:${LK}|2026-09}}% 로 급락, 「센서 오작동」 {{cause:${LK}|2026-09|센서 오작동}}건
3. 세척기 — 기준 안이지만 {{rate:세척기|2026-07}} → {{rate:세척기|2026-08}} → {{rate:세척기|2026-09}}% 로 조금씩 내려가고 있습니다
■ 반복되는 고장 원인
「주축 과열」은 ${C2} 에서만 석 달 동안 **{{causeSum:${C2}|주축 과열}}건** — 달마다 늘고 있습니다.
블록 CNC #2 의 8월 「공구 파손」({{cause:블록 CNC #2|2026-08|공구 파손}}건)은 9월에 {{rate:블록 CNC #2|2026-09}}% 로 회복했습니다. 조치가 끝났는지만 확인하면 됩니다.
■ 점검 제안
${C2} 는 주축 쪽(베어링 · 냉각 계통) 점검이 필요해 보입니다.
${LK} 는 센서 교정 상태를, 세척기는 「필터 막힘」이 늘고 있어 필터 교체 주기를 확인하는 것이 좋겠습니다.`;

const Q_CRANK = `${C2} 의 고장은 석 달 모두 **「주축 과열」 한 가지**입니다.
- 7월 {{rate:${C2}|2026-07}}% · 고장 {{cnt:${C2}|2026-07}}건 ({{ftime:${C2}|2026-07}}분)
- 8월 {{rate:${C2}|2026-08}}% · 고장 {{cnt:${C2}|2026-08}}건 ({{ftime:${C2}|2026-08}}분)
- 9월 **{{rate:${C2}|2026-09}}%** · 고장 {{cnt:${C2}|2026-09}}건 ({{ftime:${C2}|2026-09}}분)
같은 원인이 건수와 시간 모두 늘고 있어, 일시적인 문제보다는 **주축 쪽 상태가 나빠지고 있을 가능성**이 있습니다. 현장 점검으로 확인이 필요합니다.
같은 엔진가공 라인의 크랭크 연삭기 #1 은 9월 {{rate:크랭크 연삭기 #1|2026-09}}% 로 정상입니다.`;

const Q_TM = `변속기조립 라인 전체는 7월 {{line:변속기조립|2026-07}}% → 8월 {{line:변속기조립|2026-08}}% → 9월 {{line:변속기조립|2026-09}}% 로 큰 변화가 없습니다.
다만 **${LK}** 한 대가 9월에 {{rate:${LK}|2026-09}}% 로 떨어져 설비기준에 걸렸습니다 (전월 대비 {{diff:${LK}|2026-09}}%p).
9월 고장 {{cnt:${LK}|2026-09}}건 가운데 「센서 오작동」이 {{cause:${LK}|2026-09|센서 오작동}}건으로, 8월까지는 없던 원인입니다. 센서 교정 · 교체 이력을 확인해 보는 것이 좋겠습니다.`;

function fill(text, ctx) {
  const cells = ctx.설비별월집계 || [];
  const cell = (eq, m) => cells.find(c => c.설비 === eq && c.월 === m) || {};
  return text.replace(/\{\{(.+?)\}\}/g, (_, k) => {
    const [kind, rest] = k.includes(':') ? [k.slice(0, k.indexOf(':')), k.slice(k.indexOf(':') + 1)] : [k, ''];
    const a = rest.split('|');
    const one = (v) => v === undefined || v === null ? '?' : String(v);
    const pct = (v) => v === undefined || v === null ? '?' : Number(v).toFixed(1);   // 가동률은 늘 소수 한 자리
    if (kind === 'flag') return String(ctx.주의건수);
    if (kind === 'line') return pct((ctx.라인별월가동률[a[0]] || {})[a[1]]);
    if (kind === 'rate') return pct(cell(a[0], a[1]).가동률);
    if (kind === 'diff') return pct(cell(a[0], a[1]).전월대비);
    if (kind === 'cnt') return one(cell(a[0], a[1]).고장건수);
    if (kind === 'ftime') return one(cell(a[0], a[1]).고장시간);
    if (kind === 'cause') return one((cell(a[0], a[1]).원인별건수 || {})[a[2]] || 0);
    if (kind === 'causeSum') return String(cells.filter(c => c.설비 === a[0]).reduce((s, c) => s + ((c.원인별건수 || {})[a[1]] || 0), 0));
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
  if (q.includes('크랭크')) return fill(Q_CRANK, ctx);
  if (q.includes('변속기')) return fill(Q_TM, ctx);
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
