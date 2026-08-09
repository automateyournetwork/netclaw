# Specification Quality Checklist: BGP & Registry Intelligence

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-03
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

**On "no implementation details":** the spec names specific data sources (RIPEstat, PeeringDB, RDAP,
RIPE Atlas) and cites measured HTTP behaviour. This is deliberate and is not implementation leakage —
those services *are* the capability, and their observed quirks are requirements. FR-004 exists only
because RIPEstat's `unknown` diverges from RFC 6811's `NotFound`; FR-011 exists only because ARIN's
RDAP resets the connection from this host. A spec that abstracted those away would have to be
rediscovered during implementation, which is exactly what spec 080 paid for.

Concrete NetClaw artifacts (`config/openclaw.json`, `catalog.sh`, `reconcile-mcp.py`) are likewise
retained: Constitution Principle XI makes artifact coherence a non-negotiable **acceptance condition**,
not a design choice.

**Grounded before writing, not after.** Every capability was reachability-tested on 2026-08-03 before a
line of spec was written, and all four RPKI states were observed live rather than read from
documentation:

| Observation | Result |
|---|---|
| `AS13335` + `1.1.1.0/24` | `valid` |
| `AS13335` + `8.8.8.0/24` | `invalid_asn` (ROA authorises AS15169) |
| `AS3356` + `4.0.0.0/9` | `unknown` — i.e. RFC 6811 `NotFound` |
| ARIN RDAP | connection reset — unusable from this host |
| `rdap.org` bootstrap, RIPE RDAP | 200 |
| PeeringDB, RIPEstat, RIPE Atlas | 200, unauthenticated |
| Rate-limit headers | **none advertised** by RIPEstat or PeeringDB |

This is the direct lesson of R3/R4: front-load lab and API reality *before* committing to scope. Spec
080 discovered its lab problem at implementation time and lost most of a day; R4 is currently waiting on
a human-reviewed vendor trial. R9 was chosen for this slot precisely because its backends are public, and
that choice was validated by testing rather than assumed.

**Informed defaults taken** (all recorded in Assumptions):

| Open question | Default | Why |
|---|---|---|
| Which RPKI validation source? | RIPEstat | The only one verified working; Cloudflare's documented path 404s. A corroborating second validator is desirable but not assumed available |
| Which RDAP entry point? | Bootstrap / RIPE, not ARIN direct | Measured: ARIN resets. Not a preference |
| RIPE Atlas scope | Read-only inventory only | Measurement needs credentials and credits, and R8 already owns outside-in measurement |
| Write path | None | Registry lookups change nothing; there is no gate to design, unlike spec 080 |
| IRR/RPSL, BGP communities | Deferred | Adjacent but a distinct data model; better as its own item than half-delivered |

---

## Post-clarification revalidation (2026-08-03)

`/speckit.clarify` asked 5 questions; all 5 answered and integrated. Checklist re-run — **all items still
pass**. Three of the five replaced unquantified adjectives or soft verbs with testable numbers, which was
the main quality risk in the first draft.

| # | Question | Answer | Spec impact |
|---|---|---|---|
| 1 | Does US5 survive the Globalping overlap? | **Kept, narrowed** to Atlas anchors + per-AS probe counts | US5 rewritten; FR-017 narrowed; new FR-017a routes general probe-availability to Globalping; SC-011 tightened |
| 2 | Self-imposed request rate? | **≤ 4/s per source, strictly serial** | FR-023 became a number; new FR-023a bans parallel fan-out, FR-023b requires enforcement at the request layer; new SC-016a asserts it from an observed request timeline |
| 3 | Cache lifetime and location? | **Per-source TTLs, in memory only** | FR-026 became a TTL table; FR-026a forbids an on-disk store; FR-026b requires cache-age reporting; FR-026c adds force-fresh; SC-017a/b added |
| 4 | Tool-manifest ceiling? | **Same 5,000 tokens as spec 080** | New FR-027a/b/c and SC-020a, with a build-failing test |
| 5 | One RPKI validator or two? | **One, named, explicitly uncorroborated** | New FR-007a/b/c and SC-005a/b; Assumptions rewritten to make corroboration a Phase 0 question |

**Two answers worth recording the reasoning for**, because both were the *less* impressive-sounding option:

**Q5 chose honesty over apparent rigour.** Requiring two validators reads stronger, but it would have
specified a corroboration flow against Cloudflare's endpoint — which **404s as measured**. That is exactly
the "assume the API, discover otherwise at implementation" failure that cost spec 080 most of a day. FR-007c
now also forbids the subtle version of the same error: if the validator is unreachable, NetClaw reports
*validation unavailable*, never falling back to inferring state from routing or registry data. **An
unavailable validator is not a `not-found`** — which is the feature's core distinction reappearing one level
down.

**Q3 chose no persistent state.** Spec 078 caches PSIRT data on disk and is right to; that data is large and
slow-moving. Here the goal is only to avoid hammering a free service within one investigation, so an
in-memory buffer is sufficient and avoids a store to manage, back up, or leak. Per-source TTLs were
necessary because RPKI and RDAP volatility differ by orders of magnitude — a single TTL would be wrong for
at least one source, and a stale `valid` is the most dangerous stale value in the feature.

**Still deferred to Phase 0 research** (correctly — these need evidence, not opinion): build-vs-adopt across
any existing community BGP/RPKI MCP servers, and whether a second reachable RPKI validator exists.
