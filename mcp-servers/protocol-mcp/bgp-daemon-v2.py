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
import sys
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

        # ---- US2: grants, invocation, approvals, audit, config ----
        if path == "/n2n/grants" and method == "GET":
            return 200, {"grants": fed.authz.list_grants(body.get("peer") if body else None)}

        if path == "/n2n/grants" and method == "POST":
            gid = fed.authz.grant(body["peer"], body["target_type"], body["target_name"],
                                  bool(body.get("requires_approval", False)), body.get("timeout_s"))
            return 200, {"grant_id": gid}

        if len(parts) == 3 and parts[1] == "grants" and method == "DELETE":
            fed.authz.revoke(int(parts[2]))
            return 200, {"revoked": int(parts[2])}

        if path == "/n2n/invoke" and method == "POST":
            ident = body["peer"]; ttype = body.get("target_type", "tool")
            try:
                if ttype == "tool":
                    res = await fed.invoker.invoke_remote_tool(ident, body["target_name"], body.get("arguments") or {})
                else:
                    res = await fed.invoker.invoke_remote_skill(ident, body["target_name"], body.get("input_text", ""))
                return 200, res
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
            ident = body["peer"]
            if "chat_enabled" in body:
                mgr.set_chat_enabled(ident, bool(body["chat_enabled"]))
            return 200, {"success": True, "peer": ident,
                         "chat_enabled": bool(mgr.get_peer(ident)["chat_enabled"])}

        # ---- US3: chat ----
        if path == "/n2n/chat/open" and method == "POST":
            res = await fed.chat.open_and_send(body["peer"], body.get("text", ""), body.get("session_id"))
            return 200, res

        if path == "/n2n/chat/send" and method == "POST":
            res = await fed.chat.open_and_send(body["peer"], body["text"], body.get("session_id"))
            return 200, res

        if path == "/n2n/chats" and method == "GET":
            return 200, {"sessions": fed.chat.list_sessions()}

        return 404, {"error": f"unknown n2n route {path}"}
    except Exception as e:
        logger.error("N2N route error %s %s: %s", method, path, e)
        return 500, {"error": str(e)}


# ---- Asyncio HTTP server ----

async def handle_http(reader, writer):
    try:
        data = await reader.read(4096)
        request = data.decode(errors="replace")
        lines = request.split("\r\n")
        if not lines:
            writer.close()
            return

        method, path, *_ = lines[0].split(" ")

        # Parse body for POST
        body = {}
        if "\r\n\r\n" in request:
            raw_body = request.split("\r\n\r\n", 1)[1].strip()
            if raw_body:
                try:
                    body = json.loads(raw_body)
                except Exception:
                    pass

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
