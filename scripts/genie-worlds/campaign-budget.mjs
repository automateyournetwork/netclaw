// Accounting only: no provider calls or authorization creation. The coordinator
// must pin one authority root for every member/account before runtime integration.
import { DatabaseSync } from 'node:sqlite';
import { lstatSync, openSync, closeSync, realpathSync } from 'node:fs';
import { join } from 'node:path';
import { privateRoot } from './ledger.mjs';
import { need, closed, hash, UUID } from './model.mjs';

export const CAMPAIGN_POLICY = Object.freeze({
  schema: 1, currency: 'USD', target_seconds: 120,
  video_bound_microusd: 12_096_000,
  review_checkpoint_microusd: 25_000_000,
  soft_stop_microusd: 100_000_000, hard_stop_microusd: 100_000_000,
});
const money = n => need(Number.isSafeInteger(n) && n >= 0, 'invalid_microusd');
const digest = s => need(typeof s === 'string' && /^[a-f0-9]{64}$/.test(s), 'evidence_digest_required');
function add(a, b) { money(a); money(b); money(a + b); return a + b; }

export class CampaignBudget {
  // initialize is trusted bootstrap ONLY, never an agent/start-tool parameter.
  // Opening a missing root without it fails, and existing authorities cannot reset.
  constructor(root, campaignId, { initialize = false } = {}) {
    need(typeof campaignId === 'string' && /^[a-z0-9-]{1,80}$/.test(campaignId), 'invalid_campaign');
    const path = join(root, 'campaign-budget.sqlite');
    if (!initialize) need(lstatSync(root).isDirectory(), 'budget_authority_required');
    const canonicalRoot = privateRoot(root);
    if (initialize) closeSync(openSync(path, 'wx', 0o600));
    const st = lstatSync(path);
    need(st.isFile() && !st.isSymbolicLink() && st.uid === process.getuid() &&
      !(st.mode & 0o077) && st.nlink === 1, 'private_budget_required');
    for (const suffix of ['-wal', '-shm']) {
      try { const s = lstatSync(path + suffix); need(s.isFile() && !s.isSymbolicLink() && s.uid === process.getuid() && !(s.mode & 0o077), 'private_budget_required'); }
      catch (e) { if (e.code !== 'ENOENT') throw e; }
    }
    this.db = new DatabaseSync(path);
    try {
      this.db.exec('PRAGMA busy_timeout=3000; PRAGMA journal_mode=WAL;');
      const binding = hash({ root: realpathSync(canonicalRoot), campaignId, policy: CAMPAIGN_POLICY });
      if (initialize) this.db.exec(`
        CREATE TABLE authority(binding TEXT NOT NULL);
        CREATE TABLE reservations(id TEXT PRIMARY KEY, digest TEXT NOT NULL, body TEXT NOT NULL);
      `);
      if (initialize) this.db.prepare('INSERT INTO authority VALUES(?)').run(binding);
      const rows = this.db.prepare('SELECT binding FROM authority').all();
      need(rows.length === 1 && rows[0].binding === binding, 'budget_authority_mismatch');
    } catch (e) { this.db.close(); throw e; }
  }
  close() { this.db.close(); }
  tx(fn) {
    this.db.exec('BEGIN IMMEDIATE');
    try { const result = fn(); this.db.exec('COMMIT'); return result; }
    catch (e) { this.db.exec('ROLLBACK'); throw e; }
  }
  totals() {
    let settled = 0, reserved = 0, unresolved = 0, active_unknown = 0;
    for (const row of this.db.prepare('SELECT body FROM reservations').all()) {
      const b = JSON.parse(row.body);
      if (b.settlement) settled = add(settled, b.settlement.charged_microusd);
      else { reserved = add(reserved, b.bound_microusd); unresolved++; if (!b.terminal_bound_evidence) active_unknown++; }
    }
    const exposure = add(settled, reserved);
    return { settled_microusd: settled, reserved_microusd: reserved,
      exposure_microusd: exposure, unresolved, active_unknown,
      review_checkpoint_reached: exposure >= CAMPAIGN_POLICY.review_checkpoint_microusd,
      hard_ceiling_exceeded: exposure > CAMPAIGN_POLICY.hard_stop_microusd };
  }
  reserve(request) {
    closed(request, ['operation_id', 'world_number', 'review_sha256', 'service_bound_sha256', 'input_text_bound_microusd', 'target_seconds', 'session_binding_sha256']);
    need(UUID.test(request.operation_id), 'invalid_operation_id');
    need(Number.isInteger(request.world_number) && request.world_number >= 1 && request.world_number <= 5, 'invalid_world');
    need(request.target_seconds === 120, 'full_session_required');
    digest(request.review_sha256); digest(request.service_bound_sha256);
    if (request.session_binding_sha256 !== undefined) digest(request.session_binding_sha256);
    money(request.input_text_bound_microusd);
    need(request.input_text_bound_microusd > 0, 'input_text_bound_required');
    const bound = add(CAMPAIGN_POLICY.video_bound_microusd, request.input_text_bound_microusd);
    const requestDigest = hash(request);
    return this.tx(() => {
      const old = this.db.prepare('SELECT * FROM reservations WHERE id=?').get(request.operation_id);
      if (old) {
        need(old.digest === requestDigest, 'request_conflict');
        return { ...JSON.parse(old.body), newly_reserved: false };
      }
      const t = this.totals(), exposure = add(t.exposure_microusd, bound);
      need(exposure <= CAMPAIGN_POLICY.hard_stop_microusd, 'campaign_hard_stop');
      need(exposure <= CAMPAIGN_POLICY.soft_stop_microusd, 'campaign_soft_stop');
      need(t.active_unknown === 0, 'campaign_unresolved');
      const body = { ...request, bound_microusd: bound, settlement: null };
      this.db.prepare('INSERT INTO reservations VALUES(?,?,?)').run(request.operation_id, requestDigest, JSON.stringify(body));
      return { ...body, newly_reserved: true };
    });
  }
  // Pre-send lookup only: missing/settled reservations must never be recreated.
  assertReserved(request) {
    const row = this.db.prepare('SELECT * FROM reservations WHERE id=?').get(request.operation_id);
    need(row && row.digest === hash(request), 'campaign_reservation_required');
    const body = JSON.parse(row.body);
    need(!body.settlement, 'campaign_reservation_settled');
    need(!body.terminal_bound_evidence, 'campaign_terminal_no_replay');
    need(hash(body) === hash({ ...request,
      bound_microusd: CAMPAIGN_POLICY.video_bound_microusd + request.input_text_bound_microusd,
      settlement: null }), 'campaign_reservation_changed');
    return body;
  }
  // Trusted reconciliation of the ORIGINAL interaction only. A real remote
  // terminal receipt closes execution uncertainty but does not invent billing.
  // Keep the entire bound in reserved exposure until actual usage is reconciled.
  confirmTerminalBound(operationId, evidence) {
    closed(evidence, ['event_type', 'terminal_sha256', 'provider_id_sha256']);
    need(['interaction.completed','interaction.cancelled','interaction.canceled'].includes(evidence.event_type), 'terminal_receipt_required');
    digest(evidence.terminal_sha256); digest(evidence.provider_id_sha256);
    return this.tx(() => {
      const row=this.db.prepare('SELECT body FROM reservations WHERE id=?').get(operationId);
      need(row,'unknown_reservation'); const body=JSON.parse(row.body);
      if(body.terminal_bound_evidence) need(hash(body.terminal_bound_evidence)===hash(evidence),'terminal_evidence_conflict');
      body.terminal_bound_evidence=evidence;
      this.db.prepare('UPDATE reservations SET body=? WHERE id=?').run(JSON.stringify(body),operationId);
      return this.totals();
    });
  }
  // Only trusted reconciliation can supply these references. A timer, stop ACK,
  // token estimate or missing usage cannot call this as confirmed billed cost.
  settle(operationId, evidence) {
    closed(evidence, ['charged_microusd', 'terminal_sha256', 'billing_sha256']);
    money(evidence.charged_microusd); digest(evidence.terminal_sha256); digest(evidence.billing_sha256);
    return this.tx(() => {
      const row = this.db.prepare('SELECT body FROM reservations WHERE id=?').get(operationId);
      need(row, 'unknown_reservation');
      const body = JSON.parse(row.body);
      if (body.settlement) need(hash(body.settlement) === hash(evidence), 'settlement_conflict');
      // Preserve actual overruns, even above the ceiling; never clamp a charge.
      body.settlement = evidence;
      this.db.prepare('UPDATE reservations SET body=? WHERE id=?').run(JSON.stringify(body), operationId);
      return this.totals();
    });
  }
}

