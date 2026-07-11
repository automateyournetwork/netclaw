"""T006 (foundation) + US2 (T018): channel death→deregister and auto-reconnect.

Foundation slice here: a channel that closes fires on_close and deregisters
itself from the service registry (kills the zombie-channel class). The full
auto-reconnect supervisor tests land with US2 (T018).
"""

import asyncio

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation.channel import FederationChannel


def _svc(base, local_as, rid, name):
    return FederationService(local_as=local_as, router_id=rid, display_name=name,
                             manager=FederationManager(base_dir=str(base)))


def test_closed_channel_deregisters(tmp_path):
    asyncio.run(_closed_channel_deregisters(tmp_path))


async def _closed_channel_deregisters(tmp_path):
    svc = _svc(tmp_path / "a", 65001, "4.4.4.4", "John")
    reader = asyncio.StreamReader()

    class _W:
        def write(self, d): pass
        async def drain(self): pass
        def close(self): pass

    ch = FederationChannel(reader, _W(), local_identity=svc.local_identity,
                           peer_as=65007, peer_router_id="7.7.7.7",
                           manager=svc.manager, is_initiator=True, handlers=svc.handlers)
    ident = "as65007-7.7.7.7"
    svc._register_channel(ident, ch)
    assert svc.channels.get(ident) is ch

    await ch.start()
    await ch.close()          # simulate death
    await asyncio.sleep(0.05)
    # on_close hook must have removed the dead channel from the registry
    assert ident not in svc.channels, "dead channel must self-deregister (no zombie)"


def test_supervisor_reconnects_after_drop(tmp_path):
    asyncio.run(_supervisor_reconnects(tmp_path))


async def _supervisor_reconnects(tmp_path, monkeypatch=None):
    """US2/T018: with an endpoint recorded, the supervisor re-dials a federated
    peer whose channel is gone — from persisted consent, no re-consent."""
    svc = _svc(tmp_path / "a", 65001, "4.4.4.4", "John")
    svc._backoff_min = 1  # speed up the test
    # Federate with a higher-AS peer and record an endpoint (John is lower AS → dials)
    svc.manager.local_consent(65007, "7.7.7.7")
    svc.manager.remote_consent(65007, "7.7.7.7")
    svc.manager.upsert_peer(65007, "7.7.7.7", endpoint_host="127.0.0.1", endpoint_port=59999)
    ident = "as65007-7.7.7.7"
    assert svc.manager.is_federated(ident)
    assert ident not in svc.channels

    # Count dial attempts instead of standing up a real listener
    attempts = {"n": 0}
    async def fake_open(peer_as, router_id, host, port):
        attempts["n"] += 1
    svc.open_channel = fake_open

    svc.start_supervisor()
    await asyncio.sleep(3)          # supervisor runs every 2s
    svc._supervisor_task.cancel()
    assert attempts["n"] >= 1, "supervisor must auto-dial a federated peer with a dead channel"


def test_ensure_channel_fails_fast_when_unreachable(tmp_path):
    asyncio.run(_ensure_fast_fail(tmp_path))


async def _ensure_fast_fail(tmp_path):
    """FR-009: a request to a peer with no endpoint fails fast, doesn't hang."""
    svc = _svc(tmp_path / "c", 65001, "4.4.4.4", "John")
    svc.manager.local_consent(65007, "7.7.7.7")
    svc.manager.remote_consent(65007, "7.7.7.7")  # federated but no endpoint recorded
    import pytest
    with pytest.raises(RuntimeError, match="peer_unreachable"):
        await svc.ensure_channel("as65007-7.7.7.7")


def test_close_is_idempotent(tmp_path):
    asyncio.run(_close_idempotent(tmp_path))


async def _close_idempotent(tmp_path):
    svc = _svc(tmp_path / "b", 65001, "4.4.4.4", "John")
    reader = asyncio.StreamReader()

    class _W:
        def write(self, d): pass
        async def drain(self): pass
        def close(self): pass

    ch = FederationChannel(reader, _W(), local_identity=svc.local_identity,
                           peer_as=65099, peer_router_id="10.255.255.1",
                           manager=svc.manager, is_initiator=True, handlers=svc.handlers)
    svc._register_channel("as65099-10.255.255.1", ch)
    await ch.start()
    await ch.close()
    await ch.close()          # second close must not raise
    assert "as65099-10.255.255.1" not in svc.channels
