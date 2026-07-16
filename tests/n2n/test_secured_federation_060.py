"""End-to-end secured eN2N federation (US1) over a real TCP socket.

Two FederationService instances (John as65001, Nicholas as65007) federate with
N2N_CERT_MODE=on. Proves the full path: cleartext NCFED discrimination handshake
→ in-place TLS upgrade → channel-bound mutual auth → both sides pin each other's
key → live secured channel. cert_mode defaults off, so this only runs when set.
"""

import asyncio
import os

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation.channel import read_handshake


def _svc(base, local_as, rid, name):
    return FederationService(local_as=local_as, router_id=rid, display_name=name,
                             manager=FederationManager(base_dir=str(base)))


def _federate(a, b):
    a.manager.local_consent(b.local_as, b.router_id)
    a.manager.remote_consent(b.local_as, b.router_id)
    b.manager.local_consent(a.local_as, a.router_id)
    b.manager.remote_consent(a.local_as, a.router_id)


async def _run(tmp_path):
    os.environ["N2N_CERT_MODE"] = "on"
    try:
        john = _svc(tmp_path / "a", 65001, "4.4.4.4", "John")
        nick = _svc(tmp_path / "b", 65007, "7.7.7.7", "Nicholas")
        assert john.cert_mode and nick.cert_mode
        _federate(john, nick)

        async def handle(reader, writer):
            # Mimic agent.py discrimination: consume NCFED magic + handshake,
            # then hand to the listener's accept_channel.
            await reader.readexactly(5)          # NCFED magic
            hs = await read_handshake(reader)
            await nick.accept_channel(hs[0], hs[1], reader, writer)

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        await john.open_channel(65007, "7.7.7.7", "127.0.0.1", port)
        await asyncio.sleep(0.2)  # let nick finish accept + hello

        nick_ident = peer_identity(65007, "7.7.7.7")
        john_ident = peer_identity(65001, "4.4.4.4")

        # Both sides now hold a live secured channel.
        assert nick_ident in john.channels
        assert john_ident in nick.channels
        # The channel runs over TLS (ssl_object present on the writer transport).
        jch = john.channels[nick_ident]
        assert jch.writer.get_extra_info("ssl_object") is not None
        # Mutual pinning happened (both recorded the other's key fingerprint).
        assert john.manager.get_peer(nick_ident)["pinned_fp"]
        assert nick.manager.get_peer(john_ident)["pinned_fp"]
        assert john.manager.get_peer(nick_ident)["verify_state"] == "verified"

        server.close()
        await server.wait_closed()
    finally:
        os.environ.pop("N2N_CERT_MODE", None)


def test_secured_federation_end_to_end(tmp_path):
    asyncio.run(_run(tmp_path))


def test_heartbeat_carries_and_records_credential_health(tmp_path):
    """FR-024/SC-011: the heartbeat handler records a peer's reported credential
    health, and _cred_status advertises this claw's real fingerprint."""
    import asyncio as _a
    os.environ["N2N_CERT_MODE"] = "on"
    try:
        svc = _svc(tmp_path / "c", 65001, "4.4.4.4", "John")
        # This claw's advertised credential health matches its host credential.
        from bgp.federation import certs
        cert_pem, _ = svc.host_credential()
        status = svc._cred_status()
        assert status["fp"] == certs.key_fingerprint(cert_pem)
        assert status["not_after"]

        # A peer's heartbeat updates its stored credential health.
        svc.manager.upsert_peer(65007, "7.7.7.7", display_name="Nicholas")
        ident = peer_identity(65007, "7.7.7.7")

        class _Ch:
            peer_identity = ident

        _a.run(svc._on_heartbeat(_Ch(), {"cred": {"fp": "abc123", "not_after":
               "2026-10-01T00:00:00+00:00", "renew_state": "ok"}}))
        peer = svc.manager.get_peer(ident)
        assert peer["peer_cred_fp"] == "abc123"
        assert peer["peer_renew_state"] == "ok"
        svc.manager.close()
    finally:
        os.environ.pop("N2N_CERT_MODE", None)


def test_possession_proof_is_channel_bound(tmp_path):
    """RFC 5929 binding: a possession proof is over nonce||binding, so a proof
    made for one channel binding does not verify under another (nor with none) —
    preventing relay of the proof to a different TLS session."""
    import os as _os
    from bgp.federation.risk import RiskManager
    from bgp.federation.manager import FederationManager
    mgr = FederationManager(base_dir=str(tmp_path / "n2n"))
    rm = RiskManager(mgr)
    cert = rm.self_cert_pem()
    nonce = _os.urandom(32)
    b1 = _os.urandom(32)   # this session's tls-server-end-point value
    b2 = _os.urandom(32)   # a different session
    sig = rm.self_sign(nonce, b1)
    assert rm.verify_possession(cert, nonce, sig, b1) is True     # right session
    assert rm.verify_possession(cert, nonce, sig, b2) is False    # relayed → fails
    assert rm.verify_possession(cert, nonce, sig, b"") is False   # stripped binding → fails
    # Backward compat: with no binding on either side (cleartext / iN2N), raw nonce holds.
    sig0 = rm.self_sign(nonce)
    assert rm.verify_possession(cert, nonce, sig0) is True
    mgr.close()
