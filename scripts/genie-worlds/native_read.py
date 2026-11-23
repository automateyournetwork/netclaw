"""Internal selected-runtime read/parse seam; not an installed collector adapter.

The caller still owns frozen inventory, native plugin/connection qualification,
strict endpoint binding and the collector's process/deadline boundary. This
module never connects, loads credentials or exports a qualification marker.
It does not call or widen the protected show-version-only execution adapter.
"""
import hashlib
import importlib
import inspect
import math
from pathlib import Path


COMMANDS = frozenset(('show version', 'show ip interface brief',
                      'show lldp neighbors detail', 'show cdp neighbors detail',
                      'show interfaces'))
PARSERS = {
    'show version': ('show_platform', 'ShowVersion'),
    'show ip interface brief': ('show_interface', 'ShowIpInterfaceBrief'),
    'show lldp neighbors detail': ('show_lldp', 'ShowLldpNeighborsDetail'),
    'show cdp neighbors detail': ('show_cdp', 'ShowCdpNeighborsDetail'),
    'show interfaces': ('show_interface', 'ShowInterfaces'),
}


class ReadRefused(ValueError):
    pass


def validate_read(server, command, *, source_sha256):
    """Intersect the frozen command set with the pinned native read validator.

    The digest must come from the operator's selected-runtime manifest, never
    from a model/tool argument. A native refusal is final and its text is not
    echoed (it can contain private input). No fallback policy is supplied.
    """
    if not isinstance(command, str) or command not in COMMANDS:
        raise ReadRefused('unqualified_command')
    validator = getattr(server, 'validate_show_command', None)
    path = getattr(server, '__file__', None)
    if (not inspect.isfunction(validator) or not path
            or Path(inspect.getsourcefile(validator) or '').resolve() != Path(path).resolve()
            or hashlib.sha256(Path(path).read_bytes()).hexdigest() != source_sha256):
        raise ReadRefused('native_read_policy_changed')
    try:
        result = validator(command)
    except Exception:
        raise ReadRefused('native_read_policy_failed') from None
    # Native contract is precisely None on success, not general falsiness.
    if result is not None:
        raise ReadRefused('native_read_policy_refused')


def capture_once(server, device, command, *, timeout, source_sha256):
    """One execute on an already-qualified fresh connection; no parsing/retry.

    Raw output is returned before any parser runs so the collector can durably
    preserve it. Exceptions propagate as capture uncertainty in collector.py.
    This low-level function is not evidence that connection setup was qualified.
    """
    validate_read(server, command, source_sha256=source_sha256)
    if (type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 < timeout <= 30):
        raise ReadRefused('read_timeout')
    if str(getattr(device, 'os', '')) != 'iosxe':
        raise ReadRefused('parser_platform_unqualified')
    if not device.is_connected():
        raise ReadRefused('qualified_connection_required')
    expected = {'mit': True, 'operating_mode': True, 'learn_os': False,
                'learn_tokens': False, 'learn_hostname': False, 'reconnect': False}
    if (any(getattr(device, key, None) is not value for key, value in expected.items())
            or getattr(getattr(device, 'settings', None), 'LEARN_DEVICE_TOKENS', None) is not False
            or getattr(getattr(device, 'state_machine', None), 'current_state', None) != 'enable'):
        raise ReadRefused('connection_policy_not_applied')
    raw = device.execute(command, timeout=timeout)
    if not isinstance(raw, str):
        raise ReadRefused('invalid_capture')
    return raw


class OfflineDevice:
    """Deliberately has no live device, testbed, session or credential reference."""
    os = 'iosxe'

    def execute(self, *args, **kwargs):
        raise ReadRefused('offline_parser_execution_refused')


def parse_captured(command, *, output):
    if command not in COMMANDS or not isinstance(output, str):
        raise ReadRefused('invalid_offline_input')
    module, name = PARSERS[command]
    parser = getattr(importlib.import_module('genie.libs.parser.iosxe.' + module), name)
    # Even a parser which ignores output= or executes on empty output cannot
    # acquire a live device. Never use actual_device.parse here.
    return parser(device=OfflineDevice()).parse(output=output)
