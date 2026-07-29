"""068 polish: GET /n2n/members omitted node_type entirely and computed
`live` only from `fed.member_channels` (agent members) — an edge (phone)
member's connection lives in `fed.edge_channels` instead, so every edge
node showed `live=false` forever regardless of real connection health, and
the HUD's own edge-node panel (which filters on `node_type == 'edge'`)
silently rendered nothing since 066 first shipped, since `node_type` was
never even in this response to filter on. Confirmed live against a real
production Border before this fix."""

import asyncio
import importlib.util
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(REPO, "mcp-servers", "protocol-mcp")


def _load_daemon(tmp_path):
    import sys
    sys.path.insert(0, PROTO)
    spec = importlib.util.spec_from_file_location(
        "bgp_daemon_v2_edge_liveness", os.path.join(PROTO, "bgp-daemon-v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from bgp.federation.service import FederationService
    from bgp.federation.manager import FederationManager
    mod._federation = FederationService(
        local_as=65001, router_id="4.4.4.4",
        manager=FederationManager(base_dir=str(tmp_path)))
    mod._federation.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    mod._speaker = None
    return mod


def test_connected_edge_member_reports_node_type_and_live(tmp_path):
    asyncio.run(_connected_edge_member(tmp_path))


async def _connected_edge_member(tmp_path):
    from bgp.federation import certs

    mod = _load_daemon(tmp_path)
    fed = mod._federation
    member_id = "risk/phone1"
    cert_pem, _ = certs.create_self_signed(member_id)
    token = fed.risk.issue_token(label="phone1")["token"]
    fed.risk.consume_token(token, member_id, cert_pem, scope=[],
                          transport_binding="edge-ws", node_type="edge")

    # Not connected yet -- live must be false, matching an agent member
    # with no channel.
    code, body = await mod.handle_n2n("GET", "/n2n/members", {})
    assert code == 200
    row = next(m for m in body["members"] if m["member_id"] == member_id)
    assert row["node_type"] == "edge"
    assert row["live"] is False

    # A connected edge node lives in edge_channels, never member_channels --
    # this is the exact distinction the bug missed.
    fed.edge_channels[member_id] = object()
    code, body = await mod.handle_n2n("GET", "/n2n/members", {})
    row = next(m for m in body["members"] if m["member_id"] == member_id)
    assert row["live"] is True

    # /n2n/members/health must agree.
    code, body = await mod.handle_n2n("GET", "/n2n/members/health", {})
    health_row = next(m for m in body["members"] if m["member_id"] == member_id)
    assert health_row["live"] is True
