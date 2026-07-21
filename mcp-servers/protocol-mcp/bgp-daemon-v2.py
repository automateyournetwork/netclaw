#!/usr/bin/env python3
"""
BGP Daemon v2 — Persistent speaker with HTTP API for runtime route injection.
AS 65001 (NetClaw) <-> AS 65000 (Edge1 @ 172.16.0.1)

HTTP API (localhost:8179):
  POST /inject   {"network": "10.99.99.0/24", "next_hop": "172.16.0.2"}
  POST /withdraw {"network": "10.99.99.0/24"}
  GET  /rib
  GET  /peers
  GET  /status
"""
import asyncio
import ipaddress
import json
import logging
import os
import re
import sys
import urllib.parse
from ipaddress import IPv4Network
import struct

sys.path.insert(0, os.path.dirname(__file__))

from bgp.speaker import BGPSpeaker
from bgp.kernel import KernelRouteManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('/tmp/bgp-daemon-v2.log'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("bgp-daemon-v2")

ROUTER_ID   = os.environ.get("NETCLAW_ROUTER_ID", "4.4.4.4")
LOCAL_AS    = int(os.environ.get("NETCLAW_LOCAL_AS", "65001"))
BGP_PEERS   = json.loads(os.environ.get("NETCLAW_BGP_PEERS", "[]"))
API_PORT    = int(os.environ.get("BGP_API_PORT", "8179"))
BGP_LISTEN_PORT = int(os.environ.get("BGP_LISTEN_PORT", "1179"))
MESH_OPEN   = os.environ.get("NETCLAW_MESH_OPEN", "true").lower() in ("true", "1", "yes")
MESH_ENDPOINT = os.environ.get("NETCLAW_MESH_ENDPOINT", "")
LOCAL_IPV6  = os.environ.get("NETCLAW_LOCAL_IPV6", "")
DRY_RUN     = os.environ.get("NETCLAW_DRY_RUN", "").lower() in ("true", "1", "yes")

# N2N Federation (feature 052)
N2N_ENABLED = os.environ.get("N2N_ENABLED", "false").lower() in ("true", "1", "yes")
N2N_DISPLAY_NAME = os.environ.get("N2N_DISPLAY_NAME", "")
N2N_REFRESH_S = int(os.environ.get("N2N_INVENTORY_REFRESH_S", "21600"))

# Global federation service reference for the HTTP API
_federation = None

# Global speaker reference for the API
_speaker = None
# In-memory table of injected routes: prefix -> route_dict
_injected = {}


def _format_as_path(route):
    """Extract AS path as a list of integers from a BGPRoute."""
    from bgp.constants import ATTR_AS_PATH
    attr = route.path_attributes.get(ATTR_AS_PATH)
    if attr and hasattr(attr, 'segments'):
        result = []
        for seg_type, as_list in attr.segments:
            result.extend(as_list)
        return result
    return []


def _format_origin(route):
    """Extract origin as a string from a BGPRoute."""
    from bgp.constants import ATTR_ORIGIN
    attr = route.path_attributes.get(ATTR_ORIGIN)
    if attr and hasattr(attr, 'origin'):
        return {0: "IGP", 1: "EGP", 2: "INCOMPLETE"}.get(attr.origin, "UNKNOWN")
    return "UNKNOWN"


async def send_bgp_update(session, nlri_list, withdrawn=False):
    """
    Send a BGP UPDATE for the given NLRI list.
    nlri_list: list of (prefix_str, prefix_len) tuples
    """
    try:
        if withdrawn:
            # Withdrawn routes — encoded as 1-byte len + prefix bytes
            withdrawn_bytes = b""
            for (pfx, plen) in nlri_list:
                addr_bytes = IPv4Network(f"{pfx}/{plen}", strict=False).network_address.packed
                n_bytes = (plen + 7) // 8
                withdrawn_bytes += struct.pack("!B", plen) + addr_bytes[:n_bytes]

            # Empty path attrs for withdrawal
            msg = (
                struct.pack("!H", len(withdrawn_bytes))   # withdrawn len
                + withdrawn_bytes
                + struct.pack("!H", 0)                     # path attrs len
                # no NLRI
            )
        else:
            # Advertised routes
            # Build path attributes
            origin_attr = bytes([0x40, 0x01, 0x01, 0x00])           # ORIGIN IGP
            as_path_attr = bytes([0x40, 0x02, 0x06, 0x02, 0x01]) + struct.pack("!I", LOCAL_AS)  # AS_SEQUENCE [65001]
            nh_packed = ipaddress.IPv4Address("172.16.0.2").packed
            next_hop_attr = bytes([0x40, 0x03, 0x04]) + nh_packed    # NEXT_HOP

            path_attrs = origin_attr + as_path_attr + next_hop_attr

            nlri_bytes = b""
            for (pfx, plen) in nlri_list:
                addr_bytes = IPv4Network(f"{pfx}/{plen}", strict=False).network_address.packed
                n_bytes = (plen + 7) // 8
                nlri_bytes += struct.pack("!B", plen) + addr_bytes[:n_bytes]

            msg = (
                struct.pack("!H", 0)                       # no withdrawn
                + struct.pack("!H", len(path_attrs))       # path attrs len
                + path_attrs
                + nlri_bytes
            )

        # BGP message header: 16-byte marker + 2-byte length + 1-byte type
        marker = b"\xff" * 16
        total_len = 19 + len(msg)
        header = marker + struct.pack("!HB", total_len, 2)  # type 2 = UPDATE
        full_msg = header + msg

        session.writer.write(full_msg)
        await session.writer.drain()
        logger.info("Sent BGP UPDATE (%s) for %s", "withdraw" if withdrawn else "announce", nlri_list)
        return True
    except Exception as e:
        logger.error("Failed to send UPDATE: %s", e)
        return False


async def advertise_route(network: str, next_hop: str = "172.16.0.2"):
    """Advertise a prefix to all established peers."""
    net = IPv4Network(network, strict=False)
    pfx = str(net.network_address)
    plen = net.prefixlen
    key = f"{pfx}/{plen}"

    _injected[key] = {"next_hop": next_hop, "prefix": pfx, "prefix_len": plen}

    if _speaker is None:
        logger.error("Speaker not ready")
        return False

    success = False
    for peer_ip, session in _speaker.agent.sessions.items():
        state = session.fsm.get_state_name() if hasattr(session, "fsm") else "unknown"
        if state.lower() == "established":
            ok = await send_bgp_update(session, [(pfx, plen)], withdrawn=False)
            if ok:
                success = True
                logger.info("Advertised %s to %s", key, peer_ip)
    return success


async def withdraw_route(network: str):
    """Withdraw a previously advertised prefix."""
    net = IPv4Network(network, strict=False)
    pfx = str(net.network_address)
    plen = net.prefixlen
    key = f"{pfx}/{plen}"

    _injected.pop(key, None)

    if _speaker is None:
        return False

    success = False
    for peer_ip, session in _speaker.agent.sessions.items():
        state = session.fsm.get_state_name() if hasattr(session, "fsm") else "unknown"
        if state.lower() == "established":
            ok = await send_bgp_update(session, [(pfx, plen)], withdrawn=True)
            if ok:
                success = True
                logger.info("Withdrew %s from %s", key, peer_ip)
    return success


# ---- N2N Federation HTTP routes (feature 052) ----

async def handle_n2n(method, path, body):
    """Dispatch /n2n/* routes. Returns (resp_code, resp_body)."""
    if _federation is None:
        return 503, {"error": "N2N federation not enabled (set N2N_ENABLED=true)"}

    fed = _federation
    mgr = fed.manager
    parts = path.strip("/").split("/")  # e.g. ["n2n","peers","as65007-7.7.7.7","inventory"]

    try:
        if method == "GET" and path == "/n2n/status":
            peers = []
            for p in mgr.list_peers():
                meta = fed.inventory.load_remote(p["identity"], fed.refresh_s)
                peers.append({
                    "identity": p["identity"], "display_name": p["display_name"],
                    "state": p["state"], "chat_enabled": bool(p["chat_enabled"]),
                    "inventory_version": (meta or {}).get("inventory", {}).get("version") if meta else None,
                    "inventory_received_at": (meta or {}).get("received_at") if meta else None,
                    "stale": (meta or {}).get("stale") if meta else None,
                })
            return 200, {"enabled": True, "identity": fed.local_identity, "peers": peers}

        if method == "POST" and path == "/n2n/consent":
            peer_as = body.get("as"); router_id = body.get("router_id")
            if not peer_as or not router_id:
                return 400, {"error": "as and router_id required"}
            state = mgr.local_consent(int(peer_as), router_id, body.get("display_name"))
            # If we already learned remote consent, try opening the channel now.
            ident = f"as{peer_as}-{router_id}"
            if body.get("host") and body.get("port"):
                asyncio.create_task(fed.open_channel(int(peer_as), router_id,
                                                     body["host"], int(body["port"])))
            # If a channel is already open and this consent just completed
            # federation, (re)advertise + pull so a late consent still exchanges.
            if ident in fed.channels:
                async def _sync():
                    await fed.ensure_advertised(ident)
                    await fed.refresh_from(ident)
                asyncio.create_task(_sync())
            return 200, {"identity": ident, "state": state.value}

        if method == "POST" and path == "/n2n/kill":
            ident = body.get("peer")
            if not ident:
                return 400, {"error": "peer (identity) required"}
            ok = await fed.sever_local(ident)
            return (200 if ok else 404), {"severed": ok, "peer": ident}

        if method == "POST" and path == "/n2n/visibility":
            it, name, vis = body.get("item_type"), body.get("item_name"), body.get("visibility")
            if not all([it, name, vis]):
                return 400, {"error": "item_type, item_name, visibility required"}
            mgr._conn.execute(
                "INSERT OR REPLACE INTO visibility_setting (item_type,item_name,visibility,peer_list) "
                "VALUES (?,?,?,?)", (it, name, vis, json.dumps(body.get("peer_list")) if body.get("peer_list") else None))
            mgr._conn.commit()
            # Re-advertise to federated peers
            for ident, ch in list(fed.channels.items()):
                if mgr.is_federated(ident):
                    asyncio.create_task(fed._advertise_to(ch))
            return 200, {"success": True}

        if method == "GET" and len(parts) >= 3 and parts[1] == "peers":
            ident = parts[2]
            if len(parts) == 4 and parts[3] == "inventory":
                meta = fed.inventory.load_remote(ident, fed.refresh_s)
                if not meta:
                    return 404, {"error": "no inventory cached for peer"}
                return 200, meta
            peer = mgr.get_peer(ident)
            if not peer:
                return 404, {"error": "unknown peer"}
            peer["budget"] = fed.authz.budget_status(ident)
            return 200, peer

        if len(parts) == 4 and parts[1] == "peers" and parts[3] == "refresh" and method == "POST":
            return 200, await fed.refresh_from(parts[2])

        # ---- US2: grants, invocation, approvals, audit, config ----
        if path == "/n2n/grants" and method == "GET":
            return 200, {"grants": fed.authz.list_grants(body.get("peer") if body else None)}

        if path == "/n2n/grants" and method == "POST":
            for k in ("peer", "target_type", "target_name"):
                if not body.get(k):
                    return 400, {"error": f"missing required field '{k}'"}
            gid = fed.authz.grant(body["peer"], body["target_type"], body["target_name"],
                                  bool(body.get("requires_approval", False)), body.get("timeout_s"))
            return 200, {"grant_id": gid}

        if len(parts) == 3 and parts[1] == "grants" and method == "DELETE":
            fed.authz.revoke(int(parts[2]))
            return 200, {"revoked": int(parts[2])}

        if path == "/n2n/invoke" and method == "POST":
            if not body.get("peer") or not body.get("target_name"):
                return 400, {"error": "missing required field 'peer' or 'target_name'"}
            ident = body["peer"]; ttype = body.get("target_type", "tool")
            try:
                if ttype == "tool":
                    res = await fed.invoker.invoke_remote_tool(ident, body["target_name"], body.get("arguments") or {})
                else:
                    # skills go async (submit → task_id); invoke_remote_skill was
                    # renamed to submit_remote_skill in 053. A long skill must
                    # never run synchronously here or it times out (this is the
                    # very failure async delegation fixes).
                    res = await fed.invoker.submit_remote_skill(ident, body["target_name"], body.get("input_text", ""))
                return 200, res
            except Exception as e:
                code = getattr(e, "code", None); msg = getattr(e, "message", str(e))
                return 200, {"error": {"code": code, "message": msg}}

        if path == "/n2n/knowledge/route" and method == "POST":
            # Feature 064: choose which advertised collection (local or peer)
            # should answer a query — eN2N selection, deterministic (H2/H3).
            q = body.get("query")
            if not q:
                return 400, {"error": "missing required field 'query'"}
            return 200, fed.invoker.route_knowledge(q)

        if path == "/n2n/knowledge/query" and method == "POST":
            # Feature 064: retrieve a cited answer from a peer's advertised
            # collection over the dedicated n2n/knowledge/query method.
            if not body.get("peer") or not body.get("collection_id"):
                return 400, {"error": "missing required field 'peer' or 'collection_id'"}
            try:
                return 200, await fed.invoker.query_remote_knowledge(
                    body["peer"], body["collection_id"], body.get("query", ""),
                    k=int(body.get("k", 8)))
            except Exception as e:
                code = getattr(e, "code", None); msg = getattr(e, "message", str(e))
                return 200, {"error": {"code": code, "message": msg}}

        if path == "/n2n/approvals" and method == "GET":
            return 200, {"pending": fed.authz.pending_approvals()}

        if len(parts) == 3 and parts[1] == "approvals" and method == "POST":
            fed.authz.resolve_approval(int(parts[2]), body.get("action", "deny"), body.get("via", "cli"))
            return 200, {"resolved": int(parts[2]), "action": body.get("action")}

        if path == "/n2n/audit" and method == "GET":
            return 200, {"records": fed.audit.recent(body.get("peer") if body else None, 50)}

        if path == "/n2n/config" and method == "POST":
            if not body.get("peer"):
                return 400, {"error": "missing required field 'peer'"}
            ident = body["peer"]
            if "chat_enabled" in body:
                mgr.set_chat_enabled(ident, bool(body["chat_enabled"]))
            return 200, {"success": True, "peer": ident,
                         "chat_enabled": bool(mgr.get_peer(ident)["chat_enabled"])}

        # ---- US3: chat ----
        if path in ("/n2n/chat/open", "/n2n/chat/send") and method == "POST":
            if not body.get("peer"):
                return 400, {"error": "missing required field 'peer'"}
            if not body.get("text"):
                return 400, {"error": "missing required field 'text'"}
            res = await fed.chat.open_and_send(body["peer"], body["text"], body.get("session_id"))
            return 200, res

        if path == "/n2n/chats" and method == "GET":
            return 200, {"sessions": fed.chat.list_sessions()}

        # ---- US1: async delegated tasks ----
        if path == "/n2n/tasks" and method == "POST":
            if not body.get("peer") or not body.get("target_name"):
                return 400, {"error": "missing required field 'peer' or 'target_name'"}
            ttype = body.get("target_type", "skill")
            try:
                if ttype == "skill":
                    res = await fed.invoker.submit_remote_skill(
                        body["peer"], body["target_name"], body.get("input_text", ""))
                else:
                    # tools are fast/stdio — keep the synchronous 052 path
                    res = await fed.invoker.invoke_remote_tool(
                        body["peer"], body["target_name"], body.get("arguments") or {})
                return 200, res
            except Exception as e:
                return 200, {"error": {"code": getattr(e, "code", None),
                                       "message": getattr(e, "message", str(e))}}

        if path == "/n2n/tasks" and method == "GET":
            return 200, {"tasks": fed.tasks.list_recent()}

        if len(parts) == 4 and parts[1] == "tasks" and parts[3] == "cancel" and method == "POST":
            row = mgr._conn.execute("SELECT peer_identity FROM delegated_task WHERE task_id=?",
                                    (parts[2],)).fetchone()
            if row:
                try:
                    if fed.is_member_task(row["peer_identity"]):
                        ch = fed.member_channels.get(row["peer_identity"])
                        if ch is None:
                            return 200, {"task_id": parts[2], "cancelled": False,
                                         "note": "member not connected"}
                        return 200, await ch.call("n2n/tasks/cancel", {"task_id": parts[2]}, timeout=15.0)
                    return 200, await fed.invoker.cancel_remote_task(row["peer_identity"], parts[2])
                except Exception as e:
                    return 200, {"error": getattr(e, "message", str(e))}
            return 404, {"error": "unknown task"}

        # ---- US6: health + one-step connect/trust ----
        if path == "/n2n/health" and method == "GET":
            peers = []
            for p in mgr.list_peers():
                if p["state"] == "not_federated":
                    continue
                ident = p["identity"]
                h = fed.health_of(ident)
                meta = fed.inventory.load_remote(ident, fed.refresh_s)
                in_flight = [t for t in fed.tasks.list_recent()
                             if t["peer_identity"] == ident and t["state"] in ("submitted", "working")]
                peers.append({
                    "identity": ident, "display_name": p["display_name"], "state": p["state"],
                    "channel_state": h["channel_state"], "last_seen": h["last_seen"],
                    "endpoint": f"{p.get('endpoint_host')}:{p.get('endpoint_port')}",
                    "endpoint_updated_at": p.get("endpoint_updated_at"),
                    "inventory_stale": (meta or {}).get("stale") if meta else None,
                    "in_flight_tasks": [{"task_id": t["task_id"], "state": t["state"],
                                         "progress": t["progress"], "target": t["target_name"]}
                                        for t in in_flight],
                })
            return 200, {"identity": fed.local_identity, "peers": peers}

        if path == "/n2n/connect" and method == "POST":
            if not all(body.get(k) for k in ("peer", "host", "port")):
                return 400, {"error": "missing required field 'peer', 'host', or 'port'"}
            m = re.match(r"as(\d+)-(.+)", body["peer"])
            if not m:
                return 400, {"error": "peer must be 'as<AS>-<router-id>'"}
            pa, rid = int(m.group(1)), m.group(2)
            state = mgr.local_consent(pa, rid, body.get("display_name"))
            asyncio.create_task(fed.open_channel(pa, rid, body["host"], int(body["port"])))
            return 200, {"identity": body["peer"], "state": state.value, "dialing": True}

        if path == "/n2n/trust" and method == "POST":
            ident = body.get("peer")
            if not ident:
                return 400, {"error": "missing required field 'peer'"}
            if body.get("chat", True):
                mgr.set_chat_enabled(ident, True)
            granted = []
            for tgt in (body.get("tools") or []):
                ttype = "tool" if "/" in tgt else "skill"
                fed.authz.grant(ident, ttype, tgt)
                granted.append(tgt)
            return 200, {"peer": ident, "chat_enabled": True, "granted": granted}

        if len(parts) == 3 and parts[1] == "tasks" and method == "GET":
            # Status; if the task is an outbound one, fetch fresh from the peer
            task_id = parts[2]
            row = mgr._conn.execute(
                "SELECT direction, peer_identity, state FROM delegated_task WHERE task_id=?",
                (task_id,)).fetchone()
            if not row:
                return 404, {"error": "unknown task"}
            if row["direction"] == "outbound" and row["state"] not in ("completed", "failed", "cancelled"):
                try:
                    # iN2N tasks live on a MEMBER channel, not the eN2N mesh —
                    # poll the member directly (else it stalls at 'submitted').
                    if fed.is_member_task(row["peer_identity"]):
                        return 200, await fed.poll_member_task(row["peer_identity"], task_id, kind="result")
                    return 200, await fed.invoker.poll_remote_task(row["peer_identity"], task_id, kind="result")
                except Exception:
                    return 200, fed.tasks.result(task_id)
            return 200, fed.tasks.result(task_id)

        # ── iN2N: internal federation (feature 056) ──────────────────
        if path == "/n2n/risk" and method == "GET":
            r = fed.risk.get_risk()
            out = {"role": r["role"], "risk_name": r["risk_name"],
                   "description": r["description"], "enabled_stacks": r["enabled_stacks"],
                   "self_member_id": r.get("self_member_id")}
            if r["role"] == "border":
                members = fed.risk.list_members()
                out["member_count"] = len(members)
                out["members_active"] = sum(1 for m in members if m["state"] == "active")
            return 200, out

        # ── iN2N production posture (feature 057, US1/FR-003) ─────────
        if path == "/n2n/posture" and method == "GET":
            # Prefer the cached posture from the background poller (fresh, cheap);
            # fall back to an on-demand compute if the poller hasn't run yet.
            cached = getattr(fed, "posture_cache", None)
            if cached is not None:
                return 200, cached
            from bgp.federation import posture as _posture
            return 200, await _posture.compute_posture(fed)

        # ── claw certification: credential panel + rotation (feature 060) ──
        if path == "/n2n/certs" and method == "GET":
            from bgp.federation import certs as _certs
            import datetime as _dt
            def _days(na):
                if not na:
                    return None
                try:
                    return (_dt.datetime.fromisoformat(na) -
                            _dt.datetime.now(_dt.timezone.utc)).days
                except Exception:
                    return None
            creds = []
            for c in fed.manager.list_credentials():
                d = _days(c.get("not_after"))
                creds.append({"kind": c["kind"], "subject": c["subject_identity"],
                              "fingerprint": c["fingerprint"], "issuer": c.get("issuer"),
                              "not_after": c.get("not_after"), "days_remaining": d,
                              "state": c["state"],
                              "aging": ("red" if d is not None and d < 14 else
                                        "amber" if d is not None and d < 30 else "ok")})
            peers = [{"identity": p["identity"], "trust_model": p.get("trust_model"),
                      "claw_domain": p.get("claw_domain"), "verify_state": p.get("verify_state"),
                      "peer_cred_fp": p.get("peer_cred_fp"),
                      "peer_cred_not_after": p.get("peer_cred_not_after")}
                     for p in fed.manager.list_peers()]
            members = [{"member_id": m["member_id"], "credential_state": m.get("credential_state"),
                        "cred_fp": m.get("cred_fp"), "cred_not_after": m.get("cred_not_after")}
                       for m in fed.risk.list_members()]
            # Feature 063 (P4/FR-012): honest per-channel key-exchange + PQ posture.
            from bgp.federation import tls as _tls
            kex = []
            for ident, ch in (getattr(fed, "channels", {}) or {}).items():
                try:
                    sslobj = ch.writer.get_extra_info("ssl_object")
                except Exception:
                    sslobj = None
                if sslobj is None:
                    continue
                k = _tls.channel_kex(sslobj)
                k["identity"] = ident
                k["pq"] = "available" if _tls.is_pq_group(k.get("kex_group")) else "unavailable"
                kex.append(k)
            return 200, {"credentials": creds, "peers": peers, "members": members,
                         "cert_mode": "enforce" if fed.cert_enforce else
                                      ("on" if fed.cert_mode else "off"),
                         "pq_mode": getattr(fed, "pq_mode", "opportunistic"),
                         "pq_available": getattr(fed, "pq_available", False),
                         "channels_kex": kex}

        if path == "/n2n/certs/rotate" and method == "POST":
            from bgp.federation.rotation import RotationManager
            target = body.get("target")
            rot = RotationManager(fed)
            matched = [c for c in fed.manager.list_credentials()
                       if target in (c["subject_identity"], c["kind"])]
            if not matched:
                return 404, {"error": f"no credential matches {target!r}"}
            renewed = 0
            for c in matched:
                if await rot.renew_one(c):
                    renewed += 1
            return 200, {"target": target, "rotated": renewed}

        if path == "/n2n/certs/renew" and method == "POST":
            from bgp.federation.rotation import RotationManager
            n = await RotationManager(fed).run_once()
            return 200, {"renewed": n}

        # ── iN2N GAIT immutable audit trail (feature 057, US4) ───────
        if path == "/n2n/gait" and method == "GET":
            from bgp.federation import gait as _gait
            gait_dir = fed.manager.base_dir / "gait"
            return 200, {"events": _gait.recent(limit=25, gait_dir=gait_dir)}

        # ── iN2N fault isolation (feature 057, US6/FR-017/018) ───────
        if path == "/n2n/faults" and method == "GET":
            return 200, fed.health_report()

        if path == "/n2n/risk" and method == "POST":
            try:
                r = fed.risk.set_role(
                    body.get("role", "standalone"), risk_name=body.get("risk_name"),
                    description=body.get("description"),
                    enabled_stacks=body.get("enabled_stacks"),
                    border_endpoint=body.get("border_endpoint"),
                    self_member_id=body.get("self_member_id"))
            except ValueError as e:
                return 400, {"error": str(e)}
            return 200, {"role": r["role"], "risk_name": r["risk_name"],
                         "note": "restart the daemon to (re)start iN2N listeners/dialers"}

        if path == "/n2n/members" and method == "GET":
            def _spec_names(scope):
                out = []
                for e in fed.risk._scope_list(scope):
                    if isinstance(e, str):
                        if e not in fed.risk._BASE_NAMES:
                            out.append(e)
                    elif isinstance(e, dict) and e.get("tier") == "specialty":
                        out.append(e.get("name"))
                return out
            return 200, {"members": [
                {"member_id": m["member_id"], "display_name": m["display_name"],
                 "profile": m["profile"], "state": m["state"],
                 "transport_binding": m["transport_binding"],
                 "specialty_count": fed.risk.specialty_count(m["scope"]),
                 "skills": _spec_names(m["scope"]),
                 "live": m["member_id"] in fed.member_channels}
                for m in fed.risk.list_members()]}

        if path == "/n2n/members/health" and method == "GET":
            out = []
            for m in fed.risk.list_members():
                health = {}
                try:
                    health = json.loads(m["health"]) if m["health"] else {}
                except (ValueError, TypeError):
                    health = {}
                out.append({"member_id": m["member_id"], "state": m["state"],
                            "auth_failures": m["auth_failures"],
                            "live": m["member_id"] in fed.member_channels,
                            "health": health})
            return 200, {"members": out}

        if path == "/n2n/members/remove" and method == "POST":
            member_id = body.get("member_id")
            if not member_id:
                return 400, {"error": "member_id required"}
            ch = fed.member_channels.pop(member_id, None)
            if ch is not None:
                try:
                    await ch.close()
                except Exception:
                    pass
            ok = fed.risk.remove_member(member_id)
            return (200 if ok else 404), {"removed": ok, "member_id": member_id}

        if path == "/n2n/members/add" and method == "POST":
            name = body.get("name")
            if not name:
                return 400, {"error": "name required"}
            # Resolve a profile → its installed skill list via scripts/in2n-profiles.
            specialty = body.get("specialty")
            profile = body.get("profile")
            if profile and profile != "custom" and not specialty:
                specialty = _resolve_profile_skills(profile)
            try:
                out = fed.risk.add_member(name, profile=profile, specialty=specialty,
                                          ttl_seconds=body.get("ttl_seconds"),
                                          launch_cmd=body.get("launch_cmd"),
                                          on_demand=bool(body.get("on_demand", False)))
            except ValueError as e:
                return 400, {"error": str(e)}
            return 200, out

        if path == "/n2n/enroll/token" and method == "POST":
            try:
                tok = fed.risk.issue_token(label=body.get("label"),
                                           ttl_seconds=body.get("ttl_seconds"))
            except ValueError as e:
                return 400, {"error": str(e)}
            return 200, tok

        if path == "/n2n/route" and method == "POST":
            capability = body.get("capability") or body.get("target_hint")
            if not capability:
                return 400, {"error": "capability (or target_hint) required"}
            out = await fed.route_and_delegate(capability, body.get("request_text", ""))
            return (200 if "error" not in out else 409), out

        return 404, {"error": f"unknown n2n route {path}"}
    except Exception as e:
        logger.error("N2N route error %s %s: %s", method, path, e)
        return 500, {"error": str(e)}


def _resolve_profile_skills(profile: str):
    """Resolve a profile id → its installed skill names via scripts/in2n-profiles.py
    (catalog-derived, FR-019). Returns [] if the profile/tool is unavailable."""
    try:
        import importlib.util
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(repo, "scripts", "in2n-profiles.py")
        spec = importlib.util.spec_from_file_location("in2n_profiles", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.profiles().get(profile, {}).get("skills", [])
    except Exception as e:
        logger.warning("could not resolve profile '%s': %s", profile, e)
        return []


def _sync_risk_from_env(fed):
    """Populate the risk table from N2N_* env (set by the installer) so a fresh
    claw boots into its configured role without a manual /n2n/risk call."""
    role = os.environ.get("N2N_ROLE")
    if not role:
        return
    try:
        fed.risk.set_role(
            role,
            risk_name=os.environ.get("N2N_RISK_NAME"),
            description=os.environ.get("N2N_RISK_DESCRIPTION"),
            enabled_stacks=os.environ.get("N2N_ENABLED_STACKS"),
            border_endpoint=os.environ.get("N2N_BORDER_ENDPOINT"),
            self_member_id=os.environ.get("N2N_MEMBER_ID"))
        logger.info("iN2N role from env: %s (risk=%s)", role, os.environ.get("N2N_RISK_NAME"))
    except ValueError as e:
        logger.warning("iN2N env role rejected: %s", e)


async def _start_in2n(fed):
    """iN2N (feature 056): start per role. A Border listens for member dial-ins;
    a Member dials the Border outbound (no inbound port). Standalone does nothing."""
    try:
        _sync_risk_from_env(fed)
        risk = fed.risk.get_risk()
        role = risk["role"]
        if role == "border" and fed.risk.stack_enabled("in2n"):
            port = int(os.environ.get("N2N_IN2N_PORT", "0") or 0)
            if not port:
                logger.info("iN2N Border: set N2N_IN2N_PORT to accept member dial-ins")
                return

            async def on_conn(reader, writer):
                try:
                    await fed.accept_internal(reader, writer)
                except Exception as e:
                    logger.warning("iN2N accept failed: %s", e)

            server = await asyncio.start_server(on_conn, "0.0.0.0", port)
            fed._in2n_server = server  # keep a ref
            logger.info("iN2N Border listener on 0.0.0.0:%d (risk=%s)", port, risk["risk_name"])
            # feature 057: on entering production, REQUIRE (verify, never mutate)
            # security.mode=defenseclaw so the Border's OWN model turns (via the
            # OpenClaw gateway) are guarded (T019a/FR-007), then start the background
            # posture poller (US1/FR-003a). Check-only: the daemon must not rewrite
            # host security config.
            from bgp.federation import controls as _controls
            if _controls.is_production():
                ok, detail = _controls.require_defenseclaw_mode()
                logger.info("iN2N production: %s", detail)
            asyncio.create_task(_in2n_posture_poller(fed))
        elif role == "member" and risk.get("border_endpoint"):
            host, _, port = risk["border_endpoint"].rpartition(":")
            token = os.environ.get("N2N_ENROLLMENT_TOKEN", "")
            asyncio.create_task(_in2n_member_dialer(fed, host, int(port), token))
            logger.info("iN2N Member dialer → Border %s (member=%s)",
                        risk["border_endpoint"], risk.get("self_member_id"))
    except Exception as e:
        logger.error("iN2N start error: %s", e)


async def _start_cert_lifecycle(fed):
    """Feature 060: at startup obtain the domain-verified credential if the claw
    is configured for one, register long-lived local credentials for rotation,
    then renew everything due on an hourly cadence (FR-012). No-ops cheaply when
    cert_mode is off."""
    if not getattr(fed, "cert_mode", False):
        return
    from bgp.federation import acme, certs
    from bgp.federation.rotation import RotationManager
    rot = RotationManager(fed)
    try:
        # Register this claw's presented credential (ACME if configured, else the
        # self-signed host credential) so the scheduler and HUD track its expiry.
        await acme.ensure_domain_credential(fed)
        cert_pem, _ = fed.host_credential()
        kind = "acme" if acme.configured() else "host-pinned"
        subject = os.environ.get("N2N_CLAW_DOMAIN") or fed.local_identity
        rot.register(kind, subject, cert_pem, issuer=("ACME" if kind == "acme" else "self"))
    except Exception as e:
        logger.warning("cert lifecycle init: %s", e)
    interval = int(os.environ.get("N2N_CERT_RENEW_CHECK_S", "3600"))
    while True:
        try:
            n = await rot.run_once()
            if n:
                logger.info("cert rotation: renewed %d credential(s)", n)
        except Exception as e:
            logger.warning("cert rotation cycle error: %s", e)
        await asyncio.sleep(interval)


async def _in2n_posture_poller(fed, interval_s: int = 10):
    """Background poll (feature 057, US1/FR-003a): keep fed.posture_cache fresh so
    the status tool, operator heartbeat, and HUD show current posture without
    waiting for the next delegation. The delegation preflight computes posture
    itself (authoritative fail-closed) and does NOT rely on this cache."""
    from bgp.federation import posture as _posture
    prev_summary = None
    while True:
        try:
            p = await _posture.compute_posture(fed)
            fed.posture_cache = p
            if p.get("summary") != prev_summary:
                logger.info("iN2N posture: %s", p.get("summary"))
                prev_summary = p.get("summary")
        except Exception as e:
            logger.warning("posture poll error: %s", e)
        await asyncio.sleep(interval_s)


async def _in2n_member_dialer(fed, host, port, token):
    """Member side: dial the Border with bounded backoff; re-dial on drop. First
    dial enrolls (token); once enrolled/pinned, reconnects use the hello path."""
    backoff = 5
    used_token = token
    while True:
        try:
            ch = fed.border_channel
            if ch is None or getattr(ch, "_closed", True):
                await fed.dial_border(host, port, enrollment_token=used_token)
                used_token = ""  # spent after a successful enroll
                backoff = 5
        except Exception as e:
            if used_token:
                # Token may be spent already (e.g. after a restart when we are
                # still pinned on the Border) — fall back to the pinned-key hello.
                logger.info("iN2N enroll failed (%s); will retry via pinned-key hello", e)
                used_token = ""
            else:
                logger.info("iN2N dial to Border %s:%d failed (%s) — retry in %ds",
                            host, port, e, backoff)
                backoff = min(backoff * 2, 60)
        await asyncio.sleep(10 if fed.border_channel is not None else backoff)


# ---- Asyncio HTTP server ----

async def handle_http(reader, writer):
    try:
        # Read the full request: headers first (until CRLFCRLF), then the body
        # per Content-Length. A single read(4096) races TCP segmentation — httpx
        # often sends headers and body in separate segments, which silently
        # dropped the JSON body and surfaced as "missing required field 'peer'".
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = await reader.read(65536)
            if not chunk:
                break
            buf += chunk
        header_blob, _, rest = buf.partition(b"\r\n\r\n")
        header_text = header_blob.decode(errors="replace")
        lines = header_text.split("\r\n")
        if not lines or not lines[0]:
            writer.close()
            return

        method, path, *_ = lines[0].split(" ")
        # Route on the bare path — clients (n2n-mcp) pass GET parameters as a
        # query string, which must not defeat the exact-match routing below.
        # Query params are merged into `body` (JSON body wins) since handlers
        # read GET options from there.
        path, _, _query = path.partition("?")
        _query_params = {k: v[-1] for k, v in urllib.parse.parse_qs(_query).items()}

        # Determine Content-Length and read the remainder of the body
        content_length = 0
        for h in lines[1:]:
            if h.lower().startswith("content-length:"):
                try:
                    content_length = int(h.split(":", 1)[1].strip())
                except ValueError:
                    content_length = 0
                break
        body_bytes = rest
        while len(body_bytes) < content_length:
            chunk = await reader.read(65536)
            if not chunk:
                break
            body_bytes += chunk

        # Parse JSON body for POST
        body = {}
        raw_body = body_bytes.decode(errors="replace").strip()
        if raw_body:
            try:
                body = json.loads(raw_body)
            except Exception as e:
                logger.warning("Bad JSON body on %s %s: %s", method, path, e)
        for k, v in _query_params.items():
            body.setdefault(k, v)

        resp_code = 200
        resp_body = {}

        if method == "GET" and path == "/status":
            peers = []
            if _speaker:
                for peer_ip, session in _speaker.agent.sessions.items():
                    state = session.fsm.get_state_name() if hasattr(session, "fsm") else "unknown"
                    peers.append({"peer": peer_ip, "state": state})
            resp_body = {"status": "running", "peers": peers, "injected_routes": list(_injected.keys())}

        elif method == "GET" and path == "/rib":
            loc_rib_data = {}
            adj_rib_in_data = {}
            kernel_routes = []
            if _speaker:
                for route in _speaker.agent.loc_rib.get_all_routes():
                    loc_rib_data[route.prefix] = {
                        "prefix": route.prefix,
                        "next_hop": route.next_hop,
                        "peer_id": route.peer_id,
                        "peer_ip": route.peer_ip,
                        "source": route.source,
                        "afi": "IPv6" if route.afi == 2 else "IPv4",
                        "best": route.best,
                        "as_path": _format_as_path(route),
                        "origin": _format_origin(route),
                    }
                for peer_ip, sess in _speaker.agent.sessions.items():
                    if sess.is_established():
                        peer_routes = []
                        for pfx in sess.adj_rib_in.get_prefixes():
                            for r in sess.adj_rib_in.get_routes(pfx):
                                peer_routes.append({
                                    "prefix": r.prefix,
                                    "next_hop": r.next_hop,
                                    "as_path": _format_as_path(r),
                                })
                        adj_rib_in_data[peer_ip] = peer_routes
                if _speaker.agent.kernel_route_manager:
                    kernel_routes = sorted(_speaker.agent.kernel_route_manager.get_installed_routes())
            resp_body = {
                "injected": _injected,
                "loc_rib": loc_rib_data,
                "loc_rib_count": len(loc_rib_data),
                "adj_rib_in": adj_rib_in_data,
                "kernel_routes": kernel_routes,
            }

        elif method == "GET" and path == "/peers":
            peers = []
            if _speaker:
                for peer_ip, session in _speaker.agent.sessions.items():
                    state = session.fsm.get_state_name() if hasattr(session, "fsm") else "unknown"
                    peers.append({"peer": peer_ip, "state": state})
            resp_body = {"peers": peers}

        elif method == "POST" and path == "/inject":
            network = body.get("network")
            next_hop = body.get("next_hop", "172.16.0.2")
            if not network:
                resp_code = 400
                resp_body = {"error": "network required"}
            else:
                ok = await advertise_route(network, next_hop)
                resp_body = {"success": ok, "network": network, "next_hop": next_hop}

        elif method == "POST" and path == "/withdraw":
            network = body.get("network")
            if not network:
                resp_code = 400
                resp_body = {"error": "network required"}
            else:
                ok = await withdraw_route(network)
                resp_body = {"success": ok, "network": network}

        elif method == "POST" and path == "/add_peer":
            # Runtime mesh peer addition (no restart needed)
            peer_as = body.get("as")
            peer_ip = body.get("ip")
            peer_port = int(body.get("port", 179))
            accept_any = bool(body.get("accept_any_source", False))
            is_hostname = bool(body.get("hostname", False))

            if not peer_as:
                resp_code = 400
                resp_body = {"error": "as required"}
            elif not accept_any and not peer_ip:
                resp_code = 400
                resp_body = {"error": "ip required (or set accept_any_source=true)"}
            elif _speaker is None:
                resp_code = 503
                resp_body = {"error": "speaker not ready"}
            else:
                try:
                    if accept_any:
                        synthetic_key = f"mesh-as{peer_as}"
                        _speaker.add_peer(
                            peer_ip=synthetic_key,
                            peer_as=int(peer_as),
                            passive=True,
                            accept_any_source=True,
                        )
                        # Start the session
                        await _speaker.agent.start_peer(synthetic_key)
                        resp_body = {"success": True, "peer": synthetic_key, "type": "mesh_inbound"}
                    else:
                        _speaker.add_peer(
                            peer_ip=peer_ip,
                            peer_as=int(peer_as),
                            peer_port=peer_port,
                            hostname=is_hostname,
                        )
                        # Start the session
                        await _speaker.agent.start_peer(peer_ip)
                        resp_body = {"success": True, "peer": peer_ip, "type": "mesh_outbound" if is_hostname else "standard"}
                except Exception as e:
                    resp_code = 500
                    resp_body = {"error": str(e)}

        elif method == "POST" and path == "/remove_peer":
            peer_key = body.get("peer")  # IP or "mesh-asNNNN"
            if not peer_key:
                resp_code = 400
                resp_body = {"error": "peer required (IP or mesh-asNNNN)"}
            elif _speaker is None:
                resp_code = 503
                resp_body = {"error": "speaker not ready"}
            else:
                try:
                    _speaker.remove_peer(peer_key)
                    resp_body = {"success": True, "removed": peer_key}
                except Exception as e:
                    resp_code = 500
                    resp_body = {"error": str(e)}

        elif method == "GET" and path == "/mesh_directory":
            if _speaker:
                directory = {}
                for as_num, info in _speaker.agent.mesh_directory.items():
                    directory[str(as_num)] = info
                resp_body = {
                    "local_as": LOCAL_AS,
                    "mesh_endpoint": _speaker.agent.mesh_endpoint,
                    "mesh_open": MESH_OPEN,
                    "directory": directory,
                }
            else:
                resp_code = 503
                resp_body = {"error": "speaker not ready"}

        elif method == "POST" and path == "/set_mesh_endpoint":
            endpoint = body.get("endpoint", "")
            if endpoint and _speaker:
                _speaker.agent.mesh_endpoint = endpoint
                resp_body = {"success": True, "endpoint": endpoint}
            elif not _speaker:
                resp_code = 503
                resp_body = {"error": "speaker not ready"}
            else:
                resp_code = 400
                resp_body = {"error": "endpoint required"}

        elif method == "GET" and path == "/tunnels":
            if _speaker:
                resp_body = {
                    "local_as": LOCAL_AS,
                    "tunnels": _speaker.agent.tunnel_manager.get_tunnel_stats(),
                }
            else:
                resp_code = 503
                resp_body = {"error": "speaker not ready"}

        elif method == "POST" and path == "/tunnel/retry":
            if _speaker:
                agent = _speaker.agent
                retried = []
                for peer_ip, session in agent.sessions.items():
                    if session.is_established() and session.config.peer_tunnel_endpoint:
                        peer_as = session.config.peer_as
                        endpoint = session.config.peer_tunnel_endpoint
                        if agent.local_as < peer_as:
                            # Tear down existing broken tunnel first
                            await agent.tunnel_manager.teardown_tunnel(peer_as)
                            asyncio.create_task(
                                agent.tunnel_manager.initiate_tunnel(peer_as, endpoint)
                            )
                            retried.append(f"AS{peer_as} at {endpoint}")
                resp_body = {"retried": retried}
            else:
                resp_code = 503
                resp_body = {"error": "speaker not ready"}

        elif path.startswith("/n2n"):
            resp_code, resp_body = await handle_n2n(method, path, body)

        else:
            resp_code = 404
            resp_body = {"error": "not found"}

        json_resp = json.dumps(resp_body, indent=2)
        http_resp = (
            f"HTTP/1.1 {resp_code} OK\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(json_resp)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{json_resp}"
        )
        writer.write(http_resp.encode())
        await writer.drain()
    except Exception as e:
        logger.error("HTTP handler error: %s", e)
    finally:
        writer.close()


async def _current_ngrok_endpoint():
    """Return the current ngrok TCP endpoint 'host:port', or None."""
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=3)
        for t in json.loads(resp.read()).get("tunnels", []):
            if t.get("proto") == "tcp":
                return t["public_url"].replace("tcp://", "")
    except Exception:
        pass
    return None


async def _endpoint_watcher():
    """US3: on ngrok endpoint change, update our mesh endpoint and re-announce
    it to federated peers over live channels. Also re-announce periodically so
    peers that (re)connect after our restart learn the current endpoint."""
    last = _speaker.agent.mesh_endpoint if _speaker else None
    while True:
        try:
            await asyncio.sleep(30)
            cur = await _current_ngrok_endpoint()
            if not cur:
                continue
            if cur != last:
                logger.info("ngrok endpoint changed %s → %s — re-announcing to peers", last, cur)
                if _speaker:
                    _speaker.agent.mesh_endpoint = cur
                last = cur
            if _federation is not None:
                await _federation.reannounce_endpoint(cur)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.debug("endpoint watcher error: %s", e)


async def main():
    global _speaker

    logger.info("Starting NetClaw BGP daemon v2 — AS%s router-id %s (mesh_open=%s)", LOCAL_AS, ROUTER_ID, MESH_OPEN)

    # Auto-detect ngrok endpoint if not set
    mesh_endpoint = MESH_ENDPOINT
    if not mesh_endpoint:
        try:
            import urllib.request
            resp = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=3)
            tunnels = json.loads(resp.read())
            for t in tunnels.get("tunnels", []):
                if t.get("proto") == "tcp":
                    # Extract "host:port" from "tcp://host:port"
                    mesh_endpoint = t["public_url"].replace("tcp://", "")
                    logger.info("Auto-detected ngrok mesh endpoint: %s", mesh_endpoint)
                    break
        except Exception as e:
            logger.debug("Could not auto-detect ngrok endpoint: %s", e)

    # Create kernel route manager for FIB installation
    krm = KernelRouteManager(dry_run=DRY_RUN)

    _speaker = BGPSpeaker(
        local_as=LOCAL_AS,
        router_id=ROUTER_ID,
        listen_ip="0.0.0.0",
        listen_port=BGP_LISTEN_PORT,
        kernel_route_manager=krm,
        mesh_open=MESH_OPEN,
        mesh_endpoint=mesh_endpoint,
        local_ipv6=LOCAL_IPV6 or None,
    )

    for peer in BGP_PEERS:
        accept_any_source = bool(peer.get("accept_any_source", False))
        is_hostname = bool(peer.get("hostname", False))
        peer_passive = bool(peer.get("passive", False))
        peer_port = int(peer.get("port", 179))

        if accept_any_source:
            # Type 3: Inbound mesh peer — no IP, passive, matched by AS from OPEN
            synthetic_key = f"mesh-as{peer['as']}"
            _speaker.add_peer(
                peer_ip=synthetic_key,
                peer_as=peer["as"],
                passive=True,
                accept_any_source=True,
            )
            logger.info("Added mesh peer AS%s (accept_any_source, passive)", peer["as"])
        else:
            # Type 1: Local FRR peer (ip is an IP address)
            # Type 2: Outbound mesh peer (ip is a hostname like ngrok endpoint)
            _speaker.add_peer(
                peer_ip=peer["ip"],
                peer_as=peer["as"],
                peer_port=peer_port,
                passive=peer_passive,
                hostname=is_hostname,
            )
            logger.info("Added peer %s AS%s port=%s passive=%s hostname=%s",
                        peer["ip"], peer["as"], peer_port, peer_passive, is_hostname)

    # Start HTTP API
    http_server = await asyncio.start_server(handle_http, "127.0.0.1", API_PORT)
    logger.info("HTTP API listening on 127.0.0.1:%d", API_PORT)

    # Attach N2N federation service (feature 052) before starting the speaker
    # so the listener's NCFED discrimination branch can hand off channels.
    global _federation
    if N2N_ENABLED:
        try:
            from bgp.federation.service import FederationService
            _federation = FederationService(
                local_as=LOCAL_AS, router_id=ROUTER_ID,
                display_name=N2N_DISPLAY_NAME, refresh_s=N2N_REFRESH_S,
            )
            _speaker.agent.federation_service = _federation
            logger.info("N2N federation ENABLED — identity %s", _federation.local_identity)
        except Exception as e:
            logger.error("N2N federation failed to init (continuing without it): %s", e)
    else:
        logger.info("N2N federation disabled (set N2N_ENABLED=true to enable)")

    logger.info("Starting BGP speaker...")
    await _speaker.start()

    # US2: start the N2N reconnect supervisor so federation self-heals across
    # peer restarts without a manual re-dial.
    if _federation is not None:
        _federation.start_supervisor()
        # US3: watch the ngrok endpoint and re-announce it to federated peers on
        # change so nobody swaps host:port by hand (FR-010).
        asyncio.create_task(_endpoint_watcher())
        # iN2N (feature 056): start the internal-federation listener (Border) or
        # dialer (Member) per this claw's role. Members dial outbound only.
        asyncio.create_task(_start_in2n(_federation))
        # Claw certification (feature 060): obtain/refresh the domain-verified
        # credential (if configured) and run the automatic renewal scheduler.
        asyncio.create_task(_start_cert_lifecycle(_federation))

    # Auto-advertise identity route (router-id as /32)
    _speaker.agent.originate_route(f"{ROUTER_ID}/32")
    logger.info("Advertised identity route: %s/32", ROUTER_ID)

    # Main loop — log state, re-advertise injected routes on reconnect
    prev_states = {}
    async with http_server:
        while True:
            try:
                for peer_ip, session in _speaker.agent.sessions.items():
                    state = session.fsm.get_state_name() if hasattr(session, "fsm") else "unknown"
                    prev = prev_states.get(peer_ip)
                    if state != prev:
                        logger.info("Peer %s state: %s → %s", peer_ip, prev, state)
                        prev_states[peer_ip] = state
                        # Re-advertise injected routes when session comes back up
                        if state.lower() == "established" and _injected:
                            logger.info("Session up — re-advertising %d injected routes", len(_injected))
                            for key, info in list(_injected.items()):
                                await send_bgp_update(
                                    session,
                                    [(info["prefix"], info["prefix_len"])],
                                    withdrawn=False
                                )
            except Exception as e:
                logger.debug("State poll error: %s", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
