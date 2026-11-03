"""No network/executor seam: real local keys, attestations, token DB and journal."""
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from bgp.federation import exporter_tls, internal_channel, runtime
from bgp.federation.channel import RpcError
from bgp.federation.internal_security import channel_binding
from bgp.federation.manager import FederationManager
from bgp.federation.protected_contract import ProtectedError, key_id
from bgp.federation.protected_owner import write_private
from bgp.federation.risk import RiskManager
from bgp.federation.service import FederationService

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_enrollment_172', ROOT / 'scripts/protected-enroll.py')
native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)


@pytest.fixture
def harness(tmp_path, monkeypatch):
    # A private copy also lets the CLI's explicit env clearing be tested without
    # changing the test runner's process environment after this fixture ends.
    monkeypatch.setattr(os, 'environ', {})
    old_umask = os.umask(0o077)
    tmp_path.chmod(0o700)
    managers = []
    border_manager = FederationManager(base_dir=str(tmp_path / 'border-state'))
    managers.append(border_manager)
    border = RiskManager(border_manager)
    border.set_role('border', risk_name='r03-test', enabled_stacks='in2n')
    ca, _ = border.ensure_risk_ca(); hub, _ = border.hub_credential()
    ca_path = tmp_path / 'transport-ca.pem'; write_private(ca_path, ca.encode())
    entry = {'id': 'members', 'direction': 'dial', 'service': 'in2n',
             'profile': 'in2n-tls-exporter-v1', 'transport': 'direct_tcp',
             'address_ref': 'r03-reviewed-address', 'routing_host': '192.0.2.1',
             'routing_port': 19444, 'tls_server_name': 'r03.example.test',
             'ca_file': str(ca_path), 'application_identity': 'r03-test/border',
             'application_trust': ca}
    binding = {'installation_id': str(uuid.uuid4()), 'identity': 'r03-test/border',
               'key_id': key_id(hub), 'authority_generation': str(uuid.uuid4())}
    fixture = SimpleNamespace(tmp=tmp_path, entry=entry, binding=binding, border=border,
                              calls=[], channels=[], mode=None, service=None, require_claim=True)

    def select(home, kind='openclaw'):
        env = {'NETCLAW_RUNTIME': kind, 'HOME': str(home), 'N2N_BASE_DIR': str(home / 'n2n'),
               'N2N_PROTECTED_OPERATIONS': '1', 'N2N_CERT_MODE': 'enforce'}
        if kind == 'hermes': env['HERMES_HOME'] = str(home)
        else: env.update(OPENCLAW_HOME=str(home), OPENCLAW_STATE_DIR=str(home),
                         OPENCLAW_CONFIG_PATH=str(home / 'openclaw.json'))
        os.environ.clear(); os.environ.update(env)
        return runtime.selected(initialize=True).fence(initialize=True)

    def member(home=None, kind='openclaw'):
        chosen = select(home or tmp_path / 'member', kind)
        manager = FederationManager(base_dir=str(chosen.base)); managers.append(manager)
        service = FederationService(local_as=0, router_id='0.0.0.0', manager=manager)
        service.risk.set_role('member', risk_name='r03-test', self_member_id='r03-test/onprem', enabled_stacks='in2n')
        fixture.service = service
        return service

    class Writer:
        def __init__(self): self.closed = False
        def get_extra_info(self, name):
            return {'tls_profile': 'in2n-tls-exporter-v1', 'tls_version': 'TLSv1.3',
                    'tls_exporter': b'X' * 32, 'peername': ('192.0.2.1', 19444)}.get(name)
        def close(self): self.closed = True

    async def connect(*args, **kwargs):
        service = fixture.service
        # CLI builds its own service, so find its selected home for this assertion.
        chosen = runtime.selected()
        if fixture.require_claim:
            claim = json.loads((chosen.state / 'protected-enrollment-attempt.json').read_text())
            assert claim['state'] == 'outcome_unknown' and claim['enrollment_generation'] is None
        fixture.calls.append('connect')
        if fixture.mode == 'connect-failure': raise OSError('sensitive transport text')
        writer = Writer(); fixture.writer = writer
        return object(), writer

    class Channel:
        def __init__(self, reader, writer, **kwargs):
            self.writer, self.handlers, self.nonce = writer, kwargs['handlers'], kwargs['nonce']
            self._closed = False; fixture.channels.append(self)
        async def start(self):
            # These are the real protected service handlers throughout bootstrap.
            for name in ('n2n/tasks/submit', 'n2n/tools/call', 'execution/catalog', 'execution/submit'):
                with pytest.raises(RpcError): await self.handlers[name](self, {})
        async def call(self, method, params, **kwargs):
            fixture.calls.append(method)
            challenge = bytes.fromhex(params.get('member_nonce', '')) + channel_binding(self.writer, strict=True)
            if method == 'in2n/attest':
                result = border.attest_hub(challenge)
                if fixture.mode == 'bad-attestation': result['hub_sig'] = '00' * 64
                return {'hub_attestation': result}
            assert method == 'in2n/enroll', 'no hello/inventory/other method during one-use enrollment'
            assert border.verify_possession(params['cert_pem'], self.nonce,
                                            bytes.fromhex(params['signature']), channel_binding(self.writer, strict=True))
            result = border.consume_token(params['token'], params['member_id'], params['cert_pem'],
                                          installation_id=params['installation_id'])
            if fixture.mode == 'lost-reply': raise ConnectionError('accepted then lost ' + params['token'])
            result['risk_ca'] = ca; result['hub_attestation'] = border.attest_hub(challenge)
            if fixture.mode == 'missing-generation': result.pop('enrollment_generation')
            if fixture.mode == 'bad-final-attestation': result['hub_attestation']['hub_sig'] = '00' * 64
            return result
        async def close(self): self._closed = True; self.writer.close()

    monkeypatch.setattr(exporter_tls, 'open_connection', connect)
    monkeypatch.setattr(internal_channel, 'InternalChannel', Channel)
    monkeypatch.setattr(internal_channel, 'read_border_preamble', AsyncMock(return_value=b'N' * 32))
    fixture.member = member
    fixture.token = lambda: border.issue_token(ttl_seconds=300)['token']
    fixture.run = lambda svc, **kwargs: asyncio.run(svc.enroll_protected_member(
        registration=kwargs.pop('registration', entry), registry_revision=kwargs.pop('registry_revision', 1),
        border_binding=kwargs.pop('border_binding', binding), enrollment_token=kwargs.pop('token', fixture.token()), **kwargs))
    # Any actual runtime start is a test failure, including Hermes startup.
    monkeypatch.setattr(FederationService, 'start_runtime', AsyncMock(side_effect=AssertionError('runtime forbidden')))
    try: yield fixture
    finally:
        for manager in reversed(managers): manager.close()
        os.umask(old_umask)


