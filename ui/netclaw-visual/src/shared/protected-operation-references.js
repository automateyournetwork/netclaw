export const REFERENCE_CAPACITY = 32;
export const operationIdentifier = value => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,200}$/.test(value);
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const field = value => typeof value === 'string' && value.length > 0 && value.length <= 200 && !/[\u0000-\u001f\u007f]/.test(value) ? value : null;
const digest = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
function canonical(value, depth = 0) {
  if (depth > 12) throw Error('Invalid selection');
  if (value === null || typeof value === 'boolean' || typeof value === 'string' || typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + Array.from(value, item => canonical(item, depth + 1)).join(',') + ']';
  if (plain(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key], depth + 1)).join(',') + '}';
  throw Error('Invalid selection');
}
/** Match the backend's member/tool/complete-arguments selection, never a label. */
export function operationSelection(memberId, toolCall) {
  if (!field(memberId) || !operationIdentifier(toolCall?.tool) || !plain(toolCall?.arguments)) return null;
  try {
    const value = canonical([memberId, toolCall.tool, toolCall.arguments]);
    return value.length <= 65536 ? value : null;
  } catch { return null; }
}
const validReference = value => plain(value) && Object.keys(value).every(key => ['client_nonce', 'operation_id'].includes(key)) && operationIdentifier(value.client_nonce) && (value.operation_id === undefined || operationIdentifier(value.operation_id));
const clean = value => ({ client_nonce: value.client_nonce, ...(value.operation_id ? { operation_id: value.operation_id } : {}) });
export function removableOperation(value) {
  if (!value || value.reconciliation_required !== false || ['outcome_unknown', 'reconciliation_required', 'audit_pending', 'dispatch_pending', 'member_admitted', 'result_pending'].includes(value.state)) return false;
  if (['refused', 'revoked', 'denied'].includes(value.state) && value.attempt_count === 0 && value.may_have_executed === false && !value.result) return true;
  return ['completed', 'refused', 'failed'].includes(value.state) && value.result?.verified === true && value.result?.durable_ack === true && value.result?.ack_delivery_pending === false;
}
export function parsedVersion(operation) {
  const tool = operation?.result?.evidence?.output?.tool;
  if (operation?.result?.verified !== true || !plain(tool) || tool.parsed !== true || !plain(tool.output) || !plain(tool.output.version)) return { version: null, os: null };
  return { version: field(tool.output.version.version), os: field(tool.output.version.os) };
}
function ipv4(value) {
  if (typeof value !== 'string' || !/^(0|[1-9]\d{0,2})(\.(0|[1-9]\d{0,2})){3}$/.test(value)) return null;
  const parts = value.split('.').map(Number);
  return parts.every(part => part <= 255) ? parts.reduce((total, part) => total * 256 + part, 0) : null;
}
function sourcePrefix(value) {
  if (!field(value)) return false;
  const parts = value.split('/');
  if (parts.length !== 2 || !/^(0|[1-9]\d{0,2})$/.test(parts[1])) return false;
  const length = Number(parts[1]), address = ipv4(parts[0]);
  if (address !== null) return length <= 32 && address % (2 ** (32 - length)) === 0;
  if (length > 128 || !/^[0-9a-fA-F:]+$/.test(parts[0]) || !parts[0].includes(':')) return false;
  try { return new URL('http://[' + parts[0] + ']/').hostname.startsWith('['); } catch { return false; }
}
/** A compact projection of verified native evidence; model prose is never used. */
export function verifiedResultSummary(operation) {
  const call = operation?.review?.tool_call;
  if (call?.tool === 'pyats_run_show_command') {
    const value = parsedVersion(operation);
    return `${value.os || 'Unavailable'} / ${value.version || 'Unavailable'}`;
  }
  const tool = operation?.result?.evidence?.output?.tool, member = operation?.review?.member?.member_id;
  const selection = operationSelection(member, call);
  if (operation?.result?.verified !== true || !plain(tool) || tool.schemaVersion !== 1 || tool.mcp_calls !== 1 ||
      !selection || operationSelection(member, tool) !== selection || !plain(tool.output) ||
      !['endpoint_sha256', 'source_sha256', 'skill_sha256', 'mcp_schema_sha256'].every(key => digest(tool[key])) ||
      tool.endpoint_sha256 !== call.endpoint_sha256) return 'Unavailable';
  const output = tool.output, args = call.arguments;
  if (call.tool === 'netbox_get_object_by_id') {
    if (!Number.isSafeInteger(args.object_id) || args.object_id < 1 || output.id !== args.object_id || args.brief !== false || !Array.isArray(args.fields)) return 'Unavailable';
    const expected = args.object_type === 'dcim.device' ? ['id', 'name', 'status', 'site', 'device_type', 'last_updated'] : args.object_type === 'ipam.prefix' ? ['id', 'prefix', 'status', 'vrf', 'last_updated'] : null;
    if (!expected || canonical(args.fields) !== canonical(expected) || canonical(Object.keys(args).sort()) !== canonical(['brief', 'fields', 'object_id', 'object_type'])) return 'Unavailable';
    if (args.object_type === 'dcim.device' && field(output.name)) return `NetBox device ${output.name} · ID ${output.id}`;
    // Prefix records can be IPv4 or IPv6; the source's bounded CIDR is evidence,
    // while calculator support remains the separately reviewed IPv4 profile.
    if (args.object_type === 'ipam.prefix' && sourcePrefix(output.prefix)) return `NetBox prefix ${output.prefix} · ID ${output.id}`;
  }
  if (call.tool === 'subnet_calculator' && Object.keys(args).length === 1 && typeof args.cidr === 'string') {
    const parts = args.cidr.split('/'), address = ipv4(parts[0]), prefix = Number(parts[1]);
    if (parts.length !== 2 || address === null || !/^(2[4-9]|30)$/.test(parts[1])) return 'Unavailable';
    const size = 2 ** (32 - prefix);
    if (address % size || address < size || address + size * 2 > 2 ** 32 || output.network_address !== parts[0] || output.prefix_length !== prefix || output.num_addresses !== size || output.usable_hosts_count !== size - 2) return 'Unavailable';
    return `${args.cidr} · ${output.usable_hosts_count} usable hosts`;
  }
  return 'Unavailable';
}
export function operationReferences(installationId, storage = globalThis.sessionStorage) {
  if (!operationIdentifier(installationId)) throw Error('Installation identity unavailable.');
  const key = `netclaw.protected.${installationId}.operations.v2`, legacy = `netclaw.protected.${installationId}.operation`;
  const validate = value => {
    if (!Array.isArray(value) || value.length > REFERENCE_CAPACITY || value.some(row => !validReference(row)) || new Set(value.map(row => row.client_nonce)).size !== value.length || new Set(value.filter(row => row.operation_id).map(row => row.operation_id)).size !== value.filter(row => row.operation_id).length) throw Error('Retained operation references are invalid. Preserve the stored identifiers and recover an exact ID; nothing was submitted.');
    return value.map(clean);
  };
  const save = value => { validate(value); if (value.length) storage.setItem(key, JSON.stringify(value)); else storage.removeItem(key); };
  const read = () => {
    const raw = storage.getItem(key), old = storage.getItem(legacy);
    const current = raw === null ? [] : validate(JSON.parse(raw));
    if (old !== null) {
      const previous = JSON.parse(old); if (!validReference(previous)) throw Error('Legacy operation identity is invalid.');
      const same = current.find(row => row.client_nonce === previous.client_nonce);
      if (same && same.operation_id !== previous.operation_id || current.some(row => row.operation_id && row.operation_id === previous.operation_id && row.client_nonce !== previous.client_nonce)) throw Error('Retained operation identity conflict.');
      if (!same) { if (current.length >= REFERENCE_CAPACITY) throw Error('Retained operation capacity reached. Legacy identity was preserved.'); current.push(clean(previous)); }
      save(current); storage.removeItem(legacy);
    }
    return current;
  };
  return {
    read,
    put(value) {
      if (!validReference(clean(value))) throw Error('Operation identity unavailable.');
      const current = read(), index = current.findIndex(row => row.client_nonce === value.client_nonce);
      if (current.some((row, i) => i !== index && row.operation_id && row.operation_id === value.operation_id) || index >= 0 && current[index].operation_id && current[index].operation_id !== value.operation_id) throw Error('Operation identity changed. Nothing was resent.');
      if (index < 0) { if (current.length >= REFERENCE_CAPACITY) throw Error('Retained operation capacity reached. Remove a resolved reference before preparing another.'); current.push(clean(value)); }
      else current[index] = clean(value);
      save(current); return current;
    },
    remove(operation) {
      if (!removableOperation(operation)) throw Error('Unresolved operation references must be retained.');
      const current = read(), selected = current.find(row => row.client_nonce === operation.client_nonce);
      if (!selected || selected.operation_id !== operation.operation_id) throw Error('Operation identity changed.');
      const next = current.filter(row => row !== selected); save(next); return next;
    },
    discardUnsubmitted(clientNonce) {
      const current = read(), selected = current.find(row => row.client_nonce === clientNonce);
      if (!selected || selected.operation_id) throw Error('An admitted operation cannot be discarded.');
      const next = current.filter(row => row !== selected); save(next); return next;
    },
  };
}
