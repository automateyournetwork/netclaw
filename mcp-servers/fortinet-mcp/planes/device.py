"""Device plane — FortiGate observed state. Spec 080, FR-015..FR-018.

This plane answers "what is this box doing *right now*". It is not FortiManager's
intent, and the difference matters: a rule running on a FortiGate that is absent
from its policy package is an out-of-band change, and only comparing the two
surfaces it (FR-008).

Response shapes below were captured from a live FortiGate-VM running **FortiOS
7.6.7** on 2026-08-01, not inferred from documentation:

  monitor/system/interface -> results is a DICT KEYED BY INTERFACE NAME
  monitor/router/ipv4      -> results is a LIST
  monitor/vpn/ipsec        -> results is a LIST (empty when no tunnels exist)
  monitor/system/ha-peer   -> results is a LIST (empty when standalone)

The interface endpoint returning a dict rather than a list is the kind of thing
that is wrong in every third-party example and right only when measured.
"""

from __future__ import annotations

from typing import Any

from envelope import Outcome, Plane, emit, unreachable
from transport.rest import FortiOSClient, RestError

DEFAULT_VDOM = "root"


def _scope(client: FortiOSClient, vdom: str | None, device: str | None = None) -> dict[str, str]:
    """Device-plane scope: the device and the VDOM (FR-009/FR-018).

    A figure without its VDOM is ambiguous on a multi-VDOM unit, so both are
    mandatory rather than decorative. `client.device_name` resolves to the unit
    hostname so every tool reports the SAME identifier — scope that varies
    between tools cannot be correlated and is therefore worthless.
    """
    return {"device": device or client.device_name, "vdom": vdom or DEFAULT_VDOM}


async def system_status(client: FortiOSClient, vdom: str | None = None) -> dict[str, Any]:
    """Hostname, serial, version, and — per FR-017 — which HA member answered."""
    tool = "fgt_system_status"
    try:
        # get_envelope, NOT get: serial/version/build live at the TOP LEVEL of the
        # response, while hostname/model live inside `results`. Reading only
        # `results` reports the top-level fields as null — a real bug caught by a
        # live end-to-end run, not by any test written beforehand.
        body = await client.get_envelope("monitor/system/status", vdom=vdom)
        ha = await client.get("monitor/system/ha-peer", vdom=vdom)
        # cpu / memory / live session count. Measured: this endpoint carries
        # cpu, mem, disk, session, setuprate — but NOT uptime, which is not
        # exposed over REST on this build at all.
        try:
            usage = await client.get("monitor/system/resource/usage", vdom=vdom)
        except RestError:
            usage = None
    except RestError as exc:
        if exc.outcome is Outcome.PLANE_UNREACHABLE:
            return unreachable(Plane.DEVICE, client.source, str(exc), tool=tool)
        return emit(
            Plane.DEVICE, source=client.source, outcome=exc.outcome,
            message=str(exc), tool=tool,
        )

    results = body.get("results") or {}
    members = ha if isinstance(ha, list) else []

    def _current(metric: str) -> int | None:
        """Pull the `current` value out of a resource/usage metric.

        Shape: {"cpu": [{"current": 12, "historical": {...}}], ...} — a
        single-element list wrapping the live figure plus history we discard.
        """
        if not isinstance(usage, dict):
            return None
        entry = usage.get(metric)
        if isinstance(entry, list) and entry and isinstance(entry[0], dict):
            return entry[0].get("current")
        return None

    data = {
        "hostname": results.get("hostname"),
        # Top-level envelope fields — see the get_envelope comment above.
        "serial": body.get("serial"),
        "version": body.get("version"),
        "build": body.get("build"),
        "model": results.get("model_name"),
        "model_number": results.get("model_number"),
        "cpu_percent": _current("cpu"),
        "memory_percent": _current("mem"),
        # Live session count — asked for during testing and previously thought to
        # need raw CLI. It does not; it is here.
        "session_count": _current("session"),
        "log_disk": results.get("log_disk_status"),
        # FR-017: name the answering member. An HA figure that does not say which
        # unit produced it is not attributable.
        "ha_mode": "standalone" if not members else "cluster",
        "ha_members": [m.get("hostname") or m.get("serial") for m in members],
        "answering_member": results.get("hostname"),
    }

    notes = []
    if not members:
        notes.append("Standalone unit — no HA peers reported.")
    notes.append(
        "Uptime is not exposed over the FortiOS REST API on this build — it is "
        "CLI-only. Reported as absent rather than approximated."
    )
    # Licence state is NOT exposed on any REST endpoint an api-user can read; it
    # is CLI-only (`get system status`). Say so rather than letting a caller infer
    # licensing from circumstantial evidence like interface counts.
    notes.append(
        "Licence status is not available over REST — it is CLI-only. Do not infer "
        "it from interface/route/policy counts; check `get system status` on the box."
    )
    return emit(
        Plane.DEVICE, source=client.source, scope=_scope(client, vdom, results.get("hostname")),
        data=data, notes=notes, tool=tool,
    )


