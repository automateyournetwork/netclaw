# Plan

- `certs.issue_cert` gains an optional `key_pem` (as `create_self_signed` has), to
  reissue a leaf for an existing key.
- `RiskManager.hub_credential(renew=False)`: reissue with the existing `hub.key` when
  `renew` is set or the certificate expires within 7 days; otherwise return it.
- Renewal (only) holds an `fcntl` lock on `risk-ca/.hub.lock` (opened `O_NOFOLLOW`,
  0600), re-reads under the lock and uses a certificate another process just renewed,
  and writes both files with the atomic helper (`_write_secret`, which gains a `mode`).
- `RotationManager.register_hub()`; the daemon's certificate lifecycle calls it at
  startup on a Border.
- `RotationManager.renew_one` calls `hub_credential(renew=True)` for kind `hub`.
- Tests in `tests/n2n/test_hub_credential_renewal.py`; the rotation test's stub takes
  keyword arguments.
