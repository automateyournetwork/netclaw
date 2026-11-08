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
import traceback

from .etcd_lab import private

ROWS = ('minority', 'asymmetric-request', 'asymmetric-response', 'threeway', 'delay-300ms',
        'latency-safety-300ms', 'stale-member', 'clock-forward', 'clock-backward', 'clock-suspend', 'unknown-commit',
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
        self.closing = False
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
        self.closing = False
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
        if self.closing or len(self.tasks) >= 32:
            writer.transport.abort(); await writer.wait_closed(); return
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
        for writer in list(self.writers): writer.transport.abort()
        for task in list(self.tasks): task.cancel()
        if self.tasks:
            await asyncio.wait_for(asyncio.gather(*list(self.tasks), return_exceptions=True), 5)

    async def close(self):
        self.closing = True
        server, self.server = self.server, None
        if server: server.close()
        # Python3.12 waits for active client transports, not only the listener.
        # Drop owned connections before waiting, including idle HTTP keepalives.
        await self.reset()
        if server: await asyncio.wait_for(server.wait_closed(), 5)


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
            **failure_details(exc), 'completed_rows': len(self.rows)})

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


_FIXTURE_FAILURES = frozenset({
    'refused_gate_invoked_callback', 'fault_admitted_callback', 'isolated_old_authority_survived',
    'fault_not_observed', 'stale_or_uncertain_claim_consumed', 'unknown_claim_forwarded',
    'expired_reconciled_claim_forwarded', 'unknown_claim_changed', 'retired_node_restarted',
    'capacity_fault_not_committed', 'capacity_fault_not_observed_at_gate', 'capacity_restore_state_changed',
    'capacity_restore_unknown', 'preexisting_etcd_alarm', 'nospace_not_observed', 'nospace_cleanup_failed',
    'original_result_changed', 'original_ack_changed', 'target_leader_not_established',
    'epoch_not_increased', 'old_epoch_admitted', 'restart_durable_state_changed', 'member_incarnation_reused',
    'new_id_bypassed_unknown_reservation', 'restart_ack_changed', 'fixture_effect_bound',
    'restart_export_required', 'restart_baseline_not_running', 'restart_identity_changed',
    'restart_stop_not_verified', 'restart_start_not_verified', 'fixture_cleanup_incomplete', 'latency_effect_counter_mismatch', 'latency_safety_not_established',
})


def failure_details(exc):
    """Keep useful fixed fixture assertions; never dump locals or private errors."""
    message = str(exc)
    root = Path(__file__).resolve().parents[2]
    frames = []
    for frame in traceback.extract_tb(exc.__traceback__)[-12:]:
        path = Path(frame.filename)
        try: filename = str(path.resolve().relative_to(root))
        except ValueError: filename = path.name
        frames.append({'file': filename, 'function': frame.name, 'line': frame.lineno})
    code = getattr(exc, 'code', None)
    if not isinstance(code, (str, int)): code = None
    if isinstance(code, str) and (len(code) > 100 or not all(ch.isalnum() or ch in '_.-' for ch in code)): code = None
    return {'error_type': type(exc).__name__, 'code': code,
            'message': message if message in _FIXTURE_FAILURES else (code if code is not None else 'private_error_redacted'),
            'frames': frames}


def trace_store_requests(store, source, records):
    """Instrument timings only; never persist request bodies/authentication data."""
    original = store._request
    def request(path, body, **options):
        began = time.monotonic()
        result, error = None, None
        try:
            result = original(path, body, **options)
            return result
        except BaseException as exc:
            error = failure_details(exc)
            raise
        finally:
            revision = result.get('header', {}).get('revision') if isinstance(result, dict) else None
            if len(records) < 32768:
                records.append({'source_node': source, 'path': path, 'started_monotonic': began,
                    'elapsed_ms': round((time.monotonic()-began)*1000, 3),
                    'read_only': options.get('read_only', False), 'revision': revision,
                    'error_code': error['code'] if error else None})
    store._request = request


def latency_outcome(probe, before, after):
    """Safety acceptance is distinct from healthy service availability."""
    if probe['outcome'] == 'admitted':
        expected = dict(before)
        expected['fixture_' + probe['kind']] += 1
        if after != expected: raise AssertionError('latency_effect_counter_mismatch')
        return 'supported-positive'
    if (probe['outcome'] == 'refused' and probe.get('code') in ('admission_expired', 'no_quorum')
            and before == after):
        return 'bounded-safe-refusal'
    raise AssertionError('latency_safety_not_established')
