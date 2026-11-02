import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createProtectedOperationsApi } from '../shared/protected-operations-client.js';

export default function OwnerSessionGate({ enabled, installationId, children }) {
  const framed = window.top !== window.self;
  const [session, setSession] = useState(null), [ticket, setTicket] = useState(''), [busy, setBusy] = useState(true), [error, setError] = useState('');
  const lost = useCallback(() => setSession(null), []);
  const api = useMemo(() => createProtectedOperationsApi(installationId, lost), [installationId, lost]);
  useEffect(() => {
    let active = true; setSession(null); setTicket(''); setError(''); setBusy(true);
    if (!enabled || framed) { setBusy(false); return; }
    api.inspect().then(value => { if (active) setSession(value); }).catch(failure => { if (active && failure.status !== 401) setError(failure.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; api.forget(); };
  }, [api, enabled, framed]);
  useEffect(() => {
    if (!session) return;
    let timer;
    const expire = () => { api.forget(); setSession(null); setError('Owner session expired. Sign in again to recover the same operation.'); };
    const activity = () => { clearTimeout(timer); timer = setTimeout(expire, Math.max(0, Math.min(30 * 60 * 1000, session.expires_ms - Date.now()))); };
    const verify = () => { if (!document.hidden) api.inspect().then(setSession).catch(() => expire()); };
    activity(); window.addEventListener('pointerdown', activity); window.addEventListener('keydown', activity); window.addEventListener('focus', verify);
    return () => { clearTimeout(timer); window.removeEventListener('pointerdown', activity); window.removeEventListener('keydown', activity); window.removeEventListener('focus', verify); };
  }, [api, session]);
  if (!enabled) return <p>Protected operations are not enabled for this installation.</p>;
  if (framed) return <p>Open the HUD directly in a top-level browser window to use protected operations.</p>;
  const signIn = async event => {
    event.preventDefault(); if (busy) return;
    const submitted = ticket; setTicket(''); setBusy(true); setError('');
    try { setSession(await api.login(submitted)); } catch (failure) { setError(failure.message); } finally { setBusy(false); }
  };
  return <section className="protected-operations" aria-label="Owner-approved operations">
    {error && <p role="alert">{error}</p>}
    {session ? <><div className="owner-session"><p>Signed in as <strong>{session.principal.display_name}</strong> · {session.principal.subject}</p><button onClick={async () => { setError(''); try { await api.logout(); } catch (failure) { setError(failure.message); } }}>Sign out</button></div>{children({ api, session })}</> : <section className="panel"><h2>Owner sign-in</h2><p>Use the one-time ticket issued by the trusted administrator command on this installation.</p><form onSubmit={signIn}><label>One-time owner ticket<input type="password" name="owner-ticket" value={ticket} onChange={event => setTicket(event.target.value)} autoComplete="off" spellCheck="false" required disabled={busy}/></label><button className="primary" type="submit" disabled={busy || !ticket}>{busy ? 'Checking owner session…' : 'Sign in'}</button></form><p className="muted">A ticket expires after ten minutes. An existing chat session does not authorize an operation.</p></section>}
  </section>;
}
