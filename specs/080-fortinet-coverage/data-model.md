# Data Model — Fortinet Coverage (spec 080)

**Phase 1** · 2026-08-01 · Stateless server; these are **response and request shapes**, not persisted
records. Nothing here is written to a database.

---

## 1. The response envelope — the feature's core guarantee

Every tool response passes through `envelope.py`. There is no path to a client that bypasses it (plan,
"chokepoint"). FR-005 and FR-009.

```jsonc
{
  "plane": "manager" | "device" | "analyzer",   // REQUIRED, always
  "scope": { ... },                              // REQUIRED, shape depends on plane
  "source": "fortimanager-01",                   // the appliance that answered
  "retrieved_at": "2026-08-01T14:22:31Z",
  "data": { ... },                               // the plane-specific payload
  "notes": []                                    // caveats: partial answers, planes not consulted
}
```

### Scope, per plane

| Plane | Required scope fields | Why it is required |
|---|---|---|
| `manager` | `adom` | A policy-package name is unique only within an ADOM |
| `device` | `device`, `vdom` | A figure without its VDOM is ambiguous on a multi-VDOM FortiGate |
| `analyzer` | `window_start`, `window_end` | A log result without its window means nothing |

**Validation rule (FR-009)**: a response whose scope cannot be determined MUST be returned as an
`error`, never as an unqualified result. Silently omitting scope is the failure mode this exists to
prevent.

**Validation rule (FR-006)**: `plane` is set by the module that made the call, never by a caller
parameter. A manager tool cannot emit `plane: "device"`.

---

## 2. Error and non-answer shapes

Distinguishing these is as load-bearing as the envelope. Collapsing them is the error spec 078 and 079
each fought in their own domain.

```jsonc
{
  "plane": "analyzer",
  "scope": { "window_start": "...", "window_end": "..." },
  "outcome": "no_logs_in_window",
  "message": "No logs matched policy 12 between <start> and <end>.
              This is NOT evidence the rule is unused."
}
```

| Outcome | Meaning | MUST NOT be reported as |
|---|---|---|
| `ok` | Data returned | — |
| `no_logs_in_window` | Analyzer queried, nothing matched | "the rule is unused" (FR-018b) |
| `empty_result` | Manager/device queried, no such object | an error |
| `plane_unreachable` | The appliance did not answer | data from another plane (FR-007) |
| `auth_expired` | Session/token expired | "no policies exist" (edge case) |
| `auth_missing` | Env var absent — **named, never valued** | anything containing the value (FR-029) |
| `refused_read_only` | Write attempted, writes disabled | a failure of the appliance (FR-019) |
| `refused_no_approval` | Human approval missing — **named specifically** | generic "not authorised" (FR-020a) |
| `refused_no_change_record` | Approved CR missing — **named specifically** | generic "not authorised" (FR-020a) |
| `scope_indeterminate` | Scope could not be established | an unqualified result (FR-009) |

**`refused_no_approval` and `refused_no_change_record` are separate values by design.** One collapsed
"not authorised" would reproduce the exact conflation `/speckit.analyze` caught in spec 076.

---

## 3. Manager-plane entities

### ADOM
| Field | Notes |
|---|---|
| `name` | The scope key for everything below |
| `mode` | normal / backup |
| `managed_device_count` | Trial licence caps this at 3 |

### PolicyPackage
| Field | Notes |
|---|---|
| `name` | Unique **within** an ADOM only |
| `adom` | Always carried |
| `install_targets[]` | Devices/VDOMs this package installs to |
| `install_status` | Per target; distinct from "the rules exist" |

### PolicyRule
| Field | Notes |
|---|---|
| `policyid`, `position` | Order matters — shadowing is positional |
| `action` | accept / deny |
| `status` | enabled / disabled. A disabled rule is not an absent rule |
| `srcaddr[]`, `dstaddr[]`, `service[]` | **Object references**, not values |
| `srcintf[]`, `dstintf[]` | |

**Rule (FR-013)**: a `PolicyRule` returned with unresolved object *names* only is not an audit. Object
resolution is a first-class requirement, not a convenience.

### AddressObject / ServiceObject / Group
| Field | Notes |
|---|---|
| `name`, `type` | |
| `members[]` | Groups resolve **recursively**; a nested group resolved one level deep is still unresolved |
| `value` | subnet / iprange / fqdn / port-range |

### Revision
| Field | Notes |
|---|---|
| `version`, `created`, `created_by` | |
| `comments` | |

