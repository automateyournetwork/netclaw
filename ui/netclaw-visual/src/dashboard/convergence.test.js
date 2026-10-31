import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
const directory = new URL('.', import.meta.url).pathname;
const output = await build({ stdin: { contents: `import React from 'react';import {createRoot} from 'react-dom/client';import Convergence from './Convergence.jsx';const root=createRoot(document.getElementById('root'));window.show=props=>root.render(<Convergence {...props}/>);window.remove=()=>root.unmount();`, loader: 'jsx', resolveDir: directory }, bundle: true, write: false, format: 'iife', define: { 'process.env.NODE_ENV': '"production"' } });
async function until(predicate) {
  const deadline = Date.now() + 3000;
  while (!predicate()) { if (Date.now() > deadline) assert.fail('UI condition did not become ready'); await new Promise(resolve => setTimeout(resolve, 5)); }
}
const fixture = () => ({
  status: 'active', site: 'synthetic-lab', coverage: { mode: 'demo', label: 'Synthetic demonstration', description: 'Example traffic, not your network.', detail: '<img src=x onerror=alert(1)>' },
  range: '1h', start: '2026-10-30T23:00:00.000Z', end: '2026-10-31T00:00:00.000Z', read_at: '2026-10-31T00:00:01Z', exporter: null, exporters: ['127.0.0.1'],
  total: { bytes: 100000, packets: 1000, records: 200, last_received: '2020-01-01T00:00:00Z' },
  sources: [{ src_addr: '192.0.2.10', bytes: 50000, packets: 500 }], destinations: [{ dst_addr: '198.51.100.20', bytes: 50000, packets: 500 }],
  basis: 'Exported counters, not billing.', limitations: ['Sampling is not extrapolated.'], sampling: [],
});
const evidence = address => ({ site: 'synthetic-lab', coverage: fixture().coverage, address, start: fixture().start, end: fixture().end, limit: 100, records: [
  { src_addr: address, dst_addr: '203.0.113.5', sampler_address: '127.0.0.1', _time: fixture().end, bytes: 100, packets: 1 },
  { src_addr: '203.0.113.5', dst_addr: address, sampler_address: '127.0.0.1', _time: fixture().end, bytes: 200, packets: 2 },
], basis: 'Latest records involving selected address.' });
async function setup(t, handler, props = { enabled: true, installationId: 'fixture-installation' }) {
  const dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost:3000', runScripts: 'outside-only', pretendToBeVisual: true });
  t.after(() => { dom.window.remove?.(); dom.window.close(); });
  const calls = [], w = dom.window;
  w.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    const result = url === '/api/hud/session' ? { authenticated: true } : await handler(url, options);
    return { ok: result.ok !== false, json: async () => result };
  };
  w.eval(output.outputFiles[0].text); w.show(props);
  return { w, calls, body: () => w.document.body.textContent, buttons: () => [...w.document.querySelectorAll('button')] };
}

test('disabled view performs no session, MCP or external requests', async t => {
  const f = await setup(t, () => assert.fail('must not read'), { enabled: false });
  await until(() => f.body().includes('disabled')); assert.equal(f.calls.length, 0);
});

test('same-window exporter evidence is escaped and labeled as mixed-direction bounded context', async t => {
  const f = await setup(t, url => {
    const query = new URL(url, 'http://local').searchParams;
    return { ok: true, data: url.includes('/records?') ? evidence(query.get('address')) : fixture() };
  });
  await until(() => f.buttons().some(b => b.textContent === 'Inspect records'));
  assert.match(f.body(), /Synthetic demonstration/); assert.equal(f.w.document.querySelectorAll('img').length, 0);
  assert.match(f.body(), /<img src=x onerror=alert\(1\)>/);
  assert.doesNotMatch(f.body(), /Stale cached data/); // An old receipt is not a failed refresh.
  const selector = f.w.document.querySelector('[aria-label="Flow exporter"]'); selector.value = '127.0.0.1'; selector.dispatchEvent(new f.w.Event('change', { bubbles: true }));
  await until(() => f.calls.some(c => c.url.includes('exporter=127.0.0.1')) && f.w.document.querySelector('.facts').textContent.includes('Selected exporter127.0.0.1') && !f.body().includes('Reading flows'));
  f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect destinations 198.51.100.20').click();
  await until(() => f.body().includes('From selected address'));
  assert.match(f.body(), /To selected address/); assert.match(f.body(), /does not reconstruct a directional ranking total/);
  const call = f.calls.find(c => c.url.includes('/records?')), query = new URL(call.url, 'http://local').searchParams;
  assert.equal(query.get('start'), fixture().start); assert.equal(query.get('end'), fixture().end); assert.equal(query.get('exporter'), '127.0.0.1');
  assert.equal(call.options.headers['X-NetClaw-Installation'], 'fixture-installation');
  assert.equal(f.w.document.querySelector('[aria-label="Selected flow records"]').textContent.includes('50000'), false);
});

test('failed refresh retains explicitly stale data while valid empty and unconfigured responses remain distinct', async t => {
  let result = { ok: true, data: fixture() };
  const f = await setup(t, () => result);
  await until(() => f.body().includes('100000'));
  result = { ok: false, error: { code: 'unavailable', message: 'private-token' } };
  f.buttons().find(b => b.textContent === 'Refresh flows').click();
  await until(() => f.body().includes('Stale cached data'));
  assert.match(f.body(), /100000/); assert.doesNotMatch(f.body(), /private-token/);
  result = { ok: true, data: { ...fixture(), status: 'empty', total: { bytes: null, packets: null }, sources: [], destinations: [] } };
  f.buttons().find(b => b.textContent === 'Refresh flows').click();
  await until(() => f.body().includes('No retained records match'));
  assert.doesNotMatch(f.body(), /Stale cached data|100000/);
  result = { ok: true, data: { status: 'not_configured', site: 'synthetic-lab', coverage: fixture().coverage, exporters: [] } };
  f.buttons().find(b => b.textContent === 'Refresh flows').click();
  await until(() => f.body().includes('No flow source is configured'));
  assert.doesNotMatch(f.body(), /No retained records match/);
});

test('late evidence from a previous selection cannot replace the current address', async t => {
  const pending = new Map();
  const f = await setup(t, url => {
    if (!url.includes('/records?')) return { ok: true, data: fixture() };
    const address = new URL(url, 'http://local').searchParams.get('address');
    return new Promise(resolve => pending.set(address, resolve));
  });
  await until(() => f.buttons().some(b => b.textContent === 'Inspect records'));
  f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect sources 192.0.2.10').click();
  await until(() => pending.has('192.0.2.10'));
  f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect destinations 198.51.100.20').click();
  await until(() => pending.has('198.51.100.20'));
  pending.get('198.51.100.20')({ ok: true, data: evidence('198.51.100.20') });
  await until(() => f.body().includes('From selected address'));
  pending.get('192.0.2.10')({ ok: true, data: evidence('192.0.2.10') });
  await new Promise(resolve => setTimeout(resolve, 15));
  assert.match(f.w.document.querySelector('[aria-label="Selected flow records"]').textContent, /Records involving 198\.51\.100\.20/);
  assert.doesNotMatch(f.w.document.querySelector('[aria-label="Selected flow records"]').textContent, /192\.0\.2\.10/);
});