async def list_interfaces(client: FortiOSClient, vdom: str | None = None) -> dict[str, Any]:
    """Interfaces with **administrative and operational state reported separately**.

    FR-015/FR-018.

    ADMIN STATUS IS NOT LINK STATE, and conflating them was a real defect in the
    first version of this tool — found by NetClaw itself during live testing, which
    observed that only link state was exposed and said so unprompted.

        admin_status  from cmdb/system/interface  — is the interface ENABLED?
        link          from monitor/system/interface — is the carrier UP?

    An interface that is administratively **down** with a live carrier reports
    `link: true` and looks perfectly healthy if you only read the monitor endpoint.
    That is the same class of error as this feature's manager-vs-device distinction,
    one level down, and in our own code.

    `role` and `allowaccess` come from the same config read and matter for policy
    work: an interface's zone/role determines which rules can reference it.
    """
    tool = "fgt_list_interfaces"
    try:
        runtime = await client.get("monitor/system/interface", vdom=vdom)
        # Config read. If it fails we still report runtime state, but say that
        # admin status is unknown rather than implying the interface is enabled.
        try:
            config = await client.get("cmdb/system/interface", vdom=vdom)
        except RestError:
            config = None
    except RestError as exc:
        if exc.outcome is Outcome.PLANE_UNREACHABLE:
            return unreachable(Plane.DEVICE, client.source, str(exc), tool=tool)
        return emit(Plane.DEVICE, source=client.source, outcome=exc.outcome,
                    message=str(exc), tool=tool)

    # Measured: monitor returns a DICT KEYED BY INTERFACE NAME, cmdb returns a LIST.
    entries = runtime.values() if isinstance(runtime, dict) else (runtime or [])
    cfg_by_name = {
        c.get("name"): c for c in (config or []) if isinstance(c, dict) and c.get("name")
    }

    interfaces = []
    for i in entries:
        name = i.get("name")
        cfg = cfg_by_name.get(name) or {}
        admin = cfg.get("status")
        interfaces.append(
            {
                "name": name,
                "alias": i.get("alias") or cfg.get("alias") or None,
                # Administrative intent — is this interface enabled at all?
                "admin_status": admin,
                # Operational reality — is the carrier up?
                "link": i.get("link"),
                # The combination worth naming: enabled in config, no carrier.
                "admin_up_link_down": (admin == "up" and i.get("link") is False),
                "ip": i.get("ip"),
                "mask": i.get("mask"),
                "type": cfg.get("type"),
                "role": cfg.get("role"),
                "allowaccess": cfg.get("allowaccess"),
                "speed": i.get("speed"),
                "mac": i.get("mac"),
                "rx_errors": i.get("rx_errors"),
                "tx_errors": i.get("tx_errors"),
            }
        )

    notes = []
    if config is None:
        notes.append(
            "Interface configuration could not be read, so admin_status, role and "
            "allowaccess are unknown — NOT assumed enabled. Only operational link "
            "state is reported here."
        )
    else:
        notes.append(
            "admin_status is administrative intent (config); link is operational "
            "carrier state. An interface can be admin-down with link up, or "
            "admin-up with no carrier — they are different facts."
        )
    admin_down = [i["name"] for i in interfaces if i.get("admin_status") == "down"]
    if admin_down:
        notes.append(
            f"Administratively disabled: {', '.join(admin_down)}. These will not "
            "pass traffic regardless of link state."
        )

    return emit(
        Plane.DEVICE, source=client.source, scope=_scope(client, vdom),
        data={"interfaces": interfaces, "count": len(interfaces)},
        outcome=Outcome.OK if interfaces else Outcome.EMPTY_RESULT,
        notes=notes, tool=tool,
    )


async def get_routes(
    client: FortiOSClient, vdom: str | None = None, protocol: str | None = None
) -> dict[str, Any]:
    """Routing table as observed on the device (FR-015)."""
    tool = "fgt_get_routes"
    try:
        raw = await client.get("monitor/router/ipv4", vdom=vdom)
    except RestError as exc:
        if exc.outcome is Outcome.PLANE_UNREACHABLE:
            return unreachable(Plane.DEVICE, client.source, str(exc), tool=tool)
        return emit(Plane.DEVICE, source=client.source, outcome=exc.outcome,
                    message=str(exc), tool=tool)

    routes = [
        {
            "prefix": r.get("ip_mask"),
            "type": r.get("type"),
            "gateway": r.get("gateway"),
            "interface": r.get("interface"),
            "distance": r.get("distance"),
            "metric": r.get("metric"),
            "vrf": r.get("vrf"),
        }
        for r in (raw or [])
        if protocol is None or r.get("type") == protocol
    ]
    return emit(
        Plane.DEVICE, source=client.source, scope=_scope(client, vdom),
        data={"routes": routes, "count": len(routes)},
        outcome=Outcome.OK if routes else Outcome.EMPTY_RESULT,
        tool=tool,
    )


