"""Owned Docker adapter for R02. Inspection is evidence, not a systemd claim."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import socket
import time
from urllib.parse import urlparse

from .protected_runtime import (ExactToolBroker, InferenceFence, RuntimeRefused,
                                RuntimeUnknown, ScopedInference, canonical,
                                invoke_pyats, private_directory, private_write)


def inspect_agent(container, network, *, image, mounts, uid=None, gid=None, harness="openclaw"):
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


def openclaw_config(payload, relay):
    model = payload["model_profile"]["model"]
    return {
        "models": {"mode": "replace", "providers": {"defenseclaw": {
            "baseUrl": f"http://{relay}:8090/v1", "api": "openai-completions",
            "apiKey": "${NETCLAW_OPERATION_TOKEN}", "authHeader": True,
            "models": [{"id": model, "name": model, "reasoning": False,
                        "input": ["text"], "contextWindow": 200000, "maxTokens": 2048}]} }},
        "agents": {"defaults": {"model": {"primary": "defenseclaw/" + model, "fallbacks": []},
                                "workspace": "/home/agent/workspace", "skipBootstrap": True,
                                "maxConcurrent": 1}},
        "mcp": {"servers": {"approved": {"url": f"http://{relay}:8090/mcp",
                "transport": "streamable-http", "supportsParallelToolCalls": False,
                "timeout": 150, "connectTimeout": 10,
                "headers": {"Authorization": "Bearer ${NETCLAW_OPERATION_TOKEN}"},
                "toolFilter": {"include": ["pyats_run_show_command"]}}}},
        "tools": {"allow": ["approved__pyats_run_show_command"],
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
        self.config, self.manager = config, manager
        self.state = private_directory(config["state_dir"])
        self.docker = config.get("docker", "/usr/local/bin/docker")
        for name in ("agent_image", "relay_image"):
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", config[name]):
                raise RuntimeRefused("immutable_runtime_image_required")
        endpoint = urlparse(config["guard_url"])
        if endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1" or endpoint.path not in ("", "/"):
            raise RuntimeRefused("private_fixed_guard_required")
        key = config["guard_token_env"]
        if not re.fullmatch(r"NETCLAW_[A-Z0-9_]+", key) or not os.environ.get(key):
            raise RuntimeRefused("guard_credential_unavailable")
        self.guard_token = os.environ[key]
        self.pool = ipaddress.IPv4Network(config["sandbox_address_pool"])
        if self.pool.prefixlen > 24 or not self.pool.subnet_of(ipaddress.IPv4Network("198.18.0.0/15")):
            raise RuntimeRefused("reviewed_benchmark_address_pool_required")
        self.fence = InferenceFence(self.state / "inference.sqlite")

    async def command(self, *args, timeout=60):
        process = await asyncio.create_subprocess_exec(self.docker, *args,
                   stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                   env={"PATH": os.defpath, "HOME": str(Path.home())})
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
        except BaseException:
            # This only kills the Docker client. The owned container may remain;
            # retain the durable operation fence and report an unknown outcome.
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise RuntimeUnknown("docker_client_interrupted") from None
        if process.returncode != 0:
            raise RuntimeRefused("docker_operation_failed")
        if len(stdout) > 4 * 1024 * 1024:
            raise RuntimeUnknown("docker_output_bound")
        return stdout

    async def forward(self, payload, request):
        import httpx
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False,
                                     timeout=payload["limits"]["inference_timeout_ms"] / 1000) as client:
            async with client.stream("POST", self.config["guard_url"].rstrip("/") + "/v1/chat/completions",
                     headers={"X-DC-Auth": self.guard_token, "Content-Type": "application/json"},
                     content=canonical(request)) as response:
                if response.status_code != 200:
                    raise RuntimeUnknown("guard_request_not_successful")
                output = bytearray()
                async for part in response.aiter_bytes():
                    output.extend(part)
                    if len(output) > 1048576:
                        raise RuntimeUnknown("guard_response_bound")
                return json.loads(output)

    async def run(self, payload, gate):
        from mcp.server.mcpserver import MCPServer
        from starlette.responses import JSONResponse, Response
        import uvicorn
        if payload["model_profile"] != self.config["model_profile"]:
            raise RuntimeRefused("runtime_profile_changed")
        operation_id = payload["operation_id"]
        # Reusing a home is forbidden even if a prior launch left no process.
        operation_root = self.state / operation_id
        operation_root.mkdir(mode=0o700, exist_ok=False)
        agent_files = private_directory(operation_root / "agent")
        token = secrets.token_urlsafe(32)
        suffix = hashlib.sha256(operation_id.encode()).hexdigest()[:20]
        prefix = "netclaw-r02-" + suffix
        network, relay, agent = prefix + "-net", prefix + "-relay", prefix + "-agent"
        harness = payload["model_profile"]["runtime_kind"]
        if harness == "openclaw":
            private_write(agent_files / "openclaw.json", canonical(openclaw_config(payload, relay)))
        elif harness == "hermes":
            private_write(agent_files / "job.json", canonical({"operation_id": operation_id,
                          "model": payload["model_profile"]["model"],
                          "base_url": f"http://{relay}:8090/v1", "mcp_url": f"http://{relay}:8090/mcp",
                          "arguments": payload["tool_call"]["arguments"]}))
        else:
            raise RuntimeRefused("unqualified_harness")
        private_write(operation_root / "agent.env", ("NETCLAW_OPERATION_TOKEN=" + token + "\n").encode())

        async def invoke(tool, arguments):
            return await invoke_pyats(self.config["pyats"], arguments, operation_root / "tool")

        broker = ExactToolBroker(payload, gate, invoke)
        facade = ScopedInference(payload, token, self.fence,
                                  lambda request: self.forward(payload, request),
                                  tool_finished=lambda: broker.evidence is not None)
        mcp = MCPServer("Approved NetClaw operation", version="171")

        async def pyats_run_show_command(device_name: str, command: str, timeout: int, retries: int) -> dict:
            return await broker.call("pyats_run_show_command",
                      dict(device_name=device_name, command=command, timeout=timeout, retries=retries))

        mcp.add_tool(pyats_run_show_command, description="The exact owner-approved show version read.")
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
            if scope["path"] == "/mcp":
                return await mcp_app(scope, receive, send)
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
                body = json.loads(raw)
                response = await facade.invoke("POST", scope["path"],
                      {key.decode(): value.decode() for key, value in headers.items()}, body)
                if body.get("stream"):
                    reply = Response(completion_sse(response), media_type="text/event-stream")
                else:
                    reply = JSONResponse(response)
            except RuntimeRefused:
                reply = JSONResponse({"error": "inference_refused"}, status_code=403)
            except Exception:
                reply = JSONResponse({"error": "inference_outcome_unknown"}, status_code=502)
            return await reply(scope, receive, send)

        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen(64)
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False, lifespan="off"))
        server_task = None
        started = []
        try:
            async with mcp.session_manager.run():
                server_task = asyncio.create_task(server.serve(sockets=[listener]))
                # Explicit reviewed local-only pool avoids consuming Docker's
                # host-wide default pools. Docker refuses a collision before
                # starting any agent/provider. Never remove another network.
                count = self.pool.num_addresses // 16
                offset = int(suffix, 16) % count
                subnet = str(ipaddress.IPv4Network((int(self.pool.network_address) + offset * 16, 28)))
                await self.command("network", "create", "--internal", "--opt",
                     "com.docker.network.bridge.gateway_mode_ipv4=isolated", "--subnet", subnet,
                     "--label", "netclaw.spec=171", network)
                # Relay alone has a second network to the fixed host endpoint.
                await self.command("create", "--name", relay, "--network", "bridge", "--read-only",
                     "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", str(os.getuid()),
                     "--pids-limit", "64", "--memory", "128m", "--cpus", "0.5", "--label", "netclaw.spec=171",
                     "--env", "NETCLAW_TRUSTED_PORT=" + str(port), self.config["relay_image"])
                await self.command("network", "connect", "--alias", relay, network, relay)
                await self.command("start", relay)
                started.append(relay)
                prompt = ("Execute the single owner-approved MCP read exactly once using pyats_run_show_command. "
                          "Use these exact arguments: " + canonical(payload["tool_call"]["arguments"]).decode()
                          + ". Then summarize the returned version evidence. Do not use other tools or retry.")
                native_env = (["--env", "OPENCLAW_CONFIG_PATH=/run/netclaw/openclaw.json",
                               "--env", "OPENCLAW_STATE_DIR=/home/agent/state"] if harness == "openclaw" else [])
                native_args = (["agent", "--local", "--json", "--session-id", operation_id,
                                "--message", prompt, "--timeout", "180"] if harness == "openclaw" else [])
                await self.command("create", "--name", agent, "--network", network, "--read-only",
                     "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", str(os.getuid()),
                     "--pids-limit", "256", "--memory", "4g", "--cpus", "2", "--label", "netclaw.spec=171",
                     "--tmpfs", f"/home/agent:rw,noexec,nosuid,size=128m,uid={os.getuid()},gid={os.getgid()},mode=700",
                     "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m", "--mount",
                     f"type=bind,src={agent_files},dst=/run/netclaw,readonly",
                     "--env-file", str(operation_root / "agent.env"), "--env", "HOME=/home/agent",
                     *native_env, "--env", "NO_COLOR=1", self.config["agent_image"], *native_args)
                inspected = json.loads(await self.command("inspect", agent))[0]
                net = json.loads(await self.command("network", "inspect", network))[0]
                evidence = inspect_agent(inspected, net, image=self.config["agent_image"],
                                         mounts={"/run/netclaw": agent_files}, harness=harness)
                private_write(operation_root / "containment.json", canonical(evidence))
                await self.command("start", agent)
                started.append(agent)
                await self.command("wait", agent, timeout=210)
                raw = await self.command("logs", agent)
                private_write(operation_root / "agent-output.json", raw)
                if broker.evidence is None:
                    if broker.claimed:
                        raise RuntimeUnknown("tool_claim_without_evidence")
                    raise RuntimeRefused("agent_produced_no_tool_evidence")
                return {"output": {"tool": broker.evidence, "agent": raw.decode(errors="replace")},
                        "tool_evidence": broker.evidence,
                        "usage": {"inference_calls": self.fence.count(operation_id),
                                  "tool_calls": 1, "provider_usage": "unavailable"},
                        "effective_model_profile": payload["model_profile"]}
        finally:
            # No retries or new containers after interruption. Keep named stopped
            # containers, private evidence and claims for inspection/reconciliation.
            for name in reversed(started):
                try:
                    await self.command("stop", "--time", "3", name, timeout=10)
                except Exception:
                    pass
            server.should_exit = True
            if server_task:
                await server_task
            listener.close()
