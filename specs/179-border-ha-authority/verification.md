# R08 verification — implementation in progress

R08 is not yet complete. No REAL model/native effect or native client HA acceptance
has occurred. The48task plan and every qualification-matrix row remain required.
Source1.18.7/editor1.6.1/Mobile1.0.4+7 and the roadmap release hold are unchanged.

## Evidence established

- SDD spec,clarification,plan,contracts,tasks and cross-artifact analysis precede
  implementation. Analysis has zero critical/high findings at that checkpoint.
- Three actual private etcd3.6.16 voters use distinct peer/client CAs,mTLS,RBAC,
  bounded memory/CPU/storage and loopback administrative ports. Exact IDs and
  command journals are private under roadmap-r08-20261107/etcd-fixture-01.
- core-03 passes7fixture rows using actual etcd and NCFED cluster sockets:
  three-node mesh,one follower-forwarded admission,leader replacement,old-leader
  refusal,unknown reservation,single-voter continuation and two-voter refusal.
  Replacement measured15.007s. Two controlled callbacks;zero model/native calls.
- Actual socket tests separately cover strict mutual TLS,NCFED proof/method
  isolation and one member's three outbound authenticated iN2N attachments.
- Source/controlled tests cover fresh single-use admission,clock discontinuity,
  delayed receipts,unknown dispatch,member/runner reservations,device revocation
  CAS races,original result/successor ACK,lifecycle and fenced restore.
- Integrated targeted Python batch:235passed,12existing datetime warnings.
  HUD/editor lane:538HUD tests passed;211editor tests passed,3existing skips;
  focused owner35passed,TypeScript and builds pass. See clients-notes.md for
  commands,initial pre-build harness failures and exact qualification limits.

## Retained failures and limits

core-01 refused a manifest path mismatch before execution. core-02 failed cluster
transport because the application URI-SAN certificate did not establish TLS DNS
identity. The corrected fixture has a separate transport CA/DNS-SAN certificate
with each enrolled application key preserved. Both failed packets remain private.

The current fixture has not yet established the full partition/restart/storage/
retirement/restore matrix. Unit tests are not substituted for those rows. REAL
OpenClaw/DefenseClaw/Ollama/nativeMCP and browser/Code/iOS qualification remain open.
No region,physical phone,other model/runtime or additional platform is qualified.

## State and preservation

Three owned R08 voters remain running and unpaused; no qualification Border/member
process remains from core-03. Export before reviewed exact-owned cleanup. No
global prune,retained runtime upgrade,cloud change or device operation occurred.
R01 pilot and R05/R06 retirement evidence remain preserved. Never rerun spent
core directories or reuse an old activation/enrollment payload.
