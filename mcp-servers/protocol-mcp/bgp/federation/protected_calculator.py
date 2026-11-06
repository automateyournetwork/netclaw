"""Bounded summary verification and two-child coordination (Spec176).

The bounds/decimal-string approach follows Thermidor Spec004, Apache-2.0.
This module never invokes a calculator or provider: existing protected MCP and
child-operation authority remain the only execution path.
"""
import asyncio
import ipaddress
import uuid
from .protected_contract import (ProtectedError, encode, exact, ident, require,
    sha256, uuid_field, validate_review)

CAPABILITY = 'calculator_combined_v1'
SUMMARY_SOURCE_SHA256 = '582f3203269612fcf949c5875e41ac557bb096d6476c846e1ac921ba559a6364'
PROFILE_FAMILIES = {'ollama-cpu-ipv4': 4, 'ollama-cpu-ipv6': 6}
TOOLS = {4: 'subnet_calculator', 6: 'subnet_calculator_v6'}


def summary_network(tool, arguments):
    exact(arguments, 'cidr')
    cidr = arguments['cidr']
    require(isinstance(cidr, str) and 3 <= len(cidr) <= 80, 'invalid_subnet')
    family = next((family for family, name in TOOLS.items() if name == tool), None)
    require(family is not None, 'unsupported_tool')
    try:
        network = ipaddress.ip_network(cidr, strict=True)
    except ValueError:
        raise ProtectedError('unsupported_subnet') from None
    require(network.version == family and str(network) == cidr
            and (family != 6 or network.network_address.ipv4_mapped is None), 'unsupported_subnet')
    return network


def expected_summary(tool, arguments):
    """Independent integer arithmetic: constant memory even for IPv6 /0."""
    network = summary_network(tool, arguments)
    bits, prefix = network.max_prefixlen, network.prefixlen
    first = int(network.network_address)
    count = 1 << (bits - prefix)
    last = first + count - 1
    addr = ipaddress.IPv4Address if bits == 32 else ipaddress.IPv6Address
    result = {'schema_version': 1, 'family': network.version, 'network': str(network),
              'prefix_length': prefix, 'address_count': str(count),
              'first_address': str(addr(first)), 'last_address': str(addr(last)),
              'previous_subnet': str(addr(first-count)) + '/' + str(prefix) if first >= count else None,
              'next_subnet': str(addr(first+count)) + '/' + str(prefix) if first+count < 1 << bits else None}
    if bits == 32:
        offset = int(prefix < 31)
        result.update(netmask=str(addr(((1 << bits)-1) ^ (count-1))),
                      wildcard_mask=str(addr(count-1)), broadcast=str(addr(last)),
                      usable_first=str(addr(first+offset)), usable_last=str(addr(last-offset)),
                      usable_count=str(count-2*offset))
    else:
        result['subnets_64'] = str(1 << (64-prefix)) if prefix <= 64 else '0'
    return result


def verify_summary(tool, arguments, output):
    """Verify every native fact against the independently derived summary.

    The patched existing MCP returns a compact versioned summary; unrecognized or
    extra result fields cannot sneak model text into authoritative arithmetic.
    """
    expected = expected_summary(tool, arguments)
    require(isinstance(output, dict) and len(encode(output)) <= 32768,
            'calculator_result_shape')
    native = dict(expected)
    if expected['family'] == 4:
        network = summary_network(tool, arguments)
        first, count = int(network.network_address), network.num_addresses
        offset = int(network.prefixlen < 31)
        usable = count - 2*offset
        native.update(network_address=expected['first_address'], broadcast_address=expected['last_address'],
            with_netmask=network.with_netmask, with_hostmask=network.with_hostmask,
            num_addresses=count, usable_hosts_count=usable,
            usable_hosts_preview=[str(ipaddress.IPv4Address(first+offset+i)) for i in range(min(10, usable))],
            first_usable=expected['usable_first'], last_usable=expected['usable_last'],
            address_range=expected['usable_first']+' - '+expected['usable_last'],
            host_bits=32-network.prefixlen, total_bits=32,
            summary=f"CIDR {arguments['cidr']} has {count} total addresses with {usable} usable hosts "
                    f"({network.prefixlen} prefix, {32-network.prefixlen} host bits).",
            note='Showing first 10 usable hosts only (capped for large subnets).')
        for name in ('private','global','link_local','multicast','loopback','reserved','unspecified'):
            native['is_'+name] = getattr(network, 'is_'+name)
    require(encode(output) == encode(native), 'calculator_arithmetic_mismatch')
    return expected


