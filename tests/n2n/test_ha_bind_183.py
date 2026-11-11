"""Spec 183 (R09A): optional, default-off bind override (`listen`) in the PRIVATE ha-config.

Only the listening socket may change; the signed manifest address, dialing and TLS identity stay as signed.
"""
import asyncio
import hashlib
import json
import os
import socket
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lib'))

from bgp.federation import certs, exporter_tls  # noqa: E402
from bgp.federation import protected_contract as c  # noqa: E402
from bgp.federation.ha import config as ha_config, factory, node as node_module  # noqa: E402
from bgp.federation.ha.config import HAError, listen_address, validate_listen  # noqa: E402
import protected_role as pr  # noqa: E402

ADVERTISED = {'host': '203.0.113.9', 'port': 7444, 'server_name': 'n.example.test'}


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


# --- validator ---------------------------------------------------------------------------------

@pytest.mark.parametrize('value', [
    {'cluster': {'host': '127.0.0.1', 'port': 7443}},
    {'in2n': {'host': '0.0.0.0', 'port': 7444}},
    {'cluster': {'host': '10.0.0.5', 'port': 1}, 'in2n': {'host': '::1', 'port': 65535}},
])
def test_valid_listen_blocks_accepted(value):
    assert validate_listen(value) == value


@pytest.mark.parametrize('value', [
    {}, [], None, 'x',
    {'https': {'host': '127.0.0.1', 'port': 443}},                       # unknown service
    {'cluster': {'host': 'localhost', 'port': 7443}},                    # names are refused (no resolver)
    {'cluster': {'host': 'n.example.test', 'port': 7443}},
    {'cluster': {'host': '127.0.0.1', 'port': 0}},
    {'cluster': {'host': '127.0.0.1', 'port': 65536}},
    {'cluster': {'host': '127.0.0.1', 'port': '7443'}},
    {'cluster': {'host': '127.0.0.1', 'port': True}},
    {'cluster': {'host': '127.0.0.1'}},
    {'cluster': {'host': '127.0.0.1', 'port': 7443, 'extra': 1}},
    {'cluster': '127.0.0.1:7443'},
])
def test_malformed_listen_blocks_refused(value):
    with pytest.raises(HAError):
        validate_listen(value)


def test_listen_address_default_is_the_signed_address():
    assert listen_address(None, 'in2n', ADVERTISED) == ('203.0.113.9', 7444)
    assert listen_address({}, 'in2n', ADVERTISED) == ('203.0.113.9', 7444)
    assert listen_address({'cluster': {'host': '127.0.0.1', 'port': 7443}}, 'in2n', ADVERTISED) == ('203.0.113.9', 7444)


def test_listen_address_override_binds_only_the_listener():
    listen = {'in2n': {'host': '127.0.0.1', 'port': 18444}}
    assert listen_address(listen, 'in2n', ADVERTISED) == ('127.0.0.1', 18444)
    assert ADVERTISED == {'host': '203.0.113.9', 'port': 7444, 'server_name': 'n.example.test'}  # untouched


# --- listeners ---------------------------------------------------------------------------------

def tls_files(tmp_path):
    ca, ca_key = certs.create_risk_ca('bind-183')
    cert, key = certs.issue_cert(ca, ca_key, 'bind-183', san='n.example.test')
    out = {}
    for name, text in (('ca', ca), ('cert', cert), ('key', key)):
        path = tmp_path / name
        path.write_text(text)
        path.chmod(0o600)
        out[name] = str(path)
    return out


def cluster_node(files, listen):
    manifest = SimpleNamespace(anchor_key_id='x', nodes=[],
                               node=lambda node_id: {'endpoints': {'cluster': dict(ADVERTISED)}})
    calls = []

    async def noop():
        return None
    authority = SimpleNamespace(manifest=manifest, node_id='n1', bootstrap=lambda: None, start_renewal=noop)
    ledger_patch = node_module.OperationLedger
    node_module.OperationLedger = lambda authority: None
    try:
        node = node_module.ClusterNode(authority, private_key=None, ca_file=files['ca'], cert_file=files['cert'],
                                       key_file=files['key'], listen=listen)
    finally:
        node_module.OperationLedger = ledger_patch
    return node, calls


def test_cluster_listener_binds_the_override_not_the_signed_address(tmp_path, monkeypatch):
    files = tls_files(tmp_path)
    port = free_port()
    node, _ = cluster_node(files, {'cluster': {'host': '127.0.0.1', 'port': port}})

    async def run():
        await node.start()
        try:
            bound = node.server.sockets[0].getsockname()
            assert bound[0] == '127.0.0.1' and bound[1] == port
            # The advertised (signed) address is not bound by this process.
            with socket.socket() as probe:
                probe.settimeout(0.3)
                assert probe.connect_ex((ADVERTISED['host'], ADVERTISED['port'])) != 0
        finally:
            node.server.close()
            await node.server.wait_closed()
    asyncio.run(run())


