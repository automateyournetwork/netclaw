# R04b — Cloud HUD and existing Mobile QR enrollment

Status: **complete and owner accepted, 30/30 Spec175 tasks**. The stage began
with the owner's November 4 “04b time” instruction and explicit requirements for
easy local/cloud HUD and VS Code Mobile QR generation with actual virtual iPhone
verification. All four paths, native refusals, a successful protected read and
cold/background recovery passed. See
[Spec175 verification](../../../../specs/175-cloud-mobile-enrollment/verification.md)
and [handoff](../../../../specs/175-cloud-mobile-enrollment/resume.md).

On November 5, the owner accepted this completed scope and instructed packaging,
commit/PR/merge/publication and a website draft. Targets are source 1.18.6,
extension 1.6.1 and Mobile 1.0.4+7; actual release progress is tracked in
[release verification](../../../../specs/175-cloud-mobile-enrollment/release-verification.md).
No publication is claimed here. General cloud rollout remains held, R04a evidence
remains distinct, and the owner requires a **full stop before R05**.

## Outcome

The owner opens the cloud Border HUD, displays a device-enrollment QR, and scans
it using the existing Mobile registration flow. The enrolled phone reconnects
with its existing device key and exposes only the protected operations actually
supported by that Border. No replacement manual connection wizard, user sign-in
ticket, hidden login or new user-authentication scheme.

## Why this was a separate stage

The existing scanner uses the established WSS challenge/key-possession
`in2n/enroll` protocol, then `in2n/hello`. At kickoff, the protected cloud role
exposed neither a Mobile WSS listener nor HUD QR issuance and deliberately refused
legacy Ask execution. Its HTTPS operation review/decision/result contract differs
from legacy edge tasks and approvals. See the
[source and deployed-evidence assessment](../../../../specs/174-cloud-client-integration/mobile-qr-assessment.md).

## Bounded implementation scope

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


## Closure evidence — November 5

The actual local/cloud HUD and native VS Code Mobile views each generated a QR
that the iPhone simulator decoded, consumed once and used for retained-key
reconnection. The cloud flow reached the production protected operations screen.
Native refusal tests covered spent/expired enrollment, wrong domain/installation/
key and unauthorized methods; isolated source tests distinguish expiry from reuse.

The earlier `cloud-hud` operation returned a signed, acknowledged HTTP403. It and
its failed reference remain preserved. After the owner supplied a fresh credential,
a separately reviewed operation from the already enrolled `cloud-vscode` profile
returned NetBox prefix `10.112.0.0/15` successfully: one attempt, 2 provider calls,
2 inferences, 1 native MCP call, 1 HTTP200, verified signed result and durable ACK.
Actual cold launch and Home/background/resume recovered the same key, operation
and result without adding effects. Three historical rows stayed unchanged; all
four enrollment files remained byte-identical. The successful native framework
and XCTest receipts pass, with actual visible review/result/recovery captures.

Reviewed cleanup verified a 411-file export, retired only the new 3 stopped
containers and 1 empty internal network, and restored 101 containers/50 networks.
All four operation rows and evidence remained unchanged. The owned simulator was
shut down with keys/profiles retained; intended pilot/member services and the
original December 1 lifetime remain. No new cloud resource or general cloud
promotion was introduced. GAIT c25645d0 records technical completion, cleanup and
the owner's explicit scoped acceptance, closing T030. Physical camera,
SecureEnclave and other mobile platforms remain unqualified. R05 is stopped.
