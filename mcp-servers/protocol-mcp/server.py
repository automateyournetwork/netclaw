#!/usr/bin/env python3
"""
Protocol MCP Server — BGP + OSPF + GRE participation for NetClaw

Exposes 10 tools via FastMCP/stdio for live control-plane participation:
  BGP:  bgp_get_peers, bgp_get_rib, bgp_inject_route, bgp_withdraw_route, bgp_adjust_local_pref
  OSPF: ospf_get_neighbors, ospf_get_lsdb, ospf_adjust_cost
  GRE:  gre_tunnel_status
  Meta: protocol_summary

Source protocol modules: WontYouBeMyNeighbour (github.com/automateyournetwork/WontYouBeMyNeighbour)
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Add netclaw_tokens to path for GCF serialization
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))


def _gcf_dumps(data, **kwargs) -> str:
    """Serialize data using GCF with graph auto-detection and session dedup.

    Auto-detects graph-shaped data (nodes + edges) and uses graph profile.
    Session dedup tracks previously-sent symbols across calls.
    Delta encoding sends only changes on re-queries.
    Falls back to generic profile for flat data, and to JSON on any error.
    """
    try:
        from netclaw_tokens.gcf_serializer import serialize_response
        result = serialize_response(data, use_session=True, use_delta=True)
        return result["encoded_data"]
    except Exception:
        return json.dumps(data, indent=2, default=str)





# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
ROUTER_ID = os.environ.get("NETCLAW_ROUTER_ID", "4.4.4.4")
LOCAL_AS = int(os.environ.get("NETCLAW_LOCAL_AS", "65001"))
BGP_PEERS_JSON = os.environ.get("NETCLAW_BGP_PEERS", "[]")
OSPF_AREAS_JSON = os.environ.get("NETCLAW_OSPF_AREAS", "[]")
GRE_TUNNELS_JSON = os.environ.get("NETCLAW_GRE_TUNNELS", "[]")
LAB_MODE = os.environ.get("NETCLAW_LAB_MODE", "false").lower() in ("true", "1", "yes")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("protocol-mcp")

# ---------------------------------------------------------------------------
# Late-import protocol modules (heavy deps like scapy)
# ---------------------------------------------------------------------------
_bgp_connector = None
_ospf_connector = None
_bgp_speaker = None
_ospf_speaker = None
_initialized = False


async def _ensure_init():
    """Lazy-initialise protocol speakers from env config."""
    global _bgp_connector, _ospf_connector, _bgp_speaker, _ospf_speaker, _initialized
    if _initialized:
        return
    _initialized = True

    bgp_peers = json.loads(BGP_PEERS_JSON)
    ospf_areas = json.loads(OSPF_AREAS_JSON)

    # --- BGP ---
    if bgp_peers:
        try:
            from bgp.speaker import BGPSpeaker
            from connectors.bgp_connector import BGPConnector

            _bgp_speaker = BGPSpeaker(
                local_as=LOCAL_AS,
                router_id=ROUTER_ID,
            )
            for peer_cfg in bgp_peers:
                accept_any_source = bool(peer_cfg.get("accept_any_source", False))
                is_hostname = bool(peer_cfg.get("hostname", False))
                peer_passive = bool(peer_cfg.get("passive", False))
                peer_port = int(peer_cfg.get("port", 179))

                if accept_any_source:
                    # Inbound mesh peer — matched by AS from OPEN
                    synthetic_key = f"mesh-as{peer_cfg['as']}"
                    _bgp_speaker.add_peer(
                        peer_ip=synthetic_key,
                        peer_as=peer_cfg["as"],
                        passive=True,
                        accept_any_source=True,
                    )
                else:
                    # Standard peer or outbound mesh peer (hostname)
                    _bgp_speaker.add_peer(
                        peer_ip=peer_cfg["ip"],
                        peer_as=peer_cfg["as"],
                        peer_port=peer_port,
                        passive=peer_passive,
                        hostname=is_hostname,
                    )
            _bgp_connector = BGPConnector(_bgp_speaker)
            logger.info("BGP speaker initialised — AS %s, %d peer(s)", LOCAL_AS, len(bgp_peers))
        except Exception as exc:
            logger.warning("BGP init skipped: %s", exc)

    # --- OSPFv3 ---
    if ospf_areas:
        try:
            from ospfv3.speaker import OSPFv3Speaker
            from connectors.ospf_connector import OSPFConnector

            _ospf_speaker = OSPFv3Speaker(router_id=ROUTER_ID)
            _ospf_connector = OSPFConnector(_ospf_speaker)
            logger.info("OSPFv3 speaker initialised — router-id %s", ROUTER_ID)
        except Exception as exc:
            logger.warning("OSPFv3 init skipped: %s", exc)

    logger.info(
        "Protocol MCP ready  bgp=%s  ospf=%s  lab_mode=%s",
        "yes" if _bgp_connector else "no",
        "yes" if _ospf_connector else "no",
        LAB_MODE,
    )


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("protocol-mcp")


# ── BGP tools ──────────────────────────────────────────────────────────────

# The persistent mesh daemon (bgp-daemon-v2.py) is the source of truth when it
# is running: it holds the FRR lab session AND all NetClaw mesh peers. The
# private in-process speaker below only knows the env-configured peers, so
# always try the daemon API first and fall back to the speaker.
BGP_DAEMON_API = os.environ.get("BGP_DAEMON_API", "http://127.0.0.1:8179")


async def _daemon_get(path: str) -> Optional[dict]:
    """Query the running mesh daemon's HTTP API. None if daemon not running."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{BGP_DAEMON_API}{path}")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