@pytest.mark.parametrize('kind', ['openclaw', 'hermes'])
def test_real_local_trust_enrollment_and_closed_channel_without_execution(harness, kind):
    h = harness; service = h.member(kind=kind)
    result = h.run(service)
    assert result['state'] == 'enrolled' and result['enrollment_generation']
    saved = service.risk.protected_enrollment()
    assert saved['enrollment_generation'] == h.border.get_member('r03-test/onprem')['enrollment_generation']
    assert native.enrollment_status(service.runtime.home)['state'] == 'enrolled'
    assert h.calls == ['connect', 'in2n/attest', 'in2n/enroll']
    assert all(c._closed for c in h.channels) and service.border_channel is None
    assert service.protected_operations is None and service.execution_broker is None and service.hermes_runtime is None
    assert not (service.runtime.state / 'protected-profile.json').exists()
    assert not (service.runtime.state / 'native-operations').exists()
    assert 'token' not in json.dumps(result) and 'token_hash' not in result
    assert h.border.get_member('r03-test/onprem')['installation_id'] == service.runtime.installation


@pytest.mark.parametrize('fault', ['connect-failure', 'lost-reply', 'bad-attestation',
                                  'missing-generation', 'bad-final-attestation'])
def test_uncertain_attempt_is_never_replayed_even_after_service_restart(harness, fault):
    h = harness; service = h.member(); h.mode = fault
    with pytest.raises((ProtectedError, OSError, RuntimeError)): h.run(service)
    observed = native.enrollment_status(service.runtime.home)
    assert observed['state'] == 'outcome_unknown' and observed['replay_allowed'] is False
    assert all(c._closed for c in h.channels)
    calls = list(h.calls); h.mode = None
    restarted = h.member(home=service.runtime.home)
    with pytest.raises(ProtectedError): h.run(restarted)
    assert h.calls == calls


