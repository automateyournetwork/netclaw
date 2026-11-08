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


def _border(tmp_path):
    manager = FederationManager(base_dir=str(tmp_path))
    risk = RiskManager(manager)
    risk.set_role('border', risk_name='test-risk')
    return manager, risk


def test_valid_hub_credential_is_not_reissued(tmp_path):
    manager, risk = _border(tmp_path)
    try:
        first = risk.hub_credential()
        assert risk.hub_credential() == first
    finally:
        manager.close()


def test_renewal_keeps_the_hub_key_and_extends_validity(tmp_path, monkeypatch):
    from bgp.federation.protected_contract import key_id
    manager, risk = _border(tmp_path)
    try:
        anchor, ca_key = risk.ensure_risk_ca()
        now = certs._now_utc()
        with monkeypatch.context() as patch:
            patch.setattr(certs, '_now_utc', lambda: now - datetime.timedelta(days=85))
            old_cert, old_key = certs.issue_cert(anchor, ca_key, 'test-risk/border')
        directory = risk.keys_dir / 'risk-ca'
        (directory / 'hub.crt').write_text(old_cert)
        certs._write_secret(directory / 'hub.key', old_key)
        new_cert, new_key = risk.hub_credential()
        assert new_cert != old_cert
        assert key_id(new_cert) == key_id(old_cert) and new_key == old_key
        assert certs.cert_not_after(new_cert) > certs.cert_not_after(old_cert)
    finally:
        manager.close()


def test_rotation_renews_the_hub_on_its_schedule(tmp_path):
    import asyncio
    from bgp.federation.service import FederationService
    from bgp.federation.rotation import RotationManager
    svc = FederationService(local_as=65001, router_id='4.4.4.4', display_name='fixture',
                            manager=FederationManager(base_dir=str(tmp_path)))
    try:
        svc.risk.set_role('border', risk_name='test-risk')
        rot = RotationManager(svc)
        assert rot.register_hub() is True
        cert, _ = svc.risk.hub_credential()
        cred = svc.manager.list_credentials()[0]
        assert cred['kind'] == 'hub' and cred['subject_identity'] == 'test-risk/border'
        assert cred['renew_after'] < cred['not_after']
        assert asyncio.run(rot.renew_one(cred)) is True
        renewed, _ = svc.risk.hub_credential()
        assert renewed != cert and certs.key_fingerprint(renewed) == certs.key_fingerprint(cert)
        active = [c for c in svc.manager.list_credentials() if c['state'] != 'retired']
        assert len(active) == 1 and active[0]['cert_pem'] == renewed
    finally:
        svc.manager.close()


def test_thirty_days_left_is_not_renewed_on_demand(tmp_path, monkeypatch):
    manager, risk = _border(tmp_path)
    try:
        anchor, ca_key = risk.ensure_risk_ca()
        now = certs._now_utc()
        with monkeypatch.context() as patch:
            patch.setattr(certs, '_now_utc', lambda: now - datetime.timedelta(days=60))
            cert, key = certs.issue_cert(anchor, ca_key, 'test-risk/border')
        directory = risk.keys_dir / 'risk-ca'
        (directory / 'hub.crt').write_text(cert)
        certs._write_secret(directory / 'hub.key', key)
        assert risk.hub_credential() == (cert, key)
        renewed, _ = risk.hub_credential(renew=True)
        assert renewed != cert
    finally:
        manager.close()


def test_renewal_writes_files_safely(tmp_path):
    import stat
    manager, risk = _border(tmp_path)
    try:
        risk.hub_credential()
        risk.hub_credential(renew=True)
        directory = risk.keys_dir / 'risk-ca'
        assert stat.S_IMODE((directory / 'hub.key').stat().st_mode) == 0o600
        assert stat.S_IMODE((directory / 'hub.crt').stat().st_mode) == 0o644
        assert not [p for p in directory.iterdir() if p.name.startswith('.credential-')]
    finally:
        manager.close()


def test_concurrent_renewals_leave_a_matching_pair(tmp_path):
    import threading
    from bgp.federation.protected_contract import key_id
    manager, risk = _border(tmp_path)
    try:
        first_cert, _ = risk.hub_credential()
        errors = []

        def renew():
            try:
                for _ in range(5):
                    risk.hub_credential(renew=True)
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)
        threads = [threading.Thread(target=renew) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        cert, key = risk.hub_credential()
        assert key_id(cert) == key_id(first_cert)
        nonce = b'after-concurrent-renewal'
        attestation = risk.attest_hub(nonce)
        assert RiskManager.verify_hub_attestation(attestation, risk.risk_ca_pem(), nonce, 'test-risk')
    finally:
        manager.close()


def test_member_does_not_register_a_hub(tmp_path):
    from bgp.federation.service import FederationService
    from bgp.federation.rotation import RotationManager
    svc = FederationService(local_as=65001, router_id='4.4.4.4', display_name='fixture',
                            manager=FederationManager(base_dir=str(tmp_path)))
    try:
        assert RotationManager(svc).register_hub() is False
        assert svc.manager.list_credentials() == []
    finally:
        svc.manager.close()


def test_reading_a_valid_credential_needs_no_write_access(tmp_path):
    import os
    manager, risk = _border(tmp_path)
    try:
        first = risk.hub_credential()
        directory = risk.keys_dir / 'risk-ca'
        lock = directory / '.hub.lock'
        if lock.exists():
            lock.unlink()
        os.chmod(directory, 0o500)
        try:
            assert risk.hub_credential() == first
        finally:
            os.chmod(directory, 0o700)
    finally:
        manager.close()
