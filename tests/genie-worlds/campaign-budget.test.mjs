import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, copyFileSync } from 'node:fs';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { CampaignBudget, CampaignAdmission, CAMPAIGN_POLICY } from '../../scripts/genie-worlds/campaign-budget.mjs';
import { Ledger } from '../../scripts/genie-worlds/ledger.mjs';
import { projection, POLICY, CAMPAIGN_SESSION_POLICY, hash } from '../../scripts/genie-worlds/model.mjs';
const h = 'a'.repeat(64);
const request = (patch = {}) => ({ operation_id: randomUUID(), world_number: 1,
  review_sha256: h, service_bound_sha256: h, input_text_bound_microusd: 404_000,
  target_seconds: 120, ...patch });
const evidence = charged_microusd => ({ charged_microusd, terminal_sha256: h, billing_sha256: h });
function fixture(t) {
  const root = mkdtempSync(join(process.env.NETCLAW_TEST_TMP, 'campaign-'));
  const budget = new CampaignBudget(root, 'synthetic-campaign', { initialize: true });
  t.after(() => { try { budget.close(); } catch {} rmSync(root, { recursive: true, force: true }); });
  return { root, budget };
}
test('full sessions, positive input/text allowance and integer money required', t => {
  const { budget } = fixture(t);
  assert.equal(CAMPAIGN_POLICY.video_bound_microusd, 12_096_000);
  for (const n of [0, -1, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER])
    assert.throws(() => budget.reserve(request({ input_text_bound_microusd: n })));
  assert.throws(() => budget.reserve(request({ target_seconds: 20 })), /full_session_required/);
  assert.throws(() => budget.reserve(request({ service_bound_sha256: null })), /evidence_digest_required/);
  assert.equal(budget.totals().exposure_microusd, 0);
});
test('durable unknown holds original ID across restart, other worlds and callers', t => {
  const { root, budget } = fixture(t), r = request();
  assert.equal(budget.reserve(r).newly_reserved, true);
  budget.close();
  const reopened = new CampaignBudget(root, 'synthetic-campaign');
  try {
    assert.equal(reopened.reserve(r).newly_reserved, false);
    assert.throws(() => reopened.reserve({ ...r, world_number: 2 }), /request_conflict/);
    assert.throws(() => reopened.reserve(request({ world_number: 2 })), /campaign_unresolved/);
    assert.throws(() => reopened.settle(r.operation_id, { charged_microusd: 0 }), /evidence_digest_required/);
    assert.equal(reopened.totals().reserved_microusd, 12_500_000);
  } finally { reopened.close(); }
});
test('USD25 is a review checkpoint; exact USD100 boundary accepted and next refused', t => {
  const { budget } = fixture(t), a = request(), b = request({ world_number: 2 });
  budget.reserve(a); budget.settle(a.operation_id, evidence(12_500_000));
  assert.equal(budget.reserve(b).newly_reserved, true);
  assert.equal(budget.totals().exposure_microusd, 25_000_000);
  budget.settle(b.operation_id, evidence(12_500_000));
  assert.equal(budget.totals().review_checkpoint_reached, true);
  for (let i=0;i<6;i++) {
    const r=request({world_number:3}); budget.reserve(r); budget.settle(r.operation_id,evidence(12_500_000));
  }
  assert.equal(budget.totals().exposure_microusd,100_000_000);
  assert.throws(() => budget.reserve(request({ world_number: 3 })), /campaign_hard_stop/);
  assert.equal(budget.reserve(a).newly_reserved, false);
});
test('one microdollar over hard boundary refused and no reservation created', t => {
  const { budget } = fixture(t), r = request();
  budget.reserve(r); budget.settle(r.operation_id, evidence(87_500_001));
  assert.throws(() => budget.reserve(request()), /campaign_hard_stop/);
  assert.equal(budget.totals().unresolved, 0);
});
test('hard ceiling and real overrun retained without invented zero or settlement replacement', t => {
  const { budget } = fixture(t), r = request();
  assert.throws(() => budget.reserve(request({ input_text_bound_microusd: 90_000_000 })), /campaign_hard_stop/);
  budget.reserve(r);
  assert.equal(budget.settle(r.operation_id, evidence(101_000_000)).hard_ceiling_exceeded, true);
  assert.throws(() => budget.reserve(request()), /campaign_hard_stop/);
  assert.throws(() => budget.settle(r.operation_id, evidence(0)), /settlement_conflict/);
  assert.equal(budget.totals().settled_microusd, 101_000_000);
});
test('shared authority serializes separate connections and forbids reset, copy or changed identity', t => {
  const { root, budget } = fixture(t), second = new CampaignBudget(root, 'synthetic-campaign');
  try {
    const r = request(); budget.reserve(r);
    assert.equal(second.reserve(r).newly_reserved, false);
    assert.throws(() => second.reserve(request()), /campaign_unresolved/);
  } finally { second.close(); }
  assert.throws(() => new CampaignBudget(root, 'synthetic-campaign', { initialize: true }), /EEXIST/);
  assert.throws(() => new CampaignBudget(root, 'different-campaign'), /budget_authority_mismatch/);
  budget.close();
  const other = mkdtempSync(join(process.env.NETCLAW_TEST_TMP, 'campaign-copy-'));
  try {
    assert.throws(() => new CampaignBudget(other, 'synthetic-campaign'), /ENOENT/);
    copyFileSync(join(root, 'campaign-budget.sqlite'), join(other, 'campaign-budget.sqlite'));
    assert.throws(() => new CampaignBudget(other, 'synthetic-campaign'), /budget_authority_mismatch/);
  } finally { rmSync(other, { recursive: true, force: true }); }
});

