#!/usr/bin/env node
// Real Dashboard and Canvas UI against synthetic HTTP fixtures. No gateway,
// provider, MCP or production runtime is contacted by this interaction test.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import express from 'express';
import { build } from 'esbuild';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = process.argv[2];
if (!output) throw Error('Usage: convergence-handoff.mjs private-output-directory');
fs.mkdirSync(output, { recursive: true, mode: 0o700 });
const installationId = '11111111-1111-4111-8111-111111111111';
const summary = {
  status: 'active', site: 'synthetic-handoff', range: '1h', exporter: null, exporters: ['127.0.0.1'],
  start: '2026-10-31T15:00:00Z', end: '2026-10-31T16:00:00Z', read_at: '2026-10-31T16:00:01Z',
  coverage: { mode: 'demo', label: 'Synthetic demonstration', description: 'Fixture traffic, not a real network.', detail: '<script>untrusted observed text</script>' },
  total: { bytes: 100000, packets: 1000, records: 200, last_received: '2026-10-31T15:59:59.123456789Z' },
  sources: [{ src_addr: '192.0.2.1', bytes: 100000, packets: 1000, records: 200 }], destinations: [], conversations: [],
  sampling: [{ rate: 0, records: 200 }], basis: 'Exported counters, not billing.', limitations: ['Synthetic selected source only.'],
};
const record = { _time: '2026-10-31T15:59:59.123456789Z', src_addr: '192.0.2.1', dst_addr: '198.51.100.1', sampler_address: '127.0.0.1', src_port: 443, dst_port: 1234, proto: 'TCP', bytes: '1000', packets: '10', sampling_rate: '0' };
const evidence = { site: summary.site, coverage: summary.coverage, address: '192.0.2.1', start: summary.start, end: summary.end, limit: 100, records: Array.from({ length: 100 }, (_, i) => ({ ...record, _time: i ? '2026-10-31T15:59:59.123456788Z' : record._time })), basis: 'Latest records matching source OR destination.' };
const bundle = await build({ absWorkingDir: root, entryPoints: { dashboard: 'src/dashboard/main.jsx', canvas: 'src/canvas-chat/main.jsx' }, outdir: '/fixture', bundle: true, write: false, format: 'iife', define: { 'process.env.NODE_ENV': '"production"' } });
const assets = new Map(bundle.outputFiles.map(file => [path.basename(file.path), file.text]));
const app = express(); let failSummary = false;
app.use(express.json());
app.get('/api/runtime', (_req, res) => res.json({ kind: 'openclaw', installationId, label: 'Synthetic fixture', readiness: { ready: true }, capabilities: { convergence: true } }));
app.post('/api/hud/session', (_req, res) => res.json({ authenticated: true }));
app.get('/api/hud/convergence/flows', (_req, res) => failSummary ? res.status(503).json({ ok: false, error: { code: 'unavailable' } }) : res.json({ ok: true, data: summary }));
app.get('/api/hud/convergence/flows/records', (_req, res) => res.json({ ok: true, data: evidence }));
app.get('/api/chat/models', (_req, res) => res.json({ models: [] }));
app.get('/api/gateway/status', (_req, res) => res.json({ connected: false }));
app.get('/api/*', (_req, res) => res.json({}));
for (const [name, content] of assets) app.get('/' + name, (_req, res) => res.type(name.endsWith('.css') ? 'css' : 'js').send(content));
const html = name => `<!doctype html><html><head><meta charset="utf-8"><title>Convergence handoff fixture</title>${assets.has(name + '.css') ? `<link rel="stylesheet" href="/${name}.css">` : ''}</head><body><div id="root"></div><script src="/${name}.js"></script></body></html>`;
app.get('/', (_req, res) => res.type('html').send(html('dashboard')));
app.get('/logos/netclaw.png', (_req, res) => res.sendFile(path.join(root, 'public/logos/netclaw.png')));
app.get('/canvas.html', (_req, res) => res.type('html').send(html('canvas')));
const server = app.listen(0, '127.0.0.1'); await new Promise(resolve => server.once('listening', resolve));
const url = `http://127.0.0.1:${server.address().port}`;
let browser, page;
try {
  const moduleName = process.env.CONVERGENCE_PLAYWRIGHT_MODULE;
  const { chromium } = await import(moduleName ? pathToFileURL(path.resolve(moduleName)).href : 'playwright');
  browser = await chromium.launch({ headless: true, ...(process.env.CONVERGENCE_BROWSER_EXECUTABLE ? { executablePath: process.env.CONVERGENCE_BROWSER_EXECUTABLE } : {}) });
  page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
  const errors = [], requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push({ path: new URL(request.url()).pathname, url: request.url(), method: request.method() }));
  await page.goto(url);
  await page.getByRole('button', { name: /Convergence$/ }).click();
  await page.getByRole('button', { name: 'Inspect sources 192.0.2.1', exact: true }).click();
  await page.getByRole('button', { name: 'Investigate in Canvas', exact: true }).click();
  const selected = await page.locator('.context-review pre').innerText();
  const context = JSON.parse(selected.slice(selected.indexOf('\n\n') + 2));
  assert.equal(context.site, summary.site); assert.equal(context.start, summary.start); assert.equal(context.end, summary.end);
  assert.equal(context.coverage.mode, 'demo'); assert.equal(context.evidence.record_limit, 100);
  assert.equal(context.evidence.returned_records, 100); assert.ok(context.evidence.omitted_records > 0);
  assert.equal(context.evidence.records[0]._time, record._time); assert.equal(context.evidence.records[0].sampling_rate, '0');
  assert.equal(context.coverage.detail, summary.coverage.detail);
  assert.ok(selected.length < 16000);
  const frame = page.frameLocator('iframe[title="Canvas context and chat workspace"]');
  await page.getByRole('button', { name: 'Add to canvas draft', exact: true }).click();
  await page.getByText('Context added to the active draft. Review it before sending.', { exact: true }).waitFor();
  // Canvas uses a single-line input, but persists the full multiline draft in
  // its installation-owned IndexedDB session. Verify both visible and stored state.
  assert.equal(await frame.locator('input[data-composer="1"]').first().inputValue(), selected.replace(/[\r\n]/g, ''));
  const readDraft = () => page.evaluate(({ installationId, selected }) => new Promise(resolve => {
    const open = indexedDB.open(`netclaw.openclaw.${installationId}.netclaw-canvas`, 2);
    open.onerror = () => resolve(false);
    open.onsuccess = () => {
      const db = open.result, request = db.transaction('sessions').objectStore('sessions').getAll();
      request.onsuccess = () => { const found = request.result.filter(session => session.installationId === installationId).flatMap(session => Object.values(session.drafts || {})).find(value => value === selected); db.close(); resolve(found || false); };
      request.onerror = () => { db.close(); resolve(false); };
    };
  }), { installationId, selected });
  let draft = false;
  const deadline = Date.now() + 5000;
  while (!draft && Date.now() < deadline) { draft = await readDraft(); if (!draft) await new Promise(resolve => setTimeout(resolve, 50)); }
  assert.ok(draft === selected, 'The owned Canvas session must persist the exact multiline context draft');
  assert.equal(requests.some(request => request.path === '/api/chat' || request.path === '/api/chat/requests'), false);
  await page.screenshot({ path: path.join(output, 'convergence-handoff.png'), fullPage: true });
  await page.getByRole('button', { name: /Convergence$/ }).click();
  await page.getByRole('button', { name: 'Inspect sources 192.0.2.1', exact: true }).waitFor();
  failSummary = true;
  await page.getByRole('button', { name: 'Refresh flows', exact: true }).click();
  await page.getByText('Stale cached data', { exact: false }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Inspect sources 192.0.2.1', exact: true }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Investigate in Canvas', exact: true }).count(), 0);
  assert.deepEqual(errors, []); assert.ok(requests.every(request => request.url.startsWith(url + '/')));
  const report = { result: 'PASS', scope: 'Production Dashboard, Convergence panel, Canvas and owned-message bridge with synthetic HTTP fixtures; no gateway/provider/MCP qualification', browser: browser.version(), contextCharacters: selected.length, returnedRecords: context.evidence.returned_records, includedRecords: context.evidence.included_records, omittedRecords: context.evidence.omitted_records, exactDraft: draft === selected, modelRequests: 0, staleInvestigationBlocked: true, browserErrors: errors.length };
  fs.writeFileSync(path.join(output, 'convergence-handoff.json'), JSON.stringify(report, null, 2) + '\n', { mode: 0o600 });
  console.log(JSON.stringify(report));
} catch (error) {
  if (page) { await page.screenshot({ path: path.join(output, 'convergence-handoff-failure.png'), fullPage: true }); console.error((await page.locator('body').innerText()).slice(0, 2500)); }
  throw error;
} finally {
  await browser?.close(); await new Promise(resolve => server.close(resolve));
}
