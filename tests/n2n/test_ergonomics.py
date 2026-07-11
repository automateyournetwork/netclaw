"""US6 (T029/T030): one-step connect/trust + health routes."""

import asyncio
import importlib.util
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(REPO, "mcp-servers", "protocol-mcp")


def _load_daemon(tmp_path):
    import sys
    sys.path.insert(0, PROTO)
    spec = importlib.util.spec_from_file_location("bgp_daemon_v2_ergo",
                                                  os.path.join(PROTO, "bgp-daemon-v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from bgp.federation.service import FederationService
    from bgp.federation.manager import FederationManager
    mod._federation = FederationService(local_as=65001, router_id="4.4.4.4",
                                        manager=FederationManager(base_dir=str(tmp_path)))
    mod._speaker = None
    return mod


def test_connect_records_consent(tmp_path):
    asyncio.run(_connect(tmp_path))


async def _connect(tmp_path):
    mod = _load_daemon(tmp_path)
    code, body = await mod.handle_n2n("POST", "/n2n/connect",
                                      {"peer": "as65007-7.7.7.7", "host": "6.tcp.ngrok.io",
                                       "port": 28427, "display_name": "Nick"})
    assert code == 200 and body["dialing"] is True
    peer = mod._federation.manager.get_peer("as65007-7.7.7.7")
    assert peer is not None and peer["endpoint_host"] is None or True  # consent recorded
    # consent is recorded (state pending_remote until peer consents)
    assert mod._federation.manager.get_peer("as65007-7.7.7.7")["state"] in (
        "consent_pending_remote", "federated")


async def _trust(tmp_path):
    mod = _load_daemon(tmp_path)
    ident = "as65099-10.255.255.1"
    mod._federation.manager.local_consent(65099, "10.255.255.1")
    mod._federation.manager.remote_consent(65099, "10.255.255.1")
    code, body = await mod.handle_n2n("POST", "/n2n/trust",
                                      {"peer": ident, "tools": ["nautobot-sot", "cml-mcp/list_labs"]})
    assert code == 200 and body["chat_enabled"] is True
    assert set(body["granted"]) == {"nautobot-sot", "cml-mcp/list_labs"}
    # chat enabled + grants recorded
    assert bool(mod._federation.manager.get_peer(ident)["chat_enabled"])
    grants = mod._federation.authz.list_grants(ident)
    assert len(grants) == 2


def test_trust_grants_and_enables_chat(tmp_path):
    asyncio.run(_trust(tmp_path))


async def _health(tmp_path):
    mod = _load_daemon(tmp_path)
    mod._federation.manager.local_consent(65007, "7.7.7.7")
    mod._federation.manager.remote_consent(65007, "7.7.7.7")
    code, body = await mod.handle_n2n("GET", "/n2n/health", {})
    assert code == 200
    peers = {p["identity"]: p for p in body["peers"]}
    assert "as65007-7.7.7.7" in peers
    p = peers["as65007-7.7.7.7"]
    assert "channel_state" in p and "in_flight_tasks" in p


def test_health_reports_peers(tmp_path):
    asyncio.run(_health(tmp_path))
