# Contract: MCP Tool Surface

**Feature**: 076-multivendor-cli-driver | **Date**: 2026-07-30
**Transport**: stdio (declared per Constitution Principle V)
**Server id**: `multivendor-cli-mcp`

The external interface is the MCP tool surface. This is its contract: tools, arguments, return shapes,
and — most importantly — refusal and failure semantics.

---

## Design rules binding every tool

1. **Read-only by default.** Write-capable tools are absent from `tools/list` unless write mode is
   explicitly enabled (FR-022).
2. **Every result names its provenance** — the inventory source for the device, and the server that
   answered (FR-011, FR-017c).
3. **Failures are typed, not stringly.** `unreachable`, `auth_failed`, `platform_mismatch`, `denied`,
   `timeout` stay distinct (FR-005).
4. **A refusal is a successful call with a refusal result**, not a protocol error. The agent must be
   able to read *why* and route elsewhere (FR-010).
5. **No secret in any return value**, ever — credential `ref` and `path` only (FR-019).
6. **Never fabricate.** An unavailable getter, an unreachable device and a filtered command are all
   reported explicitly; none is silently omitted (FR-004, FR-007, FR-014).

---

## `list_devices`

Resolve the inventory and report what is reachable in principle.

```
list_devices(group?: string, platform?: string, source?: "live_sot"|"generated"|"operator")
  -> { devices: [ { name, hostname, platform, groups, source, owning_server } ],
       source_used: "live_sot"|"generated"|"operator",
       fallback_reason?: string }
```

- `source_used` is required (FR-017c). When it is not `live_sot`, `fallback_reason` MUST explain why —
  a stale-cache answer must never look like a live one.
- `owning_server` tells the agent which server owns each device (FR-009).
- Never returns `credential_ref` values. Presence of credentials is not reported as data.

---

## `get_facts`

Normalized, cross-vendor operational facts (FR-006).

```
get_facts(device: string, getters: string[])
  -> { device, source, server: "multivendor-cli",
       facts: [ { getter, available, data?, gap_reason?, provenance } ] }
```

- `available: false` with a `gap_reason` where the platform's NAPALM driver lacks the getter (FR-007).
- `provenance` is `napalm` or `ttp_template`. A `ttp_template` result MUST NOT be presented as
  equivalent to a `napalm` one (R9).
- **Permitted for Cisco and Junos devices**, read-only, because cross-vendor normalized comparison is
  the one case where this server is correct for those platforms (FR-008).

---

## `run_command`

Raw command execution for platforms with no normalized getter (FR-002).

```
run_command(device: string, command: string)
  -> { device, source, server, command,
       status: "ok"|"unreachable"|"auth_failed"|"platform_mismatch"|"denied"|"timeout",
       output?: string, denied_reason?: string }
```

- Filtering is applied **server-side before connecting** (FR-029). A denied command MUST NOT open a
  session.
- `denied_reason` states which rule fired — chaining, denylisted token, or non-allowlisted verb in
  read-only mode — so the operator can tell a policy refusal from a device error.
- `timeout` after the configured per-device bound, default 30s (R11, FR-016).

### Filter evaluation order (normative)

