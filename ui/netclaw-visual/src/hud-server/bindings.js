import fs from 'node:fs';
import path from 'node:path';
import { createHash, randomBytes } from 'node:crypto';
import { writePrivateAtomic } from '../security/private-files.js';
const token = () => randomBytes(24).toString('hex');
const digest = value => createHash('sha256').update(value).digest('hex');
export const safeId = value => typeof value === 'string' && /^[a-zA-Z0-9_.:-]{1,128}$/.test(value);
export function readBounded(file, limit = 8 * 1024 * 1024) {
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try { const stat = fs.fstatSync(fd); if (!stat.isFile() || stat.size > limit) throw Error('Unavailable'); return fs.readFileSync(fd, 'utf8'); } finally { fs.closeSync(fd); }
}
// No browser-supplied path, session key or assessment ID creates ownership.
export class Bindings {
  constructor(directory, clock = Date.now, installation = null) { this.directory = directory; this.clock = clock; this.busy = new Set(); this.installation = installation; this.cookieName = installation ? 'nc_hud_' + installation.installationId.replaceAll('-','') : 'nc_hud'; }
  ensure() { fs.mkdirSync(this.directory, { recursive: true, mode: 0o700 }); const stat = fs.lstatSync(this.directory); if (!stat.isDirectory() || stat.isSymbolicLink() || stat.mode & 0o077) throw Error('Private binding directory required'); }
  file(cookie) { if (!/^[a-f0-9]{48}$/.test(cookie || '')) throw Error('Unauthenticated'); this.ensure(); return path.join(this.directory, `${digest(cookie)}.json`); }
  create() { this.ensure(); const cookie = token(); this.save(cookie, { version: this.installation ? 2 : 1, ...(this.installation ? { installationId: this.installation.installationId, runtime: this.installation.kind } : {}), expires: this.clock() + 30 * 86400000, tasks: {} }); return cookie; }
  read(cookie) {
    const file = this.file(cookie), state = JSON.parse(readBounded(file));
    if (state.expires <= this.clock()) throw Error('Unauthenticated');
    if (this.installation) {
      if (state.version === 1 && this.installation.kind === 'openclaw') {
        if (!fs.existsSync(file + '.v1-backup')) writePrivateAtomic(file + '.v1-backup', JSON.stringify(state));
        Object.assign(state, { version: 2, installationId: this.installation.installationId, runtime: 'openclaw' }); this.save(cookie, state);
      }
      if (state.version !== 2 || state.installationId !== this.installation.installationId || state.runtime !== this.installation.kind) throw Error('Unauthenticated');
    } else if (state.version !== 1) throw Error('Unauthenticated');
    return state;
  }
  save(cookie, state) { writePrivateAtomic(this.file(cookie), JSON.stringify(state)); }
  task(cookie, thread, agentId = 'main') {
    if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(agentId)) throw Error('Invalid agent');
    if (!safeId(thread)) throw Error('Invalid thread');
    const state = this.read(cookie); const key = digest(thread); let task = Object.values(state.tasks).find(t => (t.thread === key || (t.resumeThread && digest(t.resumeThread) === key)) && t.gatewayKey.startsWith(`agent:${agentId}:hud:`)); const newlyCreated = !task;
    if (!task) { if (Object.keys(state.tasks).length >= 500) throw Error('Session task limit reached'); const id = token(); task = { id, thread: key, publicThread: thread, createdAt: this.clock(), gatewayKey: `agent:${agentId}:hud:${id}`, assessments: {} }; state.tasks[id] = task; this.save(cookie, state); }
    return { ...task, newlyCreated };
  }
  lookupTask(cookie, thread, agentId) {
    if (!safeId(thread) || !/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(agentId)) throw Error('Invalid chat');
    const key = digest(thread);
    return Object.values(this.read(cookie).tasks).find(t => (t.thread === key || (t.resumeThread && digest(t.resumeThread) === key)) && t.gatewayKey.startsWith(`agent:${agentId}:hud:`)) || null;
  }
  chats(cookie, agentId) {
    if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(agentId)) throw Error('Invalid agent');
    return Object.values(this.read(cookie).tasks).filter(t => t.gatewayKey.startsWith(`agent:${agentId}:hud:`));
  }
  ownedChat(cookie, id, agentId) {
    if (!safeId(id)) throw Error('Unavailable');
    const task = this.chats(cookie, agentId).find(t => t.id === id);
    if (!task) throw Error('Unavailable');
    return task;
  }
  resumeChat(cookie, id, agentId) {
    this.ownedChat(cookie, id, agentId);
    const state = this.read(cookie), task = state.tasks[id];
    if (!task.publicThread && !task.resumeThread) { task.resumeThread = `chat-${token()}`; this.save(cookie, state); }
    return { ...task, publicThread: task.publicThread || task.resumeThread };
  }
  describeChat(cookie, id, agentId, metadata) {
    this.ownedChat(cookie, id, agentId);
    const state = this.read(cookie), task = state.tasks[id];
    task.title ||= String(metadata.title || 'Chat').replace(/\s+/g, ' ').slice(0, 100);
    task.updatedAt = this.clock();
    if (typeof metadata.chatModel === 'string' && metadata.chatModel.length <= 128) task.chatModel = metadata.chatModel;
    if (['','off','minimal','low','medium','high','xhigh','max','ultra'].includes(metadata.chatEffort)) task.chatEffort = metadata.chatEffort;
    this.save(cookie, state);
  }
  begin(cookie, taskId) { const key = digest(cookie) + taskId; if (this.busy.has(key)) throw Error('Thread has an active request'); this.busy.add(key); return () => this.busy.delete(key); }
  request(cookie, taskId, nonce, bodyDigest) {
    if (!safeId(nonce)) throw Error('Invalid nonce');
    const state = this.read(cookie), task = state.tasks[taskId]; if (!task) throw Error('Unavailable');
    task.requests ||= {};
    const existing = Object.values(task.requests).find(r => r.nonce === nonce);
    if (existing) { if (existing.bodyDigest !== bodyDigest) throw Error('Nonce conflict'); return existing; }
    if (Object.keys(task.requests).length >= 500) throw Error('Request limit reached');
    const request = { id: token(), nonce, bodyDigest, state:'submitting', createdAt: this.clock() };
    task.requests[request.id] = request; this.save(cookie, state); return request;
  }
  ownedRequest(cookie, requestId) {
    if (!safeId(requestId)) throw Error('Unavailable');
    for (const task of Object.values(this.read(cookie).tasks)) if (task.requests?.[requestId]) return { task, request: task.requests[requestId] };
    throw Error('Unavailable');
  }
  requestState(cookie, requestId, outcome) {
    const {task}=this.ownedRequest(cookie,requestId), state=this.read(cookie);
    state.tasks[task.id].requests[requestId].state=outcome;this.save(cookie,state);
  }
  requireAcknowledgment(cookie, taskId, acknowledgment) {
    const state=this.read(cookie);
    const uncertain=Object.values(state.tasks).filter(t=>t.id!==taskId).flatMap(t=>Object.values(t.requests || {})).filter(r=>['unknown','submitting'].includes(r.state));
    if(uncertain.some(r=>r.id!==acknowledgment && !state.acknowledged?.includes(r.id)))throw Error('Acknowledge unresolved request before opening another conversation.');
    if(acknowledgment) this.ownedRequest(cookie,acknowledgment);
  }
  acknowledge(cookie, requestId) {
    if (!requestId) return;
    this.ownedRequest(cookie,requestId);
    const state=this.read(cookie);
    state.acknowledged=[...new Set([...(state.acknowledged || []),requestId])].slice(-500);
    this.save(cookie,state);
  }
  register(cookie, taskId, refs, messageRef) {
    const state = this.read(cookie), task = state.tasks[taskId]; if (!task) throw Error('Unavailable');
    for (const ref of refs.slice(0, 64)) {
      if (Object.keys(task.assessments).length >= 500) break;
      if (!safeId(ref.assessmentId) || typeof ref.ledgerTask !== 'string' || !/^[A-Za-z0-9_.:/-]{1,128}$/.test(ref.ledgerTask)) continue;
      if (task.assessments[ref.assessmentId]) continue;
      if (ref.parent && Object.values(task.assessments).some(a => a.parent === ref.parent)) continue;
      task.assessments[ref.assessmentId] = { ...ref, messageRef };
    }
    this.save(cookie, state);
    return refs.filter(r => task.assessments[r.assessmentId]?.messageRef === messageRef).map(r => ({ taskRef: taskId, assessmentId: r.assessmentId, messageRef }));
  }
  authorize(cookie, taskId, assessmentId) { const state = this.read(cookie); const task = state.tasks[taskId]; const ref = task?.assessments?.[assessmentId]; if (!ref) throw Error('Unavailable'); return { task, ref }; }
  revoke(cookie) { const state = this.read(cookie); state.expires = 0; state.tasks = {}; this.save(cookie, state); }
}
export function cookieFrom(req) { return (req.headers.cookie || '').split(';').map(s => s.trim()).find(s => s.startsWith('nc_hud='))?.slice(7); }
export const newMessageRef = token;

