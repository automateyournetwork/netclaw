import { runtimeInfo, runtimeStorage, sendChat, observeRequest, pendingRequest, newConversation, requestControl } from '../shared/runtime-client.js';
import { loadChat, saveChat, loadChatArchive, archiveChat } from './chat-storage.js';
import ChatUsage from './ChatUsage.jsx';
import { randomId } from '../shared/random-id.js';
import React, { lazy, Suspense, useEffect, useRef, useState } from 'react';
const LocalPal = lazy(() => import('./LocalPal.jsx'));

const validId = value => typeof value === 'string' && /^[a-zA-Z0-9_.:-]{1,128}$/.test(value);
const makeThread = () => `chat-${randomId()}`;
const demoMessages = [
  { role: 'user', content: 'How should I start investigating an intermittent routing issue?' },
  { role: 'assistant', content: 'Synthetic example — no tools were run.\n\nStart by recording the affected path, timestamps and symptoms. Compare current routing and interface observations with the intended design before proposing a change.' },
];
export default function StandardChat({ preview = false, active = true, pal = false }) {
  const selectedRuntime = runtimeInfo();
  const [requestState, setRequestState] = useState(null);
  const [palReply, setPalReply] = useState(null);
  const palVoice = useRef(null);
  const [restored] = useState(() => {
    if (preview) return { state: null, error: '' };
    try { return loadChat(runtimeStorage(window.sessionStorage)); }
    catch { return { state: null, error: 'Browser storage is unavailable; this chat cannot survive refresh.' }; }
  });
  const [savedChats, setSavedChats] = useState(() => { try { return preview ? [] : loadChatArchive(runtimeStorage(window.sessionStorage)); } catch { return []; } });
  const [conversations, setConversations] = useState([]);
  const [historyError, setHistoryError] = useState('');
  const [loadingChat, setLoadingChat] = useState(false);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [openedChat, setOpenedChat] = useState('');
  const [remoteActive, setRemoteActive] = useState(false);
  const [storageError, setStorageError] = useState(restored.error);
  const [uncertain, setUncertain] = useState(restored.state?.interrupted === true);
  const [chatModel, setChatModel] = useState(restored.state?.chatModel || '');
  const [chatEffort, setChatEffort] = useState(restored.state?.chatEffort || '');
  const [catalog, setCatalog] = useState(null);
  const [modelError, setModelError] = useState('');
  const [modelRefresh, setModelRefresh] = useState(0);
  useEffect(() => {
    if (preview) return;
    const controller = new AbortController();
    setModelError('');
    fetch('/api/chat/models', { signal: controller.signal, cache: 'no-store' })
      .then(async response => { if (!response.ok) throw Error(); return response.json(); })
      .then(data => { if (!Array.isArray(data.models)) throw Error(); setCatalog(data); })
      .catch(() => { if (!controller.signal.aborted) setModelError('Model list unavailable. The agent default is still available.'); });
    return () => controller.abort();
  }, [preview, modelRefresh]);
  const [messages, setMessages] = useState(() => preview ? demoMessages : restored.state?.messages || []);
  const [draft, setDraft] = useState(restored.state?.draft || ''), [pending, setPending] = useState(false);
  const [error, setError] = useState(restored.state?.interrupted
    ? 'This page was refreshed while a reply was pending. Your draft is restored, but the request may have run. Check its outcome before retrying; nothing was resent.' : '');
  const inFlight = useRef(null);
  const thread = useRef(restored.state?.thread || null), sending = useRef(false), composer = useRef(null), transcript = useRef(null);
  if (thread.current === null) thread.current = makeThread();
  const persist = snapshot => {
    if (preview) return;
    try {
      const value = { thread: thread.current, chatModel, chatEffort, ...snapshot };
      const error = saveChat(runtimeStorage(window.sessionStorage), value);
      setStorageError(error);
      if (error) return false;
      setSavedChats(archiveChat(runtimeStorage(window.sessionStorage), value));
      return true;
    }
    catch { setStorageError('Saved-chat storage is unavailable or full. Recent drafts may not survive switching chats.'); return false; }
  };
  useEffect(() => {
    persist(pending && inFlight.current
      ? { messages: inFlight.current.before, draft: inFlight.current.prompt, interrupted: true }
      : { messages, draft, interrupted: uncertain });
  }, [messages, draft, chatModel, chatEffort, pending, preview, uncertain]);
  useEffect(() => { if (active && transcript.current) transcript.current.scrollTop = transcript.current.scrollHeight; }, [messages, pending, active]);
  const refreshChats = async () => {
    if (preview || historyBusy) return;
    setHistoryBusy(true); setHistoryError('');
    try {
      const session = await fetch('/api/hud/session', { method: 'POST', credentials: 'same-origin' });
      if (!session.ok) throw Error();
      const response = await fetch('/api/chat/conversations', { cache: 'no-store' });
      if (!response.ok) throw Error();
      const data = await response.json();
      if (!Array.isArray(data.conversations)) throw Error();
      setConversations(data.conversations);
      setOpenedChat(current => data.conversations.find(chat => chat.thread === thread.current)?.id || current);
      if (!data.sourceAvailable) setHistoryError('Gateway history is unavailable. Saved chat entries are still listed.');
    } catch { setHistoryError('Previous chats could not be refreshed. Your current conversation is unchanged.'); }
    finally { setHistoryBusy(false); }
  };
  useEffect(() => { if (active && !preview) refreshChats(); }, [active, preview]);
  const openChat = async value => {
    if (!value || sending.current || preview || loadingChat) return;
    if (!persist({ messages, draft, interrupted: uncertain })) return;
    sending.current = true; setLoadingChat(true); setHistoryError('');
    try {
      let target;
      if (value.startsWith('local:')) {
        target = savedChats.find(chat => chat.thread === value.slice(6));
        if (!target) throw Error();
      } else {
        const response = await fetch(`/api/chat/conversations/${encodeURIComponent(value)}/open`, { method: 'POST', cache: 'no-store' });
        if (!response.ok) throw Error();
        target = await response.json();
        if (!validId(target.thread) || !Array.isArray(target.messages)) throw Error();
        const local = savedChats.find(chat => chat.thread === target.thread);
        target = { ...target, draft: local?.draft || '', interrupted: target.active === true || local?.interrupted || false };
      }
      thread.current = target.thread; setMessages(target.messages); setDraft(target.draft || '');
      setPalReply(null);
      setChatModel(target.chatModel || ''); setChatEffort(target.chatEffort || '');
      setUncertain(target.interrupted === true); setRemoteActive(target.active === true); setOpenedChat(value);
      setError(target.active ? 'This chat is still running in the selected runtime. Reload it to receive the latest saved messages before sending again.' : target.interrupted ? 'An earlier request may have run. Review the saved replies before retrying the restored draft; nothing was resent.' : '');
      if (target.truncated) setHistoryError('Showing the most recent saved transcript. Earlier context remains in the gateway session.');
      persist({ ...target, interrupted: target.interrupted === true });
    } catch { setHistoryError('The saved chat could not be loaded. Your current conversation has been kept.'); }
    finally { sending.current = false; setLoadingChat(false); }
  };
  const send = async event => {
    event.preventDefault();
    const prompt = draft.trim();
    if (!prompt || sending.current || preview || loadingChat || remoteActive) return;
    if (pal) palVoice.current?.prepareForReply();
    sending.current = true; setPending(true); setError('');
    const before = messages, context = [...messages, { role: 'user', content: prompt }];
    inFlight.current = { before, prompt }; setUncertain(true);
    persist({ messages: before, draft: prompt, interrupted: true });
    setMessages(context); setDraft('');
    try {
      const session = await fetch('/api/hud/session', { method: 'POST', credentials: 'same-origin', cache: 'no-store' });
      if (!session.ok) throw Error('The private HUD session is unavailable. Your draft has been restored.');
      const data = await sendChat({ message: prompt, messages: context.slice(-40).map(({role,content}) => ({role,content})), hudThread: thread.current, chatModel, chatEffort }, setRequestState);
      if (data.fromGateway !== true) throw Error((typeof data.gatewayIssue === 'string' ? data.gatewayIssue : 'The gateway did not return a confirmed reply.') + ' Your draft has been restored.');
      if (typeof data.response !== 'string' || !data.response.trim()) throw Error('The gateway returned an empty reply. Check the gateway before retrying; your draft has been restored.');
      const assessmentRefs = (Array.isArray(data.assessmentRefs) ? data.assessmentRefs : [])
        .filter(ref => validId(ref?.taskRef) && validId(ref?.assessmentId)).slice(0, 20);
      setUncertain(false);
      const completed = [...context, { role: 'assistant', content: data.response, assessmentRefs }];
      persist({ messages: completed, draft: '', interrupted: false });
      setMessages(completed);
      setPalReply({ id: randomId(), text: data.response });
    } catch (err) {
      setMessages(before); setDraft(prompt);
      setError(err instanceof TypeError || err instanceof SyntaxError ? 'The reply could not be received. Your draft has been restored. The gateway may still be working; check before retrying.' : err.message || 'Chat unavailable. Your draft has been restored.');
    } finally { sending.current = false; setPending(false); refreshChats(); }
  };
  const recover = async () => {
    if (sending.current) return;
    sending.current=true; setPending(true); setError('');
    try { const data=await observeRequest(thread.current,setRequestState); const completed=[...messages,{role:'user',content:draft},{role:'assistant',content:data.response || data.output}]; setMessages(completed); setDraft(''); setUncertain(false); persist({messages:completed,draft:'',interrupted:false}); }
    catch (error) { setError(error.message); }
    finally { sending.current=false; setPending(false); }
  };
  const control = async (action,body) => { try { setRequestState(await requestControl(thread.current,action,body)); } catch (error) { setError(error.message); } };
  const reset = async () => {
    if (sending.current || preview) return;
    if (!persist({ messages, draft, interrupted: uncertain })) return;
    let nextThread = makeThread();
    const unresolved = pendingRequest(thread.current);
    if (selectedRuntime?.kind === 'hermes' && unresolved) {
      try { const conversation=await newConversation(thread.current); if(!conversation)return; nextThread=conversation.thread; }
      catch(error) { setError(error.message); return; }
    }
    thread.current = nextThread; setOpenedChat(''); setRemoteActive(false); setUncertain(false);
    setPalReply(null);
    persist({ messages: [], draft: '', interrupted: false }); setMessages([]); setDraft(''); setError('');
    refreshChats(); composer.current?.focus();
  };
  const selected = catalog?.models?.find(model => chatModel ? model.id === chatModel : model.label === catalog.defaultModel);
  const efforts = selected?.efforts || [];
  const effectiveEffort = chatEffort || selected?.defaultEffort;
  const effortIndex = efforts.indexOf(effectiveEffort);
  const latestReply = messages.findLast(message => message.role === 'assistant')?.content || '';
  return <div className={pal ? 'pal-conversation-layout' : undefined}>{pal && <Suspense fallback={<p role="status">Loading your local Pal…</p>}><LocalPal ref={palVoice} active={active} preview={preview} thinking={pending} reply={palReply} latestReply={latestReply} conversationId={thread.current}/></Suspense>}
  <section className="standard-chat" aria-label="Standard Chat">
    {selectedRuntime && <p role="status">{selectedRuntime.label} · {selectedRuntime.readiness.ready ? 'API ready' : 'API unavailable'}{selectedRuntime.kind === 'hermes' ? ' · Qualified read-only tools · Configured model' : ''}</p>}
    {selectedRuntime?.kind === 'hermes' && (requestState || uncertain) && <div role="status">
      <span>{requestState?.state || 'Unresolved request'}{requestState?.runtime?.model ? ` · ${requestState.runtime.provider || 'Hermes'} / ${requestState.runtime.model}` : ''}</span>
      <button onClick={recover} disabled={pending}>Check status</button>
      <button onClick={()=>control('stop')}>Request stop</button>
      {requestState?.approval && <><p>{requestState.approval.description || 'Pending tool approval'}</p><button onClick={()=>control('approval',{approvalId:requestState.approval.id || requestState.approval.request_id,choice:'once'})}>Allow once</button><button onClick={()=>control('approval',{approvalId:requestState.approval.id || requestState.approval.request_id,choice:'deny'})}>Deny</button></>}
    </div>}
    <div className="chat-intro"><div><span className="eyebrow">Your network engineering coworker</span><h2>A conversation with NetClaw</h2><p>Ask a question, review the evidence, then follow up.</p></div><button onClick={reset} disabled={pending || loadingChat || preview}>New chat</button></div>
    <div className="chat-history-controls">
      <label htmlFor="previous-chat">Previous chats</label>
      <select id="previous-chat" value={openedChat} disabled={pending || loadingChat || preview} onChange={event => openChat(event.target.value)}>
        <option value="">Choose a previous chat…</option>
        {conversations.map(chat => <option key={chat.id} value={chat.id}>{chat.title}{chat.updatedAt ? ` · ${new Date(chat.updatedAt).toLocaleString()}` : ''}{chat.active ? ' · Running' : ''}</option>)}
        {savedChats.filter(chat => !conversations.some(remote => remote.thread === chat.thread)).map(chat => <option key={chat.thread} value={`local:${chat.thread}`}>{(chat.messages.find(m => m.role === 'user')?.content || chat.draft || 'Saved chat').slice(0, 70)} · Saved in this tab</option>)}
      </select>
      <button type="button" disabled={historyBusy || loadingChat || pending || preview} onClick={refreshChats}>Refresh chats</button>
      {openedChat && <button type="button" disabled={pending || loadingChat || preview} onClick={() => openChat(openedChat)}>Reload chat</button>}
      {loadingChat && <span role="status">Loading conversation…</span>}
    </div>
    {historyError && <div className="chat-error" role="status">{historyError}</div>}
    <div className="chat-transcript" ref={transcript} role="log" aria-label="Chat conversation" aria-live="polite" aria-relevant="additions" aria-busy={pending}>
      {!messages.length && <div className="chat-empty"><span className="chat-monogram" aria-hidden="true">N›</span><h3>What would you like to investigate?</h3><p>Try asking about network health, a routing issue, or one of your uploaded design guides.</p><small>Requests use your configured gateway and existing approval rules.</small></div>}
      {messages.map((message, index) => <article className={`chat-message ${message.role}`} key={index}><span className="chat-author">{message.role === 'user' ? 'You' : preview ? 'NetClaw · synthetic preview' : 'NetClaw'}</span><div className="chat-message-text">{message.content}</div>{message.assessmentRefs?.map(ref => <a key={`${ref.taskRef}:${ref.assessmentId}`} className="utility-link" href={`/assessment.html?task=${encodeURIComponent(ref.taskRef)}&assessment=${encodeURIComponent(ref.assessmentId)}`} target="_blank" rel="noopener noreferrer">Open Jev assessment ↗</a>)}</article>)}
      {pending && <p className="chat-working" role="status">NetClaw is working… Tool-based investigations can take several minutes.</p>}
    </div>
    {storageError && <div className="chat-error" role="status">{storageError}</div>}
    {error && <div className="chat-error" role="alert">{error}</div>}
    <form className="chat-composer" onSubmit={send}>
      <label className="sr-only" htmlFor="standard-chat-message">Message NetClaw</label>
      <div className="chat-compose-row">
        <textarea id="standard-chat-message" ref={composer} value={draft} onChange={event => setDraft(event.target.value)} placeholder={preview ? 'Synthetic preview — sending is disabled' : 'Ask NetClaw…'} rows={3} maxLength={20000} disabled={pending || loadingChat || preview} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) send(event); }}/>
        <div className="chat-composer-toolbar">
          <ChatUsage thread={thread.current} model={chatModel} revision={`${messages.length}:${pending}`} active={active} preview={preview}/>
          <div className="chat-model-control">
            <label className="sr-only" htmlFor="standard-chat-model">Model</label>
        <select id="standard-chat-model" value={chatModel} disabled={pending || loadingChat || preview || catalog?.selectionSupported === false} onChange={event => { setChatModel(event.target.value); setChatEffort(''); }}>
          <option value="">Agent default{catalog?.defaultModel ? ` · ${catalog.defaultModel}` : ''}</option>
          {(catalog?.models || []).map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
          {chatModel && !catalog?.models?.some(model => model.id === chatModel) && <option value={chatModel}>Previously selected model (unavailable)</option>}
        </select>
            <button type="button" className="chat-model-refresh" aria-label="Refresh models" title="Refresh models" disabled={pending || loadingChat || preview} onClick={() => setModelRefresh(value => value + 1)}>↻</button>
          </div>
          <details className="chat-effort-control">
            <summary>Effort · {chatEffort || (selected?.defaultEffort ? `Default (${selected.defaultEffort})` : 'Default')}</summary>
            <div className="chat-effort-panel">
              <label htmlFor="standard-chat-effort">Reasoning effort: {effectiveEffort || 'Default'}</label>
              {efforts.length > 0 ? <>
                <input id="standard-chat-effort" type="range" min="0" max={efforts.length - 1} step="1"
                  value={Math.max(0, effortIndex)} aria-valuetext={effectiveEffort || 'Default'}
                  disabled={pending || loadingChat || preview} onChange={event => setChatEffort(efforts[Number(event.target.value)])}/>
                <div className="chat-effort-scale"><span>Lighter · {efforts[0]}</span><span>Deeper · {efforts.at(-1)}</span></div>
                {chatEffort && effortIndex < 0 && <p role="alert">Saved effort is unavailable for this model. Choose again.</p>}
              </> : <p>Supported effort levels are unavailable for this model.</p>}
              <p>Higher effort can take longer and use more tokens. Account pricing is not reported.</p>
              <button type="button" disabled={pending || loadingChat || preview} onClick={() => setChatEffort('')}>Use default effort</button>
            </div>
          </details>
          <button className="primary chat-send" type="submit" aria-label={pending ? 'Working…' : 'Send message'} title={pending ? 'Working…' : 'Send message'} disabled={pending || loadingChat || remoteActive || preview || !draft.trim()}>{pending ? '…' : '↑'}</button>
        </div>
      </div>
      {catalog?.discoveryAvailable === false && <p className="chat-model-error" role="status">Runtime model discovery is unavailable. Showing configured models only.</p>}
      {modelError && <p className="chat-model-error" role="status">{modelError}</p>}
      <p className="chat-footnote">Enter to send · Shift+Enter for a new line. Conversation and draft are saved in this browser tab across refresh. Previous chats reopens saved conversations. New chat keeps your history. Gateway records follow runtime retention. The latest 40 messages are sent as context.</p>
    </form>
  </section></div>;
}