```
1. reject if the command contains any chaining character  ; && || > < ` $(
2. reject if the first token is denylisted (universal or platform-specific)
3. in read-only mode, reject unless the first token matches an allow prefix
4. otherwise permit
```

Order is contractual. `show version; write erase` passes an allowlist check on its first token and is
catastrophic, so chaining rejection MUST come first.

---

## `run_fleet`

One query, many devices (FR-013).

```
run_fleet(target: string, command?: string, getters?: string[],
          max_workers?: int = 10, timeout_s?: int = 30)
  -> { target, requested: int, max_workers, timeout_s,
       results: [ <run_command or get_facts result> ],
       summary: { ok: int, unreachable: int, auth_failed: int, denied: int, timeout: int } }
```

- `len(results) == requested`, always. Every targeted device appears, including failures — a silently
  absent device reads as success (FR-014).
- One device's failure never aborts the others (FR-014).
- Concurrency bounded by `max_workers` (FR-015).
- Exactly one of `command` or `getters` must be supplied.

---

## `check_reachability`

Diagnostic separation of the failure modes (FR-005).

```
check_reachability(device: string)
  -> { device, source, tcp: bool, auth: bool,
       platform_expected: string, platform_detected?: string,
       status: "ok"|"unreachable"|"auth_failed"|"platform_mismatch" }
```

- `platform_detected` differing from `platform_expected` yields `platform_mismatch` — the source of
  truth is wrong, and connecting with the wrong driver would produce confusing output rather than an
  error (FR-005).

---

## `apply_config` *(absent unless write mode is enabled — FR-022)*

```
apply_config(device: string, config: string, expected_state?: object)
  -> { device, status: "refused"|"awaiting_approval"|"verified"|"verification_failed"
                       |"rolled_back"|"rollback_failed",
       refused_reason?: string, owning_server?: string,
       baseline_ref?: string, approval_ref?: string, diff?: object }
```

- **`refused`** when the platform is owned by another server, with `owning_server` naming it (FR-010).
  This is the single most important refusal in the surface: it is what keeps one write path per platform,
  and therefore what keeps Principles I and VIII enforceable.
- A baseline is captured before anything is modified (FR-024) — `baseline_ref` present from
  `awaiting_approval` onward.
- No transition past `awaiting_approval` without an approval (FR-025).
- `verified` / `verification_failed` come from a structured `jdiff` comparison of actual against
  expected state, never from command exit status (FR-026, R9).
- `verification_failed` triggers rollback; `rollback_failed` halts and alerts (FR-027).

---

## Refusal semantics — worked example

A Cisco IOS-XE device, write requested:

```json
{ "device": "core-sw-01", "status": "refused",
  "refused_reason": "platform iosxe is owned by the pyats server; this server is read-only for it",
  "owning_server": "pyats" }
```

Read requested on the same device:

```json
{ "device": "core-sw-01", "source": "live_sot", "server": "multivendor-cli",
  "facts": [ { "getter": "get_bgp_neighbors", "available": true, "provenance": "napalm", "data": {} } ] }
```

Same device, two different answers, both correct: reads may overlap between servers, writes may not.

---

## Environment contract

| Variable | Purpose | Required |
|---|---|---|
| `MULTIVENDOR_INVENTORY_SOURCE` | `live_sot` \| `generated` \| `operator` \| `auto` (default `auto`) | No |
| `MULTIVENDOR_INVENTORY_PATH` | Operator-authored inventory path | Only for `operator` |
| `MULTIVENDOR_GENERATED_PATH` | Generated cache location | No |
| `MULTIVENDOR_WRITE_ENABLED` | Enables write tools; default off | No (FR-022) |
| `MULTIVENDOR_MAX_WORKERS` | Concurrency bound, default 10 | No |
| `MULTIVENDOR_TIMEOUT_S` | Per-device timeout, default 30 | No |
| `VAULT_ADDR` / `VAULT_NAMESPACE` | Preferred credential path | No (FR-018) |
| `MULTIVENDOR_USERNAME` / `MULTIVENDOR_PASSWORD` | Environment fallback credentials | No (FR-018) |

All documented in `.env.example` with descriptions and no values (Principle XIII). Vault is **not** a
prerequisite — an operator with neither a source of truth nor Vault must be able to use the server
(SC-007a).

---

## Install-time contract

| Requirement | Rule |
|---|---|
| Dependency isolation | Dedicated virtualenv; never the shared environment (FR-030a) |
| venv creation | `/usr/bin/python3 -m venv`, populated via `<venv>/bin/python -m pip` — **never bare `pip3`**, which on a split-toolchain host targets an environment the server cannot import from (R7) |
| Registration | Interpreter path resolved at install time, never hardcoded (FR-030b) |
| Post-install assertion | System `cryptography` version unchanged, checked against `/usr/bin/python3` (FR-030c) |
| Gate | `scripts/reconcile-mcp.py` exits 0 with the server registered (SC-012) |
