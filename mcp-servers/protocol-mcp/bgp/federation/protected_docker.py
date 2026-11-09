"""Owned Docker adapter for R02. Inspection is evidence, not a systemd claim."""
import asyncio
import hashlib
import hmac
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import time
from urllib.parse import urlparse

from . import protected_runtime as _runtime_source
from . import protected_mcp as _mcp_source
from . import protected_hosted as _hosted
from . import protected_ollama as _ollama
from .protected_mcp import (invoke_mcp, validate_binding as validate_mcp_binding, contract_digest as mcp_contract_digest, skill_context)

from .protected_runtime import (ExactToolBroker, InferenceFence, RuntimeRefused,
                                RuntimeUnknown, ScopedInference, canonical,
                                invoke_pyats, private_directory, private_write, sha)



_HOST_SOURCE_PATHS = {"protected_docker.py": Path(__file__),
                      "protected_runtime.py": Path(_runtime_source.__file__),
                      "protected_selection.py": Path(__file__).with_name("protected_selection.py"),
                      "protected_mcp.py": Path(_mcp_source.__file__)}
_HOST_SOURCE_PINS = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for name, path in _HOST_SOURCE_PATHS.items()}
_OLLAMA_SOURCE_PIN = hashlib.sha256(Path(_ollama.__file__).read_bytes()).hexdigest()
_HOSTED_SOURCE_PIN = hashlib.sha256(Path(_hosted.__file__).read_bytes()).hexdigest()
_GUARD_FIELDS = {"image", "config_file", "config_sha256", "policy_manifest_sha256", "env_file"}
_RUNTIME_FIELDS = {"state_dir", "agent_image", "relay_image", "docker", "docker_host", "guard_token_env",
                   "sandbox_address_pool", "model_profile", "guard", "pyats"}
_PYATS_FIELDS = {"python", "upstream", "upstream_sha256", "source_sha256", "adapter_sha256", "testbed",
                 "testbed_sha256", "known_hosts", "known_hosts_sha256", "endpoint_sha256", "credential_env"}

_MCP_RUNTIME_FIELDS = (_RUNTIME_FIELDS - {'pyats'}) | {'mcp', 'relay_transport'}

_INFERENCE_REFUSAL_CODES = frozenset('''inference_route_refused inference_capability_refused approval_expired
inference_request_bound inference_model_changed inference_fields_refused ambiguous_inference_token_limit
inference_token_limit_refused caller_guard_routing_header_refused inference_profile_refused
ollama_history_without_inference ollama_real_tool_result_required ollama_invented_assistant_history
ollama_tool_history_changed ollama_invented_tool_output ollama_unverified_tool_output
ollama_tool_arguments_invalid ollama_duplicate_tool_argument ollama_nonfinite_tool_argument
ollama_tool_family_changed ollama_approval_profile_changed ollama_caller_reasoning_refused
ollama_tool_schema_changed ollama_messages_invalid ollama_conversation_changed ollama_request_context_bound
ollama_runner_recovery_required runner_recovery_required'''.split())


def record_inference_refusal(operation_root, code):
    """Private first-refusal diagnostic: fixed vocabulary, never request/exception text."""
    receipt = Path(operation_root) / 'inference-refusal.json'
    if receipt.exists():
        return
    private_write(receipt, canonical({'schema_version': 1,
        'code': code if isinstance(code, str) and code in _INFERENCE_REFUSAL_CODES else 'inference_refused'}))


def _single_protected_error(group):
    """The lone RuntimeRefused/RuntimeUnknown inside an (Base)ExceptionGroup, else None. Nothing else is unwrapped."""
    inner = getattr(group, 'exceptions', None)
    if (type(group).__name__ in ('ExceptionGroup', 'BaseExceptionGroup') and isinstance(inner, tuple) and len(inner) == 1
            and isinstance(inner[0], (RuntimeRefused, RuntimeUnknown))):
        return inner[0]
    return None


def validate_runtime_fields(config):
    fields = set(config)
    if fields == _RUNTIME_FIELDS:
        return 'pyats'
    if fields in (_MCP_RUNTIME_FIELDS, _MCP_RUNTIME_FIELDS | {'ollama'}, _MCP_RUNTIME_FIELDS | {'hosted'}) and config.get('relay_transport') in ('unix', 'tcp'):
        if 'hosted' in config:
            try: _hosted.validate_profile(config['hosted'])
            except _hosted.HostedRefused as exc: raise RuntimeRefused(exc.code) from None
            # Hosted runs the native summary calculator or the exact reviewed NetBox read; every other binding
            # (origin, credential file, source closure, schema and selection hashes) is still enforced by
            # validate_mcp_binding below. Ollama stays calculator-only.
            if config['mcp'].get('kind') not in ('subnet_summary', 'netbox'): raise RuntimeRefused('hosted_mcp_kind_refused')
        if 'ollama' in config:
            try:
                _ollama.validate_profile(config['ollama'])
                _ollama.need(config['ollama']['guard_uid'] == os.getuid(), 'ollama_guard_uid_changed')
            except _ollama.OllamaRefused as exc: raise RuntimeRefused(exc.code) from None
            if config['mcp'].get('kind') != 'subnet_summary': raise RuntimeRefused('ollama_native_summary_required')
        validate_mcp_binding(config['mcp'], check_files=False)
        return 'mcp'
    raise RuntimeRefused('runtime_configuration_fields_refused')

# These are the qualified R02 profiles. Exact immutable image/version pairs are
# supplied by the separately reviewed runtime packet, not inferred from labels.
_QUALIFIED_HARNESSES = {"openclaw": "2026.7.1-2", "hermes": "v0.21.6"}


def _digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _hash(value, code="revision_pin_required"):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise RuntimeRefused(code)
    return value


def _image(value):
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise RuntimeRefused("immutable_runtime_image_required")
    return value


def _public_bytes(path):
    path = Path(path).absolute()
    info = path.lstat()
    if (path != path.resolve() or not stat.S_ISREG(info.st_mode)
            or info.st_uid not in (0, os.getuid()) or info.st_mode & 0o022
            or info.st_size > 128 * 1024 * 1024):
        raise RuntimeRefused("unsafe_pinned_source")
    return path.read_bytes()


def _native_identity(path, *, python=False):
    """Bind native executables too; an arbitrary replacement cannot retain a label."""
    supplied = Path(path)
    if not supplied.is_absolute():
        raise RuntimeRefused("absolute_native_executable_required")
    resolved = supplied.resolve(strict=True)
    if not os.access(resolved, os.X_OK):
        raise RuntimeRefused("native_executable_required")
    result = {"path": str(supplied), "resolved_path": str(resolved),
              "sha256": hashlib.sha256(_public_bytes(resolved)).hexdigest()}
    if python:
        venv = supplied.parent.parent / "pyvenv.cfg"
        if not venv.is_file():
            raise RuntimeRefused("isolated_pyats_python_required")
        result["pyvenv_cfg_sha256"] = hashlib.sha256(_public_bytes(venv)).hexdigest()
    return result


def _docker_host(value):
    parsed = urlparse(value)
    if (parsed.scheme != "unix" or parsed.netloc or parsed.query or parsed.fragment
            or not parsed.path or not Path(parsed.path).is_absolute()):
        raise RuntimeRefused("local_docker_socket_required")
    socket_path = Path(parsed.path)
    info = socket_path.lstat()
    if (socket_path != socket_path.resolve() or not stat.S_ISSOCK(info.st_mode)
            or info.st_uid not in (0, os.getuid())):
        raise RuntimeRefused("local_docker_socket_required")
    return "unix://" + str(socket_path)


