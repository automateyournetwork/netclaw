# R07 verification record

## Result and acceptance status

All source, runtime, native-client, evidence-export, audit and disposable-cleanup
work is complete for the scope below: **30/31 tasks closed**. Final human agreement on the measured recovery
objectives and roadmap acceptance remains open (T030). This is not yet a claim
that all 31 tasks or the roadmap gate are accepted.

The owner requested “Start Spec 178 / R07 using the saved handoff” and “drive to
100%.” Full SDD used a coordinator and three separate worktrees. Source is on
`178-recovery-gate`, based on clean main/origin `6b986426`. Unrelated PR332 and
its separate Spec177 remain preserved. No push, PR, merge, release, version bump,
public rollout or R08 work was performed. Versions remain source 1.18.6,
VS Code 1.6.1 and Mobile 1.0.4+7.

Private evidence root: `~/.local/share/netclaw/roadmap-r07-20261106/`.
See [evidence matrix](evidence-matrix.md), [runbook](runbook.md),
[measurements and proposed objectives](recovery-objectives.md), and
[task ledger](tasks.md).

## Scope and evidence classification

R07 adds actual local child-process/TLS/source-handler/native subnet execution
and actual Chromium, Mac VS Code and iOS simulator recovery. It creates no cloud
resources and makes no hosted-provider or network-device calls. Fresh private
homes, authorities, profiles and owned listeners isolate the drills. Dependency
environments were reused read-only. Test trust is scoped to exact clients or the
owned simulator; no host trust store or TLS verification was disabled.

The browser/editor workload uses a controlled RPC/DTO ledger. Mobile uses real
production enrollment, retained-key authentication and TLS with a controlled
original operation. Those client results are not new signed protected execution
or durable-ACK evidence. Protected SQLite/signature regressions and historical
actual R03–R06 cloud/provider/device evidence supply their own distinct credit,
at their frozen source and original limits. Optional ngrok is unselected and
unqualified; physical iPhone, Windows/WSL and installed Code 1.145 are not newly
qualified by these Mac/simulator passes.

## Integrated changes and checks

| Lane | Reviewed source | Validation |
|---|---|---|
| Runtime | `d002558d` → `fd3057c1` | 1,756 federation tests passed, 5 existing skips, 103 warnings; separate final authority suite 14 passed |
| Pending Border drill | `431bfa40` → `aa698b0c` (test only) | Actual pending-claim restart passed; final focused run 1 passed in 1.04s |
| HUD and editor | `7844a941` → `6de3fa95` | HUD 529/529 serial; final added UI regression 30/30; editor 209 passed / 3 existing skips; builds and TypeScript passed |
| Mobile | `7810106d` → `32f87526` | Flutter 518 passed; final focused 25 passed; analyzer clean; final exact-source iOS simulator build passed in 19.6s |
| Combined source | `32f87526` clean detached checkout | 166 spec artifacts / 4 historical exceptions, FastMCP, MCP tasks, all 6 reconciliation surfaces, catalog coverage and contract manifest/list/matrix passed |

These totals describe separate runs, not a sum of unique tests. The second broad
federation run deliberately excluded the already-passed native-delivery drill
to avoid repeating effects. The final authority addition and pending-Border test
do not change runtime production bytes. Root reviewed the scoped cherry-picks,
verified evidence hashes and confirmed tested Mobile/runtime source hashes against
the integrated tree. Later acceptance-document edits do not alter tested code.

## Runtime recovery and authority

Strict internal and edge channels check current authority before admission, after
awaited handlers/calls, and before success or error delivery. Predicate failures
fail closed. Removal persists before awaiting channel close. Current membership,
key, enrollment generation and application-certificate validity are enforced;
protected-mode predicates retain the strict-channel requirement. Bounded dial
causes distinguish connection, TLS identity, admission and cancellation failures.
No weaker fallback is introduced.

Actual strict-TLS child processes prove same-port Border restart, registry port
replacement, member restart and unchanged enrollment/key/generation. Open-channel
revocation, reconnect refusal, late success/error refusal, predicate failures and
real application-certificate expiry are covered. The certificate measurement is
request-start to refusal after expiry, not expiry-to-refusal or idle closure.
Revocation covers enrollment and pinned application key/X.509 authority; transport
TLS leaf validation remains at handshake/reconnect. No external CRL/OCSP or
continuous transport-certificate expiry monitor is claimed.

A controlled model adapter invoked the real installer-patched native subnet MCP.
Six concurrent same-ID submissions yielded one effect; pre-dispatch cancellation
yielded none; post-dispatch cancellation and member process death retained
`outcome_unknown`. Same-home restart preserved completed results and uncertain
claims without repeating original IDs. The new delivery drill made **9 native subnet calls across
3 fresh runs**, including the first failed harness run; zero hosted/device calls.
Earlier lane wording saying three calls describes one run of that drill. Existing
broad-suite native fixtures execute separately; no all-suite native-call aggregate
is asserted.

