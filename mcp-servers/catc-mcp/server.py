"""catc-mcp — Catalyst Center, read-only, all 514 GET operations behind 8 dispatchers.

Spec 087. NetClaw adopts Cisco's OFFICIAL TOOL CATALOGUE (cisco-en-programmability/
catc-mcp-oss, Apache-2.0, release/2.3.7.11) but NOT its runtime. Their 515 generated
definitions carry uri + method + parameterLocation for every operation; that catalogue is
the valuable artifact. Using it with a thin client avoids three hazards at once: the
container, the port-7001 HTTP transport, and an unbounded `fastmcp>=2.0.0` that resolves
to 3.x against five servers pinning <3.

WHY DISPATCHERS. Inlining all 515 tool definitions measures 64,420 tokens — 12.9x the
5,000-token ceiling. Curating to ~15 would cover 3% of the API. Eight grouped dispatchers
reach ALL 514 read-only operations for a fraction of the budget. Same pattern spec 083
adopted for Zabbix, but here NetClaw owns the facade, so provenance is stamped at a
chokepoint rather than left to the caller.

THE DISTINCTION THIS PROTECTS. An empty inventory is not an empty network. Zero devices
means *this controller manages none* — discovery may not have run, RBAC may scope the
account, or you may be talking to the wrong appliance. That last one is not hypothetical:
sandboxdnac2.cisco.com and sandboxdnac.cisco.com share credentials and the first has zero
devices. Every response therefore carries which appliance answered and when it observed
the data.

And "Catalyst Center says unreachable" is not "the device is down" — it is one
controller's last poll.
"""
from __future__ import annotations

import json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("catc-mcp")
CATALOG = Path(__file__).resolve().parent / "catalog"
GROUPS = ["devices", "sites", "wireless", "health", "compliance", "software", "events", "other"]
_TOKEN: dict[str, Any] = {"value": None, "acquired": 0.0}
TOKEN_TTL = 3000  # Catalyst Center tokens are time-limited; refresh well inside it


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _host() -> str:
    return (os.environ.get("CATALYST_CENTER_HOST") or "").rstrip("/")


def _ops(group: str) -> dict[str, dict]:
    p = CATALOG / f"{group}.json"
    if not p.is_file():
        return {}
    return {o["name"]: o for o in json.load(open(p, encoding="utf-8"))}


def _all_ops() -> dict[str, tuple[str, dict]]:
    out = {}
    for g in GROUPS:
        for n, o in _ops(g).items():
            out[n] = (g, o)
    return out


def _envelope(outcome: str, group: str, operation: str, data: Any = None,
              message: str | None = None, caveats: list[str] | None = None) -> dict:
    """The chokepoint. Nothing returns without the appliance identity and the time.

    `observed_at` is deliberately named for what it is — when THIS CONTROLLER was asked,
    not when the network was in this state. Catalyst Center is a database of what it last
    learned; a device can be listed and long dead, or absent and perfectly healthy.
    """
    env = {
        "source": "catalyst-center",
        "appliance": _host() or "(unset)",
        "observed_at": _utc(),
        "outcome": outcome,
        "group": group,
        "operation": operation,
        "caveats": list(caveats or []),
    }
    if data is not None:
        env["data"] = data
    if message:
        env["message"] = message
    return env


def _refused(group: str, operation: str, reason: str, outcome: str = "refused") -> dict:
    return _envelope(outcome, group, operation, message=reason)


class AuthRejected(Exception):
    """The appliance rejected the credentials.

    A distinct type on purpose. httpx.HTTPStatusError subclasses httpx.HTTPError, so a 401
    on the token endpoint would otherwise be caught by the transport handler and reported
    as `unreachable` — collapsing "credentials rejected" into "could not be reached". Those
    are different facts, and conflating them is the exact failure this server exists to
    prevent. Caught by tests/catc/test_live_catc.py.
    """


def _token(client: httpx.Client) -> str | None:
    if _TOKEN["value"] and (time.time() - _TOKEN["acquired"]) < TOKEN_TTL:
        return _TOKEN["value"]
    u, p = os.environ.get("CATALYST_CENTER_USERNAME"), os.environ.get("CATALYST_CENTER_PASSWORD")
    if not (_host() and u and p):
        return None
    r = client.post(f"{_host()}/dna/system/api/v1/auth/token", auth=(u, p), timeout=45.0)
    if r.status_code in (401, 403):
        raise AuthRejected(f"HTTP {r.status_code} from the token endpoint")
    r.raise_for_status()
    tok = r.json().get("Token")
    _TOKEN.update(value=tok, acquired=time.time())
    return tok


