"""N2N claw-to-claw chat (US3).

An operator converses with a remote NetClaw's agent through their own claw. The
message relays over the NCFED channel to the peer's gateway agent (its model,
policies, budget), and the reply comes back attributed to the peer. Per-peer
enable/disable (FR-018), rate-limited + budget-shared with invocations (FR-020),
and every exchange is transcript-logged for both operators (FR-022).
"""

import json
import logging
import os
import time
import uuid
from pathlib import Path

from .channel import RpcError, ERR_RATE_LIMITED, ERR_BUDGET_EXHAUSTED, ERR_SEVERED

logger = logging.getLogger("n2n.chat")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ChatManager:
    def __init__(self, service):
        self.service = service
        self.manager = service.manager
        self.authz = service.authz
        self.audit = service.audit
        self.chats_dir = self.manager.base_dir / "chats"

    # ---- inbound: peer's operator chats with OUR agent ----------------

    async def handle_chat_open(self, channel, params):
        peer = channel.peer_identity
        # Tier-0 default-deny: chat runs OUR gateway agent under the peer's
        # identity — an impersonation + resource surface, not presence/inventory.
        from .negotiate import allows
        if not allows(getattr(channel, "attestation", "self-asserted"), "chat/open"):
            return {"accepted": False,
                    "reason": "possession proof required for chat (tier-0 self-asserted peer)"}
        row = self.manager.get_peer(peer)
        if not row or not row["chat_enabled"]:
            return {"accepted": False, "reason": "chat not enabled for this peer"}
        session_id = params.get("session_id") or str(uuid.uuid4())
        self.manager._conn.execute(
            "INSERT OR IGNORE INTO n2n_chat_session (id, peer_identity, direction, started_at, "
            "last_activity_at, transcript_ref) VALUES (?,?,?,?,?,?)",
            (session_id, peer, "received", _now(), _now(), str(self.chats_dir / f"{session_id}.txt")))
        self.manager._conn.commit()
        return {"accepted": True, "session_id": session_id}

    async def handle_chat_message(self, channel, params):
        peer = channel.peer_identity
        from .negotiate import allows  # tier-0 default-deny (see handle_chat_open)
        if not allows(getattr(channel, "attestation", "self-asserted"), "chat/message"):
            raise RpcError(ERR_SEVERED,
                           "possession proof required for chat (tier-0 self-asserted peer)")
        row = self.manager.get_peer(peer)
        if not row or not row["chat_enabled"]:
            raise RpcError(ERR_SEVERED, "chat not enabled")
        if not self.authz._check_rate(peer):
            raise RpcError(ERR_RATE_LIMITED, "chat rate limit exceeded")
        if not self.authz._check_budget(peer):
            raise RpcError(ERR_BUDGET_EXHAUSTED, "daily budget exhausted")
        session_id = params.get("session_id")
        text = params.get("text", "")
        self._append(session_id, f"[{peer}] {text}")
        reply, tokens = await self._ask_gateway(text, session_key=f"n2n-chat-{peer}")
        self.authz.debit(peer, requests=1, tokens=tokens)
        self._append(session_id, f"[{self.service.local_identity}] {reply}")
        self._touch(session_id)
        self.audit.record(direction="inbound", peer_identity=peer, target_type="chat",
                          target_name=session_id, request_id=session_id, decision="allowlisted",
                          outcome="success")
        return {"session_id": session_id, "text": reply, "tokens_used": tokens}

    async def _ask_gateway(self, text: str, session_key: str = "n2n-chat"):
        # OpenClaw's gateway is WebSocket-only (no /v1/chat/completions REST
        # route) — run a real agent turn via the CLI instead. See gateway.py.
        from .gateway import run_agent_turn
        idle = int(os.environ.get("N2N_CHAT_IDLE_TIMEOUT_S", "300"))
        prompt = f"[A federated NetClaw peer is asking you this]\n{text}"
        return await run_agent_turn(prompt, session_key=session_key, timeout_s=idle,
                                    untrusted=True)

    # ---- outbound: OUR operator chats with the PEER's agent -----------

    async def open_and_send(self, ident: str, text: str, session_id: str = None):
        ch = self.service.channels.get(ident)
        if not ch:
            raise RpcError(ERR_SEVERED, "no channel to peer")
        if not session_id:
            opened = await ch.call("n2n/chat/open",
                                   {"operator_display": self.service.display_name}, timeout=15)
            if not opened.get("accepted"):
                return {"error": opened.get("reason", "chat refused"), "session_id": None}
            session_id = opened["session_id"]
            self.manager._conn.execute(
                "INSERT OR IGNORE INTO n2n_chat_session (id, peer_identity, direction, started_at, "
                "last_activity_at, transcript_ref) VALUES (?,?,?,?,?,?)",
                (session_id, ident, "initiated", _now(), _now(), str(self.chats_dir / f"{session_id}.txt")))
            self.manager._conn.commit()
        self._append(session_id, f"[{self.service.local_identity}] {text}")
        reply = await ch.call("n2n/chat/message", {"session_id": session_id, "text": text},
                              timeout=int(os.environ.get("N2N_CHAT_IDLE_TIMEOUT_S", "300")))
        self._append(session_id, f"[{ident}] {reply.get('text','')}")
        self._touch(session_id)
        self.audit.record(direction="outbound", peer_identity=ident, target_type="chat",
                          target_name=session_id, request_id=session_id, decision="requested",
                          outcome="success")
        return {"session_id": session_id, "source": ident, "trust": "remote-untrusted",
                "text": reply.get("text", "")}

    # ---- transcript helpers -------------------------------------------

    def _append(self, session_id: str, line: str):
        try:
            with open(self.chats_dir / f"{session_id}.txt", "a") as f:
                f.write(f"{_now()} {line}\n")
        except Exception:
            pass

    def _touch(self, session_id: str):
        self.manager._conn.execute(
            "UPDATE n2n_chat_session SET last_activity_at=?, message_count=message_count+1 WHERE id=?",
            (_now(), session_id))
        self.manager._conn.commit()

    def list_sessions(self) -> list:
        return [dict(r) for r in self.manager._conn.execute(
            "SELECT * FROM n2n_chat_session ORDER BY last_activity_at DESC LIMIT 50")]
