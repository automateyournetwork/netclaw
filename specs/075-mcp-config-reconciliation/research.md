# Phase 0 Research: MCP Config Reconciliation

**Feature**: 075-mcp-config-reconciliation
**Date**: 2026-07-30
**Purpose**: Resolve unknowns before design, and verify the spec's factual claims against the code.

---

## R1 — The "19 uncovered servers" are verifier mapping gaps, not installer gaps

**This corrects the specification.** The spec states that 19 registered servers "have no installer
catalog coverage, meaning the modular installer cannot install them." Investigation shows that is
**false**. Every one of the 19 is installable today. What is missing is a *declaration* in
`scripts/verify-catalog-coverage.py`'s two mapping tables, so the checker cannot see coverage that
already exists.

`scripts/lib/catalog.sh` contains 88 entries and `scripts/lib/install-steps.sh` contains 88
`component_install_*` functions — a clean 1:1. The relevant catalog ids all exist already:
`aap`, `aws`, `gcp`, `fmc`, `meraki`, `memory-mcp`, `te-community`, `te-official`.

The checker decides coverage two ways (`verify-catalog-coverage.py:131`): strip a trailing
`-mcp-server`/`-mcp` suffix and look for an exact catalog id, or match a declared rule in
`GROUPED_CONFIG_PREFIXES` / the explicit map. All 19 failures are cases where neither declaration
exists:

| Registered server(s) | Existing catalog id | Why it currently fails | Fix |
|---|---|---|---|
| `aap-ansible-mcp`, `aap-docs-mcp`, `aap-eda-mcp`, `aap-lint-mcp` | `aap` | Stripping `-mcp` yields `aap-ansible` etc., not `aap` | Prefix group `aap-` → `aap` |
| `aws-cloudtrail-mcp`, `aws-cloudwatch-mcp`, `aws-cost-explorer-mcp`, `aws-diagram-mcp`, `aws-iam-mcp`, `aws-network-mcp` | `aws` | Same | Prefix group `aws-` → `aws` |
| `gcp-compute-mcp`, `gcp-logging-mcp`, `gcp-monitoring-mcp`, `gcp-resource-manager-mcp` | `gcp` | Same | Prefix group `gcp-` → `gcp` |
| `cisco-fmc-mcp` | `fmc` | Strips to `cisco-fmc`, not `fmc` | Explicit alias |
| `meraki-magic-mcp` | `meraki` | Strips to `meraki-magic` | Explicit alias |
| `thousandeyes-mcp` | `te-community` | Name bears no resemblance to the id | Explicit alias |
| `thousandeyes-official-mcp` | `te-official` | Same | Explicit alias |
| `memory-mcp` | `memory-mcp` | **Checker bug**: the catalog id literally is `memory-mcp`, but the suffix is stripped *before* comparison, yielding `memory` | Explicit alias (the established workaround — `rag-mcp` already does exactly this at line 62) |

**Decision**: Fix by adding 3 prefix-group rules and 5 explicit aliases — **8 declarations, zero new
install functions, zero new catalog entries**.

**Rationale**: The mechanism already exists and is already used (`sketchfab-mcp` → `threejs-viz`,
`azure-network-mcp` → `azure`, `unreal-mcp` → `ue5`, `rag-mcp` → `rag-mcp`). This is completing a
pattern, not inventing one.

**Alternatives considered**: (a) Renaming catalog ids to match server keys — rejected, it would break
the user-facing installer component names and every existing profile membership. (b) Making the
matcher fuzzy — rejected, it would hide genuine gaps, which is the opposite of this feature's goal.
(c) Writing 19 install functions — rejected as based on the mistaken premise; it would create
duplicate installers for components that already install correctly.

**Consequence for the spec**: FR-002 and SC-001 must be reworded. These 19 are not user-facing
breakage. The spec's claim that a fresh user "cannot get 22 of the 89" is wrong — the real
user-facing number is 3 (see R2).

---

## R2 — The three Nautobot entries are genuine, user-facing breakage

Confirmed real and install-blocking. `config/openclaw.json` registers:

| Entry | Command | Args |
|---|---|---|
| `nautobot-mcp` | `/home/ubuntu/netclaw/.venv/bin/python3` | `-u /home/ubuntu/netclaw/mcp-servers/nautobot-mcp-v2/server.py` |
| `nautobot-golden-config-mcp` | `/home/ubuntu/netclaw/.venv/bin/python3` | `-u /home/ubuntu/netclaw/mcp-servers/nautobot-golden-config-mcp/server.py` |
| `nautobot-routing-mcp` | `/home/ubuntu/netclaw/.venv/bin/python3` | `-u /home/ubuntu/netclaw/mcp-servers/nautobot-routing-mcp/server.py` |

