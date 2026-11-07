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

## Native qualification source follow-up

Added `labs/ha/client_qualification.mjs`, public evidence helpers and
`extensions/netclaw-vscode/test/editor-ha.cjs`, selected by
`NETCLAW_CLOUD_SCENARIO=ha`. The coordinator supplies actual private URLs, Code
binary/profile, SHA-pinned REAL records and cumulative runtime counters later.
Drivers retain screenshots and append-only before-send artifacts. Original-once
and prepare-only phases use exclusive durable one-shot locks; recovery phases
refuse every mutation. Both read the same P256-signed original result/ACK and
record explicit acceptance limits. No native phase was launched in this lane.
See `labs/ha/CLIENT-QUALIFICATION.md` for the exact input and phase contract.

Read-only integration review found unknown follower discovery and quorum-dependent
status reads; root's fb075bb4 addresses those with no_quorum discovery, fresh WSS
authority observation and bounded private open-lab status-only fallback. HUD/editor
now visibly label retained status with last-observed time/reason, and HUD disables
reconciliation of retained observations. A separate stale-deny epoch check issue
was reported to root; this lane did not edit Python service files.

Source helper tests6/6 passed (including no native launch on import, signed
artifact tamper rejection and one-shot retry refusal); HUD affected view tests32/32
passed; TypeScript and driver syntax checks passed. Actual Code/Chromium DOM,
operating HTTPS, screenshots and REAL acceptance remain coordinator-run T038/T039.

## Native effect boundary review and adapter

Independent source review found that admission freshness preceded awaited Docker
preflight and native MCP startup. Root moved model checks to the synchronous
stdin handoff and delegated the MCP transport fix to this lane. The first SDK
memory-stream wrapper still had a scheduling gap before its background writer.
`ha/mcp_transport.py` now implements the official ClientSession stream seam with
an owned asyncio subprocess, bounded official JSON-RPC parsing, and synchronous
tool-byte handoff in the caller's task. It has no background write queue or SDK
patch. Admission is resolved after serialization and immediately before the pipe
write; initialized/list-tools preflight needs no effect permission.

One tools/call attempt is permitted per transport. The frame must fit the actual
POSIX atomic pipe limit (also capped at4096bytes;512bytes on this Mac). A full
pipe aborts its queued atomic frame synchronously, preserving the spent claim.
Expired/inactive/duplicate scopes, backpressure and oversize frames fail closed.
Owned process groups have bounded EOF/TERM/KILL cleanup. Other OS transports are
explicitly unqualified; standalone keeps its existing SDK transport.

20 controlled transport tests pass, including an actual official MCP2.3.0 session,
an actual saturated OS pipe with no delayed tool bytes, late admission, expiry
during serialization, malformed/partial/bounded input and cancellation cleanup.
Related admission/runtime/native-MCP tests plus these tests pass95/95. Initial
tests exposed the SDK2.3 JSONRPCMessage union (fixed using public TypeAdapter);
one mistyped test path selected no tests and was corrected before the95-test run.
These are controlled temporary stdio fixtures, not actual native workload, REAL
or T034 fixture acceptance. Root owns protected_mcp/Docker/admission integration
and the production-callback regression checks. No model/provider/device call or
native browser/editor qualification ran in this lane.

## Shared REAL budget claim integration

The browser/editor original-once drivers now wait for a coordinator-owned private
budget claim after actual native preparation. They validate the exact run,
operation, nonce, review, surface, claim hash and per-operation limits, retain the
claim in evidence, and recheck it before the approve tap and outgoing decision.
The coordinator must reserve and claim_send in the shared REAL budget before
atomically publishing the claim file. Clients cannot allocate/retry it. Missing
or invalid claims leave approval unsent and preserve the once-lock/original IDs.
Nine source helper tests and native driver syntax checks pass; no native launch
or REAL effect was performed by this lane.

## Model helper final HTTP handoff

The follow-up review identified another scheduling gap inside the Docker helper
after stdin delivery but before urllib initiated the guard request. Root delegated
the narrow HA helper to this lane. `ha/model_transport.py` leaves standalone and
DefenseClaw unchanged. Its pinned python source connects only to the existing
guard loopback endpoint, emits READY and records local monotonic/wall clocks. The
host passes its consumed permit's remaining integer milliseconds minus250ms;
the helper's entire READY-to-send interval must fit that remainder, with at most
250ms wall/monotonic divergence. Linux uses CLOCK_BOOTTIME to include suspend.
The clocks need not share an epoch because READY precedes the host write. This
conservatively double-counts transfer time and cannot extend the original permit.

After complete HTTP serialization, the helper checks freshness immediately before
one nonblocking socket send. Partial/blocked writes remain unknown and never retry.
A total ITIMER_REAL deadline bounds response completion even if a peer trickles
bytes. The host bounds its owned Docker-client lifetime; it does not claim that
killing that client cancels an already dispatched inference. Queued stdin cannot
become a later effect because the recipient's final clock gate rejects it.

The API is `ha_model_forward(executor,payload,request,guard_url)->bytes`; root keeps
binding validation/inspect_model and strict response validation, and changes
MemberAdmission.fresh to return floored remaining milliseconds. EffectScope now
returns that value from check/handoff. Fifteen controlled helper/pipe tests pass,
including final-clock discontinuities, delayed startup/input, partial/blocked HTTP,
hard trickle-response deadline and cancellation cleanup. Related tests pass110/110.
Only temporary controlled stdio/HTTP fixtures ran: no Docker command, actual guard,
provider/model or client qualification was launched. Production integration and
actual fixture/REAL gates remain the coordinator's responsibility.
