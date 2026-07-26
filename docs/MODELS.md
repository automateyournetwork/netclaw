# Models: brain, alert triage, and how to change them

**Audience:** operators who want one place to pick LLM models without hand-editing
`openclaw.json`.  
**Related:** [ENV-AND-LAYOUT.md](./ENV-AND-LAYOUT.md) · [CONVERGENCE.md](./CONVERGENCE.md) ·
[TOKEN-OPTIMIZATION.md](./TOKEN-OPTIMIZATION.md) · [specs/067-convergence/investigation-policy.md](../specs/067-convergence/investigation-policy.md)

---

## Short answer

| Question | Answer |
|----------|--------|
| Where do I set models? | **Repo `.env`** (`/path/to/netclaw/.env`) — primary SoT |
| How do I apply? | `./scripts/netclaw-apply-models.sh apply` **or** HUD **Convergence → Models** |
| Does editing `.env` alone change the gateway? | **No** — you must **apply** (script or HUD button) so live config is updated and the gateway restarts |
| Where do investigations get their model? | `NETCLAW_ALERT_TRIAGE_MODEL` → hook `alert` + agent id `alert` |
| Where does chat / TUI get its model? | `NETCLAW_BRAIN_MODEL` → `agents.defaults.model` |

---

## Source of truth (`.env`)

Preferred operator file:

```text
netclaw/.env
```

(Also mirrored into `~/.openclaw/.env` by the apply script so other tools see the same keys.)

### Variables

| Variable | Used for | Example |
|----------|----------|---------|
| **`NETCLAW_BRAIN_MODEL`** | Interactive **main** agent / HUD chat / Border defaults | `anthropic/claude-sonnet-5` |
| **`NETCLAW_ALERT_TRIAGE_MODEL`** | **T2 auto-investigations** (`hooks.mappings` path `alert`, agent `alert`) | `anthropic/claude-haiku-4-5-20251001` |
| **`NETCLAW_ALERT_FALLBACK_MODEL`** | Optional alert-agent fallback if primary fails | `ollama/glm-5.2:cloud` |
| **`OLLAMA_BASE_URL`** | Ollama API base (local LAN or `https://ollama.com`) | synced to gateway env |
| **`OLLAMA_API_KEY`** | Ollama Cloud (or compatible) key | synced to gateway env |

Use **provider/model** form:

```text
anthropic/claude-sonnet-5
anthropic/claude-haiku-4-5-20251001
ollama/deepseek-v4-flash:cloud
ollama/voytas26/openclaw-qwen3vl-8b-opt
```

Bare names (no `/`) are prefixed with `ollama/` by the apply script.

### What apply writes

`./scripts/netclaw-apply-models.sh apply` projects SoT into:

| Target | Fields |
|--------|--------|
| `~/.openclaw/openclaw.json` | `agents.defaults.model.primary`, `agents.list[alert].model`, `hooks.mappings[alert].model` (+ `agentId=alert` when present) |
| `~/.openclaw/gateway.systemd.env` | `NETCLAW_*_MODEL`, `OLLAMA_*` so the gateway process sees them |
| `netclaw/.env` + `~/.openclaw/.env` | Kept in sync for model keys when using `set` / presets / HUD |

Then restarts: `systemctl --user restart openclaw-gateway.service`.

**Do not** put NetClaw-only keys inside OpenClaw’s validated schema root (e.g. `tokenOptimization` — see TOKEN-OPTIMIZATION.md). Model **ids** live under normal OpenClaw `agents` / `hooks` keys.

---

## CLI

```bash
cd /path/to/netclaw

# See SoT vs live openclaw.json
./scripts/netclaw-apply-models.sh show

# After editing netclaw/.env
./scripts/netclaw-apply-models.sh apply

# One-shot set (writes .env then apply + restart)
./scripts/netclaw-apply-models.sh set \
  --brain anthropic/claude-sonnet-5 \
  --alert anthropic/claude-haiku-4-5-20251001

# Presets
./scripts/netclaw-apply-models.sh preset local         # local 9B both
./scripts/netclaw-apply-models.sh preset cloud-flash   # deepseek-v4-flash both
./scripts/netclaw-apply-models.sh preset split         # local brain + cloud alert
./scripts/netclaw-apply-models.sh preset anthropic     # Sonnet brain + Haiku 4.5 alert

# Apply without restart (rare)
./scripts/netclaw-apply-models.sh apply --no-restart
systemctl --user restart openclaw-gateway.service
```

Always restart via **systemd**, not `kill -HUP` on the node process.

---

## HUD (Convergence tab)

1. Open Visual HUD → **CONVERGENCE** (HOME).  
2. Sub-tab **Models**.  
3. Edit Brain / Alert / Fallback **or** click a preset (`split`, `cloud-flash`, `local`).  
4. **Apply & restart gateway**.  

That calls `POST /api/models` on the HUD host process (not Docker convergence-api), which updates `.env` and runs the same apply script.

Live panel shows what is currently in `openclaw.json` (defaults vs hook vs alert agent).

---

## Recommended pairings

### Anthropic: Sonnet brain + Haiku alert (good default when Anthropic is funded)

