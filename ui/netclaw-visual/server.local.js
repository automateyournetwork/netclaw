/**
 * ─────────────────────────────────────────────────────────────────────────────
 * FORK-LOCAL HUD EXTENSIONS — not part of upstream automateyournetwork/netclaw.
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * WHY THIS FILE EXISTS
 *   Upstream owns server.js and rewrites it freely (the HUD 2.0 rewrite in
 *   2ca395c deleted ~500 lines of endpoints this fork depends on). Keeping our
 *   additions inline in server.js meant every upstream pull produced a large
 *   conflict in a file we do not own, and silently dropped features when
 *   resolved in upstream's favour.
 *
 *   So everything fork-specific lives HERE instead. Upstream never touches this
 *   path, so `git merge upstream/main` cannot conflict with it.
 *
 * WHAT SERVER.JS NEEDS (the entire coupling — keep it this small)
 *   One hook near the bottom of server.js, just before server.listen():
 *
 *       await registerLocalExtensions(app, { ...ctx });
 *
 *   If this file is deleted or HUD_LOCAL_EXTENSIONS=0 is set, server.js runs as
 *   pristine upstream. That is the "optional" requirement: nothing here is
 *   load-bearing for upstream's own features.
 *
 * WHAT IT PROVIDES
 *   /api/home/status, /api/home/*   Convergence tab proxy (src/views/home/
 *                                   HomeView.js is a fork-only file)
 *   GET+POST /api/models            model SoT editor used by HomeView
 *   /api/rag/ingest-url             fork additions to KnowledgePanel
 *   /api/rag/crawl-site
 *   /api/tokens/summary             token/cost strip (see NOTE below)
 *   static dist/ + SPA fallback     upstream serves the frontend via `vite
 *                                   preview` on :3000; this fork serves the
 *                                   built dist/ from the API process on :3001
 *
 * DELIBERATE OMISSION
 *   The old code also patched /api/chat to record per-turn token usage into
 *   _lastChatUsage. That required editing the middle of upstream's chat
 *   handler — a guaranteed future conflict — and nothing in the current
 *   frontend reads it (no src/ file calls /api/tokens/summary). So the
 *   `lastTurn` field below is always null. Lifetime totals still work; they
 *   come from the token exporter, not from this process. If you ever want
 *   lastTurn back, pass a getLastChatUsage() in ctx rather than reintroducing
 *   the inline patch.
 *
 * MAINTENANCE NOTE
 *   The route bodies below are kept byte-identical to the pre-merge server.js
 *   (fork commit 30e2882) on purpose, including their original indentation, so
 *   they can be diffed directly against upstream history if a shared helper
 *   signature ever changes. Do not reformat them casually.
 *
 * CONTRACT WITH SERVER.JS
 *   Everything this file borrows from upstream arrives via ctx. As of
 *   upstream 2ca395c all twelve of these exist in server.js. If an upstream
 *   pull removes or renames one, registration fails loudly (see assertCtx)
 *   instead of half-loading.
 */

import express from 'express';
import fs from 'fs';
import path from 'path';
import { execFile } from 'child_process';
import { fileURLToPath } from 'url';
import { registerSshTerminal } from './ssh-terminal.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Borrowed-from-upstream identifiers that must be present in ctx.
const REQUIRED_CTX = [
  'ROOT',
  'OPENCLAW_ENV',
  'ROOT_ENV',
  'RAG_DATA_DIR',
  'RAG_INTAKE_DIR',
  'broadcastWS',
  'callRagTool',
  'parseEnvFile',
  'parseOneEnvFile',
  'ragStartProgressPolling',
  'readText',
  // SSH terminal (fork feature)
  'TESTBED_FILE',
  'getGatewayConfig',
  'requireTrustedClient',
];

function assertCtx(ctx) {
  const missing = REQUIRED_CTX.filter((k) => ctx?.[k] === undefined);
  if (missing.length) {
    throw new Error(
      `server.local.js: server.js no longer provides [${missing.join(', ')}]. `
      + 'An upstream pull likely renamed or removed them — update the ctx object '
      + 'at the registerLocalExtensions() call in server.js.',
    );
  }
}

