# Spec 096 — Elasticsearch log search (R12)

**Status**: implemented
**Branch**: `096-elastic-logs`
**Date**: 2026-08-05
**Roadmap**: [R12](../../docs/COVERAGE-ROADMAP.md) — APM + log platforms, **scoped to Elastic only**

## Summary

Adopt Elastic's MCP server (`docker.elastic.co/mcp/elasticsearch`, Apache-2.0, digest-pinned) to
give NetClaw read-only log search over an Elasticsearch cluster the operator already runs.

**5 tools, 1,094 tokens — 0.22× the 5,000-token ceiling.** Ten times cheaper than the Mist server
rejected in spec 095 the same day.

R12 named three targets (Dynatrace, New Relic, Elastic). This takes **Elastic only**, following the
roadmap's own pattern: "Zabbix only" for R11, "DuckDB only" for R17. The two APM vendors are SaaS
with no self-hostable verification path — the same access blocker that gated R5 — while Elastic runs
locally on a free Basic licence and was verified end to end against 25,000 indexed documents.

## The finding, and why it is the whole spec

> **A bare `search` total is capped at 10,000 and reads as if it were exact.**

Elasticsearch stops counting at 10,000 and marks the total `relation: "gte"` — *at least*. This
server **discards that qualifier** and emits the bare string `Total results: 10000`. Nothing in the
response indicates the number is a floor.

Measured against an index holding **10,075** matching documents:

| How the question is asked | Answer | Correct? |
|---|---|---|
| ground truth (`_count` API) | 10,075 | — |
| `search`, no guard | `Total results: 10000, showing 10.` | **wrong by 75** |
| `search` + `"track_total_hits": true` | `Total results: 10075` | correct |
| `esql` `STATS COUNT(*)` | `10075` | correct |

This is **worse than the raw API it wraps.** Elasticsearch itself returns
`{"value":10000,"relation":"gte"}`, so a careful client can see the number is a floor. The server
flattens it to a bare integer, making a capped count textually indistinguishable from an exact one.

The magnitude is unbounded: on a million-document index a bare search still reports 10,000 — off by
two orders of magnitude, with no signal. And the same question asked through `esql` is correct, so
**tool choice silently determines whether the number is true.**

Same class as R13's Zeek discarding invalid-checksum packets and R15's BMC timeout: a value that is
not what it appears to be, where the wrong reading is the natural one.

### How it is blocked

Unlike spec 095's Mist trap, this one has a **verified structural fix**, so the skill does not merely
warn:

- Every counting, aggregating, ranking or "how many" question routes through `esql`, **or**
- `search` carries `"track_total_hits": true` in the `query_body`.
- Unguarded `search` is for **retrieving example documents only, never for counting.**

Both remedies were confirmed to return 10,075 against the same data.

## Adopted, not built — and the deprecation trade

The upstream is **deprecated**, verbatim: *"This MCP server is deprecated and will only receive
critical security updates going forward."* It is superseded by Elastic Agent Builder's MCP endpoint.

It was adopted anyway, deliberately:

- **The supported successor is paywalled.** Agent Builder appears only under the **Enterprise** tier
  on Elastic's self-managed pricing page — not Basic, not Platinum. "Just use the supported one" is
  not a free option, structurally the same gate that deferred R10 (ntopng's Enterprise-only
  ClickHouse history).
- **The free path works.** Apache-2.0, already published, five tools, verified against Elasticsearch
  9.2.0 on an active `basic` licence. Elastic cannot withdraw a published Apache-2.0 release.
- **The image is digest-pinned** (`sha256:d57ea11d…eb003`), so a security-only update cannot change
  answers underneath the operator — the same discipline R13 applied to Zeek and Suricata.

Building a client instead was rejected: at 1,094 tokens with the trap mitigable in the skill, a
NetClaw-authored server would carry the maintenance for no capability gain. That is the opposite of
095's Catalyst-Center-shaped conclusion, and the manifest cost is the reason.

## Read-only

