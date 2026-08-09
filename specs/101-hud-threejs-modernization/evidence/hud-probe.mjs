/**
 * Objective HUD measurements over CDP: console errors + median frame time + screenshot.
 *
 * Deliberately measures only what does not need human judgement. The subjective
 * half (is the selection legible? are the six states distinguishable?) is a
 * screenshot for a person to read, per spec 101 SC-002/SC-003.
 */
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import WebSocket from '/home/johncapobianco/netclaw/ui/netclaw-visual/node_modules/ws/index.js';

const CHROME = process.env.CHROME_BIN;
const URL_ = process.env.HUD_URL || 'http://localhost:3000/';
const LABEL = process.env.LABEL || 'run';
const OUT = process.env.OUT_DIR || '.';
const SETTLE_MS = Number(process.env.SETTLE_MS || 12000);
const SAMPLE_FRAMES = Number(process.env.SAMPLE_FRAMES || 600);

mkdirSync(OUT, { recursive: true });
const PORT = 9333 + Math.floor(Math.random() * 300);

const chrome = spawn(CHROME, [
  '--headless=new', '--no-sandbox', '--disable-dev-shm-usage', `--remote-debugging-port=${PORT}`,
  '--user-data-dir=/tmp/hud-probe-profile-' + PORT,
  '--window-size=1920,1080', '--hide-scrollbars',
  '--no-first-run', '--no-default-browser-check',
  // Software GL: this host has no real GPU. Frame times are therefore
  // comparable BETWEEN runs on this host, not to a GPU machine — which is all
  // FR-047's relative budget needs.
  '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
  'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });
let chromeErr = '';
chrome.stderr.on('data', (d) => { chromeErr += d.toString(); });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function targets() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (r.ok) return (await r.json()).webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(500);
  }
  throw new Error('Chrome never opened a debugging port.\n' + chromeErr.slice(-800));
}

const wsUrl = await targets();
const ws = new WebSocket(wsUrl, { maxPayload: 256 * 1024 * 1024 });
await new Promise((res, rej) => { ws.once('open', res); ws.once('error', rej); });

let id = 0;
const pending = new Map();
const consoleErrors = [];
const pageErrors = [];

ws.on('message', (raw) => {
  const msg = JSON.parse(raw.toString());
  if (msg.id && pending.has(msg.id)) {
    const { res, rej } = pending.get(msg.id); pending.delete(msg.id);
    msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
    return;
  }
  if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
    consoleErrors.push((msg.params.args || []).map((a) => a.value ?? a.description ?? a.type).join(' '));
  }
  if (msg.method === 'Runtime.exceptionThrown') {
    pageErrors.push(msg.params.exceptionDetails?.exception?.description
      || msg.params.exceptionDetails?.text || 'exception');
  }
  if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
    consoleErrors.push(msg.params.entry.text);
  }
});

const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const mid = ++id;
  pending.set(mid, { res, rej });
  ws.send(JSON.stringify({ id: mid, method, params, ...(sessionId ? { sessionId } : {}) }));
});

// Attach to a fresh page target
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);

await S('Runtime.enable');
await S('Log.enable');
await S('Page.enable');
await S('Emulation.setDeviceMetricsOverride',
  { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });

await S('Page.navigate', { url: URL_ });
await sleep(SETTLE_MS);

// Median frame time over a sustained window, camera idle.
const frameJs = `new Promise((resolve) => {
  const t = []; let p = performance.now();
  const f = (n) => { t.push(n - p); p = n;
    if (t.length < ${SAMPLE_FRAMES}) requestAnimationFrame(f);
    else { const s = t.slice(60).sort((a,b)=>a-b);
      resolve(JSON.stringify({ median: s[s.length>>1], p95: s[Math.floor(s.length*0.95)],
                               n: s.length })); } };
  requestAnimationFrame(f);
})`;
let frame = { error: 'not collected' };
try {
  const r = await S('Runtime.evaluate', { expression: frameJs, awaitPromise: true, returnByValue: true });
  frame = JSON.parse(r.result.value);
} catch (e) { frame = { error: String(e).slice(0, 200) }; }

// Scene composition actually rendered, so "same scene" is checkable not assumed.
let scene = {};
try {
  const r = await S('Runtime.evaluate', {
    expression: `JSON.stringify({
      canvases: document.querySelectorAll('canvas').length,
      labels: document.querySelectorAll('.label').length,
      webgl2: (()=>{try{return !!document.createElement('canvas').getContext('webgl2')}catch(e){return false}})(),
      renderer: (()=>{try{const c=document.createElement('canvas').getContext('webgl2');
        const d=c.getExtension('WEBGL_debug_renderer_info');
        return d ? c.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'unknown'}catch(e){return 'err'}})(),
      title: document.title })`,
    returnByValue: true });
  scene = JSON.parse(r.result.value);
} catch (e) { scene = { error: String(e).slice(0, 120) }; }

const shot = await S('Page.captureScreenshot', { format: 'png' });
writeFileSync(`${OUT}/hud-${LABEL}.png`, Buffer.from(shot.data, 'base64'));

const report = { label: LABEL, url: URL_, settleMs: SETTLE_MS, frame, scene,
                 consoleErrors, pageErrors };
writeFileSync(`${OUT}/hud-${LABEL}.json`, JSON.stringify(report, null, 2));

console.log(JSON.stringify(report, null, 2));

ws.close();
chrome.kill('SIGKILL');
process.exit(0);
