"""Opt-in R02 runtime boundaries; no provider/device credentials reach the agent.

The trusted host owns Docker and the stdio MCP child. An isolated agent network
reaches only an owned relay, which forwards HTTP to this process's fixed loopback
listener. The agent never receives the guard credential, Docker socket or testbed.
"""
import asyncio
import contextlib
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import time
import uuid
from .protected_contract import ProtectedError, ProtectedOutcomeUnknown


class RuntimeRefused(ProtectedError):
    pass


class RuntimeUnknown(ProtectedOutcomeUnknown):
    """A durable claim may have reached its upstream; do not retry."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def private_directory(path):
    path = Path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeRefused("unsafe_private_directory")
    # Reject a symlink in any existing ancestor, not only the leaf.
    if path.absolute() != path.resolve():
        raise RuntimeRefused("symlink_private_directory")
    return path


def private_write(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + "." + secrets.token_hex(8))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        parent = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if temporary.exists():
            temporary.unlink()


class InferenceFence:
    """Durably count forwards, including unknown outcomes and process restarts."""
    def __init__(self, database):
        database = Path(database)
        private_directory(database.parent)
        if database.exists():
            info = database.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise RuntimeRefused("unsafe_inference_ledger")
        fd = os.open(database, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        self.db = sqlite3.connect(database, timeout=10, isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS protected_inference (
            operation_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
            request_sha256 TEXT NOT NULL, state TEXT NOT NULL,
            response_sha256 TEXT, PRIMARY KEY(operation_id,ordinal),
            UNIQUE(operation_id,request_sha256))""")
        if "response_json" not in {row[1] for row in self.db.execute("PRAGMA table_info(protected_inference)")}:
            self.db.execute("ALTER TABLE protected_inference ADD COLUMN response_json TEXT")

    def claim(self, operation_id, request, *, tool_finished=False):
        hashed = sha(request)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self.db.execute("SELECT * FROM protected_inference WHERE operation_id=? ORDER BY ordinal",
                                   (operation_id,)).fetchall()
            if (len(rows) >= 2 or any(row[2] == hashed for row in rows)
                    or (rows and (rows[-1][3] != "finished" or not tool_finished))):
                raise RuntimeRefused("inference_spent_or_unreconciled")
            ordinal = len(rows) + 1
            self.db.execute("INSERT INTO protected_inference(operation_id,ordinal,request_sha256,state) VALUES (?,?,?,'claimed')",
                            (operation_id, ordinal, hashed))
            self.db.execute("COMMIT")
            return ordinal
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def finish(self, operation_id, ordinal, response):
        changed = self.db.execute("""UPDATE protected_inference SET state='finished',response_sha256=?,response_json=?
            WHERE operation_id=? AND ordinal=? AND state='claimed'""",
                                  (sha(response), canonical(response).decode(), operation_id, ordinal)).rowcount
        if changed != 1:
            raise RuntimeUnknown("inference_result_conflict")

    def count(self, operation_id):
        return self.db.execute("SELECT COUNT(*) FROM protected_inference WHERE operation_id=?",
                               (operation_id,)).fetchone()[0]

    def first_response(self, operation_id):
        row = self.db.execute("SELECT state,response_json FROM protected_inference WHERE operation_id=? AND ordinal=1", (operation_id,)).fetchone()
        if row is None: return None
        if row[0] != 'finished' or row[1] is None: raise RuntimeUnknown('inference_outcome_unknown')
        return json.loads(row[1])

    def final_answer(self, operation_id):
        rows = self.db.execute("SELECT state,response_json FROM protected_inference WHERE operation_id=? ORDER BY ordinal",
                               (operation_id,)).fetchall()
        if any(state != "finished" or response is None for state, response in rows):
            raise RuntimeUnknown("inference_outcome_unknown")
        if len(rows) != 2:
            raise RuntimeRefused("guarded_summary_missing")
        response = json.loads(rows[-1][1])
        choices = response.get("choices", [])
        if len(choices) != 1:
            raise RuntimeRefused("guarded_summary_invalid")
        choice = choices[0]
        message = choice.get("message") or {}
        if (choice.get("finish_reason") != "stop" or message.get("role") != "assistant"
                or message.get("tool_calls") or not isinstance(message.get("content"), str)
                or not message["content"].strip()):
            raise RuntimeRefused("guarded_summary_invalid")
        return message["content"]

    def usage(self, operation_id):
        rows = self.db.execute("SELECT state,response_json FROM protected_inference WHERE operation_id=? ORDER BY ordinal", (operation_id,)).fetchall()
        if len(rows) != 2 or any(state != 'finished' or response is None for state, response in rows):
            raise RuntimeUnknown('inference_usage_unavailable')
        receipts = [json.loads(response).get('usage', {}) for _, response in rows]
        for receipt in receipts:
            if (any(type(receipt.get(key)) is not int or receipt[key] < 0 for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'))
                    or receipt['total_tokens'] <= 0 or receipt['prompt_tokens'] + receipt['completion_tokens'] != receipt['total_tokens']):
                raise RuntimeUnknown('inference_usage_unavailable')
        return {key: sum(row[key] for row in receipts) for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}

    def close(self):
        self.db.close()


class ScopedInference:
    """No routing/authentication header from the agent reaches DefenseClaw."""
    def __init__(self, payload, token, fence, forward, *, tool_finished=lambda: False,
                 clock_ms=lambda: int(time.time() * 1000), request_adapter=None, response_validator=None, runner_latch=None,
                 ha_admission=None):
        validate_ha_gate(payload, ha_admission)
        self.payload, self.token, self.fence, self.forward = payload, token, fence, forward
        self.tool_finished, self.clock_ms = tool_finished, clock_ms
        self.request_adapter, self.response_validator, self.runner_latch = request_adapter, response_validator, runner_latch
        self.ha_admission = ha_admission

    async def invoke(self, method, path, headers, body):
        if method != "POST" or path != "/v1/chat/completions":
            raise RuntimeRefused("inference_route_refused")
        auth = headers.get("authorization", "")
        if not hmac.compare_digest(auth, "Bearer " + self.token):
            raise RuntimeRefused("inference_capability_refused")
        if self.clock_ms() >= self.payload["limits"]["expires_at_ms"]:
            raise RuntimeRefused("approval_expired")
        if not isinstance(body, dict) or len(canonical(body)) > 1024 * 1024:
            raise RuntimeRefused("inference_request_bound")
        if body.get("model") != self.payload["model_profile"]["model"]:
            raise RuntimeRefused("inference_model_changed")
        # Non-streaming makes a complete bounded provider receipt durable before
        # delivering it. Clients cannot choose passthrough, URLs or auth fields.
        allowed = {"model", "messages", "tools", "tool_choice", "parallel_tool_calls",
                   "temperature", "top_p", "max_tokens", "max_completion_tokens",
                   "stream", "stream_options", "reasoning_effort"}
        if set(body) - allowed or not isinstance(body.get("messages"), list):
            raise RuntimeRefused("inference_fields_refused")
        request = dict(body)
        request["stream"] = False
        request.pop("stream_options", None)
        request["parallel_tool_calls"] = False
        # The qualified guard does not translate max_completion_tokens and
        # otherwise selects its much larger vendor default. Normalize at this
        # trusted boundary, without widening the provider fence's token cap.
        token_fields = set(request) & {"max_tokens", "max_completion_tokens"}
        if len(token_fields) > 1:
            raise RuntimeRefused("ambiguous_inference_token_limit")
        maximum = request.pop(next(iter(token_fields))) if token_fields else 2048
        if type(maximum) is not int or not 1 <= maximum <= 4096:
            raise RuntimeRefused("inference_token_limit_refused")
        request["max_tokens"] = maximum
        if self.request_adapter is not None:
            if any(key.lower().startswith('x-dc-') for key in headers):
                raise RuntimeRefused('caller_guard_routing_header_refused')
            try: request = self.request_adapter(request)
            except ValueError as exc: raise RuntimeRefused(getattr(exc, 'code', 'inference_profile_refused')) from None
        ordinal = self.fence.claim(self.payload["operation_id"], request,
                                   tool_finished=self.tool_finished())
        reservation = None
        if self.runner_latch is not None:
            try: reservation = self.runner_latch.begin(self.payload['operation_id'], sha(request))
            except ValueError as exc: raise RuntimeRefused(getattr(exc, 'code', 'runner_recovery_required')) from None
        try:
            # Only the fixed trusted callback supplies guard URL and credential.
            remaining = (self.payload["limits"]["expires_at_ms"] - self.clock_ms()) / 1000
            async with asyncio.timeout(min(remaining, self.payload["limits"]["inference_timeout_ms"] / 1000)):
                if self.ha_admission is not None:
                    response = await self.ha_admission('model', ordinal, sha(request), lambda: self.forward(request))
                else:
                    response = await self.forward(request)
            if not isinstance(response, dict) or len(canonical(response)) > 1024 * 1024:
                raise RuntimeUnknown("inference_response_bound")
            if self.response_validator is not None:
                response = self.response_validator(response, ordinal)
            self.fence.finish(self.payload["operation_id"], ordinal, response)
            if reservation is not None: self.runner_latch.complete(reservation)
            return response
        except BaseException as exc:
            if reservation is not None:
                try: self.runner_latch.uncertain(reservation)
                except Exception: pass  # A failed durable transition stays non-idle; never release it.
            raise RuntimeUnknown("inference_outcome_unknown") from exc


def validate_ha_gate(payload, admission):
    """Explicit HA payloads cannot enter any legacy unbound execution path."""
    if 'cluster' in payload:
        from .protected_contract import validate_cluster_binding
        validate_cluster_binding(payload['cluster'])
        if not callable(admission):
            raise RuntimeRefused('ha_runtime_unqualified')
    elif admission is not None:
        raise RuntimeRefused('ha_payload_required')


class ExactToolBroker:
    def __init__(self, payload, gate, invoke):
        self.payload, self.gate, self.invoke = payload, gate, invoke
        self.evidence = None
        self.claimed = False

    async def call(self, tool, arguments):
        approved = self.payload["tool_call"]
        if tool != approved["tool"] or canonical(arguments) != canonical(approved["arguments"]):
            raise RuntimeRefused("tool_arguments_changed")
        if self.claimed:
            raise RuntimeRefused("tool_already_claimed")
        self.claimed = True

        async def effect():
            result = await self.invoke(tool, arguments)
            self.evidence = result
            return result

        return await self.gate(dict(approved), effect)


_PYATS_CREDENTIAL_NAMES = ("PYATS_R02_USERNAME", "PYATS_R02_PASSWORD", "PYATS_R02_ENABLE_PASSWORD")


def pyats_credentials(config):
    """Scoped device credentials for the one child. Spec 182 (HA member): a launcher-started member cannot receive extra
    environment variables, so an optional private `credential_file` (exactly the three reviewed names, 0600, owner-only,
    canonical path) supplies them instead; otherwise the original environment-only behaviour is unchanged. Values are
    never logged and only reach the child's environment."""
    names = config.get("credential_env", [])
    path = config.get("credential_file")
    if path is None:
        found = {}
        for name in names:
            if name not in _PYATS_CREDENTIAL_NAMES or name not in os.environ:
                raise RuntimeRefused("missing_scoped_device_credential")
            found[name] = os.environ[name]
        return found
    credential = Path(path)
    if not isinstance(path, str) or credential.absolute() != credential.resolve():
        raise RuntimeRefused("unsafe_credential_file")
    try:
        info = credential.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 4096):
            raise RuntimeRefused("unsafe_credential_file")
        text = credential.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise RuntimeRefused("unsafe_credential_file") from None
    found = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        name, separator, value = line.partition("=")
        if (not separator or name not in _PYATS_CREDENTIAL_NAMES or name in found or not value
                or any(ord(char) < 32 for char in value)):
            raise RuntimeRefused("unsafe_credential_file")
        found[name] = value
    if set(found) != set(names) or set(found) != set(_PYATS_CREDENTIAL_NAMES):
        raise RuntimeRefused("missing_scoped_device_credential")
    return found


