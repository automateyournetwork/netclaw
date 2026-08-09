"""Manager plane — FortiManager intent. Spec 080, FR-010..FR-014, FR-022.

This plane answers "what policy is *intended* across the estate". It is not
observed state. FortiManager's policy database and a FortiGate's running config
legitimately diverge between installs, and the gap between them is where drift,
unauthorised change and failed installs live.

Every tool here is read-only. The single write operation (`install_package`)
lives in `gates.py` behind two independent gates, because pushing a policy
package to production firewalls is the highest-blast-radius action in this
feature by a wide margin.
"""

from __future__ import annotations

from typing import Any

from envelope import Outcome, Plane, emit, unreachable
from transport.jsonrpc import JsonRpcClient, JsonRpcError


def _fail(client: JsonRpcClient, exc: JsonRpcError, tool: str) -> dict[str, Any]:
    if exc.outcome is Outcome.PLANE_UNREACHABLE:
        return unreachable(Plane.MANAGER, client.source, str(exc), tool=tool)
    return emit(Plane.MANAGER, source=client.source, outcome=exc.outcome,
                message=str(exc), tool=tool)


async def list_adoms(client: JsonRpcClient) -> dict[str, Any]:
    """Enumerate ADOMs. FR-010.

    The ADOM is the scope key for everything else on this plane — a policy
    package name is unique only *within* an ADOM, so a package named without one
    is ambiguous.
    """
    tool = "fmg_list_adoms"
    try:
        data = await client.call("get", "/dvmdb/adom")
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    adoms = [
        {"name": a.get("name"), "mode": a.get("mode"), "description": a.get("desc")}
        for a in (data or [])
    ]
    # Scope for this call is the manager itself; there is no single ADOM.
    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": "<all>"},
        data={"adoms": adoms, "count": len(adoms)},
        outcome=Outcome.OK if adoms else Outcome.EMPTY_RESULT, tool=tool,
    )


async def list_devices(client: JsonRpcClient, adom: str) -> dict[str, Any]:
    """Managed FortiGates within an ADOM, with install status. FR-010."""
    tool = "fmg_list_devices"
    try:
        data = await client.call("get", f"/dvmdb/adom/{adom}/device")
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    devices = [
        {
            "name": d.get("name"),
            "serial": d.get("sn"),
            "ip": d.get("ip"),
            "os_version": d.get("os_ver"),
            "connection_status": d.get("conn_status"),
            # Distinct from "the rules exist": a device can be known to the
            # manager and still be out of sync with its package.
            "db_status": d.get("db_status"),
        }
        for d in (data or [])
    ]
    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": adom},
        data={"devices": devices, "count": len(devices)},
        outcome=Outcome.OK if devices else Outcome.EMPTY_RESULT, tool=tool,
    )


async def list_policy_packages(client: JsonRpcClient, adom: str) -> dict[str, Any]:
    """Policy packages in an ADOM, with their install targets. FR-011."""
    tool = "fmg_list_policy_packages"
    try:
        data = await client.call("get", f"/pm/pkg/adom/{adom}")
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    packages = [
        {
            "name": p.get("name"),
            "type": p.get("type"),
            "install_targets": [
                t.get("name") for t in (p.get("scope member") or []) if isinstance(t, dict)
            ],
        }
        for p in (data or [])
    ]
    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": adom},
        data={"packages": packages, "count": len(packages)},
        outcome=Outcome.OK if packages else Outcome.EMPTY_RESULT, tool=tool,
    )


async def get_policy_package(client: JsonRpcClient, adom: str, package: str) -> dict[str, Any]:
    """Ordered rules in a package. FR-011.

    Position is reported because shadowing is positional — a rule's meaning
    depends on what precedes it. Disabled rules are included: a disabled rule is
    not an absent rule, and omitting them would hide intent.
    """
    tool = "fmg_get_policy_package"
    try:
        data = await client.call("get", f"/pm/config/adom/{adom}/pkg/{package}/firewall/policy")
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    rules = [
        {
            "policyid": r.get("policyid"),
            "position": idx,
            "name": r.get("name"),
            "action": r.get("action"),
            "status": r.get("status"),
            "srcintf": r.get("srcintf"),
            "dstintf": r.get("dstintf"),
            "srcaddr": r.get("srcaddr"),
            "dstaddr": r.get("dstaddr"),
            "service": r.get("service"),
            "comments": r.get("comments"),
        }
        for idx, r in enumerate(data or [])
    ]
    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": adom, "package": package},
        data={"rules": rules, "count": len(rules)},
        outcome=Outcome.OK if rules else Outcome.EMPTY_RESULT,
        notes=["Object references are names; resolve them with fmg_resolve_object "
               "before treating this as an audit (FR-013)."],
        tool=tool,
    )