def ollama_family(model):
    if model.get('provider') != 'ollama':
        return None
    family = PROFILE_FAMILIES.get(model.get('profile_id'))
    require(family is not None and model.get('model') == 'qwen3:0.6b'
            and model.get('runtime_kind') == 'openclaw'
            and model.get('runtime_version') == '2026.7.1-2', 'unsupported_ollama_profile')
    return family


def aggregate(children, cancelled):
    states = [child['state'] for child in children]
    if any(s in ('reconciliation_required', 'outcome_unknown', 'audit_pending') for s in states):
        return 'unknown'
    if all(s == 'completed' for s in states):
        return 'complete'
    if any(s in ('approved', 'dispatch_pending', 'member_admitted', 'result_pending') for s in states):
        return 'running'
    if cancelled:
        return 'partial' if 'completed' in states else 'cancelled'
    if 'review_pending' in states:
        return 'awaiting_decisions'
    return 'partial' if 'completed' in states else 'failed'


class CombinedCoordinator:
    """Parent references existing child authority; parent creation has no effects."""
    def __init__(self, service):
        self.service = service

    def _parent(self, params, principal):
        if 'parent_id' in params:
            uuid_field(params['parent_id'])
        else:
            ident(params['client_nonce'])
        parent = self.service.store.get_combined(
            parent_id=params.get('parent_id'), client_nonce=params.get('client_nonce'),
            owner_subject=principal['subject'])
        require(parent is not None and parent['principal'] == principal
                and parent['border'] == self.service.identity, 'combined_not_found', 404)
        return parent

    def _view(self, parent, principal):
        children = []
        for index, child in enumerate(parent['children']):
            row = self.service._owned(child['operation_id'], principal)
            value = self.service._view(row, principal)
            if parent['cancelled'] or self.service.now() >= parent['expires_at_ms'] or (
                    index and children[index-1]['state'] == 'review_pending'):
                value['allowed_actions'] = [a for a in value['allowed_actions'] if a not in ('approve', 'deny')]
            children.append(dict(value, index=index, family=child['family']))
        return {'schemaVersion': 1, 'parent_id': parent['parent_id'],
                'client_nonce': parent['client_nonce'], 'request_digest': parent['request_digest'],
                'created_at_ms': parent['created_at_ms'], 'expires_at_ms': parent['expires_at_ms'],
                'cancelled': bool(parent['cancelled']), 'state': aggregate(children, parent['cancelled']),
                'children': children}

    async def prepare(self, params):
        exact(params, 'auth_context client_nonce children')
        ident(params['client_nonce'])
        children = params['children']
        require(isinstance(children, list) and len(children) == 2, 'combined_children_required')
        for index, child in enumerate(children):
            exact(child, 'family member_id profile_revision cidr')
            require(type(child['family']) is int and child['family'] == (4, 6)[index], 'combined_family_order')
            ident(child['member_id']); ident(child['profile_revision'])
            summary_network(TOOLS[child['family']], {'cidr': child['cidr']})
        require(children[0]['member_id'] != children[1]['member_id'], 'combined_distinct_members_required')
        requested = {'client_nonce': params['client_nonce'], 'children': children}
        request_digest = sha256(requested)
        with self.service._owner(params['auth_context']) as principal:
            old = self.service.store.get_combined(client_nonce=params['client_nonce'], owner_subject=principal['subject'])
            if old:
                parent = self._parent(params, principal)
                require(parent['request_digest'] == request_digest, 'client_nonce_conflict', 409)
                return self._view(parent, principal)
        catalog = await self.service.catalog({'auth_context': params['auth_context']})
        selected = []
        for child in children:
            member = next((m for m in catalog['members'] if m['member']['member_id'] == child['member_id']), None)
            require(member is not None, 'member_not_available', 409)
            models = [m for m in member['model_profiles'] if ollama_family(m) == child['family']
                      and m['profile_revision'] == child['profile_revision']]
            tools = [t for t in member['tools'] if t['tool'] == TOOLS[child['family']]
                     and t['arguments'] == {'cidr': child['cidr']}]
            require(len(models) == len(tools) == 1, 'selection_not_supported', 403)
            selected.append((member, models[0], tools[0]))
        from .protected_owner import OwnerAuthority
        from .certs import cert_not_after
        from .protected_device import DeviceAuthority
        authority_expiry = self.service.now() + 900000
        if isinstance(self.service.owner, OwnerAuthority) and not isinstance(params['auth_context'], DeviceAuthority):
            authority_expiry = min(authority_expiry, self.service.owner.authority_expiry(params['auth_context']))
        with self.service._owner(params['auth_context']) as principal:
            now = self.service.now()
            snapshots = [{'border': self.service._trust(self.service.identity),
                          'member': self.service._trust(member['member'])} for member, _, _ in selected]
            authority_expiry = min(authority_expiry, *(int(cert_not_after(cert).timestamp()*1000)
                for snapshot in snapshots for cert in snapshot.values()))
            require(now < authority_expiry, 'authority_expired', 403)
            parent_id = str(uuid.uuid4())
            parent = {'parent_id': parent_id, 'client_nonce': params['client_nonce'],
                      'principal': principal, 'border': self.service.identity, 'request_digest': request_digest,
                      'created_at_ms': now, 'expires_at_ms': authority_expiry, 'cancelled': 0, 'children': []}
            rows = []
            for index, (member, model, tool) in enumerate(selected):
                operation_id = str(uuid.uuid4())
                limits = dict(tool['limits'], expires_at_ms=min(now+180000, parent['expires_at_ms']))
                require(limits['inference_timeout_ms'] <= (60000 if index == 0 else 120000)
                        and limits['max_output_bytes'] <= 32768, 'calculator_limits_refused')
                review = {'principal': principal, 'border': self.service.identity, 'member': member['member'],
                          'model_profile': model, 'tool_call': {k: v for k, v in tool.items() if k != 'limits'},
                          'limits': limits, 'change_request_ref': None}
                validate_review(review)
                rows.append({'side': 'border', 'operation_id': operation_id, 'owner_subject': principal['subject'],
                    'review': review, 'review_digest': sha256(review), 'state': 'review_pending',
                    'client_nonce': 'calc:'+parent_id+':'+str(index), 'candidate_digest': sha256(children[index]),
                    'trust_snapshot': snapshots[index]})
                parent['children'].append({'operation_id': operation_id, 'family': children[index]['family']})
            parent = self.service.store.create_combined(parent, rows)
            return self._view(parent, principal)

    async def status(self, params):
        require(set(params) in ({'auth_context', 'parent_id'}, {'auth_context', 'client_nonce'}))
        with self.service._owner(params['auth_context']) as principal:
            parent = self._parent(params, principal)
        for child in parent['children']:
            # Reconciliation may collect a result/ACK but never creates a claim.
            await asyncio.sleep(0)
            try:
                await asyncio.wait_for(self.service.reconcile({'auth_context': params['auth_context'],
                    'operation_id': child['operation_id']}), timeout=5)
            except asyncio.TimeoutError:
                pass  # Bounded read-only recovery leaves the same claims and child state.
        with self.service._owner(params['auth_context']) as principal:
            return self._view(self._parent(params, principal), principal)

    async def cancel(self, params):
        exact(params, 'auth_context parent_id')
        with self.service._owner(params['auth_context']) as principal:
            parent = self._parent(params, principal)
            for child in parent['children']:
                self.service._audit('protected_revocation', self.service._owned(child['operation_id'], principal))
            parent = self.service.store.cancel_combined(parent['parent_id'], principal)
            return self._view(parent, principal)