def protected_tool_input_schema():
    """The complete schema generated by the same pinned MCP SDK used for serving."""
    from mcp.server.mcpserver.tools import Tool
    async def pyats_run_show_command(device_name: str, command: str, timeout: int, retries: int) -> dict:
        raise RuntimeRefused("schema_only")
    return Tool.from_function(pyats_run_show_command).parameters


def guard_policy_digest(guard):
    if not isinstance(guard, dict) or set(guard) != _GUARD_FIELDS:
        raise RuntimeRefused("operation_bound_guard_required")
    return _digest({"schema": "netclaw.guard-policy.v1", "image": _image(guard["image"]),
        "config_sha256": _hash(guard["config_sha256"]),
        "policy_manifest_sha256": _hash(guard["policy_manifest_sha256"])})


def runtime_profile_revision(config):
    profile = config["model_profile"]
    validate_runtime_fields(config)
    if not isinstance(profile, dict): raise RuntimeRefused("unqualified_execution_profile")
    if 'ollama' in config:
        local = config['ollama']
        if hashlib.sha256(_public_bytes(Path(_ollama.__file__))).hexdigest() != _OLLAMA_SOURCE_PIN:
            raise RuntimeRefused('loaded_runtime_source_changed')
        if (profile.get('provider') != 'ollama' or profile.get('model') != _ollama.MODEL
                or profile.get('profile_id') != _ollama.profile_id(local)
                or profile.get('runtime_kind') != 'openclaw' or profile.get('runtime_version') != _QUALIFIED_HARNESSES['openclaw']):
            raise RuntimeRefused('unqualified_ollama_execution_profile')
    elif 'hosted' in config:
        local = config['hosted']
        if hashlib.sha256(_public_bytes(Path(_hosted.__file__))).hexdigest() != _HOSTED_SOURCE_PIN:
            raise RuntimeRefused('loaded_runtime_source_changed')
        if (profile.get('provider') != _hosted.PROVIDER or profile.get('model') != local['model']
                or profile.get('profile_id') != _hosted.profile_id(local)
                or profile.get('runtime_kind') != 'openclaw' or profile.get('runtime_version') != _QUALIFIED_HARNESSES['openclaw']):
            raise RuntimeRefused('unqualified_hosted_execution_profile')
    elif (profile.get("provider") != "anthropic" or profile.get("model") != "claude-sonnet-4-6"
            or profile.get("runtime_kind") not in _QUALIFIED_HARNESSES
            or profile.get("runtime_version") != _QUALIFIED_HARNESSES[profile["runtime_kind"]]):
        raise RuntimeRefused("unqualified_execution_profile")
    for name, path in _HOST_SOURCE_PATHS.items():
        if hashlib.sha256(_public_bytes(path)).hexdigest() != _HOST_SOURCE_PINS[name]:
            raise RuntimeRefused("loaded_runtime_source_changed")
    return _digest({"schema": "netclaw.protected-runtime.v1",
        "harness": {key: profile[key] for key in ("runtime_kind", "runtime_version", "provider", "model")},
        "agent_image": _image(config["agent_image"]), "relay_image": _image(config["relay_image"]),
        "guard_policy_sha256": guard_policy_digest(config["guard"]),
        "native_docker": _native_identity(config["docker"]), "docker_host": _docker_host(config["docker_host"]),
        "sandbox_address_pool": config["sandbox_address_pool"], "host_adapter_sha256": dict(_HOST_SOURCE_PINS),
        **({"relay_transport": config["relay_transport"]} if "mcp" in config else {}),
        **({'ollama': _ollama.profile_binding(config['ollama']), 'ollama_source_sha256': _OLLAMA_SOURCE_PIN} if 'ollama' in config else {}),
        **({'hosted': _hosted.profile_binding(config['hosted']), 'hosted_source_sha256': _HOSTED_SOURCE_PIN} if 'hosted' in config else {})})


def tool_contract_digest(pyats):
    """Hash the advertised schema and the exact trusted implementation behind it.

    This is a tool contract revision, not merely a hash of JSON property names.
    Inventory and resolved endpoint retain their separate signed fields.
    """
    if not isinstance(pyats, dict) or set(pyats) != _PYATS_FIELDS:
        raise RuntimeRefused("pyats_configuration_fields_refused")
    sources = pyats["source_sha256"]; adapters = pyats["adapter_sha256"]
    if (set(sources) != {"pyats_mcp_server.py", "pyats_testbed_builder.py", "pyats_tasks.py"}
            or set(adapters) != {"protected-tool-broker.py", "lib/protected_pyats.py"}):
        raise RuntimeRefused("tool_source_closure_required")
    for value in [pyats["upstream_sha256"], *sources.values(), *adapters.values()]:
        _hash(value)
    if pyats["upstream_sha256"] != sources["pyats_mcp_server.py"]:
        raise RuntimeRefused("tool_source_closure_required")
    if Path(pyats["upstream"]).name != "pyats_mcp_server.py":
        raise RuntimeRefused("tool_source_closure_required")
    credentials = pyats["credential_env"]
    if (not isinstance(credentials, list) or len(set(credentials)) != len(credentials)
            or set(credentials) != {"PYATS_R02_USERNAME", "PYATS_R02_PASSWORD", "PYATS_R02_ENABLE_PASSWORD"}):
        raise RuntimeRefused("scoped_device_credentials_required")
    return _digest({"schema": "netclaw.protected-tool.v1", "tool": "pyats_run_show_command",
        "input_schema": protected_tool_input_schema(),
        "enforced_policy": {"command": "show version", "retries": 1, "timeout_min": 1, "timeout_max": 120,
                            "execute_once": True, "parse_captured_output": True, "exact_raw_arguments": True},
        "upstream_sha256": pyats["upstream_sha256"], "source_sha256": sources, "adapter_sha256": adapters,
        "native_python": _native_identity(pyats["python"], python=True), "credential_env": sorted(credentials)})


def revision_bindings(config):
    """Populate these three fields before signing a catalog; paths/secrets are not returned."""
    return {"guard_policy_sha256": guard_policy_digest(config["guard"]),
            "profile_revision": runtime_profile_revision(config),
            "tool_schema_sha256": (mcp_contract_digest(config["mcp"]) if "mcp" in config else tool_contract_digest(config["pyats"]))}


