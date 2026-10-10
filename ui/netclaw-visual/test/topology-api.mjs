import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import ssh2 from 'ssh2';
import { FACT_FIXTURES } from './topology-fixtures.mjs';
import { TOPOLOGY_SCOPES, commandsForTopologyScopes } from '../topology-scope.js';
import { TopologyService } from '../topology-service.js';

const root = path.resolve(import.meta.dirname, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-topology-api-'));
const clients = new Set();
const commands = [];
let passwordAttempts = 0;
let processHandle;
let mock;
let output = '';
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(check) {
  for (let i = 0; i < 120; i++) { if (await check()) return; await pause(50); }
  throw new Error(`Timed out waiting for mock topology API. ${output}`);
}
try {
  const keys = crypto.generateKeyPairSync('rsa', {
    modulusLength: 2048,
    privateKeyEncoding: { type: 'pkcs1', format: 'pem' },
    publicKeyEncoding: { type: 'spki', format: 'pem' },
  });
  const fingerprint = `SHA256:${crypto.createHash('sha256').update(ssh2.utils.parseKey(keys.privateKey).getPublicSSH()).digest('base64').replace(/=+$/, '')}`;
  mock = new ssh2.Server({ hostKeys: [keys.privateKey] }, client => {
    clients.add(client); client.on('close', () => clients.delete(client)); client.on('error', () => {});
    client.on('authentication', ctx => {
      if (ctx.method === 'password') passwordAttempts++;
      return ctx.method === 'password' && ctx.username === 'tester' && ctx.password === 'test-only-password' ? ctx.accept() : ctx.reject();
    });
    client.on('ready', () => client.on('session', accept => {
      const session = accept();
      session.on('pty', acceptPty => acceptPty?.());
      session.on('shell', acceptShell => {
        const channel = acceptShell(); let pending = '';
        channel.write('MOCK#');
        channel.on('data', chunk => {
          pending += chunk.toString();
          while (pending.includes('\n')) {
            const index = pending.indexOf('\n'); const cmd = pending.slice(0, index).trim(); pending = pending.slice(index + 1); commands.push(cmd);
            const response = cmd === 'show ip route' ? 'Codes: C - connected, L - local\r\nGateway of last resort is not set\r\nC 198.51.100.0/24 is directly connected, GigabitEthernet0/1\r\nL 198.51.100.1/32 is directly connected, GigabitEthernet0/1\r\n'
              : cmd === 'show ip route vrf *' ? 'Routing Table: CORP\r\nCodes: C - connected\r\nC 203.0.113.0/24 is directly connected, GigabitEthernet0/2\r\n' : (FACT_FIXTURES[cmd]?.replace(/\nMOCK#$/, '') || '');
            channel.write(`${cmd}\r\n${response}\r\nMOCK#`);
          }
        });
      });
    }));
  });
  await new Promise(resolve => mock.listen(0, '127.0.0.1', resolve));
  const sshPort = mock.address().port;
  const probe = net.createServer();
  await new Promise(resolve => probe.listen(0, '127.0.0.1', resolve));
  const port = probe.address().port; await new Promise(resolve => probe.close(resolve));
  const testbed = path.join(temp, 'testbed.json');
  const knownHosts = path.join(temp, 'known.json');
  const grants = path.join(temp, 'grants.json');
  fs.writeFileSync(testbed, JSON.stringify({ testbed: { credentials: { default: { username: 'tester', password: 'test-only-password' } } }, devices: {
    MOCK: { alias: 'Synthetic API router', os: 'iosxe', connections: { ssh: { protocol: 'ssh', ip: '127.0.0.1', port: sshPort } } },
  } }));
  fs.writeFileSync(knownHosts, JSON.stringify({ [`127.0.0.1:${sshPort}`]: { fingerprint } }));
  processHandle = spawn(process.execPath, ['server.js'], { cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'], env: {
    ...process.env, HUD_PORT: String(port), NETCLAW_TESTBED_FILE: testbed, NETCLAW_TERMINAL_KNOWN_HOSTS_FILE: knownHosts,
    NETCLAW_TOPOLOGY_FILE: grants, OPENCLAW_HOME: temp,
  } });
  processHandle.stdout.on('data', chunk => { output += chunk; }); processHandle.stderr.on('data', chunk => { output += chunk; });
  const base = `http://127.0.0.1:${port}/api/topology`;
  const post = (route, body, origin = 'http://localhost:3000') => fetch(`${base}/${route}`, { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: origin }, body: JSON.stringify(body) });
  await until(async () => { try { return (await fetch(`${base}/status`)).ok; } catch { return false; } });
  assert.equal(commands.length, 0, 'no SSH without authorization');
  assert.equal((await post('authorize', { authorized: true, devices: [{ id: 'MOCK' }], intervalSeconds: 30 }, 'https://untrusted.example')).status, 403);
  assert.equal((await post('authorize', { devices: [{ id: 'MOCK' }], intervalSeconds: 30 })).status, 400);
  assert.equal((await post('authorize', { authorized: true, devices: [{ id: 'MOCK' }], intervalSeconds: 30 })).status, 200);
  await until(async () => (await (await fetch(`${base}/status`)).json()).devices[0]?.phase === 'current');
  const response = await (await post('lookup', { type: 'prefix', value: '198.51.100.0/24', vrf: 'default' })).json();
  assert.equal(response.observations[0].connected, true);
  assert.equal(response.observations[0].stale, false);
  assert.equal(response.observations[0].device, 'Synthetic API router');
  assert.equal((await (await post('lookup', { type: 'prefix', value: '203.0.113.0/24', vrf: 'CORP' })).json()).observations.length, 1);
  assert.deepEqual(commands, ['terminal length 0', 'show ip route', 'show ip route vrf *']);
  assert.ok(!JSON.stringify(response).includes('test-only-password'));
  assert.equal((await post('revoke', {})).status, 200);
  assert.equal((await (await post('lookup', { type: 'prefix', value: '198.51.100.0/24' })).json()).observations.length, 0);
  assert.deepEqual(JSON.parse(fs.readFileSync(grants)).grants, []);
  commands.length = 0;
  const scopes = TOPOLOGY_SCOPES.map(scope => scope.id);
  assert.equal((await post('authorize', { authorized: true, scopes, devices: [{ id: 'MOCK' }], intervalSeconds: 30 })).status, 200);
  await until(async () => (await (await fetch(`${base}/status`)).json()).devices[0]?.phase === 'current');
  const identity = await (await post('lookup', { type: 'ip', value: '198.51.100.1', vrf: 'default' })).json();
  assert.equal(identity.context.identities[0].hostname, 'MOCK');
  assert.equal(identity.context.identities[1].serialNumber, 'DEMO-SERIAL-001');
  const endpoint = await (await post('lookup', { type: 'ip', value: '198.51.100.25', vrf: 'default' })).json();
  assert.equal(endpoint.context.arp[0].mac, '0011.2233.4455');
  assert.equal(endpoint.context.switching[0].vlanName, 'DEMO-USERS');
  assert.equal(endpoint.context.neighbors[0].neighbor, 'DEMO-SWITCH');
  assert.deepEqual(commands, commandsForTopologyScopes(scopes), 'only the approved command set is sent');
  assert.equal((await post('revoke', {})).status, 200);
  // GUI onboarding verifies keys before authentication, then retains passwords
  // in RAM only. The testbed deliberately contains unusable saved credentials.
  const loginTestbed = JSON.parse(fs.readFileSync(testbed));
  loginTestbed.testbed.credentials.default = { username: 'wrong-saved-user', password: 'wrong-saved-password' };
  fs.writeFileSync(testbed, JSON.stringify(loginTestbed));
  fs.writeFileSync(knownHosts, '{}');
  const loginInput = { device: 'MOCK', credentials: { username: 'tester', password: 'test-only-password' } };
  assert.equal((await post('login', loginInput, 'https://untrusted.example')).status, 403);
  const authBefore = passwordAttempts;
  const commandsBefore = commands.length;
  const challenge = await (await post('login', loginInput)).json();
  assert.equal(challenge.status, 'host-key', JSON.stringify(challenge));
  assert.equal(challenge.fingerprint, fingerprint);
  assert.equal(challenge.changed, false);
  assert.equal(passwordAttempts, authBefore, 'no password sent to an unapproved host key');
  assert.deepEqual(JSON.parse(fs.readFileSync(knownHosts)), {}, 'preflight never auto-trusts');
  assert.equal((await post('login', { ...loginInput, challenge: 'invented-token' })).status, 400);
  const verified = await (await post('login', { ...loginInput, challenge: challenge.challenge })).json();
  assert.equal(verified.status, 'ready', JSON.stringify(verified));
  assert.equal(verified.sessionCredentials, true);
  assert.equal(commands.length, commandsBefore, 'login verification does not execute commands');
  assert.equal(JSON.parse(fs.readFileSync(knownHosts))[`127.0.0.1:${sshPort}`].fingerprint, fingerprint);
  assert.equal((await post('login', { ...loginInput, challenge: challenge.challenge })).status, 400, 'approval token is single-use');
  assert.equal((await post('authorize', { authorized: true, devices: [{ id: 'MOCK' }], intervalSeconds: 30 })).status, 200);
  await until(async () => (await (await fetch(`${base}/status`)).json()).devices[0]?.phase === 'current');
  const persisted = fs.readFileSync(grants, 'utf8');
  assert.equal(JSON.parse(persisted).grants[0].sessionCredentials, true);
  const restartedService = new TopologyService({ file: grants, autoStart: false });
  assert.equal(restartedService.status().devices[0].phase, 'authorization-needed', 'RAM credentials require login after restart');
  assert.match(restartedService.status().devices[0].error, /Log in again/);
  restartedService.stop();
  assert.ok(!persisted.includes('test-only-password'));
  assert.ok(!JSON.stringify(await (await fetch(`${base}/status`)).json()).includes('test-only-password'));
  assert.ok(!fs.readFileSync(testbed, 'utf8').includes('test-only-password'), 'GUI login never rewrites testbed credentials');
  assert.equal((await post('revoke', {})).status, 200);
  assert.equal((await post('login', { device: 'MOCK' })).status, 400, 'revocation forgets entered credentials');
  const badPassword = await (await post('login', { device: 'MOCK', credentials: { username: 'tester', password: 'bad-test-password' } })).json();
  assert.match(badPassword.error, /Login failed/);
  assert.ok(!JSON.stringify(badPassword).includes('bad-test-password'));
  fs.writeFileSync(knownHosts, JSON.stringify({ [`127.0.0.1:${sshPort}`]: { fingerprint: 'SHA256:previous-key' } }));
  const changed = await (await post('login', loginInput)).json();
  assert.equal(changed.status, 'host-key');
  assert.equal(changed.changed, true);
  assert.equal(changed.previousFingerprint, 'SHA256:previous-key');
  assert.equal((await post('revoke', {})).status, 200);
  assert.equal((await post('login', { ...loginInput, challenge: changed.challenge })).status, 400, 'revocation invalidates pending host-key approval');
  console.log('Topology HTTP + SSH integration passed using a local synthetic router only.');
} finally {
  if (processHandle && processHandle.exitCode == null) {
    processHandle.kill(); await Promise.race([new Promise(resolve => processHandle.once('exit', resolve)), pause(2000)]);
    if (processHandle.exitCode == null) processHandle.kill('SIGKILL');
  }
  processHandle?.stdout?.destroy(); processHandle?.stderr?.destroy(); processHandle?.unref();
  for (const client of clients) { client.end(); client._sock?.destroy(); }
  if (mock?.listening) {
    mock.unref();
    await Promise.race([new Promise(resolve => mock.close(resolve)), pause(1000)]);
  }
  // All targets were created by this test inside this exact temporary folder.
  fs.rmSync(temp, {recursive:true, force:true});
}
// As in terminal-smoke.mjs, Windows ssh2 can retain a native handle after
// closing. Reached only after every assertion and cleanup succeeded.
process.exit(0);
