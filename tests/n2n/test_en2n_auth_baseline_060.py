"""eN2N possession-auth baseline (default, cert_mode OFF) — closes the forged-
handshake identity-spoof (CWE-290) reported by Josh/TunnelMind.

Reconciled design: the acceptor appends a single-use nonce to its handshake reply
and refuses every method except n2n/hello until the dialer signs that nonce with
the key for the cert it presents (risk.verify_possession). Two-tier admission:
  - keyless consented forger  → tier-0 "self-asserted": presence/inventory only;
    tools/call, tasks/submit, chat, endpoint_update all default-denied.
  - active forgery (cert it can't sign) → hard reject + close.
  - un-consented stranger → closed before any nonce (FR-003).

Loopback only; no real claw is contacted. cert_mode is OFF here (the default), so
this proves the baseline protects everyone without TLS.
"""

import asyncio

from bgp.constants import NCFED_MAGIC, IN2N_NONCE_SIZE
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation.risk import RiskManager
from bgp.federation.channel import FederationChannel, RpcError, read_handshake, build_handshake

FORGE_AS, FORGE_RID = 65007, "7.7.7.7"
FORGE_IDENT = f"as{FORGE_AS}-{FORGE_RID}"


def _acceptor(base):
    return FederationService(local_as=65001, router_id="4.4.4.4", display_name="B",
                             manager=FederationManager(base_dir=str(base)))


async def _serve(b):
    async def on_conn(reader, writer):
        assert await reader.readexactly(len(NCFED_MAGIC)) == NCFED_MAGIC
        peer_as, rid = await read_handshake(reader)
        await b.accept_channel(peer_as, rid, reader, writer)
    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def _dial(port, consume_nonce=True):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(build_handshake(FORGE_AS, FORGE_RID))
    await writer.drain()
    assert await reader.readexactly(len(NCFED_MAGIC)) == NCFED_MAGIC
    await read_handshake(reader)
    nonce = await reader.readexactly(IN2N_NONCE_SIZE) if consume_nonce else b""
    return reader, writer, nonce


def _chan(reader, writer, base):
    mgr = FederationManager(base_dir=str(base))
    return FederationChannel(reader, writer, local_identity="attacker", peer_as=FORGE_AS,
                             peer_router_id=FORGE_RID, manager=mgr, is_initiator=True,
                             handlers={}), mgr


async def _call(ch, method, params):
    try:
        return await ch.call(method, params, timeout=5.0)
    except Exception:
        return None


# --- keyless forger of a consented+granted identity: admitted, powerless ---

async def _tier0(tmp_path):
    b = _acceptor(tmp_path / "b")
    b.manager.local_consent(FORGE_AS, FORGE_RID)
    b.manager.remote_consent(FORGE_AS, FORGE_RID)
    b.invoker.authz.grant(FORGE_IDENT, "tool", "list_labs")
    b.invoker.authz.grant(FORGE_IDENT, "skill", "recon")
    reached = {}
    async def _fx(t, a): reached["tool"] = t; return {"ok": True}
    b.invoker._exec_tool_stdio = _fx
    server, port = await _serve(b)
    reader, writer, _n = await _dial(port)
    ch, mgr = _chan(reader, writer, tmp_path / "atk")
    await ch.start()
    hello_ok = await _call(ch, "n2n/hello", {"identity": FORGE_IDENT, "display_name": "x"})
    b.manager.set_chat_enabled(FORGE_IDENT, True)
    tool = await _call(ch, "n2n/tools/call", {"tool": "list_labs", "request_id": "r1", "arguments": {}})
    task = await _call(ch, "n2n/tasks/submit", {"skill": "recon", "input_text": "x", "request_id": "r2"})
    chat = await _call(ch, "n2n/chat/open", {})
    ep = await _call(ch, "n2n/endpoint_update", {"identity": FORGE_IDENT, "endpoint": "6.6.6.6:179"})
    att = getattr(b.channels.get(FORGE_IDENT), "attestation", None)
    await ch.close(); server.close()
    try: await asyncio.wait_for(server.wait_closed(), 3)
    except asyncio.TimeoutError: pass
    mgr.close(); b.manager.close()
    return dict(hello_ok=bool(hello_ok), att=att, reached=reached.get("tool"),
                tool=tool, task=task, chat=(chat or {}).get("accepted"),
                ep=(ep or {}).get("accepted"))


def test_tier0_forger_admitted_but_powerless(tmp_path):
    r = asyncio.run(asyncio.wait_for(_tier0(tmp_path), 20))
    assert r["hello_ok"] and r["att"] == "self-asserted"     # admitted, tier-0
    assert r["reached"] is None and r["tool"] is None         # no tool
    assert r["task"] is None                                  # no async skill
    assert r["chat"] is not True                              # no chat (even enabled)
    assert r["ep"] is not True                                # no endpoint redirect


# --- active forgery: presents a cert it cannot sign for → hard reject ---

async def _active(tmp_path):
    b = _acceptor(tmp_path / "b")
    b.manager.local_consent(FORGE_AS, FORGE_RID)
    b.manager.remote_consent(FORGE_AS, FORGE_RID)
    server, port = await _serve(b)
    reader, writer, nonce = await _dial(port)
    victim_cert = RiskManager(FederationManager(base_dir=str(tmp_path / "v"))).self_cert_pem()
    wrong_sig = RiskManager(FederationManager(base_dir=str(tmp_path / "w"))).self_sign(nonce).hex()
    ch, mgr = _chan(reader, writer, tmp_path / "atk")
    await ch.start()
    rejected = False
    try:
        await ch.call("n2n/hello", {"identity": FORGE_IDENT, "cert_pem": victim_cert,
                                    "signature": wrong_sig}, timeout=5.0)
    except RpcError:
        rejected = True
    registered = FORGE_IDENT in b.channels
    await ch.close(); server.close()
    try: await asyncio.wait_for(server.wait_closed(), 3)
    except asyncio.TimeoutError: pass
    mgr.close(); b.manager.close()
    return dict(rejected=rejected, registered=registered)


def test_active_possession_forgery_rejected(tmp_path):
    r = asyncio.run(asyncio.wait_for(_active(tmp_path), 20))
    assert r["rejected"] and not r["registered"]


# --- un-consented stranger: closed before a nonce is issued (FR-003) ---

async def _stranger(tmp_path):
    b = _acceptor(tmp_path / "b")   # NO consent for FORGE_IDENT
    server, port = await _serve(b)
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(build_handshake(FORGE_AS, FORGE_RID))
    await writer.drain()
    trailer = await reader.read(64)
    closed_no_nonce = len(trailer) < len(NCFED_MAGIC) + 8 + IN2N_NONCE_SIZE
    registered = FORGE_IDENT in b.channels
    writer.close(); server.close()
    try: await asyncio.wait_for(server.wait_closed(), 3)
    except asyncio.TimeoutError: pass
    b.manager.close()
    return dict(closed_no_nonce=closed_no_nonce, registered=registered)


def test_unconsented_stranger_closed(tmp_path):
    r = asyncio.run(asyncio.wait_for(_stranger(tmp_path), 20))
    assert not r["registered"] and r["closed_no_nonce"]
