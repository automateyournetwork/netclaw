#!/usr/bin/env python3
"""Explicit endpoint registry and selected transport lifecycle (R01).

No reservation/account mutation is implemented. Start/run are explicit operator
actions and can activate already-reserved public endpoints; never run as probes.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'mcp-servers/protocol-mcp'))
from bgp.federation.runtime import selected, read_private, write_private, private_dir
from bgp.federation.endpoint_registry import Registry, validate, configured, export_bundle, import_bundle, transport_kind, _atomic, _unique


def environment(runtime):
    spec = importlib.util.spec_from_file_location('_ngrok_literal_env', ROOT/'scripts/write-env.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    env = {key: os.environ[key] for key in ('PATH','HOME','LANG','LC_ALL','TMPDIR','SYSTEMROOT') if key in os.environ}
    for file in (runtime.env_file, runtime.home/'mesh.systemd.env'):
        try:
            fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            continue
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077 or info.st_size > 512 * 1024):
                raise ValueError('selected ngrok environment must be private and owned')
            values = module.values(stream.read())
        env.update({key:value for key,value in values.items()
                    if key in ('NGROK_AUTHTOKEN','N2N_ENDPOINT_REGISTRY','N2N_ROLE')})
    return runtime.environment(env)


def address(host, port):
    return f'[{host}]:{port}' if ':' in host else f'{host}:{port}'


def render_config(value):
    validate(value, value.get('installationId'))
    entries = [entry for entry in value['entries'] if entry['direction'] == 'listen']
    if (len(entries) != 2 or {e['service'] for e in entries} != {'in2n','en2n'}
            or any(transport_kind(e) != 'ngrok_tcp' for e in entries)):
        raise ValueError('ngrok requires separate iN2N and eN2N Border registrations')
    return {'version':'3', 'agent':{'web_addr':False, 'console_ui':False,
                                  'remote_management':False, 'update_check':False,
                                  'log':'stdout', 'log_format':'json', 'log_level':'warn'},
            'endpoints':[{'name':entry['id'],
                          'url':'tcp://' + address(entry['routing_host'], entry['routing_port']),
                          # ngrok 3.36.1 rejects tcp:// upstream origins even
                          # though current docs describe them. Bare host:port
                          # retains byte forwarding for a tcp:// endpoint.
                          'upstream':{'url':address(entry['bind_host'], entry['bind_port'])}}
                         for entry in entries]}


def _process(pid):
    if type(pid) is not int or pid <= 1:
        return None
    state = subprocess.run(['ps','-p',str(pid),'-o','stat='], capture_output=True, text=True).stdout.strip()
    if not state or state.startswith('Z'):
        return None
    started = subprocess.run(['ps','-p',str(pid),'-o','lstart='], capture_output=True, text=True).stdout.strip()
    # Linux ps otherwise truncates argv to the display width, hiding the owned
    # config path. Both macOS and Linux accept -ww for unlimited output width.
    command = subprocess.run(['ps','-ww','-p',str(pid),'-o','command='], capture_output=True, text=True).stdout.strip()
    return {'started':started, 'command':command}


class Controller:
    def __init__(self, runtime, *, binary=None):
        self.runtime = runtime
        self.binary = str(Path(binary or shutil.which('ngrok') or '/nonexistent/ngrok').absolute())
        self.base = runtime.state/'ngrok'
        self.record = self.base/'process.json'
        self.config = self.base/'agent.json'
        self.process = None

    @contextmanager
    def lock(self):
        self.runtime.fence()
        private_dir(self.base)
        fd = os.open(self.base/'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('invalid ngrok control ownership')
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _audit(self, action, outcome):
        # Bounded local durable lifecycle receipt; never log argv/environment.
        value = {'at':datetime.now(timezone.utc).isoformat(), 'installationId':self.runtime.installation,
                 'action':action, 'outcome':outcome}
        target = self.base/'lifecycle.jsonl'
        fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('invalid ngrok audit ownership')
            stream.write(json.dumps(value)+'\n'); stream.flush(); os.fsync(stream.fileno())

    def registry(self):
        registry = configured(environment(self.runtime), self.runtime)
        if registry is None:
            raise ValueError('select an owned N2N_ENDPOINT_REGISTRY; ephemeral ngrok start is unsupported')
        return registry

    def configuration(self):
        return render_config(self.registry().load())

    def verify_border_ready(self):
        """Do not forward a reserved endpoint to an unowned/stale local port."""
        spec = importlib.util.spec_from_file_location('_ngrok_federation_control', ROOT/'scripts/federation-control.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        status = module.status(self.runtime)
        owner = read_private(self.runtime.state/'daemon.json')
        process = _process(owner.get('pid'))
        if (owner.get('installationId') != self.runtime.installation or status.get('pid') != owner.get('pid')
                or not process or process['started'] != owner.get('started')
                or str(ROOT/'mcp-servers/protocol-mcp/bgp-daemon-v2.py') not in shlex.split(process['command'])):
            raise ValueError('selected Border daemon process ownership is not verified')
        with urllib.request.urlopen(module.api_url(self.runtime)+'/n2n/status', timeout=2) as response:
            raw = response.read(65537)
        if len(raw) > 65536: raise ValueError('Border status exceeds bound')
        projection = json.loads(raw).get('endpoint_registry') or {}
        registry = self.registry().load()
        expected = {e['id'] for e in registry['entries'] if e['direction'] == 'listen'}
        ready = {e['id'] for e in projection.get('services', []) if e.get('listener_ready') is True}
        if (projection.get('installationId') != self.runtime.installation
                or projection.get('revision') != registry['revision'] or expected != ready):
            raise ValueError('selected Border strict listeners are not ready for this registry')

    def status(self):
        self.runtime.fence()
        try: record = read_private(self.record)
        except FileNotFoundError:
            return {'state':'stopped', 'installationId':self.runtime.installation}
        if record.get('installationId') != self.runtime.installation:
            raise ValueError('foreign ngrok process record')
        observed = _process(record.get('pid'))
        if not observed:
            return {'state':'stopped', 'installationId':self.runtime.installation}
        args = shlex.split(observed['command'])
        if (observed['started'] != record.get('started') or record.get('binary') not in args
                or str(self.config) not in args or record.get('config') != str(self.config)):
            raise ValueError('ngrok PID ownership changed; refusing to adopt or signal')
        return {'state':'running-owned', 'installationId':self.runtime.installation,
                'pid':record['pid'], 'configDigest':record['configDigest'],
                'tcp_reachable':None, 'authenticated':False}

    def start(self):
        with self.lock():
            current = self.status()
            if current['state'] == 'running-owned':
                return current
            env = environment(self.runtime)
            if env.get('N2N_ROLE') != 'border':
                raise ValueError('only an explicitly configured Border may run ngrok')
            if not env.get('NGROK_AUTHTOKEN'):
                raise ValueError('selected private environment requires NGROK_AUTHTOKEN')
            config = self.configuration()
            self.verify_border_ready()
            data = json.dumps(config, indent=2).encode()
            _atomic(self.config, data)
            # Raw agent output is intentionally discarded: the agent is not an
            # application audit source and may emit account-specific diagnostics.
            self._audit('start', 'requested')
            process = subprocess.Popen([self.binary,'start',*[e['name'] for e in config['endpoints']],
                                        '--config',str(self.config)], env=env, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       start_new_session=True)
            self.process = process
            try:
                observed = _process(process.pid)
                if not observed or process.poll() is not None:
                    raise RuntimeError('owned ngrok process failed to start')
                write_private(self.record, {'installationId':self.runtime.installation,
                                            'pid':process.pid, 'started':observed['started'],
                                            'binary':self.binary, 'config':str(self.config),
                                            'configDigest':hashlib.sha256(data).hexdigest()})
                time.sleep(.1)
                if process.poll() is not None:
                    raise RuntimeError('owned ngrok exited; endpoints are not qualified')
                self._audit('start', 'process-running-unqualified')
                return self.status()
            except BaseException:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)
                raise

    def stop(self):
        with self.lock():
            current = self.status()
            if current['state'] == 'stopped':
                return current
            self._audit('stop', 'requested')
            os.kill(current['pid'], signal.SIGTERM)
            for _ in range(50):
                if self.process and self.process.pid == current['pid']:
                    self.process.poll()
                if not _process(current['pid']):
                    self._audit('stop', 'stopped')
                    return self.status()
                time.sleep(.1)
            raise RuntimeError('owned ngrok did not stop within 5s; no other process signalled')

    def unit(self):
        # Render only; installing/enabling a unit is an explicit operator step.
        fields = {'NETCLAW_RUNTIME':self.runtime.kind,
                  'HERMES_HOME' if self.runtime.kind == 'hermes' else 'OPENCLAW_HOME':str(self.runtime.home)}
        def quoted(value):
            if any(c in value for c in '\n\r\x00'):
                raise ValueError('invalid service path')
            return '"' + value.replace('\\','\\\\').replace('"','\\"').replace('%','%%') + '"'
        return ('[Unit]\nDescription=NetClaw owned ngrok '+self.runtime.installation+'\nAfter=network-online.target\n'
                '[Service]\nType=simple\nUMask=0077\nRestart=on-failure\nRestartSec=5\n'
                + ''.join('Environment='+quoted(k+'='+v)+'\n' for k,v in fields.items())
                + 'ExecStart='+quoted(sys.executable)+' '+quoted(str(Path(__file__).resolve()))+' run\n'
                + 'NoNewPrivileges=true\n[Install]\nWantedBy=default.target\n')

    def run(self):
        self.start()
        if self.process is None:
            raise RuntimeError('another owner already runs this agent; refusing service adoption')
        def stop(signum, frame):
            self.process.terminate()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        code = self.process.wait()
        with self.lock(): self._audit('run', 'exited')
        return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status','validate','render','unit','start','stop','run',
                                         'register','export','import','address','recover','endpoint'))
    parser.add_argument('--file')
    parser.add_argument('--id')
    parser.add_argument('--host')
    parser.add_argument('--port', type=int)
    parser.add_argument('--reservation-id')
    parser.add_argument('--address-ref')
    parser.add_argument('--expected-revision', type=int)
    args = parser.parse_args()
    runtime = selected()
    control = Controller(runtime)
    env = environment(runtime)
    if args.action in ('start','stop','status','run','unit') and env.get('N2N_ENDPOINT_REGISTRY'):
        entries = [e for e in control.registry().load()['entries'] if e['direction'] == 'listen']
        kinds = {transport_kind(e) for e in entries}
        if 'direct_tcp' in kinds:
            if kinds != {'direct_tcp'} or len(entries) != 2 or {e['service'] for e in entries} != {'in2n','en2n'}:
                raise ValueError('direct lifecycle requires two direct Border service registrations; mixed transports refused')
            if env.get('N2N_ROLE') != 'border':
                raise ValueError('direct lifecycle requires an explicitly configured Border')
            if args.action == 'unit':
                raise ValueError('unit renders ngrok only; supervise direct transport with the owned federation daemon')
            env.pop('NGROK_AUTHTOKEN', None)
            os.execve(sys.executable, [sys.executable, str(ROOT/'scripts/federation-control.py'), args.action], env)
    if args.action in ('start','stop','status','run'):
        result = getattr(control, args.action)()
        if args.action == 'run': return result
    elif args.action == 'unit':
        print(control.unit()); return 0
    else:
        env = environment(runtime)
        path = env.get('N2N_ENDPOINT_REGISTRY')
        if not path or not Path(path).is_absolute():
            raise ValueError('set an absolute N2N_ENDPOINT_REGISTRY in the selected private environment')
        runtime.fence()
        registry = Registry(path, runtime.installation)
        if args.action in ('register','import'):
            if not args.file: raise ValueError('--file required')
            with open(args.file, 'rb') as stream: raw = stream.read(65537)
            if len(raw) > 65536: raise ValueError('input exceeds 64 KiB')
            value = json.loads(raw, object_pairs_hook=_unique)
            if args.action == 'register': registry.replace(value, expected_revision=args.expected_revision)
            else:
                sys.path.insert(0, str(ROOT/'scripts/lib'))
                from setup_enrollment import materialize_remote_transport
                materialize_remote_transport(runtime, value, registry.path,
                                             expected_revision=args.expected_revision)
            result = registry.status()
        elif args.action == 'address':
            schema = registry.load()['schemaVersion']
            if (schema == 2 and (not args.address_ref or args.reservation_id is not None)
                    or schema == 1 and (not args.reservation_id or args.address_ref is not None)):
                raise ValueError('schema2 address updates require --address-ref; schema1 requires --reservation-id')
            registry.update_address(args.id, args.host, args.port, args.address_ref if schema == 2 else args.reservation_id,
                                    expected_revision=args.expected_revision)
            result = registry.status()
        elif args.action == 'recover':
            registry.recover(expected_revision=args.expected_revision)
            result = registry.status()
        elif args.action == 'export':
            result = export_bundle(registry.entry(args.id))
        elif args.action == 'render':
            result = render_config(registry.load())
        elif args.action == 'endpoint':
            entries = [e for e in registry.load()['entries'] if e['service'] == 'en2n' and e['direction'] == 'listen']
            if len(entries) != 1: raise ValueError('one external Border registration required')
            print(address(entries[0]['routing_host'], entries[0]['routing_port'])); return 0
        else: result = registry.status()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as error: sys.exit(str(error))
