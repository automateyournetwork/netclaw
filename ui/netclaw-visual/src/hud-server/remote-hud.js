import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { boundedFile, noSymlink } from './protected-assets.js';
import { strictJson } from './protected-client.js';

export const REMOTE_HUD_FEATURES = Object.freeze(['overview', 'chat', 'canvas', 'rag', 'members', 'peers', 'skills', 'runtime', 'tokenomics', 'documentation', 'reference', 'logs', 'operations']);
const exact = (v, keys) => v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
const ID = '[A-Za-z0-9_.:-]{1,128}';
export function remoteHudFeatures(value) {
  if (!Array.isArray(value) || !value.length || new Set(value).size !== value.length || value.some(v => !REMOTE_HUD_FEATURES.includes(v)) || value.includes('canvas') && !value.includes('chat')) throw Error('invalid_workspace_features');
  return Object.freeze([...value]);
}
export function readRemoteHudConfig(file, installation, expectedSha256, { backend = false, ordinary = false } = {}) {
  const raw = boundedFile(file, 65536, true);
  if (expectedSha256 !== undefined && (!/^[a-f0-9]{64}$/.test(expectedSha256) || crypto.createHash('sha256').update(raw).digest('hex') !== expectedSha256)) throw Error('workspace_config_changed');
  const value = strictJson(raw.toString('utf8'));
  if (!exact(value, ['schemaVersion', 'installationId', 'upstream', 'conversationHome', 'conversationConfig', 'features', ...(ordinary ? ['mode'] : [])]) || ordinary && value.mode !== 'ordinary-federation' || value.schemaVersion !== 1 || value.installationId !== installation.installationId || !/^http:\/\/127\.0\.0\.1:[1-9][0-9]{0,4}$/.test(value.upstream) || new URL(value.upstream).port > 65535) throw Error('invalid_workspace_config');
  for (const name of ['conversationHome', 'conversationConfig']) if (typeof value[name] !== 'string' || !path.isAbsolute(value[name]) || path.normalize(value[name]) !== value[name]) throw Error('invalid_conversation_root');
  if ((!backend && value.conversationHome === installation.home) || path.dirname(value.conversationConfig) !== value.conversationHome) throw Error('invalid_conversation_root');
  // The edge must not gain filesystem access to the conversation UID's home.
  // The backend validates its own files; the edge verifies its bound HTTP ID.
  if (backend) {
    for (const name of ['conversationHome', 'conversationConfig']) noSymlink(value[name]);
    if (!fs.statSync(value.conversationHome).isDirectory()) throw Error('invalid_conversation_root');
    boundedFile(value.conversationConfig, 1024 * 1024, true);
  }
  if (!backend && !ordinary) {
  const profile = strictJson(boundedFile(path.join(installation.home, 'netclaw-federation/protected-profile.json'), 65536, true).toString('utf8'));
  if (profile.role !== 'border' || profile.identity?.installation_id !== installation.installationId || !exact(profile.access, ['mode']) || profile.access.mode !== 'open-lab') throw Error('workspace_requires_open_lab');
  }
  return Object.freeze({ ...value, features: remoteHudFeatures(value.features) });
}

// A normal HUD service is a component of the existing Border installation,
// not another enrolled claw. Its private binding projects only the public ID;
// it never reads or copies the Border's signing keys, profile or authority DB.
export function resolveRemoteHudBackend(file) {
  const value = strictJson(boundedFile(file, 65536, true).toString('utf8'));
  if (!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value.installationId || '')) throw Error('invalid_workspace_identity');
  const installation = Object.freeze({ kind: 'openclaw', installationId: value.installationId, home: value.conversationHome,
    configPath: value.conversationConfig, envPath: path.join(value.conversationHome, '.env'), statePath: path.join(value.conversationHome, 'netclaw-hud'),
    workspacePath: path.join(value.conversationHome, 'workspace'), skillsPath: path.join(value.conversationHome, 'workspace/skills'), serviceBinding: true });
  const workspace = readRemoteHudConfig(file, installation, undefined, { backend: true, ordinary: value.mode === 'ordinary-federation' });
  if (workspace.mode === 'ordinary-federation') {
    for (const marker of ['protected-profile.json', 'protected-role.json']) {
      try { fs.lstatSync(path.join(installation.home, 'netclaw-federation', marker)); throw Error('ordinary_workspace_has_protected_profile'); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
    }
  }
  const home = fs.lstatSync(installation.home);
  if (home.uid !== process.getuid() || (home.mode & 0o777) !== 0o700) throw Error('invalid_workspace_owner');
  return { installation, workspace };
}

