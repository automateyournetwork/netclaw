"""US1 domain-verified path (T013): drive the lego ACME client. A fake lego
binary lets us prove the argv, env passthrough, cert parsing, and rotation
registration without a network or a real Let's Encrypt account."""

import asyncio
import os
import stat

from bgp.federation import acme, certs
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager


def _fake_lego(tmp_path, domain, cert_pem):
    """Write a fake lego that emits a cert to <path>/certificates/<domain>.crt,
    proving the driver invokes it with --path/--domains correctly."""
    binp = tmp_path / "lego"
    certout = tmp_path / "acmecerts"
    script = f"""#!/usr/bin/env python3
import sys, os
args = sys.argv[1:]
# find --path and --domains
path = args[args.index("--path")+1]
dom = args[args.index("--domains")+1]
d = os.path.join(path, "certificates")
os.makedirs(d, exist_ok=True)
open(os.path.join(d, dom + ".crt"), "w").write({cert_pem!r})
print("fake-lego ok for", dom)
"""
    binp.write_text(script)
    binp.chmod(binp.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(binp)


def test_issue_parses_cert_and_registers_for_rotation(tmp_path, monkeypatch):
    domain = "netclaw.automateyournetwork.ca"
    cert_pem, _ = certs.create_self_signed(domain, days=90)
    fake = _fake_lego(tmp_path, domain, cert_pem)

    monkeypatch.setenv("N2N_LEGO_BIN", fake)
    monkeypatch.setenv("N2N_CLAW_DOMAIN", domain)
    monkeypatch.setenv("N2N_ACME_DNS_PROVIDER", "godaddy")
    monkeypatch.setenv("N2N_ACME_EMAIL", "ptcapo@gmail.com")
    monkeypatch.setenv("N2N_ACME_STAGING", "1")

    assert acme.configured() is True

    svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name="John",
                            manager=FederationManager(base_dir=str(tmp_path / "n2n")))
    got = asyncio.run(acme.ensure_domain_credential(svc))
    assert got and "BEGIN CERTIFICATE" in got
    # Registered in the credential registry as an acme credential for rotation.
    creds = [c for c in svc.manager.list_credentials() if c["kind"] == "acme"]
    assert creds and creds[0]["subject_identity"] == domain
    assert creds[0]["renew_after"] is not None
    svc.manager.close()


def test_not_configured_is_noop(tmp_path, monkeypatch):
    monkeypatch.delenv("N2N_CLAW_DOMAIN", raising=False)
    monkeypatch.delenv("N2N_ACME_DNS_PROVIDER", raising=False)
    assert acme.configured() is False
    svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name="J",
                            manager=FederationManager(base_dir=str(tmp_path / "n2n")))
    assert asyncio.run(acme.ensure_domain_credential(svc)) is None
    svc.manager.close()
