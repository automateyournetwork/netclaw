"""Narrow cluster device wiring. Device proofs cross nodes; capabilities do not."""
import asyncio

from .. import protected_contract as c
from ..edge import RpcError
from ..protected_device import ClusterDeviceAuthority
from .config import check
from .edge import ClusterEdgeRegistry


def wire(service, adapter, operations):
    registry = ClusterEdgeRegistry(adapter.node.authority)
    service.ha_edge = registry
    operations.edge_registry = registry

    async def dispatch(action, params, *, ingress_node_id):
        fields = {'edge/challenge': 'node_id', 'edge/issue': 'node_id client_nonce replace_client_nonce',
            'edge/status': 'client_nonce', 'edge/enroll': 'client_nonce token member_id certificate challenge signature',
            'edge/hello': 'member_id key_fingerprint challenge signature', 'edge/revoke': 'member_id'}
        check(action in fields, 'cluster_method_refused', 403)
        c.exact(params, fields[action])
        if 'node_id' in params:
            check(params['node_id'] == ingress_node_id, 'device_ingress_mismatch', 403)
        if 'challenge' in params:
            check(params['challenge'].get('node_id') == ingress_node_id, 'device_ingress_mismatch', 403)
        await adapter.node.current(ingress_node_id)
        result = await asyncio.to_thread(getattr(registry, action.split('/')[1]), **params)
        await adapter.node.current(ingress_node_id)
        return result

    async def route(action, params):
        return await adapter.node.route('n2n/cluster/edge', {'action': action, 'params': params})

    adapter.node.edge_dispatch, service.ha_edge_route = dispatch, route
    from ..mobile_enrollment import ClusterMobileEnrollment
    service.mobile_enrollment = ClusterMobileEnrollment(service, route=route, descriptor=adapter.discovery)
    operations.mobile_enrollment = service.mobile_enrollment


async def challenge(service, channel):
    node = service.ha_runtime.node
    channel.ha_challenge = await service.ha_edge_route('edge/challenge', {'node_id': node.node_id})
    return channel.ha_challenge


def register(service, channel):
    member_id = channel.member_id
    old = service.edge_channels.get(member_id)
    service.edge_channels[member_id] = channel
    def closed(ch):
        if service.edge_channels.get(member_id) is ch:
            service.edge_channels.pop(member_id, None)
    channel.on_close = closed
    authority = ClusterDeviceAuthority(service, channel)
    async def current():
        await service.ha_runtime.node.current(service.ha_runtime.node.node_id)
        await authority.refresh()
        return True
    channel.authority_current = current
    if old is not None and old is not channel:
        task = asyncio.create_task(old.close())
        service.ha_runtime.tasks.add(task); task.add_done_callback(service.ha_runtime.tasks.discard)
    task = asyncio.create_task(service._edge_heartbeat_loop(member_id, channel))
    service.ha_runtime.tasks.add(task); task.add_done_callback(service.ha_runtime.tasks.discard)


async def authenticate(service, channel, params, *, enroll):
    try:
        check(service.ha_runtime.node is not None and not channel.trusted, 'device_channel_refused', 403)
        fields = ('installation_id client_nonce token member_id cert_pem signature runtime_kind display_name' if enroll
                  else 'installation_id member_id key_fingerprint signature')
        c.exact(params, fields)
        check(params['installation_id'] == service.runtime.installation, 'installation_changed', 409)
        challenge_value = getattr(channel, 'ha_challenge', None)
        check(isinstance(challenge_value, dict), 'device_challenge_required', 403)
        if enroll:
            check(params['runtime_kind'] == 'mobile' and isinstance(params['display_name'], str)
                  and 0 < len(params['display_name']) <= 120, 'device_profile_refused', 403)
            args = {k: params[k] for k in ('client_nonce', 'token', 'member_id', 'signature')}
            args['certificate'] = params['cert_pem']
        else:
            args = {k: params[k] for k in ('member_id', 'key_fingerprint', 'signature')}
        binding = await service.ha_edge_route('edge/enroll' if enroll else 'edge/hello',
                                             dict(args, challenge=challenge_value))
        context = {'access_mode': 'open-lab', 'installation_id': service.runtime.installation,
                   **service.ha_runtime.manifest.audience}
        channel.ha_descriptor = await service.ha_runtime.descriptor({'auth_context': context})
        channel.member_id = channel.peer_identity = binding['member_id']
        channel.ha_binding, channel.trusted = binding, True
        register(service, channel)
        service.audit.record(direction='inbound', peer_identity=binding['member_id'],
            target_type='enroll' if enroll else 'hello', target_name=binding['member_id'],
            decision='enrolled' if enroll else 'authenticated', outcome='success', channel_kind='in2n')
        return {'trusted': True, 'member_state': 'active',
                'enroll_fingerprint': binding['key_fingerprint'],
                'border': service._edge_border_capabilities(channel)}
    except c.ProtectedError as exc:
        raise RpcError(-32000, 'Cluster device authentication refused', {'code': exc.code, 'status': exc.status}) from None


async def protected_request(service, action, channel, params):
    fields = {'catalog': '', 'prepare': 'client_nonce catalog_revision member_id model_profile_id tool arguments',
              'decision': 'operation_id revision review_digest decision', 'reconcile': 'operation_id',
              'status': 'operation_id' if isinstance(params, dict) and 'operation_id' in params else 'client_nonce'}
    check(action in fields, 'cluster_method_refused', 403)
    c.exact(params, 'installation_id device_proof' + (' ' + fields[action] if fields[action] else ''))
    check(params['installation_id'] == service.runtime.installation, 'installation_changed', 409)
    authority = ClusterDeviceAuthority(service, channel)
    await authority.refresh()
    check(params['device_proof'].get('member_id') == channel.member_id
          and params['device_proof'].get('enrollment_generation') == channel.ha_binding['enrollment_generation'],
          'device_authority_changed', 403)
    original = {k:v for k,v in params.items() if k != 'device_proof'}
    args = {k:v for k,v in original.items() if k != 'installation_id'}
    context = {'access_mode': 'cluster-device-proof', 'proof': params['device_proof'], 'params': original}
    result = await getattr(service.protected_operations, action)(dict(args, auth_context=context))
    await authority.refresh()
    if isinstance(result, dict) and 'allowed_actions' in result:
        result = dict(result, allowed_actions=[a for a in result['allowed_actions'] if a != 'revoke'])
    return result


def capabilities(service, channel):
    from ..mobile_enrollment import endpoint, https_origin
    result = {'installation_id': service.runtime.installation, 'harness': service.inventory._harness_card(),
              'model': None, 'qualified_targets': [], 'minimum_mobile_version': None,
              'cluster': getattr(channel, 'ha_descriptor', None) or service.ha_runtime.discovery(),
              'capabilities': {'text': False, 'voice_text': False, 'attachments': False,
                               'task_outcomes_v1': False, 'request_recovery': False}}
    if channel is not None:
        principal = ClusterDeviceAuthority(service, channel).principal()
        result['capabilities']['protected_operations'] = {'schema': 1,
            'installation_id': service.runtime.installation, 'origin': https_origin(endpoint(service)),
            'methods': ['n2n/edge/operations/' + a for a in ('catalog','prepare','status','decision','reconcile')],
            'principal': principal, 'enrollment_generation': channel.ha_binding['enrollment_generation']}
    return result
