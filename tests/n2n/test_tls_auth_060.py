"""Real-socket TLS + channel-bound auth tests for claw certification (US1 core).

These exercise bgp/federation/tls.py over an actual loopback TLS connection —
not mocks — so the SSL context builders, channel binding (exported keying
material), fingerprint pinning, and signed-nonce proof-of-possession are proven
on the wire. This is the keystone the eN2N channel integration sits on.
"""

import os
import socket
import ssl
import threading

import pytest

from bgp.federation import tls, certs


def _tls_pair(server_ctx, client_ctx, server_hostname=None):
    """Establish a real loopback TLS connection; return (server_sslobj,
    client_sslobj) as connected wrapped sockets."""
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind(("127.0.0.1", 0))
    lsock.listen(1)
    host, port = lsock.getsockname()

    holder = {}

    def _client():
        craw = socket.create_connection((host, port))
        try:
            holder["c"] = client_ctx.wrap_socket(craw, server_hostname=server_hostname)
        except Exception as e:  # surface client-side verification failures
            holder["cerr"] = e

    t = threading.Thread(target=_client)
    t.start()
    raw, _ = lsock.accept()
    try:
        server = server_ctx.wrap_socket(raw, server_side=True)
    except ssl.SSLError:
        # Client rejected our cert (e.g. hostname mismatch) — join and re-raise
        # the client's exception, which is the assertion the test cares about.
        t.join(5)
        lsock.close()
        if holder.get("cerr"):
            raise holder["cerr"]
        raise
    t.join(5)
    lsock.close()
    if holder.get("cerr"):
        raise holder["cerr"]
    return server, holder["c"]


def test_pinned_model_handshake_and_fingerprint_pin():
    # Listener presents a self-signed (pinned-model) credential.
    cert_pem, key_pem = certs.create_self_signed("as65001-4.4.4.4")
    expected_fp = certs.key_fingerprint(cert_pem)
    sctx = tls.server_context(cert_pem, key_pem)
    cctx, sni = tls.client_context("pinned")

    s, c = _tls_pair(sctx, cctx, server_hostname=sni)
    try:
        # Dialer (client) sees the listener leaf and can pin it — the TOFU value.
        assert tls.leaf_key_fingerprint(c) == expected_fp
        # Both ends derive the same tls-server-end-point binding: the dialer from
        # the peer (listener) cert, the listener from its own cert.
        assert tls.binding_from_peer(c) == tls.binding_from_own_cert(cert_pem)
    finally:
        s.close(); c.close()


def test_signed_nonce_proof_bound_to_channel():
    # Listener credential + a separate dialer credential (its own key).
    scert, skey = certs.create_self_signed("as65001-4.4.4.4")
    dcert, dkey = certs.create_self_signed("as65007-7.7.7.7")
    cctx, _sni = tls.client_context("pinned")
    s, c = _tls_pair(tls.server_context(scert, skey), cctx)
    try:
        # Listener issues a nonce; dialer signs (nonce || server-end-point binding
        # it observes from the listener's cert).
        nonce = os.urandom(32)
        binding_client = tls.binding_from_peer(c)
        sig = tls.sign_auth(dkey, nonce, binding_client)

        # Listener verifies against the dialer's presented cert + the binding it
        # computes from its OWN cert (equal to the client's) — proof is valid.
        binding_server = tls.binding_from_own_cert(scert)
        assert binding_server == binding_client
        assert tls.verify_auth(dcert, sig, nonce, binding_server) is True

        # Tampered nonce / wrong cert / wrong binding all fail.
        assert tls.verify_auth(dcert, sig, os.urandom(32), binding_server) is False
        assert tls.verify_auth(scert, sig, nonce, binding_server) is False
        assert tls.verify_auth(dcert, sig, nonce, os.urandom(32)) is False
    finally:
        s.close(); c.close()


def test_domain_verified_context_verifies_against_test_ca(tmp_path):
    # Stand up a private CA acting as the "public" trust root, issue a leaf for
    # the claw domain, and confirm the domain-verified client context verifies
    # the chain + hostname over a real handshake.
    ca_cert, ca_key = certs.create_risk_ca("test-root")
    leaf_cert, leaf_key = certs.issue_cert(
        ca_cert, ca_key, "netclaw.automateyournetwork.ca",
        san="netclaw.automateyournetwork.ca", days=30)
    chain = leaf_cert + ca_cert  # leaf + issuer

    cafile = tmp_path / "root.pem"
    cafile.write_text(ca_cert)

    sctx = tls.server_context(chain, leaf_key)
    cctx, sni = tls.client_context("domain-verified",
                                   claw_domain="netclaw.automateyournetwork.ca",
                                   cafile=str(cafile))
    assert sni == "netclaw.automateyournetwork.ca"
    s, c = _tls_pair(sctx, cctx, server_hostname=sni)
    try:
        # A verified handshake means the client validated chain + hostname.
        assert c.getpeercert() is not None
        assert "netclaw.automateyournetwork.ca" in certs.san_names(tls.peer_leaf_pem(c))
    finally:
        s.close(); c.close()


def test_domain_verified_rejects_wrong_hostname(tmp_path):
    ca_cert, ca_key = certs.create_risk_ca("test-root")
    leaf_cert, leaf_key = certs.issue_cert(
        ca_cert, ca_key, "netclaw.automateyournetwork.ca",
        san="netclaw.automateyournetwork.ca", days=30)
    cafile = tmp_path / "root.pem"
    cafile.write_text(ca_cert)
    sctx = tls.server_context(leaf_cert + ca_cert, leaf_key)
    cctx, _ = tls.client_context("domain-verified",
                                 claw_domain="imposter.example.net",
                                 cafile=str(cafile))
    with pytest.raises(ssl.SSLCertVerificationError):
        _tls_pair(sctx, cctx, server_hostname="imposter.example.net")
