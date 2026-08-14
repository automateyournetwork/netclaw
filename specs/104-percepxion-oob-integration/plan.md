# Implementation Plan + Tasks: Lantronix Percepxion OOB integration

**Branch**: `104-percepxion-oob-integration` | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)
**Roadmap**: new coverage area

> **Note on form.** Plan and tasks are combined in one document, following spec 084's precedent. The
> skill body already existed as a working draft, iterated against both servers' actual source over
> several prior sessions (including two live root-cause findings, see spec.md), rather than
> speculatively authored here. A separate tasks.md would restate that work rather than add to it.

## Summary

Two external MCP servers (`percepxion-mcp-server`, `slc-mcp-server`), one skill
(`workspace/skills/percepxion-oob/SKILL.md`). Neither server is vendored, built, or modified by
this change, both already exist as complete, tested, actively-maintained Lantronix repositories.
This spec's work is integration: classify correctly, register per `docs/ADDING-AN-MCP.md`, add
installer coverage with the dependency isolation both servers require, and reconcile every
documentation surface.

## Technical Context

**Language/Version**: Python 3.11+ for both servers (FastMCP 3.x, stdio transport).

**Dependencies**: `percepxion-mcp-server`: `fastmcp>=3.1.0,<4.0`, `requests>=2.32.0,<3.0`,
`python-dotenv>=1.2.0,<2.0`. `slc-mcp-server`: the same three plus `hvac>=2.4.0,<3`,
`boto3>=1.43.10,<2`, `pyotp>=2.9.0,<3`. All upper-bounded; verified directly against each repo's
current `pyproject.toml` (2026-08-12).

**Storage**: none in NetClaw. Each server holds its own session token in memory for the process
lifetime; credentials come from `PERCEPXION_USERNAME`/`PERCEPXION_PASSWORD` (or Vault/AWS/CyberArk)
and `SLC_{KEY}_*` env vars respectively.

**Testing**: both servers carry their own test suites (93 tests, `percepxion-mcp-server`; 127
tests, `slc-mcp-server`), run and passing as of 2026-08-12. Nothing in this integration adds
NetClaw-side test surface, there is no NetClaw code in the call path (Principle XV shape, same as
spec 084's static-binary reasoning, here because both servers are external processes NetClaw
never imports).

**Constraints**: dedicated virtualenv per server, not the installer's shared interpreter (both
pin `fastmcp` 3.x, which conflicts with five vendored servers pinning `fastmcp<3`, see spec 076
and the Zabbix install function). No `config/openclaw.json` entry (external/on-demand
classification, see spec.md).

## Constitution Check

| Principle | Status | How |
|---|---|---|
| **I. Safety-First** | ✅ | Both servers read-only by default; `percepxion-mcp-server`'s CLI policy defaults `PERCEPXION_CLI_WRITE_ENABLED=false` with a built-in deny list; `slc-mcp-server`'s `cli_policy.py` does the same for `apply_config_commands` |
| **II. Read-Before-Write** | ✅ | Skill's Golden Rule section: confirm device identity and port state (`get_security_telemetry`/`get_port_telemetry`) before any write or CLI dispatch |
| **III. ITSM-Gated Changes** | ✅ | Skill requires explicit operator confirmation before `send_direct_cli_command` (write mode), `update_firmware_by_smart_group`, `reboot_device`, `remove_device_from_platform`; W8 (closed-loop remediation) requires an upstream incident ID recorded in every mutating call's `description` field |
| **IV. Immutable Audit Trail** | ✅ | Both platforms log independently of NetClaw: Percepxion's own audit trail (`investigate_audit_logs`, job group records) and slc-mcp-server's audit logging on device-modifying tools. No NetClaw-side GAIT gap the way spec 084 carries one, both upstream servers already audit at the platform layer |
| **V. MCP-Native** | ✅ | stdio, both servers |
| **VI. Multi-Vendor Neutrality** | ✅ n/a | Lantronix-specific by design, this is the OOB/console-server category, comparable to how `redfish-mcp` is BMC-specific |
| **VII. Skill Modularity** | ✅ | Skill's "Integration with Other NetClaw Skills" section states explicit boundaries against `pagerduty-incidents`, `servicenow-change-workflow`, `netbox-source-of-truth`, `itential-orchestration`, `gait-session-tracking`, `grafana-observability` |
| **VIII. Verify After Change** | ✅ | W8 Step 8 requires post-action audit-log confirmation; W2 preflight requires port-state verification before any automated sequence |
| **IX. Security by Default** | ✅ | Read-only CLI policy default on both servers; credentials never logged; `PERCEPXION_CLI_YOLO`/full bypass explicitly opt-in and flagged "use with extreme caution" in the skill |
| **X. Observability** | ✅ | Skill requires every diagnostic/remediation call to carry a `description` field identifying the actor and reason (W8 governance note) |
| **XI. Artifact Coherence** | ✅ | This plan's Phase 5 |
| **XII. Documentation-as-Code** | ✅ | spec.md, this plan, `SKILL.md`, upstream repos' own `README.md`/`CHANGELOG.md` (already current, this session) |
| **XIII. Credential Safety** | ✅ | Skill states explicitly: never expose `PERCEPXION_USERNAME`/`PASSWORD`, `VAULT_TOKEN`, or session tokens in logs, chat output, or error messages |
| **XIV. External Comms** | ✅ n/a | No external comms (Slack/email/etc.) initiated by this skill |
| **XV. Backwards Compatibility** | ✅ | External processes, no NetClaw code imports either server; a Lantronix release cannot break NetClaw's own codebase |
| **XVI. Spec-Driven** | ✅ | specify → plan/tasks (this document) → implement |
| **XVII. Blog** | ⏭️ waived | Standing operator decision |

