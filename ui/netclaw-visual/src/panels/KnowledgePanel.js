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

const SUPPORTED_EXT = ['.pdf', '.md', '.markdown', '.html', '.htm', '.txt',
  '.docx', '.xlsx', '.pptx', '.vsdx', '.doc', '.xls', '.ppt', '.vsd'];
const DOC_TYPES = ['other', 'vendor', 'standard', 'customer', 'install-guide'];

export class KnowledgePanel {
  constructor(socket = null) {
    this.socket = socket;
    this.documents = [];
    this.snapshots = [];
    this.progress = new Map(); // document_id/title -> {status, error}
    this.stats = null;
    this.element = null;
    this.isCollapsed = true;

    this.handleSocketMessage = this.handleSocketMessage.bind(this);
  }

  render() {
    this.element = document.createElement('div');
    this.element.id = 'knowledge-panel';
    this.element.className = 'knowledge-panel collapsed';
    this.element.innerHTML = this.getTemplate();
    this.setupEventListeners();
    if (this.socket) this.connectSocket();
    this.refresh();
    return this.element;
  }

  getTemplate() {
    return `
      <div class="kp-header">
        <div class="kp-title">
          <span class="kp-icon">&#128218;</span>
          <span>Knowledge</span>
          <span class="kp-stats" id="kp-stats"></span>
        </div>
        <button class="kp-collapse-btn" title="Expand/collapse">&#9662;</button>
      </div>
      <div class="kp-body">
        <div class="kp-upload" id="kp-dropzone">
          <input type="file" id="kp-file-input" accept="${SUPPORTED_EXT.join(',')}" hidden />
          <select id="kp-doc-type" title="Document type">
            ${DOC_TYPES.map((t) => `<option value="${t}">${t}</option>`).join('')}
          </select>
          <button id="kp-pick-btn">Upload document</button>
          <span class="kp-drop-hint">or drag a file here</span>
        </div>
        <div class="kp-progress" id="kp-progress"></div>
        <div class="kp-section-title">Documents</div>
        <div class="kp-table-wrap">
          <table class="kp-table">
            <thead><tr>
              <th>Title</th><th>Type</th><th>Source</th><th>Pages</th>
              <th>Chunks</th><th>Ingested</th><th></th>
            </tr></thead>
            <tbody id="kp-doc-rows"><tr><td colspan="7" class="kp-empty">Loading…</td></tr></tbody>
          </table>
        </div>
        <div class="kp-section-title kp-snap-title">Snapshots <span class="kp-snap-note">point-in-time live data — age always shown</span></div>
        <div class="kp-table-wrap kp-snapshots">
          <table class="kp-table">
            <thead><tr>
              <th>Label</th><th>Source</th><th>Chunks</th><th>Captured</th><th></th>
            </tr></thead>
            <tbody id="kp-snap-rows"><tr><td colspan="5" class="kp-empty">No snapshots</td></tr></tbody>
          </table>
        </div>
      </div>
    `;
  }

  setupEventListeners() {
    this.element.querySelector('.kp-collapse-btn').addEventListener('click', () => {
      this.isCollapsed = !this.isCollapsed;
      this.element.classList.toggle('collapsed', this.isCollapsed);
    });
    this.element.querySelector('.kp-header').addEventListener('dblclick', () => {
      this.isCollapsed = !this.isCollapsed;
      this.element.classList.toggle('collapsed', this.isCollapsed);
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
      this.progress.set(p.document_id || p.title, p);
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
        const cls = p.status === 'error' ? 'kp-chip-error' : p.status === 'ready' ? 'kp-chip-done' : 'kp-chip-busy';
        const err = p.error ? `<div class="kp-error-text">${this.esc(p.error)}</div>` : '';
        return `<div class="kp-chip ${cls}"><span>${this.esc(p.title || '')}</span><span class="kp-chip-status">${this.esc(p.status)}</span>${err}</div>`;
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
            <td>${this.esc(s.title)}</td>
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
