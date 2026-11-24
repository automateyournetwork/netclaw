import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { readApprovedProjection } from './approved-projection.mjs';
export class Refusal extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}
export function need(condition, code) {
  if (!condition) throw new Refusal(code);
}
export function closed(value, keys) {
  need(
    value &&
      Object.getPrototypeOf(value) === Object.prototype &&
      !Object.keys(value).some((k) => !keys.includes(k)),
    "invalid_input",
  );
}
function canonical(v) {
  if (Array.isArray(v)) return v.map(canonical);
  if (v && typeof v === "object")
    return Object.fromEntries(
      Object.keys(v)
        .sort()
        .map((k) => [k, canonical(v[k])]),
    );
  need(typeof v !== "number" || Number.isFinite(v), "invalid_input");
  return v;
}
export const hash = (value) =>
  createHash("sha256")
    .update(JSON.stringify(canonical(value)))
    .digest("hex");
export const UUID =
  /^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
export const POLICY = Object.freeze({
  model: "genie-4",
  api_version: "v1beta",
  target_seconds: 20,
  deadline_seconds_from_send: 30,
  first_frame_timeout_seconds: 10,
  terminal_wait_seconds: 5,
  viewer_lost_seconds: 3,
  manager_lost_seconds: 5,
  service_max_seconds: 120,
  currency: "USD",
  reservation_usd: 15,
});
// Explicit campaign record policy. A local deadline is not a
// provider billing cap. Leave POLICY intact for historical reviews and sessions.
export const CAMPAIGN_SESSION_POLICY = Object.freeze({
  ...Object.fromEntries(Object.entries(POLICY).filter(([k]) => k !== 'reservation_usd')),
  target_seconds: 120,
  deadline_seconds_from_send: 130, // up to 10s for first frame + 120s navigation
});
// Local shutdown only: neither timeout is provider termination/billing evidence.
export const WORKER_SHUTDOWN_DRAIN_MS = 5000;
export const MANAGER_SHUTDOWN_GRACE_MS =
  Math.max(POLICY.terminal_wait_seconds, CAMPAIGN_SESSION_POLICY.terminal_wait_seconds) * 1000 +
  WORKER_SHUTDOWN_DRAIN_MS + 1500; // IPC delivery, timer tick and process exit margin
// Select only explicit campaign records for new Google sends. Historical records
// remain readable; their old fields never acquire campaign authority implicitly.
export function sessionPolicy(record) {
  if (record.provider === 'fixture') {
    need(!record.accounting_version && !record.campaign_reservation && !record.session_policy,
      'fixture_campaign_mismatch');
    return POLICY;
  }
  need(record.provider === 'google' && record.accounting_version === 'campaign-v1' &&
    record.campaign_reservation && record.session_policy, 'campaign_session_required');
  need(hash(record.session_policy) === hash(CAMPAIGN_SESSION_POLICY), 'campaign_session_policy_mismatch');
  const bound = record.campaign_reservation.bound_microusd;
  need(Number.isSafeInteger(bound) && bound > 12_096_000 && bound <= 25_000_000 &&
    record.reserved_microusd === bound && record.reserved_usd === bound / 1_000_000 &&
    record.estimated_usd === bound / 1_000_000 && record.estimated_video_usd === 12.096,
    'campaign_session_reservation_mismatch');
  const sent = Date.parse(record.send_marked_at), deadline = Date.parse(record.deadline_at);
  // The ledger uses separate wall-clock samples for these timestamps; the
  // worker's monotonic deadline still enforces exactly 130s from the send marker.
  need(Number.isFinite(sent) && Number.isFinite(deadline) && deadline - sent >= 130000 &&
    deadline - sent <= CAMPAIGN_SESSION_POLICY.deadline_seconds_from_send * 1000 + 1000,
    'campaign_session_deadline_mismatch');
  return CAMPAIGN_SESSION_POLICY;
}
const fixture = JSON.parse(
  readFileSync(
    new URL("./fixtures/synthetic-museum-v1.json", import.meta.url),
    "utf8",
  ),
);
export function fixtureFacts() {
  return structuredClone(fixture);
}
export function projection(id) {
  const approved=readApprovedProjection();
  if(approved){need(id===undefined,'synthetic_source_not_selected');return approved;}
  id ??= 'synthetic-museum-v1';
  need(id === fixture.fixture_id, "unknown_fixture");
  const p = {
    classification: "synthetic",
    fixture_id: id,
    fixture_sha256: hash(fixture),
    text: fixture.text,
    event_id: fixture.event_id,
    event_text: fixture.event_text,
    event_send_count: 1,
  };
  return { ...p, sha256: hash(p) };
}
export function validateProjection(p) {
  need(hash(p) === hash(projection()), "private_or_modified_projection");
  return true;
}
export function validatePolicy(p) {
  need(hash(p) === hash(POLICY), "invalid_policy");
}
export const KEYS = Object.freeze({
  w: "key_w",
  a: "key_a",
  s: "key_s",
  d: "key_d",
  arrow_left: "arrow_left",
  arrow_right: "arrow_right",
  arrow_up: "arrow_up",
  arrow_down: "arrow_down",
});
export function supportedRuntime() {
  const [major, minor] = process.versions.node.split(".").map(Number);
  need(
    (major === 24 && minor >= 19) || (major === 26 && minor >= 1) || major > 26,
    "unsupported_runtime",
  );
}