def test_wrong_approved_hub_key_refuses_before_token_is_transmitted(harness):
    h = harness; service = h.member()
    with pytest.raises(ProtectedError, match='protected_border_binding_refused'):
        h.run(service, border_binding=dict(h.binding, key_id='f' * 64))
    assert h.calls == ['connect', 'in2n/attest']
    assert h.border.get_member('r03-test/onprem') is None
    assert h.channels[0]._closed


@pytest.mark.parametrize('change', ['disabled', 'late-opt-in', 'border-role', 'runtime', 'active-channel', 'peer',
                                    'worker', 'profile', 'enrolled', 'anchor', 'registry',
                                    'identity', 'revision', 'token', 'foreign-state', 'invalid-member'])
def test_invalid_or_nonfresh_preconditions_make_zero_connections(harness, change):
    h = harness; service = h.member(); kwargs = {}
    if change == 'disabled': service.protected_enabled = False
    elif change == 'late-opt-in': service._protected_from_construction = False
    elif change == 'border-role': service.risk.set_role('border', risk_name='r03-test')
    elif change == 'runtime': service.protected_operations = object()
    elif change == 'active-channel': service.border_channel = object()
    elif change == 'peer': service.channels['peer'] = object()
    elif change == 'worker': service.tasks._workers['job'] = object()
    elif change == 'profile': write_private(service.runtime.state / 'protected-profile.json', b'{}')
    elif change == 'enrolled': service.risk.store_protected_enrollment({'test': True})
    elif change == 'anchor': service.risk.store_risk_anchor(h.entry['application_trust'])
    elif change == 'registry': kwargs['registration'] = dict(h.entry, transport='ngrok_tcp')
    elif change == 'identity': kwargs['border_binding'] = dict(h.binding, identity='other/border')
    elif change == 'revision': kwargs['registry_revision'] = True
    elif change == 'token': kwargs['token'] = 'invalid'
    elif change == 'foreign-state': service.manager.base_dir = str(h.tmp / 'foreign')
    elif change == 'invalid-member': service.risk.set_role('member', risk_name='r03-test', self_member_id='r03-test/')
    with pytest.raises(ProtectedError): h.run(service, **kwargs)
    assert h.calls == []
    assert not (service.runtime.state / 'protected-enrollment-attempt.json').exists()


def test_private_dial_keyword_cannot_skip_durable_claim(harness):
    h = harness; service = h.member()
    with pytest.raises(ProtectedError, match='native_enrollment_claim_required'):
        asyncio.run(service.dial_border('192.0.2.1', 19444, enrollment_token=h.token(),
             registration=h.entry, registry_revision=1, _enrollment_only={'invented': True}))
    assert not h.calls


def test_ordinary_protected_dial_cannot_resend_enrollment_token(harness):
    h = harness; service = h.member()
    with pytest.raises(ProtectedError, match='protected_native_enrollment_required'):
        asyncio.run(service.dial_border('192.0.2.1', 19444, enrollment_token=h.token(),
                                       registration=h.entry, registry_revision=1))
    assert not h.calls


@pytest.mark.parametrize('marker', ['enrollment-packet.json', 'protected-enrollment-attempt.json'])
def test_partial_bootstrap_cannot_reopen_unprotected_legacy_runtime(harness, marker):
    h = harness; service = h.member()
    write_private(service.runtime.state / marker, b'{}')
    os.environ['N2N_PROTECTED_OPERATIONS'] = '0'
    with pytest.raises(ValueError, match='protected profile requires'):
        FederationService(local_as=0, router_id='0.0.0.0', manager=service.manager)
    assert not h.calls


