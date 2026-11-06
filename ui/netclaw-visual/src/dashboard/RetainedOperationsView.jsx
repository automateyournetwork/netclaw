import OperationResultEvidence from './OperationResultEvidence.jsx';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { operationIdentifier, operationReferences, operationSelection, verifiedResultSummary, REFERENCE_CAPACITY, removableOperation } from '../shared/protected-operation-references.js';

const json = value => JSON.stringify(value, null, 2);
export default function RetainedOperationsView({ api, principal, installationId }) {
  const store = useMemo(() => operationReferences(installationId), [installationId]);
  const [references, setReferences] = useState([]), [records, setRecords] = useState({}), [selectedNonce, setSelectedNonce] = useState(null);
  const [catalog, setCatalog] = useState(null), [memberIndex, setMemberIndex] = useState(0), [profileIndex, setProfileIndex] = useState(0), [toolIndex, setToolIndex] = useState(0);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [storageError, setStorageError] = useState(false), [recoverId, setRecoverId] = useState(''), [recoverKind, setRecoverKind] = useState('operation_id'), [clock, setClock] = useState(Date.now);
  const alive = useRef(true), locked = useRef(false), refs = useRef([]), recordRef = useRef({});
  const retainRefs = rows => { refs.current = rows; setReferences(rows); };
  const update = (nonce, patch) => { recordRef.current = { ...recordRef.current, [nonce]: { ...recordRef.current[nonce], ...patch } }; setRecords(recordRef.current); };
  const retain = (value, expected) => {
    if (!value || !operationIdentifier(value.client_nonce) || !operationIdentifier(value.operation_id) || expected?.client_nonce && expected.client_nonce !== value.client_nonce || expected?.operation_id && expected.operation_id !== value.operation_id) throw Error('Operation identity changed. Nothing was resent.');
    retainRefs(store.put(value)); update(value.client_nonce, { operation: value, uncertain: false, error: '' });
    return value.client_nonce;
  };
  useEffect(() => {
    alive.current = true;
    api.catalog().then(value => { if (alive.current) setCatalog(value); }).catch(failure => { if (alive.current) setError(failure.message); });
    try {
      const saved = store.read(); retainRefs(saved); setSelectedNonce(saved[0]?.client_nonce || null);
      for (const ref of saved) {
        update(ref.client_nonce, { uncertain: true });
        api.status(ref).then(value => { if (alive.current) retain(value, ref); }).catch(failure => { if (alive.current) update(ref.client_nonce, { error: failure.message, uncertain: true }); });
      }
    } catch (failure) { setStorageError(true); setError(failure.message); }
    return () => { alive.current = false; };
  }, [api, store]);
  const current = records[selectedNonce], operation = current?.operation, reference = references.find(row => row.client_nonce === selectedNonce);
  const expires = operation?.review?.limits?.expires_at_ms;
  useEffect(() => { setClock(Date.now()); if (!Number.isSafeInteger(expires)) return; const timer = setTimeout(() => setClock(Date.now()), Math.max(0, expires - Date.now() + 10)); return () => clearTimeout(timer); }, [expires]);
  const run = async (ref, action, mutating = false, preparing = false, sentAction) => {
    if (locked.current) return; locked.current = true; setBusy(true); setError('');
    if (mutating) update(ref.client_nonce, { uncertain: true, error: '' });
    try { if (sentAction) retainRefs(store.markSent(ref, sentAction)); const value = await action(); if (alive.current) retain(value, ref); }
    catch (failure) {
      if (alive.current) {
        if (preparing && failure.prepareNotSubmitted === true && !ref.operation_id) {
          try { retainRefs(store.discardUnsubmitted(ref.client_nonce)); if (selectedNonce === ref.client_nonce) setSelectedNonce(null); setError('The review was rejected before submission. Nothing was executed. Choose again explicitly.'); }
          catch (storageFailure) { setStorageError(true); setError(storageFailure.message); }
        } else update(ref.client_nonce, { uncertain: true, error: failure.message });
      }
    } finally { locked.current = false; if (alive.current) setBusy(false); }
  };
  const members = catalog?.members || [], member = members[memberIndex], profile = member?.model_profiles?.[profileIndex], tool = member?.tools?.[toolIndex];
  const selection = operationSelection(member?.member?.member_id, tool);
  const unresolvedSelection = references.some(ref => {
    const row = records[ref.client_nonce], op = row?.operation;
    if (!op) return true; // An unknown nonce cannot safely be assigned to a different selection.
    if (removableOperation(op)) return false;
    const retainedSelection = operationSelection(op.review?.member?.member_id, op.review?.tool_call);
    return !retainedSelection || retainedSelection === selection;
  });
  const prepare = () => {
    if (locked.current || storageError || !member || !profile || !tool || !selection || unresolvedSelection || refs.current.length >= REFERENCE_CAPACITY) return;
    const ref = { client_nonce: crypto.randomUUID() };
    try { retainRefs(store.put(ref)); setSelectedNonce(ref.client_nonce); }
    catch (failure) { setStorageError(true); setError(failure.message); return; }
    run(ref, () => api.prepare({ client_nonce: ref.client_nonce, catalog_revision: catalog.revision, member_id: member.member.member_id, model_profile_id: profile.profile_id, tool: tool.tool, arguments: tool.arguments }), true, true);
  };
  const recover = async event => {
    event.preventDefault(); if (locked.current || !operationIdentifier(recoverId)) return;
    const id = recoverId;
    if (refs.current.length >= REFERENCE_CAPACITY && !refs.current.some(ref => ref.operation_id === id)) { setError('Retained operation capacity reached. Remove a resolved reference first.'); return; }
    locked.current = true; setBusy(true); setError('');
    try { const expected = { [recoverKind]: id }; const value = await api.status(expected); if (value?.review?.border?.installation_id !== installationId || value?.review?.principal?.issuer !== principal.issuer || value?.review?.principal?.subject !== principal.subject) throw Error('The recovered operation belongs to a different Border or operator.'); if (alive.current) { setSelectedNonce(retain({ ...value, decision_sent: true, revoke_sent: true }, expected)); setRecoverId(''); } }
    catch (failure) { if (alive.current) setError(failure.message); }
    finally { locked.current = false; if (alive.current) setBusy(false); }
  };
  const actions = !busy && !current?.uncertain ? operation?.allowed_actions || [] : [];
  return <>
    <p>The Border controls approvals. Qualified NetClaw members execute each separately approved read or calculation.</p>
    {error && <p role="alert">{error}</p>}
    <section className="panel"><h2>Prepare an exact operation</h2><p>Each exact call requires its own review and approval. Preparing does not execute.</p>
      {!catalog ? <p>Reading eligible profiles…</p> : !members.length ? <p>No eligible protected member profiles are available.</p> : <div className="protected-selectors">
        <label>Member<select value={memberIndex} onChange={event => { setMemberIndex(Number(event.target.value)); setProfileIndex(0); setToolIndex(0); }}>{members.map((value, index) => <option key={value.member.member_id} value={index}>{value.member.member_id}</option>)}</select></label>
        <label>Model profile<select value={profileIndex} onChange={event => setProfileIndex(Number(event.target.value))}>{member.model_profiles.map((value, index) => <option key={value.profile_id} value={index}>{value.profile_id} · {value.runtime_kind} · {value.provider} / {value.model}</option>)}</select></label>
        <label>Read-only call<select value={toolIndex} onChange={event => setToolIndex(Number(event.target.value))}>{member.tools.map((value, index) => <option key={index} value={index}>{value.tool} · {value.device_ref}</option>)}</select></label>
        {tool && <pre aria-label="Candidate arguments">{json(tool.arguments)}</pre>}
        <button className="primary" disabled={busy || storageError || !profile || !tool || !selection || unresolvedSelection || references.length >= REFERENCE_CAPACITY} onClick={prepare}>Prepare review</button>
        {unresolvedSelection && <p>Recover the existing unresolved operation for this selection before preparing another.</p>}
      </div>}
      {references.length >= REFERENCE_CAPACITY && <p>All {REFERENCE_CAPACITY} retained slots are occupied. Explicitly remove a resolved reference before preparing another; unresolved references are preserved.</p>}
    </section>
    <section className="panel"><h2>Retained operations</h2><p>{references.length} of {REFERENCE_CAPACITY} references retained in this browser session. Keep an operation ID to recover it in another client; automatic history discovery is unavailable.</p>
      <div className="table-scroll"><table><thead><tr><th>Target / operation</th><th>Member / runtime</th><th>Outcome</th><th>Verified result</th><th>Receipt / acknowledgement</th><th>Inspect</th></tr></thead><tbody>{references.map(ref => {
        const row = records[ref.client_nonce], op = row?.operation;
        return <tr key={ref.client_nonce} aria-selected={selectedNonce === ref.client_nonce}><td>{op?.review?.tool_call?.device_ref || op?.review?.tool_call?.arguments?.device_name || 'Awaiting owned status'}<small>{ref.operation_id || ref.client_nonce}</small></td><td>{op?.review?.member?.member_id || 'Unavailable'}<small>{op?.review?.model_profile?.runtime_kind || 'Unavailable'}</small></td><td>{row?.uncertain ? 'Awaiting confirmation' : op?.state || 'Unavailable'}</td><td>{verifiedResultSummary(op)}</td><td>{op?.result?.verified === true ? 'Verified receipt' : 'Not verified'}<small>{op?.result?.durable_ack === true ? op.result.ack_delivery_pending ? 'ACK delivery pending' : 'Durable ACK' : 'ACK not confirmed'}</small></td><td><button onClick={() => setSelectedNonce(ref.client_nonce)} aria-label={`Inspect operation ${ref.operation_id || ref.client_nonce}`}>Inspect</button></td></tr>;
      })}</tbody></table></div>
      <form onSubmit={recover}><label>Reference type<select aria-label="Recovery reference type" value={recoverKind} onChange={e => setRecoverKind(e.target.value)}><option value="operation_id">Operation ID</option><option value="client_nonce">Client nonce</option></select></label><label>Recover retained reference<input value={recoverId} onChange={event => setRecoverId(event.target.value)} autoComplete="off" spellCheck="false" maxLength={200}/></label><button disabled={busy || storageError || !operationIdentifier(recoverId)}>Recover existing operation</button></form><p>Imported references recover status only. They cannot resend a decision or revocation.</p>
    </section>
    {reference && <section className="panel" aria-label="Selected operation"><h2>Operation {operation?.state || 'awaiting confirmation'}</h2><dl className="facts"><div><dt>Operation</dt><dd>{reference.operation_id || 'Recovering from client nonce'}</dd></div><div><dt>Client nonce</dt><dd>{reference.client_nonce}</dd></div><div><dt>Recorded attempts</dt><dd>{operation?.attempt_count ?? 'Not confirmed'}</dd></div></dl>
      {current?.error && <p role="alert">{current.error}</p>}
      {(current?.uncertain || operation?.reconciliation_required) && <p role="status">This operation may have been accepted or executed. Recover this same identity; nothing is automatically retried.</p>}
      <div className="protected-actions"><button disabled={busy} onClick={() => run(reference, () => api.status(reference))}>Check status</button>{reference.operation_id && <button disabled={busy} onClick={() => run(reference, () => api.reconcile(reference.operation_id))}>Reconcile existing operation</button>}</div>
      {operation?.review && <><h3>Immutable approval review</h3><dl className="facts"><div><dt>Review digest</dt><dd>{operation.review_digest}</dd></div><div><dt>Revision</dt><dd>{operation.revision}</dd></div><div><dt>Review operator</dt><dd>{operation.review.principal.display_name}</dd></div><div><dt>Review expires</dt><dd>{Number.isSafeInteger(expires) ? new Date(expires).toISOString() : 'Unavailable'}</dd></div></dl><pre aria-label="Immutable operation review">{json(operation.review)}</pre>
        {!(expires > clock) && <p>This review has expired. It cannot authorize execution.</p>}
        <div className="protected-actions">{['approve', 'deny'].map(decision => <button key={decision} className={decision === 'approve' ? 'primary' : ''} disabled={reference.decision_sent || !actions.includes(decision) || decision === 'approve' && !(expires > clock)} onClick={() => run(reference, () => api.decision(reference.operation_id, { revision: operation.revision, review_digest: operation.review_digest, decision }), true, false, 'decision')}>{decision === 'approve' ? 'Approve once' : 'Deny'}</button>)}{actions.includes('revoke') && <button disabled={busy || reference.revoke_sent} onClick={() => run(reference, () => api.revoke(reference.operation_id), true, false, 'revoke')}>Revoke remaining authority</button>}</div>
      </>}
      {operation?.approval && <><h3>Recorded approval</h3><pre>{json(operation.approval)}</pre></>}
      {operation?.result && <><h3>Execution evidence</h3><dl className="facts"><div><dt>Signature and bindings verified</dt><dd>{operation.result.verified === true ? 'Yes' : 'Not confirmed'}</dd></div><div><dt>Border acknowledgement durably stored</dt><dd>{operation.result.durable_ack === true ? 'Yes' : 'Not confirmed'}</dd></div><div><dt>ACK delivery</dt><dd>{operation.result.ack_delivery_pending ? 'Pending reconciliation' : 'No pending delivery reported'}</dd></div><div><dt>Result digest</dt><dd>{operation.result.digest || 'Not reported'}</dd></div></dl><OperationResultEvidence operation={operation}/></>}
      {operation?.error_code && <p>Recorded outcome: {operation.error_code}</p>}
      {removableOperation(operation) && !current?.uncertain && <button disabled={busy} onClick={() => { try { retainRefs(store.remove(operation)); setSelectedNonce(null); } catch (failure) { setError(failure.message); } }}>Remove resolved reference</button>}
    </section>}
  </>;
}
