# Spec 148 Mac return acceptance

**Date:** 2026-10-10. **Implementation:** `9b65b3b` on `148-hermes-hud-integration`.
**Disposition:** implementation and Mac acceptance complete; final platform-matrix
clarification and release preparation pending. Nothing pushed, merged, tagged or published.

The WSL handoff at `3252977` was fetched from origin and fast-forwarded on this Mac.
The owner explicitly authorized the repository Anthropic credential for isolated Hermes
acceptance. Only that credential was copied into a private test profile. Existing owner
configuration and services were preserved. No network-device operation was required.
After testing, only test-owned launchers were stopped and the authorized credential
copy was removed from the test profile; the owner’s original `.env` files were retained.

## Changes found through acceptance

- Pass the configured HUD chat deadline into Hermes admission. A killed companion now
  reaches durable uncertainty at the selected deadline instead of always using 15 minutes.
- Distinguish Terminal Intent preparation failures from ambiguous admission. A failure
  before submit is a known failure with `mayHaveExecuted: false`; an attempted admission
  remains uncertain and is never replayed.
- Disable Hermes auxiliary title generation and automatic context compression in the
  private profile. Those clients bypass the protected inference hook. HUD titles remain
  local metadata; oversized conversations must respect the configured model's context
  limit. Native transcript compaction/evidence preservation is separately tested.
- Return Hermes Settings as the label/value rows consumed by the dashboard. The former
  object shape rendered an empty panel. Model, provider, selected configuration and
  qualified read-only policy now appear without exposing credential values.

Mac `/tmp` resolves through `/private/tmp`; the browser fixture now canonicalizes its
profile paths so exact registration qualification does not accidentally exclude its tool.
This is a fixture correction, not a relaxation of production source/registration checks.

## Evidence and scope

| Acceptance | Result | Evidence |
|---|---|---|
| Actual Anthropic/Hermes | PASS | [Live report](evidence/mac-live-provider.json): five turns with `claude-sonnet-4-6`, violet follow-up, installed skill, registered subnet MCP, 14 usable hosts, actual provider usage |
| Real process faults | PASS | [Summary](evidence/mac-closure.json): six pinned-agent tests, actual MCP/subnet, process kills, durable lost response, configured deadline, stop, auth/provider/config/source failures; zero replay |
| Browser Chat/Avatar/Canvas | PASS | [Chromium report](evidence/mac-browser.json): two branch-point contexts, owned history, foreign cookie rejection, draft/quote/file retention, stale installation fencing, pending refresh/stop |
| Selected-runtime panels | PASS | Real browser settings/configuration/tokenomics/catalogue/federation navigation, zero provider inference during panel reads, actual Settings rows; unavailable counters are not zero |
| Upgrade/preservation | PASS | Actual component install repeated against populated custom home; all 14 captured owner/state files unchanged immediately afterward. Actual HUD check/apply/apply with browser graph/draft/quote/file retained |
| Rollback | PASS within scope | Prior Mac dashboard source (`28cbc67`) restored/reapplied on the same browser origin without losing saved Canvas work. Legacy OpenClaw v1 binding backup restored and migrated again without changing backup bytes. No owner runtime downgrade |
| Existing OpenClaw | PASS | [API](evidence/mac-openclaw.json), [browser](evidence/mac-openclaw-browser.json), [Intent](evidence/mac-openclaw-intent.json): live chat/context/model selection, Avatar, Canvas parent/child, owned history/panels and structured read-only Intent through existing gateway `2026.7.1-2` |
| Unit/regression | PASS | 369 HUD tests, 27 Canvas suites, 238 installer/HUD tests + 25 subtests, offline contracts, production four-entry build/bundle budget, selected MCP smoke, catalog/inventory/spec and MCP reconciliation |
| Existing owner preservation | PASS | Eight original/seeded file hashes unchanged; existing owner gateway PID 73241 and HUD PID 85793 still running. Test services used separate ports and profiles |

The initial OpenClaw conceptual Intent request returned an unstructured answer and was
truthfully marked uncertain. It was not replayed. A distinct format-only request returned
an accepted structured `completed/answered` report. This retains the existing fail-closed
report parser; it does not imply every model response will satisfy its schema.

Positive paused once/deny and conditional approval UI coverage uses controlled protocol
fixtures. The initial qualified subnet tool does not require a live approval pause.
Actual requests reject stale, foreign and broad approvals. This satisfies FR-022's
**where supported** condition without inventing an eligible paused operation or granting
write authority to create a test. Native tool expansion remains separate qualification.

## Platform disposition

Mac evidence is macOS 26.5.2 arm64, Node 24.19.0, Python 3.14.6 for Hermes and 3.12.12
for bridge/tool, Chromium 156.0.8078.4. WSL evidence is the actual Ubuntu 26.04 x86_64
host and Windows Edge run recorded in [validation.md](validation.md), including actual
native PowerShell Hermes refusal. Both use the same pinned Hermes source revision.

The original matrix also names Ubuntu 24.04 and native Windows OpenClaw launch. Neither
was exercised by the completed WSL session. They remain **unverified**, with no support
claim inferred from other hosts. The owner has been asked whether the tested Mac + WSL
matrix is the final release qualification scope or these remain blocking gates.

The last Mac fixes were tested on Mac; the historical WSL reports retain their actual
commits. They are not relabeled as new WSL executions. Native Windows Hermes continues
to be explicitly unsupported; the actual refusal path passed on Windows.

## Requirements and boundaries

SC-001 through SC-006 have passing scoped evidence across live/controlled agent,
real browser, ownership/policy, fault and preservation tests. SC-007's Mac OpenClaw and
upgrade evidence passes; the final declared platform matrix awaits the decision above.
T029/T034/T039/T052/T053 are complete. T038/T055 await that platform disposition;
T056 follows acceptance with release metadata reconciled against `origin/main` at
`a67aba7369e847ef50fea8542eed919552088d0c` (already an ancestor). Proposed release: 1.7.0; [reviewable release notes](release-candidate.md) are prepared.
The release helper preview passed; VERSION remains 1.6.2 until matrix acceptance.

Hermes uses the dedicated authenticated companion behind the HUD API and private MCP;
port 3000 does not connect directly to the ordinary Hermes gateway. Initial tools are
limited to the reviewed subnet calculator/skill. Attachments, arbitrary network MCPs,
configuration APPLY, model/effort overrides, hosted Avatar, shared memory and auxiliary
context compression are unavailable. Federation remains spec 149. Live CML tool
qualification is not claimed. No package publication or main merge is part of local closure.