def validate_catalog_bindings(config, payload):
    """Validate immutable model/tool bindings before an operation exists."""
    bindings = revision_bindings(config)
    if (payload["model_profile"] != config["model_profile"]
            or payload["model_profile"]["guard_policy_sha256"] != bindings["guard_policy_sha256"]
            or payload["model_profile"]["profile_revision"] != bindings["profile_revision"]
            or payload["tool_call"]["tool_schema_sha256"] != bindings["tool_schema_sha256"]):
        raise RuntimeRefused("signed_execution_revision_changed")
    guard = config["guard"]
    if "mcp" in config:
        validate_mcp_binding(config["mcp"], arguments=payload["tool_call"]["arguments"])
        if (payload["tool_call"]["tool"] != config["mcp"]["tool"]
                or payload["tool_call"]["inventory_revision"] != config["mcp"]["selection_sha256"]
                or payload["tool_call"]["endpoint_sha256"] != config["mcp"]["endpoint_sha256"]):
            raise RuntimeRefused("approved_mcp_binding_changed")
        if hashlib.sha256(_public_bytes(guard["config_file"])).hexdigest() != guard["config_sha256"]:
            raise RuntimeRefused("guard_configuration_changed")
        return bindings
    pyats = config["pyats"]
    if hashlib.sha256(_public_bytes(guard["config_file"])).hexdigest() != guard["config_sha256"]:
        raise RuntimeRefused("guard_configuration_changed")
    scripts = Path(_runtime_source.__file__).resolve().parents[4] / "scripts"
    for name, expected in pyats["source_sha256"].items():
        if hashlib.sha256(_public_bytes(Path(pyats["upstream"]).parent / name)).hexdigest() != expected:
            raise RuntimeRefused("pyats_source_changed")
    for name, expected in pyats["adapter_sha256"].items():
        if hashlib.sha256(_public_bytes(scripts / name)).hexdigest() != expected:
            raise RuntimeRefused("adapter_revision_changed")
    for path_key, hash_key in (("testbed", "testbed_sha256"), ("known_hosts", "known_hosts_sha256")):
        if hashlib.sha256(_public_bytes(pyats[path_key])).hexdigest() != pyats[hash_key]:
            raise RuntimeRefused("inventory_or_host_key_changed")
    if (payload["tool_call"]["inventory_revision"] != pyats["testbed_sha256"]
            or payload["tool_call"]["endpoint_sha256"] != pyats["endpoint_sha256"]):
        raise RuntimeRefused("approved_inventory_or_endpoint_changed")
    return bindings


def validate_execution_bindings(config, payload):
    """Validate bindings and mandatory signed operation limits at execution."""
    bindings = validate_catalog_bindings(config, payload)
    if 'ollama' in config:
        cap = _ollama.limits(config['ollama'])
        try:
            approved = payload['limits']
            issued = payload['issued_at_ms']
            values = [issued, *(approved[key] for key in ('expires_at_ms',
                'inference_timeout_ms', 'max_inference_calls', 'max_tool_calls'))]
            valid = (all(type(value) is int for value in values)
                and 0 < approved['expires_at_ms'] - issued <= cap['task_timeout_seconds']*1000
                and 0 < approved['inference_timeout_ms'] <= cap['call_timeout_seconds']*1000
                and approved['max_inference_calls'] == 2 and approved['max_tool_calls'] == 1)
        except (KeyError, TypeError):
            valid = False
        if not valid:
            raise RuntimeRefused('ollama_operation_limits_changed')
    if 'hosted' in config:
        cap = _hosted.limits(config['hosted'])
        try:
            approved = payload['limits']
            issued = payload['issued_at_ms']
            values = [issued, *(approved[key] for key in ('expires_at_ms',
                'inference_timeout_ms', 'max_inference_calls', 'max_tool_calls'))]
            valid = (all(type(value) is int for value in values)
                and 0 < approved['expires_at_ms'] - issued <= cap['task_timeout_seconds']*1000
                and 0 < approved['inference_timeout_ms'] <= cap['call_timeout_seconds']*1000
                and approved['max_inference_calls'] == cap['max_inference_calls']
                and approved['max_tool_calls'] == cap['max_tool_calls'])
        except (KeyError, TypeError):
            valid = False
        if not valid:
            raise RuntimeRefused('hosted_operation_limits_changed')
    return bindings


def validate_raw_mcp_call(body, approved, tool="pyats_run_show_command"):
    if not isinstance(body, dict):
        raise RuntimeRefused("mcp_object_required")
    if body.get("method") == "tools/call":
        params = body.get("params")
        if (not isinstance(params, dict) or params.get("name") != tool
                or "arguments" not in params or canonical(params["arguments"]) != canonical(approved)):
            raise RuntimeRefused("raw_mcp_arguments_changed")


# The host never needs a published model/guard port. This fixed trusted helper
# enters the owned network namespace as guard UID, passing the capability only
# over stdin. A lost Docker exec reply remains an uncertain provider dispatch.
_OLLAMA_GUARD_REQUEST = """import json,sys,urllib.request
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
raw=sys.stdin.buffer.read(1048577)
if len(raw)>1048576:raise ValueError('request_bound')
body=json.loads(raw)
if set(body)!={'request','guard_token','timeout_seconds'}:raise ValueError('request_fields')
request=urllib.request.Request('http://127.0.0.1:4000/v1/chat/completions',
 data=json.dumps(body['request'],separators=(',',':'),ensure_ascii=False).encode(),method='POST',
 headers={'Content-Type':'application/json','X-DC-Auth':body['guard_token'],'X-DC-Target-URL':'http://127.0.0.1:11434'})
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
with opener.open(request,timeout=body['timeout_seconds']) as response:
 if response.status!=200:raise ValueError('guard_status')
 raw=response.read(1048577)
 if len(raw)>1048576:raise ValueError('response_bound')
 json.loads(raw)
 sys.stdout.buffer.write(raw)
"""


def guard_health_probe(ollama=None):
    # The frozen keyless configuration uses the native management API on18970;
    # historical hosted configurations retain their qualified API on4001.
    port = 18970 if ollama is not None else 4001
    return ("import json,urllib.request;h=json.load(urllib.request.urlopen('http://127.0.0.1:"+str(port)+"/health',timeout=2));"
            "print(json.dumps({'guardrail':h.get('guardrail'),'version':h.get('provenance',{}).get('binary_version')}))")


def compact_summary_tool(broker, tool):
    """One native MCP text item; avoid SDK structuredContent duplication."""
    from mcp.types import TextContent
    async def compact_summary(cidr: str) -> list[TextContent]:
        evidence = await broker.call(tool, {'cidr': cidr})
        raw = canonical(_ollama.model_tool_output(evidence))
        if len(raw) > 32768: raise RuntimeRefused('calculator_result_bound')
        return [TextContent(type='text', text=raw.decode())]
    compact_summary.__name__ = tool
    return compact_summary