def test_claim_write_failure_prevents_network_and_spends_home(harness, monkeypatch):
    h = harness; service = h.member()
    monkeypatch.setattr(os, 'fsync', lambda fd: (_ for _ in ()).throw(OSError('disk unavailable')))
    with pytest.raises(OSError): h.run(service)
    assert not h.calls
    assert (service.runtime.state / 'protected-enrollment-attempt.json').exists()
    with pytest.raises(ProtectedError, match='enrollment_attempt_already_spent'): h.run(service)


def test_existing_symlink_attempt_is_not_followed_or_overwritten(harness):
    h = harness; service = h.member()
    target = h.tmp / 'preserve'; write_private(target, b'unchanged')
    (service.runtime.state / 'protected-enrollment-attempt.json').symlink_to(target)
    with pytest.raises(ProtectedError, match='enrollment_attempt_already_spent'): h.run(service)
    assert target.read_bytes() == b'unchanged' and not h.calls


def test_transport_preamble_failure_closes_socket_and_preserves_unknown(harness, monkeypatch):
    h = harness; service = h.member()
    monkeypatch.setattr(internal_channel, 'read_border_preamble', AsyncMock(side_effect=ConnectionError('dropped')))
    with pytest.raises(ConnectionError): h.run(service)
    assert h.writer.closed and not h.channels
    assert native.enrollment_status(service.runtime.home)['state'] == 'outcome_unknown'


def test_cancellation_closes_channel_and_preserves_unknown(harness, monkeypatch):
    h = harness; service = h.member()
    original = internal_channel.InternalChannel.call
    async def cancelled(self, method, params, **kwargs):
        if method == 'in2n/enroll': raise asyncio.CancelledError()
        return await original(self, method, params, **kwargs)
    monkeypatch.setattr(internal_channel.InternalChannel, 'call', cancelled)
    with pytest.raises(asyncio.CancelledError): h.run(service)
    assert h.channels[0]._closed
    assert native.enrollment_status(service.runtime.home)['state'] == 'outcome_unknown'


def test_completion_write_failure_retains_actual_generation_without_retry(harness, monkeypatch):
    h = harness; service = h.member()
    from bgp.federation import protected_owner
    original = protected_owner.write_private
    def fail_receipt(path, value):
        if Path(path).name == 'protected-enrollment-attempt.json': raise OSError('disk full')
        return original(path, value)
    monkeypatch.setattr(protected_owner, 'write_private', fail_receipt)
    with pytest.raises(OSError): h.run(service)
    status = native.enrollment_status(service.runtime.home)
    assert status['state'] == 'outcome_unknown' and status['local_generation_retained']
    assert status['enrollment_generation'] == h.border.get_member('r03-test/onprem')['enrollment_generation']
    before = list(h.calls)
    with pytest.raises(ProtectedError): h.run(service)
    assert h.calls == before


def test_concurrent_calls_share_one_durable_attempt(harness, monkeypatch):
    h = harness; service = h.member(); token = h.token()
    original = exporter_tls.open_connection
    async def delayed(*args, **kwargs):
        await asyncio.sleep(.01)  # First claim yields while seven admissions race.
        return await original(*args, **kwargs)
    monkeypatch.setattr(exporter_tls, 'open_connection', delayed)
    async def run():
        return await asyncio.gather(*[service.enroll_protected_member(registration=h.entry,
            registry_revision=1, border_binding=h.binding, enrollment_token=token) for _ in range(8)],
            return_exceptions=True)
    result = asyncio.run(run())
    assert len([x for x in result if isinstance(x, dict)]) == 1
    assert all(isinstance(x, (dict, ProtectedError)) for x in result)
    assert h.calls.count('in2n/enroll') == h.calls.count('connect') == 1


