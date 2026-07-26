#!/usr/bin/env python3
"""GreyNoise Community MCP server.

Wraps the free, unauthenticated GreyNoise Community API
(https://api.greynoise.io/v3/community/{ip}) as a single MCP tool. This answers
the highest-value question for perimeter/scan alerts — "is this IP benign
internet noise (a known scanner like Censys/Shodan) or something targeted?" —
without needing a GreyNoise Enterprise key.

The Community endpoint is rate-limited but free and requires no API key. If
GREYNOISE_API_KEY is present in the environment it is sent to raise the limit,
but it is not required.

One tool, one HTTP GET — deliberately tiny to keep the per-session tool-schema
footprint small (see docs/architecture/skill-context-scoping.md for why that
matters on context-limited models).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

COMMUNITY_URL = "https://api.greynoise.io/v3/community/{ip}"
TIMEOUT = float(os.environ.get("GREYNOISE_TIMEOUT", "10"))

mcp = FastMCP("greynoise-community")


@mcp.tool()
def greynoise_community_lookup(ip: str) -> dict:
    """Look up an IPv4/IPv6 address in the free GreyNoise Community dataset.

    Returns whether the IP is known internet "noise" (mass scanners), whether it
    belongs to a common business service (RIOT), a benign/malicious/unknown
    classification, and the actor/operator name when known (e.g. "Censys",
    "Shodan"). Use this on external source IPs in perimeter alerts (port scans,
    WAN blocks) to quickly separate routine background scanning from targeted
    activity.

    Args:
        ip: The IP address to look up (e.g. "66.132.172.181").

    Returns:
        A dict with keys: ip, noise, riot, classification, name, link,
        last_seen, message. On a miss the API returns
        classification "unknown"/message "IP not observed". On error a dict with
        an "error" key is returned instead of raising.
    """
    ip = (ip or "").strip()
    if not ip:
        return {"error": "no IP provided"}

    headers = {"accept": "application/json"}
    key = os.environ.get("GREYNOISE_API_KEY", "").strip()
    if key:
        headers["key"] = key  # optional: raises the Community rate limit

    try:
        resp = httpx.get(
            COMMUNITY_URL.format(ip=ip), headers=headers, timeout=TIMEOUT
        )
    except httpx.HTTPError as e:
        return {"ip": ip, "error": f"request failed: {e}"}

    # 404 = IP not observed by GreyNoise (a valid, useful answer).
    if resp.status_code == 404:
        return {
            "ip": ip,
            "noise": False,
            "riot": False,
            "classification": "unknown",
            "name": "unknown",
            "message": "IP not observed by GreyNoise",
        }
    if resp.status_code == 429:
        return {"ip": ip, "error": "rate limited by GreyNoise Community API "
                                   "(set GREYNOISE_API_KEY to raise the limit)"}
    if resp.status_code != 200:
        return {"ip": ip, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

    try:
        return resp.json()
    except ValueError:
        return {"ip": ip, "error": "non-JSON response from GreyNoise"}


# Token-efficient tool results (GCF) for Convergence triage.
try:
    _src = Path(__file__).resolve().parents[2] / "src"
    if _src.is_dir() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))
    from netclaw_tokens.mcp_gcf import install_gcf_on_fastmcp
    install_gcf_on_fastmcp(mcp, label="greynoise-community-mcp")
except Exception:
    pass

if __name__ == "__main__":
    mcp.run()