function admissionFixture(t) {
  const { root, budget } = fixture(t);
  const admission = new CampaignAdmission(root, 'synthetic-campaign');
  const ledger = new Ledger(join(root, 'session-a'));
  const review = ledger.review(projection(), CAMPAIGN_SESSION_POLICY, 12.5, 'google');
  const { operation_id, ...budget_review } = request();
  const input = { operation_id, projection: projection(), review_id: review.id, budget_review };
  t.after(() => { admission.close(); ledger.close(); });
  return { root, budget, admission, ledger, input };
}
test('admission commits authority before marker; local rollback retains original reservation', t => {
  const { budget, admission, ledger, input } = admissionFixture(t);
  ledger.db.exec("CREATE TRIGGER fail_marker BEFORE INSERT ON sessions BEGIN SELECT RAISE(ABORT, 'injected_marker_failure'); END;");
  assert.throws(() => admission.admit(ledger, input), /injected_marker_failure/);
  assert.equal(ledger.list().length, 0);
  assert.equal(budget.totals().reserved_microusd, 12_500_000);
  assert.equal(ledger.db.prepare('SELECT used FROM reviews WHERE id=?').get(input.review_id).used, null);
  ledger.db.exec('DROP TRIGGER fail_marker');
  const recovered = admission.admit(ledger, input);
  assert.equal(recovered.newly_created, true);
  assert.equal(recovered.campaign_reservation.bound_microusd, 12_500_000);
  assert.equal(admission.admit(ledger, input).newly_created, false);
  assert.equal(ledger.list().length, 1);
});
test('alternate session roots, account labels and changed reviews cannot evade shared hold', t => {
  const { root, budget, admission, ledger, input } = admissionFixture(t);
  admission.admit(ledger, input);
  const other = new Ledger(join(root, 'session-b'));
  try {
    // Same exact review/ID copied into another session root remains bound to A.
    const row = ledger.db.prepare('SELECT body FROM reviews WHERE id=?').get(input.review_id);
    other.db.prepare('INSERT INTO reviews(id,body) VALUES(?,?)').run(input.review_id, row.body);
    assert.throws(() => admission.admit(other, input), /request_conflict/);
    assert.throws(() => admission.admit(other, { ...input, operation_id: randomUUID() }), /campaign_unresolved/);
    assert.throws(() => admission.admit(other, { ...input, account: 'alternate' }));
    assert.throws(() => admission.admit(ledger, { ...input, budget_review: { ...input.budget_review, review_sha256: 'b'.repeat(64) } }), /request_conflict/);
    assert.equal(other.list().length, 0);
    assert.equal(budget.totals().unresolved, 1);
  } finally { other.close(); }
});
test('settled ID retrieves original only; missing marker cannot recreate paid session', t => {
  const { budget, admission, ledger, input } = admissionFixture(t);
  ledger.db.exec("CREATE TRIGGER fail_marker BEFORE INSERT ON sessions BEGIN SELECT RAISE(ABORT, 'injected_marker_failure'); END;");
  assert.throws(() => admission.admit(ledger, input), /injected_marker_failure/);
  budget.settle(input.operation_id, evidence(12_500_000));
  ledger.db.exec('DROP TRIGGER fail_marker');
  assert.throws(() => admission.admit(ledger, input), /settled_reservation_no_replay/);
  assert.equal(ledger.list().length, 0);
  assert.equal(budget.totals().settled_microusd, 12_500_000);
});
test('invalid local review reserves nothing; unbound historic marker cannot acquire authority', t => {
  const { budget, admission, ledger, input } = admissionFixture(t);
  assert.throws(() => admission.admit(ledger, { ...input, review_id: randomUUID() }), /review_required/);
  assert.equal(budget.totals().unresolved, 0);
  input.review_id = ledger.review(projection(), POLICY, 15, 'google').id;
  ledger.admit(input.operation_id, input.projection, input.review_id, 'google');
  assert.throws(() => admission.admit(ledger, input), /campaign_binding_required/);
  assert.equal(budget.totals().unresolved, 0);
});
test('admission cannot initialize missing authority or bypass historical single-attempt gate', t => {
  const { root, budget, admission, ledger, input } = admissionFixture(t);
  assert.throws(() => new CampaignAdmission(join(root, 'missing'), 'synthetic-campaign'), /ENOENT/);
  admission.admit(ledger, input);
  budget.settle(input.operation_id, evidence(12_500_000));
  assert.equal(admission.admit(ledger, input).newly_created, false);
  assert.throws(() => admission.admit(ledger, { ...input, operation_id: randomUUID() }), /single_attempt_consumed/);
  assert.equal(budget.totals().unresolved, 0);
});

