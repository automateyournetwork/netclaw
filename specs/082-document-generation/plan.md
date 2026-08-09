# Implementation Plan: Document Generation (docx / pptx / xlsx / pdf)

**Branch**: `082-document-generation` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)
**Roadmap**: R18, Tier 5 — *"Best effort-to-value ratio on the roadmap"*

## Summary

NetClaw's output lands in front of change advisory boards, auditors and directors — people who work in
Office documents. It can render Three.js topologies, drawio, markmap, UML, Blender and UE5, and cannot
produce a change-record `.docx`, an interface-audit `.xlsx`, an executive `.pptx`, or fill a PDF form. This
closes that deliverable gap.

**Approach**: one NetClaw-authored MCP server, `document-mcp`, owns all document writing behind a single
chokepoint that stamps generation time, NetClaw attribution and per-element provenance on every artefact —
the envelope pattern specs 080 and 081 used to make attribution structurally impossible to omit. Two skills
sit on top: `document-generation` (the capability and its discipline) and `network-report-documents` (the
four compositions). Six tools, no credentials, no device access, no ticket writes.

**The core discipline is new in kind, not degree.** Specs 078–081 each protected a distinction in *tool
output*, which is ephemeral. A document is emailed, filed, and read months later by someone who was not
there, and it carries the authority of its formatting. So a missing value is a **typed state a caller cannot
express as a blank**, not a convention a model is asked to follow.

**Two roadmap assumptions were measured false and are corrected here**: the upstream skills cannot be
vendored (source-available, demonstration-only — not Apache-2.0), and the dependency situation is worse than
"already present for rag-mcp" implied — rag-mcp declares them unpinned in a `pyproject.toml` the spec-077
checker has never read.

## Technical Context

**Language/Version**: Python 3.10+, system interpreter. No dedicated venv — the four libraries are already
installed and shared with `rag-mcp`; a venv would duplicate hundreds of megabytes of wheels to no benefit.
(Spec 076 needed one because Nornir/NAPALM/Netmiko conflicted; nothing here conflicts.)

**Primary Dependencies** — all four **already installed**, measured 2026-08-03:

| Distribution | Import | Installed | Declared bound |
|---|---|---|---|
| `python-docx` | `docx` | 1.2.0 | `>=1.1,<2` |
| `openpyxl` | `openpyxl` | 3.1.5 | `>=3.1,<4` |
| `python-pptx` | `pptx` | 1.0.2 | `>=1.0,<2` |
| `PyMuPDF` | **`fitz`** | 1.28.0 | `>=1.24,<2` |
| `mcp` | `mcp.server.fastmcp` | — | `>=1.2.0,<2` (load-bearing, spec 081) |

No new packages. No installed version moves (FR-032c, SC-018).

