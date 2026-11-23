import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, realpathSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { randomUUID } from "node:crypto";
import { Ledger } from "../../scripts/genie-worlds/ledger.mjs";
import { projection, POLICY, CAMPAIGN_SESSION_POLICY, sessionPolicy } from "../../scripts/genie-worlds/model.mjs";
import { FixtureProvider } from "../../scripts/genie-worlds/fixture-provider.mjs";
import { createSessionWorker } from "../../scripts/genie-worlds/worker.mjs";
const fast = {
  ...POLICY,
  target_seconds: 0.15,
  deadline_seconds_from_send: 0.3,
  first_frame_timeout_seconds: 0.05,
  terminal_wait_seconds: 0.05,
  viewer_lost_seconds: 0.2,
  manager_lost_seconds: 0.2,
};
function setup(t, options = {}, policy = fast) {
  const root = mkdtempSync(
    join(process.env.NETCLAW_TEST_TMP || realpathSync(tmpdir()), "worker-"),
  );
  const ledger = new Ledger(root);
  t.after(() => {
    ledger.close();
    rmSync(root, { recursive: true, force: true });
  });
  const p = projection(),
    id = randomUUID();
  ledger.admit(id, p, ledger.review(p, POLICY, 15, "fixture").id, "fixture");
  const provider = new FixtureProvider({ interval: 5, ...options });
  const emitted = [];
  const worker = createSessionWorker({
    ledger,
    id,
    open: async () => provider,
    policy,
    emit: (e) => emitted.push(e),
  });
  return { ledger, id, provider, worker, emitted };
}
test("target requests complete and only provider receipt ends session", async (t) => {
  const x = setup(t);
  await x.worker.run();
  assert.equal(x.ledger.get(x.id).state, "terminal");
  assert.equal(x.ledger.get(x.id).usage_state, "reconciled");
  assert(x.emitted.some((e) => e.type === "frame"));
});
test("successful complete method without receipt stays unknown and held", async (t) => {
  const x = setup(t, { noTerminal: true });
  await x.worker.run();
  assert.equal(x.ledger.get(x.id).state, "unknown");
  assert.equal(x.ledger.get(x.id).reason, "terminal_receipt_missing");
});
test("terminal without usage remains unsettled", async (t) => {
  const x = setup(t, { noUsage: true });
  await x.worker.run();
  assert.equal(x.ledger.get(x.id).state, "terminal");
  assert.equal(x.ledger.get(x.id).usage_state, "unsettled");
});
test("viewer loss terminates without waiting for target", async (t) => {
  const x = setup(
    t,
    {},
    {
      ...fast,
      target_seconds: 1,
      deadline_seconds_from_send: 2,
      viewer_lost_seconds: 0.06,
    },
  );
  await x.worker.run();
  assert.equal(x.ledger.get(x.id).reason, "viewer_lost");
  assert.equal(x.ledger.get(x.id).state, "terminal");
});
test("no first frame is stopped and can receive terminal before active", async (t) => {
  const x = setup(t, { noFrames: true });
  await x.worker.run();
  assert.equal(x.ledger.get(x.id).reason, "first_frame_timeout");
  assert.equal(x.ledger.get(x.id).state, "terminal");
});
test("event requires operator readiness and sends once", async (t) => {
  const x = setup(t);
  const run = x.worker.run();
  await new Promise((r) => setTimeout(r, 20));
  await x.worker.control({ type: "event", event_id: projection().event_id });
  assert.equal(x.provider.sent.filter((e) => typeof e === "string").length, 0);
  await x.worker.control({ type: "event_ready" });
  await x.worker.control({ type: "event", event_id: projection().event_id });
  await x.worker.control({ type: "event_ready" });
  await x.worker.control({ type: "event", event_id: projection().event_id });
  assert.equal(x.provider.sent.filter((e) => typeof e === "string").length, 1);
  await run;
});

