import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
const directory = new URL('.', import.meta.url).pathname;
const output = await build({ stdin: { contents: `import React from 'react';import {createRoot} from 'react-dom/client';import Convergence from './Convergence.jsx';const root=createRoot(document.getElementById('root'));window.show=props=>root.render(<Convergence {...props}/>);window.remove=()=>root.unmount();`, loader: 'jsx', resolveDir: directory }, bundle: true, write: false, format: 'iife', define: { 'process.env.NODE_ENV': '"production"' } });
async function until(predicate) {
  const deadline = Date.now() + 3000;
  while (!predicate()) { if (Date.now() > deadline) assert.fail('UI condition did not become ready'); await new Promise(resolve => setTimeout(resolve, 5)); }
}
const fixture = () => ({
  status: 'active', site: 'synthetic-lab', coverage: { mode: 'demo', label: 'Synthetic demonstration', description: 'Example traffic, not your network.', detail: '<img src=x onerror=alert(1)>' },
  range: '1h', start: '2026-10-30T23:00:00.000Z', end: '2026-10-31T00:00:00.000Z', read_at: '2026-10-31T00:00:01Z', exporter: null, exporters: ['127.0.0.1'],
  total: { bytes: 100000, packets: 1000, records: 200, last_received: '2020-01-01T00:00:00Z' },
  sources: [{ src_addr: '192.0.2.10', bytes: 50000, packets: 500, records: 100 }], destinations: [{ dst_addr: '198.51.100.20', bytes: 50000, packets: 500, records: 100 }],
  basis: 'Exported counters, not billing.', limitations: ['Sampling is not extrapolated.'], sampling: [],
});
const evidence = address => ({ site: 'synthetic-lab', coverage: fixture().coverage, address, start: fixture().start, end: fixture().end, limit: 100, records: [
  { src_addr: address, dst_addr: '203.0.113.5', sampler_address: '127.0.0.1', _time: fixture().end, bytes: 100, packets: 1 },
  { src_addr: '203.0.113.5', dst_addr: address, sampler_address: '127.0.0.1', _time: fixture().end, bytes: 200, packets: 2 },
], basis: 'Latest records involving selected address.' });
async function setup(t, handler, props = { enabled: true, installationId: 'fixture-installation' }) {
  const dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost:3000', runScripts: 'outside-only', pretendToBeVisual: true });
  t.after(() => { dom.window.remove?.(); dom.window.close(); });
  const calls = [], w = dom.window;
  w.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    const result = url === '/api/hud/session' ? { authenticated: true } : await handler(url, options);
    return { ok: result.ok !== false, json: async () => result };
  };
  w.eval(output.outputFiles[0].text); w.show(props);
  return { w, calls, body: () => w.document.body.textContent, buttons: () => [...w.document.querySelectorAll('button')] };
}

test('disabled view performs no session, MCP or external requests', async t => {
  const f = await setup(t, () => assert.fail('must not read'), { enabled: false });
  await until(() => f.body().includes('disabled')); assert.equal(f.calls.length, 0);
});

test('same-window exporter evidence is escaped and labeled as mixed-direction bounded context', async t => {
  const f = await setup(t, url => {
    const query = new URL(url, 'http://local').searchParams;
    return { ok: true, data: url.includes('/records?') ? evidence(query.get('address')) : fixture() };
  });
  await until(() => f.buttons().some(b => b.textContent === 'Inspect records'));
  assert.match(f.body(), /Synthetic demonstration/); assert.equal(f.w.document.querySelectorAll('img').length, 0);
  assert.match(f.body(), /<img src=x onerror=alert\(1\)>/);
  assert.doesNotMatch(f.body(), /Stale cached data/); // An old receipt is not a failed refresh.
  const selector = f.w.document.querySelector('[aria-label="Flow exporter"]'); selector.value = '127.0.0.1'; selector.dispatchEvent(new f.w.Event('change', { bubbles: true }));
  await until(() => f.calls.some(c => c.url.includes('exporter=127.0.0.1')) && f.w.document.querySelector('.facts').textContent.includes('Selected exporter127.0.0.1') && !f.body().includes('Reading flows'));
  f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect destinations 198.51.100.20').click();
  await until(() => f.body().includes('From selected address'));
  assert.match(f.body(), /To selected address/); assert.match(f.body(), /does not reconstruct a directional ranking total/);
  const call = f.calls.find(c => c.url.includes('/records?')), query = new URL(call.url, 'http://local').searchParams;
  assert.equal(query.get('start'), fixture().start); assert.equal(query.get('end'), fixture().end); assert.equal(query.get('exporter'), '127.0.0.1');
  assert.equal(call.options.headers['X-NetClaw-Installation'], 'fixture-installation');
  assert.equal(f.w.document.querySelector('[aria-label="Selected flow records"]').textContent.includes('50000'), false);
});

