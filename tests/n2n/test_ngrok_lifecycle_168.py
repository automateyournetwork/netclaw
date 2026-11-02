"""No account/endpoint creation: config and owned local process tests only."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

from test_endpoint_registry_168 import registry_data
from bgp.federation.endpoint_registry import Registry
from bgp.federation.runtime import Runtime

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('ngrok_control_168', ROOT/'scripts/ngrok-control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def test_exact_named_endpoints_without_transform_or_secrets(registry_data):
    config = control.render_config(registry_data)
    assert config['version'] == '3'
    assert config['agent']['web_addr'] is False
    assert config['agent']['remote_management'] is False
    endpoints = {e['name']:e for e in config['endpoints']}
    assert endpoints['members']['url'] == 'tcp://1.tcp.example.test:21001'
    assert endpoints['external']['url'] == 'tcp://1.tcp.example.test:21002'
    assert endpoints['members']['upstream']['url'] == '127.0.0.1:42101'
    serialized = json.dumps(config)
    for forbidden in ('authtoken', 'traffic_policy', 'proxy_protocol', 'agent_tls_termination', 'key_file'):
        assert forbidden not in serialized


def test_members_cannot_run_agent(registry_data):
    value = dict(registry_data, entries=[dict(registry_data['entries'][0], direction='dial')])
    with pytest.raises(ValueError): control.render_config(value)


def test_two_owned_processes_and_foreign_pid_refusal(tmp_path, registry_data, monkeypatch):
    # This test qualifies process ownership only, not a live daemon or endpoint.
    # The full config path must remain visible even on a narrow Linux terminal.
    monkeypatch.setenv('COLUMNS', '80')
    monkeypatch.setattr(control.Controller, 'verify_border_ready', lambda self: None)
    fake = tmp_path/'fake-ngrok'
    fake.write_text('#!/usr/bin/env python3\nimport time\nwhile True: time.sleep(.1)\n')
    fake.chmod(0o700)
    controllers = []
    for name in ('one', 'two'):
        home = tmp_path/name;home.mkdir(mode=0o700)
        runtime = Runtime('openclaw', home, home/'openclaw.json', name)
        runtime.fence(initialize=True)
        registry = Registry(runtime.state/'endpoints.json', name)
        registry.replace(dict(registry_data, installationId=name), expected_revision=0)
        (home/'.env').write_text('NGROK_AUTHTOKEN=fixture-only\nN2N_ROLE=border\nN2N_ENDPOINT_REGISTRY='+str(registry.path)+'\n')
        (home/'.env').chmod(0o600)
        controllers.append(control.Controller(runtime, binary=str(fake)))
    one, two = controllers
    try:
        first = one.start(); second = two.start()
        assert first['state'] == second['state'] == 'running-owned'
        assert first['pid'] != second['pid']
        one.stop()
        assert one.status()['state'] == 'stopped'
        assert two.status()['state'] == 'running-owned'
        restarted = one.start()
        assert restarted['pid'] != first['pid']
        assert one.configuration()['endpoints'] == two.configuration()['endpoints']
        record = json.loads(one.record.read_text())
        record['pid'] = second['pid']
        one.record.write_text(json.dumps(record))
        with pytest.raises(ValueError): one.stop()
        assert two.status()['state'] == 'running-owned'
        record['pid'] = restarted['pid']
        one.record.write_text(json.dumps(record))
    finally:
        for controller in controllers:
            controller.stop()


def test_environment_never_inherits_transport_token(tmp_path, monkeypatch):
    home = tmp_path/'clean';home.mkdir(mode=0o700)
    runtime = Runtime('openclaw', home, home/'openclaw.json', 'clean')
    monkeypatch.setenv('NGROK_AUTHTOKEN', 'foreign-token')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'foreign-provider-secret')
    env = control.environment(runtime)
    assert 'NGROK_AUTHTOKEN' not in env and 'ANTHROPIC_API_KEY' not in env


@pytest.mark.parametrize('action', ['register', 'import'])
def test_cli_refuses_ambiguous_json_without_writing(tmp_path, registry_data, monkeypatch, action):
    from bgp.federation.endpoint_registry import export_bundle
    home = tmp_path/'ambiguous'; home.mkdir(mode=0o700)
    runtime = Runtime('openclaw', home, home/'openclaw.json', 'ambiguous').fence(initialize=True)
    registry = Registry(runtime.state/'endpoints.json', runtime.installation)
    (home/'.env').write_text('N2N_ENDPOINT_REGISTRY='+str(registry.path)+'\n')
    (home/'.env').chmod(0o600)
    value = (dict(registry_data, installationId=runtime.installation) if action == 'register'
             else export_bundle(registry_data['entries'][0]))
    candidate = home/'candidate.json'
    candidate.write_text(json.dumps(value).replace('"routing_port": 21001',
                                                  '"routing_port": 1, "routing_port": 21001'))
    original_env = (home/'.env').read_bytes()
    monkeypatch.setattr(control, 'selected', lambda: runtime)
    monkeypatch.setattr(control.sys, 'argv', ['ngrok-control.py', action, '--file', str(candidate),
                                            '--expected-revision', '0'])
    with pytest.raises(ValueError, match='duplicate JSON key'):
        control.main()
    assert not registry.path.exists()
    assert (home/'.env').read_bytes() == original_env


@pytest.mark.parametrize('failure', ['pid', 'process', 'revision', 'listener', None])
def test_start_requires_owned_current_listener_evidence(tmp_path, registry_data, monkeypatch, failure):
    """Synthetic daemon observations; no process or public endpoint is started."""
    import io
    from bgp.federation.runtime import write_private
    home = tmp_path/'ready'; home.mkdir(mode=0o700)
    runtime = Runtime('openclaw', home, home/'openclaw.json', 'ready').fence(initialize=True)
    registry = Registry(runtime.state/'endpoints.json', 'ready')
    registry.replace(dict(registry_data, installationId='ready'), expected_revision=0)
    (home/'.env').write_text('N2N_ROLE=border\nNGROK_AUTHTOKEN=fixture-only\nN2N_ENDPOINT_REGISTRY='+str(registry.path)+'\n')
    (home/'.env').chmod(0o600)
    write_private(runtime.state/'daemon.json', {'installationId':'ready', 'pid':12345, 'started':'fixture-start'})
    monkeypatch.setattr(control, '_process', lambda pid: {
        'started':'foreign' if failure == 'process' else 'fixture-start',
        'command':str(ROOT/'mcp-servers/protocol-mcp/bgp-daemon-v2.py')})
    def response(url, **kwargs):
        value = {'pid':12346 if failure == 'pid' else 12345, 'installation_id':'ready', 'harness_type':'openclaw'}
        if url.endswith('/n2n/status'):
            projection = registry.status()
            if failure == 'revision': projection['revision'] += 1
            for entry in projection['services']: entry['listener_ready'] = failure != 'listener'
            value = {'endpoint_registry':projection}
        return io.BytesIO(json.dumps(value).encode())
    monkeypatch.setattr(control.urllib.request, 'urlopen', response)
    controller = control.Controller(runtime)
    if failure:
        def forbidden(*args, **kwargs): raise AssertionError('activation before readiness')
        monkeypatch.setattr(control.subprocess, 'Popen', forbidden)
        with pytest.raises(ValueError): controller.start()
    else:
        controller.verify_border_ready()
