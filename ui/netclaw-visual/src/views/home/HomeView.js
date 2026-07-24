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
        // Firing alerts help when diary DB is still empty (fresh Docker)
        this.cache.alerts = await homeFetch(`/alerts?site=${SITE}`).catch(() => null);
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
            Wi‑Fi KPIs need the UniFi exporter. On Docker Home:
            set <code>UNIFI_HOST</code> + <code>UNIFI_API_KEY</code> in <code>deploy/home/.env</code>, then
            <code>docker compose -f deploy/home/docker-compose.yml --env-file deploy/home/.env --profile unifi up -d</code>.
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

    // home-api shape: { wanProbes, edge/firewall, accessPoints, switches }
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
          No switch series on this stack. UniFi switches appear when adopted in the controller.
          Cisco <code>HomeSwitch*</code> need SNMP → VictoriaMetrics (pilot OBS), not Docker minimal.
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
      .map((e) => `<tr>
        <td>${esc((e.timestamp || e.created_at || '').toString().slice(0, 19))}</td>
        <td class="${statusClass(e.status)}">${esc(e.status)}</td>
        <td class="${statusClass(e.severity)}">${esc(e.severity)}</td>
        <td>${esc(e.alert_name || e.category || '')}</td>
        <td>${esc((e.message || '').slice(0, 120))}</td>
      </tr>`)
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
          <thead><tr><th>When</th><th>Status</th><th>Sev</th><th>Alert</th><th>Message</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="5">No diary events yet</td></tr>'}</tbody>
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
      <p class="home-muted" style="margin-bottom:12px">
        Escalated cases appear after investigations mark events <code>escalated</code>.
        Feedback + reinvestigate UI is Phase 6. Empty queue is expected until the agent posts events.
      </p>
      <div class="home-table-wrap">
        <table class="home-table">
          <thead><tr><th>When</th><th>Alert</th><th>Message</th><th>Root cause</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4">No escalated cases</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }
}