test('failed refresh retains explicitly stale data while valid empty and unconfigured responses remain distinct', async t => {
  let result = { ok: true, data: fixture() };
  const f = await setup(t, () => result);
  await until(() => f.body().includes('100000'));
  result = { ok: false, error: { code: 'unavailable', message: 'private-token' } };
  f.buttons().find(b => b.textContent === 'Refresh flows').click();
  await until(() => f.body().includes('Stale cached data'));
  assert.match(f.body(), /100000/); assert.doesNotMatch(f.body(), /private-token/);
  result = { ok: true, data: { ...fixture(), status: 'empty', total: { bytes: null, packets: null }, sources: [], destinations: [] } };
  f.buttons().find(b => b.textContent === 'Refresh flows').click();
  await until(() => f.body().includes('No retained records match'));
  assert.doesNotMatch(f.body(), /Stale cached data|100000/);
  result = { ok: true, data: { status: 'not_configured', site: 'synthetic-lab', coverage: fixture().coverage, exporters: [] } };
  f.buttons().find(b => b.textContent === 'Refresh flows').click();
  await until(() => f.body().includes('No flow source is configured'));
  assert.doesNotMatch(f.body(), /No retained records match/);
});

test('late evidence from a previous selection cannot replace the current address', async t => {
  const pending = new Map();
  const f = await setup(t, url => {
    if (!url.includes('/records?')) return { ok: true, data: fixture() };
    const address = new URL(url, 'http://local').searchParams.get('address');
    return new Promise(resolve => pending.set(address, resolve));
  });
  await until(() => f.buttons().some(b => b.textContent === 'Inspect records'));
  f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect sources 192.0.2.10').click();
  await until(() => pending.has('192.0.2.10'));
  f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect destinations 198.51.100.20').click();
  await until(() => pending.has('198.51.100.20'));
  pending.get('198.51.100.20')({ ok: true, data: evidence('198.51.100.20') });
  await until(() => f.body().includes('From selected address'));
  pending.get('192.0.2.10')({ ok: true, data: evidence('192.0.2.10') });
  await new Promise(resolve => setTimeout(resolve, 15));
  assert.match(f.w.document.querySelector('[aria-label="Selected flow records"]').textContent, /Records involving 198\.51\.100\.20/);
  assert.doesNotMatch(f.w.document.querySelector('[aria-label="Selected flow records"]').textContent, /192\.0\.2\.10/);
});

test('Investigate forwards current evidence only on explicit click and blocks failed or changing scope', async t => {
  const handoffs = []; let fail = false, hold;
  const f = await setup(t, url => {
    if (fail) return { ok: false, error: { code: 'unavailable' } };
    if (hold) return new Promise(resolve => { hold.resolve = resolve; });
    const query = new URL(url, 'http://local').searchParams;
    return { ok: true, data: url.includes('/records?') ? evidence(query.get('address')) : { ...fixture(), exporter: query.get('exporter') } };
  }, { enabled: true, installationId: 'fixture-installation', investigate: (...args) => handoffs.push(args) });
  await until(() => f.buttons().some(b => b.textContent === 'Inspect records'));
  f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect sources 192.0.2.10').click();
  await until(() => f.buttons().some(b => b.textContent === 'Investigate in Canvas'));
  assert.equal(handoffs.length, 0);
  f.buttons().find(b => b.textContent === 'Investigate in Canvas').click();
  assert.equal(handoffs.length, 1);
  const [title, context, source, retrievedAt] = handoffs[0];
  assert.match(title, /192\.0\.2\.10/); assert.equal(context.site, fixture().site);
  assert.equal(context.start, fixture().start); assert.equal(context.end, fixture().end);
  assert.equal(context.evidence.record_limit, 100); assert.equal(context.evidence.returned_records, 2);
  assert.equal(source, 'Convergence retained flow archive'); assert.equal(retrievedAt, context.evidence_read_at);
  hold = {};
  const selector = f.w.document.querySelector('[aria-label="Flow exporter"]'); selector.value = '127.0.0.1'; selector.dispatchEvent(new f.w.Event('change', { bubbles: true }));
  await until(() => hold.resolve);
  assert.equal(f.buttons().some(b => b.textContent === 'Investigate in Canvas' && !b.disabled), false);
  hold.resolve({ ok: true, data: { ...fixture(), exporter: '127.0.0.1' } }); hold = null;
  await until(() => !f.body().includes('Reading flows'));
  fail = true; f.buttons().find(b => b.textContent === 'Refresh flows').click();
  await until(() => f.body().includes('Stale cached data'));
  assert.ok(f.buttons().filter(b => b.textContent === 'Inspect records').every(b => b.disabled));
  assert.equal(f.buttons().some(b => b.textContent === 'Investigate in Canvas' && !b.disabled), false);
  assert.equal(handoffs.length, 1);
  assert.ok(f.calls.every(call => call.url.startsWith('/api/hud/')));
});

