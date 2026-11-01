import React, { useEffect, useRef, useState } from 'react';
import { convergenceContext } from './convergence-context.js';

const endpoint = '/api/hud/convergence/flows';
const array = value => Array.isArray(value) ? value : [];
const shown = value => value === null || value === undefined ? 'Not recorded' : String(value);
const errorMessages = {
  disabled: 'Convergence is disabled. Reload after enabling the integration.',
  not_configured: 'Convergence has no configured source. Follow the connection guide.',
  unauthorized: 'Access denied. Check the owned HUD session and the service viewer credential.',
  invalid_argument: 'The requested window, address or exporter is invalid.',
  compatibility: 'The service response is incompatible with this connector.',
  timeout: 'The source did not respond before the deadline.',
  unavailable: 'The source could not be read. Its traffic totals are unknown.',
};
function Coverage({ value }) {
  return <div className="convergence-coverage"><strong>{shown(value?.label || value?.mode)}</strong><p>{shown(value?.description)}</p>{value?.detail && <p>{value.detail}</p>}</div>;
}
function Limits({ values }) { return <ul>{array(values).map((value, i) => <li key={i}>{value}</li>)}</ul>; }
export default function Convergence({ enabled = false, installationId, investigate }) {
  const [ready, setReady] = useState(false), [range, setRange] = useState('1h'), [exporter, setExporter] = useState('');
  const [summary, setSummary] = useState({}), [detail, setDetail] = useState({}), [refresh, setRefresh] = useState(0);
  const sequence = useRef(0), detailSequence = useRef(0), detailController = useRef(null);
  const headers = installationId ? { 'X-NetClaw-Installation': installationId } : {};
  async function request(url, signal, method = 'GET') {
    const response = await fetch(url, { method, signal, cache: 'no-store', credentials: 'same-origin', headers });
    const value = await response.json();
    if (!response.ok || value.ok === false) throw Error(errorMessages[value.error?.code] || errorMessages.unavailable);
    return value;
  }
  useEffect(() => {
    setReady(false); setSummary({}); setDetail({});
    if (!enabled) return;
    const controller = new AbortController();
    request('/api/hud/session', controller.signal, 'POST').then(() => { if (!controller.signal.aborted) setReady(true); }).catch(() => {
      if (!controller.signal.aborted) setSummary({ error: errorMessages.unauthorized });
    });
    return () => controller.abort();
  }, [enabled, installationId]);
  useEffect(() => {
    if (!enabled || !ready) return;
    const token = ++sequence.current, controller = new AbortController();
    const query = { range, ...(exporter ? { exporter } : {}) };
    detailSequence.current++; detailController.current?.abort(); setDetail({});
    setSummary(old => ({ ...old, loading: true, error: null }));
    request(endpoint + '?' + new URLSearchParams(query), controller.signal).then(result => {
      if (sequence.current === token && !controller.signal.aborted) setSummary({ data: result.data, query, installationId, refresh, loading: false, stale: false });
    }).catch(error => {
      if (sequence.current === token && !controller.signal.aborted) setSummary(old => ({ ...old, loading: false, stale: !!old.data, error: error.message }));
    });
    return () => { controller.abort(); detailController.current?.abort(); detailSequence.current++; };
  }, [enabled, ready, range, exporter, refresh, installationId]);
  useEffect(() => () => detailController.current?.abort(), []);
  async function inspect(address, ranking) {
    const source = summary.data;
    if (!source?.start || !source?.end || !canInspect) return;
    detailController.current?.abort();
    const controller = new AbortController(), token = ++detailSequence.current;
    detailController.current = controller;
    const query = { address, start: source.start, end: source.end, ...(summary.query?.exporter ? { exporter: summary.query.exporter } : {}) };
    setDetail({ address, loading: true });
    try {
      const value = await request(endpoint + '/records?' + new URLSearchParams(query), controller.signal);
      if (token === detailSequence.current && !controller.signal.aborted) setDetail({ address, data: value.data, sourceSummary: source, selection: { address, ranking }, readAt: new Date().toISOString() });
    } catch (error) {
      if (token === detailSequence.current && !controller.signal.aborted) setDetail({ address, error: error.message });
    }
  }
  if (!enabled) return <p>Convergence is disabled.</p>;
  const data = summary.data;
  const changingQuery = data && (summary.query?.range !== range || (summary.query?.exporter || '') !== exporter);
  const canInspect = ready && !summary.loading && !summary.stale && !summary.error && !changingQuery && summary.installationId === installationId && summary.refresh === refresh;
  const context = canInspect && !detail.loading && !detail.error && detail.sourceSummary === data
    ? convergenceContext({ summary: data, evidence: detail.data, selection: detail.selection, evidenceReadAt: detail.readAt }) : null;
  return <section className="panel convergence-view" aria-label="Convergence retained flow evidence">
    <div className="section-heading"><div><span className="eyebrow">Read-only retained observations</span><h2>Convergence</h2></div><button onClick={() => setRefresh(x => x + 1)} disabled={!ready || summary.loading}>Refresh flows</button></div>
    <p>Inspect exported traffic and supporting records. These observations do not establish an application, threat verdict or whole-network coverage.</p>
    <div className="convergence-filters"><label>Window <select aria-label="Flow window" value={range} onChange={event => setRange(event.target.value)}>{['15m', '1h', '6h', '24h'].map(value => <option key={value}>{value}</option>)}</select></label><label>Exporter <select aria-label="Flow exporter" value={exporter} onChange={event => setExporter(event.target.value)}><option value="">All configured exporters</option>{array(data?.exporters).map(value => <option key={value}>{value}</option>)}</select></label></div>
    {summary.loading && <p role="status">Reading flows…{data ? ' The previous result remains visible while refreshing.' : ''}</p>}
    {summary.error && <p role="alert">{summary.stale ? 'Stale cached data — refresh failed. ' : ''}{summary.error}</p>}
    {data && <>
      <Coverage value={data.coverage}/>
      <dl className="facts"><div><dt>Site</dt><dd>{data.site}</dd></div><div><dt>Selected exporter</dt><dd>{summary.query?.exporter || 'All configured exporters'}</dd></div><div><dt>Source</dt><dd>Convergence retained flow archive</dd></div><div><dt>Observation window</dt><dd>{shown(data.start)} → {shown(data.end)}</dd></div><div><dt>Read at</dt><dd>{shown(data.read_at)}</dd></div><div><dt>Latest receipt</dt><dd>{shown(data.total?.last_received)}</dd></div><div><dt>Observed bytes / packets</dt><dd>{shown(data.total?.bytes)} / {shown(data.total?.packets)}</dd></div></dl>
      <p>Receipt time describes retained traffic age. Quiet traffic alone does not establish collector failure.</p>
      {data.status === 'not_configured' ? <p role="status">No flow source is configured for this site.</p> : data.status === 'empty' ? <p role="status">No retained records match this window. This is an empty result, not a backend failure.</p> : <div className="convergence-rankings">{[['Sources', 'sources', 'src_addr'], ['Destinations', 'destinations', 'dst_addr']].map(([title, key, field]) => <section key={key}><h3>{title}</h3><div className="table-scroll"><table><thead><tr><th>Address</th><th>Exported bytes</th><th>Packets</th><th>Evidence</th></tr></thead><tbody>{array(data[key]).map(row => <tr key={row[field]}><td>{row[field]}</td><td>{shown(row.bytes)}</td><td>{shown(row.packets)}</td><td><button disabled={!canInspect} onClick={() => inspect(row[field], key)} aria-label={`Inspect ${title.toLowerCase()} ${row[field]}`}>Inspect records</button></td></tr>)}</tbody></table></div></section>)}</div>}
      <p>{data.basis}</p><Limits values={data.limitations}/>
      {array(data.sampling).length > 0 && <p>Reported sampling: {data.sampling.map(s => `${shown(s.rate)} (${shown(s.records)} records)`).join('; ')}. Counts are not extrapolated.</p>}
    </>}
    {detail.address && <section className="convergence-evidence" aria-label="Selected flow records"><h3>Records involving {detail.address}</h3>{detail.loading && <p role="status">Reading same-window records…</p>}{detail.error && <p role="alert">{detail.error}</p>}{detail.data && <>
      {investigate && <><button className="primary" disabled={!context} onClick={() => { if (context) investigate(`Convergence ${detail.address}`, context, 'Convergence retained flow archive', detail.readAt); }}>Investigate in Canvas</button><p>Pass this evidence to NetClaw for a scoped investigation. Review the Canvas draft before sending.</p>{!context && <p role="status">Refresh and select current matching evidence before investigating.</p>}</>}
      <Coverage value={detail.data.coverage}/><p>Window: {detail.data.start} → {detail.data.end}</p>
      <p>Latest {detail.data.limit} records involving this address as source OR destination. This bounded, mixed-direction subset does not reconstruct a directional ranking total.</p>
      <div className="table-scroll"><table><thead><tr><th>Direction</th><th>Source</th><th>Destination</th><th>Exporter</th><th>Received</th><th>Bytes</th><th>Packets</th></tr></thead><tbody>{array(detail.data.records).map((record, i) => <tr key={i}><td>{record.src_addr === detail.address ? record.dst_addr === detail.address ? 'Both endpoints' : 'From selected address' : 'To selected address'}</td><td>{record.src_addr}:{record.src_port ?? '—'}</td><td>{record.dst_addr}:{record.dst_port ?? '—'}</td><td>{record.sampler_address}</td><td>{record._time}</td><td>{shown(record.bytes)}</td><td>{shown(record.packets)}</td></tr>)}</tbody></table></div>
      {!detail.data.records.length && <p>No matching retained records were returned.</p>}<p>{detail.data.basis}</p>
    </>}</section>}
  </section>;
}
