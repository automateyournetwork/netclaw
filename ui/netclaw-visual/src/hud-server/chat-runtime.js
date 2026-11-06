import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { readFile, access } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';
import { gatewayAgentId } from './gateway-agent.js';
const execute = promisify(execFile);
export function gatewayCallTimeout(method, env = process.env) {
  const name = method === 'models.list' ? 'NETCLAW_GATEWAY_CATALOG_TIMEOUT_MS'
    : ['sessions.list', 'chat.history'].includes(method) ? 'NETCLAW_GATEWAY_HISTORY_TIMEOUT_MS'
    : method === 'sessions.patch' ? 'NETCLAW_GATEWAY_SETTINGS_TIMEOUT_MS' : null;
  const requested = name ? Number(env[name]) : NaN;
  const maximum = method === 'sessions.patch' ? 120000 : 60000;
  return Number.isInteger(requested) && requested >= 20000 && requested <= maximum ? requested : 20000;
}
export function gatewayEnvironment(config, port, configPath, env = process.env, nodePath = process.execPath) {
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw Error('Invalid local gateway port.');
  const resolve = value => {
    if (typeof value !== 'string') return undefined;
    const reference = value.match(/^\$\{([A-Z_][A-Z0-9_]*)\}$/);
    return reference ? env[reference[1]] : value;
  };
  const auth = config.gateway?.auth || {};
  const token = auth.mode === 'password' ? undefined : resolve(auth.token) || env.OPENCLAW_GATEWAY_TOKEN;
  const password = token ? undefined : resolve(auth.password) || env.OPENCLAW_GATEWAY_PASSWORD;
  if (!token && !password) throw Error('Configured local gateway credentials are required.');
  // Pin the local target via the supported environment override. Credentials
  // stay off argv; never inherit a remote URL or a mismatched Node interpreter.
  return { ...env, PATH: `${path.dirname(nodePath)}${path.delimiter}${env.PATH || ''}`,
    ...(configPath ? { OPENCLAW_CONFIG_PATH: configPath } : {}),
    OPENCLAW_GATEWAY_URL: `ws://127.0.0.1:${port}`,
    OPENCLAW_GATEWAY_TOKEN: token || '', OPENCLAW_GATEWAY_PASSWORD: password || '' };
}
export async function gatewayCall(method, params, port, configPath) {
  const config = JSON.parse(await readFile(configPath, 'utf8'));
  // Resolve the owner's CLI before pinning Node in the child PATH. Otherwise
  // a sibling openclaw executable can shadow a configured wrapper/installation.
  let executable='openclaw';
  const names=process.platform==='win32'?['openclaw.exe','openclaw.cmd','openclaw']:['openclaw'];
  locate: for(const directory of (process.env.PATH||'').split(path.delimiter).filter(Boolean)){
    for(const name of names){
      const candidate=path.resolve(directory,name);
      try{await access(candidate,constants.X_OK);executable=candidate;break locate;}catch{}
    }
  }
  // Small cloud hosts can spend longer starting the native CLI. Discovery has
  // and history have bounded allowances; unrelated calls keep their deadline.
  const timeout = gatewayCallTimeout(method);
  const { stdout } = await execute(executable, ['gateway', 'call', method, '--params', JSON.stringify(params),
    '--timeout', '10000', '--json'],
  { env: gatewayEnvironment(config, port, configPath), timeout, maxBuffer: 4 * 1024 * 1024, windowsHide: true });
  return JSON.parse(stdout.slice(stdout.indexOf('{')));
}
export function createChatRuntime(call = gatewayCall) {
  const cache = new Map();
  return {
    async catalog(config, configPath) {
      const agentId = gatewayAgentId(config), port = config.gateway?.port || 18789;
      const key = JSON.stringify([agentId, port, configPath, config.agents]);
      const prior = cache.get(key);
      if (prior && Date.now() - prior.time < 60000) return prior.promise;
      const promise = (async () => {
        try {
          const data = await call('models.list', { view: 'configured' }, port, configPath);
          let native = [];
          try { native = JSON.parse(await readFile(path.join(path.dirname(configPath), 'agents', agentId, 'agent/codex-home/models_cache.json'), 'utf8')).models || []; } catch {}
          return (data.models || []).filter(m => m.available !== false && (m.agentRuntime?.id !== 'codex' || !native.length || native.some(n => n.slug === m.id && n.visibility === 'list'))).map(m => {
            const match = m.agentRuntime?.id === 'codex' && native.find(n => n.slug === m.id);
            return { ...m, thinkingLevels: match ? (m.thinkingLevels || []).filter(level => match.supported_reasoning_levels?.some(n => n.effort === level.id)) : m.thinkingLevels };
          });
        } catch { return null; }
      })();
      cache.set(key, { time: Date.now(), promise });
      return promise;
    },
    async apply({ key, model, effort, port, configPath }) {
      if (!key) throw Error('A private chat session is required for effort selection.');
      const result = await call('sessions.patch', { key, ...(model ? { model } : {}), thinkingLevel: effort || null }, port, configPath);
      if (result.ok === false || !result.entry) throw Error('The gateway did not confirm chat settings.');
      if ((effort && result.entry.thinkingLevel !== effort) || (!effort && result.entry.thinkingLevel != null)) throw Error('The gateway did not confirm the selected effort.');
    },
  };
}
