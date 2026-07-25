# Alert agent tools, history, and token burn

**Status:** Architecture notes from live investigation (2026-07)  
**Scope:** Convergence monitoring → alert-receiver → OpenClaw hooks → Risk of Claws  
**Related:**

- [`docs/TOKEN-OPTIMIZATION.md`](../../TOKEN-OPTIMIZATION.md)
- [`docs/CONVERGENCE-ALERT-SAFETY.md`](../../CONVERGENCE-ALERT-SAFETY.md)
- [`docs/architecture/skill-context-scoping.md`](../skill-context-scoping.md)
- Phase 8 device telemetry / investigation pipeline

This document captures findings and design recommendations so they survive
context loss. It is not a full implementation plan.

---

## 1. Problem statement

Running Convergence + auto-investigation burns large volumes of LLM tokens
(especially Ollama cloud / DeepSeek flash historically). Symptoms:

- Lifetime counters on the host showed **~1.7B+ input tokens** on
  `deepseek-v4-flash:cloud` alone via `openclaw-token-exporter`.
- Single `hook:alert:*` sessions recorded **~1–6M input tokens** per
  investigation in session metadata.
- Trajectories of **~8–10 MB** with only ~150 lines (fat tool payloads, not
  chatty prose).
- Operators expected **GCF / tokenOptimization / HUD token tracker** to
  control or display this; much of that path was not live.

Secondary incident: high-cardinality SNMP alerts (`SwitchInterfaceDown` on
idle ports) multiplied investigations × N fingerprints and nearly OOM’d the
host via full MCP fan-out per session.

---

## 2. Investigation findings

### 2.1 Where models actually live

Switching “my OpenClaw model” does **not** retarget everything.

| Surface | Config home | Typical model (pre-fix) |
|---------|-------------|---------------------------|
| TUI / HUD / main agent | `~/.openclaw/openclaw.json` | Operator-chosen primary |
| Alert investigations (hooks) | `hooks.mappings[].model` | Often hard-coded **cloud** (e.g. deepseek-v4-flash:cloud) |
| Risk of Claws (guardian) | `~/.openclaw-byrns-risk-guardian-claw/openclaw.json` | Separate primary + cloud routes |
| Other iN2N members | `~/.openclaw-byrns-risk-*` | Separate homes |

**Implication:** Local brain on main does not stop investigation burn if hooks
and Risk claws still call cloud.

### 2.2 What multi-turn history actually costs

Each agent step roughly re-sends:

| Chunk | Typical size | Replace with RAG? |
|-------|----------------|-------------------|
| System + skills + policies | Large, fixed | Partial (skill scoping) |
| **Full MCP tool schemas** | Huge every turn | **No** |
| Recent tool calls + **JSON results** | Grows fast | Compress / truncate / summarize |
| Conversation turns | Grows over the run | **Yes for old turns** |
| Prior investigations / inventory dumps | Can be huge | **Yes — ideal for RAG** |

**Conclusion:** Giant burn is usually **tools + results + system**, with
history stacked on top — not “chat history alone.”

### 2.3 GCF / tokenOptimization / token tracker

| Mechanism | Reality (2026-07 investigation) |
|-----------|----------------------------------|
| Repo `config/openclaw.json` `tokenOptimization` | Documented intent; **not** a native OpenClaw schema key |
| Live `~/.openclaw/openclaw.json` | Putting `tokenOptimization` there causes **gateway exit 78** (invalid config) |
| Canonical NetClaw flags | `~/.openclaw/netclaw-token-optimization.json` (and risk homes) |
| GCF serializers (`src/netclaw_tokens`) | Real library; only helps when MCP servers call it |
| Most MCP tool results | Still raw JSON re-injected every turn |
| HUD “Token Tracker” 3D orb | **Catalog card only** — not a live meter |
| `openclaw-token-exporter` `:9110` | **Does** count tokens for Prom/Grafana; now also HUD footer |

### 2.4 Alert-path failure modes that multiplied burn

