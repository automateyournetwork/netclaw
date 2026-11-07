"""Native-only authority for an enrolled device; never deserialized from RPC."""
from contextlib import contextmanager
import json
import uuid

from .protected_contract import require


class DeviceAuthority:
    def __init__(self, service, channel):
        self.service, self.channel = service, channel
        self._binding = self._current()

    def _current(self):
        service, channel = self.service, self.channel
        require(service.protected_enabled and service.protected_operations is not None,
                'protected_operations_unavailable', 503)
        require(channel.trusted and not channel._closed
                and service.edge_channels.get(channel.member_id) is channel,
                'device_channel_revoked', 403)
        member = service.risk.get_member(channel.member_id)
        require(member is not None and member['node_type'] == 'edge'
                and member['state'] in ('active', 'enrolled', 'unreachable')
                and member['installation_id'] == service.runtime.installation
                and member['key_fingerprint'] == getattr(channel, 'owner_generation', None)
                and member['enrollment_generation'] == getattr(channel, 'enrollment_generation', None),
                'device_authority_changed', 403)
        return (service.runtime.installation, channel.member_id, member['key_fingerprint'],
                member['enrollment_generation'])

    def principal(self):
        require(self._current() == self._binding, 'device_authority_changed', 403)
        installation, member_id, fingerprint, generation = self._binding
        subject = str(uuid.uuid5(uuid.UUID(installation),
            'netclaw.mobile.device:' + json.dumps([member_id, fingerprint, generation], separators=(',', ':'))))
        return {'issuer': 'device-key', 'subject': subject,
                'display_name': 'Enrolled mobile device', 'roles': ['device-operator']}

    @contextmanager
    def authorize(self, operations):
        require(operations is self.service.protected_operations, 'foreign_device_authority', 403)
        yield self.principal()


class ClusterDeviceAuthority(DeviceAuthority):
    """Native capability tied to a live channel and quorum-owned device key."""
    def _current(self):
        service, channel = self.service, self.channel
        require(service.protected_enabled and service.protected_operations is not None,
                'protected_operations_unavailable', 503)
        require(channel.trusted and not channel._closed
                and service.edge_channels.get(channel.member_id) is channel,
                'device_channel_revoked', 403)
        registry = getattr(service, 'ha_edge', None)
        require(registry is not None, 'cluster_device_authority_unavailable', 503)
        current = getattr(channel, 'ha_binding', None)
        fields = ('cluster_id', 'generation', 'member_id', 'key_fingerprint',
                  'enrollment_generation', 'principal')
        require(isinstance(current, dict) and all(k in current for k in fields)
                and current.get('state') == 'active' and current['member_id'] == channel.member_id
                and {k: current[k] for k in ('cluster_id', 'generation')} == registry.manifest.audience,
                'device_authority_changed', 403)
        return tuple(json.dumps(current[k], sort_keys=True, separators=(',', ':')) for k in fields)

    async def refresh(self):
        import asyncio
        current = await asyncio.to_thread(self.service.ha_edge.binding, self.channel.member_id)
        require(current == self.channel.ha_binding, 'device_authority_changed', 403)
        require(self._current() == self._binding, 'device_authority_changed', 403)
        return self.principal()

    def principal(self):
        require(self._current() == self._binding, 'device_authority_changed', 403)
        return json.loads(self._binding[-1])
