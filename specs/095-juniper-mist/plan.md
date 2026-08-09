# Implementation Plan: Juniper Mist (R5) — measure, reject adoption, specify the build

**Branch**: `095-juniper-mist` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)
**Measurements**: [VERIFICATION.md](VERIFICATION.md)

> **Note on sequence.** This plan was written **after** `spec.md`, in the same session and before the
> feature merged — not a post-merge reconstruction like 087–094. The gap it closes is that 095
> originally shipped `spec.md` + `VERIFICATION.md` alone, which breached Principle XVI's
> specify → plan → task → implement requirement.
>
> Nothing was implemented before this plan existed, because **the feature's outcome is a decision,
> not code.**

## Summary

R5 set out to **adopt** Juniper's official remote Mist MCP on the 089 model — remote endpoint, zero
code. That is not available: **7 tools, 11,783 tokens, 2.36× the ceiling**, with no tool-filtering
mechanism in NetClaw's config to load a subset.

Separately, the org available for verification has **1 site and 0 devices**, so the assurance
capabilities R5 exists to deliver cannot be exercised.

This spec therefore delivers a **measurement, a rejection with the number that justifies it, a build
specification, and a gate on that build** — rather than an integration.

## Technical Context

**Language/Version**: None authored. The deliverable is documentation plus one stdlib Python probe
script
**Primary Dependencies**: None. `scripts/probe-mist-mcp.py` is Python stdlib only (`urllib`, `json`);
`--count` mode calls the Anthropic `count_tokens` endpoint
**Storage**: None
**Testing**: Live measurement against `https://mcp.ai.juniper.net/mcp/mist` with the operator's own
`ac5` credential; re-runnable via the committed probe
**Target Platform**: Any — the endpoint is remote
**Project Type**: Roadmap measurement + deferred build specification
**Constraints**: Manifest ceiling 5,000 tokens; **no credential may enter the repository**
**Scale/Scope**: 7 upstream tools measured; 0 registered

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **V. MCP-Native Integration** | Capability should arrive as an MCP server | **DEFERRED** — the available server cannot be loaded within the ceiling |
| **IX. Security by Default** | Least privilege | **FINDING** — the operator's token carries `role: admin`; an Observer-role token is made a requirement on the build path |
| **XI. Full-Stack Artifact Coherence** | All touchpoints updated | **N/A by scope** — nothing is registered, so no catalog entry, install step or `EXTERNAL_INTEGRATIONS` record is due. `reconcile-mcp.py` exits 0 |
| **XIII. Credential Safety** | No secrets in the repo | **PASS** — verified by direct unpiped grep; `.env.example` carries names only |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED then remedied in-flight** — see Complexity Tracking |

## Project Structure

```text
specs/095-juniper-mist/
├── spec.md            # decision, build design, exit conditions
├── VERIFICATION.md    # every measurement, reproducible
├── plan.md            # this file
├── research.md
└── tasks.md

scripts/probe-mist-mcp.py   # re-runs the ceiling check; flags drift >500 tokens from 11,783
.env.example                # MIST_API_HOST, MIST_ORG_ID, MIST_API_TOKEN — names only
docs/COVERAGE-ROADMAP.md    # R5 -> BLOCKED — measured
```

**Structure Decision**: No `mcp-servers/` directory and no registration. Committing a probe script
rather than only prose means the rejection is **re-checkable by anyone** — if Juniper shrinks the
manifest, the script says so instead of the decision silently going stale.

## The build, when unblocked

A NetClaw-authored read-only Mist client following 094 (GET-only transport) and 087 (dispatcher
shape): 4 tools, ≤1,500-token manifest counted not estimated, Observer-role credential, and an
explicit *no telemetry* versus *no problems* distinction in every assurance response.

**Gated** on a populated org, because that distinction is the feature's central failure mode and
cannot be exercised against an empty one.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** — `spec.md` and `VERIFICATION.md` shipped without plan/research/tasks | Nothing justified it; part of the 087–096 drift, caused by sampling recent specs and mistaking the drift for the convention | Remedied here **before merge**, plus a gate so the gap cannot recur undetected |
| **Specifying a build that is not built** | The measurement is only actionable if the alternative is written down; otherwise the next person re-runs the same probe to reach the same conclusion | Deferring silently (leaving R5 `NOT STARTED`) was the status quo that wasted the investigation. Building unverifiable assurance skills was rejected — see the gate below |
| **Gating the build on an external dependency** | The verification org has 0 devices; `sites_sle` there returns `count: 1` with no metrics, so *no telemetry* and *no problems* are the same shape | Shipping three skills whose central failure mode cannot be tested would repeat R3's unverified manager/analyzer planes **by default rather than by decision** |
