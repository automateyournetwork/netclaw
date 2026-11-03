export const REFERENCE_CAPACITY = 32;
export const operationIdentifier = value => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,200}$/.test(value);
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);
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
  const field = value => typeof value === 'string' && value.length > 0 && value.length <= 200 && !/[\u0000-\u001f\u007f]/.test(value) ? value : null;
  return { version: field(tool.output.version.version), os: field(tool.output.version.os) };
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
