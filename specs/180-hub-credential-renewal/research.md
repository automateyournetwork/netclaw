# Research

- `hub_credential()` returned `hub.crt` whenever it existed (`risk.py`); the leaf is
  issued for 90 days (`certs.issue_cert(days=90)`).
- Members verify `attest_hub` against the pinned risk CA (`verify_hub_attestation`),
  which rejects an expired leaf. The anchor does not need to change, only the leaf.
- The daemon's certificate lifecycle (`_start_cert_lifecycle`, only with
  `N2N_CERT_MODE` on) registered the host or ACME credential but never the hub.
- `RotationManager.renew_one` (spec 060) renews kind `hub` by calling
  `hub_credential()` and refuses an unchanged certificate (`_validate_successor`), so
  the scheduled renewal could never succeed. It renews at
  `CERT_RENEW_FRACTION_DEFAULT` (2/3 of life, about day 60).
- `issue_cert` generated a new key on every call. The hub key id is pinned by the
  protected-operations profile (`protected_service.py`: `key_id(own_cert) ==
  identity['key_id']`), so a renewal with a new key would break protected
  operations on that Border. Reusing the key avoids that; `create_self_signed`
  already takes `key_pem` for the same reason.
- Spec 1.18.x `acme.py` renewal (#318) covers domain certificates, not this leaf.