None has a `cwd`. `/home/ubuntu` is not the home directory of the machine this was measured on, so
these fail for **every** installer including the maintainer. All three catalog ids exist
(`nautobot`, `nautobot-golden-config`, `nautobot-routing`) and all three vendored directories exist,
so this is purely a malformed registration.

**Decision**: Rewrite all three as repo-relative invocations in the same style as the majority of
entries (`python3 -u mcp-servers/<dir>/server.py`), letting `normalize-mcp-cwd.py` supply the `cwd`
at install time.

**Rationale**: It is the pattern the other ~30 local entries already use, and it is the pattern
`normalize-mcp-cwd.py` was written to service. The hardcoded `.venv` interpreter is also suspect —
no other entry references a virtualenv path, so it appears to be a one-off from a different machine.

**Open item for implementation**: confirm whether these three servers need the `.venv` interpreter
specifically (i.e. have dependencies absent from the system Python). If so, the interpreter must be
resolved relative to the install, not hardcoded.

---

## R3 — `cml-mcp` packs arguments into its command string

`cml-mcp` declares `command: "/usr/bin/python3 -m cml_mcp"` — a single string containing an
argument. It is the only entry of its kind.

**Decision**: Treat as suspect, verify, and split into `command: "python3"` with
`args: ["-m", "cml_mcp"]` if the gateway does not split on whitespace.

**Rationale**: Most process-spawning APIs do not split a command string when args are passed
separately, so this likely fails — but it has not been observed failing, and `cml-mcp` is a
long-standing integration. Asserting breakage without evidence would be wrong.

**Note**: `/usr/bin/python3` is a legitimate absolute path (system interpreter) and must NOT be
flagged by the portability check — this is the case that motivated FR-004.

---

## R4 — The existing scripts and their division of labour

All six overlapping scripts were read. They do not conflict; they cover different surfaces.

| Script | Surface | Reuse decision |
|---|---|---|
| `verify-inventory-counts.py` (261 lines) | Computes true skill/MCP counts; scans README/SOUL for numeric claims; owns the 60-entry `EXTERNAL_INTEGRATIONS` list | **Extend.** Add non-zero exit; promote `could not locate` to failure |
| `verify-catalog-coverage.py` (8.2 KB) | Maps registered servers and external integrations to catalog ids; owns `GROUPED_CONFIG_PREFIXES` and the explicit map | **Extend.** Add the 8 declarations from R1; add non-zero exit |
| `normalize-mcp-cwd.py` (94 lines) | Injects an explicit `cwd` for repo-relative entries at install time | **Reuse as-is.** Its logic is the reason R2's fix works. Already correctly skips absolute paths and package specs |
| `register-all-mcps.py` (155 lines) | Discovers servers from `mcp-servers/` and registers them with DefenseClaw | **Reuse its discovery logic** for enumerating vendored directories |
| `scan-all-mcp-source.py` | Source scanning for security review | Not needed for this feature |
| `openclaw-to-hermes-mcp.py` | Config format translation | Not needed for this feature |

**Decision**: Add one thin orchestrator that invokes the two verifiers and aggregates their exit
status. Do not merge them.

**Rationale**: Each holds distinct, hard-won domain knowledge and has its own spec lineage (047 and
049 respectively). Merging risks losing the grouping rules and external-integration rationale that
took two prior features to establish. An orchestrator satisfies FR-009's single entry point without
that risk. `verify-catalog-coverage.py` already imports `verify-inventory-counts.py` via
`importlib.util`, so the composition direction is established.

---

## R5 — CORRECTED: both verifiers already exit 1. The gap is that nothing invokes them

**This corrects an earlier version of this research item**, which claimed both scripts exit `0` and
called that the feature's central defect. That was a measurement error: the exit codes had been read
through a `| tail` pipe, which reports the pipe's exit status rather than the script's.

Verified without a pipe:

```
python3 scripts/verify-catalog-coverage.py >/dev/null 2>&1; echo $?   → 1
python3 scripts/verify-inventory-counts.py >/dev/null 2>&1; echo $?   → 1
```

`verify-catalog-coverage.py:196` returns `1` on failure and line 200 is `sys.exit(main())`. Both
scripts are correct.

**The actual enforcement gap**: nothing calls them. `.github/workflows/` contains only
`skill-review.yml`. A repository-wide search for invocations of either script finds matches only in
prose — `README.md`, `CLAUDE.md`, `docs/COVERAGE-ROADMAP.md`, `mcp-servers/README.md`, and prior spec
directories. No workflow, no shell script, no pre-commit hook runs either check.

**Decision**: Do not modify the exit-code logic. Instead:
1. Wire CI to invoke the checks and fail on non-zero (FR-010) — this is the real fix.
2. Provide a local entry point sharing the same implementation (FR-011).
3. Add a regression test asserting the exit codes stay correct, so this property is protected rather
   than assumed (FR-008 as a preserve-and-test requirement).
