/** Thermidor's stable-parent/no-repeat workflow, adapted to existing NetClaw children. */
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const id = value => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,200}$/.test(value);
const digest = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const same = (a, b) => JSON.stringify(a, Object.keys(a || {}).sort()) === JSON.stringify(b, Object.keys(b || {}).sort());
const fail = () => { throw Error('Combined request identity or review is unavailable. Recover the same request; nothing was resent.'); };
export function combinedChoices(catalog) {
  const choices = { 4: [], 6: [] };
  if (!catalog?.capabilities?.includes('calculator_combined_v1')) return choices;
  if (!Array.isArray(catalog.members) || catalog.members.length > 100) return fail();
  for (const entry of catalog.members) for (const family of [4, 6]) {
    if (!plain(entry.member) || typeof entry.member.member_id !== 'string' || entry.member.member_id.length > 200 || !Array.isArray(entry.model_profiles) || !Array.isArray(entry.tools)) return fail();
    for (const profile of entry.model_profiles) if (profile.profile_id === `ollama-cpu-ipv${family}` && profile.provider === 'ollama' && id(profile.profile_revision)) {
      for (const tool of entry.tools) if (tool.tool === (family === 4 ? 'subnet_calculator' : 'subnet_calculator_v6') && plain(tool.arguments) && Object.keys(tool.arguments).join() === 'cidr' && typeof tool.arguments.cidr === 'string' && tool.arguments.cidr.length <= 100) {
        choices[family].push({ family, member_id: entry.member.member_id, profile_revision: profile.profile_revision, cidr: tool.arguments.cidr });
        if (choices[family].length > 100) return fail();
      }
    }
  }
  return choices;
}
function cleanReference(value) {
  if (!plain(value) || !id(value.client_nonce) || Object.keys(value).some(k => !['client_nonce', 'parent_id', 'children', 'cancel_sent', 'not_submitted'].includes(k)) || value.parent_id !== undefined && !id(value.parent_id) || value.cancel_sent !== undefined && value.cancel_sent !== true || value.not_submitted !== undefined && (value.not_submitted !== true || value.parent_id || value.children || value.cancel_sent)) return fail();
  if (value.children !== undefined && (!value.parent_id || !Array.isArray(value.children) || value.children.length !== 2 || value.children.some(c => !plain(c) || !id(c.operation_id) || Object.keys(c).some(k => !['operation_id', 'decision_sent'].includes(k)) || c.decision_sent !== undefined && c.decision_sent !== true) || value.children[0].operation_id === value.children[1].operation_id)) return fail();
  if (value.parent_id && !value.children || value.cancel_sent && !value.parent_id) return fail();
  return JSON.parse(JSON.stringify(value));
}
export function combinedReference(installation, principal, storage = globalThis.sessionStorage) {
  if (!id(installation) || !id(principal?.issuer) || !id(principal?.subject)) return fail();
  const key = `netclaw.protected.${installation}.${principal.issuer}.${principal.subject}.combined.v1`;
  return {
    read() { const raw = storage.getItem(key); if (raw === null) return null; if (raw.length > 2048) return fail(); try { return cleanReference(JSON.parse(raw)); } catch { return fail(); } },
    write(value) { const next = cleanReference(value), previous = this.read(); if (previous && (previous.client_nonce !== next.client_nonce || previous.parent_id && previous.parent_id !== next.parent_id || previous.children && previous.children.some((c, i) => c.operation_id !== next.children?.[i]?.operation_id || c.decision_sent && !next.children[i].decision_sent) || previous.cancel_sent && !next.cancel_sent)) return fail(); storage.setItem(key, JSON.stringify(next)); },
    clear() { storage.removeItem(key); },
  };
}
export function validateCombined(value, ref, installation, principal) {
  if (!plain(value) || value.schemaVersion !== 1 || !id(value.parent_id) || value.client_nonce !== ref.client_nonce || ref.parent_id && value.parent_id !== ref.parent_id || !['awaiting_decisions', 'running', 'complete', 'partial', 'failed', 'cancelled', 'unknown'].includes(value.state) || !Number.isSafeInteger(value.expires_at_ms) || !Array.isArray(value.children) || value.children.length !== 2) return fail();
  value.children.forEach((child, index) => {
    const review = child?.review;
    if (!plain(child) || child.index !== index || child.family !== [4, 6][index] || !id(child.operation_id) || !id(child.client_nonce) || ref.children && ref.children[index].operation_id !== child.operation_id || !Number.isSafeInteger(child.revision) || !digest(child.review_digest) || !plain(review) || review.border?.installation_id !== installation || !same(review.principal, principal) || !['member', 'model_profile', 'tool_call', 'limits'].every(key => plain(review[key])) || !Array.isArray(child.allowed_actions)) return fail();
  });
  if (value.children[0].operation_id === value.children[1].operation_id) return fail();
  return value;
}
export class CombinedOperations {
  busy = false; value = null; uncertain = false;
  constructor(api, references, installation, principal, nonce = () => crypto.randomUUID()) { Object.assign(this, { api, references, installation, principal, nonce }); }
  async exclusive(action) { if (this.busy) throw Error('A combined request action is in progress.'); this.busy = true; try { return await action(); } finally { this.busy = false; } }
  accept(value) {
    const ref = this.references.read(); if (!ref) return fail(); validateCombined(value, ref, this.installation, this.principal);
    this.references.write({ ...ref, parent_id: value.parent_id, children: value.children.map((c, i) => ({ operation_id: c.operation_id, ...(ref.children?.[i]?.decision_sent ? { decision_sent: true } : {}) })) });
    this.value = value; this.uncertain = false; return value;
  }
  async status() { const ref = this.references.read(); if (!ref || ref.not_submitted) return fail(); this.uncertain = true; return this.accept(await this.api.combinedStatus(ref)); }
  recover() { return this.exclusive(() => this.status()); }
  recoverOriginal(kind, identifier) { return this.exclusive(async () => {
    if (!['parent_id', 'client_nonce'].includes(kind) || !id(identifier) || this.references.read()) return fail();
    const value = await this.api.combinedStatus({ [kind]: identifier });
    const expected = { client_nonce: kind === 'client_nonce' ? identifier : value?.client_nonce, ...(kind === 'parent_id' ? { parent_id: identifier } : {}) };
    validateCombined(value, expected, this.installation, this.principal);
    // An imported identifier cannot prove that an earlier decision/cancel was
    // never sent. Import is deliberately status-only; no new authority follows.
    this.references.write({ client_nonce: value.client_nonce, parent_id: value.parent_id, cancel_sent: true, children: value.children.map(c => ({ operation_id: c.operation_id, decision_sent: true })) });
    this.value = value; this.uncertain = false; return value;
  }); }
  prepare(children) { return this.exclusive(async () => {
    if (this.references.read()) throw Error('Recover the retained combined request first.');
    const choices = combinedChoices(await this.api.catalog());
    if (!Array.isArray(children) || children.length !== 2 || children.some((c, i) => c.family !== [4, 6][i] || !choices[c.family].some(choice => same(choice, c)))) return fail();
    const ref = { client_nonce: this.nonce() }; this.references.write(ref); this.uncertain = true;
    try { return this.accept(await this.api.prepareCombined({ client_nonce: ref.client_nonce, children })); }
    catch (error) { if (error.prepareNotSubmitted) { this.references.write({ ...ref, not_submitted: true }); this.uncertain = false; } throw error; }
  }); }
  decide(index, decision) { return this.exclusive(async () => {
    if (![0, 1].includes(index) || !['approve', 'deny'].includes(decision)) return fail();
    const shown = this.value?.children[index]; if (!shown || this.uncertain) return fail();
    const current = await this.status(), ref = this.references.read(), child = current.children[index];
    if (ref.cancel_sent || ref.children[index].decision_sent || child.revision !== shown.revision || child.review_digest !== shown.review_digest || !child.allowed_actions.includes(decision) || child.state !== 'review_pending' || decision === 'approve' && (child.review.limits.expires_at_ms <= Date.now() || current.expires_at_ms <= Date.now())) return fail();
    ref.children[index].decision_sent = true; this.references.write(ref); this.uncertain = true;
    await this.api.decision(child.operation_id, { revision: child.revision, review_digest: child.review_digest, decision });
    return this.status();
  }); }
  cancel() { return this.exclusive(async () => { const ref = this.references.read(); if (!ref?.parent_id || ref.cancel_sent) return fail(); this.references.write({ ...ref, cancel_sent: true }); this.uncertain = true; await this.api.cancelCombined(ref.parent_id); return this.status(); }); }
  discard() {
    const ref = this.references.read();
    const resolved = this.value && ['complete', 'partial', 'failed', 'cancelled'].includes(this.value.state)
      && this.value.children.every(c => c.reconciliation_required === false
        && (!c.may_have_executed || c.result?.verified === true && c.result?.durable_ack === true && c.result?.ack_delivery_pending === false));
    if (this.busy || this.uncertain || !ref || !ref.not_submitted && !resolved) return fail();
    this.references.clear(); this.value = null;
  }
}
