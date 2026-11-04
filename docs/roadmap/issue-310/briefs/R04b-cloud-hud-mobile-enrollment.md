# R04b — Cloud HUD and existing Mobile QR enrollment

Status: proposed bounded follow-up from the owner's November 4 steering; not
implemented or qualified by R04a. Keep R04a's VS Code delivery and historical
Mobile evidence distinct. This brief does not authorize a new cloud activation,
workload, version or public rollout.

## Outcome

The owner opens the cloud Border HUD, displays a device-enrollment QR, and scans
it using the existing Mobile registration flow. The enrolled phone reconnects
with its existing device key and exposes only the protected operations actually
supported by that Border. No replacement manual connection wizard, user sign-in
ticket, hidden login or new user-authentication scheme.

## Why this needs separate work

The existing scanner expects the established WSS challenge/key-possession
`in2n/enroll` protocol, then `in2n/hello`. The current protected cloud role exposes
neither a Mobile WSS listener nor HUD QR issuance, and deliberately refuses legacy
Ask execution. Its HTTPS operation review/decision/result contract differs from
legacy edge tasks and approvals. See the
[source and deployed-evidence assessment](../../../../specs/174-cloud-client-integration/mobile-qr-assessment.md).

## Bounded implementation tasks

1. Specify a device-only enrollment contract that preserves the existing scanner,
   key possession, single-use token and reconnect semantics. Keep device
   registration distinct from deferred user identities/SSO/RBAC. Define an exact
   protected device capability descriptor and origin/installation binding.
2. Add explicit HUD QR issuance using the existing native enrollment authority,
   with finite expiry, scoped device enrollment, no token logging and no public
   general-purpose daemon/admin route. Expired or spent codes require a fresh
   deliberate enrollment action; ambiguous enrollment must inspect retained state.
3. Provide the reviewed trusted WSS ingress and role/listener configuration within
   the existing cloud resource limits. Preserve HTTPS validation, device identity,
   Border confinement and rollback. Do not route phones to the raw iN2N TCP port.
4. Connect enrolled Mobile to the supported catalog, complete exact review, explicit
   decision, signed result and durable ACK using the existing protected backend.
   Preserve installation/device-scoped nonce and decision retention; historical
   approvals/principals remain unchanged. Legacy Ask, capture, voice, watch and
   background paths remain unavailable unless separately supported and verified.
5. Verify VS Code impact under G12 and Mobile impact under G13. Record an
   evidence-backed no-impact result where appropriate; do not silently defer either.

## Acceptance

- Actual cloud HUD QR issuance → existing native scanner → one enrolled device,
  with trusted TLS and persisted key identity; wrong domain/key, expired/spent QR
  and unauthorized method tests fail closed.
- Actual reconnect and process/background recovery retain the same enrollment and
  operation. No automatic reenrollment, prepare, decision or effect replay.
- One separately reviewed, approved bounded read returns the exact signed result
  and durable ACK. Unknown outcomes remain blocked; status/recovery adds no effects.
- Cloud legacy execution/admin routes remain closed; unrelated profiles/runtimes
  and retained authorities stay unchanged. Preserve private evidence and perform
  only reviewed cleanup of disposable resources.
- State simulator versus physical-device coverage, unsupported companion features,
  and deployment/lifetime limits explicitly. A separate manual cloud screen is
  not evidence that the QR acceptance path passed.
