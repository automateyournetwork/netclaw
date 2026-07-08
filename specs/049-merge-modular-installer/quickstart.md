# Quickstart: Merge Modular TUI Installer with Full Component-Coverage Parity

**Feature**: 049-merge-modular-installer
**Date**: 2026-07-08

## Prerequisites

1. Local clone of `automateyournetwork/netclaw` with write access (already the case in this session)
2. PR #96's branch fetched locally: `git fetch origin pull/96/head:pr-96-review` (already done)
3. `gh` CLI authenticated with push access to the base repo (already confirmed — used to open/merge PR #97)

## Workflow

### 1. Bring PR #96 up to date with main

```bash
git checkout pr-96-review
git merge main   # or rebase — resolve scripts/install.sh and README.md conflicts by
                  # taking PR #96's version of both files wholesale (clean replacement,
                  # not a line merge), then proceed to step 2
```

### 2. Backfill the 9 confirmed catalog gaps

For each gap in `research.md` R2, add one `CatalogEntry` line to `scripts/lib/catalog.sh` and one `component_install_<id>()` function to `scripts/lib/install-steps.sh`, following `contracts/catalog-entry-format.md` exactly.

### 3. Retrofit chrome-devtools

Add the `chrome-devtools` catalog entry and its install function per `research.md` R4/R5 — self-contained (browser resolution/provisioning + both MCP registrations inlined), `scripts/chrome-devtools-enable.sh` untouched and still documented as the standalone tool.

### 4. Build the coverage-check script

`scripts/verify-catalog-coverage.py` per `research.md` R3 and the `GROUPED_COVERAGE` allow-list in `contracts/catalog-entry-format.md`. Run it — it must report zero gaps before proceeding.

### 5. Amend the constitution

Per `research.md` R6 — update Principle XI's checklist line and body text, add a Sync Impact Report block, bump to the next MINOR version.

### 6. Validate

```bash
bash -n scripts/install.sh scripts/lib/*.sh scripts/chrome-devtools-enable.sh
python3 scripts/verify-catalog-coverage.py
./scripts/install.sh --list   # confirm every new entry appears, no shell errors
```

### 7. Push to the contributor's branch

```bash
git push git@github.com:calcuttin/netclaw.git pr-96-review:feat/installer-tui-refactor
```

(Confirmed viable: `maintainerCanModify: true` on PR #96.) This updates PR #96 in place. Post an explanatory, appreciative comment on the PR per the conversation with the operator, then let PR #96 merge normally (still crediting the original contributor).

## Verification

1. `scripts/verify-catalog-coverage.py` exits 0.
2. `./scripts/install.sh --list` shows all ~81 components (72 original + 9 backfilled/retrofitted), grouped correctly.
3. `./scripts/install.sh --components chrome-devtools` completes without sudo and without any credential prompt.
4. PR #96 shows `mergeable: MERGEABLE` (not `CONFLICTING`) after the push.
5. The constitution file's Sync Impact Report and version number reflect the amendment.
