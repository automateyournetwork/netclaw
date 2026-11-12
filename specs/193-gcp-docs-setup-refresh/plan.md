# Implementation Plan: GCP Deployment Setup, Guides and Documentation Refresh (R09C)

**Branch**: `193-gcp-docs-setup-refresh` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

## Summary

Add one generic, operator-neutral GCP provisioner (`scripts/netclaw-gcp.py`) and wire it into the three real
install paths: the `install.sh` TUI, the Claw Plan / assistant flow, and the VS Code setup wizard. The provisioner reuses
the proven R09/R09A pattern (plan / apply / status / teardown, label + name-prefix ownership, injected gcloud runner,
cost and list-hash gates) but takes project, region(s), prefix and topology as parameters with **no default project**.
A shared Standard Warning (single source, one file) is rendered at every entry point and acknowledged before planning.
Docs gain a separate `docs/NETCLAW-IN-GCP.md` and refreshed README / getting-started / assistant / Claw Plan sections;
the roadmap is updated. Cloud provisioning stays **outside** the Spec153 effect engine (research D1).

## Technical Context

**Language/Version**: Python 3.10+ (stdlib only, `gcloud` CLI via subprocess), Bash (install.sh TUI glue), TypeScript (VS Code extension, existing stack)
**Primary Dependencies**: Google Cloud SDK `gcloud` (user-installed); existing `scripts/lib/tui.sh`; existing extension toolchain. No new packages.
**Storage**: Per-deployment state file `~/.openclaw/gcp/<deployment-id>.json` (0600): marker, plan hash, created resource names. No database.
**Testing**: pytest/unittest with an injected fake runner (same as `tests/n2n/test_ha_multiregion_182.py`); extension `node --test`; shell driver tests via `GCLOUD` stub.
**Target Platform**: macOS and WSL2 Ubuntu (native Windows stays a read-only gate)
**Project Type**: CLI tooling + installer UI + documentation
**Performance Goals**: SC-001: first Border from installer start in <45 min elapsed (dominated by VM boot and bootstrap)
**Constraints**: nothing created before explicit confirmation; no secrets in logs/plans/state; ownership-scoped teardown; idempotent re-run
**Scale/Scope**: 1-3 Borders + 0-N Members + optional etcd witness per deployment; up to 3 regions

## Constitution Check

| Principle (summary) | Status |
|---|---|
| Safety-first / human approval for destructive and billable actions | PASS: review plan, cost gate, list-hash gate on teardown |
| Secrets never leak | PASS: FR-012; values read from env/stdin, never printed or stored |
| Full-stack artifact coherence (installer, docs, catalog, counts) | PASS with work: T-docs and consistency checks in tasks |
| Spec/verification honesty (no fixture-as-real claims) | PASS: verification.md separates stub-tested from live-verified |
| No unauthenticated exposure claims | PASS: Standard Warning, FR-015..018 |

Re-check after design: no violations; the one deviation (outside Spec153 engine) is justified in research D1.

## Project Structure

### Documentation (this feature)

```text
specs/193-gcp-docs-setup-refresh/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md verification.md
  contracts/cli.md  contracts/warning.md
  checklists/requirements.md
```

### Source (repository root)

```text
scripts/netclaw-gcp.py              # NEW generic provisioner (plan/apply/status/ssh/teardown)
scripts/lib/gcp_warning.txt         # NEW single-source Standard Warning text
scripts/lib/gcp_topology.py         # NEW pure topology -> resource plan builder (testable)
scripts/lib/gcp-menu.sh             # NEW TUI step sourced by install.sh
scripts/install.sh                  # EDIT: offer "Deploy to GCP" step
extensions/netclaw-vscode/          # EDIT: wizard QuickPick + command invoking the provisioner; tests; version bump
installer/assistant-skills/netclaw-install/SKILL.md   # EDIT
installer/spec-kit/netclaw-claw/    # EDIT (GCP topology guidance only)
docs/NETCLAW-IN-GCP.md              # NEW guide
README.md docs/GETTING-STARTED-VSCODE.md docs/ASSISTANT-INSTALL.md docs/CLAW-PLAN.md   # EDIT
docs/roadmap/issue-310/             # EDIT: R09B complete, add R09C brief, R10 depends on R09C
tests/gcp/                          # NEW tests (fake runner, scan for operator hardcodes, warning presence, doc/option parity)
```

**Structure Decision**: single new provisioner module plus thin per-frontend adapters; the extension and TUI call the same CLI so option names cannot drift (SC-002, SC-006).

## Design Notes

- Topologies (named, stable ids): `gcp-border`, `gcp-member`, `gcp-border-onprem-members`, `onprem-border-gcp-members`, `ha-risk`, `distributed-risk`.
- Software bootstrap: after infrastructure exists, the provisioner runs the repository's non-interactive installer on each VM over IAP SSH for the node role; HA/distributed topologies use the HA bootstrap generalized from `scripts/ha-r09-vm-*.sh` (de-hardcoded). Anything not yet generalizable is stated as a known limit in the guide, not hidden.
- R09B adopted items applied at setup: dedicated least-privilege service account (no keys), OS Login, IAP-only SSH, firewall with 443 restricted to a user-supplied CIDR (default: caller's IP) and 7444 public (mTLS), budget alert (optional), Private Google Access, no external IP on witness.
- Ownership/teardown: label `netclaw-deployment=<id>` plus prefix `nc-<id>-`; teardown lists, requires `--confirm-list-sha256`.
