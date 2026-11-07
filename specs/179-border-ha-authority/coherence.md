# Spec179 maintainer coherence

This record describes source integration. Actual FIXTURE, REAL, browser, native
Code and native iOS qualification remain separate gates in
[qualification-matrix.md](qualification-matrix.md). It does not mark T035–T041,
R08 or the complete roadmap accepted. R09 deployment and regional service
continuity are separate work; issue310 publication/version holds remain.

## Private setup and diagnosis

An explicitly provisioned HA home has private `protected-profile.json` schema2,
an exact hashed HA config, a signed bounded manifest pinned to an enrolled root,
and durable `ha-required.json`. Border role config owns scoped etcd credentials;
members and clients do not. Role launch schema3 verifies the whole immutable
source/Python closure and profile before the actual federation daemon starts.
No standalone endpoint registry or environment toggle can substitute for this
contract. `.env.example` records that distinction without exposing a setup path.

The existing private `scripts/ha-cluster.py` CLI binds an exact config path/hash:
status and export read current state, while drain/resume/retire and voter changes
require current maintenance authority. Fenced restore uses a new generation,
exact snapshot and actual isolation evidence. It cannot silently activate a stale
snapshot, release unknown reservations or erase the prior generation. See
[authority contract](contracts/authority.md), [recovery contract](contracts/recovery.md) and the CLI source for exact
arguments. The serial source rehearsal is documented in
[labs/ha/real-runtime.md](../../labs/ha/real-runtime.md).

Ordinary setup is deliberately unable to create or upgrade this cluster profile.
The shared `scripts/lib/ha_setup_guard.py` refuses standalone writes when any HA
marker exists, including malformed or dangling markers; profile2/HA metadata also
refuses downgrade if the marker is missing. Ambiguous protected profile metadata
fails closed. It does not remove, rewrite, migrate or repair protected state.
Guards cover legacy install/setup entry points, the N2N component step, source-plan
target/resume/file writes, Risk configuration/enrollment, remote transport import
and legacy member-home provisioning. Readiness refuses generic MCP/model probing
of those homes, because it cannot establish current quorum execution authority.
Existing ordinary new-home/standalone behavior remains covered by regression tests.

## Surface and artifact accounting

| Surface | Disposition |
|---|---|
| NCFED cluster | Private signed identities and strict mutual TLS; no generic proxy authority |
| iN2N member | Three attachments; production guarded Ollama/OpenClaw/native subnet path only |
| eN2N | Existing standalone behavior retained; external endpoint failover is not qualified here |
| HUD | Explicit cluster trust, current authority, stale/unknown state and retained references |
| VS Code | Trusted endpoint selection, exact native review and original-reference recovery |
| Mobile | P256 device authority, shared enrollment/revocation, retained key/subject/reference and bounded trusted endpoints |
| Installer/catalog | Existing components only; updated source effect/skill hashes; no advertised HA wizard or cloud deployment path |
| Operator CLI | Private status, lifecycle, voter changes, export and fenced restore |
| Environment | Private profile/manifest declaration; no new secret-bearing `.env` examples |
| SOUL/TOOLS/skills/protocol docs | Maintainer fencing/recovery guidance and explicit evidence limits |

Component counts remain **112 installer components, 239 skills and 178 MCP
integrations**. No MCP server, runtime framework, public admin endpoint, new
component or client framework was added. Canonical catalog generation, metadata
hashes and inventory checks must pass together after integration.

## Evidence limits

Fixture callbacks do not qualify model or native effects. REAL packets preserve
original approval/member result/successor ACK, source pins, actual inference and
native artifacts, and referenced GAIT commits. One durable shared budget spans
runner/HUD/Code/Mobile; unknowns stay reserved. Native app compilation or a Dart
unit test does not qualify iOS background/cold/failover behavior. Actual owned
resource cleanup and preservation checks follow exported evidence, never a
claimed success or a timeout. Final counts, fault rows and human acceptance must
come from the coordinator's completed evidence ledger.

## Source verification — 2026-11-07

The focused setup/readiness/catalog/transport preservation suite passed 113 tests
and 22 subtests. The guard plus legacy Convergence/Hermes/DefenseClaw member suite
passed 80 tests. Those suites overlap in the guard tests; their totals are not
an aggregate. Coverage includes malformed/dangling HA markers, missing-marker
profile2, plan resume, enrollment/transport import, provider-probe refusal and a
marker appearing before an actual file write. Ordinary macOS temporary-home
provisioning remains compatible. Catalog metadata, generated parity, inventory
counts, shell syntax and whitespace checks passed. These are source checks only.
