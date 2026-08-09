# Spec 095 — Juniper Mist (R5): measure, reject adoption, specify the build

**Status**: measured — adoption rejected, build specified and **gated**
**Branch**: `095-juniper-mist`
**Date**: 2026-08-05
**Roadmap**: [R5](../../docs/COVERAGE-ROADMAP.md) — Juniper Mist (official) + Apstra
**Measurements**: [VERIFICATION.md](VERIFICATION.md) — all live, operator's own org

## Summary

R5 set out to **adopt** Juniper's official remote Mist MCP server, on the 089 model: zero code, zero
install, an endpoint and a token. That is not available.

Measured live against `https://mcp.ai.juniper.net/mcp/mist` with the operator's `ac5` credential:
**7 tools, 11,783 tokens, 2.36× the 5,000-token manifest ceiling**, with no tool-filtering mechanism
in NetClaw's config to load a subset.

Separately, the org available for verification (`NetClaw`, created 2026-08-05) contains **one site and
zero devices**. The assurance capabilities R5 exists to deliver — SLE, Marvis, client troubleshooting —
have no data to return and therefore cannot be verified.

This spec records the measurement, rejects adoption with the number that justifies it, specifies the
build that replaces it, and **gates that build on a populated org** rather than shipping unverifiable
skills.

## Decision

| | |
|---|---|
| **Adopt the remote server** | **Rejected** — 11,783 tokens vs a 5,000 ceiling; no subset mechanism |
| **Build a compact read-only client** | **Specified below; blocked on a populated org** |
| **Apstra** | Deferred to R6, unchanged — the unified HPE candidate covers it and R5/R6 stay paired |
| **R5 roadmap status** | `BLOCKED — measured` (was `NOT STARTED`) |

Precedent: this is the 087 outcome, not the 089 one. Catalyst Center's official server was rejected at
515 tools / 64,420 tokens and replaced with a curated client over the same API. The cause differs —
**Mist fails at seven tools, ~1,678 tokens each** — but the remedy is the same.

## What was measured

| Measurement | Value |
|---|---|
| Server | `mistapi`, version reported as empty string |
| Protocol | MCP `2025-06-18`, streamable HTTP + SSE |
| Tools | 7 — `find_mist_entity`, `get_mist_config`, `get_mist_constants`, `get_mist_insights`, `get_mist_self`, `get_mist_stats`, `search_mist_data` |
| Tool manifest | **11,746 tokens** |
| `instructions` | 37 tokens (170 chars) |
| **Total vs ceiling** | **11,783 — 2.36× over** |
| Mutating operations reachable | **0** — no write verb exists in the manifest |
| Auth | `Authorization: Bearer` **only**; REST-style `Token` is refused |
| Region | `X-Mist-Base-URL` header; absent ⇒ defaults to `api.mist.com` ⇒ 401 for a regional token |

Three findings that outlast this spec:

1. **The chars/4 estimating convention under-reports by 17% here** (10,052 estimated vs 11,783
   measured). Safe for the low-cost adoptions it has been used on; **not safe near the ceiling.**
   Future manifest checks within ~20% of 5,000 must be counted, not estimated.
2. **`get_mist_insights` requires `query_type`, which its schema never declares.** Supplied at the top
   level it is silently dropped, then reported missing; it must be nested inside an undeclared generic
   `params` object. A model working from the schema alone cannot construct a valid SLE call.
3. **A wrong region and a bad token are indistinguishable** — both clouds 401 identically. The region
   must come from the operator's `manage.<region>.mist.com` URL.

## The empty-org problem — why the build is gated

`sites_sle` against an org with zero devices returns `count: 1` and a site ID, with no metrics. **A
site with no telemetry and a site with no problems are the same shape.** Asked about wireless health, a
model receiving that response can report the site as healthy. It is not healthy; it is empty.

This is the R15 box-vs-network distinction and the R13 zero-signature Suricata failure in a new
costume: an absence rendered as a negative finding. NetClaw's discipline is that such traps are
*reproduced and structurally blocked*, not documented and hoped away — and reproducing them requires an
org where the difference is observable.

