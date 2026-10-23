"""Long-lived Borders renew hub credentials without changing member trust."""
import datetime

from bgp.federation import certs
from bgp.federation.manager import FederationManager
from bgp.federation.risk import RiskManager


def test_expired_hub_reconnects_under_existing_anchor(tmp_path, monkeypatch):
    manager = FederationManager(base_dir=str(tmp_path))
    try:
        risk = RiskManager(manager)
        risk.set_role('border', risk_name='test-risk')
        anchor, ca_key = risk.ensure_risk_ca()
        now = certs._now_utc()
        with monkeypatch.context() as patch:
            patch.setattr(certs, '_now_utc', lambda: now - datetime.timedelta(days=100))
            expired, key = certs.issue_cert(anchor, ca_key, 'test-risk/border')
        directory = risk.keys_dir / 'risk-ca'
        (directory / 'hub.crt').write_text(expired)
        certs._write_secret(directory / 'hub.key', key)
        nonce = b'fresh-member-challenge'
        assert not RiskManager.verify_hub_attestation(
            {'hub_cert': expired, 'hub_sig': risk.sign_challenge(key, nonce).hex()},
            anchor, nonce, 'test-risk')
        attestation = risk.attest_hub(nonce)
        assert RiskManager.verify_hub_attestation(attestation, anchor, nonce, 'test-risk')
        assert risk.risk_ca_pem() == anchor
        assert risk.hub_credential()[0] == attestation['hub_cert']
    finally:
        manager.close()
