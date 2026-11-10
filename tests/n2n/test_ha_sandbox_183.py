"""Spec 183 (R09A): sandbox policy generator, node image context and DefenseClaw sidecar tooling. Offline, no docker."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from labs.ha import r09a_defenseclaw as dc  # noqa: E402
from labs.ha import r09a_image as image  # noqa: E402
from labs.ha import r09a_policy as pol  # noqa: E402

SPEC = {'node': 'nne1', 'etcd': ['nc183-border-a.northamerica-northeast1-c.c.netclaw-506315.internal:12379', 'nc183-border-b.northamerica-northeast1-c.c.netclaw-506315.internal:12379', 'nc183-witness.northamerica-northeast1-c.c.netclaw-506315.internal:12379'],
        'peers': ['nc183-border-b.northamerica-northeast1-c.c.netclaw-506315.internal:7443'], 'anthropic': True,
        'resolve': {'nc183-border-a.northamerica-northeast1-c.c.netclaw-506315.internal': '10.183.2.2', 'nc183-border-b.northamerica-northeast1-c.c.netclaw-506315.internal': '10.183.2.3', 'nc183-witness.northamerica-northeast1-c.c.netclaw-506315.internal': '10.183.2.4'}}


def refused(code, text):
    with pytest.raises(pol.PolicyRefused) as info:
        pol.validate_policy(text)
    assert str(info.value) == code


def dump(policy):
    return yaml.safe_dump(policy, sort_keys=False)


def test_build_is_deterministic_and_validates():
    first, second = pol.build_policy(SPEC), pol.build_policy(copy.deepcopy(SPEC))
    assert pol.render_yaml(first) == pol.render_yaml(second)
    summary = pol.validate_policy(pol.render_yaml(first))
    assert summary['sha256'] == pol.policy_sha256(first) and summary['endpoints'] == 5


def test_hash_ignores_comments_and_key_order_but_not_content():
    policy = pol.build_policy(SPEC)
    reordered = dict(reversed(list(policy.items())))
    assert pol.policy_sha256(reordered) == pol.policy_sha256(policy)
    other = copy.deepcopy(policy)
    other['network_policies']['etcd']['endpoints'][0]['port'] = 2380
    assert pol.policy_sha256(other) != pol.policy_sha256(policy)


def test_tcp_peers_carry_tls_skip_and_no_l7_fields():
    policy = pol.build_policy(SPEC)
    for key in ('etcd', 'border-peers'):
        for endpoint in policy['network_policies'][key]['endpoints']:
            assert endpoint['protocol'] == 'tcp' and endpoint['tls'] == 'skip'
            assert not set(endpoint) & set(pol.L7_ONLY_FIELDS)


def test_anthropic_keeps_default_tls_termination_for_provider_injection():
    anthropic = pol.build_policy(SPEC)['network_policies']['anthropic']['endpoints'][0]
    assert anthropic['host'] == 'api.anthropic.com' and anthropic['protocol'] == 'rest' and 'tls' not in anthropic
    assert 'anthropic' not in pol.build_policy({**SPEC, 'anthropic': False})['network_policies']


def test_metadata_server_and_unlisted_hosts_are_absent():
    text = pol.render_yaml(pol.build_policy(SPEC))
    assert '169.254' not in text and 'metadata' not in text and '*' not in text.replace('# ', '')
    policy = pol.build_policy(SPEC)
    hosts = {e['host'] for rule in policy['network_policies'].values() for e in rule['endpoints']}
    assert hosts == {'nc183-border-a.northamerica-northeast1-c.c.netclaw-506315.internal', 'nc183-border-b.northamerica-northeast1-c.c.netclaw-506315.internal', 'nc183-witness.northamerica-northeast1-c.c.netclaw-506315.internal', 'api.anthropic.com'}


def test_landlock_hard_requirement_and_process_user():
    policy = pol.build_policy(SPEC)
    assert policy['landlock'] == {'compatibility': 'hard_requirement'}
    assert policy['process'] == {'run_as_user': 'sandbox', 'run_as_group': 'sandbox'}
    assert policy['filesystem_policy']['read_write'] == ['/sandbox', '/tmp', '/dev/null']
    assert '/opt/nc182' in policy['filesystem_policy']['read_only']


@pytest.mark.parametrize('mutate,code', [
    (lambda p: p['landlock'].update(compatibility='best_effort'), 'landlock_hard_requirement_required'),
    (lambda p: p['process'].update(run_as_user='root'), 'process_user_invalid'),
    (lambda p: p['filesystem_policy']['read_write'].append('/opt/nc182'), 'filesystem_write_outside_state'),
    (lambda p: p['filesystem_policy']['read_write'].append('/var/run/docker.sock'), 'filesystem_path_forbidden'),
    (lambda p: p['filesystem_policy']['read_only'].append('/var/run/docker.sock'), 'filesystem_path_forbidden'),
    (lambda p: p['filesystem_policy']['read_only'].remove('/opt/nc182'), 'frozen_source_must_be_read_only'),
    (lambda p: p['filesystem_policy'].update(mounts=['/:/host']), 'host_mount_or_privilege_key_refused'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].update(enforcement='enforce'), 'l7_fields_on_tcp_refused'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].update(access='full'), 'l7_fields_on_tcp_refused'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].update(tls='terminate'), 'tcp_endpoint_requires_tls_skip'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].pop('tls'), 'endpoint_fields_invalid'),
    (lambda p: p['network_policies']['anthropic']['endpoints'][0].update(tls='skip'), 'https_endpoint_must_keep_tls_termination'),
    (lambda p: p['network_policies']['anthropic']['endpoints'][0].update(host='example.com'), 'https_host_not_approved'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].update(host='169.254.169.254'), 'metadata_or_internal_host_forbidden'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].update(host='metadata.google.internal'), 'endpoint_host_forbidden'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].update(host='*'), 'endpoint_host_forbidden'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].update(host='8.8.8.8'), 'tcp_endpoint_must_be_a_dns_name'),
    (lambda p: p['network_policies']['etcd']['endpoints'][0].update(protocol='udp'), 'endpoint_protocol_refused'),
    (lambda p: p['network_policies']['etcd'].update(binaries=[]), 'network_policy_binaries_required'),
    (lambda p: p.update(extra=1), 'policy_fields_invalid'),
    (lambda p: p.update(version=2), 'policy_version_invalid'),
    (lambda p: p.update(network_policies={}), 'network_policies_required'),
])
def test_every_refusal(mutate, code):
    policy = copy.deepcopy(pol.build_policy(SPEC))
    mutate(policy)
    refused(code, dump(policy))


def test_invalid_node_specs_refused():
    bad = [{**SPEC, 'etcd': SPEC['etcd'][:1]}, {**SPEC, 'node': 'Bad Node'}, {**SPEC, 'anthropic': 'yes'},
           {**SPEC, 'etcd': ['nc183-border-a.northamerica-northeast1-c.c.netclaw-506315.internal:12379', 'nc183-border-b.northamerica-northeast1-c.c.netclaw-506315.internal:12379', '8.8.8.8:12379']},
           {**SPEC, 'etcd': ['nc183-border-a.northamerica-northeast1-c.c.netclaw-506315.internal:12379', 'nc183-border-b.northamerica-northeast1-c.c.netclaw-506315.internal:12379', '169.254.169.254:12379']},
           {**SPEC, 'peers': ['nc183-border-b.northamerica-northeast1-c.c.netclaw-506315.internal:7444']}, {**SPEC, 'peers': ['a', 'b', 'c']}, {**SPEC, 'binaries': {'x': '/bin/x'}},
           {**SPEC, 'binaries': {'python': 'relative/python'}}, {'node': 'nne1'}]
    for spec in bad:
        with pytest.raises(pol.PolicyRefused):
            pol.build_policy(spec)


def test_garbage_policy_text_refused():
    refused('policy_yaml_invalid', 'a: [unclosed')
    refused('policy_fields_invalid', 'just a string')
    refused('policy_text_invalid', 'x' * (300 * 1024))


def test_policy_render_cli_writes_private_files(tmp_path):
    spec_file = tmp_path / 'spec.json'
    spec_file.write_text(json.dumps(SPEC))
    assert pol.main(['render', '--node-spec', str(spec_file), '--out', str(tmp_path / 'out')]) == 0
    assert oct((tmp_path / 'out' / 'policy.yaml').stat().st_mode & 0o777) == '0o600'
    assert pol.main(['validate', str(tmp_path / 'out' / 'policy.yaml')]) == 0
    assert pol.main(['render', '--node-spec', str(spec_file), '--out', str(tmp_path / 'out')]) == 2  # fresh dir only


def test_image_context_has_pinned_versions_checks_and_no_secrets(tmp_path):
    report = image.build_context(tmp_path / 'ctx')
    text = (tmp_path / 'ctx' / 'Dockerfile').read_text()
    assert 'FROM python:3.12-slim' in text and f'NODE_VERSION={image.NODE_VERSION}' in text
    assert 'openclaw@' in text and image.OPENCLAW_VERSION in text and '--ignore-scripts' in text
    assert f'DEFENSECLAW_VERSION={image.DEFENSECLAW_VERSION}' in text and 'sha256sum -c' in text
    assert f'groupadd -g {image.SANDBOX_UID} sandbox' in text and 'USER sandbox' in text
    assert 'SHASUMS256.txt' in text
    assert image.SECRET_LIKE.search(text) is None
    for name in ('freeze_image.py', '.dockerignore'):
        assert image.SECRET_LIKE.search((tmp_path / 'ctx' / name).read_text()) is None
    assert report['versions'] == {'node': '24.22.2', 'openclaw': '2026.7.1-2', 'defenseclaw': '1.0.4'}
    assert set(report['missing_inputs']) == set(image.INPUT_NAMES)
    assert '*.env' in (tmp_path / 'ctx' / '.dockerignore').read_text()


def test_image_context_freezes_trees_and_records_input_hashes(tmp_path):
    source, manifest = tmp_path / 's.tar', tmp_path / 'm.json'
    source.write_bytes(b'tar'), manifest.write_text('{}')
    report = image.build_context(tmp_path / 'ctx', {'source.tar': source, 'source-manifest.json': manifest}, require_inputs=True)
    assert report['files']['inputs/source.tar'] == hashlib.sha256(b'tar').hexdigest()
    freeze = (tmp_path / 'ctx' / 'freeze_image.py').read_text()
    assert 'freeze_tree' in freeze and 'env_manifest' in freeze and "'symlinks'" in freeze and 'npm' in freeze
    compile(freeze, 'freeze_image.py', 'exec')


def test_image_context_refusals(tmp_path):
    with pytest.raises(ValueError, match='required_inputs_missing'):
        image.build_context(tmp_path / 'a', {}, require_inputs=True)
    with pytest.raises(ValueError, match='unknown_input_refused'):
        image.build_context(tmp_path / 'b', {'evil.env': tmp_path})
    with pytest.raises(ValueError, match='base_image_invalid'):
        image.build_context(tmp_path / 'c', base_image='python:3.12; rm -rf /')
    with pytest.raises(ValueError, match='secret_in_build_context_refused'):
        image.assert_no_secrets('ANTHROPIC_API_KEY=sk-ant-abcdefghijk')
    (tmp_path / 'd').mkdir()
    with pytest.raises(FileExistsError):
        image.build_context(tmp_path / 'd')


QUALIFIED = dc.QUALIFIED_GUARD_CONFIG


@pytest.mark.skipif(not QUALIFIED.is_file(), reason='qualified R04A guard config not present on this host')
def test_defenseclaw_config_is_the_qualified_file_byte_for_byte(tmp_path):
    raw = dc.render_config()
    assert raw == QUALIFIED.read_bytes() and hashlib.sha256(raw).hexdigest() == dc.QUALIFIED_GUARD_CONFIG_SHA256
    text = raw.decode()
    for line in ('  mode: action\n', '  hook_fail_mode: closed\n', '  scanner_mode: local\n', '  detection_strategy: regex_only\n'):
        assert line in text
    assert dc.main(['render', '--out', str(tmp_path / 'dc')]) == 0
    assert (tmp_path / 'dc' / 'guard-config.yaml').read_bytes() == raw


def test_defenseclaw_refuses_pin_mismatch_missing_and_inline_key(tmp_path):
    changed = tmp_path / 'g.yaml'
    changed.write_text('config_version: 9\nllm:\n  api_key: sk-ant-abcdefghijklmnop\n')
    with pytest.raises(dc.DefenseClawRefused, match='qualified_guard_config_changed'):
        dc.render_config(changed)
    with pytest.raises(dc.DefenseClawRefused, match='qualified_guard_config_missing'):
        dc.render_config(tmp_path / 'absent.yaml')


def test_sidecar_spec_and_export_plan_carry_no_secrets():
    spec = dc.sidecar_spec('nne1')
    assert spec['mode'] == 'action' and spec['fail_closed'] is True and spec['inside_sandbox'] is True
    assert spec['listen']['guardrail_proxy'] == '127.0.0.1:4000' and spec['start'] == ['defenseclaw-gateway', 'start']
    assert dc.SECRET_LIKE.search(json.dumps(spec).encode()) is None
    plan = dc.export_plan('nne1', '/var/tmp/export')
    assert plan['steps'][0]['source'] == '/sandbox/.defenseclaw/audit.db'
    with pytest.raises(dc.DefenseClawRefused):
        dc.sidecar_spec('Bad')
    with pytest.raises(dc.DefenseClawRefused):
        dc.export_plan('nne1', 'relative/../x')


@pytest.mark.skipif(not QUALIFIED.is_file(), reason='qualified R04A guard config not present on this host')
def test_node_config_differs_from_qualified_only_by_the_listed_deviations():
    qualified, node = dc.render_config().decode().splitlines(), dc.render_node_config().decode().splitlines()
    removed = [line for line in qualified if line not in node]
    added = [line for line in node if line not in qualified]
    assert sorted(removed) == sorted(['data_dir: /guard', '  base_url: http://127.0.0.1:18888', '    base_url: http://127.0.0.1:18888',
                                      '  forward_custom_headers: false', '    forward_custom_headers: false'])
    assert sorted(added) == sorted(['  forward_custom_headers: true', '    forward_custom_headers: true', 'data_dir: /sandbox/.defenseclaw'])
    assert 'mode: action' in dc.render_node_config().decode() and 'hook_fail_mode: closed' in dc.render_node_config().decode()


def test_only_the_guard_binary_may_reach_the_provider():
    spec = {'node': 'nne1', 'etcd': ['a.z.c.p.internal:12379', 'b.z.c.p.internal:12379'], 'peers': [], 'anthropic': True,
            'resolve': {'a.z.c.p.internal': '10.0.0.2', 'b.z.c.p.internal': '10.0.0.3'}}
    policy = pol.build_policy(spec)
    assert policy['network_policies']['anthropic']['binaries'] == [{'path': '/usr/local/bin/defenseclaw-gateway'}]
