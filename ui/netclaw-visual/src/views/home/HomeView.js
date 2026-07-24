/**
 * 067-home-noc — Home product view (HUD-styled).
 * PR1: Overview mock + sub-nav shells. Live data lands in PR2 via /api/home/*.
 */

const SUBVIEWS = [
  { id: 'overview', label: 'Overview' },
  { id: 'wifi', label: 'Wi‑Fi' },
  { id: 'devices', label: 'Devices' },
  { id: 'diary', label: 'Diary' },
  { id: 'triage', label: 'Triage' },
];

// Placeholder metrics for shell demo (replaced by home-api in PR2)
const MOCK = {
  health: 92,
  latencyMs: 14,
  lossPct: 0.1,
  wifiLabel: '2 APs',
  alerts: 1,
  aps: [
    { name: 'U6-Pro — Office', band24: 'ch 1 / 40 MHz', band5: 'ch 52 / 160 MHz', retries: '28%', clients: 15 },
    { name: 'U6-Pro — Basement', band24: 'ch 11 / 40 MHz', band5: 'ch 120 / 160 MHz', retries: '25%', clients: 20 },
  ],
};

export class HomeView {
  constructor(rootEl) {
    this.root = rootEl;
    this.subview = 'overview';
    this.element = null;
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
    this.syncTopbarMetrics();
    return this.element;
  }

  templateShell() {
    const buttons = SUBVIEWS.map(
      (s) =>
        `<button type="button" class="home-sub-btn${s.id === this.subview ? ' active' : ''}" data-home-sub="${s.id}">${s.label}</button>`,
    ).join('');
    return `
      <div class="home-subnav">
        <p class="eyebrow">NetClaw Home</p>
        ${buttons}
      </div>
      <section class="home-panel" id="home-panel-body"></section>
    `;
  }

  bind() {
    this.element.querySelectorAll('.home-sub-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        this.subview = btn.dataset.homeSub;
        this.element.querySelectorAll('.home-sub-btn').forEach((b) => {
          b.classList.toggle('active', b.dataset.homeSub === this.subview);
        });
        this.renderSubview();
      });
    });
  }

  syncTopbarMetrics() {
    const set = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.textContent = v;
    };
    set('home-metric-health', String(MOCK.health));
    set('home-metric-latency', String(MOCK.latencyMs));
    set('home-metric-wifi', MOCK.wifiLabel);
    set('home-metric-alerts', String(MOCK.alerts));
  }

  renderSubview() {
    const body = this.element.querySelector('#home-panel-body');
    if (!body) return;
    const map = {
      overview: () => this.htmlOverview(),
      wifi: () => this.htmlWifi(),
      devices: () => this.htmlPlaceholder('Devices', 'Edge, APs, and probe targets will load from home-api (PR2).'),
      diary: () => this.htmlPlaceholder('Investigation diary', 'Events from NetClaw investigations will appear here (PR2).'),
      triage: () => this.htmlPlaceholder('Triage', 'Escalated cases + feedback / reinvestigate (PR6).'),
    };
    body.innerHTML = (map[this.subview] || map.overview)();
  }

  htmlOverview() {
    return `
      <div class="home-panel-header">
        <div>
          <p class="eyebrow">Site · home</p>
          <h2>OVERVIEW</h2>
        </div>
        <span class="home-badge mock">Mock data · PR1 shell</span>
      </div>
      <div class="home-kpi-grid">
        <div class="home-kpi">
          <div class="label">Health score</div>
          <div class="value ok">${MOCK.health}</div>
        </div>
        <div class="home-kpi">
          <div class="label">WAN latency</div>
          <div class="value">${MOCK.latencyMs}<span style="font-size:14px;color:var(--muted)"> ms</span></div>
        </div>
        <div class="home-kpi">
          <div class="label">Packet loss</div>
          <div class="value">${MOCK.lossPct}%</div>
        </div>
        <div class="home-kpi">
          <div class="label">Active alerts</div>
          <div class="value warn">${MOCK.alerts}</div>
        </div>
      </div>
      <p class="home-section-title">Pipeline</p>
      <p class="home-muted">
        Full Convergence: metrics → alerts → NetClaw (guardian-claw) → diary / triage → Discord / RAG.
        Live APIs and Docker/K3s deploy land in later 067 tasks. Your existing iN2N risk is preserved;
        setup ensures a guardian investigator for any operator.
      </p>
    `;
  }

  htmlWifi() {
    const rows = MOCK.aps
      .map(
        (a) => `
      <tr>
        <td>${a.name}</td>
        <td>${a.band24}</td>
        <td>${a.band5}</td>
        <td>${a.retries}</td>
        <td>${a.clients}</td>
      </tr>`,
      )
      .join('');
    return `
      <div class="home-panel-header">
        <div>
          <p class="eyebrow">Wireless</p>
          <h2>WI‑FI</h2>
        </div>
        <span class="home-badge mock">Mock · UniFi adapter later</span>
      </div>
      <div class="home-table-wrap">
        <table class="home-table">
          <thead>
            <tr>
              <th>AP</th><th>2.4 GHz</th><th>5 GHz</th><th>Retries</th><th>Clients</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="home-muted" style="margin-top:12px">
        Live source: Prometheus <code>unifi_*</code> + Integration API radios (PR2+).
        TX power is not invented when the vendor API omits it.
      </p>
    `;
  }

  htmlPlaceholder(title, copy) {
    return `
      <div class="home-panel-header">
        <div>
          <p class="eyebrow">NetClaw Home</p>
          <h2>${title.toUpperCase()}</h2>
        </div>
        <span class="home-badge">Coming soon</span>
      </div>
      <div class="home-placeholder">
        <p class="home-muted">${copy}</p>
      </div>
    `;
  }
}
