"""T021 (US3): endpoint auto-re-announce.

n2n/endpoint_update from a federated peer over its authenticated channel updates
the stored endpoint and clears backoff so the supervisor re-dials (FR-010/011);
an update for a non-federated identity is rejected (FR-012).
"""

import asyncio

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager, peer_identity


def _svc(base, local_as, rid, name):
    return FederationService(local_as=local_as, router_id=rid, display_name=name,
                             manager=FederationManager(base_dir=str(base)))


class _FakeChannel:
    """Stands in for an authenticated channel bound to a peer identity."""
    def __init__(self, peer_as, router_id):
        self.peer_as = peer_as
        self.peer_router_id = router_id
        self.peer_identity = peer_identity(peer_as, router_id)


def test_endpoint_update_from_federated_peer(tmp_path):
    asyncio.run(_update_federated(tmp_path))


async def _update_federated(tmp_path):
    svc = _svc(tmp_path / "a", 65001, "4.4.4.4", "John")
    svc.manager.local_consent(65007, "7.7.7.7")
    svc.manager.remote_consent(65007, "7.7.7.7")
    ident = "as65007-7.7.7.7"
    # seed a stale endpoint + backoff state
    svc.manager.upsert_peer(65007, "7.7.7.7", endpoint_host="old.tcp.ngrok.io", endpoint_port=111)
    svc.health[ident] = {"state": "unreachable", "attempts": 9, "next_retry_at": 9e18, "last_seen": 0}

    ch = _FakeChannel(65007, "7.7.7.7")
    res = await svc._on_endpoint_update(ch, {"identity": ident, "endpoint": "new.tcp.ngrok.io:22222"})
    assert res["accepted"] is True

    peer = svc.manager.get_peer(ident)
    assert peer["endpoint_host"] == "new.tcp.ngrok.io" and peer["endpoint_port"] == 22222
    assert peer["endpoint_updated_at"]
    # backoff cleared so the supervisor re-dials promptly
    assert ident not in svc.health


def test_endpoint_update_rejected_for_non_federated(tmp_path):
    asyncio.run(_reject_non_federated(tmp_path))


async def _reject_non_federated(tmp_path):
    svc = _svc(tmp_path / "b", 65001, "4.4.4.4", "John")
    # peer known but NOT federated (no consent) → update must be rejected (FR-012)
    svc.manager.upsert_peer(65099, "10.255.255.1")
    ch = _FakeChannel(65099, "10.255.255.1")
    res = await svc._on_endpoint_update(ch, {"identity": "as65099-10.255.255.1",
                                             "endpoint": "evil.tcp.ngrok.io:9"})
    assert res["accepted"] is False
    peer = svc.manager.get_peer("as65099-10.255.255.1")
    assert peer["endpoint_host"] != "evil.tcp.ngrok.io"
