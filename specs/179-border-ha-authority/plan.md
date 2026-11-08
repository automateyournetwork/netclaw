# Implementation Plan: R08 Border HA authority

**Branch**: `179-border-ha-authority` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

## Summary

Build provider-independent HA within NCFED: distinct cluster trust, outbound
multi-Border iN2N, one quorum-admitting authority, member/guard enforcement and
cluster-aware clients. Three real etcd voters first qualify controlled faults;
the same path then qualifies a real isolated NetClaw guarded native subnet workload.
No geographic/cloud deployment, retained-runtime upgrade or publication.

## Technical Context

**Language/Version**: Python3.12 federation/runtime;Python3.10+host helpers;existing Node24.19/React18,TypeScript5.9,Flutter/Dart.
**Primary Dependencies**: Existing NCFED/FastMCP/MCP,asyncio,httpx,cryptography/pyOpenSSL,SQLite,Docker;external pinned etcd3.6.16. Existing OpenClaw/DefenseClaw/Ollama qualification closures.
**Storage**: Private etcd bounded metadata plus member SQLite claims and immutable signed artifacts;0700directories/0600private files. No credentials in frontend state.
**Testing**: Python unit/realTLS/realetcd fault tests;Node/editor/Flutter regressions;actual browser,Code1.109 and native iOS simulator;actual guarded local model/nativeMCP.
**Target Platform**: Initial MacARM64 host with isolated LinuxARM64 voters/model/agent and Mac clients;R09 adds geography. Other platforms explicitly unqualified.
**Project Type**: Existing distributed application with opt-in HA authority.
**Performance Goals**: Proposed12sleaderlease/3srenewal;3sclaimconsumption/250msclockdivergence;measure actual detection/election/recovery under local and injected300msRTT. No zero-interruption promise.
**Constraints**: No quorum admission without majority;no automatic unknown replay;NCFED remains foundation;distinct trust/key roles;bounded owned qualification;publication hold.
**Scale/Scope**: Three Borders/voters;one actual member attached to all three;four-member/three-region topology remainsR09.10real operations/20modelcalls/10MCPeffects maximum per reviewed qualification packet.

## Constitution Check

Pre-research PASS. I–III/VIII: isolated read-only native subnet workload, baseline/
verify, no production/device configuration. IV: active GAIT, immutable evidence.
V–VII: existing MCP tool path and NCFED runtime, no new tool server/framework.
IX/XIII: private consensus with separate mTLS/RBAC, no member secrets at Borders.
X–XII: status/client/installer/documentation coherence, explicit unchanged counts.
XIV: no external announcements or tickets. XV: standalone v1 preserved;HA v2
explicit and fail-closed. XVI: spec/clarify/plan/tasks/analyze before source edits.
XVII: owner's roadmap hold keeps maintainer completion evidence;public rollout
copy/release remains deferred. Existing directives supersede broad publication text.
Post-design PASS subject to analysis of all artifacts;no safety waiver.

## Project Structure

- `mcp-servers/protocol-mcp/bgp/federation/ha/`: bounded contracts/store/authority,
  durable member claims,NCFED cluster channel,operation coordinator,lifecycle.
- Existing `service.py`, `protected_{contract,service,store,runtime,docker}.py`,
  `mobile_enrollment.py`, `edge.py`: production integration;standalone preserved.
- `scripts/lib/ha_cluster.py`, `scripts/ha-cluster.py`: private setup/status/
  lifecycle;existing installer/catalog hooks where appropriate.
- `labs/ha/`, `tests/n2n/test_ha_*_179.py`: reproducible fixture/real qualification.
- HUD shared clients/views/server;VSCode profile/client/connection/views;Mobile
  ncfed/cloud/screens;cross-language golden contract fixtures.
- `specs/179-border-ha-authority/`: complete SDD,verification,runbooks and closeout.
- Private evidence: `~/.local/share/netclaw/roadmap-r08-20261107/`.

## Design and execution phases

1. Freeze owner authorization/NCFED scope,qualification bounds,source/resource
   baselines,contracts and all required tasks. Research agents remain read-only.
2. Write meaningful failing contract/invariant tests. Build strict HA config and
   durable required-marker,private etcd adapter,leader/value/revisionCAS and
   bounded per-key operation/claim/reservation state. Keep renewal independent.
3. Reuse NCFED framing and strictTLS exporter on separately registered cluster
   channels;domain-separated mutual possession/enrollment. Add node-keyed member
   attachments without weakening standalone/eN2N. No member-to-member listener.
4. Extend protected v2 review/approval/result/ACK with cluster audience and
   historical issuer;quorum admission/nonce ownership/revocation. Integrate both
   native effect gate and ScopedInference through actual runtime construction.
   Followers proxy through the authenticated cluster channel with original IDs;
   lost write replies cause status reconciliation only.
5. Add cluster client descriptor/status/endpoint trust and shared device enrollment
   authority. Implement all affected HUD/editor/Mobile paths and exact sent markers.
6. Lifecycle and fixtures: actual3voters,TLS/RBAC,leader/partition/restart/delay/
   storage/retirement/restore drills. Export each failure before another run.
7. Review fixture evidence before starting real guarded execution. Freeze fresh
   source/profile/image hashes and exact resource/workload packet;run real native
   model/MCP positives/negatives,actual clients and loss/recovery without replay.
8. Integrate appropriate broad regressions/coherence,export evidence,verify owned
   cleanup,present full technical/measurement acceptance packet and stop beforeR09.

## Authority and data boundaries

Admission transaction checks current leased leader exact value+revision,
cluster recovery generation,membership/revocation state,approval digest and
unspent effect/model ordinal. It commits a permanent claim. Member accepts only
its unpredictable current challenge,exact process incarnation and digest within
bounded monotonic validity;consumes durably before invoking. Unknown claims retain
runner/resource fences across leader/operationID changes. No cached watch/lease
check or status response supplies admission. Complete physical-effect atomicity
with consensus is not claimed.

Bounded records separate operational authority from payload evidence. New leader
can reconstruct only metadata/review state needed for status and fresh requests;
it cannot redispatch an old ambiguous attempt. Original signed results are fetched
from member storage and verified under historical enrollment/signer snapshots.
Raw chat/RAG/member integration secrets never enter consensus.

## Resources and preservation

All new resources carry netclaw-r08 ownership and are listed before creation.
Inspect R05/R06 current receipts and schedules without executing/replaying them;
preserve Nov7/Nov8retirement and originalBorderDec1. No global Docker prune,host
trust-store edit,owner editor replacement or existing-home migration. Fresh test
CAs are scoped only to owned profiles/simulator. Runtime/image copies preserve
originals. Export private consistent ledgers/manifests before exact owned cleanup.
Native effect counters are cumulative across failures and retries of the harness;
a fresh operationID never hides consumed budget or unknown execution.

## Complexity Tracking

One external consensus dependency is necessary for majority authority. It is
private coordination,not a new application federation/tool protocol. Versioned
cluster audiences and per-node attachments are necessary because current v1
contracts deliberately pin one Border. Runtime additions stay in existing owners.

## Client manifest trust decision

An offline per-cluster enrollment signer authorizes bounded node/endpoint manifests.
Initial selected HTTPS/QR onboarding pins its public fingerprint explicitly. Clients
verify its signature and monotone revision;private signer stays operator-owned.
Do not trust an arbitrary new endpoint merely because a response names the cluster.
