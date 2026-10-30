import React, { useEffect, useId, useState, useRef } from 'react';

const controlStyle = { background: '#0D1722', color: '#DAE6EF', border: '1px solid #3C5264', borderRadius: 5, padding: 7, width: '100%', fontSize: 11 };
export default function TerminalChangeControl({ devices, value, onChange, busy }) {
  const modeId = useId();
  const [policy, setPolicy] = useState(null), [selected, setSelected] = useState([]);
  const [confirmed, setConfirmed] = useState(false), [saving, setSaving] = useState(false), [error, setError] = useState('');
  const [candidate, setCandidate] = useState(null), [inventories, setInventories] = useState([]), [harness, setHarness] = useState('');
  const [profile, setProfile] = useState('ospf-routing-v1');
  const candidateSequence=useRef(0), inventorySequence=useRef(0), currentValue=useRef(value);
  currentValue.current=value;
  useEffect(()=>()=>{candidateSequence.current++;inventorySequence.current++;},[]);
  async function selectCandidate(event) {
    const sequence=++candidateSequence.current;
    const file = event.target.files?.[0]; event.target.value = '';
    setCandidate(null); onChange({ ...value, migration: undefined });
    if (!file) return;
    try {
      if (file.size < 8 || file.size > 2 * 1024 * 1024) throw new Error('Choose a UTF-8 candidate from 8 bytes to 2 MiB.');
      const content = new TextDecoder('utf-8', { fatal:true }).decode(await file.arrayBuffer());
      if(sequence!==candidateSequence.current)return;
      const response = await fetch('/api/terminal/intent/migration-candidates', { method:'POST', headers:{ 'Content-Type':'application/json' }, body:JSON.stringify({ content }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Candidate review failed.');
      if(sequence!==candidateSequence.current)return;
      setCandidate(data); setError('');
    } catch (err) { if(sequence===candidateSequence.current)setError(err.message); }
  }
  async function refreshInventories() {
    const sequence=++inventorySequence.current;
    setHarness(''); onChange({ ...value, migration:undefined });
    try {
      const response = await fetch('/api/terminal/intent/migration-inventories');
      const data = await response.json(); if (!response.ok) throw new Error(data.error);
      if(sequence===inventorySequence.current)setInventories(data);
    } catch (err) { if(sequence===inventorySequence.current)setError(err.message || 'No active pyATS inventory.'); }
  }
  async function load() {
    try {
      const response = await fetch('/api/terminal/intent/change-policy');
      if (response.status === 404) throw new Error('Restart the NetClaw API, then reload these settings to enable Local/Lab change control.');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Restart the API to enable Change control.');
      setPolicy(data); setSelected(data.devices.map(d => d.id));
      onChange({ ...currentValue.current, policyRevision: data.revision, migration:undefined }); setError('');
    } catch (err) { setError(err.message || 'Change control unavailable.'); }
  }
  useEffect(() => { void load(); }, []);
  async function save(enabled) {
    setSaving(true); setError('');
    try {
      const response = await fetch('/api/terminal/intent/change-policy', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ revision: policy.revision, enabled, deviceIds: selected, confirmLab: confirmed }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not save policy.');
      setPolicy(data); setConfirmed(false);
      onChange({ mode: enabled ? 'local-lab' : 'production', policyRevision: data.revision, targetDeviceIds: enabled ? selected : [] });
    } catch (err) { setError(err.message); }
    finally { setSaving(false); }
  }
  const disabled = busy || saving;
  return <section aria-label="Intent change control" style={{ border: '1px solid #3C5264', borderRadius: 7, padding: 10, fontSize: 11, color: '#C3D1DE', lineHeight: 1.5 }}>
    <label htmlFor={modeId} style={{ fontWeight: 750 }}>Change control</label>
    <select id={modeId} aria-label="Change control mode" value={value.mode} disabled={disabled || !policy}
      onChange={e => onChange({ ...value, mode: e.target.value, migration:undefined })} style={{ ...controlStyle, marginTop: 6 }}>
      <option value="production">Production · ServiceNow approval</option>
      <option value="local-lab">Local / Lab · local change record</option>
    </select>
    {value.mode === 'production' ? <p>Production approval requirements remain in effect.</p> : <>
      <p style={{ color: '#F1C47C' }}>Lab devices only. Your explicit change request authorizes the stated task; NetClaw records baseline, rollback and verification locally.</p>
      {policy?.enabled && <fieldset disabled={disabled} style={{ border: 0, padding: 0, margin: '8px 0' }}>
        <legend>Devices for this request</legend>
        {policy.devices.map(d => <label key={d.id} style={{ display: 'block', marginTop: 5 }}>
          <input type="checkbox" disabled={!d.valid} checked={value.targetDeviceIds.includes(d.id)} onChange={e => onChange({ ...value, migration:undefined, targetDeviceIds: e.target.checked ? [...value.targetDeviceIds, d.id] : value.targetDeviceIds.filter(id => id !== d.id) })} />
          {' '}{d.name} · {d.host}{!d.valid ? ' — endpoint changed; reauthorize' : ''}
        </label>)}
      </fieldset>}
      {!policy?.enabled && <p>No lab devices authorized yet. Set them below before submitting.</p>}
      <details>
        <summary>Review a local migration candidate</summary>
        <p>Select one lab target. The file stays on this installation. Review the exact file and hash before attaching it to your next change request. This does not approve a hosted upload.</p>
        <input aria-label="Local migration candidate" type="file" disabled={disabled || !policy} onChange={selectCandidate} />
        {candidate && <p style={{ overflowWrap:'anywhere' }}>{candidate.bytes} bytes · SHA-256 {candidate.sha256}</p>}
        <button type="button" disabled={disabled || !policy} onClick={refreshInventories}>Refresh active pyATS bindings</button>
        <select aria-label="Active pyATS binding" value={harness} disabled={disabled} style={controlStyle} onChange={e => { setHarness(e.target.value); onChange({ ...value, migration:undefined }); }}>
          <option value="">Choose the process used by Intent</option>
          {inventories.map(i => <option key={i.harness} value={i.harness}>{i.harness.slice(0,8)} · {i.devices.map(d => d.id).join(', ')}</option>)}
        </select>
        <select aria-label="Migration verification profile" value={profile} disabled={disabled} style={controlStyle} onChange={e => { setProfile(e.target.value); onChange({ ...value, migration:undefined }); }}>
          <option value="ospf-routing-v1">OSPF, routes, traffic and management</option>
          <option value="firewall-policy-v1">Permit/deny, NAT when applicable and management</option>
        </select>
        <label><input type="checkbox" checked={Boolean(value.migration)} disabled={disabled || !candidate || !harness || value.targetDeviceIds.length !== 1}
          onChange={e => onChange({ ...value, migration:e.target.checked ? { ...candidate, harness, testbed:inventories.find(i => i.harness === harness).testbed, profile } : undefined })} /> I reviewed this exact candidate for the selected lab target and verification profile.</label>
        <p>Run pyats_list_devices in the same persistent process first. A restarted process or changed inventory requires another review. Junos requires set-format commands; live vendor qualification remains separate.</p>
      </details>
    </>}
    <details>
      <summary style={{ cursor: 'pointer' }}>Manage lab authorization</summary>
      <p>Only these selected SSH endpoints can use Local/Lab mode. This does not change collector permissions or authorize background configuration.</p>
      <fieldset disabled={disabled || !policy} style={{ maxHeight: 170, overflowY: 'auto', border: '1px solid #304455', padding: 6 }}>
        <legend>Designated lab devices</legend>
        {devices.filter(d => d.supported).map(d => <label key={d.id} style={{ display: 'block', margin: '5px 0' }}>
          <input type="checkbox" checked={selected.includes(d.id)} onChange={e => { setConfirmed(false); setSelected(e.target.checked ? [...selected, d.id] : selected.filter(id => id !== d.id)); }} />
          {' '}{d.alias || d.name || d.id} · {d.host}:{d.port}
        </label>)}
      </fieldset>
      <label style={{ display: 'block', margin: '9px 0' }}><input type="checkbox" checked={confirmed} disabled={disabled} onChange={e => setConfirmed(e.target.checked)} /> I own/administer these lab devices and authorize local change control for them.</label>
      <button type="button" disabled={disabled || !policy || !confirmed || !selected.length} onClick={() => save(true)} style={controlStyle}>Save lab authorization</button>
      <button type="button" disabled={disabled || !policy?.enabled} onClick={() => save(false)} style={{ ...controlStyle, marginTop: 6 }}>Disable lab changes</button>
    </details>
    {error && <p role="alert" style={{ color: '#EF8B92' }}>{error}</p>}
    <button type="button" disabled={disabled} onClick={load} style={{ ...controlStyle, marginTop: 7 }}>Reload settings</button>
  </section>;
}
