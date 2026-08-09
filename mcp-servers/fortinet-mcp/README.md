# fortinet-mcp

Fortinet coverage across three planes. NetClaw-authored — spec 080, roadmap **R3**
("largest single-vendor absence").

| Plane | Appliance | Answers | Transport |
|---|---|---|---|
| `manager` | FortiManager | What policy is **intended** across the estate | JSON-RPC `/jsonrpc` |
| `device` | FortiGate | What a box is **actually doing** right now | REST, bearer token |
| `analyzer` | FortiAnalyzer | What traffic **actually hit** the policy | JSON-RPC `/jsonrpc` |

**Transport:** stdio · **Framework:** FastMCP · **Tools:** 21 · **Read-only by default**

## Why this server exists

`workspace/skills/fortimanager-ops/SKILL.md` shipped for a long time as
`user-invocable: true`, declaring env vars and naming `jmpijll/fortimanager-mcp` —
a server that was **never vendored, never registered, and not installable**. The
skill was a claim with nothing behind it. An agent reading `SOUL.md` would route a
firewall question to it and discover the truth mid-investigation.

## The distinction this server protects

**FortiManager holds intent. The FortiGate holds state. They legitimately diverge
between installs, and the gap is where drift and unauthorised change live.**

A rule on the device but absent from the policy package is an out-of-band change —
invisible from either plane alone. `fgt_compare_with_manager` surfaces it.

Equally: **"no logs matched" is not "this rule is unused."** A retention window is
not all of history. That returns its own outcome (`no_logs_in_window`), never `ok`
and never an error — the same discipline spec 078 applied to "no advisories ≠ not
vulnerable" and spec 079 to "no probes ≠ outage".

## Response envelope

Every response passes through `envelope.emit()`, which is a **chokepoint, not a
helper** — a new tool cannot forget attribution or auditing:

```jsonc
{
  "plane": "manager" | "device" | "analyzer",   // set by the calling module, never by a caller
  "scope": { ... },                              // REQUIRED; shape depends on plane
  "source": "fortimanager-01",
  "retrieved_at": "2026-08-01T15:40:00Z",
  "outcome": "ok",
  "data": { ... },
  "notes": []
}
```

Required scope per plane — a response that cannot name its scope is an **error**,
not an unqualified result:

| Plane | Scope | Why |
|---|---|---|
| manager | `adom` | A package name is unique only within an ADOM |
| device | `device`, `vdom` | A figure without its VDOM is ambiguous |
| analyzer | `window_start`, `window_end` | A log result without its window is meaningless |

### Outcomes

`ok` · `empty_result` · `no_logs_in_window` · `plane_unreachable` · `auth_expired` ·
`auth_missing` · `scope_indeterminate` · `refused_read_only` ·
`refused_no_approval` · `refused_no_change_record`

The last three are **deliberately distinct**. A single "not authorised" would
reproduce the exact conflation `/speckit.analyze` caught in spec 076.

## Tools (21)

**Device — 6** · `fgt_system_status` `fgt_list_interfaces` `fgt_get_routes`
`fgt_vpn_tunnels` `fgt_get_policies` `fgt_compare_with_manager`

**Manager — 8** · `fmg_list_adoms` `fmg_list_devices` `fmg_list_policy_packages`
`fmg_get_policy_package` `fmg_search_rules` `fmg_resolve_object` `fmg_get_revisions`
`fmg_preview_install`

**Analyzer — 4** · `faz_query_logs` `faz_fetch_more` `faz_policy_activity`
`faz_list_devices`

**Write + posture — 3** · `fmg_check_change_record` `fmg_install_package`
`fortinet_posture`

## Manifest budget

**Measured 2,486 tokens against a hard 5,000 ceiling** (FR-026) — 50% headroom.
Re-measure with `python3 tests/fortinet/test_manifest_size.py`, which fails the
build if the ceiling is breached.

The manifest loads into *every* conversation whether Fortinet is in play or not, so
its cost is paid by every unrelated task. For scale, the community servers this
replaces ship **106** (`rstierli/fortimanager-mcp`), **69**
(`rstierli/fortianalyzer-mcp`) and **204+** (`paoloamato2/fortinet-mcp-server`)
tools — any one of them blows the budget several times over.

