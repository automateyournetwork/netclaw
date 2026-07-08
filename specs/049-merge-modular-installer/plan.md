# Implementation Plan: Merge Modular TUI Installer with Full Component-Coverage Parity

**Branch**: `049-merge-modular-installer` | **Date**: 2026-07-08 | **Spec**: `specs/049-merge-modular-installer/spec.md`
**Input**: Feature specification from `/specs/049-merge-modular-installer/spec.md`

## Summary

Complete community PR #96 (`calcuttin:feat/installer-tui-refactor`) directly on the contributor's branch: resolve its merge conflict with main, backfill the ~9 confirmed component-catalog gaps (GNS3, DevNet content search, Three.js viz + Sketchfab, the UDP telemetry receiver trio, Ollama, Memory MCP, Nautobot Golden Config, Nautobot Routing, base Twilio vs. Twilio Voice), retrofit spec 048's chrome-devtools-mcp as a new catalog entry + install function, build a repeatable coverage-check script so this class of drift cannot recur silently, and amend Constitution Principle XI to describe the new `catalog.sh` + `install-steps.sh` pattern. Push the completed result back onto `calcuttin:feat/installer-tui-refactor` (maintainer edits are enabled on PR #96) so it merges under the contributor's own PR, preserving their authorship.

## Technical Context

**Language/Version**: Bash (matches every existing NetClaw install/enable script and PR #96's own implementation), Python 3.10+ (for the coverage-check script, extending the existing `scripts/verify-inventory-counts.py` pattern)
**Primary Dependencies**: None beyond what's already vendored — PR #96's own `scripts/lib/*.sh`, the repo's existing Python stdlib-only tooling convention
**Storage**: N/A (installer logic + a plain-text component manifest at `~/.openclaw/netclaw-components.conf`, per PR #96's own design)
**Testing**: `bash -n` syntax checks on all modified/added shell files (matches PR #96's own stated test plan); the new coverage-check script itself is the functional test for FR-001/002/008; a dry-run install of the retrofitted chrome-devtools component
**Target Platform**: Linux, macOS, WSL2 — same targets as PR #96 and spec 048
**Project Type**: Installer/tooling merge — no application runtime code, single project
**Performance Goals**: N/A (installer runs interactively or as a short scripted CLI invocation; no throughput/latency target applies)
**Constraints**: Must not reduce installable coverage versus current main (FR-003); must preserve PR #96's own design decisions (TUI, profile system, catalog format) unchanged; chrome-devtools retrofit must preserve the no-sudo, explicit-binary-path behavior already validated in spec 048
**Scale/Scope**: ~9 new/expanded catalog entries plus their install functions, one new coverage-check script, one constitution amendment, one git merge conflict resolution across `scripts/install.sh`, `README.md`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | N/A | Installer/tooling change; no device interaction. |
| II. Read-Before-Write | N/A | No device configuration involved. |
| III. ITSM-Gated Changes | N/A | Not a production network change. |
| IV. Immutable Audit Trail | N/A | Installer runs are local, operator-initiated, not GAIT-logged operations (consistent with every existing `*-enable.sh`/`install.sh` precedent). |
| V. MCP-Native Integration | PASS | This feature touches how MCP servers get *registered by the installer*, not the MCP protocol itself; no new bespoke protocol introduced. |
| VI. Multi-Vendor Neutrality | PASS | Catalog entries stay vendor-neutral in structure (id/category/name/description); no vendor logic added to shared installer code. |
| VII. Skill Modularity | PASS | No skill content changes; this is purely installer/tooling plumbing. |
| VIII. Verify After Every Change | PASS (adapted) | "Verify" here means the coverage-check script (FR-001/002/008) plus PR #96's own existing post-install component verification — the installer-appropriate analogue of this principle, not a device-config verify. |
| IX. Security by Default | PASS | Preserves PR #96's own no-sudo-by-default posture and the chrome-devtools retrofit's existing no-credential design; adds no new elevated-privilege path. |
| X. Observability as First-Class | N/A | No new monitored system; installer coverage is observable via the new coverage-check script's own output. |
| XI. Full-Stack Artifact Coherence | PASS (this feature's core subject) | This feature *is* the update to what XI's checklist points at — the amendment itself is the artifact-coherence work for the installer's own structure. |
| XII. Documentation-as-Code | PASS | README.md (already touched by PR #96) and the constitution both get updated in this same effort. |
| XIII. Credential Safety | PASS | No new credential handling; the chrome-devtools retrofit continues to require zero credentials, matching spec 048. |
| XIV. Human-in-the-Loop | PASS | Pushing to a third party's fork branch and closing/superseding a PR are both irreversible-ish, visible-to-others actions — confirmed explicitly with the operator before execution (already done in conversation). |
| XV. Backwards Compatibility | PASS (this feature's core subject) | FR-003 *is* the backwards-compatibility requirement — no existing installable capability may be lost. |
| XVI. Spec-Driven Development | PASS | Following full SDD workflow for this merge, per the operator's own request. |
| XVII. Milestone Documentation | DEFERRED | Applies post-implementation (blog post already deferred pending the combined 048+049 post, per prior conversation). |

## Project Structure

### Documentation (this feature)

```text
specs/049-merge-modular-installer/
├── plan.md              # This file
├── research.md          # Phase 0 output — the full catalog gap analysis
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output — catalog entry / install function format contract
└── tasks.md             # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

```text
scripts/install.sh                    # PR #96's thin dispatcher (unchanged design, conflict-resolved)
scripts/lib/common.sh                 # PR #96's shared helpers (unchanged)
scripts/lib/tui.sh                    # PR #96's TUI (unchanged)
scripts/lib/catalog.sh                # + ~9 new/expanded entries (gap backfill + chrome-devtools)
scripts/lib/install-steps.sh          # + one component_install_<id>() per new/expanded entry
scripts/lib/netclaw-logo.ans          # PR #96's asset (unchanged)
scripts/lib/make-logo-art.py          # PR #96's generator (unchanged)
scripts/setup.sh                      # PR #96's credential-prompt integration (unchanged design)
scripts/verify-catalog-coverage.py    # NEW — coverage-check script (FR-001, FR-002, FR-008)
scripts/chrome-devtools-enable.sh     # Existing (spec 048) — role decided in research.md, kept or absorbed
.specify/memory/constitution.md       # Amended: Principle XI text + version bump + Sync Impact Report
README.md                             # PR #96's rewritten Quick Start, reconciled with main's current content
```

**Structure Decision**: Work happens directly on top of PR #96's branch (fetched locally as `pr-96-review`, tracking `refs/pull/96/head`), not a from-scratch reimplementation. The only new file is `scripts/verify-catalog-coverage.py`; everything else is additive entries inside PR #96's own files, following its own established conventions exactly (catalog line format, `component_install_<id>()` function shape). The completed branch is pushed back to `calcuttin:feat/installer-tui-refactor` (maintainer edits confirmed enabled) so it lands as PR #96, preserving the contributor's authorship on their original commit.

## Complexity Tracking

> No constitution violations requiring justification. The one principle worth calling out explicitly: XIV (Human-in-the-Loop) — pushing to a third-party contributor's fork and any decision to close/supersede their PR are both actions visible to someone outside this session, and were explicitly discussed and confirmed with the operator before this plan was written, not assumed.
