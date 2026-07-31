/**
 * KnowledgePanel - HUD component for the RAG Knowledge Base (Feature 062)
 *
 * Upload area (drag-and-drop + file picker), indexed-documents table rendered
 * from /api/rag/documents (no hardcoded data), per-row Delete / Re-index
 * actions behind confirm dialogs, live ingestion progress chips via the
 * 'rag_progress' WebSocket event, and a visually distinct snapshot section
 * with capture-age badges.
 *
 * Integration (TwitterPanel convention):
 * 1. import { KnowledgePanel } from './panels/KnowledgePanel.js';
 * 2. const panel = new KnowledgePanel(state.socket);
 * 3. document.body.appendChild(panel.render());
 */

import './KnowledgePanel.css';

const SUPPORTED_EXT = ['.pdf', '.md', '.markdown', '.html', '.htm', '.txt', '.json',
  '.docx', '.xlsx', '.pptx', '.vsdx', '.doc', '.xls', '.ppt', '.vsd'];
const DOC_TYPES = ['other', 'vendor', 'standard', 'customer', 'install-guide'];

const GEOM_KEY = 'netclaw.hud.knowledgePanel.v1';

export class KnowledgePanel {
  constructor(socket = null, { docked = false } = {}) {
    this.socket = socket;
    this.docked = docked;
    this.documents = [];
    this.snapshots = [];
    this.progress = new Map(); // document_id/title -> {status, error}
    this.stats = null;
    this.element = null;
    this.isCollapsed = true;
    this._drag = null;
    this._resize = null;
    this._userPositioned = false;

    this.handleSocketMessage = this.handleSocketMessage.bind(this);
  }

  render() {
    this.element = document.createElement('div');
    this.element.id = 'knowledge-panel';
    this.element.className = `knowledge-panel collapsed${this.docked ? ' kp-docked' : ''}`;
    this.element.innerHTML = this.getTemplate();
    this.setupEventListeners();
    if (!this.docked) {
      this.setupDragResize();
      this.restoreGeometry();
    }
    if (this.socket) this.connectSocket();
    this.refresh();
    return this.element;
  }

