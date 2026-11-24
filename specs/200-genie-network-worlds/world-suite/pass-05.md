# World-suite pass05 — world1

Status: source progress; live_world_passed=false.

Implemented partial T013 in existing live-packet.mjs: loadCampaignReview reads
closed typed review/service/input-text artifacts through the descriptor-checked
reader. It revalidates the operator-pinned campaign and current 29-file source
closure, binds every artifact to exact source/projection/model/policy/world/120s,
rejects expired reviews, requires provider-enforcement claims and retained evidence,
and verifies the exact video-plus-input/text reservation. Token-price products
use BigInt and round each charge up independently. Compact JSON encoding rejects
duplicate keys and lossy representations. The synthetic projection boundary stays
in force; no private projection or new MCP input is admitted.

Supported Node affected tests:43/43 passed, zero failed/skipped (live packet,
campaign budget, core ledger, manager). New tests cover reopen, wrong world,
private projection, changed source, timer/estimate claims, duration/video mismatch,
underfunded/unsafe input limits, alternate campaign, expired/extra fields, altered
contract evidence and duplicate JSON keys. Checklists15/15 and43/43 passed;
Spec Kit prerequisites and git diff --check passed. Logs, source hashes and native
GAIT retained under .spec200-local/tests/world-pass-05/. No new runtime module.

Limits: typed records express coordinator-reviewed claims, not independently
verified service contracts. No actual provider evidence was read or fabricated.
The seam is not wired into live admission. Operator-only review pinning,
manager/worker revalidation, actual request token-limit enforcement and120s
lifecycle/accounting integration remain required. Historical runtime20s/US$15/
one-attempt behavior is unchanged. No task checkbox, generated visual, member or
human acceptance closes. Changed source makes older paid packets stale.

No provider/device calls, owner dotenv reads, sealed snapshot/control/allowance/
acceptance/PROGRESS changes, owner-runtime changes, agents, branch or git commits.
Next: pin the exact review reference in trusted launch configuration and consume
this validator at campaign admission with failure-before-reservation tests.
