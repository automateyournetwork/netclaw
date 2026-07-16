"""US4/FR-019: posture surfaces channel-security state."""
import asyncio, os
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation import posture


def test_posture_channel_security_block(tmp_path):
    os.environ["N2N_CERT_MODE"] = "on"
    try:
        svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name="J",
                                manager=FederationManager(base_dir=str(tmp_path / "n2n")))
        svc.manager.upsert_peer(65007, "7.7.7.7")            # backfills legacy
        svc.manager.set_peer_trust("as65007-7.7.7.7", "pinned", verify_state="verified")
        svc.manager.upsert_peer(65099, "10.255.255.1")        # stays legacy → degraded
        p = asyncio.run(posture.compute_posture(svc))
        cs = p["channel_security"]
        assert cs["mode"] == "on"
        assert cs["by_trust_model"].get("legacy", 0) >= 1
        assert cs["degraded"] >= 1
        svc.manager.close()
    finally:
        os.environ.pop("N2N_CERT_MODE", None)
