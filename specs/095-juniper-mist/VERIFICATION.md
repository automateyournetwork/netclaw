# Spec 095 — Verification

**Date**: 2026-08-05
**Endpoint**: `https://mcp.ai.juniper.net/mcp/mist` — `initialize` reports `mistapi`, version empty string
**Protocol**: MCP `2025-06-18`, streamable HTTP, SSE responses
**Credential**: operator's own Mist token, org **NetClaw** `867ed0fe-…dd4ea`, `ac5` regional cloud.
Stored only in `~/.openclaw/.env` — **the token appears in no file in this repository**, verified with a
direct (unpiped) grep across the tree.

Everything below was measured live against Juniper's endpoint. Nothing is quoted from documentation
except the two header names, which documentation supplied and measurement then confirmed.

---

## 1. Reaching the server at all — two undocumented-by-default requirements

| Attempt | Result |
|---|---|
| `Authorization: Token <t>` | `no supported Authorization scheme found in request` |
| `Authorization: Bearer <t>`, no region header | `authentication failed: Mist API rejected credentials (HTTP 401)` |
| `Authorization: Bearer <t>` + `X-Mist-Base-URL: https://api.ac5.mist.com` | **success** |

Two failures that look identical from the client and are not:

- The Mist REST API accepts `Authorization: Token`. **The MCP server accepts only `Bearer`.** A
  credential that works against the REST API fails at the MCP with a scheme error.
- Without `X-Mist-Base-URL` the server defaults to `api.mist.com`. A valid `ac5` token is rejected
  there with a **401 that reads as a bad credential, not as a wrong region**.

Both `api.mist.com` and `api.ac5.mist.com` return `401` to an unauthenticated `GET /api/v1/self`, so
**a 401 alone cannot distinguish a bad token from a wrong region.** The regional cloud must be
established from the operator's `manage.<region>.mist.com` URL, not inferred from a failure.

`X-Mist-Org-ID` is accepted but is **not** a substitute for the per-call `org_id` argument — see §4.

---

## 2. Manifest cost — the ceiling check, and the finding that decides this spec

Measured with the Anthropic `count_tokens` endpoint against `claude-opus-4-5`, taking the delta
between an 8-token baseline request and the same request carrying the tool definitions.

| Tool | Tokens |
|---|---|
| `search_mist_data` | 4,229 |
| `get_mist_insights` | 2,815 |
| `get_mist_stats` | 2,542 |
| `get_mist_config` | 1,879 |
| `find_mist_entity` | 1,776 |
| `get_mist_constants` | 812 |
| `get_mist_self` | 669 |
| **Tool manifest total** | **11,746** |
| `instructions` (170 chars) | 37 |
| **Total against the 5,000 ceiling** | **11,783 — 2.36× over** |

`instructions` is counted deliberately, per the R10 precedent where a 5,338-token `instructions`
payload blew the ceiling once counted. Here it is negligible; **the schemas are the cost.**

Seven tools costing 11,746 tokens is **~1,678 tokens per tool** — versus ~283/tool for Catalyst
Center's 515-tool catalogue (087). This is the opposite failure mode from every prior rejection:
not too many tools, but seven dispatchers with very large descriptions and schemas.

### The chars/4 convention under-reports — by 17% here

The roadmap has estimated manifests at chars÷4 throughout (089's 818 chars → ~204 tokens is exactly
that). Applied here it gives **10,052** against a measured **11,783**.

Dense JSON schemas tokenize worse than prose. The convention is safe for the low-cost adoptions it
has been used on, but **any future measurement landing near the ceiling must be counted, not
estimated** — at this error rate an estimate of 4,300 could be a real 5,000.

---

## 3. Why a curated subset is not available

`config/openclaw.json` server entries use only `command`, `args`, `env`, `headers`, `url` across all
101 registered servers. There is **no tool-filtering key** — no allowlist, no exclude list. Registering
this server costs its whole manifest.

The three cheapest tools (`get_mist_self` + `get_mist_constants` + `find_mist_entity` = 3,257) would
fit the ceiling, but there is no supported way to load only those, and that subset excludes every
assurance capability R5 exists to obtain.

---

## 4. Two defects in the shipped schemas

**4.1 `get_mist_insights` requires a parameter its schema does not declare.**

The tool's `inputSchema` declares `required: ["insight_type"]` and these properties:
`duration, end_time, insight_type, limit, next_cursor, org_id, page, params, site_id, start_time`.

There is **no `query_type` property**. Yet:

