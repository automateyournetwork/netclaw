"""Probe synthetic discovery servers in an isolated OpenClaw state directory.

No provider calls, actual device tools, package installation or daemon operations.
Pass explicit installed Node/CLI paths; this does not update the runtime.
"""
import argparse
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node', type=Path, required=True)
parser.add_argument('--cli', type=Path, required=True)
parser.add_argument('--runtime-label', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
node, cli = args.node.resolve(), args.cli.resolve()
fixture = '''import json,sys
def answer(m):
    method=m.get('method')
    if method=='initialize': return {'protocolVersion':m.get('params',{}).get('protocolVersion','2025-03-26'),'capabilities':{'tools':{}},'serverInfo':{'name':'netclaw-fixture','version':'1.0.0'}}
    if method=='tools/list': return {'tools':[{'name':'fixture_ping','description':'Synthetic local fixture; no network operations','inputSchema':{'type':'object','properties':{}}}]}
    if method=='resources/list': return {'resources':[]}
    if method=='resources/templates/list': return {'resourceTemplates':[]}
    if method=='prompts/list': return {'prompts':[]}
    return {}
if __name__=='__main__':
    for line in sys.stdin:
        m=json.loads(line)
        with open(sys.argv[1],'a') as log: log.write(m.get('method','unknown')+'\\n')
        if 'id' in m: print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':answer(m)}),flush=True)
'''
namespace = {'__name__': 'fixture_module'}
exec(fixture, namespace)
answer = namespace['answer']
events = []

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def do_GET(self):
        events.append({'verb': 'GET', 'method': None})
        self.send_response(405); self.send_header('Content-Length', '0'); self.end_headers()
    def do_POST(self):
        m = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        events.append({'verb': 'POST', 'method': m.get('method')})
        body = json.dumps({'jsonrpc': '2.0', 'id': m.get('id'), 'result': answer(m)}).encode() if 'id' in m else b''
        self.send_response(200 if body else 202)
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers()
        self.wfile.write(body)

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
results = {'runtime': args.runtime_label, 'node': subprocess.check_output([str(node), '--version'], text=True).strip(), 'fixture_only': True, 'cases': []}
try:
    with tempfile.TemporaryDirectory(prefix='netclaw147-probe-') as directory:
        base = Path(directory)
        script = base / 'fixture.py'; script.write_text(fixture)
        for name, entry in [
            ('stdio', {'command': sys.executable, 'args': ['-u', str(script), str(base/'stdio-methods')]}),
            ('http-explicit', {'url': f'http://127.0.0.1:{server.server_port}/mcp', 'transport': 'streamable-http'}),
            ('http-url-only', {'url': f'http://127.0.0.1:{server.server_port}/mcp'}),
        ]:
            state = base / name; state.mkdir()
            entry.update({'connectionTimeoutMs': 5000, 'requestTimeoutMs': 5000})
            config = state / 'openclaw.json'; config.write_text(json.dumps({'mcp': {'servers': {'fixture': entry}}}))
            env = {'HOME': str(base), 'PATH': str(node.parent) + os.pathsep + '/usr/bin:/bin',
                   'OPENCLAW_STATE_DIR': str(state), 'OPENCLAW_CONFIG_PATH': str(config), 'NO_COLOR': '1'}
            events.clear()
            try:
                result = subprocess.run([str(node), str(cli), 'mcp', 'probe', 'fixture', '--json'],
                    env=env, cwd=base, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=25)
                case = {'name': name, 'returncode': result.returncode, 'fixture_tool_discovered': 'fixture_ping' in result.stdout,
                        'http_methods': list(events)}
                if name == 'stdio':
                    log = base / 'stdio-methods'
                    case['stdio_methods'] = log.read_text().splitlines() if log.exists() else []
                if result.returncode:
                    # Fixture environment only; show bounded diagnostics to investigate failures.
                    print(name, (result.stdout + result.stderr)[-1800:], file=sys.stderr)
            except subprocess.TimeoutExpired:
                case = {'name': name, 'timed_out': True, 'http_methods': list(events)}
            results['cases'].append(case)
finally:
    server.shutdown(); server.server_close()
print(json.dumps(results, indent=2))
args.output.write_text(json.dumps(results, indent=2)+'\n')
