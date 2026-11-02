"""Direct cloud contract: local tests only; no public listener or provider calls."""
import copy
import json
import asyncio
from functools import partial

import pytest

from bgp.federation.endpoint_registry import Registry, validate, export_bundle, import_bundle
from test_endpoint_registry_168 import registry_data
from test_ngrok_lifecycle_168 import control
from test_exporter_tls_168 import material
import test_ngrok_transport_168 as security


@pytest.mark.asyncio
async def test_strict_border_refuses_disabled_internal_stack(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from bgp.federation import endpoint_registry
    daemon = security.load_entrypoint('direct_disabled_stack168', 'mcp-servers/protocol-mcp/bgp-daemon-v2.py')
    monkeypatch.setenv('N2N_ENDPOINT_REGISTRY', str(tmp_path/'registry.json'))
    monkeypatch.setattr(daemon, '_sync_risk_from_env', lambda fed: None)
    monkeypatch.setattr(endpoint_registry, 'configured', lambda **kw: object())
    fed = SimpleNamespace(risk=SimpleNamespace(get_risk=lambda: {'role':'border'}, stack_enabled=lambda stack: False))
    with pytest.raises(ValueError, match='strict Border requires enabled iN2N'):
        await daemon._start_in2n(fed)


@pytest.mark.parametrize('rows,expected', [
    ([], False),
    ([{'service':'in2n','direction':'listen','listener_ready':True}], False),
    ([{'service':s,'direction':'listen','listener_ready':s=='in2n'} for s in ('in2n','en2n')], False),
    ([{'service':s,'direction':'listen','listener_ready':True} for s in ('in2n','en2n')], True),
])
def test_strict_border_readiness_requires_both_current_listeners(tmp_path, monkeypatch, rows, expected):
    from types import SimpleNamespace
    daemon = security.load_entrypoint('direct_listener_ready168', 'mcp-servers/protocol-mcp/bgp-daemon-v2.py')
    monkeypatch.setenv('N2N_ENDPOINT_REGISTRY', str(tmp_path/'registry.json'))
    monkeypatch.setenv('N2N_ROLE', 'border')
    monkeypatch.setattr(daemon, 'N2N_ENABLED', True)
    monkeypatch.setattr(daemon, '_federation', SimpleNamespace(endpoint_status=lambda: {'services':rows}))
    assert daemon.federation_ready(SimpleNamespace(kind='openclaw')) is expected

INTERNAL_SCENARIOS = [
    ('test_strict_enrollment_reconnect_behind_loopback_forwarding', {}),
    ('test_wrong_border_anchor_refused_before_token_consumption', {}),
    ('test_cross_connection_proof_and_enrollment_replay', {}),
    ('test_member_refuses_member_admission', {}),
] + [('test_strict_identity_refusals', {'failure':failure})
     for failure in ('tls_name','ca','border_identity','altered_binding','forged_key','unknown','expired')
] + [('test_repeated_authentication_and_revoked_open_channel', {'action':action})
     for action in ('repeat','revoke')
] + [('test_revoked_member_receives_no_new_work_on_open_channel', {'operation':operation})
     for operation in ('call','notify')]


@pytest.mark.asyncio
@pytest.mark.parametrize('scenario,arguments', INTERNAL_SCENARIOS)
async def test_direct_internal_security(tmp_path, material, monkeypatch, scenario, arguments):
    # Reuse adversarial assertions, but remove the forwarder entirely and use schema2.
    monkeypatch.setattr(security, 'pair', partial(security.pair, direct=True))
    await getattr(security, scenario)(tmp_path, material, **arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [None, 'pin','name','ca','consent'])
async def test_direct_ncfed_security(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(security, 'external_pair', partial(security.external_pair, direct=True))
    if failure:
        await security.test_external_strict_trust_refusal(tmp_path, failure)
    else:
        await security.test_public_ncfed_tls_pinned_identity_and_consent(tmp_path)


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [b'\xff'*19, b'NCTUN'+b'x'*16, b'GET / HTTP/1.1\r\n\r\n', b'PROXY TCP4 x y 1 2\r\n'])
async def test_direct_ncfed_exposure_refusal(tmp_path, monkeypatch, payload):
    monkeypatch.setattr(security, 'external_pair', partial(security.external_pair, direct=True))
    await security.test_public_listener_refuses_other_protocols_without_peer_mutation(tmp_path, payload)


@pytest.mark.asyncio
async def test_direct_relocation_preserves_enrollment_without_replay(tmp_path, material, monkeypatch):
    from bgp.federation import exporter_tls, endpoint_registry, internal_security
    async with security.pair(tmp_path, material, direct=True) as (border, member, entry):
        registry = Registry(tmp_path/'transport/registry.json', 'member')
        registry.replace({'schemaVersion':2,'installationId':'member','revision':1,'entries':[entry]}, expected_revision=0)
        monkeypatch.setattr(endpoint_registry, 'configured', lambda **kw: registry)
        monkeypatch.setenv('N2N_BORDER_REGISTRY_ID', 'members')
        await security.dial(member, entry, border.risk.issue_token()['token'])
        fingerprint = border.risk.get_member('example/test')['key_fingerprint']
        await member.border_channel.close(); await asyncio.sleep(.02)
        # A different direct listener, with the same Border credentials/state.
        listener = dict(entry, direction='listen', bind_host='127.0.0.1', bind_port=42101,
                        cert_file=material['cert'], key_file=material['key'])
        async def accept(reader, writer):
            await border.accept_internal(reader, writer, registration=listener, registry_revision=1)
        replacement = await exporter_tls.start_server(accept, '127.0.0.1', 0,
                        cert_file=material['cert'], key_file=material['key'])
        try:
            border._in2n_server.close(); await border._in2n_server.wait_closed()
            with pytest.raises(ConnectionError): await security.dial(member, entry)
            registry.update_address('members', '127.0.0.1', replacement.sockets[0].getsockname()[1],
                                    'replacement-direct', expected_revision=1)
            host, port, options = internal_security.dial_options(member, 'ignored', 1)
            assert (await member.dial_border(host, port, **options))['trusted']
            assert border.risk.get_member('example/test')['key_fingerprint'] == fingerprint
            for service in (border,member):
                assert service.manager._conn.execute('SELECT COUNT(*) FROM delegated_task').fetchone()[0] == 0
        finally:
            if member.border_channel: await member.border_channel.close()
            for channel in list(border.member_channels.values()): await channel.close()
            replacement.close(); await asyncio.wait_for(replacement.wait_closed(), 3)


@pytest.fixture
def direct_data(registry_data):
    value = copy.deepcopy(registry_data)
    value['schemaVersion'] = 2
    for entry in value['entries']:
        entry.pop('reservation_id')
        entry.update(transport='direct_tcp', address_ref='provider-border-ip',
                     routing_host='border.example.test', bind_host='10.168.0.2')
    return value


def test_direct_registry_without_ngrok_dependencies(tmp_path, direct_data):
    registry = Registry(tmp_path/'direct.json', 'test-installation')
    registry.replace(direct_data, expected_revision=0)
    assert registry.load() == direct_data
    assert all(e['transport'] == 'direct_tcp' for e in registry.status()['services'])
    bundle = export_bundle(direct_data['entries'][0])
    assert bundle['schemaVersion'] == 2
    assert bundle['endpoint']['address_ref'] == 'provider-border-ip'
    for private in ('reservation_id', 'bind_host', 'key_file', 'ca_file'):
        assert private not in bundle['endpoint']
    other = Registry(tmp_path/'member'/'registry.json', 'member-installation')
    import_bundle(other, bundle, expected_revision=0)
    assert other.load()['schemaVersion'] == 2
    assert other.entry('members')['transport'] == 'direct_tcp'


@pytest.mark.parametrize('field,value', [
    ('transport', 'automatic'), ('transport', ''), ('address_ref', ''),
    ('bind_host', '0.0.0.0'), ('bind_host', '::'), ('bind_host', '224.0.0.1'),
    ('bind_host', 'ff02::1'), ('bind_host', '255.255.255.255'),
    ('bind_host', 'border.example.test'), ('bind_host', 'fe80::1%en0'),
    ('reservation_id', 'ra_unexpected'),
])
def test_direct_unsafe_or_ambiguous_registration_refused(tmp_path, direct_data, field, value):
    direct_data['entries'][0][field] = value
    registry = Registry(tmp_path/'bad.json', 'test-installation')
    with pytest.raises(ValueError):
        registry.replace(direct_data, expected_revision=0)
    assert not registry.path.exists()


def test_explicit_ngrok_v2_still_requires_loopback(direct_data):
    for entry in direct_data['entries']:
        entry.update(transport='ngrok_tcp', address_ref='ra_fixture')
    with pytest.raises(ValueError): validate(direct_data, 'test-installation')
    for entry in direct_data['entries']: entry['bind_host'] = '127.0.0.1'
    validate(direct_data, 'test-installation')
    assert len(control.render_config(direct_data)['endpoints']) == 2


def test_direct_address_change_preserves_transport_and_recovers(tmp_path, direct_data):
    registry = Registry(tmp_path/'direct.json', 'test-installation')
    registry.replace(direct_data, expected_revision=0)
    before = registry.entry('members')
    registry.update_address('members', 'replacement.example.test', 22001, 'replacement-ip', expected_revision=1)
    after = registry.entry('members')
    assert after['address_ref'] == 'replacement-ip'
    stable = lambda e: {k:v for k,v in e.items() if k not in ('routing_host','routing_port','address_ref')}
    assert stable(before) == stable(after)
    with pytest.raises(ValueError):
        registry.update_address('members', 'stale.example.test', 22002, 'stale-ip', expected_revision=1)
    registry.recover(expected_revision=2)
    assert registry.load() == dict(direct_data, revision=3)


def test_cross_schema_bundle_requires_explicit_migration(tmp_path, registry_data, direct_data):
    registry = Registry(tmp_path/'legacy.json', 'test-installation')
    registry.replace(registry_data, expected_revision=0)
    bundle = export_bundle(direct_data['entries'][0]); bundle['endpoint']['id'] = 'new-members'
    with pytest.raises(ValueError, match='schema'):
        import_bundle(registry, bundle, expected_revision=1)
    assert registry.load() == registry_data


def test_ngrok_renderer_cannot_activate_direct_or_mixed_entries(direct_data):
    with pytest.raises(ValueError, match='ngrok'):
        control.render_config(direct_data)
    direct_data['entries'][1].update(transport='ngrok_tcp', bind_host='127.0.0.1')
    with pytest.raises(ValueError, match='ngrok'):
        control.render_config(direct_data)


@pytest.mark.parametrize('action', ['start', 'stop', 'status', 'run'])
def test_direct_cli_dispatches_owned_daemon_without_token(tmp_path, direct_data, monkeypatch, action):
    from bgp.federation.runtime import Runtime
    home = tmp_path/'direct'; home.mkdir(mode=0o700)
    runtime = Runtime('openclaw', home, home/'openclaw.json', 'test-installation').fence(initialize=True)
    registry = Registry(runtime.state/'registry.json', runtime.installation)
    registry.replace(direct_data, expected_revision=0)
    (home/'.env').write_text('N2N_ROLE=border\nN2N_ENDPOINT_REGISTRY='+str(registry.path)+'\n')
    (home/'.env').chmod(0o600)
    monkeypatch.setenv('NGROK_AUTHTOKEN', 'unrelated-token')
    monkeypatch.setattr(control, 'selected', lambda: runtime)
    monkeypatch.setattr(control.sys, 'argv', ['ngrok-control.py', action])
    observed = []
    class Dispatched(Exception): pass
    def execute(binary, argv, env):
        observed.append((binary, argv, env)); raise Dispatched
    monkeypatch.setattr(control.os, 'execve', execute)
    def forbidden(*args, **kwargs): raise AssertionError('direct mode touched ngrok lifecycle')
    monkeypatch.setattr(control.Controller, action, forbidden)
    with pytest.raises(Dispatched): control.main()
    _, argv, env = observed[0]
    assert argv[-2:] == [str(control.ROOT/'scripts/federation-control.py'), action]
    assert env['OPENCLAW_HOME'] == str(home)
    assert 'NGROK_AUTHTOKEN' not in env
    assert not (runtime.state/'ngrok').exists()
