// Node 기본 모듈(http, https, fs, path)만 사용하는 Claude API 중계 서버.
// 사내망 -> 이 프록시(8787) -> h-chat-api.autoever.com 내부 게이트웨이 -> Claude API
//
// 화면(app.html)도 이 서버가 함께 열어 준다. 브라우저로 http://localhost:8787 에 접속하면
// 화면이 뜨고, 화면은 자기가 열린 주소로 API를 부르므로 포트가 바뀌어도 어긋나지 않는다.
//
// [뉴스 검색] GET /search?q=키워드&days=30 — 구글 뉴스 RSS 에서 최근 기사 목록을 받아 온다.
// 화면은 바깥으로 못 나가므로 이 서버가 대신 다녀온다 (Claude 를 부를 때와 같은 심부름).

process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const http = require('http');
const https = require('https');
const tls = require('tls');
const fs = require('fs');
const path = require('path');

const START_PORT = 8787;
// node server.js --open 으로 실행하면, 실제로 열린 주소를 브라우저로 띄워 준다.
// (실행.bat 이 이 옵션을 쓴다. 실습 중에는 그냥 node server.js 로 띄운다.)
const OPEN_BROWSER = process.argv.includes('--open');
const UPSTREAM_HOST = 'h-chat-api.autoever.com';
const UPSTREAM_PATH = '/claude-code/v2/v1/messages';
const FORCED_MODEL = 'claude-sonnet-5';
// 응답 길이 한도의 최소값. 화면이 더 작은 값을 보내도 이 값까지 올려 잡는다.
// 2048 로 두면 대시보드용 JSON 이 중간에 잘려서 JSON.parse 가 터진다.
const DEFAULT_MAX_TOKENS = 8192;

function log(...args) {
  console.log(`[${new Date().toISOString()}]`, ...args);
}

function openBrowser(url) {
  const { spawn } = require('child_process');
  try {
    if (process.platform === 'win32') {
      spawn('cmd', ['/c', 'start', '', url], { detached: true, stdio: 'ignore' }).unref();
    } else {
      spawn(process.platform === 'darwin' ? 'open' : 'xdg-open', [url],
        { detached: true, stdio: 'ignore' }).unref();
    }
  } catch (e) {
    log('브라우저를 자동으로 열지 못했습니다. 주소창에 직접 넣어 주세요:', url);
  }
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

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.pdf': 'application/pdf',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.csv': 'text/csv; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8'
};

// ---- 뉴스 검색 ---------------------------------------------------------------
const NEWS_HOST = 'news.google.com';
// 사내망에서 바깥 접속이 막혔을 때를 위한 예비 결과. 같은 검색어 · 기간이 들어 있으면 대신 돌려준다.
const BACKUP_FILE = path.join(__dirname, '예비_검색결과.json');

function decodeEntities(s) {
  return s.replace(/<!\[CDATA\[|\]\]>/g, '')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&');
}

// RSS 의 <item> 하나가 기사 하나. 제목 · 언론사 · 날짜 · 링크만 뽑는다 (본문은 RSS 에 없다).
function parseRss(xml) {
  return [...xml.matchAll(/<item>([^]*?)<\/item>/g)].map((m) => {
    const pick = (tag) => {
      const x = m[1].match(new RegExp('<' + tag + '[^>]*>([^]*?)</' + tag + '>'));
      return x ? decodeEntities(x[1]).trim() : '';
    };
    const source = pick('source');
    let title = pick('title');
    if (source && title.endsWith(' - ' + source)) title = title.slice(0, -(source.length + 3));
    const d = new Date(pick('pubDate'));
    return { title, source, date: isNaN(d) ? '' : d.toISOString(), link: pick('link') };
  }).filter((a) => a.title && a.link);
}

// 바깥 주소에서 글을 받아 온다. 사내망에 프록시가 있으면 HTTPS_PROXY 환경변수로 넘어간다.
function fetchText(hostname, reqPath, done) {
  const headers = { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/rss+xml, text/xml' };
  const onRes = (res) => {
    if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
      const u = new URL(res.headers.location, `https://${hostname}`);
      res.resume();
      return fetchText(u.hostname, u.pathname + u.search, done);
    }
    let body = '';
    res.setEncoding('utf8');
    res.on('data', (c) => (body += c));
    res.on('end', () => (res.statusCode === 200 ? done(null, body) : done(new Error(`HTTP ${res.statusCode}`))));
  };
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  let req;
  if (proxy) {
    const p = new URL(proxy);
    req = http.request({ host: p.hostname, port: p.port || 80, method: 'CONNECT', path: `${hostname}:443` });
    req.on('connect', (res, socket) => {
      if (res.statusCode !== 200) return done(new Error(`프록시가 연결을 거절했습니다 (${res.statusCode})`));
      https.get({ hostname, path: reqPath, headers, agent: false, rejectUnauthorized: false,
        createConnection: () => tls.connect({ socket, servername: hostname, rejectUnauthorized: false }) }, onRes)
        .on('error', done);
    });
    req.end();
  } else {
    req = https.get({ hostname, path: reqPath, headers, rejectUnauthorized: false }, onRes);
  }
  req.setTimeout(15000, () => req.destroy(new Error('15초 안에 응답이 없습니다')));
  req.on('error', done);
}

