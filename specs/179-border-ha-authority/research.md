# R08 research and decisions

Research 2026-11-07; source base a4905469. This is design evidence, not runtime qualification.
Three read-only research agents examined authority, clients and qualification.

## R1 — NCFED remains the application foundation

Decision: reuse FederationChannel framing/dispatch and strict TLS1.3 exporter
transport. Introduce a separately enrolled cluster role/channel and namespace
inside protocol-mcp federation; use existing iN2N for members and unchanged eN2N
for independently administered organizations. No new MCP server or custom HTTP
application transport. etcd is the private coordination dependency only.
Rationale: owner explicitly reaffirmed NCFED during SDD; existing identity and
scope checks remain owning controls. Alternatives rejected: mapping cluster
membership from eN2N consent/AS number; direct member etcd access; replacing NCFED.

## R2 — Established quorum, bounded per-key state

Decision: pinned etcd3.6.16, three voters; separate client/peer mTLS and scoped
RBAC credentials, private direct TCP; leader lease12s, renew at3s on an independent
loop. Exact value+mod_revision comparisons fence mutations. Durable membership,
approvals, claims, reservations and evidence references are unleased. Per-key
bounded records avoid rewriting an aggregate database. Reads are linearizable;
watch/status cache never authorizes. Mutations are single-attempt; a lost reply
is unknown, and only exact committed-record readback can reconcile it.

Official release confirms3.6.16 as a supported patch;3.7 upgrade is unnecessary
for the selected APIs. Review transitive/image provenance before actual lab start.
Existing local official ARM64 digest:
`sha256:a763c581b5d8cdf5247c5b22f2e0dba1f19f0c45031e8c324b06c5ed4f60a14f`.

Sources: [release](https://etcd.io/blog/2026/oct-22-patch-release/),
[API guarantees](https://etcd.io/docs/v3.6/learning/api_guarantees/),
[failure modes](https://etcd.io/docs/v3.6/op-guide/failures/),
[transport security](https://etcd.io/docs/v3.6/op-guide/security/),
[tuning](https://etcd.io/docs/v3.6/tuning/).
Alternatives: new custom Raft/election was rejected for proof/maintenance risk;
DNS or endpoint pooling supplies routing but cannot authorize; provider-specific
coordination would bind the shared R08 architecture to one cloud.

## R3 — Admission and physical effect are separate boundaries

Decision: fresh member nonce bound to cluster generation, leader incarnation/
epoch, approval, member incarnation, operation/attempt, model/tool ordinal and
exact request digest. A quorum transaction consumes the claim. Member consumption
is one-use in its private durable journal, within3s monotonic round-trip and with
wall/monotonic divergence <=250ms. These are proposed qualification bounds;
measure and adjust explicitly before acceptance. No clock timestamp alone authorizes.
A paused process, deadline failure or ambiguous result retains the spent claim.

An admission committed immediately before loss may begin within the admission
window and finish under existing execution deadlines; each subsequent model/tool
boundary requires another fresh claim. There is no atomic transaction between etcd and arbitrary external effect.
“No new work” means no new quorum admission can commit. Existing resource/runner
exclusion prevents conflicting/new-ID work; unknowns remain until signed original
completion or a separately verified no-effect recovery. No automatic redispatch.

NetClaw seams: protected_service.effect_authorize/_execute and protected_store
already own native effect claims. ScopedInference.invoke in protected_runtime
requires a mandatory HA gate before every actual forward, wired from
protected_docker. Missing gates/old runtime profiles refuse in HA mode. A durable
HA-required marker prevents a missing adapter/config becoming standalone fallback.

## R4 — Versioned logical audience and metadata handoff

Decision: explicit version2 protected envelopes for HA with cluster binding,
separate node signer/installation, original issuer and current admission authority.
Standalone v1 remains exact and unchanged. Open-lab principal derives from cluster
audience in HA; device-key identity remains the enrolled device. Do not substitute
a cluster UUID for node installation or share node private keys.
Shared operation headers/approvals/revocations and dispatch claims permit a new
leader to reconcile by original ID. Raw signed results stay with the member and
bounded immutable node artifacts; quorum stores hashes/retrieval references.
New leader may retrieve/re-ACK original evidence but never reconstruct a new attempt.

## R5 — Clients are affected separately

HUD reference/installation header, VSCode origin+installation+principal profile,
and Mobile enrollment/HTTPS/WSS bindings currently name one Border. Add explicit
cluster descriptor and trusted endpoint set, checked node identity and monotone
manifest revision. No redirects or automatic write retries. Browser storage stays
origin-isolated; another origin needs explicit status-only original-reference recovery.
Mobile needs shared enrollment/revocation records, not merely an endpoint list.
Native existing R07 client harnesses used controlled DTOs; they cannot qualify
R08 actual HA execution. Bind new native journeys to actual signed member results.

## R6 — Fixture then real runtime

Decision: fresh local three-node/voter lab with authenticated directed fault
injection, then actual NetClaw OpenClaw2026.7.1-2 / DefenseClaw1.0.4 /
Ollama0.40.11 / Qwen3:0.6b / native subnet MCP, fresh source/image/profile hashes.
Read-only192.0.2.0/26 summary: authoritative native facts64addresses/62usable.
At most10 distinct approved operations,20inferences,10native effects, one native
operation concurrently;180s operation/60s inference limits. Separate controlled
faults are explicitly FIXTURE; zero-added-call negatives can exercise REAL binding.
No hosted provider/device/cloud call is necessary for this selected profile.

Voter bounds512MiB hard/384MiBGo target/0.6CPU,128MiBbackend quota with measured
compaction; model2GiB/no-swap/2CPU and agent1536MiB/no-swap. Thermidor192MiB voters
OOMed and aggregate ledger writes inflated WAN/quota usage. Its current HA model,
guard and effects are synthetic and production broker HA is refused. Adapt lessons
and scenario contracts, not runtime/authority/qualification or Tailscale.

## R7 — Retirement and restore

Normal node restart uses current authority. Disaster restore is a separate trusted
operator workflow: export consistent evidence, prove all old voters AND executors
isolated using exact owned process/container identities, create a new fenced
generation and fresh trust, preserve unknown reservations, then explicitly activate.
No unchecked operator boolean, UUID change or force-cluster flag is proof.
Old private state remains evidence, never a reusable activation payload.

## Scope decisions

Three-region GCP, replicated cloud workloads, external eN2N ingress failover,
users/SSO/RBAC, physical iPhone and new Windows/WSL qualification remain outside R08.
Standalone OpenClaw/Hermes remains supported; unqualified HA runtime profiles refuse.
No unresolved design choice is silently treated as qualification.

## R8 — Review corrections before implementation

NCFED exporter transport currently authenticates TLS servers and mutually proves
application key possession; it does not require TLS client certificates. Cluster
mTLS needs explicit optional client cert/key and server peer-CA verification,
including fail-if-no-peer-certificate, while preserving existing iN2N defaults.
Cluster frame decoding must reject duplicate JSON keys and unknown fields. Use
n2n/cluster/* handlers separate from eN2N/iN2N and retain R07 post-await checks;
never block synchronous authority predicates with network consensus reads.
An old restore snapshot may omit admitted work. Reconcile missing evidence or
conservatively freeze affected runners/resources;new generation is not proof of
no old effect. These corrections are reflected in contracts/qualification matrix.
