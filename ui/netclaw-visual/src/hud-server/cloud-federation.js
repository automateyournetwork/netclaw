import fs from 'node:fs';
import path from 'node:path';
import { boundedFile, noSymlink, loadProtectedAssets } from './protected-assets.js';
import { strictJson } from './protected-client.js';
import { readRemoteHudConfig } from './remote-hud.js';

const exact = (v, keys) => v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
const read = file => strictJson(boundedFile(file, 65536, true).toString('utf8'));
const uuid = value => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
const loopback = value => typeof value === 'string' && /^http:\/\/127\.0\.0\.1:[1-9][0-9]{0,4}$/.test(value) && Number(new URL(value).port) <= 65535;
export const ordinaryFederationCapability = Object.freeze({ schema: 1, execution: 'ordinary', peerChat: true });

/** An explicit fresh ordinary role. Never fall back from a protected profile. */
export function readCloudFederationConfig(config) {
  if (!exact(config, ['schemaVersion','mode','installationId','home','kind','origin','host','port','dist','manifest','manifestSha256','access','workspace','daemonUrl']) || config.schemaVersion !== 1 || config.mode !== 'ordinary-federation' || config.kind !== 'openclaw' || !uuid(config.installationId) || config.host !== '127.0.0.1' || !Number.isSafeInteger(config.port) || config.port < 1 || config.port > 65535 || !loopback(config.daemonUrl)) throw Error('invalid_ordinary_configuration');
  if (!exact(config.access, ['mode']) || config.access.mode !== 'open-lab') throw Error('invalid_ordinary_access');
  const origin = new URL(config.origin);
  if (origin.protocol !== 'https:' || origin.origin !== config.origin || origin.username || origin.password) throw Error('invalid_origin');
  noSymlink(config.home);
  const home = fs.lstatSync(config.home);
  if (!home.isDirectory() || home.uid !== process.getuid() || (home.mode & 0o777) !== 0o700) throw Error('invalid_home');
  try { fs.lstatSync(path.join(config.home, 'netclaw-federation/protected-profile.json')); throw Error('ordinary_has_protected_profile'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const identity = read(path.join(config.home, 'netclaw-hud/installation.json'));
  const role = read(path.join(config.home, 'netclaw-federation/ordinary-cloud.json'));
  if (!exact(identity, ['schemaVersion','installationId']) || identity.schemaVersion !== 1 || identity.installationId !== config.installationId || !exact(role, ['schemaVersion','installationId','role','access']) || role.schemaVersion !== 1 || role.installationId !== config.installationId || role.role !== 'border' || !exact(role.access, ['mode']) || role.access.mode !== 'open-lab') throw Error('invalid_ordinary_installation');
  const installation = Object.freeze({ home: config.home, kind: config.kind, installationId: config.installationId });
  if (!exact(config.workspace, ['path','sha256'])) throw Error('invalid_workspace');
  const workspace = readRemoteHudConfig(config.workspace.path, installation, config.workspace.sha256, { ordinary: true });
  if ([workspace.upstream, config.daemonUrl].includes(`http://127.0.0.1:${config.port}`) || workspace.upstream === config.daemonUrl) throw Error('ordinary_service_loop');
  return { ...config, authority: origin.host, installation, workspace, files: loadProtectedAssets({ ...config, workspace }) };
}

export function peerChatBody(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(k => !['peer','text','session_id'].includes(k)) || typeof value.peer !== 'string' || !/^as[0-9]{1,10}-(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(value.peer) || typeof value.text !== 'string' || !value.text.trim() || Buffer.byteLength(value.text) > 65536 || value.session_id !== undefined && value.session_id !== null && (typeof value.session_id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value.session_id))) throw Error('invalid_peer_chat');
  return { peer: value.peer, text: value.text, ...(value.session_id ? { session_id: value.session_id } : {}) };
}
