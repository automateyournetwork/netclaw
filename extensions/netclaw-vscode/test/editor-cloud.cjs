const vscode = require('vscode'), fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const readPrivate = file => {
  const s = fs.lstatSync(file);
  assert.ok(s.isFile() && !s.isSymbolicLink() && s.uid === process.getuid() && !(s.mode & 0o077) && s.size < 1024 * 1024, 'Expected an owned private bounded input file.');
  return fs.readFileSync(file, 'utf8');
};
exports.run = async () => {
  const config = JSON.parse(readPrivate(process.env.NETCLAW_CLOUD_CONFIG));
  assert.ok(['execute', 'recover'].includes(config.mode));
  assert.equal(config.expected.tool_call.tool, 'netbox_get_object_by_id');
  assert.deepEqual(config.expected.tool_call.arguments, { object_type: 'dcim.device', object_id: 1, fields: ['id', 'name', 'status', 'site', 'device_type', 'last_updated'], brief: false });
  for (const field of ['principal', 'border', 'member', 'model_profile']) assert.ok(config.expected[field] && Object.keys(config.expected[field]).length > 0, 'Expected full ' + field + ' identity is required.');
  assert.equal(config.expected.border.installation_id, config.installationId);
  const report = process.env.NETCLAW_TEST_REPORT, checkpoints = [];
  const mark = label => { checkpoints.push(label); fs.writeFileSync(report, JSON.stringify({ complete: false, mode: config.mode, editor: vscode.version, checkpoints }, null, 2), { mode: 0o600 }); };
  const extension = vscode.extensions.getExtension('NetClaw.netclaw'); assert.ok(extension);
  const api = await extension.activate(), before = api.profiles.list();
  const existing = before.find(p => p.mode === 'remote-border' && p.url === config.origin && p.installationId === config.installationId);
  if (config.mode === 'recover') assert.ok(existing, 'Recovery must reuse its existing saved profile.');
  const profile = existing || await api.profiles.save({ label: 'R04a cloud qualification', url: config.origin, installationId: config.installationId, mode: 'remote-border', harness: 'openclaw' });
  await api.connection.connect(profile);
  assert.equal(api.connection.identity.installationId, config.installationId); assert.equal(api.connection.identity.role, 'border');
  assert.throws(() => api.connection.bound()); assert.throws(() => api.management.bound());
  assert.deepEqual(api.assistants.provideMcpServerDefinitions(), []);
  mark('Actual extension verifies selected HTTPS Border and refuses local/assistant authority');
  const { chromium } = require(process.env.NETCLAW_TEST_PLAYWRIGHT);
  const browser = await chromium.connectOverCDP('http://127.0.0.1:' + process.env.NETCLAW_TEST_CDP_PORT);
  const page = browser.contexts().flatMap(c => c.pages()).find(p => p.url().includes('workbench')); assert.ok(page); page.setDefaultTimeout(30000);
  const quick = () => page.locator('.quick-input-widget input').first();
  const choose = async index => { const row = page.locator('.quick-input-list .monaco-list-row').nth(index); await row.waitFor({ state: 'visible' }); await row.click(); };
  try {
    if (!api.connection.owner.sessionState) {
      assert.ok(config.ticketFile, 'An expired session requires a fresh one-use operator ticket.');
      const pending = api.ownerWorkflow.signIn();
      await quick().waitFor({ state: 'visible' });
      assert.equal(await quick().getAttribute('type'), 'password');
      await quick().fill(readPrivate(config.ticketFile).trim()); await quick().press('Enter'); assert.equal(await pending, true);
    }
    assert.deepEqual(api.connection.owner.sessionState.principal, config.expected.principal);
    mark('Native password input establishes explicit owner authority; no ticket captured');
    let operation;
    if (config.mode === 'execute') {
      const catalog = await api.connection.owner.catalog(), choices = [];
      for (const entry of catalog.members) for (const model of entry.model_profiles) for (const tool of entry.tools) choices.push({ entry, model, tool });
      const matching = choices.map((c, index) => ({ ...c, index })).filter(c => {
        try { assert.deepEqual(c.entry.member, config.expected.member); assert.deepEqual(c.model, config.expected.model_profile); assert.equal(c.tool.tool, config.expected.tool_call.tool); assert.deepEqual(c.tool.arguments, config.expected.tool_call.arguments); return true; } catch { return false; }
      });
      assert.equal(matching.length, 1, 'Exact reviewed catalog selection must be unique.');
      let pending;
      if (config.preparedReferenceFile) {
        const ref = JSON.parse(readPrivate(config.preparedReferenceFile)); assert.ok(ref.operation_id && ref.client_nonce && !ref.decision_sent);
        pending = api.ownerWorkflow.recover();
        const retained = page.locator('.quick-input-list .monaco-list-row').filter({ hasText: ref.operation_id });
        await retained.waitFor({ state: 'visible' }); await retained.click();
      } else { pending = api.ownerWorkflow.prepare(); await choose(matching[0].index); }
      const reviewDecision = page.getByRole('button', { name: 'Review decision', exact: true }); await reviewDecision.waitFor({ state: 'visible' });
      const doc = vscode.workspace.textDocuments.find(d => d.uri.scheme === 'netclaw-owner' && d.getText().includes('review_digest')); assert.ok(doc);
      const displayed = JSON.parse(doc.getText());
      for (const field of ['principal', 'border', 'member', 'model_profile']) assert.deepEqual(displayed.review[field], config.expected[field], 'Full ' + field + ' must match frozen authority');
      assert.equal(displayed.review.tool_call.tool, config.expected.tool_call.tool); assert.deepEqual(displayed.review.tool_call.arguments, config.expected.tool_call.arguments);
      for (const [key, value] of Object.entries(config.expected.tool_call)) assert.deepEqual(displayed.review.tool_call[key], value);
      assert.equal(displayed.review.limits.max_tool_calls, 1); assert.equal(displayed.review.limits.max_inference_calls, 2); assert.equal(displayed.review.change_request_ref, null);
      assert.ok(displayed.review.limits.expires_at_ms > Date.now());
      assert.equal(doc.isUntitled, false);
      await vscode.window.showTextDocument(doc);
      await vscode.commands.executeCommand('revealLine', { lineNumber: doc.lineCount - 1, at: 'bottom' });
      await page.screenshot({ path: path.join(path.dirname(report), 'review-end-' + Date.now() + '.png') });
      await vscode.commands.executeCommand('revealLine', { lineNumber: 0, at: 'top' });
      await reviewDecision.click();
      const approve = page.getByRole('button', { name: 'Approve once', exact: true }); await approve.waitFor({ state: 'visible' });
      const dialog = page.locator('.monaco-dialog-box');
      const rendered = await dialog.textContent();
      fs.writeFileSync(path.join(path.dirname(report), 'native-review-' + Date.now() + '.json'), JSON.stringify({ virtualReview: displayed, nativeText: rendered }, null, 2), { mode: 0o600 });
      assert.ok(rendered.includes(displayed.operation_id) && rendered.includes(displayed.review_digest) && rendered.includes('Revision: ' + displayed.revision), 'Visible native decision must bind the full displayed review');
      const bounds = await approve.boundingBox(), viewport = await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
      assert.ok(bounds && bounds.x >= 0 && bounds.y >= 0 && bounds.x + bounds.width <= viewport.width && bounds.y + bounds.height <= viewport.height, 'Native approval must be inside the actual viewport');
      await page.screenshot({ path: path.join(path.dirname(report), 'review-' + Date.now() + '.png') });
      mark('Scrollable complete immutable review matches frozen identities and exact device1 read; visible native decision binds its revision/digest');
      await approve.click(); operation = await pending; assert.ok(operation);
      mark('One native Approve once accepted the exact displayed revision and digest');
    } else {
      const previous = JSON.parse(readPrivate(config.previousReport)); assert.equal(previous.complete, true);
      const recovered = api.ownerWorkflow.recover();
      const row = page.locator('.quick-input-list .monaco-list-row').filter({ hasText: previous.operation.operation_id });
      await row.waitFor({ state: 'visible' }); await row.click();
      operation = await recovered;
      assert.equal(operation.operation_id, previous.operation.operation_id); assert.equal(operation.client_nonce, previous.operation.client_nonce);
      assert.equal(operation.attempt_count, previous.operation.attempt_count); assert.equal(operation.result.digest, previous.operation.result.digest);
      mark('Actual editor process restart recovered the same operation, result digest and attempt count without a prepare or decision');
    }
    const reference = { operation_id: operation.operation_id, client_nonce: operation.client_nonce };
    const until = Date.now() + 180000;
    while (!(operation.result?.verified === true && operation.result?.durable_ack === true && operation.result?.ack_delivery_pending === false) && Date.now() < until) {
      await pause(2000); operation = await api.connection.owner.status(reference);
    }
    assert.equal(operation.state, 'completed'); assert.equal(operation.attempt_count, 1); assert.equal(operation.result.verified, true); assert.equal(operation.result.durable_ack, true); assert.equal(operation.result.ack_delivery_pending, false);
    // Show final evidence through the native recovery flow, not only a driver fetch.
    const recovery = api.ownerWorkflow.recover();
    const row = page.locator('.quick-input-list .monaco-list-row').filter({ hasText: operation.operation_id }); await row.waitFor({ state: 'visible' }); await row.click();
    const displayedResult = await recovery; assert.equal(displayedResult.result.digest, operation.result.digest);
    const resultDoc = vscode.workspace.textDocuments.find(d => d.uri.scheme === 'netclaw-owner'); assert.ok(resultDoc.getText().includes('durableAcknowledgement'));
    await page.screenshot({ path: path.join(path.dirname(report), 'result-' + Date.now() + '.png') });
    assert.deepEqual(api.profiles.list().filter(p => p.id !== profile.id), before.filter(p => p.id !== profile.id));
    mark('Actual native result view shows verified signed result, durable ACK and audit evidence; existing profiles preserved');
    fs.writeFileSync(report, JSON.stringify({ complete: true, mode: config.mode, editor: vscode.version, extension: extension.packageJSON.version, profileId: profile.id, checkpoints, operation }, null, 2), { mode: 0o600 });
  } finally { await browser.close(); }
};
