// Node 기본 모듈(http, https)만 사용하는 Claude API 중계 서버.
// 사내망 -> 이 프록시(8787) -> h-chat-api.autoever.com 내부 게이트웨이 -> Claude API

process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const http = require('http');
const https = require('https');

const START_PORT = 8787;
const UPSTREAM_HOST = 'h-chat-api.autoever.com';
const UPSTREAM_PATH = '/claude-code/v2/v1/messages';
const FORCED_MODEL = 'claude-sonnet-5';
const DEFAULT_MAX_TOKENS = 2048;

function log(...args) {
  console.log(`[${new Date().toISOString()}]`, ...args);
}

function withCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-api-key');
  return res;
}

function sendJson(res, statusCode, obj) {
  const body = Buffer.from(JSON.stringify(obj), 'utf8');
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': body.length
  });
  res.end(body);
}

// 클라이언트가 Authorization: Bearer ... 또는 x-api-key 로 보낸 키를 뽑아서
// 공백/줄바꿈을 제거한 뒤 상류로는 항상 Authorization: Bearer 형태로만 전달한다.
function extractCleanKey(headers) {
  let raw = '';
  const auth = headers['authorization'];
  if (auth) {
    raw = auth.replace(/^\s*Bearer\s+/i, '');
  } else if (headers['x-api-key']) {
    raw = headers['x-api-key'];
  }
  return raw.replace(/\s+/g, '');
}

const server = http.createServer((req, res) => {
  withCors(res);

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.method !== 'POST' || req.url.split('?')[0] !== '/v1/messages') {
    sendJson(res, 404, { error: { type: 'not_found', message: 'POST /v1/messages 만 지원합니다.' } });
    return;
  }

  const startedAt = Date.now();
  const chunks = [];

  req.on('data', (chunk) => chunks.push(chunk));

  req.on('error', (err) => {
    log('POST /v1/messages -> 요청 수신 오류:', err.message);
    if (!res.headersSent) {
      sendJson(res, 400, { error: { type: 'request_error', message: err.message } });
    }
  });

  req.on('end', () => {
    const rawBody = Buffer.concat(chunks).toString('utf8');

    let payload;
    try {
      payload = rawBody ? JSON.parse(rawBody) : {};
    } catch (e) {
      const elapsed = Date.now() - startedAt;
      log(`POST /v1/messages -> 400 (${elapsed}ms) [잘못된 JSON]`);
      log('  응답 본문 앞 300자:', String(e.message).slice(0, 300));
      sendJson(res, 400, { error: { type: 'invalid_json', message: e.message } });
      return;
    }

    payload.model = FORCED_MODEL;
    payload.stream = false;
    if (!payload.max_tokens) {
      payload.max_tokens = DEFAULT_MAX_TOKENS;
    }

    const cleanKey = extractCleanKey(req.headers);
    const outBody = Buffer.from(JSON.stringify(payload), 'utf8');

    const upstreamReq = https.request(
      {
        hostname: UPSTREAM_HOST,
        path: UPSTREAM_PATH,
        method: 'POST',
        rejectUnauthorized: false,
        headers: {
          'Authorization': `Bearer ${cleanKey}`,
          'anthropic-version': '2023-06-01',
          'Content-Type': 'application/json; charset=utf-8',
          'Content-Length': Buffer.byteLength(outBody)
        }
      },
      (upstreamRes) => {
        const respChunks = [];
        upstreamRes.on('data', (chunk) => respChunks.push(chunk));
        upstreamRes.on('end', () => {
          const elapsed = Date.now() - startedAt;
          const respBody = Buffer.concat(respChunks);
          const statusCode = upstreamRes.statusCode;

          log(`POST /v1/messages -> ${statusCode} (${elapsed}ms)`);
          if (statusCode >= 400) {
            log('  응답 본문 앞 300자:', respBody.toString('utf8').slice(0, 300));
          }

          res.writeHead(statusCode, {
            'Content-Type': upstreamRes.headers['content-type'] || 'application/json; charset=utf-8',
            'Content-Length': respBody.length
          });
          res.end(respBody);
        });
      }
    );

    upstreamReq.on('error', (err) => {
      const elapsed = Date.now() - startedAt;
      log(`POST /v1/messages -> 502 (${elapsed}ms) [상류 요청 실패]`);
      log('  응답 본문 앞 300자:', String(err.message).slice(0, 300));
      if (!res.headersSent) {
        sendJson(res, 502, { error: { type: 'upstream_error', message: err.message } });
      }
    });

    upstreamReq.end(outBody);
  });
});

function tryListen(port) {
  server.removeAllListeners('error');
  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      log(`포트 ${port} 사용 중, ${port + 1} 로 재시도`);
      tryListen(port + 1);
    } else {
      log('서버 오류:', err.message);
      process.exit(1);
    }
  });
  server.listen(port, () => {
    log(`Claude proxy 실행 중: http://localhost:${port}  (upstream: https://${UPSTREAM_HOST}${UPSTREAM_PATH})`);
  });
}

tryListen(START_PORT);
