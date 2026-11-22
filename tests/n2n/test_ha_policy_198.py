"""Spec 198 (R10): single-node loopback etcd exception and Azure private-DNS names in the sandbox policy. Offline."""
import copy
from pathlib import Path
import sys

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from labs.ha import r09a_policy as pol  # noqa: E402

SINGLE = {'node': 'nne1', 'etcd': ['host.openshell.internal:12379'], 'peers': [], 'anthropic': True,
          'resolve': {'host.openshell.internal': '127.0.0.1'}}
AZ = {'node': 'nne1', 'etcd': ['azca.r10-20261114.azure.internal:12379', 'azus.r10-20261114.azure.internal:12379',
                               'azse.r10-20261114.azure.internal:12379'],
      'peers': ['azus.r10-20261114.azure.internal:7443'], 'anthropic': True,
      'resolve': {'azca.r10-20261114.azure.internal': '10.198.1.4', 'azus.r10-20261114.azure.internal': '10.198.2.4',
                  'azse.r10-20261114.azure.internal': '10.198.3.4'}}


def test_single_node_loopback_policy_builds_and_validates():
    summary = pol.validate_policy(pol.render_yaml(pol.build_policy(SINGLE)))
    assert summary['endpoints'] >= 1


@pytest.mark.parametrize('mutate,code', [
    (lambda s: s.update(resolve={'host.openshell.internal': '10.0.0.5'}), 'single_host_loopback_required'),
])
def test_single_node_refuses_non_loopback_resolution(mutate, code):
    spec = copy.deepcopy(SINGLE); mutate(spec)
    with pytest.raises(pol.PolicyRefused) as info:
        pol.build_policy(spec)
    assert str(info.value) == code


def test_single_node_exception_is_exactly_one_etcd_endpoint_with_no_peers():
    for bad in ({'etcd': ['host.openshell.internal:12379'], 'peers': ['azus.r10-20261114.azure.internal:7443']},
                {'etcd': ['host.openshell.internal:2379']},
                {'etcd': ['host.openshell.internal:12379', 'azus.r10-20261114.azure.internal:12379']}):
        spec = {**copy.deepcopy(SINGLE), **bad, 'resolve': {'host.openshell.internal': '127.0.0.1', 'azus.r10-20261114.azure.internal': '10.198.2.4'}}
        with pytest.raises(pol.PolicyRefused):
            pol.build_policy(spec)


def test_host_openshell_internal_is_refused_as_a_peer():
    spec = {**copy.deepcopy(SINGLE), 'peers': ['host.openshell.internal:7443']}
    with pytest.raises(pol.PolicyRefused):
        pol.build_policy(spec)


def test_validator_refuses_loopback_allowance_on_any_other_port_or_address():
    policy = pol.build_policy(SINGLE)
    for rule in policy['network_policies'].values():
        for endpoint in rule['endpoints']:
            if endpoint.get('host') == 'host.openshell.internal':
                endpoint['port'] = 8443
    with pytest.raises(pol.PolicyRefused):
        pol.validate_policy(yaml.safe_dump(policy, sort_keys=False))
    policy = pol.build_policy(SINGLE)
    for rule in policy['network_policies'].values():
        for endpoint in rule['endpoints']:
            if endpoint.get('host') == 'host.openshell.internal':
                endpoint['allowed_ips'] = ['10.0.0.5/32']
    with pytest.raises(pol.PolicyRefused):
        pol.validate_policy(yaml.safe_dump(policy, sort_keys=False))


def test_azure_private_names_build_and_validate():
    summary = pol.validate_policy(pol.render_yaml(pol.build_policy(AZ)))
    assert summary['endpoints'] == 5


@pytest.mark.parametrize('host', [
    'azca.r10-2026111.azure.internal',          # short date
    'azxx.r10-20261114.azure.internal',         # unknown region code
    'azca.r10-20261114.azure.internal.evil.com',
    'azca.r10-20261114.azure.local',
    'attacker.azure.internal',
    'metadata.google.internal',
    '169.254.169.254',
])
def test_azure_name_pattern_is_exact(host):
    assert pol.cluster_host(host) is False


def test_gce_names_still_accepted_and_azure_exact_name_accepted():
    assert pol.cluster_host('nc183-border-a.northamerica-northeast1-c.c.netclaw-506315.internal')
    assert pol.cluster_host('azca.r10-20261114.azure.internal')


# --- spec 198 cross-group federation egress -------------------------------------------------------------------------
FED = {**copy.deepcopy(AZ), 'federation_peers': ['nne1-b0be28.automateyournetwork.com:7445', 'ew1-06dadd.automateyournetwork.com:7445']}
FED['resolve'] = {**AZ['resolve'], 'nne1-b0be28.automateyournetwork.com': '34.152.26.37', 'ew1-06dadd.automateyournetwork.com': '34.38.73.4'}


def test_federation_peers_get_exact_public_slash32_python_only_egress():
    policy = pol.build_policy(FED)
    rule = policy['network_policies']['federation-peers']
    assert [(e['host'], e['port'], e['allowed_ips']) for e in rule['endpoints']] == [
        ('nne1-b0be28.automateyournetwork.com', 7445, ['34.152.26.37/32']), ('ew1-06dadd.automateyournetwork.com', 7445, ['34.38.73.4/32'])]
    assert len(rule['binaries']) == 1
    assert pol.validate_policy(pol.render_yaml(policy))['endpoints'] > pol.validate_policy(pol.render_yaml(pol.build_policy(AZ)))['endpoints']


@pytest.mark.parametrize('mutate,code', [
    (lambda s: s.update(federation_peers=['nne1-b0be28.automateyournetwork.com:7444']), 'invalid_federation_endpoint'),
    (lambda s: s.update(federation_peers=['evil.example.com:7445']), 'invalid_federation_endpoint'),
    (lambda s: s.update(federation_peers=['*.automateyournetwork.com:7445']), 'invalid_federation_endpoint'),
    (lambda s: s.update(federation_peers=['34.152.26.37:7445']), 'invalid_federation_endpoint'),
    (lambda s: s['resolve'].update({'nne1-b0be28.automateyournetwork.com': '10.0.0.9'}), 'federation_resolve_must_be_public'),
    (lambda s: s['resolve'].update({'nne1-b0be28.automateyournetwork.com': '169.254.169.254'}), 'federation_resolve_must_be_public'),
    (lambda s: s['resolve'].update({'nne1-b0be28.automateyournetwork.com': '127.0.0.1'}), 'federation_resolve_must_be_public'),
    (lambda s: s['resolve'].pop('nne1-b0be28.automateyournetwork.com'), 'resolve_missing'),
])
def test_federation_egress_refuses_names_ports_and_non_public_addresses(mutate, code):
    spec = copy.deepcopy(FED); mutate(spec)
    with pytest.raises(pol.PolicyRefused) as info:
        pol.build_policy(spec)
    assert str(info.value) == code


def test_validator_refuses_a_hand_edited_federation_rule_with_a_private_or_wrong_port_endpoint():
    policy = pol.build_policy(FED)
    for field, value in (('allowed_ips', ['10.0.0.1/32']), ('port', 8443)):
        broken = copy.deepcopy(policy)
        broken['network_policies']['federation-peers']['endpoints'][0][field] = value
        with pytest.raises(pol.PolicyRefused):
            pol.validate_policy(pol.render_yaml(broken))
