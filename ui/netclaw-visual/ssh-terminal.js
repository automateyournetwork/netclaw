/**
 * ─────────────────────────────────────────────────────────────────────────────
 * FORK-LOCAL: interactive SSH terminal + "explain what's on screen".
 * Not part of upstream automateyournetwork/netclaw. See FORK-NOTES.md.
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * WHAT IT IS
 *   A real PTY to a testbed device, streamed to an xterm.js panel in the HUD,
 *   plus an /ask endpoint that hands the model the terminal's own scrollback so
 *   questions like "explain this config section" have the screen as context.
 *
 * WHY NOT pyATS FOR THE TRANSPORT
 *   pyATS/Unicon is prompt-and-expect oriented: it sets `terminal length 0`,
 *   tracks modes, and matches prompts. Tab completion, `?` help and `--More--`
 *   paging all fight that state machine, and it is Python, so it would need a
 *   sidecar per session. More importantly pyATS cannot see this session at all —
 *   it would open its own connection, so it can't supply "what's on my screen".
 *   The scrollback buffer here is what provides that. pyATS/Genie remains the
 *   right tool for *structured* analysis and is a sensible later addition, with
 *   the caveat that it reflects the device now, not this session's history.
 *
 * WHY SSE AND NOT A WEBSOCKET
 *   Upstream owns `new WebSocketServer({ server, path: '/ws' })`. Attaching a
 *   second path-scoped WebSocketServer to the same http server does not work:
 *   ws registers an 'upgrade' listener per instance, and the first one whose
 *   `path` does not match calls abortHandshake() and destroys the socket before
 *   ours is reached. Working around it means editing how upstream builds its
 *   wss — exactly the coupling this fork is trying to avoid. Server-Sent Events
 *   for device output plus small POSTs for keystrokes needs zero upstream
 *   changes, and for a human at a keyboard the latency is irrelevant.
 *
 * SECURITY POSTURE — read docs/SSH-TERMINAL-HARDENING.md before enabling.
 *   The input filter below is best-effort, not a boundary. On an interactive
 *   stream, abbreviations, `do`, pasted blocks and EEM/tclsh can evade
 *   line-oriented matching. Real enforcement is a privilege-1 device account.
 *   Set HUD_SSH_USERNAME/PASSWORD to one; otherwise this falls back to
 *   NETCLAW_USERNAME, which on these switches is privilege 15.
 *
 * ENV
 *   HUD_SSH_ENABLED=1          off by default — must be opted into
 *   HUD_SSH_USERNAME/PASSWORD  read-only device account (strongly recommended)
 *   HUD_SSH_ALLOW_CONFIG=1     lift the config-mode filter
 *   HUD_SSH_IDLE_S=900         idle disconnect
 *   HUD_SSH_MAX_SESSIONS=4     concurrent cap
 *   HUD_SSH_AUDIT              audit log path
 */

import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import yaml from 'js-yaml';
import { Client } from 'ssh2';

const IDLE_MS = (Number(process.env.HUD_SSH_IDLE_S) || 900) * 1000;
const MAX_SESSIONS = Number(process.env.HUD_SSH_MAX_SESSIONS) || 4;
const ALLOW_CONFIG = process.env.HUD_SSH_ALLOW_CONFIG === '1';
const SCROLLBACK_MAX = 256 * 1024; // ~a full `show run` with room to spare
const AUDIT_PATH = process.env.HUD_SSH_AUDIT
  || path.join(os.homedir(), '.openclaw', 'hud-ssh-audit.log');

/** sessionId -> session */
const sessions = new Map();

// ── Command filter ───────────────────────────────────────────────────────────
// Deliberately conservative. Anything that can change state, plus anything
// touching VLAN 3 / the Vlan3 SVI, which is the management path for these
// switches and is off limits per the network-change-safety rules.
const BLOCKED = [
  { re: /^\s*conf(i(g(u(r(e)?)?)?)?)?\b/i, why: 'config mode' },
  { re: /^\s*(wr|wri|writ|write)\b/i, why: 'write' },
  { re: /^\s*copy\b/i, why: 'copy' },
  { re: /^\s*(erase|format|delete|rmdir|rename)\b/i, why: 'destructive filesystem command' },
  { re: /^\s*(reload|reset)\b/i, why: 'reload' },
  { re: /^\s*no\s+/i, why: 'negation command' },
  { re: /^\s*(tclsh|guestshell|event\s+manager|do\s+conf)/i, why: 'scripting / config bypass' },
  { re: /\b(interface\s+)?vlan\s*0*3\b/i, why: 'VLAN 3 is the management path (off limits)' },
  { re: /\bVlan3\b/, why: 'Vlan3 SVI is the management path (off limits)' },
];