Root verified both successful 91-file exports and immutable worker database
`quick_check`. Each records completed/dispatch1, cancelled/dispatch0,
unknown/cancel-requested/dispatch1, and unknown/no-cancel/dispatch1. Actual authority
is `worker/federation.db`; the empty member/Border scaffolds are not its ledger.

Independent review identified and closed a missing pending-Border case. The new
drill runs production Border role/start_runtime/SQLite/EdgeChannel over verified
TLS 1.3 WSS. One original request reaches a controlled adapter, marks dispatch,
and blocks before any external call. Killing the Border leaves working/dispatch1;
same-home/port/identity restart records unknown/dispatch1. Four duplicates return
the original task, with adapter entries still one and no provider/native effect.
Two fresh test runs made two controlled entries in total and zero external calls.
Root verified all 51 exported files and three consistent SQLite snapshots. Owned
PIDs9023/9036 exited and port60359 refused after cleanup.

New native delivery proves ordinary async task behavior. Protected duplicate/ACK
credit is separately mapped to `test_protected_claims_171.py`,
`test_protected_recovery_171.py`, `test_protected_combined_176.py` and actual frozen
R03 ACK-loss evidence. Arbitrary synchronous calls are separate executions;
unknown synchronous responses must never be retried automatically.

## HUD and VS Code (G12)

HUD writes monotone decision/revoke markers before I/O. Reload, old status and
imports cannot clear them. Original ID/nonce/parent recovery is status-only;
imported references cannot approve or cancel. Redirects are refused. VS Code adds
**NetClaw: Replace Cloud Border Endpoint** with native review, same-installation,
execution-mode and principal checks, preserved profile ID/references, serialized
storage updates and a final compare-and-swap. Sessions retain their origin scope.

Actual Chromium156.0.8078.80 and Code1.109 production clients passed loss, reload,
endpoint replacement, original-reference recovery and wrong-identity refusal.
The browser's original pending operation survives a lost decision; another
controlled operation completes once. Code's pending and completed records survive
actual editor exit/restart and endpoint movement with identical references,
sent markers and result digest. Recovery adds **zero POSTs**. Total fixture effects
are two (browser and editor); no native MCP/provider/device calls occur.

Chrome made three wire POST attempts after one application dispatch when a proxy
dropped the connection before headers. All were dropped before RPC, producing
zero effects. That original witness remains. Safety depends on durable application
markers and original-ID backend deduplication, not a promise of one wire attempt.

Browser trust uses an exact generated SPKI exception in the owned process. Editor
trust uses the exact fixture CA/undici dispatcher and isolated fetch settings.
No global trust change or verification bypass was used. The first installed
Code1.145 launch exceeded its socket-path limit; a subsequent isolated startup
**touched the existing `~/.vscode-shared/sharedStorage/state.vscdb` mtime**. No
pre-launch hash exists, so content change and attribution are unknown. It was not
restored or deleted. Owner CodePID1352 retains its Nov4 start and settings predate
this session. A blanket claim that all owner files were untouched is invalid.
Successful qualification used pinned Code1.109 and separate private profiles.

Root inspected native screenshots, reports and all 45 export hashes. Owned
fixture PID88131, editor/browser processes and four listeners were stopped;
private profiles/evidence remain. Only owned temporary sockets/dependency links
were removed. The original owner editor remains running.

## Mobile (G13)

Mobile adds explicit same-host/path WSS-port recovery using the retained native
key, installation, principal and unchanged HTTPS owner origin. A serialized
compare-and-swap and lifecycle guard immediately before atomic rename retain the
old binding if a concurrent writer, disposal or suspension wins. Cold metadata
confirmation uses the same guard. Connection generations discard late completions
and errors. Revocation preserves enrollment/references. A real TLS-negative drill
found an unobserved WebSocket readiness error; the fix observes it while the
stream retains failure ownership. Production chat retry behavior is unchanged;
its test now awaits durable save before deleting the test directory.

Eight cases passed on a fresh iPhone17Pro/iOS26.5 simulator: enrollment, port
migration, wrong identity, untrusted TLS, cold recovery, foreground loss,
background/foreground recovery and actual durable member revocation. Production
FederationService/RiskManager/EdgeChannel authenticate native P256 Keychain hello
through verified TLS. This is simulator Keychain evidence, not physical Secure
Enclave or camera qualification. The CA is trusted only by the owned simulator.

A controlled completed record (`fixture:true`, `verified:false`,
`durable_ack:false`, zero attempts/effects) and sent reference were seeded once
after actual enrollment. Root compared all eight original references and results;
revocation deliberately clears the unauthenticated operation view while retaining
the reference/key. Across successful and failed attempts: 1 enrollment, 24 hellos,
20 controlled catalog calls and 20 controlled status calls; **zero operation
submissions, provider calls or native-tool calls**. No status/catalog follows
revocation. The first unused enrollment offer expired and was never consumed.

The protected UI closes WSS while inactive. The paused host-cut command may find
no live channel; the drill proves real background-to-foreground retained-key
redial, not execution during suspension or an extra socket-cut effect. Source
supervisor backoff remains bounded at60s; the measured native paths use explicit
reconnect/lifecycle flows and do not qualify its worst case.

