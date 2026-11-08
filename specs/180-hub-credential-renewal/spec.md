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
- The rotation schedule (spec 060, runs when `N2N_CERT_MODE` is on) never registered
  the hub credential, and its `hub` renewal path called `hub_credential()`, got the
  unchanged certificate back and refused it ("operator renewal is required").

## Requirements

- FR-001: Renewal reissues the hub certificate under the existing risk CA. The trust
  anchor members pinned does not change.
- FR-002: Renewal keeps the hub key. The hub key id stays the same, so identities
  that pin it (for example the protected-operations profile, spec 172) stay valid,
  and the rotation registry updates the same row instead of retiring it.
- FR-003: When the rotation schedule runs (`N2N_CERT_MODE` on), a Border registers its
  hub credential at startup and the schedule renews it at 2/3 of its life.
- FR-004: In every mode, a hub certificate within 7 days of expiry is renewed the
  next time it is used (hub attestation).
- FR-005: A hub certificate that is not due is returned unchanged.

- FR-006: Hub credential renewal is serialized across processes (daemon, rotation,
  install scripts) and replaces `hub.crt` and `hub.key` atomically. Reading a valid
  credential takes no lock and needs no write access.

## Known behaviour

- A member stores the hub certificate when its channel opens and checks that copy's
  validity. A channel that stays open across the old certificate's expiry closes then,
  and the member re-dials (`in2n-member.py`, within about 10 s) and receives the
  renewed certificate. With the schedule on, this happens at most once per renewal;
  without it, renewal happens within the last 7 days, when the member re-attests anyway.
- Protected operations (spec 172) compare the hub key id, not the certificate's
  validity, so they keep working across a renewal because the key is kept.
- A renewal that fails marks the registry row failed and the schedule does not retry
  it (pre-existing rotation behaviour); the 7-day on-demand renewal still applies.

## Out of scope

Rotating the hub key or the risk CA itself; member leaf certificates; concurrent
creation of a brand-new risk CA (`ensure_risk_ca`, unchanged).
