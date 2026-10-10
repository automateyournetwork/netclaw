// The catalogue describes capability, not operational reachability.
export const VIEWS = [
  ['chat', 'Chat', '00'],
  ['overview', 'Overview', '01'], ['canvas', 'Canvas', '02'],
  ['risk', 'Risk of Claws', '03'], ['neighbours', 'External neighbours', '04'],
  ['mobile', 'Mobile devices', '05'], ['science', 'Science Officer', '06'],
  ['network', 'Network', '07'], ['knowledge', 'Knowledge', '08'],
  ['operations', 'Operations', '09'], ['integrations', 'Integrations', '10'],
  ['settings', 'Settings', '11'], ['rag', 'RAG', '12'], ['configuration', 'Configuration', '13'], ['tokenomics', 'Tokenomics', '14'], ['documentation', 'Documentation', '15'], ['logs', 'Logs', '16'], ['security', 'Security', '17'], ['pal', 'Avatar', '18'],
];
export const GUIDES = {
  knowledge: [
    ['RAG collections', 'Search documents with citations. Keep local and peer collections distinct.', 'Search my available RAG collections and return cited evidence.', 'rag'],
    ['Memory', 'Prior decisions and observations, with their recorded validity.', 'Recall relevant prior network decisions with provenance and validity windows.', 'memory'],
    ['GCF context efficiency', 'Measured characters and token estimates are different quantities.', 'Report measured GCF context compression if recorded. Separate character counts, estimated tokens and actual provider usage.', 'gcf'],
    ['Zoom meeting context', 'Meeting evidence retains its owner, source and retrieval time.', 'Find available Zoom meeting context relevant to this investigation, with source and date.', 'zoom'],
  ],
  operations: [
    ['Incidents & changes', 'Review impact, approval, baseline and verification before execution.', 'Review open incidents and changes in scope. Show approval and verification state. Do not create or modify tickets.', 'servicenow'],
    ['Security & posture', 'Missing controls stay visible. Advisory confidence is not device health.', 'Review available security and enforcement evidence; distinguish enforced, audit-only and missing controls.', 'security'],
    ['Telemetry & events', 'Identify the collector, observation window and missing sources.', 'Review scoped telemetry and recent events, showing collectors, times and collection gaps.', 'telemetry'],
    ['Audit & reports', 'Follow the decision to its evidence, actor and outcome.', 'Show the GAIT trail and available reports for this investigation, retaining source references.', 'gait'],
  ],
};
export const list = value => Array.isArray(value) ? value : [];
export const text = (value, fallback = 'Not recorded') => typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : fallback;
export function age(value, now = Date.now()) {
  const time = typeof value === 'number' ? (value < 1e12 ? value * 1000 : value) : Date.parse(value);
  if (!Number.isFinite(time)) return 'Time unknown';
  if (time > now + 60000) return 'Clock ahead';
  const sec = Math.max(0, Math.floor((now - time) / 1000));
  return sec < 60 ? `${sec}s ago` : sec < 3600 ? `${Math.floor(sec / 60)}m ago` : `${Math.floor(sec / 3600)}h ago`;
}
export function freshness(value, now = Date.now()) {
  const time = typeof value === 'number' ? (value < 1e12 ? value * 1000 : value) : Date.parse(value);
  return !Number.isFinite(time) ? 'unknown' : time > now + 60000 || now - time > 300000 ? 'stale' : 'fresh';
}
export function observation(previous, payload, error, now = new Date().toISOString()) {
  if (error) return { ...previous, state: 'unavailable', error: 'Source could not be read', retrievedAt: now };
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return observation(previous, null, true, now);
  if (payload.available === false) return { ...previous, payload: previous?.payload || payload, state: payload.reason === 'not-configured' ? 'not_configured' : 'unavailable', error: 'Source unavailable or not configured', retrievedAt: now };
  return { payload, state: 'available', retrievedAt: now, lastSuccess: now, error: null };
}
export function entities(feed = {}) {
  const rows = [];
  const add = (kind, item) => {
    if (!item || typeof item !== 'object') return;
    const identity = item.identity || item.member_id || item.advisor_id || item.id;
    // Never collapse two unknown identities by their display name.
    if (!identity || typeof identity !== 'string') return;
    const key = `${kind}:${identity}`;
    const status = text(item.status || item.channel_state || item.state, 'Unknown');
    const row = { key, identity, kind, name: text(item.display_name || item.name || item.member_id || item.identity || item.advisor_id),
      status, freshness: freshness(item.last_seen || item.updated_at || item.last_heartbeat), seen: item.last_seen || item.updated_at || item.last_heartbeat || null,
      capabilities: item.capabilities || item.scope || item.skills || [],
      authority: kind === 'advisor' ? 'Advisory only · cannot execute' : kind === 'peer' ? 'External · permission scoped' : kind === 'edge' ? 'Edge · operator capabilities' : 'Execution member · scoped', raw: item };
    const i = rows.findIndex(r => r.key === key);
    if (i < 0) rows.push(row);
    else if (/severed|quarantined|unreachable|offline/i.test(status)) rows[i] = row;
  };
  list(feed.members).forEach(m => add(m?.node_type === 'edge' ? 'edge' : 'member', m));
  list(feed.edgeNodes).forEach(m => add('edge', m));
  list(feed.peers).forEach(p => add('peer', p));
  list(feed.advisors).forEach(a => add('advisor', a));
  return rows;
}
export function relations(rows, root = 'local') {
  return rows.map(row => ({ source: root, target: row.key, kind: row.kind === 'peer' ? 'External federation' : row.kind === 'advisor' ? 'Advice' : 'Membership' }));
}
export function selectedContext(title, data, source, retrievedAt) {
  return `Investigate: ${title}\nSource: ${source}\nRetrieved: ${retrievedAt || 'unknown'}\nThis is recorded context; verify current state before conclusions.\n\n${JSON.stringify(data, null, 2).slice(0, 12000)}`;
}
export const money = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? `$${value.toFixed(4)}` : 'Unknown';

