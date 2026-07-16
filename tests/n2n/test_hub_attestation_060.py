"""US2 hub attestation: a member cryptographically verifies the Border is its
legitimate hub (risk-CA chain + signature over the member's nonce), over a real
loopback iN2N channel. Also proves an imposter hub (no/blank CA) is rejected.
"""

import asyncio
import os

import pytest

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation import certs


def _service(base, name, mid=None, role="border", risk="johns-risk"):
    svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name=name,
                            manager=FederationManager(base_dir=str(base)))
    if role == "border":
        svc.risk.set_role("border", risk_name=risk, enabled_stacks="in2n",
                          border_endpoint="127.0.0.1:0")
    else:
        svc.risk.set_role("member", risk_name=risk, border_endpoint="127.0.0.1:0",
                          self_member_id=mid)
    return svc


async def _serve(border):
    async def on_conn(reader, writer):
        await border.accept_internal(reader, writer)
    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def _good(tmp_path):
    border = _service(tmp_path / "b", "Border")
    member = _service(tmp_path / "m", "Member", mid="johns-risk/pyats", role="member")
    token = border.risk.issue_token(label="pyats")["token"]
    server, port = await _serve(border)
    try:
        resp = await member.dial_border("127.0.0.1", port, enrollment_token=token)
        await asyncio.sleep(0.2)
        # Member stored the CA anchor and verified the hub attestation.
        assert member.risk.risk_anchor() is not None
        assert resp["pinned"] is True
        assert "johns-risk/pyats" in border.member_channels
        # The anchor equals the Border's actual risk CA.
        assert member.risk.risk_anchor().strip() == border.risk.risk_ca_pem().strip()
    finally:
        server.close()
    border.manager.close(); member.manager.close()


def test_hub_attestation_verified(tmp_path):
    asyncio.run(_good(tmp_path))


def test_imposter_hub_rejected(tmp_path):
    # A member that already holds an anchor for its risk must reject a Border that
    # cannot produce a valid attestation (verify_hub_attestation returns False).
    border = _service(tmp_path / "b", "Border")
    real_ca, _ = border.risk.ensure_risk_ca()
    # Forge a DIFFERENT ca and a hub cert under it — not the member's anchor.
    other_ca, other_key = certs.create_risk_ca("evil-risk")
    hub_cert, hub_key = certs.issue_cert(other_ca, other_key, "johns-risk/border",
                                         san="johns-risk/border")
    import bgp.federation.risk as riskmod
    nonce = os.urandom(32)
    sig = riskmod.RiskManager.sign_challenge(hub_key, nonce).hex()
    attest = {"hub_cert": hub_cert, "hub_sig": sig, "risk_ca": other_ca}
    # Member verifies against the REAL anchor → must fail (wrong CA).
    ok = riskmod.RiskManager.verify_hub_attestation(attest, real_ca, nonce, "johns-risk")
    assert ok is False
    # Sanity: a correct attestation against the real CA verifies.
    good = border.risk.attest_hub(nonce)
    assert riskmod.RiskManager.verify_hub_attestation(good, real_ca, nonce, "johns-risk") is True
    border.manager.close()
