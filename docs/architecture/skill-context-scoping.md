# Skill Context Scoping — Cutting Token Cost per Turn

## TL;DR

NetClaw ships ~192 skills. OpenClaw injects a one-line summary of **every** skill
into the system prompt on **every** turn. That skill index costs ~10–14K tokens
per turn, and because a chat API re-sends the whole prompt each turn, an
autonomous triage loop pays it 4–6 times per investigation.

We added a **skill selector** that scopes the runtime skills directory to only
the skills relevant to the current alert/query (plus a pinned safety core),
shrinking the injected index by 65–94% per turn with **no loss in tool-calling
quality**. We also added a **harness** that measures tool-calling behavior and
token burn against any model so the savings are verifiable, not theoretical.

- Selector: `scripts/skill-selector/select_skills.py`
- Harness:  `scripts/model-harness/triage_harness.py`

---

## The Problem

### What OpenClaw already does well (don't re-solve this)

OpenClaw uses **progressive disclosure** for skill *bodies*. Reading the runtime
loader (`skillflag/dist/core/list.js`, `paths.js`, `show.js`):

- `listSkills` scans the skills directory and builds an index from each skill's
  frontmatter `description` only.
- `showSkill` reads the full `SKILL.md` body **on demand**, when a skill is
  actually opened.

So the ~1.28 MB of full skill procedures is **not** front-loaded. That part is
already handled by the platform.

### What was NOT handled

`listSkills` emits **every** skill it finds in the directory — there is no
retrieval, allowlist, or enable flag. The directory contents *are* the index.
With 192 skills, that is a fixed ~10–14K-token block prepended to the system
prompt every turn, regardless of what the current task needs.