// Synthetic ledger records only: no live packet, credential or provider access.
function campaignRecord() {
  const bound = 12_106_000, sent = Date.now();
  return { provider: 'google', state: 'create_pending', usage_state: 'reserved',
    provider_id: null, accounting_version: 'campaign-v1',
    campaign_reservation: { bound_microusd: bound }, session_policy: CAMPAIGN_SESSION_POLICY,
    reserved_microusd: bound, reserved_usd: bound / 1e6, estimated_usd: bound / 1e6,
    estimated_video_usd: 12.096, send_marked_at: new Date(sent).toISOString(),
    deadline_at: new Date(sent + 130000).toISOString() };
}
test('worker selects explicit full campaign policy while preserving historical fixture policy', () => {
  assert.equal(sessionPolicy(campaignRecord()).target_seconds, 120);
  assert.equal(sessionPolicy(campaignRecord()).deadline_seconds_from_send, 130);
  assert.equal(sessionPolicy({provider:'fixture'}), POLICY);
  assert.throws(() => sessionPolicy({provider:'google', state:'create_pending'}), /campaign_session_required/);
});
test('campaign worker refuses missing, altered or underfunded record policy', () => {
  for (const patch of [
    {accounting_version:undefined}, {session_policy:POLICY},
    {session_policy:{...CAMPAIGN_SESSION_POLICY, terminal_wait_seconds:0}},
    {reserved_microusd:1}, {reserved_usd:15}, {estimated_usd:2.016},
    {estimated_video_usd:0}, {deadline_at:'invalid'},
    {deadline_at:new Date(Date.now()+30000).toISOString()},
    {deadline_at:new Date(Date.now()+150000).toISOString()},
  ]) assert.throws(() => sessionPolicy({...campaignRecord(), ...patch}), /campaign_session_/);
  assert.throws(() => sessionPolicy({...campaignRecord(), provider:'fixture'}), /fixture_campaign_mismatch/);
});
test('stored campaign policy runs fixture transport through explicit stop and terminal evidence', async t => {
  const root = mkdtempSync(join(process.env.NETCLAW_TEST_TMP || realpathSync(tmpdir()), 'campaign-worker-'));
  const ledger = new Ledger(root), id = randomUUID(), p = projection();
  t.after(() => { ledger.close(); rmSync(root, { recursive:true, force:true }); });
  const review = ledger.review(p, CAMPAIGN_SESSION_POLICY, 12.106, 'google');
  // Synthetic reservation seam: this does not qualify reviewed live admission.
  ledger.admit(id, p, review.id, 'google', null, () => ({bound_microusd:12_106_000}));
  const provider = new FixtureProvider({interval:5});
  let worker, opens = 0;
  worker = createSessionWorker({ledger, id, open:async()=>{opens++;return provider;},
    emit:e=>{if(e.type === 'frame') void worker.stop();}});
  await worker.run();
  assert.equal(opens, 1);
  assert.equal(ledger.get(id).state, 'terminal');
  assert.equal(ledger.get(id).session_policy.target_seconds, 120);
  assert.equal(ledger.get(id).reason, 'user_stop');
});
test('worker refuses live clock overrides before opening transport', () => {
  let opens = 0;
  assert.throws(() => createSessionWorker({ledger:{get:campaignRecord}, id:'synthetic',
    open:async()=>{opens++;}, policy:fast}), /live_policy_override/);
  assert.equal(opens, 0);
});
test('worker revalidates campaign record immediately before opening transport', async () => {
  for (const patch of [
    {session_policy:POLICY}, {state:'unknown'}, {provider_id:'already-sent'},
    {usage_state:'reconciled'}, {campaign_reservation:{bound_microusd:12_106_000, packet_sha256:'changed'}},
  ]) {
    let record = campaignRecord(), opens = 0;
    const worker = createSessionWorker({ledger:{get:()=>structuredClone(record)}, id:'synthetic',
      open:async()=>{opens++;}});
    record = {...record, ...patch};
    await assert.rejects(worker.run(), /campaign_session_/);
    assert.equal(opens, 0);
  }
});