  getTemplate() {
    const headerTitle = this.docked
      ? 'Double-click to expand/collapse'
      : 'Drag to move · double-click to expand/collapse';
    return `
      <div class="kp-header" title="${headerTitle}">
        <div class="kp-title">
          <span class="kp-icon">&#128218;</span>
          <span>Knowledge</span>
          <span class="kp-stats" id="kp-stats"></span>
        </div>
        <div class="kp-header-actions">
          <button type="button" class="kp-reset-btn" title="Reset position" aria-label="Reset panel position">&#8634;</button>
          <button type="button" class="kp-collapse-btn" title="Expand/collapse" aria-expanded="false">&#9662;</button>
        </div>
      </div>
      <div class="kp-body">
        <p class="kp-ops-hint">
          Upload vendor PDFs as type <strong>vendor</strong>.
          <strong>Crawl site to RAG</strong> multi-page crawls HTML docs (can take minutes).
          Green <em>ready</em> with few chunks usually means a thin/JS-only page — not a full API manual.
          <strong>Ingest page</strong> = one URL only (fast).
          OpenAPI <code>.json</code> (e.g. developer.ui.com/…/openapi.json) is supported via Upload or Ingest page.
        </p>
        <div class="kp-upload" id="kp-dropzone">
          <input type="file" id="kp-file-input" accept="${SUPPORTED_EXT.join(',')}" hidden />
          <select id="kp-doc-type" title="Document type — use vendor for UniFi/pfSense/Cisco docs">
            ${DOC_TYPES.map((t) => `<option value="${t}"${t === 'vendor' ? ' selected' : ''}>${t}</option>`).join('')}
          </select>
          <button type="button" id="kp-pick-btn">Upload file</button>
          <span class="kp-drop-hint">or drop a file here</span>
        </div>
        <div class="kp-url-row">
          <input type="url" id="kp-url-input" class="kp-url-input"
            placeholder="https://… vendor doc or handbook page"
            spellcheck="false" autocomplete="off" />
          <label class="kp-insecure-label" title="For UniFi/pfSense self-signed certs on LAN">
            <input type="checkbox" id="kp-url-insecure" checked />
            Allow insecure TLS
          </label>
          <button type="button" id="kp-url-preview-btn" title="Fetch page + list same-domain links">Preview URL</button>
          <button type="button" id="kp-url-ingest-btn" title="Ingest this page only">Ingest page</button>
          <button type="button" id="kp-url-crawl-btn" title="Crawl multi-page docs site → PDF/MD → RAG (use for UniFi API site)">Crawl site to RAG</button>
        </div>
        <div class="kp-crawl-opts" title="Used by Crawl site to RAG">
          <label>Max pages <input type="number" id="kp-crawl-max" min="1" max="150" value="60" /></label>
          <label>Depth <input type="number" id="kp-crawl-depth" min="0" max="5" value="2" /></label>
        </div>
        <div class="kp-url-preview" id="kp-url-preview" hidden></div>
        <div class="kp-progress" id="kp-progress"></div>
        <div class="kp-section-title">Documents <span class="kp-snap-note">vendor PDFs / site crawls — look for high chunk counts</span></div>
        <div class="kp-table-wrap">
          <table class="kp-table">
            <thead><tr>
              <th>Title</th><th>Type</th><th>Source</th><th>Pages</th>
              <th>Chunks</th><th>Ingested</th><th></th>
            </tr></thead>
            <tbody id="kp-doc-rows"><tr><td colspan="7" class="kp-empty">Loading…</td></tr></tbody>
          </table>
        </div>
        <div class="kp-section-title kp-snap-title">Snapshots <span class="kp-snap-note">past alert investigations (WifiDegraded…) — NOT crawl results</span></div>
        <div class="kp-table-wrap kp-snapshots">
          <table class="kp-table">
            <thead><tr>
              <th>Label</th><th>Source</th><th>Chunks</th><th>Captured</th><th></th>
            </tr></thead>
            <tbody id="kp-snap-rows"><tr><td colspan="5" class="kp-empty">No snapshots</td></tr></tbody>
          </table>
        </div>
      </div>
      <div class="kp-resize-handle" title="Drag to resize" aria-hidden="true"></div>
    `;
  }

