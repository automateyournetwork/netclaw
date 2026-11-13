"""Read-only GreyNoise Community IPv4 lookup over MCP stdio."""
import ipaddress
import math
import os

import httpx
from fastmcp import FastMCP

mcp = FastMCP("greynoise-community")


@mcp.tool()
def greynoise_community_lookup(ip: str) -> dict:
    """Look up a public IPv4 address in GreyNoise Community to identify observed scanning and known business services."""
    try:
        address = ipaddress.IPv4Address(ip.strip())
    except ValueError:
        return {"error": "Provide a publicly routable IPv4 address."}
    if not address.is_global or address.is_multicast:
        return {"error": "Provide a publicly routable IPv4 address."}

    ip = str(address)
    try:
        timeout = float(os.getenv("GREYNOISE_TIMEOUT") or "10")
        if not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError
    except ValueError:
        return {"ip": ip, "error": "GREYNOISE_TIMEOUT must be greater than 0 and at most 60 seconds."}
    headers = {"accept": "application/json"}
    key = os.getenv("GREYNOISE_API_KEY", "").strip()
    if key:
        headers["key"] = key
    try:
        response = httpx.get(f"https://api.greynoise.io/v3/community/{ip}", headers=headers, timeout=timeout)
    except httpx.HTTPError:
        return {"ip": ip, "error": "GreyNoise Community request failed."}
    if response.status_code == 404:
        return {"ip": ip, "noise": False, "riot": False, "classification": "unknown",
                "name": "unknown", "message": "IP not observed by GreyNoise"}
    if response.status_code == 429:
        return {"ip": ip, "error": "GreyNoise Community rate limit reached."}
    if response.status_code != 200:
        return {"ip": ip, "error": f"GreyNoise Community returned HTTP {response.status_code}."}
    try:
        result = response.json()
    except ValueError:
        result = None
    if not isinstance(result, dict):
        return {"ip": ip, "error": "GreyNoise Community returned an invalid response."}
    return {field: result[field] for field in ("ip", "noise", "riot", "classification", "name", "link", "last_seen", "message")
            if field in result}


if __name__ == "__main__":
    mcp.run()