async def vpn_tunnels(client: FortiOSClient, vdom: str | None = None) -> dict[str, Any]:
    """IPsec tunnels with **phase 1 and phase 2 reported separately** (FR-016).

    This separation is the point of the tool. A tunnel with phase 1 up and
    phase 2 down is neither "up" nor "down" — it is a specific, common fault
    (usually a proxy-ID/selector mismatch), and collapsing the two into one
    status field destroys the only signal that distinguishes it.
    """
    tool = "fgt_vpn_tunnels"
    try:
        raw = await client.get("monitor/vpn/ipsec", vdom=vdom)
    except RestError as exc:
        if exc.outcome is Outcome.PLANE_UNREACHABLE:
            return unreachable(Plane.DEVICE, client.source, str(exc), tool=tool)
        return emit(Plane.DEVICE, source=client.source, outcome=exc.outcome,
                    message=str(exc), tool=tool)

    tunnels = []
    for t in (raw or []):
        p2_list = t.get("proxyid") or []
        tunnels.append(
            {
                "name": t.get("name"),
                "remote_gateway": t.get("rgwy"),
                "local_gateway": t.get("lgwy"),
                # Phase 1: the IKE SA. Present and up does NOT imply traffic flows.
                "phase1_status": "up" if t.get("proxyid_num", 0) >= 0 and t.get("connection_count", 0) > 0 else "down",
                "phase1_name": t.get("name"),
                # Phase 2: the IPsec SAs, one per selector pair. Reported per
                # selector because one down selector out of five is still a fault.
                "phase2_status": "up" if any(p.get("status") == "up" for p in p2_list) else "down",
                "phase2_selectors": [
                    {
                        "name": p.get("p2name"),
                        "status": p.get("status"),
                        "src": p.get("proxy_src"),
                        "dst": p.get("proxy_dst"),
                    }
                    for p in p2_list
                ],
            }
        )

    notes = []
    if not tunnels:
        notes.append(
            "No IPsec tunnels are configured on this device. This is 'none defined', "
            "not 'all down' — the two are different findings."
        )
    return emit(
        Plane.DEVICE, source=client.source, scope=_scope(client, vdom),
        data={"tunnels": tunnels, "count": len(tunnels)},
        outcome=Outcome.OK if tunnels else Outcome.EMPTY_RESULT,
        notes=notes, tool=tool,
    )


async def get_policies(client: FortiOSClient, vdom: str | None = None) -> dict[str, Any]:
    """Firewall policy **as running on the device** — the divergence input (FR-008).

    Deliberately reads `cmdb`, not `monitor`: this is the device's configured
    ruleset, which is what FortiManager's policy package is compared against.
    """
    tool = "fgt_get_policies"
    try:
        raw = await client.get("cmdb/firewall/policy", vdom=vdom)
    except RestError as exc:
        if exc.outcome is Outcome.PLANE_UNREACHABLE:
            return unreachable(Plane.DEVICE, client.source, str(exc), tool=tool)
        return emit(Plane.DEVICE, source=client.source, outcome=exc.outcome,
                    message=str(exc), tool=tool)

    def names(items: Any) -> list[str]:
        return [i.get("name") for i in (items or []) if isinstance(i, dict)]

    policies = [
        {
            "policyid": p.get("policyid"),
            "name": p.get("name"),
            "action": p.get("action"),
            # A disabled rule is not an absent rule — it is a rule someone chose
            # to keep. Reporting only enabled rules would hide intent.
            "status": p.get("status"),
            "srcintf": names(p.get("srcintf")),
            "dstintf": names(p.get("dstintf")),
            "srcaddr": names(p.get("srcaddr")),
            "dstaddr": names(p.get("dstaddr")),
            "service": names(p.get("service")),
        }
        for p in (raw or [])
    ]
    notes = []
    if not policies:
        notes.append(
            "No firewall policies configured. Note the evaluation licence caps "
            "this device at 3 policies, so a small ruleset here may be a lab "
            "limit rather than the estate's real posture."
        )
    return emit(
        Plane.DEVICE, source=client.source, scope=_scope(client, vdom),
        data={"policies": policies, "count": len(policies)},
        outcome=Outcome.OK if policies else Outcome.EMPTY_RESULT,
        notes=notes, tool=tool,
    )
