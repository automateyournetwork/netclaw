import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, realpathSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { randomUUID } from "node:crypto";
import { Ledger } from "../../scripts/genie-worlds/ledger.mjs";
import { projection, POLICY } from "../../scripts/genie-worlds/model.mjs";
import { createSessionWorker } from "../../scripts/genie-worlds/worker.mjs";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const forever = () => new Promise(() => {});
const policy = { ...POLICY, target_seconds: 10, deadline_seconds_from_send: 0.15,
  first_frame_timeout_seconds: 10, terminal_wait_seconds: 0.075,
  viewer_lost_seconds: 10, manager_lost_seconds: 10 };
function setup(t, { send = async () => {}, lateTerminal = false, noUsage = false,
  stalledComplete = false, stalledOpen = false, openDelay = 0, policyPatch = {} } = {}) {
  const root = mkdtempSync(join(process.env.NETCLAW_TEST_TMP || realpathSync(tmpdir()), "recovery-"));
  const ledger = new Ledger(root), id = randomUUID(), p = projection();
  ledger.admit(id, p, ledger.review(p, POLICY, 15, "fixture").id, "fixture");
  t.after(() => { ledger.close(); rmSync(root, { recursive: true, force: true }); });
  let complete = 0, cancel = 0, setupCount = 0, opens = 0, deliver;
  const terminal = new Promise((r) => { deliver = r; });
  const provider = {
    id: "synthetic-recovery",
    async send(event) { if (event.event_type === "world_setup") setupCount++; return send(event); },
    complete() {
      complete++;
      if (lateTerminal) setTimeout(() => deliver({ event_type: "interaction.completed", status: "completed",
        ...(noUsage ? {} : { usage: { video_output_tokens: 0 } }) }), 25);
      return stalledComplete ? forever() : Promise.resolve();
    },
    cancel() { cancel++; return forever(); },
    async *receive() {
      yield { event_type: "step.delta", delta: { type: "video", data: Buffer.from([255, 216]).toString("base64") } };
      const receipt = await terminal;
      // A trailing frame after uncertainty must not stop receipt collection or
      // reactivate controls, even when it precedes the terminal event.
      yield { event_type: "step.delta", delta: { type: "video", data: "/9g=" } };
      yield receipt;
    },
  };
  let frame;
  const active = new Promise((r) => { frame = r; });
  const worker = createSessionWorker({ ledger, id, policy: { ...policy, ...policyPatch },
    open: () => { opens++; return stalledOpen ? forever() : openDelay ? sleep(openDelay).then(() => provider) : provider; },
    emit: (e) => { if (e.type === "frame") frame(); } });
  return { worker, ledger, id, active, counts: () => ({ complete, cancel, setupCount, opens }) };
}
async function within(promise) {
  let timer;
  try { await Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(Error("local worker did not finish")), 1000);
  })]); } finally { clearTimeout(timer); }
}
test("recording failure never settles unknown or missing usage and is bounded/idempotent", async (t) => {
  for (const noUsage of [false, true]) {
    const x = setup(t, { lateTerminal: noUsage, noUsage });
    const run = x.worker.run(); await x.active;
    x.ledger.recordingFailure(x.id, "recording_failed");
    x.ledger.recordingFailure(x.id, "recording_failed");
    assert.throws(() => x.ledger.recordingFailure(x.id, "arbitrary private text"), /invalid_recording_failure/);
    await within(x.worker.control({ type: "stop" })); await within(run);
    const s = x.ledger.get(x.id);
    assert.equal(x.ledger.recordingFailures(x.id).length, 1);
    assert.equal(s.state, noUsage ? "terminal" : "unknown");
    assert.equal(s.usage_state, noUsage ? "unsettled" : "reserved");
    for (const provider of ["fixture", "google"]) {
      const p = projection(), review = x.ledger.review(p, POLICY, 15, provider);
      assert.throws(() => x.ledger.admit(randomUUID(), p, review.id, provider), /active_or_unsettled/);
    }
  }
});
function held(x) {
  const s = x.ledger.get(x.id);
  assert.equal(s.state, "unknown");
  assert.equal(s.terminal_receipt, null);
  assert.equal(s.usage_state, "reserved");
  for (const provider of ["fixture", "google"]) {
    const p = projection(), review = x.ledger.review(p, POLICY, 15, provider);
    assert.throws(() => x.ledger.admit(randomUUID(), p, review.id, provider), /active_or_unsettled/);
  }
}
test("rejected control + blocked receive/cancel completes locally and preserves hold", async (t) => {
  const x = setup(t, { send: async (e) => { if (e.action === "key_down") throw Error("synthetic loss"); } });
  const run = x.worker.run(); await x.active;
  await x.worker.control({ type: "key", key: "w", down: true });
  await within(run);
  held(x);
  assert.equal(x.ledger.get(x.id).reason, "control_send_unknown");
  assert.deepEqual(x.counts(), { complete: 1, cancel: 1, setupCount: 1, opens: 1 });
});
test("blocked key sends cannot queue user stop; complete and cancel can also hang", async (t) => {
  const x = setup(t, { send: (e) => e.event_type === "user_action" ? forever() : Promise.resolve(), stalledComplete: true });
  const run = x.worker.run(); await x.active;
  const control = x.worker.control({ type: "key", key: "w", down: true });
  await sleep(5);
  const stop = x.worker.control({ type: "stop" });
  await within(Promise.all([run, control, stop]));
  held(x); assert.equal(x.counts().complete, 1); assert.equal(x.counts().cancel, 1);
});
for (const noUsage of [false, true]) test(`late terminal after unknown, missing usage=${noUsage}`, async (t) => {
  const x = setup(t, { lateTerminal: true, noUsage,
    send: async (e) => { if (e.action === "key_down") throw Error("synthetic loss"); } });
  const run = x.worker.run(); await x.active;
  await x.worker.control({ type: "key", key: "w", down: true });
  assert.equal(x.ledger.get(x.id).state, "unknown");
  await within(run);
  assert.equal(x.ledger.get(x.id).state, "terminal");
  assert.equal(x.ledger.get(x.id).usage_state, noUsage ? "unsettled" : "reconciled");
  assert.equal(x.counts().complete, 1);
});
test("manager heartbeat loss stops a stalled setup and receiver", async (t) => {
  const x = setup(t, { send: forever, policyPatch: { manager_lost_seconds: 0.05 } });
  await within(x.worker.run()); held(x);
  assert.equal(x.counts().complete, 1); assert.equal(x.counts().cancel, 1);
});
test("never-returning create is locally bounded without replacement creation", async (t) => {
  const x = setup(t, { stalledOpen: true });
  await within(x.worker.run()); held(x);
  assert.deepEqual(x.counts(), { complete: 0, cancel: 0, setupCount: 0, opens: 1 });
});
test("setup rejection stops immediately while retaining unknown and reservation", async (t) => {
  const x = setup(t, { send: async () => { throw Error("setup rejected"); } });
  await within(x.worker.run()); held(x);
  assert.equal(x.ledger.get(x.id).reason, "setup_send_unknown");
  assert.equal(x.counts().complete, 1);
});
test("creation returning after local expiry cancels original transport without setup or ledger mutation", async (t) => {
  const x = setup(t, { openDelay: 400 });
  await within(x.worker.run()); held(x);
  const snapshot = x.ledger.get(x.id);
  await sleep(225);
  assert.deepEqual(x.ledger.get(x.id), snapshot);
  assert.deepEqual(x.counts(), { complete: 0, cancel: 1, setupCount: 0, opens: 1 });
});