// Trusted backend seam only. One coordinator-pinned authority must be shared by
// all session roots/accounts. No bootstrap or authority selection in tool inputs.
// Not wired to the live manager until packet evidence and 120s policy qualify.
export class CampaignAdmission {
  #budget;
  constructor(authorityRoot, campaignId) {
    this.#budget = new CampaignBudget(authorityRoot, campaignId);
  }
  close() { this.#budget.close(); }
  admit(ledger, input) {
    closed(input, ['operation_id', 'projection', 'review_id', 'projection_ref', 'budget_review']);
    closed(input.budget_review, ['world_number', 'review_sha256', 'service_bound_sha256', 'input_text_bound_microusd', 'target_seconds']);
    const root = realpathSync(ledger.root);
    return ledger.admit(input.operation_id, input.projection, input.review_id,
      'google', input.projection_ref ?? null, (sessionDigest, existing) => {
        const reservation = this.#budget.reserve({ ...input.budget_review,
          operation_id: input.operation_id,
          session_binding_sha256: hash({ root, session_digest: sessionDigest }),
        });
        // A settled ID can retrieve an existing session, never create a new one.
        need(existing || (!reservation.settlement && !reservation.terminal_bound_evidence), 'settled_reservation_no_replay');
        return { session_binding_sha256: reservation.session_binding_sha256,
          bound_microusd: reservation.bound_microusd,
          review_sha256: reservation.review_sha256 };
      });
  }
}
