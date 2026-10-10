import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createServer } from 'vite';
import { WebSocket, WebSocketServer } from 'ws';
import { createLocalAccess, guardHudServer, localAccessMiddleware } from './local-access.js';

test('Vite interface HTTP and WebSocket proxy retain Host/Origin enforcement', async t => {
  const host = process.platform === 'darwin' ? '127.0.0.1' : '127.0.0.2'; // macOS requires an explicit alias for other loopback addresses.
  const api = http.createServer();
  await new Promise(resolve => api.listen(0, '127.0.0.1', resolve));
  t.after(() => api.close());
  const probe = http.createServer();
  await new Promise(resolve => probe.listen(0, host, resolve));
  const uiPort = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  const ports = { api: api.address().port, ui: uiPort };
  const allowed = createLocalAccess(ports, { host });
  const middleware = localAccessMiddleware(allowed);
  let hits = 0;
  api.on('request', (req, res) => middleware(req, res, () => {
    hits++;
    res.end('proxied');
  }));
  const wss = new WebSocketServer({
    server: api, path: '/ws',
    verifyClient: ({ req }, done) => done(allowed(req), 403, 'Forbidden'),
  });
  wss.on('connection', socket => socket.send('connected'));
  t.after(() => wss.close());
  const ui = await createServer({
    configFile: false,
    plugins: [{
      name: 'access-test',
      configureServer(server) {
        guardHudServer(server, createLocalAccess(ports, { host, allowRemote: true }));
      },
    }],
    server: { host, port: uiPort, strictPort: true, proxy: {
      '/api': { target: 'http://127.0.0.1:' + ports.api },
      '/ws': { target: 'ws://127.0.0.1:' + ports.api, ws: true },
    } },
  });
  await ui.listen();
  t.after(() => ui.close());
  const origin = 'http://' + host + ':' + uiPort;
  let response = await fetch(origin + '/api/probe', { headers: { origin } });
  assert.equal(response.status, 200);
  assert.equal(await response.text(), 'proxied');
  response = await fetch(origin + '/api/probe', { headers: { origin: 'http://evil.example' } });
  assert.equal(response.status, 403);
  const hostileStatus = await new Promise((resolve, reject) => {
    http.get(origin + '/api/probe', { headers: { host: 'evil.example' } }, res => {
      res.resume();
      resolve(res.statusCode);
    }).on('error', reject);
  });
  assert.equal(hostileStatus, 403);
  assert.equal(hits, 1);

  const connect = originHeader => new Promise(resolve => {
    const socket = new WebSocket('ws://' + host + ':' + uiPort + '/ws', { origin: originHeader });
    const timeout = setTimeout(() => { socket.terminate(); resolve('timeout'); }, 3000);
    const finish = result => { clearTimeout(timeout); socket.terminate(); resolve(result); };
    socket.on('message', data => finish(data.toString()));
    socket.on('error', () => finish('denied'));
    socket.on('unexpected-response', (_req, res) => { res.resume(); finish('denied'); });
  });
  assert.equal(await connect(origin), 'connected');
  assert.equal(await connect('http://evil.example'), 'denied');
});
