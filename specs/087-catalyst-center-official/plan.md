# Implementation Plan: Catalyst Center — official Cisco MCP server, curated

**Branch**: `087-catalyst-center-official` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)
**Roadmap**: operator-requested, Tier 1 adjacent

> ## ⚠ This is a reconstruction
>
> Written **2026-08-05**, after the feature merged, from `spec.md`, `VERIFICATION.md`, the merged
> code and the git history. It is **not** the artifact that guided the work — no `plan.md` existed
> while 087 was built, which breached Principle XVI.
>
> It is reconstructed rather than omitted so the artifact set is complete and the reasoning is
> recoverable. Where the delivered design diverged from the spec, this plan records **what was
> actually built**, not what was originally proposed.

## Summary

Replace NetClaw's community Catalyst Center coverage with Cisco's first-party server. The existing
integration was unregistered, untracked, and carried an unbounded `fastmcp>=0.1.0` pin — not a
baseline worth preserving.

The engineering problem is **not adoption but curation**: the upstream default exposes **515 tools /
64,420 tokens**, 12.9× the manifest ceiling and the largest surface ever evaluated in this project.

**Delivered**: 8 grouped dispatchers + `catc_find` + `catc_describe_operation` = **10 tools / 1,821
tokens**, reaching **all 514 read-only operations**.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: Cisco `cisco-en-programmability/catc-mcp-oss` (Apache-2.0,
`release/2.3.7.11`) — **its catalogue, not its runtime** (see Complexity Tracking)
**Storage**: None — stateless proxy to the Catalyst Center appliance
**Testing**: Live, against two Cisco DevNet sandbox appliances with deliberately different contents
**Target Platform**: Linux
**Project Type**: MCP integration — adopt the catalogue, author a thin dispatcher
**Performance Goals**: Manifest ≤ 5,000 tokens (achieved 1,821)
**Constraints**: Read-only — all 514 GET operations, the single POST excluded
**Scale/Scope**: 514 reachable operations behind 10 tools

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **II. Read-Before-Write** | No mutation | **PASS** — 514 GETs; the one POST (`getApplicationPolicy`, misleadingly named) is excluded |
| **V. MCP-Native** | Capability as MCP server | **PASS** |
| **VI. Multi-Vendor Neutrality** | No lock-in | **PASS** — replaces like with like |
| **IX. Security by Default** | Least privilege, no ambient targets | **PASS** — explicit appliance, credentials from env |
| **X. Observability** | Answers must be attributable | **PASS** — every response stamped with which appliance answered and when |
| **XI. Artifact Coherence** | All touchpoints | **PASS** — spec §"Artifact coherence (Principle XI)" |
| **XV. Backwards Compatibility** | Replacement must not orphan callers | **PASS** — community server retired in the same change |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED** — see Complexity Tracking |

## Project Structure

```text
specs/087-catalyst-center-official/
├── spec.md              # written first
├── VERIFICATION.md      # live evidence, incl. the design change
├── plan.md              # this reconstruction
├── research.md          # reconstruction
└── tasks.md             # reconstruction

mcp-servers/catc-mcp/server.py   # the authored dispatcher layer
```

**Structure Decision**: NetClaw authors a dispatcher server over Cisco's **operation catalogue**.
The upstream *runtime* is not used — it carries an unbounded `fastmcp>=2.0.0` pin that collides with
five NetClaw servers pinning `<3`, an HTTP transport on port 7001, and a container requirement.
Consuming the catalogue takes the value (Cisco's maintained operation list) without the hazards.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** — implementation preceded any plan or task artifact | Nothing justified it; part of the 087–096 drift | Remedied by this reconstruction plus a gate so the gap cannot recur undetected |
| **Authoring a dispatcher instead of adopting the server as-is** | 515 tools is 12.9× the ceiling; no filtering mechanism reaches an acceptable manifest while preserving coverage | Curating ~15 individual tools (the spec's original design) was **built and abandoned**: it fit the ceiling at ~4,200 tokens but reached only **~3% of the API**. Dispatchers reach 100% at 1,821 |
| **Consuming the catalogue, not the runtime** | Upstream runtime's unbounded `fastmcp>=2.0.0` would break five servers pinning `<3` | Vendoring the runtime unmodified (the 083 posture) was impossible without inheriting the dependency conflict |

## Design change during implementation — recorded, not hidden

The spec proposed ~15 hand-curated tools. Measurement during the build showed that reached ~3% of
the API. The delivered design — 8 dispatchers plus discovery (`catc_find`) and schema
(`catc_describe_operation`) — reaches **all 514** read operations for **1,821 tokens**.

`VERIFICATION.md` opens by stating the spec records the superseded approach. That is the correct
disposition: the spec is a record of intent at the time, the verification is the record of fact.
