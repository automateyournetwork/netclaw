import React, { useEffect, useRef, useState } from 'react';

const endpoint = '/api/hud/convergence/vm-security';
const array = value => Array.isArray(value) ? value : [];
const when = seconds => typeof seconds === 'number' ? new Date(seconds * 1000).toISOString() : 'Not recorded';
const unknown = value => value === null || value === undefined ? 'unknown' : String(value);
const patterns = {
  port_scan: 'Possible port scanning',
  network_sweep: 'Possible network sweep',
  protected_network_contact: 'Protected network contact',
};
// The service's assessment words, never upgraded to "safe" or "compromised".
const assessments = {
  review: 'Possible patterns to review.',
  no_patterns_observed: 'No patterns in the sampled, covered traffic. This is not an all-clear.',
  insufficient_evidence: 'Insufficient evidence: current activity is unknown.',
};
const sourceKinds = { proxmox: 'Proxmox VE observer', synthetic: 'Synthetic demonstration' };

function Source({ source }) {
  const c = source.coverage || {}, s = source.summary || {};
  return <section className="convergence-vm-source" aria-label={`VM Security source ${source.node}`}>
    <h4>{source.node} <small>({sourceKinds[source.kind] || source.kind})</small></h4>
    <dl className="facts">
      <div><dt>Status</dt><dd>{source.status}</dd></div>
      <div><dt>Last contact</dt><dd>{when(source.last_contact)}</dd></div>
      <div><dt>Observed at</dt><dd>{when(source.observed_at)}</dd></div>
      <div><dt>Assessment</dt><dd>{assessments[s.assessment] || s.assessment}</dd></div>
    </dl>
    <ul className="convergence-vm-coverage">
      <li>Packet metadata is sampled; counts describe the retained sample, not all traffic.</li>
      <li>Capture drops in the last interval: {unknown(c.capture_drops_recent_delta)}; events discarded: {unknown(c.events_discarded_recent_delta)}.</li>
      <li>Largest gap between snapshots: {c.max_snapshot_gap_seconds === null || c.max_snapshot_gap_seconds === undefined ? 'unknown' : `${c.max_snapshot_gap_seconds} s`}; VMs without a UUID (not analysed): {unknown(c.missing_uuid_vm_count)}.</li>
      {s.findings_truncated && <li>Only the first {array(source.findings).length} of {s.finding_count} findings are listed.</li>}
      {array(c.limitations).map((line, i) => <li key={i}>{line}</li>)}
    </ul>
    {array(source.findings).length > 0 && <div className="table-scroll"><table><thead><tr><th>Pattern</th><th>VM</th><th>First / last seen</th><th>Evidence</th><th>Caveat</th></tr></thead><tbody>
      {source.findings.map(f => <tr key={f.id}>
        <td>{patterns[f.kind] || f.kind}</td>
        <td>{f.vm_id}</td>
        <td>{when(f.first_seen)} → {when(f.last_seen)}</td>
        <td>{f.evidence.unique_destination_ports} ports, {f.evidence.unique_destination_ips} addresses, {f.evidence.unique_tcp_five_tuples} TCP five-tuples
          {f.evidence.destination_ip ? `; to ${f.evidence.destination_ip}` : ''}{f.evidence.destination_port !== null ? ` port ${f.evidence.destination_port}` : ''}
          <ul>{array(f.evidence.examples).map((e, i) => <li key={i}>{e.protocol} {e.src_ip}:{e.src_port ?? '—'} → {e.dst_ip}:{e.dst_port ?? '—'} at {when(e.observed_at)}</li>)}</ul></td>
        <td>{f.caveat}</td>
      </tr>)}</tbody></table></div>}
    <div className="table-scroll"><table><thead><tr><th>VM</th><th>Power</th><th>Capture</th><th>Findings</th></tr></thead><tbody>
      {array(source.vms).map(vm => <tr key={vm.vm_id}><td>{vm.vm_id}</td><td>{vm.power_state}</td><td>{vm.capture_state}</td><td>{vm.finding_count}</td></tr>)}
    </tbody></table></div>
    <p>Unobserved, stopped or partially captured VMs are coverage gaps, not clean results.</p>
  </section>;
}

export default function ConvergenceVmSecurity({ ready, installationId, request, errorMessages }) {
  const [state, setState] = useState({ open: false });
  const sequence = useRef(0), controller = useRef(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { controller.current?.abort(); sequence.current++; setState({ open: false }); }, [installationId]);
  async function load() {
    controller.current?.abort();
    const current = new AbortController(), token = ++sequence.current;
    controller.current = current;
    setState(old => ({ ...old, open: true, loading: true, error: null }));
    try {
      const value = await request(endpoint, current.signal);
      if (token === sequence.current && !current.signal.aborted) setState({ open: true, data: value.data, readAt: new Date().toISOString() });
    } catch (error) {
      // A failed refresh keeps earlier data, marked stale; it never becomes "no findings".
      if (token === sequence.current && !current.signal.aborted) setState(old => ({ ...old, loading: false, stale: !!old.data, error: error.message || errorMessages.unavailable }));
    }
  }
  const data = state.data;
  return <section className="convergence-vm-security" aria-label="Convergence VM Security">
    <div className="section-heading"><h3>VM Security</h3><button onClick={load} disabled={!ready || state.loading}>{state.open ? 'Refresh VM Security' : 'Show VM Security'}</button></div>
    <p>Advisory patterns from hypervisor-side observation over the last five minutes. Findings are for review; they are not proof of attack or compromise.</p>
    {state.loading && <p role="status">Reading VM Security…</p>}
    {state.error && <p role="alert">{state.stale ? 'Stale cached data — refresh failed. ' : ''}{state.error}</p>}
    {data && <>
      {data.synthetic && <p className="convergence-synthetic" role="note"><strong>Synthetic demonstration.</strong> No real virtual machine traffic was observed.</p>}
      <p>Site {data.site}; read at {state.readAt}; window {data.window_seconds ? `${data.window_seconds / 60} minutes` : 'not recorded'}.</p>
      {data.status === 'not_configured' ? <p role="status">No VM Security source is configured for this site.</p>
        : array(data.sources).map(source => <Source key={source.id} source={source}/>)}
    </>}
  </section>;
}
