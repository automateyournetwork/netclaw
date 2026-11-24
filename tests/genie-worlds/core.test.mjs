import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, statSync, mkdirSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import {
  projection,
  validateProjection,
  POLICY,
  hash,
} from "../../scripts/genie-worlds/model.mjs";
import { Ledger } from "../../scripts/genie-worlds/ledger.mjs";
const temp = () =>
  mkdtempSync(join(process.env.NETCLAW_TEST_TMP || tmpdir(), "genie-test-"));
function setup(t) {
  const root = temp();
  t.after(() => rmSync(root, { recursive: true, force: true }));
  return { root, db: new Ledger(root) };
}
test("only exact independent synthetic projection is eligible", () => {
  const p = projection();
  assert.equal(p.classification, "synthetic");
  assert.equal(validateProjection(p), true);
  assert.throws(
    () => validateProjection({ ...p, classification: "private" }),
    /projection/,
  );
  assert.throws(
    () => validateProjection({ ...p, text: "renamed private topology" }),
    /projection/,
  );
  assert.throws(
    () => validateProjection({ ...p, api_key: "fake" }),
    /projection/,
  );
  assert.throws(() => projection("private-snapshot"), /fixture/);
});
test("private ownership and duplicate operation survive a reopened database", (t) => {
  const { root, db } = setup(t);
  const p = projection(),
    review = db.review(p, POLICY, 15, "fixture");
  const id = randomUUID();
  const a = db.admit(id, p, review.id, "fixture");
  assert.equal(a.operation_id, id);
  assert.equal(db.admit(id, p, review.id, "fixture").operation_id, id);
  assert.throws(() => db.admit(id, p, review.id, "google"), /conflict/);
  db.close();
  const reopened = new Ledger(root);
  t.after(() => reopened.close());
  assert.equal(reopened.get(id).state, "create_pending");
  assert.equal(statSync(join(root, "sessions.sqlite")).mode & 0o777, 0o600);
  const r = reopened.review(p, POLICY, 15, "fixture");
  assert.throws(
    () => reopened.admit(randomUUID(), p, r.id, "fixture"),
    /unsettled/,
  );
});
test("unknown and absent usage retain reservation; valid terminal usage settles same operation", (t) => {
  const { db } = setup(t);
  t.after(() => db.close());
  const p = projection(),
    r = db.review(p, POLICY, 15, "fixture"),
    id = randomUUID();
  db.admit(id, p, r.id, "fixture");
  db.transition(id, "unknown", { reason: "worker_lost" });
  assert.equal(db.get(id).usage_state, "reserved");
  db.terminal(id, { event_type: "interaction.completed", status: "completed" });
  assert.equal(db.get(id).usage_state, "unsettled");
  assert.throws(
    () =>
      db.admit(
        randomUUID(),
        p,
        db.review(p, POLICY, 15, "fixture").id,
        "fixture",
      ),
    /unsettled/,
  );
  db.terminal(id, {
    event_type: "interaction.completed",
    status: "completed",
    usage: { video_output_tokens: 120 },
  });
  assert.equal(db.get(id).usage_state, "reconciled");
  assert.throws(() => db.transition(id, "active"), /transition/);
  db.admit(randomUUID(), p, db.review(p, POLICY, 15, "fixture").id, "fixture");
});
test("review is bound to provider and policy; no paid admission through fixture approval", (t) => {
  const { db } = setup(t);
  t.after(() => db.close());
  const p = projection(),
    r = db.review(p, POLICY, 15, "fixture");
  assert.throws(() => db.admit(randomUUID(), p, r.id, "google"), /review/);
  assert.throws(
    () => db.review(p, { ...POLICY, target_seconds: 120 }, 15, "fixture"),
    /policy/,
  );
  assert.throws(() => db.review(p, POLICY, 1, "fixture"), /allowance/);
  assert.equal(hash({ b: 2, a: 1 }), hash({ a: 1, b: 2 }));
});
test("send-once event identity and setup terminal events are representable", (t) => {
  const { db } = setup(t);
  t.after(() => db.close());
  const p = projection(),
    id = randomUUID();
  db.admit(id, p, db.review(p, POLICY, 15, "fixture").id, "fixture");
  db.transition(id, "active");
  assert.equal(db.claimEvent(id, p.event_id), true);
  assert.equal(db.claimEvent(id, p.event_id), false);
  db.transition(id, "stop_requested");
  assert.throws(() => db.claimEvent(id, "another"), /event/);
  db.terminal(id, {
    event_type: "interaction.completed",
    usage: { video_output_tokens: 0 },
  });
  assert.equal(db.get(id).state, "terminal");
});
test("symlink state root is refused", (t) => {
  const root = temp();
  t.after(() => rmSync(root, { recursive: true, force: true }));
  mkdirSync(join(root, "real"));
  symlinkSync(join(root, "real"), join(root, "alias"));
  assert.throws(() => new Ledger(join(root, "alias")), /symlink/);
});
test("unrelated or invalid usage does not settle an operation", (t) => {
  const { db } = setup(t);
  t.after(() => db.close());
  const p = projection(),
    id = randomUUID();
  db.admit(id, p, db.review(p, POLICY, 15, "fixture").id, "fixture");
  db.terminal(id, {
    event_type: "interaction.completed",
    usage: { unrelated: 10 },
  });
  assert.equal(db.get(id).usage_state, "unsettled");
  db.terminal(id, {
    event_type: "interaction.completed",
    usage: {
      total_output_tokens: 10,
      output_tokens_by_modality: [{ modality: "video", tokens: 10 }],
    },
  });
  assert.equal(db.get(id).usage_state, "reconciled");
});