export function register(app, ctx) {
  assertCtx(ctx);

  const {
    ROOT,
    OPENCLAW_ENV,
    ROOT_ENV,
    RAG_DATA_DIR,
    RAG_INTAKE_DIR,
    broadcastWS,
    callRagTool,
    parseEnvFile,
    parseOneEnvFile,
    ragStartProgressPolling,
    readText,
  } = ctx;

  registerConvergence(app, { parseEnvFile });
  registerTokens(app, { readText });
  registerModels(app, {
    ROOT, OPENCLAW_ENV, ROOT_ENV, parseEnvFile, parseOneEnvFile,
    readText, broadcastWS,
  });
  registerRag(app, {
    RAG_DATA_DIR, RAG_INTAKE_DIR, callRagTool, ragStartProgressPolling, broadcastWS,
  });

  const ssh = registerSshTerminal(app, {
    TESTBED_FILE: ctx.TESTBED_FILE,
    parseEnvFile,
    readText,
    requireTrustedClient: ctx.requireTrustedClient,
    askModel: makeAskModel(ctx.getGatewayConfig),
  });

  // MUST be last: the SPA fallback swallows every unmatched GET.
  registerFrontend(app);

  return {
    routes: [
      '/api/home/status', '/api/home/*', '/api/tokens/summary',
      'GET+POST /api/models', '/api/rag/ingest-url', '/api/rag/crawl-site',
      `/api/ssh/* (${ssh.enabled ? 'enabled' : 'disabled'})`,
    ],
    servesFrontend: fs.existsSync(path.join(__dirname, 'dist', 'index.html')),
    sshEnabled: ssh.enabled,
  };
}

/**
 * One-shot model call through the OpenClaw gateway, for the terminal's /ask.
 * Kept here rather than in ssh-terminal.js so that module stays transport-only
 * and has no opinion about how the model is reached.
 */