export function inspectCommand(line) {
  const cmd = String(line || '').trim();
  if (!cmd) return { allowed: true };
  if (ALLOW_CONFIG) {
    // Even with config explicitly allowed, VLAN 3 stays hard-blocked.
    const v = BLOCKED.slice(-2).find((b) => b.re.test(cmd));
    return v ? { allowed: false, why: v.why } : { allowed: true };
  }
  const hit = BLOCKED.find((b) => b.re.test(cmd));
  return hit ? { allowed: false, why: hit.why } : { allowed: true };
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function stripAnsi(s) {
  return String(s)
    .replace(/\u001b\][^\u0007]*(?:\u0007|\u001b\\)/g, '')
    .replace(/\u001b[[\]()#;?]*[0-9;]*[A-Za-z]/g, '')
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '')
    .replace(/\r(?!\n)/g, '\n');
}

function audit(entry) {
  const line = JSON.stringify({ ts: new Date().toISOString(), ...entry });
  try {
    fs.mkdirSync(path.dirname(AUDIT_PATH), { recursive: true });
    fs.appendFileSync(AUDIT_PATH, `${line}\n`, { mode: 0o600 });
  } catch (err) {
    console.warn('[ssh] audit write failed:', err.message);
  }
}

/**
 * Resolve a device to connection details, server-side only. Credentials and IPs
 * never travel to the browser — the client only ever sends a device id.
 */
function resolveDevice(deviceId, { TESTBED_FILE, parseEnvFile, readText }) {
  const doc = yaml.load(readText(TESTBED_FILE) || '') || {};
  const devices = doc.devices || {};
  const name = Object.keys(devices)
    .find((n) => n === deviceId || n.toLowerCase() === String(deviceId).toLowerCase());
  if (!name) return { error: `Unknown device: ${deviceId}` };

  const dev = devices[name];
  const conns = dev.connections || {};
  const conn = conns.ssh || conns.cli
    || Object.values(conns).find((c) => c && c.ip);
  if (!conn?.ip) return { error: `No SSH connection defined for ${name}` };

  // testbed.yaml stores %ENV{VAR}; resolve against .env + process.env.
  const env = { ...parseEnvFile(), ...process.env };
  const deref = (v) => String(v ?? '').replace(/%ENV\{([^}]+)\}/g, (_, k) => env[k] || '');
  const creds = doc.testbed?.credentials || {};

  // Prefer a dedicated read-only account when configured.
  const username = process.env.HUD_SSH_USERNAME || deref(creds.default?.username);
  const password = process.env.HUD_SSH_PASSWORD || deref(creds.default?.password);
  if (!username || !password) {
    return { error: 'No credentials: set HUD_SSH_USERNAME/HUD_SSH_PASSWORD (recommended) or NETCLAW_USERNAME/NETCLAW_PASSWORD' };
  }

  return {
    name,
    host: conn.ip,
    port: Number(conn.port) || 22,
    os: dev.os || 'unknown',
    type: dev.type || 'unknown',
    username,
    password,
    usingDedicatedAccount: Boolean(process.env.HUD_SSH_USERNAME),
  };
}

function touch(s) { s.lastActivity = Date.now(); }

function closeSession(id, reason) {
  const s = sessions.get(id);
  if (!s) return;
  try { s.stream?.end(); } catch { /* already gone */ }
  try { s.client?.end(); } catch { /* already gone */ }
  for (const res of s.listeners) {
    try {
      res.write(`event: closed\ndata: ${JSON.stringify({ reason })}\n\n`);
      res.end();
    } catch { /* client already gone */ }
  }
  sessions.delete(id);
  audit({ event: 'close', sessionId: id, device: s.device.name, reason });
}

// Reap idle sessions. unref() so this never holds the process open.
const reaper = setInterval(() => {
  const now = Date.now();
  for (const [id, s] of sessions) {
    if (now - s.lastActivity > IDLE_MS) closeSession(id, 'idle-timeout');
  }
}, 30000);
if (typeof reaper.unref === 'function') reaper.unref();

