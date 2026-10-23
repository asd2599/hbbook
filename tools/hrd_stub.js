// 교육 만족도 현황판 M4 — 스크린샷용 AI 응답 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
// /v1/messages 에는 미리 적어 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
// 답 속 숫자는 화면이 보낸 집계(JSON)에서 채운다 — 화면과 숫자가 어긋나지 않는다.
// 진짜 응답으로 다시 찍으려면 tools/hrd-shots.py 를 --live 로 돌린다.
//
//   node tools/hrd_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8794);
const L = '신임 팀장 리더십', A = 'AI 업무 활용';

const SUMMARY = `■ 한눈에
두 과정 여섯 차수에서 {{all:응답수}}명이 응답했고, 평균 만족도는 **{{all:만족도}}점**(목표 대비 {{all:달성률}}%) 입니다.
교육기준에 걸린 차수는 **{{flag}}곳**이고, 만족도 7점 이하 응답은 {{all:7점이하}}명입니다.
가장 낮은 곳은 **${L} 2차**({{g:${L}|2차|만족도}}점) 입니다.
■ 먼저 볼 차수
1. ${L} 2차 — 평균 {{g:${L}|2차|만족도}}점, 7점 이하 {{g:${L}|2차|7점이하비율}}% (두 기준 모두 걸림)
2. ${A} 3차 — 평균은 {{g:${A}|3차|만족도}}점으로 목표에 가깝지만 7점 이하가 **{{g:${A}|3차|7점이하비율}}%** — 점수가 둘로 갈렸습니다
3. ${A} 1차 — 평균 {{g:${A}|1차|만족도}}점, 이해도 {{g:${A}|1차|이해도}}점으로 여섯 차수 중 이해도가 가장 낮습니다
■ 코멘트에서 보이는 것
리더십 2차에서 낮은 점수를 준 사람들은 대부분 **롤플레이 · 면담 실습이 빠지고 이론만 이어졌다**고 적었습니다. 현업적용도도 {{g:${L}|2차|현업적용도}}점으로 가장 낮습니다.
AI 3차의 낮은 점수는 **실습 PC · 사내망 접속 문제**에 몰려 있고, 9~10점을 준 사람들은 내용에 만족했습니다.
AI 1차는 **진도가 빨랐다**는 말이 많았고, 2차에서는 "진도가 적당했다"는 말이 나왔습니다.
■ 다음 차수 개선 제안
리더십 과정은 2차에서 롤플레이 실습이 빠진 이유와, 다음 차수에 다시 들어가는지 확인이 필요합니다.
AI 과정은 교육 전날 실습 PC 와 사내망 접속을 미리 점검하는 것이 좋겠습니다.`;

const Q_AI3 = `${A} 3차는 평균 {{g:${A}|3차|만족도}}점으로 목표({{goal}})에 가깝지만, 7점 이하가 {{g:${A}|3차|7점이하}}명(**{{g:${A}|3차|7점이하비율}}%**)이라 교육기준에 걸렸습니다.
- 7점 이하를 준 사람들은 거의 모두 **실습 PC · 사내망 접속 문제**를 적었습니다 — 「접속이 안 돼 실습 절반을 못 했다」 · 「로그인 오류로 한참 기다렸다」
- 9~10점을 준 사람들은 「실습 위주라 좋았다」 · 「강사님 설명이 쉬웠다」 처럼 내용에 만족했습니다
- 이해도도 {{g:${A}|3차|이해도}}점으로, 2차({{g:${A}|2차|이해도}}점)보다 낮습니다
내용보다 **실습 환경** 때문에 점수가 갈렸을 가능성이 있습니다. 그날 교육장 PC · 네트워크에 문제가 있었는지 확인이 필요합니다.`;

const Q_L2 = `점수만으로 원인을 단정할 수는 없지만, 코멘트에서 보이는 것은 이렇습니다.
- 평균 만족도 1차 {{g:${L}|1차|만족도}}점 → **2차 {{g:${L}|2차|만족도}}점** → 3차 {{g:${L}|3차|만족도}}점 — 2차만 크게 내려갔습니다
- 7점 이하 {{g:${L}|2차|7점이하}}명 대부분이 **롤플레이 · 면담 실습이 빠지고 이론만 이어졌다**고 적었습니다
- 현업적용도도 {{g:${L}|2차|현업적용도}}점으로 같은 과정 다른 차수보다 낮습니다
2차만 실습 구성이 달랐는지 — 강사나 교안이 바뀌었는지 확인이 필요합니다.`;

function fill(text, ctx) {
  const groups = ctx.차수별 || [];
  const fmt = (field, v) => {
    if (v === undefined || v === null) return '?';
    if (['만족도', '이해도', '추천도', '현업적용도'].includes(field)) return Number(v).toFixed(2);
    if (field === '달성률' || field === '7점이하비율') return Number(v).toFixed(1);
    return String(v);
  };
  return text.replace(/\{\{(.+?)\}\}/g, (_, k) => {
    if (k === 'flag') return String((ctx.주의차수 || []).length);
    if (k === 'goal') return ((ctx.교육기준 || {}).목표) || '?';
    const kind = k.slice(0, k.indexOf(':')), a = k.slice(k.indexOf(':') + 1).split('|');
    if (kind === 'all') return fmt(a[0], (ctx.전체 || {})[a[0]]);
    if (kind === 'g') return fmt(a[2], (groups.find(g => g.과정 === a[0] && g.차수 === a[1]) || {})[a[2]]);
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
  if (q.includes('3차') || q.includes('갈렸')) return fill(Q_AI3, ctx);
  if (q.includes('리더십')) return fill(Q_L2, ctx);
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
