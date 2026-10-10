import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import path from 'node:path';
import { readPrivate } from './selection.js';
const names = ['status','conversation_open','history','submit','request_status','events','approval','stop'].map(n => 'hermes_hud_' + n);
export function createHermesRuntime(installation, root, { env = process.env } = {}) {
  let pending;
  const connect = async () => {
    const client = new Client({ name: 'netclaw-hud', version: '1.0.0' });
    const direct = env.NETCLAW_HUD_BRIDGE_PYTHON;
    const childEnv = Object.fromEntries(Object.entries(env).filter(([k]) => !k.startsWith('OPENCLAW_')));
    let auth={};
    if(!childEnv.NETCLAW_HERMES_HUD_API_KEY) auth=readPrivate(path.join(installation.statePath || path.join(installation.home,'netclaw-hud'),'companion-auth.json'));
    Object.assign(childEnv, { HERMES_HOME: installation.home, NETCLAW_RUNTIME: 'hermes', NETCLAW_HUD_INSTALLATION_ID: installation.installationId, PYTHON_DOTENV_DISABLED: '1',
      NETCLAW_RUNTIME_ROOT:path.join(installation.home,'python-runtimes'),NETCLAW_RUNTIME_ENV:path.join(installation.home,'.env'),
      NETCLAW_HERMES_HUD_API_KEY:childEnv.NETCLAW_HERMES_HUD_API_KEY || auth.key,
      NETCLAW_HERMES_HUD_PORT:childEnv.NETCLAW_HERMES_HUD_PORT || String(auth.port || 8643) });
    const transport = new StdioClientTransport({ command: direct || 'python3',
      args: direct ? ['-u', path.join(root, 'mcp-servers/hermes-hud-mcp/server.py')] : ['-u',path.join(root,'scripts/component-launch.py'),'hermes-hud','--server','hermes-hud-mcp'],
      cwd: root, env: childEnv, stderr: 'ignore' });
    await client.connect(transport, { timeout: 10000 });
    const listed = (await client.listTools()).tools.map(t => t.name).sort();
    if (JSON.stringify(listed) !== JSON.stringify([...names].sort())) { await client.close(); throw Error('capability_unavailable'); }
    client.onclose = () => { pending = null; };
    return client;
  };
  return {
    kind: 'hermes',
    async call(operation, args = {}) {
      const name = 'hermes_hud_' + operation;
      if (!names.includes(name)) throw Error('capability_unsupported');
      pending ||= connect().catch(error => { pending = null; throw error; });
      const client = await pending;
      const result = await client.callTool({ name, arguments: { ...args, installationId: installation.installationId } }, { timeout: 15000 });
      if (result.isError) throw Object.assign(Error('runtime_unavailable'), { cause: result.content });
      const value = result.structuredContent || JSON.parse(result.content.filter(c => c.type === 'text').map(c => c.text).join(''));
      const output=value.result || value;
      if(output.error)throw Object.assign(Error(output.error.message),{code:output.error.code});
      return output;
    },
    async close() { if (pending) await (await pending).close(); pending = null; },
  };
}
