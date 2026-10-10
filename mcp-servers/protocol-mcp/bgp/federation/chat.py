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
import re
import stat
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
        if not row or not row["chat_enabled"] or not self.manager.is_federated(peer):
            return {"accepted": False, "reason": "chat not enabled for this peer"}
        session_id = params.get("session_id") or str(uuid.uuid4())
        try:
            self._register(session_id, peer, "received")
        except (ValueError, RpcError):
            return {"accepted": False, "reason": "invalid or already owned chat session"}
        return {"accepted": True, "session_id": session_id}

    def _register(self, session_id, peer, direction):
        self._transcript_path(session_id)
        row = self.manager._conn.execute("SELECT * FROM n2n_chat_session WHERE id=?", (session_id,)).fetchone()
        if row and (row["peer_identity"] != peer or row["direction"] != direction):
            raise RpcError(ERR_SEVERED, "chat session belongs to another peer or direction")
        self.manager._conn.execute(
            "INSERT OR IGNORE INTO n2n_chat_session (id, peer_identity, direction, started_at, "
            "last_activity_at, transcript_ref) VALUES (?,?,?,?,?,?)",
            (session_id, peer, direction, _now(), _now(), str(self._transcript_path(session_id))))
        self.manager._conn.commit()

    async def handle_chat_message(self, channel, params):
        peer = channel.peer_identity
        from .negotiate import allows  # tier-0 default-deny (see handle_chat_open)
        if not allows(getattr(channel, "attestation", "self-asserted"), "chat/message"):
            raise RpcError(ERR_SEVERED,
                           "possession proof required for chat (tier-0 self-asserted peer)")
        row = self.manager.get_peer(peer)
        if not row or not row["chat_enabled"] or not self.manager.is_federated(peer):
            raise RpcError(ERR_SEVERED, "chat not enabled")
        session_id = params.get("session_id")
        self._require_session(session_id, peer, "received")
        if not self.authz._check_rate(peer):
            raise RpcError(ERR_RATE_LIMITED, "chat rate limit exceeded")
        if not self.authz.reserve_request(peer):
            raise RpcError(ERR_BUDGET_EXHAUSTED, "daily budget exhausted")
        session_id = params.get("session_id")
        text = params.get("text", "")
        self._append(session_id, f"[{peer}] {text}")
        from .execution import conversation_id
        session_key=conversation_id(self.service.runtime.installation or str(self.manager.base_dir),peer,session_id)
        extra={'channel':channel,'peer':peer} if self.service.runtime.kind=='hermes' else {}
        reply, tokens = await self._ask_gateway(text, session_key=session_key,**extra)
        self.authz.debit(peer, requests=0, tokens=tokens)
        self._append(session_id, f"[{self.service.local_identity}] {reply}")
        self._touch(session_id)
        self.audit.record(direction="inbound", peer_identity=peer, target_type="chat",
                          target_name=session_id, request_id=session_id, decision="allowlisted",
                          outcome="success")
        return {"session_id": session_id, "text": reply, "tokens_used": tokens}

    async def _ask_gateway(self, text: str, session_key: str = "n2n-chat", channel=None, peer=None):
        # gateway.py talks to the gateway's own WS RPC protocol directly
        # (feature 116) -- see its module docstring for why a per-turn CLI
        # subprocess was replaced with a persistent connection.
        from .gateway import run_agent_turn
        idle = int(os.environ.get("N2N_CHAT_IDLE_TIMEOUT_S", "300"))
        prompt = f"[A federated NetClaw peer is asking you this]\n{text}"
        extra={}
        if self.service.runtime.kind=='hermes':
            def current(_):
                row=self.manager.get_peer(peer)
                return bool(channel and not getattr(channel,'_closed',False) and row and row['chat_enabled'] and self.manager.is_federated(peer))
            extra['execution']=self.service.execution_context(requester=peer,origin='external',request=str(uuid.uuid4()),conversation=session_key,
                target_type='chat',target=session_key,prompt=prompt,profile='chat',authorize=current,timeout_s=idle)
        return await run_agent_turn(prompt, session_key=session_key, timeout_s=idle,
                                    untrusted=True,**extra)

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
            self._register(session_id, ident, "initiated")
        self._require_session(session_id, ident, "initiated")
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

    def _transcript_path(self, session_id):
        if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", session_id):
            raise RpcError(ERR_SEVERED, "invalid chat session id")
        if self.chats_dir.is_symlink():
            raise ValueError("Linked transcript directory refused")
        return self.chats_dir / f"{session_id}.txt"

    def _require_session(self, session_id, peer, direction):
        self._transcript_path(session_id)
        row = self.manager._conn.execute("SELECT * FROM n2n_chat_session WHERE id=?", (session_id,)).fetchone()
        if not row or row["peer_identity"] != peer or row["direction"] != direction:
            raise RpcError(ERR_SEVERED, "unknown or unowned chat session")

    def _append(self, session_id: str, line: str):
        path = self._transcript_path(session_id)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("Transcript must be a regular file")
            os.fchmod(fd, 0o600)
            # Escape embedded newlines so peer text cannot forge another log line.
            data = f"{_now()} {json.dumps(line, ensure_ascii=False)}\n".encode()
            with os.fdopen(fd, "ab", closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(fd)

    def _touch(self, session_id: str):
        self.manager._conn.execute(
            "UPDATE n2n_chat_session SET last_activity_at=?, message_count=message_count+1 WHERE id=?",
            (_now(), session_id))
        self.manager._conn.commit()

    def list_sessions(self) -> list:
        return [dict(r) for r in self.manager._conn.execute(
            "SELECT * FROM n2n_chat_session ORDER BY last_activity_at DESC LIMIT 50")]
