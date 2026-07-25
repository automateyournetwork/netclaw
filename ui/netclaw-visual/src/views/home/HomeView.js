/**
 * 067-convergence — Home product view (HUD-styled).
 * Live data via HUD proxy /api/home/* → convergence-api / Network Guardian (dual-run).
 */

const SUBVIEWS = [
  { id: 'overview', label: 'Overview' },
  { id: 'wifi', label: 'Wi‑Fi' },
  { id: 'devices', label: 'Devices' },
  { id: 'diary', label: 'Diary' },
  { id: 'triage', label: 'Triage' },
  { id: 'models', label: 'Models' },
];

const SITE = 'home';

async function homeFetch(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = { Accept: 'application/json', ...(options.headers || {}) };
  let body;
  if (options.body != null && method !== 'GET' && method !== 'HEAD') {
    headers['Content-Type'] = 'application/json';
    body = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
  }
  const res = await fetch(`/api/home${path}`, {
    method,
    headers,
    body,
    signal: AbortSignal.timeout(options.timeoutMs || 25000),
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const err = new Error(data?.error || data?.detail || `HTTP ${res.status}`);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fmtMbps(bits) {
  if (bits == null || Number.isNaN(Number(bits))) return '—';
  const n = Number(bits);
  if (n > 1e6) return `${(n / 1e6).toFixed(0)}`;
  if (n > 1e3) return `${(n / 1e3).toFixed(1)}k`;
  return String(n);
}

function statusClass(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'healthy' || s === 'ok' || s === 'resolved') return 'ok';
  if (s === 'degraded' || s === 'warning' || s === 'watch' || s === 'investigating') return 'warn';
  if (s === 'unhealthy' || s === 'critical' || s === 'alert' || s === 'escalated') return 'crit';
  return '';
}

/** Device name → external management GUI (pfSense / UniFi) when mgmtUrl present. */
function nameLink(label, url, title) {
  const text = esc(label || '—');
  if (!url || !/^https?:\/\//i.test(String(url))) return text;
  const href = esc(url);
  const tip = esc(title || `Open management GUI: ${url}`);
  return `<a class="home-mgmt-link" href="${href}" target="_blank" rel="noopener noreferrer" title="${tip}">${text}</a>`;
}

export class HomeView {
  constructor(rootEl) {
    this.root = rootEl;
    this.subview = 'overview';
    this.element = null;
    this.cache = {};
    this.lastError = null;
    this.loading = false;
    /** @type {string|null} selected escalated event id */
    this.selectedEventId = null;
    this.triageBusy = false;
    this.triageFlash = null; // { kind, message }
    this.modelsBusy = false;
    this.modelsFlash = null; // { kind, message }
    /** @type {{ brain?: string, alert?: string, fallback?: string }|null} */
    this.modelsDraft = null;
  }

  mount() {
    if (!this.root) return;
    this.element = document.createElement('div');
    this.element.className = 'home-shell';
    this.element.innerHTML = this.templateShell();
    this.root.innerHTML = '';
    this.root.appendChild(this.element);
    this.bind();
    this.renderSubview();
    this.refresh();
    return this.element;
  }

  templateShell() {
    const buttons = SUBVIEWS.map(
      (s) =>
        `<button type="button" class="home-sub-btn${s.id === this.subview ? ' active' : ''}" data-home-sub="${s.id}">${s.label}</button>`,
    ).join('');
    return `
      <div class="home-frame">
        <div class="home-toolbar">
          <div class="home-toolbar-left">
            <p class="eyebrow home-toolbar-title">NetClaw Convergence</p>
            <div class="home-segmented" role="tablist" aria-label="Convergence sections">
              ${buttons}
            </div>
          </div>
          <button type="button" class="home-refresh-btn" id="home-refresh" title="Refresh data">
            <span class="home-refresh-icon" aria-hidden="true">↻</span>
            <span>Refresh</span>
          </button>
        </div>
        <section class="home-panel" id="home-panel-body"></section>
      </div>
    `;
  }

  bind() {
    this.element.querySelectorAll('.home-sub-btn[data-home-sub]').forEach((btn) => {
      btn.addEventListener('click', () => {
        this.subview = btn.dataset.homeSub;
        this.element.querySelectorAll('.home-sub-btn[data-home-sub]').forEach((b) => {
          b.classList.toggle('active', b.dataset.homeSub === this.subview);
        });
        this.renderSubview();
        this.refresh();
      });
    });
    this.element.querySelector('#home-refresh')?.addEventListener('click', () => this.refresh(true));

    // Models panel actions
    this.element.addEventListener('click', (ev) => {
      const btn = ev.target.closest('[data-models-action]');
      if (!btn || !this.element.contains(btn)) return;
      const action = btn.getAttribute('data-models-action');
      if (action === 'apply') this.handleModelsApply(false);
      else if (action === 'preset') this.handleModelsApply(true, btn.getAttribute('data-preset'));
      else if (action === 'reload') this.refreshModels();
    });
    this.element.addEventListener('input', (ev) => {
      const t = ev.target;
      if (!t || !t.getAttribute || !t.getAttribute('data-models-field')) return;
      if (!this.modelsDraft) this.modelsDraft = {};
      this.modelsDraft[t.getAttribute('data-models-field')] = t.value;
    });

    // Triage actions (event delegation — panel body is re-rendered often)
    this.element.addEventListener('click', (ev) => {
      const sel = ev.target.closest('[data-triage-select]');
      if (sel) {
        this.selectedEventId = sel.getAttribute('data-triage-select');
        this.renderSubview();
        return;
      }
      const actionBtn = ev.target.closest('[data-triage-action]');
      if (actionBtn && !this.triageBusy) {
        const action = actionBtn.getAttribute('data-triage-action');
        const id = actionBtn.getAttribute('data-event-id') || this.selectedEventId;
        if (id && action) this.handleTriageAction(action, id);
      }
    });
  }

  getEscalatedEvents() {
    const raw = this.cache.escalated;
    return raw?.events || raw?.items || (Array.isArray(raw) ? raw : []);
  }

  getSelectedEvent() {
    const events = this.getEscalatedEvents();
    if (!events.length) return null;
    if (this.selectedEventId) {
      const found = events.find((e) => String(e.id) === String(this.selectedEventId));
      if (found) return found;
    }
    return events[0];
  }

  notesFromForm(eventId) {
    const elId = `triage-notes-${String(eventId)}`;
    const ta = this.element?.querySelector(`textarea[id="${elId}"]`);
    return (ta?.value || '').trim();
  }

  async handleTriageAction(action, eventId) {
    if (this.triageBusy) return;
    this.triageBusy = true;
    this.triageFlash = null;
    this.renderSubview();
    const notes = this.notesFromForm(eventId);
    try {
      if (action === 'need_more') {
        const res = await homeFetch(`/events/${encodeURIComponent(eventId)}/reinvestigate?site=${SITE}`, {
          method: 'POST',
          body: { expert_feedback: notes || undefined, site: SITE },
        });
        const st = res?.reinvestigate?.status || 'accepted';
        this.triageFlash = {
          kind: st === 'error' ? 'error' : 'ok',
          message:
            st === 'skipped'
              ? 'Case reopened as investigating. Alert-receiver not configured on convergence-api (set ALERT_RECEIVER_URL to re-hook guardian-claw).'
              : st === 'error'
                ? `Reinvestigate partial: case reopened, but receiver error: ${res?.reinvestigate?.reason || res?.reinvestigate?.detail?.message || 'unknown'}`
                : 'Need More sent — case is investigating; investigator will re-run.',
        };
        this.selectedEventId = null;
      } else {
        // Feedback buttons: correct | partial | incorrect | resolve
        const qualityMap = {
          correct: 'correct',
          partial: 'partially_correct',
          incorrect: 'incorrect',
          resolve: null,
        };
        const feedback_quality = qualityMap[action];
        const body = {
          expert_feedback: notes || undefined,
        };
        if (feedback_quality) body.feedback_quality = feedback_quality;
        if (action === 'correct' || action === 'resolve') {
          body.status = 'resolved';
          body.severity = action === 'correct' ? 'ok' : undefined;
        }
        // incorrect / partial stay escalated unless notes say otherwise
        await homeFetch(`/events/${encodeURIComponent(eventId)}?site=${SITE}`, {
          method: 'PATCH',
          body,
        });
        this.triageFlash = {
          kind: 'ok',
          message:
            action === 'correct'
              ? 'Marked correct and resolved.'
              : action === 'partial'
                ? 'Marked partially correct — still escalated for follow-up.'
                : action === 'incorrect'
                  ? 'Marked incorrect — still escalated; add notes and Need More if re-run needed.'
                  : 'Case resolved.',
        };
        if (action === 'correct' || action === 'resolve') this.selectedEventId = null;
      }
      // Refresh queue
      this.cache.escalated = await homeFetch(`/events/escalated?site=${SITE}`).catch(async () =>
        homeFetch(`/events?site=${SITE}&status=escalated&limit=20`),
      );
      // Keep diary warm
      this.cache.events = await homeFetch(`/events?site=${SITE}&limit=30`).catch(() => this.cache.events);
    } catch (err) {
      this.triageFlash = {
        kind: 'error',
        message: err.message || String(err),
      };
    } finally {
      this.triageBusy = false;
      this.renderSubview();
    }
  }

  async refresh(force = false) {
    // Coalesce concurrent refreshes; still run one more pass if requested while busy
    if (this.loading) {
      this._refreshAgain = true;
      return;
    }
    this.loading = true;
    this.lastError = null;
    this.renderSubview(); // show loading
    try {
      const status = await homeFetch('/status').catch(() => ({ configured: false }));
      this.cache.status = status;

      if (!status.configured) {
        this.lastError = {
          kind: 'config',
          message: 'Convergence API not configured. Set CONVERGENCE_API_URL + CONVERGENCE_API_TOKEN (aliases: HOME_API_* / NETWORK_GUARDIAN_*) in ~/.openclaw/.env',
        };
        this.syncTopbarMetrics(null);
        return;
      }

      // Health + wifi always — top-right Command Deck metrics (Health / WAN / Wi‑Fi / Alerts)
      this.cache.health = await homeFetch(`/health?site=${SITE}`);
      this.cache.wifi = await homeFetch(`/wifi?site=${SITE}`).catch(() => this.cache.wifi || null);

      if (this.subview === 'devices' || force) {
        this.cache.devices = await homeFetch(`/devices?site=${SITE}`);
      }
      if (this.subview === 'diary' || force) {
        this.cache.events = await homeFetch(`/events?site=${SITE}&limit=30`);
        // Firing alerts help when diary DB is still empty (fresh Docker)
        this.cache.alerts = await homeFetch(`/alerts?site=${SITE}`).catch(() => null);
      }
      if (this.subview === 'triage' || force) {
        this.cache.escalated = await homeFetch(`/events/escalated?site=${SITE}`).catch(async () =>
          homeFetch(`/events?site=${SITE}&status=escalated&limit=20`),
        );
      }
      if (this.subview === 'models' || force) {
        await this.refreshModels(false);
      }

      this.syncTopbarMetrics(this.cache.health);
    } catch (err) {
      this.lastError = {
        kind: err.status === 502 || err.status === 503 ? 'down' : 'error',
        message: err.message || String(err),
        detail: err.payload,
      };
      // Keep last good topbar values if we have them
      this.syncTopbarMetrics(this.cache.health || null);
    } finally {
      this.loading = false;
      this.renderSubview();
      if (this._refreshAgain) {
        this._refreshAgain = false;
        this.refresh(true);
      }
    }
  }

  syncTopbarMetrics(health) {
    const set = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.textContent = v;
    };
    // Allow no-arg call to re-use cache (tab switch)
    const h = health === undefined ? this.cache?.health : health;
    if (!h) {
      set('home-metric-health', '—');
      set('home-metric-latency', '—');
      set('home-metric-wifi', '—');
      set('home-metric-alerts', '—');
      return;
    }
    const hs = h.healthScore?.value ?? h.health_score ?? '—';
    const lat = h.wanLatency?.value ?? h.latency ?? '—';
    const alerts = h.alertCount?.firing ?? h.alerts?.firing ?? '—';
    set('home-metric-health', String(hs));
    set('home-metric-latency', lat === '—' ? '—' : String(Math.round(Number(lat) * 10) / 10));
    set('home-metric-wifi', this.cache.wifi?.clients?.wireless != null
      ? `${this.cache.wifi.clients.wireless} cl.`
      : '—');
    set('home-metric-alerts', String(alerts));
  }

  renderSubview() {
    const body = this.element?.querySelector('#home-panel-body');
    if (!body) return;

    if (this.loading && !this.cache.health) {
      body.innerHTML = this.htmlBanner('loading', 'Loading home telemetry…');
      return;
    }
    if (this.lastError) {
      body.innerHTML =
        this.htmlBanner(this.lastError.kind, this.lastError.message) +
        this.htmlBodyForSubview();
      return;
    }
    body.innerHTML = this.htmlBodyForSubview();
  }

  htmlBanner(kind, message) {
    const label =
      kind === 'config' ? 'Not configured' :
      kind === 'down' ? 'API unreachable' :
      kind === 'loading' ? 'Loading' : 'Error';
    return `
      <div class="home-banner home-banner-${esc(kind)}">
        <span class="home-badge ${kind === 'loading' ? '' : 'mock'}">${esc(label)}</span>
        <p class="home-muted" style="margin:8px 0 16px">${esc(message)}</p>
      </div>`;
  }

  htmlBodyForSubview() {
    const map = {
      overview: () => this.htmlOverview(),
      wifi: () => this.htmlWifi(),
      devices: () => this.htmlDevices(),
      diary: () => this.htmlDiary(),
      triage: () => this.htmlTriage(),
      models: () => this.htmlModels(),
    };
    return (map[this.subview] || map.overview)();
  }

  async refreshModels(render = true) {
    try {
      const res = await fetch('/api/models', {
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(10000),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`);
      this.cache.models = data;
      if (!this.modelsDraft) {
        this.modelsDraft = {
          brain: data.sot?.brain || '',
          alert: data.sot?.alert || '',
          fallback: data.sot?.fallback || '',
        };
      }
    } catch (err) {
      this.cache.models = { error: err.message || String(err) };
    }
    if (render && this.subview === 'models') this.renderSubview();
  }

  async handleModelsApply(isPreset, presetName) {
    if (this.modelsBusy) return;
    this.modelsBusy = true;
    this.modelsFlash = { kind: 'ok', message: isPreset ? `Applying preset ${presetName}…` : 'Applying models…' };
    this.renderSubview();
    try {
      // Capture current form values (re-render may wipe inputs)
      const body = isPreset
        ? { preset: presetName, restart: true }
        : {
            brain: this.modelsDraft?.brain || this.element?.querySelector('[data-models-field="brain"]')?.value,
            alert: this.modelsDraft?.alert || this.element?.querySelector('[data-models-field="alert"]')?.value,
            fallback:
              this.modelsDraft?.fallback ??
              this.element?.querySelector('[data-models-field="fallback"]')?.value ??
              '',
            restart: true,
          };
      const res = await fetch('/api/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(120000),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.error || data?.detail || `HTTP ${res.status}`);
      }
      this.modelsDraft = {
        brain: data.sot?.NETCLAW_BRAIN_MODEL || body.brain || this.modelsDraft?.brain,
        alert: data.sot?.NETCLAW_ALERT_TRIAGE_MODEL || body.alert || this.modelsDraft?.alert,
        fallback: data.sot?.NETCLAW_ALERT_FALLBACK_MODEL || body.fallback || this.modelsDraft?.fallback,
      };
      this.modelsFlash = {
        kind: 'ok',
        message: 'Applied to .env + openclaw.json; gateway restarted. Investigations use alert model; chat uses brain.',
      };
      await this.refreshModels(false);
    } catch (err) {
      this.modelsFlash = { kind: 'error', message: err.message || String(err) };
    } finally {
      this.modelsBusy = false;
      this.renderSubview();
    }
  }

  htmlModels() {
    const m = this.cache.models;
    const err = m?.error;
    const sot = m?.sot || {};
    const live = m?.live || {};
    const draft = this.modelsDraft || {
      brain: sot.brain || '',
      alert: sot.alert || '',
      fallback: sot.fallback || '',
    };
    const flash = this.modelsFlash
      ? `<p class="home-flash home-flash-${esc(this.modelsFlash.kind)}">${esc(this.modelsFlash.message)}</p>`
      : '';
    if (err && !sot.file) {
      return `
        <div class="home-panel-header">
          <div><p class="eyebrow">OpenClaw</p><h2>MODELS</h2></div>
        </div>
        ${flash}
        <p class="home-muted">Could not load model status: ${esc(err)}</p>`;
    }
    const liveBrain = live.defaultsPrimary || '—';
    const liveHook = live.hookAlert?.model || '—';
    const liveAgent = live.alertAgent?.primary || live.alertAgent || '—';
    return `
      <div class="home-panel-header">
        <div>
          <p class="eyebrow">SoT · netclaw/.env</p>
          <h2>MODELS</h2>
        </div>
        <button type="button" class="home-refresh-btn" data-models-action="reload" ${this.modelsBusy ? 'disabled' : ''}>Reload</button>
      </div>
      ${flash}
      <p class="home-muted">
        One place to set brains. Edit fields (or pick a preset), then <strong>Apply &amp; restart gateway</strong>.
        Writes <code>NETCLAW_BRAIN_MODEL</code> / <code>NETCLAW_ALERT_TRIAGE_MODEL</code> in
        <code>${esc(sot.file || '…/netclaw/.env')}</code>, projects into
        <code>~/.openclaw/openclaw.json</code> + <code>gateway.systemd.env</code>.
        CLI: <code>./scripts/netclaw-apply-models.sh show|apply|preset cloud-flash</code>
      </p>
      <div class="home-models-grid">
        <div class="home-models-card">
          <p class="home-section-title">Source of truth</p>
          <label class="home-models-label">Brain (interactive main / HUD chat)
            <input type="text" class="home-models-input" data-models-field="brain"
              value="${esc(draft.brain)}" placeholder="ollama/deepseek-v4-flash:cloud"
              ${this.modelsBusy ? 'disabled' : ''} />
          </label>
          <label class="home-models-label">Alert triage (T2 hooks / thin alert agent)
            <input type="text" class="home-models-input" data-models-field="alert"
              value="${esc(draft.alert)}" placeholder="ollama/deepseek-v4-flash:cloud"
              ${this.modelsBusy ? 'disabled' : ''} />
          </label>
          <label class="home-models-label">Alert fallback (optional)
            <input type="text" class="home-models-input" data-models-field="fallback"
              value="${esc(draft.fallback)}" placeholder="ollama/glm-5.2:cloud"
              ${this.modelsBusy ? 'disabled' : ''} />
          </label>
          <div class="home-models-actions">
            <button type="button" class="home-action-btn primary" data-models-action="apply" ${this.modelsBusy ? 'disabled' : ''}>
              ${this.modelsBusy ? 'Applying…' : 'Apply & restart gateway'}
            </button>
          </div>
          <p class="home-section-title" style="margin-top:1rem">Presets</p>
          <div class="home-models-presets">
            <button type="button" class="home-action-btn" data-models-action="preset" data-preset="split" ${this.modelsBusy ? 'disabled' : ''} title="Local chat + cloud investigations">split</button>
            <button type="button" class="home-action-btn" data-models-action="preset" data-preset="cloud-flash" ${this.modelsBusy ? 'disabled' : ''}>cloud-flash</button>
            <button type="button" class="home-action-btn" data-models-action="preset" data-preset="local" ${this.modelsBusy ? 'disabled' : ''}>local</button>
          </div>
        </div>
        <div class="home-models-card">
          <p class="home-section-title">Live OpenClaw</p>
          <div class="home-detail-rows">
            <div class="home-detail-row"><span>defaults.primary</span><strong>${esc(liveBrain)}</strong></div>
            <div class="home-detail-row"><span>hooks.alert.model</span><strong>${esc(liveHook)}</strong></div>
            <div class="home-detail-row"><span>agent alert.primary</span><strong>${esc(typeof liveAgent === 'object' ? liveAgent.primary || JSON.stringify(liveAgent) : liveAgent)}</strong></div>
            <div class="home-detail-row"><span>hook agentId</span><strong>${esc(live.hookAlert?.agentId || '—')}</strong></div>
            <div class="home-detail-row"><span>OLLAMA_BASE_URL</span><strong>${esc(sot.ollamaBaseUrl || '—')}</strong></div>
            <div class="home-detail-row"><span>OLLAMA_API_KEY</span><strong>${sot.ollamaKeySet ? 'set' : '—'}</strong></div>
          </div>
          <p class="home-muted" style="margin-top:0.75rem">
            After Apply, new T2 investigations use the alert model. In-flight sessions keep their original model.
          </p>
        </div>
      </div>
    `;
  }

  htmlOverview() {
    const h = this.cache.health;
    if (!h) {
      return `
        <div class="home-panel-header">
          <div><p class="eyebrow">Site · ${SITE}</p><h2>OVERVIEW</h2></div>
        </div>
        <p class="home-muted">No health data yet. Click Refresh after configuring Home API.</p>`;
    }
    const score = h.healthScore?.value;
    const scoreStatus = h.healthScore?.status || statusClass(score >= 90 ? 'healthy' : score >= 70 ? 'degraded' : 'unhealthy');
    const lat = h.wanLatency?.value;
    const loss = h.wanLoss?.value;
    const dl = h.speedtest?.download;
    const ul = h.speedtest?.upload;
    const firing = h.alertCount?.firing ?? 0;
    const dual = this.cache.status?.dualRun;

    return `
      <div class="home-panel-header">
        <div>
          <p class="eyebrow">Site · ${esc(h.site || SITE)}</p>
          <h2>OVERVIEW</h2>
        </div>
        <span class="home-badge${dual ? '' : ''}">${dual ? 'Dual-run · pilot Guardian' : 'Live'}</span>
      </div>
      <div class="home-kpi-grid" role="group" aria-label="Home health metrics">
        <div class="home-kpi">
          <div class="home-kpi-label">Health score</div>
          <div class="home-kpi-value ${statusClass(scoreStatus)}">${score != null ? esc(score) : '—'}</div>
        </div>
        <div class="home-kpi">
          <div class="home-kpi-label">WAN latency</div>
          <div class="home-kpi-value ${statusClass(h.wanLatency?.status)}">${lat != null ? esc(Number(lat).toFixed(1)) : '—'}<span class="unit"> ms</span></div>
        </div>
        <div class="home-kpi">
          <div class="home-kpi-label">Packet loss</div>
          <div class="home-kpi-value ${statusClass(h.wanLoss?.status)}">${loss != null ? esc(loss) : '—'}<span class="unit">%</span></div>
        </div>
        <div class="home-kpi">
          <div class="home-kpi-label">Speedtest</div>
          <div class="home-kpi-value ${statusClass(h.speedtest?.status)}" title="${
            dl == null
              ? 'No speedtest metrics — enable full stack: docker compose -f docker-compose.yml -f docker-compose.full.yml --profile full up -d'
              : ''
          }">${
            dl != null
              ? `${esc(dl)}<span class="unit"> / ${ul != null ? esc(ul) : '—'} Mbps</span>`
              : 'n/a<span class="unit"> (no runner)</span>'
          }</div>
        </div>
        <div class="home-kpi">
          <div class="home-kpi-label">Firing alerts</div>
          <div class="home-kpi-value ${firing > 0 ? 'warn' : 'ok'}">${esc(firing)}</div>
        </div>
        ${h.devices?.snmpSwitches != null ? `
        <div class="home-kpi" title="Greenfield device_snmp — campus switches">
          <div class="home-kpi-label">Switches (SNMP)</div>
          <div class="home-kpi-value ${statusClass(h.devices.status)}">${esc(h.devices.snmpSwitches)}<span class="unit">${
            h.devices.portsUp != null
              ? ` · ${esc(h.devices.portsUp)}/${esc(h.devices.portsTotal ?? '—')} if`
              : ''
          }</span></div>
        </div>` : ''}
      </div>
      <p class="home-section-title">Pipeline</p>
      <p class="home-muted">
        Metrics → Alertmanager → alert-receiver → risk investigator (guardian-claw) → diary / triage.
        Convergence tab proxies <code>/api/home/*</code> to convergence-api (or pilot Network Guardian during dual-run).
      </p>
    `;
  }

  htmlWifi() {
    const w = this.cache.wifi;
    if (!w) {
      return `<div class="home-panel-header"><div><p class="eyebrow">Wireless</p><h2>WI‑FI</h2></div></div>
        <p class="home-muted">No Wi‑Fi data loaded. Click Refresh.</p>`;
    }
    const clients = w.clients || {};
    const retries = Array.isArray(w.txRetries) ? w.txRetries : [];
    const hasAnyClient =
      [clients.wireless, clients.wired, clients.guest, clients.total].some(
        (v) => v != null && Number(v) > 0,
      );
    const hasSeries = hasAnyClient || retries.length > 0;
    // Group by device
    const byDev = new Map();
    for (const r of retries) {
      const name = r.device || r.name || 'AP';
      if (!byDev.has(name)) byDev.set(name, { name, bands: [] });
      byDev.get(name).bands.push(r);
    }
    const rows = [...byDev.values()]
      .map((d) => {
        const b24 = d.bands.find((b) => /2\.4/i.test(b.band || ''));
        const b5 = d.bands.find((b) => /5/i.test(b.band || ''));
        // Prefer per-row mgmtUrl; fall back to wifi.mgmt.unifi
        const link = nameLink(d.name, d.bands[0]?.mgmtUrl || w.mgmt?.unifi, 'Open UniFi Network console');
        return `<tr>
          <td>${link}</td>
          <td class="${statusClass(b24?.status)}">${b24 ? `${esc(b24.value)}%` : '—'}</td>
          <td class="${statusClass(b5?.status)}">${b5 ? `${esc(b5.value)}%` : '—'}</td>
        </tr>`;
      })
      .join('');

    const emptyHint = !hasSeries
      ? `<div class="home-banner home-banner-config" style="margin:12px 0">
          <span class="home-badge mock">No unifi_* metrics</span>
          <p class="home-muted" style="margin:8px 0 0">
            Wi‑Fi KPIs need the UniFi exporter. On Docker Convergence:
            set <code>UNIFI_HOST</code> + <code>UNIFI_API_KEY</code> in <code>deploy/convergence/.env</code>, then
            <code>docker compose -f deploy/convergence/docker-compose.yml --env-file deploy/convergence/.env --profile unifi up -d</code>.
            Until then Overview WAN probes still work; this tab will stay empty.
          </p>
        </div>`
      : '';

    return `
      <div class="home-panel-header">
        <div>
          <p class="eyebrow">Wireless · ${esc(clients.wireless ?? '—')} clients</p>
          <h2>WI‑FI</h2>
        </div>
        <span class="home-badge${hasSeries ? '' : ' mock'}">${hasSeries ? 'Live · unifi_*' : 'Waiting · unifi'}</span>
      </div>
      ${emptyHint}
      <div class="home-kpi-grid home-kpi-grid-4">
        <div class="home-kpi"><div class="home-kpi-label">Wireless</div><div class="home-kpi-value">${esc(clients.wireless ?? '—')}</div></div>
        <div class="home-kpi"><div class="home-kpi-label">Wired</div><div class="home-kpi-value">${esc(clients.wired ?? '—')}</div></div>
        <div class="home-kpi"><div class="home-kpi-label">Guest</div><div class="home-kpi-value">${esc(clients.guest ?? '—')}</div></div>
        <div class="home-kpi"><div class="home-kpi-label">Total</div><div class="home-kpi-value">${esc(clients.total ?? '—')}</div></div>
      </div>
      <p class="home-section-title">TX retries by AP / band</p>
      <div class="home-table-wrap">
        <table class="home-table">
          <thead><tr><th>AP</th><th>2.4 GHz retries</th><th>5 GHz retries</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="3">No retry series yet</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }

  htmlDevices() {
    const d = this.cache.devices;
    if (!d) {
      return `<div class="home-panel-header"><div><p class="eyebrow">Inventory</p><h2>DEVICES</h2></div></div>
        <p class="home-muted">No device data loaded. Click Refresh.</p>`;
    }

    // convergence-api shape: { wanProbes, edge/firewall, accessPoints, switches }
    const probes = Array.isArray(d.wanProbes) ? d.wanProbes : [];
    const edge = Array.isArray(d.edge) ? d.edge : (Array.isArray(d.firewall) ? d.firewall : []);
    const aps = Array.isArray(d.accessPoints) ? d.accessPoints : [];
    const switches = Array.isArray(d.switches) ? d.switches : [];
    const flat = Array.isArray(d.devices) ? d.devices : Array.isArray(d) ? d : d.items || [];

    const probeRows = probes
      .map((p) => {
        const st = p.status || '';
        return `<tr>
          <td>${esc(p.target || p.endpoint || '—')}</td>
          <td>${esc(p.type || 'probe')}</td>
          <td class="${statusClass(st === 'online' || st === 'up' ? 'healthy' : st === 'offline' || st === 'down' ? 'unhealthy' : st)}">${esc(st || '—')}</td>
          <td>${p.latencyMs != null ? `${esc(p.latencyMs)} ms` : '—'}</td>
        </tr>`;
      })
      .join('');

    const edgeRows = edge
      .map((e) => {
        const st = e.status || '';
        const detail = [
          e.model,
          e.latencyMs != null ? `${e.latencyMs} ms` : null,
          e.cpu != null && e.cpu > 0 ? `CPU ${e.cpu}%` : null,
          e.endpoint,
        ].filter(Boolean).join(' · ');
        return `<tr>
          <td>${nameLink(e.name || '—', e.mgmtUrl, 'Open pfSense / edge management')}</td>
          <td>${esc(e.role || 'firewall')}</td>
          <td class="${statusClass(st === 'online' || st === 'up' ? 'healthy' : 'unhealthy')}">${esc(st || '—')}</td>
          <td>${esc(detail)}</td>
        </tr>`;
      })
      .join('');

    const apRows = aps
      .map((ap) => {
        const st = ap.status || (ap.up === 1 || ap.up === true ? 'online' : ap.up === 0 ? 'offline' : '');
        const detail = [
          ap.clients != null ? `${ap.clients} clients` : null,
          ap.cpu != null ? `CPU ${ap.cpu}%` : null,
          ap.memory != null ? `Mem ${ap.memory}%` : null,
          ap.uptime || null,
        ].filter(Boolean).join(' · ');
        return `<tr>
          <td>${nameLink(ap.name || ap.device || '—', ap.mgmtUrl || d.mgmt?.unifi, 'Open UniFi Network console')}</td>
          <td>${esc(ap.model || 'AP')}</td>
          <td class="${statusClass(st === 'online' || st === 'up' ? 'healthy' : 'unhealthy')}">${esc(st || '—')}</td>
          <td>${esc(detail || ap.mac || '')}</td>
        </tr>`;
      })
      .join('');

    const swRows = switches
      .map((sw) => {
        const st = sw.status || '';
        const portsUp = sw.portsUp ?? sw.interfacesUp;
        const portsTotal = sw.portsTotal ?? sw.interfacesTotal;
        const detail = [
          portsUp != null ? `${portsUp}/${portsTotal ?? '—'} ports up` : null,
          sw.model,
          sw.cpu != null && sw.cpu > 0 ? `CPU ${sw.cpu}%` : null,
          sw.source ? `src:${sw.source}` : null,
        ].filter(Boolean).join(' · ');
        return `<tr>
          <td>${nameLink(sw.name || sw.device_name || '—', sw.mgmtUrl, 'Open switch management')}</td>
          <td>Switch</td>
          <td class="${statusClass(st === 'online' || st === 'up' ? 'healthy' : st)}">${esc(st || '—')}</td>
          <td>${esc(detail)}</td>
        </tr>`;
      })
      .join('');

    const flatRows = flat
      .map((dev) => {
        const name = dev.name || dev.device || dev.id || '—';
        const role = dev.role || dev.type || '';
        const status = dev.status || dev.state || (dev.up === 1 || dev.up === true ? 'up' : dev.up === 0 ? 'down' : '');
        const ip = dev.ip || dev.instance || '';
        return `<tr>
          <td>${esc(name)}</td>
          <td>${esc(role)}</td>
          <td class="${statusClass(status === 'up' || status === 'online' ? 'healthy' : status === 'down' ? 'unhealthy' : status)}">${esc(status || '—')}</td>
          <td>${esc(ip)}</td>
        </tr>`;
      })
      .join('');

    const hasStructured = probes.length || edge.length || aps.length || switches.length;
    const body = hasStructured
      ? `
      ${edge.length ? `
        <p class="home-section-title">Firewall / edge</p>
        <div class="home-table-wrap">
          <table class="home-table">
            <thead><tr><th>Name</th><th>Role</th><th>Status</th><th>Detail</th></tr></thead>
            <tbody>${edgeRows}</tbody>
          </table>
        </div>` : `
        <p class="home-section-title">Firewall / edge</p>
        <p class="home-muted">No edge probe yet. Docker stack probes pfSense HTTPS when <code>blackbox_edge</code> is configured.</p>`}
      ${probes.length ? `
        <p class="home-section-title">WAN / blackbox probes</p>
        <div class="home-table-wrap">
          <table class="home-table">
            <thead><tr><th>Target</th><th>Type</th><th>Status</th><th>Latency</th></tr></thead>
            <tbody>${probeRows}</tbody>
          </table>
        </div>` : ''}
      ${aps.length ? `
        <p class="home-section-title">Access points (UniFi)</p>
        <div class="home-table-wrap">
          <table class="home-table">
            <thead><tr><th>Name</th><th>Model</th><th>Status</th><th>Detail</th></tr></thead>
            <tbody>${apRows}</tbody>
          </table>
        </div>` : `
        <p class="home-section-title">Access points</p>
        <p class="home-muted">No APs — enable UniFi exporter (<code>--profile unifi</code>).</p>`}
      ${switches.length ? `
        <p class="home-section-title">Switches</p>
        <div class="home-table-wrap">
          <table class="home-table">
            <thead><tr><th>Name</th><th>Role</th><th>Status</th><th>Detail</th></tr></thead>
            <tbody>${swRows}</tbody>
          </table>
        </div>` : `
        <p class="home-section-title">Switches</p>
        <p class="home-muted">
          No switch series yet. UniFi switches appear when adopted in the controller.
          Campus Cisco IF-MIB: <code>docker compose --profile device-snmp up -d</code>
          (or K3s <code>components/device-snmp</code>). Greenfield metrics use
          <code>ifOperStatus{job="device_snmp"}</code>.
        </p>`}
      `
      : `
      <div class="home-table-wrap">
        <table class="home-table">
          <thead><tr><th>Name</th><th>Role</th><th>Status</th><th>IP / instance</th></tr></thead>
          <tbody>${flatRows || '<tr><td colspan="4">No devices in response</td></tr>'}</tbody>
        </table>
      </div>`;

    return `
      <div class="home-panel-header">
        <div><p class="eyebrow">Edge · APs · probes</p><h2>DEVICES</h2></div>
        <span class="home-badge">Live</span>
      </div>
      ${body}
    `;
  }

  htmlDiary() {
    const ev = this.cache.events;
    const events = ev?.events || ev?.items || [];
    const alerts = this.cache.alerts;
    const firing = alerts?.firing || alerts?.alerts || [];
    const rows = events
      .map((e) => {
        const rag = e.rag_document_id
          ? `<code class="home-rag-id" title="RAG snapshot id">${esc(e.rag_document_id)}</code>`
          : '<span class="home-muted">—</span>';
        return `<tr>
        <td>${esc((e.timestamp || e.created_at || '').toString().slice(0, 19))}</td>
        <td class="${statusClass(e.status)}">${esc(e.status)}</td>
        <td class="${statusClass(e.severity)}">${esc(e.severity)}</td>
        <td>${esc(e.alert_name || e.category || '')}</td>
        <td>${esc((e.message || '').slice(0, 100))}</td>
        <td>${rag}</td>
      </tr>`;
      })
      .join('');

    const alertRows = (Array.isArray(firing) ? firing : [])
      .map((a) => `<tr>
        <td>${esc((a.startsAt || a.starts_at || '').toString().slice(0, 19))}</td>
        <td class="${statusClass(a.severity)}">${esc(a.severity || '')}</td>
        <td>${esc(a.name || a.alertname || a.labels?.alertname || '')}</td>
        <td>${esc(a.summary || a.annotations?.summary || a.duration || '')}</td>
      </tr>`)
      .join('');

    return `
      <div class="home-panel-header">
        <div><p class="eyebrow">Investigations</p><h2>DIARY</h2></div>
        <span class="home-badge">Live · events</span>
      </div>
      ${!events.length ? `
        <p class="home-muted" style="margin-bottom:12px">
          Diary rows are written when alert-receiver / guardian-claw posts investigations to
          <code>POST /api/events</code>. An empty table is normal on a fresh Docker stack until
          alerts flow through the host webhook (Alertmanager → :8099 → NetClaw).
        </p>` : ''}
      <div class="home-table-wrap">
        <table class="home-table">
          <thead><tr><th>When</th><th>Status</th><th>Sev</th><th>Alert</th><th>Message</th><th>RAG id</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="6">No diary events yet</td></tr>'}</tbody>
        </table>
      </div>
      ${alertRows ? `
        <p class="home-section-title">Firing alerts (Alertmanager)</p>
        <div class="home-table-wrap">
          <table class="home-table">
            <thead><tr><th>Since</th><th>Sev</th><th>Alert</th><th>Summary</th></tr></thead>
            <tbody>${alertRows}</tbody>
          </table>
        </div>` : ''}
    `;
  }

  htmlTriage() {
    const events = this.getEscalatedEvents();
    const selected = this.getSelectedEvent();
    const flash = this.triageFlash
      ? `<div class="home-banner home-banner-${esc(this.triageFlash.kind === 'error' ? 'error' : 'ok')}" style="margin-bottom:12px">
           <span class="home-badge">${this.triageFlash.kind === 'error' ? 'Error' : 'Done'}</span>
           <p class="home-muted" style="margin:8px 0 0">${esc(this.triageFlash.message)}</p>
         </div>`
      : '';
    const busy = this.triageBusy ? ' is-busy' : '';

    const list = events
      .map((e) => {
        const active = selected && String(e.id) === String(selected.id) ? ' active' : '';
        const when = (e.escalated_at || e.timestamp || '').toString().slice(0, 19);
        return `
          <button type="button" class="home-triage-item${active}" data-triage-select="${esc(e.id)}">
            <span class="home-triage-item-when">${esc(when)}</span>
            <span class="home-triage-item-alert">${esc(e.alert_name || 'case')}</span>
            <span class="home-triage-item-msg">${esc((e.message || '').slice(0, 90))}</span>
            ${e.rag_document_id ? '<span class="home-rag-chip" title="RAG document">RAG</span>' : ''}
          </button>`;
      })
      .join('');

    let detail = `
      <div class="home-triage-empty">
        <p class="home-muted">No escalated cases. Cases appear when the investigator sets
        <code>status=escalated</code> (needs human action). Use Diary for the full timeline.</p>
      </div>`;

    if (selected) {
      const id = selected.id;
      const ragBlock = selected.rag_document_id
        ? `<div class="home-triage-field">
             <span class="home-triage-label">RAG document</span>
             <code class="home-rag-id">${esc(selected.rag_document_id)}</code>
             ${selected.rag_snapshotted_at ? `<span class="home-muted"> · ${esc(String(selected.rag_snapshotted_at).slice(0, 19))}</span>` : ''}
           </div>`
        : `<div class="home-triage-field">
             <span class="home-triage-label">RAG document</span>
             <span class="home-muted">Not snapshotted yet</span>
           </div>`;

      detail = `
        <div class="home-triage-detail${busy}">
          <div class="home-triage-detail-head">
            <div>
              <p class="eyebrow">${esc(selected.alert_name || 'Investigation')}</p>
              <h3 class="home-triage-title">${esc(selected.message || 'Escalated case')}</h3>
            </div>
            <span class="home-badge crit">escalated</span>
          </div>
          <div class="home-triage-meta">
            <span>id <code>${esc(String(id).slice(0, 8))}…</code></span>
            <span class="${statusClass(selected.severity)}">sev ${esc(selected.severity || '—')}</span>
            <span>${esc((selected.escalated_at || selected.timestamp || '').toString().slice(0, 19))}</span>
          </div>
          <div class="home-triage-field">
            <span class="home-triage-label">Root cause</span>
            <p>${esc(selected.root_cause || '—')}</p>
          </div>
          <div class="home-triage-field">
            <span class="home-triage-label">Investigation notes</span>
            <pre class="home-triage-notes-pre">${esc(selected.investigation_notes || '—')}</pre>
          </div>
          ${ragBlock}
          ${selected.expert_feedback ? `
            <div class="home-triage-field">
              <span class="home-triage-label">Prior operator feedback</span>
              <p>${esc(selected.expert_feedback)}
                ${selected.feedback_quality ? ` <span class="home-muted">(${esc(selected.feedback_quality)})</span>` : ''}
              </p>
            </div>` : ''}
          <label class="home-triage-field" for="triage-notes-${esc(id)}">
            <span class="home-triage-label">Your notes (optional)</span>
            <textarea id="triage-notes-${esc(id)}" class="home-triage-textarea" rows="3"
              placeholder="Context for the investigator or diary…"></textarea>
          </label>
          <div class="home-triage-actions" role="group" aria-label="Feedback">
            <button type="button" class="home-triage-btn ok" data-triage-action="correct" data-event-id="${esc(id)}"
              ${this.triageBusy ? 'disabled' : ''}>Correct</button>
            <button type="button" class="home-triage-btn warn" data-triage-action="partial" data-event-id="${esc(id)}"
              ${this.triageBusy ? 'disabled' : ''}>Partial</button>
            <button type="button" class="home-triage-btn crit" data-triage-action="incorrect" data-event-id="${esc(id)}"
              ${this.triageBusy ? 'disabled' : ''}>Incorrect</button>
            <button type="button" class="home-triage-btn accent" data-triage-action="need_more" data-event-id="${esc(id)}"
              ${this.triageBusy ? 'disabled' : ''}>Need More</button>
            <button type="button" class="home-triage-btn ghost" data-triage-action="resolve" data-event-id="${esc(id)}"
              ${this.triageBusy ? 'disabled' : ''}>Resolve</button>
          </div>
          <p class="home-muted home-triage-hint">
            <strong>Need More</strong> reopens the case as <code>investigating</code> and re-triggers the host
            investigation pipe when alert-receiver is reachable. Other buttons write operator feedback via PATCH.
          </p>
        </div>`;
    }

    return `
      <div class="home-panel-header">
        <div><p class="eyebrow">Operator queue</p><h2>TRIAGE</h2></div>
        <span class="home-badge">Live · ${esc(String(events.length))} escalated</span>
      </div>
      ${flash}
      <p class="home-muted" style="margin-bottom:12px">
        Review escalated investigations, leave feedback, or request a deeper re-run without leaving the HUD.
      </p>
      <div class="home-triage-layout">
        <div class="home-triage-list" role="listbox" aria-label="Escalated cases">
          ${list || '<p class="home-muted">Queue empty</p>'}
        </div>
        <div class="home-triage-detail-wrap">
          ${detail}
        </div>
      </div>
    `;
  }
}