test('mismatched response never enables investigation and failed detail does not reuse an old selection', async t => {
  let mismatch = true, failed = false; const handoffs = [];
  const f = await setup(t, url => {
    if (!url.includes('/records?')) return { ok: true, data: fixture() };
    if (failed) return { ok: false, error: { code: 'unauthorized' } };
    const address = new URL(url, 'http://local').searchParams.get('address');
    return { ok: true, data: { ...evidence(address), ...(mismatch ? { site: 'different-site' } : {}) } };
  }, { enabled: true, installationId: 'fixture-installation', investigate: (...args) => handoffs.push(args) });
  await until(() => f.buttons().some(b => b.textContent === 'Inspect records'));
  const inspect = () => f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect sources 192.0.2.10').click();
  inspect(); await until(() => f.buttons().some(b => b.textContent === 'Investigate in Canvas'));
  assert.equal(f.buttons().find(b => b.textContent === 'Investigate in Canvas').disabled, true);
  mismatch = false; inspect(); await until(() => f.buttons().some(b => b.textContent === 'Investigate in Canvas' && !b.disabled));
  failed = true; inspect(); await until(() => f.body().includes('Access denied'));
  assert.equal(f.buttons().some(b => b.textContent === 'Investigate in Canvas'), false);
  assert.equal(handoffs.length, 0);
});

test('changing installation clears old summary and investigation context', async t => {
  const handoffs = []; let nextPending;
  const props = { enabled: true, installationId: 'first', investigate: (...args) => handoffs.push(args) };
  const f = await setup(t, (url, options) => {
    if (options.headers['X-NetClaw-Installation'] === 'second') return new Promise(resolve => { nextPending = resolve; });
    const address = new URL(url, 'http://local').searchParams.get('address');
    return { ok: true, data: address ? evidence(address) : fixture() };
  }, props);
  await until(() => f.buttons().some(b => b.textContent === 'Inspect records'));
  f.buttons().find(b => b.getAttribute('aria-label') === 'Inspect sources 192.0.2.10').click();
  await until(() => f.buttons().some(b => b.textContent === 'Investigate in Canvas' && !b.disabled));
  f.w.show({ ...props, installationId: 'second' });
  await until(() => nextPending);
  assert.equal(f.buttons().some(b => b.textContent === 'Investigate in Canvas' && !b.disabled), false);
  assert.equal(handoffs.length, 0);
});

