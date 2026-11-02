"""Opt-in R02 runtime boundaries; no provider/device credentials reach the agent.

The trusted host owns Docker and the stdio MCP child. An isolated agent network
reaches only an owned relay, which forwards HTTP to this process over a Unix
socket. The agent never receives the guard credential, Docker socket or testbed.
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


class RuntimeRefused(ValueError):
    pass


class RuntimeUnknown(RuntimeError):
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
            self.db.execute("INSERT INTO protected_inference VALUES (?,?,?,'claimed',NULL)",
                            (operation_id, ordinal, hashed))
            self.db.execute("COMMIT")
            return ordinal
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def finish(self, operation_id, ordinal, response):
        changed = self.db.execute("""UPDATE protected_inference SET state='finished',response_sha256=?
            WHERE operation_id=? AND ordinal=? AND state='claimed'""",
                                  (sha(response), operation_id, ordinal)).rowcount
        if changed != 1:
            raise RuntimeUnknown("inference_result_conflict")

    def count(self, operation_id):
        return self.db.execute("SELECT COUNT(*) FROM protected_inference WHERE operation_id=?",
                               (operation_id,)).fetchone()[0]

    def close(self):
        self.db.close()


class ScopedInference:
    """No routing/authentication header from the agent reaches DefenseClaw."""
    def __init__(self, payload, token, fence, forward, *, tool_finished=lambda: False,
                 clock_ms=lambda: int(time.time() * 1000)):
        self.payload, self.token, self.fence, self.forward = payload, token, fence, forward
        self.tool_finished, self.clock_ms = tool_finished, clock_ms

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
        ordinal = self.fence.claim(self.payload["operation_id"], request,
                                   tool_finished=self.tool_finished())
        try:
            # Only the fixed trusted callback supplies guard URL and credential.
            response = await self.forward(request)
            if not isinstance(response, dict) or len(canonical(response)) > 1024 * 1024:
                raise RuntimeUnknown("inference_response_bound")
            self.fence.finish(self.payload["operation_id"], ordinal, response)
            return response
        except BaseException as exc:
            raise RuntimeUnknown("inference_outcome_unknown") from exc


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


async def invoke_pyats(config, arguments, operation_root):
    """The approved effect is a private official MCP stdio invocation."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    operation_root = private_directory(operation_root)
    approved = operation_root / "approved-arguments.json"
    private_write(approved, canonical(arguments))
    source = Path(config["upstream"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != config["upstream_sha256"]:
        raise RuntimeRefused("pyats_source_changed")
    script = Path(__file__).resolve().parents[4] / "scripts" / "protected-tool-broker.py"
    # Explicit small environment; no inherited provider keys, profiles or proxies.
    environment = {"PATH": os.defpath, "HOME": str(operation_root),
                   "PYTHONUNBUFFERED": "1", "PYTHON_DOTENV_DISABLED": "1",
                   "PYATS_TESTBED_PATH": config["testbed"], "PYATS_MCP_CONN_CACHE_TTL": "0",
                   "PYATS_MCP_ARTIFACTS_DIR": str(operation_root / "pyats")}
    for name in config.get("credential_env", []):
        if not name.startswith("PYATS_") or name not in os.environ:
            raise RuntimeRefused("missing_scoped_device_credential")
        environment[name] = os.environ[name]
    params = StdioServerParameters(command=config["python"], env=environment,
                                   args=[str(script), "--upstream", str(source),
                                         "--upstream-sha256", config["upstream_sha256"],
                                         "--approved", str(approved),
                                         "--logfile", str(operation_root / "device.log")])
    with (operation_root / "pyats-stderr.log").open("w") as error_log:
        os.chmod(error_log.name, 0o600)
        async with stdio_client(params, errlog=error_log) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                response = await session.call_tool("pyats_run_show_command", arguments)
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
    from .protected_docker import DockerExecutor
    return DockerExecutor(config, manager=manager)
