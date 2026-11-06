// Actual installed-editor qualification. It never substitutes a backend/provider.
const vscode = require('vscode'), fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function privateJson(file) {
  const s = fs.lstatSync(file);
  assert.ok(s.isFile() && !s.isSymbolicLink() && s.uid === process.getuid() && !(s.mode & 0o077) && s.size < 1024 * 1024);
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}
exports.run = async () => {
  const config = privateJson(process.env.NETCLAW_CLOUD_CONFIG), report = process.env.NETCLAW_TEST_REPORT;
  assert.ok(['execute', 'recover'].includes(config.mode));
  assert.match(config.peer, /^as\d+-[\d.]+$/);
  const events = [], checkpoints = [];
  const save = extra => fs.writeFileSync(report, JSON.stringify({ complete: false, mode: config.mode, editor: vscode.version, checkpoints, events, ...extra }, null, 2), { mode: 0o600 });
  const mark = label => { checkpoints.push(label); save({}); };
  const extension = vscode.extensions.getExtension('NetClaw.netclaw'); assert.ok(extension);
  const api = await extension.activate(), before = api.profiles.list();
  const existing = before.find(p => p.mode === 'remote-border' && p.url === config.origin && p.installationId === config.installationId);
  if (config.mode === 'recover') assert.ok(existing, 'Recovery requires the original saved profile.');
  const profile = existing || await api.profiles.save({ label: 'R06 ordinary cloud federation', url: config.origin, installationId: config.installationId, mode: 'remote-border', harness: 'openclaw' });
  await api.connection.connect(profile);
  assert.equal(api.connection.identity.installationId, config.installationId);
  assert.deepEqual(api.connection.identity.capabilities.externalFederation, { schema: 1, execution: 'ordinary', peerChat: true });
  assert.throws(() => api.management.bound()); assert.deepEqual(api.assistants.provideMcpServerDefinitions(), []);
  const client = api.connection.bound().client, original = client.request.bind(client);
  client.request = async (...args) => {
    const [method, route] = args;
    const item = { method, route, at: new Date().toISOString() }; events.push(item); save({});
    const result = await original(...args);
    if (route === '/api/n2n/chat' || route === '/api/chat' || /\/conversations\/.*\/open$/.test(route)) item.result = result;
    save({}); return result;
  };
  const { chromium } = require(process.env.NETCLAW_TEST_PLAYWRIGHT);
  const browser = await chromium.connectOverCDP('http://127.0.0.1:' + process.env.NETCLAW_TEST_CDP_PORT);
  const page = browser.contexts().flatMap(c => c.pages()).find(p => p.url().includes('workbench')); assert.ok(page); page.setDefaultTimeout(30000);
  async function frameWith(selector) {
    const until = Date.now() + 60000;
    while (Date.now() < until) {
      for (const frame of page.frames()) {
        try { if (await frame.locator(selector).count()) return frame; }
        catch (error) { if (page.isClosed()) throw error; /* A replaced webview frame can detach during enumeration. */ }
      }
      await pause(200);
    }
    throw Error('Native webview unavailable: ' + selector);
  }
  try {
    await vscode.commands.executeCommand('netclaw.openPeers');
    const peers = await frameWith('body[data-kind="peers"]');
    await peers.locator('#content').filter({ hasText: config.peer }).waitFor();
    await page.screenshot({ path: path.join(path.dirname(report), config.mode + '-peers.png') });
    mark('Selected cloud identity and actual peer inventory visible; local management and assistant authority unavailable');
    let peerResult;
    if (config.mode === 'execute') {
      const pending = vscode.commands.executeCommand('netclaw.openPeerChat');
      const row = page.locator('.quick-input-list .monaco-list-row').filter({ hasText: config.peerLabel });
      await row.waitFor(); await row.click();
      const input = page.locator('.quick-input-widget input').first(); await input.waitFor(); await input.fill(config.peerPrompt); await input.press('Enter');
      const send = page.getByRole('button', { name: 'Send', exact: true }); await send.waitFor();
      const dialog = await page.locator('.monaco-dialog-box').textContent(); assert.ok(dialog.includes(config.installationId) && dialog.includes(config.peerPrompt));
      fs.writeFileSync(path.join(path.dirname(report), 'peer-submit.claim.json'), JSON.stringify({ peer: config.peer, installationId: config.installationId, prompt: config.peerPrompt, automaticReplay: false }), { flag: 'wx', mode: 0o600 });
      await send.click(); await pending;
      peerResult = events.find(e => e.route === '/api/n2n/chat')?.result;
      assert.equal(peerResult?.source, config.peer); assert.equal(peerResult?.trust, 'remote-untrusted'); assert.ok(peerResult?.text?.includes(config.peerMarker));
      const reply = await frameWith('body[data-kind="peerChat"]');
      await reply.locator('#content').filter({ hasText: config.peerMarker }).waitFor();
      await page.screenshot({ path: path.join(path.dirname(report), 'peer-reply.png') });
      mark('One native peer selection, prompt and exact confirmation returned the attributed live peer response');
    }
    await vscode.commands.executeCommand('netclaw.openChat');
    const chat = await frameWith('#composer #prompt');
    if (config.mode === 'execute') {
      await chat.locator('#prompt').fill(config.prompt);
      fs.writeFileSync(path.join(path.dirname(report), 'chat-submit.claim.json'), JSON.stringify({ installationId: config.installationId, prompt: config.prompt, automaticReplay: false }), { flag: 'wx', mode: 0o600 });
      await chat.locator('#send').click();
      await chat.locator('#transcript').filter({ hasText: config.answerMarker }).waitFor({ timeout: 300000 });
      assert.equal(events.filter(e => e.method === 'POST' && e.route === '/api/chat').length, 1);
      assert.equal(events.find(e => e.route === '/api/chat')?.result?.fromGateway, true);
      mark('One native Chat submission completed through the selected gateway');
    } else {
      const previous = privateJson(config.previousReport); assert.equal(previous.complete, true);
      await chat.locator('#transcript').filter({ hasText: config.answerMarker }).waitFor();
      await chat.locator('#history').click();
      const row = page.locator('.quick-input-list .monaco-list-row').filter({ hasText: config.prompt.slice(0, 30) });
      await row.waitFor(); await row.click();
      await chat.locator('#transcript').filter({ hasText: config.answerMarker }).waitFor();
      assert.equal(events.filter(e => e.method === 'POST' && ['/api/chat', '/api/n2n/chat'].includes(e.route)).length, 0);
      assert.ok(events.some(e => /\/conversations\/.*\/open$/.test(e.route)));
      mark('Actual editor restart reopened the original owned conversation with no chat resubmission');
    }
    await page.screenshot({ path: path.join(path.dirname(report), config.mode + '-chat.png') });
    assert.deepEqual(api.profiles.list().filter(p => p.id !== profile.id), before.filter(p => p.id !== profile.id));
    save({ complete: true, profileId: profile.id, peerResult, extension: extension.packageJSON.version });
  } finally { client.request = original; await browser.close(); }
};
