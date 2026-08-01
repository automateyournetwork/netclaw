# Phase 1 Data Model: Generic Multivendor CLI Driver

**Feature**: 076-multivendor-cli-driver | **Date**: 2026-07-30

No database. These are the runtime entities, their validation rules, and the state transitions that
matter. Field names are indicative; the constraints are the contract.

---

## Entity: Device

The unit of connection.

| Field | Type | Rules |
|---|---|---|
| `name` | string | Unique within a resolution. The operator-facing handle |
| `hostname` | string | Address or resolvable name |
| `platform` | PlatformId | Drives driver selection. Mismatch is detectable (FR-005) |
| `credential_ref` | string | **A reference, never a secret** (FR-017d) |
| `groups` | list[string] | Site / role / tag membership; targets for fleet queries |
| `source` | InventorySource | Which of the three supplied this device (FR-017c) |
| `owning_server` | string | Which MCP server owns this platform (FR-009–011) |

**Validation**
- `credential_ref` MUST NOT contain a password, key, or token. Rejecting a device whose inventory
  record carries credential-shaped fields is required, not optional (FR-017d, Principle XIII).
- `platform` absent → the device is unusable; report rather than guess a default driver.
- `source` MUST always be populated, so a stale-cache answer is never mistaken for a live one.

---

## Entity: InventorySource

Exactly three, with different authority and different write rules. **The distinction between the two
file-based sources is the part that matters**: conflating them destroys operator work.

| Source | Authority | Server may overwrite | Staleness |
|---|---|---|---|
| `live_sot` | Preferred | n/a | None — queried per call |
| `generated` | Cache / offline fallback | **Yes** — by design | Since last refresh |
| `operator` | Operator's own | **Never** | Operator's responsibility |

**Rules**
- Resolution order: `live_sot` → `generated` → `operator`, falling back on unreachability (FR-017b).
- `generated` files MUST carry a machine-readable marker identifying them as generated, so a refresh
  can never overwrite an `operator` file (FR-017b).
- `generated` MUST be reproducible from its source. One that cannot be regenerated is a defect (FR-017a).
- pyATS `testbed.yaml` is **not** a source (FR-017e).
- No source may contain credential material (FR-017d).

---

## Entity: PlatformId

The OS family determining driver, command syntax, and destructive-command vocabulary.

| Field | Type | Notes |
|---|---|---|
| `family` | enum | e.g. `mikrotik_routeros`, `vyos`, `sonic`, `nokia_srlinux`, `extreme_exos`, `huawei_vrp`, `dell_os10`, `ubiquiti_edge` |
| `netmiko_driver` | string | Raw-CLI transport driver |
| `napalm_driver` | string \| null | Null where NAPALM has no driver — normalized facts unavailable |
| `owning_server` | string | `pyats` \| `junos-mcp` \| `multivendor-cli` |
| `deny_tokens` | list[string] | Destructive first tokens **for this platform** (R6) |

**Why `deny_tokens` is per-platform**: the Constitution names `write erase`, `reload`, `format flash:` —
all Cisco syntax. Equivalents differ: VyOS `delete`, MikroTik `/system reset-configuration`, SR Linux
`tools system configuration`, SONiC `config erase`. A Cisco-shaped denylist is insufficient (FR-023).

---

## Entity: CommandPolicy

Server-side enforcement (FR-029) — never advisory skill prose.

| Field | Type | Notes |
|---|---|---|
| `allow_prefixes` | list[string] | `show`, `display`, `get`, … — read-only verbs |
| `deny_tokens` | list[string] | Universal plus per-platform |
| `chain_chars` | list[string] | `;`, `&&`, `\|\|`, `>`, `<`, backtick, `$(` |
| `mode` | enum | `read_only` (default) \| `write_enabled` (FR-022) |

**Evaluation order** — order is itself a requirement, because a permissive check running first would
defeat the others:

```
1. reject if any chain_chars present        ← first: chaining defeats every later check
2. reject if first token in deny_tokens (universal or platform)
3. in read_only mode, reject unless first token matches allow_prefixes
4. otherwise permit
```

**Rule**: chaining rejection MUST precede allowlist evaluation. `show version; write erase` passes an
allowlist check on its first token and is catastrophic.

---

## Entity: NormalizedFact

A datum whose shape is identical across platforms — the unit of cross-vendor comparison.