1. **High-cardinality alerts** (admin-up + oper-down per idle port) → one
   OpenClaw session per fingerprint.
2. **Eager `bundle-tools`** → full MCP set (~20–26 servers) per session.
3. **main-session-restart-recovery** after OOM → respawns interrupted
   `hook:alert:*` sessions and re-pays tool load.
4. **Hook model pinned to cloud** while interactive model was local.

Defense-in-depth for (1) is documented in
[`CONVERGENCE-ALERT-SAFETY.md`](../../CONVERGENCE-ALERT-SAFETY.md).

---

## 3. Multi-turn history vs RAG

### 3.1 Short answer

**RAG can replace long / cross-session history** for recall of prior facts.  
**RAG cannot replace working memory** for the current tool loop, and it does
**not** shrink tool-schema cost.

### 3.2 Recommended hybrid

```text
Active window (last 2–6 turns + last tool results, size-capped)
        +
RAG retrieve top-k facts (device, alertname, prior root cause)
        +
Compact summary of older steps in this run
```

| Use case | Prefer |
|----------|--------|
| Prior investigations, runbooks, “this port is always idle” | **RAG / memory** |
| In-session “use the interfaces from the last tool call” | **Short window** |
| Mid-run state after many tools | **Compaction summary** |
| Tool JSON bloat | **GCF / truncate**, not more history |

### 3.3 Investigation session policy (recommended)

- **New session per alert fingerprint** (already: `hook:alert:{{fingerprint}}`).
- **Do not** aggressively restart-recover half-finished hook sessions after crash.
- Inject **RAG priors** at kickoff (alert-receiver already searches prior cases).
- Cap OpenClaw session growth: short window + mid-run summary every N tool steps.

---

## 4. Slimming tools without ruining the alert agent

### 4.1 Do **not** create one claw per tool

Wrong granularity:

- Process/memory overhead multiplies.
- Orchestration and routing become the product.
- Correlation across metrics + logs + device state needs one mind holding
  short working state.

### 4.2 Do use **domain claws** + thin orchestrator

```text
┌─────────────────────────────────────────┐
│  Alert orchestrator (thin tools)        │  ← hook:alert always starts here
│  Prom · logs · light inventory · diary  │
└───────────────┬─────────────────────────┘
                │ escalate when needed
     ┌──────────┼──────────┬──────────────┐
     ▼          ▼          ▼              ▼
  pyATS      secops    guardian-claw     viz
  member     member    (risk)            member
```

This matches existing **Risk of Claws / iN2N members** and
**domain-expert-delegation**, not “MCP method = process.”

### 4.3 Minimal kit for the alert orchestrator

Enough for most Convergence / home alerts:

| Keep | Why |
|------|-----|
| Prometheus / metrics | Confirm alert, trends |
| Loki / logs (if present) | Correlate |
| Light inventory / devices | Name ↔ IP, role |
| Diary / Guardian write | Record outcome |
| Label-driven UniFi or pfSense | Only when alert labels require |

**Usually not on the alert agent (interactive TUI may keep these):**

- Full Nautobot CRUD / golden config suite  
- CML / lab  
- GitHub, drawio, markmap, RFC, Wikipedia  
- Full pyATS unless escalated  
- Every Nautobot MCP variant at once  

### 4.4 Profile by alert family (allowlist, not one claw per tool)

| Alert family | Orchestrator tools | Escalate to |
|--------------|--------------------|-------------|
| WAN / blackbox | Prom | edge / pfSense if needed |
| Wi‑Fi / UniFi | UniFi + Prom | — |
| Switch link lost | Prom + light device | pyATS member |
| Security / blocks | pfSense + logs | secops / threatintel |
| Exporter down | Prom only | — |

Implementation options:

- Dedicated OpenClaw **agent id** for hooks with a minimal `mcp.servers` set.
- Or **tool allow/deny policy** on the hook path while `main` stays rich.
- **Skill scoping** (already) for skill docs; **tool scoping** for schemas.

