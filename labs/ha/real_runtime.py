"""Bounded coordinator runner for REAL R08 qualification, never a fixture.

Every mutating phase is explicit and one-shot. Import/help performs no runtime
action. Preparation requires a reviewed source map and the matching fixture gate.
Public R05 artifacts may be read; its homes, model namespace and secrets are not
adopted. The production role launcher, factory and guarded executor do the work.
"""
import argparse
import copy
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import time
import uuid
from types import SimpleNamespace

from .real_budget import (Budget, LIMITS, RehearsalRefused, canonical, digest, need,
                          private_directory, publish_new, read_private, sha_value, uuid_value,
                          validate_claim, write_new)


def hashed_file(path, expected, *, private=False, maximum=128 * 1024 * 1024):
    sha_value(expected)
    path = Path(path).absolute()
    need(path == path.resolve(), 'artifact_symlink_refused')
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_uid in (0, os.getuid()) and not info.st_mode & 0o022
         and info.st_size <= maximum and info.st_nlink == 1, 'artifact_file_refused')
    raw = read_private(path, maximum) if private else path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == expected, 'artifact_changed')
    return raw


def safe_relative(value):
    need(isinstance(value, str) and value and not value.startswith('/') and '\\' not in value
         and all(p not in ('', '.', '..') for p in value.split('/')), 'source_path_refused')
    return value


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pin_protocol_source(source):
    """Do not compute a profile against another already-imported source closure."""
    directory = Path(source) / 'mcp-servers/protocol-mcp'
    for name, module in list(sys.modules.items()):
        if name == 'bgp' or name.startswith('bgp.'):
            filename = getattr(module, '__file__', None)
            need(filename and Path(filename).resolve().is_relative_to(directory), 'mixed_source_process_refused')
    sys.path.insert(0, str(directory))


def validate_plan(plan):
    fields = {'schema_version', 'root', 'run_id', 'name', 'source_root', 'source_files', 'source_sha256',
              'fixture_gate_file', 'fixture_gate_sha256', 'template_file', 'template_sha256',
              'python', 'ports', 'guard_token_variable'}
    need(isinstance(plan, dict) and set(plan) == fields and type(plan['schema_version']) is int
         and plan['schema_version'] == 1, 'invalid_real_plan')
    uuid_value(plan['run_id'])
    need(isinstance(plan['name'], str) and re.fullmatch('netclaw-r08-[a-z0-9-]{6,48}', plan['name']), 'invalid_owned_name')
    for key in ('root', 'source_root', 'fixture_gate_file', 'template_file'):
        p = Path(plan[key]); need(p.is_absolute() and p == p.resolve(), 'absolute_owned_path_required')
    need(not Path(plan['root']).is_relative_to(Path(plan['source_root']))
         and not Path(plan['source_root']).is_relative_to(Path(plan['root'])), 'separate_source_required')
    files = plan['source_files']
    need(isinstance(files, dict) and 1 <= len(files) <= 20000, 'source_bound_exceeded')
    for path, expected in files.items(): safe_relative(path); sha_value(expected)
    need(digest(files) == plan['source_sha256'], 'source_map_changed')
    sha_value(plan['fixture_gate_sha256']); sha_value(plan['template_sha256'])
    python = plan['python']
    need(isinstance(python, dict) and set(python) == {'executable', 'sha256', 'environment', 'manifest_file', 'manifest_sha256'},
         'invalid_python_plan')
    for key in ('executable', 'environment', 'manifest_file'):
        need(Path(python[key]).is_absolute(), 'absolute_python_path_required')
    sha_value(python['sha256']); sha_value(python['manifest_sha256'])
    need(plan['guard_token_variable'] == 'DEFENSECLAW_GATEWAY_TOKEN', 'invalid_guard_variable')
    ports = plan['ports']
    need(isinstance(ports, dict) and set(ports) == {'cluster', 'in2n', 'https', 'edge', 'bgp', 'api'}, 'invalid_ports')
    flat = []
    for key, values in ports.items():
        need(isinstance(values, list) and len(values) == (4 if key == 'api' else 3)
             and all(type(p) is int and 1024 <= p <= 65535 for p in values), 'invalid_ports')
        flat.extend(values)
    need(len(set(flat)) == len(flat), 'duplicate_port')
    return plan


def verify_fixture_gate(plan):
    gate = json.loads(hashed_file(plan['fixture_gate_file'], plan['fixture_gate_sha256'], private=True))
    need(gate.get('schema_version') == 1 and gate.get('class') == 'FIXTURE' and gate.get('passed') is True
         and gate.get('source_sha256') == plan['source_sha256'], 'fixture_gate_required')
    return gate


def freeze_source(plan, root):
    verify_fixture_gate(plan)
    source = Path(plan['source_root']); destination = root / 'source'
    # Check the complete reviewed input before writing the first source file.
    total = 0
    for name, expected in plan['source_files'].items():
        raw = hashed_file(source / name, expected); total += len(raw)
        need(total <= 512 * 1024 * 1024, 'source_byte_bound_exceeded')
    private_directory(destination, create=True)
    for name, expected in plan['source_files'].items():
        path = destination / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        for parent in path.parents:
            if parent == destination: break
            os.chmod(parent, 0o700)
        write_new(path, hashed_file(source / name, expected))
        os.chmod(path, 0o500 if os.access(source / name, os.X_OK) else 0o400)
    for directory, _, _ in os.walk(destination, topdown=False): os.chmod(directory, 0o500)
    manifest = {'schemaVersion': 1, 'files': plan['source_files']}
    write_new(root / 'source-manifest.json', manifest)
    return destination


