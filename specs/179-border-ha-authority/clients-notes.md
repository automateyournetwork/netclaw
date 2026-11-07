# R08 HUD and editor implementation lane

Local implementation for T026, T028–T031 on `179-r08-clients`, based on the
frozen Spec179 client contract. No version change, publication, native client
qualification, provider/device/cloud operation or retained-runtime mutation.

## Implemented

- Shared bounded WebCrypto P256 verifier checks canonical Python JSON/domain,
  DER signatures, P256 SPKI fingerprints, certificate validity, signed endpoint
  membership, distinct node installations, explicit anchor, generation and
  monotone manifest revision. Public golden fixtures contain no private keys.
- Protected server accepts schema2 HA profile plus owned `ha-required.json`,
  checks the pinned HA config hash, verifies `cluster.info` discovery and exposes
  `/api/runtime.cluster` and exact `/api/hud/cluster`. HTTP requests keep node
  installation and add cluster ID/generation. Private bridge context is exact.
- HUD first connection requires explicit anchor acceptance over HTTPS. Cluster,
  generation and principal scope references within this origin. Status describes
  leader/follower/no quorum/fenced/retired; stale reviews cannot enable approval;
  missing original artifacts display retained result metadata. Enrolled endpoint
  navigation is explicit. Another origin requires status-only reference import;
  browser storage is never represented as replicated.
- Editor saves verified public cluster bindings, explicitly reviews the anchor,
  persists monotone manifests, and CAS selects an enrolled HTTPS node while
  preserving profile ID and cluster/principal operation reference namespace.
  Distinct node installations remain distinct. Original issuer reviews recover
  on successor nodes; sent/unknown decisions are not replayed. Native overview
  and evidence include authority and original result reference information.
- HA combined execution is not advertised or offered. Standalone combined flows
  and their independently retained child references stay unchanged. Redirects
  and automatic mutation retries remain refused.

## Verification

Qualified source runtime: Node24.19.0 at the existing spec155-native-tests path.
Extension TypeScript check and build pass. HUD Vite build passes with its existing
large-chunk warning. Focused shared/protected HTTP/browser tests:87 passed;
owner/editor profile suite:35 passed. Actual browser/editor qualification is
still T038/T039 and is coordinator-owned. These tests use FIXTURE observations;
none establishes REAL signed runtime acceptance.

The broad editor suite after build reported214 tests,211 pass,3 existing skips.
The initial pre-build run exposed missing `dist/assistant.mjs` in this fresh
worktree, then its old process appended cancellation output to the reused log.
Its exact owned test processes were stopped; no retained runtime was touched.
A fresh clean post-build adapter/stdio run passed both2 tests. Broad HUD suite passed538/538 tests.

## Integration and native qualification

Root supplies private `cluster.info` and HA operation DTOs, with configured
open-lab context available even during no quorum. Discovery is not an execution
permit. `result_reference` remains separate from a present verified artifact.
A retired node should remain in the signed manifest as a historical issuer;
removing historical signer metadata would require authenticated historical
manifest evidence before a client could accept that original review.

For T038 use the production protected server/build, selected HTTPS node origin,
explicit Trust cluster button, original retained operation IDs/nonces and real
signed result records. Capture leader/follower/no-quorum/stale-review states,
then navigate another manifest HTTPS origin and explicitly import original IDs.
Do not seed another origin's sessionStorage. Record zero added mutation calls on
status/reload/lost-result recovery.

For T039 build the source extension in an isolated Code1.109 profile. Add a new
Name/HTTPS URL connection, explicitly accept the anchor, prepare/review the real
original operation, then use Replace cloud Border endpoint for an enrolled
successor. Record same profile ID/cluster reference namespace, different node
installation, preserved sent marker, old review refusal and original result
reference. The existing cloud-editor driver is the launch entry; native modal
review and real signed record correlation are required separately from DTO tests.
