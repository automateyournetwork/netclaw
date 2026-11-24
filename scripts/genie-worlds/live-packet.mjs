import { readFileSync, lstatSync, readdirSync, realpathSync, openSync, closeSync, fstatSync, readSync, constants } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseEnv } from 'node:util';
import { createHash } from 'node:crypto';
import { need, closed, hash, POLICY, CAMPAIGN_SESSION_POLICY, projection, validateProjection, sessionPolicy } from './model.mjs';
import { CampaignBudget, CampaignAdmission, CAMPAIGN_POLICY } from './campaign-budget.mjs';
// Explicit reviewed closure. New runtime modules/assets require a new source review;
// never silently expand an existing approval. Installed dependencies use the lockfile.
const CONTROL_SOURCE_FILES = [
  'scripts/genie-worlds/mcp_server.py',
  'mcp-servers/genie-worlds-mcp/server.py',
  'mcp-servers/genie-worlds-mcp/requirements.txt',
  'workspace/skills/netclaw-genie-worlds/SKILL.md',
  'workspace/skills/netclaw-genie-worlds/references/tools.md',
];
export const LIVE_SOURCE_FILES = Object.freeze([...[
  'audit.mjs', 'approved-projection.mjs', 'campaign-budget.mjs', 'check-runtime.mjs', 'offline-snapshot.mjs', 'preparation.mjs', 'world-designs.mjs', 'cli.mjs', 'fixture-provider.mjs', 'ledger.mjs', 'live-packet.mjs',
  'manager.mjs', 'model.mjs', 'provider.mjs', 'worker.mjs', 'package.json', 'package-lock.json',
  'viewer/index.html', 'viewer/viewer.mjs', 'viewer/viewer.css',
  'viewer/network-graph.mjs', 'viewer/selection.mjs',
  'fixtures/synthetic-museum-v1.json', 'fixtures/baseline.jpg', 'fixtures/movement.jpg', 'fixtures/event.jpg',
].map(n => 'scripts/genie-worlds/' + n), ...CONTROL_SOURCE_FILES]);

function validateSourceClosure() {
  const found = [];
  function visit(directory, prefix = '') {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      if (['node_modules', '__pycache__'].includes(entry.name)) continue;
      const name = prefix + entry.name;
      need(!entry.isSymbolicLink(), 'source_closure_symlink');
      if (entry.isDirectory()) visit(join(directory, entry.name), name + '/');
      else if (name.endsWith('.mjs') || /^(viewer|fixtures)\//.test(name) || ['package.json', 'package-lock.json'].includes(name)) {
        need(entry.isFile(), 'source_closure_file_required');
        found.push('scripts/genie-worlds/' + name);
      }
    }
  }
  visit(fileURLToPath(new URL('.', import.meta.url)));
  for (const name of CONTROL_SOURCE_FILES) {
    const path = fileURLToPath(new URL('../../' + name, import.meta.url));
    need(lstatSync(path).isFile() && !lstatSync(path).isSymbolicLink(), 'source_closure_symlink');
    found.push(name);
  }
  need(hash(found.sort()) === hash([...LIVE_SOURCE_FILES].sort()), 'source_closure_changed');
}

function privateBytes(path, reference = null) {
  need(typeof path === 'string' && resolve(path) === path, 'private_path_required');
  for (let p = path; p !== dirname(p); p = dirname(p))
    need(!lstatSync(p).isSymbolicLink(), 'private_path_symlink');
  const st = lstatSync(path);
  const check = s => need(s.isFile() && s.uid === process.getuid() &&
    !(s.mode & 0o077) && s.nlink === 1, 'private_file_required');
  check(st);
  need(st.size > 0 && st.size <= 1024 * 1024, 'private_file_size');
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const before = fstatSync(fd); check(before);
    need(before.dev === st.dev && before.ino === st.ino && before.size === st.size, 'private_file_changed');
    if (reference) need(before.dev === reference.dev && before.ino === reference.ino &&
      before.size === reference.size_bytes, 'artifact_identity_changed');
    // Fixed allocation and bounded read, including one byte to detect growth.
    const bytes = Buffer.alloc(before.size + 1);
    let length = 0, count;
    while (length < bytes.length && (count = readSync(fd, bytes, length, bytes.length - length, null)) > 0) length += count;
    const after = fstatSync(fd); check(after);
    need(length === before.size && after.size === before.size &&
      after.ctimeMs === before.ctimeMs &&
      after.mtimeMs === before.mtimeMs, 'private_file_changed');
    for (let p = path; p !== dirname(p); p = dirname(p))
      need(!lstatSync(p).isSymbolicLink(), 'private_path_symlink');
    const current = lstatSync(path); check(current);
    need(current.dev === before.dev && current.ino === before.ino &&
      current.size === after.size && current.ctimeMs === after.ctimeMs, 'private_file_changed');
    const result = bytes.subarray(0, length);
    if (reference) need(createHash('sha256').update(result).digest('hex') === reference.sha256, 'artifact_content_changed');
    return result;
  } finally { closeSync(fd); }
}
function privateFile(path) { return privateBytes(path).toString('utf8'); }

