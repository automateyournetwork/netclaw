const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vscode = require('vscode');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function readPrivate(file) {
  assert.ok(path.isAbsolute(file)); const st = fs.lstatSync(file);
  assert.ok(st.isFile() && !st.isSymbolicLink() && st.uid === process.getuid() && !(st.mode & 0o077) && st.size <= 1024 * 1024);
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}
function samePair(actual, expected) {
  assert.equal(actual.parent_id, expected.parent_id); assert.equal(actual.client_nonce, expected.client_nonce);
  assert.equal(actual.children.length, 2);
  for (const i of [0, 1]) {
    assert.equal(actual.children[i].family, [4, 6][i]);
    for (const field of ['operation_id', 'review_digest', 'review']) assert.deepEqual(actual.children[i][field], expected.children[i][field]);
  }
}
// Actual native editor UI. One separate process invocation per child decision.
exports.run = async () => {
  const config = readPrivate(process.env.NETCLAW_CLOUD_CONFIG), report = process.env.NETCLAW_TEST_REPORT;
  assert.ok(['prepare', 'decision', 'recover'].includes(config.mode));
  const extension = vscode.extensions.getExtension('NetClaw.netclaw'); assert.ok(extension);
  const api = await extension.activate(), before = api.profiles.list();
  const selected = before.filter(p => p.mode === 'remote-border' && p.url === config.origin && p.installationId === config.installationId && (!config.profile_id || p.id === config.profile_id));
  assert.equal(selected.length, 1, 'Reuse exactly one retained cloud profile; do not create another identity.');
  await api.connection.connect(selected[0]);
  assert.equal(api.connection.identity.installationId, config.installationId);
  assert.equal(api.connection.owner.openLab, true, 'This pilot uses Name + URL, without owner login.');
  assert.deepEqual(api.connection.owner.principal, config.principal);
  assert.equal(api.connection.ownerBound().client, api.connection.owner);
  assert.throws(() => api.management.bound(), 'Cloud profiles never acquire local host management.');
  const { chromium } = require(process.env.NETCLAW_TEST_PLAYWRIGHT);
  const browser = await chromium.connectOverCDP('http://127.0.0.1:' + process.env.NETCLAW_TEST_CDP_PORT);
  const page = browser.contexts().flatMap(c => c.pages()).find(p => p.url().includes('workbench')); assert.ok(page); page.setDefaultTimeout(30000);
  const row = text => page.locator('.quick-input-list .monaco-list-row').filter({ hasText: text });
  const choose = async text => { const target = row(text); await target.waitFor({ state: 'visible' }); assert.equal(await target.count(), 1); await target.click(); };
  const document = () => { const doc = vscode.window.activeTextEditor?.document; assert.ok(doc && doc.uri.scheme === 'netclaw-owner' && !doc.isUntitled); return JSON.parse(doc.getText()); };
  const currentDocument = async predicate => {
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) { const value = document(); if (predicate(value)) return value; await pause(50); }
    throw Error('The native immutable review document has not rendered; no decision submitted.');
  };
  const capture = async label => { const file = path.join(path.dirname(report), 'combined-' + label + '-' + Date.now() + '.png'); await page.screenshot({ path: file }); fs.chmodSync(file, 0o600); return file; };
  const claim = () => {
    assert.ok(path.isAbsolute(config.claim_file)); const directory = fs.lstatSync(path.dirname(config.claim_file));
    assert.ok(directory.isDirectory() && !directory.isSymbolicLink() && directory.uid === process.getuid() && !(directory.mode & 0o077));
    fs.writeFileSync(config.claim_file, JSON.stringify({ mode: config.mode, installationId: config.installationId, parent_id: config.combined?.parent_id, child_index: config.child_index, decision: config.decision, at: new Date().toISOString() }), { flag: 'wx', mode: 0o600 });
  };
  const images = [];
  try {
    let value;
    if (config.mode === 'prepare') {
      assert.equal(config.children.length, 2);
      claim();
      if (config.archive_combined) {
        const recovery = api.ownerWorkflow.recoverCombined();
        await row('Remove resolved reference').waitFor({ state: 'visible' });
        const old = await currentDocument(v => v.parent_id === config.archive_combined.parent_id); samePair(old, config.archive_combined);
        assert.equal(old.state, 'complete');
        for (const i of [0, 1]) {
          assert.equal(old.children[i].result?.verified, true);
          assert.equal(old.children[i].result?.durable_ack, true);
          assert.equal(old.children[i].result?.ack_delivery_pending, false);
          assert.equal(old.children[i].result?.digest, config.archive_combined.children[i].result?.digest);
        }
        const archive = path.join(path.dirname(report), 'archived-combined.json');
        const fd = fs.openSync(archive, 'wx', 0o600);
        try { fs.writeFileSync(fd, JSON.stringify(old, null, 2)); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
        await choose('Remove resolved reference'); await recovery;
      }
      const pending = api.ownerWorkflow.prepareCombined();
      for (const i of [0, 1]) {
        assert.equal(config.children[i].family, [4, 6][i]);
        const candidate = page.locator('.quick-input-list .monaco-list-row').filter({ hasText: config.children[i].cidr }).filter({ hasText: config.children[i].member_id }).filter({ hasText: config.children[i].profile_revision });
        await candidate.waitFor({ state: 'visible' }); assert.equal(await candidate.count(), 1); await candidate.click();
      }
      await row('Keep for recovery').waitFor({ state: 'visible' }); value = await currentDocument(v => v.state === 'awaiting_decisions' && v.children?.length === 2);
      assert.equal(value.children.length, 2); assert.deepEqual(value.children.map(c => c.family), [4, 6]);
      for (const i of [0, 1]) {
        const child = value.children[i], expected = config.children[i];
        assert.equal(child.review.member.member_id, expected.member_id); assert.equal(child.review.tool_call.arguments.cidr, expected.cidr);
        assert.equal(child.review.model_profile.profile_revision, expected.profile_revision); assert.equal(child.review.model_profile.provider, 'ollama');
        assert.deepEqual(child.review.principal, config.principal);
      }
      images.push(await capture('two-reviews')); await choose('Keep for recovery'); await pending;
    } else if (config.mode === 'decision') {
      assert.ok([0, 1].includes(config.child_index)); assert.ok(['approve', 'deny'].includes(config.decision));
      claim();
      const pending = api.ownerWorkflow.recoverCombined();
      await choose('Review one pending child'); await choose('Review IPv' + [4, 6][config.child_index]);
      const read = page.getByRole('button', { name: 'Review decision', exact: true }); await read.waitFor({ state: 'visible' });
      const expected = config.combined.children[config.child_index];
      const displayed = await currentDocument(v => v.operation_id === expected.operation_id);
      for (const field of ['operation_id', 'revision', 'review_digest', 'review']) assert.deepEqual(displayed[field], expected[field]);
      images.push(await capture('child-review')); await read.click();
      const label = config.decision === 'approve' ? 'Approve once' : 'Deny';
      const decision = page.getByRole('button', { name: label, exact: true }); await decision.waitFor({ state: 'visible' });
      const text = await page.locator('.monaco-dialog-box').textContent(); assert.ok(text.includes(expected.operation_id) && text.includes(expected.review_digest) && text.includes('other child requires its own separate approval'));
      images.push(await capture('separate-decision')); await decision.click();
      // Successful submission leads to a new choice, never an automatic second decision.
      await row('Keep for recovery').waitFor({ state: 'visible' }); await choose('Keep for recovery'); value = await pending;
      samePair(value, config.combined);
    } else {
      value = await api.connection.owner.combinedStatus(config.combined); samePair(value, config.combined);
      if (config.cancel_unapproved === true) {
        assert.ok(value.children.every(child => child.approval == null && child.attempt_count === 0));
        claim();
        const cancellation = api.ownerWorkflow.recoverCombined();
        await row('Cancel remaining children').waitFor({ state: 'visible' });
        const shown = await currentDocument(v => v.parent_id === value.parent_id); samePair(shown, value);
        images.push(await capture('cancel-unapproved'));
        await choose('Cancel remaining children'); await cancellation;
        value = await api.connection.owner.combinedStatus(config.combined); samePair(value, config.combined);
        assert.ok(value.children.every(child => child.attempt_count === 0));
        assert.equal(value.cancelled, true);
        const fd = fs.openSync(path.join(path.dirname(report), 'cancelled-pair.json'), 'wx', 0o600);
        try { fs.writeFileSync(fd, JSON.stringify(value, null, 2)); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
      }
    }
    if (config.expected_states) {
      assert.ok(config.expected_states.length > 0 && config.expected_states.every(s => ['awaiting_decisions', 'running', 'complete', 'partial', 'failed', 'cancelled', 'unknown'].includes(s)));
      const deadline = Date.now() + 180000;
      while (!config.expected_states.includes(value.state)) {
        assert.ok(Date.now() < deadline, 'State still pending; preserve the parent and recover without another decision.');
        await pause(2000); value = await api.connection.owner.combinedStatus(value);
      }
    }
    if (config.mode === 'recover' && config.preserve_effects === true) for (const i of [0, 1]) {
      assert.equal(value.children[i].attempt_count, config.combined.children[i].attempt_count);
      for (const field of ['digest', 'verified', 'durable_ack', 'ack_delivery_pending']) assert.equal(value.children[i].result?.[field], config.combined.children[i].result?.[field]);
    }
    // Display even partial/unknown evidence in the production native recovery view.
    const view = api.ownerWorkflow.recoverCombined(); await row('Keep reference').waitFor({ state: 'visible' });
    const shown = await currentDocument(v => v.parent_id === value.parent_id); samePair(shown, value); images.push(await capture('state-' + shown.state)); await choose(config.cancel_unapproved === true ? 'Remove resolved reference' : 'Keep reference'); await view;
    assert.deepEqual(api.profiles.list(), before);
    fs.writeFileSync(report, JSON.stringify({ complete: true, mode: config.mode, editor: vscode.version, profileId: selected[0].id, combined: shown, images, native_decisions: config.mode === 'decision' ? 1 : 0, observed_at: new Date().toISOString() }, null, 2), { flag: 'wx', mode: 0o600 });
  } finally { await browser.close(); }
};
