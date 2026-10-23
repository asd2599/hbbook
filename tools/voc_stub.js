// 고객 VOC 현황판 M4 — 스크린샷용 AI 응답 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
// /v1/messages 에는 미리 정해 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
//   · 원문 분류 — 낱말을 보고 감성 · 주제를 붙인다 (돌릴 때마다 같은 결과)
//   · 요약 · 대화 — 답 속 숫자는 화면이 보낸 집계(JSON)에서 채운다 — 화면과 숫자가 어긋나지 않는다
// 진짜 응답으로 다시 찍으려면 tools/voc-shots.py 를 --live 로 돌린다.
//
//   node tools/voc_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8796);

const POS = /친절|감사|만족|좋았|편리/;
const NEG = /소음|냄새|안 열|자주 뜹|불규칙|덜컹|떨림|늦게|다시 생겼|오래 걸|불편|멈|끊|재부팅|안 됩|안 먹|꺼졌|밀려|안 된다|어렵|대기|세 군데|다음 달|미뤄|모릅|지연|늦어지|답이 없|연락이 없|못 받|처리가 안|안 나옵/;
const TOPIC = [
  [/방법을 알/, '사용 방법'], [/EV|전기차|배터리|충전구/, 'EV 정비 예약'],
  [/업데이트|화면|블루투스|터치|재부팅|휴대폰|카메라/, '화면·연결 오류'], [/소음|덜컹|떨림/, '소음·진동'],
  [/냄새|에어컨/, '에어컨 냄새'], [/출고/, '출고 일정'], [/비용/, '정비 비용'], [/예약/, '정비 예약'], [/수리/, '수리 품질'],
  [/상담/, '상담 응대'], [/친절|감사|만족|좋았|편리/, '칭찬'],
  [/연비|옵션|트림|공간|루프랙|원격|시승|하이브리드/, '사양 확인'], [/혜택|계약|환불|색상/, '계약·혜택'],
  [/리콜|점검 주기|보증/, '보증·점검'], [/경고등/, '경고등'], [/트렁크|와이퍼|창문|시동/, '부품 작동'],
];

function classify(content) {
  const out = [];
  for (const line of content.split('\n')) {
    const m = line.match(/^(\d+)\. \[(.+?) · (.+?)\] (.*)$/);
    if (!m) continue;
    const t = m[4];
    const s = POS.test(t) ? '긍정' : NEG.test(t) ? '부정' : '중립';
    const topic = (TOPIC.find(([re]) => re.test(t)) || [0, '기타 문의'])[1];
    out.push({ n: Number(m[1]), 감성: s, 주제: topic });
  }
  return JSON.stringify(out);
}

function pick(ctx) {
  const cell = (car, type) => (ctx.차종x유형 || []).find(g => g.차종 === car && g.유형 === type) || { 주별건수: [] };
  const raw = k => ((ctx.급증원문 || {})[k] || []);
  const tagged = typeof ctx.AI분류 === 'object';
  return { cell, raw, tagged, all: ctx.전체 || {}, late: ctx.지연문의 || [] };
}
const w = g => g.주별건수 || [];
const last = (g, i) => w(g)[w(g).length - i];
const pct = x => (x > 0 ? '+' : '') + Math.round(x) + '%';

function summary(ctx) {
  const d = pick(ctx), a = d.all, tu = d.cell('투싼', '품질'), io = d.cell('아이오닉 5', '서비스'), gr = d.cell('그랜저', '판매·계약');
  const tuRaw = d.raw('투싼 · 품질'), upd = tuRaw.filter(r => /업데이트/.test(r.문의)).length;
  const old = d.late.slice().sort((x, y) => y.경과일 - x.경과일)[0];
  const s = ctx.AI분류;
  return `■ 한눈에
${ctx.이번주} 접수는 ${a.이번주}건으로 전주(${a.전주}건)보다 ${pct(a.전주대비)} 늘었습니다.
급증 기준에 걸린 곳은 **${(ctx.급증 || []).length}곳**(${(ctx.급증 || []).join(' · ')}), 7일 넘게 처리 중인 문의는 **${a.지연}건**입니다.
${d.tagged ? `AI 분류로는 이번 주 부정 ${s.부정}건 · 긍정 ${s.긍정}건 · 중립 ${s.중립}건입니다.` : '원문 분류는 아직 하지 않았습니다.'}
■ 먼저 볼 곳
1. 투싼 · 품질 — ${last(tu, 2)} → ${last(tu, 1)}건(${pct(tu.전주대비)})${d.tagged ? `, 부정 비율 ${tu.부정비율}%` : ''}
2. 아이오닉 5 · 서비스 — ${last(io, 2)} → ${last(io, 1)}건(${pct(io.전주대비)})${d.tagged ? `, 부정 비율 ${io.부정비율}%` : ''}
3. 처리 지연 ${d.late.length}건 — 가장 오래된 것은 ${old ? `${old.차종} · ${old.유형}(${old.경과일}일째)` : '-'}
■ 고객이 말하는 것
투싼 품질 문의 ${tuRaw.length}건 가운데 **${upd}건이 「9월 소프트웨어 업데이트 뒤」 화면 멈춤 · 블루투스 끊김**을 말합니다.
아이오닉 5 서비스는 **EV 정비 예약이 밀린다**는 말이 반복됩니다.
그랜저 판매·계약도 ${last(gr, 2)} → ${last(gr, 1)}건으로 늘었고 **출고 지연** 문의가 섞여 있습니다(기준에는 걸리지 않음).
■ 다음 주 할 일
업데이트와 화면 멈춤이 관련 있는지 **품질 부서 확인이 필요합니다.**
EV 정비가 되는 서비스센터와 예약 대기를 확인하고, 지연 ${d.late.length}건은 담당자에게 회신 일정을 받는 것이 좋겠습니다.`;
}

function askTucson(ctx) {
  const d = pick(ctx), tu = d.cell('투싼', '품질'), raw = d.raw('투싼 · 품질');
  const upd = raw.filter(r => /업데이트/.test(r.문의)), neg = raw.filter(r => r.감성 === '부정').length;
  const lateTu = d.late.filter(r => r.차종 === '투싼' && r.유형 === '품질').length;
  return `투싼 · 품질 문의는 ${w(tu).join(' → ')}건으로, 이번 주가 전주보다 **${pct(tu.전주대비)}** 늘었습니다.
- 이번 주 ${raw.length}건 중 **${upd.length}건**이 업데이트를 말합니다 — 「${upd[0] ? upd[0].문의 : ''}」 · 「${upd[1] ? upd[1].문의 : ''}」
${d.tagged ? `- AI 분류로는 ${raw.length}건 중 ${neg}건이 부정, 주요 주제는 ${(tu.주요주제 || []).join(' · ')}\n` : ''}- 지난주에 접수된 투싼 품질 문의 ${lateTu}건은 아직 처리 중입니다
원문만으로 업데이트가 원인이라고 단정할 수는 없어, **품질 부서 확인이 필요합니다.**`;
}

function answer(body) {
  const last = [...(body.messages || [])].reverse().find(m => m.role === 'user');
  const q = String((last && last.content) || '');
  if (/^ping$/i.test(q.trim())) return 'pong';
  const sys = String(body.system || '');
  if (sys.includes('분류하는 보조자')) return classify(q);
  const ctx = JSON.parse(sys.slice(sys.indexOf('{')) || '{}');
  if (q.includes('■')) return summary(ctx);
  if (q.includes('투싼')) return askTucson(ctx);
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
      }, 300);
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
