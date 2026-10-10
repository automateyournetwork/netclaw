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
    """Delegate to controls.security_mode() — the single source of truth.

    This previously read ~/.openclaw/openclaw.json, which is the *gateway*
    config. That file's schema has no `security.mode` key (OpenClaw rejects it
    outright: "security: Unrecognized key"), so the lookup could never succeed
    and this always fell through to "hobby". The visible effect was that
    _defenseclaw_inspect() below returned True unconditionally, silently
    disabling the per-tool block-list check on every federated tool call even
    with DefenseClaw fully enabled.

    controls._security_config_path() reads ~/.openclaw/config/openclaw.json,
    which is where the mode actually lives (see CLAUDE.md and that docstring).
    """
    from .controls import security_mode
    return security_mode()


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

    def _approval(self,invocation_id,decision,peer,target_type,target,request_id,body):
        from .execution import digest
        decision.request_binding=digest([peer,target_type,target,request_id,decision.grant['id'],body])
        approval=self.authz.create_approval(invocation_id,decision.request_binding)
        decision.approval_id=approval['approval_id']
        return approval

    def _admit(self, peer, target_type, target, request_id, original, *, already_trusted=False,request_body=None):
        if original.code=='approval_required':
            from .execution import digest
            expected=digest([peer,target_type,target,request_id,original.grant['id'],request_body])
            if original.request_binding!=expected:raise RpcError(ERR_APPROVAL_EXPIRED,'request differs from approved operation')
        if target_type in ("knowledge", "knowledge_replica"):
            visible = {entry["collection_id"] for entry in self.service.inventory._load_knowledge(peer)}
            if target not in visible:
                self.audit.record(direction="inbound", peer_identity=peer, target_type=target_type,
                                  target_name=target, request_id=request_id,
                                  decision="not_allowlisted", outcome="denied")
                raise RpcError(ERR_NOT_ALLOWLISTED, "collection is no longer available to this peer")
        decision = self.authz.admit(peer, target_type, target, original,
                                    already_trusted=already_trusted)
        if not decision.allowed:
            self.audit.record(direction="inbound", peer_identity=peer, target_type=target_type,
                              target_name=target, request_id=request_id,
                              decision=decision.code, outcome="denied")
            raise RpcError(_CODE_MAP.get(decision.code, -32000), decision.reason)

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
        # spec 121: an internal (iN2N) channel's peer_identity is this member's
        # own self-referential identity for its channel to Border, not an eN2N
        # BGP peer — is_federated() has no row for that and always denies it.
        # See authorization.py's already_trusted param docstring.
        from .internal_channel import InternalChannel
        already_trusted = isinstance(channel, InternalChannel)
        if already_trusted and self.service.risk.role()=='member':
            from .runtime import selected
            if selected().kind=='hermes' and ('subnet-calculator' not in self.service.member_scope or tool!='subnet-calc-mcp/subnet_calculator'):
                raise RpcError(ERR_NOT_ALLOWLISTED,'tool is outside member scope')
        decision = self.authz.authorize(peer, "tool", tool, already_trusted=already_trusted)

        if not decision.allowed and decision.code != "approval_required":
            self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                              target_name=tool, request_id=req_id, decision=decision.code, outcome="denied")
            raise RpcError(_CODE_MAP.get(decision.code, -32000), decision.reason)

        if decision.code == "approval_required":
            inv_id = self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                                       target_name=tool, request_id=req_id, decision="approval_required",
                                       outcome="pending")
            appr = self._approval(inv_id,decision,peer,'tool',tool,req_id,arguments)
            self.service.notify_approval(inv_id, peer, "tool", tool)
            if not await self._await_approval(appr["approval_id"]):
                raise RpcError(ERR_APPROVAL_EXPIRED, "approval not granted")

        if not await _defenseclaw_inspect(tool, arguments):
            self.audit.record(direction="inbound", peer_identity=peer, target_type="tool",
                              target_name=tool, request_id=req_id, decision="guardrail_blocked", outcome="denied")
            raise RpcError(ERR_GUARDRAIL_BLOCKED, "DefenseClaw inspection blocked the call")

        self._admit(peer, "tool", tool, req_id, decision, already_trusted=already_trusted,request_body=arguments)
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

        deadline=params.get('deadline')
        import math
        if deadline is not None and (not isinstance(deadline,(int,float)) or isinstance(deadline,bool) or not math.isfinite(deadline) or deadline<=time.time()):
            raise RpcError(-32602,'invalid or expired parent deadline')
        tm = self.service.tasks
        task_id = tm.create(direction="inbound", peer_identity=peer, target_type="skill",
                            target_name=skill, input_text=input_text,client_request=req_id or None,request_payload={'deadline':deadline})

        async def worker(progress):
            # Approval (if required) happens inside the background worker so submit
            # returns instantly; the task sits in 'working' until approved/expired.
            if decision.code == "approval_required":
                inv_id = self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                                           target_name=skill, request_id=task_id,
                                           decision="approval_required", outcome="pending")
                appr = self._approval(inv_id,decision,peer,'skill',skill,task_id,input_text)
                self.service.notify_approval(inv_id, peer, "skill", skill)
                progress("awaiting approval")
                if not await self._await_approval(appr["approval_id"]):
                    raise RpcError(ERR_APPROVAL_EXPIRED, "approval not granted")
            self._admit(peer, "skill", skill, task_id, decision,request_body=input_text)
            progress("running skill")
            try:
                extra={}
                if self.service.runtime.kind=='hermes':extra={'task_id':task_id,'channel':channel,'decision':decision,'deadline':deadline}
                output, tokens = await self._exec_skill_gateway(
                    skill, input_text, progress=progress, peer=peer,**extra)
            except asyncio.TimeoutError:
                self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                                  target_name=skill, request_id=task_id, decision="allowlisted",
                                  outcome="timeout")
                raise RpcError(ERR_EXECUTION_TIMEOUT,
                               f"skill {skill} timed out — a gateway scope approval may "
                               f"still be pending; check its status before further action")
            except RpcError:
                raise
            except Exception:
                # EnforcementRefused and execution errors must still land in the
                # audit table + GAIT trail (the pre-fix path recorded nothing).
                self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                                  target_name=skill, request_id=task_id, decision="allowlisted",
                                  outcome="error")
                raise
            self.authz.debit(peer, requests=0, tokens=tokens)
            self.audit.record(direction="inbound", peer_identity=peer, target_type="skill",
                              target_name=skill, request_id=task_id, decision="allowlisted",
                              outcome="success")
            return output, tokens

        tm.run(task_id, worker)
        return {"task_id": task_id, "state": "submitted"}

    # Retrieval is bound to the submitting peer (NCFED -00 §9.2/§14.6): the
    # authenticated channel identity must match the task's recorded owner, and
    # a non-owner is answered as if the task did not exist.

    def _owned_task(self,channel,params):
        member_id=getattr(channel,'member_id',None)
        member=self.service.risk.get_member(member_id) if member_id else None
        from .edge import EdgeChannel
        edge=isinstance(channel,EdgeChannel) or bool(member and member['node_type']=='edge')
        generation=getattr(channel,'owner_generation',None)
        task=params.get('task_id','')
        if edge:
            if not member or not getattr(channel,'trusted',False) or member['state'] in ('removed','quarantined') or member['key_fingerprint']!=generation:
                return '',True
            if params.get('request_id'):task=self.service.tasks.resolve_owned_request(channel.peer_identity,params['request_id'],generation) or ''
            if not self.service.tasks.generation_matches(task,channel.peer_identity,generation):return '',True
        return task,edge

    async def handle_task_status(self, channel, params):
        task,edge=self._owned_task(channel,params)
        if edge:await self.service.reconcile_hermes_task(task)
        result=self.service.tasks.status(task,owner=channel.peer_identity)
        return self.service.tasks.project_edge(task,result) if edge else result

    async def handle_task_result(self, channel, params):
        task,edge=self._owned_task(channel,params)
        if edge:await self.service.reconcile_hermes_task(task)
        result=self.service.tasks.result(task,owner=channel.peer_identity)
        return self.service.tasks.project_edge(task,result) if edge else result

    async def handle_task_cancel(self, channel, params):
        task_id,edge=self._owned_task(channel,params)
        cancelled = self.service.tasks.cancel(task_id, owner=channel.peer_identity)
        # The phone's own Cancel button (chat_screen.dart _cancel()) never
        # reads this RPC's return value -- it waits for a pushed
        # n2n/edge/ask_result, exactly like a normal completion (mirrors
        # _edge_on_ask's _push_result_when_done). A task cancelled via the
        # live-worker path already gets that push from there; a task
        # cancelled via tasks.py's no-live-worker fallback (e.g. orphaned by
        # a daemon restart) never goes through that code at all, so without
        # this the phone would show the fixed-up task as "cancelled" server
        # side while its UI stays stuck on "Working..." forever.
        if cancelled and self.service.edge_channels.get(channel.peer_identity) is channel:
            result = self.service.tasks.result(task_id)
            if result.get("state") == "cancelled":
                try:
                    await channel.notify("n2n/edge/ask_result", {
                        "task_id": task_id, "state": "cancelled",
                        "output_text": None, "tokens_used": 0,
                    })
                except Exception:
                    pass
        state=self.service.tasks.status(task_id,owner=channel.peer_identity).get('state')
        return {"task_id": task_id, "cancelled": state=='cancelled','cancel_requested':cancelled,
                'cancellation_confirmed':state=='cancelled','state':state}

    # ---- feature 064: federated knowledge retrieval -------------------

    async def handle_knowledge_query(self, channel, params):
        """Server side of `n2n/knowledge/query` (a dedicated NCFED method, not the
        MCP tools/call proxy). Default-deny + possession tier + per-peer grant,
        no existence oracle, agent-composed cited answer, audited (FR-004/007/008)."""
        from . import knowledge as _knowledge
        peer = channel.peer_identity
        collection_id = params.get("collection_id", "")
        query = params.get("query", "")
        req_id = params.get("request_id", "")
        collection = collection_id.split(":", 1)[-1] if collection_id else ""

        # Tier-0 default-deny: a self-asserted (keyless) peer may not retrieve.
        from .negotiate import allows
        if not allows(getattr(channel, "attestation", "self-asserted"), "knowledge/query"):
            self.audit.record(direction="inbound", peer_identity=peer, target_type="knowledge",
                              target_name=collection_id, request_id=req_id,
                              decision="not_allowlisted", outcome="denied")
            raise RpcError(ERR_NOT_ALLOWLISTED,
                           "possession proof required for knowledge/query (tier-0 peer)")

        # No existence oracle: a collection this peer may not see is answered
        # exactly like one that does not exist (same shape), before any grant check.
        visible = {e["collection_id"] for e in self.service.inventory._load_knowledge(peer)}
        if collection_id not in visible:
            self.audit.record(direction="inbound", peer_identity=peer, target_type="knowledge",
                              target_name=collection_id, request_id=req_id,
                              decision="not_found", outcome="denied")
            return {"answer": None, "not_found": True,
                    "provenance": {"peer": self.service.local_identity,
                                   "collection_id": collection_id}}

        # Default-deny per-peer grant (reuses the tools/call authorizer path).
        decision = self.authz.authorize(peer, "knowledge", collection_id)
        if not decision.allowed and decision.code != "approval_required":
            self.audit.record(direction="inbound", peer_identity=peer, target_type="knowledge",
                              target_name=collection_id, request_id=req_id,
                              decision=decision.code, outcome="denied")
            raise RpcError(_CODE_MAP.get(decision.code, -32000), decision.reason)
        if decision.code == "approval_required":
            inv_id = self.audit.record(direction="inbound", peer_identity=peer,
                                       target_type="knowledge", target_name=collection_id,
                                       request_id=req_id, decision="approval_required",
                                       outcome="pending")
            appr = self._approval(inv_id,decision,peer,'knowledge',collection_id,req_id,params)
            self.service.notify_approval(inv_id, peer, "knowledge", collection_id)
            if not await self._await_approval(appr["approval_id"]):
                raise RpcError(ERR_APPROVAL_EXPIRED, "approval not granted")

        # Compose an agent-grounded, cited answer from the LIVE local RAG. The
        # gateway agent has the rag-mcp tools; the prompt scopes it to this
        # collection. External peer input → untrusted turn (never embedded).
        from .gateway import run_agent_turn
        prompt = (f"A federated peer ({peer}) asks about your knowledge collection "
                  f"'{collection}'. Using your RAG knowledge base, answer the question "
                  f"and cite the source document(s) and page(s). If the collection does "
                  f"not contain the answer, say so plainly.\n\nQuestion: {query}")
        self._admit(peer, "knowledge", collection_id, req_id, decision,request_body=params)
        try:
            answer, tokens = await run_agent_turn(
                prompt, session_key=f"n2n-knowledge-{peer}", untrusted=True,
                timeout_s=self.tool_timeout)
        except asyncio.TimeoutError:
            self.audit.record(direction="inbound", peer_identity=peer, target_type="knowledge",
                              target_name=collection_id, request_id=req_id,
                              decision="allowlisted", outcome="timeout")
            raise RpcError(ERR_EXECUTION_TIMEOUT, "knowledge query timed out")
        result = {"answer": answer,
                  "provenance": {"peer": self.service.local_identity,
                                 "collection_id": collection_id}}
        ref = self.audit.store_result(req_id or f"{peer}-{collection_id}", result)
        self.audit.record(direction="inbound", peer_identity=peer, target_type="knowledge",
                          target_name=collection_id, request_id=req_id,
                          decision="allowlisted", outcome="success", result_ref=ref)
        return result

    async def query_remote_knowledge(self, ident, collection_id, query, k: int = 8):
        """Client side: ask peer `ident` to answer from its `collection_id`."""
        ch = await self._channel(ident)
        req_id = f"{self.service.local_identity}:{int(time.time()*1000)}"
        self.audit.record(direction="outbound", peer_identity=ident, target_type="knowledge",
                          target_name=collection_id, request_id=req_id,
                          decision="requested", outcome="pending")
        result = await self._outbound_call(
            ch, "n2n/knowledge/query",
            {"collection_id": collection_id, "query": query,
             "k": k, "request_id": req_id},
            ident=ident, target_type="knowledge", target_name=collection_id,
            req_id=req_id, timeout=self.tool_timeout + 5)
        return {"source": ident, "trust": "remote-untrusted", "result": result}

    # ---- feature 065: chroma-to-chroma replication ----------------------
    #
    # `knowledge_replica` is a distinct target_type from `knowledge` (FR-002)
    # — holding a query-retrieval grant does NOT authorize replication, and
    # vice versa. Gating otherwise mirrors handle_knowledge_query exactly
    # (tier-0 denial, no-existence-oracle visibility, default-deny grant,
    # audit) — replication is at least as sensitive as query, so it reuses
    # the same shape rather than inventing a lighter one.

    async def _replicate_gate(self, channel, params, method_name: str):
        """Shared tier/visibility/grant checks for both replicate_manifest and
        replicate_batch. Returns (peer, collection_id, req_id) on success, or
        raises/returns a not-found dict exactly like handle_knowledge_query."""
        from .negotiate import allows
        peer = channel.peer_identity
        collection_id = params.get("collection_id", "")
        req_id = params.get("request_id", "")

        if not allows(getattr(channel, "attestation", "self-asserted"), "knowledge/replicate"):
            self.audit.record(direction="inbound", peer_identity=peer,
                              target_type="knowledge_replica", target_name=collection_id,
                              request_id=req_id, decision="not_allowlisted", outcome="denied")
            raise RpcError(ERR_NOT_ALLOWLISTED,
                           "possession proof required for knowledge/replicate (tier-0 peer)")

        # No existence oracle — same visible set query-retrieval uses (FR-013).
        # A kind='replica' row is never in this set (knowledge.py excludes it),
        # so a third peer can't discover or replicate a replica this way either
        # (FR-009's onward-propagation clause).
        visible = {e["collection_id"] for e in self.service.inventory._load_knowledge(peer)}
        if collection_id not in visible:
            self.audit.record(direction="inbound", peer_identity=peer,
                              target_type="knowledge_replica", target_name=collection_id,
                              request_id=req_id, decision="not_found", outcome="denied")
            return None, {"not_found": True}

        # Distinct grant type from query-retrieval (FR-002).
        decision = self.authz.authorize(peer, "knowledge_replica", collection_id)
        if not decision.allowed and decision.code != "approval_required":
            self.audit.record(direction="inbound", peer_identity=peer,
                              target_type="knowledge_replica", target_name=collection_id,
                              request_id=req_id, decision=decision.code, outcome="denied")
            raise RpcError(_CODE_MAP.get(decision.code, -32000), decision.reason)
        if decision.code == "approval_required":
            inv_id = self.audit.record(direction="inbound", peer_identity=peer,
                                       target_type="knowledge_replica", target_name=collection_id,
                                       request_id=req_id, decision="approval_required",
                                       outcome="pending")
            appr = self._approval(inv_id,decision,peer,'knowledge_replica',collection_id,req_id,params)
            self.service.notify_approval(inv_id, peer, "knowledge_replica", collection_id)
            if not await self._await_approval(appr["approval_id"]):
                raise RpcError(ERR_APPROVAL_EXPIRED, "approval not granted")
        self._admit(peer, "knowledge_replica", collection_id, req_id, decision,request_body=params)
        return (peer, collection_id, req_id), None

    async def handle_replicate_manifest(self, channel, params):
        """Server side of `n2n/knowledge/replicate_manifest`: returns the
        embedding model + total chunk count for a collection so the requester
        can refuse locally (mismatch/over-cap) before any batch is requested
        (FR-003/FR-017) — zero content in this response either way."""
        gated, not_found = await self._replicate_gate(channel, params, "replicate_manifest")
        if not_found is not None:
            return not_found
        peer, collection_id, req_id = gated
        from . import knowledge as _knowledge
        collection = collection_id.split(":", 1)[-1] if collection_id else ""
        entries = {e["collection_id"]: e for e in _knowledge.build_entries()}
        entry = entries.get(collection_id)
        if entry is None:
            # Advertised to this peer (passed visibility) but the collection
            # vanished between grant and now (renamed/deleted) — refused, not
            # a fabricated manifest (spec Edge Cases).
            self.audit.record(direction="inbound", peer_identity=peer,
                              target_type="knowledge_replica", target_name=collection_id,
                              request_id=req_id, decision="not_found", outcome="denied")
            return {"not_found": True}
        from .chroma_store_bridge import chunk_count_for
        result = {"collection_id": collection_id, "embedding_model": entry["embedding_model"],
                  "chunk_count": chunk_count_for(collection)}
        self.audit.record(direction="inbound", peer_identity=peer,
                          target_type="knowledge_replica", target_name=collection_id,
                          request_id=req_id, decision="allowlisted", outcome="success")
        return result

    async def handle_replicate_batch(self, channel, params):
        """Server side of `n2n/knowledge/replicate_batch`: one page of
        {ids, embeddings, texts, metadatas} for a collection (FR-004/FR-005)."""
        gated, not_found = await self._replicate_gate(channel, params, "replicate_batch")
        if not_found is not None:
            return not_found
        peer, collection_id, req_id = gated
        collection = collection_id.split(":", 1)[-1] if collection_id else ""
        offset = int(params.get("offset", 0))
        limit = int(params.get("limit", 200))
        from .chroma_store_bridge import get_chunks_page
        # Metadata is forwarded exactly as ingestion stored it (title,
        # document_id, doc_type, breadcrumb, section, page, ...) — no
        # additional filtering beyond what ingestion already scrubbed
        # (FR-014); source_path/content_hash/capture_commands are registry
        # columns, never chunk metadata, so they were never here to leak.
        page = get_chunks_page(collection, offset, limit)
        self.audit.record(direction="inbound", peer_identity=peer,
                          target_type="knowledge_replica", target_name=collection_id,
                          request_id=req_id, decision="allowlisted", outcome="success")
        return {"collection_id": collection_id, "offset": offset,
                "returned": len(page["ids"]), **page}

    async def fetch_replicate_manifest(self, ident: str, collection_id: str) -> dict:
        """Client side: ask peer `ident` for the manifest of `collection_id`."""
        ch = await self._channel(ident)
        req_id = f"{self.service.local_identity}:{int(time.time()*1000)}"
        self.audit.record(direction="outbound", peer_identity=ident,
                          target_type="knowledge_replica", target_name=collection_id,
                          request_id=req_id, decision="requested", outcome="pending")
        return await self._outbound_call(
            ch, "n2n/knowledge/replicate_manifest",
            {"collection_id": collection_id, "request_id": req_id},
            ident=ident, target_type="knowledge_replica", target_name=collection_id,
            req_id=req_id, timeout=self.tool_timeout)

    async def fetch_replicate_batch(self, ident: str, collection_id: str,
                                    offset: int, limit: int) -> dict:
        """Client side: pull one page of `collection_id`'s chunks from peer `ident`."""
        ch = await self._channel(ident)
        req_id = f"{self.service.local_identity}:{int(time.time()*1000)}"
        return await ch.call("n2n/knowledge/replicate_batch",
                             {"collection_id": collection_id, "offset": offset,
                              "limit": limit, "request_id": req_id},
                             timeout=self.tool_timeout)

    def route_knowledge(self, query: str):
        """Choose a collection for `query` across local + cached peer cards
        (data-model Knowledge Route Decision). eN2N selection lives in
        knowledge.py, not the iN2N router (finding H2)."""
        from . import knowledge as _knowledge
        sources = [{"source": "local", "entries": _knowledge.build_entries()}]
        for ident in list(self.service.channels):
            if not self.service.manager.is_federated(ident):
                continue
            card = self.service.inventory.load_remote(ident) or {}
            entries = card.get("knowledge") or []
            if entries:
                sources.append({"source": ident, "entries": entries})
        return _knowledge.select_collection(query, sources)

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
        from .runtime import selected, ROOT
        runtime=self.service.runtime
        if runtime.kind=='hermes':
            import sys
            import yaml
            from .hermes_runtime import call_stdio
            from .execution import Refused
            if not self.service.hermes_runtime:raise Refused('selected federation runtime is not ready')
            sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
            from policy import qualified_servers, ToolPolicy
            import hashlib
            config=yaml.safe_load(runtime.config.read_text()) or {}
            servers,entries=qualified_servers(config,home=runtime.home)
            native='mcp__'+server_id.replace('-','_')+'__'+tool_name
            policy=ToolPolicy(entries,runtime.config,hashlib.sha256(runtime.config.read_bytes()).hexdigest())
            policy.check_arguments(native,arguments)
            registration=servers.get(server_id)
            if tool!='subnet-calc-mcp/subnet_calculator' or not registration:raise Refused('unqualified direct Hermes tool')
            env=runtime.environment()
            env.update(registration.get('env') or {})
            result=await call_stdio(registration['command'],registration.get('args',[]),env,tool_name,arguments,timeout=self.tool_timeout)
            return {'content':[{'type':'text','text':json.dumps(result)}],'isError':False}
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
                                  progress=None, peer: str = None, task_id=None, channel=None, decision=None,deadline=None):
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
        from .execution import conversation_id
        import uuid
        request=task_id or str(uuid.uuid4())
        session=conversation_id(self.service.runtime.installation or str(self.manager.base_dir),peer or 'local',request)
        timeout_s=min(self.skill_timeout,max(.001,deadline-time.time())) if deadline else self.skill_timeout
        extra={}
        if self.service.runtime.kind=='hermes':
            def current(_):
                if not channel or getattr(channel,'_closed',False):return False
                return self.authz.still_authorized(peer,'skill',skill,decision)
            extra['execution']=self.service.execution_context(requester=peer,origin='external',request=request,conversation=session,
                target_type='skill',target=skill,prompt=prompt,profile='subnet',authorize=current,task_id=task_id,
                grant=decision.grant['id'] if decision and decision.grant else None,timeout_s=timeout_s)
        return await run_agent_turn(prompt, session_key=session,
                                    timeout_s=timeout_s,
                                    untrusted=True, on_stall=on_stall,**extra)

    # ---- outbound: WE ask a peer to run something ----------------------

    async def _channel(self, ident):
        """Get a live channel, reconnecting on demand (FR-009) rather than
        failing on a dead/absent one.

        spec 121: every outbound caller here (invoke_remote_tool, etc.) had only
        ever been exercised against eN2N BGP-identity peers — ensure_channel()
        looks up self.service.channels (the eN2N dict) and raises "not
        federated" for ANY identity it doesn't recognize as a BGP peer,
        including a perfectly live internal (iN2N) member such as
        "johns-risk/viz", which lives in self.service.member_channels instead
        and is brought up via ensure_member_up(), not ensure_channel(). Without
        this branch, Border could never actually call n2n/tools/call (or any
        other outbound method) on one of its own members — confirmed live: a
        real call to invoke_remote_tool("johns-risk/viz", ...) failed with
        "peer_unreachable: not federated" despite the member being connected."""
        try:
            if self.service.is_member_task(ident):
                ch = await self.service.ensure_member_up(ident)
                if ch is None:
                    raise RuntimeError(f"member {ident!r} could not be brought up")
                return ch
            return await self.service.ensure_channel(ident)
        except Exception as e:
            raise RpcError(ERR_SEVERED, str(e))

    async def _outbound_call(self, ch, method, params, *, ident, target_type,
                             target_name, req_id, timeout):
        """Make an outbound federated call and record its TERMINAL outcome.

        Feature 100 (US5/FR-034..037). Every outbound path used to write one row with
        `outcome="pending"` and then never write again, so a success, a refusal by the
        peer, and a timeout were indistinguishable in the audit trail and every
        outbound row sat pending forever.

        The terminal row reuses the SAME `request_id` as the pending row (FR-035), so
        both sides of a federated call reconcile it by one identifier — the caller's
        pending/terminal pair joins to the callee's inbound row.

        Note the terminal row keeps `decision="requested"`: on an outbound call *we*
        made no authorization decision, we asked. What varies is the outcome.
        """
        def _terminal(outcome):
            self.audit.record(direction="outbound", peer_identity=ident,
                              target_type=target_type, target_name=target_name,
                              request_id=req_id, decision="requested", outcome=outcome)

        self.service.tasks.outbound_intent(ident,method,params,request=req_id)
        try:
            result = await ch.call(method, params, timeout=timeout)
        except RpcError as e:
            self.service.tasks.settle_intent(req_id,'outcome_unknown' if e.code==ERR_EXECUTION_TIMEOUT else 'refused')
            # A refusal returned by the peer is auditable evidence, not a transient
            # response to discard (FR-036). Its own timeout code maps to `timeout`
            # rather than being flattened into a denial (FR-037).
            _terminal("timeout" if e.code == ERR_EXECUTION_TIMEOUT else "denied")
            raise
        except (asyncio.TimeoutError, TimeoutError):
            self.service.tasks.settle_intent(req_id,'outcome_unknown')
            _terminal("timeout")
            raise
        except Exception:
            self.service.tasks.settle_intent(req_id,'outcome_unknown')
            # Channel dropped before a response. Still terminal — FR-037 forbids
            # leaving the row pending just because the failure was not a clean refusal.
            _terminal("error")
            raise
        _terminal("success")
        self.service.tasks.settle_intent(req_id,'completed')
        return result

    async def invoke_remote_tool(self, ident, tool, arguments):
        ch = await self._channel(ident)
        import uuid
        req_id = str(uuid.uuid4())
        self.audit.record(direction="outbound", peer_identity=ident, target_type="tool",
                          target_name=tool, request_id=req_id, decision="requested", outcome="pending")
        result = await self._outbound_call(
            ch, "n2n/tools/call",
            {"tool": tool, "arguments": arguments, "request_id": req_id},
            ident=ident, target_type="tool", target_name=tool, req_id=req_id,
            timeout=self.tool_timeout + 5)
        return {"source": ident, "trust": "remote-untrusted", "result": result}

    async def submit_remote_skill(self, ident, skill, input_text, *, execution_scope=None):
        """Async (053): submit a skill task to a peer, return the task_id
        immediately. The peer runs it in the background; poll via task_status/
        task_result. Short call — survives ngrok resets (FR-005)."""
        ch = await self._channel(ident)
        import uuid
        request=str(uuid.uuid4())
        body={'skill':skill,'input_text':input_text,'request_id':request}
        if execution_scope:body['deadline']=execution_scope.deadline
        self.service.tasks.outbound_intent(ident,'n2n/tasks/submit',body,request=request)
        try:resp = await ch.call("n2n/tasks/submit",body, timeout=min(30.,max(.001,execution_scope.deadline-time.time())) if execution_scope else 30.0)
        except BaseException:
            self.service.tasks.settle_intent(request,'outcome_unknown');raise
        task_id = resp.get("task_id")
        if task_id:
            self.service.tasks.record_outbound(task_id, ident, "skill", skill)
            self.audit.record(direction="outbound", peer_identity=ident, target_type="skill",
                              target_name=skill, request_id=task_id, decision="requested",
                              outcome="submitted")
        self.service.tasks.settle_intent(request,'submitted' if task_id else 'refused',task_id)
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
