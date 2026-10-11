import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { ownedDirectory, readOwned } from './files.js';
import { fail, invariant } from './errors.js';
import { supportsHudNode } from '../../../../scripts/hud-node-version.mjs';

export function bindInstallation({ home, kind, expectedInstallationId }, { nodeVersion = process.versions.node } = {}) {
  invariant(process.platform !== 'win32', 'UNSUPPORTED');
  invariant(supportsHudNode(nodeVersion), 'INCOMPATIBLE');
  invariant(['openclaw', 'hermes'].includes(kind));
  invariant(typeof home === 'string' && path.isAbsolute(home) && home !== path.parse(home).root);
  ownedDirectory(home, { privateMode: false });
  const statePath = path.join(home, 'netclaw-hud');
  const identityPath = path.join(statePath, 'installation.json');
  function readIdentity() {
    try {
      ownedDirectory(statePath);
      const value = JSON.parse(readOwned(identityPath, { limit: 8192 }));
      invariant(value.schemaVersion === 1 && /^[a-f\d]{8}(?:-[a-f\d]{4}){3}-[a-f\d]{12}$/.test(value.installationId), 'INCOMPATIBLE');
      return value.installationId;
    } catch (error) { if (error.code === 'ENOENT') fail('INCOMPATIBLE'); throw error; }
  }
  const installationId = readIdentity();
  invariant(!expectedInstallationId || installationId === expectedInstallationId, 'IDENTITY_CHANGED');
  const configPath = path.join(home, kind === 'hermes' ? 'config.yaml' : 'openclaw.json');
  readOwned(configPath, { limit: 4 * 1024 * 1024 });
  const user = os.userInfo();
  const hostId = createHash('sha256').update(`${os.hostname()}\0${fs.realpathSync(home)}\0${installationId}`).digest('hex');
  const principal = Object.freeze({ surface: 'operator', principalId: `os:${user.uid}`, grantId: null, generation: 0, installationId });
  return Object.freeze({ installationId, home, kind, statePath, configPath, envPath: path.join(home, '.env'), hostId, principal,
    assertCurrent() { ownedDirectory(home, { privateMode: false }); invariant(readIdentity() === installationId, 'IDENTITY_CHANGED'); readOwned(configPath, { limit: 4 * 1024 * 1024 }); },
  });
}
