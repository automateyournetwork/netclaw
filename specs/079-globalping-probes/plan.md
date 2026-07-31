# Implementation Plan: Globalping Global Probe Measurement

**Branch**: `079-globalping-probes` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)
**Roadmap**: R8 | **Research**: [research.md](./research.md)

## Summary

Register the official Globalping remote MCP (`https://mcp.globalping.dev/mcp`) and add one skill that gives
NetClaw an outside-in view of the network it otherwise only sees from within.

**There is no server to write.** The endpoint is official, maintained and works. The engineering in this
feature is entirely in the skill and the integration artifacts, and it concentrates on one thing: making sure
NetClaw never reports *"no probe matched your location filter"* as *"the service is down"*.

## Technical Context

**Language/Version**: None — no NetClaw-authored server code. Skill is Markdown; registration is JSON;
integration edits are Bash/JS/Markdown.
**Primary Dependencies**: None new. The remote endpoint is reached by OpenClaw's existing remote-MCP
transport, the same path Datadog and DevNet content search already use.
**Storage**: None. No cache, no state. Measurements are ad-hoc and results are not retained — a stale
external reachability result is worse than no result, so caching would be actively harmful here (contrast
spec 078, where a 6-hour advisory cache is correct because advisories change weekly).
**Testing**: `tests/globalping/run-tests.sh` — offline assertions over registration and skill content, plus
an opt-in `live-api.sh` that spends real measurements.
**Target Platform**: Linux (NetClaw host), remote HTTP transport.
**Project Type**: Remote MCP integration + skill.
**Constraints**: 500 probe-measurements/hour authenticated, shared account-wide. **Cost equals probe count**
— `limit: 20` spends 20 units (research R4, corrected by controlled test). Public targets only.
**Scale/Scope**: 5 measurement tools, ~4,800 probes across ~1,390 ASNs, 1 skill, 8 Principle XI artifacts.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| **I. Safety-First** | PASS | Read-only measurement. No device access, no writes, no config change. |
| **II. Read-Before-Write** | N/A | No writes exist in this feature. |
| **III. ITSM-Gated Changes** | N/A | No changes are made to anything. |
| **IV. Immutable Audit Trail** | PASS | GAIT session recorded at close-out. |
| **V. MCP-Native** | PASS | Consumed strictly as an MCP server; no shelling out to `ping`/`dig`. |
| **VI. Multi-Vendor Neutrality** | PASS | Vendor-independent by nature — measures public infrastructure, not vendor devices. |
| **VII. Skill Modularity** | PASS | One skill, one purpose: outside-in measurement. |
| **VIII. Verify After Change** | N/A | No changes to verify. |
| **IX. Security by Default** | PASS | Token via env only. **Private/internal targets refused locally before any outbound call** (FR-009) — the disclosure boundary is enforced on our side, not theirs. |
| **X. Observability** | PASS | This feature *is* observability, from a vantage point NetClaw has never had. |
| **XI. Artifact Coherence** | **GATE** | All eight artifacts explicit as tasks (T018–T024a). Not assumed. |
| **XII. Documentation-as-Code** | PASS | Skill, README, TOOLS, spec, research all in-repo. |
| **XIII. Credential Safety** | PASS | `GLOBALPING_TOKEN` name-only in `.env.example`. **Note**: `limits` output echoes an 8-character token fragment — flagged in the skill so tool output is not pasted into public places verbatim. |
| **XIV. Human-in-the-Loop for External Comms** | **REVIEW — see below** | This feature transmits to a third party by design. |
| **XV. Backwards Compatibility** | PASS | Purely additive. |
| **XVI. Spec-Driven Development** | PASS | Full chain followed; research measured before speccing. |
| **XVII. Milestone Documentation** | PASS | Blog drafted for review, unpublished. |

### Principle XIV — the one that needs a decision, not a checkmark

Principle XIV governs external communications. This feature has two outbound flows, and they are not equal:

