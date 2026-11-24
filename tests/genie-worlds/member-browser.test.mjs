import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createBrowserFixture } from './browser-fixture.mjs';
import { createManager } from '../../scripts/genie-worlds/manager.mjs';
const run = promisify(execFile);

for (const fault of ['none', 'event_checkpoint', 'final_flush', 'event_receipt_commit']) {
test(`actual Chrome/stdio MCP original-ID evidence: ${fault}`, {
  skip: !process.env.NETCLAW_BROWSER_EXECUTABLE || !process.env.NETCLAW_MCP_PYTHON, timeout: 30000,
}, async t => {
  const { root, m, browser } = await createBrowserFixture(t, 'member-browser-', {
    snapshotRegistryPath: process.env.NETCLAW_TEST_SNAPSHOT_REGISTRY || null,
  });
  if (fault === 'event_receipt_commit') {
    // Real SQLite abort after the manager writes/fsyncs the JPEG. This models
    // the file/transaction gap, not a process kill or a provider failure.
    m.ledger.db.exec(`CREATE TEMP TRIGGER refuse_event_receipt BEFORE INSERT ON event_checkpoints
      BEGIN SELECT RAISE(ABORT, 'synthetic_event_receipt_commit_failure'); END`);
  }
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
  page.setDefaultTimeout(5000);
  const external = [], errors = [], checkpoints = [], events = [];
  page.on('websocket', socket => socket.on('framesent', ({ payload }) => {
    try { const message = JSON.parse(payload); if (message.type === 'event') events.push(message); } catch {}
  }));
  let finalRequests = 0;
  await page.route('**/v1/sessions/*/*', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/checkpoint')) {
      const name = route.request().postDataJSON().name; checkpoints.push(name);
      if (fault === 'event_checkpoint' && name === 'event')
        return route.fulfill({ status: 503, json: { error: 'synthetic_checkpoint_failure' } });
    }
    if (path.endsWith('/recording-final')) {
      finalRequests++;
      if (fault === 'final_flush')
        return route.fulfill({ status: 503, json: { error: 'synthetic_final_flush_failure' } });
    }
    return route.continue();
  });
  page.on('request', r => { if (!r.url().startsWith(m.origin+'/')) external.push(r.url()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(m.origin+'/#'+m.bootstrap);
  if (process.env.NETCLAW_TEST_SNAPSHOT_REGISTRY) {
    await page.locator('#snapshots button').first().click();
    await page.waitForFunction(() => document.querySelector('#world-designs').children.length === 5);
    await page.getByRole('button', { name: 'R1', exact: true }).click();
    assert.match(await page.locator('#snapshot-fact').textContent(), /Ethernet0\/1/);
    assert.match(await page.locator('#snapshot-status').textContent(), /FROZEN HISTORICAL SNAPSHOT/);
    await page.locator('#world-designs button').nth(3).click();
    const design = JSON.parse(await page.locator('#world-design').textContent());
    assert.equal(design.style_id, 'packet-scale'); assert.equal(design.generated, false);
    assert.equal(design.hosted_eligible, false); assert.equal(design.provenance.filter(x=>x.kind==='physical_link').length, 3);
  }
  await page.getByRole('button', { name: 'Review for member start' }).click();
  await page.waitForFunction(() => document.querySelector('#result').textContent.includes('genie_world_start'));
  const reviewed = JSON.parse(await page.locator('#result').textContent());
  assert.equal(m.ledger.list().length, 0);
  const call = async (name, args) => {
    const result = await run(process.env.NETCLAW_MCP_PYTHON, ['tests/genie-worlds/mcp_call.py', name, JSON.stringify(args)], {
      cwd: process.cwd(), timeout: 10000, maxBuffer: 65536,
      env: { PATH: process.env.PATH, PYTHONDONTWRITEBYTECODE: '1', NETCLAW_GENIE_CONTROL_FILE: join(root, 'mcp-control.json') },
    });
    return JSON.parse(result.stdout.trim());
  };
  const started = await call(reviewed.tool, reviewed.arguments);
  assert.equal(started.operation_id, reviewed.arguments.request_id);
  await page.waitForFunction(() => document.querySelector('#status').textContent.startsWith('active'));
  await page.locator('canvas').focus(); await page.keyboard.down('w');
  await page.waitForTimeout(300); await page.keyboard.up('w');
  await page.getByRole('button', { name: 'Capture navigation checkpoint' }).click();
  await page.getByRole('button', { name: 'Target visible: dim corridor' }).click();
  await page.waitForTimeout(300);
  await page.getByRole('button', { name: 'Capture event checkpoint' }).click();
  await page.waitForFunction(() => /Event: (saved|unconfirmed)/i.test(document.querySelector('#capture-status').textContent));
  const stopped = await call('genie_world_stop', { request_id: crypto.randomUUID(), operation_id: started.operation_id });
  assert.equal(stopped.operation_id, started.operation_id);
  // Terminal provider status can precede the recorder's asynchronous final flush.
  if (fault === 'final_flush') {
    await page.waitForFunction(() => document.querySelector('#status').textContent.includes('Recording final confirmation unavailable'));
  } else {
    await new Promise((resolve, reject) => {
      const deadline = Date.now() + 5000;
      const check = () => {
        if (m.ledger.recordingStatus(started.operation_id).receipt) return resolve();
        if (Date.now() >= deadline) return reject(new Error('Final recording receipt not persisted'));
        setTimeout(check, 25);
      };
      check();
    });
  }
  const evidence = await call('genie_world_evidence', { operation_id: started.operation_id });
  assert.equal(evidence.session.terminal_confirmed, true); assert.equal(evidence.session.event_state, 'sent');
  assert.equal(evidence.session.operation_id, reviewed.arguments.request_id);
  assert.equal(m.ledger.list().length, 1, 'faults cannot create a replacement operation');
  assert.deepEqual(checkpoints, ['baseline', 'navigation', 'event'], 'no checkpoint replay');
  assert.equal(finalRequests, 1, 'no final-flush replay');
  assert.equal(events.length, 1, 'fictional event is never replayed');
  const eventUnconfirmed = ['event_checkpoint', 'event_receipt_commit'].includes(fault);
  assert.equal(evidence.event_checkpoint.state, eventUnconfirmed ? 'unconfirmed' : 'correlated');
  if (eventUnconfirmed) assert.equal(evidence.event_checkpoint.receipt, null);
  else {
    const receipt = evidence.event_checkpoint.receipt;
    const artifact = evidence.manifest.find(a => a.artifact_ref === `${started.operation_id}_event_jpg`);
    assert.equal(receipt.operation_id, started.operation_id);
    assert.equal(receipt.event_id, events[0].event_id);
    assert.equal(receipt.visible_effect, 'unassessed');
    assert(receipt.frame_sequence > 0);
    assert.match(receipt.worker_frame_sha256, /^[a-f0-9]{64}$/);
    assert.equal(receipt.sha256, artifact.sha256);
    assert.equal(receipt.size_bytes, artifact.size_bytes);
  }
  const media = evidence.manifest.find(a => a.mime === 'video/webm');
  assert(media.size_bytes > 0);
  assert.equal(evidence.recording.state, fault === 'final_flush' ? 'unconfirmed' : 'final_flush_acknowledged');
  if (fault === 'final_flush') {
    assert.equal(evidence.recording.receipt, null);
    assert.equal(evidence.recording.reason, 'final_flush_unconfirmed');
  } else {
    assert.equal(evidence.recording.receipt.sha256, media.sha256);
    assert.equal(evidence.recording.receipt.size_bytes, media.size_bytes);
  }
  assert.equal(evidence.manifest.length, fault === 'event_checkpoint' ? 3 : 4);
  assert.deepEqual(evidence.recording_failures, []);
  assert.equal(evidence.acceptance, null);
  assert.equal(evidence.live_world_proven, false); assert.deepEqual(external, []); assert.deepEqual(errors, []);
  if (process.env.NETCLAW_BROWSER_EVIDENCE) {
    const out = process.env.NETCLAW_BROWSER_EVIDENCE; mkdirSync(out, { recursive: true, mode: 0o700 });
    await page.screenshot({ path: join(out, `member-mcp-${fault}.png`), fullPage: true });
    writeFileSync(join(out, `member-mcp-${fault}.json`), JSON.stringify({ ...evidence, actual_mcp: true, actual_browser: true, actual_agent: false, google_calls: 0, external_browser_requests: 0 }, null, 2), { mode: 0o600 });
  }
  if (fault === 'event_receipt_commit') {
    const artifact = evidence.manifest.find(a => a.artifact_ref === `${started.operation_id}_event_jpg`);
    assert(artifact?.size_bytes > 0, 'JPEG persisted even though the receipt transaction aborted');
    assert.equal(m.ledger.eventCheckpoint(started.operation_id), null);
    await page.close();
    await m.close();
    let restarted;
    try {
      restarted = await createManager({ root,
        snapshotRegistryPath: process.env.NETCLAW_TEST_SNAPSHOT_REGISTRY || null });
      const retained = await call('genie_world_evidence', { operation_id: started.operation_id });
      assert.deepEqual(retained.event_checkpoint, { state: 'unconfirmed', receipt: null });
      assert.deepEqual(retained.manifest, evidence.manifest, 'restart neither rewrites nor discards the orphan JPEG');
      assert.deepEqual(retained.session, evidence.session);
      assert.equal(retained.acceptance, null);
      assert.equal(retained.live_world_proven, false);
      const original = await call(reviewed.tool, reviewed.arguments);
      assert.equal(original.operation_id, started.operation_id);
      assert.equal(restarted.ledger.list().length, 1);
      assert.equal(restarted.workers.size, 0, 'original-ID lookup cannot spawn a replacement worker');
      assert.equal(restarted.ledger.eventCheckpoint(started.operation_id), null);
      assert.equal(events.length, 1);
      assert.deepEqual(checkpoints, ['baseline', 'navigation', 'event']);
      if (process.env.NETCLAW_BROWSER_EVIDENCE) {
        writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE, 'member-mcp-event-receipt-restarted.json'),
          JSON.stringify({ ...retained, actual_mcp: true, actual_browser: true, actual_agent: false,
            google_calls: 0, sqlite_abort_injected: true, manager_reopened: true,
            process_crash_tested: false, original_id_lookup: original.operation_id,
            replacement_workers: restarted.workers.size }, null, 2), { mode: 0o600 });
      }
    } finally { await restarted?.close(); }
  }
});
}
