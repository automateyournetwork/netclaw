"""FederationService — wires manager + channel + inventory into the daemon.

Owns the set of live NCFED channels, registers the lifecycle (n2n/hello,
n2n/consent_state, n2n/sever) and capability (n2n/inventory, n2n/inventory_get)
wire methods, and drives outbound channel establishment when both consents are
present (lower-AS initiates).
"""

import asyncio
import logging
import os
from typing import Dict, Optional

from ..constants import NCFED_MAGIC
from .manager import FederationManager, PeerState, peer_identity
from .channel import FederationChannel, read_handshake, build_handshake
from .inventory import InventoryBuilder
from .audit import Auditor

logger = logging.getLogger("n2n.service")


def local_model() -> str:
    """The model this claw runs, advertised to peers in n2n/hello so they can
    size their wait timeouts. Falls back through the common env vars."""
    return (os.environ.get("N2N_MODEL")
            or os.environ.get("NETCLAW_MODEL")
            or os.environ.get("BEDROCK_MODEL_ID")
            or "unknown")


def local_suggested_timeout_s() -> int:
    """How long a peer should wait for OUR chat/skill replies. A slow local
    model (e.g. an Ollama Cloud model) advertises a larger value so the far
    side doesn't give up mid-turn. Defaults to the chat idle timeout."""
    try:
        return int(os.environ.get("N2N_SUGGESTED_TIMEOUT_S")
                   or os.environ.get("N2N_CHAT_IDLE_TIMEOUT_S")
                   or "300")
    except (TypeError, ValueError):
        return 300


# Upper bound applied to a peer-advertised timeout before we honor it, so a
# misconfigured or hostile peer can't make us block indefinitely.
MAX_HONORED_TIMEOUT_S = 900


