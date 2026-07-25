# Contract: Investigation policy (067 Phase 9)

**Consumer**: `services/alert-receiver` (primary); optional setup/CLI; optional HUD read-only status later.  
**Detail**: [`../investigation-policy.md`](../investigation-policy.md)

## Policy file

| Item | Value |
|------|--------|
| Host path | `~/.openclaw/investigation-policy.yaml` |
| Example seed | `deploy/convergence/config/investigation-policy.example.yaml` |
| Env override | `INVESTIGATION_POLICY_PATH` (optional) |
| Reload | Cache TTL ≤ 60s **or** SIGHUP / documented reload endpoint |

Missing or invalid file → **tier T0** + warning log (fail-safe).

## Tier resolution (order)

1. `force_t0` rules / label `investigate=false` / documented high-cardinality force  
2. `allow_t2` match → **T2** (if budgets admit)  
3. `allow_t1` match → **T1**  
4. else `default_tier`  
5. `degrade.force_max_tier` or budget trip may clamp downward  

## Behavior by tier

| Tier | alert-receiver MUST |
|------|---------------------|
| **T0** | Not call multi-tool OpenClaw investigate hook; optional diary/Discord only |
| **T1** | At most one-shot summarize (0–1 tools); hard completion token cap; no full MCP farm |
| **T2** | Existing investigate hook with **thin tool profile** (dedicated agent id `alert`); subject to budgets |

## Thin T2 agent (OpenClaw)

| Item | Value |
|------|--------|
| Agent id | `alert` |
| Seed | `deploy/convergence/config/alert-agent.example.json` |
| Apply | `scripts/netclaw-alert-agent-profile.sh apply` |
| Tools | Explicit `tools.allow` (prometheus / rag / memory / pfsense / unifi / …) — not full `main` MCP set |
| Hook | `hooks.mappings` path `alert` → `agentId: alert`; `allowedAgentIds` includes `alert` |

## Budgets

Configurable; minimum required:

- Max concurrent T2 investigations  
- Max T2 admissions per rolling hour (or equivalent)

On trip: clamp to T0 or T1; emit metric + log; do not crash process.

## Metrics (Prometheus text on alert-receiver `/metrics`)

| Name | Type | Labels |
|------|------|--------|
| `netclaw_investigations_by_tier` | counter | `tier` = `T0`\|`T1`\|`T2` |
| `netclaw_investigation_budget_trips_total` | counter | `budget` = `concurrent`\|`hourly`\|… |
| (existing) suppress / rate / concurrency | counter | as today |

## Log line (required)

```text
investigation_policy tier=T2 rule=allow_t2:WanHardDown alertname=… fingerprint=…
```

## Setup presets → policy seed

| Preset | `default_tier` | `allow_t2` |
|--------|----------------|------------|
| `observe-only` | T0 | `[]` |
| `triage-cheap` | T1 | `[]` (or severity-based allow_t1) |
| `investigate-critical` | T0 | documented critical alertnames only |

## Non-requirements (Phase 9)

- GUI editor for policy  
- Per-MCP-tool claws  
- OpenClaw `tokenOptimization` key inside `openclaw.json` (invalid schema)