export function bgpEntities(snapshot = {}) {
  if (snapshot.available !== true) return [];
  return list(snapshot.peers).filter(p => p && typeof p.peer === 'string').map(p => ({
    key: 'bgp:' + p.peer, identity: p.peer, name: p.peer, kind: 'router',
    status: text(p.state, 'Unknown'), seen: snapshot.generatedAt, raw: p,
    authority: 'Observed BGP session · not physical cabling',
  }));
}

export function clawInventory(row) {
  const raw = row?.raw || {};
  const envelope = raw.inventory || {};
  const card = envelope.inventory || envelope;
  const servers = list(card.mcp_servers || raw.mcp_servers);
  const llm = card.llm || raw.llm || {};
  return { servers, harness: text(card.harness?.type, 'unknown'), harnessVersion: text(card.harness?.version, 'unknown'), model: text(llm.primary_model || raw.model, row?.kind === 'edge' ? 'No local LLM · requests handled by Border / delegated Claw' : 'Not reported'),
    fallbacks: list(llm.fallbacks), guarded: llm.guarded, source: card.source || (row?.kind === 'peer' ? 'Peer capability advertisement' : 'Member configuration report'),
    observedAt: envelope.received_at || card.issued_at || card.generatedAt || raw.inventory_received_at,
    stale: envelope.stale === true, available: card.available !== false && Array.isArray(card.mcp_servers || raw.mcp_servers) };
}

export function securitySummary(settings, posture, sourceAvailable) {
  const fresh = sourceAvailable && posture && freshness(posture.computed_at) === 'fresh';
  const controls = list(posture?.controls);
  const known = ['sandbox','model-guard','audit'].every(name => controls.some(c => c.name === name && typeof c.available === 'boolean'));
  const enforced = fresh && known && posture.mode === 'production' && posture.state === 'enforced' && controls.every(c => c.available === true);
  return { label: !fresh ? 'Enforcement unknown / stale' : enforced ? settings?.labMode === true ? 'PRODUCTION reported · LAB bypass enabled' : 'PRODUCTION · enforcement reported' : posture.mode === 'production' ? 'PRODUCTION · degraded or incomplete' : posture.mode === 'testing' ? 'LAB / testing · federation guards not enforced' : 'Enforcement mode unknown',
    lab: settings?.labMode === true ? 'LAB bypass enabled' : settings?.labMode === false ? 'LAB bypass disabled' : 'LAB setting unknown',
    enforced, fresh };
}