const vmSecurity = () => JSON.parse(JSON.stringify({"generated_at": 1793988324, "site": "lab", "sources": [{"coverage": {"allowlisted_tuple_count": 0, "capture_drops_recent_delta": 0, "capture_drops_total": 0, "counter_delta_seconds": 240, "events_discarded_recent_delta": 0, "events_discarded_total": 0, "excluded_identity_events": 0, "fresh": true, "history_count": 420, "history_limited": false, "inventory_ok": true, "limitations": ["Synthetic demonstration data: no virtual machine traffic was observed.", "Packet metadata is sampled; counts describe the retained sample only."], "max_snapshot_gap_seconds": 30, "metadata_cap_reached": false, "metadata_count": 180, "missing_uuid_vm_count": 0, "packet_capture_ok": true, "policy_configured": true, "sampled": true, "snapshot_count": 9, "snapshot_span_seconds": 240}, "findings": [{"caveat": "Synthetic demonstration finding; no real traffic was observed.", "evidence": {"destination_ip": "198.51.100.20", "destination_port": null, "examples": [{"dst_ip": "198.51.100.20", "dst_port": 22, "ifindex": 101, "observed_at": 1793988114, "protocol": "tcp", "src_ip": "192.0.2.11", "src_port": 40000, "tap": "tap101i0"}, {"dst_ip": "198.51.100.20", "dst_port": 23, "ifindex": 101, "observed_at": 1793988144, "protocol": "tcp", "src_ip": "192.0.2.11", "src_port": 40001, "tap": "tap101i0"}, {"dst_ip": "198.51.100.20", "dst_port": 80, "ifindex": 101, "observed_at": 1793988174, "protocol": "tcp", "src_ip": "192.0.2.11", "src_port": 40002, "tap": "tap101i0"}, {"dst_ip": "198.51.100.20", "dst_port": 443, "ifindex": 101, "observed_at": 1793988204, "protocol": "tcp", "src_ip": "192.0.2.11", "src_port": 40003, "tap": "tap101i0"}, {"dst_ip": "198.51.100.20", "dst_port": 3389, "ifindex": 101, "observed_at": 1793988234, "protocol": "tcp", "src_ip": "192.0.2.11", "src_port": 40004, "tap": "tap101i0"}], "unique_destination_ips": 1, "unique_destination_ports": 48, "unique_tcp_five_tuples": 48}, "first_seen": 1793988084, "id": "d0000000000000000001", "kind": "port_scan", "last_seen": 1793988294, "severity": "review", "vm_id": 101, "vm_uuid": "00000000-0000-4000-8000-000000000101"}, {"caveat": "Synthetic demonstration finding; no real traffic was observed.", "evidence": {"destination_ip": null, "destination_port": 445, "examples": [{"dst_ip": "198.51.100.1", "dst_port": 445, "ifindex": 102, "observed_at": 1793988114, "protocol": "tcp", "src_ip": "192.0.2.12", "src_port": 40000, "tap": "tap102i0"}, {"dst_ip": "198.51.100.2", "dst_port": 445, "ifindex": 102, "observed_at": 1793988144, "protocol": "tcp", "src_ip": "192.0.2.12", "src_port": 40001, "tap": "tap102i0"}, {"dst_ip": "198.51.100.3", "dst_port": 445, "ifindex": 102, "observed_at": 1793988174, "protocol": "tcp", "src_ip": "192.0.2.12", "src_port": 40002, "tap": "tap102i0"}, {"dst_ip": "198.51.100.4", "dst_port": 445, "ifindex": 102, "observed_at": 1793988204, "protocol": "tcp", "src_ip": "192.0.2.12", "src_port": 40003, "tap": "tap102i0"}, {"dst_ip": "198.51.100.5", "dst_port": 445, "ifindex": 102, "observed_at": 1793988234, "protocol": "tcp", "src_ip": "192.0.2.12", "src_port": 40004, "tap": "tap102i0"}], "unique_destination_ips": 64, "unique_destination_ports": 1, "unique_tcp_five_tuples": 64}, "first_seen": 1793988084, "id": "d0000000000000000002", "kind": "network_sweep", "last_seen": 1793988294, "severity": "review", "vm_id": 102, "vm_uuid": "00000000-0000-4000-8000-000000000102"}, {"caveat": "Synthetic demonstration finding; no real traffic was observed.", "evidence": {"destination_ip": "203.0.113.10", "destination_port": 5432, "examples": [{"dst_ip": "203.0.113.10", "dst_port": 5432, "ifindex": 103, "observed_at": 1793988114, "protocol": "tcp", "src_ip": "192.0.2.13", "src_port": 40000, "tap": "tap103i0"}, {"dst_ip": "203.0.113.10", "dst_port": 5432, "ifindex": 103, "observed_at": 1793988144, "protocol": "tcp", "src_ip": "192.0.2.13", "src_port": 40001, "tap": "tap103i0"}, {"dst_ip": "203.0.113.10", "dst_port": 5432, "ifindex": 103, "observed_at": 1793988174, "protocol": "tcp", "src_ip": "192.0.2.13", "src_port": 40002, "tap": "tap103i0"}], "unique_destination_ips": 1, "unique_destination_ports": 1, "unique_tcp_five_tuples": 3}, "first_seen": 1793988084, "id": "d0000000000000000003", "kind": "protected_network_contact", "last_seen": 1793988294, "severity": "review", "vm_id": 103, "vm_uuid": "00000000-0000-4000-8000-000000000103"}], "id": "demo-hypervisor", "kind": "synthetic", "last_contact": 1793988319, "node": "demo-node-1", "observed_at": 1793988319, "site": "lab", "status": "reporting", "summary": {"affected_vm_count": 3, "assessment": "review", "finding_count": 3, "findings_truncated": false}, "vms": [{"capture_state": "observing", "finding_count": 1, "nics": [{"capture_state": "observing", "ifindex": 101, "name": "net0", "tap": "tap101i0"}], "power_state": "running", "vm_id": 101, "vm_uuid": "00000000-0000-4000-8000-000000000101"}, {"capture_state": "observing", "finding_count": 1, "nics": [{"capture_state": "observing", "ifindex": 102, "name": "net0", "tap": "tap102i0"}], "power_state": "running", "vm_id": 102, "vm_uuid": "00000000-0000-4000-8000-000000000102"}, {"capture_state": "observing", "finding_count": 1, "nics": [{"capture_state": "observing", "ifindex": 103, "name": "net0", "tap": "tap103i0"}], "power_state": "running", "vm_id": 103, "vm_uuid": "00000000-0000-4000-8000-000000000103"}, {"capture_state": "observing", "finding_count": 0, "nics": [{"capture_state": "observing", "ifindex": 104, "name": "net0", "tap": "tap104i0"}], "power_state": "running", "vm_id": 104, "vm_uuid": "00000000-0000-4000-8000-000000000104"}, {"capture_state": "stopped", "finding_count": 0, "nics": [{"capture_state": "absent", "ifindex": null, "name": "net0", "tap": "tap105i0"}], "power_state": "stopped", "vm_id": 105, "vm_uuid": "00000000-0000-4000-8000-000000000105"}]}, {"coverage": {"allowlisted_tuple_count": 0, "capture_drops_recent_delta": null, "capture_drops_total": null, "counter_delta_seconds": null, "events_discarded_recent_delta": null, "events_discarded_total": null, "excluded_identity_events": 0, "fresh": false, "history_count": 0, "history_limited": false, "inventory_ok": false, "limitations": ["Synthetic demonstration data: no virtual machine traffic was observed.", "No snapshot in the last five minutes; current activity is unknown."], "max_snapshot_gap_seconds": null, "metadata_cap_reached": false, "metadata_count": 0, "missing_uuid_vm_count": 0, "packet_capture_ok": false, "policy_configured": false, "sampled": true, "snapshot_count": 0, "snapshot_span_seconds": 0}, "findings": [], "id": "demo-stale-hypervisor", "kind": "synthetic", "last_contact": 1793987424, "node": "demo-node-2", "observed_at": 1793987424, "site": "lab", "status": "stale", "summary": {"affected_vm_count": 0, "assessment": "insufficient_evidence", "finding_count": 0, "findings_truncated": false}, "vms": [{"capture_state": "unavailable", "finding_count": 0, "nics": [{"capture_state": "error", "ifindex": null, "name": "net0", "tap": "tap201i0"}], "power_state": "unknown", "vm_id": 201, "vm_uuid": "00000000-0000-4000-8000-000000000201"}]}], "status": "configured", "synthetic": true, "window_seconds": 300}));

