"""R02's read-only adapter: execute once, then parse that captured output.

This module deliberately does not change the ordinary upstream MCP tools.
Its caller owns authentication, exact approved arguments and the effect claim.
"""
import hashlib
import importlib.metadata
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import stat


class ProtectedPyatsRefused(ValueError):
    pass


ARGUMENT_KEYS = {"device_name", "command", "timeout", "retries"}

# Qualification is deliberately narrower than ordinary pyATS support. In this
# pinned IOS-XE plugin, operating_mode=True suppresses automatic mode discovery;
# it is an internal skip marker, not a claim about the device's operating mode.
# MIT alone does not suppress that discovery (which can also change PnP state).
UNICON_SOURCE_SHA256 = "e53e542cee1b5b531ffeb9042e43685eaad3cf1fc36a4f0c46fe23a949f3f7b7"
NATIVE_VERSIONS = {"unicon": "25.2", "unicon.plugins": "25.2", "pyats": "25.2", "genie": "25.2"}


def validate_native_policy(document, device_name):
    """Before connecting, pin the qualified plugin and its native interpreter seams.

    The digest covers all installed Unicon .py/.so files, including the selected
    providers, state machines, settings, services and compiled topology adapter.
    It is bound by this adapter's signed source revision. This Mac qualification
    does not attest every Python dependency or qualify other vendor platforms.
    """
    selected = document["devices"][device_name]
    if selected.get("os") != "iosxe" or selected.get("platform") != "iol":
        raise ProtectedPyatsRefused("unqualified_connection_plugin")
    for name, expected in NATIVE_VERSIONS.items():
        if importlib.metadata.version(name) != expected:
            raise ProtectedPyatsRefused("native_dependency_version_changed")
    spec = importlib.util.find_spec("unicon")
    if spec is None or not spec.origin:
        raise ProtectedPyatsRefused("native_dependency_missing")
    root = Path(spec.origin).resolve(strict=True).parent
    manifest = {}
    for path in sorted(root.rglob("*")):
        if path.suffix not in (".py", ".so") or "__pycache__" in path.parts:
            continue
        if path.is_symlink() or not path.is_file():
            raise ProtectedPyatsRefused("native_dependency_path_changed")
        manifest[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != UNICON_SOURCE_SHA256:
        raise ProtectedPyatsRefused("native_dependency_source_changed")


def connection_policy():
    return {"mit": True, "operating_mode": True, "learn_os": False,
            "learn_tokens": False, "learn_hostname": False, "reconnect": False,
            "settings": {"LEARN_DEVICE_TOKENS": False},
            "init_config_commands": [], "init_exec_commands": []}


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


def endpoint_identity(device_name, device):
    connections = device.connections
    defaults = connections.get("defaults", {})
    if set(defaults) - {"class"}:
        raise ProtectedPyatsRefused("connection_defaults_refused")
    default_class = defaults.get("class")
    if default_class is not None and default_class != "unicon.Unicon":
        try:
            from unicon import Unicon
        except ImportError:
            raise ProtectedPyatsRefused("connection_class_refused") from None
        if default_class is not Unicon:
            raise ProtectedPyatsRefused("connection_class_refused")
    names = set(connections) - {"defaults"}
    if len(names) != 1 or not names <= {"cli", "ssh"}:
        raise ProtectedPyatsRefused("ambiguous_connection")
    name = next(iter(names))
    connection = connections[name]
    if set(connection) - {"protocol", "ip", "port", "credentials", "ssh_options"}:
        raise ProtectedPyatsRefused("connection_options_refused")
    if (connection.get("protocol") != "ssh"
            or any(connection.get(key) for key in ("proxy", "command", "via"))):
        raise ProtectedPyatsRefused("unqualified_connection")
    try:
        host = str(ipaddress.ip_address(str(connection.get("ip", ""))))
        port = int(connection.get("port", 22))
    except (ValueError, TypeError):
        raise ProtectedPyatsRefused("unqualified_endpoint") from None
    if not 1 <= port <= 65535:
        raise ProtectedPyatsRefused("unqualified_endpoint")
    identity = {"device_name": device_name, "os": str(device.os), "protocol": "ssh",
                "host": host, "port": port, "connection": name}
    options = connection.get("ssh_options")
    if options:
        prefix = "-F /dev/null -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=yes -o UserKnownHostsFile="
        if not isinstance(options, str) or not options.startswith(prefix):
            raise ProtectedPyatsRefused("ssh_routing_options_refused")
        path = Path(options[len(prefix):])
        if not path.is_absolute() or any(char.isspace() for char in str(path)) or str(path.absolute()) != str(path.resolve()):
            raise ProtectedPyatsRefused("unsafe_known_hosts")
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ProtectedPyatsRefused("unsafe_known_hosts")
        identity["known_hosts_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        identity["host_key_policy"] = "strict"
    return identity


def validate_document(document, device_name):
    """Reject YAML inheritance, arbitrary classes and custom hooks before load."""
    if (not isinstance(document, dict) or set(document) != {"testbed", "devices"}
            or set(document["testbed"]) - {"name", "credentials"}
            or set(document["devices"]) != {device_name}):
        raise ProtectedPyatsRefused("minimal_testbed_required")
    selected = document["devices"][device_name]
    if set(selected) - {"alias", "type", "os", "platform", "connections"}:
        raise ProtectedPyatsRefused("testbed_hooks_refused")
    connections = selected["connections"]
    if connections.get("defaults", {}) not in ({}, {"class": "unicon.Unicon"}):
        raise ProtectedPyatsRefused("testbed_defaults_refused")
    from types import SimpleNamespace
    endpoint = endpoint_identity(device_name, SimpleNamespace(os=selected["os"], connections=connections))
    if endpoint.get("host_key_policy") != "strict":
        raise ProtectedPyatsRefused("strict_host_key_required")
    credentials = document["testbed"].get("credentials", {})
    if credentials != {"default": {"username": "%ENV{PYATS_R02_USERNAME}", "password": "%ENV{PYATS_R02_PASSWORD}"},
                       "enable": {"password": "%ENV{PYATS_R02_ENABLE_PASSWORD}"}}:
        raise ProtectedPyatsRefused("scoped_credential_references_required")
    for name, connection in connections.items():
        if name != "defaults" and "credentials" in connection:
            raise ProtectedPyatsRefused("per_connection_credentials_refused")


def execute_once(server, arguments, *, logfile, before_execute=None, endpoint_sha256=None):
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
    endpoint = None
    if endpoint_sha256 is not None:
        endpoint = endpoint_identity(arguments["device_name"], device)
        encoded = json.dumps(endpoint, sort_keys=True, separators=(",", ":")).encode()
        if hashlib.sha256(encoded).hexdigest() != endpoint_sha256:
            raise ProtectedPyatsRefused("resolved_endpoint_changed")
    original_load = server._load_testbed
    original_args = server._get_testbed_connection_args
    server._load_testbed = lambda: testbed

    def connection_args(selected):
        # Do not import arbitrary testbed connection hooks into this profile.
        options = {**connection_policy(), "log_stdout": False,
                   "logfile": str(logfile), "connection_timeout": arguments["timeout"]}
        if endpoint is not None:
            options["via"] = endpoint["connection"]
        return options

    server._get_testbed_connection_args = connection_args
    actual = None
    try:
        actual = server._get_device(arguments["device_name"])
        # Never let execute's state transition or automatic reconnect send an
        # unreviewed enable/setup command. The qualified SSH login lands in exec.
        for name in ("mit", "operating_mode", "learn_os", "learn_tokens", "learn_hostname", "reconnect"):
            if getattr(actual, name, None) is not connection_policy()[name]:
                raise ProtectedPyatsRefused("connection_policy_not_applied")
        if getattr(getattr(actual, "settings", None), "LEARN_DEVICE_TOKENS", None) is not False:
            raise ProtectedPyatsRefused("connection_policy_not_applied")
        if getattr(getattr(actual, "state_machine", None), "current_state", None) != "enable":
            raise ProtectedPyatsRefused("initial_exec_state_required")
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
                "connection_init_config_commands": [], "connection_init_exec_commands": [],
                "connection_policy": connection_policy(), "initial_state": "enable"}
    finally:
        try:
            server._disconnect_device(actual)
        finally:
            server._load_testbed = original_load
            server._get_testbed_connection_args = original_args


def source_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
