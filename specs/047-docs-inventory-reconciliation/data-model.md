# Phase 1 Data Model: Documentation Inventory Reconciliation

This feature has no runtime database or persisted state. "Data model" here means the conceptual entities the verification script and documentation edits must agree on, and the rules that define each entity's count.

## Entity: Skill

**Represents**: One documented operational capability exposed to the NetClaw agent.

**Identity**: The directory name under `workspace/skills/` (e.g., `pyats-network`, `azure-network-ops`).

**Fields**:
- `name` (string) — directory name, also the skill's identity
- `has_skill_md` (boolean) — whether `workspace/skills/<name>/SKILL.md` exists

**Validation rule**: A directory counts as a Skill if and only if `has_skill_md` is true. `SKILL-SCHEMA.md` is a top-level file, not a directory, and is never counted.

**Count**: `Skill count` = number of entities satisfying the validation rule. Ground truth at spec time: 190 (subject to re-verification at implementation time per spec.md Assumptions).

## Entity: MCP Integration

**Represents**: One distinct, individually-usable MCP server NetClaw supports.

**Identity**: The server's registered/documented tool-facing name (e.g., `azure-network-mcp`, `chkp-management`, `gitlab-mcp`).

**Fields**:
- `name` (string) — identity
- `source` (enum: `openclaw-config` | `external-documented`) — where this integration is known from:
  - `openclaw-config`: a top-level entry under `mcpServers` in `config/openclaw.json`. Confirmed during implementation that this population is already fully individually registered — e.g. the Check Point suite's 15 `chkp-*` servers are 15 separate top-level keys, not one entry needing expansion, even though all 15 share a single vendored directory (`checkpoint-mcp-servers/`) under `mcp-servers/`. No bundle-expansion arithmetic is needed.
  - `external-documented`: installed at runtime via pip/npm/Docker, documented in README's MCP Servers table or vendored under `mcp-servers/`, but absent from `config/openclaw.json` entirely (roughly 59 servers as of implementation — pyATS, F5, Catalyst Center, GitHub, Microsoft Graph, Itential, Cisco NSO, Cisco CML, AWS/GCP families, and others; see the script's `EXTERNAL_INTEGRATIONS` list for the current definitive set)
- `vendored_dir` (string | null) — the corresponding directory under `mcp-servers/`, if one exists locally (null for purely external installs); note this is a many-to-one relationship for Check Point (15 entities share one vendored directory)

**Validation rule**: Every entity is counted exactly once, keyed by its individual registered/documented name — not by its vendored directory (which can hold multiple entities, as with Check Point) and not by any parent bundle grouping (there is none in `config/openclaw.json`).

**Count**: `MCP integration count` = count of all entities satisfying the validation rule, unioned across both `source` values with no duplicates. Ground truth at implementation time: 49 `config/openclaw.json` entries (already including all 15 `chkp-*` individually) + 59 external-documented = 108. Exact total is computed by `scripts/verify-inventory-counts.py`, not hand-asserted in documentation prose.

## Entity: Canonical Documentation File

**Represents**: One of the five files in scope for reconciliation.

**Instances** (fixed set, per spec.md):
1. `README.md`
2. `SOUL.md`
3. `SOUL-SKILLS.md`
4. `mcp-servers/README.md`
5. `ui/netclaw-visual/README.md`

**Fields**:
- `count_claims` (list of {location, claimed_skill_count, claimed_mcp_count}) — every place in the file text that states a numeric skill or MCP count
- `inventory_table_rows` (list) — for README.md and mcp-servers/README.md specifically, the set of server/skill names actually enumerated in table form

**Validation rule**: Every `count_claims` entry's `claimed_skill_count` MUST equal the Skill count; every `claimed_mcp_count` MUST equal the MCP Integration count. For README.md and mcp-servers/README.md, `inventory_table_rows` MUST be a superset containing one row per Skill entity (README only) and one row per MCP Integration entity (both files) — no omissions.

## Entity: Counting Report (script output)

**Represents**: The output of running `scripts/verify-inventory-counts.py`.

**Fields**:
- `computed_skill_count` (int)
- `computed_mcp_count` (int)
- `mcp_breakdown` (dict of source → count, for transparency: config entries, bundle expansions, external-documented)
- `doc_discrepancies` (list of {file, location, claimed_value, computed_value}) — any place a documentation file's parsed numeric claim disagrees with the computed count
- `exit_code` (0 if `doc_discrepancies` is empty, 1 otherwise)

This is the artifact User Story 3 (spec.md) and FR-010 require: a single command a maintainer runs to get a pass/fail signal instead of manually re-reading five files.
