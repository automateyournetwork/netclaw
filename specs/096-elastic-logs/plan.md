# Implementation Plan: Elasticsearch log search (R12)

**Branch**: `096-elastic-logs` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/096-elastic-logs/spec.md`

## Summary

Adopt Elastic's MCP server to give NetClaw read-only log search over an operator-supplied
Elasticsearch cluster (8.x/9.x). Five tools at **1,094 tokens** — 0.22× the 5,000-token manifest
ceiling. No NetClaw-authored server code: the deliverable is a registration, an installer component,
a skill, and the documentation surfaces.

The technical crux is not integration but **correctness**: the server flattens Elasticsearch's
capped `hits.total` (`{"value":10000,"relation":"gte"}`) into a bare `Total results: 10000`,
discarding the qualifier that marks the number a floor. The design therefore routes every counting
question through `esql` or `track_total_hits: true`, both verified against a known 10,075-document
ground truth.

## Technical Context

**Language/Version**: None authored. Bash (installer component), JSON (registration), Markdown
(skill + docs) — matching every other adopted-server integration in this repo
**Primary Dependencies**: `docker.elastic.co/mcp/elasticsearch` pinned at
`sha256:d57ea11dcb3451ca332cb6d3bb8c4bb1ea29f15e498937ad6c2eada9f88eb003` (image reports
`elasticsearch_core_mcp_server` 0.4.6, MCP framework `rmcp` 0.2.1, Apache-2.0); Docker; an
Elasticsearch 8.x/9.x cluster the operator already runs
**Storage**: None. NetClaw persists nothing — the cluster holds all data. No cache, no local index
**Testing**: Live verification against Elasticsearch 9.2.0 (`basic` licence) seeded with 25,000
realistic network syslog documents; `scripts/reconcile-mcp.py` for artifact coherence
**Target Platform**: Linux with Docker (primary). Network path uses
`--add-host=host.docker.internal:host-gateway` rather than `--network host`, which is Linux-only,
so a macOS Docker Desktop install works unchanged
**Project Type**: MCP integration — adopt, not build
**Performance Goals**: Manifest ≤ 5,000 tokens (achieved: 1,094). No latency target; query cost is
the cluster's, not NetClaw's
**Constraints**: Read-only; no write verb may be reachable. Upstream is deprecated (security updates
only) so the image MUST be digest-pinned. Counting answers MUST be exact or explicitly bounded
**Scale/Scope**: 1 server, 5 tools, 1 skill, 0 lines of authored server code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| **II. Read-Before-Write** | No mutating capability | **PASS** — all 5 tools read; manifest holds no index/update/delete/reindex verb, so writes are unreachable regardless of credential |
| **V. MCP-Native Integration** | Capability arrives as an MCP server, not bespoke glue | **PASS** — registered as `elasticsearch-mcp` |
| **VI. Multi-Vendor Neutrality** | No lock-in; existing backends unaffected | **PASS** — Splunk, Datadog, GCP Logging skills unchanged; FR-004 defines selection by where data lives |
| **IX. Security by Default** | Least privilege | **PASS** — skill requires an API key scoped `read` + `view_index_metadata`; superuser explicitly discouraged |
| **X. Observability First-Class** | Adds observability reach | **PASS** — this is the point of R12 |
| **XI. Full-Stack Artifact Coherence** | Every touchpoint updated | **PASS** — config, catalog, install step, profile, skill, `.env.example`, TOOLS.md, README/SOUL counts; verified by `reconcile-mcp.py` exit 0 |
| **XII. Documentation-as-Code** | Behaviour documented where it is used | **PASS** — the counting rule appears in skill, catalog description, and install step |
| **XIII. Credential Safety** | No secrets in repo | **PASS** — `.env.example` carries names only; values live in `~/.openclaw/.env` |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED THEN REMEDIATED** — see Complexity Tracking |

### Post-Phase-1 re-check

No new violations. The design adds no authored code, so no new dependency pins (Principle from spec
077) and no startup-surface risk beyond Docker availability, which the install step warns about
explicitly rather than failing silently.

## Project Structure

### Documentation (this feature)

```text
specs/096-elastic-logs/
├── spec.md              # Feature specification (written first, then this plan)
├── plan.md              # This file
├── research.md          # Phase 0 — candidate evaluation, deprecation trade, trap discovery
├── data-model.md        # Phase 1 — the entities this feature reasons about
├── quickstart.md        # Phase 1 — operator setup and first verified query
├── contracts/           # Phase 1 — tool contracts and the counting invariant
│   ├── tools.md
│   └── counting-invariant.md
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

No `src/` tree: this feature authors no server. The touched paths are:

```text
config/openclaw.json                          # elasticsearch-mcp registration (docker, digest-pinned)
scripts/lib/catalog.sh                        # "elastic|Observability & Telemetry|..." + PROFILE_OBSERVABILITY
scripts/lib/install-steps.sh                  # component_install_elastic()
scripts/verify-catalog-coverage.py            # alias: elasticsearch-mcp -> elastic
workspace/skills/elasticsearch-logs/SKILL.md  # the skill, carrying the counting rule
.env.example                                  # ES_URL, ES_API_KEY, ES_USERNAME, ES_PASSWORD, ES_SSL_SKIP_VERIFY
TOOLS.md, README.md, SOUL.md                  # infrastructure reference + counts
```

**Structure Decision**: Adopted-server layout. The repo's only precedent for a Docker-command
server is `github-mcp`, and this registration follows it — `command: "docker"`, `args` carrying
`run -i --rm`, environment passed by name. It diverges in two respects, both deliberate: the image
is pinned by digest (following R13's Zeek/Suricata discipline, because a deprecated upstream must
not shift underneath us), and `--add-host=host.docker.internal:host-gateway` is added because
`ES_URL` resolves inside the container, where a host cluster is not `localhost`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached during this feature** — implementation (registration, catalog, install step, skill) was written before `plan.md` and `tasks.md` existed | Nothing justified it. The author sampled specs 091/092/094, saw `spec.md` alone, and inferred that was the convention — sampling a drift that began at 087 and mistaking it for the standard | The dominant practice is 72 of 86 specs carrying full artifacts. Remedy: artifacts completed retroactively for this spec before merge, the same gap backfilled for 084 and 087–095, and a gate added so the drift cannot recur undetected |
| **Adopting a deprecated upstream** | The supported successor (Elastic Agent Builder MCP endpoint) is Enterprise-tier on self-managed. The free path is this one | Building a NetClaw client was rejected: at 1,094 tokens with the trap mitigable in the skill, authored code would add maintenance for no capability gain. Deferring (the R10 outcome) was rejected because, unlike ntopng, this path *works* on a free licence and is Apache-2.0 — already published and unwithdrawable |