function readBackup(key) {
  try {
    const all = JSON.parse(fs.readFileSync(BACKUP_FILE, 'utf8'));
    return all.results && all.results[key] ? { ...all.results[key], backup: true, savedAt: all.savedAt } : null;
  } catch (e) {
    return null;
  }
}

function handleSearch(req, res) {
  const u = new URL(req.url, 'http://localhost');
  const q = (u.searchParams.get('q') || '').trim();
  const days = Math.min(Math.max(parseInt(u.searchParams.get('days'), 10) || 30, 1), 365);
  if (!q) return sendJson(res, 400, { error: { type: 'bad_request', message: '검색어(q)가 비어 있습니다.' } });

  const startedAt = Date.now();
  const rssPath = '/rss/search?q=' + encodeURIComponent(`${q} when:${days}d`) + '&hl=ko&gl=KR&ceid=KR:ko';
  fetchText(NEWS_HOST, rssPath, (err, xml) => {
    const elapsed = Date.now() - startedAt;
    if (!err) {
      const items = parseRss(xml);
      log(`GET /search "${q}" ${days}일 -> ${items.length}건 (${elapsed}ms)`);
      return sendJson(res, 200, { query: q, days, fetchedAt: new Date().toISOString(), items });
    }
    const backup = readBackup(`${q}|${days}`);
    if (backup) {
      log(`GET /search "${q}" -> 바깥 접속 실패(${err.message}), 예비 결과 ${backup.items.length}건으로 대신합니다`);
      return sendJson(res, 200, backup);
    }
    log(`GET /search "${q}" -> 502 (${elapsed}ms) ${err.message}`);
    sendJson(res, 502, { error: { type: 'search_error',
      message: `구글 뉴스에 닿지 못했습니다 — 사내망에서 바깥 접속이 막혔을 수 있습니다. (원인: ${err.message})` } });
  });
}

// 이 폴더 안의 파일만 그대로 내보낸다. (/ 로 들어오면 app.html)
function serveFile(req, res) {
  let rel = decodeURIComponent(req.url.split('?')[0]);
  if (rel === '/') rel = '/app.html';

  const root = __dirname;
  const target = path.join(root, path.normalize(rel).replace(/^([/\\])+/, ''));
  if (!target.startsWith(root)) {
    sendJson(res, 403, { error: { type: 'forbidden', message: '폴더 밖의 파일은 열 수 없습니다.' } });
    return;
  }

  fs.readFile(target, (err, data) => {
    if (err) {
      sendJson(res, 404, { error: { type: 'not_found', message: `${rel} 를 찾을 수 없습니다.` } });
      return;
    }
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(target).toLowerCase()] || 'application/octet-stream',
      'Content-Length': data.length,
      'Cache-Control': 'no-store'
    });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  withCors(res);

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const pathname = req.url.split('?')[0];

  if (req.method === 'GET' && pathname === '/search') {
    handleSearch(req, res);
    return;
  }

  if (req.method === 'GET' || req.method === 'HEAD') {
    serveFile(req, res);
    return;
  }

  if (req.method !== 'POST' || pathname !== '/v1/messages') {
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
    // 화면이 보낸 값이 더 작으면 올려 잡는다. max_tokens 는 API 필수 필드라 화면 쪽 코드가
    // 거의 항상 직접 적는데, 그 값이 작으면 대시보드용 JSON 이 중간에 잘려 JSON.parse 가 터진다.
    // 한도를 키운다고 답이 길어지지는 않는다 — 잘리지만 않게 해 주는 값이다.
    payload.max_tokens = Math.max(Number(payload.max_tokens) || 0, DEFAULT_MAX_TOKENS);

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

// 이미 쓰는 포트면 다음 번호로 넘어간다.
// 성공/실패 처리는 반드시 once 로 달고 매번 걷어낸다. on 으로 쌓으면
// 나중에 성공했을 때 실패한 포트의 안내까지 한꺼번에 찍혀서 엉뚱한 주소를 알려 주게 된다.
function tryListen(port) {
  server.removeAllListeners('error');
  server.removeAllListeners('listening');

  server.once('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      log(`포트 ${port} 은 이미 쓰고 있어서 ${port + 1} 로 넘어갑니다.`);
      tryListen(port + 1);
    } else {
      log('서버 오류:', err.message);
      process.exit(1);
    }
  });

  server.once('listening', () => {
    const real = server.address().port;      // 실제로 열린 포트만 알린다
    const url = `http://localhost:${real}`;
    log(`Claude proxy 실행 중: ${url}  (upstream: https://${UPSTREAM_HOST}${UPSTREAM_PATH})`);
    log(`화면을 열려면 브라우저에서 ${url} 로 들어가세요.`);
    console.log(`READY ${url}`);
    // 검은 창이 여러 개 떠 있어도 어느 앱인지 보이도록 창 제목에 주소를 넣는다.
    // 출력이 파일이나 다른 프로그램으로 넘어갈 때는 글자가 깨지므로 진짜 콘솔에서만 보낸다.
    if (process.stdout.isTTY) {
      process.stdout.write(`]0;AI App ${url} - 닫으면 꺼집니다`);
    }
    if (OPEN_BROWSER) openBrowser(url);
  });

  server.listen(port);
}

tryListen(START_PORT);
