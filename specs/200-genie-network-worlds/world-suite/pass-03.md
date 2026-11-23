# Pass03 — world1 trusted campaign authority pin

2026-11-23. One offline partial T013 unit. Spec Kit prerequisites and checklists
pass (15/15 requirements,43/43 quality); optional git hooks excluded. No task closes.

`loadCampaignAuthority` now requires operator launch configuration naming a private
binding file and its exact SHA256. The binding identifies the existing canonical
campaign root, campaign ID, campaign policy hash and SQLite file device/inode.
Missing configuration, changed binding bytes, replacement database, symlinks,
wrong ownership/permissions or stored root/policy identity fail closed. It never
initializes a budget. Each live packet must carry the same binding digest, so a
session root or account alias cannot select a separate authority through the packet.
The shared packet loader enforces this at CLI, manager and worker checks. Manager
passes only the two pin variables alongside PATH to a live worker; credentials
remain backend-loaded. No new runtime module; source review closure stays29 files.
All earlier source packets are stale and lack the now-required campaign pin.

Affected live-packet/campaign-budget/core/manager tests: **35/35 pass, zero skipped**
on supported Node. New cases exercise absent/mismatched pins, altered bindings,
missing/replaced/symlinked databases, reopen and alternate session-root persistence.
Only synthetic credentials/budget authorities are used; no owner dotenv is read.
Private test logs/hashes/native GAIT: `.spec200-local/tests/world-pass-03/`.

Limits: manager still uses ordinary admission rather than CampaignAdmission.
Historical20s/US$15/one-attempt policy is unchanged. Authority pinning does not
verify the service/input-text bounds, create an allowance or authorize a call.
Live worker launch/Google/member/visual acceptance remain untested. No generated
media exists to review in this pass; world1 recognizability/drift remain unassessed.
No control/allowance/acceptance/PROGRESS or snapshot edits, device/provider calls,
owner-runtime changes, agents, loops, branch changes, commits or publication.

Next: validate exact reviewed service/input-text artifacts, wire CampaignAdmission
into the manager using the pinned authority, and qualify120s lifecycle/accounting
before preparing any fresh paid packet. Preserve first synthetic proof and T029.