1. **The measurement itself** — a public target, a location filter, a probe count. This is the operation the
   operator asked for. Reaching out is the entire point, and the target is public by definition (private ones
   are refused). No gate needed.

2. **The `context` analytics field** — a 15-25 word natural-language description of *why* the call is being
   made, which the vendor states is used for "analytics and user intent tracking" (research R3). This is
   different in kind. Every other NetClaw integration sends only what the operation requires; this one asks
   for a description of operator intent.

**Resolution**: not gated per call — a confirmation prompt on every ping would make the integration useless
and would train operators to click through. Instead: NetClaw sends a **generic, task-shaped** value carrying
no customer name, internal hostname, ticket reference or topology detail (FR-012), and the skill **states
plainly that the field reaches a third party** (FR-012a) so the operator can decide whether to enable the
integration at all. The disclosure is the control, at the right granularity.

Recorded rather than waved through, because "it's just analytics" is exactly the reasoning that would let a
customer name leave the building.

## Project Structure

### Documentation (this feature)

```text
specs/079-globalping-probes/
├── spec.md
├── plan.md              # this file
├── research.md          # R1-R7, all measured live
├── contracts/
│   └── mcp-tools.md     # the tool surface as measured, incl. what NOT to document
├── quickstart.md
├── tasks.md
└── checklists/
    └── requirements.md
```

### Source (repository)

```text
config/openclaw.json                          # remote MCP registration (FR-001)
workspace/skills/globalping-external-checks/
└── SKILL.md                                  # the actual deliverable
scripts/lib/catalog.sh                        # catalog entry + PROFILE membership
scripts/lib/install-steps.sh                  # component_install_globalping()
ui/netclaw-visual/server.js                   # TWO entries: node list AND annotation map
SOUL.md / README.md / TOOLS.md / .env.example  # identity, tables, env names
docs/COVERAGE-ROADMAP.md                      # R8 status + outcome
tests/globalping/
├── run-tests.sh                              # offline, no measurements spent
└── live-api.sh                               # opt-in, spends real budget
```

**No `mcp-servers/` directory.** That absence is the design decision from research R1, not an omission.

## Phase 0 — Research

Complete. See [research.md](./research.md). Seven questions resolved against the live endpoint; four of the
spec's starting assumptions turned out wrong. R4's budget conclusion was itself wrong on first pass — it
claimed per-call billing, and a controlled test showed billing is **per probe**. That correction is recorded
in R4 rather than overwritten, because the wrong version had already reached the spec, the skill and the
tasks.

## Phase 1 — Design

No data model: there is no persisted entity, no cache and no state. The three outcome shapes that matter
(`no_probes_found` / `0-of-N successful` / locally refused) are documented in
[contracts/mcp-tools.md](./contracts/mcp-tools.md) alongside the tool surface, since they are properties of
the remote contract rather than of a NetClaw schema.

## Phase 2 — Task ordering

1. **Registration first** — nothing can be tested until the endpoint answers through NetClaw.
2. **The skill's safety semantics next** — the three-way distinction is the feature's substance.
3. **Then the composition boundaries** (ThousandEyes, gtrace, inside-out tooling).
4. **Then Principle XI artifacts**, each an explicit task.
5. **Close-out**: gate green, roadmap, GAIT, blog.

## Complexity Tracking

No constitutional violations requiring justification. The feature adds no dependency, no server, no storage
and no write path.

The one deliberate asymmetry worth recording: **this spec forbids caching where the previous one required
it.** Spec 078 caches advisories for 6 hours because Cisco publishes weekly. Here, a cached result would
answer "was it reachable earlier?" when the question is "is it reachable now" — so caching would be actively
harmful regardless of budget. Same-shaped decision, opposite answer, for reasons specific to each domain.

**A correction worth recording**: an earlier draft of research R4 concluded that a call costs one unit
regardless of probe count, and built guidance on "breadth is free". A controlled test showed cost equals
probe count. The wrong conclusion had already reached the spec, the skill and the task list; all were
corrected. Both specs need the *same* economy instinct — they differ only in what a unit buys.