class FederationService:
    def __init__(self, *, local_as: int, router_id: str, display_name: str = "",
                 refresh_s: int = 21600, manager: Optional[FederationManager] = None):
        self.local_as = local_as
        self.router_id = router_id
        self.local_identity = peer_identity(local_as, router_id)
        self.display_name = display_name or os.uname().nodename
        self.refresh_s = refresh_s
        self.manager = manager or FederationManager()
        self.inventory = InventoryBuilder(self.manager)
        self.audit = Auditor(self.manager)
        self.channels: Dict[str, FederationChannel] = {}
        os.environ["N2N_LOCAL_IDENTITY"] = self.local_identity

        # US2/US3 engines
        from .authorization import Authorizer
        from .invocation import Invoker
        from .chat import ChatManager
        self.authz = Authorizer(self.manager)
        self.invoker = Invoker(self)
        self.chat = ChatManager(self)
        # Optional callback the daemon sets to push approval prompts to the
        # operator's channels (Slack/Webex/CLI) via the gateway (FR-013).
        self.approval_notifier = None

        # Handler map passed to every channel this service creates (per-service,
        # not global — see FederationChannel).
        self.handlers = {
            "n2n/hello": self._on_hello,
            "n2n/consent_state": self._on_consent_state,
            "n2n/sever": self._on_sever,
            "n2n/inventory": self._on_inventory,
            "n2n/inventory_get": self._on_inventory_get,
            "n2n/tools/call": self.invoker.handle_tools_call,
            "n2n/tasks/submit": self.invoker.handle_task_submit,
            "n2n/chat/open": self.chat.handle_chat_open,
            "n2n/chat/message": self.chat.handle_chat_message,
        }

    def notify_approval(self, invocation_id, peer, target_type, target_name):
        """Push an approval prompt to the operator's channels (FR-013). Best-effort."""
        logger.info("APPROVAL NEEDED: %s wants to run %s '%s' (invocation %s)",
                    peer, target_type, target_name, invocation_id)
        if self.approval_notifier:
            try:
                self.approval_notifier(invocation_id, peer, target_type, target_name)
            except Exception as e:
                logger.warning("approval notifier failed: %s", e)

    async def _on_hello(self, channel, params):
        channel.display_name = params.get("display_name")
        # Peer presence on the channel implies they consented to us.
        self.manager.remote_consent(channel.peer_as, channel.peer_router_id)
        # Record the model + suggested wait timeout the peer advertised so our
        # outbound chat/skill calls to them size their timeout correctly.
        self.manager.set_peer_profile(channel.peer_identity,
                                      model=params.get("model"),
                                      suggested_timeout_s=params.get("suggested_timeout_s"))
        state = self.manager._recompute_state(channel.peer_identity)
        if state == PeerState.FEDERATED:
            asyncio.create_task(self._advertise_to(channel))
        return {"identity": self.local_identity, "display_name": self.display_name,
                "version": "1.0", "model": local_model(),
                "suggested_timeout_s": local_suggested_timeout_s()}

    async def _on_consent_state(self, channel, params):
        return {"state": self.manager.get_peer(channel.peer_identity)["state"]}

    async def _on_sever(self, channel, params):
        self.manager.sever(channel.peer_identity)
        await channel.close()
        self.channels.pop(channel.peer_identity, None)
        return {"acked": True}

    async def _on_inventory(self, channel, params):
        self.inventory.cache_remote(channel.peer_identity, params)
        logger.info("Cached inventory v%s from %s", params.get("version"), channel.peer_identity)
        return {"accepted": True, "version": params.get("version")}

    async def _on_inventory_get(self, channel, params):
        return self.inventory.build(channel.peer_identity)

    async def refresh_from(self, ident: str) -> dict:
        """Actively PULL a federated peer's inventory over the open channel
        (n2n/inventory_get) and cache it. Recovers from a missed push — e.g.
        when the peer consented after the channel opened."""
        ch = self.channels.get(ident)
        if not ch:
            return {"error": "no channel to peer"}
        if not self.manager.is_federated(ident):
            return {"error": "peer not federated"}
        try:
            inv = await ch.call("n2n/inventory_get", {}, timeout=15.0)
            self.inventory.cache_remote(ident, inv)
            logger.info("Pulled inventory v%s from %s", inv.get("version"), ident)
            return {"pulled": True, "version": inv.get("version")}
        except Exception as e:
            return {"error": str(e)}

    async def ensure_advertised(self, ident: str):
        """If a channel exists and the peer is federated, (re)advertise to it.
        Called when local consent completes federation after the channel opened."""
        ch = self.channels.get(ident)
        if ch and self.manager.is_federated(ident):
            await self._advertise_to(ch)

    async def _advertise_to(self, channel):
        """Push our inventory to the peer. Retries briefly because the peer may
        finish its own consent→federated transition a beat after we do (both
        sides advertise on federate, which can race)."""
        inv = self.inventory.build(channel.peer_identity)
        for attempt in range(4):
            try:
                await channel.call("n2n/inventory", inv, timeout=30.0)
                return
            except Exception as e:
                if attempt == 3:
                    logger.warning("Advertise to %s failed: %s", channel.peer_identity, e)
                    return
                await asyncio.sleep(0.2)

    # ---- inbound channel (called from agent discrimination) -----------

    async def accept_channel(self, peer_as: int, router_id: str, reader, writer):
        ident = peer_identity(peer_as, router_id)
        # Channel-anchored identity check (FR-003): only accept for a peer we
        # know and have at least locally consented / federated with.
        peer = self.manager.get_peer(ident)
        if not peer or peer["state"] in (PeerState.NOT_FEDERATED.value, PeerState.SEVERED.value):
            # Learn presence but require local consent before doing anything.
            self.manager.upsert_peer(peer_as, router_id)
            if not self.manager._has_consent(ident, "local_grant"):
                logger.info("NCFED from %s but no local consent — recording remote consent only", ident)
        # Send our handshake reply
        writer.write(build_handshake(self.local_as, self.router_id))
        await writer.drain()
        ch = FederationChannel(reader, writer, local_identity=self.local_identity,
                               peer_as=peer_as, peer_router_id=router_id,
                               manager=self.manager, is_initiator=False, handlers=self.handlers)
        self.channels[ident] = ch
        await ch.start()
        # The initiator sends n2n/hello; our _on_hello handler replies and, if
        # both consents are present, advertises. Nothing more to do here.
        logger.info("Accepted NCFED channel from %s", ident)

    # ---- outbound channel (lower-AS initiates) ------------------------

    async def open_channel(self, peer_as: int, router_id: str, host: str, port: int):
        ident = peer_identity(peer_as, router_id)
        if self.local_as >= peer_as:
            logger.debug("Not initiating to %s — higher/equal AS waits", ident)
            return
        # An explicit (re)dial always replaces any existing channel. A channel
        # can silently die (ngrok resets the long-lived TCP) without being
        # removed from the registry, leaving a zombie that makes chat/open time
        # out forever. Tear it down and build fresh so re-dial actually recovers.
        old = self.channels.pop(ident, None)
        if old is not None:
            logger.info("Replacing existing channel to %s (re-dial)", ident)
            try:
                await old.close()
            except Exception:
                pass
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=30.0)
            writer.write(build_handshake(self.local_as, self.router_id))
            await writer.drain()
            # Acceptor replies with a full handshake (magic + AS + router-id);
            # consume the 5-byte magic before reading AS + router-id.
            reply_magic = await asyncio.wait_for(reader.readexactly(5), timeout=10.0)
            if reply_magic != NCFED_MAGIC:
                logger.warning("Bad reply magic from %s: %r", ident, reply_magic)
                writer.close()
                return
            hs = await read_handshake(reader)
            if not hs or peer_identity(hs[0], hs[1]) != ident:
                logger.warning("Handshake mismatch opening channel to %s", ident)
                writer.close()
                return
            ch = FederationChannel(reader, writer, local_identity=self.local_identity,
                                   peer_as=peer_as, peer_router_id=router_id,
                                   manager=self.manager, is_initiator=True, handlers=self.handlers)
            self.channels[ident] = ch
            await ch.start()
            resp = await ch.call("n2n/hello", {"identity": self.local_identity,
                                               "display_name": self.display_name, "versions": ["1.0"],
                                               "model": local_model(),
                                               "suggested_timeout_s": local_suggested_timeout_s()})
            ch.display_name = resp.get("display_name")
            # Store the acceptor's advertised model + suggested wait timeout.
            self.manager.set_peer_profile(ident, model=resp.get("model"),
                                          suggested_timeout_s=resp.get("suggested_timeout_s"))
            self.manager.remote_consent(peer_as, router_id)
            if self.manager._recompute_state(ident) == PeerState.FEDERATED:
                await self._advertise_to(ch)
            logger.info("Opened NCFED channel to %s", ident)
        except Exception as e:
            logger.warning("open_channel to %s failed: %s", ident, e)

    async def sever_local(self, ident: str) -> bool:
        ok = self.manager.sever(ident)
        ch = self.channels.pop(ident, None)
        if ch:
            try:
                await ch.notify("n2n/sever", {})
            except Exception:
                pass
            await ch.close()
        return ok
