#!/usr/bin/env python3
"""R09A (spec 183) OpenShell sandbox policy generator and validator. Pure functions and private-file output only.

Implements specs/183-openshell-defenseclaw-gcp/contracts/sandbox-policy.md for OpenShell 0.1.7 (schema facts verified
live on 2026-11-10): `version: 1`, `filesystem_policy`, `landlock`, `process`, `network_policies.<name>.endpoints[]` and
`binaries[]`. For `protocol: tcp` endpoints the L7 fields (enforcement, access, rules, deny_rules) are rejected by the
gateway and `tls: skip` is required so the egress proxy does not terminate TLS (it would break the TLS exporter binding
the HA channels depend on). The Anthropic endpoint stays an HTTPS endpoint with the default TLS termination because the
OpenShell provider mechanism injects the credential into the HTTP request.

  python -m labs.ha.r09a_policy render --node-spec node.json --out DIR
  python -m labs.ha.r09a_policy validate POLICY.yaml

node_spec (JSON): {"node": "nne1", "etcd": ["<inst>.<zone>.c.<project>.internal:2379", ...3], "peers": ["<inst>.<zone>.c.<project>.internal:7443"], "anthropic": true,
                   "binaries": {"python": "...", "node": "...", "defenseclaw": "..."}}   (binaries optional)
"""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sys

import yaml

POLICY_VERSION_FIELD = 1
SANDBOX_USER = 'sandbox'
READ_ONLY = ['/usr', '/lib', '/lib64', '/bin', '/sbin', '/proc', '/dev/urandom', '/etc', '/opt/nc182']
READ_WRITE = ['/sandbox', '/tmp', '/dev/null']  # the only writable locations: state and scratch
FORBIDDEN_PATHS = ('/', '/root', '/home', '/var/lib/docker', '/var/run/docker.sock', '/run/docker.sock', '/var/run', '/run', '/host')
ANTHROPIC_HOST = 'api.anthropic.com'
FORBIDDEN_HOST_NAMES = {'metadata', 'metadata.google.internal', 'metadata.goog', 'localhost', 'host.docker.internal'}
TOP_KEYS = {'version', 'filesystem_policy', 'landlock', 'process', 'network_policies'}
L7_ONLY_FIELDS = ('enforcement', 'access', 'rules', 'deny_rules')
DEFAULT_BINARIES = {'python': '/opt/nc182/venv/bin/python3.12', 'node': '/opt/nc182/node/bin/node',
                    'defenseclaw': '/usr/local/bin/defenseclaw-gateway'}
NODE_CODE = re.compile(r'^[a-z][a-z0-9]{1,15}$')
FORBIDDEN_KEYS = {'mounts', 'volumes', 'host_path', 'hostpath', 'bind', 'binds', 'devices', 'privileged', 'cap_add', 'host_network'}


class PolicyRefused(ValueError):
    """Only a fixed code is carried; no input text is echoed."""