Tools here are **parameterised, not enumerated**: `fmg_get_policy_package(adom,
package)` rather than a tool per object type.

## Writes: two independent gates

`fmg_install_package` pushes policy to production firewalls.

| Condition | Outcome |
|---|---|
| `FORTINET_ALLOW_WRITES` unset | `refused_read_only` |
| No `approved_by` | `refused_no_approval` |
| No approved ServiceNow CR (non-lab) | `refused_no_change_record` |
| Both satisfied | rollback revision identified → install → verify |

`is_lab` waives **only** the change-record gate, never approval. An unclassifiable
device is treated as **production** (inherited from spec 076: guessing "lab" wrongly
permits an unauthorised change; guessing "production" wrongly costs one CR).

Gate logic ported from `mcp-servers/multivendor-cli-mcp/tools/change.py` — copied
rather than imported, since the servers are separate processes with separate
dependency sets.

## Environment

| Variable | Plane | Notes |
|---|---|---|
| `FORTIMANAGER_HOST` / `FORTIMANAGER_API_TOKEN` | manager | |
| `FORTIGATE_HOST` / `FORTIGATE_API_TOKEN` | device | |
| `FORTIANALYZER_HOST` / `FORTIANALYZER_API_TOKEN` | analyzer | token auth needs FAZ 7.2.2+ |
| `FORTINET_VERIFY_SSL` | all | default `true` |
| `FORTINET_ALLOW_WRITES` | all | default `false` |
| `FORTINET_AUDIT_LOG` | all | GAIT trail path; defaults under `~/.openclaw/gait/` |

Each plane is independently optional. A missing variable is reported **by name,
never by value** — including inside exception text, which is where credentials
usually leak.

## Install

```bash
netclaw_pip_install -r mcp-servers/fortinet-mcp/requirements.txt
```

Two dependencies: `mcp>=1.2.0,<2` and `httpx>=0.27.0,<1`. The `mcp` upper bound is
**load-bearing** — 2.0.0 removed `mcp.server.fastmcp`, which this server imports
(spec 077).

No Fortinet SDK. `pyFMG`, `fortiosapi` and `fortigate-api` were all evaluated and
rejected: JSON-RPC here is a POST with `method`/`params`/`session`, and an SDK would
add a dependency and a pinning hazard over an abstraction simpler than the thing
abstracted.

## Tests

```bash
./tests/fortinet/run-tests.sh          # envelope, audit, credentials
python3 tests/fortinet/test_manifest_size.py
```

**Every test runs without an appliance.** That is a design property, not a
limitation — the guarantees this server makes are structural. It earned its keep on
2026-08-01, when the lab was unavailable for most of a day and the foundation
shipped anyway.

## Field notes

Measured against a live FortiGate-VM, FortiOS **7.6.7**, 2026-08-01:

- `monitor/system/interface` returns a **dict keyed by interface name**, not a list.
  Most third-party examples get this wrong.
- `monitor/router/ipv4`, `monitor/vpn/ipsec`, `monitor/system/ha-peer` return lists;
  the latter two are empty on a standalone box with no tunnels. **Empty is
  `empty_result`, not an error.**
- An **unregistered** FortiGate refuses REST auth entirely: every request returns
  401 regardless of token validity, trusthost or admin profile. Verified by packet
  capture that the source address matched the api-user trusthost. If everything
  returns `auth_expired`, check `get system status` for `License Status: Valid`
  before suspecting the token.
- FortiOS 8.0.0 GA has a separate defect where the web GUI logs out in a loop on the
  1 vCPU trial profile (`VM resource exceeds license limit` → `httpsd` restarts).
  SSH and REST are unaffected. 7.4/7.6 do not exhibit it.
- The evaluation licence caps a unit at 1 vCPU, 2 GB RAM, 3 interfaces, 3 routes and
  3 firewall policies. A small ruleset on such a box is a lab limit, not the
  estate's posture.

## Related

`workspace/skills/fortimanager-ops` · `workspace/skills/fortigate-ops` ·
`workspace/skills/fortianalyzer-ops` · `fwrule-analyzer` (FortiOS parser, consumes
policy from here) · `multivendor-cli-mcp` (spec 076 — FortiOS **CLI**, a different
plane)
