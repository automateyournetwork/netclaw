"""Device-plane distinctions. Spec 080 + spec 082 completion, FR-015/FR-016/FR-018.

No appliance. Two conflations are tested here, both of which shipped in spec 080's
first version and were found by the running system rather than by these tests:

  1. admin status vs link state  — an admin-down interface with a live carrier
     reads as healthy if you only read the monitor endpoint.
  2. VPN phase 1 vs phase 2      — collapsing them hides the most common IPsec
     fault, where IKE is up and no traffic passes.

Deliberately NOT verified live: setting a real interface administratively down.
`port1` is the management path on the lab unit, and disabling it to prove a test
would cost access to the device. The stub proves the logic; the live run proves
the field mapping.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "fortinet-mcp"))

_AUDIT = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
os.environ["FORTINET_AUDIT_LOG"] = _AUDIT.name

from planes import device  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


class StubClient:
    """Minimal FortiOSClient stand-in returning canned payloads per path."""

    def __init__(self, payloads: dict, fail: set[str] | None = None) -> None:
        self._payloads = payloads
        self._fail = fail or set()
        self.source = "stub-fortigate"
        self.device_name = "STUBSERIAL01"

    async def resolve_identity(self) -> str:
        return self.device_name

    async def get(self, path, vdom=None, **kw):
        if path in self._fail:
            from transport.rest import RestError
            raise RestError(f"stub failure for {path}")
        return self._payloads.get(path)

    async def get_envelope(self, path, vdom=None, **kw):
        return {"results": self._payloads.get(path), "serial": "STUBSERIAL01",
                "version": "v7.6.7", "build": 3704}


def test_admin_down_is_not_link_down() -> None:
    """The conflation NetClaw itself reported. An interface enabled in config with
    no carrier, and one DISABLED in config with a live carrier, must be
    distinguishable — the second is the dangerous one, because monitor alone
    reports it as up."""
    c = StubClient({
        "monitor/system/interface": {
            "port1": {"name": "port1", "link": True, "ip": "10.1.1.1", "mask": 24},
            "port2": {"name": "port2", "link": True, "ip": "10.2.2.1", "mask": 24},
            "port3": {"name": "port3", "link": False, "ip": "0.0.0.0", "mask": 0},
        },
        "cmdb/system/interface": [
            {"name": "port1", "status": "up", "role": "wan", "type": "physical"},
            # The trap: administratively DISABLED but the carrier is live.
            {"name": "port2", "status": "down", "role": "lan", "type": "physical"},
            {"name": "port3", "status": "up", "role": "lan", "type": "physical"},
        ],
    })
    r = asyncio.run(device.list_interfaces(c))
    by = {i["name"]: i for i in r["data"]["interfaces"]}

    check("admin-up + link-up reads healthy",
          by["port1"]["admin_status"] == "up" and by["port1"]["link"] is True)
    check("admin-DOWN with live carrier is reported admin_status=down",
          by["port2"]["admin_status"] == "down",
          f"got {by['port2']['admin_status']!r} — this interface passes no traffic")
    check("that interface still shows link=True (why monitor alone misleads)",
          by["port2"]["link"] is True)
    check("admin-up + link-down is flagged",
          by["port3"]["admin_up_link_down"] is True)
    check("admin-down interfaces are named in notes",
          any("port2" in n for n in r["notes"]), str(r["notes"])[:120])
    check("role is populated from config", by["port1"]["role"] == "wan")


def test_missing_config_does_not_imply_enabled() -> None:
    """If the config read fails, admin status is UNKNOWN — never assumed up.
    Assuming enabled would recreate the exact conflation, silently."""
    c = StubClient(
        {"monitor/system/interface": {"port1": {"name": "port1", "link": True}}},
        fail={"cmdb/system/interface"},
    )
    r = asyncio.run(device.list_interfaces(c))
    i = r["data"]["interfaces"][0]
    check("admin_status is None, not 'up'", i["admin_status"] is None, repr(i["admin_status"]))
    check("notes say admin status is unknown, not assumed",
          any("NOT assumed enabled" in n for n in r["notes"]), str(r["notes"])[:140])


def test_vpn_phases_reported_separately() -> None:
    """FR-016. A tunnel with phase 1 up and phase 2 down is neither up nor down —
    it is a selector/proxy-ID mismatch, and collapsing the two hides it."""
    c = StubClient({
        "monitor/vpn/ipsec": [
            {"name": "to-branch", "rgwy": "203.0.113.9", "lgwy": "198.51.100.2",
             "connection_count": 1, "proxyid_num": 1,
             "proxyid": [{"p2name": "sel-1", "status": "down",
                          "proxy_src": [], "proxy_dst": []}]},
        ],
    })
    r = asyncio.run(device.vpn_tunnels(c))
    t = r["data"]["tunnels"][0]
    check("phase1 and phase2 are separate fields",
          "phase1_status" in t and "phase2_status" in t)
    check("phase1 up while phase2 down is representable",
          t["phase1_status"] == "up" and t["phase2_status"] == "down",
          f"p1={t['phase1_status']} p2={t['phase2_status']}")
    check("per-selector detail is preserved", len(t["phase2_selectors"]) == 1)
    check("no single collapsed 'status' field exists", "status" not in t, str(list(t)))


def test_no_tunnels_is_none_defined_not_all_down() -> None:
    c = StubClient({"monitor/vpn/ipsec": []})
    r = asyncio.run(device.vpn_tunnels(c))
    joined = " ".join(r["notes"]).lower()
    check("empty tunnel list is 'none defined'", "none defined" in joined, joined[:100])
    check("and explicitly not 'all down'", "not 'all down'" in joined or "not all down" in joined)


def main() -> int:
    print("device-plane distinction tests (no appliance required)")
    for fn in (
        test_admin_down_is_not_link_down,
        test_missing_config_does_not_imply_enabled,
        test_vpn_phases_reported_separately,
        test_no_tunnels_is_none_defined_not_all_down,
    ):
        print(f"\n{fn.__name__}")
        fn()
    os.unlink(_AUDIT.name)
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all device-plane distinction tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
