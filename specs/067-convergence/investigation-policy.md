# Investigation policy & token economics (067 Phase 9)

**Feature**: 067-convergence  
**Phase**: 9 (optional PR after Phase 8 telemetry)  
**Status**: Spec’d  
**Working notes** (gitignored): `docs/architecture/convergence-context/token-burn-remediation-plan.md`

## Problem

The Convergence pipe (Alertmanager → alert-receiver → OpenClaw → guardian → diary)
is valuable but **unbounded multi-tool investigation on every alert** is not
economically sustainable. Tool schemas every turn, multi-million-token sessions,
and hook models hard-coded to cloud burned operator quota without improving
outcomes on noisy alerts (e.g. idle switch ports).

## Goals

1. **Default cheap/safe**: most alerts do not open multi-tool LLM investigations.
2. **Explicit open**: operators expand auto-investigation as alert hygiene improves.
3. **Easy to change**: policy is data (YAML), not a code deploy.
4. **Observe plane independent of LLM**: metrics, pages, and diary write paths work when OpenClaw is down or budget is exhausted.
5. **Budgets**: hard caps on concurrent / hourly T2 and tokens per investigation.

## Non-goals

- Making a 9B local model the sole multi-step investigator.
- One claw per MCP tool.
- Replacing Grafana or removing interactive full-tool TUI sessions.
- Putting NetClaw `tokenOptimization` inside OpenClaw-validated `openclaw.json` (gateway rejects unknown keys — see `docs/TOKEN-OPTIMIZATION.md`).

## Investigation tiers

| Tier | Name | LLM | Tools | When |
|------|------|-----|-------|------|
| **T0** | Observe | None | None | Default; diary/Discord/metrics only |
| **T1** | Summarize | One-shot cheap | 0–1 read-only max | Optional cheap context for warnings |
| **T2** | Investigate | Multi-turn | Thin MCP profile + optional escalate | Allowlisted critical / low-cardinality only |
| **T3** | Human | Operator-gated | Full interactive tools | TUI / manual reinvestigate |

**Default product posture:** `default_tier: T0` with empty `allow_t2` until the
operator opens specific alertnames (nuclear / cost-controlled). As hygiene
improves, add `allow_t2` / `allow_t1` rows without code changes.

## Policy file (SoT)

**Path (host):** `~/.openclaw/investigation-policy.yaml`  
**Optional deploy seed:** `deploy/convergence/config/investigation-policy.example.yaml`

```yaml
version: 1
default_tier: T0

tiers:
  T0:
    llm: none
  T1:
    llm: summarize
    max_tools: 0
    max_completion_tokens: 4000
  T2:
    llm: investigate
    agent: alert            # thin tool profile agent id when available
    max_turns: 8
    max_tokens: 200000

# Explicit opens (empty = no multi-tool auto)
allow_t2: []
# Example when hygiene is ready:
# allow_t2:
#   - alertname: WanHardDown
#   - alertname: SwitchLinkLost
#     severity: critical

allow_t1: []

force_t0:
  - alertname: SwitchIdlePortsPresent
  - label: investigate=false

budgets:
  max_t2_per_hour: 3
  max_concurrent_t2: 2
  dedup_ttl_seconds: 1800

degrade:
  # When true or when budget trip: only T0/T1
  force_max_tier: null      # null | T0 | T1
```

### Resolution order

1. `force_t0` / Prom label `investigate=false` / cardinality high without explicit allow  
2. `allow_t2` match → T2 (if budgets admit)  
3. `allow_t1` match → T1  
4. else `default_tier`  
5. `degrade.force_max_tier` or budget trip may clamp downward  

Log every decision: `tier=T2 rule=allow_t2:WanHardDown` (or `default_tier`).

## Thin T2 tool profile (when T2 runs)

**Include:** prometheus (required), rag priors (compact), diary/Guardian write;  
optional UniFi or pfSense **by alert labels only**.

**Exclude from auto T2:** full Nautobot/golden-config suite, CML, GitHub, drawio,
markmap, RFC, wiki, ollama-mcp domain router, full pyATS (escalate to domain
member instead).

Interactive `main` may keep a rich MCP set; **hooks must not share it**.

## Domain claws (not per-tool claws)

Escalate deep work to existing Risk of Claws members (pyATS, secops, guardian,
viz) rather than loading every MCP on the border for every alert.

## Config coherence

| Item | Rule |
|------|------|
| Hook `model` | Follows policy / brain for T1–T2; not a stale cloud pin when operator chose local |
| Risk member models | Documented; toggle script may align with main when desired |
| `netclaw-token-optimization.json` | NetClaw-owned; never inside OpenClaw schema root |
| Mode presets | `observe-only` \| `triage-cheap` \| `investigate-critical` \| `interactive-full` map to policy defaults + MCP profiles |

## Metrics

alert-receiver (and optional HUD):

- `netclaw_investigations_by_tier{tier=T0\|T1\|T2}`
- existing suppressed / rate / concurrency counters
- budget trip counter

## Acceptance (independent test)

1. With `default_tier: T0` and empty `allow_t2`, a synthetic warning alert produces **no** multi-tool OpenClaw hook (T0 diary/Discord only if configured).  
2. Adding `allow_t2: [{ alertname: TestCritical }]` and reloading policy allows T2 for that name only.  
3. Budget trip clamps to T0/T1; observe plane (Prom, AM, convergence-api) remains up.  
4. Setup documents how to open T2 as hygiene improves (quickstart).

## Tasks

See `tasks.md` Phase 9 (T096+).