function makeAskModel(getGatewayConfig) {
  return async function askModel(prompt) {
    const gw = getGatewayConfig();
    if (!gw.chatCompletionsEnabled) {
      throw new Error('gateway chatCompletions endpoint is disabled');
    }
    const r = await fetch(`http://127.0.0.1:${gw.port}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${gw.token}`,
        'Content-Type': 'application/json',
        'x-openclaw-agent-id': 'main',
      },
      body: JSON.stringify({
        model: 'openclaw',
        messages: [{ role: 'user', content: prompt }],
        stream: false,
      }),
      signal: AbortSignal.timeout(120000),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      throw new Error(data?.error?.message || `gateway HTTP ${r.status}`);
    }
    const text = data.choices?.[0]?.message?.content || data.choices?.[0]?.text || '';
    if (!text) throw new Error('gateway returned an empty completion');
    return text;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Frontend: serve the built Vite bundle + SPA fallback.
//
// Upstream's deployment model is `vite preview` on :3000 proxying /api to the
// API process on :3001, so upstream's server.js serves no static files at all
// and GET / returns "Cannot GET /". This fork runs a single process on :3001,
// so it needs both halves here.
//
// Note we do NOT touch the bind address. `server.listen(port)` with no host
// already binds all interfaces (:: dual-stack), so upstream is LAN-reachable
// as-is; a missing static handler was the only reason / appeared "down".
// ─────────────────────────────────────────────────────────────────────────────
function registerFrontend(app) {
  const distDir = path.join(__dirname, 'dist');
  const indexHtml = path.join(distDir, 'index.html');
  if (!fs.existsSync(indexHtml)) {
    console.warn('[local] dist/ not built — frontend not served. Run: npm run build');
    return;
  }
  app.use(express.static(distDir));
  app.get('*', (req, res, next) => {
    // Never let the SPA fallback mask a genuine 404 from the API surface.
    if (req.path.startsWith('/api/') || req.path === '/ws') return next();
    res.sendFile(indexHtml);
  });
}


// ───────────────────────────────────────────────────────────────────────────
// Convergence tab (067) — env-var driven, nothing hard-coded.
// CONVERGENCE_API_URL/TOKEN, aliases HOME_API_* and NETWORK_GUARDIAN_*.
// ───────────────────────────────────────────────────────────────────────────
function registerConvergence(app, { parseEnvFile }) {
// ── 067-convergence: proxy HOME tab → convergence-api / Network Guardian (dual-run) ──
// Prefer CONVERGENCE_API_*; aliases HOME_API_* and NETWORK_GUARDIAN_* for dual-run / legacy.
function homeApiConfig() {
  const env = { ...parseEnvFile(), ...process.env };
  const base = (
    env.CONVERGENCE_API_URL
    || env.HOME_API_URL
    || env.NETWORK_GUARDIAN_URL
    || ''
  ).replace(/\/$/, '');
  const token = (
    env.CONVERGENCE_API_TOKEN
    || env.HOME_API_TOKEN
    || env.NETWORK_GUARDIAN_TOKEN
    || ''
  );
  return { base, token };
}

app.get('/api/home/status', (req, res) => {
  const { base, token } = homeApiConfig();
  res.json({
    configured: Boolean(base && token),
    base: base || null,
    tokenConfigured: Boolean(token),
    dualRun: Boolean(base && /network-guardian|guardian/i.test(base)),
  });
});

// Mount: browser → /api/home/health?site=home → upstream /api/health?site=home
app.use('/api/home', async (req, res, next) => {
  // Let /api/home/status fall through if not already handled (GET only above)
  if (req.path === '/status' || req.path === 'status') return next();

  const { base, token } = homeApiConfig();
  if (!base) {
    return res.status(503).json({
      error: 'Convergence API not configured',
      hint: 'Set CONVERGENCE_API_URL + CONVERGENCE_API_TOKEN (aliases: HOME_API_* or NETWORK_GUARDIAN_*) in ~/.openclaw/.env',
    });
  }
  // req.url is relative to mount, e.g. /health?site=home
  const rel = req.url.startsWith('/') ? req.url : `/${req.url}`;
  const url = `${base}/api${rel}`;
  try {
    const headers = {
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
    const hasBody = !['GET', 'HEAD'].includes(req.method) && req.body && Object.keys(req.body).length > 0;
    if (hasBody) headers['Content-Type'] = 'application/json';
    const upstream = await fetch(url, {
      method: req.method,
      headers,
      body: hasBody ? JSON.stringify(req.body) : undefined,
      signal: AbortSignal.timeout(20000),
    });
    const text = await upstream.text();
    res.status(upstream.status);
    res.setHeader('Content-Type', upstream.headers.get('content-type') || 'application/json');
    res.send(text);
  } catch (err) {
    res.status(502).json({
      error: 'Home API unreachable',
      detail: err.message,
      target: base,
    });
  }
});
}

// ───────────────────────────────────────────────────────────────────────────
// Token / cost summary strip.
// ───────────────────────────────────────────────────────────────────────────
function registerTokens(app, { readText }) {
// NOTE: this stays null — see DELIBERATE OMISSION in the file header. Kept so
// the endpoint body below remains byte-identical to the pre-merge original.
// Backs the HUD footer strip. Source: openclaw-token-exporter scrape
// of ~/.openclaw/agents/*/sessions/*.jsonl (same counters as Grafana).
const TOKEN_EXPORTER_URL =
  process.env.TOKEN_EXPORTER_URL || 'http://127.0.0.1:9110/metrics';

let _lastChatUsage = null; // { input, output, total, model, at }

function parsePromCounters(text) {
  const byModel = new Map(); // model -> { input, output, cost, calls, provider }
  let totalIn = 0;
  let totalOut = 0;
  let totalCost = 0;
  let totalCalls = 0;
  for (const line of String(text || '').split('\n')) {
    if (!line || line.startsWith('#')) continue;
    const m = line.match(
      /^(netclaw_model_(?:input_tokens|output_tokens|cost_usd|calls)_total)\{([^}]*)\}\s+([0-9.eE+-]+)/,
    );
    if (!m) continue;
    const [, metric, labels, valStr] = m;
    const val = parseFloat(valStr);
    if (!Number.isFinite(val)) continue;
    const lab = {};
    for (const part of labels.split(',')) {
      const eq = part.indexOf('=');
      if (eq < 1) continue;
      lab[part.slice(0, eq)] = part.slice(eq + 1).replace(/^"|"$/g, '');
    }
    const model = lab.model || 'unknown';
    const provider = lab.provider || 'unknown';
    const row = byModel.get(model) || {
      model,
      provider,
      input: 0,
      output: 0,
      cost: 0,
      calls: 0,
    };
    if (metric.includes('input_tokens')) {
      row.input = val;
      totalIn += val;
    } else if (metric.includes('output_tokens')) {
      row.output = val;
      totalOut += val;
    } else if (metric.includes('cost_usd')) {
      row.cost = val;
      totalCost += val;
    } else if (metric.includes('calls_total')) {
      row.calls = val;
      totalCalls += val;
    }
    byModel.set(model, row);
  }
  // Prefer summing unique models once (input/output counted above may double-count
  // if we add every metric line — recompute from map)
  totalIn = 0;
  totalOut = 0;
  totalCost = 0;
  totalCalls = 0;
  const models = [...byModel.values()].sort((a, b) => b.input - a.input);
  for (const r of models) {
    totalIn += r.input || 0;
    totalOut += r.output || 0;
    totalCost += r.cost || 0;
    totalCalls += r.calls || 0;
  }
  return { models, totalIn, totalOut, totalCost, totalCalls };
}
app.get('/api/tokens/summary', async (req, res) => {
  let exporter = null;
  let exporterError = null;
  try {
    const r = await fetch(TOKEN_EXPORTER_URL, { signal: AbortSignal.timeout(2500) });
    if (!r.ok) throw new Error(`exporter HTTP ${r.status}`);
    const text = await r.text();
    exporter = parsePromCounters(text);
  } catch (err) {
    exporterError = err.message;
  }

  // NetClaw-owned token optimization flags (NOT openclaw.json — OpenClaw schema rejects unknown keys)
  let tokenOptimization = null;
  try {
    const optPath = path.join(
      process.env.HOME || '/root',
      '.openclaw',
      'netclaw-token-optimization.json',
    );
    tokenOptimization = JSON.parse(readText(optPath) || 'null');
  } catch {
    /* ignore */
  }

  const top = (exporter?.models || []).slice(0, 5).map((m) => ({
    model: m.model,
    provider: m.provider,
    input: Math.round(m.input),
    output: Math.round(m.output),
    calls: Math.round(m.calls),
  }));

  res.json({
    ok: !exporterError,
    exporterError,
    exporterUrl: TOKEN_EXPORTER_URL,
    lifetime: exporter
      ? {
          input: Math.round(exporter.totalIn),
          output: Math.round(exporter.totalOut),
          costUsd: Math.round(exporter.totalCost * 10000) / 10000,
          calls: Math.round(exporter.totalCalls),
        }
      : null,
    topModels: top,
    lastTurn: _lastChatUsage,
    tokenOptimization: tokenOptimization
      ? {
          enabled: Boolean(tokenOptimization.enabled),
          footerDisplay: tokenOptimization.footerDisplay || null,
          gcfSerializationDefault: Boolean(tokenOptimization.gcfSerializationDefault),
        }
      : { enabled: false },
    timestamp: new Date().toISOString(),
  });
});
}

// ───────────────────────────────────────────────────────────────────────────
// Model SoT (.env) + apply to live OpenClaw.
// ───────────────────────────────────────────────────────────────────────────
function registerModels(app, {
  ROOT, OPENCLAW_ENV, ROOT_ENV, parseEnvFile, parseOneEnvFile,
  readText, broadcastWS,
}) {
const APPLY_MODELS_SCRIPT = path.join(ROOT, 'scripts', 'netclaw-apply-models.sh');
const MODEL_ENV_KEYS = [
  'NETCLAW_BRAIN_MODEL',
  'NETCLAW_ALERT_TRIAGE_MODEL',
  'NETCLAW_ALERT_FALLBACK_MODEL',
  'OLLAMA_BASE_URL',
  'OLLAMA_API_KEY',
];

function readOpenclawModelsLive() {
  try {
    const raw = readText(path.join(process.env.HOME || '/root', '.openclaw', 'openclaw.json'));
    if (!raw) return {};
    const d = JSON.parse(raw);
    const defaults = d?.agents?.defaults?.model || {};
    let alertAgent = null;
    for (const a of d?.agents?.list || []) {
      if (a?.id === 'alert') alertAgent = a.model || null;
    }
    let hookAlert = null;
    for (const m of d?.hooks?.mappings || []) {
      if (m?.match?.path === 'alert') {
        hookAlert = { model: m.model || null, agentId: m.agentId || null };
      }
    }
    return {
      defaultsPrimary: defaults.primary || null,
      alertAgent,
      hookAlert,
    };
  } catch {
    return {};
  }
}

function writeModelEnvKeys(updates) {
  // Prefer repo .env as operator SoT; also mirror into ~/.openclaw/.env
  const targets = [ROOT_ENV];
  if (fs.existsSync(OPENCLAW_ENV) || fs.existsSync(path.dirname(OPENCLAW_ENV))) {
    targets.push(OPENCLAW_ENV);
  }
  for (const targetFile of targets) {
    let text = readText(targetFile);
    if (!text) text = '';
    for (const [key, value] of Object.entries(updates)) {
      if (value == null || value === '') continue;
      if (!MODEL_ENV_KEYS.includes(key) && !key.startsWith('NETCLAW_') && !key.startsWith('OLLAMA_')) {
        continue;
      }
      const regex = new RegExp(`^${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*=.*$`, 'm');
      const newLine = `${key}=${value}`;
      if (regex.test(text)) text = text.replace(regex, newLine);
      else text = `${text.trimEnd()}\n${newLine}\n`;
    }
    try {
      fs.mkdirSync(path.dirname(targetFile), { recursive: true });
      fs.writeFileSync(targetFile, text, 'utf8');
    } catch (err) {
      console.warn(`[models] write ${targetFile}: ${err.message}`);
    }
  }
}

function runApplyModels({ restart = true } = {}) {
  return new Promise((resolve, reject) => {
    if (!fs.existsSync(APPLY_MODELS_SCRIPT)) {
      reject(new Error(`Missing ${APPLY_MODELS_SCRIPT}`));
      return;
    }
    const args = ['apply'];
    if (!restart) args.push('--no-restart');
    execFile(
      APPLY_MODELS_SCRIPT,
      args,
      {
        cwd: ROOT,
        env: { ...process.env, NETCLAW_DIR: ROOT, NETCLAW_ENV_FILE: ROOT_ENV },
        timeout: 120000,
        maxBuffer: 2 * 1024 * 1024,
      },
      (err, stdout, stderr) => {
        if (err) {
          err.stdout = stdout;
          err.stderr = stderr;
          reject(err);
          return;
        }
        resolve({ stdout: String(stdout || ''), stderr: String(stderr || '') });
      },
    );
  });
}
app.get('/api/models', (req, res) => {
  const env = parseEnvFile();
  // Prefer repo .env values for display when both set
  const rootEnv = parseOneEnvFile(ROOT_ENV);
  const brain = rootEnv.NETCLAW_BRAIN_MODEL || env.NETCLAW_BRAIN_MODEL || '';
  const alert = rootEnv.NETCLAW_ALERT_TRIAGE_MODEL || env.NETCLAW_ALERT_TRIAGE_MODEL || '';
  const fallback = rootEnv.NETCLAW_ALERT_FALLBACK_MODEL || env.NETCLAW_ALERT_FALLBACK_MODEL || '';
  const live = readOpenclawModelsLive();
  res.json({
    sot: {
      file: ROOT_ENV,
      brain,
      alert,
      fallback,
      ollamaBaseUrl: rootEnv.OLLAMA_BASE_URL || env.OLLAMA_BASE_URL || '',
      ollamaKeySet: Boolean(rootEnv.OLLAMA_API_KEY || env.OLLAMA_API_KEY),
    },
    live,
    presets: {
      local: {
        brain: 'ollama/voytas26/openclaw-qwen3vl-8b-opt',
        alert: 'ollama/voytas26/openclaw-qwen3vl-8b-opt',
        fallback: '',
      },
      'cloud-flash': {
        brain: 'ollama/deepseek-v4-flash:cloud',
        alert: 'ollama/deepseek-v4-flash:cloud',
        fallback: 'ollama/glm-5.2:cloud',
      },
      split: {
        brain: 'ollama/voytas26/openclaw-qwen3vl-8b-opt',
        alert: 'ollama/deepseek-v4-flash:cloud',
        fallback: 'ollama/glm-5.2:cloud',
      },
      anthropic: {
        brain: 'anthropic/claude-sonnet-5',
        alert: 'anthropic/claude-haiku-4-5-20251001',
        fallback: '',
      },
    },
    applyScript: 'scripts/netclaw-apply-models.sh',
    generatedAt: new Date().toISOString(),
  });
});

app.post('/api/models', async (req, res) => {
  try {
    const body = req.body || {};
    const restart = body.restart !== false;
    const preset = body.preset ? String(body.preset) : null;

    if (preset) {
      await new Promise((resolve, reject) => {
        const args = ['preset', preset];
        if (!restart) args.push('--no-restart');
        execFile(
          APPLY_MODELS_SCRIPT,
          args,
          {
            cwd: ROOT,
            env: { ...process.env, NETCLAW_DIR: ROOT, NETCLAW_ENV_FILE: ROOT_ENV },
            timeout: 120000,
            maxBuffer: 2 * 1024 * 1024,
          },
          (err, stdout, stderr) => {
            if (err) {
              err.stdout = stdout;
              err.stderr = stderr;
              reject(err);
              return;
            }
            resolve({ stdout, stderr });
          },
        );
      });
    } else {
      const updates = {};
      if (body.brain) updates.NETCLAW_BRAIN_MODEL = String(body.brain).trim();
      if (body.alert) updates.NETCLAW_ALERT_TRIAGE_MODEL = String(body.alert).trim();
      if (body.fallback != null && body.fallback !== '') {
        updates.NETCLAW_ALERT_FALLBACK_MODEL = String(body.fallback).trim();
      }
      if (body.ollamaBaseUrl) updates.OLLAMA_BASE_URL = String(body.ollamaBaseUrl).trim();
      if (!Object.keys(updates).length) {
        return res.status(400).json({
          error: 'Expected { brain, alert } or { preset: "local"|"cloud-flash"|"split" }',
        });
      }
      writeModelEnvKeys(updates);
      await runApplyModels({ restart });
    }

    broadcastWS('config:updated', {
      keys: ['NETCLAW_BRAIN_MODEL', 'NETCLAW_ALERT_TRIAGE_MODEL'],
      generatedAt: new Date().toISOString(),
    });
    res.json({
      ok: true,
      restarted: restart,
      sot: parseOneEnvFile(ROOT_ENV),
      live: readOpenclawModelsLive(),
    });
  } catch (err) {
    console.error('[models] apply failed:', err.message, err.stderr || '');
    res.status(500).json({
      error: err.message || 'apply failed',
      detail: String(err.stderr || err.stdout || '').slice(0, 2000),
    });
  }
});
}

// ───────────────────────────────────────────────────────────────────────────
// RAG: URL ingestion + depth-1 same-site crawl (fork additions).
// ───────────────────────────────────────────────────────────────────────────
function registerRag(app, {
  RAG_DATA_DIR, RAG_INTAKE_DIR, callRagTool, ragStartProgressPolling, broadcastWS,
}) {
app.post('/api/rag/ingest-url', async (req, res) => {
  const url = String(req.body?.url || '').trim();
  const mode = (req.body?.mode || 'preview').toLowerCase();
  if (!url || !/^https?:\/\//i.test(url)) {
    return res.status(400).json({ error: 'url is required (http or https)' });
  }
  if (mode !== 'preview' && mode !== 'ingest') {
    return res.status(400).json({ error: "mode must be 'preview' or 'ingest'" });
  }
  const args = {
    url,
    mode,
    include_linked: Boolean(req.body?.include_linked),
    doc_type: req.body?.doc_type || 'other',
  };
  if (req.body?.scope_token) args.scope_token = req.body.scope_token;
  if (req.body?.title) args.title = req.body.title;
  // Self-signed local gear (UniFi :11443, pfSense, etc.)
  if (req.body?.verify_ssl === false || req.body?.insecure === true) {
    args.verify_ssl = false;
  } else if (req.body?.verify_ssl === true) {
    args.verify_ssl = true;
  }

  try {
    if (mode === 'ingest') {
      res.status(202).json({ status: 'pending', url, mode: 'ingest' });
      ragStartProgressPolling();
      try {
        const result = await callRagTool('rag_ingest_url', args, 900);
        if (result.success) {
          const pages = result.data?.pages || [];
          const firstOk = pages.find((p) => p?.success || p?.data?.document_id);
          const docId = firstOk?.data?.document_id || firstOk?.document_id || null;
          const title = firstOk?.data?.title || result.data?.title || url;
          broadcastWS('rag_progress', {
            document_id: docId,
            title,
            status: 'ready',
            error: null,
            pages_ingested: result.data?.ingested,
          });
        } else {
          broadcastWS('rag_progress', {
            document_id: null,
            title: url,
            status: 'error',
            error: result.error?.message || 'URL ingest failed',
          });
        }
      } catch (ingestErr) {
        broadcastWS('rag_progress', {
          document_id: null,
          title: url,
          status: 'error',
          error: ingestErr.message,
        });
      }
      broadcastWS('rag_update', { documents_changed: true });
      return;
    }

    // preview — synchronous so the UI can show linked pages + scope_token
    const result = await callRagTool('rag_ingest_url', args, 120);
    if (!result.success) {
      return res.status(500).json(result.error || { error: 'preview failed' });
    }
    res.json(result.data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * Multi-page docs-site crawl → Markdown → rag_ingest (HUD "Crawl site to RAG").
 * Body: { url, max_pages?, depth?, insecure?, doc_type?, title? }
 * Runs async (202); progress via rag_progress / rag_update WS events.
 */
app.post('/api/rag/crawl-site', async (req, res) => {
  const url = String(req.body?.url || '').trim();
  if (!url || !/^https?:\/\//i.test(url)) {
    return res.status(400).json({ error: 'url is required (http or https)' });
  }
  const maxPages = Math.min(Math.max(parseInt(req.body?.max_pages, 10) || 60, 1), 150);
  const depth = Math.min(Math.max(parseInt(req.body?.depth, 10) || 2, 0), 5);
  const insecure = Boolean(
    req.body?.insecure === true
    || req.body?.verify_ssl === false
  );
  const docType = req.body?.doc_type || 'vendor';
  const titleHint = req.body?.title || null;

  const hostSafe = url.replace(/^https?:\/\//i, '').replace(/[^\w.-]+/g, '_').slice(0, 80);
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  fs.mkdirSync(RAG_INTAKE_DIR, { recursive: true });
  const outBase = path.join(RAG_INTAKE_DIR, `crawl_${hostSafe}_${stamp}`);
  const outPdf = `${outBase}.pdf`;
  const outMd = `${outBase}.md`;
  const script = path.join(ROOT, 'scripts', 'docs-site-to-pdf.py');
  if (!fs.existsSync(script)) {
    return res.status(500).json({ error: 'docs-site-to-pdf.py not found in repo' });
  }

  const label = `crawl:${url}`;
  res.status(202).json({
    status: 'pending',
    url,
    max_pages: maxPages,
    depth,
    out_pdf: outPdf,
    out_md: outMd,
  });

  broadcastWS('rag_progress', {
    document_id: null,
    title: label,
    status: 'crawling',
    error: null,
  });
  ragStartProgressPolling();

  const args = [
    script,
    '--start-url', url,
    '--out', outPdf,
    '--max-pages', String(maxPages),
    '--depth', String(depth),
    '--delay', '0.25',
    '--markdown',
  ];
  if (insecure) args.push('--insecure');

  execFile(
    RAG_PYTHON,
    args,
    {
      timeout: 30 * 60 * 1000,
      maxBuffer: 16 * 1024 * 1024,
      env: {
        ...process.env,
        PATH: `${path.dirname(RAG_PYTHON)}${path.delimiter}${process.env.PATH || ''}`,
        RAG_DATA_DIR,
        NETCLAW_GCF_MODE: 'off',
      },
    },
    async (err, stdout, stderr) => {
      const outText = `${stdout || ''}\n${stderr || ''}`.trim();
      // Script prints "[  3/60] d=0 'Title'" per page and "Writing PDF (N pages)"
      const pageHits = [...outText.matchAll(/\[\s*(\d+)\//g)].map((m) => parseInt(m[1], 10));
      const pagesFromLog = pageHits.length ? Math.max(...pageHits) : 0;
      const writingMatch = outText.match(/Writing PDF \((\d+) pages\)/i);
      const pagesReported = writingMatch ? parseInt(writingMatch[1], 10) : pagesFromLog;

      if (err) {
        const msg = (stderr || err.message || 'crawl failed').toString().slice(0, 800);
        broadcastWS('rag_progress', {
          document_id: null,
          title: label,
          status: 'error',
          error: msg,
          detail: pagesReported ? `crawl stopped after ~${pagesReported} page(s)` : null,
        });
        broadcastWS('rag_update', { documents_changed: true });
        return;
      }

      // Prefer Markdown for RAG chunking; fall back to PDF
      const ingestPath = fs.existsSync(outMd) ? outMd : outPdf;
      if (!fs.existsSync(ingestPath)) {
        broadcastWS('rag_progress', {
          document_id: null,
          title: label,
          status: 'error',
          error: `Crawl finished but no output file. Often means every page was empty HTML (JS-only SPA). stdout: ${(stdout || '').slice(0, 240)}`,
        });
        broadcastWS('rag_update', { documents_changed: true });
        return;
      }

      const byteSize = fs.statSync(ingestPath).size;
      const textSample = ingestPath.endsWith('.md')
        ? fs.readFileSync(ingestPath, 'utf8')
        : '';
      const charCount = textSample.length;
      // Quality gate: refuse clearly empty / SPA-shell crawls
      const minPages = 2;
      const minChars = 1500;
      const thin =
        (pagesReported > 0 && pagesReported < minPages)
        || (charCount > 0 && charCount < minChars)
        || (byteSize < 2500 && pagesReported <= 1);

      if (thin) {
        const reason = [
          pagesReported ? `${pagesReported} page(s) crawled` : 'unknown page count',
          charCount ? `${charCount} chars in markdown` : `${byteSize} byte file`,
          'Too thin for useful API docs — site is likely a JS SPA shell, not server-rendered HTML.',
          'Try an official public docs URL, or export/print PDF from the browser, then Upload file.',
        ].join(' · ');
        broadcastWS('rag_progress', {
          document_id: null,
          title: label,
          status: 'error',
          error: reason,
          pages_crawled: pagesReported,
          file_bytes: byteSize,
        });
        broadcastWS('rag_update', { documents_changed: true });
        return;
      }

      broadcastWS('rag_progress', {
        document_id: null,
        title: label,
        status: 'parsing',
        error: null,
        detail: `crawled ${pagesReported || '?'} page(s), ${(byteSize / 1024).toFixed(0)} KiB → indexing`,
      });

      try {
        const result = await callRagTool('rag_ingest', {
          file_path: ingestPath,
          doc_type: docType,
          source: `hud-crawl:${url}`,
          ...(titleHint ? { title: titleHint } : {
            title: `Docs crawl: ${url.replace(/^https?:\/\//, '').slice(0, 80)} (${pagesReported || '?'} pages)`,
          }),
        }, 900);
        if (result.success) {
          broadcastWS('rag_progress', {
            document_id: result.data?.document_id || null,
            title: result.data?.title || label,
            status: 'ready',
            error: null,
            detail: `OK · ${pagesReported || '?'} pages · ${result.data?.chunk_count ?? '?'} chunks`,
            pages_crawled: pagesReported,
            file: ingestPath,
            chunk_count: result.data?.chunk_count,
          });
        } else {
          broadcastWS('rag_progress', {
            document_id: null,
            title: label,
            status: 'error',
            error: result.error?.message || 'rag_ingest after crawl failed',
          });
        }
      } catch (ingestErr) {
        broadcastWS('rag_progress', {
          document_id: null,
          title: label,
          status: 'error',
          error: ingestErr.message,
        });
      }
      broadcastWS('rag_update', { documents_changed: true });
    },
  );
});
}