for (const lateTerminal of [false, true]) test(`focus-loss release rejection stops immediately; late terminal=${lateTerminal}`, async (t) => {
  const sent = [];
  const x = setup(t, { lateTerminal, noUsage: true,
    policyPatch: { deadline_seconds_from_send: 10 },
    send: async (e) => {
      if (e.event_type !== "user_action") return;
      sent.push([e.action, e.input]);
      if (e.action === "key_up" && e.input === "key_w") throw Error("synthetic release lost");
    } });
  const run = x.worker.run(); await x.active;
  // Always drain the original worker, including when the regression fails.
  try {
    for (const key of ["w", "a"]) await x.worker.control({ type: "key", key, down: true });
    await x.worker.control({ type: "release" });
    assert.equal(x.ledger.get(x.id).state, "unknown");
    assert.equal(x.ledger.get(x.id).reason, "release_transport_lost");
    assert.equal(x.counts().complete, 1);
    await x.worker.control({ type: "key", key: "s", down: true });
    await x.worker.control({ type: "release" });
    await within(run);
    assert.deepEqual(sent, [["key_down", "key_w"], ["key_down", "key_a"],
      ["key_up", "key_w"], ["key_up", "key_a"]]);
    const audit = x.ledger.db.prepare("SELECT body FROM audit ORDER BY seq").all().map((r) => JSON.parse(r.body));
    assert.deepEqual(audit.filter((e) => e.type === "key_release_attempt").map((e) => e.key), ["w", "a"]);
    assert.deepEqual(audit.filter((e) => e.type === "key_release_unknown").map((e) => e.key), ["w"]);
    if (lateTerminal) {
      assert.equal(x.ledger.get(x.id).state, "terminal");
      assert.equal(x.ledger.get(x.id).usage_state, "unsettled");
      const p = projection(), review = x.ledger.review(p, POLICY, 15, "fixture");
      assert.throws(() => x.ledger.admit(randomUUID(), p, review.id, "fixture"), /active_or_unsettled/);
    } else held(x);
    assert.equal(x.counts().opens, 1);
  } finally { await x.worker.stop(); await within(run); }
});