Building `wireless-assurance`, `client-troubleshooting`, and `marvis-query` skills now would ship three
skills whose central failure mode cannot be tested. R3's FortiManager and FortiAnalyzer planes are
already in that state deliberately; adding three more by default is drift, not a decision.

## The build, when unblocked

A NetClaw-authored read-only Mist client, following 094 (Redfish) for the GET-only posture and 087 for
the dispatcher shape.

- **Transport**: direct to `https://$MIST_API_HOST/api/v1/…`. The remote MCP is not an intermediary;
  its ceiling breach is the reason this exists.
- **Verb discipline**: the client issues **no HTTP verb but `GET`**, as 094's Redfish client does. Write
  reach is absent by construction, not by prompt instruction and not by credential scope.
- **Manifest target**: **≤ 1,500 tokens**, counted with `count_tokens`, never estimated.
- **Tools** (4, org- and site-scoped, each taking an explicit `org_id`):

  | Tool | Purpose |
  |---|---|
  | `mist_inventory` | sites, devices, inventory — what exists |
  | `mist_stats` | device/client/port state — what it is doing now |
  | `mist_assurance` | SLE metrics and Marvis actions — what is wrong |
  | `mist_search` | events, alarms, client sessions — what happened |

- **Emptiness is explicit.** Every response distinguishes *no telemetry* from *no problems*. A zero
  device count in scope makes an assurance answer report "no telemetry — cannot characterise health",
  never a health verdict. This is the trap in §"The empty-org problem" and the client's first assertion.
- **Credential**: an **Observer-role org token**. The operator's current token is `role: admin` and
  carries full write reach over the org — unused by this design, but held. Least privilege is a
  requirement, not a preference.

### Exit conditions

The build proceeds when **either**:

- a Mist org with at least one live AP or switch is reachable (a Juniper SE demo org, or hardware in
  the operator's own org — the org already has `trial_enabled: true`), **or**
- the operator accepts, explicitly and on the record, that the assurance tools ship unverified against
  real telemetry, as R3's manager and analyzer planes did.

The first is preferred. Neither is resolved by more implementation work in this repository.

## Scope

**In scope**: the measurement above; the adoption decision; the client design; the roadmap status
change; a committed probe script so both blockers are re-checkable by anyone.

**Out of scope**: the client implementation (gated); skills (gated on the client); Apstra (R6);
`config/openclaw.json` registration — **nothing is registered by this spec**, so no catalog entry,
install step, or `EXTERNAL_INTEGRATIONS` record is due. `docs/ADDING-AN-MCP.md` applies in full to the
build, not to this measurement.

## Artifacts

| Path | What |
|---|---|
| `specs/095-juniper-mist/spec.md` | this document |
| `specs/095-juniper-mist/VERIFICATION.md` | every measurement, reproducible |
| `scripts/probe-mist-mcp.py` | re-runs the manifest and ceiling check |
| `.env.example` | `MIST_API_HOST`, `MIST_ORG_ID`, `MIST_API_TOKEN` — names only |
| `docs/COVERAGE-ROADMAP.md` | R5 → `BLOCKED — measured`, with the number |

## Success criteria

- **SC-001** — The ceiling breach is a counted number from the live endpoint, not an estimate. ✅ 11,783
- **SC-002** — The rejection names a mechanism (no tool filtering across 101 servers), not a preference. ✅
- **SC-003** — The empty-org trap is stated as an observed response shape, not a hypothetical. ✅
- **SC-004** — Both schema defects are reproduced with the exact arguments that trigger them. ✅
- **SC-005** — The credential's `admin` role is recorded, with least privilege required on the build path. ✅
- **SC-006** — No capability is claimed that was not exercised. The only tool proven against real data is
  `get_mist_constants` (284 device models), a static catalogue. ✅
- **SC-007** — Assurance skills are not built against an org that cannot exercise them. ✅ (gated)