def _call(group: str, operation: str, params: dict | None) -> dict:
    """One path to the appliance. Every outcome is typed; none is a bare empty list."""
    ops = _ops(group)
    if operation not in ops:
        near = [n for n in ops if operation.lower() in n.lower()][:5]
        return _refused(group, operation,
                        f"No such read-only operation in group '{group}'. "
                        f"{'Did you mean: ' + ', '.join(near) + '. ' if near else ''}"
                        f"Use catc_find to search all {sum(len(_ops(g)) for g in GROUPS)} operations.")
    if not _host():
        return _refused(group, operation, "CATALYST_CENTER_HOST is not set — no appliance "
                        "is configured. This is not a statement about any network.",
                        "not_configured")
    spec = ops[operation]
    uri = spec["uri"]
    verify = (os.environ.get("CATALYST_CENTER_VERIFY_SSL", "true").lower() == "true")
    caveats = []
    if not verify:
        caveats.append("TLS verification is DISABLED for this appliance.")

    # Path parameters are substituted; everything else becomes a query parameter.
    supplied = dict(params or {})
    for k, v in list(supplied.items()):
        if "{" + k + "}" in uri:
            uri = uri.replace("{" + k + "}", str(v))
            supplied.pop(k)
    if "{" in uri:
        missing = [s.split("}")[0] for s in uri.split("{")[1:]]
        return _refused(group, operation,
                        f"Missing required path parameter(s): {', '.join(missing)}. "
                        f"Call catc_describe_operation('{operation}') for the schema.")

    try:
        with httpx.Client(verify=verify, timeout=60.0) as client:
            tok = _token(client)
            if not tok:
                return _refused(group, operation,
                                "Could not obtain a Catalyst Center token — credentials are "
                                "missing or rejected. THIS IS NOT AN EMPTY RESULT: the "
                                "controller's state is unknown.", "auth_failed")
            r = client.get(f"{_host()}{uri}", headers={"X-Auth-Token": tok}, params=supplied)
    except AuthRejected as exc:
        _TOKEN.update(value=None, acquired=0.0)
        return _refused(group, operation,
                        f"Catalyst Center at {_host()} rejected the credentials ({exc}). "
                        f"The controller's state is UNKNOWN, not empty.", "auth_failed")
    except httpx.HTTPError as exc:
        return _refused(group, operation,
                        f"Catalyst Center at {_host()} could not be reached: {exc}. "
                        f"THIS IS NOT AN EMPTY RESULT.", "unreachable")

    if r.status_code == 401:
        _TOKEN.update(value=None, acquired=0.0)
        return _refused(group, operation, "Catalyst Center rejected the token (401). The "
                        "controller's state is unknown, not empty.", "auth_failed")
    if r.status_code == 403:
        return _refused(group, operation,
                        "Catalyst Center returned 403 — this account's RBAC does not permit "
                        "this operation. An answer you did get from a related call may be "
                        "SCOPED, not complete.", "forbidden")
    if r.status_code >= 400:
        return _refused(group, operation, f"Catalyst Center returned HTTP {r.status_code}: "
                        f"{r.text[:200]}", "error")

    try:
        payload = r.json()
    except ValueError:
        return _refused(group, operation, "Response was not JSON.", "error")

    body = payload.get("response", payload) if isinstance(payload, dict) else payload
    outcome = "ok"

    # A ZERO COUNT is the same absence as an empty list, and reads even more like data.
    # Found by live testing: getDeviceConfigCount returned a bare 0 on the empty appliance
    # and 4 on the populated one, and the empty-list branch below never fired. A scalar 0
    # presented without a caveat is exactly the failure this server exists to prevent.
    _zero = (body == 0) or (isinstance(body, dict) and set(body) == {"count"} and not body["count"])
    if _zero:
        outcome = "empty"
        caveats.append(
            "ZERO COUNT. This controller counted no matching records — NOT that the network "
            "has none. The same causes apply as for an empty list: discovery may not have "
            f"run, RBAC may scope this account, or this may be the wrong appliance ({_host()})."
        )
    elif isinstance(body, list) and not body:
        outcome = "empty"
        caveats.append(
            "EMPTY RESULT. This means this controller returned no records — NOT that the "
            "network has none. Distinguish: discovery may not have run; this account's RBAC "
            "may scope results; a filter may have excluded everything; or this may be the "
            f"wrong appliance ({_host()}). Do not report an absence as a network fact."
        )
    elif isinstance(body, list):
        caveats.append(f"{len(body)} record(s) as last known to this controller. Catalyst "
                       "Center reports what it last learned, not live device state.")
    return _envelope(outcome, group, operation, data=body, caveats=caveats)


