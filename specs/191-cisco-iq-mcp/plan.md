# Implementation Plan: Cisco IQ Remote MCP Integration

**Branch**: `191-cisco-iq-mcp` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/191-cisco-iq-mcp/spec.md` (issue #346)

## Summary

Register Cisco's official Cisco IQ remote MCP server (Streamable HTTP, `Authorization: Bearer` key) through NetClaw's existing native remote MCP support (the same `url` + `headers` shape as `meraki-mcp`). One stdlib-only Python module (`scripts/cisco_iq.py`) with a thin Bash wrapper (`scripts/cisco-iq-enable.sh`) gives administrators enable / disable / diagnose / rotate / update / status / policy-check without an AI operator. A deny-by-default policy file, a skill, an admin doc, an offline contract suite and the full artifact-coherence set (catalog, installer, counts, env example) complete it. No Cisco IQ tool names or schemas are invented.

## Technical Context

**Language/Version**: Python 3.10+ (stdlib only), Bash wrapper
**Primary Dependencies**: none new. Reuses semantics of `scripts/write-env.py` (private atomic dotenv writes; value from stdin only)
**Storage**: runtime `~/.openclaw/.env` (key, region), runtime `~/.openclaw/openclaw.json` (registration), private backups (0600) beside them; no database
**Testing**: `unittest`/pytest-style offline suite at `tests/cisco-iq/` with a local mock Streamable HTTP endpoint on 127.0.0.1; shell harness `run-tests.sh`; declared in `tests/contract-suites.json`
**Target Platform**: macOS and WSL2/Linux (matches installer policy)
**Project Type**: admin CLI tooling + config + skill + docs (no server code)
**Performance Goals**: diagnose completes in <15 s on unreachable network (timeouts bounded)
**Constraints**: no secrets in argv/output/logs; no network in default test run; HTTPS enforced for non-loopback endpoints
**Scale/Scope**: single registration, three regions

## Constitution Check

| Principle | Status |
|---|---|
| I/II Safety, Read-before-write | PASS: integration is read-only by policy; scripts preview before write |
| V MCP-Native | PASS: native remote client, no adapter |
| IX/XIII Security, Credential Safety | PASS: env reference only, 0600, redaction, no argv secrets |
| XI Artifact Coherence | PASS planned: README, SOUL, TOOLS, .env.example, catalog.sh, install-steps.sh, catalog.json, verify scripts, SKILL.md, HUD env-map |
| XV Backwards compat | PASS: purely additive |
| XVI Spec-driven | PASS: spec, plan, research, tasks (tasks.md) |
| XVII WordPress milestone | N/A for this autonomous run; noted as not done |

Re-check after design: no violations. Honest limit recorded: NetClaw's native client has no per-tool gate, so "read-only allowlisted" is policy + DefenseClaw + skill instruction, not a kernel guarantee.

## Project Structure

### Documentation

```text
specs/191-cisco-iq-mcp/
├── spec.md  plan.md  research.md  data-model.md  quickstart.md  tasks.md
├── contracts/ (cli.md, registration.md, policy.schema.json)
├── checklists/requirements.md
└── verification.md   # written during implement
```

### Source Code

```text
scripts/cisco_iq.py              # all logic: regions, redaction, env/config edit, diagnose, policy
scripts/cisco-iq-enable.sh       # thin wrapper (subcommand dispatch), no logic
config/cisco-iq-policy.json      # deny-by-default read-only policy, empty verified allowlist
workspace/skills/cisco-iq/SKILL.md
docs/CISCO-IQ.md
tests/cisco-iq/{run-tests.sh,test_*.py,mock_server.py}
tests/contract-suites.json       # + cisco-iq suite
scripts/lib/catalog.sh, scripts/lib/install-steps.sh, config/components/catalog.json,
scripts/verify-inventory-counts.py (EXTERNAL_INTEGRATIONS), scripts/verify-catalog-coverage.py (alias if needed),
README.md, SOUL.md, TOOLS.md, .env.example, ui/netclaw-visual/env-map.js
```

**Structure Decision**: single Python module so redaction and region table have one source of truth; wrapper stays logic-free.

## Complexity Tracking

None.