def test_existing_unprotected_enrollment_dial_is_unchanged(harness, monkeypatch):
    h = harness; seeded = h.member(); h.require_claim = False
    os.environ['N2N_PROTECTED_OPERATIONS'] = '0'
    service = FederationService(local_as=0, router_id='0.0.0.0', manager=seeded.manager)
    assert not service.protected_enabled
    # Do not invoke unprotected handlers. This case checks only legacy admission.
    monkeypatch.setattr(internal_channel.InternalChannel, 'start', AsyncMock())
    original = internal_channel.InternalChannel.call
    async def allow_inventory(self, method, params, **kwargs):
        if method == 'n2n/inventory': h.calls.append(method); return {}
        return await original(self, method, params, **kwargs)
    monkeypatch.setattr(internal_channel.InternalChannel, 'call', allow_inventory)
    async def run():
        result = await service.dial_border('192.0.2.1', 19444, enrollment_token=h.token(),
                                          registration=h.entry, registry_revision=1)
        assert service.border_channel.trusted
        await service.border_channel.close()
        return result
    assert asyncio.run(run())['enrollment_generation']
    assert h.calls == ['connect', 'in2n/attest', 'in2n/enroll', 'n2n/inventory']
    assert not (service.runtime.state / 'protected-enrollment-attempt.json').exists()


def test_protected_pinned_key_hello_does_not_reenroll(harness, monkeypatch):
    h = harness; service = h.member(); h.run(service)
    # A full profile's runtime/catalog are irrelevant until start_runtime; this
    # test never starts it. The existing hello path consumes only Border binding.
    identity = dict(service.risk.protected_enrollment(), key_id=key_id(service.risk.self_cert_pem()))
    write_private(service.runtime.state / 'protected-profile.json',
        {'schemaVersion': 1, 'role': 'member', 'identity': identity,
         'border': h.binding, 'catalog': {'member': identity, 'model_profiles': [], 'tools': []},
         'runtime': {'test_only_never_started': True}})
    h.require_claim = False; h.calls.clear()
    original = internal_channel.InternalChannel.call
    async def hello(self, method, params, **kwargs):
        if method == 'in2n/hello':
            h.calls.append(method)
            assert params['key_fingerprint'] == identity['key_id'] and 'token' not in params
            assert h.border.verify_possession(service.risk.self_cert_pem(), self.nonce,
                bytes.fromhex(params['signature']), channel_binding(self.writer, strict=True))
            return {'trusted': True, 'hub_attestation': h.border.attest_hub(
                bytes.fromhex(params['member_nonce']) + channel_binding(self.writer, strict=True))}
        if method == 'n2n/inventory': h.calls.append(method); return {}
        return await original(self, method, params, **kwargs)
    monkeypatch.setattr(internal_channel.InternalChannel, 'call', hello)
    async def run():
        result = await service.dial_border('192.0.2.1', 19444, registration=h.entry, registry_revision=1)
        assert service.border_channel.trusted and service.border_channel.protected_peer_binding == h.binding
        await service.border_channel.close()
        return result
    assert asyncio.run(run())['trusted']
    assert h.calls == ['connect', 'in2n/attest', 'in2n/hello', 'n2n/inventory']
    assert service.risk.protected_enrollment() == {k: v for k, v in identity.items() if k != 'key_id'}


@pytest.mark.parametrize('kind', ['openclaw', 'hermes'])
def test_native_helper_fresh_home_public_ca_copy_clean_env_and_readonly_status(harness, kind):
    h = harness
    packet = {'schemaVersion': 1, 'runtime_kind': kind, 'member_id': 'r03-test/onprem',
              'border': h.binding, 'registration': h.entry}
    path = h.tmp / 'packet.json'; write_private(path, packet)
    token = h.tmp / 'token'; write_private(token, (h.token() + '\n').encode())
    home = h.tmp / 'fresh-helper'
    os.environ.update(ANTHROPIC_API_KEY='must-never-be-inherited', PYATS_R02_PASSWORD='must-be-dropped',
                      PYTHONPATH='must-be-dropped', HTTPS_PROXY='must-be-dropped')
    result = asyncio.run(native.enroll(str(home), str(path), str(token)))
    assert result['state'] == 'enrolled'
    assert not any(key in os.environ for key in ('ANTHROPIC_API_KEY', 'PYATS_R02_PASSWORD', 'PYTHONPATH', 'HTTPS_PROXY'))
    registry = json.loads((home / 'netclaw-federation/member-registry.json').read_text())
    copied = Path(registry['entries'][0]['ca_file'])
    assert copied.parent == home / 'netclaw-federation' and copied.read_bytes() == Path(h.entry['ca_file']).read_bytes()
    assert len(registry['entries']) == 1 and registry['installationId'] == result['installation_id']
    assert not (home / 'netclaw-federation/protected-profile.json').exists()
    before = {str(p): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in home.rglob('*') if p.is_file()}
    calls = list(h.calls)
    assert native.enrollment_status(home) == result
    after = {str(p): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in home.rglob('*') if p.is_file()}
    assert before == after and h.calls == calls
    with pytest.raises(FileExistsError): asyncio.run(native.enroll(str(home), str(path), str(token)))
    assert h.calls == calls


