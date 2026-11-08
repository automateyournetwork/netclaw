# Spec179 Mobile implementation lane

Source branch: `179-r08-mobile`, based on coordinator checkpoint `f37d676e`.
This lane implements T027/T032/T033 source and prepares T040 harness source.
Coordinator-owned integration, real quorum/runtime evidence and native execution
are separate acceptance work; this document does not mark those tasks complete.

## Implemented

- `ha/edge.py` stores device registrations, single-use challenge digests,
  enrollment-token hashes and revocation in the existing quorum Authority CAS.
  Challenge lifetime is30 seconds, offer lifetime120 seconds, at most64 live
  challenges,128 retained offers and manifest-bounded32 devices. Revoked device
  identities are retained. Device proofs require valid P256 certificates and
  bind exact cluster generation, serving node, installation, nonce, purpose,
  member and token digest. No Risk/SQLite fallback exists.
- Enrollment/revocation atomically maintains
  `edge-principals/<principal.subject>` for coordinator-owned operation/admission
  CAS. Forwarded protected calls carry exact device-signed method/parameter
  proofs. `verify_request` mints a native `VerifiedClusterDevice`; serialized
  principals never become authority. `ClusterDeviceAuthority.refresh()` performs
  its fresh registry read off the event loop. The root service supplies actual
  authenticated ingress and checks active principal in every effect gate.
- The cluster mobile enrollment adapter returns the existing bounded QR matrix
  DTO and adds explicit cluster/generation/anchor/manifest/node pins plus the
  offer client nonce. Tokens are present only in the transient matrix. Exact
  trusted HTTPS discovery verifies the signed manifest before any key proof.
- Mobile verifies Python canonical manifests with platform P256/SHA256 public
  crypto, validates P256 SPKI and X509 time bounds, rejects duplicate JSON keys,
  unknown schema fields, wrong identities, manifest rollback or same-revision
  content changes, untrusted anchors, retired/fenced nodes and changed subjects.
  The verified descriptor is deeply immutable. No TLS bypass or redirect is
  permitted; WSS independently uses platform certificate/hostname verification.
- The retained device key/subject/enrollment generation survive explicit
  selection among at most three manifest endpoints. Selection uses a retained-key
  hello only and atomically updates routing after verification; cancellation or
  stale storage prevents the commit. A newer verified manifest is persisted
  before subsequent use on same-node reconnect. Pending enrollment identity and
  monotone operation send markers remain retained on unknown outcomes.
- Secure operation storage uses cluster+generation+device-subject audience,
  independent of the selected node's installation/origin. Each protected WSS
  call receives a domain-separated signed request proof. HA catalog is limited
  to `cluster_execution_v2`; combined operations remain unavailable.
- Original review issuer identity is checked against the signed manifest.
  New authority epochs make old reviews non-actionable. Quorum failure disables
  new preparation/approval and preserves local references. Original result
  references remain visible while an artifact is unavailable; reconciliation
  remains tied to the same operation. Standalone behavior stays supported.

## Validation

- Python26 tests pass: HA registry/proofs7, standalone mobile enrollment17 and
  protected Mobile capability2. These are source/state-machine tests, not real
  etcd or real provider/native execution evidence.
- Flutter full suite524 passed after the initial implementation. The full524 suite passed again after manifest high-water persistence and
  recovery refinements. The final handshake-binding test was then added and
  the cluster/protected-device suites20 passed. Flutter analyzer reports no issues. The coordinator should
  repeat integrated checks after cherry-picks/wire changes as needed.
- Seven new Mobile tests include actual macOS CryptoKit verification of canonical
  Python golden manifests and signature-negative mutations, duplicate-key/depth
  limits, retained pending pins, stable secure-storage audience, stale epoch and
  no-quorum approval refusal, and explicit alternate-node identity retention.
  Tests compile the exact production public verifier into a temporary source-test
  executable; non-macOS runs explicitly skip those native CryptoKit tests.
- Production `ClusterPublicCrypto.swift`, `EdgeIdentityPlugin.swift`, existing
  `X509SelfSigned.swift`, and qualification `R08SimulatorPlugin.swift` compiled
  successfully for both arm64 and x86_64 iOS Simulator targets via `swiftc`.
- Full Flutter simulator app build first required a watch-companion destination.
  Generic Xcode compilation then stopped on the existing ignored
  `ios/Runner/GoogleService-Info.plist` absence in this isolated worktree. No
  retained owner Firebase configuration was copied. This is not a completed
  whole-app build or simulator-run claim. Android native compilation/execution
  has not been performed in this lane.

## Integration seams and remaining evidence

The coordinator owns `service.py`, `protected_service.py`, HA factory, NCFED
forwarding and operation ledger. Wire `service.ha_edge`, channel `ha_challenge`
and `ha_binding`, and await async cluster mobile issue/status results. WSS
capabilities carry `border.cluster`, basic five protected methods and
`protected_operations.enrollment_generation`. Unknown authority observations use
`no_quorum`, never follower/leader with a null epoch. Forwarded original params
include serving `installation_id` plus `device_proof`; verify the exact ingress
installation and parameters independently at the leader, then use the principal
index inside every operation/admission CAS.

Native source is in `integration_test/cluster_recovery_test.dart`, its adjacent
procedure, and the isolated R08 simulator plugin. Existing QR native
enroll/prepare/approve/recover phases now check explicit cluster pins and stable
device authority. The new recovery driver exercises native alternate selection,
host-recorded quorum/leader faults, background/resume and cold restart against
the exact original REAL signed operation. It never prepares, approves or
reconciles. No simulator was booted, installed or launched by this lane, and no
provider, device, cloud or retained runtime was touched. The real operation,
signed result/ACK, GAIT and independent effect counts remain coordinator work.

Local Python commits: `f34c013f`, `b9a4a61f`. No push, PR, version change,
publication or shared GAIT branch mutation was performed.