def copy_model_store(source, destination):
    """Fresh copies only, with no writes/hardlinks into the retained artifact."""
    source, destination = Path(source), Path(destination)
    need(source.is_absolute() and source == source.resolve(), 'model_source_refused')
    private_directory(destination, create=True)
    total, count = 0, 0
    for directory, dirs, files in os.walk(source, followlinks=False):
        relative = Path(directory).relative_to(source)
        need(not Path(directory).is_symlink() and all(not (Path(directory) / d).is_symlink() for d in dirs), 'model_symlink_refused')
        target = destination / relative; target.mkdir(mode=0o700, exist_ok=True)
        for name in files:
            src = Path(directory) / name; info = src.lstat()
            need(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o222 and info.st_nlink == 1
                 and info.st_uid in (0, os.getuid()), 'model_source_refused')
            total += info.st_size; count += 1
            need(total <= 2 * 1024**3 and count <= 32, 'model_artifact_bound')
            # Stream the large public blobs rather than allocating their contents.
            fd = os.open(target / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with src.open('rb') as inp, os.fdopen(fd, 'wb') as out:
                shutil.copyfileobj(inp, out, 1024 * 1024); out.flush(); os.fsync(out.fileno())
            os.chmod(target / name, 0o400)
    for directory, _, _ in os.walk(destination, topdown=False): os.chmod(directory, 0o500)


def prepare(plan_file):
    """Private files only. No Docker/daemon/provider/native client starts here."""
    plan = validate_plan(json.loads(read_private(plan_file, 8 * 1024 * 1024)))
    verify_fixture_gate(plan)
    template = json.loads(hashed_file(plan['template_file'], plan['template_sha256'], private=True))
    runtime = template.get('runtime', template)
    need(runtime.get('mcp', {}).get('kind') == 'subnet_summary' and runtime.get('ollama', {}).get('family') == 4,
         'qualified_native_template_required')
    root = private_directory(plan['root'], create=True)
    write_new(root / 'reviewed-plan.json', plan)
    Budget(root, run_id=plan['run_id'], create=True)
    source = freeze_source(plan, root)
    pin_protocol_source(source)
    from bgp.federation import protected_ollama as model
    from bgp.federation.protected_mcp import validate_binding
    model.verify_store(runtime['ollama'])
    validate_binding(runtime['mcp'], check_files=True)
    artifacts = private_directory(root / 'artifacts', create=True)
    copy_model_store(runtime['ollama']['model_store'], artifacts / 'models')
    new_model = dict(runtime['ollama'], model_store=str(artifacts / 'models'))
    model.verify_store(new_model)
    guard = copy.deepcopy(runtime['guard'])
    write_new(artifacts / 'guard-config.yaml', hashed_file(guard['config_file'], guard['config_sha256'], private=True))
    guard['config_file'] = str(artifacts / 'guard-config.yaml')
    # This is the only guard.env creation. The old env_file is never opened.
    token = secrets.token_urlsafe(32)
    write_new(artifacts / 'guard.env', (plan['guard_token_variable'] + '=' + token + '\n').encode())
    guard['env_file'] = str(artifacts / 'guard.env')
    write_new(artifacts / 'guard-capability', token.encode())
    mcp = copy.deepcopy(runtime['mcp'])
    native = private_directory(artifacts / 'native-subnet', create=True)
    for name, expected in mcp['source_sha256'].items():
        safe_relative(name); target = native / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        write_new(target, hashed_file(Path(mcp['source_root']) / name, expected))
        os.chmod(target, 0o400)
    for directory, _, _ in os.walk(native, topdown=False): os.chmod(directory, 0o500)
    mcp['source_root'] = str(native)
    skill = private_directory(artifacts / 'subnet-calculator', create=True) / 'SKILL.md'
    write_new(skill, hashed_file(mcp['skill']['path'], mcp['skill']['sha256']))
    os.chmod(skill, 0o400); mcp['skill']['path'] = str(skill)
    # Python's already-verified immutable public environment is reused read-only.
    runtime = copy.deepcopy(runtime)
    runtime.update(state_dir=str(root / 'homes/member/netclaw-federation/runtime'),
                   guard_token_env='NETCLAW_R08_GUARD_TOKEN', guard=guard, mcp=mcp, ollama=new_model)
    write_new(root / 'runtime-template.json', runtime)
    write_new(root / 'tool-template.json', template['tool'])
    from .etcd_lab import EtcdLab
    lab = EtcdLab(root / 'voters').prepare()
    need(not set(lab.document['ports']) & {port for ports in plan['ports'].values() for port in ports},
         'voter_runtime_port_collision')
    prepare_identity(plan, root, lab)
    write_new(root / 'prepared.json', {'schema_version': 1, 'run_id': plan['run_id'],
              'source_sha256': plan['source_sha256'], 'class': 'PREPARATION', 'model_calls': 0, 'native_effects': 0})
    return {'prepared': True, 'root': str(root), 'class': 'PREPARATION'}


def prepare_identity(plan, root, lab):
    from cryptography.hazmat.primitives import serialization
    from bgp.federation import protected_contract as c
    from bgp.federation.ha.config import sign_manifest
    from .etcd_lab import certificate
    identity = private_directory(lab.root / 'cluster-identity', create=True)
    anchor_key, anchor = certificate(identity, 'root')
    nodes = []
    for i in range(3):
        _, cert = certificate(identity, f'node{i}', issuer_key=anchor_key, issuer=anchor, names=('localhost',))
        pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        nodes.append({'node_id': str(uuid.uuid4()), 'installation_id': str(uuid.uuid4()),
            'identity': plan['name'] + f'-border{i}', 'key_id': c.key_id(pem), 'certificate': pem, 'role': 'border',
            'endpoints': {**{k: {'host': '127.0.0.1', 'port': plan['ports'][k][i], 'server_name': 'localhost'}
                            for k in ('cluster', 'in2n')},
                          'https': f'https://localhost:{plan["ports"]["https"][i]}',
                          'wss': f'wss://localhost:{plan["ports"]["https"][i]}/mobile/ws'}})
    value = {'schema_version': 1, 'cluster_id': lab.document['cluster_id'], 'generation': lab.document['generation'],
             'organization': plan['name'], 'revision': 1, 'nodes': nodes,
             'limits': {'leader_lease_s': 12, 'renewal_s': 3, 'admission_ms': 3000,
                        'clock_uncertainty_ms': 250, 'max_operations': 1024, 'max_members': 32}}
    write_new(identity / 'manifest.json', sign_manifest(value, read_private(identity / 'root.key').decode()))
    certificate(identity, 'member', issuer_key=anchor_key, issuer=anchor, names=('localhost',))
    lab.prepare_cluster_transport()
    https = private_directory(root / 'https-pki', create=True)
    key, cert = certificate(https, 'https-ca')
    for i in range(3): certificate(https, f'border{i}', issuer_key=key, issuer=cert, names=('localhost', '127.0.0.1'))


class Rehearsal:
    def __init__(self, root):
        self.root = private_directory(root)
        self.plan = validate_plan(json.loads(read_private(self.root / 'reviewed-plan.json', 8 * 1024 * 1024)))
        need(str(self.root) == self.plan['root'], 'run_root_changed')
        self.budget = Budget(self.root, run_id=self.plan['run_id'])
        self.source = self.root / 'source'
        need(Path(__file__).resolve() == self.source / 'labs/ha/real_runtime.py', 'run_frozen_source_required')
        actual = {str(p.relative_to(self.source)) for p in self.source.rglob('*') if p.is_file() or p.is_symlink()}
        need(actual == set(self.plan['source_files']), 'frozen_source_closure_changed')
        for name, expected in self.plan['source_files'].items():
            hashed_file(self.source / name, expected)
            need(not (self.source / name).stat().st_mode & 0o222, 'frozen_source_writable')
        self.model = load_module('netclaw_r08_model_qualification', self.source / 'labs/ollama/qualify.py')

    def model_args(self):
        runtime = json.loads(read_private(self.root / 'runtime-template.json'))
        return SimpleNamespace(docker=runtime['docker'], docker_host=runtime['docker_host'],
            state_dir=str(self.root / 'model'), owner_spec=179, owner_name=self.plan['name'],
            image=runtime['ollama']['model_image'], model_store=runtime['ollama']['model_store'],
            name=self.plan['name'] + '-model', family=4, guard_uid=os.getuid(), model_uid=21006)

    def start_model(self):
        verify_fixture_gate(self.plan)
        write_new(self.root / 'model-start.claim.json', {'run_id': self.plan['run_id']})
        return self.model.prepare(self.model_args())

    def materialize(self):
        """Freeze exact observed model identity into profile2 and role schema3."""
        pin_protocol_source(self.source)
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.config import verify_manifest
        from bgp.federation.ha.internal import border_binding
        from bgp.federation.manager import FederationManager
        from bgp.federation.risk import RiskManager
        from bgp.federation.protected_docker import revision_bindings
        self.model.inspect(self.model_args())
        runtime = json.loads(read_private(self.root / 'runtime-template.json'))
        runtime['ollama'] = json.loads(read_private(self.root / 'model/profile.json'))
        bindings = revision_bindings(runtime)
        runtime['model_profile'].update({k: bindings[k] for k in ('guard_policy_sha256', 'profile_revision')})
        identity = self.root / 'voters/cluster-identity'; transport = self.root / 'voters/cluster-transport'
        anchor = read_private(identity / 'root.crt').decode()
        manifest = verify_manifest(read_private(identity / 'manifest.json'), anchor, expected_key_id=c.key_id(anchor))
        credential = json.loads(read_private(self.root / 'voters/credentials.json'))
        voter = json.loads(read_private(self.root / 'voters/owned.json'))
        homes = private_directory(self.root / 'homes', create=True)
        contracts = private_directory(self.root / 'contracts', create=True)
        member_cert = read_private(identity / 'member.crt').decode()
        member = {'installation_id': str(uuid.uuid4()), 'member_id': self.plan['name'] + '/subnet',
                  'key_id': c.key_id(member_cert), 'enrollment_generation': str(uuid.uuid4())}
        tool = json.loads(read_private(self.root / 'tool-template.json'))
        need(tool['tool'] == 'subnet_calculator' and tool['arguments'] == {'cidr': '192.0.2.0/26'}
             and tool['limits'] == {'inference_timeout_ms': 60000, 'tool_timeout_ms': 30000, 'max_inference_calls': 2,
                                   'max_tool_calls': 1, 'max_output_bytes': 262144}, 'reviewed_tool_changed')
        tool['tool_schema_sha256'] = bindings['tool_schema_sha256']
        catalog = {'member': member, 'model_profiles': [runtime['model_profile']], 'tools': [tool]}
        c.validate_catalog_entry(catalog)
        for i, name in enumerate(('border0', 'border1', 'border2', 'member')):
            role = 'member' if i == 3 else 'border'; binding = member if i == 3 else border_binding(manifest, manifest.nodes[i]['node_id'])
            home = private_directory(homes / name, create=True)
            for child in ('n2n', 'netclaw-federation', 'netclaw-hud'): private_directory(home / child, create=True)
            state = home / 'netclaw-federation'
            write_new(home / 'netclaw-hud/installation.json', {'schemaVersion': 1, 'installationId': binding['installation_id']})
            write_new(state / 'owner.json', {'schemaVersion': 1, 'installationId': binding['installation_id'], 'kind': 'openclaw', 'home': str(home)})
            write_new(state / 'ha-required.json', {'schema_version': 1, **manifest.audience})
            old_umask = os.umask(0o077)
            try:
                manager = FederationManager(base_dir=str(home / 'n2n'))
                risk = RiskManager(manager)
                risk.set_role(role, risk_name=self.plan['name'], enabled_stacks='in2n', self_member_id=member['member_id'] if i == 3 else None)
                write_new(home / 'n2n/keys/self.crt', read_private(identity / ('member.crt' if i == 3 else f'node{i}.crt')))
                write_new(home / 'n2n/keys/self.key', read_private(identity / ('member.key' if i == 3 else f'node{i}.key')))
                manager._conn.close()
            finally: os.umask(old_umask)
            config = {'schema_version': 1, 'role': role, 'manifest_file': str(identity / 'manifest.json'),
                      'anchor_certificate_file': str(identity / 'root.crt'), 'anchor_key_id': c.key_id(anchor),
                      'transport_ca_file': str(transport / 'transport-ca.crt')}
            if i == 3:
                config.update(certificate_file=str(identity / 'member.crt'), private_key_file=str(identity / 'member.key'))
                write_new(state / 'guard-capability', read_private(self.root / 'artifacts/guard-capability'))
                profile = {'schemaVersion': 2, 'role': role, 'identity': binding, 'catalog': catalog, 'runtime': runtime}
            else:
                write_new(state / 'etcd-password', credential[name].encode())
                pki = self.root / 'voters/pki'
                config.update(node_id=manifest.nodes[i]['node_id'], transport_certificate_file=str(transport / f'node{i}.crt'),
                    private_key_file=str(transport / f'node{i}.key'), etcd={
                    'endpoints': [f'https://127.0.0.1:{port}' for port in voter['ports']],
                    'ca_file': str(pki / 'client-ca.crt'), 'certificate_file': str(pki / f'border{i}.crt'),
                    'private_key_file': str(pki / f'border{i}.key'), 'username': name, 'password_file': str(state / 'etcd-password')})
                profile = {'schemaVersion': 2, 'role': role, 'identity': binding, 'access': {'mode': 'open-lab'}}
                write_new(home / 'openclaw.json', {'netclaw': {'controlOnly': True}})
                write_new(state / 'protected-operator.env',
                          ('NETCLAW_PROTECTED_OPERATOR_TOKEN=' + secrets.token_urlsafe(32) + '\n').encode())
            write_new(state / 'ha-config.json', config)
            profile['ha'] = {'config_file': str(state / 'ha-config.json'), 'config_sha256': digest(config)}
            write_new(state / 'protected-profile.json', profile)
            python = self.plan['python']
            env = {'NETCLAW_LOCAL_AS': str(65179 + i), 'NETCLAW_ROUTER_ID': f'127.0.0.{i + 1}',
                   'N2N_DISPLAY_NAME': self.plan['name'] + '-' + name, 'BGP_API_PORT': str(self.plan['ports']['api'][i]),
                   'N2N_INVENTORY_REFRESH_S': '0'}
            if i < 3:
                env['N2N_EDGE_WS_PORT'] = str(self.plan['ports']['edge'][i])
                env['BGP_LISTEN_PORT'] = str(self.plan['ports']['bgp'][i])
            contract = {'schemaVersion': 3, 'installation_id': binding['installation_id'], 'role': role,
                'runtime_kind': 'openclaw', 'control_only': i < 3, 'home': str(home), 'source_root': str(self.source),
                'python': python['executable'], 'python_sha256': python['sha256'], 'python_env': python['environment'],
                'python_env_manifest': python['manifest_file'], 'python_env_manifest_sha256': python['manifest_sha256'],
                'source_manifest': str(self.root / 'source-manifest.json'),
                'source_manifest_sha256': hashlib.sha256(read_private(self.root / 'source-manifest.json', 8 * 1024 * 1024)).hexdigest(),
                'profile_sha256': digest(profile), 'origin': None if i == 3 else manifest.nodes[i]['endpoints']['https'], 'environment': env}
            if i == 3: contract['guard_token_file'] = str(state / 'guard-capability')
            write_new(contracts / (name + '.json'), contract)
        write_new(self.root / 'member.json', {'binding': member, 'certificate': member_cert})
        for name in ('border0', 'border1', 'border2', 'member'): self.validate_role(name)
        write_new(self.root / 'materialized.json', {'schema_version': 1, 'profile_kind': 2, 'launch_schema': 3,
                                                  'manifest_sha256': c.sha256(manifest.value), 'member': member})
        return {'materialized': True, 'member': member}

    def validate_role(self, name):
        need(name in ('border0', 'border1', 'border2', 'member'), 'role_not_owned')
        module = load_module('netclaw_r08_role', self.source / 'scripts/lib/protected_role.py')
        return module.validate(self.root / 'contracts' / (name + '.json'))

    def start_coordination(self):
        """Provision the fresh consensus/member record before any runtime starts.

        The initial enrollment uses the same authority CAS implementation. Its
        short provisioning lease expires without renewal; daemons subsequently
        campaign with distinct incarnations. No runtime command is dispatched.
        """
        pin_protocol_source(self.source)
        from .etcd_lab import EtcdLab
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.config import verify_manifest
        from bgp.federation.ha.authority import Authority
        from bgp.federation.ha.operations import OperationLedger
        verify_fixture_gate(self.plan)
        member = json.loads(read_private(self.root / 'member.json'))
        write_new(self.root / 'coordination-start.claim.json', {'run_id': self.plan['run_id']})
        lab = EtcdLab(self.root / 'voters').load(); lab.start()
        identity = lab.root / 'cluster-identity'
        anchor = read_private(identity / 'root.crt').decode()
        manifest = verify_manifest(read_private(identity / 'manifest.json'), anchor, expected_key_id=c.key_id(anchor))
        store = lab.store(0)
        try:
            authority = Authority(store, manifest, manifest.nodes[0]['node_id'])
            authority.bootstrap(create=True)
            need(authority.campaign(), 'initial_enrollment_authority_unavailable')
            OperationLedger(authority).enroll_member(member['binding'], member['certificate'])
            record = {'schema_version': 1, 'member': member['binding'], 'provisioning_epoch': authority.epoch,
                      'lease_renewed': False, 'execution_dispatches': 0}
            write_new(self.root / 'coordination-ready.json', record)
            return record
        finally: store.close()

    def start_role(self, name):
        self.validate_role(name)
        claim = self.root / (name + '-start.claim.json')
        write_new(claim, {'run_id': self.plan['run_id'], 'role': name, 'at_ms': int(time.time() * 1000)})
        log = self.root / (name + '-daemon.log')
        fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        argv = [self.plan['python']['executable'], '-I', '-B', str(self.source / 'scripts/protected-role.py'),
                '--contract', str(self.root / 'contracts' / (name + '.json')), 'run']
        try:
            with os.fdopen(fd, 'wb') as stream:
                process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                    cwd=self.root / 'homes' / name, env={'PATH': '/usr/bin:/bin', 'HOME': str(self.root / 'homes' / name)}, start_new_session=True)
        except BaseException:
            write_new(self.root / (name + '-start.unknown.json'), {'state': 'outcome_unknown'}); raise
        write_new(self.root / (name + '-spawn.json'), {'pid': process.pid, 'argv': argv})
        return {'spawned_pid': process.pid, 'ready': False}

    def operator(self, node, method, params):
        need(node in ('border0', 'border1', 'border2') and method in ('catalog', 'prepare', 'decision', 'status', 'reconcile', 'cluster.info'),
             'operator_method_refused')
        state = self.root / 'homes' / node / 'netclaw-federation'
        info = json.loads(read_private(state / 'protected-operator.json'))
        profile = json.loads(read_private(state / 'protected-profile.json'))
        need(info.get('installationId') == profile['identity']['installation_id'] and type(info.get('port')) is int
             and 1024 <= info['port'] <= 65535, 'operator_identity_changed')
        token_file = read_private(state / 'protected-operator.env').decode()
        match = re.fullmatch('NETCLAW_PROTECTED_OPERATOR_TOKEN=([A-Za-z0-9_-]{43,128})\n?', token_file)
        need(match, 'operator_credential_invalid')
        request = canonical({'method': method, 'params': params})
        need(len(request) <= 1024 * 1024, 'operator_request_bound')
        connection = http.client.HTTPConnection('127.0.0.1', info['port'], timeout=15)
        try:
            connection.request('POST', '/operator', request, {'Authorization': 'Bearer ' + match[1], 'Content-Type': 'application/json'})
            response = connection.getresponse(); raw = response.read(1024 * 1024 + 1)
            need(len(raw) <= 1024 * 1024, 'operator_response_bound')
            value = json.loads(raw)
            need(response.status == 200 and value.get('ok') is True, 'operator_refused')
            return value['result']
        finally: connection.close()

    def context(self, node):
        profile = json.loads(read_private(self.root / 'homes' / node / 'netclaw-federation/protected-profile.json'))
        manifest = json.loads(read_private(self.root / 'voters/cluster-identity/manifest.json'))['manifest']
        return {'access_mode': 'open-lab', 'installation_id': profile['identity']['installation_id'],
                'cluster_id': manifest['cluster_id'], 'generation': manifest['generation']}

    def prepare_review(self, node):
        context = self.context(node)
        catalog = self.operator(node, 'catalog', {'auth_context': context})
        expected = json.loads(read_private(self.root / 'member.json'))['binding']
        entries = [entry for entry in catalog['members'] if entry['member'] == expected]
        need(len(entries) == 1, 'real_member_missing')
        entry = entries[0]
        need(len(entry['model_profiles']) == 1 and len(entry['tools']) == 1, 'ambiguous_real_catalog')
        nonce = str(uuid.uuid4())
        # Claim creation before the first prepare: unknown creation is not retried.
        write_new(self.root / ('prepare-' + nonce + '.claim.json'), {'node': node, 'client_nonce': nonce})
        dto = self.operator(node, 'prepare', {'auth_context': context, 'client_nonce': nonce,
            'catalog_revision': catalog['revision'], 'member_id': expected['member_id'],
            'model_profile_id': entry['model_profiles'][0]['profile_id'], 'tool': 'subnet_calculator',
            'arguments': {'cidr': '192.0.2.0/26'}})
        need(dto['client_nonce'] == nonce and dto['state'] == 'review_pending', 'review_not_pending')
        write_new(self.root / ('review-' + dto['operation_id'] + '.json'), dto)
        return dto

    def publish_claim(self, review_file, surface, destination):
        review = json.loads(read_private(review_file))
        self.validate_review(review)
        claim = self.budget.reserve(operation_id=review['operation_id'], client_nonce=review['client_nonce'],
                                    review_digest=review['review_digest'], surface=surface)
        self.budget.claim_send(claim, surface=surface)
        # File creation is the handoff: the allocated client is the sole sender.
        # Losing publication is unresolved and never reassigns another sender.
        publish_new(destination, claim)
        return {'claim_id': claim['claim_id'], 'surface': surface, 'claim_file': str(destination)}

    def approve_once(self, node, review_file):
        review = json.loads(read_private(review_file))
        self.validate_review(review)
        claim = self.budget.reserve(operation_id=review['operation_id'], client_nonce=review['client_nonce'],
                                    review_digest=review['review_digest'], surface='runner')
        self.budget.claim_send(claim, surface='runner')
        write_new(self.root / ('claim-' + claim['claim_id'] + '.json'), claim)
        try:
            dto = self.operator(node, 'decision', {'auth_context': self.context(node), 'operation_id': claim['operation_id'],
                'revision': review['revision'], 'review_digest': claim['review_digest'], 'decision': 'approve'})
            write_new(self.root / ('approval-' + claim['operation_id'] + '.json'), dto)
            return {'claim': claim, 'operation': dto}
        except BaseException as error:
            evidence = self._pre_dispatch_refusal_evidence(node, claim) if (
                isinstance(error, RehearsalRefused) and str(error) == 'operator_refused') else None
            if evidence: self.budget.refused(claim, evidence_sha256=evidence)
            else: self.budget.unknown(claim['claim_id'])
            raise

    def _pre_dispatch_refusal_evidence(self, node, claim):
        """Only a definitive operator refusal followed by an independent status read proving the
        original review was never dispatched may release the active slot. Any doubt stays unknown."""
        try:
            dto = self.operator(node, 'status', {'auth_context': self.context(node), 'operation_id': claim['operation_id']})
            if (dto.get('state') == 'review_pending' and dto.get('attempt_count') == 0
                    and dto.get('may_have_executed') is False and dto.get('reconciliation_required') is False):
                return hashlib.sha256(canonical({'node': node, 'status': dto})).hexdigest()
        except BaseException:
            return None
        return None

    def validate_review(self, review):
        uuid_value(review['operation_id']); sha_value(review['review_digest'])
        need(digest(review['review']) == review['review_digest'] and review['state'] == 'review_pending'
             and 'approve' in review['allowed_actions'] and type(review['revision']) is int and review['revision'] > 0,
             'original_pending_review_required')
        profile = json.loads(read_private(self.root / 'homes/member/netclaw-federation/protected-profile.json'))
        manifest = json.loads(read_private(self.root / 'voters/cluster-identity/manifest.json'))['manifest']
        value = review['review']; limits = value['limits']
        need(value['member'] == profile['identity'] and value['model_profile'] == profile['catalog']['model_profiles'][0]
             and value['tool_call'] == {k: v for k, v in profile['catalog']['tools'][0].items() if k != 'limits'}
             and {k: limits[k] for k in limits if k != 'expires_at_ms'} == profile['catalog']['tools'][0]['limits']
             and 0 < limits['expires_at_ms'] - int(time.time() * 1000) <= 180000
             and value['cluster']['cluster_id'] == manifest['cluster_id']
             and value['cluster']['generation'] == manifest['generation'], 'review_scope_changed')

    def attachment_status(self):
        state = self.root / 'homes/member/netclaw-federation'
        value = json.loads(read_private(state / 'member-daemon-status.json'))
        owner = json.loads(read_private(state / 'daemon.json'))
        member = json.loads(read_private(self.root / 'member.json'))['binding']
        stamp = subprocess.check_output(['ps', '-p', str(owner['pid']), '-o', 'lstart='], text=True).strip()
        need(value.get('installation_id') == owner.get('installationId') == member['installation_id']
             and value.get('pid') == owner.get('pid') and stamp == owner.get('started')
             and 0 <= time.time() - value['observed_at'] <= 10 and value.get('authenticated') is True
             and value.get('attachments') == 3, 'three_real_attachments_required')
        return value

    def export_operation(self, claim_file, destination):
        """Verify the original signatures and measured native artifacts, then settle.

        Signed terminal failures can be exported, but do not release the budget's
        single active slot. Missing results/ACKs use export_unknown instead.
        """
        pin_protocol_source(self.source)
        from .etcd_lab import EtcdLab
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.config import verify_manifest
        from bgp.federation.ha.internal import border_binding
        from bgp.federation.ha.operations import operation_key
        claim = json.loads(read_private(claim_file))
        validate_claim(claim, operation_id=claim['operation_id'], client_nonce=claim['client_nonce'],
            review_digest=claim['review_digest'], surface=claim['surface'], run_id=self.plan['run_id'])
        reservation = [r for r in self.budget.snapshot()['reservations'] if r['claim'] == claim]
        need(len(reservation) == 1 and reservation[0]['state'] in ('send_claimed', 'unknown'), 'budget_claim_not_sent')
        lab = EtcdLab(self.root / 'voters').load(); store = lab.store(0)
        try: row, revision = store.read(operation_key(claim['operation_id']))
        finally: store.close()
        need(row and row['client_nonce'] == claim['client_nonce'] and row['review_digest'] == claim['review_digest']
             and row['ack'] and row.get('ack_delivered') is True, 'original_ack_required')
        member_home = self.root / 'homes/member'
        database = member_home / 'n2n/federation.db'
        read_private(database, 32 * 1024 * 1024)
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            native_row = db.execute("SELECT * FROM protected_operation WHERE side='member' AND operation_id=?", (claim['operation_id'],)).fetchone()
            need(native_row is not None, 'native_original_operation_required')
            native = dict(native_row)
        for key in ('receipt', 'approval', 'ack', 'tool_evidence', 'audit_refs'):
            native[key] = json.loads(native[key]) if native[key] is not None else None
        need(native['receipt'] and native['ack'] == row['ack'] and native['approval'] == row['approval']
             and native['attempt_id'] == row['attempt_id'] and native['state'] == 'acknowledged', 'native_ack_not_retained')
        identity = lab.root / 'cluster-identity'; anchor = read_private(identity / 'root.crt').decode()
        manifest = verify_manifest(read_private(identity / 'manifest.json'), anchor, expected_key_id=c.key_id(anchor))
        issuer = manifest.node(row['review']['cluster']['issuer_node_id'])
        approval = c.verify(row['approval'], issuer['certificate'], c.HA_APPROVAL)
        receipt = c.verify(native['receipt'], row['trust_snapshot']['member'], c.HA_RESULT)
        accepting_node = manifest.node(row['ack']['payload']['acceptance']['node_id'])
        ack = c.verify(row['ack'], accepting_node['certificate'], c.HA_ACK)
        receipt_digest = c.digest(c.HA_RESULT, receipt)
        need(c.digest(c.HA_APPROVAL, approval) == row['approval_digest'] == receipt['approval_sha256']
             and c.sha256(c.review_from_payload(approval)) == claim['review_digest']
             and all(receipt[k] == row['review'][k] for k in ('principal', 'border', 'member', 'model_profile', 'cluster'))
             and receipt['operation_id'] == claim['operation_id'] and receipt['attempt_id'] == row['attempt_id']
             and receipt['approval_id'] == row['approval_id']
             and receipt['tool_call_sha256'] == c.sha256(row['review']['tool_call'])
             and receipt_digest == native['receipt_digest'] == row['result_ref']['digest'] == ack['receipt_sha256']
             and receipt['tool_evidence_sha256'] == c.sha256(native['tool_evidence'])
             and receipt['output_sha256'] == c.sha256(receipt['output'])
             and all(ack[k] == receipt[k] for k in ('operation_id', 'approval_id', 'attempt_id', 'receipt_id', 'border', 'member', 'cluster'))
             and ack['acceptance']['border'] == border_binding(manifest, accepting_node['node_id']), 'signed_evidence_changed')
        runtime = member_home / 'netclaw-federation/runtime'
        inference_db = runtime / 'inference.sqlite'
        read_private(inference_db, 32 * 1024 * 1024)
        with sqlite3.connect(inference_db.as_uri() + '?mode=ro', uri=True) as db:
            calls = db.execute('SELECT ordinal,request_sha256,state,response_sha256 FROM protected_inference WHERE operation_id=? ORDER BY ordinal',
                              (claim['operation_id'],)).fetchall()
            total_inferences = db.execute('SELECT count(*) FROM protected_inference').fetchone()[0]
        need(len(calls) <= 2 and total_inferences <= 20 and native['effect_claimed'] in (0, 1), 'observed_budget_exceeded')
        artifacts = {}
        operation_root = runtime / claim['operation_id']
        for name in ('containment.json', 'cleanup.json', 'ollama-accounting.json', 'tool/mcp-schema.json',
                     'tool/mcp-call.json', 'tool/native-mcp-result.json', 'tool/mcp-result.json', 'tool/tool-evidence.json'):
            path = operation_root / name
            if path.exists(): artifacts[name] = json.loads(read_private(path, 1024 * 1024))
        finished = receipt['outcome'] == 'succeeded' and receipt['effect_status'] == 'finished'
        if finished:
            need(len(calls) == 2 and all(r[2] == 'finished' for r in calls) and native['effect_finished'] == 1
                 and native['tool_evidence'] == artifacts.get('tool/tool-evidence.json')
                 and native['tool_evidence']['mcp_calls'] == 1
                 and native['tool_evidence']['independent_verification'] is True
                 and native['tool_evidence']['native_result_sha256'] == c.sha256(artifacts['tool/native-mcp-result.json'])
                 and not artifacts.get('cleanup.json', {}).get('unresolved', ['missing']), 'real_native_evidence_incomplete')
        export = private_directory(destination, create=True)
        from .real_evidence import execution_evidence
        counters = execution_evidence(self.root, claim['operation_id'])
        write_new(export / 'execution-evidence.json', counters)
        for name, value in {'original-approval.json': row['approval'], 'original-member-result.json': native['receipt'],
                            'successor-ack.json': row['ack'], 'cluster-ledger.json': row, 'member-ledger.json': native,
                            'measured-artifacts.json': artifacts}.items(): write_new(export / name, value)
        gait = {}
        for role in ('border0', 'border1', 'border2', 'member'):
            path = self.root / 'homes' / role / 'n2n/gait'
            if not (path / '.git').is_dir(): continue
            head = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
            trail = subprocess.check_output(['git', '-C', str(path), 'show', head + ':federation-events.jsonl'])
            need(len(trail) <= 8 * 1024 * 1024 and trail == (path / 'federation-events.jsonl').read_bytes(), 'gait_uncommitted')
            write_new(export / (role + '-gait.jsonl'), trail)
            gait[role] = {'head': head, 'sha256': hashlib.sha256(trail).hexdigest()}
        need('member' in gait and ('border' + str(manifest.nodes.index(accepting_node))) in gait, 'attributable_gait_required')
        # Verify references actually name commits containing this operation and
        # this principal; a plausible SHA or an unrelated GAIT HEAD is insufficient.
        for role, ref in [('member', receipt['audit_refs'][key]) for key in ('dispatch', 'result')] + [
                ('border' + str(manifest.nodes.index(accepting_node)), ack['audit_ref'])] + ([
                ('member', receipt['audit_refs']['effect'])] if finished else []):
            need(isinstance(ref, str) and re.fullmatch('[a-f0-9]{40}', ref), 'gait_reference_required')
            path = self.root / 'homes' / role / 'n2n/gait'
            trail = subprocess.check_output(['git', '-C', str(path), 'show', ref + ':federation-events.jsonl'], timeout=10)
            need(len(trail) <= 8 * 1024 * 1024, 'gait_export_bound')
            event = json.loads(trail.splitlines()[-1])
            need(event['protected']['operation_id'] == claim['operation_id']
                 and event['protected']['principal'] == receipt['principal'], 'gait_reference_mismatch')
        packet = {'schema_version': 1, 'class': 'REAL', 'run_id': self.plan['run_id'], 'claim': claim,
                  'source_sha256': self.plan['source_sha256'], 'receipt_sha256': receipt_digest,
                  'original_issuer_node_id': issuer['node_id'], 'ack_node_id': accepting_node['node_id'],
                  'etcd_revision': revision, 'inference_claims': [list(r) for r in calls],
                  'claimed_native_effects': native['effect_claimed'], 'finished_native_effects': native['effect_finished'],
                  'observed_total_inference_claims': total_inferences, 'gait': gait, 'successful_native_workload': finished,
                  'actual_effect_totals': counters['actual_effect_totals'],
                  'full_matrix_qualified': False}
        write_new(export / 'packet.json', packet)
        if finished:
            self.budget.settle(claim, receipt_sha256=receipt_digest, inferences=len(calls), native_effects=1)
        else: self.budget.unknown(claim['claim_id'])
        write_new(export / 'budget-after.json', self.budget.snapshot())
        return {'packet_file': str(export / 'packet.json'), 'receipt_sha256': receipt_digest, 'successful_native_workload': finished}

    def _consensus_evidence(self):
        from .etcd_lab import EtcdLab
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.config import HAError, verify_manifest
        from bgp.federation.ha.recovery import export_snapshot
        lab = EtcdLab(self.root / 'voters').load()
        identity = lab.root / 'cluster-identity'
        anchor = read_private(identity / 'root.crt').decode()
        manifest = verify_manifest(read_private(identity / 'manifest.json'), anchor, expected_key_id=c.key_id(anchor))
        store = lab.store(0)
        try:
            return {'available': True, 'snapshot': export_snapshot(store, manifest),
                    'consistency': 'single_linearizable_prefix_read'}
        except HAError as exc:
            return {'available': False, 'reason': exc.code}
        finally:
            store.close()

    def export_unknown(self, claim_file, destination):
        """Retain unresolved evidence without requiring or inventing result/ACK.

        This is not successful reconciliation. The one active budget slot stays
        unknown even if export fails. No execution or consensus mutation occurs.
        """
        pin_protocol_source(self.source)
        from .real_evidence import execution_evidence, observation, table_rows
        claim = json.loads(read_private(claim_file))
        validate_claim(claim, operation_id=claim['operation_id'], client_nonce=claim['client_nonce'],
            review_digest=claim['review_digest'], surface=claim['surface'], run_id=self.plan['run_id'])
        reservations = [r for r in self.budget.snapshot()['reservations'] if r['claim'] == claim]
        need(len(reservations) == 1 and reservations[0]['state'] in ('send_claimed', 'unknown'), 'budget_claim_not_sent')
        self.budget.unknown(claim['claim_id'])
        evidence = execution_evidence(self.root, claim['operation_id'])
        consensus = self._consensus_evidence()
        records = consensus.get('snapshot', {}).get('records', {})
        row = records.get('operations/' + claim['operation_id'], {}).get('value')
        if row is not None:
            need(all(row[k] == claim[k] for k in ('operation_id', 'client_nonce', 'review_digest')), 'original_operation_mismatch')
        local = table_rows(evidence['journals']['member'], 'protected_operation')
        member_rows = [r for r in local if r.get('side') == 'member' and r['operation_id'] == claim['operation_id']] if local is not None else []
        need(len(member_rows) <= 1, 'ambiguous_original_operation')
        native = member_rows[0] if member_rows else None
        if native is not None:
            need(native['review_digest'] == claim['review_digest'], 'original_operation_mismatch')
            if row is not None:
                need(native['attempt_id'] == row['attempt_id'] and native['approval_digest'] == row['approval_digest'], 'original_operation_mismatch')
        export = private_directory(destination, create=True)
        files = {'original-claim.json': claim, 'consensus-evidence.json': consensus,
                 'execution-evidence.json': evidence, 'original-member-record.json': native,
                 'original-cluster-record.json': row, 'budget-after.json': self.budget.snapshot(),
                 'saved-review-observation.json': observation(self.root / ('review-' + claim['operation_id'] + '.json'))}
        # Preserve owned daemon/model observations as observations, never proof
        # that a named PID/container is currently stopped or isolated.
        files['owned-observations.json'] = {name: observation(self.root / name) for name in
            ('model/owned.json', 'model/stop-receipt.json', 'border0-spawn.json', 'border1-spawn.json',
             'border2-spawn.json', 'member-spawn.json', 'homes/member/netclaw-federation/daemon.json',
             'homes/member/netclaw-federation/member-daemon-status.json')}
        for name, value in files.items(): write_new(export / name, value)
        packet = {'schema_version': 1, 'class': 'REAL', 'evidence_kind': 'unresolved_operation_snapshot',
            'run_id': self.plan['run_id'], 'source_sha256': self.plan['source_sha256'],
            'original_ids': {k: claim[k] for k in ('operation_id', 'client_nonce', 'review_digest')},
            'attempt_id': row.get('attempt_id') if row else native.get('attempt_id') if native else None,
            'result_available': bool(native and native.get('receipt')), 'ack_available': bool(row and row.get('ack')),
            'original_envelopes_verified': False, 'consensus_available': consensus['available'],
            'actual_effect_totals': evidence['actual_effect_totals'], 'globally_consistent_snapshot': False,
            'budget_state': 'unknown', 'successful_native_workload': False, 'full_matrix_qualified': False,
            'artifact_sha256': {name: digest(value) for name, value in files.items()}}
        write_new(export / 'packet.json', packet)
        return {'packet_file': str(export / 'packet.json'), 'successful_native_workload': False, 'budget_state': 'unknown'}

    def stop_role(self, name):
        cfg, environment = self.validate_role(name)
        write_new(self.root / (name + '-stop.claim.json'), {'run_id': self.plan['run_id']})
        result = subprocess.run([cfg['python'], '-I', '-B', str(self.source / 'scripts/federation-control.py'), 'stop'],
            cwd=cfg['home'], env=environment, stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
        # Credential-bearing environment is never persisted or printed.
        need(result.returncode == 0, 'owned_daemon_stop_unknown')
        write_new(self.root / (name + '-stopped.json'), {'stopped': True, 'installation_id': cfg['installation_id']})
        return {'role': name, 'stopped': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    sub = commands.add_parser('prepare'); sub.add_argument('--plan', required=True)
    for name in ('model-start', 'coordination-start', 'materialize', 'start-role', 'stop-role', 'review', 'approve',
                 'publish-claim', 'export-operation', 'export-unknown', 'attachments', 'budget', 'observe'):
        sub = commands.add_parser(name); sub.add_argument('--root', required=True)
        if name in ('start-role', 'stop-role'): sub.add_argument('--role', choices=('border0', 'border1', 'border2', 'member'), required=True)
        if name in ('review', 'approve', 'observe'): sub.add_argument('--node', choices=('border0', 'border1', 'border2'), required=True)
        if name in ('approve', 'publish-claim'): sub.add_argument('--review-file', required=True)
        if name == 'publish-claim':
            sub.add_argument('--surface', choices=('hud', 'vscode', 'mobile'), required=True); sub.add_argument('--destination', required=True)
        if name == 'observe': sub.add_argument('--operation-id', required=True)
        if name in ('export-operation', 'export-unknown'): sub.add_argument('--claim-file', required=True); sub.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    if args.command == 'prepare': result = prepare(args.plan)
    else:
        run = Rehearsal(args.root)
        if args.command == 'model-start': result = run.start_model()
        elif args.command == 'coordination-start': result = run.start_coordination()
        elif args.command == 'materialize': result = run.materialize()
        elif args.command == 'start-role': result = run.start_role(args.role)
        elif args.command == 'stop-role': result = run.stop_role(args.role)
        elif args.command == 'review': result = run.prepare_review(args.node)
        elif args.command == 'approve': result = run.approve_once(args.node, args.review_file)
        elif args.command == 'publish-claim': result = run.publish_claim(args.review_file, args.surface, args.destination)
        elif args.command == 'export-operation': result = run.export_operation(args.claim_file, args.destination)
        elif args.command == 'export-unknown': result = run.export_unknown(args.claim_file, args.destination)
        elif args.command == 'attachments': result = run.attachment_status()
        elif args.command == 'observe':
            uuid_value(args.operation_id)
            result = run.operator(args.node, 'reconcile', {'auth_context': run.context(args.node), 'operation_id': args.operation_id})
        else: result = run.budget.snapshot()
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, TypeError, RuntimeError):
        print('r08_real_runtime: failed_or_unknown; retain original IDs and private evidence', file=sys.stderr)
        raise SystemExit(1)
