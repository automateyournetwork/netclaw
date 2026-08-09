# Phase 0 Research — Elasticsearch log search (R12)

**Date**: 2026-08-05 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

All findings below were measured against a live Elasticsearch 9.2.0 on a free `basic` licence,
seeded with 25,000 realistic network syslog documents. Nothing is quoted from vendor marketing.

---

## R1 — Scope: which of R12's three targets is buildable

**Decision**: **Elastic only.** Dynatrace and New Relic are out of scope for this spec.

**Rationale**: R12 names Dynatrace, New Relic and Elastic. Both APM vendors are SaaS-only with no
self-hostable verification path — the same access blocker that gated R5 (Juniper Mist) hours
earlier, where an empty tenant made the central failure mode untestable. Elastic runs locally on a
free licence, so its traps are reproducible.

**Alternatives considered**: Doing all three (rejected — two would ship unverified, repeating the
FortiManager/FortiAnalyzer situation from R3); deferring R12 entirely (rejected — Elastic is
verifiable today).

**Precedent**: the roadmap's own pattern of narrowing a multi-vendor item to the verifiable one —
"Zabbix only" for R11, "DuckDB only" for R17.

---

## R2 — Does NetClaw already have this capability?

**Decision**: Partially, and the gap is real but narrower than first stated.

**Finding**: NetClaw already registers `splunk-mcp` (3 skills), `datadog-mcp` (`datadog-logs`),
`gcp-logging-mcp`, `grafana-mcp` and `prometheus-mcp`. An initial claim that NetClaw had "no log
search at all" was **wrong** and is corrected here.

What is true: **no Elasticsearch backend exists**, and Elasticsearch is the dominant self-hosted
netops log store. Additionally, in this environment `SPLUNK_HOST` and `SPLUNK_TOKEN` are unset and
the endpoint is unreachable (`curl` exit 000), so the registered Splunk skills currently point at
nothing.

**Consequence for design**: the value is a *backend*, not a *capability*, so FR-004 (explicit
backend boundaries) matters more than it would for a greenfield integration. An agent that fans out
across backends hoping one answers will read an empty result from the wrong store as an absence of
events.

---

## R3 — Which Elasticsearch MCP server