def need(condition, code):
    if not condition:
        raise PolicyRefused(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def policy_sha256(policy):
    """Content hash of the parsed policy (comments and key order do not matter)."""
    return hashlib.sha256(canonical(policy)).hexdigest()


GCE_INTERNAL = re.compile(r'^[a-z]([a-z0-9-]{0,61}[a-z0-9])?\.[a-z][a-z0-9-]*\.c\.[a-z][a-z0-9-]*\.internal$')


def _endpoint(value, port, label):
    """`name:port` where name is a GCE zonal internal DNS name (`<instance>.<zone>.c.<project>.internal`).

    Live finding (OpenShell 0.1.7): tcp endpoints must be DNS hostnames; an IP literal is refused because direct IP
    connections bypass policy DNS. The metadata server and any non-GCE-internal name are never accepted here."""
    need(isinstance(value, str) and value.count(':') == 1, 'invalid_' + label)
    host, _, text = value.partition(':')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise PolicyRefused('tcp_endpoint_must_be_a_dns_name')
    need(GCE_INTERNAL.match(host) is not None and host not in FORBIDDEN_HOST_NAMES, 'invalid_' + label)
    need(text.isdigit() and int(text) == port, 'invalid_' + label)
    return host, port


def _binary(path):
    need(isinstance(path, str) and path.startswith('/') and '..' not in path.split('/') and len(path) <= 200
         and re.fullmatch(r'[A-Za-z0-9_./+-]+', path) is not None, 'invalid_binary')
    return {'path': path}


def check_node_spec(spec):
    need(isinstance(spec, dict) and set(spec) <= {'node', 'etcd', 'peers', 'anthropic', 'binaries'}
         and {'node', 'etcd', 'peers', 'anthropic'} <= set(spec), 'invalid_node_spec')
    need(isinstance(spec['node'], str) and NODE_CODE.match(spec['node']), 'invalid_node')
    need(isinstance(spec['etcd'], list) and len(spec['etcd']) == 3 and len(set(spec['etcd'])) == 3, 'etcd_three_voters_required')
    need(isinstance(spec['peers'], list) and len(spec['peers']) <= 2 and len(set(spec['peers'])) == len(spec['peers']), 'invalid_peers')
    need(type(spec['anthropic']) is bool, 'invalid_anthropic_flag')
    binaries = dict(DEFAULT_BINARIES)
    if 'binaries' in spec:
        need(isinstance(spec['binaries'], dict) and set(spec['binaries']) <= set(DEFAULT_BINARIES), 'invalid_binaries')
        binaries.update(spec['binaries'])
    return binaries


def build_policy(spec):
    """Deterministic policy dict for one node (`netclaw-node` sandbox)."""
    binaries = check_node_spec(spec)
    etcd = [_endpoint(item, 2379, 'etcd_endpoint') for item in spec['etcd']]
    peers = [_endpoint(item, 7443, 'peer_endpoint') for item in spec['peers']]
    policies = {
        'etcd': {'name': 'etcd-voters', 'endpoints': [
            {'host': h, 'port': p, 'protocol': 'tcp', 'tls': 'skip'} for h, p in etcd],
            'binaries': [_binary(binaries['python'])]}}
    if peers:
        policies['border-peers'] = {'name': 'border-peers', 'endpoints': [
            {'host': h, 'port': p, 'protocol': 'tcp', 'tls': 'skip'} for h, p in peers],
            'binaries': [_binary(binaries['python'])]}
    if spec['anthropic']:
        # Default TLS termination (no `tls` field): required for OpenShell to inject the provider credential.
        policies['anthropic'] = {'name': 'anthropic-api', 'endpoints': [
            {'host': ANTHROPIC_HOST, 'port': 443, 'protocol': 'https', 'enforcement': 'enforce', 'access': 'full'}],
            'binaries': [_binary(binaries['defenseclaw']), _binary(binaries['node'])]}
    policy = {'version': POLICY_VERSION_FIELD,
              'filesystem_policy': {'include_workdir': True, 'read_only': list(READ_ONLY), 'read_write': list(READ_WRITE)},
              'landlock': {'compatibility': 'hard_requirement'},
              'process': {'run_as_user': SANDBOX_USER, 'run_as_group': SANDBOX_USER},
              'network_policies': policies}
    validate_policy(render_yaml(policy))
    return policy


def render_yaml(policy):
    body = yaml.safe_dump(policy, sort_keys=False, default_flow_style=False)
    return f'# generated by labs/ha/r09a_policy.py (spec 183); content sha256: {policy_sha256(policy)}\n{body}'


def _scan_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            need(str(key).lower() not in FORBIDDEN_KEYS, 'host_mount_or_privilege_key_refused')
            _scan_keys(item)
    elif isinstance(value, list):
        for item in value:
            _scan_keys(item)


def validate_policy(text):
    """Refuse anything outside contracts/sandbox-policy.md. Returns {'sha256', 'endpoints', 'binaries'}."""
    need(isinstance(text, str) and len(text) <= 256 * 1024, 'policy_text_invalid')
    try:
        policy = yaml.safe_load(text)
    except yaml.YAMLError:
        raise PolicyRefused('policy_yaml_invalid') from None
    need(isinstance(policy, dict) and set(policy) == TOP_KEYS, 'policy_fields_invalid')
    _scan_keys(policy)
    need(type(policy['version']) is int and policy['version'] == POLICY_VERSION_FIELD, 'policy_version_invalid')
    need(policy['landlock'] == {'compatibility': 'hard_requirement'}, 'landlock_hard_requirement_required')
    need(policy['process'] == {'run_as_user': SANDBOX_USER, 'run_as_group': SANDBOX_USER}, 'process_user_invalid')
    fs = policy['filesystem_policy']
    need(isinstance(fs, dict) and set(fs) == {'include_workdir', 'read_only', 'read_write'}
         and isinstance(fs['include_workdir'], bool), 'filesystem_policy_invalid')
    for key in ('read_only', 'read_write'):
        need(isinstance(fs[key], list) and all(isinstance(p, str) and p.startswith('/') and '..' not in p.split('/') for p in fs[key]),
             'filesystem_path_invalid')
        for path in fs[key]:
            need(path.rstrip('/') not in FORBIDDEN_PATHS and not path.startswith(('/var/lib/docker', '/var/run/docker', '/run/docker')),
                 'filesystem_path_forbidden')
    need(set(fs['read_write']) <= set(READ_WRITE), 'filesystem_write_outside_state')
    need('/opt/nc182' in fs['read_only'] and not any(p == '/opt/nc182' or p.startswith('/opt/nc182/') for p in fs['read_write']),
         'frozen_source_must_be_read_only')
    networks = policy['network_policies']
    need(isinstance(networks, dict) and networks, 'network_policies_required')
    count = 0
    binaries_seen = set()
    for name, rule in networks.items():
        need(isinstance(name, str) and re.fullmatch(r'[a-z0-9-]{1,40}', name), 'network_policy_name_invalid')
        need(isinstance(rule, dict) and set(rule) == {'name', 'endpoints', 'binaries'}, 'network_policy_fields_invalid')
        need(isinstance(rule['binaries'], list) and rule['binaries'] and all(isinstance(b, dict) and set(b) == {'path'}
             for b in rule['binaries']), 'network_policy_binaries_required')
        for item in rule['binaries']:
            binaries_seen.add(_binary(item['path'])['path'])
        need(isinstance(rule['endpoints'], list) and rule['endpoints'], 'network_policy_endpoints_required')
        for endpoint in rule['endpoints']:
            need(isinstance(endpoint, dict), 'endpoint_invalid')
            host, port, protocol = endpoint.get('host'), endpoint.get('port'), endpoint.get('protocol')
            need(isinstance(host, str) and host and '*' not in host and host.lower() not in FORBIDDEN_HOST_NAMES, 'endpoint_host_forbidden')
            need(not host.startswith('169.254.') and not host.endswith('.local')
                 and (not host.endswith('.internal') or host == 'host.openshell.internal' or GCE_INTERNAL.match(host) is not None),
                 'metadata_or_internal_host_forbidden')
            need(type(port) is int and 1 <= port <= 65535, 'endpoint_port_invalid')
            if protocol == 'tcp':
                for field in L7_ONLY_FIELDS:
                    need(field not in endpoint, 'l7_fields_on_tcp_refused')
                need(set(endpoint) == {'host', 'port', 'protocol', 'tls'}, 'endpoint_fields_invalid')
                need(endpoint['tls'] == 'skip', 'tcp_endpoint_requires_tls_skip')
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    pass
                else:
                    raise PolicyRefused('tcp_endpoint_must_be_a_dns_name')
                need(GCE_INTERNAL.match(host) is not None or host == 'host.openshell.internal', 'tcp_endpoint_must_be_gce_internal_name')
            elif protocol == 'https':
                need(host == ANTHROPIC_HOST and port == 443, 'https_host_not_approved')
                need('tls' not in endpoint, 'https_endpoint_must_keep_tls_termination')
                need(set(endpoint) == {'host', 'port', 'protocol', 'enforcement', 'access'}
                     and endpoint['enforcement'] == 'enforce' and endpoint['access'] == 'full', 'endpoint_fields_invalid')
            else:
                raise PolicyRefused('endpoint_protocol_refused')
            count += 1
    return {'sha256': policy_sha256(policy), 'endpoints': count, 'binaries': sorted(binaries_seen)}


def render(spec_path, out_dir):
    spec = json.loads(Path(spec_path).read_text())
    policy = build_policy(spec)
    text = render_yaml(policy)
    summary = validate_policy(text)
    out = Path(out_dir)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name, data in (('policy.yaml', text.encode()),
                       ('policy.json', json.dumps({'node': spec['node'], **summary}, sort_keys=True, indent=2).encode())):
        fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    r = sub.add_parser('render')
    r.add_argument('--node-spec', required=True)
    r.add_argument('--out', required=True)
    v = sub.add_parser('validate')
    v.add_argument('policy')
    args = parser.parse_args(argv)
    try:
        if args.action == 'render':
            print(json.dumps(render(args.node_spec, args.out), sort_keys=True))
        else:
            print(json.dumps(validate_policy(Path(args.policy).read_text()), sort_keys=True))
        return 0
    except (PolicyRefused, OSError, ValueError, KeyError) as error:
        print('refused:' + (str(error) if isinstance(error, PolicyRefused) else type(error).__name__), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
