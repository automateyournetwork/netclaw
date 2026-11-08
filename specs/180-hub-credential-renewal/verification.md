# Verification

No credentials are recorded here.

## Tests

- `tests/n2n/test_hub_credential_renewal.py` (9 tests):
  - an expired hub certificate fails attestation; after renewal the member verifies it
    against the unchanged risk CA (this test fails on 1.18.7);
  - a valid credential is returned unchanged;
  - renewal keeps the key id (`protected_contract.key_id`) and extends `notAfter`;
  - `register_hub()` schedules the hub (kind, subject, renew-after before expiry) and
    `RotationManager.renew_one` renews it in place: one active registry row with the
    new certificate and the same key fingerprint; a member registers nothing;
  - a certificate with 30 days left is not renewed on demand, but is with `renew=True`;
  - after renewal `hub.key` is 0600, `hub.crt` 0644, and no temporary files remain;
  - four threads renewing at once leave a matching pair that members can verify;
  - reading a valid credential works with `risk-ca/` read-only.
- `tests/n2n/test_rotation_truthfulness.py` and `test_hub_attestation_060.py` pass.
- Full `tests/n2n` on the development host: 1463 passed. The same 8 failures and 158
  collection errors occur on unchanged `main` there; they come from packages not
  installed on that host (for example `service_identity`), not from this change.

## Live

The on-demand renewal (FR-004, first commit) has run on an operator Border since
2026-10-23: the expired hub leaf was reissued under the same CA and all members
re-attested. Keeping the key (FR-002), the scheduled path (FR-003) and the lock (FR-006) are
covered by the tests above, not yet by a live renewal; the daemon's startup call to
`register_hub()` is not exercised by a test; the next live renewal on that Border is
due by 2027-01-14 at the latest.

## Not verified

macOS; a Border with protected operations enrolled going through a live renewal.
