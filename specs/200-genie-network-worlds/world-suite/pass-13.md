# World-suite pass13 — world2 / durable provider create ownership

Assignment: SPEC200_WORLD_PASS=13, SPEC200_WORLD_NUMBER=2; source_refinement.
Applied Spec Kit prerequisites and read current authority/handoff/context. Written
checklists remain15/15requirements and43/43quality. Optional Git hooks skipped.

Concrete work: added a transactional permanent provider_creates claim immediately
before the official SDK create call, comparing the reviewed current record and
checking its deadline. Two ledger connections cannot enter create for the same
operation. Reopened original-ID calls cannot consume the claim again. Create
failure/missing ID/connect failure records unknown, preserving any observed provider
ID and all campaign exposure. A claimed create cannot become failed_pre_send,
including the existing worker's pre-transport deadline path after a restart.
No new runtime module; the reviewed source closure remains29files. Old exact paid
packets require coordinator refresh because existing source bytes changed.

Verification: supported Node ran live/provider/core/campaign-budget/worker/recovery/
manager tests:97/97 pass,0failed,0skipped. New scenarios use synthetic pinned review
records and injected transport only. They cover two simultaneous opens through
separate SQLite connections, restart/reopen before an observable result, create
rejection, missing provider ID, connect rejection and refusal of false pre-send
settlement. Existing actual pinned SDK transport mocks still pass. Initial failing
checks, intermediate97/97 and final97/97 logs retained privately under
.spec200-local/tests/world-pass-13/. Runtime snapshot/control not modified.

Limits: no actual Google frames, fantasy visual review, device/SSH/CML call, owner
dotenv read, private projection export or paid execution. Reopened connections
simulate restart; no new OS process-death drill or live provider termination/billing
proof. No task checkbox, installed member or human T029 closure.15/30 remains.
No branches/commits/agents/loops/publication/tickets/runtime changes.

Next defect to qualify: delayed create/connect completion after worker cleanup may
reach the provider adapter's ledger writes after that ledger closes. Use controlled
promises to check original-ID retention, bounded cancellation/no setup and held
unknown exposure, including process loss. Then qualify input/text/service bounds
and trusted original-ID terminal/billing reconciliation. Actual world2 fantasy
camera/landmark refinement still needs coordinator-owned Google visual evidence.

Daily memory, tasks/readiness/data model and HANDOFF updated. Native GAIT reuses
current root/branch; end record and gait_log retained privately alongside tests.