test('VM Security loads only when opened, labels synthetic data and keeps assessments advisory', async t => {
  const f = await setup(t, url => url.startsWith('/api/hud/convergence/vm-security') ? { ok: true, data: vmSecurity() } : { ok: true, data: fixture() });
  await until(() => f.body().includes('Refresh flows'));
  await new Promise(resolve => setTimeout(resolve, 50));
  assert.equal(f.calls.filter(c => c.url.includes('vm-security')).length, 0);
  const open = () => f.buttons().find(b => /VM Security/.test(b.textContent));
  await until(() => open() && !open().disabled); open().click();
  await until(() => f.body().includes('Synthetic demonstration.'));
  const text = f.body();
  for (const phrase of ['Possible port scanning', 'Possible network sweep', 'Protected network contact', 'Possible patterns to review.',
                        'Insufficient evidence: current activity is unknown.', 'not proof of attack or compromise', 'coverage gaps, not clean results'])
    assert.ok(text.includes(phrase), phrase);
  assert.ok(!/\bsafe\b|all clear|compromised/i.test(text.replace('not an all-clear', '').replace('proof of attack or compromise', '')));
});

test('VM Security refresh failure keeps the earlier result marked stale', async t => {
  let fail = false;
  const f = await setup(t, url => url.startsWith('/api/hud/convergence/vm-security')
    ? (fail ? { ok: false, error: { code: 'unavailable' } } : { ok: true, data: vmSecurity() }) : { ok: true, data: fixture() });
  const button = () => f.buttons().find(b => /VM Security/.test(b.textContent));
  await until(() => button() && !button().disabled); button().click();
  await until(() => f.body().includes('Synthetic demonstration.'));
  fail = true; button().click();
  await until(() => f.body().includes('Stale cached data'));
  assert.ok(f.body().includes('Possible port scanning'));
});

test('VM Security without a source says so instead of showing an empty result', async t => {
  const f = await setup(t, url => url.startsWith('/api/hud/convergence/vm-security')
    ? { ok: true, data: { site: 'synthetic-lab', status: 'not_configured', sources: [] } } : { ok: true, data: fixture() });
  const button = () => f.buttons().find(b => /VM Security/.test(b.textContent));
  await until(() => button() && !button().disabled); button().click();
  await until(() => f.body().includes('No VM Security source is configured'));
});

