"""FederationService — wires manager + channel + inventory into the daemon.

Owns the set of live NCFED channels, registers the lifecycle (n2n/hello,
n2n/consent_state, n2n/sever) and capability (n2n/inventory, n2n/inventory_get)
wire methods, and drives outbound channel establishment when both consents are
present (lower-AS initiates).
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Optional

from ..constants import NCFED_MAGIC
from .manager import FederationManager, PeerState, peer_identity
from .channel import FederationChannel, read_handshake, build_handshake
from .inventory import InventoryBuilder
from .audit import Auditor

logger = logging.getLogger("n2n.service")


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
        from .tasks import TaskManager
        self.authz = Authorizer(self.manager)
        self.invoker = Invoker(self)
        self.chat = ChatManager(self)
        self.tasks = TaskManager(self.manager, self.audit,
                                 retention_s=int(os.environ.get("N2N_TASK_RETENTION_S", "3600")))
        # Optional callback the daemon sets to push approval prompts to the
        # operator's channels (Slack/Webex/CLI) via the gateway (FR-013).
        self.approval_notifier = None

        # US2 auto-reconnect: per-peer ChannelHealth (in-memory) + supervisor.
        self.peer_caps: Dict[str, dict] = {}   # ident -> capability descriptor (US4)
        self.health: Dict[str, dict] = {}   # ident -> {state, attempts, next_retry_at, last_seen}
        self._supervisor_task = None
        self._backoff_min = int(os.environ.get("N2N_RECONNECT_BACKOFF_MIN_S", "5"))
        self._backoff_max = int(os.environ.get("N2N_RECONNECT_BACKOFF_MAX_S", "60"))
        self._unreachable_after = int(os.environ.get("N2N_RECONNECT_UNREACHABLE_AFTER", "5"))

        # Handler map passed to every channel this service creates (per-service,
        # not global — see FederationChannel).
        self.handlers = {
            "n2n/hello": self._on_hello,
            "n2n/consent_state": self._on_consent_state,
            "n2n/endpoint_update": self._on_endpoint_update,
            "n2n/sever": self._on_sever,
            "n2n/inventory": self._on_inventory,
            "n2n/inventory_get": self._on_inventory_get,
            "n2n/tools/call": self.invoker.handle_tools_call,
            "n2n/tasks/submit": self.invoker.handle_task_submit,
            "n2n/tasks/status": self.invoker.handle_task_status,
            "n2n/tasks/result": self.invoker.handle_task_result,
            "n2n/tasks/cancel": self.invoker.handle_task_cancel,
            "n2n/chat/open": self.chat.handle_chat_open,
            "n2n/chat/message": self.chat.handle_chat_message,
        }

        # ── iN2N (feature 056): internal federation within one risk ──────
        from .risk import RiskManager
        from .router import RiskRouter
        self.risk = RiskManager(self.manager)
        self.router = RiskRouter(self.risk)
        self.member_channels: Dict[str, object] = {}   # border side: member_id -> InternalChannel
        self.border_channel = None                      # member side: our channel to the Border
        self.member_last_activity = time.time()         # member side: for cold/on-demand idle-exit
        self._spawning = set()                          # border side: members mid cold-start
        # member side: the capabilities this claw will actually run (its scope).
        # Populated from N2N_MEMBER_SCOPE (JSON list of capability names) or set
        # programmatically; enforced on inbound submits (FR-023).
        self.member_scope = set()
        try:
            import json as _json
            self.member_scope = set(_json.loads(os.environ.get("N2N_MEMBER_SCOPE", "[]")))
        except Exception:
            self.member_scope = set()
        # Border-side iN2N handlers (the member authenticates, then we route to it).
        self._in2n_border_handlers = {
            "in2n/enroll": self._in2n_on_enroll,
            "in2n/hello": self._in2n_on_hello,
            "n2n/inventory": self._in2n_on_member_inventory,
        }
        # Member-side iN2N handlers (the Border delegates work to us).
        self._in2n_member_handlers = {
            "n2n/tasks/submit": self._in2n_member_submit,
            "n2n/tasks/status": self.invoker.handle_task_status,
            "n2n/tasks/result": self.invoker.handle_task_result,
            "n2n/tasks/cancel": self.invoker.handle_task_cancel,
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
        # US4: store the peer's capability descriptor (or 052 baseline if absent)
        from .negotiate import normalize, local_descriptor
        self.peer_caps[channel.peer_identity] = normalize(params.get("capabilities"))
        # Peer presence on the channel implies they consented to us.
        self.manager.remote_consent(channel.peer_as, channel.peer_router_id)
        state = self.manager._recompute_state(channel.peer_identity)
        if state == PeerState.FEDERATED:
            asyncio.create_task(self._advertise_to(channel))
        return {"identity": self.local_identity, "display_name": self.display_name,
                "version": "1.0", "capabilities": local_descriptor()}

    def _register_channel(self, ident, ch):
        """Track a channel and set its on_close hook so a dead channel
        deregisters itself (US2) — no zombie channels lingering in the registry."""
        def _deregister(closed_ch):
            if self.channels.get(ident) is closed_ch:
                self.channels.pop(ident, None)
                logger.info("Channel to %s closed — deregistered", ident)
        ch.on_close = _deregister
        self.channels[ident] = ch

    async def _on_endpoint_update(self, channel, params):
        """US3: a federated peer announced a new public endpoint over its
        authenticated channel. Trust it only for THIS channel's identity
        (FR-012), update the record, and let the supervisor re-dial (FR-011)."""
        endpoint = params.get("endpoint", "")
        ident = channel.peer_identity  # bound to the authenticated session, not attacker-supplied
        if not self.manager.is_federated(ident) or ":" not in endpoint:
            return {"accepted": False}
        host, _, port = endpoint.rpartition(":")
        try:
            port = int(port)
        except ValueError:
            return {"accepted": False}
        self.manager.upsert_peer(channel.peer_as, channel.peer_router_id,
                                 endpoint_host=host, endpoint_port=port)
        self.manager._conn.execute(
            "UPDATE federation_peer SET endpoint_updated_at=? WHERE identity=?",
            (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), ident))
        self.manager._conn.commit()
        # Reset backoff so the supervisor re-dials the new endpoint promptly.
        self.health.pop(ident, None)
        logger.info("Peer %s announced new endpoint %s — will re-dial", ident, endpoint)
        return {"accepted": True}

    async def reannounce_endpoint(self, new_endpoint: str):
        """US3: tell every federated peer with a live channel our new public
        endpoint so they re-dial without a manual host:port swap (FR-010)."""
        for ident, ch in list(self.channels.items()):
            if self.manager.is_federated(ident):
                try:
                    await ch.call("n2n/endpoint_update",
                                  {"identity": self.local_identity, "endpoint": new_endpoint},
                                  timeout=15.0)
                except Exception as e:
                    logger.debug("endpoint reannounce to %s failed: %s", ident, e)

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
        return self.inventory.build(channel.peer_identity, posture=getattr(self, 'posture_cache', None))

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
        inv = self.inventory.build(channel.peer_identity, posture=getattr(self, 'posture_cache', None))
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

    def _en2n_allowed(self) -> bool:
        """FR-014: only a Border (or a standalone claw) runs the external eN2N
        stack. A Member never federates externally — it talks only to its Border."""
        try:
            return self.risk.role() != "member"
        except Exception:
            return True  # fail open to pre-056 behavior if risk state is unavailable

    async def accept_channel(self, peer_as: int, router_id: str, reader, writer):
        if not self._en2n_allowed():
            logger.info("iN2N Member role — refusing inbound eN2N channel (FR-014)")
            try:
                writer.close()
            except Exception:
                pass
            return
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
        self._register_channel(ident, ch)
        await ch.start()
        # The initiator sends n2n/hello; our _on_hello handler replies and, if
        # both consents are present, advertises. Nothing more to do here.
        logger.info("Accepted NCFED channel from %s", ident)

    # ---- outbound channel (lower-AS initiates) ------------------------

    async def open_channel(self, peer_as: int, router_id: str, host: str, port: int):
        if not self._en2n_allowed():
            logger.info("iN2N Member role — not opening outbound eN2N channel (FR-014)")
            return
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
            self._register_channel(ident, ch)
            await ch.start()
            from .negotiate import local_descriptor, normalize
            resp = await ch.call("n2n/hello", {"identity": self.local_identity,
                                               "display_name": self.display_name,
                                               "versions": ["1.0"],
                                               "capabilities": local_descriptor()})
            ch.display_name = resp.get("display_name")
            self.peer_caps[ident] = normalize(resp.get("capabilities"))  # US4
            self.manager.remote_consent(peer_as, router_id)
            if self.manager._recompute_state(ident) == PeerState.FEDERATED:
                await self._advertise_to(ch)
            logger.info("Opened NCFED channel to %s", ident)
            self.health[ident] = {"state": "up", "attempts": 0, "next_retry_at": 0,
                                  "last_seen": time.time()}
        except Exception as e:
            logger.warning("open_channel to %s failed: %s", ident, e)

    # ---- US2: auto-reconnect supervisor + health ----------------------

    def start_supervisor(self):
        """Launch the background reconnect supervisor (call once, from an event
        loop — e.g. the daemon main after the speaker starts)."""
        if self._supervisor_task is None:
            self._supervisor_task = asyncio.create_task(self._reconnect_supervisor())
            logger.info("N2N reconnect supervisor started")

    async def _reconnect_supervisor(self):
        """For each federated peer with no live channel, re-dial with bounded
        backoff (FR-007/008). Consent persists, so no re-consent is needed."""
        while True:
            try:
                await asyncio.sleep(2)
                now = time.time()
                for peer in self.manager.list_peers():
                    ident = peer["identity"]
                    if peer["state"] != PeerState.FEDERATED.value:
                        continue
                    if ident in self.channels:
                        continue  # live
                    # Only the lower-AS side dials; higher-AS waits for inbound.
                    if self.local_as >= peer["peer_as"]:
                        continue
                    if not peer.get("endpoint_host") or not peer.get("endpoint_port"):
                        continue  # no endpoint to dial yet
                    h = self.health.setdefault(ident, {"state": "reconnecting", "attempts": 0,
                                                        "next_retry_at": 0, "last_seen": 0})
                    if now < h["next_retry_at"]:
                        continue
                    h["state"] = "reconnecting"
                    await self.open_channel(peer["peer_as"], peer["router_id"],
                                            peer["endpoint_host"], peer["endpoint_port"])
                    if ident not in self.channels:  # dial failed → back off
                        h["attempts"] += 1
                        backoff = min(self._backoff_min * (2 ** min(h["attempts"], 6)),
                                      self._backoff_max)
                        h["next_retry_at"] = now + backoff
                        if h["attempts"] >= self._unreachable_after:
                            h["state"] = "unreachable"  # keep retrying, but flag for display
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("reconnect supervisor loop error: %s", e)

    async def ensure_channel(self, ident: str):
        """On-demand reconnect: if no live channel, dial now (FR-009). Returns
        the channel or raises so the caller fails fast rather than hanging."""
        ch = self.channels.get(ident)
        if ch:
            return ch
        peer = self.manager.get_peer(ident)
        if not peer or peer["state"] != PeerState.FEDERATED.value:
            raise RuntimeError("peer_unreachable: not federated")
        if self.local_as >= peer["peer_as"]:
            raise RuntimeError("peer_unreachable: awaiting inbound (higher AS)")
        if not peer.get("endpoint_host"):
            raise RuntimeError("peer_unreachable: no endpoint")
        await self.open_channel(peer["peer_as"], peer["router_id"],
                                peer["endpoint_host"], peer["endpoint_port"])
        ch = self.channels.get(ident)
        if not ch:
            raise RuntimeError("peer_unreachable: reconnect failed")
        return ch

    def health_of(self, ident: str) -> dict:
        h = self.health.get(ident, {"state": "unknown", "attempts": 0, "last_seen": 0})
        return {"channel_state": ("up" if ident in self.channels else h.get("state", "down")),
                "attempts": h.get("attempts", 0), "last_seen": h.get("last_seen", 0)}

    def health_report(self) -> dict:
        """iN2N truthful fault isolation (feature 057, US6/FR-017/018).

        Distinguishes three causes so the operator heartbeat gives an accurate
        diagnosis instead of the 056 misdiagnosis (a poll bug read as a member
        flap). Precedence: daemon > member > backend > none — a daemon-down masks
        member reports (you can't know member state if the daemon is down), and a
        backend fault is only reported when the daemon AND the member are up.

          * daemon-down       — the iN2N listener isn't bound (federation layer fault)
          * member-down       — daemon up, but a member has no live channel
          * backend-unreachable — member up, but its last task reported its backend
                                  (device/API) unreachable — NOT a federation fault
        """
        daemon_up = self.risk.is_border() and getattr(self, "_in2n_server", None) is not None
        members, backends = {}, {}
        member_fault = backend_fault = False
        for m in self.risk.list_members():
            mid = m["member_id"]
            live = mid in self.member_channels
            will_cold = (not live) and bool(m.get("launch_cmd")) and (
                bool(m.get("on_demand")) or self.risk.managed_by(mid) == "service")
            members[mid] = {"state": "up" if live else "down", "will_cold_start": will_cold}
            if not live and m.get("state") == "active":
                member_fault = True
            # backend reachability is reported by the member in its health JSON
            # (set from a task result); absence = unknown, not a fault.
            backend = "unknown"
            try:
                h = json.loads(m["health"]) if m.get("health") else {}
                backend = h.get("backend", "unknown")
            except (ValueError, TypeError):
                backend = "unknown"
            backends[mid] = backend
            if live and backend == "unreachable":
                backend_fault = True

        if not daemon_up:
            fault_class = "daemon"
        elif member_fault:
            fault_class = "member"
        elif backend_fault:
            fault_class = "backend"
        else:
            fault_class = "none"
        return {"daemon": "up" if daemon_up else "down", "members": members,
                "backends": backends, "fault_class": fault_class}

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

    # ================================================================
    # iN2N — internal federation within one risk (feature 056)
    # Hub-and-spoke: members dial the Border outbound; the Border routes and
    # delegates to them. Trust is a pinned self-signed key (TOFU), not consent.
    # ================================================================

    # ---- Border side: accept a member dial-in + authenticate ----------

    async def accept_internal(self, reader, writer):
        """Border side: a member dialed our iN2N listener. Send the challenge
        preamble, then run an InternalChannel; the member authenticates via
        in2n/enroll (first time) or in2n/hello (pinned-key proof)."""
        from .internal_channel import InternalChannel, send_border_preamble
        nonce = await send_border_preamble(writer)
        ch = InternalChannel(reader, writer, local_identity=self.local_identity,
                             member_id=None, is_border_side=True,
                             handlers=self._in2n_border_handlers, nonce=nonce)
        await ch.start()
        logger.info("Accepted iN2N dial-in (awaiting member auth)")
        return ch

    def _register_member_channel(self, member_id, ch):
        """Track a member's channel; deregister + mark unreachable on close."""
        def _deregister(closed_ch):
            if self.member_channels.get(member_id) is closed_ch:
                self.member_channels.pop(member_id, None)
                self.risk.mark_unreachable(member_id)
                logger.info("iN2N member %s channel closed — deregistered", member_id)
        ch.on_close = _deregister
        self.member_channels[member_id] = ch

    async def _in2n_on_enroll(self, channel, params):
        """First-time enrollment: verify token + proof-of-possession, pin key."""
        from .internal_channel import _ERR_NOT_TRUSTED, _ERR_NOT_A_BORDER
        from .channel import RpcError
        if not self.risk.is_border():
            raise RpcError(_ERR_NOT_A_BORDER, "this claw is not a Border")
        token = params.get("token", "")
        member_id = params.get("member_id", "")
        cert_pem = params.get("cert_pem", "")
        signature = bytes.fromhex(params.get("signature", "") or "")
        # Proof the dialer holds the private key for the cert it presents (FR-013).
        if not self.risk.verify_possession(cert_pem, channel.nonce, signature):
            raise RpcError(_ERR_NOT_TRUSTED, "key possession proof failed")
        try:
            res = self.risk.consume_token(
                token, member_id, cert_pem,
                scope=params.get("scope"),
                runtime_kind=params.get("runtime_kind", "process"),
                display_name=params.get("display_name"),
                transport_binding=params.get("transport_binding", "distributed"))
        except ValueError as e:
            raise RpcError(_ERR_NOT_TRUSTED if "TRUSTED" in str(e) else -32021, str(e))
        channel.member_id = member_id
        channel.peer_identity = member_id
        channel.trusted = True
        self.risk.verify_member(member_id, self.risk.fingerprint_of(cert_pem))
        self._register_member_channel(member_id, channel)
        self.audit.record(direction="inbound", peer_identity=member_id,
                          target_type="enroll", target_name=member_id,
                          decision="enrolled", outcome="success", channel_kind="in2n")
        logger.info("iN2N member %s enrolled + active", member_id)
        return res

    async def _in2n_on_hello(self, channel, params):
        """Reconnect: authenticate against the pinned key (FR-013a)."""
        from .internal_channel import _ERR_NOT_TRUSTED
        from .channel import RpcError
        member_id = params.get("member_id", "")
        fingerprint = params.get("key_fingerprint", "")
        signature = bytes.fromhex(params.get("signature", "") or "")
        mem = self.risk.get_member(member_id)
        if not mem or not mem.get("pinned_key"):
            raise RpcError(_ERR_NOT_TRUSTED, "unknown or unpinned member")
        ok = (mem["key_fingerprint"] == fingerprint
              and self.risk.verify_possession(mem["pinned_key"], channel.nonce, signature)
              and self.risk.verify_member(member_id, fingerprint))
        if not ok:
            quarantined = self.risk.record_auth_failure(member_id)
            if quarantined:
                self.notify_member_quarantine(member_id)
            raise RpcError(_ERR_NOT_TRUSTED, "pinned-key auth failed")
        channel.member_id = member_id
        channel.peer_identity = member_id
        channel.trusted = True
        self._register_member_channel(member_id, channel)
        return {"risk": self.risk.get_risk().get("risk_name"), "trusted": True,
                "member_state": "active"}

    async def _in2n_on_member_inventory(self, channel, params):
        """A member advertises its (scoped) capabilities. We already know its
        scope from enrollment; record freshness and ack (no secrets, reused guard)."""
        if channel.member_id:
            self.risk.update_health(channel.member_id, inventory_at=time.time())
        return {"accepted": True}

    def notify_member_quarantine(self, member_id):
        """Surface an auto-quarantine to the operator (in-band; FR-013d). Uses the
        same approval_notifier hook the daemon wires to the gateway if present."""
        logger.warning("iN2N ALERT: member %s auto-quarantined (repeated auth/health failure)",
                       member_id)
        if self.approval_notifier:
            try:
                self.approval_notifier(None, member_id, "quarantine", member_id)
            except Exception:
                pass

    # ---- Border side: route + delegate to a member --------------------

    def _audit_actor(self) -> str:
        """Attributable actor for the GAIT trail (FR-012): '<risk>/border' when
        this claw is a Border, else its federation identity."""
        try:
            risk = self.risk.get_risk()
            if risk.get("role") == "border" and risk.get("risk_name"):
                return f"{risk['risk_name']}/border"
        except Exception:
            pass
        return self.local_identity

    async def _component_scan_member(self, member_id: str):
        """US3/FR-008: DefenseClaw component scan of a member's scoped skills,
        cached in the member row. Returns (ok, verdict). 'pass' is cached and
        short-circuits re-scan; a flag blocks the member until re-provisioned."""
        from . import controls
        cached = self.risk.component_scan(member_id)
        if cached == "pass":
            return True, "pass"
        if cached and cached.startswith("flagged:"):
            return False, cached
        mem = self.risk.get_member(member_id)
        skills = []
        for e in self.risk._scope_list(mem.get("scope") if mem else None):
            if isinstance(e, dict) and e.get("tier") == "specialty":
                skills.append(e.get("name"))
            elif isinstance(e, str) and e not in self.risk._BASE_NAMES:
                skills.append(e)
        ok, verdict = await controls.component_scan(skills)
        # Cache only definitive verdicts (pass/flagged); transient errors re-scan.
        if verdict == "pass" or verdict.startswith("flagged:"):
            self.risk.set_component_scan(member_id, verdict)
        return ok, verdict

    async def route_and_delegate(self, capability: str, input_text: str) -> dict:
        """Select the owning member (deterministic) and delegate the work as an
        async task over its channel. Returns {task_id, member_id} or an error."""
        from .router import NoCapableMember
        try:
            member_id = self.router.select_member(capability)["member_id"]
        except NoCapableMember as e:
            return {"error": "IN2N_ERR_NO_CAPABLE_MEMBER", "message": str(e)}
        return await self.delegate_to_member(member_id, capability, input_text)

    async def ensure_member_up(self, member_id: str, wait_s: float = 30.0):
        """Cold/on-demand: if a member has no live channel, bring it up and wait
        for it to dial in and authenticate. Returns the channel, or None if it
        can't be brought up (e.g. a remote member the Border can't spawn).

        Feature 057:
          * single-owner (US5/FR-014): a member managed by its own durable service
            is NOT shell-spawned — the cold-start path ensures its unit is active
            instead (no double-launch).
          * fail-closed sandbox (US2/FR-005): in production a member that cannot be
            sandboxed is NOT cold-started; the cold-start wait is widened to absorb
            OpenShell spin-up so a sandboxed cold member isn't falsely unreachable."""
        from . import controls
        ch = self.member_channels.get(member_id)
        if ch is not None:
            return ch

        # US5 single-owner: a service-managed member is owned by its systemd unit.
        if self.risk.managed_by(member_id) == "service":
            unit = self.risk.service_unit(member_id) or f"netclaw-member-{member_id.replace('/', '-')}.service"
            await self._ensure_unit_active(unit)
            return await self._wait_for_dial(member_id, wait_s)

        launch_cmd, on_demand = self.risk.launch_spec(member_id)
        if not launch_cmd or not on_demand:
            return None   # remote member (or no spawn spec) — can't cold-start here

        # US2 fail-closed: in production a member must run CONFINED. Refuse to
        # cold-start if the confinement mechanism is unavailable; otherwise launch
        # the on-demand member inside a transient confined systemd unit.
        confined = False
        if controls.is_production():
            ok, detail = await controls.sandbox_available()
            if not ok:
                logger.warning("iN2N production: refusing cold-start of %s — "
                               "confinement unavailable (%s)", member_id, detail)
                return None
            confined = True
            wait_s = max(wait_s, 90.0)   # absorb confined-launch overhead
        if member_id in self._spawning:
            # another route is already cold-starting it; just wait
            pass
        else:
            self._spawning.add(member_id)
            try:
                if confined:
                    argv = controls.confined_cold_start(launch_cmd, member_id)
                    logger.info("iN2N cold-start (confined): %s", member_id)
                    await asyncio.create_subprocess_exec(
                        *argv, stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL)
                else:
                    logger.info("iN2N cold-start: spawning on-demand member %s", member_id)
                    await asyncio.create_subprocess_shell(
                        launch_cmd, stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL)
            except Exception as e:
                logger.warning("cold-start spawn of %s failed: %s", member_id, e)
                self._spawning.discard(member_id)
                return None
        # Wait for the member to dial in + authenticate (channel registered).
        ch = await self._wait_for_dial(member_id, wait_s)
        self._spawning.discard(member_id)
        if ch is None:
            logger.warning("iN2N cold-start: %s did not come up within %ss", member_id, wait_s)
        return ch

    async def _wait_for_dial(self, member_id: str, wait_s: float = 30.0):
        """Wait until a member's channel is registered (it dialed in + authed)."""
        deadline = time.time() + wait_s
        while time.time() < deadline:
            ch = self.member_channels.get(member_id)
            if ch is not None:
                return ch
            await asyncio.sleep(0.5)
        return None

    async def _ensure_unit_active(self, unit: str) -> bool:
        """US5 single-owner: start a member's durable systemd --user unit if it
        isn't already active (never shell-spawn a service-managed member).
        Best-effort; returns True if the unit is (now) active."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "--user", "is-active", "--quiet", unit)
            if await proc.wait() == 0:
                return True
            logger.info("iN2N: starting durable member unit %s", unit)
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "--user", "start", unit,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            return await proc.wait() == 0
        except FileNotFoundError:
            logger.warning("systemctl --user not available; cannot manage unit %s", unit)
            return False
        except Exception as e:
            logger.warning("could not ensure unit %s active: %s", unit, e)
            return False

    async def delegate_to_member(self, member_id: str, capability: str,
                                 input_text: str) -> dict:
        from .channel import RpcError
        from . import controls, posture

        # US1/FR-003a: synchronous production preflight — the authoritative
        # fail-closed check. Skipped entirely in testing mode (guards off), which
        # also keeps this off the hot path / out of the frozen regression suite.
        enforcement = "testing"
        if controls.is_production():
            p = await posture.compute_posture(self)
            decision = posture.posture_ok_for_delegation(p)
            if not decision["allow"]:
                logger.warning("iN2N production preflight REFUSED delegation to %s: %s",
                               member_id, decision["reason"])
                return {"error": "production_degraded", "member_id": member_id,
                        "enforcement": decision["enforcement"],
                        "refused_control": decision["refused_control"],
                        "message": decision["reason"]}
            enforcement = decision["enforcement"]
            # US3/FR-008: component scan the member's scoped skills before it runs
            # (cached per member; a flagged component blocks that member).
            scan_ok, verdict = await self._component_scan_member(member_id)
            if not scan_ok:
                logger.warning("iN2N production: member %s blocked by component scan (%s)",
                               member_id, verdict)
                return {"error": "component_flagged", "member_id": member_id,
                        "enforcement": "refused:model-guard", "refused_control": "model-guard",
                        "message": f"DefenseClaw component scan blocked {member_id}: {verdict}"}

        ch = self.member_channels.get(member_id)
        if ch is None:
            ch = await self.ensure_member_up(member_id)   # cold-start on-demand members
        if ch is None:
            return {"error": "member_unreachable", "enforcement": enforcement,
                    "message": f"member {member_id} has no live channel "
                               f"(and could not be cold-started)"}
        try:
            resp = await ch.call("n2n/tasks/submit",
                                 {"skill": capability, "input_text": input_text}, timeout=30.0)
        except RpcError as e:
            return {"error": "out_of_scope" if e.code == -32031 else "delegation_failed",
                    "code": e.code, "message": e.message, "member_id": member_id,
                    "enforcement": enforcement}
        task_id = resp.get("task_id")
        if task_id:
            self.tasks.record_outbound(task_id, member_id, "skill", capability)
            # FR-020/C2: attribute the audit + GAIT event to the Border, tag the
            # channel, and flag audit-degraded runs.
            self.audit.record(direction="outbound", peer_identity=member_id,
                              target_type="skill", target_name=capability,
                              request_id=task_id, decision="requested",
                              outcome="submitted", channel_kind="in2n",
                              event="delegation", actor=self._audit_actor())
        return {"member_id": member_id, "enforcement": enforcement, **resp}

    async def poll_member_task(self, member_id: str, task_id: str, kind: str = "status") -> dict:
        """Border side: fetch an iN2N delegated task's status/result from the
        MEMBER over its internal channel (NOT the eN2N path). On a terminal
        result, cache it locally so it survives a member flap/restart."""
        ch = self.member_channels.get(member_id)
        if ch is None:
            # member not connected — try to (cold-)start it, else fall back local
            ch = await self.ensure_member_up(member_id, wait_s=15)
        if ch is None:
            return (self.tasks.result(task_id) if kind == "result"
                    else self.tasks.status(task_id))
        method = "n2n/tasks/result" if kind == "result" else "n2n/tasks/status"
        try:
            resp = await ch.call(method, {"task_id": task_id}, timeout=30.0)
        except Exception:
            return (self.tasks.result(task_id) if kind == "result"
                    else self.tasks.status(task_id))
        if kind == "result" and resp.get("state") in ("completed", "failed", "cancelled"):
            ref = self.audit.store_result(task_id, resp)
            self.tasks._set(task_id, state=resp["state"], result_ref=ref,
                            completed_at=resp.get("completed_at"))
        return {"member_id": member_id, **resp}

    def is_member_task(self, peer_identity: str) -> bool:
        """True if a delegated_task's peer_identity is one of our risk members
        (iN2N) rather than an eN2N BGP peer."""
        return bool(self.risk.get_member(peer_identity))

    # ---- Member side: dial the Border + run delegated work ------------

    async def dial_border(self, host: str, port: int, enrollment_token: str = "",
                          ssl_context=None):
        """Member side: connect outbound to the Border, complete the handshake
        (enroll if we have a token, else hello with pinned-key proof), and stay
        available for delegated tasks. No inbound port is opened (FR-006/SC-011)."""
        from .internal_channel import InternalChannel, read_border_preamble
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ssl_context), timeout=30.0)
        nonce = await read_border_preamble(reader)
        if nonce is None:
            writer.close()
            raise RuntimeError("bad iN2N preamble from Border")
        ch = InternalChannel(reader, writer, local_identity=self.local_identity,
                             member_id=self.risk.self_member_id(), is_border_side=False,
                             handlers=self._in2n_member_handlers, nonce=nonce)
        await ch.start()
        cert_pem = self.risk.self_cert_pem()
        signature = self.risk.self_sign(nonce).hex()
        member_id = self.risk.self_member_id()
        if enrollment_token:
            resp = await ch.call("in2n/enroll", {
                "token": enrollment_token, "member_id": member_id,
                "cert_pem": cert_pem, "signature": signature,
                "scope": list(self.member_scope) or None,
                "runtime_kind": os.environ.get("N2N_MEMBER_RUNTIME", "process"),
                "transport_binding": "distributed"}, timeout=30.0)
        else:
            resp = await ch.call("in2n/hello", {
                "member_id": member_id,
                "key_fingerprint": self.risk.fingerprint_of(cert_pem),
                "signature": signature}, timeout=30.0)
        ch.trusted = True   # we pinned the Border endpoint at provisioning
        self.border_channel = ch
        logger.info("iN2N: dialed Border %s:%s as %s (%s)", host, port, member_id, resp)
        return resp

    async def _in2n_member_submit(self, channel, params):
        """Member side: the Border delegates a task. Enforce scope (FR-023),
        then run it as a background task reusing the 053 TaskManager + gateway
        executor. Auth is implicit within the risk (no grants), but scope is not."""
        from .internal_channel import _ERR_NOT_TRUSTED
        from .channel import RpcError
        from ..constants import IN2N_ERR_OUT_OF_SCOPE
        skill = params.get("skill", "")
        input_text = params.get("input_text", "")
        border = channel.member_id or "border"
        self.member_last_activity = time.time()   # reset idle-exit timer (cold/on-demand)
        if self.member_scope and skill not in self.member_scope:
            self.audit.record(direction="inbound", peer_identity=border,
                              target_type="skill", target_name=skill,
                              decision="out_of_scope", outcome="denied", channel_kind="in2n")
            raise RpcError(IN2N_ERR_OUT_OF_SCOPE,
                           f"'{skill}' is outside this member's scope")
        tm = self.tasks
        task_id = tm.create(direction="inbound", peer_identity=border,
                            target_type="skill", target_name=skill, input_text=input_text)

        async def worker(progress):
            progress("running skill")
            # A MEMBER executes in OpenClaw EMBEDDED mode with its OWN provider/
            # model (N2N_MEMBER_MODEL) over only its scoped MCPs — no gateway
            # (feature 056). Falls back to the gateway path if not a member.
            from .gateway import run_agent_turn
            member_model = os.environ.get("N2N_MEMBER_MODEL")
            if self.risk.role() == "member":
                prompt = (f"Execute the '{skill}' skill for the following request "
                          f"and return only the result:\n\n{input_text}")
                output, tokens = await run_agent_turn(
                    prompt, session_key=f"in2n-{skill}",
                    timeout_s=self.invoker.skill_timeout, local=True, model=member_model)
            else:
                output, tokens = await self.invoker._exec_skill_gateway(skill, input_text)
            self.audit.record(direction="inbound", peer_identity=border,
                              target_type="skill", target_name=skill, request_id=task_id,
                              decision="in_scope", outcome="success", channel_kind="in2n")
            return output, tokens

        tm.run(task_id, worker)
        return {"task_id": task_id, "state": "submitted"}
