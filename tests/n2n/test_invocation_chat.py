"""T032/T036: loopback invocation + chat over the real NCFED channel.

Two federated services connected by an in-memory duplex stream pair. Exercises
US2 (allowlisted tool call, denial, budget) and US3 (chat enabled/disabled),
stubbing the tool executor and gateway so no external processes are needed.
"""

import asyncio
import json

import pytest

from bgp.federation import invocation
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation.channel import FederationChannel, RpcError


@pytest.fixture(autouse=True)
def _guards_off(monkeypatch):
    """These eN2N regression tests exercise pure authz allow/deny — force
    OpenClaw's security.mode 'off' so they don't depend on the host's real
    ~/.openclaw/openclaw.json (feature 057 legitimately sets it to 'defenseclaw'
    on a production host, which would otherwise route these tool calls through the
    real DefenseClaw CLI). Keeps the test hermetic without changing what it asserts."""
    monkeypatch.setattr(invocation, "_security_mode", lambda: "hobby")


def _svc(base, local_as, rid, name):
    return FederationService(local_as=local_as, router_id=rid, display_name=name,
                             manager=FederationManager(base_dir=str(base)))


async def _linked_channels(initiator, acceptor):
    """Wire two FederationChannels back-to-back over asyncio pipes (no TCP)."""
    a_ident = initiator.local_identity
    b_ident = acceptor.local_identity

    # initiator -> acceptor stream, acceptor -> initiator stream
    r_ia, w_ia = _pipe()
    r_ai, w_ai = _pipe()

    ini_ch = FederationChannel(r_ai, w_ia, local_identity=a_ident,
                               peer_as=acceptor.local_as, peer_router_id=acceptor.router_id,
                               manager=initiator.manager, is_initiator=True, handlers=initiator.handlers)
    acc_ch = FederationChannel(r_ia, w_ai, local_identity=b_ident,
                               peer_as=initiator.local_as, peer_router_id=initiator.router_id,
                               manager=acceptor.manager, is_initiator=False, handlers=acceptor.handlers)
    acc_ch.authenticated = True; acc_ch.attestation = "possession"   # post-possession session (reconciled auth)
    initiator.channels[peer_identity(acceptor.local_as, acceptor.router_id)] = ini_ch
    acceptor.channels[peer_identity(initiator.local_as, initiator.router_id)] = acc_ch
    await ini_ch.start()
    await acc_ch.start()
    return ini_ch, acc_ch


def _pipe():
    """Return (StreamReader, StreamWriter) where writes feed the reader."""
    reader = asyncio.StreamReader()

    class _W:
        def write(self, data): reader.feed_data(data)
        async def drain(self): pass
        def close(self): pass
    return reader, _W()


def _federate(a, b):
    a.manager.local_consent(b.local_as, b.router_id)
    a.manager.remote_consent(b.local_as, b.router_id)
    b.manager.local_consent(a.local_as, a.router_id)
    b.manager.remote_consent(a.local_as, a.router_id)


def test_tool_invocation_allow_and_deny(tmp_path):
    asyncio.run(_run_invocation(tmp_path))


async def _run_invocation(tmp_path):
    john = _svc(tmp_path / "a", 65001, "4.4.4.4", "John")
    nick = _svc(tmp_path / "b", 65007, "7.7.7.7", "Nicholas")
    _federate(john, nick)
    john_ident = john.local_identity  # as65001-4.4.4.4

    # Stub Nicholas's tool executor so no real MCP server is spawned
    async def fake_exec(tool, arguments):
        return {"content": [{"type": "text", "text": f"ran {tool}"}], "isError": False}
    nick.invoker._exec_tool_stdio = fake_exec

    await _linked_channels(john, nick)

    # Not allowlisted → explicit denial + audit on Nicholas's side
    try:
        await john.invoker.invoke_remote_tool(nick.local_identity, "cml-mcp/list_labs", {})
        assert False, "expected denial"
    except RpcError as e:
        assert e.code == -32001  # not_allowlisted

    # Grant then invoke → success, both sides audited
    nick.authz.grant(john_ident, "tool", "cml-mcp/list_labs")
    res = await john.invoker.invoke_remote_tool(nick.local_identity, "cml-mcp/list_labs", {})
    assert res["trust"] == "remote-untrusted"
    assert "ran cml-mcp/list_labs" in json.dumps(res["result"])

    # Audit present on both sides
    assert any(r["decision"] == "allowlisted" and r["outcome"] == "success"
               for r in nick.audit.recent(john_ident))
    assert any(r["direction"] == "outbound" for r in john.audit.recent(nick.local_identity))


def test_chat_enabled_and_disabled(tmp_path):
    asyncio.run(_run_chat(tmp_path))


async def _run_chat(tmp_path):
    john = _svc(tmp_path / "a", 65001, "4.4.4.4", "John")
    byrn = _svc(tmp_path / "b", 65099, "10.255.255.1", "Byrn")
    _federate(john, byrn)

    # Stub Byrn's gateway call
    async def fake_ask(text, session_key="n2n-chat"):
        return (f"Byrn's claw says: re '{text[:20]}' — area 0 is fine.", 42)
    byrn.chat._ask_gateway = fake_ask

    await _linked_channels(john, byrn)

    # Chat disabled by default → refused
    r = await john.chat.open_and_send(byrn.local_identity, "why is OSPF flapping?")
    assert r.get("session_id") is None and "not enabled" in r.get("error", "").lower()

    # Enable on Byrn's side, retry → attributed reply
    byrn.manager.set_chat_enabled(john.local_identity, True)
    r2 = await john.chat.open_and_send(byrn.local_identity, "why is OSPF flapping?")
    assert r2["source"] == byrn.local_identity
    assert r2["trust"] == "remote-untrusted"
    assert "area 0 is fine" in r2["text"]