def inspect_guard(container, *, image, home, env_file, payload, config_sha256, policy_manifest_sha256, running=False, ollama=None):
    config, host = container["Config"], container["HostConfig"]
    if 'cluster' in payload and host.get('LogConfig') != {'Type':'json-file', 'Config':{'max-file':'1'}}:
        raise RuntimeRefused('guard_log_rotation_unqualified')
    expected_args = ["--home", "/guard", "--config-sha256", config_sha256,
                     "--policy-manifest-sha256", policy_manifest_sha256]
    if ollama is not None: expected_args += ["--provider", "ollama"]
    expected_network = "container:"+ollama["model_container_id"] if ollama is not None else "bridge"
    expected_networks = set() if ollama is not None else {"bridge"}
    if (container["Image"] != image or config.get("User") != str(os.getuid())
            or host.get("Privileged") or not host.get("ReadonlyRootfs")
            or host.get("CapDrop") != ["ALL"] or host.get("CapAdd")
            or host.get("SecurityOpt") != ["no-new-privileges"]
            or host.get("NetworkMode") != expected_network or set(container["NetworkSettings"]["Networks"]) != expected_networks
            or host.get("PidMode") not in (None, "") or host.get("IpcMode") != "private"
            or host.get("UsernsMode") not in (None, "") or host.get("Devices")
            or host.get("Memory") != 768*1024*1024 or host.get("PidsLimit") != 128
            or host.get("NanoCpus") != 1000000000 or host.get("Tmpfs") != {"/tmp": "rw,noexec,nosuid,size=64m"}
            or config.get("Entrypoint") != ["python3", "/opt/netclaw/scripts/protected-guard.py"]
            or config.get("Cmd") != expected_args):
        raise RuntimeRefused("guard_containment_changed")
    mounts = [entry for entry in container.get("Mounts", []) if entry.get("Type") != "tmpfs"]
    expected_mounts = {"/guard": (str(home), True), "/guard/guard.env": (str(env_file), False)}
    if (len(mounts) != 2 or any(entry.get("Type") != "bind" for entry in mounts)
            or {entry["Destination"]: (entry.get("Source"), entry.get("RW")) for entry in mounts} != expected_mounts):
        raise RuntimeRefused("guard_mounts_changed")
    environment = {}
    for item in config.get("Env", []):
        key, value = item.split("=", 1)
        if key in environment: raise RuntimeRefused("guard_environment_changed")
        environment[key] = value
    allowed = {"PATH", "LANG", "GPG_KEY", "PYTHON_VERSION", "PYTHON_SHA256", "HOME", "DEFENSECLAW_HOME",
               "NETCLAW_OPERATION_ID", "NETCLAW_OPERATION_EXPIRES_MS", "NETCLAW_OPERATION_MODEL", "NETCLAW_OPERATION_MAX_PROVIDER_CALLS"}
    expected = {"NETCLAW_OPERATION_ID": payload["operation_id"], "NETCLAW_OPERATION_EXPIRES_MS": str(payload["limits"]["expires_at_ms"]),
                "NETCLAW_OPERATION_MODEL": payload["model_profile"]["model"], "NETCLAW_OPERATION_MAX_PROVIDER_CALLS": "2"}
    if (set(environment)-allowed or environment.get("HOME") != "/guard/official-user"
            or environment.get("DEFENSECLAW_HOME") != "/guard"
            or any(environment.get(key) != value for key, value in expected.items())):
        raise RuntimeRefused("guard_environment_changed")
    bindings = host.get("PortBindings") or {}
    if ollama is not None:
        if bindings or any((container['NetworkSettings'].get('Ports') or {}).values()):
            raise RuntimeRefused('ollama_guard_extra_binding_refused')
        return None
    if set(bindings) != {"4000/tcp"} or len(bindings["4000/tcp"]) != 1 or bindings["4000/tcp"][0].get("HostIp") != "127.0.0.1":
        raise RuntimeRefused("guard_public_binding_refused")
    if running:
        ports = {key: value for key, value in container["NetworkSettings"]["Ports"].items() if value}
        if set(ports) != {"4000/tcp"} or len(ports["4000/tcp"] or []) != 1 or ports["4000/tcp"][0]["HostIp"] != "127.0.0.1":
            raise RuntimeRefused("guard_public_binding_refused")
        return "http://127.0.0.1:" + ports["4000/tcp"][0]["HostPort"]


def strict_inference_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise RuntimeRefused("duplicate_inference_key")
            result[key] = value
        return result
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise RuntimeRefused("nonfinite_inference_number")
        return number
    try:
        return json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                          parse_float=finite, parse_constant=lambda _: (_ for _ in ()).throw(RuntimeRefused("nonfinite_inference_number")))
    except (ValueError, UnicodeError, RecursionError):
        raise RuntimeRefused("invalid_inference_json") from None


def inspect_agent(container, network, *, image, mounts, uid=None, gid=None, harness="openclaw", ollama=None):
    """Validate actual Docker inspect data before starting the model process."""
    config, host = container["Config"], container["HostConfig"]
    uid = os.getuid() if uid is None else uid
    gid = os.getgid() if gid is None else gid
    if (type(uid) is not int or uid <= 0 or config.get("User") != str(uid)
            or container["Image"] != image
            or not host.get("ReadonlyRootfs") or host.get("Privileged")
            or set(host.get("CapDrop") or []) != {"ALL"}
            or host.get("CapAdd")
            or host.get("SecurityOpt") != ["no-new-privileges"]
            or host.get("PidMode") not in (None, "") or host.get("IpcMode") != "private"
            or host.get("UsernsMode") not in (None, "")
            or host.get("Devices") or host.get("PortBindings")
            or not 0 < host.get("Memory", 0) <= 4 * 1024 ** 3
            or not 0 < host.get("PidsLimit", 0) <= 256
            or not 0 < host.get("NanoCpus", 0) <= 2 * 10 ** 9):
        raise RuntimeRefused("agent_isolation_mismatch")
    if ollama is not None:
        expected_memory = _ollama.limits(ollama)['agent_memory_mib']*1024**2
        if host.get('Memory') != expected_memory or host.get('MemorySwap') != expected_memory:
            raise RuntimeRefused('ollama_agent_swap_or_memory_changed')
    expected_tmpfs = {"/home/agent": f"rw,noexec,nosuid,size=128m,uid={uid},gid={gid},mode=700",
                      "/tmp": "rw,noexec,nosuid,size=128m"}
    if host.get("Tmpfs") != expected_tmpfs:
        raise RuntimeRefused("agent_writable_mount_mismatch")
    if set(container["NetworkSettings"]["Networks"]) != {network["Name"]}:
        raise RuntimeRefused("agent_network_mismatch")
    if (not network.get("Internal") or network.get("EnableIPv6")
            or network.get("Options", {}).get("com.docker.network.bridge.gateway_mode_ipv4") != "isolated"):
        raise RuntimeRefused("agent_network_not_isolated")
    actual_mounts = {entry["Destination"]: (entry.get("Source"), entry.get("RW"))
                     for entry in container.get("Mounts", []) if entry.get("Type") != "tmpfs"}
    if actual_mounts != {destination: (str(source), False) for destination, source in mounts.items()}:
        raise RuntimeRefused("agent_mount_mismatch")
    keys = {entry.split("=", 1)[0] for entry in config.get("Env", [])}
    allowed = {"PATH", "NODE_VERSION", "YARN_VERSION", "NODE_ENV", "HOME",
               "OPENCLAW_HOME", "OPENCLAW_CONFIG_PATH", "OPENCLAW_STATE_DIR",
               "NETCLAW_OPERATION_TOKEN", "NO_COLOR"}
    if harness == "hermes":
        allowed = {"PATH", "LANG", "GPG_KEY", "PYTHON_VERSION", "PYTHON_SHA256", "HOME",
                   "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED", "NETCLAW_OPERATION_TOKEN", "NO_COLOR"}
    elif harness != "openclaw":
        raise RuntimeRefused("unqualified_harness")
    if keys - allowed:
        raise RuntimeRefused("agent_environment_not_allowlisted")
    return {"image": image, "user": config["User"], "read_only": True,
            "capabilities_dropped": ["ALL"], "no_new_privileges": True,
            "network": network["Name"], "gateway_mode": "isolated",
            "mount_destinations": sorted(mounts), "environment_names": sorted(keys),
            "memory_bytes": host["Memory"], "pids_limit": host["PidsLimit"]}


