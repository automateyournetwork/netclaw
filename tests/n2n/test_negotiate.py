"""T025 (US4): capability & version negotiation.

Descriptor build/normalize, graceful degrade for a pre-053 peer, and the hello
exchange storing the peer's descriptor on both sides.
"""

import asyncio

import bgp.federation.negotiate as neg
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager, peer_identity


def test_local_descriptor_cached(monkeypatch):
    neg._local_descriptor = None
    calls = {"n": 0}
    def fake_probe():
        calls["n"] += 1
        return "session-id"
    monkeypatch.setattr(neg, "_probe_agent_invoke", fake_probe)
    d1 = neg.local_descriptor()
    d2 = neg.local_descriptor()
    assert d1 is d2 and calls["n"] == 1        # probed once, cached (FR-014)
    assert d1["proto_version"] == "053" and "async_tasks" in d1["features"]


def test_missing_descriptor_degrades_to_052():
    n = neg.normalize(None)
    assert n["proto_version"] == "052" and n["features"] == []
    assert neg.peer_supports(None, "async_tasks") is False


def test_peer_supports():
    d = {"proto_version": "053", "features": ["async_tasks", "negotiate"]}
    assert neg.peer_supports(d, "async_tasks") is True
    assert neg.peer_supports(d, "nope") is False


def test_hello_exchanges_descriptors(tmp_path):
    asyncio.run(_hello_exchange(tmp_path))


async def _hello_exchange(tmp_path):
    from bgp.federation.channel import FederationChannel

    def svc(base, asn, rid, name):
        return FederationService(local_as=asn, router_id=rid, display_name=name,
                                 manager=FederationManager(base_dir=str(base)))

    def pipe():
        r = asyncio.StreamReader()
        class W:
            def write(self, d): r.feed_data(d)
            async def drain(self): pass
            def close(self): pass
        return r, W()

    john = svc(tmp_path / "a", 65001, "4.4.4.4", "John")
    nick = svc(tmp_path / "b", 65007, "7.7.7.7", "Nick")
    for a, b in ((john, nick), (nick, john)):
        a.manager.local_consent(b.local_as, b.router_id)
        a.manager.remote_consent(b.local_as, b.router_id)

    r_ia, w_ia = pipe(); r_ai, w_ai = pipe()
    ini = FederationChannel(r_ai, w_ia, local_identity=john.local_identity, peer_as=65007,
                            peer_router_id="7.7.7.7", manager=john.manager,
                            is_initiator=True, handlers=john.handlers)
    acc = FederationChannel(r_ia, w_ai, local_identity=nick.local_identity, peer_as=65001,
                            peer_router_id="4.4.4.4", manager=nick.manager,
                            is_initiator=False, handlers=nick.handlers)
    john._register_channel("as65007-7.7.7.7", ini)
    nick._register_channel("as65001-4.4.4.4", acc)
    await ini.start(); await acc.start()

    resp = await ini.call("n2n/hello", {"identity": john.local_identity,
                                        "display_name": "John", "versions": ["1.0"],
                                        "capabilities": neg.local_descriptor()})
    # John learns Nick's descriptor from the hello result
    assert resp["capabilities"]["proto_version"] == "053"
    # Nick stored John's descriptor from the hello params
    assert nick.peer_caps["as65001-4.4.4.4"]["proto_version"] == "053"
    assert "async_tasks" in nick.peer_caps["as65001-4.4.4.4"]["features"]