**Decision**: `docker.elastic.co/mcp/elasticsearch` (Elastic's own), digest-pinned.

**Rationale**: Apache-2.0, vendor-authored, 5 tools, 1,094 tokens measured.

**Alternatives considered**:

| Candidate | Verdict |
|---|---|
| `elastic/mcp-server-elasticsearch` (this one) | **chosen** — official, Apache-2.0, small manifest |
| `@elastic/mcp-server-elasticsearch` on npm | **rejected** — npm-deprecated at 0.3.1, redirects to the container for 0.4.0+ |
| `zx8086/mcp-server-elasticsearch` (community, 104+ operations) | **rejected** — 104 operations against a 5,000-token ceiling is the failure mode that killed Catalyst Center's 515-tool bundle (087) and Mist's 7 dispatchers (095) |
| `cr7258/elasticsearch-mcp-server` (ES + OpenSearch) | **rejected** — community, and OpenSearch breadth is not needed |
| Build a NetClaw client | **rejected** — see R5 |

---

## R4 — The deprecation, and whether it disqualifies adoption

**Decision**: Adopt anyway, digest-pinned, with the trade recorded.

**Finding**: the server emits its own deprecation on every start, verbatim:

> `DEPRECATION NOTICE: This MCP server is deprecated and will only receive critical security updates
> going forward. It has been superseded by Elastic Agent Builder, which includes its own MCP server`

**The decisive question was whether the successor is reachable.** It is not, on a free licence:
Elastic's self-managed pricing page lists *"Elastic Agent Builder for RAG and search development
with third-party LLM providers"* **only under the Enterprise tier**. Basic and Platinum do not carry
it.

That is structurally identical to R10 (ntopng), deferred because ClickHouse flow history is
Enterprise M+ only. **The difference, and the reason the outcomes differ**: ntopng's free edition
could not do the job at all, whereas this server *works* on Basic, is Apache-2.0, and is already
published — Elastic cannot withdraw it.

**Mitigation**: pin by digest (`sha256:d57ea11d…eb003`). A security-only upstream must not be able
to change answers underneath the operator. Same discipline R13 applied to Zeek and Suricata.

---

## R5 — Adopt versus build

**Decision**: Adopt.

**Rationale**: 1,094 tokens is 0.22× the ceiling, and the one correctness defect is fully mitigable
from the skill. Authored code would carry maintenance for no capability gain.

**Contrast with 095 (Mist), decided the same day**: there, adoption was rejected and a build
specified — because the manifest was 11,783 tokens (2.36× over) with no tool-filtering mechanism.
**The manifest cost is what separates the two outcomes**, not a preference for adopting or building.

---

## R6 — Manifest cost (the ceiling gate)

**Decision**: Passes comfortably.

Measured with the Anthropic `count_tokens` endpoint as a delta over an 8-token baseline:

| Component | Tokens |
|---|---|
| `search` | 683 |
| `get_mappings` | 601 |
| `get_shards` | 597 |
| `esql` | 596 |
| `list_indices` | 596 |
| **Tool manifest (combined)** | **1,089** |
| `instructions` (32 chars) | 5 |
| **Total vs 5,000 ceiling** | **1,094 — 0.22×** |

Per-tool figures each include ~570 tokens of fixed framing, which is why they do not sum to the
combined total. Counting `instructions` is deliberate (the R10 precedent); here it is negligible.

---

## R7 — The correctness trap

**Decision**: Real, reproducible, and mitigable. This is the finding the spec is built around.

**Discovery**: seeded 25,000 documents of which **10,075** match `severity: error` — deliberately
just above Elasticsearch's 10,000-document counting cap.

| Path | Result |
|---|---|
| ground truth `_count` | 10,075 |
| `search`, unguarded | `Total results: 10000, showing 10.` |
| `search` + `track_total_hits: true` | `Total results: 10075` |
| `esql` `STATS COUNT(*)` | `10075` |

**Mechanism**: Elasticsearch returns `{"value":10000,"relation":"gte"}` — the `relation` field marks
the value a floor. The server renders only the integer, so **a capped count is textually identical
to an exact one**, and the model has no way to detect it. This makes the wrapper *less* safe than
the API it wraps.

**Severity**: unbounded. A million-document index still reports 10,000.

**Mitigation (both verified)**: route counting through `esql`, or set `track_total_hits: true`.

**Precedent class**: R13's Zeek silently discarding invalid-checksum packets; R15's BMC timeout
establishing nothing about the host. A value that is not what it appears to be, where the wrong
reading is the natural one.

---

## R8 — Two suspected defects that did not survive checking

Recorded so they are not re-investigated.

- **"Aggregations are dropped"** — **false**. A valid aggregation returns
  `Aggregations results:` with buckets matching the raw `_search` response exactly. The empty output
  that prompted this came from an *invalid* aggregation (a `terms` agg on a `text` field, which
  Elasticsearch itself rejects with HTTP 400).
- **"Errors are silently swallowed"** — **false**. The invalid aggregation returns a proper JSON-RPC
  error. The apparent `{}` was a probe printing only the `result` field, which is empty when an
  `error` field is present instead.

Both were stated as findings before verification and corrected on checking. Argument-name errors
(`query_body` vs `queryBody`) also fail **loudly** with a deserialization error naming the missing
field — notably better than the Mist server's silent parameter drop (095, R7).

---

## R9 — Container network path

**Decision**: `--add-host=host.docker.internal:host-gateway`, not `--network host`.

**Rationale**: `ES_URL` is resolved inside the container, so a cluster on the host is not
`localhost` — the server even logs `Container mode: could not find a replacement for 'localhost'`.
Both paths were tested and reach the host cluster, but `--network host` is Linux-only and would
break macOS Docker Desktop installs.

**Verified**: `list_indices` through the gateway path returned `netclaw-syslog`, 25,000 docs.

**Alternatives considered**: `--network host` (rejected — not portable); requiring a remote cluster
only (rejected — the local case is the common lab setup).

---

## R10 — Test-harness artifact worth recording

A heredoc-fed stdio session appears to hang after `initialize`. It is not a server defect: closing
stdin makes the server log `input stream terminated` and exit before answering later messages. A
real MCP client holds the pipe open. Any future probe of a stdio server must keep stdin open —
a persistent `subprocess.Popen` pipe, not a heredoc.
