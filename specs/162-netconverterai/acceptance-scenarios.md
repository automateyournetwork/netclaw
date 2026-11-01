# Spec162 acceptance scenarios

These scenarios define expected outcomes. Actual source/fixture and live status is recorded in [verification.md](verification.md); the expectation table is not a pass list. Current scoped completion and remaining platform/appliance limits are recorded there; the historical pending gates were superseded by actual qualification.

| Scenario | Expected observation | Evidence classification |
|---|---|---|
| Hosted read-only connection exposes an unexpected mutation | Mutation remains unavailable; a readable status explains the selected mode | Controlled MCP peer |
| Legacy bridge offers supported base operations | Tools are discovered and qualified without submitting anything | Controlled peer; actual upstream discovery separately |
| Account absent, license pending or executable absent | Specific readiness failure, no success claim or unrelated installer fallback | Isolated installation |
| User declines exact-file approval | Zero submission calls and no consumed job allowance | Controlled peer |
| File bytes, options, target, destination or binding change after approval | Approval no longer matches; no submission occurs | Isolated boundary test |
| Same approval used concurrently or after consumption/expiry | At most one outbound submission attempt | Concurrent controlled peer |
| Submission reaches peer but response is lost | Unknown-outcome state persists; restart does not create a second job | Fault-injected controlled peer |
| Polling never reaches a terminal state | Finite polling budget and resumable known job identity | Controlled peer |
| Download digest mismatch, changed existing file or path escape | No trusted downstream artifact and no overwrite of unrelated content | Isolated filesystem |
| Guidance/report contains instruction-like text | Treated as evidence; cannot approve, execute or widen scope | Skill behavioral evaluation |
| Router result is generated but NEEDS REVIEW | Candidate remains review-required in every output | Synthetic report |
| Report has zero NAT rules or incomplete data | No NAT verification claim; coverage gap is explicit | Synthetic report |
| Unsupported source/target/device-class combination | Refused or marked unavailable before submission, no invented translation | Capability fixtures |
| Source inventory has names/IPs but no configurations | Requests/collects authorized source artifacts; no synthesized running config | Composition fixture |
| Hosted and local connections cannot prove same identity | No automatic route switch or implicit job association | Binding fixture |
| Guided preview is unavailable | No fallback from approved-draft workflow to ordinary submission | Controlled peer |
| FRR candidate is requested | Native converter support is checked; independent intent adaptation is labeled and separately tested | Proposal fixture |
| Target lab image or interface mapping is missing | Proposal reports prerequisite gaps; cannot claim boot/acceptance | Twin fixture |
| Compatible image, capacity and authorized lab scope exist | Create and boot isolated target, baseline it, load reviewed candidate and observe applicable functional checks | Live virtual-target acceptance |
| Source and target virtual images both exist | Run the same scoped positive/negative flow and routing expectations on both; retain differences and coverage gaps | Live differential rehearsal |
| Lab node fails, candidate is rejected or a test fails | Preserve evidence and isolate the failure; recover/clean only run-owned resources under the approved policy | Fault-injected orchestration plus live cases where feasible |
| Virtual target lacks a physical-device feature | State exact image/feature coverage; do not claim hardware performance or ASIC equivalence | Evidence review |
| Batfish rejects or partially parses candidate | Parse coverage remains visible and downstream claims narrow accordingly | Static-analysis fixture; actual service separately |
| pyATS dynamic inventory is composed | Candidate validation and explicit activation precede observations; fixture output cannot claim real device state | Existing Spec160 contract |
| Jev is disabled or lacks disclosure consent | Proposal proceeds with review marked unavailable; no hidden provider call | Composition fixture |
| Diagram and change package are generated | Observed/proposed topology and executed/planned tests remain distinct; no ticket is sent | Local artifact review |
| Existing NetClaw installation is configured differently | New optional component does not alter unrelated components, homes or credentials | Installer regression |

The five Ralph iterations must record the exact same review prompt, current task/evidence state, meaningful findings, resulting edits, targeted checks and remaining qualification limits. Iteration count is not itself evidence of completeness.