All five tools read (`list_indices`, `get_mappings`, `search`, `esql`, `get_shards`). The manifest
contains no index, update, delete, or reindex verb, so **no write is reachable regardless of
credential** — a property of the tool surface, not of the token. The skill nonetheless requires an
API key scoped to `read` + `view_index_metadata`; nothing here needs a superuser.

## Requirements

- **FR-001** — Registered as `elasticsearch-mcp`, `command: docker`, digest-pinned, repo-relative
  (no host path). Matches the `github-mcp` precedent, the only other Docker-command server.
- **FR-002** — `ES_URL` resolves **inside the container**: a cluster on the host is
  `http://host.docker.internal:9200`, not `localhost`. The registration passes
  `--add-host=host.docker.internal:host-gateway` rather than `--network host`, which is Linux-only.
- **FR-003** — The counting rule is stated in the skill, the catalog description, and the install
  step — every surface an operator might read before their first wrong number.
- **FR-004** — Backend boundaries are explicit: this skill owns Elasticsearch; Splunk, Datadog, GCP
  Logging, Prometheus/Grafana and DuckDB each own theirs. An empty result from the wrong store is
  indistinguishable from an absence of events, so the skill asks rather than fanning out.
- **FR-005** — Emptiness is reported as "no matching events in `<index>` for `<range>`", never as
  "no errors occurred".

## Verification

Against Elasticsearch **9.2.0**, licence `basic`/`active`, 25,000 realistic network syslog documents
(BGP/OSPF/LINEPROTO/SEC events across 12 devices).

| Check | Result |
|---|---|
| Manifest cost | **1,094 tokens** (1,089 tools + 5 instructions) — **0.22× ceiling** |
| Server identity | `rmcp` 0.2.1, image reports `elasticsearch_core_mcp_server` **0.4.6** |
| Protocol | MCP `2025-03-26` |
| Licence tier | `type: basic, status: active` — no Enterprise features in play |
| `list_indices` | `netclaw-syslog`, 25,000 docs — matches ground truth |
| `esql` `COUNT(*)` | 25,000 total / 10,075 filtered — both correct |
| `search` unguarded | `Total results: 10000` — **the trap, reproduced** |
| `search` + `track_total_hits` | 10,075 — **mitigation confirmed** |
| Valid aggregation | returned correctly, buckets match the raw `_search` response exactly |
| Invalid aggregation | proper JSON-RPC error — **not** silently swallowed |
| Wrong argument names | loud deserialization error naming the missing field |
| Portable network path | `host.docker.internal` reaches the host cluster; 25,000 docs returned |
| `reconcile-mcp.py` | exit 0 |

Two behaviours were investigated and **cleared** rather than recorded as defects: aggregations are
not dropped, and errors are not swallowed. Both initially looked like findings and did not survive
checking — noted here so they are not re-investigated.

## Out of scope

- **Dynatrace and New Relic** — SaaS-only, no self-hostable verification path. R12 stays open for
  them; this spec does not claim them.
- **Agent Builder MCP endpoint** — Enterprise-tier; revisit only if an Enterprise licence appears.
- **Writing to Elasticsearch** — no ingest, no index management, no ILM. Read-only is the point.
- **Standing up a cluster** — NetClaw installs no Elasticsearch. The operator brings one.
- **Replacing existing log backends** — Splunk, Datadog and GCP Logging skills are unchanged.

## Success criteria

- **SC-001** — Manifest measured, not estimated, and inside the ceiling. ✅ 1,094 / 5,000
- **SC-002** — At least one silent wrong answer reproduced live against real data. ✅ 10,000 vs 10,075
- **SC-003** — That trap has a verified mitigation the skill mandates, not merely warns about. ✅
- **SC-004** — The deprecation and its Enterprise-gated successor are recorded, so adopting a
  security-only upstream is a visible decision. ✅
- **SC-005** — No capability claimed that was not exercised: all five tools called against real data. ✅
- **SC-006** — Backend selection is deterministic rather than guessed. ✅ FR-004
- **SC-007** — `reconcile-mcp.py` exits 0. ✅
