# Data Model: Merge Modular TUI Installer with Full Component-Coverage Parity

**Feature**: 049-merge-modular-installer
**Date**: 2026-07-08

None of these are persisted by a database — they are plain-text/shell structures already defined by PR #96's own design. This document records their exact shape so new entries (the gap backfill + chrome-devtools) are added consistently, and so the coverage-check script has a precise contract to parse against.

## Entities

### CatalogEntry

One line in `scripts/lib/catalog.sh`'s `CATALOG` array.

| Field | Type | Description |
|-------|------|-------------|
| id | str | Unique identifier, lowercase, hyphen-separated (e.g. `chrome-devtools`). Maps 1:1 to an install function name via `component_install_<id with hyphens as underscores>()`. |
| category | str | Display grouping in the TUI checklist (e.g. `Analysis & Diagrams`, `ITSM & DevOps`). New entries use an existing category where the component fits; a new category is only introduced if none fits. |
| name | str | Human-readable display name shown in the TUI and `--list` output. |
| description | str | One-line description, may note tool/server counts in parentheses (e.g. `(15 servers)`), matching existing entries' style. |

**Validation rules**: `id` must be unique across `CATALOG` (enforced implicitly by `catalog_has()`/`catalog_field()`'s linear scan — first match wins, so a duplicate id would silently shadow). No entry may reference an `id` with no corresponding `component_install_<id>()` function, or `install.sh`'s component-selection flow fails at runtime for that entry.

### InstallFunction

The bash function `component_install_<id>()` in `scripts/lib/install-steps.sh` implementing one `CatalogEntry`.

**Validation rules**: Self-contained (per R5) — does not shell out to a separate `*-enable.sh` script even if one exists for standalone use; may inline the same logic. Must not require sudo unless the installer's own sudo-confirmation flow is used (matches PR #96's stated "asks before each individual command that needs root" design).

### ProfileDefinition

A named, space-separated string of `CatalogEntry` ids (e.g. `PROFILE_RECOMMENDED`), registered in `profile_components()`'s case statement and `PROFILE_NAMES`.

**Validation rules**: Every id listed must exist in `CATALOG` (the installer's own `catalog_has()` check enforces this at runtime for `--components`; profile strings are not currently validated the same way, so a typo here fails silently — the new coverage-check script also cross-checks profile membership against catalog ids as a side effect of R3's design).

### CoverageReport

The output of `scripts/verify-catalog-coverage.py` (R3) — not a persisted entity, a computed diff.

| Field | Type | Description |
|-------|------|-------------|
| registered_servers | set[str] | MCP server ids from `config/openclaw.json`'s `mcpServers` keys |
| catalog_covered | set[str] | Server ids covered by a `CatalogEntry`, expanded through the intentional-grouping allow-list (e.g. `checkpoint` expands to all 15 `chkp-*` ids) |
| gaps | set[str] | `registered_servers - catalog_covered` — anything left here is a real, unexplained gap |
| exit_code | int | `0` if `gaps` is empty, non-zero otherwise (so this can gate a pre-merge check) |

### ComponentManifest

The per-host record at `~/.openclaw/netclaw-components.conf` (PR #96's own design, unchanged by this feature) — a newline-separated list of installed catalog entry ids, used to preselect the TUI checklist on re-run.

**Validation rules** (new, per FR-009): if the manifest contains an id that no longer exists in `CATALOG` (e.g. a name that changed across this merge), the installer's re-run flow must surface that explicitly rather than silently dropping it from the preselection with no explanation.

## Relationships

```
CatalogEntry --[implemented by exactly one]--> InstallFunction
ProfileDefinition --[references many]--> CatalogEntry (by id)
ComponentManifest --[records many installed]--> CatalogEntry (by id)
CoverageReport --[computed from]--> CatalogEntry (all) + config/openclaw.json (all registered servers)
```

## State Transitions

### Coverage status (per registered MCP server, as tracked by CoverageReport)

```
registered, no catalog coverage           → GAP (fails the check)
registered, direct 1:1 catalog entry      → COVERED
registered, covered via grouping allow-list → COVERED (documented exception)
```
