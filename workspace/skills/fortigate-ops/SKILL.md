---
name: fortigate-ops
description: "FortiGate device operations — system status, interfaces, routing, IPsec VPN tunnel state with phase 1 and phase 2 reported separately, HA member identification, per-VDOM scoping, and manager-vs-device drift detection. Use when asking what a FortiGate is ACTUALLY doing right now, whether a tunnel is up, or whether the device matches FortiManager's intent."
version: 1.0.0
license: Apache-2.0
tags: [fortinet, fortigate, fortios, firewall, vpn, ipsec, vdom, ha, security, multi-vendor]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["FORTINET_MCP_CMD", "FORTIGATE_HOST", "FORTIGATE_API_TOKEN"] } } }
---

# FortiGate Operations — the device plane

## MCP Server

- **Server**: `fortinet-mcp` (NetClaw-authored, spec 080 / roadmap R3)
- **Command**: `$FORTINET_MCP_CMD`
- **Transport**: stdio · FortiOS REST API, bearer token
- **Requires**: `FORTIGATE_HOST`, `FORTIGATE_API_TOKEN`
- **Mode**: read-only — this skill has no write path at all

## The distinction this skill exists to protect

**A FortiGate knows what it is doing. It does not know what it was supposed to do.**

| Question | Plane | Skill |
|---|---|---|
| "Is the tunnel up? What's in the routing table?" | device | **this skill** |
| "What policy is *intended* across the estate?" | manager | `fortimanager-ops` |
| "Has anything ever *matched* this rule?" | analyzer | `fortianalyzer-ops` |
| "Run a raw FortiOS CLI command" | CLI | `multivendor-raw-cli` (spec 076) |

If a device does not answer, this skill reports that it did not answer. **It never
substitutes FortiManager's intended configuration as though it were observed
state** — that would turn "the box is unreachable" into a confident, wrong
description of a box nobody can see.

## Tools (6, all read-only)

| Tool | What it answers |
|---|---|
| `fgt_system_status` | Hostname, serial, version, HA mode, **which member answered** |
| `fgt_list_interfaces` | Interfaces: link, addressing, speed, error counters, per VDOM |
| `fgt_get_routes` | Routing table as observed, optional protocol filter |
| `fgt_vpn_tunnels` | IPsec tunnels — **phase 1 and phase 2 separately** |
| `fgt_get_policies` | Firewall policy as running on the device |
| `fgt_compare_with_manager` | Divergence between intent and observed state |

## Phase 1 and phase 2 are reported separately, always

This is the single most important behaviour here.

A tunnel with **phase 1 up and phase 2 down** is neither "up" nor "down". It is a
specific and common fault — usually a proxy-ID or selector mismatch — where IKE
negotiated fine and no traffic can actually pass. Collapsing the two into one
`status` field destroys the only signal that distinguishes it from a healthy tunnel
or a dead one.

`fgt_vpn_tunnels` therefore returns `phase1_status`, `phase2_status`, and
`phase2_selectors[]` per selector pair, because one down selector out of five is
still a fault worth naming.

## Every response carries its plane and scope

```jsonc
{ "plane": "device", "scope": {"device": "FGVMEVS9GWUAOMBD", "vdom": "root"},
  "source": "...", "outcome": "ok", "data": {...}, "notes": [] }
```

**Scope is mandatory.** A figure without its VDOM is ambiguous on a multi-VDOM unit,
so a response that cannot name its scope is returned as an error rather than as an
unqualified result.

## Workflow: "is the tunnel up?"

1. `fgt_vpn_tunnels` — read **both** phases.
2. Phase 1 down → IKE/peer/PSK/routing problem. Check `fgt_get_routes` for a path
   to the remote gateway.
3. Phase 1 up, phase 2 down → selector/proxy-ID mismatch. Inspect
   `phase2_selectors[]` for which pair failed.
4. Both up but no traffic → not a tunnel problem. Move to policy
   (`fgt_get_policies`) or to the analyzer plane for whether anything matched.

## Workflow: out-of-band change detection

1. `fgt_compare_with_manager` with the ADOM and package.
2. **`only_in_device`** → rules on the box that are absent from the policy package.
   Someone changed the firewall directly. This is the highest-value finding this
   skill produces and it is invisible from either plane alone.
3. **`only_in_manager`** → package not installed since those rules were added.
4. If either plane is unreachable, the tool refuses to compare and names the plane
   that failed. A half-comparison would be worse than none.

## Notes on evaluation-licensed labs

A FortiGate-VM evaluation licence caps the unit at **1 vCPU, 2 GB RAM, 3 interfaces,
3 routes and 3 firewall policies**. A small ruleset on such a device is a lab limit,
not the estate's real posture — `fgt_get_policies` says so in its notes.

An **unlicensed** FortiGate refuses REST authentication entirely: every request
returns 401 regardless of token validity, trusthost, or admin profile. If every call
fails with `auth_expired`, check `get system status` for `License Status: Valid`
before suspecting the token.

## Integration with other skills

| Skill | How they compose |
|---|---|
| `fortimanager-ops` | The intent this device is measured against |
| `fortianalyzer-ops` | Whether traffic actually matched what is configured here |
| `fwrule-analyzer` | Feed `fgt_get_policies` output to its FortiOS parser |
| `multivendor-raw-cli` | Raw CLI (spec 076). Use when you need command output, not structure |
| `pyats-troubleshoot` | Correlate firewall path findings with routing/device state elsewhere |
| `gait-session-tracking` | Every operation here is GAIT-audited automatically |

## Important rules

- **Read-only.** This skill cannot change a FortiGate. Policy changes go through
  `fortimanager-ops` and its two gates.
- **Never report phase 1 and phase 2 as one status.**
- **Never fill an unreachable device's silence with manager data.**
- **Always carry the VDOM.**