### 4.5 Rule of thumb

| Granularity | Verdict |
|-------------|---------|
| One claw per **tool** | Too fine — don’t |
| One claw per **domain** | Good (Risk of Claws pattern) |
| Thin **alert orchestrator** + escalate | Best cost / quality for monitoring |
| Same full MCP zoo for TUI and alerts | Current pain |

---

## 5. Risk of Claws placement

Keep **capability members**, not per-tool claws:

| Member | Owns |
|--------|------|
| guardian-claw | Triage ownership, risk narrative, diary coordination |
| pyats | Device CLI / operational state |
| secops | Security tooling |
| viz | Topology / visual |
| cml | Lab only |

Interactive TUI/HUD may use a richer MCP set on `main`.  
**Hooks must not share that full set.**

Model routing for Risk homes is **independent** of main; point
`agents.defaults.model` and Ollama base URL at local when cloud quota is
exhausted. Domain `ROUTE_*` / ollama-mcp env in member homes must not silently
re-target **ollama-cloud**.

---

## 6. Token visibility (what was missing vs what exists)

| Path | Role |
|------|------|
| `openclaw-token-exporter` `:9110` | Session `.jsonl` → Prom counters |
| HUD `/api/tokens/summary` + footer strip | Lifetime + last turn + opt flags |
| Chat reply token footer | Per-turn when OpenAI-compat `usage` present |
| `netclaw-token-optimization.json` | NetClaw flags (GCF default, footer policy) |
| token-tracker skill | Agent-facing instructions; not a HUD widget |
| GCF in MCP servers | Only where implemented (`gcf_dumps`, etc.) |

See [`docs/TOKEN-OPTIMIZATION.md`](../../TOKEN-OPTIMIZATION.md) for the
OpenClaw schema constraint (gateway exit 78 if `tokenOptimization` is stuffed
into `openclaw.json`).

---

## 7. Recommended end state (checklist)

**Alert path**

- [ ] Dedicated alert tool profile (4–6 MCPs max) or strict deny-list  
- [ ] Hook `model` = local brain (not hard-coded cloud)  
- [ ] No high-cardinality investigate=true alerts (link-lost edge detect only)  
- [ ] Admission control on alert-receiver (concurrency, rate, dedup)  
- [ ] RAG priors injected; short active window; no aggressive hook-session recovery  

**Risk of Claws**

- [ ] Domain members only; local primary when desired  
- [ ] No silent ollama-cloud routes for all domains  

**Tokens**

- [ ] NetClaw token-optimization file present  
- [ ] Exporter + HUD strip live  
- [ ] GCF on high-volume MCP tool results (Prom, Nautobot, pyATS dumps)  
- [ ] Interactive `main` may stay rich; hooks stay thin  

**History**

- [ ] Hybrid: short window + compaction + RAG for prior cases  
- [ ] Do not treat full session replay as the default for investigations  

---

## 8. Implementation priority (suggested)

1. **Tool profile for hooks** (largest token win; quality preserved via escalate).  
2. **Model alignment** (hooks + Risk claws → same local brain as main when desired).  
3. **History policy** (window + RAG priors + no OOM recovery of hook farms).  
4. **GCF on hot MCP paths** (result size, not schema).  
5. **Optional:** mid-run “state so far” summary every N tool steps.

---

## 9. Decisions (summary)

| Decision | Choice |
|----------|--------|
| One claw per tool? | **No** |
| Domain claws? | **Yes** (existing Risk of Claws shape) |
| Alert agent tools? | **Thin allowlist + escalate** |
| Giant chat history? | **Replace long history with RAG + summary; keep short working window** |
| Same MCP set for TUI and alerts? | **No** |
| tokenOptimization in openclaw.json? | **No** — NetClaw-owned file only |

---

## 10. Changelog

| Date | Note |
|------|------|
| 2026-07-25 | Initial capture from live incident + architecture discussion (tools, RAG, tokens, Risk of Claws). |
