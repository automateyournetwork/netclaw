# Pass08 — world1 explicit worker campaign policy

Bounded source unit: the worker now selects the explicit campaign-v1 session
policy (120s target, 130s send deadline, 5s terminal wait) from its stored record.
Historical Google records without that marker are refused for new worker sends;
original-ID ledger lookup and evidence are unchanged. Fixture policy remains20s
and accelerated test clocks are fixture-only. Invalid policy, reservation amounts
or deadline fields refuse; the worker rechecks the record, reserved/create-pending
state and absence of a provider ID immediately before opening transport.

Verification:79/79 affected tests, zero skipped, with supported Node: campaign
budget, ledger/core, live review/source closure, manager, worker, provider and
recovery. Five added tests cover full-policy selection versus historical records,
malformed policy/accounting, forbidden live clock override, record changes between
construction/open, and a real local ledger record through synthetic transport,
explicit stop and terminal receipt. Synthetic transport is never Google evidence.
This is not a timed120s service or provider-billing-cap qualification.
Checklists remain15/15 requirements and43/43 quality; git diff --check passes.
Private results, hashes and native GAIT: .spec200-local/tests/world-pass-08/.

No new runtime module; the29-file source closure remains. Changed hashes invalidate
old paid packets. Partial T013/T020 only: no checkbox, generated-world, visual,
member or human acceptance. Manager still uses ordinary Ledger.admit and historical
reviews; its Google records now fail closed at worker construction. The direct
openGoogle adapter still needs its own reviewed-campaign pre-send enforcement.
Do not describe the worker record validator as proof of trusted review authority.

Next: migrate the manager/live-packet/local-review contracts together, wire
admitReviewedCampaign after awaited audit, freeze/propagate all four authority
and review launch pins, and revalidate at the provider boundary before any send.
Preserve original-ID recovery, reservation-before-marker and unknown holds.
Coordinator alone reviews actual contract evidence and creates a fresh live packet.
No provider/device calls, dotenv reads, snapshot/control/allowance/acceptance/
PROGRESS edits, owner runtime changes, agents, branches, commits or publication.