// For coordinator-reviewed source/review/service/input-text evidence references.
// Verifies retained bytes and file identity, NOT the truth of a service/billing
// claim. loadCampaignReview adds typed consistency checks before campaign admission.
export function readReviewedArtifact(reference) {
  closed(reference, ['path', 'sha256', 'dev', 'ino', 'size_bytes']);
  need(typeof reference.sha256 === 'string' && /^[a-f0-9]{64}$/.test(reference.sha256) &&
    ['dev', 'ino', 'size_bytes'].every(k => Number.isSafeInteger(reference[k]) && reference[k] >= 0), 'artifact_reference_required');
  return privateBytes(reference.path, reference);
}
export function loadCredential(path) {
  const env = parseEnv(privateFile(path));
  const key = env.GEMINI_API_KEY || env.GOOGLE_API_KEY;
  need(typeof key === 'string' && key.length > 20 && key.length < 512, 'credential_missing');
  return key;
}
// Operator launch configuration, never a packet/tool-selected authority or bootstrap.
export function loadCampaignAuthority(env = process.env) {
  const path = env.NETCLAW_GENIE_CAMPAIGN_AUTHORITY;
  const pin = env.NETCLAW_GENIE_CAMPAIGN_AUTHORITY_SHA256;
  need(typeof path === 'string' && /^[a-f0-9]{64}$/.test(pin || ''), 'campaign_pin_required');
  const bytes = privateFile(path);
  need(createHash('sha256').update(bytes).digest('hex') === pin, 'campaign_pin_changed');
  const a = JSON.parse(bytes);
  closed(a, ['schema', 'campaign_id', 'authority_root', 'authority_dev', 'authority_ino', 'policy_sha256']);
  need(a.schema === 1 && a.policy_sha256 === hash(CAMPAIGN_POLICY), 'campaign_policy_mismatch');
  need(typeof a.authority_root === 'string' && resolve(a.authority_root) === a.authority_root &&
    realpathSync(a.authority_root) === a.authority_root, 'campaign_root_mismatch');
  const st = lstatSync(join(a.authority_root, 'campaign-budget.sqlite'));
  need(Number.isSafeInteger(a.authority_dev) && Number.isSafeInteger(a.authority_ino) &&
    st.dev === a.authority_dev && st.ino === a.authority_ino, 'campaign_identity_changed');
  // Existing authority only. Also validates private ownership and stored root/policy binding.
  const budget = new CampaignBudget(a.authority_root, a.campaign_id);
  budget.close();
  return { ...a, sha256: pin };
}
function validateSources(sourceFiles) {
  validateSourceClosure();
  need(sourceFiles && hash(Object.keys(sourceFiles).sort()) === hash([...LIVE_SOURCE_FILES].sort()), 'source_manifest_required');
  for (const [name, digest] of Object.entries(sourceFiles)) {
    const bytes = readFileSync(new URL('../../' + name, import.meta.url));
    need(createHash('sha256').update(bytes).digest('hex') === digest, 'live_source_changed');
  }
}
// Trusted backend seam, not a tool or approval creator. The coordinator must pin
// the review reference and assess the cited provider contracts. Validation proves
// consistency of those reviewed claims, never their truth or live enforcement.
// Live manager integration still requires the qualified 120s runtime migration.
export function loadCampaignReview(reference, context, env = process.env) {
  closed(context, ['world_number', 'source_files', 'projection']);
  need(Number.isInteger(context.world_number) && context.world_number >= 1 && context.world_number <= 5, 'invalid_world');
  validateProjection(context.projection); // Preserve the independent synthetic gate.
  validateSources(context.source_files);
  const authority = loadCampaignAuthority(env);
  const common = {schema:1, campaign_id:authority.campaign_id,
    campaign_authority_sha256:authority.sha256, source_manifest_sha256:hash(context.source_files),
    projection_sha256:context.projection.sha256, policy_sha256:hash(CAMPAIGN_POLICY),
    model:'genie-4', currency:'USD', world_number:context.world_number, target_seconds:120};
  function record(ref, kind, fields) {
    const bytes = readReviewedArtifact(ref), value = JSON.parse(bytes.toString('utf8'));
    // Require compact JSON.stringify encoding to reject duplicate keys, lossy
    // numbers, malformed UTF-8 and ambiguous representations without a parser dependency.
    need(bytes.equals(Buffer.from(JSON.stringify(value))), 'artifact_json_encoding');
    closed(value, [...Object.keys(common), 'kind', ...fields]);
    need(value.kind === kind && Object.entries(common).every(([k,v]) => value[k] === v), 'review_binding_mismatch');
    return value;
  }
  const review = record(reference, 'campaign_review', ['expires_at', 'reservation_microusd', 'service_bound', 'input_text_bound']);
  need(typeof review.expires_at === 'string' && Date.parse(review.expires_at) > Date.now(), 'review_expired');
  const service = record(review.service_bound, 'service_bound', ['enforcement', 'max_seconds', 'video_bound_microusd', 'evidence']);
  need(service.enforcement === 'provider' && service.max_seconds === 120 &&
    service.video_bound_microusd === CAMPAIGN_POLICY.video_bound_microusd, 'service_bound_required');
  readReviewedArtifact(service.evidence);
  const input = record(review.input_text_bound, 'input_text_bound', ['enforcement', 'max_input_tokens', 'max_output_text_tokens',
    'input_price_microusd_per_million', 'output_text_price_microusd_per_million', 'bound_microusd', 'evidence']);
  need(input.enforcement === 'provider', 'input_text_enforcement_required');
  const amounts = ['max_input_tokens', 'max_output_text_tokens', 'input_price_microusd_per_million',
    'output_text_price_microusd_per_million', 'bound_microusd'];
  need(amounts.every(k => Number.isSafeInteger(input[k]) && input[k] > 0), 'input_text_bound_required');
  // Round each charge upward separately with exact integer arithmetic.
  const charge = (tokens, rate) => (BigInt(tokens) * BigInt(rate) + 999999n) / 1000000n;
  const required = charge(input.max_input_tokens, input.input_price_microusd_per_million) +
    charge(input.max_output_text_tokens, input.output_text_price_microusd_per_million);
  need(BigInt(input.bound_microusd) >= required, 'input_text_underfunded');
  readReviewedArtifact(input.evidence);
  const total = service.video_bound_microusd + input.bound_microusd;
  need(Number.isSafeInteger(total) && review.reservation_microusd === total &&
    total <= CAMPAIGN_POLICY.soft_stop_microusd, 'review_reservation_mismatch');
  return {world_number:common.world_number, target_seconds:120, review_sha256:reference.sha256,
    service_bound_sha256:review.service_bound.sha256, input_text_bound_microusd:input.bound_microusd};
}
export function loadLivePacket(path, env = process.env) {
  const p = JSON.parse(privateFile(path));
  const campaign = p.schema === 2;
  closed(p, ['schema', 'state_root', 'credential_file', 'projection_sha256', 'policy_sha256', 'allowance_usd', 'attempts', 'authorized', 'authorization_ref', 'expires_at', 'source_files', 'campaign_authority_sha256',
    ...(campaign ? ['world_number', 'reservation_microusd', 'campaign_review_sha256'] : [])]);
  need([1, 2].includes(p.schema) && p.authorized === true && typeof p.authorization_ref === 'string' && p.authorization_ref.length > 0, 'live_authorization_required');
  // Schema 1 remains the historical 20s/$15 format; never reinterpret its bytes.
  need(p.attempts === 1 && p.projection_sha256 === projection().sha256 &&
    p.policy_sha256 === hash(campaign ? CAMPAIGN_SESSION_POLICY : POLICY), 'live_packet_mismatch');
  if (!campaign) need(p.allowance_usd === POLICY.reservation_usd, 'live_packet_mismatch');
  need(Date.parse(p.expires_at) > Date.now(), 'live_packet_expired');
  need(resolve(p.state_root) === p.state_root, 'private_path_required');
  validateSources(p.source_files);
  const authority = loadCampaignAuthority(env);
  need(p.campaign_authority_sha256 === authority.sha256, 'campaign_packet_mismatch');
  if (campaign) {
    // The packet cannot nominate its own review. Reload the operator-pinned
    // descriptor and every source/evidence reference before touching credentials.
    const { budget_review } = reviewedCampaign(projection(), env);
    const bound = CAMPAIGN_POLICY.video_bound_microusd + budget_review.input_text_bound_microusd;
    need(p.world_number === budget_review.world_number &&
      p.campaign_review_sha256 === budget_review.review_sha256 &&
      Number.isSafeInteger(p.reservation_microusd) && p.reservation_microusd === bound &&
      p.allowance_usd === bound / 1_000_000, 'campaign_packet_mismatch');
  }
  loadCredential(p.credential_file);
  return p;
}

