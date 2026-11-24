"""Private capture-once orchestration; no SSH or native policy bypass.

An operator-selected local adapter exports qualified_read_only_capture=True,
capture_once(device, command, timeout=...) or capture_context(...), and
parse_captured(..., output=...). Contexts preserve raw before cleanup; durable
lifecycle markers retire uncertain cleanup even when raw capture is complete.
The marker is a capability contract, NOT evidence of native policy qualification.
Adapters load only in fresh selected-interpreter processes, never forked sessions.
"""
from contextlib import nullcontext
from datetime import datetime, timezone
import importlib.util
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid

_spec = importlib.util.spec_from_file_location('genie_world_facts', Path(__file__).with_name('facts.py'))
facts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(facts)
LIMIT = 8 * 1024 * 1024


def _write(path, data):
    # A killed writer must not leave a partial capture looking complete.
    temporary = path.with_name(path.name + '.partial')
    with open(temporary, 'xb') as f:
        os.chmod(temporary, 0o600)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)


def _child(request_path):
    os.umask(0o077)
    request = json.loads(Path(request_path).read_text())
    # The child owns a deadline too: loss of the parent must not leave a native
    # connection/parser running indefinitely. A kill never proves remote cleanup.
    if 'deadline_monotonic' in request:
        if os.getpgrp() != os.getpid():
            raise ValueError('owned_process_group_required')
        remaining = request['deadline_monotonic'] - time.monotonic()
        if remaining <= 0:
            return
        def expire(*_):
            os.killpg(os.getpgrp(), signal.SIGKILL)
        signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, remaining)
    directory = Path(request_path).parent
    outcome, parsed, failure_reason = 'unavailable', None, None
    try:
        spec = importlib.util.spec_from_file_location('capture_adapter', request['adapter'])
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        if getattr(adapter, 'qualified_read_only_capture', False) is not True:
            raise ValueError('qualified_capture_capability_required')
        _write(directory / 'capture-started', b'1')
        context_factory = getattr(adapter, 'capture_context', None)
        if context_factory is not None:
            if not callable(context_factory):
                raise ValueError('invalid_capture_context')
            # Persistent marker also covers abrupt process death during __exit__.
            _write(directory / 'lifecycle-started', b'1')
            context = context_factory(request['device'], request['command'],
                                      timeout=request['timeout'], evidence_directory=directory)
        else:
            context = nullcontext(adapter.capture_once(request['device'], request['command'],
                                                        timeout=request['timeout']))
        admitted = persisted = False
        with context as raw:
            if not isinstance(raw, str):
                raise ValueError('invalid_capture')
            data = raw.encode('utf8')
            with open(request['budget'], 'r+') as budget:
                fcntl.flock(budget, fcntl.LOCK_EX)
                available = int(budget.read())
                admitted = len(data) <= available
                if admitted:
                    budget.seek(0)
                    budget.write(str(available - len(data)))
                    budget.truncate()
                    budget.flush()
                fcntl.flock(budget, fcntl.LOCK_UN)
            if not admitted:
                failure_reason = 'evidence_limit'
            else:
                _write(directory / 'raw', data)
                persisted = True
                outcome = 'raw_only'
        if context_factory is not None:
            _write(directory / 'lifecycle-finished', b'1')
        # Detached parsing is permitted only after a clean context exit.
        if admitted and persisted:
            try:
                parsed = adapter.parse_captured(request['device'], request['command'], output=raw)
                if not isinstance(parsed, dict):
                    raise ValueError('invalid_parse')
                # Bound normalized transport as well as raw evidence.
                if len(json.dumps(parsed).encode()) > LIMIT:
                    raise ValueError('parsed_limit')
                outcome = 'observed' if parsed else 'empty'
            except Exception:
                parsed, outcome = None, 'parse_failed'
    except Exception:
        pass  # Exception strings and native stdout must never escape this process.
    _write(directory / 'result', json.dumps({'outcome': outcome, 'parsed': parsed,
                                           'failure_reason': failure_reason}).encode())
    if 'deadline_monotonic' in request:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _stop(process):
    # POSIX only: kill the entire owned group, including adapter descendants.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        # Darwin can report EPERM for the just-expired, now empty group after
        # the child's own group kill. Never suppress it for a running leader.
        process.wait(timeout=1)
    process.wait(timeout=1)


