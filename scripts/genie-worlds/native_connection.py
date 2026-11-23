"""Internal frozen single-device preparation; no connection or credential-file reads.

This is not a collector adapter or authorization. Operator-owned source metadata
must supply both digests; never accept them from a model. Reuse only the existing
native plugin/endpoint helpers, not the protected show-version execution grant.
The caller must still qualify and bound the actual connection and capture.
"""
import copy
from dataclasses import dataclass, field
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
from types import SimpleNamespace

_spec = importlib.util.spec_from_file_location('_spec200_connection_policy',
    Path(__file__).resolve().parents[1] / 'lib/protected_pyats.py')
policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy)
SSH_PREFIX = '-F /dev/null -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=yes -o UserKnownHostsFile='
CREDENTIALS = {'default': {'username': '%ENV{SPEC200_PYATS_USERNAME}',
    'password': '%ENV{SPEC200_PYATS_PASSWORD}'},
    'enable': {'password': '%ENV{SPEC200_PYATS_ENABLE_PASSWORD}'}}


class ConnectionRefused(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _endpoint(name, device, *, loaded=False):
    try:
        endpoint = policy.endpoint_identity(name, device)
        connection = device.connections[endpoint['connection']]
        options = connection.get('ssh_options', '')
        if (endpoint.get('host_key_policy') != 'strict'
                or not re.fullmatch(r'/[A-Za-z0-9_./-]+', options[len(SSH_PREFIX):])
                or type(connection.get('port',22)) is not int
                or (not loaded and 'credentials' in connection)):
            raise ValueError()
        return endpoint
    except Exception:
        raise ConnectionRefused('strict_endpoint_required') from None


@dataclass(frozen=True)
class PreparedDevice:
    device: object = field(repr=False)
    name: str
    endpoint_sha256: str
    via: str
    credentials: object = field(repr=False)

    def connection_options(self, timeout):
        """Recheck mutable resolved endpoint/trust immediately before future connect.

        No connection is made here. The caller must select a private logfile,
        own the process deadline, validate the command and check resulting posture.
        """
        if (type(timeout) not in (int,float) or not math.isfinite(timeout)
                or not 0 < timeout <= 30):
            raise ConnectionRefused('connection_timeout')
        if str(getattr(self.device, 'platform', '')) != 'iol':
            raise ConnectionRefused('resolved_platform_changed')
        if digest(_endpoint(self.name,self.device,loaded=True)) != self.endpoint_sha256:
            raise ConnectionRefused('resolved_endpoint_changed')
        if self.device.connections[self.via].get('credentials',{}) != self.credentials:
            raise ConnectionRefused('resolved_credentials_changed')
        if self.device.is_connected():
            raise ConnectionRefused('fresh_connection_required')
        return {**policy.connection_policy(), 'via':self.via,
                'log_stdout':False, 'connection_timeout':timeout}


def prepare_device(document, device_name, *, document_sha256, endpoint_sha256, loader=None):
    """Validate frozen input and pinned native plugin BEFORE pyATS topology load.

    loader is a local testing seam, not an exposed tool input. Default loader is
    the installed pyATS loader; it resolves only the three scoped ENV references.
    No YAML input, custom classes/hooks, inherited testbeds or cached devices.
    """
    try:
        encoded = json.dumps(document, allow_nan=False)
        if len(encoded.encode()) > 65536 or digest(document) != document_sha256:
            raise ConnectionRefused('frozen_testbed_changed')
        document = copy.deepcopy(document)
        if (not isinstance(device_name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', device_name)
                or set(document) != {'testbed','devices'}
                or set(document['testbed']) != {'name','credentials'}
                or set(document['devices']) != {device_name}
                or not isinstance(document['testbed']['name'],str)
                or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',document['testbed']['name'])):
            raise ConnectionRefused('minimal_testbed_required')
        if document['testbed']['credentials'] != CREDENTIALS:
            raise ConnectionRefused('scoped_credential_references_required')
        selected = document['devices'][device_name]
        if (set(selected) - {'type','os','platform','connections'}
                or selected.get('type') not in ('router','switch')
                or selected.get('os') != 'iosxe' or selected.get('platform') != 'iol'
                or selected['connections'].get('defaults',{}) not in ({},{'class':'unicon.Unicon'})):
            raise ConnectionRefused('minimal_device_required')
        endpoint = _endpoint(device_name, SimpleNamespace(os=selected['os'],connections=selected['connections']))
        if digest(endpoint) != endpoint_sha256:
            raise ConnectionRefused('frozen_endpoint_changed')
    except ConnectionRefused:
        raise
    except Exception:
        raise ConnectionRefused('invalid_frozen_testbed') from None
    try:
        policy.validate_native_policy(document, device_name)
    except Exception:
        raise ConnectionRefused('native_connection_policy_refused') from None
    try:
        if loader is None:
            from pyats.topology.loader import load
            loader = load
        testbed = loader(document)
        if set(testbed.devices) != {device_name}:
            raise ConnectionRefused('resolved_device_set_changed')
        device = testbed.devices[device_name]
        prepared = PreparedDevice(device,device_name,endpoint_sha256,endpoint['connection'],
                                  getattr(testbed,'credentials',{}))
        prepared.connection_options(30)
        return prepared
    except ConnectionRefused:
        raise
    except Exception:
        raise ConnectionRefused('native_testbed_load_failed') from None
