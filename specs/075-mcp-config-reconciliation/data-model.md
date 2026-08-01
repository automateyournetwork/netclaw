# Phase 1 Data Model: MCP Config Reconciliation

**Feature**: 075-mcp-config-reconciliation | **Date**: 2026-07-30

No database. These are the in-memory entities the reconciliation logic builds from existing
repository files, and the rules that decide pass or fail.

---

## Entity: Integration

One capability NetClaw can use. Assembled by joining the four registration surfaces.

| Field | Source | Notes |
|---|---|---|
| `id` | `config/openclaw.json` key, or `EXTERNAL_INTEGRATIONS` name, or vendored directory name | Not globally consistent — the join is the hard part |
| `state` | Derived | `registered` \| `external` \| `dropped` — exactly one (FR-014) |
| `reason` | `EXTERNAL_INTEGRATIONS` comment or dropped record | Required unless `registered` (FR-015, FR-016) |
| `vendored_dir` | `mcp-servers/<dir>` | Optional — remote and on-demand integrations have none |
| `catalog_id` | `scripts/lib/catalog.sh` | Required when `registered` (FR-001) |
| `install_fn` | `scripts/lib/install-steps.sh` | `component_install_<catalog_id with - as _>` |
| `command`, `args`, `cwd` | `config/openclaw.json` entry | Present only when `registered` |

### State rules

- Exactly one state per integration. Two states, or none, is a failure (FR-014, FR-017).
- `registered` requires a resolvable `catalog_id` (FR-001).
- `external` and `dropped` require a non-empty `reason` (FR-015, FR-016).
- A `vendored_dir` with no integration in any state is a failure naming the directory (FR-017).
  This is the inversion that stops the external list rotting silently.

---

## Entity: CoverageMapping

How a registered server key resolves to a catalog id. Three mechanisms, checked in order.

| Mechanism | Location | Example |
|---|---|---|
| Suffix-strip exact match | `strip_mcp_suffix()` then exact lookup | `suzieq-mcp` → `suzieq` |
| Prefix group | `GROUPED_CONFIG_PREFIXES` | `chkp-` → `checkpoint` |
| Explicit alias | explicit map | `azure-network-mcp` → `azure` |

### The 8 declarations this feature adds (research R1)

| Declaration | Mechanism | Covers |
|---|---|---|
| `aap-` → `aap` | prefix group | 4 servers |
| `aws-` → `aws` | prefix group | 6 servers |
| `gcp-` → `gcp` | prefix group | 4 servers |
| `cisco-fmc-mcp` → `fmc` | alias | 1 |
| `meraki-magic-mcp` → `meraki` | alias | 1 |
| `thousandeyes-mcp` → `te-community` | alias | 1 |
| `thousandeyes-official-mcp` → `te-official` | alias | 1 |
| `memory-mcp` → `memory-mcp` | alias | 1 — works around the suffix-strip bug, same pattern as the existing `rag-mcp` entry |

Total 19 servers, 8 declarations. No new catalog entries, no new install functions.

---

## Entity: PathClassification

Applied to every `command`, every element of `args`, and `cwd`.

| Class | Rule | Verdict |
|---|---|---|
| `repo_relative` | Resolves to an existing file under the repository root | Pass — `normalize-mcp-cwd.py` supplies `cwd` at install |
| `system_absolute` | Begins `/usr/`, `/bin/`, `/sbin/`, `/opt/`, `/etc/` | Pass — portable across machines |
| `machine_specific` | Begins `/home/` or `/Users/` | **Fail** (FR-003) — names the entry and path |
| `package_spec` | Bare name or registry spec (`npx -y @scope/pkg`, `uvx pkg`) | Pass |
| `embedded_args` | Command string containing whitespace | **Flag for verification** (FR-005) — not an automatic failure |

The `system_absolute` class is why FR-004 exists: a naive absolute-path ban would flag
`/usr/bin/python3`, which is legitimate. The three Nautobot entries are `machine_specific`;
`cml-mcp` is `embedded_args`.

---

## Entity: DocumentedClaim

A numeric assertion about capability counts in prose.

| Field | Notes |
|---|---|
| `file`, `line` | `README.md` or `SOUL.md` |
| `pattern` | The regex locating the claim |
| `kind` | `skill` \| `mcp` |
| `claimed` | Parsed from the text |
| `computed` | 199 skills, 149 integrations (2026-07-30) |
| `locatable` | Whether the pattern still matches anything |

### Rules

- `claimed != computed` → failure naming file, line, both numbers (FR-013).
- `locatable == false` → **failure**, not an advisory note (FR-012). This is the current silent
  degradation: two README claims drifted in phrasing and stopped being checked.

### The 9 known-wrong claims

| File | Line | Claims | Should be |
|---|---|---|---|
| README.md | 7 | 198 skills, 115 MCP | 199, 149 |
| README.md | 242 | 113 MCP, 191 skills | 149, 199 |
| README.md | 521 | `## MCP Servers (115)` | 149 |
| README.md | 661 | `## Skills (198)` | 199 |
| SOUL.md | 15 | 198 skills, 115 MCP | 199, 149 |
| SOUL.md | 398 | 191 skills | 199 |

Plus 2 unlocatable: README installer prose (skills) and README installer prose (MCP).

---

## Entity: ReconciliationResult

| Field | Notes |
|---|---|
| `surface` | `vendored` \| `registered` \| `catalog` \| `docs` \| `portability` |
| `status` | `pass` \| `fail` \| `flagged` |
| `findings[]` | Each names the item and the observed vs expected state (FR-013) |
| `overall` | `fail` if any surface fails; determines the exit code |

### Exit contract

| Condition | Exit |
|---|---|
| All surfaces pass | `0` |
| Any surface fails | **non-zero** (FR-008) |
| Only `flagged` items (e.g. `embedded_args`) | `0`, with warnings printed |
| `--warn-only` passed | `0` regardless, findings still printed (Principle XV mitigation) |

---

## Derived counts (ground truth, 2026-07-30)

| Quantity | Value |
|---|---|
| Registered integrations | 89 |
| External integrations | 60 |
| Total MCP integrations | **149** |
| Skills (dirs with `SKILL.md`) | **199** |
| Vendored directories | 59 |
| Catalog entries | 88 |
| Install functions | 88 |
| Coverage-check failures to fix | 19 (via 8 declarations) |
| Machine-specific paths to fix | 3 |
| Embedded-arg commands to verify | 1 |
| Wrong documented claims | 9 |
| Unlocatable claims | 2 |
| Bypassed vendored directories | 9 |