```
get_mist_insights({"insight_type":"sle","query_type":"sites_sle","scope":"org","org_id":"<org>"})
  → Tool error: param "query_type" is required for insight_type "sle"
```

The argument was supplied at the top level, **silently dropped** (not rejected as unknown), and then
reported missing. The working form has to be inferred — it belongs inside the undocumented generic
`params` object:

```
get_mist_insights({"insight_type":"sle","org_id":"<org>","params":{"query_type":"sites_sle"}})
  → {"count":1,"data":[{"site_id":"3eb28ffc-…"}],"insight_type":"sle","total":1}
```

A model constructing a call from the schema alone cannot reach the working form. It must read the
prose in the error message and guess the nesting. This affects the single most valuable tool for R5's
stated purpose — SLE and Marvis.

**4.2 `X-Mist-Org-ID` does not populate the per-call `org_id`.**

With the header set, `search_mist_data({"search_type":"wireless_clients","scope":"org"})` fails with
`required: missing properties: ["org_id"]`. The header scopes the server; it does not fill arguments.
Every org-scoped call must repeat `org_id` explicitly.

Not every parameter error is this soft: `stats_type` and `search_type` are strict enums and reject
invalid values loudly, naming the full valid set. The inconsistency is the hazard — some wrong
arguments fail loudly, one important one fails misleadingly.

---

## 5. Read-only posture

All seven tools are read-shaped (`get_*`, `find_*`, `search_*`). The manifest contains no create,
update, delete, reboot, or claim verb, so **no mutating operation is reachable through this server**
regardless of credential.

That is a property of the tool surface, not of the credential — and it matters here, because:

**The operator's token carries `role: admin`.** `GET /api/v1/self` returns:

```json
{"privileges":[{"scope":"org","role":"admin","org_id":"867ed0fe-…","name":"NetClaw"}],
 "tags":["mist-customer"]}
```

An admin token has full write reach over the org through the REST API. Nothing in this spec's design
uses that reach, but the credential holds it. **An Observer-role org token is the correct credential**
and is a requirement on the build path (§7), not a preference.

---

## 6. What the empty org can and cannot establish

Org NetClaw contains: **1 site** (`Primary Site`, `America/Los_Angeles`), **0 devices**, **0 inventory**,
**0 alarms**, **0 licences** (`trial_enabled: true`).

Verified end to end:

| Call | Result |
|---|---|
| `get_mist_self` | full identity, privileges, org name — matches the REST API exactly |
| `get_mist_constants{device_models}` | **284 device models** — a populated, non-trivial payload |
| `get_mist_stats{org_devices}` | `{"count":0,"data":[]}` |
| `search_mist_data{wireless_clients\|alarms\|devices}` | `{"count":0,"results":[]}` |
| `get_mist_insights{marvis_actions}` | `{"count":0,"data":[]}` |
| `get_mist_insights{sle, params.query_type=sites_sle}` | `{"count":1,"data":[{"site_id":"3eb28ffc-…"}]}` |

**Not established**: whether any assurance payload parses correctly. Every count above is zero because
the org is empty, not because a code path was exercised. `get_mist_constants` is the one tool proven
against real data, and it is a static catalogue — it touches no org state.

### The empty-org trap, stated precisely

The last row is the one to be careful with. `sites_sle` returns **`count: 1`** — a non-zero count, a
real site ID, and **no SLE metrics whatsoever**. Asked "how is wireless health at this site?", a model
receiving `count: 1` with no failing metrics can report the site as healthy.

The site is not healthy. It has no APs, no clients, and no telemetry. **A site with no data and a site
with no problems are the same shape in this response**, and nothing in the payload distinguishes them.

This is the same class as R15's box-vs-network distinction and R13's zero-signature Suricata: an
absence being reported as a negative finding. Any skill built on this tool must establish that
telemetry exists before characterising health — which, in an org with zero devices, it cannot.

---

## 7. Conclusion

Adoption is **rejected on the ceiling**: 11,783 tokens, 2.36× over, no filtering mechanism available.

Verification of the assurance data paths is **not possible in this org**: the one capability that
returned real data is a static device-model catalogue.

The build path and its exit conditions are specified in `spec.md`. Both blockers are external —
neither is resolved by more implementation work here.

## Reproducing

```bash
set -a; source ~/.openclaw/.env; set +a
python3 scripts/probe-mist-mcp.py            # initialize + tools/list + manifest sizing
python3 scripts/probe-mist-mcp.py --count    # exact token count (needs ANTHROPIC_API_KEY)
```
