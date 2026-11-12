# Verification: Spec 193 (R09C)

Date: 2026-11-12. Honest scope: **stub-tested and read-only live-checked; no billable GCP resource was created by this spec's work.**

| Item | Evidence | Status |
|---|---|---|
| Provisioner behavior (warning gate, no default project, prerequisites, plan/apply gates, idempotent apply, partial failure, ownership-scoped teardown with verification, topology shapes, R09B items in plan) | `tests/gcp/test_netclaw_gcp.py`, 13 tests with an in-memory fake gcloud | PASS |
| Docs/installer/extension parity, warning verbatim in README and guide, roadmap, cost table within 15% of builder | `tests/gcp/test_docs_parity.py`, 8 tests | PASS |
| VS Code command, topology ids match provisioner, hostile input quoted/refused | `extensions/netclaw-vscode/test/gcp.test.mjs`, `npm run check` (tsc) | PASS |
| Extension full suite | 224 tests, 219 pass, 2 fail (`actual managed HUD launcher`: "HUD requires Node 24.19+", this host has Node 25.3 build path / environment), rest unrelated | pre-existing, not caused by this change |
| `verify-inventory-counts.py`, `build-catalog.py --check` | PASS | PASS |
| `reconcile-mcp.py` | catalog/docs/portability/skill-limits pass; `dependencies` (humanrail pin) and `startup` (missing local Python modules) FAIL, unrelated to this spec | pre-existing |
| Read-only live prerequisite check against the real gcloud (auth, project access, required APIs) | returned no missing prerequisites | PASS |
| install.sh / gcp-menu.sh | `bash -n` syntax only; interactive TUI path not exercised end to end | NOT QUALIFIED |
| VS Code command in a real editor | compile + unit tests only; no editor-host run | NOT QUALIFIED |
| Real creation, bootstrap and teardown in GCP (SC-001, SC-003 live, SC-007 live) | not run: billable, needs owner go-ahead | OPEN (T014) |
| Generated `gcloud ... create` flags accepted by real gcloud | not exercised (only read-only calls were made) | OPEN (T014) |

## Known limits
- `bootstrap` installs minimal NetClaw over IAP SSH; Risk enrollment is the existing Member/Border flow; HA bootstrap (etcd/authority) and the OpenShell/DefenseClaw stack from R09A are not generalized into `bootstrap`. HA and distributed topologies therefore provision the infrastructure correctly but are not claimed to produce a running HA Risk without the manual enrollment/HA steps.
- Cloud provisioning is outside the Spec153 effect engine (research D1); it uses its own plan hash and cost/list gates.
- No authentication exists; this spec only warns.