def test_cluster_listener_default_uses_the_signed_address(tmp_path, monkeypatch):
    files = tls_files(tmp_path)
    seen = {}

    async def fake_start_server(handler, host, port, **kwargs):
        seen.update(host=host, port=port)
        return SimpleNamespace(sockets=[])
    monkeypatch.setattr(node_module.exporter_tls, 'start_server', fake_start_server)
    node, _ = cluster_node(files, None)
    asyncio.run(node.start())
    assert (seen['host'], seen['port']) == (ADVERTISED['host'], ADVERTISED['port'])


def runtime(config, monkeypatch):
    seen = {}

    async def fake_start_server(handler, host, port, **kwargs):
        seen.update(host=host, port=port)
        return SimpleNamespace(sockets=[])
    monkeypatch.setattr(factory.exporter_tls, 'start_server', fake_start_server)

    async def started():
        return None
    runtime = object.__new__(factory.HAServiceRuntime)
    runtime.operations = SimpleNamespace(start=started)
    runtime.node = SimpleNamespace(node_id='n1')
    runtime.manifest = SimpleNamespace(node=lambda node_id: {'endpoints': {'in2n': dict(ADVERTISED)}})
    runtime.config = config
    runtime.accept_internal = lambda *a: None
    runtime.server = None
    runtime.attachments = None
    return runtime, seen


@pytest.mark.parametrize('override', [None, {'in2n': {'host': '127.0.0.1', 'port': 18444}}])
def test_in2n_listener_override_and_default(override, monkeypatch):
    config = {'transport_certificate_file': '/x', 'private_key_file': '/y'}
    if override:
        config['listen'] = override
    rt, seen = runtime(config, monkeypatch)
    asyncio.run(rt.start())
    expected = ('127.0.0.1', 18444) if override else (ADVERTISED['host'], ADVERTISED['port'])
    assert (seen['host'], seen['port']) == expected


# --- private configuration loader --------------------------------------------------------------

def private_file(path, data=b'x'):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    return str(path)


def border_config(tmp_path, listen=None, **extra):
    root = tmp_path.resolve()
    files = {name: private_file(root / name) for name in
             ('manifest', 'anchor', 'transport-ca', 'tcert', 'tkey', 'etca', 'etcert', 'etkey', 'etpw')}
    value = {'schema_version': 1, 'role': 'border', 'manifest_file': files['manifest'],
             'anchor_certificate_file': files['anchor'], 'anchor_key_id': 'a' * 64,
             'transport_ca_file': files['transport-ca'], 'node_id': str(uuid.uuid4()),
             'transport_certificate_file': files['tcert'], 'private_key_file': files['tkey'],
             'etcd': {'endpoints': ['https://10.0.0.1:2379'], 'ca_file': files['etca'], 'certificate_file': files['etcert'],
                      'private_key_file': files['etkey'], 'username': 'border0', 'password_file': files['etpw']}}
    if listen is not None:
        value['listen'] = listen
    value.update(extra)
    raw = c.encode(value)
    path = private_file(root / 'ha-config.json', raw)
    return {'config_file': path, 'config_sha256': hashlib.sha256(raw).hexdigest()}, value


def test_loader_default_off_is_unchanged(tmp_path):
    ref, value = border_config(tmp_path)
    loaded = factory.load_configuration(ref, role='border')
    assert 'listen' not in loaded and loaded == value


def test_loader_accepts_valid_listen_and_refuses_bad(tmp_path):
    ref, value = border_config(tmp_path, {'cluster': {'host': '127.0.0.1', 'port': 7443},
                                          'in2n': {'host': '127.0.0.1', 'port': 7444}})
    assert factory.load_configuration(ref, role='border')['listen']['cluster']['port'] == 7443
    other = tmp_path / 'bad'
    other.mkdir()
    ref, _ = border_config(other, {'cluster': {'host': 'not-an-ip', 'port': 7443}})
    with pytest.raises(HAError):
        factory.load_configuration(ref, role='border')


def test_loader_still_refuses_unknown_fields(tmp_path):
    ref, _ = border_config(tmp_path, None, surprise=1)
    with pytest.raises(Exception):
        factory.load_configuration(ref, role='border')


