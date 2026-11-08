"""Owned loopback byte forwarders for REAL partition rows (spec 179, R08).

Stdlib only. Opaque TCP forwarding: no TLS termination, no certificates or keys,
no byte inspection. One process hosts every forwarder listed in an immutable
spec; a private control directory holds a monotone `policy.json` (written by this
module's `cut`/`heal`/`delay` commands) and the process writes `metrics.json`,
`events.jsonl`, `owner.json` and `final-metrics.json` there.

Names are `b<i>-v<k>`: Border i's own forwarder to etcd voter k. A Border reaches
the voters only through its own set, so cutting `b<i>-*` isolates Border i from the
etcd majority without touching the other Borders or the voters.

Directions: `request` is client->upstream (Border->voter), `response` is
upstream->client. Policy changes sever only the connections of forwarders whose
rule changed, so a dropped TLS byte stream can never survive a heal.

Commands (run with the reviewed immutable Python, from the frozen source):
  start --control DIR [--spec FILE]   spawn detached owner process (spec in DIR/spec.json)
  serve --control DIR                 foreground server (used by start)
  cut|heal|delay|status|wait-applied|stop --control DIR ...
"""
import argparse
import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

NAME = re.compile(r'[a-z][a-z0-9-]{0,31}')
MODES, DIRECTIONS = ('pass', 'block'), ('pass', 'drop')
SPEC_FIELDS = {'schema_version', 'owner', 'forwarders'}
POLICY_FIELDS = {'schema_version', 'generation', 'owner', 'rules'}
RULE_FIELDS = {'mode', 'request', 'response', 'delay_ms'}
MAX_FORWARDERS, MAX_CONNECTIONS, MAX_DELAY_MS = 32, 128, 2000
PASS = {'mode': 'pass', 'request': 'pass', 'response': 'pass', 'delay_ms': 0}


class ProxyRefused(ValueError):
    pass


def need(value, code):
    if not value:
        raise ProxyRefused(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def private_directory(path):
    path = Path(path).absolute()
    need(path == path.resolve(), 'private_path_required')
    info = path.lstat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077,
         'private_directory_required')
    return path


def read_private(path, maximum=65536):
    path = Path(path).absolute()
    need(path == path.resolve(), 'private_path_required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
             and info.st_size <= maximum, 'private_file_required')
        return stream.read(maximum + 1)


def write_new(path, value):
    path = Path(path).absolute(); private_directory(path.parent)
    raw = value if isinstance(value, bytes) else canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def replace_private(path, value):
    """Atomic publication that readers never see half-written (policy/metrics)."""
    path = Path(path).absolute(); private_directory(path.parent)
    temporary = path.with_name('.' + path.name + '.next')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def process_start(pid):
    """Kernel-reported start time; with the pid it identifies one process incarnation."""
    result = subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)], capture_output=True, text=True, timeout=5)
    return ' '.join(result.stdout.split()) if result.returncode == 0 else None


def validate_spec(value):
    need(isinstance(value, dict) and set(value) == SPEC_FIELDS and value['schema_version'] == 1
         and isinstance(value['owner'], str) and value['owner'].startswith('netclaw-r08-'), 'invalid_spec')
    rows = value['forwarders']
    need(isinstance(rows, list) and 1 <= len(rows) <= MAX_FORWARDERS, 'invalid_spec')
    names, ports = set(), set()
    for row in rows:
        need(isinstance(row, dict) and set(row) == {'name', 'listen_port', 'target_port'}
             and isinstance(row['name'], str) and NAME.fullmatch(row['name']), 'invalid_spec')
        for key in ('listen_port', 'target_port'):
            need(type(row[key]) is int and 1024 <= row[key] <= 65535, 'invalid_spec')
        need(row['name'] not in names and row['listen_port'] not in ports and row['listen_port'] != row['target_port'],
             'invalid_spec')
        names.add(row['name']); ports.add(row['listen_port'])
    # An owned listener must never also be another forwarder's upstream (no loops).
    need(not ports & {row['target_port'] for row in rows}, 'forwarder_loop_refused')
    return value