Enrollment/migration passed before the readiness-error fix. Final negative,
cold/loss/lifecycle/revocation cases used the fix before final cosmetic syntax/comment
cleanup. The exact committed application then compiled successfully but was not
redeployed after cleanup. Both build hashes and source provenance are retained. Exact source extracted
from the installed native-tested Dart kernel proves six changed production files
byte-identical and four cosmetic-only (layout/comments, optional commas and two
redundant single-statement brace pairs). The complete diff and mechanical token
comparison are retained; no executable conditions, calls or literals differ.
Root verified 100 evidence files, 44 export files, 128 final Mobile source files,
80 runtime source files and both exported SQLite quick_checks; screenshots show
visible refusal/preservation. ServicePID90192 stopped, all four ports refused,
and the owned simulator is shut down. Its private key was not exported; its
private shutdown profile remains evidence.

## Retained failures and validation limits

- First broad federation run: 1,738 passed / 19 failed / 5 skipped. Seventeen
  failures came from missing ChromaDB in the reused R05 environment; two came
  from legacy fake channels without a strict flag. Compatibility was corrected;
  the complete R04a environment was then reused read-only for the passing run.
- First native-delivery harness raw pytest tree was pruned before export. Its
  original XML/traceback and reached three-effect assertions remain, but missing
  raw files are not reconstructed. Both later successful exports are intact.
- Default concurrent HUD run passed528/529 with an Avatar button timing failure.
  Isolated Avatar23/23 and the complete serial529/529 pass are retained; no skip
  was added. Initial editor test startup lacked a built prerequisite; its owned
  hung child was stopped before the build and successful suite.
- Mobile wrong-cert-v1 exposed the fixed readiness error. V2 failed in the host
  screenshot handoff after Flutter changed its simulator container; V3 resolves
  the active owned container and passed. Failed attempts remain evidence.
- Root reconciliation initially failed only for a pre-existing ignored installed
  HumanRail clone's unbounded MCP pin. Clean tracked-source reconciliation passes
  all six surfaces. No owner runtime was modified or qualified by that check.

## Evidence export and resource preservation

Root independently checked the following private manifests:

| Artifact | SHA-256 |
|---|---|
| Primary native delivery,91 files | `41a42ddec728bf13d6a7b6588bfd1fe5908930379e6d4571379d2edce9add735` |
| Second successful delivery,91 files | `31994a2009262e8bc0a52846ccbee92980691ed8567591bd138f3e255962d25e` |
| Final pending Border,51 files | `e7a6ca8fc8f8d82ca703d24ac6bbd8eb8e9908d09218f6d59e672db805a70955` |
| Native surfaces,45 files | `2b9a0e20801363a43df716d473f435b3078e14f60d64b9660337583eeab18be9` |
| Mobile evidence,100 files | `8bf2c6ac9d2abd4f796ac41358d32ddfec8b187f4093b41ff61ac4fe7d9594a4` |
| Mobile export,44 files | `79ba4f18c0dcd0fcb64762670cde52645a0ad5f96f2071fa84f8ecc39b0c1262` |

Startup read-only cloud inventory observed4running VMs,4ready disks,5addresses
and5networks belonging to retained R01/R05/R06/original resources. No R07 cloud
resource exists. R05/R06 check modes pass again at closeout without execution:

- R05 execution manifest `5b6a39412c4d02f8ab9ad3923af9768eef34eddc62cd281820a13f41b7d201ec`;
  retirement plan `6b0d31a82f705bfcd0a2426f1757338d6782e73790522d76351d072d0bdc0716`;
  quiesce November7 19:36:25Z, cleanup not before19:41:25Z.
- R06 plan `4f03feb371bcc3df640adf0c8f6d0a5b3177d891be07a0faddd540c575a588c0`;
  quiesce November8 15:09:35Z, cleanup15:14:35Z, fallback15:19:35Z.
- Original Border December1 lifetime is unchanged. Scheduled future cleanup is
  **not** reported as completed or zero billable residue.

No spent plans, old enrollment or unknown effects were replayed. Retained evidence
homes/worktrees remain private; disposable active services are stopped.

## Audit and final gate

GAIT session `r07-spec178-recovery-20261106` was created, checked out and verified;
kickoff `4ef9b452`, progress `020893e0`, technical closeout `5e0d9493`.
The final `gait_log` was displayed and saved privately. Daily memory and infrastructure notes retain
scope, failures, source and cleanup. Startup pyATS inventory failed initialization
because its selected HTTP runtime was absent; no device or installation was
changed. MemPalace was unavailable; file memory and GAIT preserve the record.

The [R07 brief](../../docs/roadmap/issue-310/briefs/R07-recovery-gate.md) explicitly
requires “measure first, then set. [HUMAN]” for recovery objectives. Human agreement
and final acceptance are the remaining gate; they will be recorded verbatim in a
subsequent acceptance entry. Acceptance does not authorize R08 or publication.
