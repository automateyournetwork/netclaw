"""Source-only checks of the REAL qualification instrumentation. No cluster, Docker or daemon."""
import asyncio
import base64
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import threading
import uuid

import pytest

from bgp.federation.ha.admission import MemberAdmission
from bgp.federation.ha.config import HAError
try:  # exporter TLS dependencies may be absent in a source-only environment
    from bgp.federation.ha.internal import MemberAttachments
    from bgp.federation.ha.member import ClusterMemberOperations
except ImportError:  # pragma: no cover
    MemberAttachments = ClusterMemberOperations = None
from bgp.federation.ha.store import EtcdStore
from test_ha_admission_179 import setup as admission_setup

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from labs.ha import real_instrument as real

RUN_ID, INSTALLATION = str(uuid.uuid4()), str(uuid.uuid4())
OPERATION = str(uuid.uuid4())


def private(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def make_run(tmp_path, role_name='member', scenario='clock-wall-step', parameters=None):
    root = private(tmp_path / 'run')
    source = private(root / 'source/labs/ha')
    for name in ('real_instrument.py', 'real_role_launcher.py'):
        shutil.copy(REPO / 'labs/ha' / name, source / name)
    frozen = {f'labs/ha/{n}': hashlib.sha256((source / n).read_bytes()).hexdigest()
              for n in ('real_instrument.py', 'real_role_launcher.py')}
    name = 'netclaw-r08-unit-test'
    def put(path, value):
        path.write_bytes(real.canonical(value)); os.chmod(path, 0o600)
    put(root / 'reviewed-plan.json', {'run_id': RUN_ID, 'name': name, 'root': str(root), 'source_files': frozen})
    put(root / 'materialized.json', {'launch_schema': 3, 'profile_kind': 2})
    contract = {'schemaVersion': 3, 'installation_id': INSTALLATION, 'role': real.ROLE_NAMES[role_name], 'runtime_kind': 'openclaw',
                'control_only': role_name != 'member', 'home': str(private(root / 'homes' / role_name)),
                'source_root': str(root / 'source')}
    private(root / 'contracts'); put(root / 'contracts' / (role_name + '.json'), contract)
    raw = (root / 'contracts' / (role_name + '.json')).read_bytes()
    private(root / 'instrument')
    config = real.build_config(root, role_name, scenario, hashlib.sha256(raw).hexdigest(), INSTALLATION, RUN_ID, name, parameters)
    put(root / 'instrument' / f'{role_name}-{scenario}.json', config)
    return root, config, contract, root / 'instrument' / f'{role_name}-{scenario}.json'


def validator_for(contract, environment=None):
    def validate(path): return dict(contract), dict(environment or {})
    return validate


def start(tmp_path, scenario, role_name=None, parameters=None, armed=OPERATION):
    role_name = role_name or ('member' if real.SCENARIOS[scenario][0] == 'member' else 'border0')
    root, config, contract, config_file = make_run(tmp_path, role_name, scenario, parameters)
    instrument = real.Instrument(config)
    if armed:
        real.arm(config_file, armed)
    return instrument, root, config_file


def phases(instrument):
    return sorted(json.loads(p.read_text())['phase'] for p in instrument.directory.glob('*-*-*.json') if 'claim' not in p.name[:6])


def evidence(instrument):
    return [json.loads(p.read_text()) for p in sorted(instrument.directory.glob(f"{instrument.config['role_name']}-*.json"))]


# ---------------------------------------------------------------------------------- default-off / shape

def test_import_patches_nothing_and_production_never_names_the_instrument():
    assert 'real_instrument' not in inspect.getsource(MemberAdmission)
    for source in (REPO / 'mcp-servers').rglob('*.py'):
        if '/ha/' in str(source) or source.name.startswith(('protected_', 'federation')):
            assert 'real_instrument' not in source.read_text(errors='ignore'), source
    assert 'monotonic' in inspect.signature(MemberAdmission.__init__).parameters  # production default stays time.*
    assert MemberAdmission.__init__.__module__ == 'bgp.federation.ha.admission'


@pytest.mark.skipif(MemberAttachments is None, reason='exporter TLS dependencies unavailable')
def test_production_surfaces_have_the_patched_signatures():
    assert list(inspect.signature(MemberAdmission.begin).parameters) == ['self', 'context', 'kind', 'ordinal', 'request_digest']
    assert list(inspect.signature(MemberAdmission.fresh).parameters) == ['self', 'started']
    assert inspect.iscoroutinefunction(MemberAttachments.send_admission)
    for name in ('member_result', 'acknowledge'):
        function = getattr(ClusterMemberOperations, name)
        assert inspect.iscoroutinefunction(function) and list(inspect.signature(function).parameters) == ['self', 'channel', 'params']
    assert list(inspect.signature(EtcdStore._request).parameters) == ['self', 'path', 'body', 'read_only', 'login']


def test_config_is_exact_and_scenario_role_bound(tmp_path):
    root, config, *_ = make_run(tmp_path)
    assert real.validate_config(dict(config)) == config
    bad = [dict(config, scenario='arbitrary'), dict(config, extra=1), dict(config, role='border', role_name='border0'),
           dict(config, scenario='unknown-commit-recovered'), dict(config, parameters={'kind': 'model'}),
           dict(config, parameters={'kind': 'model', 'ordinal': 1, 'delta_ms': 10}),
           dict(config, evidence_dir=str(root / 'elsewhere')), dict(config, source_root='/tmp/source'),
           dict(config, run_name='netclaw-r05-prod')]
    for value in bad:
        with pytest.raises(real.InstrumentRefused):
            real.validate_config(value)
    for scenario, parameters in [('clock-monotonic-step', {'kind': 'model', 'ordinal': 1, 'delta_ms': -900}),
                                 ('stale-leader-held-claim', {'kind': 'model', 'ordinal': 1, 'hold_ms': 100})]:
        with pytest.raises(real.InstrumentRefused):
            real.build_config(root, 'member', scenario, 'a' * 64, INSTALLATION, RUN_ID, 'netclaw-r08-unit-test', parameters)


def test_unarmed_instrument_installs_but_never_acts(tmp_path):
    instrument, *_ = start(tmp_path, 'clock-wall-step', armed=None)
    journal, manifest, member, context, *_ = admission_setup(tmp_path / 'a')
    instrument.install(MemberAdmission=MemberAdmission)
    try:
        live = MemberAdmission(tmp_path / 'live', manifest, member)
        request, started = live.begin(context, 'model', 1, 'c' * 64)
        assert live.fresh(started) > 0
    finally:
        instrument.uninstall()
    assert [e['phase'] for e in evidence(instrument)] == ['installed']
    assert not list(instrument.directory.glob('claim-*'))
    assert MemberAdmission.begin.__module__ == 'bgp.federation.ha.admission'  # restored


# ---------------------------------------------------------------------------------- (a) clock

@pytest.mark.asyncio
@pytest.mark.parametrize('scenario', ['clock-wall-step', 'clock-monotonic-step'])
async def test_clock_step_is_scenario_exact_and_one_shot(tmp_path, scenario):
    instrument, root, config_file = start(tmp_path, scenario)
    journal, manifest, member, context, clock, response = admission_setup(tmp_path / 'a')
    instrument.install(MemberAdmission=MemberAdmission)
    effects = []
    async def send(request): return response(request)
    async def effect(): effects.append('model')
    try:
        live = MemberAdmission(tmp_path / 'live', manifest, member)
        other = dict(context, operation_id=str(uuid.uuid4()))
        # Another operation and another kind are untouched.
        request, started = live.begin(other, 'model', 1, 'c' * 64); assert live.fresh(started) > 0
        request, started = live.begin(dict(context, operation_id=OPERATION), 'tool', 1, 'c' * 64); assert live.fresh(started) > 0
        # The armed operation's exact admission is refused by the production gate before invoke.
        with pytest.raises(HAError, match='clock_uncertain'):
            await live.run(dict(context, operation_id=OPERATION), 'model', 1, 'c' * 64, send, effect)
        assert effects == []
        # One-shot: a restarted instrument/process with the same evidence directory never fires again.
        again = real.Instrument(real.validate_config(json.loads(config_file.read_text())))
        assert again.claim(OPERATION) is False
    finally:
        instrument.uninstall()
    kinds = [e['phase'] for e in evidence(instrument)]
    assert kinds == ['installed', 'clock-step', 'gate-refusal']
    refusal = evidence(instrument)[-1]
    assert refusal['details']['code'] == 'clock_uncertain' and refusal['operation_id'] == OPERATION
    for path in instrument.directory.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.asyncio
async def test_clock_step_outside_manifest_bounds_is_not_injected(tmp_path):
    instrument, *_ = start(tmp_path, 'clock-monotonic-step', parameters={'kind': 'model', 'ordinal': 1, 'delta_ms': 2000})
    journal, manifest, member, context, *_ = admission_setup(tmp_path / 'a')
    manifest.limits['clock_uncertainty_ms'] = 2000  # step no longer exceeds the uncertainty bound
    instrument.install(MemberAdmission=MemberAdmission)
    try:
        live = MemberAdmission(tmp_path / 'live', manifest, member)
        request, started = live.begin(dict(context, operation_id=OPERATION), 'model', 1, 'c' * 64)
        assert live.fresh(started) > 0
    finally:
        instrument.uninstall()
    assert not list(instrument.directory.glob('claim-*'))


# ---------------------------------------------------------------------------------- (d) stale leader

class FakeAttachments:
    def __init__(self): self.sent = []
    async def send_admission(self, request):
        self.sent.append(request)
        return {'payload': {'claim': {'epoch': 5, 'leader': {'node_id': 'node-a'}, 'request': request}, 'commit_revision': 9},
                'key_id': 'k', 'signature': 's'}


@pytest.mark.asyncio
async def test_held_claim_is_returned_unchanged_after_release_once(tmp_path):
    instrument, *_ = start(tmp_path, 'stale-leader-held-claim')
    instrument.install(MemberAttachments=FakeAttachments)
    try:
        attachments = FakeAttachments()
        request = {'operation_id': OPERATION, 'kind': 'model', 'ordinal': 1}
        (instrument.directory / 'release.json').write_bytes(b'{}')
        before = await asyncio.wait_for(attachments.send_admission(request), 5)
        assert before['payload']['claim']['epoch'] == 5 and attachments.sent == [request]
        # Not held: other op, other kind, and the same claim a second time.
        for other in (dict(request, operation_id=str(uuid.uuid4())), dict(request, kind='tool'), request):
            await asyncio.wait_for(attachments.send_admission(other), 5)
        instrument.params['hold_ms'] = 300  # timeout path (config bound is 4 s; unit-test shortcut only)
    finally:
        instrument.uninstall()
    rows = evidence(instrument)
    assert [r['phase'] for r in rows] == ['installed', 'claim-held', 'claim-released']
    assert rows[1]['details']['claim_epoch'] == 5 and rows[2]['details']['reason'] == 'released'
    assert rows[1]['details']['proof_sha256'] == rows[2]['details']['proof_sha256']


# ---------------------------------------------------------------------------------- (b) result / ack

class FakeChannel:
    trusted = strict = True
    attestation = 'possession'
    _closed = False
    protected_peer_binding = {'installation_id': 'i'}
    def __init__(self): self.closed = 0
    async def close(self): self.closed += 1


class FakeOperations:
    def __init__(self): self.results, self.acks = [], []
    async def member_result(self, channel, params):
        self.results.append(params); return {'payload': {'receipt': 1}}
    async def acknowledge(self, channel, params):
        self.acks.append(params); return {'state': 'acknowledged'}


@pytest.mark.asyncio
async def test_result_reply_loss_is_one_shot_and_leaves_ack_untouched(tmp_path):
    instrument, *_ = start(tmp_path, 'result-reply-loss')
    instrument.install(ClusterMemberOperations=FakeOperations)
    try:
        ops, channel = FakeOperations(), FakeChannel()
        assert not hasattr(FakeOperations.acknowledge, '__wrapped__') and 'acknowledge' not in [p[1] for p in instrument.patches]
        other = await ops.member_result(channel, {'operation_id': str(uuid.uuid4())})
        assert other == {'payload': {'receipt': 1}} and channel.closed == 0
        weak = FakeChannel(); weak.attestation = 'none'
        await ops.member_result(weak, {'operation_id': OPERATION}); assert weak.closed == 0
        assert not list(instrument.directory.glob('claim-*'))  # unauthenticated channel did not spend the claim
        with pytest.raises(ConnectionError, match='instrumented_result_reply_loss'):
            await ops.member_result(channel, {'operation_id': OPERATION})
        assert channel.closed == 1 and len(ops.results) == 3  # the production lookup ran; only the reply was lost
        assert await ops.member_result(channel, {'operation_id': OPERATION}) == {'payload': {'receipt': 1}}
    finally:
        instrument.uninstall()
    assert [r['phase'] for r in evidence(instrument)] == ['installed', 'result-reply-dropped']
    assert evidence(instrument)[1]['details']['envelope_sha256'] == real.sha({'payload': {'receipt': 1}})


@pytest.mark.asyncio
async def test_ack_delivery_loss_happens_before_production_persistence(tmp_path):
    instrument, *_ = start(tmp_path, 'ack-delivery-loss')
    instrument.install(ClusterMemberOperations=FakeOperations)
    try:
        ops, channel = FakeOperations(), FakeChannel()
        ack = {'ack': {'payload': {'operation_id': OPERATION}}}
        with pytest.raises(ConnectionError, match='instrumented_ack_delivery_loss'):
            await ops.acknowledge(channel, ack)
        assert ops.acks == [] and channel.closed == 1
        assert await ops.acknowledge(channel, ack) == {'state': 'acknowledged'} and ops.acks == [ack]
        assert await ops.acknowledge(channel, {'bad': 1}) == {'state': 'acknowledged'}  # malformed passes through to production
    finally:
        instrument.uninstall()
    assert [r['phase'] for r in evidence(instrument)] == ['installed', 'ack-delivery-dropped']


# ---------------------------------------------------------------------------------- (c) unknown commit

def b64(text): return base64.b64encode(text.encode()).decode()


def committed_store(monkeypatch, calls):
    prefix = f'/netclaw/ha/{uuid.uuid4()}/{uuid.uuid4()}/'
    def fake(self, path, body, *, read_only=False, login=False):
        calls.append((path, read_only, body)); return {'succeeded': True, 'header': {'revision': '41'}}
    monkeypatch.setattr(EtcdStore, '_request', fake)
    store = EtcdStore.__new__(EtcdStore); store.prefix = prefix
    return store


def admit(store, operation=OPERATION, action='admit_model'):
    decision = {'decision_id': str(uuid.uuid4()), 'action': action, 'leader': {}, 'epoch': 3,
                'writes_sha256': 'a' * 64, 'result_sha256': 'b' * 64}
    store.txn([('control', 'revision', 1)], [('operations/' + operation, {'state': 'member_admitted'}, None),
                                             ('decisions/' + decision['decision_id'], decision, None)])
    return decision


@pytest.mark.parametrize('scenario', ['unknown-commit-recovered', 'unknown-commit-unresolved'])
def test_commit_reply_drop_follows_a_real_commit_exactly_once(tmp_path, monkeypatch, scenario):
    instrument, *_ = start(tmp_path, scenario)
    calls = []; store = committed_store(monkeypatch, calls)
    instrument.install(EtcdStore=EtcdStore, HAError=HAError)
    try:
        admit(store, str(uuid.uuid4()))      # another operation
        admit(store, action='approve')        # another action
        assert len(calls) == 2 and not list(instrument.directory.glob('claim-*'))
        with pytest.raises(HAError, match='commit_unknown'):
            admit(store)
        assert len(calls) == 3  # the real request was sent exactly once, then its reply was dropped
        decision_key = json.loads(json.dumps(calls[-1][2]))['success'][1]['request_put']['key']
        read = {'key': decision_key, 'serializable': False}
        if scenario == 'unknown-commit-unresolved':
            with pytest.raises(HAError, match='no_quorum'):
                store._request('/v3/kv/range', read, read_only=True)
            assert len(calls) == 3  # recovery read refused before the network
        calls.clear()
        store._request('/v3/kv/range', read, read_only=True)  # one-shot: reads pass again
        admit(store)  # and later claims are not dropped
        assert len(calls) == 2
    finally:
        instrument.uninstall()
    phases_seen = [r['phase'] for r in evidence(instrument)]
    expected = ['installed', 'commit-reply-drop-armed', 'commit-reply-dropped']
    assert phases_seen == expected + (['recovery-read-refused'] if scenario.endswith('unresolved') else [])
    assert evidence(instrument)[2]['details']['etcd_revision'] == '41'


def test_commit_scenario_refuses_without_ha_error_class(tmp_path):
    instrument, *_ = start(tmp_path, 'unknown-commit-recovered')
    with pytest.raises(TypeError):
        instrument._commit(EtcdStore=EtcdStore)


# ---------------------------------------------------------------------------------- one-shot / evidence

def test_claim_is_atomic_across_threads_and_instruments(tmp_path):
    instrument, root, config_file = start(tmp_path, 'result-reply-loss')
    peers = [real.Instrument(json.loads(config_file.read_text())) for _ in range(8)]
    results = []
    threads = [threading.Thread(target=lambda p=p: results.append(p.claim(OPERATION))) for p in peers]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert results.count(True) == 1


def test_fault_is_suppressed_when_evidence_cannot_be_written(tmp_path, monkeypatch):
    instrument, *_ = start(tmp_path, 'result-reply-loss')
    monkeypatch.setattr(real, 'write_new', lambda path, value: (_ for _ in ()).throw(OSError('disk')) if 'claim' not in str(path) else None)
    assert instrument.fire(OPERATION, 'result-reply-dropped') is False


def test_arm_and_release_are_new_only_and_exact(tmp_path):
    instrument, root, config_file = start(tmp_path, 'result-reply-loss', armed=None)
    assert instrument.armed() is None
    real.arm(config_file, OPERATION)
    with pytest.raises(FileExistsError):
        real.arm(config_file, str(uuid.uuid4()))
    assert instrument.armed() == OPERATION and instrument.wants(OPERATION) and not instrument.wants(str(uuid.uuid4()))
    # Wrong run / scenario / loose permission arm files are ignored.
    arm = instrument.directory / 'arm.json'
    fresh = real.Instrument(json.loads(config_file.read_text()))
    os.chmod(arm, 0o644); assert fresh.armed() is None
    os.chmod(arm, 0o600)
    arm.write_bytes(real.canonical({'schema_version': 1, 'run_id': str(uuid.uuid4()), 'scenario': 'result-reply-loss',
                                    'operation_id': OPERATION, 'armed_ms': 1}))
    assert fresh.armed() is None
    assert real.main(['arm', '--config', str(config_file), '--operation-id', 'not-a-uuid']) == 1


def test_create_config_cli_writes_a_new_only_private_config(tmp_path):
    root, config, contract, _ = make_run(tmp_path, 'border1', 'unknown-commit-recovered')
    assert real.main(['create-config', '--root', str(root), '--role-name', 'border1', '--scenario', 'unknown-commit-unresolved',
                      '--param', 'kind=model']) == 0
    made = root / 'instrument/border1-unknown-commit-unresolved.json'
    assert stat.S_IMODE(made.stat().st_mode) == 0o600 and real.validate_config(json.loads(made.read_text()))
    assert real.main(['create-config', '--root', str(root), '--role-name', 'border1', '--scenario', 'unknown-commit-unresolved']) == 1


# ---------------------------------------------------------------------------------- qualification refusal

def qualify(tmp_path, scenario='clock-wall-step', role_name='member', **changes):
    root, config, contract, config_file = make_run(tmp_path, role_name, scenario)
    cfg = dict(contract, **changes)
    return real.check_qualification(root / 'contracts' / (role_name + '.json'), config_file, source_root=root / 'source',
                                    validator=validator_for(cfg), module_file=root / 'source/labs/ha/real_instrument.py'), \
        (root, config, contract, config_file)


def test_real_qualification_profile_is_accepted(tmp_path):
    (config, cfg, environment), _ = qualify(tmp_path)
    assert config['scenario'] == 'clock-wall-step' and cfg['role'] == 'member'


@pytest.mark.parametrize('changes', [{'schemaVersion': 1}, {'runtime_kind': 'hermes'}, {'role': 'border'},
                                     {'installation_id': str(uuid.uuid4())}, {'control_only': True},
                                     {'home': '/tmp/other-home'}, {'source_root': '/tmp/other-source'}])
def test_non_qualification_contract_is_refused(tmp_path, changes):
    with pytest.raises(real.InstrumentRefused):
        qualify(tmp_path, **changes)


def test_production_validation_failure_is_propagated(tmp_path):
    root, config, contract, config_file = make_run(tmp_path)
    def refuse(path): raise ValueError('protected_role_refused')
    with pytest.raises(ValueError):
        real.check_qualification(root / 'contracts/member.json', config_file, source_root=root / 'source', validator=refuse,
                                 module_file=root / 'source/labs/ha/real_instrument.py')


def test_run_layout_and_frozen_source_are_enforced(tmp_path):
    root, config, contract, config_file = make_run(tmp_path)
    contract_file, module = root / 'contracts/member.json', root / 'source/labs/ha/real_instrument.py'
    ok = dict(source_root=root / 'source', validator=validator_for(contract), module_file=module)
    real.check_qualification(contract_file, config_file, **ok)
    # contract outside <root>/contracts, or a different role file
    moved = root / 'member.json'; moved.write_bytes(contract_file.read_bytes()); os.chmod(moved, 0o600)
    with pytest.raises(real.InstrumentRefused): real.check_qualification(moved, config_file, **ok)
    # not the frozen source copy (the module under test is the repository file)
    with pytest.raises(real.InstrumentRefused):
        real.check_qualification(contract_file, config_file, **dict(ok, module_file=REPO / 'labs/ha/real_instrument.py'))
    # contract changed after the config was written
    contract_file.write_bytes(contract_file.read_bytes() + b' '); os.chmod(contract_file, 0o600)
    with pytest.raises(real.InstrumentRefused, match='contract_changed'): real.check_qualification(contract_file, config_file, **ok)
    # instrumentation source that is not the reviewed frozen file
    root2, config2, contract2, config_file2 = make_run(tmp_path / 'two')
    module2 = root2 / 'source/labs/ha/real_instrument.py'; os.chmod(module2, 0o600); module2.write_text(module2.read_text() + '\n# edit\n')
    with pytest.raises(real.InstrumentRefused, match='instrument_source_not_frozen'):
        real.check_qualification(root2 / 'contracts/member.json', config_file2, source_root=root2 / 'source',
                                 validator=validator_for(contract2), module_file=module2)


def test_plan_binding_and_ambient_environment_are_enforced(tmp_path):
    root, config, contract, config_file = make_run(tmp_path)
    kw = dict(source_root=root / 'source', validator=validator_for(contract, {'A': '1'}), module_file=root / 'source/labs/ha/real_instrument.py')
    real.check_qualification(root / 'contracts/member.json', config_file, environ={'A': '1'}, **kw)
    with pytest.raises(real.InstrumentRefused, match='ambient_environment_refused'):
        real.check_qualification(root / 'contracts/member.json', config_file, environ={'A': '1', 'PYTHONPATH': '/x'}, **kw)
    plan = root / 'reviewed-plan.json'
    value = json.loads(plan.read_text()); value['run_id'] = str(uuid.uuid4()); plan.write_bytes(real.canonical(value))
    with pytest.raises(real.InstrumentRefused, match='run_plan_mismatch'):
        real.check_qualification(root / 'contracts/member.json', config_file, **kw)
    os.chmod(config_file, 0o644)
    with pytest.raises(real.InstrumentRefused, match='private_file_required'):
        real.check_qualification(root / 'contracts/member.json', config_file, **kw)


def test_launcher_refuses_outside_a_frozen_run_and_pins_the_exec_chain(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location('real_role_launcher_under_test', REPO / 'labs/ha/real_role_launcher.py')
    launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
    root, config, contract, config_file = make_run(tmp_path)
    # The repository launcher is not the run's frozen copy.
    assert launcher.main(['--contract', str(root / 'contracts/member.json'), '--instrument-config', str(config_file), 'validate'],
                         validator=validator_for(contract)) == 1
    assert 'real_instrument_refused' in capsys.readouterr().err
    installed = []
    class Probe:
        def install(self, **kw): installed.append(kw)
    real_module = launcher.instrument_module()
    guard = launcher.guarded_execve(real_module, Probe(), None)
    for path, argv in [('/bin/sh', [sys.executable]), (sys.executable, [sys.executable, '-I', '-B', '/other/daemon.py']),
                       (sys.executable, [sys.executable, str(launcher.DAEMON)])]:
        with pytest.raises(real_module.InstrumentRefused):
            guard(path, argv, dict(os.environ))
    assert installed == []


@pytest.mark.asyncio
async def test_combined_result_and_ack_loss_are_independent_one_shots(tmp_path):
    instrument, *_ = start(tmp_path, 'result-and-ack-loss')
    instrument.install(ClusterMemberOperations=FakeOperations)
    try:
        ops, channel = FakeOperations(), FakeChannel()
        ack = {'ack': {'payload': {'operation_id': OPERATION}}}
        with pytest.raises(ConnectionError): await ops.member_result(channel, {'operation_id': OPERATION})
        with pytest.raises(ConnectionError): await ops.acknowledge(channel, ack)
        await ops.member_result(channel, {'operation_id': OPERATION}); await ops.acknowledge(channel, ack)
    finally:
        instrument.uninstall()
    assert sorted(p.name for p in instrument.directory.glob('claim-*')) == ['claim-ack-delivery-loss.json', 'claim-result-reply-loss.json']