def test_helper_rejects_secret_bundle_instead_of_transport_ca(harness):
    h = harness
    wrong = h.tmp / 'wrong-ca'; write_private(wrong, b'ANTHROPIC_API_KEY=sentinel')
    packet = {'schemaVersion': 1, 'runtime_kind': 'openclaw', 'member_id': 'r03-test/onprem',
              'border': h.binding, 'registration': dict(h.entry, ca_file=str(wrong))}
    path = h.tmp / 'packet.json'; write_private(path, packet)
    with pytest.raises(ProtectedError, match='transport_ca_certificate_required'): native.read_packet(path)
    assert not h.calls


def test_actual_isolated_cli_status_is_readonly_and_has_no_secret_output(harness):
    h = harness; service = h.member(); h.run(service)
    before = {str(p): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
              for p in service.runtime.home.rglob('*') if p.is_file()}
    command = [sys.executable, '-I', '-B', str(ROOT / 'scripts/protected-enroll.py'),
               '--home', str(service.runtime.home), 'status']
    result = subprocess.run(command, capture_output=True, text=True, timeout=15,
                            env={'PATH': '/usr/bin:/bin', 'ANTHROPIC_API_KEY': 'never-display-this-value'})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['state'] == 'enrolled'
    assert 'never-display-this-value' not in result.stdout + result.stderr
    after = {str(p): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
             for p in service.runtime.home.rglob('*') if p.is_file()}
    assert before == after


def test_actual_isolated_cli_sanitizes_remote_rpc_error_without_traceback(harness):
    h = harness
    packet = {'schemaVersion': 1, 'runtime_kind': 'openclaw', 'member_id': 'r03-test/onprem',
              'border': h.binding, 'registration': h.entry}
    path = h.tmp / 'packet.json'; write_private(path, packet)
    token = h.token(); token_path = h.tmp / 'token'; write_private(token_path, token.encode())
    # Real isolated CLI/env/setup/error entrypoint. Only the network admission
    # method is substituted; its untrusted RpcError deliberately echoes the token.
    bootstrap = '''import runpy,sys
from pathlib import Path
repo,home,packet,token=sys.argv[1:]
sys.path.insert(0,str(Path(repo)/'mcp-servers/protocol-mcp'))
from bgp.federation.service import FederationService
from bgp.federation.channel import RpcError
async def refused(self,**kwargs):
    raise RpcError(-32023,'REMOTE_SECRET_MARKER '+kwargs['enrollment_token'])
FederationService.enroll_protected_member=refused
script=str(Path(repo)/'scripts/protected-enroll.py')
sys.argv=[script,'--home',home,'enroll','--packet',packet,'--token-file',token]
runpy.run_path(script,run_name='__main__')
'''
    result = subprocess.run([sys.executable, '-I', '-B', '-c', bootstrap, str(ROOT),
        str(h.tmp / 'cli-error-home'), str(path), str(token_path)], capture_output=True, text=True,
        timeout=15, env={'PATH': '/usr/bin:/bin'})
    assert result.returncode == 1 and result.stdout == ''
    assert json.loads(result.stderr) == {'error': 'enrollment_unavailable', 'replay_allowed': False}
    assert all(marker not in result.stdout + result.stderr for marker in ('Traceback', 'REMOTE_SECRET_MARKER', token))