def openclaw_config(payload, relay, *, ollama=None):
    model = payload["model_profile"]["model"]
    tool = payload["tool_call"]["tool"]
    return {
        "models": {"mode": "replace", "providers": {"defenseclaw": {
            "baseUrl": f"http://{relay}:8090/v1", "api": "openai-completions",
            "apiKey": "${NETCLAW_OPERATION_TOKEN}", "authHeader": True,
            "models": [{"id": model, "name": model, "reasoning": False,
                        "input": ["text"], "contextWindow": 16384 if ollama else 200000, "maxTokens": 1024 if ollama else 2048}]} }},
        "agents": {"defaults": {"model": {"primary": "defenseclaw/" + model, "fallbacks": []},
                                "workspace": "/home/agent/workspace", "skipBootstrap": True,
                                "maxConcurrent": 1}},
        "mcp": {"servers": {"approved": {"url": f"http://{relay}:8090/mcp",
                "transport": "streamable-http", "supportsParallelToolCalls": False,
                "timeout": 150, "connectTimeout": 10,
                "headers": {"Authorization": "Bearer ${NETCLAW_OPERATION_TOKEN}"},
                "toolFilter": {"include": [tool]}}}},
        "tools": {"allow": ["approved__" + tool],
                  "deny": ["group:runtime", "group:fs", "group:web", "group:ui",
                           "group:sessions", "group:messaging", "group:automation", "nodes"]},
        "plugins": {"allow": []}, "gateway": {"mode": "local"},
    }


def completion_sse(response):
    """Deliver a completed guarded JSON answer to a streaming OpenAI client."""
    chunks = []
    for choice in response.get("choices", []):
        message = dict(choice.get("message") or {})
        if "tool_calls" in message:
            message["tool_calls"] = [dict(call, index=index) for index, call in enumerate(message["tool_calls"])]
        chunks.append({"id": response.get("id", "protected"), "object": "chat.completion.chunk",
                       "created": response.get("created", int(time.time())), "model": response.get("model"),
                       "choices": [{"index": choice.get("index", 0), "delta": message,
                                    "finish_reason": choice.get("finish_reason")}],
                       "usage": response.get("usage")})
    return b"".join(b"data: " + canonical(chunk) + b"\n\n" for chunk in chunks) + b"data: [DONE]\n\n"


