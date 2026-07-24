/**
 * 067-home-noc — Home product view (HUD-styled).
 * Live data via HUD proxy /api/home/* → home-api / Network Guardian (dual-run).
 */

const SUBVIEWS = [
  { id: 'overview', label: 'Overview' },
  { id: 'wifi', label: 'Wi‑Fi' },
  { id: 'devices', label: 'Devices' },
  { id: 'diary', label: 'Diary' },
  { id: 'triage', label: 'Triage' },
];

const SITE = 'home';

async function homeFetch(path) {
  const res = await fetch(`/api/home${path}`, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(20000),
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

export class HomeView {
  constructor(rootEl) {
    this.root = rootEl;
    this.subview = 'overview';
    this.element = null;
    this.cache = {};
    this.lastError = null;
    this.loading = false;
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
            <p class="eyebrow home-toolbar-title">NetClaw Home</p>
            <div class="home-segmented" role="tablist" aria-label="Home sections">
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
  }

  async refresh(force = false) {
    if (this.loading) return;
    this.loading = true;
    this.lastError = null;
    this.renderSubview(); // show loading
    try {
      const status = await homeFetch('/status').catch(() => ({ configured: false }));
      this.cache.status = status;

      if (!status.configured) {
        this.lastError = {
          kind: 'config',
          message: 'Home API not configured. Set NETWORK_GUARDIAN_URL + NETWORK_GUARDIAN_TOKEN (or HOME_API_*) in ~/.openclaw/.env',
        };
        this.syncTopbarMetrics(null);
        return;
      }

      if (this.subview === 'overview' || force) {
        this.cache.health = await homeFetch(`/health?site=${SITE}`);
      }
      if (this.subview === 'wifi' || force) {
        this.cache.wifi = await homeFetch(`/wifi?site=${SITE}`);
      }
      if (this.subview === 'devices' || force) {
        this.cache.devices = await homeFetch(`/devices?site=${SITE}`);
      }
      if (this.subview === 'diary' || force) {
        this.cache.events = await homeFetch(`/events?site=${SITE}&limit=30`);
      }
      if (this.subview === 'triage' || force) {
        this.cache.escalated = await homeFetch(`/events/escalated?site=${SITE}`).catch(async () =>
          homeFetch(`/events?site=${SITE}&status=escalated&limit=20`),
        );
      }

      // Always refresh health for topbar when possible
      if (!this.cache.health) {
        this.cache.health = await homeFetch(`/health?site=${SITE}`);
      }
      this.syncTopbarMetrics(this.cache.health);
    } catch (err) {
      this.lastError = {
        kind: err.status === 502 || err.status === 503 ? 'down' : 'error',
        message: err.message || String(err),
        detail: err.payload,
      };
      this.syncTopbarMetrics(null);
    } finally {
      this.loading = false;
      this.renderSubview();
    }
  }

  syncTopbarMetrics(health) {
    const set = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.textContent = v;
    };
    if (!health) {
      set('home-metric-health', '—');
      set('home-metric-latency', '—');
      set('home-metric-wifi', '—');
      set('home-metric-alerts', '—');
      return;
    }
    const hs = health.healthScore?.value ?? health.health_score ?? '—';
    const lat = health.wanLatency?.value ?? health.latency ?? '—';
    const alerts = health.alertCount?.firing ?? health.alerts?.firing ?? '—';
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
    };
    return (map[this.subview] || map.overview)();
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
          <div class="home-kpi-value ${statusClass(h.speedtest?.status)}">${dl != null ? esc(dl) : '—'}<span class="unit"> / ${ul != null ? esc(ul) : '—'} Mbps</span></div>
        </div>
        <div class="home-kpi">
          <div class="home-kpi-label">Firing alerts</div>
          <div class="home-kpi-value ${firing > 0 ? 'warn' : 'ok'}">${esc(firing)}</div>
        </div>
      </div>
      <p class="home-section-title">Pipeline</p>
      <p class="home-muted">
        Metrics → Alertmanager → alert-receiver → risk investigator (guardian-claw) → diary / triage.
        HOME tab proxies <code>/api/home/*</code> to home-api (or pilot Network Guardian during dual-run).
      </p>
    `;
  }

  htmlWifi() {
    const w = this.cache.wifi;
    if (!w) {
      return `<div class="home-panel-header"><div><p class="eyebrow">Wireless</p><h2>WI‑FI</h2></div></div>
        <p class="home-muted">No Wi‑Fi data loaded.</p>`;
    }
    const clients = w.clients || {};
    const retries = Array.isArray(w.txRetries) ? w.txRetries : [];
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
        return `<tr>
          <td>${esc(d.name)}</td>
          <td class="${statusClass(b24?.status)}">${b24 ? `${esc(b24.value)}%` : '—'}</td>
          <td class="${statusClass(b5?.status)}">${b5 ? `${esc(b5.value)}%` : '—'}</td>
        </tr>`;
      })
      .join('');

    return `
      <div class="home-panel-header">
        <div>
          <p class="eyebrow">Wireless · ${esc(clients.wireless ?? '—')} clients</p>
          <h2>WI‑FI</h2>
        </div>
        <span class="home-badge">Live · unifi_*</span>
      </div>
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
          <tbody>${rows || '<tr><td colspan="3">No retry series</td></tr>'}</tbody>
        </table>
      </div>
      <p class="home-muted" style="margin-top:12px">Channel/width from Integration API lands with agent tools; this view uses Prometheus export.</p>
    `;
  }

  htmlDevices() {
    const d = this.cache.devices;
    if (!d) {
      return `<div class="home-panel-header"><div><p class="eyebrow">Inventory</p><h2>DEVICES</h2></div></div>
        <p class="home-muted">No device data loaded.</p>`;
    }
    // API shape may be { devices: [...] } or array
    const list = Array.isArray(d.devices) ? d.devices : Array.isArray(d) ? d : d.items || [];
    const rows = list
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

    return `
      <div class="home-panel-header">
        <div><p class="eyebrow">Edge · APs · probes</p><h2>DEVICES</h2></div>
        <span class="home-badge">Live</span>
      </div>
      <div class="home-table-wrap">
        <table class="home-table">
          <thead><tr><th>Name</th><th>Role</th><th>Status</th><th>IP / instance</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4">No devices in response — check API shape</td></tr>'}</tbody>
        </table>
      </div>
      ${!list.length ? `<pre class="home-muted" style="font-size:11px;overflow:auto">${esc(JSON.stringify(d, null, 2).slice(0, 800))}</pre>` : ''}
    `;
  }

  htmlDiary() {
    const ev = this.cache.events;
    const events = ev?.events || ev?.items || [];
    const rows = events
      .map((e) => `<tr>
        <td>${esc((e.timestamp || e.created_at || '').toString().slice(0, 19))}</td>
        <td class="${statusClass(e.status)}">${esc(e.status)}</td>
        <td class="${statusClass(e.severity)}">${esc(e.severity)}</td>
        <td>${esc(e.alert_name || e.category || '')}</td>
        <td>${esc((e.message || '').slice(0, 120))}</td>
      </tr>`)
      .join('');

    return `
      <div class="home-panel-header">
        <div><p class="eyebrow">Investigations</p><h2>DIARY</h2></div>
        <span class="home-badge">Live · events</span>
      </div>
      <div class="home-table-wrap">
        <table class="home-table">
          <thead><tr><th>When</th><th>Status</th><th>Sev</th><th>Alert</th><th>Message</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="5">No events</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }

  htmlTriage() {
    const raw = this.cache.escalated;
    const events = raw?.events || raw?.items || (Array.isArray(raw) ? raw : []);
    const rows = events
      .map((e) => `<tr>
        <td>${esc((e.timestamp || '').toString().slice(0, 19))}</td>
        <td>${esc(e.alert_name || '')}</td>
        <td>${esc((e.message || '').slice(0, 100))}</td>
        <td>${esc((e.root_cause || '').slice(0, 80))}</td>
      </tr>`)
      .join('');

    return `
      <div class="home-panel-header">
        <div><p class="eyebrow">Operator queue</p><h2>TRIAGE</h2></div>
        <span class="home-badge">Live · escalated</span>
      </div>
      <p class="home-muted" style="margin-bottom:12px">Feedback buttons + reinvestigate land in a later 067 phase. Review notes here for now.</p>
      <div class="home-table-wrap">
        <table class="home-table">
          <thead><tr><th>When</th><th>Alert</th><th>Message</th><th>Root cause</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4">No escalated cases</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }
}
