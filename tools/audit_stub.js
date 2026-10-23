// 감사실 M4 — 스크린샷용 AI 응답 자리표시 서버 (교안 캡처 전용 · 배포하지 않는다)
//
// API 키 없이 교안 캡처를 찍을 때만 쓴다. server.js 와 똑같이 화면을 열어 주고,
// /v1/messages 에는 미리 적어 둔 답을 돌려준다. 실제 Claude 응답이 아니다.
// 진짜 응답으로 다시 찍으려면 tools/audit-shots.py 를 --live 로 돌린다.
//
//   node tools/audit_stub.js <앱 폴더> [포트]

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || 8790);

const SUMMARY = `■ 한눈에
석 달 302건 · 25,350,000원 가운데 **12건(4,702,400원)** 이 점검기준에 걸렸습니다.
걸린 12건 중 **5건이 구매팀 박준형** 한 사람입니다.
가장 큰 건은 9월 3일 노트북 구입 **1,250,000원**(한도 초과)입니다.
■ 먼저 소명 받을 건
1. 8/20(목) 01:35 블루문 380,000원 — 심야 + 유흥주점, 적요가 "기타"
2. 8/12 르블랑 와인바 290,000 + 275,000원 — 2분 간격 두 번 결제(분할 결제 의심)
3. 7/25(토) 그린힐CC 420,000원 — 주말 + 골프장
4. 9/18 상품권나라 500,000원 — 상품권, 받은 사람 확인 필요
■ 걸렸지만 정상일 수 있는 건
7/9 23:52 시티택시 32,400원 — 적요가 "야근 후 귀가". 근태 기록과 맞으면 정상입니다.
9/3 노트북 1,250,000원 — 업무용이 맞다면, 카드가 아니라 자산 구매 절차를 거쳤어야 하는지만 확인합니다.
■ 눈에 띄는 점
박준형(구매팀)의 걸린 금액이 1,865,000원으로 가장 많고, 적요가 "업무협의 · 기타"처럼 짧아 상대방이 드러나지 않습니다.`;

const Q_WEEKEND = `주말 사용은 **3건**입니다.
- 7/25(토) 07:10 구매팀 **박준형** · 그린힐CC(골프장) 420,000원 — 제한 업종에도 걸림
- 8/22(토) 14:20 인사팀 **강하늘** · 해피마트 분당점 187,000원 — 적요 "사무실 비품"
- 9/27(일) 23:10 영업2팀 **한도윤** · 청담 포차 164,000원 — 심야 사용에도 걸림
세 건 모두 적요만으로는 주말에 써야 했던 이유가 드러나지 않아 소명이 필요합니다.`;

const Q_BUY = `구매팀에서 걸린 **5건은 모두 박준형** 한 사람입니다. 구매팀의 다른 사람은 걸린 건이 없습니다.
- 골프장 1건(주말) · 와인바 2건(같은 날 분할 결제) · 유흥주점 1건(심야) · 상품권 1건
- 금액 합계 1,865,000원
- 적요가 "협력사 미팅 · 업무협의 · 기타 · 명절 선물"로, **누구와 무엇을 했는지**가 적혀 있지 않습니다.
협력사 접대였다면 참석자와 목적을, 상품권은 받은 사람 목록을 소명받는 것이 좋겠습니다.`;

function answer(body) {
  const last = [...(body.messages || [])].reverse().find(m => m.role === 'user');
  const q = String(last && last.content || '');
  if (/^ping$/i.test(q.trim())) return 'pong';
  if (q.includes('■')) return SUMMARY;
  if (q.includes('주말')) return Q_WEEKEND;
  if (q.includes('구매팀')) return Q_BUY;
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
