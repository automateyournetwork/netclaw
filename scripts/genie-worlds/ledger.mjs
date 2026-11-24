import { DatabaseSync } from "node:sqlite";
import { mkdirSync, lstatSync, chmodSync, existsSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { randomUUID } from "node:crypto";
import {
  need,
  hash,
  UUID,
  POLICY,
  CAMPAIGN_SESSION_POLICY,
  projection,
  validateProjection,
  validatePolicy,
} from "./model.mjs";
export function privateRoot(path) {
  const root = resolve(path);
  need(root !== dirname(root), "invalid_state_root");
  for (let p = root; p !== dirname(p); p = dirname(p))
    if (existsSync(p))
      need(!lstatSync(p).isSymbolicLink(), "symlink_state_root");
  if (existsSync(root)) {
    const s = lstatSync(root);
    need(s.isDirectory() && s.uid === process.getuid(), "state_ownership");
  }
  mkdirSync(root, { recursive: true, mode: 0o700 });
  chmodSync(root, 0o700);
  return root;
}
const transitions = {
  create_pending: [
    "active",
    "stop_requested",
    "unknown",
    "terminal",
    "failed_pre_send",
  ],
  active: ["stop_requested", "unknown", "terminal"],
  stop_requested: ["unknown", "terminal"],
  unknown: ["terminal"],
  terminal: [],
  failed_pre_send: [],
};
export class Ledger {
  #retained = 0;
  #closing = false;
  #closed = false;
  constructor(root) {
    process.umask(0o077);
    this.root = privateRoot(root);
    const path = join(this.root, "sessions.sqlite");
    for (const suffix of ["-wal", "-shm"])
      if (existsSync(path + suffix))
        need(!lstatSync(path + suffix).isSymbolicLink(), "symlink_state_file");
    if (existsSync(path))
      need(
        !lstatSync(path).isSymbolicLink() &&
          lstatSync(path).uid === process.getuid(),
        "state_ownership",
      );
    this.db = new DatabaseSync(path);
    chmodSync(path, 0o600);
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=3000;
   CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,body TEXT NOT NULL,used TEXT);
   CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,digest TEXT NOT NULL,state TEXT NOT NULL,usage_state TEXT NOT NULL,body TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS events(operation_id TEXT PRIMARY KEY,event_id TEXT NOT NULL,sent_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS provider_creates(operation_id TEXT PRIMARY KEY,claimed_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY,prev TEXT NOT NULL,hash TEXT NOT NULL,body TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS recording_failures(operation_id TEXT NOT NULL,code TEXT NOT NULL,at TEXT NOT NULL,PRIMARY KEY(operation_id,code));
   CREATE TABLE IF NOT EXISTS recording_receipts(operation_id TEXT PRIMARY KEY,body TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS event_checkpoints(operation_id TEXT PRIMARY KEY,body TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS controls(id TEXT PRIMARY KEY,digest TEXT NOT NULL,operation_id TEXT NOT NULL,body TEXT NOT NULL);`);
  }
  close() {
    this.#closing = true;
    if (!this.#retained && !this.#closed) {
      this.db.close();
      this.#closed = true;
    }
  }
  retain() {
    // An already-started provider open may outlive local worker cleanup. Keep
    // this exact connection until its original ID/error has been recorded.
    need(!this.#closing, 'ledger_closing');
    this.#retained++;
    let released = false;
    return () => {
      if (released) return;
      released = true;
      this.#retained--;
      if (this.#closing) this.close();
    };
  }
  claimProviderCreate(id, validatedRecord) {
    // A committed claim is never reusable, even if the process dies before the
    // transport returns an ID. The campaign reservation remains held separately.
    return this.tx(() => {
      const b = this.get(id);
      need(hash(b) === hash(validatedRecord), 'campaign_session_changed');
      need(b.provider === 'google' && b.state === 'create_pending' &&
        b.usage_state === 'reserved' && !b.provider_id, 'paid_admission_required');
      need(Date.parse(b.deadline_at) > Date.now(), 'campaign_send_expired');
      need(!this.db.prepare('SELECT 1 FROM provider_creates WHERE operation_id=?').get(id),
        'provider_create_claimed');
      this.db.prepare('INSERT INTO provider_creates VALUES(?,?)').run(id, new Date().toISOString());
      this.audit('provider_create_claimed', { operation_id: id });
    });
  }
  claimControl(requestId, operationId, action, eventId) {
    need(UUID.test(requestId), 'invalid_request_id');
    need(['event', 'stop'].includes(action), 'invalid_control');
    if (action === 'event') need(eventId === projection().event_id, 'invalid_event');
    const digest = hash({ operationId, action, eventId: eventId ?? null });
    return this.tx(() => {
      this.get(operationId);
      const old = this.db.prepare('SELECT * FROM controls WHERE id=?').get(requestId);
      if (old) { need(old.digest === digest, 'request_conflict'); return { ...JSON.parse(old.body), newly_created: false }; }
      need(this.db.prepare('SELECT count(*) AS n FROM controls WHERE operation_id=?').get(operationId).n < 32, 'control_limit');
      const result = { request_id: requestId, operation_id: operationId, action, status: 'pending', code: null };
      this.db.prepare('INSERT INTO controls VALUES(?,?,?,?)').run(requestId, digest, operationId, JSON.stringify(result));
      this.audit('control_requested', { request_id: requestId, operation_id: operationId, action });
      return { ...result, newly_created: true };
    });
  }
  settleControl(requestId, status, code = null) {
    need(['accepted', 'refused', 'unknown'].includes(status), 'invalid_control_result');
    this.tx(() => {
      const row = this.db.prepare('SELECT body FROM controls WHERE id=?').get(requestId);
      need(row, 'unknown_control');
      const b = JSON.parse(row.body);
      if (b.status !== 'pending') return;
      Object.assign(b, { status, code });
      this.db.prepare('UPDATE controls SET body=? WHERE id=?').run(JSON.stringify(b), requestId);
      this.audit('control_result', { request_id: requestId, operation_id: b.operation_id, status, code });
    });
  }
  controlResults(id) {
    return this.db.prepare('SELECT body FROM controls WHERE operation_id=? ORDER BY rowid DESC LIMIT 32').all(id).map(row => JSON.parse(row.body));
  }
  recordingFailure(id, code) {
    this.get(id);
    need(["recording_start_failed", "recording_failed", "recording_upload_failed", "recording_limit"].includes(code), "invalid_recording_failure");
    this.tx(() => {
      const result = this.db.prepare("INSERT OR IGNORE INTO recording_failures VALUES(?,?,?)").run(id, code, new Date().toISOString());
      if (result.changes) this.audit("recording_failure", { operation_id: id, code });
    });
  }
  recordingFailures(id) {
    return this.db.prepare("SELECT code,at FROM recording_failures WHERE operation_id=? ORDER BY at,code").all(id);
  }
  recordingStatus(id) {
    this.get(id);
    const row = this.db.prepare("SELECT body FROM recording_receipts WHERE operation_id=?").get(id);
    const receipt = row ? JSON.parse(row.body) : null;
    return this.recordingFailures(id).length
      ? { state: "incomplete", reason: "recording_failure", receipt }
      : receipt ? { state: "final_flush_acknowledged", receipt }
      : { state: "unconfirmed", reason: "final_flush_unconfirmed", receipt: null };
  }
  eventCheckpoint(id) {
    this.get(id);
    const row = this.db.prepare('SELECT body FROM event_checkpoints WHERE operation_id=?').get(id);
    return row ? JSON.parse(row.body) : null;
  }
  recordEventCheckpoint(id, capture) {
    return this.tx(() => {
      need(this.get(id).event_state === 'sent', 'event_not_sent');
      const event = this.db.prepare('SELECT * FROM events WHERE operation_id=?').get(id);
      need(event, 'event_not_sent');
      const receipt = { ...capture, operation_id: id, event_id: event.event_id,
        event_send_marked_at: event.sent_at, captured_at: new Date().toISOString(), visible_effect: 'unassessed' };
      this.db.prepare('INSERT INTO event_checkpoints VALUES(?,?)').run(id, JSON.stringify(receipt));
      this.audit('event_checkpoint', receipt);
      return receipt;
    });
  }
  acknowledgeRecording(id, media) {
    return this.tx(() => {
      const current = this.recordingStatus(id);
      need(current.state !== "incomplete", "recording_already_failed");
      if (current.receipt) {
        need(current.receipt.sha256 === media.sha256 && current.receipt.size_bytes === media.size_bytes,
          "recording_receipt_conflict");
        return current;
      }
      const receipt = { ...media, at: new Date().toISOString() };
      this.db.prepare("INSERT INTO recording_receipts VALUES(?,?)").run(id, JSON.stringify(receipt));
      this.audit("recording_final_flush", { operation_id: id, ...receipt });
      return this.recordingStatus(id);
    });
  }
  tx(fn) {
    this.db.exec("BEGIN IMMEDIATE");
    try {
      const r = fn();
      this.db.exec("COMMIT");
      return r;
    } catch (e) {
      this.db.exec("ROLLBACK");
      throw e;
    }
  }
  audit(type, data) {
    const body = JSON.stringify({
      type,
      at: new Date().toISOString(),
      ...data,
    });
    const prev =
      this.db.prepare("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").get()
        ?.hash || "";
    this.db
      .prepare("INSERT INTO audit(prev,hash,body)VALUES(?,?,?)")
      .run(prev, hash({ prev, body }), body);
  }
  review(p, policy, allowance, provider) {
    validateProjection(p);
    const campaign = hash(policy) === hash(CAMPAIGN_SESSION_POLICY);
    if (!campaign) validatePolicy(policy);
    need(["fixture", "google"].includes(provider), "invalid_provider");
    const bound = Math.round(allowance * 1_000_000);
    need(
      campaign
        ? provider === 'google' && Number.isSafeInteger(bound) &&
          bound > 12_096_000 && bound <= 25_000_000 && bound / 1_000_000 === allowance
        : Number.isFinite(allowance) && allowance >= 15,
      "allowance_insufficient",
    );
    const body = {
      id: randomUUID(),
      projection_sha256: p.sha256,
      policy_sha256: hash(policy),
      allowance_usd: allowance,
      provider,
      ...(campaign ? { accounting_version: 'campaign-v1', reservation_microusd: bound } : {}),
      expires_at: Date.now() + 600000,
    };
    this.tx(() => {
      this.db
        .prepare("INSERT INTO reviews(id,body)VALUES(?,?)")
        .run(body.id, JSON.stringify(body));
      this.audit("review", {
        review_id: body.id,
        projection_sha256: p.sha256,
        provider,
      });
    });
    return body;
  }
  admit(id, p, reviewId, provider, projectionRef = null, reserveCampaign = null) {
    need(UUID.test(id), "invalid_request_id");
    validateProjection(p);
    const digest = hash({ p, reviewId, provider, policy: POLICY, ...(projectionRef ? { projectionRef } : {}) });
    return this.tx(() => {
      const old = this.db.prepare("SELECT * FROM sessions WHERE id=?").get(id);
      if (old) {
        need(old.digest === digest, "request_conflict");
        if (reserveCampaign) {
          const b = JSON.parse(old.body);
          need(b.campaign_reservation, 'campaign_binding_required');
          need(hash(reserveCampaign(digest, true)) === hash(b.campaign_reservation), 'campaign_binding_mismatch');
        }
        return { ...JSON.parse(old.body), newly_created: false };
      }
      if (provider === "google")
        need(!this.db.prepare("SELECT id FROM sessions WHERE json_extract(body,'$.provider')='google'").get(), "single_attempt_consumed");
      const r = this.db
        .prepare("SELECT * FROM reviews WHERE id=?")
        .get(reviewId);
      need(r && !r.used, "review_required");
      const review = JSON.parse(r.body);
      // Original-ID lookup above preserves historical records. A new campaign
      // marker requires an explicitly full-duration local review, never an
      // implicit upgrade of the historical 20s/$15 review.
      const campaign = Boolean(reserveCampaign);
      need(
        review.expires_at > Date.now() &&
          review.provider === provider &&
          review.projection_sha256 === p.sha256 &&
          review.policy_sha256 === hash(campaign ? CAMPAIGN_SESSION_POLICY : POLICY) &&
          (campaign ? review.accounting_version === 'campaign-v1' : !review.accounting_version),
        "review_stale",
      );
      // Conservative installation-wide hold: alternate account labels cannot bypass it.
      need(
        !this.db
          .prepare(
            "SELECT id FROM sessions WHERE state NOT IN ('terminal','failed_pre_send') OR usage_state != 'reconciled'",
          )
          .get(),
        "active_or_unsettled",
      );
      // Separate authority commits first. A later local rollback/crash must NOT
      // release its reservation. Retry only this original ID and exact binding.
      const campaignReservation = reserveCampaign?.(digest, false);
      if (reserveCampaign) need(campaignReservation && provider === 'google' &&
        Number.isSafeInteger(campaignReservation.bound_microusd) &&
        campaignReservation.bound_microusd > 12_096_000 &&
        campaignReservation.bound_microusd <= 25_000_000 &&
        campaignReservation.bound_microusd === review.reservation_microusd &&
        review.allowance_usd === campaignReservation.bound_microusd / 1_000_000,
      'invalid_campaign_reservation');
      const policy = campaignReservation ? CAMPAIGN_SESSION_POLICY : POLICY;
      const reservedUsd = campaignReservation ? campaignReservation.bound_microusd / 1_000_000 : review.allowance_usd;
      const body = {
        operation_id: id,
        projection_sha256: p.sha256,
        ...(projectionRef ? { projection_ref: projectionRef } : {}),
        review_id: reviewId,
        provider,
        ...(campaignReservation ? {
          campaign_reservation: campaignReservation,
          accounting_version: 'campaign-v1',
          session_policy: policy,
          estimated_video_usd: 12.096,
          reserved_microusd: campaignReservation.bound_microusd,
        } : {}),
        state: "create_pending",
        usage_state: "reserved",
        estimated_usd: provider === "fixture" ? 0 : campaignReservation ? reservedUsd : 2.016,
        reserved_usd: provider === "fixture" ? 0 : reservedUsd,
        send_marked_at: new Date().toISOString(),
        deadline_at: new Date(Date.now() + policy.deadline_seconds_from_send * 1000).toISOString(),
        provider_id: null,
        terminal_receipt: null,
        reason: null,
        event_state: "planned",
      };
      this.db.prepare("UPDATE reviews SET used=? WHERE id=?").run(id, reviewId);
      this.db
        .prepare("INSERT INTO sessions VALUES(?,?,?,?,?)")
        .run(id, digest, body.state, body.usage_state, JSON.stringify(body));
      this.audit("send_marked", {
        operation_id: id,
        provider,
        projection_sha256: p.sha256,
      });
      return { ...body, newly_created: true };
    });
  }
  get(id) {
    need(UUID.test(id), "invalid_operation_id");
    const r = this.db.prepare("SELECT body FROM sessions WHERE id=?").get(id);
    need(r, "not_found");
    return JSON.parse(r.body);
  }
  list() {
    return this.db
      .prepare("SELECT body FROM sessions ORDER BY rowid DESC LIMIT 100")
      .all()
      .map((r) => JSON.parse(r.body));
  }
  save(body) {
    this.db
      .prepare("UPDATE sessions SET state=?,usage_state=?,body=? WHERE id=?")
      .run(
        body.state,
        body.usage_state,
        JSON.stringify(body),
        body.operation_id,
      );
  }
  transition(id, state, patch = {}) {
    return this.tx(() => {
      const b = this.get(id);
      if (state === 'failed_pre_send')
        need(!b.provider_id &&
          !this.db.prepare('SELECT 1 FROM provider_creates WHERE operation_id=?').get(id),
        'provider_create_may_have_sent');
      need(
        b.state === state || transitions[b.state]?.includes(state),
        "invalid_transition",
      );
      Object.assign(b, patch, { state });
      if (state === "failed_pre_send") b.usage_state = "reconciled";
      this.save(b);
      this.audit(state, { operation_id: id, reason: b.reason });
      return b;
    });
  }
  providerId(id, providerId) {
    need(
      typeof providerId === "string" && providerId.length <= 256,
      "provider_contract",
    );
    return this.tx(() => {
      const b = this.get(id);
      b.provider_id = providerId;
      this.save(b);
      return b;
    });
  }
  terminal(id, receipt) {
    need(
      ['interaction.completed', 'interaction.cancelled', 'interaction.canceled'].includes(receipt?.event_type),
      "terminal_receipt_required",
    );
    need(JSON.stringify(receipt).length <= 32768, "provider_contract");
    return this.tx(() => {
      const b = this.get(id);
      need(
        b.state === "terminal" || transitions[b.state]?.includes("terminal"),
        "invalid_transition",
      );
      b.state = "terminal";
      b.terminal_receipt = receipt;
      b.usage_state = validUsage(receipt.usage) ? "reconciled" : "unsettled";
      b.finished_at = new Date().toISOString();
      this.save(b);
      this.audit("terminal", {
        operation_id: id,
        usage_state: b.usage_state,
        receipt_sha256: hash(receipt),
      });
      return b;
    });
  }
  claimEvent(id, eventId) {
    return this.tx(() => {
      const b = this.get(id);
      need(eventId === projection().event_id, "invalid_event");
      const old = this.db
        .prepare("SELECT * FROM events WHERE operation_id=?")
        .get(id);
      if (old) return false;
      need(b.state === "active", "event_unavailable");
      this.db
        .prepare("INSERT INTO events VALUES(?,?,?)")
        .run(id, eventId, new Date().toISOString());
      b.event_state = "send_marked";
      this.save(b);
      this.audit("event_send_marked", { operation_id: id, event_id: eventId });
      return true;
    });
  }
  eventSent(id) {
    this.tx(() => {
      const b = this.get(id);
      b.event_state = "sent";
      this.save(b);
    });
  }
}
export function validUsage(usage) {
  if (!usage || typeof usage !== "object" || Array.isArray(usage)) return false;
  const scalar = new Set([
    "video_output_tokens",
    "text_output_tokens",
    "input_tokens",
    "initial_input_tokens",
    "total_input_tokens",
    "total_output_tokens",
    "total_tokens",
    "total_cached_tokens",
    "total_thought_tokens",
    "total_tool_use_tokens",
  ]);
  const breakdown = new Set([
    "input_tokens_by_modality",
    "output_tokens_by_modality",
    "tool_use_tokens_by_modality",
  ]);
  const integer = (v) => Number.isSafeInteger(v) && v >= 0;
  const valid = Object.entries(usage).every(([k, v]) =>
    scalar.has(k)
      ? integer(v)
      : breakdown.has(k) &&
        Array.isArray(v) &&
        v.length <= 16 &&
        v.every(
          (row) =>
            row &&
            Object.keys(row).every((k) => ["modality", "tokens"].includes(k)) &&
            typeof row.modality === "string" &&
            row.modality.length <= 32 &&
            integer(row.tokens),
        ),
  );
  return (
    valid &&
    (integer(usage.video_output_tokens) ||
      integer(usage.total_output_tokens) ||
      (Array.isArray(usage.output_tokens_by_modality) &&
        usage.output_tokens_by_modality.some(
          (r) => r.modality.toLowerCase() === "video",
        )))
  );
}