// This is an application route map, never a generic proxy or native-control API.
// Queries exist only for the already bounded log filter.
export function remoteHudRoute(method, target, features, peerChat = false) {
  if (typeof target !== 'string' || target.length > 1024 || !target.startsWith('/') || /[\\#\u0000-\u0020\u007f]/.test(target) || /%(?!3A)/.test(target.split('?')[0])) return false;
  const [encodedPath, query, extra] = target.split('?');
  const pathname = encodedPath.replaceAll('%3A', ':');
  if (pathname.split('/').some(part => part === '.' || part === '..')) return false;
  if (extra !== undefined) return false;
  const has = name => features.includes(name);
  if (query !== undefined) {
    if (method !== 'GET' || !has('logs') || !new RegExp(`^/api/hud/logs/${ID}$`).test(pathname)) return false;
    const values = new URLSearchParams(query);
    if ([...values.keys()].some(k => !['q', 'severity'].includes(k)) || [...new Set(values.keys())].some(k => values.getAll(k).length !== 1) || (values.get('q') || '').length > 200 || !['all','error','warning','info','debug','unknown'].includes(values.get('severity') || 'all')) return false;
  }
  if (method === 'GET') {
    const routes = {
      '/api/graph': ['overview','skills'], '/api/n2n': ['overview','members','peers','operations'], '/api/bgp': ['overview','peers'],
      '/api/gateway/status': ['overview','runtime'], '/api/budget/status': ['overview','tokenomics'], '/api/budget/config': ['tokenomics'],
      '/api/hud/runtime': ['runtime','overview'], '/api/hud/security': ['overview'], '/api/hud/tokenomics': ['tokenomics'],
      '/api/chat/models': ['chat'], '/api/chat/conversations': ['chat'], '/api/rag/documents': ['rag'], '/api/rag/stats': ['rag'],
      '/api/hud/documentation': ['documentation'], '/api/hud/reference': ['reference'], '/api/hud/openapi.json': ['reference'], '/api/hud/logs': ['logs'],
    };
    if (routes[pathname]?.some(has)) return true;
    return has('skills') && new RegExp(`^/api/skill/${ID}$`).test(pathname)
      || has('documentation') && new RegExp(`^/api/hud/documentation/${ID}$`).test(pathname)
      || has('logs') && new RegExp(`^/api/hud/logs/${ID}$`).test(pathname);
  }
  if (method !== 'POST' || query !== undefined) return false;
  if (peerChat && has('peers') && pathname === '/api/n2n/chat') return true;
  return has('chat') && (['/api/chat', '/api/chat/usage'].includes(pathname) || new RegExp(`^/api/chat/conversations/${ID}/open$`).test(pathname))
    || has('rag') && ['/api/rag/search', '/api/rag/upload'].includes(pathname);
}

export function remoteHudBackendBoundary(workspace, installation) {
  return (req, res, next) => {
    if (req.url !== '/api/runtime' && !remoteHudRoute(req.method, req.url, workspace.features, workspace.mode === 'ordinary-federation')) return res.status(404).json({ code: 'route_unavailable' });
    if (req.method !== 'GET' && req.headers['x-netclaw-installation'] !== installation.installationId) return res.status(409).json({ code: 'installation_changed' });
    // Never read browser credentials, including old local HUD cookies.
    delete req.headers.cookie; delete req.headers.authorization;
    next();
  };
}
const scalar = v => typeof v === 'string' || typeof v === 'boolean' || typeof v === 'number' && Number.isFinite(v) ? v : null;
const pick = (v, keys) => Object.fromEntries(keys.filter(k => v?.[k] !== undefined).map(k => [k, scalar(v[k])]));
const rows = v => Array.isArray(v) ? v.slice(0, 128) : [];
function inventory(value) {
  const v = value?.inventory || value;
  return !v ? null : { ...pick(v, ['available','source','issued_at','received_at','version','stale']), harness: pick(v.harness,['type','version']), skills: rows(v.skills).map(s => pick(s, ['name','description','invocable'])), llm: { ...pick(v.llm,['primary_model','guarded']), fallbacks: rows(v.llm?.fallbacks).map(scalar) }, mcp_servers: rows(v.mcp_servers).map(s => ({ name: scalar(s.name), tools: rows(s.tools).map(scalar) })) };
}
export function projectRemoteHud(target, value) {
  if (target === '/api/hud/runtime') return { ...value, controlUi: { available: false, reason: 'Native gateway administration remains private. Use Chat and Canvas here.' } };
  if (target !== '/api/n2n') return value;
  return { ...pick(value,['available','generatedAt','identity']), risk: pick(value.risk,['risk_name','name','role','description']),
    members: rows(value.members).map(v => ({ ...pick(v,['member_id','display_name','profile','status','state','live','last_seen','last_heartbeat','updated_at','heartbeat_age_s','node_type']), skills: rows(v.skills).map(scalar), inventory: inventory(v.inventory) })),
    peers: rows(value.peers).map(v => ({ ...pick(v,['identity','display_name','state','channel_state','last_seen','updated_at','endpoint_updated_at','transport','remote_as','router_id','consent_local','consent_remote','chat_enabled','inventory_version','inventory_received_at','stale']), inventory: inventory(v.inventory), in_flight_tasks: rows(v.in_flight_tasks).map(t => typeof t === 'string' ? t : pick(t,['task_id','state','target_type','target_name','progress','updated_at'])) })),
    approvals: rows(value.approvals).map(v => pick(v,['id','peer_identity','target_type','target_name','status','created_at','expires_at'])),
    posture: { ...pick(value.posture,['mode','state','computed_at']), controls: rows(value.posture?.controls).map(v => pick(v,['name','available','detail'])) },
    advisors: rows(value.advisors), gait: rows(value.gait).map(v => pick(v,['id','timestamp','event','action','detail','commit','operation_id','member_id'])),
    edgeNodes: rows(value.edgeNodes).map(v => pick(v,['member_id','display_name','status','state','live','last_seen','node_type'])),
    recentPushes: rows(value.recentPushes).map(v => pick(v,['id','timestamp','status','state','target_type','member_id'])),
    replicationJobs: rows(value.replicationJobs).map(v => pick(v,['task_id','created_at','status','state','target_type','member_id'])) };
}
async function boundedResponse(response, limit = 8 * 1024 * 1024) {
  let size = 0; const chunks = [];
  for await (const chunk of response.body || []) { size += chunk.length; if (size > limit) throw Error('workspace_response_bound'); chunks.push(chunk); }
  return strictJson(Buffer.concat(chunks).toString('utf8'));
}
export function remoteHudTimeout(target) {
  if (target === '/api/chat') return 590000;
  if (target === '/api/n2n/chat') return 320000;
  // History may perform two bounded native reads: transcript, then model metadata.
  if (new RegExp(`^/api/chat/conversations/${ID}/open$`).test(target)) return 130000;
  return 90000;
}
export function createRemoteHud(workspace, installation, fetcher = fetch) {
  let active = 0;
  const verify = async () => {
    const response = await fetcher(workspace.upstream + '/api/runtime', { redirect: 'error', headers: { 'X-NetClaw-Installation': installation.installationId }, signal: AbortSignal.timeout(5000) });
    const value = await boundedResponse(response, 65536);
    if (!response.ok || value.installationId !== installation.installationId || value.kind !== 'openclaw' || value.remoteHudBackend?.schema !== 1 || value.remoteHudBackend.mode !== workspace.mode || JSON.stringify(value.remoteHudBackend.features) !== JSON.stringify(workspace.features)) throw Error('workspace_identity_changed');
    return value;
  };
  return { verify, async handle(req, res) {
    if (!remoteHudRoute(req.method, req.url, workspace.features, workspace.mode === 'ordinary-federation')) return false;
    if (req.method !== 'GET' && req.headers['x-netclaw-installation'] !== installation.installationId) { res.status(409).json({ code: 'installation_changed' }); return true; }
    if (active >= 4) { res.status(429).json({ code: 'workspace_busy' }); return true; }
    active++;
    try {
      await verify();
      let size = 0; const chunks = [];
      for await (const chunk of req) { size += chunk.length; if (size > (req.url === '/api/rag/upload' ? 12 : 4) * 1024 * 1024) { res.status(413).json({ code: 'request_too_large' }); return true; } chunks.push(chunk); }
      const headers = { 'X-NetClaw-Installation': installation.installationId };
      if (req.headers['content-type']) headers['Content-Type'] = req.headers['content-type'];
      const response = await fetcher(workspace.upstream + req.url, { method: req.method, headers, body: chunks.length ? Buffer.concat(chunks) : undefined, redirect: 'error', signal: AbortSignal.timeout(remoteHudTimeout(req.url)) });
      const value = await boundedResponse(response);
      res.status(response.status).json(response.ok ? projectRemoteHud(req.url, value) : value);
    } catch { if (!res.headersSent) res.status(503).json({ code: 'workspace_unavailable', error: 'The configured conversation workspace is unavailable. No automatic retry was made.' }); }
    finally { active--; }
    return true;
  } };
}