  setupEventListeners() {
    const setCollapsed = (collapsed) => {
      this.isCollapsed = collapsed;
      this.element.classList.toggle('collapsed', this.isCollapsed);
      const btn = this.element.querySelector('.kp-collapse-btn');
      if (btn) {
        btn.title = this.isCollapsed ? 'Expand knowledge base' : 'Collapse knowledge base';
        btn.setAttribute('aria-expanded', this.isCollapsed ? 'false' : 'true');
        btn.innerHTML = this.isCollapsed ? '&#9652;' : '&#9662;';
      }
      this.persistGeometry();
    };

    this.element.querySelector('.kp-collapse-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      setCollapsed(!this.isCollapsed);
    });
    this.element.querySelector('.kp-reset-btn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.resetGeometry();
    });
    // Header tap toggles on coarse pointers (H007)
    this.element.querySelector('.kp-header').addEventListener('click', (e) => {
      if (e.target.closest('.kp-collapse-btn') || e.target.closest('.kp-reset-btn')) return;
      const coarse = window.matchMedia('(pointer: coarse)').matches
        || document.getElementById('app')?.classList.contains('mobile-layout');
      if (!coarse) return;
      setCollapsed(!this.isCollapsed);
    });
    this.element.querySelector('.kp-header').addEventListener('dblclick', (e) => {
      if (e.target.closest('.kp-collapse-btn') || e.target.closest('.kp-reset-btn')) return;
      setCollapsed(!this.isCollapsed);
    });

    const input = this.element.querySelector('#kp-file-input');
    this.element.querySelector('#kp-pick-btn').addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
      if (input.files.length) this.upload(input.files[0]);
      input.value = '';
    });

    const dropzone = this.element.querySelector('#kp-dropzone');
    ['dragenter', 'dragover'].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.add('kp-dragover');
      })
    );
    ['dragleave', 'drop'].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.remove('kp-dragover');
      })
    );
    dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files.length) this.upload(e.dataTransfer.files[0]);
    });

    this._urlPreview = null; // last preview payload (scope_token, linked_pages)
    this.element.querySelector('#kp-url-preview-btn')?.addEventListener('click', () => {
      this.previewUrl();
    });
    this.element.querySelector('#kp-url-ingest-btn')?.addEventListener('click', () => {
      this.ingestUrl({ includeLinked: false });
    });
    this.element.querySelector('#kp-url-crawl-btn')?.addEventListener('click', () => {
      this.crawlSiteToRag();
    });
    this.element.querySelector('#kp-url-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.previewUrl();
      }
    });
  }

  docType() {
    return this.element.querySelector('#kp-doc-type')?.value || 'other';
  }

  /** Prefer insecure TLS for LAN gear (self-signed UniFi/pfSense). */
  verifySslFlag() {
    const box = this.element.querySelector('#kp-url-insecure');
    // checked = allow insecure → verify_ssl false
    if (box) return !box.checked;
    return undefined; // let server auto-detect private IPs
  }

  async previewUrl() {
    const input = this.element.querySelector('#kp-url-input');
    const url = (input?.value || '').trim();
    const box = this.element.querySelector('#kp-url-preview');
    if (!url || !/^https?:\/\//i.test(url)) {
      if (box) {
        box.hidden = false;
        box.innerHTML = '<span class="kp-error-text">Enter a full http(s) URL.</span>';
      }
      return;
    }
    if (box) {
      box.hidden = false;
      box.innerHTML = '<span class="kp-chip-busy">Fetching preview…</span>';
    }
    try {
      const body = { url, mode: 'preview', doc_type: this.docType() };
      const vs = this.verifySslFlag();
      if (vs === false) body.verify_ssl = false;
      if (vs === true) body.verify_ssl = true;
      const res = await fetch('/api/rag/ingest-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        this._urlPreview = null;
        box.innerHTML = `<span class="kp-error-text">${this.esc(data.error || data.message || res.status)}</span>`;
        return;
      }
      this._urlPreview = { ...data, url };
      const links = data.linked_pages || [];
      const spa = Boolean(data.spa_shell);
      const thin = Boolean(data.thin);
      const textChars = data.text_chars != null ? Number(data.text_chars) : null;
      const linkList = links.length
        ? `<ul class="kp-url-links">${links
            .slice(0, 12)
            .map((p) => `<li title="${this.esc(p.url)}">${this.esc(p.title || p.url)}</li>`)
            .join('')}${links.length > 12 ? `<li>… +${links.length - 12} more</li>` : ''}</ul>`
        : '<p class="kp-drop-hint">No same-domain linked pages (or non-HTML).</p>';
      const warnText = data.warning || data.message || '';
      const warnBlock = (spa || thin || warnText)
        ? `<div class="kp-url-warn" role="status">
            <strong>${spa ? 'JS SPA shell — not crawlable docs' : 'Thin page'}</strong>
            ${textChars != null ? `<span class="kp-drop-hint"> · ~${textChars} text chars</span>` : ''}
            <p class="kp-drop-hint">${this.esc(warnText || (
              spa
                ? 'UniFi OS and similar UIs load API docs in the browser. Preview only sees static HTML (no <a href> tree). Use developer.ui.com, an OpenAPI JSON export, or upload a PDF.'
                : 'Little extractable text — ingest may produce almost no chunks.'
            ))}</p>
            ${spa ? `<p class="kp-drop-hint">Better sources:
              <code>https://developer.ui.com/network/</code> (Crawl site),
              controller <code>/proxy/network/api/openapi</code> (needs auth cookie/API key),
              or HUD <strong>Upload file</strong> of a saved OpenAPI/PDF.
            </p>` : ''}
          </div>`
        : '';
      box.innerHTML = `
        <div class="kp-url-preview-head">
          <strong>${this.esc(data.title || url)}</strong>
          <span class="kp-drop-hint">${this.esc(data.content_type || '')}</span>
          ${spa ? '<span class="kp-type kp-type-other" title="JavaScript app shell">SPA</span>' : ''}
        </div>
        <p class="kp-drop-hint">${links.length} same-domain link(s)${data.truncated ? ' (list truncated)' : ''}</p>
        ${warnBlock}
        ${linkList}
        <div class="kp-url-preview-actions">
          <button type="button" id="kp-url-ingest-one"
            title="${spa ? 'Will index almost no useful text' : 'Ingest this page only'}">
            Ingest this page only${spa ? ' (not recommended)' : ''}
          </button>
          <button type="button" id="kp-url-ingest-all" ${links.length ? '' : 'disabled'}
            title="Requires preview scope token">Ingest page + ${links.length} linked</button>
        </div>
      `;
      box.querySelector('#kp-url-ingest-one')?.addEventListener('click', () => {
        this.ingestUrl({ includeLinked: false });
      });
      box.querySelector('#kp-url-ingest-all')?.addEventListener('click', () => {
        this.ingestUrl({ includeLinked: true });
      });
    } catch (err) {
      this._urlPreview = null;
      if (box) box.innerHTML = `<span class="kp-error-text">${this.esc(err.message)}</span>`;
    }
  }

  async ingestUrl({ includeLinked = false } = {}) {
    const input = this.element.querySelector('#kp-url-input');
    const url = (input?.value || '').trim() || this._urlPreview?.url;
    if (!url || !/^https?:\/\//i.test(url)) {
      window.alert('Enter a full http(s) URL first.');
      return;
    }
    if (includeLinked && !this._urlPreview?.scope_token) {
      window.alert('Preview the URL first so linked-page scope can be confirmed.');
      return;
    }
    const label = includeLinked ? `${url} (+links)` : url;
    this.progress.set(label, { title: label, status: 'uploading', error: null });
    this.renderProgress();
    try {
      const body = {
        url,
        mode: 'ingest',
        include_linked: includeLinked,
        doc_type: this.docType(),
      };
      const vs = this.verifySslFlag();
      if (vs === false) body.verify_ssl = false;
      if (vs === true) body.verify_ssl = true;
      if (includeLinked) body.scope_token = this._urlPreview.scope_token;
      const res = await fetch('/api/rag/ingest-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok && res.status !== 202) {
        const data = await res.json().catch(() => ({}));
        this.progress.set(label, {
          title: label,
          status: 'error',
          error: data.error || data.message || `HTTP ${res.status}`,
        });
      } else {
        this.progress.set(label, { title: label, status: 'parsing', error: null });
      }
    } catch (err) {
      this.progress.set(label, { title: label, status: 'error', error: err.message });
    }
    this.renderProgress();
  }

  /**
   * Multi-page crawl (docs-site-to-pdf.py) → Markdown → rag_ingest.
   * Prefer this for large API documentation sites with no official PDF.
   */
  async crawlSiteToRag() {
    const input = this.element.querySelector('#kp-url-input');
    const url = (input?.value || '').trim();
    if (!url || !/^https?:\/\//i.test(url)) {
      window.alert('Enter a full http(s) docs site URL first.');
      return;
    }
    const maxPages = parseInt(this.element.querySelector('#kp-crawl-max')?.value, 10) || 60;
    const depth = parseInt(this.element.querySelector('#kp-crawl-depth')?.value, 10);
    const depthVal = Number.isFinite(depth) ? depth : 2;
    const ok = window.confirm(
      `Crawl site to RAG?\n\n${url}\n\nMax pages: ${maxPages}  Depth: ${depthVal}\n`
      + 'This may take several minutes for large API docs. Continue?',
    );
    if (!ok) return;

    const label = `crawl:${url}`;
    // Clear old chips so investigation snapshots don't look like crawl results
    this.progress.clear();
    this.progress.set(label, {
      title: label,
      status: 'crawling',
      error: null,
      detail: `max ${maxPages} pages · depth ${depthVal} · type ${this.docType()} — keep this panel open`,
    });
    this.renderProgress();

    try {
      const body = {
        url,
        max_pages: maxPages,
        depth: depthVal,
        doc_type: this.docType(),
        insecure: this.verifySslFlag() === false,
      };
      const res = await fetch('/api/rag/crawl-site', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok && res.status !== 202) {
        this.progress.set(label, {
          title: label,
          status: 'error',
          error: data.error || data.message || `HTTP ${res.status}`,
        });
      } else {
        this.progress.set(label, {
          title: label,
          status: 'crawling',
          error: null,
          detail: `Job accepted — crawling in background (not the Snapshots list below)`,
        });
      }
    } catch (err) {
      this.progress.set(label, { title: label, status: 'error', error: err.message });
    }
    this.renderProgress();
  }

  /** Desktop: free drag + resize; geometry persisted in localStorage. */
  setupDragResize() {
    const header = this.element.querySelector('.kp-header');
    const handle = this.element.querySelector('.kp-resize-handle');
    if (!header) return;

    const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
    const viewport = () => {
      const vv = window.visualViewport;
      return {
        w: vv?.width ?? window.innerWidth,
        h: vv?.height ?? window.innerHeight,
        ox: vv?.offsetLeft ?? 0,
        oy: vv?.offsetTop ?? 0,
      };
    };

    const applyPos = (left, top, width, height) => {
      const vp = viewport();
      const w = clamp(width ?? (this.element.offsetWidth || 520), 280, vp.w - 16);
      const h = this.isCollapsed
        ? null
        : clamp(height ?? (this.element.offsetHeight || 360), 160, vp.h - 16);
      const l = clamp(left, vp.ox, Math.max(vp.ox, vp.ox + vp.w - w));
      const t = clamp(top, vp.oy, Math.max(vp.oy, vp.oy + vp.h - (h || 48)));
      this.element.classList.add('kp-positioned');
      this.element.style.left = `${l}px`;
      this.element.style.top = `${t}px`;
      this.element.style.right = 'auto';
      this.element.style.bottom = 'auto';
      this.element.style.width = `${w}px`;
      if (h != null && !this.isCollapsed) {
        this.element.style.height = `${h}px`;
        this.element.style.maxHeight = 'none';
      }
      this._userPositioned = true;
    };

    header.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      if (e.target.closest('button') || e.target.closest('select') || e.target.closest('input')) return;
      // On mobile sheet mode, keep bottom-sheet behavior (no free drag)
      if (document.getElementById('app')?.classList.contains('mobile-layout')
        || document.getElementById('app')?.classList.contains('landscape-layout')) {
        return;
      }
      const rect = this.element.getBoundingClientRect();
      this._drag = {
        id: e.pointerId,
        offsetX: e.clientX - rect.left,
        offsetY: e.clientY - rect.top,
        moved: false,
      };
      header.setPointerCapture(e.pointerId);
      this.element.classList.add('kp-dragging');
      e.preventDefault();
    });

    header.addEventListener('pointermove', (e) => {
      if (!this._drag || this._drag.id !== e.pointerId) return;
      this._drag.moved = true;
      applyPos(
        e.clientX - this._drag.offsetX,
        e.clientY - this._drag.offsetY,
        this.element.offsetWidth,
        this.element.offsetHeight,
      );
    });

    const endDrag = (e) => {
      if (!this._drag || (e.pointerId != null && this._drag.id !== e.pointerId)) return;
      this._drag = null;
      this.element.classList.remove('kp-dragging');
      this.persistGeometry();
    };
    header.addEventListener('pointerup', endDrag);
    header.addEventListener('pointercancel', endDrag);

    if (handle) {
      handle.addEventListener('pointerdown', (e) => {
        if (e.button !== 0 || this.isCollapsed) return;
        if (document.getElementById('app')?.classList.contains('mobile-layout')) return;
        const rect = this.element.getBoundingClientRect();
        this._resize = {
          id: e.pointerId,
          startX: e.clientX,
          startY: e.clientY,
          startW: rect.width,
          startH: rect.height,
          left: rect.left,
          top: rect.top,
        };
        handle.setPointerCapture(e.pointerId);
        e.preventDefault();
        e.stopPropagation();
      });
      handle.addEventListener('pointermove', (e) => {
        if (!this._resize || this._resize.id !== e.pointerId) return;
        const w = this._resize.startW + (e.clientX - this._resize.startX);
        const h = this._resize.startH + (e.clientY - this._resize.startY);
        applyPos(this._resize.left, this._resize.top, w, h);
      });
      const endResize = (e) => {
        if (!this._resize || (e.pointerId != null && this._resize.id !== e.pointerId)) return;
        this._resize = null;
        this.persistGeometry();
      };
      handle.addEventListener('pointerup', endResize);
      handle.addEventListener('pointercancel', endResize);
    }

    window.addEventListener('resize', () => {
      if (!this._userPositioned || !this.element.classList.contains('kp-positioned')) return;
      const rect = this.element.getBoundingClientRect();
      applyPos(rect.left, rect.top, rect.width, rect.height);
    });
  }

  persistGeometry() {
    if (this.docked || !this.element) return;
    try {
      const rect = this.element.getBoundingClientRect();
      const payload = {
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
        collapsed: this.isCollapsed,
        positioned: this._userPositioned,
      };
      localStorage.setItem(GEOM_KEY, JSON.stringify(payload));
    } catch {
      /* ignore quota */
    }
  }

  restoreGeometry() {
    try {
      const raw = localStorage.getItem(GEOM_KEY);
      if (!raw) return;
      const g = JSON.parse(raw);
      if (!g || !g.positioned) return;
      this.isCollapsed = !!g.collapsed;
      this.element.classList.toggle('collapsed', this.isCollapsed);
      this.element.classList.add('kp-positioned');
      this.element.style.left = `${g.left}px`;
      this.element.style.top = `${g.top}px`;
      this.element.style.right = 'auto';
      this.element.style.bottom = 'auto';
      this.element.style.width = `${g.width || 520}px`;
      if (!this.isCollapsed && g.height) {
        this.element.style.height = `${g.height}px`;
        this.element.style.maxHeight = 'none';
      }
      this._userPositioned = true;
      const btn = this.element.querySelector('.kp-collapse-btn');
      if (btn) {
        btn.setAttribute('aria-expanded', this.isCollapsed ? 'false' : 'true');
        btn.innerHTML = this.isCollapsed ? '&#9652;' : '&#9662;';
      }
    } catch {
      /* ignore */
    }
  }

  resetGeometry() {
    try {
      localStorage.removeItem(GEOM_KEY);
    } catch {
      /* ignore */
    }
    this._userPositioned = false;
    this.element.classList.remove('kp-positioned');
    this.element.style.left = '';
    this.element.style.top = '';
    this.element.style.right = '';
    this.element.style.bottom = '';
    this.element.style.width = '';
    this.element.style.height = '';
    this.element.style.maxHeight = '';
  }

  connectSocket() {
    this.socket.addEventListener('message', this.handleSocketMessage);
  }

  handleSocketMessage(event) {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      return;
    }
    if (data.type === 'rag_progress') {
      const p = data.payload || {};
      // Ignore noise: bulk "ready" for old investigation snapshots (no detail / not a job we started)
      const title = p.title || '';
      const isCrawlOrUploadJob =
        title.startsWith('crawl:')
        || title.startsWith('hud-crawl:')
        || title.startsWith('Docs crawl:')
        || title.startsWith('Documentation crawl')
        || p.detail
        || p.pages_crawled
        || (p.status && !['ready', 'error'].includes(p.status));
      if (p.status === 'ready' && !isCrawlOrUploadJob && !p.document_id?.startsWith?.('doc_')) {
        // Still refresh tables when a real doc finishes; skip chip spam for snapshots
        if (p.document_id) this.refresh();
        return;
      }
      // Prefer stable key by title for crawl jobs (document_id may be null until end)
      const key = p.document_id || p.title || `progress-${Date.now()}`;
      this.progress.set(key, {
        title: p.title || key,
        status: p.status,
        error: p.error || null,
        detail: p.detail || null,
        chunk_count: p.chunk_count,
        pages_crawled: p.pages_crawled,
      });
      this.renderProgress();
      if (p.status === 'ready' || p.status === 'error') this.refresh();
    } else if (data.type === 'rag_update') {
      this.refresh();
    }
  }

  async refresh() {
    try {
      const [docsRes, statsRes] = await Promise.all([
        fetch('/api/rag/documents'),
        fetch('/api/rag/stats'),
      ]);
      if (docsRes.ok) {
        const data = await docsRes.json();
        this.documents = data.documents || [];
        this.snapshots = data.snapshots || [];
      }
      if (statsRes.ok) this.stats = await statsRes.json();
    } catch {
      /* server not up yet — table shows loading state */
    }
    this.renderTables();
  }

  async upload(file) {
    const maxMB = 100;
    if (file.size > maxMB * 1024 * 1024) {
      this.progress.set(file.name, {
        title: file.name,
        status: 'error',
        error: `File exceeds the ${maxMB} MB cap (raise RAG_MAX_DOC_MB to override).`,
      });
      this.renderProgress();
      return;
    }
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!SUPPORTED_EXT.includes(ext)) {
      this.progress.set(file.name, {
        title: file.name,
        status: 'error',
        error: `'${ext}' is not supported. Supported: ${SUPPORTED_EXT.join(', ')}`,
      });
      this.renderProgress();
      return;
    }

    this.progress.set(file.name, { title: file.name, status: 'uploading', error: null });
    this.renderProgress();

    const form = new FormData();
    form.append('file', file);
    form.append('doc_type', this.element.querySelector('#kp-doc-type').value);
    try {
      const res = await fetch('/api/rag/upload', { method: 'POST', body: form });
      if (!res.ok && res.status !== 202) {
        const body = await res.json().catch(() => ({}));
        this.progress.set(file.name, {
          title: file.name,
          status: 'error',
          error: body.error || `Upload failed (${res.status})`,
        });
      } else {
        this.progress.set(file.name, { title: file.name, status: 'parsing', error: null });
      }
    } catch (err) {
      this.progress.set(file.name, { title: file.name, status: 'error', error: err.message });
    }
    this.renderProgress();
  }

  async deleteDocument(id, title) {
    if (!window.confirm(`Delete "${title}" from the knowledge base?\nThis removes all its chunks from every index.`)) return;
    const res = await fetch(`/api/rag/documents/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      window.alert(`Delete failed: ${body.error || body.message || res.status}`);
    }
    this.refresh();
  }

  async reindexDocument(id, title) {
    if (!window.confirm(`Re-index "${title}" under the current chunking/embedding configuration?`)) return;
    const res = await fetch(`/api/rag/documents/${encodeURIComponent(id)}/reindex`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      window.alert(`Re-index failed: ${body.error || body.message || res.status}`);
    }
    this.refresh();
  }

  renderProgress() {
    const el = this.element.querySelector('#kp-progress');
    const items = [...this.progress.values()].slice(-5);
    el.innerHTML = items
      .map((p) => {
        const cls = p.status === 'error' ? 'kp-chip-error'
          : p.status === 'ready' ? 'kp-chip-done'
          : 'kp-chip-busy';
        const err = p.error ? `<div class="kp-error-text">${this.esc(p.error)}</div>` : '';
        const detail = p.detail ? `<div class="kp-detail-text">${this.esc(p.detail)}</div>` : '';
        const statusLabel = p.status === 'crawling' ? 'crawling…'
          : p.status === 'parsing' ? 'indexing…'
          : p.status === 'ready' ? (p.chunk_count != null ? `ready · ${p.chunk_count} chunks` : 'ready')
          : p.status;
        return `<div class="kp-chip ${cls}"><span>${this.esc(p.title || '')}</span><span class="kp-chip-status">${this.esc(statusLabel)}</span>${detail}${err}</div>`;
      })
      .join('');
  }

  renderTables() {
    const statsEl = this.element.querySelector('#kp-stats');
    if (this.stats) {
      statsEl.textContent = `${this.stats.document_count} docs · ${this.stats.total_chunks} chunks`;
    }

    const docRows = this.element.querySelector('#kp-doc-rows');
    if (!this.documents.length) {
      docRows.innerHTML = '<tr><td colspan="7" class="kp-empty">No documents indexed yet — upload one above.</td></tr>';
    } else {
      docRows.innerHTML = this.documents
        .map(
          (d) => `<tr>
            <td title="${this.esc(d.id)}">${this.esc(d.title)}</td>
            <td><span class="kp-type kp-type-${this.esc(d.doc_type)}">${this.esc(d.doc_type)}</span></td>
            <td class="kp-source">${this.esc(d.source)}</td>
            <td>${d.page_count ?? '—'}</td>
            <td>${d.chunk_count ?? 0}</td>
            <td>${this.esc((d.ingest_ts || '').slice(0, 10))}</td>
            <td class="kp-actions">
              <button data-action="reindex" data-id="${this.esc(d.id)}" data-title="${this.esc(d.title)}" title="Re-index">&#8635;</button>
              <button data-action="delete" data-id="${this.esc(d.id)}" data-title="${this.esc(d.title)}" title="Delete">&#128465;</button>
            </td>
          </tr>`
        )
        .join('');
    }

    const snapRows = this.element.querySelector('#kp-snap-rows');
    if (!this.snapshots.length) {
      snapRows.innerHTML = '<tr><td colspan="5" class="kp-empty">No snapshots</td></tr>';
    } else {
      snapRows.innerHTML = this.snapshots
        .map(
          (s) => `<tr>
            <td><span class="kp-type kp-type-snapshot">investigation</span> ${this.esc(s.title)}</td>
            <td class="kp-source">${this.esc(s.source)}</td>
            <td>${s.chunk_count ?? 0}</td>
            <td><span class="kp-age-badge ${s.stale ? 'kp-stale' : ''}" title="${this.esc(s.age_human || '')}">${this.esc(s.age_human || s.capture_ts || '')}${s.stale ? ' · STALE' : ''}</span></td>
            <td class="kp-actions">
              <button data-action="delete" data-id="${this.esc(s.id)}" data-title="${this.esc(s.title)}" title="Delete">&#128465;</button>
            </td>
          </tr>`
        )
        .join('');
    }

    this.element.querySelectorAll('.kp-actions button').forEach((btn) => {
      btn.addEventListener('click', () => {
        const { action, id, title } = btn.dataset;
        if (action === 'delete') this.deleteDocument(id, title);
        else if (action === 'reindex') this.reindexDocument(id, title);
      });
    });
  }

  esc(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
  }
}