def test_member_config_does_not_accept_listen(tmp_path):
    root = tmp_path.resolve()
    files = {name: private_file(root / name) for name in ('manifest', 'anchor', 'ca', 'cert', 'key')}
    value = {'schema_version': 1, 'role': 'member', 'manifest_file': files['manifest'],
             'anchor_certificate_file': files['anchor'], 'anchor_key_id': 'a' * 64, 'transport_ca_file': files['ca'],
             'certificate_file': files['cert'], 'private_key_file': files['key'],
             'listen': {'in2n': {'host': '127.0.0.1', 'port': 7444}}}
    raw = c.encode(value)
    path = private_file(root / 'ha-config.json', raw)
    with pytest.raises(Exception):
        factory.load_configuration({'config_file': path, 'config_sha256': hashlib.sha256(raw).hexdigest()}, role='member')


# --- role launcher -----------------------------------------------------------------------------

HA_FILES = ('factory.py', 'config.py', 'authority.py', 'channel.py', 'internal.py', 'member.py', 'border.py',
            'operations.py', 'admission.py', 'store.py', 'effect.py', 'mcp_transport.py', 'model_transport.py')


def launcher_fixture(tmp_path, listen):
    root = tmp_path.resolve()
    home = root / 'home'
    for sub in ('netclaw-federation', 'netclaw-hud'):
        (home / sub).mkdir(parents=True, mode=0o700)
    ref, value = border_config(root, listen)
    node_id, installation = value['node_id'], str(uuid.uuid4())
    cluster = {'cluster_id': str(uuid.uuid4()), 'generation': str(uuid.uuid4())}
    origin = 'https://n.example.test'
    manifest = {'schema': 'netclaw.ncfed.cluster-manifest.v1', 'signature': {},
                'manifest': {**cluster, 'nodes': [{'node_id': node_id, 'installation_id': installation,
                                                    'key_id': 'b' * 64, 'endpoints': {'https': origin}}]}}
    # The ha-config must reference the manifest it names; re-point and re-hash.
    value['manifest_file'] = private_file(root / 'manifest.json', c.encode(manifest))
    raw = c.encode(value)
    config_path = root / 'ha-config.json'
    os.unlink(config_path)
    private_file(config_path, raw)
    private_file(home / 'netclaw-federation/ha-required.json', c.encode({'schema_version': 1, **cluster}))
    sources = private_file(root / 'sources.json', json.dumps({'files': {
        'mcp-servers/protocol-mcp/bgp/federation/ha/' + name: 'f' * 64 for name in HA_FILES}}).encode())
    cfg = {'role': 'border', 'installation_id': installation, 'origin': origin, 'source_manifest': sources}
    profile = {'identity': {'key_id': 'b' * 64},
               'ha': {'config_file': str(config_path), 'config_sha256': hashlib.sha256(raw).hexdigest()}}
    return cfg, profile, home, root


def test_role_validator_accepts_a_valid_listen_block(tmp_path):
    cfg, profile, home, root = launcher_fixture(tmp_path, {'cluster': {'host': '127.0.0.1', 'port': 7443},
                                                           'in2n': {'host': '127.0.0.1', 'port': 7444}})
    config = pr.validate_ha_profile(cfg, profile, home, root)
    assert config['listen']['in2n']['port'] == 7444


def test_role_validator_default_off_is_unchanged(tmp_path):
    cfg, profile, home, root = launcher_fixture(tmp_path, None)
    assert 'listen' not in pr.validate_ha_profile(cfg, profile, home, root)


@pytest.mark.parametrize('bad', [
    {'cluster': {'host': 'localhost', 'port': 7443}},
    {'cluster': {'host': '127.0.0.1', 'port': 0}},
    {'cluster': {'host': '127.0.0.1', 'port': 7443, 'x': 1}},
    {'other': {'host': '127.0.0.1', 'port': 7443}},
    {},
])
def test_role_validator_refuses_a_bad_listen_block(tmp_path, bad):
    cfg, profile, home, root = launcher_fixture(tmp_path, bad)
    with pytest.raises(pr.RoleRefused):
        pr.validate_ha_profile(cfg, profile, home, root)


def test_role_validator_still_refuses_unknown_config_fields(tmp_path):
    cfg, profile, home, root = launcher_fixture(tmp_path, None)
    path = Path(profile['ha']['config_file'])
    value = json.loads(path.read_text())
    value['surprise'] = 1
    raw = c.encode(value)
    os.unlink(path)
    private_file(path, raw)
    profile['ha']['config_sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(pr.RoleRefused):
        pr.validate_ha_profile(cfg, profile, home, root)