class DockerExecutor:
    def __init__(self, config, *, manager):
        config = json.loads(canonical(config))
        validate_runtime_fields(config)
        self.config, self.manager = config, manager
        self.state = private_directory(config["state_dir"])
        self.docker = _native_identity(config["docker"])["resolved_path"]
        self.docker_host = _docker_host(config["docker_host"])
        self.docker_config = private_directory(self.state / "docker-cli")
        docker_configuration = self.docker_config / "config.json"
        if docker_configuration.exists() and _public_bytes(docker_configuration) != b"{}":
            raise RuntimeRefused("native_docker_configuration_changed")
        private_write(docker_configuration, b"{}")
        for name in ("agent_image", "relay_image"):
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", config[name]):
                raise RuntimeRefused("immutable_runtime_image_required")
        key = config["guard_token_env"]
        if not re.fullmatch(r"NETCLAW_[A-Z0-9_]+", key) or not os.environ.get(key):
            raise RuntimeRefused("guard_credential_unavailable")
        self.guard_token = os.environ[key]
        self.guards = {}
        self.pool = ipaddress.IPv4Network(config["sandbox_address_pool"])
        if self.pool.prefixlen > 24 or not self.pool.subnet_of(ipaddress.IPv4Network("198.18.0.0/15")):
            raise RuntimeRefused("reviewed_benchmark_address_pool_required")
        self.fence = InferenceFence(self.state / "inference.sqlite")
        self.ollama = config.get('ollama')
        self.hosted = config.get('hosted')
        self.runner_latch = (_ollama.RunnerLatch(self.state/'ollama-runner.sqlite', _ollama.digest(_ollama.profile_binding(self.ollama)))
                             if self.ollama is not None else None)

    async def start_guard(self, payload, operation_root, name, owned):
        config = self.config.get("guard")
        required = _GUARD_FIELDS
        if not isinstance(config, dict) or set(config) != required:
            raise RuntimeRefused("operation_bound_guard_required")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", config["image"]):
            raise RuntimeRefused("immutable_guard_image_required")
        for field in ("config_sha256", "policy_manifest_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}", config[field]):
                raise RuntimeRefused("guard_pin_required")
        for field in ("config_file", "env_file"):
            path = Path(config[field])
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077 or path.absolute() != path.resolve() or "," in str(path)):
                raise RuntimeRefused("unsafe_guard_binding")
        raw_config = Path(config["config_file"]).read_bytes()
        if hashlib.sha256(raw_config).hexdigest() != config["config_sha256"]:
            raise RuntimeRefused("guard_configuration_changed")
        home = private_directory(operation_root / "guard")
        private_write(home / "config.yaml", raw_config)
        # Docker Desktop needs the nested read-only bind's mountpoint to exist
        # in the writable parent bind before creating a read-only rootfs. This
        # empty owned file never receives or copies the provider credential.
        mountpoint = os.open(home / "guard.env", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(mountpoint)
        if self.ollama is not None:
            await self.inspect_model()
            if self.runner_latch.snapshot()['state'] != 'idle': raise RuntimeRefused('ollama_runner_recovery_required')
        guard_network = 'container:'+self.ollama['model_container_id'] if self.ollama else 'bridge'
        publish_args = [] if self.ollama else ['--publish', '127.0.0.1::4000']
        provider_args = ['--provider', 'ollama'] if self.ollama else []
        await self.command("create", "--name", name, "--network", guard_network, "--read-only",
             "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", str(os.getuid()),
             "--pids-limit", "128", "--memory", "768m", "--cpus", "1", "--label", "netclaw.spec=179" if "cluster" in payload else "netclaw.spec=176" if self.ollama else "netclaw.spec=171",
             *(['--log-driver', 'json-file', '--log-opt', 'max-file=1'] if 'cluster' in payload else []),
             "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
             "--mount", f"type=bind,src={home},dst=/guard",
             "--mount", f"type=bind,src={config['env_file']},dst=/guard/guard.env,readonly",
             *publish_args, "--env", "NETCLAW_OPERATION_ID=" + payload["operation_id"],
             "--env", "NETCLAW_OPERATION_EXPIRES_MS=" + str(payload["limits"]["expires_at_ms"]),
             "--env", "NETCLAW_OPERATION_MODEL=" + payload["model_profile"]["model"],
             "--env", "NETCLAW_OPERATION_MAX_PROVIDER_CALLS=2", config["image"],
             "--home", "/guard", "--config-sha256", config["config_sha256"],
             "--policy-manifest-sha256", config["policy_manifest_sha256"], *provider_args)
        owned.append(name)  # A lost start reply must still stop this owned object.
        inspected = json.loads(await self.command("inspect", name))[0]
        inspect_guard(inspected, image=config["image"], home=home, env_file=config["env_file"], payload=payload,
                      config_sha256=config["config_sha256"], policy_manifest_sha256=config["policy_manifest_sha256"], ollama=self.ollama)
        await self.command("start", name)
        inspected = json.loads(await self.command("inspect", name))[0]
        self.guards[payload["operation_id"]] = inspect_guard(inspected, image=config["image"], home=home,
            env_file=config["env_file"], payload=payload, config_sha256=config["config_sha256"],
            policy_manifest_sha256=config["policy_manifest_sha256"], running=True, ollama=self.ollama)
        if self.ollama is not None:
            self.guards[payload['operation_id']] = (await self.inspect_model())['guard_url']
        # Native foreground startup has no daemon PID receipt. Inspect actual
        # health inside the guard namespace, where its admin listener is loopback.
        probe = guard_health_probe(self.ollama)
        for _ in range(40):
            if int(time.time() * 1000) >= payload["limits"]["expires_at_ms"]:
                raise RuntimeRefused("operation_expired")
            try:
                health = json.loads(await self.command("exec", name, "python3", "-c", probe, timeout=5))
                if (health.get("guardrail", {}).get("state") == "running"
                        and health["guardrail"].get("details", {}).get("mode") == "action"
                        and health.get("version") == "1.0.4"):
                    private_write(home / "qualified-health.json", canonical(health))
                    return
            except RuntimeRefused:
                pass
            await asyncio.sleep(0.25)
        raise RuntimeRefused("guard_not_ready")

    async def inspect_model(self):
        try:
            inspected = json.loads(await self.command('inspect', self.ollama['model_container_id']))[0]
            await asyncio.to_thread(_ollama.verify_store, self.ollama)
            networks = inspected['NetworkSettings']['Networks']
            if len(networks) != 1: raise RuntimeRefused('ollama_network_changed')
            model_network = json.loads(await self.command('network', 'inspect', next(iter(networks))))[0]
            if not model_network.get('Internal') or model_network.get('EnableIPv6'):
                raise RuntimeRefused('ollama_network_not_private')
            namespace = (await self.command('exec', self.ollama['model_container_id'], 'readlink', '/proc/self/ns/net', timeout=5)).decode().strip()
            image_config = json.loads(await self.command('image', 'inspect', self.ollama['model_image']))[0]
            if image_config.get('Id') != self.ollama['model_image']: raise RuntimeRefused('ollama_image_changed')
            actual_rules = json.loads(await self.command('exec', '--privileged', '--user', '0', self.ollama['model_container_id'], 'nft', '-j', 'list', 'ruleset', timeout=5))
            return _ollama.verify_confinement(self.ollama, inspected, namespace,
                image_environment=image_config['Config'].get('Env', []), policy_sha256=_ollama.nft_policy_digest(actual_rules))
        except _ollama.OllamaRefused as exc:
            raise RuntimeRefused(exc.code) from None

    async def command(self, *args, timeout=60, input_data=None):
        if _public_bytes(self.docker_config / "config.json") != b"{}":
            raise RuntimeRefused("native_docker_configuration_changed")
        if _docker_host(self.config["docker_host"]) != self.docker_host:
            raise RuntimeRefused("native_docker_host_changed")
        process = await asyncio.create_subprocess_exec(self.docker, "--host", self.docker_host,
                   "--config", str(self.docker_config), *args,
                   stdin=asyncio.subprocess.PIPE if input_data is not None else asyncio.subprocess.DEVNULL,
                   stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                   env={"PATH": os.defpath, "HOME": str(self.docker_config)})
        tasks = []
        try:
            async def bounded_read(stream, maximum):
                output = bytearray()
                while chunk := await stream.read(65536):
                    output.extend(chunk)
                    if len(output) > maximum:
                        raise RuntimeUnknown("docker_output_bound")
                return bytes(output)
            async with asyncio.timeout(timeout):
                if input_data is not None:
                    if not isinstance(input_data, bytes) or len(input_data) > 1048576:
                        raise RuntimeRefused('docker_input_bound')
                    process.stdin.write(input_data)
                    await process.stdin.drain()
                    process.stdin.close()
                tasks = [asyncio.create_task(bounded_read(process.stdout, 4 * 1024 * 1024)),
                         asyncio.create_task(bounded_read(process.stderr, 1024 * 1024)),
                         asyncio.create_task(process.wait())]
                stdout, _stderr, _status = await asyncio.gather(*tasks)
        except BaseException:
            # This only kills the Docker client. The owned container may remain;
            # retain the durable operation fence and report an unknown outcome.
            if process.returncode is None:
                process.kill()
            # Stop prior readers before draining the killed client's pipes.
            # wait() alone can deadlock behind a full asyncio pipe buffer.
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await asyncio.wait_for(process.communicate(), 5)
            except (TimeoutError, asyncio.CancelledError):
                pass
            raise RuntimeUnknown("docker_client_interrupted") from None
        if process.returncode != 0:
            raise RuntimeRefused("docker_operation_failed")
        return stdout

    async def forward(self, payload, request):
        import httpx
        validate_execution_bindings(self.config, payload)
        guard_url = self.guards.get(payload["operation_id"])
        if not guard_url:
            raise RuntimeRefused("operation_bound_guard_unavailable")
        if getattr(self, 'hosted', None) is not None and 'cluster' in payload:
            from .ha.hosted_model_transport import ha_hosted_model_forward
            return strict_inference_json(await ha_hosted_model_forward(self, payload, request, guard_url))
        if self.ollama is not None:
            current = await self.inspect_model()
            if current['guard_url'] != guard_url: raise RuntimeRefused('ollama_guard_binding_changed')
            remaining = (payload['limits']['expires_at_ms']-int(time.time()*1000))/1000
            deadline = min(remaining, payload['limits']['inference_timeout_ms']/1000)
            if deadline <= 0: raise RuntimeRefused('approval_expired')
            if 'cluster' in payload:
                from .ha.model_transport import ha_model_forward
                return strict_inference_json(await ha_model_forward(self, payload, request, guard_url))
            raw = await self.command('exec', '--interactive', '--user', str(self.ollama['guard_uid']),
                self.ollama['model_container_id'], 'python3', '-c', _OLLAMA_GUARD_REQUEST,
                input_data=canonical({'request': request, 'guard_token': self.guard_token, 'timeout_seconds': deadline}), timeout=deadline)
            return strict_inference_json(raw)
        guard_headers = {"X-DC-Auth": self.guard_token, "Content-Type": "application/json"}
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False,
                                     timeout=payload["limits"]["inference_timeout_ms"] / 1000) as client:
            async with client.stream("POST", guard_url + "/v1/chat/completions",
                     headers=guard_headers,
                     content=canonical(request)) as response:
                if response.status_code != 200:
                    raise RuntimeUnknown("guard_request_not_successful")
                output = bytearray()
                async for part in response.aiter_bytes():
                    output.extend(part)
                    if len(output) > 1048576:
                        raise RuntimeUnknown("guard_response_bound")
                return json.loads(output)

    async def run(self, payload, gate, *, ha_admission=None):
        from .protected_runtime import validate_ha_gate
        validate_ha_gate(payload, ha_admission)
        if ha_admission is not None and not (self.ollama or getattr(self, 'hosted', None)):
            raise RuntimeRefused('ha_runtime_unqualified')
        from mcp.server.mcpserver import MCPServer
        from starlette.responses import JSONResponse, Response
        import uvicorn
        validate_execution_bindings(self.config, payload)
        if int(time.time() * 1000) >= payload["limits"]["expires_at_ms"]:
            raise RuntimeRefused("operation_expired")
        operation_id = payload["operation_id"]
        started_monotonic = time.monotonic()
        # Reusing a home is forbidden even if a prior launch left no process.
        operation_root = self.state / operation_id
        operation_root.mkdir(mode=0o700, exist_ok=False)
        agent_files = private_directory(operation_root / "agent")
        token = secrets.token_urlsafe(32)
        suffix = hashlib.sha256(operation_id.encode()).hexdigest()[:20]
        prefix = ("netclaw-r08-" if 'cluster' in payload else "netclaw-r05-" if self.ollama else "netclaw-r02-") + suffix
        network, relay, agent = prefix + "-net", prefix + "-relay", prefix + "-agent"
        harness = payload["model_profile"]["runtime_kind"]
        if harness == "openclaw":
            private_write(agent_files / "openclaw.json", canonical(openclaw_config(payload, relay, ollama=self.ollama)))
        elif harness == "hermes":
            private_write(agent_files / "job.json", canonical({"operation_id": operation_id,
                          "model": payload["model_profile"]["model"],
                          "base_url": f"http://{relay}:8090/v1", "mcp_url": f"http://{relay}:8090/mcp",
                          "arguments": payload["tool_call"]["arguments"], "tool": payload["tool_call"]["tool"],
                          "skill_context": skill_context(self.config["mcp"]) if "mcp" in self.config else ""}))
        else:
            raise RuntimeRefused("unqualified_harness")
        private_write(operation_root / "agent.env", ("NETCLAW_OPERATION_TOKEN=" + token + "\n").encode())

        async def invoke(tool, arguments):
            validate_execution_bindings(self.config, payload)
            if "mcp" not in self.config and payload["tool_call"]["inventory_revision"] != self.config["pyats"]["testbed_sha256"]:
                raise RuntimeRefused("approved_inventory_changed")
            if "mcp" not in self.config and payload["tool_call"]["endpoint_sha256"] != self.config["pyats"]["endpoint_sha256"]:
                raise RuntimeRefused("approved_endpoint_changed")
            remaining = (payload["limits"]["expires_at_ms"] - int(time.time() * 1000)) / 1000
            try:
                async with asyncio.timeout(min(remaining, payload["limits"]["tool_timeout_ms"] / 1000)):
                    async def native():
                        if "mcp" in self.config:
                            return await invoke_mcp(self.config["mcp"], arguments, operation_root / "tool",
                                **({'ha_required': True, 'ha_admission': lambda call:
                                    ha_admission('tool', 1, sha(payload['tool_call']), call)} if 'cluster' in payload else {}))
                        return await invoke_pyats(self.config["pyats"], arguments, operation_root / "tool")
                    return await native()
            except TimeoutError as exc:
                raise RuntimeUnknown("tool_outcome_unknown") from exc

        broker = ExactToolBroker(payload, gate, invoke)
        def local_request(request):
            request = _ollama.validate_history(request, self.fence.first_response(operation_id), broker.evidence)
            return _ollama.calculator_request(request, payload, self.ollama)
        facade = ScopedInference(payload, token, self.fence,
                                  lambda request: self.forward(payload, request),
                                  tool_finished=lambda: broker.evidence is not None,
                                  request_adapter=local_request if self.ollama else None,
                                  response_validator=(lambda response, ordinal: _ollama.validate_response(response, ordinal, payload)) if self.ollama else None,
                                  runner_latch=self.runner_latch, ha_admission=ha_admission)
        mcp = MCPServer("Approved NetClaw operation", version="171")

        async def pyats_run_show_command(device_name: str, command: str, timeout: int, retries: int) -> dict:
            return await broker.call("pyats_run_show_command",
                      dict(device_name=device_name, command=command, timeout=timeout, retries=retries))

        async def netbox_get_object_by_id(object_type: str, object_id: int, fields: list[str], brief: bool) -> dict:
            return await broker.call("netbox_get_object_by_id", dict(object_type=object_type, object_id=object_id, fields=fields, brief=brief))

        async def subnet_calculator(cidr: str) -> dict:
            return await broker.call("subnet_calculator", {"cidr": cidr})

        async def subnet_calculator_v6(cidr: str) -> dict:
            return await broker.call("subnet_calculator_v6", {"cidr": cidr})

        native_tools = {"pyats_run_show_command": pyats_run_show_command,
                        "netbox_get_object_by_id": netbox_get_object_by_id,
                        "subnet_calculator": subnet_calculator, "subnet_calculator_v6": subnet_calculator_v6}
        if self.ollama:
            mcp.add_tool(compact_summary_tool(broker, payload['tool_call']['tool']),
                         description="Execute only the exact owner-approved read once.")
        else:
            mcp.add_tool(native_tools[payload["tool_call"]["tool"]], description="Execute only the exact owner-approved read once.")
        mcp_app = mcp.streamable_http_app(json_response=True, stateless_http=True,
                                         max_request_body_size=1048576)

        async def app(scope, receive, send):
            if scope["type"] != "http":
                return
            headers = {}
            for key, value in scope["headers"]:
                if key in headers:
                    return await JSONResponse({"error": "duplicate_header"}, status_code=400)(scope, receive, send)
                headers[key] = value
            if not hmac.compare_digest(headers.get(b"authorization", b""), ("Bearer " + token).encode()):
                return await JSONResponse({"error": "capability_refused"}, status_code=403)(scope, receive, send)
            if scope["method"] != "POST" or scope["path"] not in ("/mcp", "/v1/chat/completions") or scope.get("query_string"):
                return await JSONResponse({"error": "route_refused"}, status_code=404)(scope, receive, send)
            raw = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                raw.extend(message.get("body", b""))
                if len(raw) > 1048576:
                    return await JSONResponse({"error": "bound"}, status_code=413)(scope, receive, send)
                if not message.get("more_body"):
                    break
            try:
                body = strict_inference_json(bytes(raw))
                if scope["path"] == "/mcp":
                    validate_raw_mcp_call(body, payload["tool_call"]["arguments"], payload["tool_call"]["tool"])
                    delivered = False
                    async def replay_body():
                        nonlocal delivered
                        if not delivered:
                            delivered = True
                            return {"type": "http.request", "body": bytes(raw), "more_body": False}
                        return await receive()
                    return await mcp_app(scope, replay_body, send)
                response = await facade.invoke("POST", scope["path"],
                      {key.decode(): value.decode() for key, value in headers.items()}, body)
                if body.get("stream"):
                    reply = Response(completion_sse(response), media_type="text/event-stream")
                else:
                    reply = JSONResponse(response)
            except RuntimeRefused as exc:
                record_inference_refusal(operation_root, exc.code)
                reply = JSONResponse({"error": "inference_refused"}, status_code=403)
            except Exception:
                reply = JSONResponse({"error": "inference_outcome_unknown"}, status_code=502)
            return await reply(scope, receive, send)

        unix_relay = self.config.get("relay_transport") == "unix"
        if unix_relay:
            broker_dir = private_directory(operation_root / "broker")
            broker_socket = broker_dir / "broker.sock"
            if len(str(broker_socket).encode()) > 103:
                raise RuntimeRefused("broker_socket_path_too_long")
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(broker_socket))
            broker_socket.chmod(0o600)
            relay_args = ["--mount", f"type=bind,src={broker_dir},dst=/broker,readonly",
                          "--env", "NETCLAW_TRUSTED_SOCKET=/broker/broker.sock"]
            relay_network = network
        else:
            listener = socket.socket()
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
            relay_args = ["--env", "NETCLAW_TRUSTED_PORT=" + str(port)]
            relay_network = "bridge"
        listener.listen(64)
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False, lifespan="off"))
        server_task = None
        resource_task = None
        resource_observations = []
        started = []
        try:
            async with mcp.session_manager.run():
                server_task = asyncio.create_task(server.serve(sockets=[listener]))
                await self.start_guard(payload, operation_root, prefix + "-guard", started)
                # Explicit reviewed local-only pool avoids consuming Docker's
                # host-wide default pools. Docker refuses a collision before
                # starting any agent/provider. Never remove another network.
                count = self.pool.num_addresses // 16
                offset = int(suffix, 16) % count
                subnet = str(ipaddress.IPv4Network((int(self.pool.network_address) + offset * 16, 28)))
                await self.command("network", "create", "--internal", "--opt",
                     "com.docker.network.bridge.gateway_mode_ipv4=isolated", "--subnet", subnet,
                     "--label", "netclaw.spec=179" if "cluster" in payload else "netclaw.spec=176" if self.ollama else "netclaw.spec=171", network)
                # Relay alone has a second network to the fixed host endpoint.
                await self.command("create", "--name", relay, "--network", relay_network, "--read-only",
                     "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", str(os.getuid()),
                     "--pids-limit", "64", "--memory", "128m", "--cpus", "0.5", "--label", "netclaw.spec=179" if "cluster" in payload else "netclaw.spec=176" if self.ollama else "netclaw.spec=171",
                     *relay_args, self.config["relay_image"])
                if not unix_relay:
                    await self.command("network", "connect", "--alias", relay, network, relay)
                started.append(relay)
                await self.command("start", relay)
                prompt = ("Execute the single owner-approved MCP read exactly once using " + payload["tool_call"]["tool"] + ". "
                          "Use these exact arguments: " + canonical(payload["tool_call"]["arguments"]).decode()
                          + ". Then summarize the actual returned evidence. Do not use other tools or retry.")
                if "mcp" in self.config:
                    prompt += skill_context(self.config["mcp"])
                    private_write(operation_root / "reviewed-skill-context.txt", prompt.encode())
                native_env = (["--env", "OPENCLAW_CONFIG_PATH=/run/netclaw/openclaw.json",
                               "--env", "OPENCLAW_STATE_DIR=/home/agent/state"] if harness == "openclaw" else [])
                native_args = (["agent", "--local", "--json", "--session-id", operation_id,
                                "--message", prompt, "--timeout", "180"] if harness == "openclaw" else [])
                await self.command("create", "--name", agent, "--network", network, "--read-only",
                     "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", str(os.getuid()),
                     "--pids-limit", "256", "--memory", "1536m" if self.ollama else "4g",
                     *(["--memory-swap", "1536m"] if self.ollama else []), "--cpus", "2", "--label", "netclaw.spec=179" if "cluster" in payload else "netclaw.spec=176" if self.ollama else "netclaw.spec=171",
                     "--tmpfs", f"/home/agent:rw,noexec,nosuid,size=128m,uid={os.getuid()},gid={os.getgid()},mode=700",
                     "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m", "--mount",
                     f"type=bind,src={agent_files},dst=/run/netclaw,readonly",
                     "--env-file", str(operation_root / "agent.env"), "--env", "HOME=/home/agent",
                     *native_env, "--env", "NO_COLOR=1", self.config["agent_image"], *native_args)
                inspected = json.loads(await self.command("inspect", agent))[0]
                net = json.loads(await self.command("network", "inspect", network))[0]
                evidence = inspect_agent(inspected, net, image=self.config["agent_image"],
                                         mounts={"/run/netclaw": agent_files}, harness=harness, ollama=self.ollama)
                private_write(operation_root / "containment.json", canonical(evidence))
                started.append(agent)
                await self.command("start", agent)
                async def observe_resources():
                    while len(resource_observations) < 80:
                        try:
                            for resource_name in (agent, self.ollama['model_container_id']):
                                raw_sample = (await self.command('stats', '--no-stream', '--format', '{{json .}}', resource_name, timeout=10)).strip()
                                if not raw_sample: continue  # Exited agent, not a zero-memory measurement.
                                sample = json.loads(raw_sample)
                                if any(not isinstance(sample.get(key), str) or len(sample[key]) > 200 for key in ('CPUPerc', 'MemUsage', 'PIDs')):
                                    raise RuntimeRefused('ollama_resource_accounting_unavailable')
                                resource_observations.append({'role': 'agent' if resource_name == agent else 'model',
                                    'elapsed_ms': int((time.monotonic()-started_monotonic)*1000),
                                    **{key: sample[key] for key in ('CPUPerc', 'MemUsage', 'PIDs')}})
                        except (RuntimeRefused, ValueError):
                            return
                        await asyncio.sleep(5)
                if self.ollama: resource_task = asyncio.create_task(observe_resources())
                exit_status = (await self.command("wait", agent, timeout=210)).strip()
                raw = await self.command("logs", agent)
                private_write(operation_root / "agent-output.json", raw)
                if broker.evidence is None:
                    if broker.claimed:
                        raise RuntimeUnknown("tool_claim_without_evidence")
                    raise RuntimeRefused("agent_produced_no_tool_evidence")
                # Retain real tool evidence even when the summary failed. A
                # finished read does not establish successful model completion.
                answer = self.fence.final_answer(operation_id)
                if exit_status != b"0":
                    raise RuntimeRefused("agent_summary_failed")
                if token in answer or self.guard_token in answer:
                    raise RuntimeRefused("capability_in_model_output")
                local_usage = {}
                if self.ollama:
                    if resource_task:
                        resource_task.cancel(); await asyncio.gather(resource_task, return_exceptions=True)
                    if not {'agent', 'model'}.issubset({row['role'] for row in resource_observations}):
                        raise RuntimeRefused('ollama_resource_accounting_unavailable')
                    local_usage = {'provider_usage': self.fence.usage(operation_id), 'elapsed_ms': int((time.monotonic()-started_monotonic)*1000),
                                   'resource_observations': resource_observations, 'provider_api_charges_microusd': 0}
                    private_write(operation_root/'ollama-accounting.json', canonical(local_usage))
                return {"output": {"tool": broker.evidence, "model_answer": answer},
                        "tool_evidence": broker.evidence,
                        "usage": {"inference_calls": self.fence.count(operation_id),
                                  "tool_calls": 1, "provider_usage": "unavailable", **local_usage},
                        "effective_model_profile": payload["model_profile"]}
        except BaseException as group:
            # `mcp.session_manager.run()` is an anyio task group: a refusal raised in its body leaves as an
            # ExceptionGroup, which the member then cannot classify (not a ProtectedError), so it recorded
            # `outcome_unknown` and sent no result even though no effect was ever claimed (live finding, hosted
            # NetBox member: guard_not_ready). Hosted only: re-raise the single reviewed Protected* error unchanged so
            # the member's existing rules apply (an unclaimed effect becomes a signed refusal; an unknown stays unknown).
            single = _single_protected_error(group) if getattr(self, 'hosted', None) is not None else None
            if single is not None:
                raise single from None
            raise
        finally:
            # No retries or new containers after interruption. Keep named stopped
            # containers, private evidence and claims for inspection/reconciliation.
            unresolved = []
            if resource_task:
                resource_task.cancel(); await asyncio.gather(resource_task, return_exceptions=True)
            for name in reversed(started):
                try:
                    await self.command("stop", "--time", "8", name, timeout=15)
                    stopped = json.loads(await self.command("inspect", name))[0]
                    if stopped.get("State", {}).get("Running"):
                        raise RuntimeUnknown("owned_runtime_still_running")
                except Exception:
                    unresolved.append(name)
            try:
                server.should_exit = True
                if server_task:
                    try:
                        await asyncio.wait_for(server_task, 10)
                    except (Exception, asyncio.CancelledError):
                        server.force_exit = True
                        server_task.cancel()
                        unresolved.append("owned_http_server")
            finally:
                listener.close()
                self.guards.pop(operation_id, None)
            try:
                private_write(operation_root / "cleanup.json", canonical({"owned": started, "unresolved": unresolved}))
            except Exception:
                raise RuntimeUnknown("owned_runtime_cleanup_evidence_unavailable") from None
            if unresolved:
                raise RuntimeUnknown("owned_runtime_stop_unconfirmed")
