"""Production HA construction from owned, versioned, pinned private profiles."""
import asyncio
import hashlib
from pathlib import Path
import time

from .. import exporter_tls, protected_contract as c
from ..protected_runtime import build_executor
from .admission import MemberAdmission
from .authority import Authority
from .border import ClusterBorderOperations
from .config import check, HAError, listen_address, read_private, require_ha, validate_listen, verify_manifest
from .internal import MemberAttachments, accept_member, border_binding
from .member import ClusterMemberOperations
from .node import ClusterNode
from .signatures import sign
from .store import EtcdStore


def load_configuration(reference, *, role):
    c.exact(reference, 'config_file config_sha256')
    c.digest_field(reference['config_sha256'])
    raw = read_private(reference['config_file'])
    check(hashlib.sha256(raw).hexdigest() == reference['config_sha256'], 'ha_configuration_changed', 409)
    value = c.decode(raw)
    fields = 'schema_version role manifest_file anchor_certificate_file anchor_key_id transport_ca_file'
    fields += (' node_id transport_certificate_file private_key_file etcd' if role == 'border'
               else ' certificate_file private_key_file')
    if role == 'border' and 'listen' in value:
        fields += ' listen'
    c.exact(value, fields)
    check(type(value['schema_version']) is int and value['schema_version'] == 1 and value['role'] == role,
          'invalid_ha_configuration')
    c.digest_field(value['anchor_key_id'])
    for key, path in value.items():
        if key.endswith('_file'):
            check(isinstance(path, str) and '\x00' not in path and len(path) <= 4096 and Path(path).is_absolute(), 'invalid_ha_file')
            read_private(path)
    if role == 'border':
        c.uuid_field(value['node_id'])
        if 'listen' in value:
            validate_listen(value['listen'])
        c.exact(value['etcd'], 'endpoints ca_file certificate_file private_key_file username password_file')
        for key, path in value['etcd'].items():
            if key.endswith('_file'):
                check(isinstance(path, str) and '\x00' not in path and len(path) <= 4096 and Path(path).is_absolute(), 'invalid_ha_file')
                read_private(path)
    return value


