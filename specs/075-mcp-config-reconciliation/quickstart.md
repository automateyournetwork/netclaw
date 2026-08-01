# Quickstart: Adding an MCP Integration

**Feature**: 075-mcp-config-reconciliation | **Date**: 2026-07-30

This is the procedure roadmap items **R1–R24** each follow (FR-023). It is drafted here and ships as
`docs/ADDING-AN-MCP.md`.

The goal it serves: **all registered integrations must be obtainable by someone installing their own
NetClaw risk.** Every step exists because omitting it has broken that at least once.

---

## Before you start

Decide which kind of integration this is, because it determines whether it gets a config entry at
all:

| Kind | Gets a `config/openclaw.json` entry? | Example |
|---|---|---|
| Vendored, pre-registered | **Yes** | `suzieq-mcp`, `memory-mcp` |
| Installed on demand (pip/npm/Docker) | No — goes in `EXTERNAL_INTEGRATIONS` | pyATS, NetBox, nmap |
| Remote / OAuth | No — external, reason `remote/OAuth` | Zscaler, ThousandEyes official |
| Bundled into a skill's runtime | No — external, reason `skill-bundled` | Computer Use |

Getting this wrong is the most common error. "Not in the config" is a legitimate, documented state
for 60 of NetClaw's 149 integrations — it does not mean forgotten.

---

## Steps

### 1. Vendor or identify the server

If vendoring under `mcp-servers/<name>/`, add a `.gitignore` negation entry — the repo ignores
broadly and new server directories are otherwise silently untracked.

### 2. Register it (pre-registered kinds only)

Add to `config/openclaw.json`. **Use repo-relative paths:**

```json
"example-mcp": {
  "command": "python3",
  "args": ["-u", "mcp-servers/example-mcp/server.py"]
}
```

Do **not** hardcode an absolute path. Three Nautobot entries did exactly that
(`/home/ubuntu/netclaw/...`) and were broken for every installer, including the maintainer's own
machine, until this feature found them. `scripts/normalize-mcp-cwd.py` supplies the correct absolute
`cwd` at install time for each user's own machine.

Do **not** pack arguments into `command` (`"python3 -m foo"`). Use `command` plus `args`.

System interpreters (`/usr/bin/python3`) are acceptable — they are portable. Anything under `/home/`
or `/Users/` is not.

### 3. Record its state (external kinds only)

Add the human-readable name to `EXTERNAL_INTEGRATIONS` in `scripts/verify-inventory-counts.py`,
**in the same PR**, with a comment giving the reason. Omitting this now causes a loud failure naming
your directory rather than silent undercounting.

### 4. Add installer coverage

- `scripts/lib/catalog.sh` — one entry, `"id|Category|Name|Description"`
- `scripts/lib/install-steps.sh` — one `component_install_<id>()` function, `-` becoming `_`

If your integration registers several servers under one selectable component (as Check Point does
with 15), declare the grouping in `scripts/verify-catalog-coverage.py` rather than adding 15 catalog
entries. If your server key does not reduce to your catalog id by stripping `-mcp`, add an explicit
alias. Nineteen servers were failing the coverage check purely for want of 8 such declarations.

### 5. Update the documentation surfaces

Per Constitution Principle XI:

- `README.md` — description, architecture, **and the counts**
- `SOUL.md` — capability summary and **the counts**
- `workspace/skills/<name>/SKILL.md` — if adding a skill
- `.env.example` — new variables, names and descriptions only, never values
- `TOOLS.md` — infrastructure reference
- `mcp-servers/<name>/README.md` — tools, env vars, transport, install

The counts are the part everyone forgets: they were wrong in 9 places across two files.

### 6. Verify

```bash
scripts/reconcile-mcp.py
```

Exit `0` means reconciled. Non-zero names exactly what is missing. Run this **before** pushing — CI
runs the same command and hard-fails on it.

To check one surface while iterating:

```bash
scripts/reconcile-mcp.py --surface catalog
scripts/reconcile-mcp.py --surface portability
```

To confirm a skill's chain resolves:

```bash
scripts/trace-skill.py <skill-name>
```

### 7. Confirm installability

The property that actually matters is that a *fresh user* can obtain this. `reconcile-mcp.py`
verifies it statically: installer coverage exists and no path is machine-specific. No running agent
is needed, and your own live gateway's contents are irrelevant.

---

## Checklist

```
[ ] Integration kind decided (pre-registered / on-demand / remote / skill-bundled)
[ ] Vendored dir added with .gitignore negation (if vendoring)
[ ] config/openclaw.json entry with repo-relative paths, command and args separate (if pre-registered)
[ ] EXTERNAL_INTEGRATIONS entry with reason (if external)
[ ] catalog.sh entry
[ ] install-steps.sh component_install_<id>()
[ ] Grouping rule or alias declared if the key doesn't reduce to the catalog id
[ ] README.md updated INCLUDING counts
[ ] SOUL.md updated INCLUDING counts
[ ] SKILL.md created (if adding a skill)
[ ] .env.example updated (names only)
[ ] TOOLS.md updated
[ ] mcp-servers/<name>/README.md created
[ ] scripts/reconcile-mcp.py exits 0
[ ] GAIT session logged
```

---

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `catalog: X: no matching catalog id` | Key doesn't reduce to the catalog id by stripping `-mcp` | Add an alias or prefix group |
| `portability: X: machine-specific` | Absolute path under `/home/` | Make it repo-relative |
| `vendored: mcp-servers/X: no recorded state` | Vendored but neither registered nor recorded external | Do one or the other |
| `docs: README.md:N: claims 198` | Counts not updated | Update them |
| `docs: could not locate 'installer prose'` | Prose was reworded so the check can no longer find it | Restore a matchable phrasing or update the pattern |
| Server not visible after install | Missing `cwd` | Confirm `normalize-mcp-cwd.py` ran |