async def invoke_pyats(config, arguments, operation_root, *, ha_required=False, ha_admission=None):
    """The approved effect is a private official MCP stdio invocation.

    Spec 182 (HA member): with `ha_required` the single tools/call is written through the HA stdio transport after a fresh
    effect admission, exactly as `protected_mcp.invoke_mcp` does for the calculator and NetBox reads. Without it (the
    original R02 path) behaviour is unchanged."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    if ha_required:
        if not callable(ha_admission):
            raise RuntimeRefused("ha_runtime_unqualified")
        from .ha.mcp_transport import ha_stdio_client
        stdio_client = ha_stdio_client
    operation_root = private_directory(operation_root)
    approved = operation_root / "approved-arguments.json"
    private_write(approved, canonical(arguments))
    source = Path(config["upstream"])
    manifest = config["source_sha256"]
    if set(manifest) != {"pyats_mcp_server.py", "pyats_testbed_builder.py", "pyats_tasks.py"}:
        raise RuntimeRefused("pyats_source_closure_required")
    frozen_source = private_directory(operation_root / "source")
    for name, digest in manifest.items():
        raw_source = (source.parent / name).read_bytes()
        if hashlib.sha256(raw_source).hexdigest() != digest:
            raise RuntimeRefused("pyats_source_changed")
        private_write(frozen_source / name, raw_source)
        os.chmod(frozen_source / name, 0o400)
    source = frozen_source / "pyats_mcp_server.py"
    if manifest[source.name] != config["upstream_sha256"]:
        raise RuntimeRefused("pyats_source_changed")
    private_write(operation_root / "source-manifest.json", canonical(manifest))
    os.chmod(frozen_source, 0o500)
    testbed = Path(config["testbed"])
    info = testbed.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or testbed.absolute() != testbed.resolve()):
        raise RuntimeRefused("unsafe_private_testbed")
    raw_testbed = testbed.read_bytes()
    if hashlib.sha256(raw_testbed).hexdigest() != config["testbed_sha256"]:
        raise RuntimeRefused("testbed_revision_changed")
    known_hosts = Path(config["known_hosts"])
    known_info = known_hosts.lstat()
    if (not stat.S_ISREG(known_info.st_mode) or known_info.st_uid != os.getuid()
            or known_info.st_mode & 0o077 or known_hosts.absolute() != known_hosts.resolve()):
        raise RuntimeRefused("unsafe_known_hosts")
    host_keys = known_hosts.read_bytes()
    if hashlib.sha256(host_keys).hexdigest() != config["known_hosts_sha256"]:
        raise RuntimeRefused("known_hosts_changed")
    frozen_keys = operation_root / "known_hosts"
    private_write(frozen_keys, host_keys)
    os.chmod(frozen_keys, 0o400)
    import yaml
    document = yaml.safe_load(raw_testbed)
    connections = document["devices"][arguments["device_name"]]["connections"]
    names = set(connections) - {"defaults"}
    if len(names) != 1:
        raise RuntimeRefused("minimal_connection_required")
    connection = connections[next(iter(names))]
    prefix = "-F /dev/null -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=yes -o UserKnownHostsFile="
    if connection.get("ssh_options") != prefix + str(known_hosts):
        raise RuntimeRefused("reviewed_ssh_policy_changed")
    connection["ssh_options"] = prefix + str(frozen_keys)
    frozen_testbed = operation_root / "testbed.yaml"
    private_write(frozen_testbed, yaml.safe_dump(document, sort_keys=False).encode())
    private_write(operation_root / "inventory-binding.json", canonical({
        "reviewed_testbed_sha256": config["testbed_sha256"],
        "materialized_testbed_sha256": hashlib.sha256(frozen_testbed.read_bytes()).hexdigest(),
        "known_hosts_sha256": config["known_hosts_sha256"]}))
    scripts = Path(__file__).resolve().parents[4] / "scripts"
    adapters = config["adapter_sha256"]
    if set(adapters) != {"protected-tool-broker.py", "lib/protected_pyats.py"}:
        raise RuntimeRefused("adapter_source_closure_required")
    adapter_root = private_directory(operation_root / "adapter")
    private_directory(adapter_root / "lib")
    for name, expected in adapters.items():
        raw_adapter = (scripts / name).read_bytes()
        if hashlib.sha256(raw_adapter).hexdigest() != expected:
            raise RuntimeRefused("adapter_revision_changed")
        private_write(adapter_root / name, raw_adapter)
        os.chmod(adapter_root / name, 0o400)
    script = adapter_root / "protected-tool-broker.py"
    # Explicit small environment; no inherited provider keys, profiles or proxies.
    environment = {"PATH": os.defpath, "HOME": str(operation_root),
                   "PYTHONUNBUFFERED": "1", "PYTHON_DOTENV_DISABLED": "1",
                   "PYATS_TESTBED_PATH": str(frozen_testbed), "PYATS_MCP_CONN_CACHE_TTL": "0",
                   "PYATS_MCP_ARTIFACTS_DIR": str(operation_root / "pyats")}
    environment.update(pyats_credentials(config))
    params = StdioServerParameters(command=config["python"], env=environment,
                                   args=[str(script), "--upstream", str(source),
                                         "--upstream-sha256", config["upstream_sha256"],
                                         "--source-manifest", str(operation_root / "source-manifest.json"),
                                         "--endpoint-sha256", config["endpoint_sha256"],
                                         "--approved", str(approved),
                                         "--logfile", str(operation_root / "device.log")])
    with (operation_root / "pyats-stderr.log").open("w") as error_log:
        os.chmod(error_log.name, 0o600)
        async with stdio_client(params, errlog=error_log) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                if ha_required:
                    private_write(operation_root / "pyats-call.json", canonical(
                        {"tool": "pyats_run_show_command", "arguments": arguments, "state": "intent_prepared",
                         "prepared_at_ms": int(time.time() * 1000)}))

                async def call():
                    return await session.call_tool("pyats_run_show_command", arguments)

                # Process creation, initialization and every private file precede the fresh challenge; the HA transport
                # rechecks the consumed scope at the synchronous stdin handoff of the one tools/call.
                response = await ha_admission(call) if ha_required else await call()
                if response.is_error:
                    raise RuntimeUnknown("pyats_effect_failed")
                evidence = response.structured_content
                if evidence is None:
                    texts = [part.text for part in response.content if getattr(part, "type", None) == "text"]
                    if len(texts) != 1:
                        raise RuntimeUnknown("pyats_result_shape")
                    evidence = json.loads(texts[0])
                private_write(operation_root / "tool-evidence.json", canonical(evidence))
                return evidence


def build_executor(config, *, manager):
    # Presence of either wrapper discriminator commits to the strict wrapper
    # parser. A malformed wrapper must never fall back to a legacy executor.
    if isinstance(config, dict) and ('schemaVersion' in config or 'profiles' in config):
        from .protected_selection import ProfiledExecutor
        return ProfiledExecutor(config, manager=manager)
    from .protected_docker import DockerExecutor
    return DockerExecutor(config, manager=manager)
