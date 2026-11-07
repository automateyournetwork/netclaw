"""Owned, bounded fixture byte faults and row evidence; no TLS termination.

These proxies alter actual TCP byte paths below NCFED/HTTPS authentication. They
are explicit application/quorum path faults, not evidence of a Raft peer cut.
"""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import time

from .etcd_lab import private

ROWS = ('minority', 'asymmetric-request', 'asymmetric-response', 'threeway', 'delay-300ms',
        'stale-member', 'clock-forward', 'clock-backward', 'clock-suspend', 'unknown-commit',
        'lost-result', 'lost-ack', 'record-capacity', 'nospace', 'full-restart',
        'retired-return', 'fenced-restore')


def fault_plan():
    return {'schema_version': 1, 'class': 'FIXTURE',
            'network_scope': 'border-quorum-and-ncfed-byte-paths',
            'raft_peer_partition_qualified': False, 'rows': list(ROWS),
            'bounds': {'deadline_s': 90, 'direction_delay_ms': 150, 'max_proxy_connections': 32,
                       'chunk_bytes': 16384, 'maximum_callbacks': 64},
            'required_separate_rows': ['leader-loss-each-node', 'quorum-loss-two-voters',
                                       'topology-trust', 'real-profile-counters', 'hud', 'vscode', 'mobile']}


def validate_plan(plan):
    if plan != fault_plan():
        raise ValueError('fixture_plan_changed')
    return plan


class ByteProxy:
    def __init__(self, name, target_host, target_port, *, bind_host='127.0.0.1', bind_port=0):
        if not isinstance(name, str) or not name or len(name) > 120:
            raise ValueError('invalid_proxy_name')
        if not isinstance(target_host, str) or type(target_port) is not int or not 1 <= target_port <= 65535:
            raise ValueError('invalid_proxy_target')
        self.name, self.target_host, self.target_port = name, target_host, target_port
        self.bind_host, self.bind_port = bind_host, bind_port
        self.server, self.tasks, self.writers = None, set(), set()
        self.generation = 0
        self.directions = {direction: {'mode': 'pass', 'delay_ms': 0, 'received_bytes': 0,
            'forwarded_bytes': 0, 'dropped_bytes': 0} for direction in ('request', 'response')}
        self.connections, self.connection_errors = 0, 0

    @property
    def port(self):
        if self.server is None:
            raise ValueError('proxy_not_started')
        return self.server.sockets[0].getsockname()[1]

    async def start(self):
        if self.server is not None:
            raise ValueError('proxy_already_started')
        self.server = await asyncio.start_server(self._accept, self.bind_host, self.bind_port)
        return self

    def policy(self, *, request='pass', response='pass', delay_ms=0):
        if request not in ('pass', 'drop') or response not in ('pass', 'drop'):
            raise ValueError('invalid_proxy_policy')
        if type(delay_ms) is not int or not 0 <= delay_ms <= 300:
            raise ValueError('invalid_proxy_delay')
        self.generation += 1
        for direction, mode in (('request', request), ('response', response)):
            self.directions[direction].update(mode=mode, delay_ms=delay_ms)

    async def _copy(self, reader, writer, direction):
        while raw := await reader.read(16384):
            counter = self.directions[direction]
            counter['received_bytes'] += len(raw)
            if counter['delay_ms']:
                await asyncio.sleep(counter['delay_ms'] / 1000)
            # Re-read the live mode after delay: a fault change cannot release a
            # previously buffered packet into a newly isolated path.
            if counter['mode'] == 'drop':
                counter['dropped_bytes'] += len(raw)
                continue
            writer.write(raw); await writer.drain()
            counter['forwarded_bytes'] += len(raw)

    async def _accept(self, reader, writer):
        task = asyncio.current_task()
        if len(self.tasks) >= 32:
            writer.close(); await writer.wait_closed(); return
        self.tasks.add(task); self.writers.add(writer); self.connections += 1
        upstream = None
        copies = []
        try:
            upstream_reader, upstream = await asyncio.wait_for(
                asyncio.open_connection(self.target_host, self.target_port), 3)
            self.writers.add(upstream)
            copies = [asyncio.create_task(self._copy(reader, upstream, 'request')),
                      asyncio.create_task(self._copy(upstream_reader, writer, 'response'))]
            await asyncio.wait(copies, return_when=asyncio.FIRST_COMPLETED)
        except (OSError, asyncio.TimeoutError):
            self.connection_errors += 1
        finally:
            for child in copies:
                child.cancel()
            if copies:
                await asyncio.gather(*copies, return_exceptions=True)
            for stream in (writer, upstream):
                if stream:
                    self.writers.discard(stream); stream.close()
                    try: await stream.wait_closed()
                    except OSError: pass
            self.tasks.discard(task)

    def observation(self):
        return {'kind': 'byte-proxy', 'name': self.name, 'target_host': self.target_host,
                'target_port': self.target_port, 'policy_generation': self.generation,
                'connections': self.connections, 'connection_errors': self.connection_errors,
                **copy.deepcopy(self.directions), 'observed_at_ms': int(time.time() * 1000)}

    async def reset(self):
        self.policy()
        # Discarded TLS bytes cannot be repaired by reusing that TCP session.
        # Close only the proxy's own connections; normal clients may reconnect.
        for writer in list(self.writers): writer.close()
        for task in list(self.tasks): task.cancel()
        if self.tasks: await asyncio.gather(*list(self.tasks), return_exceptions=True)

    async def close(self):
        if self.server:
            self.server.close(); await self.server.wait_closed()
            self.server = None
        await self.reset()


