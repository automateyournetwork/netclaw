import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { Bindings } from './bindings.js';
import { mountChatHistory } from './chat-history.js';
import { OpenLabBindings, createOpenLabBindings, labConversationContext } from './open-lab-bindings.js';

const installation = { installationId: 'b164621c-a94e-4c28-a087-d9c9dabcce21', kind: 'openclaw' };
function fixture(t) {
  const root = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'netclaw-lab-bindings-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const directory = path.join(root, 'lab-conversations');
  return { root, directory, bindings: createOpenLabBindings(directory, installation, () => 1000) };
}

test('explicit lab context ignores headers and does not create a session or cookie', t => {
  const { bindings, directory } = fixture(t);
  assert.equal(labConversationContext(new Proxy({}, { get() { throw Error('Headers must not be read'); } })), undefined);
  assert.equal(bindings.cookieName, undefined);
  assert.equal(bindings.openLab, true);
  assert.deepEqual(bindings.read(), bindings.read('untrusted-cookie'));
  assert.deepEqual(fs.readdirSync(directory), []);
  assert.throws(() => bindings.create(), /do not use sessions/);
  assert.throws(() => bindings.revoke(), /do not use sessions/);
});

test('all lab visitors resume the same public thread across process restart', t => {
  const { bindings, directory } = fixture(t);
  const task = bindings.task(undefined, 'canvas:root', 'engineer');
  bindings.describeChat(undefined, task.id, 'engineer', { title: 'Shared lab question', chatModel: 'sonnet', chatEffort: 'low' });
  const resumed = new OpenLabBindings(directory, () => 4000, installation);
  assert.equal(resumed.task('not-a-credential', 'canvas:root', 'engineer').id, task.id);
  assert.equal(resumed.resumeChat(undefined, task.id, 'engineer').publicThread, 'canvas:root');
  assert.equal(resumed.chats(undefined, 'engineer')[0].title, 'Shared lab question');
  assert.equal(resumed.lookupTask(undefined, 'canvas:root', 'engineer').gatewayKey, task.gatewayKey);
  assert.equal(resumed.lookupTask(undefined, 'canvas:root', 'other'), null);
  assert.equal(resumed.read().expires, undefined);
  assert.equal(fs.statSync(directory).mode & 0o777, 0o700);
  assert.equal(fs.statSync(resumed.file()).mode & 0o777, 0o600);
});

test('existing chat history handlers list and reopen the shared lab without cookies', async t => {
  const { bindings } = fixture(t);
  const task = bindings.task(undefined, 'chat:one', 'engineer'), calls = [], routes = new Map();
  mountChatHistory({ get: (p, f) => routes.set(p, f), post: (p, f) => routes.set(p, f) }, {
    bindings, config: () => ({ agents: { entries: { engineer: {} } } }), configPath: '/fixture/config',
    runtime: { catalog: async () => [] },
    call: async (method, args) => {
      calls.push({ method, args });
      return method === 'sessions.list' ? { sessions: [{ key: task.gatewayKey, derivedTitle: 'Shared conversation' }] } :
        { messages: [{ role: 'user', content: 'Question' }, { role: 'assistant', content: 'Answer' }, { role: 'system', content: 'Internal' }], sessionInfo: {} };
    },
  });
  const invoke = async route => {
    const res = { code: 200, headers: {}, set(k, v) { this.headers[k] = v; return this; }, status(code) { this.code = code; return this; }, json(body) { this.body = body; return this; } };
    await routes.get(route)({ headers: {}, params: { id: task.id } }, res);
    return res;
  };
  const listed = await invoke('/api/chat/conversations');
  assert.equal(listed.code, 200); assert.equal(listed.body.conversations[0].id, task.id);
  const opened = await invoke('/api/chat/conversations/:id/open');
  assert.equal(opened.code, 200); assert.equal(opened.body.thread, 'chat:one');
  assert.deepEqual(opened.body.messages.map(m => m.content), ['Question', 'Answer']);
  assert.equal(opened.headers['Set-Cookie'], undefined);
  assert.equal(calls[1].args.sessionKey, task.gatewayKey);
  assert.deepEqual(calls.map(c => c.method), ['sessions.list', 'chat.history']);
});

test('installation and runtime changes cannot read or overwrite the existing state', t => {
  const { bindings, directory } = fixture(t);
  bindings.task(undefined, 'chat:one'); const before = fs.readFileSync(bindings.file());
  for (const changed of [{ ...installation, installationId: 'f03c0a7c-5444-4cd6-b745-394471cf328a' }, { ...installation, kind: 'hermes' }]) {
    const other = createOpenLabBindings(directory, changed);
    assert.throws(() => other.read());
    assert.throws(() => other.save(undefined, { version: 1, mode: 'open-lab', installationId: changed.installationId, runtime: changed.kind, tasks: {} }));
    assert.deepEqual(fs.readFileSync(bindings.file()), before);
  }
});

test('legacy sessions are neither imported nor accepted as shared lab records', t => {
  const { root, directory, bindings } = fixture(t);
  const legacy = new Bindings(path.join(root, 'legacy')), cookie = legacy.create();
  legacy.task(cookie, 'old-thread');
  assert.equal(bindings.chats(cookie, 'main').length, 0);
  fs.writeFileSync(bindings.file(), JSON.stringify(legacy.read(cookie)), { mode: 0o600 });
  assert.throws(() => createOpenLabBindings(directory, installation).read());
});