async def search_rules(
    client: JsonRpcClient, adom: str, package: str,
    src: str | None = None, dst: str | None = None,
    service: str | None = None, obj: str | None = None,
) -> dict[str, Any]:
    """Find rules referencing a source, destination, service or object. FR-012."""
    tool = "fmg_search_rules"
    try:
        data = await client.call("get", f"/pm/config/adom/{adom}/pkg/{package}/firewall/policy")
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    def refs(field: Any) -> list[str]:
        if isinstance(field, list):
            return [str(x) for x in field]
        return [str(field)] if field else []

    matches = []
    for idx, r in enumerate(data or []):
        hay = {
            "src": refs(r.get("srcaddr")),
            "dst": refs(r.get("dstaddr")),
            "service": refs(r.get("service")),
        }
        hit = (
            (src and src in hay["src"])
            or (dst and dst in hay["dst"])
            or (service and service in hay["service"])
            or (obj and any(obj in v for v in hay.values()))
        )
        if hit:
            matches.append(
                {
                    "policyid": r.get("policyid"), "position": idx,
                    "name": r.get("name"), "action": r.get("action"),
                    "status": r.get("status"), **hay,
                }
            )

    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": adom, "package": package},
        data={"matches": matches, "count": len(matches),
              "criteria": {"src": src, "dst": dst, "service": service, "object": obj}},
        outcome=Outcome.OK if matches else Outcome.EMPTY_RESULT, tool=tool,
    )


async def resolve_object(
    client: JsonRpcClient, adom: str, name: str, obj_type: str = "address"
) -> dict[str, Any]:
    """Resolve an object to its members, **recursively**. FR-013.

    A rule reported with unresolved object names is not an audit — "allow
    GRP_CORP to GRP_DMZ" tells you nothing about which addresses that permits.
    Groups are expanded transitively: a nested group resolved one level deep is
    still unresolved.
    """
    tool = "fmg_resolve_object"
    base = f"/pm/config/adom/{adom}/obj/firewall"
    seen: set[str] = set()

    async def expand(obj_name: str, depth: int = 0) -> dict[str, Any]:
        if obj_name in seen or depth > 10:  # cycle guard; FortiManager permits them
            return {"name": obj_name, "cycle_or_depth_limit": True}
        seen.add(obj_name)

        for kind in (f"{obj_type}grp", obj_type):
            try:
                data = await client.call("get", f"{base}/{kind}/{obj_name}")
            except JsonRpcError:
                continue
            if not data:
                continue
            entry = data[0] if isinstance(data, list) else data
            members = entry.get("member")
            if members:
                return {
                    "name": obj_name, "type": kind,
                    "members": [
                        await expand(m if isinstance(m, str) else m.get("name"), depth + 1)
                        for m in members
                    ],
                }
            return {
                "name": obj_name, "type": kind,
                "value": entry.get("subnet") or entry.get("fqdn")
                or entry.get("start-ip") or entry.get("tcp-portrange"),
            }
        return {"name": obj_name, "unresolved": True}

    try:
        resolved = await expand(name)
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": adom},
        data={"object": resolved}, tool=tool,
    )


async def get_revisions(client: JsonRpcClient, adom: str, package: str) -> dict[str, Any]:
    """Revision history — the rollback context a change review needs. FR-014.

    A gated install identifies its rollback revision *before* applying, not after
    failing (FR-021, Principle II).
    """
    tool = "fmg_get_revisions"
    try:
        data = await client.call("get", f"/dvmdb/adom/{adom}/revision")
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    revisions = [
        {"version": r.get("version"), "created": r.get("created_time"),
         "created_by": r.get("created_by"), "comments": r.get("desc")}
        for r in (data or [])
    ]
    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": adom, "package": package},
        data={"revisions": revisions, "count": len(revisions)},
        outcome=Outcome.OK if revisions else Outcome.EMPTY_RESULT, tool=tool,
    )


async def preview_install(
    client: JsonRpcClient, adom: str, package: str, target: str | None = None
) -> dict[str, Any]:
    """What an install *would* change. FR-022.

    Read-only and **requires neither gate**, because it changes nothing. Named
    `preview` and never `install` so the distinction survives autocomplete.
    """
    tool = "fmg_preview_install"
    params: dict[str, Any] = {"adom": adom, "pkg": package}
    if target:
        params["scope"] = [{"name": target}]
    try:
        data = await client.call("exec", "/securityconsole/install/preview", **params)
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": adom, "package": package},
        data={"preview": data, "target": target},
        notes=["Preview only — nothing was changed and no gate was required."],
        tool=tool,
    )
