#!/usr/bin/env python3
"""Keep NetClaw STDIO clients compatible with the HTTP-only pyATS MCP.

The owned upstream process runs authenticated HTTP on a random loopback port.
Default lifetime follows STDIO. An explicitly started foreground session can
retain inventory across client turns; no automatic daemon or restart is used.
"""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote
import re
import tempfile
import secrets
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent/'lib'))
from pyats_session import binding, publish, read as read_session

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('MCP redirects refused')


def forward(url, message, timeout, token=None):
    params = message.get('params') or {}
    meta = params.get('_meta') or {}
    protocol = meta.get('io.modelcontextprotocol/protocolVersion', '2025-06-18')
    if not isinstance(protocol, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', protocol):
        raise ValueError('Invalid MCP protocol version')
    method = message.get('method', '')
    if not isinstance(method, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', method):
        raise ValueError('Invalid MCP method')
    headers = {
        'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
        'MCP-Protocol-Version': protocol, 'MCP-Method': method,
    }
    if token:
        headers['Authorization'] = 'Bearer ' + token
    name = params.get('taskId') if method.startswith('tasks/') else params.get('name')
    if name is not None:
        if not isinstance(name, str):
            raise ValueError('Invalid MCP routing name')
        headers['MCP-Name'] = quote(name, safe='')
    request = urllib.request.Request(url, data=json.dumps(message).encode(), headers=headers)
    # Ignore proxy environment variables: private RPC must never go to a proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        if not 200 <= response.status < 300:
            raise ValueError('MCP HTTP request refused')
        raw = response.read(32 * 1024 * 1024 + 1)
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError('MCP response exceeds 32 MiB')
        if not raw:
            if 'id' in message:
                raise ValueError('Empty response to MCP request')
            return None
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError('Invalid MCP response')
        return result


def stop_process(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    if proc.poll() is None:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve-session', type=Path, help='Run a foreground, authenticated session; publish a new private descriptor')
    parser.add_argument('--session-seconds', type=int, default=14400, help='Foreground session lifetime, at most 8 hours')
    args = parser.parse_args()
    if not 60 <= args.session_seconds <= 28800:
        raise ValueError('Session lifetime must be 60 to 28800 seconds')
    python = Path(os.environ.get('PYATS_VENV', str(Path.home()/'.openclaw/pyats-venv'))) / 'bin/python'
    managed = python.parent.parent/'upstream/pyats_mcp_server.py'
    fallback = managed if managed.is_file() else ROOT/'mcp-servers/pyATS_MCP/pyats_mcp_server.py'
    script = Path(os.environ.get('PYATS_UPSTREAM_SCRIPT', str(fallback)))
    if not python.is_file() or not script.is_file():
        print('pyATS HTTP runtime missing. Run scripts/install.sh --add pyats.', file=sys.stderr)
        return 1
    timeout = float(os.environ.get('MCP_CALL_TIMEOUT', '120'))
    if not 0 < timeout <= 3600:
        raise ValueError('MCP_CALL_TIMEOUT must be between 0 and 3600 seconds')
    descriptor = os.environ.get('PYATS_SESSION_FILE')
    if descriptor and not args.serve_session:
        session = read_session(Path(descriptor), binding(os.environ, python, script))
        relay(f"http://127.0.0.1:{session['port']}/mcp", timeout, session['token'],
              lambda: read_session(Path(descriptor), binding(os.environ, python, script)))
        return 0
    session_binding = binding(os.environ, python, script) if args.serve_session else None
    if args.serve_session and args.serve_session.exists():
        raise ValueError('Session descriptor already exists; use a new path')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, PYATS_MCP_HTTP_HOST='127.0.0.1', PYATS_MCP_HTTP_PORT=str(port),
               PYATS_MCP_TRANSPORT_MODE='stateless',PYTHON_DOTENV_DISABLED='1')
    token = secrets.token_hex(32)
    env['NETCLAW_PYATS_HTTP_TOKEN'] = token
    if env.get('NETCLAW_TESTBED_MODE')=='dynamic':
        env.pop('PYATS_TESTBED_PATH',None);env['PYATS_MCP_DYNAMIC_ONLY']='1'
    # Upstream's task store is exclusive. Each owned process gets private
    # artifacts/evidence; clients never share an active inventory or task DB.
    artifacts=Path(env.get('PYATS_MCP_ARTIFACTS_DIR',str(python.parent.parent.parent/'pyats-artifacts')))
    artifacts.mkdir(parents=True,exist_ok=True,mode=0o700)
    session=Path(tempfile.mkdtemp(prefix='session-',dir=artifacts))
    env['PYATS_MCP_ARTIFACTS_DIR']=str(session);env['PYATS_MCP_TASK_DB']=str(session/'tasks.sqlite3')
    # Upstream/Unicon can log complete commands, configs and authentication
    # diagnostics. Keep the entire child stream private, including on failure.
    log_fd=os.open(session/'upstream.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(log_fd,'wb') as private_log:
        proc = subprocess.Popen([str(python), '-u', str(ROOT/'scripts/pyats-managed.py'),'--upstream',str(script)], env=env,
                                stdin=subprocess.DEVNULL, stdout=private_log, stderr=private_log, start_new_session=True)
    def interrupted(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        deadline = time.monotonic() + 45
        while True:
            if proc.poll() is not None:
                raise RuntimeError('pyATS HTTP server exited during startup')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('pyATS HTTP server startup timed out')
                time.sleep(.05)
        url = f'http://127.0.0.1:{port}/mcp'
        if args.serve_session:
            expires = time.time() + args.session_seconds
            publish(args.serve_session, {'schema': 1, 'pid': proc.pid, 'port': port,
                                        'token': token, 'binding': session_binding, 'expires': expires})
            print('Managed pyATS session ready. Keep this foreground owner running; stop with Ctrl-C.', flush=True)
            while time.time() < expires:
                if proc.poll() is not None:
                    raise RuntimeError('Managed session exited; no automatic restart')
                time.sleep(.25)
        else:
            relay(url, timeout, token)
    finally:
        stop_process(proc)
    return 0


def relay(url, timeout, token, check=None):
    for line in sys.stdin:
        message = None
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError('MCP message must be an object')
            if check:
                check()  # Recheck expiry, ownership and live process every call.
            result = forward(url, message, timeout, token)
            if result is not None:
                print(json.dumps(result), flush=True)
        except Exception as error:
            # Never echo request arguments (may contain credentials/config).
            result = {'jsonrpc': '2.0', 'id': message.get('id') if isinstance(message, dict) else None,
                      'error': {'code': -32603, 'message': f'pyATS HTTP bridge: {type(error).__name__}'}}
            print(json.dumps(result), flush=True)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'pyATS HTTP bridge stopped: {type(error).__name__}', file=sys.stderr)
        raise SystemExit(1)
