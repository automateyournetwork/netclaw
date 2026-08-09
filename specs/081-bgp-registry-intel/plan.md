# Implementation Plan: BGP & Registry Intelligence (RPKI / RDAP / PeeringDB / RIPEstat)

**Branch**: `081-bgp-registry-intel` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/081-bgp-registry-intel/spec.md`
**Research**: [research.md](./research.md) — **read R2 first**; it changes the primary data source
**Roadmap**: R9 — Tier 2, "the internet / external plane"

## Summary

Spec 079 (R8) gave NetClaw a vantage point outside its own domain: Globalping *measures* toward a target.
This feature answers the questions that follow — **who is this allocated to, is this announcement
legitimate, where does this network peer** — from four public, unauthenticated sources.

Build `mcp-servers/bgp-intel-mcp/`. Four capability areas plus a narrowed Atlas pair, ~10 tools, read-only
throughout. No credentials exist anywhere in this feature, which removes an entire class of risk present in
specs 078 and 080.

The engineering weight is not in the HTTP. It is in **four distinctions that are trivially easy to collapse
and dangerous when collapsed**, chief among them: **RPKI `not-found` is not `invalid`.** Most of the
internet has no ROA; reporting unsigned space as a finding would manufacture false incidents at scale.

**Phase 0 changed the primary source.** The spec assumed RIPEstat. `rpki-validator.ripe.net` is better on
three counts — RFC 6811 vocabulary natively, `state` and `reason` as separate fields, and the VRPs that drove
the verdict included. All four states are now live-verified against it (research R9).

## Technical Context

**Language/Version**: Python 3.10+, system interpreter. No dedicated venv — two pure-HTTP packages move
nothing shared (unlike spec 076).

**Primary Dependencies**: `mcp>=1.2.0,<2` and `httpx>=0.27.0,<1`. Identical to specs 078 and 080. The `mcp`
upper bound is **load-bearing and now urgent**: Phase 0 confirmed the MCP Python SDK has shipped **v2**
targeting the 2026-07-28 spec, and v2 removes `mcp.server.fastmcp`, which this server imports. Spec 077's
rule is no longer hypothetical.

No RDAP/RPKI/BGP library. The payloads are plain JSON and the value is in the **semantics** — which state
means what — not the transport. An SDK would add a pinning hazard while abstracting the one thing this
feature must not abstract.

**Storage**: **None on disk.** Per-source in-memory TTL cache only (clarification Q3): RPKI 5 min, routing
15 min, RDAP/PeeringDB/Atlas 24 h. Deliberately unlike spec 078, which caches PSIRT data on disk because
that data is large and slow-moving; here the cache is a courtesy buffer for one investigation, not a
registry mirror.

**Testing**: Contract tests over pure functions — envelope/provenance, the four RPKI states, input
refusal, rate limiter, cache TTLs. Live integration tests against all four public sources, which — unlike
spec 080 — need no lab, no credentials and no licence. Harness follows `tests/reconcile/run-tests.sh`
(spec 075): bash + stdlib.

**Target Platform**: Linux. Outbound HTTPS only.

**Project Type**: New vendored MCP server + skill + installer catalog entry.

**Performance Goals**: None. Deliberately **slower than possible** — FR-023a prohibits parallel fan-out.

**Constraints**: ≤ 4 req/s per source, strictly serial (FR-023). Manifest ≤ 5,000 tokens (FR-027a).
Read-only — no write path exists to gate. Every response carries source + retrieval time + outcome
structurally (FR-019). No ASN/geo enrichment: `gtrace` owns it (FR-032).

**Scale/Scope**: 4 data sources, ~10 tools, 5 user stories, 54 FRs, 28 SCs.

**No external blockers.** Every source is public and reachable today — verified before the spec was written
and again in Phase 0. This is the first item since R8 with no lab, licence, trial or entitlement on the
critical path, which is precisely why it was selected while R4 waits on a vendor trial.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Applies | Assessment |
|---|---|---|
| **I — Safety-First (NON-NEGOTIABLE)** | **Yes — inverted** | No device is touched and nothing is changed. The safety risk here is not damage but **false conclusions**: a wrong `valid` says an announcement is authorised when it is not; a wrong `invalid` sends someone chasing a hijack that is not happening. FR-007b makes that asymmetry explicit |
| II — Read-Before-Write | N/A | Read-only feature; there is no write to precede |
| III — ITSM-Gated Changes | N/A | No changes are made. **Deliberately N/A, not "inherited"** — spec 076 was caught claiming inheritance where nothing existed, and the honest answer here is that the principle does not apply |
| **IV — Immutable Audit Trail** | **Yes** | FR-022: every operation GAIT-logged **by construction**, at the same chokepoint as provenance. Spec 080's `/speckit.analyze` caught this exact requirement with a verification task and no implementing task; Stage 2 carries the implementation |
| **V — MCP-Native** | **Yes** | FastMCP, stdio, JSON-RPC lifecycle |
| VI — Multi-Vendor Neutrality | **Yes — vendor-free** | Registries and RIRs, not vendors. Nothing here is vendor-specific |
| **VII — Skill Modularity** | **Yes — drove two clarifications** | FR-032 keeps ASN/geo enrichment with `gtrace`; FR-017a keeps general probe availability with Globalping. Q1 narrowed US5 specifically to avoid duplication |
| VIII — Verify After Change | N/A | No changes |
| **IX — Security by Default** | **Yes** | No credentials to steal. FR-028 refuses private/reserved input **before** any outbound request, so internal addressing is never disclosed to a third party — the same discipline spec 079 applied to Globalping |
| **X — Observability** | **Yes** | Provenance on every result is the feature's core observability property. HUD node required by XI |
| **XI — Artifact Coherence (NON-NEGOTIABLE)** | **Yes — every touchpoint** | FR-038: registration, catalog, profiles, install fn, **both** HUD entries, README/SOUL counts **and** a SOUL capability section, SKILL.md, `.env.example`, `TOOLS.md`, server README. Gated by `reconcile-mcp.py` |
| XII — Documentation-as-Code | Yes | Server README + SKILL.md, same PR |
| **XIII — Credential Safety** | **Yes — trivially** | There are no credentials. `.env.example` gains only optional tuning variables. This is the first roadmap item with no secret to leak |
| XIV — Human-in-the-Loop | N/A | No external communications, no writes |
| XV — Backwards Compatibility | Yes — low risk | Two pure-HTTP packages; nothing shared moves |
| XVI — Spec-Driven Development | Yes | Spec ratified, 5 clarifications resolved, plan precedes implementation |
| XVII — Milestone Documentation | Yes | Blog post at completion, presented for review before publishing |

**Gate result: PASS.** No violations requiring justification.

**Four principles are genuinely N/A here (II, III, VIII, XIV), and that is stated rather than fudged.** Spec
076 was caught claiming Principle III was "inherited from the existing approval path" when nothing
implemented it. A read-only feature that queries public registries has no change to gate, and pretending
otherwise to fill a table cell would be the same dishonesty in a different direction.

**Post-Phase-1 re-check (2026-08-03): still PASS.** Principle I is strengthened by design: the four
distinctions are enforced as distinct typed outcomes rather than prose, so a caller cannot collapse them
even by accident. Principle IV is satisfied at the same chokepoint as provenance, so the spec-080 defect
cannot recur.

## Project Structure

### Documentation (this feature)

```text
specs/081-bgp-registry-intel/
├── spec.md              # Ratified; 5 clarifications
├── plan.md              # This file
├── research.md          # Phase 0 — R2 changed the primary source; R9 verified all four states
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── mcp-tools.md     # Phase 1 — tool surface, provenance envelope, outcome semantics
├── checklists/
│   └── requirements.md  # Spec quality (PASS, revalidated after clarification)
└── tasks.md             # Phase 2 — /speckit.tasks
```

### Source Code (repository root)

```text
mcp-servers/bgp-intel-mcp/
├── server.py                # FastMCP entry point, stdio; tool registration
├── envelope.py              # CHOKEPOINT: source + retrieved_at + outcome + GAIT (FR-019/020/022)
├── outcomes.py              # The typed distinctions — RPKI states, source-failure vs no-record
├── http_client.py           # Rate limiter (4/s serial per source) + TTL cache + User-Agent (FR-023/025/026)
├── validate.py              # Input refusal: private/reserved/bogon/malformed, v4 + v6 (FR-028/029/030)
├── sources/
│   ├── rpki.py              # rpki-validator.ripe.net primary, RIPEstat fallback (research R2)
│   ├── rdap.py              # IANA bootstrap -> direct RIR -> rdap.org fallback (research R4)
│   ├── routing.py           # RIPEstat as-overview + routing-status
│   ├── peeringdb.py         # PeeringDB net/ixlan
│   └── atlas.py             # Anchors + per-AS probe counts ONLY (FR-017a)
├── requirements.txt         # mcp>=1.2.0,<2 · httpx>=0.27.0,<1
└── README.md

