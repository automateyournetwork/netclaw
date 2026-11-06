"""Host isolation, fixed expiry, provider-only projection and no replay."""
import base64
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock
import uuid
import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'labs/cloud/gcp/r06'


def module(name):
    spec = importlib.util.spec_from_file_location('r06_' + name, SOURCE / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


guard, host, secret = [module(n) for n in ('host_guard', 'render_host', 'project_secret')]
CONFIG = dict(schemaVersion=1, run_id='20261106-aabbcc', interface='ens4', quota_bytes=1024,
              rate_bits=1000000, expires_at='2026-11-07T12:00:00Z')


def write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
    path.chmod(0o600)


def test_guard_keeps_iap_export_after_expiry_and_never_forwards():
    closed = guard.rules({}, False, True, bootstrap=True).decode()
    opened = guard.rules(CONFIG, True, False).decode()
    for rules in (opened, closed):
        assert 'hook output priority -150' in rules
        assert 'ip daddr 35.235.240.0/20 tcp sport 22 ct state established accept' in rules
        assert 'chain forward { type filter hook forward priority -300; policy accept;\ndrop' in rules
        assert 'flush ruleset' not in rules
        assert 'meta skuid != { 10021, 10022, 10023 } ip daddr 169.254.169.254 tcp dport { 53, 80 } accept' in rules
        assert 'meta skuid { 10021, 10023 } ip daddr 169.254.0.0/16 drop' in rules
        assert 'meta skuid { 10021, 10022, 10023 } ip6 daddr { fe80::/10, fd20:ce::254 } drop' in rules
    assert 'quota egress { over 1024 bytes; }' in opened
    assert 'quota' not in closed
    assert 'udp sport 68 udp dport 67 accept' in closed


def test_guard_cannot_reset_consumed_quota_or_open_after_failed_shaper(tmp_path):
    calls = []
    def command(args, **kwargs):
        calls.append((args, kwargs))
        if args[:3] == ['ip', '-j', '-d']:
            return Mock(stdout=json.dumps([{'ifname': n, 'flags': ['UP']} for n in ('lo', 'ens4')]).encode(), returncode=0)
        if args[:3] == ['tc', '-j', 'qdisc']:
            return Mock(stdout=b'[]', returncode=0)
        if args[:3] == ['tc', 'qdisc', 'replace']:
            raise guard.Refused('injected_shaper_failure')
        return Mock(stdout=b'', returncode=1 if args[:2] == ['nft', 'list'] else 0)
    now = dt.datetime(2026, 11, 6, 12, tzinfo=dt.timezone.utc)
    with pytest.raises(guard.Refused, match='shaper'):
        guard.activate(CONFIG, tmp_path, command=command, now=now)
    with pytest.raises(guard.Refused, match='spent'):
        guard.activate(CONFIG, tmp_path, command=command, now=now)
    assert all(b'quota egress' not in kw.get('input', b'') for _, kw in calls)
    with pytest.raises(guard.Refused, match='unknown_active_link'):
        guard.validate_links([{'ifname': n, 'flags': ['UP']} for n in ('lo', 'ens4', 'docker0')], 'ens4')


@pytest.mark.parametrize('role', ['a', 'b'])
def test_renderer_separates_signer_gateway_and_public_edge(role):
    files = host.render(dict(schemaVersion=1, role=role, expires_at=CONFIG['expires_at']))
    for name, user, forbidden in [('federation', 'signer', 'gateway'), ('gateway', 'gateway', 'signer'),
                                   ('workspace', 'gateway', 'signer'), ('hud', 'signer', 'gateway')]:
        unit = files[f'netclaw-r06-{name}.service']
        assert f'User=netclaw-r06-{user}' in unit
        assert f'InaccessiblePaths=/var/lib/netclaw-r06-{forbidden}' in unit
        assert 'IPAddressDeny=169.254.0.0/16' in unit
        assert 'Restart=no' in unit and 'ProtectSystem=strict' in unit
        assert 'netclaw-r06-expiry.timer' in unit
    assert 'CAP_NET_BIND_SERVICE' in files['netclaw-r06-caddy.service']
    assert 'r06-' + role + '-gcp-montreal' in files['Caddyfile']
    assert 'response_header_timeout 325s' in files['Caddyfile']
    assert 'respond 404' in files['Caddyfile']
    assert '2026-11-07 12:00:00 UTC' in files['netclaw-r06-expiry.timer']
    assert files['openclaw'] == '#!/bin/sh\nexec /opt/netclaw-r06/bin/node /opt/netclaw-r06/openclaw/openclaw.mjs "$@"\n'
    assert 'MemoryMax=1024M' in files['netclaw-r06-workspace.service']
    assert 'Environment=NODE_OPTIONS=--max-old-space-size=256' in files['netclaw-r06-workspace.service']
    assert 'Environment=NETCLAW_GATEWAY_HISTORY_TIMEOUT_MS=60000' in files['netclaw-r06-workspace.service']


@pytest.fixture
def projection(tmp_path):
    home = tmp_path / 'gateway'
    (home / 'netclaw-federation').mkdir(mode=0o700, parents=True)
    home.chmod(0o700)
    installation = str(uuid.uuid4())
    write(home / 'netclaw-hud/installation.json', dict(schemaVersion=1, installationId=installation))
    payload = json.dumps(dict(schemaVersion=1, installationId=installation,
                             environment={'ANTHROPIC_API_KEY': 'sk-ant-fixture'})).encode()
    cfg = dict(schemaVersion=1, installationId=installation, home=str(home), role='a', secrets={
        'provider': dict(version='projects/netclaw-fixture/secrets/netclaw-r06-20261106-aabbcc-a/versions/1',
                         payloadSha256=hashlib.sha256(payload).hexdigest())})
    def request(url, headers):
        if url.startswith('http://169.254.'):
            return {'access_token': 'fixture-token'}
        return {'payload': {'data': base64.b64encode(payload).decode()}}
    return home, cfg, request


def test_provider_projection_is_exact_and_reentry_only_preserves_same_bytes(projection):
    home, cfg, request = projection
    values = secret.retrieve(cfg, request)
    secret.project(cfg, values)
    secret.project(cfg, values)
    path = home / 'netclaw-federation/provider.env'
    assert path.read_text() == 'ANTHROPIC_API_KEY=sk-ant-fixture\n'
    assert path.stat().st_mode & 0o777 == 0o600
    path.write_text('changed')
    with pytest.raises(secret.Refused, match='changed'):
        secret.project(cfg, values)


@pytest.mark.parametrize('fault', ['other_org', 'latest', 'other_run_digest', 'device_credential'])
def test_projection_refuses_wrong_scope(projection, fault):
    _, cfg, request = projection
    if fault == 'other_org':
        cfg['role'] = 'b'
    elif fault == 'latest':
        cfg['secrets']['provider']['version'] = cfg['secrets']['provider']['version'].replace('/1', '/latest')
    elif fault == 'other_run_digest':
        cfg['secrets']['provider']['payloadSha256'] = '0' * 64
    else:
        cfg['secrets']['netbox'] = cfg['secrets'].pop('provider')
    with pytest.raises(secret.Refused):
        secret.retrieve(cfg, request)
