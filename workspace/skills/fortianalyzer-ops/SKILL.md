---
name: fortianalyzer-ops
description: "FortiAnalyzer log operations — policy-filtered traffic log query within a bounded time window, offset pagination, per-policy activity checks, and logging-device inventory. Use when asking whether traffic actually matched a firewall rule, investigating what hit a policy, or determining whether a rule is genuinely unused."
version: 1.0.0
license: Apache-2.0
tags: [fortinet, fortianalyzer, logs, traffic, siem, firewall, audit, security]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["FORTINET_MCP_CMD", "FORTIANALYZER_HOST", "FORTIANALYZER_API_TOKEN"] } } }
---

# FortiAnalyzer Operations — the analyzer plane

## MCP Server

- **Server**: `fortinet-mcp` (NetClaw-authored, spec 080 / roadmap R3)
- **Command**: `$FORTINET_MCP_CMD`
- **Transport**: stdio · JSON-RPC over `/jsonrpc` (the same dialect FortiManager speaks)
- **Requires**: `FORTIANALYZER_HOST`, `FORTIANALYZER_API_TOKEN` (FortiAnalyzer 7.2.2+ for token auth)
- **Mode**: read-only

## The one rule that matters most here

> ### "No logs matched" is NOT "this rule is unused."

This skill exists to answer "is this rule dead?" — and that question is dangerously
easy to answer wrongly. An empty result can mean:

- nothing matched **in the window you queried** (retention is finite; history is not)
- the device never forwarded logs to this analyzer at all
- logging is disabled on the rule itself

Reporting any of those as "unused" would license someone to delete a live firewall
rule. So an empty result returns the explicit outcome **`no_logs_in_window`**, never
`ok` and never an error, with a message saying what it does and does not prove.

This is the same error class as spec 078's *"no advisories ≠ not vulnerable"* and
spec 079's *"no probes found ≠ outage"*, and it gets the same treatment: a separate,
named outcome that cannot be silently collapsed.

## Where this plane sits

| Question | Plane | Skill |
|---|---|---|
| "Has anything actually matched this rule?" | analyzer | **this skill** |
| "What policy is *intended*?" | manager | `fortimanager-ops` |
| "What is the box *running* right now?" | device | `fortigate-ops` |

The manager knows a rule **exists**. Only the analyzer knows whether anyone ever
**matched** it. A configured rule is not a used rule.

## Tools (4, all read-only)

| Tool | What it answers |
|---|---|
| `faz_query_logs` | Traffic logs matching a filter within a bounded window |
| `faz_fetch_more` | Next page, re-run at an offset |
| `faz_policy_activity` | Did anything match policy N in this window? |
| `faz_list_devices` | Which devices forward logs here — **check this first** |

## Time windows are mandatory and always stated

If you supply no window, the tools apply the **last 24 hours** and say so in
`scope.window_start` / `scope.window_end` and in `notes`. An unbounded log query
against a busy analyzer is slow, expensive, and produces a result nobody can
interpret because they do not know what period it covers.

Every response echoes the window **actually queried**, not the one requested.

## Pagination

`faz_fetch_more` re-runs the search at a new offset. It does **not** reuse
FortiAnalyzer's search task id (`tid`), because those are single-use and expire —
treating one as a durable cursor produces silent truncation, where you believe you
have all the results and you have some of them.

## Workflow: is this firewall rule dead?

1. **`faz_list_devices`** — confirm the device that owns the rule actually forwards
   logs here. If it does not, stop: an empty result would mean nothing.
2. `faz_policy_activity` with the policy id and an explicit, generous window.
3. Read the outcome:
   - `ok` with `sessions_matched > 0` → the rule is live. Do not remove it.
   - **`no_logs_in_window`** → nothing matched *in that window*. Not proof of disuse.
4. Before concluding a rule is unused, verify: log forwarding on, retention covers
   the period, logging enabled on the rule itself.
5. Only then treat it as a removal candidate — and route the actual change through
   `fortimanager-ops`, which enforces the two write gates.

## Workflow: what hit this policy?

1. `faz_query_logs` with `filter_expr` (e.g. `policyid=12`) and a bounded window.
2. Page with `faz_fetch_more` using the returned `next_offset` while `has_more`.
3. Correlate sources and destinations against `fmg_resolve_object` to check whether
   the traffic matches what the rule *intended* to permit.

## Every response carries its plane and scope

```jsonc
{ "plane": "analyzer",
  "scope": {"adom": "root", "window_start": "...", "window_end": "..."},
  "outcome": "no_logs_in_window", "message": "... This is NOT evidence the rule is unused." }
```

The window is part of the scope, not an optional detail. A log result without its
window is uninterpretable, so a response that cannot state one is an error.

## Integration with other skills

| Skill | How they compose |
|---|---|
| `fortimanager-ops` | Find the rule (intent), then come here for whether it was used |
| `fortigate-ops` | Device state; use together to separate "not configured" from "not used" |
| `fwrule-analyzer` | Shadowed rules found there + zero activity here = strong removal case |
| `servicenow-change-workflow` | Rule removal is a production change — CR required |
| `gait-session-tracking` | Every query here is GAIT-audited automatically |

## Important rules

- **Never report an empty window as "unused".**
- **Always state the window** you queried, including the default.
- **Check `faz_list_devices` before trusting silence.**
- **Read-only** — findings here justify a change; they never make one.
