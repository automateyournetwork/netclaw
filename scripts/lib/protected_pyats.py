"""R02's read-only adapter: execute once, then parse that captured output.

This module deliberately does not change the ordinary upstream MCP tools.
Its caller owns authentication, exact approved arguments and the effect claim.
"""
import hashlib
import json
from pathlib import Path


class ProtectedPyatsRefused(ValueError):
    pass


ARGUMENT_KEYS = {"device_name", "command", "timeout", "retries"}


def validate_arguments(arguments):
    if not isinstance(arguments, dict) or set(arguments) != ARGUMENT_KEYS:
        raise ProtectedPyatsRefused("exact_arguments_required")
    if (not isinstance(arguments["device_name"], str)
            or not 1 <= len(arguments["device_name"]) <= 200
            or arguments["command"] != "show version"
            or type(arguments["timeout"]) is not int
            or not 1 <= arguments["timeout"] <= 120
            or type(arguments["retries"]) is not int
            or arguments["retries"] != 1):
        raise ProtectedPyatsRefused("unqualified_read")


def execute_once(server, arguments, *, logfile, before_execute=None):
    """Blocking owned child operation. No retry, including parser failure.

    The MCP child is dedicated to one approved operation, so temporary upstream
    hooks cannot race another request. Connection initialization is separately
    bounded and never enters configuration mode. A timeout may leave a command
    in flight; the parent must retain its durable spent claim.
    """
    validate_arguments(arguments)
    if getattr(server, "_CONN_CACHE_TTL", 0) != 0:
        raise ProtectedPyatsRefused("connection_cache_forbidden")
    testbed = server._load_testbed()
    device = testbed.devices.get(arguments["device_name"])
    if device is None:
        raise ProtectedPyatsRefused("unknown_device")
    connected = getattr(device, "is_connected", lambda: False)
    if connected():
        raise ProtectedPyatsRefused("fresh_connection_required")
    if str(device.os) not in ("ios", "iosxe"):
        raise ProtectedPyatsRefused("unqualified_parser_platform")
    original_load = server._load_testbed
    original_args = server._get_testbed_connection_args
    server._load_testbed = lambda: testbed

    def connection_args(selected):
        # Do not import arbitrary testbed connection hooks into this profile.
        return {"init_config_commands": [], "init_exec_commands": [],
                "log_stdout": False, "logfile": str(logfile),
                "connection_timeout": arguments["timeout"],
                "learn_hostname": False}

    server._get_testbed_connection_args = connection_args
    actual = None
    try:
        actual = server._get_device(arguments["device_name"])
        if before_execute is not None:
            before_execute()
        raw = actual.execute(arguments["command"], timeout=arguments["timeout"])
        if not isinstance(raw, str):
            raise ProtectedPyatsRefused("invalid_device_output")
        # output= prevents Genie from executing the command again. Fail parsing
        # without fallback I/O; raw evidence remains the authoritative output.
        try:
            parsed = actual.parse(arguments["command"], output=raw)
            json.dumps(parsed, allow_nan=False)
        except Exception:
            parsed = None
        return {"status": "completed", "device": arguments["device_name"],
                "command": arguments["command"], "output": parsed if parsed is not None else raw,
                "parsed": parsed is not None, "raw_output": raw,
                "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "execute_calls": 1, "attempts_made": 1,
                "connection_init_config_commands": [], "connection_init_exec_commands": []}
    finally:
        try:
            server._disconnect_device(actual)
        finally:
            server._load_testbed = original_load
            server._get_testbed_connection_args = original_args


def source_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