Because each turn of an agentic loop re-sends the full system prompt, the cost is
`index_tokens × turns`. Measured on DeepSeek V4-Pro (see
[baseline numbers](#measured-results)): a single InstanceDown triage burned
**56,763 tokens** with the full index, of which ~54.8K was input — dominated by
the repeated index.

---

## The Fix

### Integration point

OpenClaw's skill discovery is purely directory-based. The runtime skills
directory it scans is:

```
~/.openclaw/workspace/skills/
```

populated at install time from the repo's canonical catalog:

```
workspace/skills/            # canonical, all 192 skills, never mutated
```

Since the **directory contents are the index**, scoping the index = controlling
which skill directories are present in the runtime dir. No fork of OpenClaw is
needed.

> **Code-level gotcha:** OpenClaw's `listSkillDirs` uses `dirent.isDirectory()`,
> which returns `false` for symlinked directories. So the scoped set must be
> **real directories** — the selector copies them, it does not symlink.

> **⚠️ DEPLOYMENT REQUIREMENT — target must NOT be the canonical catalog.**
> The runtime skills dir (`--target`) and the canonical catalog (`--catalog`)
> **must be separate physical directories**. In some deployments
> `~/.openclaw/workspace/skills` is a **symlink to the repo's `workspace/skills`**
> — meaning target and catalog are the same directory. Applying scoping in that
> setup would **delete skills from the canonical catalog**. Before enabling
> scoping, replace the symlink with a real copy:
>
> ```bash
> rm ~/.openclaw/workspace/skills                       # remove the symlink
> cp -r /home/ubuntu/netclaw/workspace/skills ~/.openclaw/workspace/skills
> ```
>
> The selector enforces this with a hard guard: it **refuses to `--apply`** when
> `realpath(target) == realpath(catalog)` (exits non-zero, writes nothing). The
> receiver treats that as a fail-open and proceeds with the full catalog.

> **⚠️ Pin every skill you can't afford to lose.** Scoping removes any skill not
> selected or pinned. If a skill is untracked in git, removing it is
> unrecoverable from the repo. Keep `--pin` complete (safety + mandatory
> workflow skills) and commit your skills so git can restore them.

### How the selector works

`scripts/skill-selector/select_skills.py`:

1. Loads the full catalog from `workspace/skills/` (frontmatter only).
2. Builds a query string from a free-text `--query` and/or an `--alert` JSON
   (alertname, summary, platform, role, severity).
3. Ranks skills by relevance:
   - **embeddings** ranker (default when available) using
     `sentence-transformers` with the same `all-MiniLM-L6-v2` model the Memory
     MCP uses, so no new dependency footprint.
   - **keyword** ranker as automatic fallback (zero dependencies).
4. Selects the top-k plus a **pinned safety core** that is always kept
   regardless of the query (e.g. `alert-triage`, `gait-session-tracking`,
   `humanrail-escalation`, and device skills like `pyats-network`).
5. Materializes exactly that set into the runtime skills directory (real dirs),
   removing only skill subdirs and leaving any other files intact.

Safety: **dry-run by default**. Nothing is written without `--apply`. The full
catalog is restorable with `--restore-all`, and the canonical repo copy is never
touched.

### Where it runs

This is a **per-run** step, not a one-time setup. It runs automatically from the
alert-receiver, scoped to each incoming alert:

```
alert fires → receiver enriches with SoT → scope_skills_for_alert() → OpenClaw triage runs
```

The integration lives in `scripts/alert-receiver/server.py` (`scope_skills_for_alert`),
called from `process_alert` after device resolution and before `trigger_netclaw`.
It is **opt-in and fail-open**:

- Disabled by default (`SKILL_SCOPING_ENABLED=false`) — behavior is unchanged
  until you turn it on.
- On any selector error/timeout, it logs a warning and proceeds with the
  existing catalog — an investigation never fails because scoping failed.
- Resolved alerts skip scoping (they only post an all-clear).
- Scoping is serialized with a lock so concurrent alerts can't leave the shared
  skills directory half-written.
- **Restore-after-trigger**: after triggering (and a short delay so the fresh
  alert session has read the scoped dir), the receiver restores the full catalog
  so interactive sessions aren't left with the reduced set. A generation counter
  ensures that if a newer alert re-scoped in the meantime, the stale restore is
  skipped. Controlled by `SKILL_RESTORE_AFTER_TRIGGER` (default on) and
  `SKILL_RESTORE_DELAY` (default 8s).

Enable and tune it via the receiver's `.env` (see
`scripts/alert-receiver/.env.example`):

```bash
SKILL_SCOPING_ENABLED=true
SKILL_SELECTOR_PYTHON=/home/ubuntu/netclaw/.venv/bin/python   # needs pyyaml (+ optional sentence-transformers)
SKILL_SELECTOR_PINS=alert-triage,gait-session-tracking,memory-management,humanrail-escalation,pyats-network,pyats-troubleshoot
SKILL_SELECTOR_K=8
SKILL_SELECTOR_RANKER=keyword     # fast, no deps; use "auto"/"embeddings" for semantic ranking
```

To run it manually (or from another trigger), call the selector directly.

---

## Usage

```bash
# Dry run — see what would be selected for an alert (no writes)
python3 scripts/skill-selector/select_skills.py \
  --alert '{"alertname":"InstanceDown","device_platform":"iosxe"}'

# Scope the runtime dir for that alert, pinning device-investigation skills
python3 scripts/skill-selector/select_skills.py \
  --alert @/tmp/alert.json \
  --pin "alert-triage,gait-session-tracking,memory-management,humanrail-escalation,pyats-network,pyats-troubleshoot" \
  --k 8 --apply

# Free-text query
python3 scripts/skill-selector/select_skills.py \
  --query "bgp neighbor flapping on juniper core" --k 10 --apply

# Restore the full catalog (undo scoping)
python3 scripts/skill-selector/select_skills.py --restore-all --apply

# Machine-readable output (for wiring into the alert receiver)
python3 scripts/skill-selector/select_skills.py --alert @/tmp/alert.json --json
```

Key flags: `--catalog` (source, default repo), `--target` (runtime dir),
`--k`, `--pin`, `--ranker {keyword,embeddings,auto}`, `--apply`,
`--restore-all`, `--json`.

---

## Verifying with the Harness

`scripts/model-harness/triage_harness.py` runs a realistic triage loop with mock
MCP tools (Prometheus, pyATS, Loki, Alertmanager, Discord) against any Ollama
model, and reports per-turn + total token burn and tool-calling behavior.

```bash
# Inspect the assembled prompt + token estimate, no model call
python3 scripts/model-harness/triage_harness.py --dry-run --skill-index full

# Measure a full-catalog run (baseline)
python3 scripts/model-harness/triage_harness.py --scenario instance_down --skill-index full

# Measure a scoped run (point at a scoped dir produced by the selector)
python3 scripts/model-harness/triage_harness.py \
  --scenario instance_down --skill-index full --skills-dir /path/to/scoped/skills
```

Endpoint/model default to the local Ollama proxy via `OLLAMA_BASE_URL` (which
forwards `*:cloud` models to Ollama Cloud). The daemon must be authenticated
(`ollama signin` on the host).

---

## Measured Results

Model: `deepseek-v4-pro:cloud` via the local Ollama proxy. Scenario:
`InstanceDown` (Cisco IOS-XE switch). One triage run each.

| Metric                 | Full catalog (192) | Scoped (8) | Change |
|------------------------|-------------------:|-----------:|-------:|
| Injected skill index   | ~10.6K tokens      | ~0.6K      | −94%   |
| System prompt (total)  | ~13.8K tokens      | ~3.8K      | −73%   |
| Turn-1 input tokens    | 13,080             | 4,536      | −65%   |
| Total run tokens       | 56,763             | 37,629     | −34%*  |
| Turns                  | 4                  | 6          | —      |
| Hallucinated tools     | 0                  | 0          | —      |
| Posted final report    | yes                | yes        | —      |

\* The **per-turn** reduction (65–73%) is deterministic. **Total-run** savings
are larger on average (34–64% across our runs) but vary with how many turns the
model chooses to take — input tokens dominate total cost, so fewer/leaner turns
compound the win. This particular scoped run happened to take 6 turns vs 4.

**Tool-calling quality held**: with device skills pinned, the model called
`pyats_run_command` correctly and produced a valid triage report. Zero
hallucinated tools across all runs.

---

## Caveats & Tuning

- **Under-selection is the failure mode to watch.** If the ranker misses a skill
  the task needs, the model loses that capability for the run. Mitigations:
  raise `--k`, or add commonly-needed skills to `--pin`. For the triage path we
  pin `pyats-network` and `pyats-troubleshoot`.
- **This is not a cost play on a flat-rate plan.** On the $20 Ollama Pro plan
  you pay a fixed fee, not per token — so scoping saves **quota** (the 5-hour
  session and 7-day weekly usage caps) and **latency**, not dollars. It becomes
  a dollar play only on per-token billing.
- **Retrieval quality should be sanity-checked** against real alert types before
  relying on autonomous scoping. Run the selector in dry-run and eyeball the
  selected set for your common scenarios.
- **Embeddings ranker** requires `sentence-transformers` (already present via the
  Memory MCP). Without it, the keyword ranker is used automatically. The receiver
  defaults to the keyword ranker to keep the webhook hot path fast and
  dependency-light; set `SKILL_SELECTOR_RANKER=auto` for semantic selection.
- **Concurrent alert bursts share one skills directory.** Scoping is serialized
  to prevent partial writes, and a generation counter prevents a stale restore
  from clobbering a newer alert's scope. Because OpenClaw resolves skills
  per-run from this single directory, a fresh alert session reads whatever is on
  disk at session start — so the receiver scopes just before triggering and
  restores shortly after. Under exact-simultaneous alert + interactive load the
  window is still shared; true isolation would need per-session skill dirs.

**Runtime read timing (verified):** OpenClaw builds the skill snapshot per run
(`resolveSkillsPromptForRun` → `buildWorkspaceSkillSnapshot` → live `readdirSync`,
no startup cache), and each alert spawns a fresh session. So scoping the
directory just before triggering is reliably picked up by that alert's
investigation, with no gateway restart needed.

---

## Files

| Path | Purpose |
|------|---------|
| `scripts/skill-selector/select_skills.py` | Scope runtime skills dir by relevance |
| `scripts/model-harness/triage_harness.py` | Measure token burn + tool-calling |
| `scripts/alert-receiver/server.py` | Auto-scopes per alert (`scope_skills_for_alert`) |
| `scripts/alert-receiver/.env.example` | Scoping config (`SKILL_SCOPING_*`) |
| `docs/architecture/skill-context-scoping.md` | This document |