// Operator-only launch descriptor. No model/tool arguments select a review,
// world, source closure or authority. Reload all retained bytes on every admission.
// The manager supplies its frozen operator launch pins after its native audit.
export function admitReviewedCampaign(ledger, input, env = process.env) {
  closed(input, ['operation_id', 'projection', 'review_id', 'projection_ref']);
  const { authority, budget_review } = reviewedCampaign(input.projection, env);
  const admission = new CampaignAdmission(authority.authority_root, authority.campaign_id);
  try { return admission.admit(ledger, { ...input, budget_review }); }
  finally { admission.close(); }
}
function reviewedCampaign(p, env) {
  const path = env.NETCLAW_GENIE_CAMPAIGN_REVIEW;
  const pin = env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256;
  need(typeof path === 'string' && /^[a-f0-9]{64}$/.test(pin || ''), 'campaign_review_pin_required');
  const bytes = privateBytes(path);
  need(createHash('sha256').update(bytes).digest('hex') === pin, 'campaign_review_pin_changed');
  const launch = JSON.parse(bytes.toString('utf8'));
  need(bytes.equals(Buffer.from(JSON.stringify(launch))), 'artifact_json_encoding');
  closed(launch, ['schema', 'world_number', 'source_files', 'review']);
  need(launch.schema === 1, 'campaign_review_launch_schema');
  const budget_review = loadCampaignReview(launch.review, {
    world_number: launch.world_number, source_files: launch.source_files,
    projection: p,
  }, env);
  const authority = loadCampaignAuthority(env);
  return { authority, budget_review };
}

