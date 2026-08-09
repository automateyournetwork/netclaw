# Specification Quality Checklist: Document Generation

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-03
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
  - Library *names and installed versions* appear only as a dependency-availability finding (FR-030) and as
    evidence for the licence/pin decisions. No code structure, module layout, or API design is specified.
- [x] Focused on user value and business needs
  - The framing is the deliverable gap: NetClaw's output lands in front of CABs, auditors and directors who
    work in Office documents.
- [x] Written for non-technical stakeholders
  - The core discipline ("a document must never fabricate to fill a blank") is stated in plain terms an
    auditor would recognise.
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
  - Five decisions were deferred to `/speckit.clarify` rather than assumed. **All five are now resolved** —
    see `## Clarifications` in the spec and **Decisions taken in clarification** below.
- [x] Requirements are testable and unambiguous
  - Each FR states an observable behaviour. The negative requirements (FR-001 through FR-004) are testable by
    opening a generated document with a known-missing input.
- [x] Success criteria are measurable
  - 22 SCs. SC-009 and SC-020 specifically require *opening the file*, not inspecting code.
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
  - 4 user stories, 14 scenarios.
- [x] Edge cases identified
  - 7, including two that only exist because the output is a document: filename collision against a file
    already attached to a ticket, and untrusted source text being interpreted as a spreadsheet formula.
- [x] Scope is clearly bounded
  - Three explicit boundaries (FR-035/036/037) against diagram skills, rag-mcp, and
    servicenow-change-workflow. Out of Scope names six exclusions.
- [x] Dependencies and assumptions identified
  - All four libraries measured as already installed; the rag-mcp unpinned-declaration hazard is recorded
    rather than glossed.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation leakage into specification

## Constitutional Alignment

- [x] **Principle IV** (immutable GAIT audit) — FR-034, SC-019: every generation including failures.
- [x] **Principle VII** (skill modularity) — FR-035/036/037 draw the boundaries so this does not absorb
      diagram rendering, document ingestion, or CR lifecycle management.
- [x] **Principle XI** (artifact coherence) — FR-038 through FR-041 enumerate every surface, including both
      HUD entries and curated profile membership, plus FR-039's iN2N member artifacts.
- [x] **Principle XIII** (credential safety) — no credentials are introduced (Assumptions); data arrives from
      skills that already hold their own.
- [x] **Principle XIV** (externally-visible actions) — sending a document anywhere is explicitly Out of
      Scope; writing a file is not an outward-facing action.
- [x] **Principle XVI** (spec-driven) — this document.
- [x] **Principle XVII** (blog milestone) — waived by standing operator decision.

## Lessons Carried Forward

- [x] **Spec 076** — do not move a shared dependency version (the `cryptography` incident). FR-030.
- [x] **Spec 077** — `netclaw_pip_install`, never bare pip; upper-bound any pin whose submodule is imported.
      FR-031, FR-032.
- [x] **Spec 078** — record what was not exercised rather than claiming it. FR-042, FR-043, SC-020.
- [x] **Spec 080** — administrative and operational state stay separate columns (FR-015); and the deeper
      lesson that **passing structural tests do not prove the payload is populated** — which is exactly why
      SC-009 and SC-020 require opening the file.
- [x] **Spec 081** — per-element provenance, not one collective citation. FR-009, SC-010.

## Notes

### What makes this feature's central risk new

Specs 078–081 each protected a distinction in *tool output*, which is ephemeral — read once, in context, by
the person who asked. A document is not: it is emailed, filed, and read months later by someone who was not
there, and it carries the authority of its formatting. That is why FR-001 through FR-005 are stated as
prohibitions rather than preferences, and why provenance must be durable in the document body (FR-008)
rather than in a filename or a tool response.

### The licence finding changes the roadmap's plan

The roadmap directed *"vendor the four official skills; note their licence terms explicitly."* Noting the
terms **is** the finding: measured 2026-08-03, the four `anthropics/skills` document skills are
source-available and demonstration-only, not Apache-2.0. Vendoring them into NetClaw is not licence-
compatible, so R18 becomes build-rather-than-adopt — for a **licensing** reason, which is a different
situation from R1/R3/R9 where community options were technically inadequate. FR-028/FR-029.

### Decisions taken in clarification (session 2026-08-03)

All five resolved. Nothing outstanding blocks `/speckit.plan`.

1. **Licence approach** → **Build NetClaw's own outright.** Upstream cited as capability reference only;
   never vendored, and **no install or fetch path for it** (FR-029a, SC-017). One Apache-2.0 code surface.
