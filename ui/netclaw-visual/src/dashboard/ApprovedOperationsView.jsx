import React, { useEffect, useMemo, useRef, useState } from 'react';
import OwnerSessionGate from './OwnerSessionGate.jsx';
import RetainedOperationsView from './RetainedOperationsView.jsx';
import { operationReference } from '../shared/protected-operations-client.js';
import './protected-operations.css';

const terminal = new Set(['completed', 'refused', 'failed', 'denied', 'cancelled', 'revoked']);
const json = value => JSON.stringify(value, null, 2);
function Operations({ api, session, installationId }) {
  const references = useMemo(() => operationReference(installationId), [installationId]);
  const [catalog, setCatalog] = useState(null), [memberIndex, setMemberIndex] = useState(0), [profileIndex, setProfileIndex] = useState(0), [toolIndex, setToolIndex] = useState(0);
  const [reference, setReference] = useState(() => references.read()), [operation, setOperation] = useState(null), [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState(false), [error, setError] = useState('');
  const [rejectedDraft, setRejectedDraft] = useState(false);
  const lock = useRef(false), alive = useRef(true), referenceRef = useRef(reference);
  const [clock, setClock] = useState(Date.now);
  useEffect(() => {
    setClock(Date.now()); const expires = operation?.review?.limits?.expires_at_ms;
    if (!Number.isSafeInteger(expires)) return;
    const timer = setTimeout(() => setClock(Date.now()), Math.max(0, expires - Date.now() + 10));
    return () => clearTimeout(timer);
  }, [operation]);
  const retain = value => {
    const expected = referenceRef.current;
    if (!value || typeof value.operation_id !== 'string' || typeof value.client_nonce !== 'string' || expected?.operation_id && expected.operation_id !== value.operation_id || expected?.client_nonce && expected.client_nonce !== value.client_nonce) throw Error('Operation identity changed. Nothing was resent.');
    references.write(value); referenceRef.current = { operation_id: value.operation_id, client_nonce: value.client_nonce }; setReference(referenceRef.current); setOperation(value); setUncertain(false); setRejectedDraft(false);
  };
  useEffect(() => {
    alive.current = true;
    api.catalog().then(value => { if (alive.current) setCatalog(value); }).catch(failure => { if (alive.current) setError(failure.message); });
    const saved = references.read();
    if (saved) { setBusy(true); setUncertain(true); api.status(saved).then(value => { if (alive.current) retain(value); }).catch(failure => { if (alive.current) setError(failure.message); }).finally(() => { if (alive.current) setBusy(false); }); }
    return () => { alive.current = false; };
  }, [api, references]);
  const run = async (action, mutating = false, preparing = false) => {
    if (lock.current) return; lock.current = true; setBusy(true); setError('');
    if (mutating) setUncertain(true);
    try { const value = await action(); if (alive.current) retain(value); }
    catch (failure) {
      const notSubmitted = preparing && failure.prepareNotSubmitted === true && !referenceRef.current?.operation_id;
      // A confirmed local refusal never reached admission. Do not strand its
      // nonce after reload or session loss; the next preparation still needs an
      // explicit user action and gets a fresh nonce. Unknown replies keep it.
      if (notSubmitted) { try { references.clear(); } catch { /* Explicit discard will retry storage cleanup. */ } }
      if (alive.current) { setError(failure.message); setUncertain(!notSubmitted); setRejectedDraft(notSubmitted); }
    }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  };
  const members = catalog?.members || [], selected = members[memberIndex], profile = selected?.model_profiles?.[profileIndex], tool = selected?.tools?.[toolIndex];
  const prepare = () => {
    if (!selected || !profile || !tool || reference || lock.current) return;
    const client_nonce = crypto.randomUUID();
    // Persist identity BEFORE I/O. Never persist the reviewed authority or credentials.
    try { references.write({ client_nonce }); } catch { setError('Private operation identity could not be saved. Nothing was submitted.'); return; }
    referenceRef.current = { client_nonce }; setReference(referenceRef.current);
    run(() => api.prepare({ client_nonce, catalog_revision: catalog.revision, member_id: selected.member.member_id, model_profile_id: profile.profile_id, tool: tool.tool, arguments: tool.arguments }), true, true);
  };
  const discardRejected = () => {
    if (!rejectedDraft || busy || referenceRef.current?.operation_id) return;
    try { references.clear(); } catch { setError('The rejected draft could not be cleared. Nothing was submitted.'); return; }
    referenceRef.current = null; setReference(null); setOperation(null); setRejectedDraft(false); setUncertain(false); setError('');
    setCatalog(null); setMemberIndex(0); setProfileIndex(0); setToolIndex(0);
    api.catalog().then(value => { if (alive.current) setCatalog(value); }).catch(failure => { if (alive.current) setError(failure.message); });
  };
  const actions = !uncertain && !busy ? operation?.allowed_actions || [] : [];
  const review = operation?.review;
  const reviewCurrent = review && review.limits?.expires_at_ms > clock;
  const canNew = operation && !uncertain && terminal.has(operation.state) && !operation.reconciliation_required && (operation.state === 'completed' || !operation.may_have_executed);
  return <>
    {error && <p role="alert">{error}</p>}
    {!reference && <section className="panel"><h2>Prepare an exact operation</h2><p>Select a qualified member, model and read-only call. Preparing a review does not execute it.</p>
      {!catalog ? <p>Reading eligible profiles…</p> : !members.length ? <p>No eligible protected member profiles are available.</p> : <div className="protected-selectors">
        <label>Member<select value={memberIndex} onChange={event => { setMemberIndex(Number(event.target.value)); setProfileIndex(0); setToolIndex(0); }}>{members.map((value, index) => <option value={index} key={value.member.member_id}>{value.member.member_id}</option>)}</select></label>
        <label>Model profile<select value={profileIndex} onChange={event => setProfileIndex(Number(event.target.value))}>{selected.model_profiles.map((value, index) => <option value={index} key={value.profile_id}>{value.profile_id} · {value.runtime_kind} · {value.provider} / {value.model}</option>)}</select></label>
        <label>Read-only call<select value={toolIndex} onChange={event => setToolIndex(Number(event.target.value))}>{selected.tools.map((value, index) => <option value={index} key={index}>{value.tool} · {value.device_ref}</option>)}</select></label>
        {tool && <><h3>Exact arguments</h3><pre aria-label="Candidate arguments">{json(tool.arguments)}</pre></>}
        <button className="primary" disabled={busy || !tool || !profile} onClick={prepare}>Prepare review</button>
      </div>}
    </section>}
    {reference && <section className="panel"><h2>Operation {rejectedDraft ? 'not submitted' : operation?.state || 'awaiting confirmation'}</h2><dl className="facts"><div><dt>Operation</dt><dd>{reference.operation_id || (rejectedDraft ? 'No operation submitted' : 'Recovering from client nonce')}</dd></div><div><dt>Client nonce</dt><dd>{reference.client_nonce}</dd></div><div><dt>Recorded attempts</dt><dd>{rejectedDraft ? 0 : operation?.attempt_count ?? 'Not confirmed'}</dd></div></dl>
      {rejectedDraft && <><p role="status">This review was rejected before submission. Discard the draft to choose again; nothing will be retried automatically.</p><button disabled={busy} onClick={discardRejected}>Discard rejected review</button></>}
      {(uncertain || operation?.reconciliation_required || operation?.may_have_executed && !terminal.has(operation.state)) && <p role="status">The operation may have been accepted or executed. Check this same operation; no approval, model call or tool call will be automatically repeated.</p>}
      {!rejectedDraft && <div className="protected-actions"><button disabled={busy} onClick={() => run(() => api.status(reference))}>{busy ? 'Checking…' : 'Check status'}</button>
        {reference.operation_id && <button disabled={busy} onClick={() => run(() => api.reconcile(reference.operation_id))}>Reconcile existing operation</button>}
      </div>}
      {review && <><h3>Immutable approval review</h3><p>Review the complete principal, member identity, model profile, tool arguments and limits before approving once.</p><dl className="facts"><div><dt>Review digest</dt><dd>{operation.review_digest}</dd></div><div><dt>Revision</dt><dd>{operation.revision}</dd></div><div><dt>Signed-in owner</dt><dd>{session.principal.display_name}</dd></div><div><dt>Review expires</dt><dd>{new Date(review.limits.expires_at_ms).toISOString()}</dd></div></dl><pre aria-label="Immutable operation review">{json(review)}</pre>
        {!reviewCurrent && <p>This review has expired. It cannot authorize execution.</p>}
        <div className="protected-actions">{['approve', 'deny'].map(decision => <button key={decision} className={decision === 'approve' ? 'primary' : ''} disabled={!actions.includes(decision) || decision === 'approve' && !reviewCurrent} onClick={() => run(() => api.decision(reference.operation_id, { revision: operation.revision, review_digest: operation.review_digest, decision }), true)}>{decision === 'approve' ? 'Approve once' : 'Deny'}</button>)}
          {actions.includes('revoke') && <button disabled={busy} onClick={() => run(() => api.revoke(reference.operation_id), true)}>Revoke remaining authority</button>}
        </div>
      </>}
      {operation?.approval && <><h3>Recorded approval</h3><pre>{json(operation.approval)}</pre></>}
      {operation?.result && <><h3>Execution evidence</h3><dl className="facts"><div><dt>Receipt received</dt><dd>Yes</dd></div><div><dt>Signature and bindings verified</dt><dd>{operation.result.verified === true ? 'Yes' : 'Not confirmed'}</dd></div><div><dt>Border acknowledgement durably stored</dt><dd>{operation.result.durable_ack === true ? 'Yes' : 'Not confirmed'}</dd></div><div><dt>ACK delivery</dt><dd>{operation.result.ack_delivery_pending ? 'Pending reconciliation' : 'No pending delivery reported'}</dd></div><div><dt>Result digest</dt><dd>{operation.result.digest || 'Not reported'}</dd></div></dl>{operation.result.verified === true && <pre aria-label="Verified execution evidence">{json(operation.result.evidence)}</pre>}</>}
      {operation?.error_code && <p>Recorded outcome: {operation.error_code}</p>}
      {canNew && <button disabled={busy} onClick={() => { references.clear(); referenceRef.current = null; setReference(null); setOperation(null); setError(''); }}>Prepare a new review</button>}
    </section>}
  </>;
}

export default function ApprovedOperationsView({ enabled, installationId, retainMultiple = false }) {
  const View = retainMultiple ? RetainedOperationsView : Operations;
  return <OwnerSessionGate key={installationId} enabled={enabled} installationId={installationId}>{({ api, session }) => <View key={installationId + session.principal.subject} api={api} session={session} installationId={installationId}/>}</OwnerSessionGate>;
}
