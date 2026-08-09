---
name: catalyst-center-readonly
description: "Query Cisco Catalyst Center read-only — device inventory, site hierarchy, wireless, assurance health, compliance, software images, events. All 514 read-only API operations reachable through 8 grouped dispatchers. Use when asked what Catalyst Center manages, where a device sits, what its health or compliance state is, or to reconcile controller state against the devices themselves."
version: 1.0.0
license: Apache-2.0
tags: [cisco, catalyst-center, dnac, inventory, assurance, compliance, wireless, sites]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["CATALYST_CENTER_HOST", "CATALYST_CENTER_USERNAME", "CATALYST_CENTER_PASSWORD"] } } }
---

# Catalyst Center (read-only)

## Server

`catc-mcp` — a NetClaw client over **Cisco's official tool catalogue**
(`cisco-en-programmability/catc-mcp-oss`, Apache-2.0, `release/2.3.7.11`). **Strictly read-only**: all
**514 GET operations**, the one mutating operation excluded. Manifest **1,821 tokens**, where inlining
every upstream tool would cost **64,420**.

## The 10 tools

**Start with discovery** — the catalogue is far too large to carry in the tool list:

| Tool | Use |
|---|---|
| `catc_find(query, group, limit)` | **Search all 514 operations** by keyword or URI. Start here |
| `catc_describe_operation(name)` | Full parameter schema for one operation |

**Then dispatch** — `catc_<group>(operation, params)`:

`catc_devices` · `catc_sites` · `catc_wireless` · `catc_health` · `catc_compliance` ·
`catc_software` · `catc_events` · `catc_other`

**Operation names are not guessable.** They are generated from Cisco's API spec — the device list is
`api_getSites`-style naming, not `getDeviceList`. **Always `catc_find` first.** Guessing wastes a call and
gets a refusal that names near-matches.

## ⚠ Two rules

### 1. An empty inventory is not an empty network

Zero devices means **this controller manages none**. It does not mean the network is empty. The causes are
different and matter:

| Cause | What it means |
|---|---|
| Discovery has not run | devices exist, Catalyst Center has not found them |
| RBAC scopes the account | the estate is larger than this account can see |
| **The wrong appliance** | you are asking a controller that manages nothing |
| A filter excluded everything | your parameters, not the network |
| Genuinely nothing onboarded | the only case that is about the estate |

**This is not hypothetical.** The two DevNet sandboxes share credentials and are not equivalent —
`sandboxdnac.cisco.com` has 4 devices and 25 sites; `sandboxdnac2.cisco.com` has **0 devices** and
authenticates perfectly. An inventory answer from the second looks exactly like a real empty estate.

That is why **every response names the appliance it came from**, and why an empty result *or a zero count*
carries an explicit caveat. **Repeat the appliance name when you report a count**, especially a zero.

### 2. "Catalyst Center says" is not "the device is"

`reachabilityStatus` is the controller's **last polling result**, not ground truth. A device shown
Unreachable may be perfectly healthy and merely unreachable *from the controller* — a management-VRF
problem, an ACL, a dead SNMP/NETCONF agent on an otherwise forwarding switch.

Catalyst Center is a **database of what it last learned**. A device can be listed and long dead, or absent
and carrying traffic. Say **when** it was observed, and if the answer matters, confirm against the device
with `pyats` or `multivendor-cli`.

## Outcomes you will see

| `outcome` | Means |
|---|---|
| `ok` | records returned |
| `empty` | this controller returned nothing — **see rule 1**, never report as a network fact |
| `unreachable` | the appliance could not be reached. **Not** an empty result |
| `auth_failed` | credentials rejected or token expired. State is **unknown**, not empty |
| `forbidden` | RBAC denied it — and a related answer you *did* get may be **scoped, not complete** |
| `not_configured` | no appliance is configured at all |
| `refused` | unknown operation, or a missing path parameter |

`unreachable`, `auth_failed` and `empty` are **three different facts**. Never collapse them.

## Boundaries

| Want to… | Use |
|---|---|
| Read the **device** itself | `pyats`, `multivendor-cli` — when they disagree with the controller, **the device is right** |
| **Intended** state | `netbox`, `nautobot` — this is *discovered* state. A device here and not in NetBox is a reconciliation finding, not an error |
| Search Cisco **documentation** | `devnet-catalyst-search` — that reads docs; this queries an appliance |
| Wireless client experience over time | `thousandeyes`, `prometheus` |
| Change anything | **nothing here.** Read-only; no mutation is reachable |

## Rules

1. **`catc_find` before dispatching.** Operation names are generated, not guessable.
2. **Never report an empty result or zero count as a network fact.** Name the appliance.
3. **Never say a device is down** because Catalyst Center cannot reach it.
4. **State when the controller observed the data.**
5. **`forbidden` on one call means other answers may be scoped.** Say so.
6. **Read-only.**
