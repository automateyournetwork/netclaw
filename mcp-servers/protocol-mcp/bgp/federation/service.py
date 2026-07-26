"""FederationService — wires manager + channel + inventory into the daemon.

Owns the set of live NCFED channels, registers the lifecycle (n2n/hello,
n2n/consent_state) and capability (n2n/inventory, n2n/inventory_get)
wire methods, and drives outbound channel establishment when both consents are
present (lower-AS initiates). Severing is local-only — no wire method (§13).
"""

import asyncio
import json
import logging
import os
import secrets
import time
from typing import Dict, Optional

from ..constants import NCFED_MAGIC, IN2N_NONCE_SIZE
from .manager import FederationManager, PeerState, peer_identity
from .channel import (
    FederationChannel, read_handshake, build_handshake, RpcError, ERR_NOT_FEDERATED,
)
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

        # ── feature 060: secured channels. Default OFF so this code changes
        # nothing until an operator opts in; 'on' upgrades every eN2N channel to
        # TLS + channel-bound auth; 'enforce' additionally refuses cleartext.
        _mode = os.environ.get("N2N_CERT_MODE", "off").strip().lower()
        self.cert_mode = _mode in ("on", "enforce", "true", "1", "yes")
        self.cert_enforce = _mode == "enforce"
        self._host_cred: Optional[tuple] = None   # (cert_pem, key_pem), lazily created
        # Feature 063 (P4): PQ posture. 'opportunistic' offers the hybrid where the
        # stack supports it and accepts classical fallback; 'require' hard-refuses a
        # classical channel — but on a stack that CANNOT do PQ at all, 'require'
        # fails fast at startup rather than silently refusing every peer (FR-011).
        from . import tls as _tls
        self.pq_mode = os.environ.get("N2N_PQ_MODE", "opportunistic").strip().lower()
        self.pq_available = _tls.pq_available()
        if self.pq_mode == "require" and not self.pq_available:
            raise RuntimeError(
                "N2N_PQ_MODE=require but post-quantum key exchange is unavailable on "
                "this crypto stack (needs OpenSSL >= 3.5 / Python >= 3.15 for "
                "X25519MLKEM768 + negotiated-group readout). Use 'opportunistic' or "
                "upgrade the stack.")

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
        from .replication import ReplicationManager
        self.replication = ReplicationManager(self)
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
            "n2n/inventory": self._on_inventory,
            "n2n/inventory_get": self._on_inventory_get,
            "n2n/tools/call": self.invoker.handle_tools_call,
            "n2n/tasks/submit": self.invoker.handle_task_submit,
            "n2n/tasks/status": self.invoker.handle_task_status,
            "n2n/tasks/result": self.invoker.handle_task_result,
            "n2n/tasks/cancel": self.invoker.handle_task_cancel,
            "n2n/knowledge/query": self.invoker.handle_knowledge_query,
            "n2n/knowledge/replicate_manifest": self.invoker.handle_replicate_manifest,
            "n2n/knowledge/replicate_batch": self.invoker.handle_replicate_batch,
            "n2n/chat/open": self.chat.handle_chat_open,
            "n2n/chat/message": self.chat.handle_chat_message,
            "n2n/heartbeat": self._on_heartbeat,
        }

        # ── iN2N (feature 056): internal federation within one risk ──────
        from .risk import RiskManager
        from .router import RiskRouter
        self.risk = RiskManager(self.manager)
        self.router = RiskRouter(self.risk)
        self.member_channels: Dict[str, object] = {}   # border side: member_id -> InternalChannel
        # feature 066: border side, node_type='edge' members (phones) — a
        # separate registry from member_channels because edge nodes never
        # carry agent-member capabilities (no BGP/eN2N/inventory dispatch,
        # FR-012) and are addressed by push_to_edge(), not delegate_to_member().
        self.edge_channels: Dict[str, object] = {}
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
        # feature 066: Border-side handlers for edge (phone) connections. Only
        # the handshake + built-in health methods (FR-012) — never BGP/eN2N/
        # inventory. n2n/edge/message has no server-side handler because it is
        # Border-initiated only (push_to_edge calls it; nothing calls it on us).
        self._edge_border_handlers = {
            "in2n/enroll": self._edge_on_enroll,
            "in2n/hello": self._edge_on_hello,
            "n2n/edge/register_push": self._edge_on_register_push,
            # feature 067: phone-to-Border command channel. n2n/tasks/* are
            # the SAME handler functions the existing iN2N member-facing
            # surface already uses (they're generic over channel.peer_identity,
            # which EdgeChannel already has post-auth) -- reused as-is, not
            # reimplemented (research D4).
            "n2n/edge/ask": self._edge_on_ask,
            "n2n/tasks/status": self.invoker.handle_task_status,
            "n2n/tasks/result": self.invoker.handle_task_result,
            "n2n/tasks/cancel": self.invoker.handle_task_cancel,
            # feature 068: biometric-gated approvals + capability advertisement.
            "n2n/edge/register_capabilities": self._edge_on_register_capabilities,
            "n2n/edge/approval_resolve": self._edge_on_approval_resolve,
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
        # feature 068 (US1/FR-001): the first real delivery mechanism behind
        # this hook — push to every connected edge node via the EXISTING
        # push_to_edge() (066/US2), including its existing disconnected-
        # device FCM/APNs fallback (066/US3). No "reason" field exists in
        # the current approval_request/remote_invocation_record schema (this
        # hook has only ever carried invocation_id/peer/target_type/
        # target_name, confirmed by grepping every call site) -- not
        # fabricated here.
        if not self.edge_channels:
            return
        row = self.manager._conn.execute(
            "SELECT id FROM approval_request WHERE invocation_id=? AND status='pending' "
            "ORDER BY id DESC LIMIT 1", (invocation_id,)).fetchone()
        if not row:
            return
        approval_id = row["id"]
        risk_name = (self.risk.get_risk() or {}).get("risk_name")
        payload = {
            "content_type": "approval",
            "approval_id": approval_id,
            "target_type": target_type,
            "target_name": target_name,
            "requesting_agent": peer,
            "risk_name": risk_name,
            "pushed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        for member_id in list(self.edge_channels.keys()):
            asyncio.create_task(self._push_approval_best_effort(member_id, payload))

    async def _push_approval_best_effort(self, member_id, payload):
        try:
            await self.push_to_edge(member_id, payload)
        except Exception as e:
            logger.warning("approval push to edge %s failed: %s", member_id, e)

    def notify_key_change(self, ident):
        """Surface an NCFED key change for a federated peer (possible
        impersonation) to the operator via the same approval_notifier hook the
        iN2N quarantine path uses. Best-effort; the new key is never auto-trusted."""
        logger.warning("eN2N ALERT: pinned key changed for federated peer %s — rejected", ident)
        if self.approval_notifier:
            try:
                self.approval_notifier(None, ident, "key_change", ident)
            except Exception:
                pass

    async def _on_hello(self, channel, params):
        # eN2N possession auth (baseline — reconciled from Josh/TunnelMind's report,
        # closing CWE-290 by default; reuses risk.py possession primitives). Only
        # the ACCEPTOR issued a nonce, so only it challenges.
        #   cert present ⇒ tier-1 "possession": must prove possession + match the
        #     TOFU pin, else hard-reject + close (active forgery / key change).
        #   cert absent  ⇒ tier-0 "self-asserted": admitted (federated for presence
        #     + inventory) but execution/impersonation surfaces stay default-denied
        #     (negotiate.allows) — UNLESS cert_enforce, which requires possession.
        # Strangers are already closed in accept_channel (FR-003).
        if not channel.is_initiator and not channel.authenticated:
            cert_pem = params.get("cert_pem", "")
            signature = bytes.fromhex(params.get("signature", "") or "")
            if cert_pem:
                # On a TLS channel, bind the proof to this session via the
                # tls-server-end-point value (hash of OUR certificate, which the
                # dialer also signed over); empty on cleartext (RFC 5929).
                binding = self._channel_binding_own()
                if not self.risk.verify_possession(cert_pem, channel.nonce, signature, binding):
                    logger.warning("n2n.auth.failed: possession proof failed for claimed %s",
                                   channel.peer_identity)
                    channel._auth_failed = True
                    raise RpcError(ERR_NOT_FEDERATED, "possession proof failed")
                # TOFU pin: bind this identity to its cert on first contact; a later
                # key change is possible impersonation — reject + alert, NEVER
                # silently re-pin.
                if self.risk.check_peer_pin(channel.peer_identity, cert_pem) == "mismatch":
                    logger.warning("NCFED key changed for %s", channel.peer_identity)
                    self.notify_key_change(channel.peer_identity)
                    channel._auth_failed = True
                    raise RpcError(ERR_NOT_FEDERATED, "pinned key mismatch")
                channel.attestation = "possession"
                channel.cert_pem = cert_pem
                # Record the pin in the peer row too (HUD/posture visibility);
                # check_peer_pin above holds the authoritative file pin.
                from . import certs
                self.manager.set_peer_pin(channel.peer_identity,
                                          certs.key_fingerprint(cert_pem))
                self.manager.set_peer_trust(channel.peer_identity, "pinned",
                                            verify_state="verified")
            elif self.cert_enforce:
                # Mandatory certs: a keyless peer cannot federate in enforce mode.
                logger.warning("cert enforce: refusing keyless (tier-0) hello from %s",
                               channel.peer_identity)
                channel._auth_failed = True
                raise RpcError(ERR_NOT_FEDERATED,
                               "peer requires certificate-secured federation — run "
                               "scripts/patch-claw-certs.sh")
            channel.authenticated = True
            if not self._register_channel(channel.peer_identity, channel):
                channel._auth_failed = True
                raise RpcError(ERR_NOT_FEDERATED,
                               "identity already held by a possession-proven peer")
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
        deregisters itself (US2) — no zombie channels lingering in the registry.

        Eviction guard: refuse (return False) when a possession-proven channel
        already holds this identity and the incoming one is an inbound, tier-0
        (self-asserted) session — a keyless peer must not knock the pinned peer
        offline. Our own outbound re-dials (is_initiator) always replace."""
        existing = self.channels.get(ident)
        if (existing is not None and getattr(existing, "attestation", "") == "possession"
                and not ch.is_initiator and getattr(ch, "attestation", "") != "possession"):
            logger.warning("Refusing tier-0 inbound channel for %s — possession-proven peer holds it", ident)
            return False
        def _deregister(closed_ch):
            if self.channels.get(ident) is closed_ch:
                self.channels.pop(ident, None)
                logger.info("Channel to %s closed — deregistered", ident)
        ch.on_close = _deregister
        self.channels[ident] = ch
        return True

    async def _on_endpoint_update(self, channel, params):
        """US3: a federated peer announced a new public endpoint over its
        authenticated channel. Trust it only for THIS channel's identity
        (FR-012), update the record, and let the supervisor re-dial (FR-011)."""
        from .negotiate import allows
        endpoint = params.get("endpoint", "")
        ident = channel.peer_identity  # bound to the authenticated session, not attacker-supplied
        if not allows(getattr(channel, "attestation", "self-asserted"), "endpoint_update"):
            logger.info("tier-0 peer %s denied endpoint_update — possession proof required", ident)
            return {"accepted": False}
        if not self.manager.is_federated(ident) or ":" not in endpoint:
            return {"accepted": False}
        host, _, port = endpoint.rpartition(":")
        try:
            port = int(port)
        except ValueError:
            return {"accepted": False}
        # upsert_peer bumps endpoint_updated_at whenever an endpoint is written
        # (feature 063), so a single call persists both the address and freshness.
        self.manager.upsert_peer(channel.peer_as, channel.peer_router_id,
                                 endpoint_host=host, endpoint_port=port)
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

    # ---- feature 060: secured-channel credential + upgrade ------------

    async def _on_heartbeat(self, channel, params):
        """FR-024: record the peer's reported credential health so the HUD/posture
        never show it staler than one heartbeat interval (SC-011)."""
        cred = params.get("cred") or {}
        fp = cred.get("fp")
        if fp:
            self.manager.set_peer_cred_health(
                channel.peer_identity, fp, cred.get("not_after"), cred.get("renew_state"))
        return None  # notification — no reply

    def _channel_binding(self, writer) -> bytes:
        """Dialer side: the tls-server-end-point binding (SHA-256 of the peer's
        server certificate) for the current channel, or b"" on cleartext. The
        dialer includes this in its possession signature (RFC 5929)."""
        if not self.cert_mode:
            return b""
        from . import tls
        sslobj = writer.get_extra_info("ssl_object")
        return (tls.binding_from_peer(sslobj) or b"") if sslobj else b""

    def _channel_binding_own(self) -> bytes:
        """Acceptor side: the same binding computed from OUR presented certificate
        (equals the dialer's _channel_binding for the same session), or b"" on
        cleartext."""
        if not self.cert_mode:
            return b""
        from . import tls
        try:
            return tls.binding_from_own_cert(self.host_credential()[0])
        except Exception:
            return b""

    def _cred_status(self) -> Optional[dict]:
        """This claw's credential health to advertise on heartbeats (FR-024)."""
        if not self.cert_mode:
            return None
        from . import certs
        cert_pem, _ = self.host_credential()
        try:
            na = certs.cert_not_after(cert_pem).isoformat()
        except Exception:
            na = None
        return {"fp": certs.key_fingerprint(cert_pem), "not_after": na,
                "renew_state": "ok"}

    def host_credential(self) -> tuple:
        """The credential this claw presents on secured channels. If a domain is
        configured and an ACME certificate exists, present that (domain-verified
        peers validate its WebPKI chain; pinned peers pin its key). Otherwise the
        pinned-model self-signed credential under keys/host/, created once."""
        from . import certs
        # Prefer the domain-verified (ACME) credential when present.
        domain = os.environ.get("N2N_CLAW_DOMAIN")
        if domain:
            kd = certs.keys_dir(str(self.manager.base_dir))
            acme_crt = kd / "acme" / "certificates" / f"{domain}.crt"
            acme_key = kd / "acme" / "certificates" / f"{domain}.key"
            if acme_crt.exists() and acme_key.exists():
                return acme_crt.read_text(), acme_key.read_text()
        if self._host_cred is None:
            kd = certs.keys_dir(str(self.manager.base_dir))
            crt, key = kd / "host" / "host.crt", kd / "host" / "host.key"
            if crt.exists() and key.exists():
                self._host_cred = (crt.read_text(), key.read_text())
            else:
                cert_pem, key_pem = certs.create_self_signed(self.local_identity)
                crt.write_text(cert_pem)
                certs._write_secret(key, key_pem)
                self._host_cred = (cert_pem, key_pem)
        return self._host_cred

    async def _secure_dial(self, reader, writer, ident: str):
        """Dialer side, cert_mode ENCRYPTION layer (feature 060): upgrade the
        connection to TLS and verify the LISTENER (domain-verified WebPKI chain +
        SAN, or pinned fingerprint / TOFU). The dialer authenticates ITSELF to the
        listener separately, over n2n/hello (baseline possession proof). Returns
        the upgraded (reader, writer) or None on refusal."""
        from . import tls, certs
        peer = self.manager.get_peer(ident) or {}
        trust = peer.get("trust_model") or "pinned"
        if trust == "legacy":
            trust = "pinned"  # first secured contact with a known peer → pin it
        claw_domain = peer.get("claw_domain")
        cctx, server_hostname = tls.client_context(trust, claw_domain=claw_domain)
        reader, writer = await tls.upgrade_to_tls(
            reader, writer, cctx, server_side=False, server_hostname=server_hostname)
        sslobj = writer.get_extra_info("ssl_object")
        if trust == "domain-verified":
            names = certs.san_names(tls.peer_leaf_pem(sslobj) or "")
            if claw_domain and claw_domain not in names:
                logger.warning("Refusing %s: cert SAN %s != claw_domain %s",
                               ident, names, claw_domain)
                self._cert_refuse(ident, f"SAN {names} != {claw_domain}")
                return None
        else:  # pinned — TOFU on first contact, else the listener key must match
            pin = tls.leaf_key_fingerprint(sslobj)
            stored = peer.get("pinned_fp")
            if stored and pin not in (stored, peer.get("pinned_fp_next")):
                logger.warning("Refusing %s: listener pinned key changed", ident)
                self._cert_refuse(ident, "listener pinned key changed — re-verify out of band")
                return None
            if not stored:
                self.manager.set_peer_pin(ident, pin)  # TOFU-pin the listener
        if not self._pq_ok(sslobj, ident):
            return None
        self.manager.set_peer_trust(ident, trust, verify_state="verified")
        return reader, writer

    async def _secure_accept(self, reader, writer, ident: str):
        """Listener side, cert_mode ENCRYPTION layer: present our credential and
        upgrade to TLS. The dialer verifies OUR cert during its handshake; we
        authenticate the DIALER separately via its n2n/hello possession proof.
        Returns upgraded (reader, writer) or None on failure."""
        from . import tls
        cert_pem, key_pem = self.host_credential()
        reader, writer = await tls.upgrade_to_tls(
            reader, writer, tls.server_context(cert_pem, key_pem), server_side=True)
        sslobj = writer.get_extra_info("ssl_object")
        if not self._pq_ok(sslobj, ident):
            return None
        return reader, writer

    def _pq_ok(self, sslobj, ident: str) -> bool:
        """Feature 063 (P4/FR-011): in 'require' mode on a PQ-capable stack, refuse
        a channel that negotiated a classical (non-PQ) group. On a stack that can't
        do PQ, 'require' already failed fast at startup, so this is a no-op there and
        opportunistic mode always accepts. None (unreadable group) is not PQ."""
        if self.pq_mode != "require" or not self.pq_available:
            return True
        from . import tls
        group = tls.channel_kex(sslobj).get("kex_group")
        if tls.is_pq_group(group):
            return True
        logger.warning("Refusing %s: N2N_PQ_MODE=require but negotiated classical group %r",
                       ident, group)
        self._cert_refuse(ident, f"PQ required but negotiated classical group {group!r}")
        return False

    def _cert_refuse(self, ident: str, reason: str):
        self.manager.set_peer_trust(ident, (self.manager.get_peer(ident) or {}).get(
            "trust_model") or "pinned", verify_state="refused-pending-patch")
        try:
            self.audit.record_cert_event(kind="verify-refused", subject_identity=ident,
                                          detail=reason)
        except Exception:
            pass

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
        # FR-003 (reconciled): admit only a peer we have locally consented to
        # (every federated / consent-pending-local peer has). A true stranger — no
        # local_grant — is learned as presence and then closed WITHOUT a nonce/
        # hello: no channel, not even tier-0. This keeps an un-consented forger off
        # the wire entirely.
        self.manager.upsert_peer(peer_as, router_id)
        if not self.manager._has_consent(ident, "local_grant"):
            logger.info("NCFED from %s but no local consent — closing (FR-003)", ident)
            try:
                writer.close()
            except Exception:
                pass
            return
        # Send our handshake reply.
        writer.write(build_handshake(self.local_as, self.router_id))
        await writer.drain()
        # cert_mode ENCRYPTION layer (feature 060): upgrade to TLS before anything
        # sensitive (the possession nonce + hello then ride inside TLS).
        if self.cert_mode:
            try:
                upgraded = await self._secure_accept(reader, writer, ident)
            except Exception as e:
                logger.warning("Secure accept from %s failed: %s", ident, e)
                upgraded = None
            if upgraded is None:
                try:
                    writer.close()
                except Exception:
                    pass
                return
            reader, writer = upgraded
        # Possession challenge (baseline auth): the dialer must sign this nonce
        # with the key for the cert it presents in n2n/hello (reuses risk.py).
        nonce = secrets.token_bytes(IN2N_NONCE_SIZE)
        writer.write(nonce)
        await writer.drain()
        ch = FederationChannel(reader, writer, local_identity=self.local_identity,
                               peer_as=peer_as, peer_router_id=router_id,
                               manager=self.manager, is_initiator=False, handlers=self.handlers)
        ch.nonce = nonce
        ch.cred_status = self._cred_status()
        await ch.start()
        # The initiator sends n2n/hello carrying the possession proof; _on_hello
        # verifies it, registers the channel (tier gate), and advertises.
        logger.info("Accepted NCFED channel from %s (awaiting possession proof)", ident)

    # ---- outbound channel (lower-AS initiates) ------------------------

    async def open_channel(self, peer_as: int, router_id: str, host: str, port: int):
        if not self._en2n_allowed():
            logger.info("iN2N Member role — not opening outbound eN2N channel (FR-014)")
            return
        ident = peer_identity(peer_as, router_id)
        from ..constants import ncfed_initiates
        if not ncfed_initiates(self.local_as, self.router_id, peer_as, router_id):
            logger.debug("Not initiating to %s — higher (AS, router-id) tuple waits", ident)
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
            # cert_mode ENCRYPTION layer (feature 060): upgrade to TLS + verify
            # the listener (domain/pin) before anything sensitive.
            if self.cert_mode:
                upgraded = await self._secure_dial(reader, writer, ident)
                if upgraded is None:
                    writer.close()
                    return
                reader, writer = upgraded
            # Read the acceptor's possession-challenge nonce (baseline auth).
            nonce = await asyncio.wait_for(reader.readexactly(IN2N_NONCE_SIZE), timeout=10.0)
            ch = FederationChannel(reader, writer, local_identity=self.local_identity,
                                   peer_as=peer_as, peer_router_id=router_id,
                                   manager=self.manager, is_initiator=True, handlers=self.handlers)
            ch.cred_status = self._cred_status()
            sslobj = writer.get_extra_info("ssl_object")
            if self.cert_mode and sslobj is not None:
                # Dialer-side tier: the TLS handshake proved the LISTENER possesses
                # the key for the certificate _secure_dial just verified (pin /
                # domain SAN), which is the same possession property _on_hello
                # establishes for a dialer. Without this, attestation is only ever
                # set on the acceptor side, so a listener's endpoint_update /
                # execution surface is tier-0 forever on every channel it did not
                # itself dial (observed live 2026-07-18 against both mesh peers,
                # which silently disabled endpoint_reannounce on dialed channels).
                from . import tls as _tls
                ch.attestation = "possession"
                ch.cert_pem = _tls.peer_leaf_pem(sslobj)
            self._register_channel(ident, ch)
            await ch.start()
            from .negotiate import local_descriptor, normalize
            # Prove possession of our key over the acceptor's nonce (reuses risk.py),
            # bound to this TLS session by the tls-server-end-point value (the hash
            # of the listener's certificate we just verified) when encrypted — so
            # the proof cannot be relayed to a different session (RFC 5929).
            binding = self._channel_binding(writer)
            resp = await ch.call("n2n/hello", {"identity": self.local_identity,
                                               "display_name": self.display_name,
                                               "versions": ["1.0"],
                                               "cert_pem": self.risk.self_cert_pem(),
                                               "signature": self.risk.self_sign(nonce, binding).hex(),
                                               "capabilities": local_descriptor()})
            # A well-behaved peer returns a dict; guard against a peer that returns
            # a bare string or other shape so one odd hello reply can't abort the
            # whole dial (normalize() already tolerates a non-dict descriptor).
            if not isinstance(resp, dict):
                logger.warning("Peer %s returned non-dict n2n/hello result (%s) — "
                               "treating as empty", ident, type(resp).__name__)
                resp = {}
            ch.display_name = resp.get("display_name")
            self.peer_caps[ident] = normalize(resp.get("capabilities"))  # US4
            self.manager.remote_consent(peer_as, router_id)
            if self.manager._recompute_state(ident) == PeerState.FEDERATED:
                await self._advertise_to(ch)
            # Feature 063 (P1/FR-001): persist the endpoint we just reached ONLY on
            # a successful, authenticated dial — never on the failure path below —
            # so the reconnect supervisor re-dials this current address instead of a
            # stale one (the live bug the packet capture surfaced). A bad dial that
            # raises before here leaves the prior good address intact.
            self.manager.upsert_peer(peer_as, router_id,
                                     endpoint_host=host, endpoint_port=port)
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
            # An edge (phone) member's live connection lives in edge_channels,
            # never member_channels (agent members only) -- checking only the
            # latter reported every connected phone as down, and since its DB
            # row is `active` that also tripped member_fault, mislabelling the
            # WHOLE risk fault_class="member" when nothing was wrong. Same bug
            # class fixed in ec7acdd for GET /n2n/members and
            # /n2n/members/health; this third call site was missed.
            live = mid in self.member_channels or mid in self.edge_channels
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
        # Severing is a local operator action (kill switch): revoke our grant and
        # drop the channel. There is deliberately NO peer-to-peer sever message
        # (NCFED -00 §13) — a remote sever notification would let a peer that
        # reached federated state revoke our grant, so the peer learns of the
        # sever only by the channel closing and being refused on re-dial.
        ok = self.manager.sever(ident)
        ch = self.channels.pop(ident, None)
        if ch:
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
            # Map the risk-layer sentinel to its wire code: a member_id already
            # pinned to a different key is MEMBER_ID_TAKEN (-32022), distinct
            # from a spent/expired token (-32021). (NCFED -00 §9.3)
            from ..constants import (IN2N_ERR_ENROLL_TOKEN_INVALID,
                                     IN2N_ERR_MEMBER_ID_TAKEN)
            msg = str(e)
            if "TRUSTED" in msg:
                code = _ERR_NOT_TRUSTED
            elif "MEMBER_ID_TAKEN" in msg:
                code = IN2N_ERR_MEMBER_ID_TAKEN
            else:
                code = IN2N_ERR_ENROLL_TOKEN_INVALID
            raise RpcError(code, msg)
        channel.member_id = member_id
        channel.peer_identity = member_id
        channel.trusted = True
        self.risk.verify_member(member_id, self.risk.fingerprint_of(cert_pem))
        self._register_member_channel(member_id, channel)
        self.audit.record(direction="inbound", peer_identity=member_id,
                          target_type="enroll", target_name=member_id,
                          decision="enrolled", outcome="success", channel_kind="in2n")
        logger.info("iN2N member %s enrolled + active", member_id)
        # US2: bootstrap the risk CA trust anchor to the member at enrollment, and
        # (if it challenged us) attest we are the legitimate hub.
        anchor = self.risk.risk_ca_pem() or (self.risk.ensure_risk_ca()[0])
        res = dict(res)
        res["risk_ca"] = anchor
        mnonce = params.get("member_nonce")
        if mnonce:
            attest = self.risk.attest_hub(bytes.fromhex(mnonce))
            if attest:
                res["hub_attestation"] = attest
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
            # FR-022: attribute the failure to its source so a foreign host cannot
            # unpin a healthy member by spraying failing auths.
            src = self._channel_source(channel)
            est = (self.member_channels.get(member_id) and
                   self._channel_source(self.member_channels[member_id]))
            quarantined = self.risk.record_auth_failure(
                member_id, source=src, established_source=est)
            if quarantined:
                self.notify_member_quarantine(member_id)
            raise RpcError(_ERR_NOT_TRUSTED, "pinned-key auth failed")
        channel.member_id = member_id
        channel.peer_identity = member_id
        channel.trusted = True
        self._register_member_channel(member_id, channel)
        result = {"risk": self.risk.get_risk().get("risk_name"), "trusted": True,
                  "member_state": "active"}
        # US2 hub attestation: if the member challenged us with a nonce, prove we
        # are the legitimate hub (CA-signed hub cert + signature over the nonce).
        mnonce = params.get("member_nonce")
        if mnonce:
            attest = self.risk.attest_hub(bytes.fromhex(mnonce))
            if attest:
                result["hub_attestation"] = attest
        return result

    @staticmethod
    def _channel_source(channel) -> Optional[str]:
        """Best-effort remote address of an internal channel, for per-source
        auth-failure accounting (FR-022)."""
        try:
            peer = channel.writer.get_extra_info("peername")
            return f"{peer[0]}:{peer[1]}" if peer else None
        except Exception:
            return None

    async def _in2n_on_member_inventory(self, channel, params):
        """A member advertises its (scoped) capabilities. We already know its
        scope from enrollment; record freshness and ack (no secrets, reused guard)."""
        if channel.member_id:
            self.risk.update_health(channel.member_id, inventory_at=time.time())
        return {"accepted": True}

    # ---- feature 066: edge (phone) connections -------------------------
    # WebSocket transport instead of raw TCP (research D2); same trust model
    # (pinned-key possession over a Border-issued nonce) and same wire method
    # names (in2n/enroll, in2n/hello) as agent-member iN2N enrollment (contract
    # §2) — only consume_token()'s new node_type="edge" argument (T006) and a
    # separate registry (self.edge_channels, T008) distinguish it.

    # ---- edge (phone) agent-turn budget --------------------------------

    def _edge_ask_timeout(self) -> int:
        """Wall-clock budget for one phone request's agent turn.

        MUST be >= the member `skill_timeout` this turn may delegate into,
        otherwise the parent dies while its own child is still running (see
        _edge_on_ask). Defaults to the member budget plus headroom for the
        Border's own reasoning either side of the delegation.
        """
        override = os.environ.get("N2N_EDGE_ASK_TIMEOUT_S")
        if override:
            try:
                return max(60, int(override))
            except ValueError:
                logger.warning("N2N_EDGE_ASK_TIMEOUT_S=%r is not an int — ignoring", override)
        member_budget = getattr(self.invoker, "skill_timeout", 600)
        return int(member_budget) + self._edge_ask_stall_extension()

    def _edge_ask_stall_extension(self) -> int:
        """Extra seconds granted when a turn is still alive at the stall
        checkpoint. Also the headroom added on top of the member budget."""
        try:
            return max(30, int(os.environ.get("N2N_EDGE_ASK_STALL_EXTENSION_S", "180")))
        except ValueError:
            return 180

    async def _edge_notify_progress(self, member_id: str, task_id: str, text: str):
        """Best-effort progress ping to a phone mid-turn. Never raises: a
        disconnected phone just doesn't get it, and the turn continues."""
        ch = self.edge_channels.get(member_id)
        if not ch:
            return
        try:
            await ch.notify("n2n/edge/task_progress",
                            {"task_id": task_id, "detail": text})
        except Exception as e:
            logger.debug("edge progress notify to %s failed: %s", member_id, e)

    def _register_edge_channel(self, member_id, ch):
        """Track an edge node's channel; deregister on close and start its
        Border-driven heartbeat loop (T011) — the BASE_FLOOR-equivalent
        health-monitoring guarantee for a member that never runs a skill
        (D5/T010)."""
        def _deregister(closed_ch):
            if self.edge_channels.get(member_id) is closed_ch:
                self.edge_channels.pop(member_id, None)
                self.risk.mark_unreachable(member_id)
                logger.info("Edge node %s channel closed — deregistered", member_id)
        ch.on_close = _deregister
        self.edge_channels[member_id] = ch
        asyncio.create_task(self._edge_heartbeat_loop(member_id, ch))

    async def _edge_heartbeat_once(self, member_id: str, ch) -> bool:
        """One heartbeat check (contract §4): call n2n/edge/heartbeat on the
        connected phone and record liveness in member.health, exactly as
        member_heartbeat does for agent members. This is the entire
        BASE_FLOOR-equivalent guarantee (D5/T010) for a node_type='edge'
        member with zero skills delivered — extracted from the loop below so
        it's directly callable/testable without waiting on real timers."""
        try:
            await ch.call("n2n/edge/heartbeat", {})
            self.risk.update_health(member_id, last_heartbeat=time.time())
            return True
        except Exception as e:
            logger.warning("Edge node %s: heartbeat failed (%s)", member_id, e)
            return False

    async def _edge_heartbeat_loop(self, member_id, ch):
        """Border-initiated heartbeat (contract §4): periodically run
        _edge_heartbeat_once; after NCFED_HEARTBEAT_MISS_LIMIT consecutive
        misses, closes the channel (which deregisters it and marks the
        member unreachable, US3/SC-006). Reuses the same interval/miss-limit
        as eN2N/iN2N channel liveness (NCFED_HEARTBEAT_INTERVAL/_MISS_LIMIT)
        so there is one heartbeat-miss window across the whole daemon, not a
        second constant to keep in sync."""
        from ..constants import NCFED_HEARTBEAT_INTERVAL, NCFED_HEARTBEAT_MISS_LIMIT
        misses = 0
        while self.edge_channels.get(member_id) is ch and not ch._closed:
            await asyncio.sleep(NCFED_HEARTBEAT_INTERVAL)
            if self.edge_channels.get(member_id) is not ch or ch._closed:
                break
            if await self._edge_heartbeat_once(member_id, ch):
                misses = 0
            else:
                misses += 1
                if misses >= NCFED_HEARTBEAT_MISS_LIMIT:
                    await ch.close()
                    break

    async def push_to_edge(self, member_id: str, content: dict, timeout: float = 30.0) -> dict:
        """Explicitly push content to a connected edge node (US2/FR-008),
        mirroring delegate_to_member()'s existing call-out shape (D8). Called
        ONLY from an explicit operator/agent action (n2n_notify_phone → the
        daemon's POST /n2n/edge/push route) — there is no other code path
        that calls this, so no ordinary channel traffic is ever mirrored to
        a phone. Raises ValueError if the edge node is not currently
        connected; the caller (the HTTP route) is responsible for the
        platform push-notification fallback (FR-011, US3)."""
        ch = self.edge_channels.get(member_id)
        if not ch:
            raise ValueError(f"edge node {member_id} not connected")
        result = await ch.call("n2n/edge/message", content, timeout=timeout)
        # Audit every explicit push (Constitution IV) so the HUD/operator can
        # see recent phone deliveries via the existing /n2n/audit query,
        # exactly like every other iN2N action.
        self.audit.record(direction="outbound", peer_identity=member_id,
                          target_type="edge_push", target_name=content.get("content_type"),
                          decision="pushed", outcome="success", channel_kind="in2n")
        return result

    async def edge_self_status(self, member_id: str, timeout: float = 30.0) -> dict:
        """On-demand self-status (contract §4) — the edge-node analogue of
        member_report_audit, scoped to what's meaningful for a device rather
        than a process."""
        ch = self.edge_channels.get(member_id)
        if not ch:
            raise ValueError(f"edge node {member_id} not connected")
        status = await ch.call("n2n/edge/self_status", {}, timeout=timeout)
        self.risk.update_health(member_id, self_status=status, self_status_at=time.time())
        return status

    async def accept_edge_ws(self, ws):
        """Border side: a phone dialed our edge WS listener. Challenge it with
        a nonce (the WS-transport equivalent of send_border_preamble's raw
        IN2N_MAGIC+nonce for agent members — WS has no bytes-before-the-
        protocol channel, so the challenge is the first JSON-RPC notification),
        then run an EdgeChannel; it authenticates via in2n/enroll (first time)
        or in2n/hello (pinned-key proof)."""
        from .edge import EdgeChannel
        nonce = secrets.token_bytes(IN2N_NONCE_SIZE)
        ch = EdgeChannel(ws, local_identity=self.local_identity,
                         handlers=self._edge_border_handlers)
        ch.nonce = nonce
        await ch.notify("n2n/edge/challenge", {"nonce": nonce.hex()})
        await ch.start()
        logger.info("Accepted edge WS dial-in (awaiting device auth)")
        if ch._read_task:
            await ch._read_task

    async def _edge_on_enroll(self, channel, params):
        """First-time edge enrollment: verify possession + consume the token
        with node_type='edge' (T006/D9) so the resulting member row carries no
        BASE_FLOOR skill names (D5/T010) — the edge node satisfies that
        guarantee via n2n/edge/heartbeat + n2n/edge/self_status instead."""
        from .internal_channel import _ERR_NOT_TRUSTED, _ERR_NOT_A_BORDER
        from .edge import RpcError
        if not self.risk.is_border():
            raise RpcError(_ERR_NOT_A_BORDER, "this claw is not a Border")
        token = params.get("token", "")
        member_id = params.get("member_id", "")
        cert_pem = params.get("cert_pem", "")
        signature = bytes.fromhex(params.get("signature", "") or "")
        if not self.risk.verify_possession(cert_pem, channel.nonce, signature):
            raise RpcError(_ERR_NOT_TRUSTED, "key possession proof failed")
        try:
            res = self.risk.consume_token(
                token, member_id, cert_pem,
                scope=[],
                runtime_kind=params.get("runtime_kind", "mobile"),
                display_name=params.get("display_name"),
                transport_binding="edge-ws",
                node_type="edge")
        except ValueError as e:
            from ..constants import IN2N_ERR_ENROLL_TOKEN_INVALID, IN2N_ERR_MEMBER_ID_TAKEN
            msg = str(e)
            if "TRUSTED" in msg:
                code = _ERR_NOT_TRUSTED
            elif "MEMBER_ID_TAKEN" in msg:
                code = IN2N_ERR_MEMBER_ID_TAKEN
            else:
                code = IN2N_ERR_ENROLL_TOKEN_INVALID
            raise RpcError(code, msg)
        channel.member_id = member_id
        channel.peer_identity = member_id
        channel.trusted = True
        self.risk.verify_member(member_id, self.risk.fingerprint_of(cert_pem))
        self._register_edge_channel(member_id, channel)
        self.audit.record(direction="inbound", peer_identity=member_id,
                          target_type="enroll", target_name=member_id,
                          decision="enrolled", outcome="success", channel_kind="in2n")
        logger.info("Edge node %s enrolled + active — confirm fingerprint out of band: %s",
                   member_id, res.get("enroll_fingerprint"))
        return res

    async def _edge_on_hello(self, channel, params):
        """Reconnect: authenticate against the pinned key, mirroring
        _in2n_on_hello, but additionally refuses a non-edge member_id
        (defense in depth — an agent member's credentials must never grant
        access to the phone-facing listener, even though EdgeChannel's own
        handler map already excludes every method an agent identity could
        otherwise reach, FR-012)."""
        from .internal_channel import _ERR_NOT_TRUSTED
        from .edge import RpcError
        member_id = params.get("member_id", "")
        fingerprint = params.get("key_fingerprint", "")
        signature = bytes.fromhex(params.get("signature", "") or "")
        mem = self.risk.get_member(member_id)
        if not mem or not mem.get("pinned_key") or mem.get("node_type") != "edge":
            raise RpcError(_ERR_NOT_TRUSTED, "unknown or unpinned edge node")
        ok = (mem["key_fingerprint"] == fingerprint
              and self.risk.verify_possession(mem["pinned_key"], channel.nonce, signature)
              and self.risk.verify_member(member_id, fingerprint))
        if not ok:
            src = self._edge_channel_source(channel)
            est = (self.edge_channels.get(member_id) and
                   self._edge_channel_source(self.edge_channels[member_id]))
            quarantined = self.risk.record_auth_failure(
                member_id, source=src, established_source=est)
            if quarantined:
                self.notify_member_quarantine(member_id)
            raise RpcError(_ERR_NOT_TRUSTED, "pinned-key auth failed")
        channel.member_id = member_id
        channel.peer_identity = member_id
        channel.trusted = True
        self._register_edge_channel(member_id, channel)
        return {"risk": self.risk.get_risk().get("risk_name"), "trusted": True,
               "member_state": "active"}

    @staticmethod
    def _edge_channel_source(channel) -> Optional[str]:
        """Best-effort remote address of an edge (WebSocket) channel."""
        try:
            addr = channel.ws.remote_address
            return f"{addr[0]}:{addr[1]}" if addr else None
        except Exception:
            return None

    async def _edge_on_register_push(self, channel, params):
        """An enrolled, connected edge node registers its platform push
        token (US3/T031) so push_to_edge's fallback can reach it while
        disconnected — called once after the app obtains an FCM/APNs token,
        and again whenever the platform rotates it."""
        from .edge import RpcError
        if not channel.trusted or not channel.member_id:
            raise RpcError(-32023, "edge node not authenticated")
        platform = params.get("platform", "")
        token = params.get("token", "")
        if not token:
            raise RpcError(-32602, "token required")
        try:
            self.risk.register_push(channel.member_id, platform, token)
        except ValueError as e:
            raise RpcError(-32602, str(e))
        return {"registered": True}

    async def _edge_on_register_capabilities(self, channel, params):
        """An enrolled, connected edge node declares which capture types it
        currently allows (feature 068, US3/FR-007a) — written into the SAME
        member.scope column RiskRouter already reads (research D1); a type
        omitted here is invisible to routing entirely, not merely refused."""
        from .edge import RpcError
        if not channel.trusted or not channel.member_id:
            raise RpcError(-32023, "edge node not authenticated")
        capabilities = params.get("capabilities", [])
        try:
            self.risk.set_capture_capabilities(channel.member_id, capabilities)
        except ValueError as e:
            raise RpcError(-32602, str(e))
        return {"registered": True}

    async def _edge_on_approval_resolve(self, channel, params):
        """The phone resolves a pushed approval via biometric authentication
        (feature 068, US1). Calls the EXISTING Authorizer.resolve_approval()
        unchanged (research D6) -- no biometric proof travels over the wire;
        the Border trusts the phone's report the same way it trusts any
        other edge-node action (research D7). The existing 'first resolution
        wins' behavior (resolve_approval's WHERE status='pending' clause)
        applies unmodified if the CLI/HTTP path resolved it first."""
        from .edge import RpcError
        if not channel.trusted or not channel.member_id:
            raise RpcError(-32023, "edge node not authenticated")
        approval_id = params.get("approval_id")
        action = params.get("action")
        if approval_id is None or action not in ("approve", "deny"):
            raise RpcError(-32602, "approval_id and action ('approve'|'deny') required")
        self.authz.resolve_approval(int(approval_id), action, via="biometric")
        return {"approval_id": approval_id, "resolved": True}

    async def _edge_on_ask(self, channel, params):
        """Phone asks the Border something (feature 067, US1/US2/US3): create
        a delegated_task (feature 053, TaskManager) and run a real agent turn
        in the background via gateway.run_agent_turn(), mirroring
        _in2n_member_submit's task-creation shape (not its embedded-mode
        execution — this runs in gateway mode, like chat.py's peer-chat path).

        untrusted=False (the default): a phone request is the OPERATOR'S OWN
        device (FR-002's operator-extension trust model — the same unchecked
        local access Slack/CLI/TUI already have), NOT external eN2N peer
        input. Do not copy chat.py's untrusted=True unconditionally here.

        The agent's own existing tool-using behavior (n2n_route/n2n_delegate/
        n2n_invoke) decides whether to answer directly, delegate to an
        in-risk member, or route over eN2N -- no branching logic exists here
        for that (research D3); this handler's only job is getting the
        phone's text into an agent turn and the answer back out."""
        from .edge import RpcError
        if not channel.trusted or not channel.member_id:
            raise RpcError(-32023, "edge node not authenticated")
        text = params.get("text", "")
        # feature 068 (US2/research D3): a capture may stand alone with no
        # accompanying text (FR-005) -- text is required only in the
        # ABSENCE of an attachment.
        attachment = params.get("attachment")
        if not text and not attachment:
            raise RpcError(-32602, "text or attachment required")
        member_id = channel.member_id
        task_id = self.tasks.create(direction="inbound", peer_identity=member_id,
                                    target_type="edge_ask", target_name="ask",
                                    input_text=text)

        async def worker(progress):
            from .gateway import run_agent_turn
            progress("asking the agent")
            prompt = text
            message_file = None
            if attachment:
                content_type = attachment.get("content_type", "image")
                content = attachment.get("content", "")
                if not prompt:
                    prompt = f"[Operator sent a {content_type} capture with no additional text]"
                # A capture can be large enough (up to NCFED's 16 MiB
                # aggregate bound, FR-005a) to exceed a safe CLI-argument
                # length -- fold it into a file and use --message-file
                # (research D3/gateway.py), never a raw CLI argument.
                import tempfile
                fd, message_file = tempfile.mkstemp(suffix=".txt", prefix="netclaw-capture-")
                with os.fdopen(fd, "w") as f:
                    f.write(f"{prompt}\n\n[Attached {content_type}, base64-encoded]\n{content}\n")
            try:
                # openclaw agent's --session-id/--session-key rejects a
                # value containing "/" ("Invalid session ID") -- every
                # edge member_id is risk-scoped ("risk/<label>") and always
                # contains one, so it must be sanitized here, unlike peer/
                # skill identifiers elsewhere in this file which never do.
                session_key = "n2n-edge-" + member_id.replace("/", "_")

                # A phone request routinely delegates to an in-risk member,
                # and that member's own agent turn gets `skill_timeout`
                # (default 600s). Passing no timeout here inherited
                # run_agent_turn's 300s default, so the INNER budget was twice
                # the OUTER one: a delegating request was allowed to outlive
                # the request that started it, and the phone's turn was killed
                # while its own delegation was still legitimately running.
                #
                # Observed twice on a real device (2026-07-26): identical CML
                # questions failed at exactly 300s while their `cml-node-
                # operations` delegation completed *afterwards* — the work
                # succeeded and the answer had nowhere to land. A third,
                # warm-cache run finished in 114s and looked fine, which is the
                # worst failure profile: it passes on a retry and fails cold.
                #
                # The phone's budget must therefore always be >= the member
                # budget it may have to wait on.
                timeout_s = self._edge_ask_timeout()

                def on_stall(waited_s):
                    # The turn is alive but slow. Tell the phone rather than
                    # leaving it on a silent spinner, and extend instead of
                    # dying on a blind deadline. Scheduled, not awaited:
                    # run_agent_turn calls on_stall synchronously.
                    self.tasks._set(task_id, progress="still working…")
                    asyncio.create_task(self._edge_notify_progress(
                        member_id, task_id,
                        f"Still working on this — {int(waited_s)}s so far."))
                    return self._edge_ask_stall_extension()

                output, tokens = await run_agent_turn(
                    prompt, session_key=session_key, untrusted=False,
                    message_file=message_file,
                    timeout_s=timeout_s, on_stall=on_stall)
            finally:
                if message_file:
                    try:
                        os.remove(message_file)
                    except OSError:
                        pass
            return output, tokens
        worker_task = self.tasks.run(task_id, worker)

        async def _push_result_when_done():
            # Best-effort: only reaches the phone if it's connected when the
            # task finishes (contract §2) -- otherwise it recovers via
            # n2n/tasks/status|result on reconnect.
            #
            # This deliberately targets the member's CURRENT channel rather
            # than the object that submitted the request. It used to require
            # `ch is channel`, so any reconnect during the turn meant the
            # answer was never pushed at all -- not attempted, not logged.
            # Phones reconnect constantly (a real iPhone reconnected 4x during
            # one 2-minute turn), so on a long request that was the common
            # case, not the edge case: the work completed, the answer existed,
            # and the phone sat on "Working" forever.
            #
            # Object identity was never the security property; the member
            # identity and the channel's trusted flag are. Both are checked.
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
            result = self.tasks.result(task_id)
            ch = self.edge_channels.get(member_id)
            if ch is None:
                logger.info(
                    "edge ask_result for %s not pushed — no live channel; the "
                    "phone recovers this via n2n/tasks/result on reconnect", member_id)
                return
            if not getattr(ch, "trusted", False):
                logger.warning(
                    "edge ask_result for %s not pushed — channel is not trusted", member_id)
                return
            if ch is not channel:
                # Normal after a reconnect. Worth recording, because a silent
                # skip here is exactly what hid this bug.
                logger.info("edge ask_result for %s pushing to a reconnected channel",
                            member_id)
            try:
                await ch.notify("n2n/edge/ask_result", {
                    "task_id": task_id, "state": result.get("state"),
                    "output_text": result.get("output_text"),
                    # A failed task carries its reason under `error`, not
                    # `output_text` -- forward it so the phone can say why
                    # instead of showing a bare "failed" with no text.
                    "error": result.get("error"),
                    "tokens_used": result.get("tokens_used"),
                })
            except Exception as e:
                logger.warning("edge ask_result push to %s failed: %s", member_id, e)
        asyncio.create_task(_push_result_when_done())
        return {"task_id": task_id}

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
        async task over its channel. Returns {task_id, member_id} or an error.

        feature 068 (US3/research D1/D2): a capability may resolve to an edge
        node (a phone advertising a capture capability via its scope, exactly
        like any agent member) — RiskRouter.select_member() already handles
        this with zero changes. What differs is HOW the selected target is
        invoked: an edge node has no skill to run via n2n/tasks/submit, so it
        branches to delegate_to_edge() (n2n/edge/capture) instead of
        delegate_to_member() (n2n/tasks/submit)."""
        from .router import NoCapableMember
        try:
            member_id = self.router.select_member(capability)["member_id"]
        except NoCapableMember as e:
            return {"error": "IN2N_ERR_NO_CAPABLE_MEMBER", "message": str(e)}
        member = self.risk.get_member(member_id)
        if member and member.get("node_type") == "edge":
            return await self.delegate_to_edge(member_id, capability)
        return await self.delegate_to_member(member_id, capability, input_text)

    async def delegate_to_edge(self, member_id: str, capability: str) -> dict:
        """Border-requested capture (feature 068, US3): mirrors
        delegate_to_member()'s call-out shape for an edge node. No production
        posture/component-scan preflight applies — there is no skill to scan,
        only a device-native capability. Tracked via the SAME self.tasks
        pattern _edge_on_ask (067) already established, so
        n2n_task_status/result/cancel work unchanged regardless of whether
        the target was an agent member or an edge node (research D2)."""
        ch = self.edge_channels.get(member_id)
        if ch is None:
            return {"error": "member_unreachable", "member_id": member_id,
                    "message": f"edge node {member_id} is not connected"}
        task_id = self.tasks.create(direction="outbound", peer_identity=member_id,
                                    target_type="capture", target_name=capability)

        async def worker(progress):
            progress("requesting capture")
            result = await ch.call("n2n/edge/capture", {"capability": capability},
                                   timeout=120.0)
            if result.get("decision") != "captured":
                raise RuntimeError(result.get("reason", "capture declined"))
            return result, 0
        self.tasks.run(task_id, worker)
        self.audit.record(direction="outbound", peer_identity=member_id,
                          target_type="capture", target_name=capability,
                          request_id=task_id, decision="requested",
                          outcome="submitted", channel_kind="in2n",
                          event="delegation", actor=self._audit_actor())
        return {"member_id": member_id, "task_id": task_id, "state": "submitted"}

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
        # US2: challenge the Border to attest it is our legitimate hub.
        member_nonce = os.urandom(32)
        if enrollment_token:
            resp = await ch.call("in2n/enroll", {
                "token": enrollment_token, "member_id": member_id,
                "cert_pem": cert_pem, "signature": signature,
                "member_nonce": member_nonce.hex(),
                "scope": list(self.member_scope) or None,
                "runtime_kind": os.environ.get("N2N_MEMBER_RUNTIME", "process"),
                "transport_binding": "distributed"}, timeout=30.0)
            # Persist the CA anchor delivered at enrollment.
            if resp.get("risk_ca"):
                self.risk.store_risk_anchor(resp["risk_ca"])
        else:
            resp = await ch.call("in2n/hello", {
                "member_id": member_id,
                "key_fingerprint": self.risk.fingerprint_of(cert_pem),
                "member_nonce": member_nonce.hex(),
                "signature": signature}, timeout=30.0)
        # US2 hub attestation: if we hold an anchor, the Border MUST prove it is
        # the legitimate hub for our risk; a missing/invalid attestation aborts.
        anchor = self.risk.risk_anchor()
        if anchor:
            risk_name = (member_id.split("/", 1)[0] if member_id else
                         (self.risk.get_risk() or {}).get("risk_name") or "risk")
            attest = resp.get("hub_attestation")
            if not attest or not self.risk.verify_hub_attestation(
                    attest, anchor, member_nonce, risk_name):
                writer.close()
                raise RuntimeError("iN2N hub attestation failed — refusing to trust Border")
            logger.info("iN2N: verified hub attestation for %s", risk_name)
        ch.trusted = True   # we pinned the Border endpoint at provisioning
        self.border_channel = ch
        logger.info("iN2N: dialed Border %s:%s as %s (%s)", host, port, member_id,
                    {k: v for k, v in resp.items() if k not in ("risk_ca", "hub_attestation")})
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
        # Record the task's owner as the channel's peer_identity (== member_id
        # once authenticated) so it always matches the identity the retrieval
        # handlers authorize against (owner-bound tasks, NCFED -00 §14.6).
        border = (getattr(channel, "peer_identity", None)
                  or getattr(channel, "member_id", None) or "border")
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
