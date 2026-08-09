---
name: fortimanager-ops
description: "FortiManager policy operations — ADOM inventory, policy package review, recursive object resolution, revision history, install preview, and gated package install. Use when auditing FortiGate firewall policy at the MANAGER level (intent), reviewing ADOM policy packages, or planning a package install with rollback context."
version: 2.0.0
license: Apache-2.0
tags: [fortinet, fortimanager, firewall, policy, adom, security, multi-vendor]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["FORTINET_MCP_CMD", "FORTIMANAGER_HOST", "FORTIMANAGER_API_TOKEN"] } } }
---

# FortiManager Operations — the manager plane

## MCP Server

- **Server**: `fortinet-mcp` (NetClaw-authored, spec 080 / roadmap R3)
- **Command**: `$FORTINET_MCP_CMD`
- **Transport**: stdio
- **Requires**: `FORTIMANAGER_HOST`, `FORTIMANAGER_API_TOKEN`
- **Mode**: read-only by default; installs require **two** gates (below)

> **v2.0.0**: this skill previously declared `FORTIMANAGER_MCP_CMD` pointing at
> `jmpijll/fortimanager-mcp`, which was never vendored, never registered and not
> installable — the skill was a claim with no server behind it. It is now backed by
> `fortinet-mcp`, and the command variable changed to `FORTINET_MCP_CMD` because one
> server serves all three Fortinet planes.

## The distinction this skill exists to protect

**FortiManager holds INTENT. It does not know what a device is actually doing.**

| Question | Plane | Skill |
|---|---|---|
| "What policy is *supposed* to apply here?" | manager | **this skill** |
| "What is the box *actually* running? Is the tunnel up?" | device | `fortigate-ops` |
| "Has anything ever *matched* this rule?" | analyzer | `fortianalyzer-ops` |
| "Run a raw FortiOS CLI command" | CLI | `multivendor-raw-cli` (spec 076) |

A policy package and a FortiGate's running config legitimately diverge between
installs. That gap is where drift, unauthorised change and failed installs live —
use `fgt_compare_with_manager` to surface it rather than assuming they agree.

## Tools (8 read-only + 2 write)

| Tool | What it answers |
|---|---|
| `fmg_list_adoms` | Which ADOMs exist. The ADOM scopes everything else |
| `fmg_list_devices` | Managed FortiGates, connection and sync status |
| `fmg_list_policy_packages` | Packages in an ADOM and their install targets |
| `fmg_get_policy_package` | Ordered rules: position, action, enabled state |
| `fmg_search_rules` | Rules matching a source, destination, service or object |
| `fmg_resolve_object` | Object/group → members, **resolved recursively** |
| `fmg_get_revisions` | Revision history — rollback context |
| `fmg_preview_install` | What an install *would* change. **No gate required** |
| `fmg_check_change_record` | Is a ServiceNow CR approved? Read-only |
| `fmg_install_package` | **Production change.** Two gates, see below |

## Every response carries its plane and scope

```jsonc
{ "plane": "manager", "scope": {"adom": "root", "package": "Corp"},
  "source": "...", "outcome": "ok", "data": {...}, "notes": [] }
```

`outcome` distinguishes results that look alike: `ok`, `empty_result`,
`plane_unreachable`, `auth_expired`, `auth_missing`, `scope_indeterminate`, and the
three separate write refusals. **An expired session is `auth_expired`, never "no
policies exist"** — that would be a silent, plausible, wrong answer.

## Workflow: policy package audit

1. `fmg_list_adoms` → pick the ADOM. A package name is unique only within one.
2. `fmg_list_policy_packages` → find the package and its install targets.
3. `fmg_get_policy_package` → ordered rules. Note **position**: shadowing is positional.
4. `fmg_resolve_object` on every group a rule references. **A rule reported only by
   object name is not an audit** — "allow GRP_CORP to GRP_DMZ" says nothing about
   which addresses that permits.
5. `fmg_get_revisions` → rollback context before proposing any change.
6. Feed the rules to `fwrule-analyzer` for overlap, shadowing and conflict analysis.

## Workflow: is intent matching reality?

1. `fmg_get_policy_package` — the intent.
2. `fgt_compare_with_manager` (in `fortigate-ops`) — the divergence.
3. `only_in_device` entries are candidate **out-of-band changes**: someone edited
   the firewall directly. This is the single most valuable finding here.
4. `only_in_manager` usually means the package has not been installed since those
   rules were added — check `fmg_list_devices` sync status.

## Writes: two gates, and neither substitutes for the other

`fmg_install_package` pushes policy to production firewalls — the highest
blast-radius action available here.

| Condition | Outcome |
|---|---|
| `FORTINET_ALLOW_WRITES` not set | `refused_read_only` |
| No `approved_by` | `refused_no_approval` |
| No approved ServiceNow CR (non-lab) | `refused_no_change_record` |
| Both present | proceeds: revision identified → install → verify |

**Human approval and a ServiceNow change record are different gates.** A CR does
not imply a human said yes; a human saying yes does not imply change control
approved it. Lab devices waive the CR gate **only** — never the approval gate — and
a device that cannot be classified is treated as **production**.

Always run `fmg_preview_install` first. It shows what would change and needs no gate.

## Integration with other skills

| Skill | How they compose |
|---|---|
| `fortigate-ops` | Device-plane state; `fgt_compare_with_manager` for drift |
| `fortianalyzer-ops` | Whether a rule has actually matched traffic |
| `fwrule-analyzer` | Feed retrieved policy to its FortiOS parser for overlap/shadowing |
| `servicenow-change-workflow` | Supplies the CR that satisfies gate 2 of `fmg_install_package` |
| `multivendor-raw-cli` | Raw FortiOS CLI (spec 076) — a different plane, not a substitute |
| `gait-session-tracking` | Every operation here is GAIT-audited automatically |

## Important rules

- **Treat package install as production change execution** — baseline, verify, rollback.
- **Always name the ADOM.** A package without one is ambiguous.
- **Resolve objects before drawing conclusions.**
- **Never present manager intent as observed device state.**
- **An empty result is not an error**, and `auth_expired` is not "no data".
