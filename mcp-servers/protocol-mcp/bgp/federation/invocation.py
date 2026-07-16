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
    """Return True if the tool is ALLOWED by DefenseClaw's block/allow list.

    Runs only when security.mode == defenseclaw. Uses `defenseclaw tool status
    <tool>` — the real block/allow query (feature 057 fix: the previous
    `defenseclaw tool inspect` is NOT a valid subcommand, so under defenseclaw mode
    it errored and denied every eN2N tool call). We deny only on an explicit
    'blocked' verdict; if the status can't be determined we allow (the DefenseClaw
    LLM guardrail proxy is the primary inspection path — this CLI check is the
    coarser per-tool block-list gate)."""
    if _security_mode() != "defenseclaw":
        return True
    try:
        proc = await asyncio.create_subprocess_exec(
            "defenseclaw", "tool", "status", tool,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        text = (out.decode(errors="replace") if out else "").lower()
        return "blocked" not in text        # deny only if explicitly blocked
    except FileNotFoundError:
        logger.warning("security.mode=defenseclaw but 'defenseclaw' CLI not found — denying tool")
        return False
    except Exception as e:
        logger.warning("DefenseClaw tool-status error (%s) — allowing (proxy guards I/O)", e)
        return True


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
        # Tier-0 default-deny: a self-asserted (keyless) peer is federated for
        # presence+inventory but may not invoke tools — possession proof required.
        from .negotiate import allows
        if not allows(getattr(channel, "attestation", "self-asserted"), "tools/call"):
            self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                              target_name=tool, request_id=req_id, decision="not_allowlisted",
                              outcome="denied")
            raise RpcError(ERR_NOT_ALLOWLISTED,
                           "possession proof required for tools/call (tier-0 self-asserted peer)")
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
        """Async (053): authorize synchronously, then create a task, spawn a
        background worker, and return {task_id} immediately. The peer polls
        n2n/tasks/status and fetches n2n/tasks/result — no long call to drop."""
        peer = channel.peer_identity
        skill = params.get("skill", "")
        input_text = params.get("input_text", "")
        req_id = params.get("request_id", "")
        # Tier-0 default-deny: tasks/submit is the async twin of tools/call — it
        # authorizes and executes a granted skill via the local gateway. A keyless
        # (self-asserted) peer may not, or it would bypass the tools/call gate via
        # the async path. Possession proof required.
        from .negotiate import allows
        if not allows(getattr(channel, "attestation", "self-asserted"), "tasks/submit"):
            self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                              target_name=skill, request_id=req_id, decision="not_allowlisted",
                              outcome="denied")
            raise RpcError(ERR_NOT_ALLOWLISTED,
                           "possession proof required for tasks/submit (tier-0 self-asserted peer)")
        decision = self.authz.authorize(peer, "skill", skill)

        if not decision.allowed and decision.code != "approval_required":
            self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                              target_name=skill, request_id=req_id, decision=decision.code, outcome="denied")
            raise RpcError(_CODE_MAP.get(decision.code, -32000), decision.reason)

        tm = self.service.tasks
        task_id = tm.create(direction="inbound", peer_identity=peer, target_type="skill",
                            target_name=skill, input_text=input_text)

        async def worker(progress):
            # Approval (if required) happens inside the background worker so submit
            # returns instantly; the task sits in 'working' until approved/expired.
            if decision.code == "approval_required":
                inv_id = self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                                           target_name=skill, request_id=task_id,
                                           decision="approval_required", outcome="pending")
                appr = self.authz.create_approval(inv_id)
                self.service.notify_approval(inv_id, peer, "skill", skill)
                progress("awaiting approval")
                if not await self._await_approval(appr["approval_id"]):
                    raise RpcError(ERR_APPROVAL_EXPIRED, "approval not granted")
            progress("running skill")
            try:
                output, tokens = await self._exec_skill_gateway(
                    skill, input_text, progress=progress, peer=peer)
            except asyncio.TimeoutError:
                self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                                  target_name=skill, request_id=task_id, decision="allowlisted",
                                  outcome="timeout")
                raise RpcError(ERR_EXECUTION_TIMEOUT,
                               f"skill {skill} timed out — a gateway scope approval may "
                               f"still be pending; approve it and resubmit")
            except RpcError:
                raise
            except Exception:
                # EnforcementRefused and execution errors must still land in the
                # audit table + GAIT trail (the pre-fix path recorded nothing).
                self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                                  target_name=skill, request_id=task_id, decision="allowlisted",
                                  outcome="error")
                raise
            self.authz.debit(peer, requests=1, tokens=tokens)
            self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                              target_name=skill, request_id=task_id, decision="allowlisted",
                              outcome="success")
            return output, tokens

        tm.run(task_id, worker)
        return {"task_id": task_id, "state": "submitted"}

    async def handle_task_status(self, channel, params):
        return self.service.tasks.status(params.get("task_id", ""))

    async def handle_task_result(self, channel, params):
        return self.service.tasks.result(params.get("task_id", ""))

    async def handle_task_cancel(self, channel, params):
        task_id = params.get("task_id", "")
        return {"task_id": task_id, "cancelled": self.service.tasks.cancel(task_id)}

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

    async def _exec_skill_gateway(self, skill: str, input_text: str,
                                  progress=None, peer: str = None):
        """Delegate a skill to the local gateway agent (its model/policies/budget).

        Uses the `openclaw agent` CLI — the gateway is WebSocket-only and has no
        REST completions route (see gateway.py). The peer's input is marked
        `untrusted` so embedded (--local) execution stays refused unless
        production containment verifies (2026-07-14 delegation-bypass review).

        If the gateway holds the session at its scope-upgrade approval gate the
        CLI goes silent; `on_stall` bridges that hold into the operator's n2n
        approval notifications and the task's progress state, and extends the
        wait by the approval window so a human can approve instead of the task
        dying on a blind hard timeout."""
        from .gateway import run_agent_turn

        def on_stall(waited_s):
            if progress:
                progress("awaiting gateway approval")
            self.service.notify_approval(
                None, peer or "unknown-peer", "gateway-scope", f"n2n-skill-{skill}")
            return self.authz.approval_window_s

        prompt = (f"A federated NetClaw peer has requested you run the '{skill}' skill. "
                  f"Execute it for the following request and return only the result:\n\n{input_text}")
        return await run_agent_turn(prompt, session_key=f"n2n-skill-{skill}",
                                    timeout_s=self.skill_timeout,
                                    untrusted=True, on_stall=on_stall)

    # ---- outbound: WE ask a peer to run something ----------------------

    async def _channel(self, ident):
        """Get a live channel, reconnecting on demand (FR-009) rather than
        failing on a dead/absent one."""
        try:
            return await self.service.ensure_channel(ident)
        except Exception as e:
            raise RpcError(ERR_SEVERED, str(e))

    async def invoke_remote_tool(self, ident, tool, arguments):
        ch = await self._channel(ident)
        req_id = f"{self.service.local_identity}:{int(time.time()*1000)}"
        self.audit.record(direction="outbound", peer_identity=ident, target_type="tool",
                          target_name=tool, request_id=req_id, decision="requested", outcome="pending")
        result = await ch.call("n2n/tools/call",
                               {"tool": tool, "arguments": arguments, "request_id": req_id},
                               timeout=self.tool_timeout + 5)
        return {"source": ident, "trust": "remote-untrusted", "result": result}

    async def submit_remote_skill(self, ident, skill, input_text):
        """Async (053): submit a skill task to a peer, return the task_id
        immediately. The peer runs it in the background; poll via task_status/
        task_result. Short call — survives ngrok resets (FR-005)."""
        ch = await self._channel(ident)
        resp = await ch.call("n2n/tasks/submit",
                             {"skill": skill, "input_text": input_text}, timeout=30.0)
        task_id = resp.get("task_id")
        if task_id:
            self.service.tasks.record_outbound(task_id, ident, "skill", skill)
            self.audit.record(direction="outbound", peer_identity=ident, target_type="skill",
                              target_name=skill, request_id=task_id, decision="requested",
                              outcome="submitted")
        return {"source": ident, "trust": "remote-untrusted", **resp}

    async def poll_remote_task(self, ident, task_id, kind="status"):
        """Fetch status or result of an outbound task from the peer (short call).
        On a completed result, cache it locally so it survives a later drop (FR-004)."""
        ch = self.service.channels.get(ident)
        if not ch:
            # Channel down: fall back to the last locally-cached status/result.
            tm = self.service.tasks
            return tm.result(task_id) if kind == "result" else tm.status(task_id)
        method = "n2n/tasks/result" if kind == "result" else "n2n/tasks/status"
        resp = await ch.call(method, {"task_id": task_id}, timeout=30.0)
        # Cache terminal results locally against the outbound row (retrieval after drop)
        if kind == "result" and resp.get("state") in ("completed", "failed", "cancelled"):
            ref = self.audit.store_result(task_id, resp)
            self.service.tasks._set(task_id, state=resp["state"], result_ref=ref,
                                    completed_at=resp.get("completed_at"))
        return {"source": ident, "trust": "remote-untrusted", **resp}

    async def cancel_remote_task(self, ident, task_id):
        ch = await self._channel(ident)
        return await ch.call("n2n/tasks/cancel", {"task_id": task_id}, timeout=15.0)
