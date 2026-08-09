---
name: zabbix-availability
description: "Device availability and monitored inventory from Zabbix — is a device reachable, since when, how often has it flapped, and what is the NMS actually watching. Use when someone asks how long a device has been down, whether it is flapping, or what is and is not being monitored."
version: 1.0.0
license: Apache-2.0
tags: [zabbix, nms, snmp, monitoring, availability, uptime, inventory, observability]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["ZABBIX_URL", "ZABBIX_TOKEN"] } } }
---

# Zabbix Availability & Inventory

## Server

`zabbix-mcp` — vendored third-party, read-only, three tools. See
[zabbix-metrics-history](../zabbix-metrics-history/SKILL.md) for the shared cautions.

## ⚠ The wording rule — this is the whole skill

> ### "Zabbix cannot reach it" is **not** "the device is down."

An NMS reports what **one poller** saw, from **one vantage point**, at **one polling interval**. That is
evidence, not a verdict.

A device can be unreachable from Zabbix and completely healthy: a firewall rule, a management-VRF problem,
a dead SNMP daemon on an otherwise forwarding router, or a poller that has simply not tried recently.

**Never write "the device is down."** Write:

> *"Zabbix has been unable to reach rtr-01 since 14:02 UTC. That is the monitoring system's view from its
> own vantage point — it is not confirmation the device is down. `pyats` or `multivendor-cli` can check the
> device directly."*

This is the same discipline `globalping-external-checks` applies to probes, and it matters **more** here,
because an NMS *feels* authoritative in a way a probe network does not.

## Four states, not two

| State | `available` | Say |
|---|---|---|
| Reachable | `1` | *"Zabbix reached it at \<time>"* |
| Unreachable | `2` | *"Zabbix cannot reach it as of \<time>"* — never "it is down" |
| Unknown | `0` | *"Zabbix has not yet established reachability"* — not the same as unreachable |
| **Not monitored** | host absent | *"this device is not monitored by Zabbix"* — **not the same as unreachable**, and by far the most common cause of surprise |

```jsonc
zabbix_api("host.get", {
  "output": ["hostid","host","name","status"],
  "selectInterfaces": ["interfaceid","ip","dns","port","available","error","errors_from"],
  "selectTags": "extend"
})
```

## Always carry the time

Availability without a timestamp is a claim about the present that may be minutes or hours stale. **Every
answer states when that state was last observed.** `errors_from` gives you when the failure began.

## Down vs flapping — different problems

*"It has been down for 40 minutes"* and *"it has bounced nine times in 40 minutes"* lead to completely
different investigations. Get the transitions, not just the current state — `event.get` against the
unreachability trigger gives you the history.

Report the **count of transitions** as well as the current state whenever the window contains more than one.

## Inventory — what is the NMS actually watching?

```jsonc
zabbix_api("host.get",      {"output":["hostid","host","status"], "selectInterfaces":"extend",
                             "selectParentTemplates":["name"], "selectHostGroups":["name"]})
zabbix_api("hostgroup.get", {"output":"extend"})
zabbix_api("item.get",      {"hostids":["<id>"],
                             "output":["itemid","name","key_","value_type","units","history","trends","lastclock"]})
```

Two rules:

- **A disabled host (`status: 1`) is shown as disabled, never omitted.** A device nobody is watching is a
  **finding**, not an absence — it is usually how a gap in monitoring is discovered.
- **List items with their units and retention** (`history`, `trends`). This lets an engineer see *how far
  back a question can be answered* before they ask it, which is far better than asking and getting nothing.

An item whose `lastclock` is empty is **monitored but has never returned a value** — a broken poll, and a
real finding. Do not report it as "no data".

## Boundaries

| Want to… | Use |
|---|---|
| Metric values over time | `zabbix-metrics-history` |
| Problems and alerts | `zabbix-problem-review` |
| Unsolicited traps | `snmptrap-mcp` — push, not poll |
| Flows | `ipfix-mcp` |
| Instrumented metrics | `prometheus`, `grafana` |
| SaaS monitoring | `auvik`, `thousandeyes`, `datadog` |
| **Confirm** whether a device is actually down | `pyats`, `multivendor-cli`, `fortinet` — go ask the device. This skill only reports what the poller saw |
| Add, enable or disable a host | **nothing here.** Read-only; NMS configuration is out of scope entirely |

## Rules

1. **Never say "the device is down."** Say what Zabbix observed, and when.
2. **Always timestamp the observation.**
3. **Not monitored ≠ unreachable.** Check before you conclude.
4. **Report flap counts, not just current state.**
5. **Show disabled hosts.** Omitting them hides the gap.
6. **Read-only.**
