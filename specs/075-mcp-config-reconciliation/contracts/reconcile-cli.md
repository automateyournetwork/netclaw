# Contract: Reconciliation CLI

**Feature**: 075-mcp-config-reconciliation | **Date**: 2026-07-30

The external interface of this feature is a set of command-line checks. This is their contract:
invocation, exit codes, and output guarantees. CI and the local pre-push command both depend on it.

---

## `scripts/reconcile-mcp.py` — the single entry point (FR-009)

```
scripts/reconcile-mcp.py [--warn-only] [--surface SURFACE] [--json] [--quiet]
```

| Option | Behaviour |
|---|---|
| *(none)* | Run every surface. Exit non-zero if any fails |
| `--warn-only` | Print all findings, always exit `0` (Principle XV mitigation) |
| `--surface S` | Run one of `vendored`, `registered`, `catalog`, `docs`, `portability`. Repeatable |
| `--json` | Emit machine-readable results to stdout; human text suppressed |
| `--quiet` | Suppress passing surfaces; print only findings |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | All surfaces passed, or only `flagged` findings, or `--warn-only` |
| `1` | One or more surfaces failed |
| `2` | Could not run — missing input file, unparseable JSON, bad arguments |

Exit `2` is distinct from `1` so CI can tell "the repository is inconsistent" from "the check itself
is broken." A missing `config/openclaw.json` must never be reported as a reconciliation failure.

### Guarantees

- **No network access.** Must pass in an offline container.
- **No running agent required** (FR-029, SC-013). Never reads `~/.openclaw/openclaw.json`.
- **Read-only.** Never writes to any repository file. Remediation is a separate human/task action.
- **Deterministic.** Same repository state yields identical output and exit code, so CI and local
  runs cannot disagree (FR-011).
- **Path-independent.** Resolves paths from its own location, not the caller's `cwd`, matching every
  existing script in `scripts/`.
- **No credentials in output** (Principle XIII). Reports env var *names*, never values.

### Output format

Every finding is one line:

```
<SURFACE>: <ITEM>: <observed> (expected <expected>)
```

Examples:

```
portability: nautobot-mcp: command '/home/ubuntu/netclaw/.venv/bin/python3' is machine-specific (expected repo-relative or system path)
catalog: aap-ansible-mcp: no matching catalog id (expected direct, prefix-group, or alias match)
docs: README.md:7: claims 198 skills (expected 199)
vendored: mcp-servers/foo-mcp: no recorded state (expected registered, external, or dropped)
```

Each names the surface, the item, and both states — satisfying FR-013's "actionable without
re-deriving the analysis."

### Summary block

```
Reconciliation: FAIL
  vendored      pass    59 directories, 59 explained
  registered    pass    89 entries
  catalog       FAIL    19 of 89 unmapped
  docs          FAIL    9 wrong claims, 2 unlocatable
  portability   FAIL    3 machine-specific paths, 1 flagged
```

The word `FAIL` appearing anywhere in the summary MUST correspond to a non-zero exit. The defining
defect this feature fixes is that `FAIL` currently coexists with exit `0`.

---

## Extended: `scripts/verify-inventory-counts.py`

Existing invocation unchanged. Changes:

| Change | Requirement |
|---|---|
| Exit non-zero when the documentation check fails | FR-008 |
| Treat an unlocatable expected claim as a failure, not a note | FR-012 |
| Accept `--warn-only` to restore prior exit-0 behaviour | Principle XV |

**Backwards-compatibility risk**: any existing caller relying on exit `0` will now see `1`. Callers
must be audited before this lands.

---

## Extended: `scripts/verify-catalog-coverage.py`

Existing invocation unchanged. Changes:

| Change | Requirement |
|---|---|
| Add 3 prefix-group rules and 5 explicit aliases | FR-002 |
| Exit non-zero when the coverage check fails | FR-008 |
| Accept `--warn-only` | Principle XV |

Grouping semantics must be preserved: one catalog id legitimately covering many servers is correct,
not a gap (FR-019).

---

## New: `scripts/check-mcp-portability.py`

```
scripts/check-mcp-portability.py [--config PATH] [--warn-only] [--json]
```

Classifies every `command`, `args` element, and `cwd` per the `PathClassification` model.

| Verdict | Classes |
|---|---|
| Pass | `repo_relative`, `system_absolute`, `package_spec` |
| Fail | `machine_specific` |
| Flag (exit 0, warn) | `embedded_args` |

Must not flag `/usr/bin/python3` (FR-004). Must flag all three Nautobot entries (FR-003).

---

## New: `scripts/trace-skill.py`

```
scripts/trace-skill.py <skill-name> [--json]
```

Reports the chain from skill to backing integration to recorded state and catalog component
(FR-025).

| Exit | Meaning |
|---|---|
| `0` | Chain resolved, including when the backing integration is intentionally external |
| `1` | Chain broken — integration registered but unmapped, or path non-portable |
| `2` | No such skill |

"Intentionally external and not installed" MUST report as an expected state, not a fault (FR-026).
This is a diagnostic tool, so it is not part of the CI gate.

---

## CI contract (FR-010)

CI invokes `scripts/reconcile-mcp.py` with no arguments and fails the job on non-zero exit. The job
must not require credentials, network, or an installed agent. `--warn-only` MUST NOT be used in CI —
that would reproduce the exact defect being fixed.

## Local contract (FR-011)

The same script with the same arguments, runnable pre-push. CI and local runs share one
implementation so results cannot diverge.