class Evidence:
    def __init__(self, path, scope, *, required=()):
        self.path = Path(path).absolute()
        self.path.mkdir(mode=0o700, exist_ok=False)
        self.rows, self.required = [], tuple(required)
        self.scope = {**scope, 'class': 'FIXTURE', 'real_profile_qualified': False}
        private(self.path / 'scope.json', self.scope)

    def row(self, case, *, passed, effects_before, effects_after, observations, **details):
        if type(passed) is not bool or not observations or not isinstance(case, str):
            raise ValueError('row_requires_observation')
        for counters in (effects_before, effects_after):
            if (set(counters) != {'fixture_model', 'fixture_tool'} or any(
                    type(value) is not int or value < 0 for value in counters.values())):
                raise ValueError('controlled_counters_are_not_real_profile_evidence')
        result = {'case': case, 'class': 'FIXTURE', 'real_profile_qualified': False,
                  'passed': passed, 'effects_before': effects_before, 'effects_after': effects_after,
                  'observations': observations, **details}
        private(self.path / f'{len(self.rows):02d}-{case}.json', result)
        self.rows.append(result)
        return result

    def fail(self, case, exc):
        private(self.path / 'failure.json', {'class': 'FIXTURE', 'case': case,
            'error_type': type(exc).__name__, 'code': getattr(exc, 'code', None), 'completed_rows': len(self.rows)})

    def finish(self):
        completed = {r['case'] for r in self.rows if r['passed']}
        missing = sorted(set(self.required) - completed)
        result = {'class': 'FIXTURE', 'real_profile_qualified': False,
                  'passed': not missing and all(r['passed'] for r in self.rows),
                  'missing_rows': missing, 'rows': self.rows}
        private(self.path / 'complete.json', result)
        return result


def source_digest():
    root = Path(__file__).resolve().parents[2]
    files = sorted((root / 'mcp-servers/protocol-mcp/bgp/federation').rglob('*.py'))
    files += sorted((root / 'labs/ha').glob('*.py'))
    return hashlib.sha256(json.dumps({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in files}, sort_keys=True).encode()).hexdigest()


async def owned_call(function, *args, **kwargs):
    """Do not let cancellation hide a still-running owned mutation thread.

    The underlying command has its own finite deadline. Inspection/cleanup starts
    only after that bounded call has settled; an HTTP/subprocess timeout remains
    an unknown outcome and is never resent here.
    """
    task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await asyncio.shield(task)
        except Exception:
            pass
        raise