async def _daemon_post(path: str, body: dict) -> Optional[dict]:
    """POST to the running mesh daemon's HTTP API. None if daemon not running."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{BGP_DAEMON_API}{path}", json=body)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


@mcp.tool()
async def bgp_get_peers() -> str:
    """List BGP peer sessions with state, AS, IP, uptime, and prefix counts.

    Includes NetClaw mesh peers (other NetClaw instances over ngrok) when the
    mesh daemon is running, plus local router peers (e.g. FRR lab).
    """
    daemon = await _daemon_get("/peers")
    if daemon is not None:
        status = await _daemon_get("/status") or {}
        rib = await _daemon_get("/rib") or {}
        # Enrich with AS numbers from loc-rib AS paths
        peer_as = {}
        for route in (rib.get("loc_rib") or {}).values():
            path = route.get("as_path") or []
            if route.get("peer_ip") and path:
                peer_as.setdefault(route["peer_ip"], path[0])
        peers = [
            {**p, "as": peer_as.get(p.get("peer")),
             "mesh": str(p.get("peer", "")).startswith("mesh-")
                     or not all(c in "0123456789abcdefABCDEF:." for c in str(p.get("peer", "")))}
            for p in daemon.get("peers", [])
        ]
        return _gcf_dumps({"peers": peers, "count": len(peers),
                           "source": "mesh-daemon", "daemon_status": status.get("status")})
    await _ensure_init()
    if not _bgp_connector:
        return json.dumps({"error": "BGP not configured. Set NETCLAW_BGP_PEERS, or start the mesh daemon."})
    peers = await _bgp_connector.get_peers()
    return _gcf_dumps({"peers": peers, "count": len(peers), "source": "in-process speaker"})


@mcp.tool()
async def bgp_get_rib(prefix: Optional[str] = None) -> str:
    """Query the Loc-RIB. Optionally filter by prefix (e.g. '10.0.0.0/24').

    Includes routes learned from NetClaw mesh peers when the mesh daemon is running.
    """
    daemon = await _daemon_get("/rib")
    if daemon is not None:
        routes = list((daemon.get("loc_rib") or {}).values())
        if prefix:
            routes = [r for r in routes if r.get("prefix") == prefix]
        return _gcf_dumps({"routes": routes, "count": len(routes), "source": "mesh-daemon"})
    await _ensure_init()
    if not _bgp_connector:
        return json.dumps({"error": "BGP not configured. Set NETCLAW_BGP_PEERS, or start the mesh daemon."})
    routes = await _bgp_connector.get_rib(prefix=prefix)
    return _gcf_dumps({"routes": routes, "count": len(routes), "source": "in-process speaker"})


@mcp.tool()
async def bgp_inject_route(
    network: str,
    next_hop: Optional[str] = None,
    as_path: Optional[str] = None,
    local_pref: int = 100,
) -> str:
    """Inject a route into the BGP RIB and advertise to peers.

    Args:
        network: CIDR prefix (e.g. '192.168.1.0/24')
        next_hop: Next-hop IP (defaults to 0.0.0.0 / self)
        as_path: Comma-separated AS path (e.g. '65001,65002')
        local_pref: LOCAL_PREF value (default 100)
    """
    body = {"network": network}
    if next_hop:
        body["next_hop"] = next_hop
    daemon = await _daemon_post("/inject", body)
    if daemon is not None:
        return _gcf_dumps({**daemon, "source": "mesh-daemon"})

    await _ensure_init()
    if not _bgp_connector:
        return json.dumps({"error": "BGP not configured."})

    parsed_path = [int(a) for a in as_path.split(",")] if as_path else None
    result = await _bgp_connector.inject_route(
        network=network,
        next_hop=next_hop,
        as_path=parsed_path,
        local_pref=local_pref,
    )
    return _gcf_dumps(result)


@mcp.tool()
async def bgp_withdraw_route(network: str) -> str:
    """Withdraw a route from the BGP RIB.

    Args:
        network: CIDR prefix to withdraw (e.g. '192.168.1.0/24')
    """
    daemon = await _daemon_post("/withdraw", {"network": network})
    if daemon is not None:
        return _gcf_dumps({**daemon, "source": "mesh-daemon"})

    await _ensure_init()
    if not _bgp_connector:
        return json.dumps({"error": "BGP not configured."})
    result = await _bgp_connector.withdraw_route(network=network)
    return _gcf_dumps(result)


@mcp.tool()
async def bgp_adjust_local_pref(network: str, local_pref: int) -> str:
    """Change the LOCAL_PREF for a route in the RIB.

    Args:
        network: CIDR prefix (e.g. '10.0.0.0/24')
        local_pref: New LOCAL_PREF value (higher = more preferred)
    """
    await _ensure_init()
    if not _bgp_connector:
        return json.dumps({"error": "BGP not configured."})
    result = await _bgp_connector.adjust_local_pref(network=network, local_pref=local_pref)
    return _gcf_dumps(result)


# ── OSPF tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def ospf_get_neighbors() -> str:
    """List OSPF neighbors with state, address, priority, and router ID."""
    await _ensure_init()
    if not _ospf_connector:
        return json.dumps({"error": "OSPF not configured. Set NETCLAW_OSPF_AREAS."})
    neighbors = await _ospf_connector.get_neighbors()
    return _gcf_dumps({"neighbors": neighbors, "count": len(neighbors)})


@mcp.tool()
async def ospf_get_lsdb() -> str:
    """Query the OSPF Link State Database (LSDB)."""
    await _ensure_init()
    if not _ospf_connector:
        return json.dumps({"error": "OSPF not configured. Set NETCLAW_OSPF_AREAS."})
    lsas = await _ospf_connector.get_lsdb()
    return _gcf_dumps({"lsdb": lsas, "count": len(lsas)})


@mcp.tool()
async def ospf_adjust_cost(interface: str, cost: int) -> str:
    """Change the OSPF cost on an interface.

    Args:
        interface: Interface name (e.g. 'gre-netclaw')
        cost: New OSPF cost (1-65535)
    """
    await _ensure_init()
    if not _ospf_connector:
        return json.dumps({"error": "OSPF not configured."})
    result = await _ospf_connector.adjust_interface_cost(cost=cost)
    result["interface"] = interface
    return _gcf_dumps(result)


# ── GRE tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def gre_tunnel_status() -> str:
    """Check GRE tunnel status via system commands (ip tunnel show, ip addr show)."""
    tunnels = []
    try:
        # ip tunnel show
        result = subprocess.run(
            ["ip", "tunnel", "show"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            if "gre" in line.lower():
                tunnels.append(line.strip())

        # ip addr show for tunnel interfaces
        result2 = subprocess.run(
            ["ip", "-br", "addr", "show"],
            capture_output=True, text=True, timeout=5,
        )
        tunnel_addrs = []
        for line in result2.stdout.strip().splitlines():
            if "gre" in line.lower():
                tunnel_addrs.append(line.strip())

    except Exception as exc:
        return json.dumps({"error": str(exc)})

    return _gcf_dumps(
        {"tunnels": tunnels, "addresses": tunnel_addrs, "count": len(tunnels)},
    )


# ── Meta tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def protocol_summary() -> str:
    """Consolidated BGP + OSPF + GRE state summary."""
    await _ensure_init()
    summary = {
        "router_id": ROUTER_ID,
        "local_as": LOCAL_AS,
        "lab_mode": LAB_MODE,
        "bgp": None,
        "ospf": None,
        "gre": None,
    }

    # BGP
    if _bgp_connector:
        try:
            peers = await _bgp_connector.get_peers()
            rib = await _bgp_connector.get_rib()
            summary["bgp"] = {
                "configured": True,
                "peer_count": len(peers),
                "peers": peers,
                "rib_size": len(rib),
            }
        except Exception as exc:
            summary["bgp"] = {"configured": True, "error": str(exc)}
    else:
        summary["bgp"] = {"configured": False}

    # OSPF
    if _ospf_connector:
        try:
            neighbors = await _ospf_connector.get_neighbors()
            summary["ospf"] = {
                "configured": True,
                "neighbor_count": len(neighbors),
                "neighbors": neighbors,
            }
        except Exception as exc:
            summary["ospf"] = {"configured": True, "error": str(exc)}
    else:
        summary["ospf"] = {"configured": False}

    # GRE (always available via system commands)
    try:
        gre_raw = await gre_tunnel_status()
        summary["gre"] = json.loads(gre_raw)
    except Exception as exc:
        summary["gre"] = {"error": str(exc)}

    return _gcf_dumps(summary)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