**Storage**: none. Files land in `workspace/output/document-mcp/` (gitignored, feature 046's convention).
GAIT records append to `~/.openclaw/gait/document-mcp.jsonl`.

**Testing**: `tests/document/run-tests.sh` — plain Python, stdlib only, no pytest, following
`tests/bgp-intel/`. Suites **reparse the generated files and assert on their contents**, because spec 080
shipped three nulls past 24 passing tests that only checked envelope shape.

**Target Platform**: Linux, stdio MCP server invoked by OpenClaw.

**Project Type**: MCP server + skills, matching every NetClaw-authored integration.

**Performance Goals**: not latency-sensitive. Bound: 50,000 data rows per worksheet (`DOCUMENT_MAX_ROWS`),
with the bound written **into the document** when applied (FR-027).

**Constraints**: manifest ≤ 5,000 tokens (FR-038a); no credentials anywhere; read-only with respect to
infrastructure (FR-033); never overwrite an output file (FR-018, enforced with `O_EXCL`).

**Scale/Scope**: 6 tools, 2 skills, ~10 server modules, 7 test suites.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 below.*

| Principle | Status | How |
|---|---|---|
| **I. Safety-First (NON-NEGOTIABLE)** | ✅ | No device access, no ticket writes, no destructive path. The only side effect is a new file in a gitignored directory. |
| **II. Read-Before-Write** | ✅ n/a | No infrastructure write exists. `pdf_inspect_form` before `pdf_fill_form` is the same discipline applied to the one artefact this feature does read. |
| **III. ITSM-Gated Changes** | ✅ n/a | FR-033: no device or ticket is touched, so no gate is designable. Stated explicitly rather than silently skipped — spec 080's analyze caught exactly this kind of omission. |
| **IV. Immutable Audit Trail** | ✅ | FR-034/SC-019: every generation **including refusals** writes a GAIT record at the chokepoint. Verified by `test_provenance.py`, not merely asserted. |
| **V. MCP-Native Integration** | ✅ | FastMCP, stdio, registered in `config/openclaw.json` with repo-relative paths. |
| **VI. Multi-Vendor Neutrality** | ✅ | The server holds no vendor knowledge — it renders TaggedValues. Vendor specifics live in the upstream skills that produce the data. |
| **VII. Skill Modularity** | ✅ | FR-035/036/037 draw hard boundaries against diagram skills, `rag-mcp`, and `servicenow-change-workflow`. FR-005d keeps writing logic out of skills and composition out of the server. |
| **VIII. Verify After Every Change** | ✅ | Every acceptance test **opens the produced file**. FR-025/042/043: a code path that ran without error is not evidence. |
| **IX. Security by Default** | ✅ | FR-026: untrusted text is forced to `inlineStr` so a leading `=` cannot become a live formula (measured, research D5). Embedded image paths are constrained to the workspace output dir. |
| **X. Observability** | ✅ | GAIT per call; `list_documents` makes output discoverable; `written_with_gaps` is a distinct outcome from `ok` so incompleteness is observable. |
| **XI. Artifact Coherence (NON-NEGOTIABLE)** | ✅ | FR-038–FR-041 enumerate all 14 checklist items plus the two easy-to-miss ones (curated profile membership; **both** HUD entries) and the SOUL capability section. `reconcile-mcp.py` must exit 0. |
| **XII. Documentation-as-Code** | ✅ | spec, research, data-model, contracts, quickstart, 2 SKILL.md, server README, TOOLS.md, .env.example, VERIFICATION.md. |
| **XIII. Credential Safety** | ✅ | No credentials exist in this feature. Data arrives from skills that already hold their own. Nothing to redact — but the GAIT record still logs shapes, not payloads. |
| **XIV. Human-in-the-Loop for External Comms** | ✅ | **Sending is explicitly out of scope.** Writing a file is not an outward-facing action; `slack-report-delivery`/`webex-report-delivery` own delivery and already carry the gate. |
| **XV. Backwards Compatibility** | ⚠️ **one touch** | This feature edits `mcp-servers/rag-mcp/pyproject.toml` (FR-032b) and `scripts/check-dependency-pins.py`. Both are additive-bound corrections that move no installed version; FR-032d requires re-exercising rag-mcp ingestion afterwards. See Complexity Tracking. |
| **XVI. Spec-Driven Development** | ✅ | specify → clarify (5 Q) → plan → tasks → analyze → implement. |
| **XVII. Milestone Documentation (WordPress)** | ⏭️ **waived** | Standing operator decision: blog posts skipped. Recorded, not silently dropped. |

### Artifact Coherence Checklist (constitution §282) — mapped

| Item | Target |
|---|---|
| README.md (description, architecture, counts) | new rows in the MCP table, 2 skill rows, 4 count sites → 155 / 209 |
| `scripts/lib/catalog.sh` | `document\|Platform Services\|Document Generation\|…` + `PROFILE_RECOMMENDED` |
| `scripts/lib/install-steps.sh` | `component_install_document()` |
| `verify-catalog-coverage.py` | passes |
| `ui/netclaw-visual/server.js` | **two** entries: `INTEGRATION_CATALOG` node + `ENV_MAP` annotation |
| SOUL.md | capability section + 2 count sites → 209 / 155 |
| `workspace/skills/<name>/SKILL.md` | `document-generation`, `network-report-documents` |
| `.env.example` | 4 optional vars, box-header block |
| TOOLS.md | `## Document Generation (\`document-mcp\`, NetClaw-native)` |
| `config/openclaw.json` | `document-mcp` entry, repo-relative |
| `mcp-servers/document-mcp/README.md` | created |
| GAIT session log | recorded |
| Existing skills unbroken | rag-mcp ingestion re-exercised (FR-032d) |
| WordPress blog post | waived by operator |

## Project Structure

### Documentation (this feature)

```text
specs/082-document-generation/
├── plan.md                      # this file
├── spec.md                      # 58 FRs, 31 SCs, 5 clarifications
├── research.md                  # Phase 0 — 13 measured findings
├── data-model.md                # Phase 1 — TaggedValue and friends
├── quickstart.md                # Phase 1
├── contracts/
│   └── mcp-tools.md             # Phase 1 — 6 tools
├── checklists/
│   └── requirements.md
├── VERIFICATION.md              # honest per-format status (FR-042/043)
└── tasks.md                     # Phase 2 — /speckit.tasks
```

### Source code (repository root)

```text
mcp-servers/document-mcp/
├── server.py                # FastMCP entrypoint, stdio, 6 @mcp.tool defs
├── envelope.py              # THE CHOKEPOINT — emit/refused + GAIT      (FR-005b, FR-034)
├── outcomes.py              # Outcome enum + TaggedValue vocabulary      (FR-005c)
├── provenance.py            # SourceRecord accumulation, Sources model   (FR-006..FR-010)
├── output.py                # O_EXCL timestamped writer                  (FR-016..FR-020)
├── sanitize.py              # untrusted text; the openpyxl forced-string (FR-026)
├── writers/
│   ├── __init__.py
│   ├── docx_writer.py       # inline Source column, footer, Sources section
│   ├── xlsx_writer.py       # per-row Source column, failed rows, Sources sheet
│   ├── pptx_writer.py       # visible on-slide source line, Sources slide
│   └── pdf_writer.py        # named-field fill, unfilled/unmatched
├── requirements.txt         # bounded pins
└── README.md

workspace/skills/
├── document-generation/SKILL.md         # capability + discipline + limits
└── network-report-documents/SKILL.md    # the four compositions

tests/document/
├── run-tests.sh
├── test_tagged_values.py    # v-without-src refused; unavailable ≠ failed ≠ {"v":""}
├── test_provenance.py       # REPARSE each file: stamp, per-element source, Sources section
├── test_no_fabrication.py   # gaps render explicitly; failed rows present; counts honest
├── test_sanitize.py         # =1+1 → data_type 's', raw XML has no <f>
├── test_pdf_forms.py        # round-trip, non-fillable, unfilled + unmatched
├── test_output_paths.py     # same-second writes don't collide; first file untouched
└── test_manifest_size.py    # ≤ 5,000 tokens + read-only surface guard

# Modified elsewhere
config/openclaw.json                     # + document-mcp
scripts/lib/catalog.sh                   # + entry, + PROFILE_RECOMMENDED
scripts/lib/install-steps.sh             # + component_install_document()
scripts/check-dependency-pins.py         # read pyproject.toml; dist→module alias map
mcp-servers/rag-mcp/pyproject.toml       # bound the unpinned declarations
ui/netclaw-visual/server.js              # + INTEGRATION_CATALOG, + ENV_MAP
README.md · SOUL.md · TOOLS.md · .env.example
docs/COVERAGE-ROADMAP.md                 # ALREADY DONE — R18 licence correction
```

Note the writer module filenames are `docx_writer.py`, `xlsx_writer.py`, `pptx_writer.py`, `pdf_writer.py`.
An earlier draft of this plan justified the suffix as avoiding shadowing of the third-party packages;
**that was measured false** (research D14) — inside the `writers/` package, `from pptx import Presentation`
resolves to the real package, because Python 3 imports are absolute by default. Shadowing bites only for a
module at the *top level* of the inserted directory. The names are kept for readability at the call site and
because they stay safe if `writers/` is ever flattened into the server directory — not for a hazard that
does not exist at this layout.

**Structure Decision**: one MCP server plus two skills, modelled on `bgp-intel-mcp` (spec 081 — the newest,
and the one that correctly factored `Outcome` out of `envelope.py`). Four servers (one per format) was
rejected: it quadruples registration, install functions and HUD pairs while forcing the shared provenance
logic into either duplication or a fifth shared surface.

## Implementation Phases

| Phase | Content | Gate |
|---|---|---|
| **A. Foundation** | `outcomes.py`, `envelope.py`, `provenance.py`, `output.py`, `sanitize.py` + their tests | `test_tagged_values`, `test_output_paths`, `test_sanitize` pass |
| **B. US1 + US2 (both P1)** | `docx_writer.py`, `xlsx_writer.py`, `docx_write`, `xlsx_write`; `test_provenance`, `test_no_fabrication` | A real `.docx` and `.xlsx` produced **and opened** |
| **C. US3 (P2)** | `pptx_writer.py`, `pptx_write` | A real `.pptx` produced and opened, with an embedded diagram from an existing skill |
| **D. US4 (P3)** | `pdf_writer.py`, `pdf_inspect_form`, `pdf_fill_form`; `test_pdf_forms` | A real form filled and reopened |
| **E. Dependency correction** | bound `document-mcp/requirements.txt`; bound `rag-mcp/pyproject.toml`; teach `check-dependency-pins.py` to read pyproject + dist→module aliases | rag-mcp ingestion re-exercised (FR-032d); `reconcile-mcp.py` exit 0 |
| **F. Skills + artifacts** | 2 SKILL.md, catalog, install-steps, openclaw.json, both HUD entries, README/SOUL/TOOLS/.env.example, server README, README drift fix (research D13) | `reconcile-mcp.py` exit 0; `verify-inventory-counts.py` exit 0; `trace-skill.py` resolves both skills |
| **G. Honest verification** | `VERIFICATION.md`, manifest measurement, live end-to-end run | Per-format table distinguishing **produced-and-opened** from **executed-without-error** |

Phases B, C and D are independently shippable — each user story stands alone, per the spec's priority
ordering. E is sequenced after D so a dependency change cannot be blamed for a writer bug.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Editing another feature's file** (`rag-mcp/pyproject.toml`) — Principle XV touch | rag-mcp declares the same four libraries **unpinned**. If this feature bounds them only for itself, two servers declare conflicting requirements for one shared install. | Bounding here only (clarification option A) leaves the conflict *and* rag-mcp's pre-existing spec-077 hazard. Deferring to a follow-on (option D) ships a known conflict. Mitigated by FR-032c (no installed version moves) and FR-032d (re-exercise rag-mcp ingestion). |
| **Modifying a shared tool** (`scripts/check-dependency-pins.py`) | The checker reads `requirements.txt` only, so rag-mcp has **never been scanned** — its clean bill of health is an artefact of invisibility. It also matches by distribution name, so `pymupdf`→`fitz` would be missed even if scanned. | Fixing only rag-mcp's declaration patches one instance and leaves every future `pyproject.toml`-declaring server unchecked. The baseline is `reconcile-mcp.py` exit 0, so the change must keep it at 0 while catching strictly more. |
| **Fixing pre-existing README drift** (research D13) | README was never updated for specs 080/081 — no MCP rows for Fortinet or BGP-intel, no `bgp-registry-intel`/`fortigate-ops`/`fortianalyzer-ops` skill rows. `verify-inventory-counts.py` misses it because it checks headline arithmetic, not table membership. | This feature edits those exact tables anyway. Leaving it means the next feature inherits a README two specs behind, and the drift compounds silently because no check catches it. |

## Post-Design Constitution Re-Check

Re-evaluated after Phase 1. **No new violations.** Three notes:

1. **Principle IV strengthened by design, not just declared.** Spec 080's `/speckit.analyze` caught GAIT
   having verification but no implementation — the same defect it had caught in spec 076. Here GAIT emission
   is inside `envelope.emit()`, which every writer must pass through, and `test_provenance.py` asserts the
   record exists for a refusal as well as a success. There is no code path that writes a file without one.

2. **Principle IX gained a concrete threat.** Phase 0 measured that openpyxl converts a leading `=` into
   `<f>1+1</f>` — a live formula built from untrusted device or ticket text. FR-026 was written before that
   was confirmed; it is now backed by a measurement and a specific mitigation (`data_type='s'` at the single
   write helper, verified against raw sheet XML).

3. **Principle XI's surface grew by one.** Beyond the constitution's 14 items, `docs/ADDING-AN-MCP.md` names
   two easy-to-miss extras — curated install-profile membership, and the fact the HUD needs **two** entries —
   both of which are in the task list rather than assumed. The iN2N five-artifact obligation is **not**
   triggered (research D11: this is Border work by construction, since it holds no credentials and composes
   across domains), and that is recorded as a decision rather than an omission.

## Artifacts Generated

| File | Phase |
|---|---|
| `research.md` | 0 — 13 findings, all measured on this machine |
| `data-model.md` | 1 — TaggedValue, SourceRecord, DocumentStamp, block/sheet/slide/form models, Outcome |
| `contracts/mcp-tools.md` | 1 — 6 tools, shared types, refusal table, non-goals |
| `quickstart.md` | 1 — install, four workflows, the one rule, three stated limits |
| `plan.md` | this file |

**Next**: `/speckit.tasks`.
