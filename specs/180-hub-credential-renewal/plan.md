# Plan

- `certs.issue_cert` gains an optional `key_pem` (as `create_self_signed` has), to
  reissue a leaf for an existing key.
- `RiskManager.hub_credential(renew=False)`: reissue with the existing `hub.key` when
  `renew` is set or the certificate expires within 7 days; otherwise return it.
- Renewal holds an `fcntl` lock on `risk-ca/.hub.lock` and writes both files with the
  atomic temp-file-and-rename helper (`_write_secret`, which gains a `mode`).
- `RotationManager.renew_one` calls `hub_credential(renew=True)` for kind `hub`.
- Tests in `tests/n2n/test_hub_credential_renewal.py`; the rotation test's stub takes
  keyword arguments.
