import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const invalid = () => { throw Error('selection_invalid: repair the runtime selection descriptor or explicit home.'); };
export function resolveValues(env, ownerHome, descriptor = null) {
  if (descriptor !== null && (typeof descriptor !== 'object' || descriptor.schemaVersion !== 1 || !['openclaw','hermes'].includes(descriptor.kind) || typeof descriptor.home !== 'string' || !path.isAbsolute(descriptor.home))) invalid();
  const kind = env.NETCLAW_RUNTIME ?? descriptor?.kind ?? 'openclaw';
  if (!['openclaw','hermes'].includes(kind)) invalid();
  const matching = descriptor?.kind === kind ? descriptor : {};
  const override = kind === 'hermes' ? env.HERMES_HOME : env.OPENCLAW_STATE_DIR || env.OPENCLAW_HOME;
  const home = path.normalize(override || matching.home || path.join(ownerHome, '.' + kind));
  if (!path.isAbsolute(home) || home === path.parse(home).root) invalid();
  const inherited = home === matching.home ? matching.configPath : undefined;
  const configPath = (kind === 'openclaw' && (env.OPENCLAW_CONFIG_PATH || inherited)) || path.join(home, kind === 'hermes' ? 'config.yaml' : 'openclaw.json');
  if (!path.isAbsolute(configPath)) invalid();
  return { kind, home, configPath: path.normalize(configPath) };
}
export function selectionFile(env = process.env) {
  return path.join(env.XDG_CONFIG_HOME || path.join(env.HOME || os.homedir(), '.config'), 'netclaw', 'runtime.json');
}
export function readPrivate(file, limit = 8192) {
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > limit || (process.platform !== 'win32' && (stat.mode & 0o077 || stat.uid !== process.getuid()))) invalid();
  const fd = fs.openSync(file, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
  try { return JSON.parse(fs.readFileSync(fd, 'utf8')); } finally { fs.closeSync(fd); }
}
export function privateDirectory(directory) {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const stat = fs.lstatSync(directory);
  if (!stat.isDirectory() || stat.isSymbolicLink() || (process.platform !== 'win32' && (stat.mode & 0o077 || stat.uid !== process.getuid()))) invalid();
}
export function writePrivate(file, value) {
  privateDirectory(path.dirname(file));
  if (fs.existsSync(file) || (() => { try { return fs.lstatSync(file).isSymbolicLink(); } catch { return false; } })()) readPrivate(file);
  const temp = `${file}.${randomUUID()}.tmp`;
  const fd = fs.openSync(temp, 'wx', 0o600);
  try { fs.writeFileSync(fd, JSON.stringify(value, null, 2) + '\n'); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  fs.renameSync(temp, file);
}
export function resolveRuntime({ env = process.env, initialize = false, platform = process.platform } = {}) {
  let descriptor = null;
  try { descriptor = readPrivate(selectionFile(env)); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const value = resolveValues(env, env.HOME || os.homedir(), descriptor);
  if (platform === 'win32' && value.kind === 'hermes') throw Error('capability_unsupported: launch Hermes HUD inside Ubuntu on WSL2.');
  if (fs.existsSync(value.home)) {
    const stat = fs.lstatSync(value.home);
    if (!stat.isDirectory() || stat.isSymbolicLink() || (platform !== 'win32' && stat.uid !== process.getuid())) invalid();
    value.home = fs.realpathSync(value.home);
  }
  const statePath = path.join(value.home, 'netclaw-hud');
  const identity = path.join(statePath, 'installation.json');
  let installationId;
  try { const saved = readPrivate(identity); if (saved.schemaVersion !== 1 || !/^[a-f0-9-]{36}$/.test(saved.installationId)) invalid(); installationId = saved.installationId; }
  catch (error) {
    if (error.code !== 'ENOENT') throw error;
    if (initialize) {
      privateDirectory(statePath); installationId = randomUUID();
      let fd;
      try { fd=fs.openSync(identity,'wx',0o600);fs.writeFileSync(fd,JSON.stringify({schemaVersion:1,installationId}));fs.fsyncSync(fd); }
      catch(error) { if(error.code!=='EEXIST')throw error; const existing=readPrivate(identity); if(existing.schemaVersion!==1 || !/^[a-f0-9-]{36}$/.test(existing.installationId))invalid(); installationId=existing.installationId; }
      finally { if(fd!==undefined)fs.closeSync(fd); }
    }
  }
  return { ...value, installationId: installationId || null, statePath, envPath: path.join(value.home,'.env'),
    skillsPath: path.join(value.home, value.kind === 'hermes' ? 'skills' : 'workspace/skills'),
    workspacePath: path.join(value.home,'workspace'), descriptorFile: selectionFile(env) };
}
export function selectRuntime(kind, home, env = process.env) {
  if(process.platform==='win32' && kind==='hermes')throw Error('capability_unsupported: launch Hermes HUD inside Ubuntu on WSL2.');
  const value = resolveValues({ NETCLAW_RUNTIME: kind, [kind === 'hermes' ? 'HERMES_HOME' : 'OPENCLAW_HOME']: home }, env.HOME || os.homedir());
  if (!fs.statSync(value.home).isDirectory()) invalid();
  writePrivate(selectionFile(env), { schemaVersion:1,...value });
  const selectedEnv={...env,NETCLAW_RUNTIME:kind};
  for(const key of ['HERMES_HOME','OPENCLAW_HOME','OPENCLAW_STATE_DIR','OPENCLAW_CONFIG_PATH'])delete selectedEnv[key];
  selectedEnv[kind==='hermes'?'HERMES_HOME':'OPENCLAW_HOME']=value.home;
  return resolveRuntime({env:selectedEnv,initialize:true});
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv[2] === '--fixture') {
      const fixture = JSON.parse(fs.readFileSync(0,'utf8')); let result;
      try { result = resolveValues(fixture.env, '/owner', fixture.descriptor); } catch { result = {error:true}; }
      console.log(JSON.stringify(result));
    } else console.log(JSON.stringify(resolveRuntime()));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