// ─────────────────────────────────────────────────────────────────────────────
export function registerSshTerminal(app, ctx) {
  const { TESTBED_FILE, parseEnvFile, readText, requireTrustedClient, askModel } = ctx;

  const enabled = process.env.HUD_SSH_ENABLED === '1';

  // Gate the whole surface. Off by default; trusted-client check always applies;
  // bearer token additionally required when HUD_API_TOKEN is set.
  const gate = (req, res, next) => {
    if (!enabled) {
      return res.status(503).json({
        error: 'SSH terminal disabled',
        hint: 'Set HUD_SSH_ENABLED=1. Read docs/SSH-TERMINAL-HARDENING.md first — '
          + 'without HUD_SSH_USERNAME this uses a privilege-15 account.',
      });
    }
    const required = process.env.HUD_API_TOKEN;
    if (required) {
      const got = (req.get('authorization') || '').replace(/^Bearer\s+/i, '');
      if (got !== required) return res.status(401).json({ error: 'Bearer token required' });
    }
    return requireTrustedClient(req, res, next);
  };

  app.get('/api/ssh/capabilities', (req, res) => {
    res.json({
      enabled,
      allowConfig: ALLOW_CONFIG,
      dedicatedAccount: Boolean(process.env.HUD_SSH_USERNAME),
      tokenRequired: Boolean(process.env.HUD_API_TOKEN),
      idleSeconds: IDLE_MS / 1000,
      maxSessions: MAX_SESSIONS,
      open: sessions.size,
    });
  });

  app.post('/api/ssh/open', gate, (req, res) => {
    if (sessions.size >= MAX_SESSIONS) {
      return res.status(429).json({ error: `Session cap reached (${MAX_SESSIONS})` });
    }
    const device = resolveDevice(req.body?.device, { TESTBED_FILE, parseEnvFile, readText });
    if (device.error) return res.status(400).json({ error: device.error });

    const id = crypto.randomBytes(12).toString('hex');
    const client = new Client();
    const session = {
      id,
      device,
      client,
      stream: null,
      raw: [],          // chunks pending delivery to attached listeners
      text: '',         // ANSI-stripped scrollback, the model's context
      pending: '',      // partial keystrokes not yet submitted as a line
      listeners: new Set(),
      lastActivity: Date.now(),
      clientIp: (req.ip || '').replace(/^::ffff:/, ''),
      status: 'connecting',
    };
    sessions.set(id, session);

    client
      .on('ready', () => {
        client.shell({ term: 'xterm-256color', cols: 120, rows: 34 }, (err, stream) => {
          if (err) {
            session.status = 'error';
            closeSession(id, `shell failed: ${err.message}`);
            return;
          }
          session.stream = stream;
          session.status = 'open';
          stream.on('data', (chunk) => {
            const s = chunk.toString('utf8');
            touch(session);
            session.text = (session.text + stripAnsi(s)).slice(-SCROLLBACK_MAX);
            for (const r of session.listeners) {
              try { r.write(`data: ${JSON.stringify({ d: s })}\n\n`); } catch { /* dropped */ }
            }
          });
          stream.on('close', () => closeSession(id, 'remote-closed'));
        });
      })
      .on('error', (err) => {
        session.status = 'error';
        session.error = err.message;
        audit({ event: 'connect-error', device: device.name, error: err.message });
        closeSession(id, `ssh error: ${err.message}`);
      })
      .connect({
        host: device.host,
        port: device.port,
        username: device.username,
        password: device.password,
        readyTimeout: 20000,
        // These switches are IOS-XE 16.12; allow the older KEX/cipher set they offer.
        algorithms: {
          kex: [
            'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521',
            'diffie-hellman-group14-sha256', 'diffie-hellman-group14-sha1',
            'diffie-hellman-group-exchange-sha1', 'diffie-hellman-group1-sha1',
          ],
          serverHostKey: ['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-ed25519'],
          cipher: ['aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-cbc', '3des-cbc'],
        },
      });

    audit({
      event: 'open',
      sessionId: id,
      device: device.name,
      host: device.host,
      username: device.username,
      dedicatedAccount: device.usingDedicatedAccount,
      from: session.clientIp,
    });

    res.json({
      sessionId: id,
      device: { name: device.name, os: device.os, type: device.type },
      readOnlyEnforcedByApp: !ALLOW_CONFIG,
      dedicatedAccount: device.usingDedicatedAccount,
      warning: device.usingDedicatedAccount ? null
        : 'Using NETCLAW_* credentials (privilege 15 on these switches). '
          + 'Set HUD_SSH_USERNAME/PASSWORD to a privilege-1 account.',
    });
  });

  // SSE: device output. One long-lived response per attached viewer.
  app.get('/api/ssh/:id/stream', gate, (req, res) => {
    const s = sessions.get(req.params.id);
    if (!s) return res.status(404).json({ error: 'No such session' });

    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    });
    res.write(`event: ready\ndata: ${JSON.stringify({ sessionId: s.id, status: s.status })}\n\n`);
    s.listeners.add(res);

    const ka = setInterval(() => {
      try { res.write(': ka\n\n'); } catch { /* dropped */ }
    }, 15000);
    if (typeof ka.unref === 'function') ka.unref();

    req.on('close', () => {
      clearInterval(ka);
      s.listeners.delete(res);
    });
    return undefined;
  });

  // Keystrokes. Filtering happens on submitted lines, not raw bytes, so a
  // blocked command is caught at Enter rather than mid-word.
  app.post('/api/ssh/:id/input', gate, (req, res) => {
    const s = sessions.get(req.params.id);
    if (!s) return res.status(404).json({ error: 'No such session' });
    if (!s.stream) return res.status(409).json({ error: `Session not ready (${s.status})` });

    const data = String(req.body?.data ?? '');
    if (!data) return res.json({ ok: true });
    touch(s);

    let out = '';
    for (const ch of data) {
      if (ch === '\r' || ch === '\n') {
        const verdict = inspectCommand(s.pending);
        if (!verdict.allowed) {
          audit({
            event: 'blocked',
            sessionId: s.id,
            device: s.device.name,
            command: s.pending.trim(),
            why: verdict.why,
            from: s.clientIp,
          });
          const msg = `\r\n\u001b[31m[HUD blocked: ${verdict.why}]\u001b[0m\r\n`;
          s.text += `\n[HUD blocked: ${verdict.why}] ${s.pending.trim()}\n`;
          for (const r of s.listeners) {
            try { r.write(`data: ${JSON.stringify({ d: msg })}\n\n`); } catch { /* dropped */ }
          }
          // Clear the device's input line so the blocked text isn't left staged.
          out += '\u0015';
          s.pending = '';
          continue;
        }
        audit({
          event: 'command',
          sessionId: s.id,
          device: s.device.name,
          command: s.pending.trim(),
          from: s.clientIp,
        });
        s.pending = '';
        out += '\n';
      } else if (ch === '\u007f' || ch === '\b') {
        s.pending = s.pending.slice(0, -1);
        out += ch;
      } else if (ch === '\u0015') {
        s.pending = '';
        out += ch;
      } else {
        if (ch >= ' ') s.pending += ch;
        out += ch;
      }
    }
    if (out) s.stream.write(out);
    return res.json({ ok: true });
  });

  app.post('/api/ssh/:id/resize', gate, (req, res) => {
    const s = sessions.get(req.params.id);
    if (!s?.stream) return res.status(404).json({ error: 'No such session' });
    const cols = Math.max(20, Math.min(500, Number(req.body?.cols) || 120));
    const rows = Math.max(5, Math.min(200, Number(req.body?.rows) || 34));
    try { s.stream.setWindow(rows, cols, 0, 0); } catch { /* best effort */ }
    return res.json({ ok: true, cols, rows });
  });

  /**
   * The point of the whole feature: answer a question using this session's own
   * scrollback as context, so "explain this section" works on what is actually
   * on screen.
   */
  app.post('/api/ssh/:id/ask', gate, async (req, res) => {
    const s = sessions.get(req.params.id);
    if (!s) return res.status(404).json({ error: 'No such session' });
    touch(s);

    const question = String(req.body?.question || '').trim();
    const selection = String(req.body?.selection || '').trim();
    if (!question && !selection) {
      return res.status(400).json({ error: 'Expected { question } and/or { selection }' });
    }

    // Selection is the focus; recent scrollback is the surrounding context.
    const context = s.text.slice(-24000);
    const prompt = [
      `You are inspecting a live SSH session to ${s.device.name}`,
      ` (${s.device.type}, ${s.device.os}).`,
      '\n\nThe operator is looking at this terminal. Answer from what is shown.',
      ' If the screen does not contain the answer, say so and name the show',
      ' command that would reveal it — do not invent output.',
      selection ? `\n\n--- SELECTED TEXT (the focus of the question) ---\n${selection}` : '',
      `\n\n--- RECENT TERMINAL SCROLLBACK ---\n${context}`,
      `\n\n--- QUESTION ---\n${question || 'Explain the selected configuration and why it matters.'}`,
    ].join('');

    try {
      const answer = await askModel(prompt);
      audit({
        event: 'ask',
        sessionId: s.id,
        device: s.device.name,
        question: question.slice(0, 300),
        hasSelection: Boolean(selection),
        from: s.clientIp,
      });
      return res.json({
        answer,
        device: s.device.name,
        contextChars: context.length,
        selectionChars: selection.length,
      });
    } catch (err) {
      return res.status(502).json({ error: `Model request failed: ${err.message}` });
    }
  });

  app.get('/api/ssh', gate, (req, res) => {
    res.json({
      sessions: [...sessions.values()].map((s) => ({
        sessionId: s.id,
        device: s.device.name,
        status: s.status,
        viewers: s.listeners.size,
        scrollbackChars: s.text.length,
        idleSeconds: Math.round((Date.now() - s.lastActivity) / 1000),
      })),
    });
  });

  app.delete('/api/ssh/:id', gate, (req, res) => {
    if (!sessions.has(req.params.id)) return res.status(404).json({ error: 'No such session' });
    closeSession(req.params.id, 'client-closed');
    return res.json({ ok: true });
  });

  return { enabled, routes: 8 };
}
