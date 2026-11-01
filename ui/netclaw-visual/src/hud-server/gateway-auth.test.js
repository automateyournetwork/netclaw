import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { gatewayBearerToken } from './gateway-auth.js';

test('native env secret reference authenticates the HUD HTTP request', async () => {
  const server = http.createServer((req, res) => {
    res.writeHead(req.headers.authorization === 'Bearer selected-token' ? 200 : 401);
    res.end('{}');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const config = { gateway: { auth: { token: { source: 'env', provider: 'default', id: 'SELECTED_TOKEN' } } } };
    const token = gatewayBearerToken(config, { SELECTED_TOKEN: 'selected-token', OPENCLAW_GATEWAY_TOKEN: 'wrong-token' });
    const response = await fetch(`http://127.0.0.1:${server.address().port}/v1/models`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    assert.equal(response.status, 200);
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('explicit unresolved or unsupported references never use another credential', () => {
  const env = { OPENCLAW_GATEWAY_TOKEN: 'unrelated-token' };
  for (const token of [{ source: 'env', provider: 'default', id: 'MISSING' },
    { source: 'file', provider: 'default', id: '/private/key' },
    { source: 'env', provider: 'custom', id: 'OPENCLAW_GATEWAY_TOKEN' }, '${MISSING}', 'bad\nheader']) {
    assert.equal(gatewayBearerToken({ gateway: { auth: { token } } }, env), '');
  }
});

test('literal and string environment references remain compatible', () => {
  assert.equal(gatewayBearerToken({ gateway: { auth: { token: 'literal' } } }, {}), 'literal');
  assert.equal(gatewayBearerToken({ gateway: { auth: { token: '${TOKEN}' } } }, { TOKEN: 'resolved' }), 'resolved');
  assert.equal(gatewayBearerToken({ gateway: {} }, { OPENCLAW_GATEWAY_TOKEN: 'selected' }), 'selected');
  assert.equal(gatewayBearerToken({ gateway: { auth: { mode: 'password' } } }, { OPENCLAW_GATEWAY_TOKEN: 'stale' }), '');
});
