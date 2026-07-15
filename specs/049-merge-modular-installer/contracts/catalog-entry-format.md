# Contract: Catalog Entry & Install Function Format

**Feature**: 049-merge-modular-installer
**Date**: 2026-07-08

This is the format contract every new/expanded catalog entry in this feature must follow — it is PR #96's own existing format, documented here so the 9 backfilled entries plus `chrome-devtools` are indistinguishable in style from the other 72.

## Catalog line (`scripts/lib/catalog.sh`)

```
"<id>|<Category>|<Name>|<Description>"
```

- `<id>`: lowercase, hyphen-separated, unique. Becomes `component_install_<id_with_underscores>()`.
- `<Category>`: one of the existing category headers (`Device Automation`, `Source of Truth`, `Fabric & Orchestration`, `Security`, `Cloud`, `Observability`, `Labs & Simulation`, `ITSM & DevOps`, `Analysis & Diagrams`, `Voice & Social`, `Platform Services`) unless no existing category fits.
- `<Name>`: Title Case display name.
- `<Description>`: one line, may parenthesize tool/server counts.

Example (this feature adds):
```
"chrome-devtools|Analysis & Diagrams|Chrome DevTools|Browser automation/inspection — visualization QA, controller GUI gap-fill, API discovery, Watch Mode (2 servers)"
```

## Install function (`scripts/lib/install-steps.sh`)

```bash
component_install_<id>() {
log_step "Configuring <Name>..."
echo "  Source: <upstream link or Built-in>"
echo "  Auth: <credential requirement, or 'None'>"
echo "  Transport: <stdio/http/etc + how it's spawned>"

# self-contained logic — no delegation to a separate *-enable.sh script
# even if one exists for standalone use (see research.md R5)
...

echo ""
}
```

- No leading indentation inside the function body (matches every existing function in the file — flat style, not 4-space indented).
- Ends with a blank `echo ""` line (matches every existing function).
- Must not require sudo directly; if a step genuinely needs elevation, use the installer's existing sudo-confirmation mechanism rather than calling `sudo` unconditionally.

## Profile membership

Adding an id to a `PROFILE_*` string is optional per entry — only add it where the new component clearly belongs in that curated profile's theme (e.g. `chrome-devtools` fits `recommended` given it now underpins visualization-QA workflows already in that profile; the telemetry receivers fit `observability`).

## Coverage allow-list entry (`scripts/verify-catalog-coverage.py`)

For any catalog id that intentionally covers more than one registered MCP server (a grouping, per R4/FR-010):

```python
GROUPED_COVERAGE = {
    "chrome-devtools": ["chrome-devtools-mcp", "chrome-devtools-mcp-visible"],
    "checkpoint": ["chkp-argos-erm", "chkp-cpinfo-analysis", ...],  # existing, documented here for completeness
    "aws": ["aws-network", "aws-cloudwatch", ...],
    ...
}
```

Any registered server id not reachable via a direct `catalog_id == server_id` match, and not listed as a value somewhere in `GROUPED_COVERAGE`, is reported as a gap.