class HAServiceRuntime:
    def __init__(self, service, config, manifest, envelope, anchor):
        self.service, self.config, self.manifest = service, config, manifest
        self.envelope, self.anchor = envelope, anchor
        self.operations = self.node = self.attachments = self.server = None
        self.tasks = set()

    def register_member(self, channel):
        member_id = channel.member_id
        old = self.service.member_channels.get(member_id)
        self.service.member_channels[member_id] = channel
        def closed(ch):
            if self.service.member_channels.get(member_id) is ch:
                self.service.member_channels.pop(member_id, None)
        channel.on_close = closed
        if old is not None and old is not channel:
            task = asyncio.create_task(old.close())
            self.tasks.add(task); task.add_done_callback(self.tasks.discard)

    async def accept_internal(self, reader, writer):
        check(self.node is not None, 'members_cannot_listen', 403)
        async def admission(ch, params):
            return await self.node.admit_member(ch, params)
        async def admission_status(ch, params):
            await self.node.member_current(ch.protected_peer_binding)
            return await self.node.route('n2n/cluster/admission-status',
                                          {'request': params, 'member': ch.protected_peer_binding})
        return await accept_member(self.node, reader, writer,
            handlers={'execution/admission': admission, 'execution/admission-status': admission_status},
            on_authenticated=self.register_member)

    async def start(self):
        try:
            await self.operations.start()
            if self.node:
                address = self.manifest.node(self.node.node_id)['endpoints']['in2n']
                bind_host, bind_port = listen_address(self.config.get('listen'), 'in2n', address)
                self.server = await exporter_tls.start_server(self.accept_internal, bind_host, bind_port,
                    cert_file=self.config['transport_certificate_file'], key_file=self.config['private_key_file'],
                    close_clients=True)
            else:
                await self.attachments.start()
        except BaseException:
            await self.close()
            raise

    async def close(self):
        if self.server:
            self.server.close()
        if self.attachments: await self.attachments.close()
        for channel in list(self.service.member_channels.values()): await channel.close()
        for channel in list(getattr(self.service, 'edge_channels', {}).values()): await channel.close()
        for task in list(self.tasks): task.cancel()
        if self.tasks: await asyncio.gather(*list(self.tasks), return_exceptions=True)
        if self.operations: await self.operations.close()
        if self.server: await self.server.wait_closed()

    async def descriptor(self, params):
        c.exact(params, 'auth_context')
        check(self.node is not None, 'wrong_role')
        with self.operations._owner(params['auth_context']): pass
        state, leader_id, epoch = 'no_quorum', None, None
        try:
            rows = await asyncio.to_thread(self.node.authority.snapshot)
            control, leader = rows['control'][0], rows['leader'][0]
            if not control['active'] or control.get('recovery', {}).get('capacity_frozen'): state = 'fenced'
            elif control['nodes'][self.node.node_id]['state'] == 'retired': state = 'retired'
            elif control['nodes'][self.node.node_id]['state'] == 'drained': state = 'fenced'
            elif leader:
                leader_id, epoch = leader['node_id'], rows['leader'][1]
                state = 'leader' if leader_id == self.node.node_id else 'follower'
        except HAError as exc:
            if exc.code == 'node_retired': state = 'retired'
            elif exc.code in ('recovery_fenced', 'cluster_changed', 'manifest_changed'): state = 'fenced'
        return self.discovery({'state': state, 'leader_node_id': leader_id, 'epoch': epoch,
                               'observed_at_ms': int(time.time()*1000)})

    def discovery(self, authority=None):
        # Identity discovery alone is never evidence of current authority.
        return {'schema_version': 1, 'mode': 'cluster', **self.manifest.audience,
                'manifest_revision': self.manifest.revision, 'node_id': self.node.node_id,
                'installation_id': self.operations.identity['installation_id'],
                'manifest': self.envelope, 'anchor_certificate': self.anchor, 'anchor_key_id': self.manifest.anchor_key_id,
                'authority': authority or {'state': 'no_quorum', 'leader_node_id': None, 'epoch': None,
                                          'observed_at_ms': int(time.time()*1000)}}