## Complexity Tracking

| Deviation | Why | Alternative rejected because |
|---|---|---|
| **Two MCP servers behind one skill** | Percepxion and slc-mcp-server answer genuinely different questions (fleet-wide async vs. single-device sync, see spec.md's routing table) and an operator/agent needs both to cover OOB end-to-end. Splitting into two skills (`percepxion-fleet-ops` + `slc-console-ops`) was considered and rejected: the highest-value content is the *routing rule between them* (Key Terms, CLI Command Routing sections), which would either duplicate across two skills or live awkwardly in just one, orphaning the other. | A single skill with an explicit disambiguation section (matches `zabbix-availability`/`zabbix-metrics-history`'s sibling-skill precedent, but inline rather than cross-file, since the routing decision itself is the content) |
| **No `mcp-servers/<name>/README.md`** | That artifact is for vendored copies (see spec.md's "External, not vendored" section); `aap-automation` (the closest precedent, also external/on-demand) has none either | Writing one anyway would create a second, driftable copy of documentation that already lives correctly in each upstream repo's own `README.md` |

## Tasks

### Phase 1, Classify and verify (BLOCKING)

- [X] T001 Confirm neither server is vendorable-in-good-conscience-as-frozen: both are actively
      co-developed by the same author submitting this integration, not a stable third-party
      target (FR of spec.md's "External, not vendored" section)
- [X] T002 Verify both `pyproject.toml` dependency pins directly against the current repos, no
      unbounded pin on an imported submodule (FR-007)
- [X] T003 Confirm both servers' own test suites pass on current `main` (93 tests
      `percepxion-mcp-server`, 127 tests `slc-mcp-server`), recorded rather than assumed

### Phase 2, Skill (P1, this is the integration's substance)

- [X] T004 Add `workspace/skills/percepxion-oob/SKILL.md`, `name:` field matching the directory
      exactly (every real skill in the repo does this, our source draft's frontmatter did not)
- [X] T005 Add `user-invocable: true` to frontmatter, matching the majority convention (111 of
      ~230 sampled skills)
- [X] T006 Verify the CLI-output-retrieval correction (FR-002): `get_job_group` returns status and
      metadata only, `get_cli_command_output` (percepxion-mcp-server v1.1.0+) returns the actual
      text, corrected at all 8 sites in the skill body where the prior draft conflated them
- [X] T007 Verify the role-based `organization_id` requirement (FR-005) is documented at the point
      an agent would first hit it (multi-tenant discovery) and in the Platform Security
      Configuration section as the authoritative statement

### Phase 3, Installer coverage (P1)

- [X] T008 Add `percepxion` and `slc` entries to `EXTERNAL_INTEGRATIONS` in
      `scripts/verify-inventory-counts.py` with a reason comment
- [X] T009 Add `scripts/lib/catalog.sh` entries for both, `Category` = a new "Out-of-Band" grouping
- [X] T010 Add `component_install_percepxion()` and `component_install_slc()` to
      `scripts/lib/install-steps.sh`: `clone_or_pull` into `$MCP_DIR`, then a **dedicated venv**
      per FR-006 (`netclaw_venv_create` with `uv venv` fallback, install with `--python` targeting
      the venv explicitly, never `netclaw_pip_install`, matching the Zabbix precedent's exact
      justification since both packages pin `fastmcp` 3.x)
- [X] T011 Add both to `PROFILE_MULTIVENDOR` (per the R1/spec-076-adjacent lesson that a component
      absent from every named profile is easy to miss, see `docs/ADDING-AN-MCP.md`'s "Two
      artifacts that are easy to miss")

### Phase 4, Documentation surfaces + counts (P1)

- [X] T012 `README.md`: description in the integrations prose paragraph, and the count line
      (163 → 165 MCP integrations, 221 → 222 skills)
- [X] T013 `SOUL.md`: capability summary describing what OOB coverage now means for the agent, not
      only the count (per `docs/ADDING-AN-MCP.md`'s "Two artifacts that are easy to miss" #3)
- [X] T014 `.env.example`: `PERCEPXION_USERNAME`, `PERCEPXION_PASSWORD`, `PERCEPXION_API_URL`, and
      `SLC_{KEY}_IP`/`SLC_{KEY}_USERNAME`/`SLC_{KEY}_PASSWORD` (names and a comment only, no
      values)
- [X] T015 `TOOLS.md`: infrastructure reference entry for both servers
- [X] T016 `python3 scripts/verify-inventory-counts.py` exits with the documentation check PASS
      and the exact predicted delta (spec.md Verification)

### Phase 5, Reconcile and verify

- [X] T017 `scripts/reconcile-mcp.py --surface catalog` clean
- [X] T018 `scripts/reconcile-mcp.py --surface portability` clean (no machine-specific paths, this
      integration introduces none since it writes no `config/openclaw.json` entry)
- [X] T019 `scripts/reconcile-mcp.py --surface dependencies` clean (FR-007, already verified in
      Phase 1, re-checked here against the gate's own static scan)
- [X] T020 `scripts/reconcile-mcp.py` (all surfaces) exits 0
- [X] T021 `scripts/verify-spec-artifacts.py` passes against this spec directory

## Dependencies

Phase 1 blocks Phase 2 (no point documenting tools against an unverified server state). Phase 2
blocks Phase 3 (installer coverage references the skill's own install instructions). Phases 3 and
4 can run in parallel. Phase 5 depends on all prior phases landing.
