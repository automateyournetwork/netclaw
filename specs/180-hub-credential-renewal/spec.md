# Spec 180: The Border renews its hub credential

Created 2026-11-08; branch `180-hub-credential-renewal`, on 1.18.7; status:
implementation and verification. Found on an operator Border that had run past the
hub certificate's 90-day lifetime.

## Problem

`RiskManager.hub_credential()` issues the Border's hub certificate under the risk CA
once (90 days, `certs.issue_cert`) and afterwards returns `hub.crt` whatever its expiry.

- A Border running longer than 90 days presents an expired hub certificate. Members
  verify the hub attestation against the risk CA, reject it, and stop re-attaching
  on reconnect.
- The rotation schedule (spec 060) registers the hub credential and renews it at
  2/3 of its life by calling `hub_credential()`. It gets the unchanged certificate
  back, refuses it ("operator renewal is required") and the credential never renews.

## Requirements

- FR-001: Renewal reissues the hub certificate under the existing risk CA. The trust
  anchor members pinned does not change.
- FR-002: Renewal keeps the hub key. The hub key id stays the same, so identities
  that pin it (for example the protected-operations profile, spec 172) stay valid,
  and the rotation registry updates the same row instead of retiring it.
- FR-003: The rotation schedule renews the hub credential when it is due.
- FR-004: Without the rotation schedule, a hub certificate within 7 days of expiry is
  renewed the next time it is used (hub attestation).
- FR-005: A hub certificate that is not due is returned unchanged.

## Out of scope

Rotating the hub key or the risk CA itself; member leaf certificates.
