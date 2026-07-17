"""Feature 063 / US3 (P3): metadata minimization — ECH seam + accepted residuals.

On the reference stack (no ECH), P3 is deliberately a no-op that documents the
SNI residual and leaves the wire unchanged. These tests close the FR-009
verification gap: the ECH seam never breaks connectivity, and the 13-byte NCFED
preamble that discriminates the shared listening port is UNCHANGED — so a peer
that does not implement the metadata seam still federates (proven end-to-end by
test_endpoint_persistence_063 and the 060 baseline).
"""

import ssl

from bgp.constants import NCFED_MAGIC
from bgp.federation import tls
from bgp.federation.channel import build_handshake


def test_ech_seam_is_a_harmless_noop_on_this_stack():
    assert tls.ech_available() is False
    # Passing an ech_config on a non-ECH stack must NOT raise and must still yield
    # a usable client context (connectivity preserved — FR-007/FR-009).
    ctx, hostname = tls.client_context("domain-verified", claw_domain="netclaw.example",
                                       ech_config=b"pretend-ech-config")
    assert isinstance(ctx, ssl.SSLContext)
    assert hostname == "netclaw.example"   # SNI still set — accepted, reported residual


def test_pinned_context_unaffected_by_ech_arg():
    ctx, hostname = tls.client_context("pinned", ech_config=b"ignored")
    assert isinstance(ctx, ssl.SSLContext)
    assert hostname is None
    assert ctx.verify_mode == ssl.CERT_NONE   # pinned model unchanged


def test_preamble_discrimination_unchanged():
    """FR-008/FR-009: the shared-port discriminator must be byte-for-byte the same
    so non-implementing peers still key off it. 13-byte NCFED preamble:
    5-byte magic + 4-byte AS + 4-byte router-id."""
    hs = build_handshake(65001, "4.4.4.4")
    assert hs[:5] == NCFED_MAGIC
    assert len(hs) == 13
    assert NCFED_MAGIC == b"NCFED"
