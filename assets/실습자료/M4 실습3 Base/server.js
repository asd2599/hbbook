/* ==========================================================================
   server.js — 사내망에서 Claude API 를 부르는 중계 서버
   현대자동차 AX 중급과정 · M4 실습 Base

   이 파일이 하는 일 두 가지
     1) 같은 폴더의 app.html 을 브라우저에 띄워 준다  (http://localhost:8787)
     2) 화면이 보낸 질문을 사내 Claude API 로 넘겨 주고, 답을 그대로 돌려준다

   실행 방법 : 터미널에서  node server.js
   설치할 것 : 없음 (Node 기본 모듈만 씁니다 — npm install 하지 않습니다)
   ========================================================================== */

/* ---- 발급받은 API 키를 아래 따옴표 안에 붙여넣으세요 --------------------- */
const API_KEY = '';
/* -------------------------------------------------------------------------- */

const http  = require('http');
const https = require('https');
const fs    = require('fs');
const path  = require('path');

const API_HOST = 'h-chat-api.autoever.com';
const API_PATH = '/claude-code/v2/v1/messages';
const MODEL    = 'claude-sonnet-5';
let   PORT     = 8787;

// 사내 프록시 구간의 인증서 때문에 검증을 끈다 (사내망 전용)
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'text/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.pdf':  'application/pdf',
};

/* ---- 화면이 보낸 질문을 사내 Claude API 로 넘긴다 ------------------------- */
function callClaude(bodyText, key, done) {
  let body;
  try {
    body = JSON.parse(bodyText || '{}');
  } catch (e) {
    return done(400, JSON.stringify({ error: '보낸 내용이 JSON 형식이 아닙니다.' }));
  }

  // 빠뜨리기 쉬운 값은 서버가 채워 준다
  body.model = MODEL;
  body.stream = false;
  if (!body.max_tokens) body.max_tokens = 2048;

  const payload = Buffer.from(JSON.stringify(body), 'utf8');

  // 키에 섞여 들어오는 공백·줄바꿈을 지운다 (붙여넣기 사고 방지)
  const token = String(key || '').replace(/\s+/g, '');
  if (!token) {
    return done(401, JSON.stringify({
      error: 'API 키가 없습니다. server.js 맨 위의 API_KEY 에 발급받은 키를 붙여넣으세요.'
    }));
  }

  const req = https.request({
    host: API_HOST,
    path: API_PATH,
    method: 'POST',
    rejectUnauthorized: false,
    headers: {
      // 사내 서버는 x-api-key 가 아니라 Bearer 방식을 씁니다
      'Authorization': 'Bearer ' + token,
      'anthropic-version': '2023-06-01',
      'Content-Type': 'application/json; charset=utf-8',
      'Content-Length': Buffer.byteLength(payload),
      // Origin · Referer 는 붙이지 않습니다 — 붙으면 사내 서버가 403 으로 막습니다
    },
  }, function (res) {
    let out = '';
    res.setEncoding('utf8');
    res.on('data', function (c) { out += c; });
    res.on('end', function () { done(res.statusCode, out); });
  });

  req.on('error', function (err) {
    done(502, JSON.stringify({ error: '사내 API 서버에 연결하지 못했습니다: ' + err.message }));
  });

  req.write(payload);
  req.end();
}

/* ---- 서버 ---------------------------------------------------------------- */
const server = http.createServer(function (req, res) {
  const started = Date.now();
  const pathname = String(req.url || '/').split('?')[0];

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }

  // (1) 질문 넘기기
  if (req.method === 'POST' && pathname === '/v1/messages') {
    let chunks = '';
    req.setEncoding('utf8');
    req.on('data', function (c) { chunks += c; });
    req.on('end', function () {
      const key = API_KEY || String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
      callClaude(chunks, key, function (code, text) {
        console.log(new Date().toLocaleTimeString(), 'POST /v1/messages', code,
                    (Date.now() - started) + 'ms');
        if (code >= 400) console.log('   →', String(text).slice(0, 300));
        res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(text);
      });
    });
    return;
  }

  // (2) 화면 띄우기
  const name = (pathname === '/' ? '/app.html' : pathname).replace(/^\/+/, '');
  const file = path.join(__dirname, path.normalize(name).replace(/^(\.\.[\\/])+/, ''));

  fs.readFile(file, function (err, data) {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('파일을 찾을 수 없습니다: ' + name);
    }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream' });
    res.end(data);
  });
});

/* 포트가 이미 쓰이고 있으면 하나씩 올려 가며 연다 */
server.on('error', function (err) {
  if (err.code === 'EADDRINUSE' && PORT < 8800) {
    PORT += 1;
    return server.listen(PORT);
  }
  console.error('서버를 켜지 못했습니다:', err.message);
});

server.listen(PORT, function () {
  console.log('');
  console.log('  준비됐습니다. 브라우저에서 아래 주소를 여세요.');
  console.log('     http://localhost:' + PORT);
  console.log('');
  console.log('  이 창을 닫으면 앱도 꺼집니다.');
  console.log('');
});
