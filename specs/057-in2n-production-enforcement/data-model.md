# Phase 1 Data Model: iN2N Production-Mode Enforcement & Durable Runtime

Entities are mostly **in-memory runtime state** plus **small additive columns** on the existing `~/.openclaw/n2n/federation.db` and a **new GAIT git repo**. No wire-schema entities. Nothing here changes the eN2N/iN2N protocol.

## 1. RiskPosture (in-memory, cached; computed by `posture.py`)

The Border's truthful self-report. Recomputed on the background poll and on demand.

| Field | Type | Notes |
|-------|------|-------|
| `mode` | enum `testing` \| `production` | from `N2N_RISK_MODE` |
| `state` | enum `testing` \| `enforced` \| `degraded` | `testing` when mode=testing; else derived from controls |
| `controls` | list[EnforcementControl] | the three controls with live availability |
| `missing` | list[str] | names of controls not active (empty when enforced) |
| `strict_all` | bool | operator override (`N2N_STRICT_ALL`) |
| `computed_at` | epoch float | freshness for the heartbeat/HUD |

**Rules**: `state == enforced` **iff** `mode == production` AND all three controls `available`. Any missing control in production ⇒ `degraded` and `missing` names each. `mode == testing` ⇒ `state == testing` regardless of controls (guards intentionally off, FR-006), never a false production claim (FR-002).

**State transitions**: `testing → production(enforced)` when mode flips and all controls up; `enforced → degraded` when a poll/preflight finds a control down; `degraded → enforced` when it recovers. Transitions are observations, not persisted.

## 2. EnforcementControl (in-memory; probed by `controls.py`)

| Field | Type | Notes |
|-------|------|-------|
| `name` | enum `sandbox` \| `model-guard` \| `audit` | maps to OpenShell / DefenseClaw / GAIT |
| `kind` | enum `containment` \| `audit` | drives FR-019 (containment=block, audit=warn) |
| `available` | bool | last probe result |
| `detail` | str | human reason when unavailable (e.g. "defenseclaw proxy unreachable") |
| `probed_at` | epoch float | for the ~3s probe cache |

**Probes** (each a cheap local check, cached ~3s):
- `sandbox` → `openshell_available()`: `openshell` binary present + cheap health/exec check.
- `model-guard` → `defenseclaw_available()`: `defenseclaw` binary present + guard/proxy health.
- `audit` → `gait_recording()`: GAIT repo initialized and writable (a test commit or `git status` succeeds).

## 3. Member (EXISTING `member` table — additive columns)

Existing columns (056): `member_id`, pinned key, transport binding, `scope`, `health`, `state`, `launch_cmd`, `on_demand`. **Add**:

| New column | Type | Notes |
|-----------|------|-------|
| `managed_by` | text `service` \| `cold` | `service` = has a durable systemd unit (always-on); `cold` = spawned on route. Default `cold` (backward-compatible). |
| `service_unit` | text NULL | unit name (`netclaw-member-<id>.service`) when `managed_by=service`. |
| `component_scan` | text NULL | cached DefenseClaw component-scan result for this member (`pass` \| `flagged:<what>` \| NULL=not scanned). |

**Migration**: `ALTER TABLE member ADD COLUMN ...` guarded by a `PRAGMA table_info` check (same idempotent pattern as 056 additions). Existing rows default to `cold` / NULL — no behavior change until a member is promoted to service-managed.

**Rules**: single-owner — a member with `managed_by=service` is launched/kept-alive by its unit; the cold-start path (`_cold_start`) MUST NOT `create_subprocess_shell` it (it may only `systemctl --user start` the unit if inactive). A `cold` member keeps the 056 cold-start behavior (now sandbox-wrapped in production).

## 4. GAITFederationEvent (NEW — git commits in `~/.openclaw/n2n/gait/`)

Not a table — an immutable git-committed record. `audit.py` still writes the SQLite `remote_invocation_record` row (authoritative, queryable); `gait.py` additionally commits the event and returns a SHA stored in the existing `gait_ref` column.

| Field (in the committed JSON) | Notes |
|-------------------------------|-------|
| `event` | `delegation` \| `enrollment` \| `removal` \| `quarantine` |
| `actor` | operator/claw identity (attributable, FR-012) |
| `member_id` / `peer_identity` | subject of the event |
| `target` | skill/tool + request_id where applicable |
| `channel_kind` | `in2n` \| `en2n` (mirrors the SQLite discriminator) |
| `sqlite_row_id` | back-reference to the `remote_invocation_record` row |
| `ts` | ISO-8601 UTC |

**Rules**: append-only; one commit per event; commit message encodes `event/actor/ts`; **never amended or rebased** (corrections = new commits, Constitution IV / FR-012). Unbounded (FR-012a) — `git gc` only, no rotation. Repo is separate from the netclaw source repo.

## 5. DurableService (generated artifact — systemd `--user` units)

| Field | Type | Notes |
|-------|------|-------|
| `unit_name` | str | `netclaw-mesh.service` or `netclaw-member-<id>.service` |
| `exec_start` | str | daemon: `python3 bgp-daemon-v2.py`; member: sandbox-wrapped `in2n-member.py` (always-on, no `--idle-exit`) |
| `env_file` | path | `~/.openclaw/mesh.systemd.env` (daemon) or the member's env file |
| `restart` | const `always` | + `RestartSec` bounded |
| `wanted_by` | const `default.target` | auto-start on login/boot |

**Rules**: generated by `scripts/in2n-services.py` (FR-015), never hand-authored; the mesh unit template is checked into the repo (Constitution XI). Idempotent regenerate. On non-systemd hosts the generator degrades gracefully and posture reports the durability aspect degraded.

## 6. HealthFaultReport (in-memory; `service.py` + heartbeat)

| Field | Type | Notes |
|-------|------|-------|
| `daemon` | enum `up` \| `down` | mesh daemon / listener reachable |
| `members` | map member_id → `{state: up\|down\|cold-eligible, will_cold_start: bool}` | per-member, from `health`/`_spawning`/`managed_by` |
| `backends` | map member_id → `reachable` \| `unreachable` \| `unknown` | derived from the member's last task result, NOT from federation state |
| `fault_class` | enum `none` \| `daemon` \| `member` \| `backend` | the single most-relevant cause for the heartbeat (FR-017/018) |

**Rules**: `fault_class` precedence: `daemon` > `member` > `backend` > `none` — a daemon-down masks member reports (you can't know member state if the daemon is down). A backend fault is only reported when the daemon and the member are both up (FR-017).

## Relationships

```
RiskPosture 1—* EnforcementControl        (posture aggregates the 3 controls)
Member 1—0..1 DurableService              (always-on member ⇒ one unit; cold ⇒ none)
Member 1—* GAITFederationEvent            (delegations/enroll/removal/quarantine about it)
remote_invocation_record 1—0..1 GAITFederationEvent  (gait_ref SHA cross-links)
HealthFaultReport —uses→ Member.managed_by + health + task results
```