The rollback context for FR-021. A gated install identifies its rollback revision **before** applying,
not after failing.

---

## 4. Device-plane entities

### DeviceStatus
`hostname`, `serial`, `version`, `ha_mode`, `ha_member` *(FR-017 — which cluster member answered)*,
`vdom_enabled`.

### Interface / Route
Per VDOM (FR-018). Free-licence lab caps both at 3.

### VpnTunnel — models an explicit spec requirement
| Field | Notes |
|---|---|
| `name`, `remote_gateway` | |
| `phase1_status` | up / down |
| `phase2_status` | up / down — **separate field, deliberately** |
| `phase2_selectors[]` | |

**Rule (FR-016)**: phase 1 and phase 2 are never collapsed into one `status`. A tunnel with phase 1 up
and phase 2 down is neither "up" nor "down", and that state is a common real fault.

---

## 5. Analyzer-plane entities

### LogQuery (request)
| Field | Notes |
|---|---|
| `adom` | |
| `filter` | policy id / address / service |
| `window_start`, `window_end` | **A default bound is applied and stated if absent** (FR-018c) |
| `offset`, `limit` | |

### LogResult
| Field | Notes |
|---|---|
| `entries[]` | |
| `total`, `has_more`, `next_offset` | Re-run at offset; do **not** treat FortiAnalyzer's `tid` as a durable cursor (research R1) |
| `window_start`, `window_end` | Echoed back — the window actually queried, not the one requested |

**Rule**: `entries: []` is `no_logs_in_window`, never "unused".

---

## 6. Write-path state (US3 only)

```
requested → read_only_refused
          → awaiting_approval        (no human approval)
          → awaiting_change_record   (approved by human, no valid CR)
          → baseline_captured
          → applied
          → verified | rollback_attempted → rolled_back | rollback_failed
```

| Field | Notes |
|---|---|
| `approved_by` | Human approval — gate 1 |
| `change_request` | ServiceNow CR — gate 2, **independently required** |
| `is_lab` | Exempts gate 2 only. **Never** gate 1 (FR-024) |
| `baseline_revision` | Captured before apply |

**Rule (FR-020)**: reaching `baseline_captured` requires **both** gates. There is no transition that
satisfies one by way of the other.

**Rule (inherited, spec 076)**: a device that cannot be classified is treated as **production**.
Misclassifying production as lab permits an unauthorised change; the reverse costs one CR.

**Rule (FR-022)**: install *preview* does not enter this machine at all — it changes nothing and requires
neither gate.

---

## 7. Cross-plane divergence (FR-008)

Not an appliance entity — a NetClaw finding.

| Field | Notes |
|---|---|
| `manager_state` | Rule as it exists in the policy package (intent) |
| `device_state` | Rule as it exists on the FortiGate (observed) |
| `divergence` | `only_in_manager` / `only_in_device` / `differs` |
| `planes_consulted[]` | |

**Rule**: a divergence is **reported**, never silently resolved. `only_in_device` is an out-of-band
change — the single most operationally interesting thing this feature can surface, and invisible from
either plane alone.

---

## 8. Credentials (never in any response)

**Nine variables.** One server serves all three planes, so there is **one** command variable, not one per
skill.

| Var | Plane |
|---|---|
| `FORTINET_MCP_CMD` | all — the server command all three skills invoke |
| `FORTIMANAGER_HOST`, `FORTIMANAGER_API_TOKEN` | manager |
| `FORTIGATE_HOST`, `FORTIGATE_API_TOKEN` | device |
| `FORTIANALYZER_HOST`, `FORTIANALYZER_API_TOKEN` | analyzer |
| `FORTINET_VERIFY_SSL` | all — default `true` (FR-030) |
| `FORTINET_ALLOW_WRITES` | all — default `false` (FR-019) |

**Naming note (resolved by `/speckit.analyze`)**: the existing `fortimanager-ops/SKILL.md` declares
`FORTIMANAGER_MCP_CMD`. That name is **superseded** by `FORTINET_MCP_CMD`, because one server now backs
three skills and a manager-named command variable would misdescribe the device and analyzer skills. T067's
back-fill must change it, and the regenerated iN2N member (T074) must follow — the old name resolving to
nothing is precisely the defect this feature exists to fix.

**Rule (FR-029)**: absence is reported **by variable name**. No token, session id or password appears in
any response, log or GAIT record — including inside error strings, which is where they usually leak.
