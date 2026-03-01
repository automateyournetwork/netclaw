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

@mcp.tool()
async def bgp_get_peers() -> str:
    """List BGP peer sessions with state, AS, IP, uptime, and prefix counts."""
    await _ensure_init()
    if not _bgp_connector:
        return json.dumps({"error": "BGP not configured. Set NETCLAW_BGP_PEERS."})
    peers = await _bgp_connector.get_peers()
    return json.dumps({"peers": peers, "count": len(peers)}, indent=2)


@mcp.tool()
async def bgp_get_rib(prefix: Optional[str] = None) -> str:
    """Query the Loc-RIB. Optionally filter by prefix (e.g. '10.0.0.0/24')."""
    await _ensure_init()
    if not _bgp_connector:
        return json.dumps({"error": "BGP not configured. Set NETCLAW_BGP_PEERS."})
    routes = await _bgp_connector.get_rib(prefix=prefix)
    return json.dumps({"routes": routes, "count": len(routes)}, indent=2)


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
    return json.dumps(result, indent=2)


@mcp.tool()
async def bgp_withdraw_route(network: str) -> str:
    """Withdraw a route from the BGP RIB.

    Args:
        network: CIDR prefix to withdraw (e.g. '192.168.1.0/24')
    """
    await _ensure_init()
    if not _bgp_connector:
        return json.dumps({"error": "BGP not configured."})
    result = await _bgp_connector.withdraw_route(network=network)
    return json.dumps(result, indent=2)


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
    return json.dumps(result, indent=2)


# ── OSPF tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def ospf_get_neighbors() -> str:
    """List OSPF neighbors with state, address, priority, and router ID."""
    await _ensure_init()
    if not _ospf_connector:
        return json.dumps({"error": "OSPF not configured. Set NETCLAW_OSPF_AREAS."})
    neighbors = await _ospf_connector.get_neighbors()
    return json.dumps({"neighbors": neighbors, "count": len(neighbors)}, indent=2)


@mcp.tool()
async def ospf_get_lsdb() -> str:
    """Query the OSPF Link State Database (LSDB)."""
    await _ensure_init()
    if not _ospf_connector:
        return json.dumps({"error": "OSPF not configured. Set NETCLAW_OSPF_AREAS."})
    lsas = await _ospf_connector.get_lsdb()
    return json.dumps({"lsdb": lsas, "count": len(lsas)}, indent=2)


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
    return json.dumps(result, indent=2)


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

    return json.dumps(
        {"tunnels": tunnels, "addresses": tunnel_addrs, "count": len(tunnels)},
        indent=2,
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

    return json.dumps(summary, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
