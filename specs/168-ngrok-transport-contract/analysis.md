> Historical analysis checkpoints are retained below. Current implementation,
> owner-approved full public HUD and actual live acceptance are in verification.md.

# R01 pre-implementation analysis — 2026-11-01

Read-only analysis completed after tasks generation and before runtime changes.
Reviewed spec, plan, tasks, data model, transport contract and constitution 1.2.1.

| Metric | Result |
|---|---|
| Requirements / buildable success criteria | 20 / 8 |
| Tasks | 31, sequential IDs and valid checkbox format |
| Requirement coverage | 28/28; mapping in tasks.md |
| User stories | Four, each with independent acceptance test |
| Unmapped tasks | None; setup/coherence/handoff tasks map to constitution and FR019–020 |
| CRITICAL / HIGH / MEDIUM findings | 0 / 0 / 0 |
| Unresolved ambiguity / duplication | 0 / 0 |
| Requirements checklist | 11/11 |

Implementation may proceed under the roadmap driver. The bounded adapter is a
design risk requiring actual socket/lifecycle evidence. Current dependency
measurements establish only synthetic cryptographic compatibility. Live ngrok
account/endpoint and separate-network requirements are covered by T027–T028 but
remain unqualified; T028 must stay unchecked without actual evidence. Platform
limits and human review before R03 are not waived by analysis success.

G2's eN2N identification metadata and explicit legacy compatibility are documented
resolutions, not cleartext application fallback. Added helpers extend existing MCP
transport management and do not add a parallel device/tool integration. No
constitution amendment or exception is proposed.

## Implementation reconciliation

The initially referenced `api.py` does not exist in this source tree; the existing
status API is in `bgp-daemon-v2.py`. Plan/tasks now name that file. No API scope
was added by this path correction. Installed ngrok3.36.1 rejected the current
documentation's TCP upstream-origin syntax; research records the measured
bare-host:port correction and successful config check.

Implementation adds readiness gating before agent activation and one-snapshot
registry status to avoid reporting a listener from a different revision. The
final federation suite passes814 tests with5 explicitly recorded fixture skips.
There is no claim of external security review or live qualification. T028 and the
human R03 gate remain open; see verification.md. Source checks do not convert
these release/deployment limits into successful live acceptance.

## Direct-cloud amendment analysis — 2026-11-01

The owner approved the direct-cloud pivot and deployment guidance, then requested
a working cloud HUD link and matching on-prem iN2N evidence. Amended artifacts
have26 functional requirements,8 success criteria and40 tasks. FR021–024 map to
T033–T036/T028; FR025 toT037/T039; FR026 toT036/T040. Existing requirements retain
their original mapping. Historical ngrok records are not relabeled as live passes.

Cross-artifact review found stale mandatory-ngrok gates, an obsolete API-key
blocker, old task totals, a no-HUD scope statement and the claim that the extension
was unchanged. Current spec/plan/tasks/resume/verification/drafts now resolve
those contradictions; original dated evidence remains historical. No HIGH or
CRITICAL source-design inconsistency remains. Exact cloud creation/activation and
live evidence are explicit outstanding gates, not analysis success.

HUD inspection corrected an initial assumption: owned chat bindings do not provide
a public login. The supported remote operator path is SSH, carried over GCP IAP
for this pilot by default. No unauthenticated public proxy is proposed. This
keeps the R01 observation within existing access controls; a public login gateway
requires separate review. No external security review is implied.

## Final owner-amended scope reconciliation

The owner superseded IAP-only/status-only access with the full open HTTPS lab HUD
and explicitly authorized Anthropic Sonnet and a real on-prem subnet answer.
The fixed ingress, scoped tool policies, private administration and later R15–17
user controls reflect that decision. Normal browser Chat, member task/tool
correlation, RAG indexing/retrieval and Canvas handoff now have actual evidence.
GCP DNS/certificates and real address relocation passed. R01 requirements retain
their task mapping; optional ngrok and untested platforms retain explicit limits.
No later brief, publication, existing-runtime upgrade or device operation follows
from this closure. Final source coherence and audit receipts are in verification.md.