def validate_rule(rule):
    need(isinstance(rule, dict) and set(rule) == RULE_FIELDS and rule['mode'] in MODES
         and rule['request'] in DIRECTIONS and rule['response'] in DIRECTIONS
         and type(rule['delay_ms']) is int and 0 <= rule['delay_ms'] <= MAX_DELAY_MS, 'invalid_policy')
    return rule


def validate_policy(value, spec, floor=0):
    need(isinstance(value, dict) and set(value) == POLICY_FIELDS and value['schema_version'] == 1
         and type(value['generation']) is int and value['generation'] >= floor
         and value['owner'] == spec['owner'], 'invalid_policy')
    need(isinstance(value['rules'], dict) and set(value['rules']) == {r['name'] for r in spec['forwarders']}, 'invalid_policy')
    for rule in value['rules'].values(): validate_rule(rule)
    return value


class Forwarders:
    def __init__(self, control):
        self.control = private_directory(control)
        self.spec = validate_spec(json.loads(read_private(self.control / 'spec.json')))
        self.rules = {}
        self.generation, self.sha = 0, None
        self.counters = {r['name']: {'connections_accepted': 0, 'connections_refused': 0, 'connections_severed': 0,
            'connections_failed_upstream': 0,
            'request': {'received_bytes': 0, 'forwarded_bytes': 0, 'dropped_bytes': 0},
            'response': {'received_bytes': 0, 'forwarded_bytes': 0, 'dropped_bytes': 0}} for r in self.spec['forwarders']}
        self.tasks = {r['name']: set() for r in self.spec['forwarders']}
        self.servers, self.stopping = [], asyncio.Event()

    def policy(self):
        raw = read_private(self.control / 'policy.json')
        value = validate_policy(json.loads(raw), self.spec, self.generation)
        digest = hashlib.sha256(raw).hexdigest()
        if value['generation'] == self.generation and self.sha not in (None, digest):
            raise ProxyRefused('policy_generation_reused')
        return value, digest

    def apply(self):
        value, digest = self.policy()
        if value['generation'] == self.generation and self.sha == digest:
            return
        severed = {}
        for name, rule in value['rules'].items():
            if self.rules.get(name) != rule:
                # Only forwarders whose rule changed lose their relays; the others keep running.
                live = list(self.tasks[name]); severed[name] = len(live)
                self.counters[name]['connections_severed'] += len(live)
                for task in live: task.cancel()
        self.rules, self.generation, self.sha = value['rules'], value['generation'], digest
        self.event({'kind': 'policy_applied', 'generation': self.generation, 'policy_sha256': digest,
                    'rules': self.rules, 'severed': severed})

    def event(self, record):
        line = canonical({'at_ms': int(time.time() * 1000), **record}) + b'\n'
        fd = os.open(self.control / 'events.jsonl', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'ab') as stream:
            stream.write(line); stream.flush(); os.fsync(stream.fileno())

    async def copy(self, name, reader, writer, direction):
        counter = self.counters[name][direction]
        while data := await reader.read(16384):
            rule = self.rules[name]
            counter['received_bytes'] += len(data)
            if rule['delay_ms']: await asyncio.sleep(rule['delay_ms'] / 1000)
            rule = self.rules[name]
            if rule['mode'] == 'block' or rule[direction] == 'drop':
                counter['dropped_bytes'] += len(data)
            else:
                writer.write(data); await writer.drain(); counter['forwarded_bytes'] += len(data)

    async def relay(self, name, target_port, reader, writer):
        task, upstream, copies = asyncio.current_task(), None, []
        count = self.counters[name]
        if sum(len(t) for t in self.tasks.values()) >= MAX_CONNECTIONS:
            count['connections_refused'] += 1; writer.close(); return
        self.tasks[name].add(task)
        try:
            if self.rules[name]['mode'] == 'block':
                count['connections_refused'] += 1; return
            count['connections_accepted'] += 1
            try:
                upstream_reader, upstream = await asyncio.wait_for(asyncio.open_connection('127.0.0.1', target_port), 3)
            except (OSError, asyncio.TimeoutError):
                count['connections_failed_upstream'] += 1; return
            copies = [asyncio.create_task(self.copy(name, reader, upstream, 'request')),
                      asyncio.create_task(self.copy(name, upstream_reader, writer, 'response'))]
            await asyncio.wait(copies, return_when=asyncio.FIRST_COMPLETED)
        except (OSError, asyncio.CancelledError):
            pass
        finally:
            for copy in copies: copy.cancel()
            if copies: await asyncio.gather(*copies, return_exceptions=True)
            for stream in (writer, upstream):
                if stream:
                    stream.close()
                    try: await stream.wait_closed()
                    except (OSError, asyncio.CancelledError): pass
            self.tasks[name].discard(task)

    def snapshot(self):
        return {'schema_version': 1, 'owner': self.spec['owner'], 'pid': os.getpid(),
                'policy_generation': self.generation, 'policy_sha256': self.sha,
                'observed_at_ms': int(time.time() * 1000), 'rules': self.rules,
                'active_connections': {n: len(t) for n, t in self.tasks.items()},
                'forwarders': self.counters}

    async def run(self):
        self.apply()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT): loop.add_signal_handler(sig, self.stopping.set)
        for row in self.spec['forwarders']:
            handler = (lambda n, t: lambda r, w: self.relay(n, t, r, w))(row['name'], row['target_port'])
            self.servers.append(await asyncio.start_server(handler, '127.0.0.1', row['listen_port']))
        record = {'schema_version': 1, 'owner': self.spec['owner'], 'pid': os.getpid(), 'start': process_start(os.getpid()),
                  'argv': sys.argv, 'control': str(self.control), 'spec_sha256': hashlib.sha256(canonical(self.spec)).hexdigest(),
                  'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'listen_ports': [r['listen_port'] for r in self.spec['forwarders']], 'started_at_ms': int(time.time() * 1000)}
        write_new(self.control / 'owner.json', record)
        try:
            while not self.stopping.is_set():
                self.apply()
                replace_private(self.control / 'metrics.json', self.snapshot())
                try: await asyncio.wait_for(self.stopping.wait(), .05)
                except asyncio.TimeoutError: pass
        finally:
            for server in self.servers: server.close()
            live = [t for tasks in self.tasks.values() for t in tasks]
            for task in live: task.cancel()
            await asyncio.gather(*live, return_exceptions=True)
            write_new(self.control / 'final-metrics.json', self.snapshot())


# ---------------------------------------------------------------- controller side

def load_spec(control):
    return validate_spec(json.loads(read_private(Path(control) / 'spec.json')))


def init_control(control, spec):
    """Create a fresh control directory with spec and an all-pass generation-1 policy."""
    spec = validate_spec(spec)
    control = Path(control).absolute()
    control.mkdir(mode=0o700, exist_ok=False)
    write_new(control / 'spec.json', spec)
    write_new(control / 'policy.json', {'schema_version': 1, 'generation': 1, 'owner': spec['owner'],
                                        'rules': {r['name']: dict(PASS) for r in spec['forwarders']}})
    return control


def select(spec, *, forwarders=(), border=None, voter=None, all_=False):
    names = [r['name'] for r in spec['forwarders']]
    chosen = set(forwarders)
    need(chosen <= set(names), 'unknown_forwarder')
    for name in names:
        match = re.fullmatch(r'b(\d+)-v(\d+)', name)
        if all_ or (match and (border is not None or voter is not None)
                    and (border is None or int(match[1]) == border) and (voter is None or int(match[2]) == voter)):
            chosen.add(name)
    need(chosen, 'empty_selection')
    return sorted(chosen)


def update(control, names, **changes):
    """Locked read-modify-write of policy.json with generation+1; returns the new policy."""
    control = private_directory(control); spec = load_spec(control)
    fd = os.open(control / '.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        value = validate_policy(json.loads(read_private(control / 'policy.json')), spec)
        for name in names: value['rules'][name] = validate_rule({**value['rules'][name], **changes})
        value['generation'] += 1
        validate_policy(value, spec)
        replace_private(control / 'policy.json', value)
    return value


def cut(control, names, direction='both'):
    need(direction in ('both', 'request', 'response'), 'invalid_direction')
    if direction == 'both': return update(control, names, mode='block', request='drop', response='drop')
    # One-way cut keeps the TCP path open and blackholes only the chosen direction.
    return update(control, names, mode='pass', request='drop' if direction == 'request' else 'pass',
                  response='drop' if direction == 'response' else 'pass')


def heal(control, names):
    return update(control, names, **PASS)


def delay(control, names, milliseconds):
    return update(control, names, delay_ms=milliseconds)


def status(control):
    return json.loads(read_private(Path(control) / 'metrics.json', 1024 * 1024))


def wait_applied(control, generation, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            metrics = status(control)
            if metrics['policy_generation'] >= generation:
                return metrics
        except (OSError, ValueError, ProxyRefused): pass
        time.sleep(.02)
    raise ProxyRefused('policy_not_applied')


def start(control, python=None):
    control = private_directory(control)
    need(not (control / 'owner.json').exists(), 'proxy_already_started')
    log = control / 'proxy.log'
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    argv = [python or sys.executable, '-I', '-B', str(Path(__file__).resolve()), 'serve', '--control', str(control)]
    with os.fdopen(fd, 'wb') as stream:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, start_new_session=True,
                                   env={'PATH': '/usr/bin:/bin'})
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if (control / 'owner.json').exists() and (control / 'metrics.json').exists():
            return {'started': True, 'pid': process.pid}
        if process.poll() is not None: break
        time.sleep(.05)
    raise ProxyRefused('proxy_start_unknown')


def stop(control):
    """Stop only the recorded process incarnation (pid + start time + argv control path)."""
    control = private_directory(control)
    record = json.loads(read_private(control / 'owner.json'))
    need(not (control / 'stopped.json').exists(), 'proxy_already_stopped')
    pid = record['pid']
    need(process_start(pid) == record['start'], 'owned_process_changed')
    command = subprocess.run(['ps', '-o', 'command=', '-p', str(pid)], capture_output=True, text=True, timeout=5).stdout
    need(str(control) in command and 'real_proxies.py' in command, 'owned_process_changed')
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and process_start(pid) == record['start']: time.sleep(.05)
    need(process_start(pid) != record['start'], 'owned_process_stop_unknown')
    write_new(control / 'stopped.json', {'schema_version': 1, 'pid': pid, 'owner': record['owner'],
                                         'stopped_at_ms': int(time.time() * 1000)})
    return {'stopped': True, 'pid': pid}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('start', 'serve', 'cut', 'heal', 'delay', 'status', 'wait-applied', 'stop'):
        sub = commands.add_parser(name); sub.add_argument('--control', required=True)
        if name in ('cut', 'heal', 'delay'):
            sub.add_argument('--forwarder', action='append', default=[]); sub.add_argument('--border', type=int)
            sub.add_argument('--voter', type=int); sub.add_argument('--all', action='store_true')
        if name == 'cut': sub.add_argument('--direction', choices=('both', 'request', 'response'), default='both')
        if name == 'delay': sub.add_argument('--ms', type=int, required=True)
        if name == 'wait-applied': sub.add_argument('--generation', type=int, required=True)
        if name == 'start': sub.add_argument('--python')
    args = parser.parse_args(argv)
    if args.command == 'serve':
        asyncio.run(Forwarders(args.control).run()); return
    if args.command == 'start': result = start(args.control, args.python)
    elif args.command == 'stop': result = stop(args.control)
    elif args.command == 'status': result = status(args.control)
    elif args.command == 'wait-applied': result = wait_applied(args.control, args.generation)
    else:
        names = select(load_spec(args.control), forwarders=args.forwarder, border=args.border, voter=args.voter, all_=args.all)
        policy = (cut(args.control, names, args.direction) if args.command == 'cut' else
                  heal(args.control, names) if args.command == 'heal' else delay(args.control, names, args.ms))
        result = {'generation': policy['generation'], 'forwarders': names}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        print('real_proxies: failed_or_unknown; retain control directory evidence', file=sys.stderr)
        raise SystemExit(1)
