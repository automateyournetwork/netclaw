"""Feature 063 / US1 (P1): endpoint persistence — the live re-dial bug.

Before 063, /n2n/connect and open_channel dialed a peer's freshly-advertised
host:port but never wrote endpoint_host/endpoint_port to the federation_peer
row, so after a restart the reconnect supervisor fell back to the STALE stored
endpoint and got connection-refused until a manual re-dial.

These tests prove, at the store level (T003) and end-to-end over loopback with
cert_mode OFF/baseline auth (T008), that:
  - a successful, authenticated dial persists the reached endpoint + bumps freshness
  - a failed dial does NOT overwrite a previously-good address
  - a fresh manager over the same DB (simulated restart) sees the persisted address,
    which is exactly what the reconnect supervisor reads to auto-redial (SC-001).
Loopback only; no real claw is contacted.
"""

import asyncio
import socket

from bgp.constants import NCFED_MAGIC
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation.channel import read_handshake

DIALER_AS, DIALER_RID = 65001, "4.4.4.4"     # lower AS → initiates
ACCEPT_AS, ACCEPT_RID = 65007, "7.7.7.7"     # higher AS → accepts
ACCEPT_IDENT = f"as{ACCEPT_AS}-{ACCEPT_RID}"


# ---- T003: store-level persistence primitive --------------------------------

def test_upsert_persists_endpoint_and_bumps_freshness(tmp_path):
    mgr = FederationManager(base_dir=str(tmp_path / "m"))
    mgr.upsert_peer(ACCEPT_AS, ACCEPT_RID, endpoint_host="new.tcp.ngrok.io", endpoint_port=20000)
    p = mgr.get_peer(ACCEPT_IDENT)
    assert p["endpoint_host"] == "new.tcp.ngrok.io"
    assert p["endpoint_port"] == 20000
    assert p["endpoint_updated_at"], "a written endpoint must bump endpoint_updated_at"


def test_upsert_without_endpoint_preserves_prior_address(tmp_path):
    """A metadata-only upsert (e.g. display_name, remote_consent) must not wipe a
    good stored address — the guard that keeps a bad dial from clobbering it."""
    mgr = FederationManager(base_dir=str(tmp_path / "m"))
    mgr.upsert_peer(ACCEPT_AS, ACCEPT_RID, endpoint_host="good.tcp.ngrok.io", endpoint_port=19999)
    before = mgr.get_peer(ACCEPT_IDENT)["endpoint_updated_at"]
    mgr.upsert_peer(ACCEPT_AS, ACCEPT_RID, display_name="renamed")  # no endpoint
    p = mgr.get_peer(ACCEPT_IDENT)
    assert p["endpoint_host"] == "good.tcp.ngrok.io"
    assert p["endpoint_port"] == 19999
    assert p["endpoint_updated_at"] == before, "no-endpoint upsert must not bump freshness"


# ---- T008: end-to-end dial persists, restart re-targets, bad dial is safe ----

async def _acceptor_server(base):
    b = FederationService(local_as=ACCEPT_AS, router_id=ACCEPT_RID, display_name="B",
                          manager=FederationManager(base_dir=str(base)))
    b.manager.local_consent(DIALER_AS, DIALER_RID)   # acceptor consents to dialer

    async def on_conn(reader, writer):
        assert await reader.readexactly(len(NCFED_MAGIC)) == NCFED_MAGIC
        peer_as, rid = await read_handshake(reader)
        await b.accept_channel(peer_as, rid, reader, writer)

    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    return b, server, server.sockets[0].getsockname()[1]


async def _run(tmp_path):
    b, server, port = await _acceptor_server(tmp_path / "b")
    dialer_base = tmp_path / "a"
    a = FederationService(local_as=DIALER_AS, router_id=DIALER_RID, display_name="A",
                          manager=FederationManager(base_dir=str(dialer_base)))
    a.manager.local_consent(ACCEPT_AS, ACCEPT_RID)   # dialer consents to acceptor

    async with server:
        # 1. successful dial → endpoint persisted + fresh
        await asyncio.wait_for(a.open_channel(ACCEPT_AS, ACCEPT_RID, "127.0.0.1", port), 15)
        persisted = a.manager.get_peer(ACCEPT_IDENT)
        assert ACCEPT_IDENT in a.channels, "channel should be up"
        assert persisted["endpoint_host"] == "127.0.0.1"
        assert persisted["endpoint_port"] == port
        good_freshness = persisted["endpoint_updated_at"]
        assert good_freshness

        # 2. a bad dial (dead port) must NOT overwrite the good stored address.
        #    Grab an ephemeral port and close it so the connect is refused fast.
        s = socket.socket(); s.bind(("127.0.0.1", 0)); dead_port = s.getsockname()[1]; s.close()
        await a.channels[ACCEPT_IDENT].close()
        a.channels.pop(ACCEPT_IDENT, None)
        await asyncio.wait_for(a.open_channel(ACCEPT_AS, ACCEPT_RID, "127.0.0.1", dead_port), 15)
        after_bad = a.manager.get_peer(ACCEPT_IDENT)
        assert after_bad["endpoint_host"] == "127.0.0.1"
        assert after_bad["endpoint_port"] == port, "bad dial must not clobber good address"
        assert after_bad["endpoint_updated_at"] == good_freshness

    # 3. simulated restart: fresh manager over the SAME db sees the persisted
    #    address — exactly what the reconnect supervisor reads to auto-redial.
    restarted = FederationManager(base_dir=str(dialer_base))
    row = restarted.get_peer(ACCEPT_IDENT)
    return row["endpoint_host"], row["endpoint_port"], port


def test_dial_persists_survives_restart_and_bad_dial(tmp_path):
    host, prt, expected = asyncio.run(asyncio.wait_for(_run(tmp_path), 40))
    assert (host, prt) == ("127.0.0.1", expected)