def collect(devices, capability_path, parser_version, *, evidence_root,
            read_timeout=30, overall_timeout=None, byte_limit=LIMIT, profile='initial',
            child_env=None):
    """At most two processes, one capture/read; timeouts retire that device.

    Smaller limits support fault drills. Limits cannot exceed FR-014. This API
    is local operator code, not an agent-supplied adapter path or read grant.
    Raw bytes remain private; no retries or transport fallbacks are implemented.
    """
    if os.name != 'posix':
        raise ValueError('process_boundary_unqualified_on_platform')
    if profile not in facts.PROFILES:
        raise ValueError('collection_profile')
    commands, overall_limit = facts.PROFILES[profile]
    if overall_timeout is None:
        overall_timeout = overall_limit
    if not 1 <= len(devices) <= 4 or len(set(devices)) != len(devices):
        raise ValueError('device_limit')
    if (not math.isfinite(read_timeout) or not 0 < read_timeout <= 30
            or not math.isfinite(overall_timeout) or not 0 < overall_timeout <= overall_limit
            or not isinstance(byte_limit, int) or not 0 < byte_limit <= LIMIT):
        raise ValueError('collection_limit')
    adapter = str(Path(capability_path).resolve(strict=True))
    root = Path(evidence_root)
    if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError('private_evidence_root_required')
    pending = [(device, command, index) for index, command in enumerate(commands) for device in devices]
    active, observations, retired = [], [], set()
    sample_ready = {}
    remaining = byte_limit
    budget_path = root / ('capture-budget-' + str(uuid.uuid4()))
    _write(budget_path, str(byte_limit).encode())
    deadline = time.monotonic() + overall_timeout
    try:
        while pending or active:
            while pending and len(active) < 2 and time.monotonic() < deadline and remaining > 0:
                pending = [(d, c, i) for d, c, i in pending if d not in retired]
                busy = {entry[2] for entry in active}
                now = time.monotonic()
                index = next((i for i, (d, c, n) in enumerate(pending)
                              if d not in busy and (n != 5 or now >= sample_ready.get(d, math.inf))), None)
                if index is None:
                    break
                device, command, command_index = pending.pop(index)
                directory = Path(tempfile.mkdtemp(prefix='capture-', dir=root))
                began = datetime.now(timezone.utc).isoformat()
                started = time.monotonic()
                expires = min(deadline, started + read_timeout)
                request = {'adapter': adapter, 'device': device, 'command': command,
                           'timeout': read_timeout, 'budget': str(budget_path.resolve()),
                           'profile': profile, 'command_index': command_index,
                           'deadline_monotonic': expires}
                _write(directory / 'request', json.dumps(request).encode())
                process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                                            '--child', str(directory / 'request')],
                                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, start_new_session=True,
                                           env=child_env)
                active.append((process, directory, device, command, began,
                               expires, command_index))
            for entry in active[:]:
                process, directory, device, command, began, expires, command_index = entry
                timed_out = time.monotonic() >= expires
                if process.poll() is None and not timed_out:
                    continue
                _stop(process)
                active.remove(entry)
                raw, parsed, outcome = '', None, 'timeout' if timed_out else 'unavailable'
                failure_reason = None
                raw_path = directory / 'raw'
                if raw_path.exists():
                    size = raw_path.stat().st_size
                    if size <= remaining:
                        raw = raw_path.read_bytes().decode('utf8')
                        remaining -= size
                        if not timed_out:
                            outcome = 'raw_only'
                    else:
                        failure_reason = 'evidence_limit'
                if not timed_out and failure_reason is None:
                    result_path = directory / 'result'
                    if result_path.exists() and result_path.stat().st_size <= LIMIT + 128:
                        result = json.loads(result_path.read_text())
                        outcome, parsed = result['outcome'], result['parsed']
                        failure_reason = result.get('failure_reason')
                capture_unknown = (directory / 'capture-started').exists() and not raw_path.exists()
                cleanup_unknown = ((directory / 'lifecycle-started').exists()
                                   and not (directory / 'lifecycle-finished').exists())
                if timed_out or capture_unknown or cleanup_unknown or failure_reason == 'evidence_limit':
                    retired.add(device)
                if command_index == 4:
                    # Conservative end-to-start gap, after capture AND parsing.
                    # No worker is occupied while waiting; no shorter drill gap.
                    sample_ready[device] = time.monotonic() + 10
                observations.append({'id': str(uuid.uuid4()), 'device_ref': device,
                    'classification': 'private', 'command': command,
                    'profile': profile, 'command_index': command_index,
                    **({'sample_index': command_index - 3} if command == 'show interfaces' else {}),
                    'started_at': began, 'finished_at': datetime.now(timezone.utc).isoformat(),
                    'outcome': outcome, 'parser_version': parser_version, 'raw': raw,
                    'parsed': parsed, 'sha256': facts.evidence_hash(raw),
                    'artifact_ref': directory.name,
                    'failure_reason': failure_reason,
                    'capture_outcome_unknown': capture_unknown,
                    'cleanup_outcome_unknown': cleanup_unknown})
                # Retain request/raw/result locally for failure inspection, not stdout.
            if time.monotonic() >= deadline or remaining <= 0:
                pending.clear()
            if active or pending:
                time.sleep(.005)
    finally:
        for process, *_ in active:
            _stop(process)
    return {'classification': 'private', 'observations': observations,
            'profile': profile, 'complete': len(observations) == len(devices) * len(commands),
            'qualification': 'process_deadline_enforced_native_policy_required',
            'facts': facts.normalize(observations, profile=profile)}


if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == '--child':
    _child(sys.argv[2])