test("successful focus-loss release keeps navigation active without duplicate key-up", async (t) => {
  const sent = [];
  const x = setup(t, { lateTerminal: true, policyPatch: { deadline_seconds_from_send: 10 },
    send: async (e) => { if (e.event_type === "user_action") sent.push([e.action, e.input]); } });
  const run = x.worker.run(); await x.active;
  try {
    await x.worker.control({ type: "key", key: "w", down: true });
    await x.worker.control({ type: "release" });
    await x.worker.control({ type: "release" });
    assert.equal(x.ledger.get(x.id).state, "active");
    assert.equal(x.counts().complete, 0);
    await x.worker.control({ type: "key", key: "a", down: true });
    await x.worker.stop(); await within(run);
    assert.deepEqual(sent, [["key_down", "key_w"], ["key_up", "key_w"],
      ["key_down", "key_a"], ["key_up", "key_a"]]);
    assert.equal(x.ledger.get(x.id).usage_state, "reconciled");
  } finally { await x.worker.stop(); await within(run); }
});

test("blocked focus-loss release cannot block stop and late rejection cannot mutate the ledger", async (t) => {
  let rejectRelease, attempts = 0;
  const x = setup(t, { policyPatch: { deadline_seconds_from_send: 10 },
    send: (e) => {
      if (e.action !== "key_up") return Promise.resolve();
      attempts++;
      return new Promise((_, reject) => { rejectRelease = reject; });
    } });
  const run = x.worker.run(); await x.active;
  try {
    await x.worker.control({ type: "key", key: "w", down: true });
    const release = x.worker.control({ type: "release" });
    await sleep(5);
    await x.worker.control({ type: "stop" });
    await within(Promise.all([run, release]));
    held(x);
    const before = x.ledger.db.prepare("SELECT * FROM audit ORDER BY seq").all();
    assert.equal(before.map((r) => JSON.parse(r.body)).filter((e) => e.type === "key_release_attempt" && e.key === "w").length, 1);
    rejectRelease(Error("late synthetic rejection")); await sleep(5);
    assert.deepEqual(x.ledger.db.prepare("SELECT * FROM audit ORDER BY seq").all(), before);
    assert.equal(attempts, 1);
    assert.equal(x.counts().complete, 1);
  } finally { await x.worker.stop(); await within(run); }
});