| Role | Model id | Why |
|------|----------|-----|
| **Brain** | `anthropic/claude-sonnet-5` | Strong instruction-following, routing, multi-step chat; large context (1M in this install’s registry). Good Border / interactive model. |
| **Alert triage** | `anthropic/claude-haiku-4-5-20251001` | Structured skill following + tool calls at **much lower cost** than Sonnet for high-volume hooks. Enough for thin T2 (Prom/RAG/pfSense/UniFi). |

```bash
./scripts/netclaw-apply-models.sh set \
  --brain anthropic/claude-sonnet-5 \
  --alert anthropic/claude-haiku-4-5-20251001
```

**Caveats**

- Use the **real API id** for Haiku: `claude-haiku-4-5-20251001` — not a guessed `claude-haiku-3.5` (that failed in production; see `docs/blog/2026-07-21-alert-investigation-debugging.md`).
- Ensure `ANTHROPIC_API_KEY` is set in the env the **gateway** loads (`~/.openclaw/gateway.systemd.env` and/or apply from `.env` that already has the key for other tools). Apply currently syncs Ollama + model keys; Anthropic key must already be present for the gateway (usually already is on this host).
- T2 is still gated by **investigation policy** (`allow_t2`). Cheap Haiku does not mean “investigate everything” — keep nuclear default or investigate-critical allowlists.
- Thin **alert** agent still strips the full MCP zoo; Haiku is a good fit for that slim surface. Deep pyATS/secops work should still escalate to domain members.

### Ollama Cloud (good when Anthropic quota is tight)

| Role | Model id | Why |
|------|----------|-----|
| Brain and/or alert | `ollama/deepseek-v4-flash:cloud` | Large context, previously proven on this host for investigations; set `OLLAMA_BASE_URL=https://ollama.com` + `OLLAMA_API_KEY`. |
| Fallback | `ollama/glm-5.2:cloud` | Optional secondary |

```bash
./scripts/netclaw-apply-models.sh preset cloud-flash
# or split: local chat + cloud investigate
./scripts/netclaw-apply-models.sh preset split
```

### Local-only (offline / zero cloud burn)

| Role | Model id | Why |
|------|----------|-----|
| Both | `ollama/voytas26/openclaw-qwen3vl-8b-opt` | Free local; **often fails multi-tool T2** (empty / length stops). Prefer T0 policy or expect weak investigations. |

```bash
./scripts/netclaw-apply-models.sh preset local
```

### Split cost posture (recommended hybrid)

| Role | Model |
|------|--------|
| Brain | Local 9B **or** Haiku |
| Alert T2 | Haiku **or** `deepseek-v4-flash:cloud` |

Keeps interactive chat cheap while investigations stay capable.

---

## Alert loop (efficient T2)

Autonomous T2 path (host agent + Docker diary):

1. Docker AM / synthetic → host `alert-receiver` → diary **POST** on Docker `:3080`  
2. OpenClaw hook `agentId=alert`, **`deliver=false`** (no Discord channel required)  
3. Border: `n2n_route` → **`n2n_task_wait`** → member `guardian-claw` investigates  
4. Member: Discord webhook + **PATCH same diary** (`NETWORK_GUARDIAN_URL` must match receiver)

Member env SoT: `migration-staging/members/guardian-claw/.env`  
Must use the same diary base URL as `services/alert-receiver/.env` (`http://127.0.0.1:3080` for Docker Convergence).

## How this relates to investigation policy (Phase 9)

Models control **which LLM** runs when an investigation is admitted.  
Policy controls **whether** an investigation is admitted (T0 / T1 / T2).

```text
Alertmanager → alert-receiver → policy tier
                                 ├─ T0: no multi-tool hook (no model burn)
                                 ├─ T1: cheap summary path
                                 └─ T2: hook → agent alert → NETCLAW_ALERT_TRIAGE_MODEL
```

Policy file: `~/.openclaw/investigation-policy.yaml`  
CLI: `./scripts/netclaw-investigation-policy.sh show|seed-observe-only|seed-investigate-critical`  
Thin tools: `./scripts/netclaw-alert-agent-profile.sh apply`

---

## Checklist when models “don’t change”

1. Did you **apply** after editing `.env`? (`show` still shows old live values otherwise.)  
2. Is the gateway **active**? `systemctl --user status openclaw-gateway`  
3. Is the **hook** model set, not only defaults? Hook can differ from main — that is intentional.  
4. For Anthropic: is the id in `models.providers.anthropic.models[]` and is `ANTHROPIC_API_KEY` available to the gateway?  
5. For Ollama Cloud: `OLLAMA_BASE_URL` + `OLLAMA_API_KEY` in `gateway.systemd.env` after apply.  
6. In-flight sessions keep their old model; only **new** runs pick up the change.

---

## See also

- Script: [`scripts/netclaw-apply-models.sh`](../scripts/netclaw-apply-models.sh)  
- HUD: Convergence → **Models** · `GET/POST /api/models`  
- Spec quickstart: [`specs/067-convergence/quickstart.md`](../specs/067-convergence/quickstart.md)  
- Alert cost / thin tools: [`docs/architecture/convergence-context/alert-agent-tools-and-tokens.md`](./architecture/convergence-context/alert-agent-tools-and-tokens.md)  
