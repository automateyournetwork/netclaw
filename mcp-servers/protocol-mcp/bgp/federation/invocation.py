"""N2N remote invocation (US2): inbound execution + outbound requests.

Two execution paths (research.md R3):
  - Tools: spawn the target MCP server via stdio, initialize → tools/call. No
    LLM. DefenseClaw inspection runs first when security.mode == defenseclaw.
  - Skills: delegated to the local OpenClaw gateway as a chat completion under
    the remote operator's own model, policies, and budget.

Wire methods (contracts/n2n-wire-protocol.md): n2n/tools/call, n2n/tasks/submit.
Inbound = authorize → (approval hold) → execute → audit. Outbound requests are
issued from the daemon HTTP API via the service.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from .channel import (
    RpcError, ERR_NOT_ALLOWLISTED, ERR_APPROVAL_PENDING, ERR_APPROVAL_EXPIRED,
    ERR_BUDGET_EXHAUSTED, ERR_RATE_LIMITED, ERR_EXECUTION_TIMEOUT, ERR_SEVERED,
    ERR_GUARDRAIL_BLOCKED,
)

logger = logging.getLogger("n2n.invocation")

_CODE_MAP = {
    "not_allowlisted": ERR_NOT_ALLOWLISTED,
    "approval_required": ERR_APPROVAL_PENDING,
    "approval_expired": ERR_APPROVAL_EXPIRED,
    "budget_exhausted": ERR_BUDGET_EXHAUSTED,
    "rate_limited": ERR_RATE_LIMITED,
    "severed": ERR_SEVERED,
    "guardrail_blocked": ERR_GUARDRAIL_BLOCKED,
    "timeout": ERR_EXECUTION_TIMEOUT,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _openclaw_config() -> dict:
    for p in (_repo_root() / "config" / "openclaw.json",
              Path(os.path.expanduser("~/.openclaw/openclaw.json"))):
        try:
            return json.loads(p.read_text())
        except Exception:
            continue
    return {}


def _security_mode() -> str:
    try:
        cfg = json.loads(Path(os.path.expanduser("~/.openclaw/openclaw.json")).read_text())
        return (cfg.get("security") or {}).get("mode", "hobby")
    except Exception:
        return "hobby"


async def _defenseclaw_inspect(tool: str, arguments: dict) -> bool:
    """Return True if allowed. Runs only when security.mode == defenseclaw (FR-014)."""
    if _security_mode() != "defenseclaw":
        return True
    try:
        proc = await asyncio.create_subprocess_exec(
            "defenseclaw", "tool", "inspect", tool,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(proc.communicate(json.dumps(arguments).encode()), timeout=15)
        return proc.returncode == 0
    except FileNotFoundError:
        logger.warning("security.mode=defenseclaw but 'defenseclaw' CLI not found — denying tool")
        return False
    except Exception as e:
        logger.warning("DefenseClaw inspection error (%s) — denying", e)
        return False


class Invoker:
    def __init__(self, service):
        self.service = service
        self.manager = service.manager
        self.authz = service.authz
        self.audit = service.audit
        self.tool_timeout = int(os.environ.get("N2N_TOOL_TIMEOUT_S", "120"))
        self.skill_timeout = int(os.environ.get("N2N_SKILL_TIMEOUT_S", "600"))

    # ---- inbound: a peer asks US to run something ----------------------

    async def handle_tools_call(self, channel, params):
        peer = channel.peer_identity
        tool = params.get("tool", "")
        arguments = params.get("arguments") or {}
        req_id = params.get("request_id", "")
        decision = self.authz.authorize(peer, "tool", tool)

        if not decision.allowed and decision.code != "approval_required":
            self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                              target_name=tool, request_id=req_id, decision=decision.code, outcome="denied")
            raise RpcError(_CODE_MAP.get(decision.code, -32000), decision.reason)

        if decision.code == "approval_required":
            inv_id = self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                                       target_name=tool, request_id=req_id, decision="approval_required",
                                       outcome="pending")
            appr = self.authz.create_approval(inv_id)
            self.service.notify_approval(inv_id, peer, "tool", tool)
            if not await self._await_approval(appr["approval_id"]):
                raise RpcError(ERR_APPROVAL_EXPIRED, "approval not granted")

        if not await _defenseclaw_inspect(tool, arguments):
            self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                              target_name=tool, request_id=req_id, decision="guardrail_blocked", outcome="denied")
            raise RpcError(ERR_GUARDRAIL_BLOCKED, "DefenseClaw inspection blocked the call")

        self.authz.debit(peer, requests=1)
        try:
            result = await self._exec_tool_stdio(tool, arguments)
            ref = self.audit.store_result(req_id or f"{peer}-{tool}", result)
            self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                              target_name=tool, request_id=req_id, decision="allowlisted",
                              outcome="success", result_ref=ref)
            return result
        except asyncio.TimeoutError:
            self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                              target_name=tool, request_id=req_id, decision="allowlisted", outcome="timeout")
            raise RpcError(ERR_EXECUTION_TIMEOUT, f"tool {tool} timed out")

    async def handle_task_submit(self, channel, params):
        peer = channel.peer_identity
        skill = params.get("skill", "")
        input_text = params.get("input_text", "")
        req_id = params.get("request_id", "")
        decision = self.authz.authorize(peer, "skill", skill)

        if not decision.allowed and decision.code != "approval_required":
            self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                              target_name=skill, request_id=req_id, decision=decision.code, outcome="denied")
            raise RpcError(_CODE_MAP.get(decision.code, -32000), decision.reason)

        if decision.code == "approval_required":
            inv_id = self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                                       target_name=skill, request_id=req_id, decision="approval_required",
                                       outcome="pending")
            appr = self.authz.create_approval(inv_id)
            self.service.notify_approval(inv_id, peer, "skill", skill)
            if not await self._await_approval(appr["approval_id"]):
                raise RpcError(ERR_APPROVAL_EXPIRED, "approval not granted")

        try:
            output, tokens = await self._exec_skill_gateway(skill, input_text)
            self.authz.debit(peer, requests=1, tokens=tokens)
            ref = self.audit.store_result(req_id or f"{peer}-{skill}", {"output_text": output})
            self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                              target_name=skill, request_id=req_id, decision="allowlisted",
                              outcome="success", result_ref=ref)
            return {"status": "completed", "output_text": output, "tokens_used": tokens}
        except asyncio.TimeoutError:
            self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                              target_name=skill, request_id=req_id, decision="allowlisted", outcome="timeout")
            raise RpcError(ERR_EXECUTION_TIMEOUT, f"skill {skill} timed out")

    async def _await_approval(self, approval_id: int) -> bool:
        deadline = time.time() + self.authz.approval_window_s
        while time.time() < deadline:
            status = self.authz.approval_status(approval_id)
            if status == "approved":
                return True
            if status in ("denied", "expired"):
                return False
            await asyncio.sleep(1.0)
        return False

    # ---- executors ----------------------------------------------------

    async def _exec_tool_stdio(self, tool: str, arguments: dict) -> dict:
        """Spawn the target MCP server and perform initialize → tools/call."""
        if "/" not in tool:
            raise RpcError(-32602, "tool must be 'server_id/tool_name'")
        server_id, tool_name = tool.split("/", 1)
        cfg = _openclaw_config().get("mcpServers", {}).get(server_id)
        if not cfg:
            raise RpcError(-32602, f"unknown MCP server '{server_id}'")

        command = cfg.get("command")
        args = cfg.get("args", [])
        env = dict(os.environ)
        for k, v in (cfg.get("env") or {}).items():
            env[k] = os.path.expandvars(v) if isinstance(v, str) else str(v)

        async def run():
            proc = await asyncio.create_subprocess_exec(
                command, *args, cwd=str(_repo_root()), env=env,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)

            async def send(obj):
                proc.stdin.write((json.dumps(obj) + "\n").encode()); await proc.stdin.drain()

            async def recv_id(want_id):
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        raise RpcError(-32000, "MCP server closed unexpectedly")
                    try:
                        msg = json.loads(line)
                    except Exception:
                        continue
                    if msg.get("id") == want_id:
                        return msg

            await send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                   "clientInfo": {"name": "n2n", "version": "1.0"}}})
            await recv_id(1)
            await send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            await send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments}})
            resp = await recv_id(2)
            try:
                proc.terminate()
            except Exception:
                pass
            if "error" in resp:
                return {"content": [{"type": "text", "text": json.dumps(resp["error"])}], "isError": True}
            return resp.get("result", {})

        return await asyncio.wait_for(run(), timeout=self.tool_timeout)

    async def _exec_skill_gateway(self, skill: str, input_text: str):
        """Delegate a skill to the local gateway (its model/policies/budget)."""
        import httpx
        cfg = json.loads(Path(os.path.expanduser("~/.openclaw/openclaw.json")).read_text())
        gw = cfg.get("gateway", {})
        port = gw.get("port", 18789)
        token = (gw.get("auth") or {}).get("token", "")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        prompt = (f"A federated NetClaw peer has requested you run the '{skill}' skill. "
                  f"Execute it for the following request and return only the result:\n\n{input_text}")
        body = {"model": "netclaw", "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=self.skill_timeout) as client:
            resp = await client.post(f"http://127.0.0.1:{port}/v1/chat/completions",
                                     json=body, headers=headers)
            data = resp.json()
        try:
            output = data["choices"][0]["message"]["content"]
        except Exception:
            output = json.dumps(data)[:2000]
        tokens = 0
        try:
            tokens = data.get("usage", {}).get("total_tokens", 0)
        except Exception:
            pass
        return output, tokens

    # ---- outbound: WE ask a peer to run something ----------------------

    async def invoke_remote_tool(self, ident, tool, arguments):
        ch = self.service.channels.get(ident)
        if not ch:
            raise RpcError(ERR_SEVERED, "no channel to peer")
        req_id = f"{self.service.local_identity}:{int(time.time()*1000)}"
        self.audit.record(direction="outbound", peer_identity=ident, target_type="tool",
                          target_name=tool, request_id=req_id, decision="requested", outcome="pending")
        result = await ch.call("n2n/tools/call",
                               {"tool": tool, "arguments": arguments, "request_id": req_id},
                               timeout=self.tool_timeout + 5)
        return {"source": ident, "trust": "remote-untrusted", "result": result}

    async def invoke_remote_skill(self, ident, skill, input_text):
        ch = self.service.channels.get(ident)
        if not ch:
            raise RpcError(ERR_SEVERED, "no channel to peer")
        req_id = f"{self.service.local_identity}:{int(time.time()*1000)}"
        self.audit.record(direction="outbound", peer_identity=ident, target_type="skill",
                          target_name=skill, request_id=req_id, decision="requested", outcome="pending")
        result = await ch.call("n2n/tasks/submit",
                               {"skill": skill, "input_text": input_text, "request_id": req_id},
                               timeout=self.skill_timeout + 5)
        return {"source": ident, "trust": "remote-untrusted", "result": result}
