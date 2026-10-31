import path from 'node:path';
import { execFile } from 'node:child_process';
import { isIP } from 'node:net';
import { cookieFrom } from './bindings.js';
import { mcpCommand } from '../security/command.js';

const messages = Object.freeze({
  disabled: 'Convergence is disabled.', not_configured: 'Convergence connection settings are incomplete.',
  invalid_argument: 'Choose a supported flow window, address and exporter.',
  unauthorized: 'Convergence access was denied.', unavailable: 'Convergence is unavailable.',
  timeout: 'Convergence did not respond before the deadline.', compatibility: 'The Convergence response is incompatible.',
});
const statuses = { disabled: 409, not_configured: 409, invalid_argument: 400, unauthorized: 403, unavailable: 503, timeout: 504, compatibility: 502 };
const fail = (code = 'unavailable') => ({ ok: false, error: { code, message: messages[code] || messages.unavailable } });
export const convergenceEnabled = env => env.CONVERGENCE_ENABLED === 'true';
const tools = Object.freeze({ summary: 'convergence_flow_summary', evidence: 'convergence_flow_evidence' });

// Same launcher and isolated interpreter as the native MCP registration. No shell,
// browser-selected command, arbitrary HTTP path or second API client is involved.
export function createConvergenceReader(root, getEnvironment, execute = execFile) {
  return (kind, args) => new Promise(resolve => {
    if (!Object.hasOwn(tools, kind)) return resolve(fail('invalid_argument'));
    const env = getEnvironment();
    if (!convergenceEnabled(env)) return resolve(fail('disabled'));
    const command = mcpCommand(['python3', path.join(root, 'scripts/component-launch.py'), 'convergence-read']);
    execute('python3', [path.join(root, 'scripts/mcp-call.py'), command, tools[kind], JSON.stringify(args)], {
      env: { ...env, MCP_CALL_TIMEOUT: '24' }, timeout: 28000, maxBuffer: 2 * 1024 * 1024,
    }, (error, stdout) => {
      if (error) return resolve(fail(error.killed ? 'timeout' : 'unavailable'));
      try {
        const result = JSON.parse(stdout);
        if (result.isError) return resolve(fail());
        const structured = result.structuredContent || JSON.parse(result.content[0].text);
        const value = structured.result || structured;
        if (value.ok === false) return resolve(fail(Object.hasOwn(messages, value.error?.code) ? value.error.code : 'unavailable'));
        if (value.ok !== true || !value.data || typeof value.data !== 'object' || value.data.site !== env.CONVERGENCE_SITE) return resolve(fail('compatibility'));
        resolve({ ok: true, data: value.data });
      } catch { resolve(fail('compatibility')); }
    });
  });
}

export function flowArguments(kind, query = {}) {
  const names = kind === 'summary' ? ['range', 'exporter'] : ['address', 'start', 'end', 'exporter'];
  if (Object.keys(query).some(k => !names.includes(k)) || Object.values(query).some(v => typeof v !== 'string' || v.length > 128)) throw Error();
  const result = { ...query };
  if (result.exporter !== undefined && !isIP(result.exporter)) throw Error();
  if (kind === 'summary') {
    result.range ||= '1h';
    if (!['15m', '1h', '6h', '24h'].includes(result.range)) throw Error();
  } else {
    if (!isIP(result.address || '')) throw Error();
    const iso = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/;
    if (![result.start, result.end].every(v => typeof v === 'string' && iso.test(v) && Number.isFinite(Date.parse(v)))) throw Error();
    const span = Date.parse(result.end) - Date.parse(result.start);
    if (span <= 0 || span > 86400000) throw Error();
  }
  return result;
}

export function mountConvergence(app, { bindings, getEnv, allowedRequest = () => false, read }) {
  let active = 0;
  const route = kind => async (req, res) => {
    res.set('Cache-Control', 'no-store');
    if (!allowedRequest(req)) return res.status(403).json(fail('unauthorized'));
    const owner = cookieFrom(req);
    const authorize = () => {
      bindings.read(owner);
      const expected = req.headers['x-netclaw-installation'];
      if (expected && expected !== bindings.installation?.installationId) throw Error();
    };
    try { authorize(); } catch { return res.status(401).json(fail('unauthorized')); }
    if (kind === 'status') return res.json({ enabled: convergenceEnabled(getEnv()) });
    if (!convergenceEnabled(getEnv())) return res.status(409).json(fail('disabled'));
    let args;
    try { args = flowArguments(kind, req.query); } catch { return res.status(400).json(fail('invalid_argument')); }
    if (active >= 4) return res.status(503).json(fail());
    active++;
    try {
      const result = await read(kind, args);
      try { authorize(); } catch { return res.status(401).json(fail('unauthorized')); }
      if (!convergenceEnabled(getEnv())) return res.status(409).json(fail('disabled'));
      if (result?.ok !== true) {
        const code = Object.hasOwn(messages, result?.error?.code) ? result.error.code : 'unavailable';
        return res.status(statuses[code]).json(fail(code));
      }
      if (result.data?.site !== getEnv().CONVERGENCE_SITE) return res.status(502).json(fail('compatibility'));
      return res.json(result);
    } catch { return res.status(503).json(fail()); }
    finally { active--; }
  };
  app.get('/api/hud/convergence/status', route('status'));
  app.get('/api/hud/convergence/flows', route('summary'));
  app.get('/api/hud/convergence/flows/records', route('evidence'));
}