test('campaign marker records full-duration policy and complete reviewed bound', t => {
  const { admission, ledger, input } = admissionFixture(t);
  const before = Date.now();
  const result = admission.admit(ledger, input);
  assert.equal(result.session_policy.target_seconds, 120);
  assert.equal(result.session_policy.deadline_seconds_from_send, 130);
  assert.equal(result.session_policy.terminal_wait_seconds, 5);
  assert.equal(result.accounting_version, 'campaign-v1');
  assert.equal(result.estimated_video_usd, 12.096);
  assert.equal(result.estimated_usd, 12.5);
  assert.equal(result.reserved_usd, 12.5);
  assert.equal(result.reserved_microusd, 12_500_000);
  assert.ok(Date.parse(result.deadline_at) >= before + 130_000);
  assert.deepEqual(ledger.get(input.operation_id).session_policy, result.session_policy);
});

test('original campaign markers keep historical fields unchanged across restart', t => {
  const { admission, ledger, input } = admissionFixture(t);
  admission.admit(ledger, input);
  // Retained prior-pass local review and marker: never rewrite these on lookup.
  const oldReview = JSON.parse(ledger.db.prepare('SELECT body FROM reviews WHERE id=?').get(input.review_id).body);
  delete oldReview.accounting_version; delete oldReview.reservation_microusd;
  oldReview.policy_sha256 = hash(POLICY); oldReview.allowance_usd = 15;
  const reviewBytes = JSON.stringify(oldReview);
  ledger.db.prepare('UPDATE reviews SET body=? WHERE id=?').run(reviewBytes, input.review_id);
  const historic = ledger.get(input.operation_id);
  delete historic.session_policy;
  delete historic.accounting_version;
  delete historic.estimated_video_usd;
  delete historic.reserved_microusd;
  historic.estimated_usd = 2.016;
  historic.reserved_usd = 15;
  historic.deadline_at = new Date(Date.now() + 30_000).toISOString();
  ledger.save(historic);
  const reopened = new Ledger(ledger.root);
  try {
    assert.deepEqual(admission.admit(reopened, input), { ...historic, newly_created: false });
    assert.deepEqual(reopened.get(input.operation_id), historic);
    assert.equal(reopened.db.prepare('SELECT body FROM reviews WHERE id=?').get(input.review_id).body, reviewBytes);
  } finally { reopened.close(); }
});

test('ordinary admission retains legacy estimate and cannot claim campaign policy', t => {
  const { ledger, input } = admissionFixture(t);
  input.review_id = ledger.review(projection(), POLICY, 15, 'google').id;
  const result = ledger.admit(input.operation_id, input.projection, input.review_id, 'google');
  assert.equal(result.estimated_usd, 2.016);
  assert.equal(result.reserved_usd, 15);
  assert.equal(result.session_policy, undefined);
  assert.equal(result.accounting_version, undefined);
});

test('campaign display follows reviewed input/text bound rather than legacy allowance', t => {
  const { admission, ledger, input } = admissionFixture(t);
  input.review_id = ledger.review(projection(), CAMPAIGN_SESSION_POLICY, 12.346001, 'google').id;
  const result = admission.admit(ledger, { ...input, budget_review: {
    ...input.budget_review, input_text_bound_microusd: 250_001,
  } });
  assert.equal(result.reserved_microusd, 12_346_001);
  assert.equal(result.reserved_usd, 12.346001);
  assert.equal(result.estimated_usd, 12.346001);
});

