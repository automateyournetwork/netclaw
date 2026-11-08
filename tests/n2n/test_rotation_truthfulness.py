import asyncio
import datetime
from bgp.federation import certs,acme
from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService
from bgp.federation.rotation import RotationManager
import pytest


def setup(tmp_path):
    svc=FederationService(local_as=65001,router_id='4.4.4.4',display_name='fixture',manager=FederationManager(base_dir=str(tmp_path)))
    return svc,RotationManager(svc)


@pytest.mark.parametrize('kind',['risk-ca','hub','acme'])
def test_unchanged_certificate_is_not_renewed_or_retired(tmp_path,monkeypatch,kind):
    svc,rot=setup(tmp_path);pem,key=certs.create_self_signed('fixture')
    if kind=='risk-ca':monkeypatch.setattr(svc.risk,'ensure_risk_ca',lambda:(pem,key))
    elif kind=='hub':monkeypatch.setattr(svc.risk,'hub_credential',lambda **kw:(pem,key))
    else:
        async def renew(*args):return pem
        monkeypatch.setattr(acme,'renew',renew)
    rot.register(kind,'fixture',pem);cred=svc.manager.list_credentials()[0]
    try:
        assert asyncio.run(rot.renew_one(cred)) is False
        retained=svc.manager.list_credentials();assert len(retained)==1 and retained[0]['cert_pem']==pem
        assert retained[0]['state']!='retired'
        assert 'renewed' not in [r['kind'] for r in svc.audit.recent_cert_events(10)]
    finally:svc.manager.close()


def test_same_key_new_certificate_remains_active(tmp_path,monkeypatch):
    svc,rot=setup(tmp_path);old,key=certs.create_self_signed('fixture')
    certificate=certs.x509.load_pem_x509_certificate(old.encode())
    private=certs.serialization.load_pem_private_key(key.encode(),password=None)
    renewed=certs._cert_pem(certs.x509.CertificateBuilder().subject_name(certificate.subject).issuer_name(certificate.issuer).public_key(private.public_key()).serial_number(certs.x509.random_serial_number()).not_valid_before(certificate.not_valid_before_utc).not_valid_after(certificate.not_valid_after_utc+datetime.timedelta(days=30)).sign(private,certs.hashes.SHA256()))
    async def renew(*args):return renewed
    monkeypatch.setattr(acme,'renew',renew)
    rot.register('acme','fixture',old);cred=svc.manager.list_credentials()[0]
    try:
        assert asyncio.run(rot.renew_one(cred)) is True
        active=svc.manager.list_credentials();assert len(active)==1 and active[0]['state']=='active'
        assert active[0]['cert_pem']==renewed
    finally:svc.manager.close()


def test_host_certificate_renewal_preserves_peer_pin_and_private_key(tmp_path):
    svc,rot=setup(tmp_path/'local');peer,_=setup(tmp_path/'remote')
    old,key=svc.host_credential()
    peer.risk.check_peer_pin(svc.local_identity,old)
    rot.register('host-pinned',svc.local_identity,old);cred=svc.manager.list_credentials()[0]
    try:
        assert asyncio.run(rot.renew_one(cred)) is True
        new,new_key=svc.host_credential()
        assert peer.risk.check_peer_pin(svc.local_identity,new)=='match'
        assert new_key==key and certs.fingerprint(new)!=certs.fingerprint(old)
        assert svc.manager.list_credentials()[0]['state']=='active'
        assert not any(e['kind']=='overlap-opened' for e in svc.audit.recent_cert_events(10))
    finally:svc.manager.close();peer.manager.close()


def test_heartbeat_reports_failed_renewal(tmp_path):
    svc, rot = setup(tmp_path)
    svc.cert_mode = True
    pem, _ = svc.host_credential()
    try:
        assert svc._cred_status()['renew_state'] == 'unknown'
        rot.register('host-pinned', svc.local_identity, pem)
        assert svc._cred_status()['renew_state'] == 'ok'
        svc.manager.set_credential_state(certs.key_fingerprint(pem), 'failed')
        assert svc._cred_status()['renew_state'] == 'failed'
    finally:
        svc.manager.close()


def test_acme_renewal_requests_existing_pinned_key(tmp_path, monkeypatch):
    monkeypatch.setenv('N2N_LEGO_BIN', str(tmp_path / 'lego'))
    (tmp_path / 'lego').touch()
    monkeypatch.setenv('N2N_ACME_EMAIL', 'fixture@example.test')
    monkeypatch.setenv('N2N_ACME_DNS_PROVIDER', 'fixture')
    calls = []
    async def run(argv, **kwargs):
        calls.append(argv)
        return 0, ''
    monkeypatch.setattr(acme, '_run', run)
    asyncio.run(acme.renew('example.test', tmp_path))
    renew = [c for c in calls if 'renew' in c][0]
    assert renew[renew.index('renew') + 1:] == ['--days', '30', '--reuse-key', '--no-random-sleep']
