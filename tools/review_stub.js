// 보안 심의 진행 현황판 M4 — 스크린샷용 AI 응답 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
// /v1/messages 에는 미리 적어 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
// 답 속 숫자 · 요청번호는 화면이 보낸 집계(JSON)에서 채운다 — 화면과 숫자가 어긋나지 않는다.
// 진짜 응답으로 다시 찍으려면 tools/review-shots.py 를 --live 로 돌린다.
//
//   node tools/review_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8795);
const SR = '보안성검토', TP = '기술보호 사내심의', GA = '정부 승인 신청';

function pick(ctx) {
  const open = ctx.진행중요청 || [];
  const flagged = open.filter(r => (r.걸린기준 || []).length);
  const of = (p, f) => flagged.filter(r => r.절차 === p && (!f || r.기술분야 === f));
  const proc = p => (ctx.절차별 || []).find(x => x.절차 === p) || {};
  const cell = (f, p) => (ctx.기술분야x절차 || []).find(x => x.기술분야 === f && x.절차 === p) || {};
  const month = (m, p) => ((ctx.월별접수 || {})[m] || {})[p] || 0;
  return { open, flagged, of, proc, cell, month, all: ctx.전체 || {} };
}
const line = r => `${r.요청번호} — 경과 ${r.경과일}일 · ${r.멈춘일수}일째 멈춤 · 「${r.최근코멘트}」`;

function summary(ctx) {
  const d = pick(ctx), a = d.all, tpA = d.of(TP, '자율주행');
  const over = d.flagged.filter(r => r.걸린기준.includes('기한 초과')).sort((x, y) => (y.경과일 - y.처리기한) - (x.경과일 - x.처리기한));
  const stallOnly = d.flagged.filter(r => !r.걸린기준.includes('기한 초과'));
  const top = [tpA.sort((x, y) => y.멈춘일수 - x.멈춘일수)[0], over.find(r => r.절차 === GA), stallOnly[0]].filter(Boolean);
  return `■ 한눈에
7~9월 세 달 동안 심의 요청 ${a.접수}건이 들어와 ${a.완료}건이 끝났습니다(완료율 **${a.완료율}%**). 완료 건의 평균 소요일은 ${Number(a.평균소요일).toFixed(1)}일입니다.
진행 중 ${a.진행중}건 가운데 심의기준에 걸린 요청은 **${d.flagged.length}건**입니다.
그중 **${tpA.length}건이 자율주행 분야 기술보호 사내심의**에 몰려 있습니다.
■ 먼저 챙길 요청
${top.map((r, i) => `${i + 1}. ${r.요청번호} ${r.절차} · ${r.기술분야} — 경과 ${r.경과일}일(기한 ${r.처리기한}일)` +
    (r.걸린기준.includes('기한 초과') ? (r.멈춘일수 >= 14 ? `, ${r.멈춘일수}일째 멈춤` : '') : `, 기한 안이지만 ${r.멈춘일수}일째 움직임이 없습니다`)).join('\n')}
■ 지연 사유에서 보이는 것
자율주행 기술보호 심의 가운데 2건은 **협력사 NDA 서명본 미제출**로 보완 요청 단계에 멈춰 있고, 1건은 위원회 심의 일정이 정해지지 않았습니다.
정부 승인 신청은 **정부 보완 요구 회신(자료 번역)** 과 **요청부서 담당자 변경**이 사유로 적혀 있습니다.
보안성검토는 9월 접수가 ${d.month('2026-09', SR)}건으로 7월(${d.month('2026-07', SR)}건)보다 늘었습니다.
■ 다음 달 할 일
자율주행 쪽 요청부서에 NDA 서명본 회신 일정을 확인하고, 10월 첫 주 위원회 일정을 확정할 필요가 있습니다.
멈춘 요청은 새 담당자를 확인해 회신 일정을 받고, 늘어난 보안성검토 접수에 맞춰 검토 인력 배정을 확인하는 것이 좋겠습니다.`;
}

function askAuto(ctx) {
  const d = pick(ctx), tpA = d.of(TP, '자율주행'), c = d.cell('자율주행', TP), p = d.proc(TP);
  return `자율주행 분야 기술보호 사내심의는 진행 중 ${c.진행중}건 가운데 **${tpA.length}건**이 심의기준에 걸렸습니다.
${tpA.map(r => '- ' + line(r)).join('\n')}
- 끝난 건도 평균 **${Number(c.평균소요일).toFixed(1)}일**로, 기술보호 사내심의 전체 평균(${Number(p.평균소요일).toFixed(1)}일)보다 깁니다
코멘트로 보면 **협력사 NDA 서명본**을 기다리는 요청이 둘입니다. 왜 자율주행 쪽 협력사에서만 늦어지는지는 요청부서에 **확인이 필요합니다.**`;
}

function answer(body) {
  const last = [...(body.messages || [])].reverse().find(m => m.role === 'user');
  const q = String((last && last.content) || '');
  if (/^ping$/i.test(q.trim())) return 'pong';
  const sys = String(body.system || '');
  const ctx = JSON.parse(sys.slice(sys.indexOf('{')) || '{}');
  if (q.includes('■')) return summary(ctx);
  if (q.includes('자율주행')) return askAuto(ctx);
  if (q.includes('먼저') || q.includes('챙길')) return summary(ctx).split('■ 지연')[0].split('■ 먼저 챙길 요청\n')[1];
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
