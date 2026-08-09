---
name: zabbix-problem-review
description: "Review current and historical problems from Zabbix — severity, which host, when it started, how long it has been active, and whether anyone has acknowledged it. Use when someone asks what is broken right now, how long something has been broken, or what happened during a window that has already passed."
version: 1.0.0
license: Apache-2.0
tags: [zabbix, nms, monitoring, alerts, problems, incidents, triage, observability]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["ZABBIX_URL", "ZABBIX_TOKEN"] } } }
---

# Zabbix Problem Review

## Server

`zabbix-mcp` — vendored third-party, read-only, three tools. See
[zabbix-metrics-history](../zabbix-metrics-history/SKILL.md) for the shared cautions.

## Current problems vs history — use the right one

| Question | Method | Note |
|---|---|---|
| What is wrong **now**? | **`problem.get`** | Reads a dedicated problem table. This is the right one |
| What happened **then**? | `event.get` | Historical, heavier, needs a time window |
| What rule fired it? | `trigger.get` | The definition behind a problem |

```jsonc
zabbix_api("problem.get", {
  "output": "extend", "selectAcknowledges": "extend", "selectTags": "extend",
  "recent": false, "sortfield": ["eventid"], "sortorder": "DESC"
})
```

Every problem you report carries: **severity · host · when it started · how long it has been active ·
acknowledgement state**. "How long" is the question NetClaw could not answer at all before this integration
existed — do not drop it.

## The distinction that matters most here

> ### "No active problems" and "the NMS could not be reached" are not the same answer.

An empty problem list is a **legitimate, positive finding** — the monitoring system looked and found
nothing wrong. An unreachable NMS is a **failure to look**.

They are both an empty result over the wire, and reporting the second as the first is the most misleading
thing this skill can do: it tells an engineer everything is fine at exactly the moment monitoring is blind.

Three outcomes, three different sentences:

| | Say |
|---|---|
| NMS reachable, nothing wrong | *"Zabbix reports no active problems as of \<time>."* |
| NMS unreachable | *"Zabbix could not be reached — this is not a statement about the network."* |
| Credentials rejected | *"Zabbix rejected the credentials — the monitoring state is unknown."* |

## Acknowledgement is a workflow fact, never a resolution

An acknowledged problem is **still happening**. Someone has said "I've seen this", which is a fact about the
team, not about the network.

Report it as *"active, acknowledged by \<who> at \<when>"*. Never let acknowledgement soften the description
of the underlying condition, and never let a filtered-out acknowledged problem disappear from a count.

## Filtering

Filter **before** you answer — by severity, host or group — rather than returning everything and asking the
reader to ignore rows. Use `severities`, `hostids` or `groupids` on the call.

Severities: 0 not classified · 1 information · 2 warning · 3 average · 4 high · 5 disaster.

When you filter, **say what you filtered out**, so "two problems" is never mistaken for "two problems exist".

## Resolved problems

`event.get` with `value: 0` gives resolutions. Report **both** onset and resolution times — a problem that
lasted four minutes and one that lasted four hours are different incidents, and the duration is usually the
point of the question.

## Boundaries

| Want to… | Use |
|---|---|
| Metric values over time | `zabbix-metrics-history` |
| Availability and inventory | `zabbix-availability` |
| Unsolicited traps | `snmptrap-mcp` — push, not poll |
| Flows | `ipfix-mcp` |
| Instrumented metrics / dashboards | `prometheus`, `grafana` |
| SaaS monitoring | `auvik`, `thousandeyes`, `datadog` |
| Current device state | `pyats`, `multivendor-cli`, `fortinet` — this is the poller's view over time |
| Acknowledge, close or suppress anything | **nothing here.** This integration is strictly read-only |

## Rules

1. **Never report an unreachable NMS as "no problems".**
2. **Always give duration**, not just onset.
3. **Acknowledged ≠ resolved.** Say "acknowledged", never imply "handled".
4. **Say what you filtered out.**
5. **Read-only.** Acknowledging an alert is a real action a human owns; there is no write path here.
