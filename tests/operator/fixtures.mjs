import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

/** All fixtures use freshly allocated homes. Never derive a target from HOME. */
export function installationFixture(t, kind = 'openclaw') {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw150-fixture-')));
  fs.chmodSync(root, 0o700);
  const home = path.join(root, kind), statePath = path.join(home, 'netclaw-hud');
  fs.mkdirSync(statePath, { recursive: true, mode: 0o700 });
  const installationId = randomUUID();
  fs.writeFileSync(path.join(statePath, 'installation.json'), JSON.stringify({ schemaVersion: 1, installationId }), { mode: 0o600 });
  const configPath = path.join(home, kind === 'hermes' ? 'config.yaml' : 'openclaw.json');
  fs.writeFileSync(configPath, kind === 'hermes' ? 'model: fixture\n' : '{"agents":{}}\n', { mode: 0o600 });
  fs.writeFileSync(path.join(home, '.env'), '# synthetic configuration\nUNMANAGED=value\n', { mode: 0o600 });
  const cleanup = () => fs.rmSync(root, { recursive: true, force: true });
  t?.after(cleanup);
  return { root, home, statePath, configPath, installationId, kind, cleanup };
}

export const nonce = (time = Date.now()) => `${time}:${randomUUID()}`;
export function authoritativeApproval() {
  let valid = true;
  const calls = [];
  return {
    calls, withdraw() { valid = false; },
    async verify(reference, intent) {
      calls.push({ reference, intent });
      return { verified: valid && reference === 'CHG-fixture', state: valid ? 'Implement' : 'Withdrawn',
        actionDigest: intent.actionDigest, approverId: 'independent-approver', incidentsClear: true };
    },
  };
}
export function auditFixture() {
  const records = [];
  return { records, available: true, async record(value) {
    if (!this.available) throw new Error('synthetic audit loss');
    records.push(structuredClone(value)); return { commit: randomUUID(), source: 'synthetic-audit' };
  } };
}
