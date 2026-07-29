/**
 * FORK-LOCAL: device SSH terminal + selection assistant.
 * Not part of upstream. See ../../FORK-NOTES.md.
 *
 * Transport is SSE down / POST up rather than a WebSocket — upstream owns the
 * '/ws' path and a second path-scoped WebSocketServer on the same http server
 * aborts the handshake. Rationale in ../../ssh-terminal.js.
 */

import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import './TerminalPanel.css';

let active = null; // only one terminal panel at a time

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
));

/** Minimal markdown: fenced code, inline code, bold, headings, bullets. */
function renderAnswer(md) {
  const parts = String(md).split(/```(?:[a-zA-Z]*)\n?/);
  return parts.map((chunk, i) => {
    if (i % 2 === 1) return `<pre class="tp-code">${esc(chunk)}</pre>`;
    return esc(chunk)
      .replace(/^### (.*)$/gm, '<h4>$1</h4>')
      .replace(/^## (.*)$/gm, '<h3>$1</h3>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^[-*] (.*)$/gm, '<li>$1</li>')
      .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
      .replace(/\n{2,}/g, '<br><br>');
  }).join('');
}

async function api(pathname, opts = {}) {
  const res = await fetch(pathname, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.hint || `HTTP ${res.status}`);
  return data;
}

export async function openTerminalPanel(deviceName) {
  if (active) closeTerminalPanel();

  const root = document.createElement('div');
  root.className = 'panel tp-panel';
  root.innerHTML = `
    <div class="tp-head">
      <span class="tp-title">SSH — ${esc(deviceName)}</span>
      <span class="tp-badge" id="tp-badge">connecting…</span>
      <button class="tp-x" id="tp-close" title="Close session">✕</button>
    </div>
    <div class="tp-body">
      <div class="tp-term" id="tp-term"></div>
      <div class="tp-side">
        <div class="tp-side-head">Selection assistant</div>
        <div class="tp-hint" id="tp-sel-hint">
          Select text in the terminal, then Explain — or just ask a question.
          The model receives the terminal scrollback as context.
        </div>
        <button class="tp-btn" id="tp-explain" disabled>Explain selection</button>
        <div class="tp-answer" id="tp-answer"></div>
        <form class="tp-askrow" id="tp-askform">
          <input id="tp-q" class="tp-q" placeholder="Ask about what's on screen…" autocomplete="off">
          <button class="tp-btn tp-ask" type="submit">Ask</button>
        </form>
      </div>
    </div>`;
  document.body.appendChild(root);

  const badge = root.querySelector('#tp-badge');
  const answerEl = root.querySelector('#tp-answer');
  const explainBtn = root.querySelector('#tp-explain');

  const term = new Terminal({
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
    fontSize: 12,
    theme: { background: '#0b1020', foreground: '#d6e2ff', selectionBackground: '#3b5bdb' },
    cursorBlink: true,
    scrollback: 8000,
  });
  const fit = new FitAddon();
  term.loadAddon(fit);
  term.open(root.querySelector('#tp-term'));
  try { fit.fit(); } catch { /* not laid out yet */ }

  const setBadge = (text, cls) => {
    badge.textContent = text;
    badge.className = `tp-badge ${cls || ''}`;
  };

  let session = null;
  let stream = null;

  try {
    session = await api('/api/ssh/open', {
      method: 'POST',
      body: JSON.stringify({ device: deviceName }),
    });
  } catch (err) {
    setBadge('unavailable', 'bad');
    term.writeln(`\x1b[31mCould not open a session: ${err.message}\x1b[0m`);
    term.writeln('');
    term.writeln('\x1b[90mThe terminal is opt-in. Enable with HUD_SSH_ENABLED=1 after');
    term.writeln('reading docs/SSH-TERMINAL-HARDENING.md.\x1b[0m');
    active = { root, term, session: null, stream: null };
    return;
  }

  setBadge(session.dedicatedAccount ? 'read-only account' : 'privilege 15 ⚠', session.dedicatedAccount ? 'ok' : 'warn');
  if (session.warning) term.writeln(`\x1b[33m${session.warning}\x1b[0m`);

  // Device output.
  stream = new EventSource(`/api/ssh/${session.sessionId}/stream`);
  stream.onmessage = (e) => {
    try {
      const { d } = JSON.parse(e.data);
      if (d) term.write(d);
    } catch { /* keepalive or partial frame */ }
  };
  stream.addEventListener('closed', (e) => {
    let reason = 'closed';
    try { reason = JSON.parse(e.data).reason || reason; } catch { /* default */ }
    setBadge(reason, 'bad');
    term.writeln(`\r\n\x1b[33m[session ${reason}]\x1b[0m`);
    stream.close();
  });
  stream.onerror = () => setBadge('stream lost', 'bad');

  // Keystrokes, coalesced so a fast typist doesn't generate a POST per char.
  let pending = '';
  let flushTimer = null;
  const flush = async () => {
    flushTimer = null;
    const data = pending;
    pending = '';
    if (!data) return;
    try {
      await api(`/api/ssh/${session.sessionId}/input`, {
        method: 'POST',
        body: JSON.stringify({ data }),
      });
    } catch (err) {
      term.writeln(`\r\n\x1b[31m[input failed: ${err.message}]\x1b[0m`);
    }
  };
  term.onData((d) => {
    pending += d;
    // Send immediately on Enter so command latency stays imperceptible.
    if (/[\r\n]/.test(d)) { if (flushTimer) clearTimeout(flushTimer); flush(); return; }
    if (!flushTimer) flushTimer = setTimeout(flush, 15);
  });

  term.onSelectionChange(() => {
    explainBtn.disabled = !term.getSelection().trim();
  });

  const ask = async (question) => {
    const selection = term.getSelection().trim();
    if (!question && !selection) return;
    answerEl.innerHTML = '<div class="tp-spin">thinking…</div>';
    try {
      const r = await api(`/api/ssh/${session.sessionId}/ask`, {
        method: 'POST',
        body: JSON.stringify({ question, selection }),
      });
      answerEl.innerHTML = `
        <div class="tp-meta">${r.selectionChars ? `${r.selectionChars} chars selected · ` : ''}${r.contextChars} chars of scrollback</div>
        <div class="tp-md">${renderAnswer(r.answer)}</div>`;
      answerEl.scrollTop = 0;
    } catch (err) {
      answerEl.innerHTML = `<div class="tp-err">${esc(err.message)}</div>`;
    }
  };

  explainBtn.addEventListener('click', () => ask('Explain this and why it matters. Flag anything risky or non-default.'));
  root.querySelector('#tp-askform').addEventListener('submit', (e) => {
    e.preventDefault();
    const input = root.querySelector('#tp-q');
    const q = input.value.trim();
    if (!q) return;
    input.value = '';
    ask(q);
  });
  root.querySelector('#tp-close').addEventListener('click', closeTerminalPanel);

  const onResize = () => {
    try {
      fit.fit();
      api(`/api/ssh/${session.sessionId}/resize`, {
        method: 'POST',
        body: JSON.stringify({ cols: term.cols, rows: term.rows }),
      }).catch(() => {});
    } catch { /* ignore */ }
  };
  window.addEventListener('resize', onResize);
  onResize();
  term.focus();

  active = { root, term, session, stream, onResize };
}

export function closeTerminalPanel() {
  if (!active) return;
  const { root, term, session, stream, onResize } = active;
  if (onResize) window.removeEventListener('resize', onResize);
  try { stream?.close(); } catch { /* already closed */ }
  if (session?.sessionId) {
    fetch(`/api/ssh/${session.sessionId}`, { method: 'DELETE' }).catch(() => {});
  }
  try { term?.dispose(); } catch { /* already disposed */ }
  root.remove();
  active = null;
}

export function isTerminalOpen() {
  return Boolean(active);
}