def from_service(service, profile):
    from ..protected_service import OperatorBridge, validate_profile
    state, identity, role = service.runtime.state, profile['identity'], profile['role']
    check(identity['installation_id'] == service.runtime.installation, 'installation_mismatch', 403)
    check((role == 'border') == service.risk.is_border(), 'role_mismatch', 503)
    if role == 'border':
        check(profile.get('access') == {'mode': 'open-lab'}, 'ha_access_unqualified', 403)
    config = load_configuration(profile['ha'], role=role)
    envelope = c.decode(read_private(config['manifest_file']))
    anchor = read_private(config['anchor_certificate_file']).decode()
    manifest = verify_manifest(envelope, anchor, expected_key_id=config['anchor_key_id'])
    require_ha(state, manifest, adapter_ready=True)
    original_profile, original_config = c.encode(profile), c.encode(config)
    files = {path for key, path in config.items() if key.endswith('_file')}
    files.update(path for key, path in config.get('etcd', {}).items() if key.endswith('_file'))
    file_hashes = {path: hashlib.sha256(read_private(path)).hexdigest() for path in files}
    def current():
        observed = validate_profile(c.decode(read_private(state / 'protected-profile.json')), role=role, identity=identity)
        check(c.encode(observed) == original_profile, 'local_profile_changed', 403)
        check(c.encode(load_configuration(observed['ha'], role=role)) == original_config, 'ha_configuration_changed', 403)
        check(c.decode(read_private(config['manifest_file'])) == envelope
              and read_private(config['anchor_certificate_file']).decode() == anchor, 'manifest_changed', 403)
        check(all(hashlib.sha256(read_private(path)).hexdigest() == digest for path, digest in file_hashes.items()),
              'ha_configuration_changed', 403)
        require_ha(state, manifest, adapter_ready=True)
    adapter = HAServiceRuntime(service, config, manifest, envelope, anchor)
    private_key = read_private(config['private_key_file']).decode()
    if role == 'border':
        node_id = config['node_id']; node = manifest.node(node_id)
        check(identity == border_binding(manifest, node_id), 'local_authority_changed', 403)
        check(c.key_id(read_private(config['transport_certificate_file']).decode()) == node['key_id'], 'node_key_mismatch', 403)
        check(sign('hello', {'startup': True}, private_key)['key_id'] == node['key_id'], 'node_key_mismatch', 403)
        etcd = config['etcd']
        store = EtcdStore(etcd['endpoints'], prefix=f'/netclaw/ha/{manifest.cluster_id}/{manifest.generation}/',
            ca=etcd['ca_file'], certificate=etcd['certificate_file'], private_key=etcd['private_key_file'],
            username=etcd['username'], password=read_private(etcd['password_file'], 256).decode().strip())
        authority = Authority(store, manifest, node_id)
        adapter.node = ClusterNode(authority, private_key=private_key, ca_file=config['transport_ca_file'],
            cert_file=config['transport_certificate_file'], key_file=config['private_key_file'],
            listen=config.get('listen'))
        adapter.node.local_current = current
        operations = ClusterBorderOperations(adapter.node, state_dir=state, member_channels=service.member_channels,
                                             audit_writer=service.audit.protected, current=current)
        operations.cluster_info = adapter.descriptor
        from .edge_service import wire
        wire(service, adapter, operations)
        operations.bridge = OperatorBridge(operations, state, service.runtime.installation)
        service.cluster_channels = adapter.node.channels
    else:
        check(all(identity['installation_id'] != node['installation_id']
                  and identity['key_id'] != node['key_id'] for node in manifest.nodes),
              'member_border_identity_collision', 403)
        certificate = read_private(config['certificate_file']).decode()
        check(c.key_id(certificate) == identity['key_id'] == sign('attachment-member', {'startup': True}, private_key)['key_id'],
              'member_key_mismatch', 403)
        c.validate_catalog_entry(profile['catalog'])
        check(profile['catalog']['member'] == identity, 'catalog_identity_mismatch', 403)
        executor = build_executor(profile['runtime'], manager=service.manager)
        try:
            if hasattr(executor, 'validate_catalog'):
                executor.validate_catalog(profile['catalog'], runtime_config=profile['runtime'])
            async def current_attachment(): current()
            attachments = MemberAttachments(manifest, identity, private_key, ca_file=config['transport_ca_file'],
                                             handlers={}, current=current_attachment)
            def catalog():
                current()
                if hasattr(executor, 'validate_catalog'):
                    executor.validate_catalog(profile['catalog'], runtime_config=profile['runtime'])
                else:
                    c.validate_catalog_entry(profile['catalog'])
                return profile['catalog']
            operations = ClusterMemberOperations(service.manager, manifest=manifest, identity=identity,
                certificate=certificate, private_key=private_key, attachments=attachments,
                journal=MemberAdmission(state / 'ha-member', manifest, identity), catalog_provider=catalog,
                executor=executor, audit_writer=service.audit.protected, current=current)
            attachments.handlers = {method: getattr(operations, action) for method, action in {
                'execution/catalog':'member_catalog','execution/submit':'submit','execution/status':'member_status',
                'execution/result':'member_result','execution/ack':'acknowledge'}.items()}
            adapter.attachments = attachments
            service.border_channels = attachments.channels
        except BaseException:
            if hasattr(executor, 'close'):
                executor.close()
            raise
    operations.config = profile
    adapter.operations = operations
    service.ha_runtime = adapter
    return operations
