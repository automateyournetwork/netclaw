import { runtimeInfo } from '../shared/runtime-client.js';
import React, { useEffect, useRef, useState } from 'react';
import { list, text } from './model.js';

async function request(url, options = {}) {
  const response = await fetch(url, { cache: 'no-store', ...options, signal: options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(150000)]) : AbortSignal.timeout(150000) });
  if (!response.ok) throw new Error(response.status === 413 ? 'File exceeds the configured upload size limit.' : response.status === 415 ? 'Unsupported file type.' : 'The local service could not complete this request. Check its configuration and try again.');
  return response.json();
}
const demoDocs = { documents: [{ id: 'synthetic-runbook', title: 'Branch routing runbook', collection: 'documents', ingest_status: 'ready', chunk_count: 24, source: 'Synthetic example', ingest_ts: '2026-09-28T12:00:00Z' }], snapshots: [], replicas: [] };
const demoStats = { document_count: 1, total_chunks: 24, collections: ['documents'], embedding_model: 'Synthetic preview' };
const demoConfig = { environmentFile: '~/.openclaw/.env (synthetic example)', integrations: [{ id: 'jev', notes: 'Synthetic configuration presence; no credentials loaded.', files: ['config/openclaw.json'], fields: [{ key: 'JEV_ENABLED', isSet: true }, { key: 'TYPESAFE_API_KEY', isSet: false }] }] };

export function RagView({ preview, investigate }) {
  const [docs, setDocs] = useState(null), [stats, setStats] = useState(null), [error, setError] = useState(''), [status, setStatus] = useState('');
  const [refresh, setRefresh] = useState(0), [uploading, setUploading] = useState(false), [searching, setSearching] = useState(false);
  const [collection, setCollection] = useState('documents'), [query, setQuery] = useState(''), [results, setResults] = useState(null);
  const form = useRef(null), mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (preview) { setDocs(demoDocs); setStats(demoStats); return; }
    const controller = new AbortController(); let timer;
    const read = async () => {
      try {
        const [documents, totals] = await Promise.all([request('/api/rag/documents', { signal: controller.signal }), request('/api/rag/stats', { signal: controller.signal })]);
        if (!controller.signal.aborted) { setDocs(documents); setStats(totals); setError(''); }
      } catch (e) { if (!controller.signal.aborted) setError(e.message); }
      if (!controller.signal.aborted) timer = setTimeout(read, 10000);
    };
    read(); return () => { controller.abort(); clearTimeout(timer); };
  }, [preview, refresh]);
  const upload = async event => {
    event.preventDefault(); if (preview || uploading) return;
    setUploading(true); setStatus('Uploading…');
    try { await request('/api/rag/upload', { method: 'POST', body: new FormData(form.current) }); if (mounted.current) { setStatus('Upload accepted. Ingestion is pending; check the document status below.'); form.current.reset(); setRefresh(n => n + 1); } }
    catch (e) { if (mounted.current) setStatus(e.message); }
    finally { if (mounted.current) setUploading(false); }
  };
  const search = async event => {
    event.preventDefault(); if (searching) return;
    setSearching(true); setResults(null); setStatus('Retrieving cited evidence…');
    try {
      const result = preview ? { results: [{ title: 'Branch routing runbook', chunk_text: 'Synthetic example: verify interface counters before changing routing policy.', citation: '[Synthetic runbook §2]', score: 0.82, low_confidence: false }], collection, corpus_empty: false } : await request('/api/rag/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, collection, k: 5 }) });
      if (mounted.current) { setResults({ ...result, query, retrievedAt: new Date().toISOString() }); setStatus('Retrieval complete. Review source excerpts before drawing conclusions.'); }
    } catch (e) { if (mounted.current) setStatus(e.message); }
    finally { if (mounted.current) setSearching(false); }
  };
  const collections = [...new Set(['documents', ...list(stats?.collections), ...list(docs?.snapshots).map(d => d.collection), ...list(docs?.replicas).map(d => d.collection)])].filter(Boolean);
  return <div className="workspace-tools">
    <section className="panel"><span className="eyebrow">Local knowledge base</span><h2>RAG · documents & retrieval</h2><p>Upload source material, inspect ingestion, and retrieve evidence with citations. Peer replicas and captured snapshots retain their provenance.</p>
      {error && <p role="alert">{error} Previously loaded records may be stale.</p>}
      <p>{stats ? `${stats.document_count ?? 'Unknown'} ready documents · ${stats.total_chunks ?? 'Unknown'} chunks · ${text(stats.embedding_model)}` : 'Reading the local RAG service…'}</p><button onClick={() => setRefresh(n => n + 1)} disabled={preview}>Refresh collections</button>
    </section>
    <div className="guide-grid"><section className="panel"><h2>Upload a document</h2><p>PDF, text, Markdown, HTML and Office documents. Upload acceptance precedes indexing; only ready documents can be retrieved.</p>
      <form ref={form} onSubmit={upload} className="tool-form"><label>Document<input type="file" name="file" required disabled={preview || uploading} accept=".pdf,.md,.markdown,.html,.htm,.txt,.docx,.xlsx,.pptx,.vsdx,.doc,.xls,.ppt,.vsd"/></label><label>Title (optional)<input name="title" maxLength={200} disabled={preview || uploading}/></label><label>Document type<select name="doc_type" disabled={preview || uploading}>{['other','vendor','standard','customer','install-guide'].map(t => <option key={t}>{t}</option>)}</select></label><button className="primary" disabled={preview || uploading}>{uploading ? 'Uploading…' : 'Upload & index'}</button></form>{preview && <p className="muted">Uploads are available in the running application. This preview does not accept files.</p>}
    </section><section className="panel"><h2>Search the knowledge base</h2><form onSubmit={search} className="tool-form"><label>Collection<select value={collection} onChange={e => setCollection(e.target.value)}>{collections.map(c => <option key={c}>{c}</option>)}</select></label><label>Question or search terms<textarea value={query} onChange={e => setQuery(e.target.value)} required maxLength={4000} rows={4}/></label><button className="primary" disabled={searching || !query.trim()}>{searching ? 'Searching…' : preview ? 'Show synthetic retrieval' : 'Retrieve evidence'}</button></form><p className="muted">Retrieval returns source excerpts. Continue in Canvas for an investigation with Border.</p></section></div>
    {status && <p role="status" className="notice">{status}</p>}
    {results && <section className="panel"><h2>Retrieved evidence</h2><p>Collection: {text(results.collection)} · retrieved {results.retrievedAt}</p>{!list(results.results).length && <p>{results.corpus_empty ? 'This collection is empty.' : 'No matching excerpts returned.'}</p>}{list(results.results).map((r,i) => <article className="question" key={r.chunk_id || i}><h3>{text(r.title)}</h3><p>{text(r.chunk_text)}</p><p><strong>{text(r.citation, 'Citation unavailable')}</strong></p><p className="muted">Relevance score: {text(r.score)}{r.low_confidence ? ' · LOW CONFIDENCE' : ''}{r.age_human ? ` · ${r.age_human}` : ''}{r.source_peer_identity ? ` · Peer: ${r.source_peer_identity}` : ''}</p><button onClick={() => investigate('RAG evidence', { question: results.query, collection: results.collection, excerpt: r }, '/api/rag/search', results.retrievedAt)}>Use evidence in Canvas ↗</button></article>)}</section>}
    <section className="panel"><h2>Collections & ingestion</h2>{!docs && <p>Document inventory unavailable until the service responds.</p>}{docs && ['documents','snapshots','replicas'].map(kind => <div key={kind}><h3>{kind === 'replicas' ? 'Peer replicas' : kind === 'snapshots' ? 'Captured snapshots' : 'Local documents'}</h3><div className="table-scroll"><table><thead><tr><th>Document</th><th>Collection / source</th><th>Ingestion</th><th>Chunks</th></tr></thead><tbody>{list(docs[kind]).map(d => <tr key={d.id}><td>{text(d.title)}<small>{text(d.ingest_ts)}{d.age_human && ` · ${d.age_human}`}</small></td><td>{text(d.collection)}<small>{text(d.source_peer_identity || d.source)}{d.replicated_at && ` · replicated ${d.replicated_at}`}</small></td><td>{text(d.ingest_status)}{d.error && <small>{typeof d.error === 'string' ? d.error : 'Ingestion failed'}</small>}</td><td>{text(d.chunk_count)}</td></tr>)}</tbody></table>{!list(docs[kind]).length && <p>No {kind} reported.</p>}</div></div>)}</section>
  </div>;
}

