# Contract — `fortinet-mcp` tool surface

**Phase 1** · 2026-08-01 · Transport **stdio**, framework **FastMCP**, JSON-RPC lifecycle
(`initialize`, `tools/list`, `tools/call`) per Principle V.

**Budget: the entire `tools/list` response MUST measure ≤ 5,000 tokens** (FR-026). This contract is
written to that constraint — it is why the surface is 20 tools and not 200. Every tool below is
**parameterised** rather than enumerated (research R5).

---

## Universal response envelope

Every tool returns the shape in [data-model.md §1](../data-model.md). No exceptions, enforced by
`envelope.py` rather than by convention.

```jsonc
{ "plane": "...", "scope": {...}, "source": "...", "retrieved_at": "...",
  "data": {...}, "notes": [], "outcome": "ok" }
```

---

## Manager plane — 8 tools (`plane: "manager"`, scope requires `adom`)

| Tool | Params | Returns | Req |
|---|---|---|---|
| `fmg_list_adoms` | — | ADOMs + managed-device counts | FR-010 |
| `fmg_list_devices` | `adom` | Managed FortiGates, install status | FR-010 |
| `fmg_list_policy_packages` | `adom` | Packages + install targets | FR-011 |
| `fmg_get_policy_package` | `adom`, `package` | Ordered rules: position, action, status, object refs | FR-011 |
| `fmg_search_rules` | `adom`, `package?`, `src?`, `dst?`, `service?`, `object?` | Matching rules | FR-012 |
| `fmg_resolve_object` | `adom`, `name`, `type?` | Object → members, **resolved recursively** | FR-013 |
| `fmg_get_revisions` | `adom`, `package` | Revision history — rollback context | FR-014 |
| `fmg_preview_install` | `adom`, `package`, `target?` | What an install *would* change | FR-022 |

`fmg_preview_install` is **read-only and requires neither gate** — it changes nothing (FR-022). It is
deliberately named `preview`, never `install`.

---

## Device plane — 6 tools (`plane: "device"`, scope requires `device` + `vdom`)

| Tool | Params | Returns | Req |
|---|---|---|---|
| `fgt_system_status` | `vdom?` | Hostname, serial, version, HA mode, **answering HA member** | FR-015, FR-017 |
| `fgt_list_interfaces` | `vdom?` | Interfaces + state, per VDOM | FR-015, FR-018 |
| `fgt_get_routes` | `vdom?`, `protocol?` | Routing table, per VDOM | FR-015 |
| `fgt_vpn_tunnels` | `vdom?` | **`phase1_status` and `phase2_status` as separate fields** | FR-016 |
| `fgt_get_policies` | `vdom?` | Rules as *running on the device* — the divergence input | FR-008 |
| `fgt_compare_with_manager` | `adom`, `package`, `device`, `vdom?` | Divergence finding across both planes | FR-008 |

`fgt_compare_with_manager` is the only tool touching two planes. Its envelope carries
`plane: "device"` with `planes_consulted: ["manager","device"]` in `data`, because the *comparison* is
anchored on observed state. If either plane is unreachable it returns `plane_unreachable` naming which —
it never compares against a plane it could not read (FR-007).

---

## Analyzer plane — 4 tools (`plane: "analyzer"`, scope requires the window)

| Tool | Params | Returns | Req |
|---|---|---|---|
| `faz_query_logs` | `adom`, `filter`, `window_start?`, `window_end?`, `limit?` | Entries + `total`/`has_more`/`next_offset`; **window echoed back** | FR-018a/b |
| `faz_fetch_more` | `adom`, `handle`, `offset` | Next page — re-runs at offset, does not reuse a consumed `tid` | FR-018a |
| `faz_policy_activity` | `adom`, `policyid`, `window_start?`, `window_end?` | Whether traffic matched a rule in the window | FR-018a/b |
| `faz_list_devices` | `adom` | Devices logging to this analyzer | FR-018a |

**Default window (FR-018c)**: absent bounds ⇒ **last 24 hours**, applied and stated in `scope`, never an
unbounded query.

**`faz_policy_activity` empty result** ⇒ `outcome: "no_logs_in_window"` with the explicit message that
this is *not* evidence the rule is unused. This tool answers the question most likely to be misread, so
the guard lives in the tool rather than in the skill.

---

## Write path — 2 tools, disabled by default

Both refuse unless `FORTINET_ALLOW_WRITES=true` (FR-019).

| Tool | Params | Req |
|---|---|---|
| `fmg_install_package` | `adom`, `package`, `target`, `approved_by`, `change_request` | FR-020, FR-021 |
| `fmg_check_change_record` | `change_request` | FR-020 |

### Gate semantics — the contract that matters most

`fmg_install_package` evaluates **two independent gates**:

| Condition | `outcome` |
|---|---|
| `FORTINET_ALLOW_WRITES` unset/false | `refused_read_only` |
| `approved_by` absent | `refused_no_approval` |
| `change_request` absent/unapproved, device **not** lab | `refused_no_change_record` |
| Both satisfied | proceeds: baseline → apply → verify |

**Neither gate can satisfy the other.** Distinct outcome values exist so a caller cannot conflate them,
and each refusal names the specific missing gate (FR-020a). A single "not authorised" would reproduce the
exact defect `/speckit.analyze` found in spec 076.

`is_lab` exempts **only** the change-record gate, never the approval gate (FR-024). An unclassifiable
device is treated as **production** (inherited from spec 076).

On success: rollback revision identified **before** apply; state verified after; failed verification
attempts rollback (FR-021, Principles II and VIII).

---

## Total surface: 20 tools

8 manager + 6 device + 4 analyzer + 2 write.

**This count is a design target, not a measurement.** FR-025 requires the real `tools/list` token count be
taken with `count_tokens` once the surface exists, and recorded. If it exceeds 5,000, tools are merged or
parameters folded — the ceiling wins, not the surface.

---

## Error semantics

Every `outcome` in [data-model.md §2](../data-model.md) is reachable from this surface. Three obligations
that are easy to get wrong and are therefore contractual:

1. **`auth_missing` names the environment variable and never its value** (FR-029) — including inside
   exception text, which is where credentials usually leak.
2. **`auth_expired` is an authentication condition, not an empty result.** An expired FortiManager session
   returning "no policies" would be a silent, plausible, wrong answer.
3. **`plane_unreachable` names the plane** and MUST NOT be answered from another (FR-007). A cross-plane
   question with one plane down returns what responded plus a note saying which did not.