// Revalidate pinned authority/evidence immediately before create. Never admits,
// reserves, repairs a missing marker, or treats a terminal ID as a new send.
export function validateReviewedCampaignSend(ledger, id, env = process.env) {
  const record = ledger.get(id);
  need(record.provider === 'google' && record.state === 'create_pending' &&
    record.usage_state === 'reserved' && !record.provider_id, 'paid_admission_required');
  sessionPolicy(record);
  need(Date.parse(record.deadline_at) > Date.now(), 'campaign_send_expired');
  const p = projection();
  need(record.operation_id === id && record.projection_sha256 === p.sha256, 'campaign_session_changed');
  const { authority, budget_review } = reviewedCampaign(p, env);
  const sessionDigest = hash({ p, reviewId: record.review_id, provider: 'google', policy: POLICY,
    ...(record.projection_ref ? { projectionRef: record.projection_ref } : {}) });
  const budget = new CampaignBudget(authority.authority_root, authority.campaign_id);
  try {
    const reservation = budget.assertReserved({ ...budget_review, operation_id: id,
      session_binding_sha256: hash({ root: realpathSync(ledger.root), session_digest: sessionDigest }) });
    need(hash(record.campaign_reservation) === hash({
      session_binding_sha256: reservation.session_binding_sha256,
      bound_microusd: reservation.bound_microusd, review_sha256: reservation.review_sha256,
    }), 'campaign_binding_mismatch');
  } finally { budget.close(); }
  return record;
}