2. **Tool surface** → **One MCP server + skills on top.** The server owns all writing and stamps generation
   time, attribution and per-element provenance at a single chokepoint; unavailable and failed are typed
   states a caller cannot express as a blank (FR-005a–d). Skills own the four compositions and contain no
   writing logic. Manifest ≤ 5,000 tokens (FR-038a). *Rationale: prose guidance in a skill cannot enforce
   FR-001–FR-004; the envelope chokepoint from specs 080/081 can.*
3. **Provenance rendering** → **Visible per-element attribution plus a sources section** (FR-008a, FR-009a).
   Source column per spreadsheet row; visible inline/footnoted source per figure in documents and decks; a
   sources section with as-of times in every file. **Hidden mechanisms — cell comments, tooltips, document
   metadata — do not satisfy the requirement** and may only be additive. Verified by a forwarding/print test
   (SC-010b). *Rationale: comments are hidden by default, stripped on paste, and absent in print, which are
   exactly the scenarios FR-008 exists for.*
4. **Templates** → **Scratch-only for docx/xlsx/pptx; PDF form filling stays** (FR-023a, FR-024a/b). An
   Office template is rejected with a stated reason. Corporate-branded-template support is an explicit
   follow-on. *Rationale: a PDF form's fields are explicitly named and machine-readable, so "no data for this
   field" is unambiguous; Word/PowerPoint placeholder-matching is the guessing version of the same problem.*
5. **Dependency pinning** → **Upper-bounded pins here, and rag-mcp's declaration corrected to match**
   (FR-032a–d). Bounds describe the already-installed majors; **no installed version moves** (SC-018), and
   rag-mcp ingestion is re-exercised afterwards (SC-018e). *Rationale: two servers declaring conflicting
   requirements for one shared install is worse than either option alone, and PyMuPDF-as-`fitz` is precisely
   spec 077's submodule case.*

### `/speckit.analyze` remediation (2026-08-03) — all 14 findings fixed

Two HIGH, seven MEDIUM, five LOW. Every one applied before implementation; nothing accepted as known-debt.

| ID | Fix |
|---|---|
| C1 | Template rejection extended to `xlsx_write` (T067a) and `pptx_write` (T081a) via a shared helper, plus a parametrised test (T057b). It had been tasked for `.docx` only. |
| C2 | Licence verification task added (T122a) — the constraint that redefined R18 had **zero** tasks. |
| C3 | FR-036/FR-037 boundaries now required in the skills, TOOLS.md and server README (T109b, T110a, T116, T123). Only FR-035 had been tasked. |
| C4 | FR-004's no-inference prohibition added to **both** SKILL.md files (T109a, T110a) — the server cannot fabricate, but the composing agent can, and that half had no home. |
| C5 | `test_manifest_size.py` wired into `run-tests.sh` (T119a); it would otherwise never have run. |
| C6 | Source disagreement promoted from an unbacked edge case to FR-027b + SC-027, with T047b and T057a. |
| C7 | The iN2N Border-only decision now lands in a shipped artifact (T124a), not just the plan. |
| F1 | research.md D9's filenames corrected to match plan.md and tasks.md. |
| F2 | plan.md's shadowing rationale was **measured false** and withdrawn; research D14 records the measurement. The naming is kept for real reasons. |
| U1 | The prose lint's trigger is now defined with an allow-list; "contains a bare number" would have fired on every date. |
| U2 | The read-only surface guard's predicate restated — four of six tools *do* write files, so the original wording was wrong, not merely vague. |
| U3 | Merged-state detection enumerated instead of gestured at. |
| A1 | FR-027a added: `.docx` blocks and `.pptx` slides are now bounded, not spreadsheets alone. |
| A2 | `output_id` (input) vs `safe_id` (sanitised) relationship stated once. |
| D1 | The overloaded SC-018a–e block split: dependency claims stay at SC-018/018a/018b, structural claims move to SC-023/024/025. Two duplicate SCs I introduced during remediation (SC-026/027 restating SC-017/SC-008b) were removed rather than left. |

**Post-remediation traceability**, verified mechanically: 60 FRs, 33 SCs, **145 tasks**, every requirement
has ≥1 task, no task references a requirement that does not exist.

### Deferred to planning (not clarification-blocking)

- **Scale bound for large datasets** (FR-027, SC-016) — the requirement that a bound exist and be stated *in
  the document* is fixed; the specific number is a planning decision informed by what `openpyxl` handles
  comfortably.
- **Whether an iN2N member gets this capability** (FR-039) — the obligation is conditional and the five
  member artifacts are already enumerated; which member, if any, is a planning call.
