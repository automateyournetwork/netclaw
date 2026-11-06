"""Retained delivery must not turn an unknown cleanup into a replay."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'labs/cloud/gcp/r06'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('r06_retire', SOURCE/'retire.py')
retire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retire)


@pytest.fixture
def execution(tmp_path, monkeypatch):
    config = {'run_id': '20261106-a4fd', 'quiesce_at': '2026-11-08T15:09:35Z',
              'cleanup_at': '2026-11-08T15:14:35Z', 'export_manifest': '/private/export.json'}
    monkeypatch.setattr(retire, 'validate', lambda c: {'plan_sha256': 'frozen'})
    calls = []
    monkeypatch.setattr(retire, 'invoke', lambda c, action, output, timeout: calls.append(action))
    return config, calls, tmp_path


@pytest.mark.parametrize('when', ['2026-11-08T15:09:34Z', '2026-11-08T15:11:36Z', '2026-11-09T15:09:35Z'])
def test_early_or_missed_window_cannot_stop_or_delete(execution, when):
    config, calls, root = execution
    with pytest.raises(ValueError, match='start_window'):
        retire.execute(config, root, now=retire.timestamp(when))
    assert calls == [] and not (root/'workflow-claim.json').exists()


def test_unknown_export_is_claimed_and_never_replayed(execution, monkeypatch):
    config, calls, root = execution
    def fail(c, action, output, timeout):
        calls.append(action)
        if action == 'quiesce-export': raise TimeoutError('lost reply')
    monkeypatch.setattr(retire, 'invoke', fail)
    with pytest.raises(TimeoutError):
        retire.execute(config, root, now=retire.timestamp(config['quiesce_at']))
    assert calls == ['inspect', 'quiesce-export']
    assert json.loads((root/'failure.json').read_text())['automatic_replay'] is False
    with pytest.raises(FileExistsError):
        retire.execute(config, root, now=retire.timestamp(config['quiesce_at']))
    assert calls == ['inspect', 'quiesce-export']


def test_unverified_export_prevents_teardown(execution, monkeypatch):
    config, calls, root = execution
    def refuse(*args): raise ValueError('export_changed')
    monkeypatch.setattr(retire, 'verify', refuse)
    with pytest.raises(ValueError, match='export_changed'):
        retire.execute(config, root, now=retire.timestamp(config['quiesce_at']))
    assert calls == ['inspect', 'quiesce-export']
    assert not (root/'settled.json').exists()


def test_private_input_change_refuses_before_operations(tmp_path):
    files = {}
    for name in ('ops.py', 'review.json', 'authorization.json', 'remote.py'):
        path = tmp_path/name
        path.write_text('{}')
        path.chmod(0o600)
        files[str(path)] = retire.hashlib.sha256(path.read_bytes()).hexdigest()
    config = {'schemaVersion': 1, 'scope': 'r06', 'run_id': '20261106-a4fd',
              'quiesce_at': '2026-11-08T15:09:35Z', 'cleanup_at': '2026-11-08T15:14:35Z',
              'expires_at': '2026-11-08T15:19:35Z', 'python': sys.executable,
              'ops': str(tmp_path/'ops.py'), 'review': str(tmp_path/'review.json'),
              'authorization': str(tmp_path/'authorization.json'),
              'export_manifest': str(tmp_path/'export.json'), 'files': files}
    (tmp_path/'ops.py').write_text('changed')
    with pytest.raises(ValueError, match='input_changed'):
        retire.validate(config)
    config['scope'] = 'r05'
    with pytest.raises(ValueError, match='scope_invalid'):
        retire.validate(config)
