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

# Global speaker reference for the API
_speaker = None
# In-memory table of injected routes: prefix -> route_dict
_injected = {}


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
            resp_body = {"injected": _injected}

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

    logger.info("Starting NetClaw BGP daemon v2 — AS%s router-id %s", LOCAL_AS, ROUTER_ID)

    _speaker = BGPSpeaker(
        local_as=LOCAL_AS,
        router_id=ROUTER_ID,
        listen_ip="0.0.0.0",
        listen_port=BGP_LISTEN_PORT,
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
