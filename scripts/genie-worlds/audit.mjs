import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { need } from "./model.mjs";
const run = promisify(execFile);
const script = `import sys,json,os
sys.path.insert(0,os.environ['NETCLAW_GENIE_GAIT_MODULE_DIR'])
import gait_mcp as g
p=json.loads(sys.argv[1])
def call(name,**kw):
 f=getattr(g,name); r=(f.fn if hasattr(f,'fn') else f)(**kw)
 if not r.get('ok'): raise RuntimeError('audit_failed')
 return r
call('gait_status',path=p['root'])
r=call('gait_record_turn',user_text='Genie lifecycle',assistant_text=p['event'],note='Spec200 lifecycle')
print(json.dumps({'commit':r['commit']}))`;
export async function nativeAudit(root, event, env = process.env) {
  need(
    env.NETCLAW_GENIE_GAIT_PYTHON && env.NETCLAW_GENIE_GAIT_MODULE_DIR,
    "audit_unavailable",
  );
  const result = await run(
    env.NETCLAW_GENIE_GAIT_PYTHON,
    ["-c", script, JSON.stringify({ root, event: JSON.stringify(event) })],
    {
      env: {
        ...env,
        PYTHONDONTWRITEBYTECODE: "1",
        GAIT_MCP_STICKY_FILE: root + "/gait-root",
      },
      timeout: 10000,
      maxBuffer: 8192,
    },
  );
  return JSON.parse(result.stdout.trim());
}
