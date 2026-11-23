import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, realpathSync, mkdirSync, existsSync, writeFileSync, readFileSync } from "node:fs";
import http from "node:http";
import net from "node:net";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { randomUUID } from "node:crypto";
import { createManager } from "../../scripts/genie-worlds/manager.mjs";
import { projection, POLICY } from "../../scripts/genie-worlds/model.mjs";
import { Ledger } from "../../scripts/genie-worlds/ledger.mjs";
async function setup(t) {
  const root = mkdtempSync(
    join(process.env.NETCLAW_TEST_TMP || realpathSync(tmpdir()), "manager-"),
  );
  const m = await createManager({
    root,
    audit: async () =>
      new Promise((r) => setTimeout(() => r({ commit: "fixture-audit" }), 10)),
  });
  t.after(async () => {
    await m.close();
    rmSync(root, { recursive: true, force: true });
  });
  return m;
}
function request(m, path, body) {
  return fetch(m.origin + path, {
    method: body ? "POST" : "GET",
    headers: {
      Authorization: `Bearer ${m.owner}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
}
test("navigation checkpoints require active session, baseline and a subsequent observed frame", { timeout: 10000 }, async (t) => {
  const m = await setup(t), id = randomUUID();
  const review = m.ledger.review(projection(), POLICY, 15, "fixture");
  await request(m, '/v1/sessions', { request_id: id, review_ref: review.id });
  const child = m.workers.get(id);
  const frame = () => new Promise(resolve => {
    const listener = message => { if (message.type === 'frame') { child.off('message', listener); resolve(message); } };
    child.on('message', listener);
  });
  const data = readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg', import.meta.url)).toString('base64');
  const capture = (name, frame_sequence) => request(m, `/v1/sessions/${id}/checkpoint`, { name, data, ...(frame_sequence === undefined ? {} : { frame_sequence }) });
  const before = await frame();
  assert.equal((await capture('navigation', before.sequence)).status, 400, 'baseline required');
  assert.equal((await capture('baseline')).status, 200);
  assert.equal((await capture('navigation')).status, 400, 'frame reference required');
  assert.equal((await capture('navigation', before.sequence)).status, 400, 'pre-baseline frame refused');
  assert.equal((await capture('navigation', 999999)).status, 400, 'unobserved frame refused');
  assert.equal(existsSync(join(m.root, 'artifacts', id, 'navigation.jpg')), false);
  const after = await frame();
  assert.equal((await capture('navigation', after.sequence)).status, 200);
  assert.equal((await capture('navigation', after.sequence)).status, 400, 'immutable capture');
  const evidence = await (await request(m, `/v1/sessions/${id}/evidence`)).json();
  assert.equal(evidence.event_checkpoint.state, 'unconfirmed', 'navigation does not mint event evidence');
  assert.equal(evidence.live_world_proven, false);
  m.ledger.transition(id, 'unknown', { reason: 'fixture_loss' });
  rmSync(join(m.root, 'artifacts', id, 'navigation.jpg'));
  assert.equal((await capture('navigation', after.sequence)).status, 400, 'inactive original session refused');
  await m.close();
  const restarted = await createManager({ root: m.root });
  try { assert.equal((await request(restarted, `/v1/sessions/${id}/checkpoint`, { name: 'navigation', data, frame_sequence: after.sequence })).status, 400); }
  finally { await restarted.close(); }
});
test("event checkpoints require original sent event and subsequent worker frame; receipt survives restart", { timeout: 10000 }, async (t) => {
  const m = await setup(t), id = randomUUID();
  const review = m.ledger.review(projection(), POLICY, 15, "fixture");
  await request(m, '/v1/sessions', { request_id: id, review_ref: review.id });
  const child = m.workers.get(id);
  const frame = () => new Promise(resolve => {
    const listener = message => { if (message.type === 'frame') { child.off('message', listener); resolve(message); } };
    child.on('message', listener);
  });
  const before = await frame();
  const data = readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg', import.meta.url)).toString('base64');
  const capture = (name, frame_sequence) => request(m, `/v1/sessions/${id}/checkpoint`, { name, data, ...(frame_sequence === undefined ? {} : { frame_sequence }) });
  assert.equal((await capture('event')).status, 400, 'direct POST cannot bypass viewer event gating');
  assert.equal((await capture('event', before.sequence)).status, 400);
  child.send({ type: 'event_ready', event_id: projection().event_id });
  child.send({ type: 'event', event_id: projection().event_id });
  await new Promise(resolve => {
    const listener = message => { if (message.type === 'status' && message.session.event_state === 'sent') { child.off('message', listener); resolve(); } };
    child.on('message', listener);
  });
  const noBaseline = await frame();
  assert.equal((await capture('event', noBaseline.sequence)).status, 400, 'sent event still requires baseline');
  assert.equal((await capture('baseline')).status, 200);
  assert.equal((await capture('event', before.sequence)).status, 400, 'old frame cannot be relabeled post-event');
  assert.equal((await capture('event', 999999)).status, 400, 'invented frame refused');
  const after = await frame();
  assert.equal((await capture('event', after.sequence)).status, 200);
  assert.equal((await capture('event', after.sequence)).status, 400, 'immutable checkpoint');
  const evidence = await (await request(m, `/v1/sessions/${id}/evidence`)).json();
  const receipt = evidence.event_checkpoint.receipt;
  assert.equal(evidence.event_checkpoint.state, 'correlated');
  assert.equal(receipt.operation_id, id);
  assert.equal(receipt.event_id, projection().event_id);
  assert.equal(receipt.frame_sequence, after.sequence);
  assert.match(receipt.worker_frame_sha256, /^[a-f0-9]{64}$/);
  assert.equal(receipt.visible_effect, 'unassessed');
  assert.equal(evidence.live_world_proven, false);
  await m.close();
  const restarted = await createManager({ root: m.root });
  try {
    const retained = await (await request(restarted, `/v1/sessions/${id}/evidence`)).json();
    assert.deepEqual(retained.event_checkpoint.receipt, receipt);
    assert.equal(retained.event_checkpoint.state, 'correlated');
    assert.equal(restarted.workers.size, 0);
    writeFileSync(join(m.root, 'artifacts', id, 'event.jpg'), 'tampered');
    const changed = await (await request(restarted, `/v1/sessions/${id}/evidence`)).json();
    assert.equal(changed.event_checkpoint.state, 'incomplete');
    assert.deepEqual(changed.event_checkpoint.receipt, receipt);
  } finally { await restarted.close(); }
});
test("final recording acknowledgement is bounded, immutable and separate from provider evidence", async (t) => {
  const m = await setup(t), id = randomUUID();
  const review = m.ledger.review(projection(), POLICY, 15, "fixture");
  m.ledger.admit(id, projection(), review.id, "fixture");
  const route = `/v1/sessions/${id}`;
  const evidence = async () => (await request(m, route + "/evidence")).json();
  const finalize = size_bytes => request(m, route + "/recording-final", { size_bytes });
  const upload = () => fetch(m.origin + route + "/recording", {
    method: "POST", headers: { Authorization: `Bearer ${m.owner}`, "Content-Type": "video/webm" },
    body: Buffer.from("synthetic-media"),
  });
  assert.equal((await evidence()).recording.state, "unconfirmed");
  assert.equal((await finalize(0)).status, 400);
  assert.equal((await finalize(15)).status, 400);
  assert.equal((await upload()).status, 200);
  assert.equal((await finalize(13)).status, 400);
  assert.equal((await evidence()).recording.state, "unconfirmed");
  const receipt = await (await finalize(15)).json();
  assert.equal(receipt.state, "final_flush_acknowledged", JSON.stringify(receipt));
  assert.deepEqual(await (await finalize(15)).json(), receipt, "same final flush is idempotent");
  assert.equal((await (await upload()).json()).error, "recording_finalized");
  assert.equal((await evidence()).session.terminal_confirmed, false);
  assert.equal((await evidence()).live_world_proven, false);
  writeFileSync(join(m.root, "artifacts", id, "viewer.webm"), "different-media", { mode: 0o600 });
  assert.equal((await evidence()).recording.reason, "recording_artifact_mismatch");
  assert.equal((await (await finalize(15)).json()).error, "recording_receipt_conflict");
  m.ledger.recordingFailure(id, "recording_failed");
  assert.equal(m.ledger.recordingStatus(id).state, "incomplete");
  assert.deepEqual(m.ledger.recordingStatus(id).receipt, receipt.receipt, "failure preserves original receipt");
});
test("host/origin, owner auth and unsupported paid mode are refused", async (t) => {
  const m = await setup(t);
  assert.equal((await fetch(m.origin + "/v1/draft")).status, 403);
  assert.equal(
    (
      await fetch(m.origin + "/v1/draft", {
        headers: {
          Authorization: `Bearer ${m.owner}`,
          Origin: "https://evil.example",
        },
      })
    ).status,
    403,
  );
  assert.equal(
    (
      await request(m, "/v1/reviews", {
        projection_sha256: projection().sha256,
        provider: "google",
      })
    ).status,
    400,
  );
  assert.equal(
    (
      await request(m, "/v1/reviews", {
        projection_sha256: projection().sha256,
        provider: "fixture",
        approved: true,
      })
    ).status,
    400,
  );
});
test("concurrent duplicate starts create one worker and original request is addressable", async (t) => {
  const m = await setup(t);
  const review = await (
    await request(m, "/v1/reviews", {
      projection_sha256: projection().sha256,
      provider: "fixture",
    })
  ).json();
  const id = randomUUID(),
    body = { request_id: id, review_ref: review.id };
  const replies = await Promise.all([
    request(m, "/v1/sessions", body),
    request(m, "/v1/sessions", body),
  ]);
  for (const r of replies) {
    assert.equal(r.status, 200);
    assert.equal((await r.json()).operation_id, id);
  }
  assert.equal(m.workers.size, 1);
  assert.equal(
    (await (await request(m, "/v1/sessions/" + id)).json()).operation_id,
    id,
  );
  await request(m, `/v1/sessions/${id}/stop`, {});
});
test("worker kill remains unknown after manager restart", async (t) => {
  const m = await setup(t);
  const review = await (
    await request(m, "/v1/reviews", {
      projection_sha256: projection().sha256,
      provider: "fixture",
    })
  ).json();
  const id = randomUUID();
  await request(m, "/v1/sessions", { request_id: id, review_ref: review.id });
  m.workers.get(id).kill("SIGKILL");
  await new Promise((r) => setTimeout(r, 100));
  assert.equal(m.ledger.get(id).state, "unknown");
  const r2 = await (
    await request(m, "/v1/reviews", {
      projection_sha256: projection().sha256,
      provider: "fixture",
    })
  ).json();
  assert.equal(
    (
      await request(m, "/v1/sessions", {
        request_id: randomUUID(),
        review_ref: r2.id,
      })
    ).status,
    409,
  );
  await m.close();
  const restarted = await createManager({ root: m.root });
  try {
    assert.equal(restarted.ledger.get(id).state, "unknown");
    const review = await (
      await request(restarted, "/v1/reviews", {
        projection_sha256: projection().sha256,
        provider: "fixture",
      })
    ).json();
    assert.equal(
      (
        await request(restarted, "/v1/sessions", {
          request_id: randomUUID(),
          review_ref: review.id,
        })
      ).status,
      409,
    );
  } finally {
    await restarted.close();
  }
});
test("native audit failure prevents admission and worker launch", async (t) => {
  const root = mkdtempSync(
    join(process.env.NETCLAW_TEST_TMP || realpathSync(tmpdir()), "audit-"),
  );
  const m = await createManager({
    root,
    audit: async () => {
      throw Error("unavailable");
    },
  });
  t.after(async () => {
    await m.close();
    rmSync(root, { recursive: true, force: true });
  });
  const r = await (
    await request(m, "/v1/reviews", {
      projection_sha256: projection().sha256,
      provider: "fixture",
    })
  ).json();
  assert.equal(
    (
      await request(m, "/v1/sessions", {
        request_id: randomUUID(),
        review_ref: r.id,
      })
    ).status,
    400,
  );
  assert.equal(m.workers.size, 0);
  assert.equal(m.ledger.list().length, 0);
});

for (const disconnect of [false, true]) test(`shutdown refuses deferred admission; disconnected=${disconnect}`, async (t) => {
  const root = mkdtempSync(join(process.env.NETCLAW_TEST_TMP || realpathSync(tmpdir()), "closing-audit-"));
  const entered = Promise.withResolvers(), auditResult = Promise.withResolvers();
  const m = await createManager({ root, audit: () => {
    entered.resolve(); return auditResult.promise;
  }});
  t.after(async () => {
    auditResult.resolve({ commit: "synthetic-audit" });
    await m.close(); rmSync(root, { recursive: true, force: true });
  });
  const review = await (await request(m, "/v1/reviews", {
    projection_sha256: projection().sha256, provider: "fixture",
  })).json();
  const reply = Promise.withResolvers();
  const req = http.request(m.origin + "/v1/sessions", {
    method: "POST", headers: { Authorization: `Bearer ${m.owner}`, "Content-Type": "application/json" },
  }, res => {
    let data = ""; res.on("data", chunk => { data += chunk; });
    res.on("end", () => reply.resolve({ status: res.statusCode, body: JSON.parse(data) }));
  });
  req.on("error", () => reply.resolve(null));
  req.end(JSON.stringify({ request_id: randomUUID(), review_ref: review.id }));
  await entered.promise;
  let finished = false;
  const closing = m.close(); closing.then(() => { finished = true; });
  const repeated = m.close();
  if (disconnect) {
    req.destroy(); await reply.promise;
  }
  await new Promise(r => setTimeout(r, 50));
  assert.equal(finished, false, "audit still owns the ledger/lock even after disconnect");
  assert(existsSync(join(root, "manager.lock")));
  auditResult.resolve({ commit: "synthetic-audit" });
  const response = await reply.promise;
  await closing;
  assert.equal(repeated, closing, "all callers share shutdown completion");
  if (!disconnect) assert.deepEqual(response, { status: 503, body: { error: "manager_closing" } });
  assert.equal(m.workers.size, 0);
  assert.equal(existsSync(join(root, "manager.lock")), false);
  const retained = new Ledger(root);
  try { assert.equal(retained.list().length, 0, "no admission, reservation or send marker"); }
  finally { retained.close(); }
});

test("shutdown rejects new admission while preserving original-ID observation and worker drain", async (t) => {
  const m = await setup(t);
  const review = await (await request(m, "/v1/reviews", {
    projection_sha256: projection().sha256, provider: "fixture",
  })).json();
  const id = randomUUID(), input = { request_id: id, review_ref: review.id };
  assert.equal((await request(m, "/v1/sessions", input)).status, 200);
  const child = m.workers.get(id);
  child.kill("SIGSTOP");
  const closing = m.close();
  try {
    const response = await request(m, "/v1/sessions", { ...input, request_id: randomUUID() });
    assert.equal(response.status, 503);
    assert.equal((await response.json()).error, "manager_closing");
    const original = await request(m, "/v1/sessions", input);
    assert.equal(original.status, 200);
    assert.equal((await original.json()).operation_id, id);
    assert.equal(m.ledger.list().length, 1);
    assert.equal(m.workers.get(id), child);
  } finally { child.kill("SIGCONT"); await closing; }
  assert.equal(m.workers.size, 0);
});

test("manager close reaps a frozen owned child and retains unknown after restart", { timeout: 18000 }, async (t) => {
  const m = await setup(t);
  const review = await (await request(m, "/v1/reviews", {
    projection_sha256: projection().sha256, provider: "fixture",
  })).json();
  const id = randomUUID();
  await request(m, "/v1/sessions", { request_id: id, review_ref: review.id });
  const child = m.workers.get(id);
  // SIGSTOP actually prevents IPC stop and deadline execution in the child.
  assert.equal(child.kill("SIGSTOP"), true);
  const exit = new Promise((resolve) => child.once("exit", (code, signal) => resolve({ code, signal })));
  const at = Date.now();
  await m.close();
  assert(Date.now() - at < 15000);
  assert.deepEqual(await exit, { code: null, signal: "SIGKILL" });
  assert.equal(m.workers.size, 0);
  assert.throws(() => process.kill(child.pid, 0), /ESRCH/);
  const retained = new Ledger(m.root);
  try {
    const s = retained.get(id);
    assert.equal(s.state, "unknown");
    assert.equal(s.reason, "manager_cleanup_expired");
    assert.equal(s.usage_state, "reserved");
    assert.equal(s.terminal_receipt, null);
  } finally { retained.close(); }
});

test("actual recording sink failure persists, requests stop, and refuses further chunks", async (t) => {
  const m = await setup(t);
  const review = await (await request(m, "/v1/reviews", {
    projection_sha256: projection().sha256, provider: "fixture",
  })).json();
  const id = randomUUID();
  await request(m, "/v1/sessions", { request_id: id, review_ref: review.id });
  // A directory at the artifact sink causes a real filesystem write failure.
  mkdirSync(join(m.root, "artifacts", id, "viewer.webm"), { recursive: true, mode: 0o700 });
  const upload = () => fetch(`${m.origin}/v1/sessions/${id}/recording`, {
    method: "POST", headers: { Authorization: `Bearer ${m.owner}`, "Content-Type": "video/webm" }, body: "synthetic",
  });
  assert.equal((await upload()).status, 400);
  assert.equal(m.ledger.recordingFailures(id)[0].code, "recording_upload_failed");
  assert.equal((await (await upload()).json()).error, "recording_already_failed");
  assert.equal(m.ledger.recordingFailures(id).length, 1);
  const evidence = await (await request(m, `/v1/sessions/${id}/evidence`)).json();
  assert.equal(evidence.recording_failures[0].code, "recording_upload_failed");
  assert(!evidence.manifest.some((a) => a.mime === "video/webm"));
  const until = Date.now() + 2000;
  while (m.ledger.get(id).state !== "terminal" && Date.now() < until) await new Promise((r) => setTimeout(r, 20));
  assert.equal(m.ledger.get(id).state, "terminal");
  await m.close();
  const retained = new Ledger(m.root);
  try { assert.equal(retained.recordingFailures(id)[0].code, "recording_upload_failed"); }
  finally { retained.close(); }
});

for (const recording of [false, true]) test(`shutdown bounds stalled HTTP body; recording=${recording}`, async (t) => {
  const m = await setup(t);
  const review = m.ledger.review(projection(), POLICY, 15, "fixture");
  const id = randomUUID();
  if (recording) m.ledger.admit(id, projection(), review.id, "fixture");
  const req = http.request(m.origin + (recording ? `/v1/sessions/${id}/recording` : "/v1/sessions"), {
    method: "POST", headers: { Authorization: `Bearer ${m.owner}`,
      "Content-Type": recording ? "video/webm" : "application/json", "Content-Length": 100 },
  });
  req.on("error", () => {});
  req.write("x"); // Complete headers, deliberately unfinished body.
  await new Promise(r => setTimeout(r, 50));
  let finished = false;
  const closing = m.close().then(() => { finished = true; });
  try {
    await Promise.race([closing, new Promise(r => setTimeout(r, 1800))]);
    assert.equal(finished, true, "an incomplete HTTP body must not indefinitely own shutdown");
  } finally { req.destroy(); await closing; }
  assert.equal(existsSync(join(m.root, "manager.lock")), false);
  const retained = new Ledger(m.root);
  try {
    assert.equal(retained.list().length, recording ? 1 : 0);
    if (recording) {
      assert.equal(retained.recordingFailures(id)[0].code, "recording_upload_failed",
        "aborted upload handler records failure before the ledger closes");
      assert.equal(existsSync(join(m.root, "artifacts", id, "viewer.webm")), false);
    }
  } finally { retained.close(); }
});

test("shutdown allows an in-flight evidence upload to finish inside HTTP grace", async (t) => {
  const m = await setup(t);
  const review = m.ledger.review(projection(), POLICY, 15, "fixture");
  const id = randomUUID(); m.ledger.admit(id, projection(), review.id, "fixture");
  const response = Promise.withResolvers();
  const req = http.request(`${m.origin}/v1/sessions/${id}/recording`, {
    method: "POST", headers: { Authorization: `Bearer ${m.owner}`,
      "Content-Type": "video/webm", "Content-Length": 2 },
  }, res => { res.resume(); res.on("end", () => response.resolve(res.statusCode)); });
  req.on("error", response.reject); req.write("x");
  await new Promise(r => setTimeout(r, 50));
  const closing = m.close();
  await new Promise(r => setTimeout(r, 100));
  assert(existsSync(join(m.root, "manager.lock")));
  req.end("y");
  assert.equal(await response.promise, 200);
  await closing;
  assert(existsSync(join(m.root, "artifacts", id, "viewer.webm")));
  const retained = new Ledger(m.root);
  try { assert.equal(retained.recordingFailures(id).length, 0); }
  finally { retained.close(); }
});

for (const upgraded of [false, true]) test(`shutdown bounds silent socket; upgraded=${upgraded}`, async (t) => {
  const m = await setup(t);
  const address = new URL(m.origin);
  const socket = net.createConnection({ host: address.hostname, port: Number(address.port) });
  const closed = new Promise(resolve => socket.once("close", resolve));
  socket.on("error", () => {});
  await new Promise(resolve => socket.once("connect", resolve));
  if (upgraded) {
    const review = m.ledger.review(projection(), POLICY, 15, "fixture");
    const id = randomUUID(); m.ledger.admit(id, projection(), review.id, "fixture");
    const handshake = new Promise(resolve => socket.once("data", resolve));
    socket.write(`GET /v1/view/${id} HTTP/1.1\r\nHost: ${address.host}\r\nOrigin: ${m.origin}\r\nAuthorization: Bearer ${m.owner}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: c3ludGhldGljLXRlc3QxOA==\r\nSec-WebSocket-Version: 13\r\n\r\n`);
    assert.match((await handshake).toString(), /101 Switching Protocols/);
    // Raw peer deliberately never acknowledges the websocket close frame.
    socket.resume();
  } else {
    socket.write("POST /v1/sessions HTTP/1.1\r\nHost: ");
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  let finished = false;
  const closing = m.close().then(() => { finished = true; });
  try {
    await Promise.race([closing, new Promise(resolve => setTimeout(resolve, 1800))]);
    assert.equal(finished, true);
    await Promise.race([closed, new Promise((_, reject) => setTimeout(() => reject(Error("socket_not_closed")), 500))]);
  } finally { socket.destroy(); await closing; }
});
