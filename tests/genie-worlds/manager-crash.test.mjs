import test from 'node:test';
import assert from 'node:assert/strict';
import { fork, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { once } from 'node:events';
import { mkdtempSync, readFileSync, writeFileSync, rmSync, unlinkSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { createManager } from '../../scripts/genie-worlds/manager.mjs';
import { projection, POLICY } from '../../scripts/genie-worlds/model.mjs';
const run = promisify(execFile);
const request = (m, path, body) => fetch(m.origin + path, {
  method: body ? 'POST' : 'GET', headers: { Authorization: `Bearer ${m.owner}`, 'Content-Type': 'application/json' },
  ...(body ? { body: JSON.stringify(body) } : {}),
});

if (process.argv[2] === '--crash-fixture') {
  const root = process.argv[3];
  const survivingWorker = process.argv[4] === 'surviving-worker';
  const m = await createManager({ root, snapshotRegistryPath: null });
  const id = randomUUID(), review = m.ledger.review(projection(), POLICY, 15, 'fixture');
  const draftResponse = await request(m, '/v1/drafts', { request_id: randomUUID(), synthetic_fixture_id: 'synthetic-museum-v1' });
  const draft = await draftResponse.json();
  assert.equal(draftResponse.status, 200, JSON.stringify(draft));
  const start = { request_id: id, review_ref: review.id, projection_ref: draft.projection_ref };
  assert.equal((await request(m, '/v1/sessions', start)).status, 200);
  const worker = m.workers.get(id);
  const frame = async () => { for (;;) { const [message] = await once(worker, 'message'); if (message.type === 'frame') return message; } };
  await frame();
  const data = readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg', import.meta.url)).toString('base64');
  assert.equal((await request(m, `/v1/sessions/${id}/checkpoint`, { name: 'baseline', data })).status, 200);
  worker.send({ type: 'event_ready', event_id: projection().event_id });
  worker.send({ type: 'event', event_id: projection().event_id });
  for (;;) { const [message] = await once(worker, 'message'); if (message.type === 'status' && message.session.event_state === 'sent') break; }
  const after = await frame();
  // Test-only seam: the real HTTP handler has saved/fsynced the JPEG but has
  // not entered the receipt transaction. In the surviving-worker scenario,
  // IPC disconnect must let the original worker persist its terminal receipt.
  m.ledger.recordEventCheckpoint = () => {
    if (!survivingWorker) process.kill(worker.pid, 'SIGSTOP');
    writeFileSync(join(root, 'crash-boundary.json'), JSON.stringify({ start, worker_pid: worker.pid,
      session: m.ledger.get(id), event_file_bytes: readFileSync(join(root, 'artifacts', id, 'event.jpg')).length }), { mode: 0o600 });
    process.kill(process.pid, 'SIGKILL');
  };
  await request(m, `/v1/sessions/${id}/checkpoint`, { name: 'event', data, frame_sequence: after.sequence });
  throw Error('crash seam was not reached');
} else {
  for (const survivingWorker of [false, true]) test(`SIGKILL after event JPEG with ${survivingWorker ? 'surviving' : 'unavailable'} worker preserves original evidence through actual MCP`, {
    skip: !process.env.NETCLAW_MCP_PYTHON || !process.env.NETCLAW_TEST_TMP, timeout: 20000,
  }, async t => {
    const root = mkdtempSync(join(process.env.NETCLAW_TEST_TMP, 'manager-crash-'));
    let child, recovered;
    t.after(async () => {
      try { if (child?.pid) { try { process.kill(-child.pid, 'SIGKILL'); } catch (e) { if (e.code !== 'ESRCH') throw e; } } }
      finally { try { await recovered?.close(); } finally { rmSync(root, { recursive: true, force: true }); } }
    });
    child = fork(fileURLToPath(import.meta.url), ['--crash-fixture', root, survivingWorker ? 'surviving-worker' : 'unavailable-worker'], {
      execPath: process.execPath, execArgv: [], detached: true,
      stdio: ['ignore', 'ignore', 'pipe', 'ipc'], env: { PATH: process.env.PATH },
    });
    let stderr = ''; child.stderr.on('data', x => { stderr += x; });
    const [code, signal] = await once(child, 'exit');
    assert.equal(code, null, stderr); assert.equal(signal, 'SIGKILL', stderr);
    const boundary = JSON.parse(readFileSync(join(root, 'crash-boundary.json')));
    assert(boundary.event_file_bytes > 0);
    assert.equal(boundary.session.event_state, 'sent');
    assert.equal(boundary.session.terminal_receipt, null);
    // Only the unavailable-worker scenario kills the owned group. Otherwise
    // observe the original worker exit itself after its manager IPC disconnects.
    if (!survivingWorker) process.kill(-child.pid, 'SIGKILL');
    for (let i = 0; i < 200; i++) {
      try { process.kill(boundary.worker_pid, 0); } catch (e) { if (e.code === 'ESRCH') break; throw e; }
      await new Promise(r => setTimeout(r, 10));
    }
    assert.throws(() => process.kill(boundary.worker_pid, 0), { code: 'ESRCH' });
    await assert.rejects(createManager({ root, snapshotRegistryPath: null }), /manager_lock_exists_review_required/);
    const lock = JSON.parse(readFileSync(join(root, 'manager.lock')));
    assert.equal(lock.pid, child.pid);
    assert.throws(() => process.kill(lock.pid, 0), { code: 'ESRCH' });
    unlinkSync(join(root, 'manager.lock'));
    recovered = await createManager({ root, snapshotRegistryPath: null });
    const call = async (name, args) => {
      const result = await run(process.env.NETCLAW_MCP_PYTHON,
        ['tests/genie-worlds/mcp_call.py', name, JSON.stringify(args)], {
          timeout: 10000, maxBuffer: 65536, env: { PATH: process.env.PATH, PYTHONDONTWRITEBYTECODE: '1',
            NETCLAW_GENIE_CONTROL_FILE: join(root, 'mcp-control.json') },
        });
      return JSON.parse(result.stdout.trim());
    };
    const id = boundary.start.request_id;
    const evidence = await call('genie_world_evidence', { operation_id: id });
    assert.equal(evidence.session.operation_id, id);
    assert.equal(evidence.session.state, survivingWorker ? 'terminal' : 'unknown');
    assert.equal(evidence.session.terminal_confirmed, survivingWorker);
    assert.equal(evidence.session.usage_state, survivingWorker ? 'reconciled' : 'reserved');
    if (survivingWorker) {
      assert.equal(evidence.session.reason, 'manager_disconnected');
      assert.deepEqual(evidence.session.reported_usage, { video_output_tokens: 0 });
      assert.deepEqual(recovered.ledger.get(id).terminal_receipt, {
        event_type: 'interaction.completed', status: 'completed', usage: { video_output_tokens: 0 },
      });
      assert.equal(recovered.ledger.get(id).provider_id, boundary.session.provider_id);
    }
    assert.equal(evidence.session.event_state, 'sent');
    assert.deepEqual(evidence.event_checkpoint, { state: 'unconfirmed', receipt: null });
    const artifact = evidence.manifest.find(a => a.artifact_ref === `${id}_event_jpg`);
    assert.equal(artifact.size_bytes, boundary.event_file_bytes);
    assert.equal(evidence.live_world_proven, false); assert.equal(evidence.acceptance, null);
    assert.equal((await call('genie_world_start', boundary.start)).operation_id, id);
    assert.equal(recovered.workers.size, 0);
    assert.equal(recovered.ledger.list().length, 1);
    if (!survivingWorker) {
      const review = recovered.ledger.review(projection(), POLICY, 15, 'fixture');
      const refused = await request(recovered, '/v1/sessions', { request_id: randomUUID(), review_ref: review.id });
      assert.equal(refused.status, 409);
      assert.match((await refused.json()).error, /active_or_unsettled/);
    }
    const audit = recovered.ledger.db.prepare('SELECT body FROM audit ORDER BY seq').all().map(r => JSON.parse(r.body));
    const count = type => audit.filter(r => r.type === type).length;
    assert.equal(count('send_marked'), 1);
    assert.equal(count('event_send_marked'), 1);
    assert.equal(count('event_checkpoint'), 0);
    assert.equal(count('terminal'), survivingWorker ? 1 : 0);
    assert.deepEqual(await call('genie_world_evidence', { operation_id: id }), evidence, 'lookups never replay events or mint receipts');
    assert.equal(recovered.workers.size, 0); assert.equal(recovered.ledger.list().length, 1);
    writeFileSync(join(process.env.NETCLAW_TEST_TMP, survivingWorker ? 'manager-only-crash-evidence.json' : 'manager-crash-evidence.json'), JSON.stringify({
      ...evidence, actual_mcp: true, actual_agent: false, actual_browser: false, google_calls: 0,
      process_crash_tested: true, manager_signal: signal, worker_suspended_then_killed: !survivingWorker,
      original_worker_exited_itself: survivingWorker, creates: count('send_marked'),
      event_send_claims: count('event_send_marked'), terminal_receipts: count('terminal'),
      stale_lock_refused: true, owned_children_stopped: true, replacement_workers: 0,
    }, null, 2), { mode: 0o600 });
  });
}
