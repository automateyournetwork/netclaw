# Adding an MCP Integration

**Established by**: spec 075 (`specs/075-mcp-config-reconciliation/`) | **Date**: 2026-07-30

**This is the procedure every roadmap item R1–R24 follows.** Established by spec 075 after
reconciliation found three integrations that had shipped broken for every installer, nineteen that
failed the coverage check for want of a declaration, and nine wrong capability counts.

The goal it serves: **all registered integrations must be obtainable by someone installing their own
NetClaw risk.** Every step exists because omitting it has broken that at least once.

---

## Before you start — the spec comes first

**Constitution Principle XVI**: `specify → plan → task → implement`, and *"ad-hoc or undocumented
feature additions ('cowboy coding') are not permitted."*

Your spec directory needs `spec.md`, `plan.md`, a task list, and `research.md` **before**
implementation. `scripts/verify-spec-artifacts.py` enforces it and CI runs it.

A combined `plan.md` carrying a `## Tasks` section satisfies the task requirement — spec 084 does
exactly that, deliberately. Do not create a stub `tasks.md` to satisfy the checker.

> **This was not being followed.** An audit on 2026-08-05 found **ten consecutive specs (087–096)**
> shipped with `spec.md` alone, against 72 of 86 that carried the full set. The drift was
> self-reinforcing: an author checking the three most recent specs saw `spec.md` alone and concluded
> that was the convention. It was the drift. The gate exists so the next person cannot make the same
> inference.

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
scripts/reconcile-mcp.py --surface startup      # actually launches your server
scripts/reconcile-mcp.py --surface packages     # npx/uvx packages your skill invokes
```

The `startup` surface (spec 088) launches every registered stdio server and reports the ones that
cannot start. Use it on your own server before pushing:

```bash
scripts/check-server-startup.py --only <your-server-key>
```

A **timeout is success** — a server that imports cleanly and then blocks reading stdio is behaving
correctly. Only a fatal startup error (missing module, absent entry point, syntax error) is a
finding. This surface currently reports as `WARN` rather than failing the build, because seven
pre-existing servers cannot start and two of them need an SDK that is not publicly distributable;
see `specs/088-server-startup-check/spec.md` for the exit condition.

To confirm a skill's chain resolves:

```bash
scripts/trace-skill.py <skill-name>
```

### 7. Confirm installability

The property that actually matters is that a *fresh user* can obtain this — and that what they
obtain can actually run. `reconcile-mcp.py` checks both:

- **Statically** (`catalog`, `docs`, `portability`, `dependencies`): installer coverage exists, no
  path is machine-specific, counts agree, pins are bounded.
- **Dynamically** (`startup`, spec 088): your server is launched and must not die on import.

No running agent is needed, and your own live gateway's contents are irrelevant. The static surfaces
alone were not enough: they compare declarations against each other, so for four specs' worth of
history they all passed while seven registered servers could not start.

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
[ ] check-server-startup.py --only <key> reports no finding (timeout is success)
[ ] If a skill invokes a package via npx/uvx: python3 scripts/check-package-references.py --refresh
[ ] .env.example updated (names only)
[ ] TOOLS.md updated
[ ] mcp-servers/<name>/README.md created
[ ] scripts/reconcile-mcp.py exits 0
[ ] GAIT session logged

--- only if an iN2N member should use it (see the section below) ---
[ ] Server registered in the MEMBER's own config (OPENCLAW_CONFIG_PATH)
[ ] Credentials added to the member's .env slice
[ ] SKILL.md synced into the member's workspace
[ ] N2N_MEMBER_SCOPE updated in .env AND the member.scope column in federation.db
[ ] scripts/in2n-profiles.py prefixes match SKILL names (not tool names)
[ ] systemctl --user restart netclaw-mesh.service  (Border caches the roster)
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

---

## If an iN2N member should use it (five more artifacts)

**Established by spec 080 (R3), after three live Slack attempts failed with
`IN2N_ERR_NO_CAPABLE_MEMBER` on a server that was correctly registered.**

Steps 1–7 above wire a server into the **Border Claw**. They do nothing for a member.

**An iN2N member is a separate claw.** It has its own config, its own `.env`, its own workspace, and its
capabilities are recorded in the Border's database — not read from the repo at request time. Registering a
server on the Border makes it invisible to every member.

Worse, the Border **caches the member roster in memory**, so even a correct database row does not take
effect until the mesh daemon reloads.

### The five

**1. Register the server in the member's own config**

```bash
# The member's config path is in its .env as OPENCLAW_CONFIG_PATH
grep OPENCLAW_CONFIG_PATH migration-staging/members/<member>/.env
```

Add the same `mcp.servers` entry you added to the Border's config, including `cwd`. A member config
typically contains only `memory-mcp` until you do this.

**2. Add credentials to the member's `.env`**

The member does not inherit the Border's environment. Its `.env` is a least-privilege slice, and the
integration's variables must be added to it explicitly.

**3. Sync the skills into the member's workspace**

```bash
cp workspace/skills/<skill>/SKILL.md ~/.openclaw-<risk>-<member>/workspace/skills/<skill>/
```

**4. Widen the member's scope — in TWO places**

`N2N_MEMBER_SCOPE` in the member's `.env` **and** the `scope` column of the `member` table in
`~/.openclaw/n2n/federation.db`. The `.env` governs what the member announces; the database is what
`n2n_route` consults when deciding who can answer.

If the skill belongs to a profile, update `scripts/in2n-profiles.py` so a future regeneration keeps it.
**`prefixes` there matches SKILL NAMES, not tool names** — setting it to tool prefixes silently resolves to
zero specialty skills, which is worse than leaving it alone.

```bash
python3 scripts/in2n-profiles.py scope <profile>   # verify it resolves to the skills you expect
```

**5. Restart the mesh daemon**

```bash
systemctl --user restart netclaw-mesh.service
```

Without this the Border keeps routing against the stale in-memory roster and returns
`IN2N_ERR_NO_CAPABLE_MEMBER` for a capability that is, on disk, present.

### Verify

```bash
python3 -c "
import sqlite3, os, json
c = sqlite3.connect(os.path.expanduser('~/.openclaw/n2n/federation.db'))
r = c.execute('SELECT state, scope FROM member WHERE member_id=?', ('<risk>/<member>',)).fetchone()
print('state:', r[0])
print('specialty:', [x['name'] for x in json.loads(r[1]) if x.get('tier')=='specialty'])
"
```

State must read `active` and the specialty list must contain your skills.

### Why this is not in the checklist above

None of it is caught by `reconcile-mcp.py`. That gate verifies a *fresh installer* can obtain the
integration, which is the property it was built for — and `migration-staging/` is untracked local state, so
it is correctly outside the gate's remit. Nothing statically verifies that a member which *should* have a
capability actually does.

Members are also **cold-started on demand** and idle-exit after 900s, so a member being absent from
`systemctl --user list-units` is normal and not evidence of a problem.

**A refusal from a member is not necessarily a bug.** In spec 080's case the member correctly declined a
device-plane question because it only owned a manager-plane skill, and named the right skill in its
refusal. That is the plane discipline working. The bug was that no member carried the named skill.

## Pinning rules (spec 077 — enforced by the gate)

Two rules, both because they break **fresh installs only** and so survive unnoticed.

**1. Bound any pin on a package whose submodule you import.**

```
mcp>=1.0.0        # WRONG if you write `from mcp.server.fastmcp import ...`
mcp>=1.0.0,<2     # right
```

`mcp 2.0.0` removed `mcp.server.fastmcp` entirely. Twenty declarations across the repo resolved that
breaking major and would have died on import for every new installer. The gate statically scans your
source for submodule imports and fails on an unbounded pin — you cannot forget.

If a bound is genuinely un-inferable (the package does not use semver), record an exception with a
reason in `scripts/check-dependency-pins.py`. Silencing without a reason is not possible by design.

**2. Never call `pip` or `pip3` directly. Use the helper.**

```bash
netclaw_pip_install -r "$SERVER_DIR/requirements.txt"        # right
NETCLAW_VENV="$MY_VENV" netclaw_pip_install -r requirements.txt   # into a venv
netclaw_venv_create "$MY_VENV"                               # venv that works without ensurepip
```

`pip3` and `python3` are not guaranteed to be the same interpreter. On a host where they differ, a bare
`pip3 install` reports success and installs where the server cannot import from — then fails at first
use with `ModuleNotFoundError`. 130 call sites had this shape before spec 077.

`scripts/lib/pip-helper.sh` is sourced by `install-steps.sh`, so the helper is always available.

## Two artifacts that are easy to miss (found missing after spec 076)

R1 shipped with a catalog entry and an install function — so it was *selectable* — but three artifacts
were still missing, and none of them fail the gate:

**1. Curated install-profile membership.** `scripts/lib/catalog.sh` defines `PROFILE_MINIMAL`,
`PROFILE_RECOMMENDED`, `PROFILE_CISCO`, `PROFILE_MULTIVENDOR`, `PROFILE_CLOUD`, `PROFILE_SECURITY`. A
component absent from all of them appears only in the fine-tune checklist. The multivendor CLI driver was
missing from `PROFILE_MULTIVENDOR` — the one profile named after it.

**2. The HUD needs TWO entries, not one.** `ui/netclaw-visual/server.js` has a *node list*
(`{ id: '...', name: ..., prefixes: [...] }`) which renders the node, and a separate *annotation map*
(`'id': { env, files, notes }`). Adding only the annotation leaves no node on the dashboard.

**3. SOUL.md needs the capability, not just the count.** Bumping "N skills backed by M MCP servers" does
not tell the agent what it can now do. Add a section describing the capability and its routing boundaries.

None of these is caught by `reconcile-mcp.py`, so they need checking by hand until they are.
