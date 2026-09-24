const https = require('https');
const http = require('http');
const tls = require('tls');
const fs = require('fs');
const path = require('path');

const TMP = process.env.TEMP || process.env.TMPDIR || 'C:\\Users\\Administrator\\AppData\\Local\\Temp';
const KEY = path.join(TMP, '__dev_https_key.pem');
const CERT = path.join(TMP, '__dev_https_cert.pem');

const TARGET_HOST = '127.0.0.1';
const TARGET_PORT = 8000;
const LISTEN_PORT = 8443;
const LISTEN_HOST = '127.0.0.1';

function proxy(req, res) {
  const origin = req.headers.origin || '*';
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,PATCH,OPTIONS,HEAD');
  res.setHeader('Access-Control-Allow-Headers', (req.headers['access-control-request-headers'] || 'Content-Type,Authorization,Accept,X-Requested-With,baggage,sentry-trace'));
  res.setHeader('Access-Control-Expose-Headers', '*');
  res.setHeader('Access-Control-Max-Age', '86400');
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }
  const outHeaders = Object.assign({}, req.headers);
  outHeaders.host = TARGET_HOST + ':' + TARGET_PORT;
  delete outHeaders['content-length'];
  delete outHeaders['connection'];
  const preq = http.request({ hostname: TARGET_HOST, port: TARGET_PORT, method: req.method, path: req.url, headers: outHeaders, timeout: 180000 });
  preq.on('timeout', () => { try { preq.destroy(new Error('upstream timeout')); } catch(_) {} });
  preq.on('response', pres => {
    const hdrs = Object.assign({}, pres.headers);
    delete hdrs['access-control-allow-origin'];
    delete hdrs['access-control-allow-credentials'];
    delete hdrs['access-control-expose-headers'];
    try { res.writeHead(pres.statusCode || 502, hdrs); } catch(_) {}
    pres.pipe(res, { end: true });
  });
  preq.on('error', err => {
    try { if (!res.headersSent) res.writeHead(502, { 'Content-Type': 'application/json' }); } catch(_) {}
    res.end(JSON.stringify({ code: 5020, message: 'Bad Gateway: ' + err.message }));
  });
  req.pipe(preq, { end: true });
}

try {
  const srv = https.createServer({ key: fs.readFileSync(KEY), cert: fs.readFileSync(CERT), secureContext: tls.createSecureContext({ key: fs.readFileSync(KEY), cert: fs.readFileSync(CERT) }) }, proxy);
  srv.on('tlsClientError', () => {});
  srv.listen(LISTEN_PORT, LISTEN_HOST, () => {
    process.stdout.write('[HTTPS PROXY UP] https://' + LISTEN_HOST + ':' + LISTEN_PORT + ' -> http://' + TARGET_HOST + ':' + TARGET_PORT + '\n');
  });
  srv.on('error', e => process.stderr.write('SRV_ERR: ' + e.message + '\n'));
} catch (e) {
  process.stderr.write('STARTUP_FAIL: ' + e.message + '\n');
  process.exit(2);
}
