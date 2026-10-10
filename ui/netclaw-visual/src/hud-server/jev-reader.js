import os from 'node:os';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { mcpCommand } from '../security/command.js';
export function createJevReader(root, getEnvironment = () => process.env, runtimeHome = null) {
  return (id, task) => new Promise((resolve, reject) => {
    if (!/^[A-Za-z0-9_.:-]{1,128}$/.test(id) || !/^[A-Za-z0-9_.:/-]{1,128}$/.test(task)) return reject(Error('Unavailable'));
    const environment=getEnvironment();
    const home=runtimeHome || (environment.NETCLAW_RUNTIME==='hermes' ? environment.HERMES_HOME : environment.OPENCLAW_STATE_DIR || environment.OPENCLAW_HOME) || path.join(os.homedir(), '.openclaw');
    const python = path.join(home, 'jev-venv', 'bin', 'python');
    const command = mcpCommand([python, path.join(root, 'mcp-servers/jev-mcp/server.py'), '--read-task-id', task]);
    execFile('python3', [path.join(root, 'scripts/mcp-call.py'), command, 'jev_assessment', JSON.stringify({ assessment_id: id })], { timeout: 12000, maxBuffer: 1024 * 1024, env: { ...environment, JEV_DATA_DIR:environment.JEV_DATA_DIR || path.join(home,'jev'), MCP_CALL_TIMEOUT: '8' } }, (error, stdout) => {
      if (error) return reject(Error('Unavailable'));
      try { const result = JSON.parse(stdout); if (result.isError) throw Error(); const data = result.structuredContent || JSON.parse(result.content[0].text); const value = data.result || data; if (value.assessment_id !== id) throw Error(); resolve({ ...value, provider: value.endpoint === 'https://api.typesafe.ai/v1/systemone' ? 'TypeSafe / Jev' : 'Compatible endpoint' }); }
      catch { reject(Error('Unavailable')); }
    });
  });
}
