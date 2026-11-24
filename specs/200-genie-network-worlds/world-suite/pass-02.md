# Pass02 — world1 reservation-before-send admission seam

2026-11-23. Assignment: pass02, world1. One offline partial T013/T020 unit.
Spec Kit prerequisites passed; checklists remain15/15 requirements and43/43 quality.
Optional git hooks skipped. No task checkbox or acceptance gate closes.

Added trusted-backend `CampaignAdmission` in the existing campaign-budget module.
It opens an existing authority without bootstrap, accepts no account/root override
in admission inputs, and binds each reservation to canonical session root plus
exact ledger request digest. Ledger admission validates its local review before
reserving; the campaign transaction commits before the local send marker.
A local rollback preserves the reservation. Only the same ID/root/request can
recover it. Existing sessions return idempotently; a settled reservation without
its session marker cannot create another session. Historical unbound markers
cannot silently acquire campaign authority. The one-attempt gate stays intact.

Five new offline integration tests cover marker-write failure/rollback/recovery,
alternate roots and IDs, account-key rejection, changed budget review, settled
missing-marker refusal, invalid local reviews, missing authority and historical
single-attempt protection. Test billing, terminal and bound digests are explicitly
synthetic. Combined campaign-budget/core/live-packet/recovery tests: **39/39 pass,
zero skipped** on supported Node. `git diff --check` passes. No new runtime module;
source closure stays29 files, but changed source bytes invalidate prior packets.

Private evidence: `.spec200-local/tests/world-pass-02/` contains logs, hashes,
native GAIT start/final and full retained gait_log. Existing audit root/branch
reused. No provider/device calls, owner dotenv reads, snapshot modifications,
control/allowance/acceptance edits, PROGRESS edits, owner-runtime changes, agents,
loops, git branch changes, source commits or publication.

Limits: this is a tested admission seam, NOT live-manager activation. The trusted
launcher still must pin one authority across all roots/accounts. Referenced bound,
review, terminal and billing artifacts require content/identity verification;
digest syntax alone is not proof. The old manager still calls ordinary admission,
and its20s/US$15 policy is unchanged. The new seam's campaign reservation is kept
separate from those historical session fields until runtime policy integration.
No generated visual evidence, actual Risk-member acceptance or T029 verdict exists.

Next: implement trusted launcher/packet binding to one campaign authority, refuse
missing/changed bindings, and validate exact reviewed bound artifacts before this
seam is enabled. Follow with deterministic120s worker timing/termination tests.
