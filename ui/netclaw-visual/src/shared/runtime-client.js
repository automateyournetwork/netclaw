let current = null;
export function workspaceFetch(url, options = {}) {
  if (current?.access?.mode !== 'open-lab') return globalThis.fetch(url, options);
  const headers = new Headers(options.headers || {});
  headers.delete('Authorization'); headers.delete('Cookie'); headers.delete('X-CSRF-Token');
  if (options.method && !['GET','HEAD'].includes(options.method)) headers.set('X-NetClaw-Installation', current.installationId);
  return globalThis.fetch(url, { ...options, credentials: 'omit', headers });
}
export async function ensureConversationContext() {
  if (current?.access?.mode === 'open-lab') {
    if (!current.capabilities?.remoteHud?.features?.includes('chat')) throw Error('Conversation workspace is unavailable.');
    await verifyRuntime(); return;
  }
  const response = await workspaceFetch('/api/hud/session', { method: 'POST', credentials: 'same-origin' });
  if (!response.ok) throw Error('HUD conversation storage is unavailable.');
}
export const runtimeInfo = () => current;
export async function bootstrapRuntime() {
  const response = await workspaceFetch('/api/runtime', { credentials:'omit', cache:'no-store', signal:AbortSignal.timeout(15000) });
  if (!response.ok) throw Error('Runtime selection is unavailable. Check the HUD server and reload.');
  const value = await response.json();
  if (!['openclaw','hermes'].includes(value.kind) || !/^[a-f0-9-]{36}$/.test(value.installationId)) throw Error('Runtime identity is unavailable.');
  current = Object.freeze(value);
  return current;
}
export const runtimeKey = key => current ? `netclaw.${current.kind}.${current.installationId}.${key}` : key;
export function runtimeStorage(storage) {
  if (!current) return storage; // Isolated unit previews; production bootstraps before importing applications.
  const identity = current.installationId, kind = current.kind;
  const keyFor = key => `netclaw.${kind}.${identity}.${key}`;
  return {
    getItem(key) {
      let raw = storage.getItem(keyFor(key));
      if (raw === null && kind === 'openclaw') {
        const claim = storage.getItem('netclaw.legacy-storage-owner');
        if (!claim || claim === identity) {
          const legacy = storage.getItem(key);
          if (legacy !== null) {
            storage.setItem('netclaw.legacy-storage-owner', identity);
            raw = JSON.stringify({ installationId:identity, value:legacy });
            storage.setItem(keyFor(key), raw); // Keep original as recovery backup.
          }
        }
      }
      if (raw === null) return null;
      const record = JSON.parse(raw);
      if (record.installationId !== identity || typeof record.value !== 'string') throw Error('Saved workspace belongs to another installation.');
      return record.value;
    },
    setItem(key,value) { storage.setItem(keyFor(key),JSON.stringify({ installationId:identity,value:String(value) })); },
    removeItem(key) { storage.removeItem(keyFor(key)); },
  };
}
export async function verifyRuntime() {
  if (!current) return bootstrapRuntime();
  const response=await workspaceFetch('/api/runtime',{cache:'no-store',signal:AbortSignal.timeout(15000)});
  const value=await response.json();
  if (!response.ok || value.installationId!==current.installationId || value.kind!==current.kind) throw Error('The selected runtime changed. Reload the HUD before sending or recovering work. Your saved conversation is preserved.');
  return current;
}
export async function newConversation(thread,{releaseCapacity=false}={}) {
  await verifyRuntime();
  const pending=pendingRequest(thread);
  const uncertain=pending && !['completed','failed','cancelled','interrupted'].includes(pending.state);
  if(releaseCapacity && (!uncertain || !pending.requestId || !pending.capacityReleaseEligible))throw Error('Check the owned unknown request status before releasing its slot.');
  const confirmation=releaseCapacity
    ? 'Review this request’s history and tool evidence first. Releasing its HUD admission slot does not cancel or undo it; its outcome stays unknown. It may still run alongside new work. Accept this risk, release its slot and start a new chat?'
    : 'The earlier request may have executed. Starting a new conversation does not cancel or undo it. Acknowledge and continue?';
  if (uncertain && !window.confirm(confirmation)) return null;
  const response=await workspaceFetch('/api/chat/conversations',{method:'POST',headers:{'Content-Type':'application/json','X-NetClaw-Installation':current.installationId},body:JSON.stringify(uncertain ? {acknowledgedUncertainRequestId:pending.requestId,...(releaseCapacity ? {releaseUncertainCapacity:true} : {})} : {})});
  if (!response.ok) throw Error('Check the unresolved request status before starting another conversation.');
  return response.json();
}
const store = () => runtimeStorage(window.sessionStorage);
export function pendingRequest(thread) { try { return JSON.parse(store().getItem('pending.'+thread) || 'null'); } catch { return null; } }
const remember = (thread,value) => store().setItem('pending.'+thread,JSON.stringify(value));
export function restoreOwnedRequest(thread,value) {
  if(!value || typeof value.requestId!=='string' || !/^[A-Za-z0-9_.:-]{1,128}$/.test(value.requestId))throw Error('Owned request identity unavailable.');
  const saved=pendingRequest(thread);
  const record={...(saved?.requestId===value.requestId ? saved : {}),requestId:value.requestId,state:value.state};
  remember(thread,record);return record;
}
const settled = new Set(['completed','failed','cancelled','interrupted','unknown']);
export async function observeRequest(thread, onProgress = () => {}) {
  await verifyRuntime();
  let record = pendingRequest(thread);
  if (!record) throw Error('No saved request is available. Open the owned conversation history.');
  if (!record.requestId) {
    const response=await workspaceFetch(`/api/chat/requests?hudThread=${encodeURIComponent(thread)}&nonce=${encodeURIComponent(record.nonce)}`,{cache:'no-store'});
    if (!response.ok) throw Error('Admission could not be confirmed. Nothing was resent. Check conversation history before starting a new chat.');
    const found=await response.json();
    record={...record,requestId:found.requestId}; remember(thread,record);
  }
  const deadline=Date.now()+15*60*1000;
  while (Date.now()<deadline) {
    const response=await workspaceFetch('/api/chat/requests/'+encodeURIComponent(record.requestId),{cache:'no-store',signal:AbortSignal.timeout(20000)});
    if (!response.ok) throw Error('Request status is unavailable. Nothing was resent; check its status again.');
    const value=await response.json();
    if(value.requestId && value.requestId!==record.requestId) throw Error('Request identity changed. Nothing was resent; open owned history.');
    // Status fields cannot replace the original locally recorded submission.
    record={...record,...value,requestId:record.requestId,nonce:record.nonce,submission:record.submission};
    remember(thread,record); onProgress(value);
    if (settled.has(value.state)) {
      if (value.state==='completed') {
        // Standard Chat needs a receipt across UI persistence/repeated recovery.
        // Canvas/classic retain their existing completion cleanup behavior.
        if (!record.submission?.anchor) store().removeItem('pending.'+thread);
        return {...value,requestId:record.requestId,submission:record.submission};
      }
      throw Error(value.state==='unknown' ? 'Outcome unknown. Do not resend this operation. Check history and status, or acknowledge the uncertainty before starting a new conversation.' : `Hermes request ${value.state}. Review its history and tool evidence before retrying.`);
    }
    await new Promise(resolve => setTimeout(resolve,750));
  }
  throw Error('Observation deadline reached. Hermes may still be running. Nothing will be resent.');
}
export async function sendChat(body,onProgress,recovery) {
  if(current) await verifyRuntime();
  const headers={'Content-Type':'application/json',...(current?{'X-NetClaw-Installation':current.installationId}:{})};
  if (current?.kind !== 'hermes') {
    const response=await workspaceFetch('/api/chat',{method:'POST',headers,body:JSON.stringify(body)});
    const value=await response.json(); if (!response.ok || !value.fromGateway) throw Error(value.error || value.gatewayIssue || 'The gateway did not return a confirmed reply.');
    return value;
  }
  if (pendingRequest(body.hudThread) && !['completed','failed','cancelled','interrupted'].includes(pendingRequest(body.hudThread).state)) throw Error('This conversation has an unresolved request. Check its status before submitting more work.');
  const nonce=crypto.randomUUID(), submission={prompt:body.message,nonce,...(recovery ? {anchor:recovery} : {})};
  remember(body.hudThread,{nonce,submission});
  const response=await workspaceFetch('/api/chat/requests',{method:'POST',headers,body:JSON.stringify({...body,clientNonce:nonce})});
  const value=await response.json();
  if (!response.ok) { store().removeItem('pending.'+body.hudThread); throw Error(value.error || 'Hermes rejected this request before admission.'); }
  remember(body.hudThread,{...value,nonce,submission}); onProgress?.(value);
  return observeRequest(body.hudThread,onProgress);
}
export async function requestControl(thread,action,body={}) {
  await verifyRuntime();
  const record=pendingRequest(thread);
  if (!record?.requestId) throw Error('Request identity is unavailable. Check status first.');
  const response=await workspaceFetch(`/api/chat/requests/${encodeURIComponent(record.requestId)}/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!response.ok) throw Error('The request control could not be applied. Check its current status.');
  return response.json();
}
