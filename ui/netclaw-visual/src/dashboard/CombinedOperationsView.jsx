import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CombinedOperations, combinedChoices, combinedReference } from '../shared/protected-combined.js';

export default function CombinedOperationsView({ api, installationId, principal }) {
  const controller = useMemo(() => new CombinedOperations(api, combinedReference(installationId, principal), installationId, principal), [api, installationId, principal]);
  const [choices, setChoices] = useState(null), [selection, setSelection] = useState({ 4: 0, 6: 0 });
  const [reference, setReference] = useState(null), [value, setValue] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const alive = useRef(true), lock = useRef(false);
  const sync = () => { setReference(controller.references.read()); setValue(controller.value); };
  const run = async action => {
    if (lock.current) return; lock.current = true; setBusy(true); setError('');
    try { await action(); } catch (failure) { if (alive.current) setError(failure.message); }
    finally { lock.current = false; if (alive.current) { try { sync(); } catch (failure) { setError(failure.message); } setBusy(false); } }
  };
  useEffect(() => {
    alive.current = true;
    run(async () => { const catalog = await api.catalog(); if (!alive.current) return; setChoices(combinedChoices(catalog)); const saved = controller.references.read(); if (saved && !saved.not_submitted) await controller.recover(); });
    return () => { alive.current = false; };
  }, [controller]);
  if (!reference && !error && (!choices || !choices[4].length || !choices[6].length)) return null;
  return <section className="panel" aria-label="Combined subnet request"><h2>Local IPv4 + cloud IPv6</h2>
    <p>One request, two separate approvals. Each member runs its own local model. Provider API charge is zero; compute and transfer costs remain separate.</p>
    {error && <p role="alert">{error}</p>}
    {!reference && choices && <><div className="protected-selectors">{[4, 6].map(family => <label key={family}>IPv{family} member<select aria-label={`IPv${family} calculator`} value={selection[family]} disabled={busy} onChange={e => setSelection({ ...selection, [family]: Number(e.target.value) })}>{choices[family].map((choice, i) => <option key={i} value={i}>{choice.member_id} · {choice.cidr}</option>)}</select></label>)}</div>
      <button className="primary" disabled={busy || !choices[4].length || !choices[6].length} onClick={() => run(() => controller.prepare([choices[4][selection[4]], choices[6][selection[6]]]))}>Prepare both reviews</button></>}
    {reference && <><p>Request: {reference.parent_id || 'Awaiting confirmation'} · {value?.state || (reference.not_submitted ? 'Not submitted' : 'Unknown')}</p>
      {controller.uncertain && <p role="status">Check this same request. No preparation, approval or model call is repeated automatically.</p>}
      {!reference.not_submitted && <button disabled={busy} onClick={() => run(() => controller.recover())}>Check combined status</button>}
      {value?.children.map((child, index) => <article key={child.operation_id} aria-label={`IPv${child.family} child`}><h3>IPv{child.family} · {child.state}</h3><p>{child.review.member.member_id} · {child.review.tool_call.arguments.cidr} · {child.review.model_profile.provider} / {child.review.model_profile.model}</p>
        <p>Operation: {child.operation_id} · Review: {child.review_digest}</p><pre aria-label={`IPv${child.family} immutable review`}>{JSON.stringify(child.review, null, 2)}</pre>
        <div className="protected-actions">{['approve', 'deny'].map(decision => <button key={decision} className={decision === 'approve' ? 'primary' : ''} disabled={busy || controller.uncertain || reference.cancel_sent || reference.children[index].decision_sent || !child.allowed_actions.includes(decision) || decision === 'approve' && child.review.limits.expires_at_ms <= Date.now()} onClick={() => run(() => controller.decide(index, decision))}>{decision === 'approve' ? `Approve IPv${child.family} once` : `Deny IPv${child.family}`}</button>)}</div>
        {child.result && <><p>Signed result verified: {child.result.verified === true ? 'Yes' : 'Not confirmed'} · Durable ACK: {child.result.durable_ack === true ? 'Yes' : 'Not confirmed'}</p>{child.result.verified === true && <pre aria-label={`IPv${child.family} verified result`}>{JSON.stringify(child.result.evidence, null, 2)}</pre>}</>}
        {child.error_code && <p>Recorded outcome: {child.error_code}</p>}
      </article>)}
      {reference.parent_id && <button disabled={busy || reference.cancel_sent} onClick={() => run(() => controller.cancel())}>Cancel remaining children</button>}
      {(reference.not_submitted || ['complete', 'partial', 'failed', 'cancelled'].includes(value?.state)) && <button disabled={busy || controller.uncertain} onClick={() => run(() => controller.discard())}>{reference.not_submitted ? 'Discard unsubmitted combined request' : 'Remove resolved combined reference'}</button>}
    </>}
  </section>;
}