4. `--warn-only` becomes optional convenience rather than a compatibility requirement, since the
   audit found no caller to protect.

**Rationale**: The scripts were never the problem. Editing them would have been churn against
correct code, and would have left the actual gap — nothing running them — untouched.

**Risk, unchanged**: wiring CI while the checks legitimately fail lands a red build on `main`. The
enforcement-last ordering therefore still holds, for the same reason as before: remediate first,
wire second.

**Lesson recorded**: never read an exit code through a pipe. `cmd | tail` yields `tail`'s status.
Use `cmd >/dev/null 2>&1; echo $?` or `${PIPESTATUS[0]}`.

---

## R6 — Portability check design

**Decision**: Fail a registration when it contains an absolute path that lies within a home
directory (`/home/*`, `/Users/*`) or otherwise outside both the repository and the standard system
prefixes. Permit `/usr/*`, `/bin/*`, `/opt/*` and bare package specs.

**Rationale**: The distinction that matters is machine-specific versus system-wide, not absolute
versus relative (FR-004). `/usr/bin/python3` is portable in practice; `/home/ubuntu/netclaw/...` is
not. A home-directory prefix is the reliable signal, and it catches the actual defect class found.

**Alternatives considered**: banning all absolute paths (would flag `cml-mcp` and any system
interpreter — too noisy, and would push people toward suppressions); allowlisting per entry (defers
the problem to a list that rots, the exact failure mode of `EXTERNAL_INTEGRATIONS`).

---

## R7 — The host/sandbox working-directory conflict is not resolvable here

`normalize-mcp-cwd.py` intentionally injects an absolute repo path as `cwd` because the gateway runs
from `$HOME`. The sandbox does not have that path mounted, so the same value cannot serve both.

**Decision**: Record as a documented limitation per FR-007's escape clause. Do not attempt to solve
it in this feature.

**Rationale**: It is one of four known Ring-1 cutover blockers and the other three (skills never
uploaded, loopback gateway binding, uncontainerized members) are outside this feature's scope.
Solving one of four does not produce a working cutover, and attempting it would expand R0 well
beyond config hygiene. The limitation is recorded so a future cutover feature inherits the analysis
rather than rediscovering it.

**Important**: this does not affect the stated goal. A fresh user installing their own risk gets a
correct absolute `cwd` for *their* machine from `normalize-mcp-cwd.py` at install time. The conflict
only bites when moving an already-installed config into the sandbox.

---

## R8 — Recording integration state without another list that rots

The `EXTERNAL_INTEGRATIONS` list is hand-maintained and carries its own staleness warning. FR-018
requires the external set be verifiable against the repository or fail when stale.

**Decision**: Derive the vendored-directory set from the filesystem, then require every directory to
be explained by exactly one of: a registered config entry (possibly via a mapping rule), an
`EXTERNAL_INTEGRATIONS` entry, or a new explicit dropped-with-reason record. Fail on any
unexplained directory.

**Rationale**: This inverts the failure mode. Today, forgetting to add a name causes silent
undercounting. Under this scheme, forgetting causes a loud failure naming the directory. The list
stays hand-maintained — that is unavoidable, since "why is this not registered" is human knowledge —
but it can no longer rot silently.

**Alternatives considered**: a machine-readable manifest per vendored directory (cleaner, but 59
new files and a migration, disproportionate here); inferring intent from directory contents
(unreliable — nothing in the source distinguishes "installed on demand" from "forgotten").

---

## R9 — Language, dependencies, testing

**Decision**: Python 3.10+, standard library only. Tests as a shell-driven fixture harness that
mutates copies of the real config/catalog/docs in a temporary directory and asserts exit codes.

**Rationale**: Matches every existing script in `scripts/` (all stdlib-only per their docstrings) and
the repo's stated convention. The checks are exit-code contracts over file inputs, so fixture-based
exit-code assertions test exactly the contract SC-002 specifies. No pytest dependency is introduced
for tooling that must run in a bare CI container.

---

## Summary of corrections this research forces on the spec

| Spec claim | Reality | Action |
|---|---|---|
| 19 servers have no installer coverage; installer cannot install them | All 19 are installable; the verifier's mapping tables are incomplete | Reword FR-002, SC-001, US1 premise |
| A fresh user cannot obtain 22 of 89 | The real user-facing number is 3 (the Nautobot entries) | Correct in US1 |
| `memory-mcp` lacks coverage | Its catalog id is `memory-mcp`; the checker strips the suffix before comparing — a checker bug | Note as a bug fix, not a gap |

Everything else in the spec survived verification: both checks exit 0 while reporting `FAIL`, the 3
Nautobot entries are genuinely broken, `cml-mcp` is genuinely anomalous, the 9 wrong counts and 2
unlocatable claims are real, and the 9 bypassed vendored directories are real.