export function readTranscript(directory, gatewayKey) {
  try {
    const sessions = JSON.parse(readBounded(path.join(directory, 'sessions.json')));
    const session = sessions[gatewayKey];
    if (!safeId(session?.sessionId)) return null;
    // Resolve ONLY the runtime's session-id mapping; ignore sessionFile paths.
    const lines = readBounded(path.join(directory, session.sessionId + '.jsonl')).split('\n');
    return lines.filter(Boolean).map(line => JSON.parse(line));
  } catch { return null; }
}
const jevTool = name => typeof name === 'string' && /(?:^|__)jev_evaluate$/.test(name);
export function assessmentProofs(before, after) {
  if (!Array.isArray(before) || !Array.isArray(after)) return [];
  const prior = new Set(before.map(e => e.id).filter(Boolean));
  const calls = new Map(), refs = [];
  for (const event of after) {
    if (!event.id || prior.has(event.id) || event.type !== 'message') continue;
    const msg = event.message;
    if (msg?.role === 'assistant') for (const block of Array.isArray(msg.content) ? msg.content : []) {
      if (block.type === 'toolCall' && jevTool(block.name) && safeId(block.id)) calls.set(block.id, block.name);
    }
    if (!['toolResult', 'tool'].includes(msg?.role) || !calls.has(msg.toolCallId) || !jevTool(msg.toolName)) continue;
    // Trust runtime tool-result envelopes, never assistant prose or quoted JSON.
    for (const block of Array.isArray(msg.content) ? msg.content : []) {
      if (block.type !== 'text') continue;
      try {
        const result = JSON.parse(block.text);
        const value = result.structuredContent?.result || result.structuredContent || result;
        if (!safeId(value.assessment_id) || typeof value.task_id !== 'string' || !['ok','timeout','unavailable','incompatible_provider','usage_bound_exceeded'].includes(value.status)) continue;
        refs.push({ assessmentId: value.assessment_id, ledgerTask: value.task_id, toolEventId: event.id, parent: value.reconsideration_of || null });
      } catch { /* unsupported runtime envelope is unbound */ }
    }
  }
  return refs;
}

