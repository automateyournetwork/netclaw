# Tasks

- [x] T001 Reproduce: an expired hub certificate fails member attestation (regression test fails without the fix).
- [x] T002 Renew under the existing CA on demand within 7 days of expiry.
- [x] T003 Keep the hub key on renewal (`issue_cert(key_pem=...)`).
- [x] T004 Rotation schedule renews the hub credential explicitly.
- [x] T005 Tests: expired hub re-attests, valid credential unchanged, key id kept and validity extended, rotation renews in place.
- [x] T006 Release metadata.