test('invalid trusted reservation result cannot produce a misleading session marker', t => {
  const { ledger, input } = admissionFixture(t);
  for (const bound of [0, 12_096_000, -1, 12_500_000.5, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => ledger.admit(input.operation_id, input.projection,
      input.review_id, 'google', null, () => ({ bound_microusd: bound })), /invalid_campaign_reservation/);
    assert.equal(ledger.list().length, 0);
  }
  assert.equal(ledger.db.prepare('SELECT used FROM reviews WHERE id=?').get(input.review_id).used, null);
});

test('new campaign admission refuses historical local reviews before reserving', t => {
  const { admission, ledger, input, budget } = admissionFixture(t);
  const historical = ledger.review(projection(), POLICY, 15, 'google');
  const before = ledger.db.prepare('SELECT body,used FROM reviews WHERE id=?').get(historical.id);
  assert.throws(() => admission.admit(ledger, { ...input, review_id: historical.id }), /review_stale/);
  assert.equal(budget.totals().exposure_microusd, 0);
  assert.equal(ledger.list().length, 0);
  assert.deepEqual(ledger.db.prepare('SELECT body,used FROM reviews WHERE id=?').get(historical.id), before);
  assert.throws(() => ledger.admit(input.operation_id, input.projection, input.review_id, 'google'), /review_stale/);
});

test('campaign local review preserves exact microdollars and rejects invalid policy or allowance', t => {
  const { ledger } = admissionFixture(t);
  const r = ledger.review(projection(), CAMPAIGN_SESSION_POLICY, 12.346001, 'google');
  assert.equal(r.accounting_version, 'campaign-v1');
  assert.equal(r.reservation_microusd, 12_346_001);
  assert.equal(r.allowance_usd, 12.346001);
  for (const amount of [0, 12.096, 12.5000001, 25.000001, NaN, Infinity])
    assert.throws(() => ledger.review(projection(), CAMPAIGN_SESSION_POLICY, amount, 'google'), /allowance_insufficient/);
  assert.throws(() => ledger.review(projection(), CAMPAIGN_SESSION_POLICY, 12.5, 'fixture'), /allowance_insufficient/);
  assert.throws(() => ledger.review(projection(), { ...CAMPAIGN_SESSION_POLICY, target_seconds: 20 }, 12.5, 'google'), /invalid_policy/);
});

test('reservation mismatch retains its hold without consuming review or creating marker', t => {
  const { admission, ledger, input, budget } = admissionFixture(t);
  assert.throws(() => admission.admit(ledger, { ...input, budget_review: {
    ...input.budget_review, input_text_bound_microusd: 500_000,
  } }), /invalid_campaign_reservation/);
  assert.equal(budget.totals().reserved_microusd, 12_596_000);
  assert.equal(ledger.list().length, 0);
  assert.equal(ledger.db.prepare('SELECT used FROM reviews WHERE id=?').get(input.review_id).used, null);
  for (const missing of [null, undefined, false])
    assert.throws(() => ledger.admit(input.operation_id, input.projection, input.review_id,
      'google', null, () => missing), /invalid_campaign_reservation/);
  assert.equal(ledger.list().length, 0);
});

test('remote terminal without usage retains full bound and permits only distinct bounded work', t => {
 const {budget,root}=fixture(t),a=request();budget.reserve(a);
 assert.throws(()=>budget.confirmTerminalBound(a.operation_id,{event_type:'local_timeout',terminal_sha256:h,provider_id_sha256:h}),/terminal_receipt_required/);
 assert.throws(()=>budget.reserve(request()),/campaign_unresolved/);
 const terminal={event_type:'interaction.cancelled',terminal_sha256:h,provider_id_sha256:h};
 const totals=budget.confirmTerminalBound(a.operation_id,terminal);
 assert.equal(totals.reserved_microusd,12_500_000);assert.equal(totals.settled_microusd,0);
 assert.equal(totals.unresolved,1);assert.equal(totals.active_unknown,0);
 assert.throws(()=>budget.assertReserved(a),/campaign_terminal_no_replay/);
 const second=new CampaignBudget(root,'synthetic-campaign');
 try {second.reserve(request({world_number:2}));assert.equal(second.totals().exposure_microusd,25_000_000);} finally {second.close();}
 assert.throws(()=>budget.confirmTerminalBound(a.operation_id,{...terminal,terminal_sha256:'b'.repeat(64)}),/terminal_evidence_conflict/);
});
