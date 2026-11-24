# Spec200 and maintainer PR reconciliation — 2026-11-24

The owner requested completion/merge of Spec200, then explicitly added all open
Byrn Baker PRs to the integration scope. This is source integration only: no
existing runtime upgrade, cloud activation, new paid Google run, Marketplace/tag
publication or external announcement occurred.

| PR | Scope | Reviewed result |
| --- | --- | --- |
| [366](https://github.com/automateyournetwork/netclaw/pull/366) | Spec200 integration | Merged `0979c445` after47/47 hosted checks on `97fc1f1a`;30/30 accepted-scope tasks. |
| [361](https://github.com/automateyournetwork/netclaw/pull/361) | Member skill-limit evidence | Corrected a literal\n in the rollback example; merged `7b82d09d`. Documentation only. |
| [362](https://github.com/automateyournetwork/netclaw/pull/362) | Consent before persisting an unauthenticated peer | Reviewed the ordering/consent path and regression;39/39 hosted checks, merged `91e45db0`. |
| [365](https://github.com/automateyournetwork/netclaw/pull/365) | Teardown/member evidence and H23 backlog | Reconciled overlapping #361/#362 edits, retaining H20/H22 and the new H23; merged `eba834bc`. Documentation only. |
| [364](https://github.com/automateyournetwork/netclaw/pull/364) | Existing Three.js skill CLI | Regenerated canonical skill/Bash catalog;29 local tests and42/42 hosted checks; merged `6ccc79c2`. This remains separate from Google Spec200 worlds. |
| [363](https://github.com/automateyournetwork/netclaw/pull/363) | Approval-pending synchronous response | Reviewed retry/unknown/concurrency correction and protected source pin; 40/40 hosted checks on `42e9c6c6`, merged `dd3af3c9`. |

The #363 review found that the actual caller's second request hit a duplicate SQLite
primary key before reaching the callee. A new caller/callee regression reproduced
that failure. The fix atomically reclaims only an identical peer/method/body
binding after an explicit `approval_pending` response. Unknown, completed, refused
and concurrently dispatching operations stay closed. Rejected reuse is audited
without rewriting the original intent. Exact protected Hermes source hashes were
updated after reviewing the MCP argument/error change; tool and argument policy
scope was not expanded.

The targeted approval/consent/protected-source tests pass 37/37. A broader local
federation run passed 2,765 tests with 15 skips and one missing private native-NetBox artifact
failure. That same failure was reproduced on the unchanged baseline; it is not
silently reclassified as a passing live qualification. The final repaired PR passed all 40 clean hosted checks before merge. Private review logs retain the before/after failure and evidence.

The final documentation reconciliation corrects stale installer/release text and
current SDD headers that still described the completed collector/member checks as
open. It retains the owner's illustration acceptance and every visual/event,
platform, testing-posture and unsettled-billing limit. See
[final qualification](final-qualification.md) for the actual Google/member and
collector evidence. The five recordings and sealed source archive are unchanged.

Original 198 is preserved at `856bbc883279f4c3584664bfd7b34fe50bc7a57f`. Resume its
Azure/GCP acceptance work after this reconciliation, under its separate cloud
budget/activation controls.199 remains reserved for AWS.

Combined main at `dd3af3c9` passes all 66 targeted approval, consent, protected-source and visualization checks. Canonical skill/Bash catalog parity and metadata checks pass. This final documentation change is reviewed separately; earlier green checks are not substituted for its hosted result.