// Keep detail to fields needed for typed evidence. Endpoint/provider credentials
// and arbitrary ledger extras cannot cross this boundary.
export function projectAssessment(record) {
  if (!record || !safeId(record.assessment_id)) throw Error('Unavailable');
  const fields = ['assessment_id','status','purpose','model','provider','created_at','questions','answers','evidence_metadata','request_digest','state_digest','usage','cost_usd','reserved_cost_usd','charge_status','reconsideration_of'];
  return Object.fromEntries(fields.filter(key => record[key] !== undefined).map(key => [key, record[key]]));
}

// This is Border-authored interpretation, never authority or evidence proof.
export function influenceBlocks(content) {
  const values = [];
  for (const match of String(content).matchAll(/```jev-influence\s*\n([\s\S]*?)```/g)) {
    try { const value = JSON.parse(match[1]); if (safeId(value.assessment_id) && ['supported','challenged','changed','unavailable'].includes(value.status) && typeof value.explanation === 'string' && value.explanation.length <= 4000) values.push(value); } catch { /* absent interpretation */ }
  }
  return values;
}
export function attachInfluences(proofs, before, after) {
  if (!Array.isArray(before) || !Array.isArray(after)) return proofs;
  const previous = new Set(before.map(e => e.id));
  const found = new Map();
  for (const event of after) {
    if (!event.id || previous.has(event.id) || event.message?.role !== 'assistant') continue;
    for (const block of Array.isArray(event.message.content) ? event.message.content : []) {
      if (block.type !== 'text') continue;
      for (const value of influenceBlocks(block.text)) found.set(value.assessment_id, { status: value.status, explanation: value.explanation, source_message: event.id });
    }
  }
  return proofs.map(proof => found.has(proof.assessmentId) ? { ...proof, influence: found.get(proof.assessmentId) } : proof);
}
export function displayBorderText(content) {
  return String(content).replace(/```jev-influence\s*\n([\s\S]*?)```/g, (full) => {
    const value = influenceBlocks(full)[0];
    return value ? `Jev ${value.status} Border's recommendation: ${value.explanation}` : full;
  });
}
