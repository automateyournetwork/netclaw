import { workspaceFetch as fetch } from '../shared/runtime-client.js';
import React, { useEffect, useState } from 'react';
const count = n => typeof n === 'number' ? n.toLocaleString() : 'Not reported';
const when = n => typeof n === 'number' && n > 0 ? new Date(n).toLocaleString() : 'Not reported';

export default function ChatUsage({ thread, model, revision, active, preview }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    setData(null);
    if (!active || preview) return;
    const controller = new AbortController();
    let busy = false;
    const load = async () => {
      if (busy || document.hidden) return;
      busy = true;
      try {
        const response = await fetch('/api/chat/usage', {
          method: 'POST', credentials: 'same-origin', cache: 'no-store',
          headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
          body: JSON.stringify({ hudThread: thread, chatModel: model }),
        });
        if (!response.ok) throw Error();
        const value = await response.json();
        if (!controller.signal.aborted) { setData(value); setError(''); }
      } catch {
        if (!controller.signal.aborted) { setError('Usage refresh failed.'); setData(null); }
      } finally { busy = false; }
    };
    load();
    const interval = setInterval(load, 30000);
    document.addEventListener('visibilitychange', load);
    return () => { controller.abort(); clearInterval(interval); document.removeEventListener('visibilitychange', load); };
  }, [thread, model, revision, active, preview, refresh]);
  const context = data?.context, quota = data?.quota;
  const known = context?.available && !context?.stale;
  const remaining = quota?.available && !quota?.stale
    ? Math.min(...quota.windows.map(window => window.remainingPercent)) : null;
  return <details className="chat-usage">
    <summary aria-label="Context window and account usage">
      <span className="chat-context-ring" aria-hidden="true" style={{ '--used': `${known ? Math.min(100, context.percentUsed) : 0}%` }}/>
      <span>{known ? `${Math.round(context.percentUsed)}% context` : 'Context —'}</span>
      <span className="chat-quota-summary">{remaining !== null ? `${Math.round(remaining)}% quota left` : 'Limits —'}</span>
    </summary>
    <div className="chat-usage-panel">
      <strong>Context window</strong>
      <p>{known ? `${count(context.used)} / ${count(context.capacity)} tokens (${Math.round(context.percentUsed)}% used)` : context?.reason || 'No current context report.'}</p>
      {context?.stale && <p>Context refresh failed; the previous snapshot is stale.</p>}
      <small>Last reported session context, including runtime instructions and tools when reported. Draft text is not included.</small>
      <p className="chat-usage-time">Context updated: {when(context?.updatedAt)}</p>
      <strong>Provider/account quotas{quota?.provider ? ` · ${quota.provider}` : ''}</strong>
      {quota?.windows?.map((window, index) => <div key={index} className="chat-quota-window">
        <span>{window.label}: {Math.round(window.remainingPercent)}% remaining{quota.stale ? ' (stale)' : ''}</span>
        <progress aria-label={`${window.label} quota remaining`} max="100" value={window.remainingPercent}/>
        <small>Resets: {when(window.resetAt)}</small>
      </div>)}
      {!quota?.available && <p>{quota?.reason || 'Quota data not available yet.'}</p>}
      {quota?.stale && <p>Quota refresh failed. Previous values may be out of date.</p>}
      <p className="chat-usage-time">Provider snapshot: {when(quota?.updatedAt)}</p>
      <small>Provider limits are shared across account activity. Reports are cached for up to five minutes.</small>
      {error && <p role="status">{error}</p>}
      <button type="button" onClick={() => setRefresh(value => value + 1)} disabled={preview}>Refresh usage</button>
    </div>
  </details>;
}