def _mk(group: str, blurb: str):
    async def tool(operation: str, params: dict | None = None) -> dict:
        return _call(group, operation, params)
    tool.__name__ = f"catc_{group}"
    tool.__doc__ = (
        f"{blurb}\n\n"
        f"Read-only Catalyst Center operations in the '{group}' group "
        f"({len(_ops(group))} available). Pass `operation` (the operation name) and "
        f"`params`.\n\n"
        f"Discover names with catc_find('<keyword>'); get a parameter schema with "
        f"catc_describe_operation('<name>').\n\n"
        f"Every response states which appliance answered and when. An EMPTY result means "
        f"this controller returned no records — never that the network has none."
    )
    return tool


BLURBS = {
    "devices":    "Device inventory, interfaces, discovery and onboarding.",
    "sites":      "Site hierarchy, buildings, floors, IPAM and per-site profiles.",
    "wireless":   "Wireless controllers, settings, profiles, RF and access points.",
    "health":     "Assurance — device and client health, issues, trends, analytics.",
    "compliance": "Compliance state, security advisories, field notices, network bugs.",
    "software":   "Software images, golden images and update state.",
    "events":     "Events, tasks, executions, webhooks and notification config.",
    "other":      "Everything else in the catalogue — fabric, templates, policy, licensing, energy.",
}
for _g in GROUPS:
    mcp.tool()(_mk(_g, BLURBS[_g]))


@mcp.tool()
async def catc_find(query: str = "", group: str = "", limit: int = 40) -> dict:
    """Search all 514 read-only Catalyst Center operations by keyword or URI fragment.

    Start here. The full catalogue is far too large to carry in this tool list, so this is
    how you discover what exists. Returns operation names, their group, HTTP method and
    URI. Then call catc_describe_operation for a schema, and catc_<group> to execute.
    """
    q = (query or "").lower()
    hits = []
    for name, (g, o) in sorted(_all_ops().items()):
        if group and g != group:
            continue
        if q and q not in name.lower() and q not in o["uri"].lower() and q not in o.get("description", "").lower():
            continue
        hits.append({"operation": name, "group": g, "uri": o["uri"]})
    total = len(hits)
    env = _envelope("ok" if hits else "empty", group or "(all)", "catc_find",
                    data=hits[:limit])
    env["caveats"].append(f"{total} operation(s) matched; showing {min(total, limit)}. "
                          "This searches the LOCAL catalogue — it does not contact the appliance.")
    if not hits:
        env["caveats"].append("No operation matched. This is a catalogue miss, not an "
                              "empty network — try a broader keyword.")
    return env


@mcp.tool()
async def catc_describe_operation(operation: str) -> dict:
    """Full parameter schema for one Catalyst Center operation.

    Returns its group, HTTP method, URI, description and every parameter with where it
    goes (path or query). Call this before catc_<group> when unsure of arguments.
    """
    found = _all_ops().get(operation)
    if not found:
        near = [n for n in _all_ops() if operation.lower() in n.lower()][:5]
        return _refused("(all)", operation,
                        f"Unknown operation. {'Closest: ' + ', '.join(near) if near else ''} "
                        f"Use catc_find to search.")
    g, o = found
    return _envelope("ok", g, operation, data={
        "operation": operation, "group": g, "method": o["method"], "uri": o["uri"],
        "description": o.get("description", ""), "parameters": o.get("params", {}),
        "path_parameters": [s.split("}")[0] for s in o["uri"].split("{")[1:]],
    })


if __name__ == "__main__":
    mcp.run(transport="stdio")