test('shared thread lock ignores cookie changes and only permits existing tasks', t => {
  const { bindings } = fixture(t), task = bindings.task(undefined, 'chat:one');
  const release = bindings.begin(undefined, task.id);
  assert.throws(() => bindings.begin('different-cookie', task.id), /active request/);
  assert.throws(() => bindings.begin(undefined, 'not-an-existing-task'));
  release(); bindings.begin(undefined, task.id)();
});

test('unknown request identity and assessment provenance survive restart without resend', t => {
  const { bindings, directory } = fixture(t), task = bindings.task(undefined, 'chat:one');
  const request = bindings.request(undefined, task.id, 'nonce1', 'digest1');
  bindings.requestState(undefined, request.id, 'unknown');
  bindings.register(undefined, task.id, [{ assessmentId: 'assessment1', ledgerTask: 'ledger1', toolEventId: 'event1' }], 'message1');
  const resumed = createOpenLabBindings(directory, installation), next = resumed.task(undefined, 'chat:two');
  assert.equal(resumed.request(undefined, task.id, 'nonce1', 'digest1').id, request.id);
  assert.equal(resumed.ownedRequest(undefined, request.id).request.state, 'unknown');
  assert.throws(() => resumed.request(undefined, task.id, 'nonce1', 'changed'));
  assert.throws(() => resumed.requireAcknowledgment(undefined, next.id));
  assert.equal(resumed.authorize(undefined, task.id, 'assessment1').ref.messageRef, 'message1');
  assert.throws(() => resumed.authorize(undefined, next.id, 'assessment1'));
});

test('symlink directories, ancestor aliases and symlink or hardlinked files are refused', t => {
  const { root, directory, bindings } = fixture(t);
  bindings.task(undefined, 'chat:one'); const file = bindings.file();
  const link = path.join(root, 'alias'); fs.symlinkSync(directory, link);
  assert.throws(() => createOpenLabBindings(link, installation).read());
  assert.throws(() => createOpenLabBindings(path.join(link, 'child'), installation).read());
  const copy = path.join(root, 'original.json'); fs.renameSync(file, copy); fs.symlinkSync(copy, file);
  assert.throws(() => bindings.read()); assert.throws(() => bindings.save(undefined, { ...bindings.installation }));
  fs.unlinkSync(file); fs.linkSync(copy, file); assert.throws(() => bindings.read());
});

test('directory and file permissions fail closed without automatic repair', t => {
  const { directory, bindings } = fixture(t); bindings.task(undefined, 'chat:one'); const file = bindings.file();
  fs.chmodSync(file, 0o644); assert.throws(() => bindings.read()); assert.equal(fs.statSync(file).mode & 0o777, 0o644);
  fs.chmodSync(file, 0o600); fs.chmodSync(directory, 0o755); assert.throws(() => bindings.read());
  assert.equal(fs.statSync(directory).mode & 0o777, 0o755);
});

test('oversize, malformed and out-of-scope task records are rejected', t => {
  const { bindings } = fixture(t), task = bindings.task(undefined, 'chat:one'), file = bindings.file();
  const state = bindings.read(), before = fs.readFileSync(file);
  state.tasks[task.id].title = 'x'.repeat(8 * 1024 * 1024);
  assert.throws(() => bindings.save(undefined, state)); assert.deepEqual(fs.readFileSync(file), before);
  const bad = JSON.parse(before); bad.tasks[task.id].gatewayKey = 'agent:other:private:outside';
  fs.writeFileSync(file, JSON.stringify(bad)); assert.throws(() => bindings.read());
  fs.writeFileSync(file, '{'); assert.throws(() => bindings.read());
  fs.truncateSync(file, 8 * 1024 * 1024 + 1); assert.throws(() => bindings.read());
});

test('task and per-task request limits remain bounded', t => {
  const { bindings } = fixture(t), task = bindings.task(undefined, 'chat:one'), state = bindings.read();
  state.tasks[task.id].requests = Object.fromEntries(Array.from({ length: 500 }, (_, i) => ['r' + i, { id: 'r' + i, nonce: 'n' + i, bodyDigest: 'digest' }]));
  bindings.save(undefined, state);
  assert.throws(() => bindings.request(undefined, task.id, 'new-nonce', 'digest'), /Request limit/);
  for (let i = 1; i < 500; i++) {
    const id = i.toString(16).padStart(48, '0');
    state.tasks[id] = { ...task, id, thread: i.toString(16).padStart(64, '0'), publicThread: 't' + i, gatewayKey: `agent:main:hud:${id}` };
  }
  bindings.save(undefined, state);
  assert.throws(() => bindings.task(undefined, 'new-thread'), /task limit/);
});

test('ordinary Bindings still require separate cookies and support revocation', t => {
  const { root } = fixture(t), normal = new Bindings(path.join(root, 'normal'), Date.now, installation);
  assert.throws(() => normal.read());
  const first = normal.create(), second = normal.create(), task = normal.task(first, 'chat:one');
  assert.equal(normal.chats(second, 'main').length, 0);
  assert.throws(() => normal.ownedChat(second, task.id, 'main'));
  normal.revoke(first); assert.throws(() => normal.read(first));
});