export function ConfigurationView({ preview }) {
  const [config, setConfig] = useState(null), [error, setError] = useState(''), [query, setQuery] = useState(''), [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (preview) { setConfig(demoConfig); return; }
    const controller = new AbortController();
    request('/api/hud/configuration', { signal: controller.signal }).then(data => { setConfig(data); setError(''); }).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [preview, refresh]);
  const q = query.toLowerCase();
  return <section className="panel workspace-tools"><span className="eyebrow">Installation configuration</span><h2>Configuration items</h2><p>Environment source: <code>{config?.environmentFile || 'Reading…'}</code>. Values stay masked. Presence means a value is stored, not that a connection works.</p><p>Read-only inventory. Edit the local configuration file to change values, then refresh. Runtime environment overrides may differ from the file.</p><p>Core configuration: <code>{runtimeInfo()?.kind === 'hermes' ? 'Selected Hermes config.yaml' : 'Selected OpenClaw openclaw.json'}</code> · repository defaults: <code>config/openclaw.json</code> · device inventory: <code>testbed/testbed.yaml</code></p>
    <div className="tool-form"><label>Filter configuration<input value={query} onChange={e => setQuery(e.target.value)} placeholder="Integration, variable or file…"/></label><button onClick={() => setRefresh(n => n + 1)} disabled={preview}>Refresh configuration</button></div>{error && <p role="alert">{error} Previous configuration may be stale.</p>}
    {list(config?.integrations).filter(i => `${i.id} ${list(i.fields).map(f => f.key).join(' ')} ${list(i.files).join(' ')}`.toLowerCase().includes(q)).map(i => <details key={i.id} className="config-item"><summary>{i.id} · {list(i.fields).filter(f => f.isSet).length}/{list(i.fields).length} variables set</summary><p>{i.notes}</p><div className="table-scroll"><table><thead><tr><th>Variable</th><th>State</th><th>Value</th></tr></thead><tbody>{list(i.fields).map(f => <tr key={f.key}><td><code>{f.key}</code></td><td>{f.isSet ? 'Set' : 'Not set'}</td><td>{f.isSet ? '••••••••' : '—'}</td></tr>)}</tbody></table></div><h3>Related files</h3>{list(i.files).length ? <ul>{i.files.map(f => <li key={f}><code>{f}</code></li>)}</ul> : <p>No additional files listed.</p>}</details>)}
  </section>;
}
