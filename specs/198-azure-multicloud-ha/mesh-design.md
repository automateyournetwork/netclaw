# Six-Border Azure/GCP mesh

Actual completed live qualification: [closure](closure-20261124.md),
[binding contract](contracts/cross-cloud-federation.md), [verification](verification.md).
The historical dual-enrollment proposal is superseded by this design.

## Topology and authority

Two independent three-voter etcd authorities run on three distinct regions each:
Azure Canada Central/East US2/Sweden Central and GCP Montreal/Belgium/Singapore.
Each member belongs to exactly one group and keeps its own durable effect/result
ledger. Mac subnet and NetBox members attach outbound to their group's three
Borders; the physical GCP NetBox member belongs to GCP. All six ingresses expose
the signed union catalog through the explicitly configured peer connection.
There is no six-voter authority and no dual-group member identity.

The measured authenticated attachment round trip selects the nearest live Border.
That measurement includes attestation/quorum processing and is not a pure network
ping. A follower forwards to its current leader; proximity never grants authority.
The signed qualification admission window is9000ms. One admission RPC waits for
that window, never retries another attachment, and retains the existing monotonic
consume/effect-boundary expiry checks, quorum proof and single-use nonce journal.

## Cross-group execution and clients

The ingress authenticates its own operator and sends one exact, signed peer relay
under the pinned peer policy. The receiving group authorizes the operation under
its own principal, manifest, lease and epoch, retaining origin cluster/principal/
nonce provenance. Its internal idempotency key namespaces the original nonce by
origin; its operation UUID remains the identifier used by the ingress client.
Status returns the original public client nonce consistently. Each effect still
requires fresh receiving-group admission and the member retains its signed result
until the receiving authority durably ACKs it. An uncertain response is retained
and fenced; it does not authorize another dispatch or a substitute member.

The ingress endorses the exact peer DTO and public enrollment with its own pinned
node signature. HUD and VS Code verify this endorsement, the receiving public
manifest/certificates, original principal/nonce, remote authority epoch and exact
immutable review. A peer identity is never silently treated as local identity.
The endorsement grants no execution permission. Saved recovery references remain
bounded non-secret identifiers; original results/ACKs are recovered without a
second approval or effect.

## Acceptance and retirement

The required matrix is six local plus six cross-group completed operations, with
all four follower ingresses represented. Actual HUD and native Code approval and
GET-only cold recovery, a physical cloud NetBox read, and a GCP operation after
observed leader change are separate witnesses. Guard-unavailable tests run after
the positive cases. A rendered catalog, a checkbox or a fixture cannot substitute
for those results.

Fresh signed generation2 ran on the original seven VMs with unchanged deadlines
and reservations. Generation1's unknown operation, identities, databases and
quorum state were exported before replacement and remain retained. Final teardown
must export all current evidence first, verify all exact run-owned VMs/disks/IPs/
firewalls and both generations' DNS absent, stop owned Mac qualification members,
and close ledger/watchdog state only after verified cloud absence. The Spec200
checkout/evidence and unrelated owner services remain preserved.
