# Phase 1 Data Model — Elasticsearch log search (R12)

**Date**: 2026-08-05 | **Plan**: [plan.md](plan.md)

NetClaw persists **nothing** for this feature — no cache, no local index, no registry. The entities
below are what the integration *reasons about*; all of them live in the operator's cluster or in the
MCP response envelope. They are modelled here because the skill's correctness rules depend on
distinguishing them.

---

## Entity: Index

The unit of storage a query targets.

| Field | Source | Notes |
|---|---|---|
| `index` | `list_indices` | name, e.g. `netclaw-syslog` |
| `status` | `list_indices` | `open` / `close` — a closed index answers nothing |
| `docs.count` | `list_indices` | **ground truth for "is there data here at all"** |

**Rule**: a zero `docs.count` means the index is empty. A non-zero count with zero query hits means
*the query* found nothing. These are different answers and must not be conflated (FR-005).

---

## Entity: Field mapping

| Field | Source | Notes |
|---|---|---|
| field name | `get_mappings` | |
| type | `get_mappings` | `text`, `keyword`, `date`, `long`, … |

**Rule**: `text` fields are analysed. A `term` query or `terms` aggregation against one will not
behave as a user expects — aggregating on a bare `text` field is rejected by Elasticsearch outright
(HTTP 400, *"Fielddata is disabled"*). The `.keyword` sibling is the exact-match/grouping form.

**Consequence**: mappings are read **before** composing a query, not after one returns nothing.
Guessing field names is the most common cause of a false empty result.

---

## Entity: Result total — the one that carries the defect

This is the entity the whole spec turns on.

| Representation | Shape | Trustworthy? |
|---|---|---|
| Elasticsearch native | `{"value": 10000, "relation": "gte"}` | yes — `relation` marks it a floor |
| Elasticsearch native | `{"value": 10075, "relation": "eq"}` | yes — exact |
| **MCP server rendering** | `Total results: 10000` | **NO — `relation` is discarded** |
| MCP + `track_total_hits: true` | `Total results: 10075` | yes |
| `esql` `STATS COUNT(*)` | `10075` | yes |

**State transition that matters**: a total crossing 10,000 silently changes meaning from *exact* to
*at least*, while its rendered form does not change at all.

**Invariant** (see `contracts/counting-invariant.md`): a total may only be reported to a human when
it came from `esql`, or from a `search` carrying `track_total_hits: true`. Any other total is
unbounded-wrong and must not be stated as a number.

---

## Entity: Document (log event)

Opaque to this integration — NetClaw imposes no schema. Field names come from `get_mappings`, never
from assumption. Common netops shapes (`@timestamp`, `device`, `severity`, `message`) are
conventions of the operator's data, not requirements of this feature.

---

## Entity: Backend selection

Not a stored entity; a decision the skill must make deterministically.

| Backend | Owns |
|---|---|
| `elasticsearch-logs` (this) | logs indexed in Elasticsearch / ELK |
| `splunk-search` | logs in Splunk |
| `datadog-logs` | logs in Datadog |
| `gcp-cloud-logging` | Google Cloud audit/platform logs |
| `prometheus-monitoring`, `grafana-observability` | time-series metrics, not logs |
| `duckdb-analysis` | exported files on disk, not a live store |

**Rule**: selection is by *where the data lives*, never by question shape. If unknown, ask. Fanning
out across backends produces empty results from the wrong stores, which are indistinguishable from
an absence of events (FR-004).