| Field | Type | Notes |
|---|---|---|
| `getter` | string | NAPALM getter name |
| `available` | bool | False where the platform's driver lacks it |
| `data` | object \| null | Null when unavailable |
| `gap_reason` | string \| null | Why unavailable, when it is (FR-007) |
| `provenance` | enum | `napalm` \| `ttp_template` |

**Rules**
- Unavailability MUST be reported explicitly, never silently omitted from results (FR-007).
- `provenance = ttp_template` MUST NOT be presented as equivalent to `napalm`. Emulating a missing
  getter by scraping CLI output and labelling it normalized is the exact failure FR-007 prevents (R9).

---

## Entity: RawCommandResult

| Field | Type |
|---|---|
| `device` | string |
| `command` | string |
| `output` | string \| null |
| `status` | enum: `ok` \| `unreachable` \| `auth_failed` \| `platform_mismatch` \| `denied` \| `timeout` |
| `denied_reason` | string \| null |

**Rule**: the five failure statuses MUST remain distinct (FR-005). "Unreachable" and "auth failed"
have entirely different remediations, and collapsing them wastes an operator's time.

---

## Entity: FleetQuery / FleetResult

| Field | Type | Notes |
|---|---|---|
| `target` | string | Group, tag, or explicit device list |
| `max_workers` | int | Default 10, operator-overridable (R11) |
| `timeout_s` | int | Default 30 per device (R11) |
| `results` | list[RawCommandResult \| NormalizedFact] | One per device |

**Rules**
- One device's failure MUST NOT abort the others (FR-014).
- Every targeted device MUST appear in `results`, including failures — a silently missing device reads
  as "fine" (FR-014).
- Devices contacted concurrently, bounded by `max_workers` (FR-015).

---

## Entity: ChangeTransaction (US5, P3)

| Field | Type | Notes |
|---|---|---|
| `device` | string | |
| `baseline` | string | Captured **before** any modification (FR-024) |
| `baseline_path` | path | Inside the sandbox root only |
| `approval` | ApprovalRef | Required; absent means no application (FR-025) |
| `expected_state` | object | For post-change comparison |
| `actual_state` | object | Read back after application |
| `verification` | enum | `pass` \| `fail` — via `jdiff` structured diff (FR-026, R9) |
| `rollback` | enum \| null | `not_needed` \| `succeeded` \| `failed` (FR-027) |

**State transitions** — each arrow is a gate, not a step:

```
requested
   → refused                      if platform is owned by another server (FR-010)
   → baseline_captured            (FR-024, Principle II)
   → awaiting_approval            (FR-025, Principle I)
   → applied                      only after approval
   → verified | verification_failed   via jdiff (FR-026, Principle VIII)
   → rolled_back | rollback_failed    on verification failure (FR-027)
```

**Rules**
- No transition to `applied` without both `baseline_captured` and an approval (FR-024, FR-025).
- Verification MUST compare state, not command exit status (FR-026, Principle VIII).
- `rollback_failed` MUST halt and alert rather than continue (Principle VIII).
- Every transition GAIT-logged (FR-028, Principle IV).
- Cisco/Junos devices terminate at `refused` (FR-010).

---

## Entity: CredentialResolution

| Field | Type | Notes |
|---|---|---|
| `ref` | string | From the Device record |
| `path` | enum | `vault` \| `environment` (FR-018) |
| `resolved` | bool | |

**Rules**
- Vault preferred; environment is a documented fallback. Vault MUST NOT be a hard prerequisite (FR-018).
- `path` MUST be reported so a deployment's posture is inspectable (FR-018a).
- A credential MUST NEVER be read from an inventory file, whichever source (FR-019).
- The secret value MUST NOT appear in any result, log, or audit record — only `ref` and `path`.

---

## Cross-cutting invariants

1. **No secret on disk** outside a gitignored `.env` (FR-019, Principle XIII).
2. **Attribution everywhere** — every device answer names its inventory source, and every result names
   the server that produced it (FR-017c, FR-011).
3. **One write path per platform** (FR-010). Reads may overlap; writes may not.
4. **Explicit gaps over silent omission** — an unavailable getter, an unreachable device and a denied
   command are all reported, never dropped (FR-004, FR-007, FR-014).
5. **Filtering is server-side** (FR-029). Skill documentation describes policy; it never enforces it.
