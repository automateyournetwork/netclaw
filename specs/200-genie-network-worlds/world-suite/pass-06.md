# World-suite pass06 — world1

Status: source progress; live_world_passed=false.

Partial T013: added admitReviewedCampaign in existing live-packet.mjs. It reads
an operator-only, SHA256-pinned launch descriptor containing the exact review
reference, world number and source manifest. Each call reloads descriptor,
review/service/input-text/contract bytes, current source closure and campaign
identity before invoking shared CampaignAdmission. Closed input rejects supplied
budget evidence or authority selectors. No reservation/session marker is created
on pin, artifact, world, source or authority validation failure. Original-ID
retrieval retains one shared reservation; admission closes its database handle.

Supported Node:47/47 affected tests pass, zero failed/skipped (live packet,
campaign budget, core ledger, manager). Four new tests exercise successful
reservation/reopen, rejected tool-supplied evidence, missing/changed launch pin,
contract/authority tampering and correctly pinned but inconsistent world/source
claims. The initial40/41 run failed only because a new assertion expected the
wrong existing refusal code; changed unknown_field to actual invalid_input.
Both logs are retained under .spec200-local/tests/world-pass-06/, with hashes
and native GAIT. Requirements15/15 and quality43/43 remain complete.

Limits: this is an offline qualified backend seam, not yet the live manager path.
Manager still uses ordinary Ledger.admit; historical20s/US$15/one-attempt fields
are unchanged. Do not wire this seam to paid execution until session accounting,
120s runtime policy, token limits and original-ID reconciliation qualify together.
Typed provider-enforcement claims still require coordinator review of real
contracts; synthetic tests do not prove service bounds. No new runtime modules;
29-file closure remains exact and changed hashes invalidate older paid packets.
No generated visual, member or human acceptance, task checkbox or live gate closes.

No provider/device calls, owner dotenv reads, private export, sealed bundle,
control/allowance/acceptance/PROGRESS edits, runtime changes, branches, agents,
loops or git commits. Next: align120s session/ledger policy and USD displays with
campaign reservations, then wire manager admission and worker validation using
captured operator launch pins. Preserve unknown holds and original IDs.