workspace/skills/bgp-registry-intel/   # ONE skill — see Structure Decision
config/openclaw.json                   # + registration, repo-relative paths
scripts/lib/catalog.sh                 # + entry, + PROFILE_SECURITY / PROFILE_RECOMMENDED
scripts/lib/install-steps.sh           # + component_install_bgp_intel()
ui/netclaw-visual/server.js            # + node list entry AND annotation map entry (TWO edits)
tests/bgp-intel/                       # contract tests + live integration tests
```

**Structure Decision**: `sources/` splits by **data source**, because each has its own endpoint shape,
failure mode and TTL — and FR-021 requires per-element provenance, which is natural when each module owns
its own attribution. `envelope.py` is a **chokepoint** every response passes through: FR-019 and FR-022 are
only guarantees if omission is structurally impossible, which spec 080 proved works.

`outcomes.py` is separate from `envelope.py` deliberately. The four RPKI states and the
source-failure-vs-no-record distinction are the feature's *domain logic*, not its plumbing, and giving them
their own module means the distinction is reviewable in one place rather than scattered across five source
modules.

**One skill, not four.** Unlike spec 080 — where three appliances with three credential sets justified three
skills under Principle VII — these four sources answer facets of a **single** operator question: "what do I
know about this internet resource?" A user asking about a suspicious prefix wants RPKI *and* registry *and*
routing in one answer. Splitting them would force the model to orchestrate four skills for one question.

## Implementation ordering

**Distinctions and provenance before any source; sources before composition.**

```
Stage 1  Server skeleton, deps, envelope.py + outcomes.py + contract tests   (FR-019/020/022, FR-002)
Stage 2  GAIT audit inside the chokepoint + its tests                        (FR-022, Principle IV)
Stage 3  http_client.py: rate limiter, TTL cache, User-Agent + tests         (FR-023–027)
Stage 4  validate.py: input refusal, v4 + v6 + tests                         (FR-028–030)
Stage 5  US1 — RPKI: all four states, VRPs included, validator named         (FR-001–007c)
Stage 6  US2 — RDAP: bootstrap resolution, per-registry attribution          (FR-008–011)
Stage 7  US3 — routing status; US4 — PeeringDB                               (FR-012–016)
Stage 8  US5 — Atlas anchors + per-AS probe counts only                      (FR-017–018)
Stage 9  Manifest measurement against the 5,000-token ceiling                (FR-027a/b/c)
Stage 10 Artifact coherence: registration, catalog, installer, HUD, docs     (FR-038–042)
Stage 11 Skill, verification table, honest reporting                         (FR-031–033, FR-036/037)
```

**Stages 1–2 before any source.** The four RPKI states are the feature's reason to exist. Writing a source
first and adding the distinction afterwards produces exactly the code that collapses `not-found` into
`invalid`, because collapsing is the path of least resistance once you already hold a string from an API.

**Stage 3 before Stage 5** so no source can be written that bypasses the rate limiter. FR-023b requires
enforcement at the request layer precisely so a tool added later inherits it without knowing it exists.

**Stage 4 before Stage 5** so private-address refusal exists before anything can call out. FR-028 is a
disclosure control, not a validation nicety — the same reasoning spec 079 applied to Globalping.

**Stage 9 before Stage 10** so registration never lands a manifest that breaches the ceiling.

**Stage 5 is the MVP.** US1 alone — "is this announcement legitimate?" — delivers the capability nothing
else in NetClaw has, and the four remaining sources are additive.

## Key design decisions

**Build, not adopt** (research R1). `peerglass` covers a similar surface with **42 tools across 9 phases**
including satellite tracking and DNS-censorship detection. Adopting it means either registering a charter
NetClaw did not choose or suppressing most of it, and 42 tools is the wrong order of magnitude against a
5,000-token ceiling. Notably it arrived independently at three of this spec's clarified decisions — TTL
caching in the 5-minute-to-24-hour band, per-result attribution, read-only — which is reassuring convergent
evidence rather than borrowed design.

**`rpki-validator.ripe.net`, not RIPEstat** (research R2). It reports RFC 6811 vocabulary natively
(`not-found`, not `unknown`), separates `state` from `reason` instead of fusing them into `invalid_asn`, and
returns the VRPs that drove the verdict. FR-004's translation requirement survives only for the RIPEstat
fallback path.

**One validator, and say so** (research R3). A second endpoint is reachable, but **both are RIPE NCC
Routinator** — same engine, same operator, same trust anchors. Comparing them would produce agreement that
means nothing. FR-007a's "explicitly uncorroborated" is therefore evidence-based, not a shrug.

**Deliberately serial** (FR-023a). `peerglass` parallelises for latency; this does the opposite. Against
volunteer-funded infrastructure, being over-polite costs latency nobody notices and being under-polite
costs the integration.

**Per-source TTLs, in memory** (clarification Q3). A stale `valid` is the most dangerous stale value in the
feature, so RPKI gets 5 minutes while RDAP gets 24 hours. One global TTL would be wrong for at least one
source. Nothing on disk: no store to manage, back up or leak.

**An unavailable validator is not a `not-found`** (FR-007c). The feature's core distinction, one level down
— and the subtlest bug available here. When the validator is unreachable, NetClaw must not infer state from
routing data, registry data, or the absence of a ROA.

## Complexity Tracking

> No Constitution Check violations require justification.

| Item | Note |
|---|---|
| Four sources, one skill | Deliberate departure from spec 080's one-skill-per-plane. These answer facets of one question; splitting would force four-skill orchestration for a single ask |
| `outcomes.py` separate from `envelope.py` | The distinctions are domain logic, not plumbing. Keeping them in one reviewable module is the point of the feature |
| Two RPKI endpoints in one module | Primary + documented fallback with different vocabularies. FR-004 exists for the fallback; collapsing to one endpoint would lose resilience |
| Rate limiter slower than necessary | Not an oversight (FR-023a). Free community infrastructure |

## Phase 2 preview

`/speckit.tasks` will produce the dependency-ordered list. Expected shape: Stage 1 blocks everything;
Stage 2 folds into the same chokepoint; Stage 3 and Stage 4 both block Stages 5–8; Stages 5–8 are
independently deliverable per user story; Stage 9 blocks Stage 10.

Three items carried from research as **tasks, not assumptions**:

1. **Measure the manifest** once the surface exists — cannot be done earlier.
2. **Confirm ARIN's reset is not host-specific** before documenting it as a property of ARIN rather than of
   this environment.
3. **Find an ASN genuinely absent from PeeringDB** for SC-010, rather than assuming one exists.

Unlike specs 080 and (pending) 4, **no task here waits on an external party.** Every source is public.
FR-037 therefore sets a harder bar than R3 met: near-total live verification is the expectation, and any
unexercised capability must be justified explicitly or cut.
