import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import net from 'node:net';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';

const source = fileURLToPath(new URL('../..', import.meta.url));
function request(port, headers = {}) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: '127.0.0.1', port, path: '/api/testbed/raw', headers }, res => {
      res.resume(); res.on('end', () => resolve(res.statusCode));
    });
    req.on('error', reject);
  });
}
function upgrade(port, origin) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: '127.0.0.1', port, path: '/ws', headers: {
      Connection: 'Upgrade', Upgrade: 'websocket', 'Sec-WebSocket-Version': '13',
      'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==', Origin: origin,
    } });
    req.on('upgrade', (res, socket) => { socket.destroy(); resolve(res.statusCode); });
    req.on('response', res => { res.resume(); resolve(res.statusCode); });
    req.on('error', reject);
  });
}

test('real HUD server rejects hostile HTTP and WebSocket requests before fixture access', { timeout: 15000 }, async t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-hud-security-'));
  const ui = path.join(root, 'ui', 'netclaw-visual');
  fs.mkdirSync(ui, { recursive: true });
  fs.mkdirSync(path.join(root, 'testbed'));
  fs.writeFileSync(path.join(root, 'testbed', 'testbed.yaml'), 'devices: {}\n');
  // The API composes sibling feature modules; include them in this isolated fixture.
  for (const name of fs.readdirSync(source).filter(name => name.endsWith('.js') || name === 'genie_parse.py' || name === 'package.json')) {
    fs.copyFileSync(path.join(source, name), path.join(ui, name));
  }
  for (const name of ['node_modules', 'src']) fs.symlinkSync(path.join(source, name), path.join(ui, name), 'dir');
  const socket = net.createServer(); socket.listen(0, '127.0.0.1'); await once(socket, 'listening');
  const port = socket.address().port; await new Promise(resolve => socket.close(resolve));
  const bin = path.join(root, 'bin'); fs.mkdirSync(bin);
  fs.writeFileSync(path.join(bin, 'openclaw'), `#!${process.execPath}
const fs = require('node:fs');
const path = require('node:path');
const method = process.argv[4];
const params = JSON.parse(process.argv[process.argv.indexOf('--params') + 1]);
if (method === 'models.list') console.log(JSON.stringify({models:[{provider:'fixture',id:'large',available:true,thinkingDefault:'low',thinkingLevels:[{id:'low'},{id:'high'}]}]}));
else if (method === 'sessions.patch') {
 if (fs.existsSync(path.join(process.env.HOME,'reject-patch'))) process.exit(1);
 fs.writeFileSync(path.join(process.env.HOME,'last-patch.json'),JSON.stringify(params));
 console.log(JSON.stringify({ok:true,entry:{thinkingLevel:params.thinkingLevel}}));
} else if (method === 'sessions.list') console.log(JSON.stringify({sessions:[]}));
else if (method === 'chat.history') console.log(JSON.stringify({messages:[{role:'user',content:'Earlier question'},{role:'assistant',content:'Earlier answer'}],sessionInfo:{}}));
else process.exit(1);
`, { mode: 0o700 });
  const child = spawn(process.execPath, ['server.js'], {
    cwd: ui, env: { PATH: `${bin}:${process.env.PATH}`, HOME: root, USERPROFILE: root,
      OPENCLAW_HOME: path.join(root, '.openclaw'), HUD_PORT: String(port), HUD_UI_PORT: '3000', HUD_CHAT_TIMEOUT_MS: '1000' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(async () => {
    if (child.exitCode === null) { child.kill(); await once(child, 'exit'); }
    fs.rmSync(root, { recursive: true, force: true });
  });
  let stderr = ''; child.stderr.on('data', chunk => { stderr += chunk; });
  await new Promise((resolve, reject) => {
    child.stdout.on('data', chunk => { if (String(chunk).includes('listening')) resolve(); });
    child.once('exit', code => reject(new Error(`HUD exited ${code}: ${stderr}`)));
    child.once('error', reject);
  });
  assert.equal(await request(port), 200, 'local CLI keeps access');
  assert.equal(await request(port, { Origin: 'http://127.0.0.1:3000' }), 200, 'local frontend keeps access');
  assert.equal(await request(port, { Origin: 'https://untrusted.example' }), 403, 'foreign browser cannot read fixture');
  assert.equal(await request(port, { Host: 'rebound.example' }), 403, 'DNS rebinding host rejected');
  assert.equal(await request(port, { Origin: 'null' }), 403, 'opaque origin rejected');
  assert.equal(await upgrade(port, 'https://untrusted.example'), 403, 'foreign WebSocket rejected');
  assert.equal(await upgrade(port, 'http://127.0.0.1:3000'), 101, 'local WebSocket preserved');

  const skills = path.join(root, 'workspace', 'skills');
  const sessions = path.join(root, '.openclaw', 'agents', 'main', 'sessions');
  const outside = path.join(root, 'outside');
  for (const dir of [skills, sessions, outside]) fs.mkdirSync(dir, { recursive:true });
  fs.writeFileSync(path.join(outside, 'SKILL.md'), '# outside fixture\n');
  fs.writeFileSync(path.join(outside, 'private.jsonl'), '{}\n');
  fs.symlinkSync(outside, path.join(skills, 'linked'), 'dir');
  fs.symlinkSync(path.join(outside, 'private.jsonl'), path.join(sessions, 'linked.jsonl'));
  fs.mkdirSync(path.join(skills, 'ordinary'));
  fs.writeFileSync(path.join(skills, 'ordinary', 'SKILL.md'), '# Ordinary\n\nValid skill.\n');
  fs.writeFileSync(path.join(sessions, 'ordinary.jsonl'), '{}\n');
  for (const route of ['/api/skill/ordinary']) {
    assert.equal((await fetch(`http://127.0.0.1:${port}${route}`)).status, 200, route);
  }
  for (const route of [
    '/api/skill/..%2f..%2foutside', '/api/skill/linked',
    '/api/session/ordinary/tools', '/api/session/..%2f..%2f..%2f..%2foutside%2fprivate/tools', '/api/session/linked/tools',
  ]) {
    assert.equal((await fetch(`http://127.0.0.1:${port}${route}`)).status, 404, route);
  }
  fs.writeFileSync(path.join(root, '.openclaw', 'openclaw.json'), JSON.stringify({
    agents: { defaults: { budget: { sessionBudgetUsd:0, maxToolCallsPerTurn:0 } } },
  }));
  const budget = await (await fetch(`http://127.0.0.1:${port}/api/budget/status`)).json();
  assert.equal(budget.sessionBudgetUsd, 0);
  assert.equal(budget.maxToolCallsPerTurn, 0);
  assert.equal(budget.status, 'halted');
  fs.writeFileSync(path.join(root, '.openclaw', 'openclaw.json'), JSON.stringify({ gateway: { port:19443, tls:{enabled:true}, controlUi:{basePath:'/operations'}, auth:{token:'never-project-this'} } }));
  const runtimeResponse = await fetch(`http://127.0.0.1:${port}/api/hud/runtime`);
  const runtime = await runtimeResponse.json();
  assert.equal(runtimeResponse.headers.get('cache-control'), 'no-store');
  assert.deepEqual(runtime.controlUi, {available:true,port:19443,basePath:'/operations',tls:true});
  assert.doesNotMatch(JSON.stringify(runtime), /never-project-this|token/);
  const requests = []; let emptyReply = false, stalledReply = false;
  const gateway = http.createServer((req, res) => {
    let body = ''; req.on('data', chunk => { body += chunk; }); req.on('end', () => {
      requests.push({ path:req.url, headers:req.headers, body:JSON.parse(body) });
      if (stalledReply) return;
      res.writeHead(200, {'Content-Type':'application/json'});
      res.end(JSON.stringify({choices:[{message:{content:emptyReply ? '' : 'Synthetic gateway reply'}}]}));
    });
  });
  gateway.listen(0, '127.0.0.1'); await once(gateway, 'listening');
  t.after(() => new Promise(resolve => { gateway.closeAllConnections(); gateway.close(resolve); }));
  fs.writeFileSync(path.join(root, '.openclaw', 'openclaw.json'), JSON.stringify({gateway:{port:gateway.address().port,auth:{token:'fixture-only-token'},http:{endpoints:{chatCompletions:{enabled:true}}}}}));
  const bootstrap = await fetch(`http://127.0.0.1:${port}/api/hud/session`, {method:'POST'});
  assert.equal(bootstrap.status, 200);
  const cookie = bootstrap.headers.get('set-cookie').split(';')[0];
  for (const hudThread of ['chat-fixture-one','chat-fixture-one','chat-fixture-two']) {
    const result = await fetch(`http://127.0.0.1:${port}/api/chat`, {method:'POST',headers:{'Content-Type':'application/json',Cookie:cookie},body:JSON.stringify({message:'Synthetic question',messages:[{role:'user',content:'Synthetic question'}],hudThread})});
    assert.equal(result.status, 200);const reply = await result.json();
    assert.equal(reply.fromGateway,true);assert.equal(reply.response,'Synthetic gateway reply');
  }
  assert.equal(requests.length, 3);
  assert.equal(requests[0].path, '/v1/chat/completions');
  assert.equal(requests[0].headers.authorization,'Bearer fixture-only-token');
  assert.deepEqual(requests[0].body.messages,[{role:'user',content:'Synthetic question'}]);
  assert.ok(requests[0].headers['x-openclaw-session-key']);
  assert.equal(requests[0].headers['x-openclaw-session-key'],requests[1].headers['x-openclaw-session-key']);
  assert.notEqual(requests[1].headers['x-openclaw-session-key'],requests[2].headers['x-openclaw-session-key']);
  const modelConfig = { agents: { defaults: { model: 'fixture/fast@private-profile', models: { 'fixture/fast@private-profile': {}, 'fixture/large': {} } } }, gateway:{port:gateway.address().port,auth:{token:'fixture-only-token'},http:{endpoints:{chatCompletions:{enabled:true}}}} };
  fs.writeFileSync(path.join(root, '.openclaw', 'openclaw.json'), JSON.stringify(modelConfig));
  const settingsGraph = await (await fetch(`http://127.0.0.1:${port}/api/graph`)).json();
  assert.equal(settingsGraph.settings.find(row => row.label === 'Primary Model').value, 'fixture/fast');
  assert.doesNotMatch(JSON.stringify(settingsGraph.config), /private-profile|fixture-only-token/);
  const catalog = await (await fetch(`http://127.0.0.1:${port}/api/chat/models`)).json();
  assert.doesNotMatch(JSON.stringify(catalog), /private-profile|fixture-only-token/);
  for (const chatModel of [catalog.models.find(m => m.label === 'fixture/large').id, '']) {
    const result = await fetch(`http://127.0.0.1:${port}/api/chat`, {method:'POST',headers:{'Content-Type':'application/json',Cookie:cookie},body:JSON.stringify({message:'Model fixture',messages:[{role:'user',content:'Model fixture'}],hudThread:'chat-model-fixture',chatModel})});
    assert.equal((await result.json()).fromGateway, true);
    assert.equal(requests.at(-1).headers['x-openclaw-model'], chatModel ? 'fixture/large' : 'fixture/fast@private-profile');
  }
  const selectedId = catalog.models.find(m => m.label === 'fixture/large').id;
  const effortRequest = { message: 'Effort fixture', messages: [{role:'user',content:'Effort fixture'}], hudThread:'chat-effort-fixture', chatModel:selectedId, chatEffort:'low' };
  const sendEffort = body => fetch(`http://127.0.0.1:${port}/api/chat`, { method:'POST', headers:{'Content-Type':'application/json',Cookie:cookie}, body:JSON.stringify(body) });
  assert.equal((await (await sendEffort(effortRequest)).json()).fromGateway, true);
  const patch = JSON.parse(fs.readFileSync(path.join(root,'last-patch.json')));
  assert.equal(patch.key, requests.at(-1).headers['x-openclaw-session-key']);
  assert.equal(patch.model, 'fixture/large'); assert.equal(patch.thinkingLevel, 'low');
  const beforeEffortReject = requests.length;
  assert.equal((await sendEffort({...effortRequest,chatEffort:'ultra'})).status,400);
  fs.writeFileSync(path.join(root,'reject-patch'),'yes');
  const refused = await (await sendEffort(effortRequest)).json();
  assert.equal(refused.fromGateway,false); assert.match(refused.gatewayIssue,/No message was sent/);
  assert.equal(requests.length,beforeEffortReject,'failed settings never start inference');
  fs.unlinkSync(path.join(root,'reject-patch'));
  assert.equal((await (await sendEffort({...effortRequest,chatEffort:''})).json()).fromGateway,true);
  assert.equal(JSON.parse(fs.readFileSync(path.join(root,'last-patch.json'))).thinkingLevel,null);
  const historyList = await (await fetch(`http://127.0.0.1:${port}/api/chat/conversations`,{headers:{Cookie:cookie}})).json();
  const saved = historyList.conversations.find(c=>c.thread==='chat-effort-fixture');
  assert.ok(saved); assert.equal(saved.title,'Effort fixture');
  const opened = await (await fetch(`http://127.0.0.1:${port}/api/chat/conversations/${saved.id}/open`,{method:'POST',headers:{Cookie:cookie}})).json();
  assert.equal(opened.thread,'chat-effort-fixture'); assert.equal(opened.messages[1].content,'Earlier answer');
  assert.equal((await fetch(`http://127.0.0.1:${port}/api/chat/conversations/${saved.id}/open`,{method:'POST'})).status,404);
  const originalKey = requests.at(-1).headers['x-openclaw-session-key'];
  assert.equal((await (await sendEffort({...effortRequest,hudThread:opened.thread})).json()).fromGateway,true);
  assert.equal(requests.at(-1).headers['x-openclaw-session-key'],originalKey,'reopened chat continues exact gateway context');
  const beforeRejected = requests.length;
  const rejected = await fetch(`http://127.0.0.1:${port}/api/chat`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'Reject fixture',chatModel:'unconfigured-model'})});
  assert.equal(rejected.status, 400);
  assert.equal(requests.length, beforeRejected, 'invalid selection never reaches gateway');
  emptyReply = true;
  const empty = await (await fetch(`http://127.0.0.1:${port}/api/chat`, {method:'POST',headers:{'Content-Type':'application/json',Cookie:cookie},body:JSON.stringify({message:'Empty reply fixture',messages:[{role:'user',content:'Empty reply fixture'}],hudThread:'chat-empty-fixture'})})).json();
  assert.equal(empty.fromGateway,false);assert.match(empty.gatewayIssue,/empty chat response/);
  stalledReply = true;
  const timedOut = await (await fetch(`http://127.0.0.1:${port}/api/chat`, {
    method:'POST', headers:{'Content-Type':'application/json',Cookie:cookie},
    body:JSON.stringify({message:'Stalled fixture',messages:[{role:'user',content:'Stalled fixture'}],hudThread:'chat-timeout-fixture'}),
  })).json();
  assert.equal(timedOut.fromGateway, false);
  assert.match(timedOut.gatewayIssue, /did not finish within/);
  assert.match(timedOut.gatewayIssue, /check the gateway for any tool actions before retrying/);
  assert.equal((await fetch(`http://127.0.0.1:${port}/api/chat/history`)).status,400,'unscoped history is unavailable');


});
