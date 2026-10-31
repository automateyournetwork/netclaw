#!/usr/bin/env node
// Actual external API -> isolated MCP -> production HUD routes -> React/Chromium.
// Receives private fixture connection settings; never operates an existing runtime.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL, fileURLToPath } from 'node:url';
import crypto from 'node:crypto';
import express from 'express';
import { build } from 'esbuild';
import { Bindings } from '../src/hud-server/bindings.js';
import { mountAssessmentRoutes } from '../src/hud-server/assessment-routes.js';
import { mountConvergence, createConvergenceReader } from '../src/hud-server/convergence.js';
import { createLocalAccess, localAccessMiddleware } from '../src/security/local-access.js';

const [connectionFile, output] = process.argv.slice(2);
if (!connectionFile || !output) throw Error('Usage: convergence-read.mjs private-connection.json private-output-directory');
const parsed = JSON.parse(fs.readFileSync(connectionFile, 'utf8'));
const env = { ...process.env, ...(parsed.environment || parsed) };
for (const key of ['NETCLAW_RUNTIME_ROOT', 'NETCLAW_RUNTIME_ENV', 'CONVERGENCE_API_URL', 'CONVERGENCE_API_TOKEN', 'CONVERGENCE_SITE', 'CONVERGENCE_EXPORTERS']) {
  if (!env[key]) throw Error(`Private fixture setting ${key} is required`);
}
assert.equal(env.CONVERGENCE_ENABLED, 'true');
const directory = path.resolve(output); fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
const root = fileURLToPath(new URL('../../../', import.meta.url));
const installation = { installationId: crypto.randomUUID(), kind: 'openclaw' };
const bindingsDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'convergence-browser-bindings-'));
const bindings = new Bindings(bindingsDirectory, Date.now, installation);
const app = express(); let allowed = () => false;
app.use((req, res, next) => localAccessMiddleware(allowed)(req, res, next));
app.use(express.json());
app.use((req, _res, next) => {
  const selected = (req.headers.cookie || '').split(';').map(value => value.trim()).find(value => value.startsWith(bindings.cookieName + '='));
  if (selected) req.headers.cookie = 'nc_hud=' + selected.slice(bindings.cookieName.length + 1);
  next();
});
mountAssessmentRoutes(app, { bindings, readAssessment: async () => null });
mountConvergence(app, { bindings, getEnv: () => env, allowedRequest: req => allowed(req), read: createConvergenceReader(root, () => env) });
const bundle = await build({ stdin: { contents: `import React from 'react';import {createRoot} from 'react-dom/client';import Convergence from './Convergence.jsx';createRoot(document.getElementById('root')).render(<Convergence enabled={true} installationId=${JSON.stringify(installation.installationId)}/>);`, loader: 'jsx', resolveDir: path.join(root, 'ui/netclaw-visual/src/dashboard') }, bundle: true, write: false, format: 'iife', define: { 'process.env.NODE_ENV': '"production"' } });
app.get('/', (_req, res) => res.type('html').send('<!doctype html><html><head><meta charset="utf-8"><title>Convergence integration qualification</title><link rel="stylesheet" href="/fixture.css"></head><body><main id="root"></main><script src="/fixture.js"></script></body></html>'));
app.get('/fixture.js', (_req, res) => res.type('js').send(bundle.outputFiles[0].text));
app.get('/fixture.css', (_req, res) => res.type('css').send(fs.readFileSync(path.join(root, 'ui/netclaw-visual/src/dashboard/dashboard.css'), 'utf8')));
const server = app.listen(0, '127.0.0.1'); await new Promise(resolve => server.once('listening', resolve));
const port = server.address().port, url = `http://127.0.0.1:${port}`;
allowed = createLocalAccess({ api: port, ui: port + 1 }, { host: '127.0.0.1' });
const moduleName = process.env.CONVERGENCE_PLAYWRIGHT_MODULE;
let browser;
try {
  const { chromium } = await import(moduleName ? pathToFileURL(path.resolve(moduleName)).href : 'playwright');
  assert.equal((await fetch(url + '/api/hud/convergence/flows')).status, 401);
  browser = await chromium.launch({ headless: true, ...(process.env.CONVERGENCE_BROWSER_EXECUTABLE ? { executablePath: process.env.CONVERGENCE_BROWSER_EXECUTABLE } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
  const errors = [], requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push({ url: request.url(), headers: request.headers(), method: request.method() }));
  const summaryResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/hud/convergence/flows');
  await page.goto(url);
  const first = await (await summaryResponse).json();
  assert.equal(first.ok, true); assert.equal(first.data.status, 'active');
  assert.equal(first.data.site, env.CONVERGENCE_SITE); assert.ok(first.data.total.records > 0);
  const exporter = first.data.exporters[0]; assert.ok(exporter);
  const filteredResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/hud/convergence/flows' && new URL(response.url()).searchParams.get('exporter') === exporter);
  await page.getByLabel('Flow exporter', { exact: true }).selectOption(exporter);
  const summary = await (await filteredResponse).json(); assert.equal(summary.ok, true);
  const button = page.getByRole('button', { name: /^Inspect sources / }).first();
  await button.waitFor();
  const address = (await button.getAttribute('aria-label')).replace('Inspect sources ', '');
  const evidenceResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/hud/convergence/flows/records');
  await button.click();
  const response = await evidenceResponse, evidence = await response.json(), query = new URL(response.url()).searchParams;
  assert.equal(evidence.ok, true); assert.ok(evidence.data.records.length > 0);
  assert.equal(query.get('start'), summary.data.start); assert.equal(query.get('end'), summary.data.end);
  assert.equal(query.get('exporter'), exporter); assert.equal(query.get('address'), address);
  assert.equal(evidence.data.coverage.mode, summary.data.coverage.mode);
  await page.getByText('Latest 100 records involving this address', { exact: false }).waitFor();
  const rendered = await page.locator('body').innerText();
  assert.ok(rendered.includes(summary.data.coverage.label));
  assert.ok(rendered.includes('does not reconstruct a directional ranking total'));
  assert.ok(!rendered.includes(env.CONVERGENCE_API_TOKEN));
  assert.ok(!JSON.stringify(requests).includes(env.CONVERGENCE_API_TOKEN));
  assert.ok(!JSON.stringify([summary, evidence]).includes(env.CONVERGENCE_API_TOKEN));
  assert.deepEqual(errors, []);
  assert.ok(requests.every(request => request.url.startsWith(url + '/')));
  assert.ok(requests.every(request => request.method === 'GET' || new URL(request.url).pathname === '/api/hud/session'));
  const cookies = await page.context().cookies();
  const cookie = cookies.find(item => item.name === bindings.cookieName); assert.ok(cookie);
  const authHeaders = { cookie: `nc_hud=${cookie.value}`, 'X-NetClaw-Installation': installation.installationId };
  assert.equal((await fetch(url + '/api/hud/convergence/flows', { headers: { ...authHeaders, origin: 'https://evil.example' } })).status, 403);
  assert.equal((await fetch(url + '/api/hud/convergence/flows', { headers: { ...authHeaders, 'X-NetClaw-Installation': 'wrong' } })).status, 401);
  await page.screenshot({ path: path.join(directory, 'convergence-' + summary.data.coverage.mode + '.png'), fullPage: true });
  bindings.revoke(cookie.value);
  assert.equal((await fetch(url + '/api/hud/convergence/flows', { headers: authHeaders })).status, 401);
  const report = { result: 'PASS', scope: 'Actual service, isolated MCP, production HUD routes and React browser; no gateway/model invocation', site: summary.data.site, coverage: summary.data.coverage.mode, records: summary.data.total.records, evidenceRecords: evidence.data.records.length, start: summary.data.start, end: summary.data.end, browser: browser.version(), browserErrors: errors.length };
  fs.writeFileSync(path.join(directory, 'convergence-' + summary.data.coverage.mode + '.json'), JSON.stringify(report, null, 2) + '\n', { mode: 0o600 });
  console.log(JSON.stringify(report));
} finally {
  await browser?.close(); await new Promise(resolve => server.close(resolve));
  fs.rmSync(bindingsDirectory, { recursive: true, force: true });
}
