# Verification: Spec 193 (R09C)

Date: 2026-11-12. Honest scope: **fake-runner tested, plus one real single-Border GCP deploy / bootstrap / teardown (clean).** HA and distributed shapes were not created live.

| Item | Evidence | Status |
|---|---|---|
| Provisioner behavior (warning gate, no default project, prerequisites, plan/apply gates, idempotent apply, partial failure, ownership-scoped teardown with verification, topology shapes, R09B items in plan) | `tests/gcp/test_netclaw_gcp.py`, 13 tests with an in-memory fake gcloud | PASS |
| Docs/installer/extension parity, warning verbatim in README and guide, roadmap, cost table within 15% of builder | `tests/gcp/test_docs_parity.py`, 8 tests | PASS |
| VS Code command, topology ids match provisioner, hostile input quoted/refused | `extensions/netclaw-vscode/test/gcp.test.mjs`, `npm run check` (tsc) | PASS |
| Extension full suite | 224 tests, 219 pass, 2 fail (`actual managed HUD launcher`: "HUD requires Node 24.19+", this host has Node 25.3 build path / environment), rest unrelated | pre-existing, not caused by this change |
| `verify-inventory-counts.py`, `build-catalog.py --check` | PASS | PASS |
| `reconcile-mcp.py` | catalog/docs/portability/skill-limits pass; `dependencies` (humanrail pin) and `startup` (missing local Python modules) FAIL, unrelated to this spec | pre-existing |
| Read-only live prerequisite check against the real gcloud (auth, project access, required APIs) | returned no missing prerequisites | PASS |
| Interactive TUI (`gcp_deploy_menu`) in a real pseudo-terminal: decline at the warning creates nothing; full path (ack, topology, project, region, CIDR) reaches the real plan and declining at "Create exactly this plan" creates nothing | scripted pty run, real gcloud read-only calls; only the intended deployment existed afterward | PASS |
| VS Code 1.146.0 real editor host: extension loads, `netclaw.deployGcp` registered, command with unacknowledged warning opens no terminal and plans nothing | `@vscode/test-electron` run (harness kept outside the repo) | PASS (partial: the acknowledged click-through was not UI-driven) |
| **Real GCP run, 2026-11-12, project owned by the requester, `gcp-border`, northamerica-northeast1**: plan (read-only) -> apply created 8 resources + 2 IAM bindings, real `gcloud create` flags accepted; second apply `exists` x8, `0 created` (idempotent); status; state file mode 600; foreign-node ssh refused; `bootstrap` over IAP SSH to a real VM | live | PASS |
| Teardown (real): list printed, wrong hash REFUSED, correct hash deleted instance, address, 3 firewalls, subnet, network, service account and both IAM bindings; "0 owned resource(s) remain"; independent gcloud listing showed 0 `nc-f9378a` resources and 0 IAM bindings | live | PASS |
| Cost of the live run | about 40 minutes of one e2-standard-2 + one static IP, well under $0.10 | recorded |

### Defects found by the real run and fixed
1. `bootstrap` assumed the VM already had Node, npm and uv, so the installer preflight blocked. It now installs git/python/pipx/uv and a **checksum-verified** Node 24.x tarball (`scripts/lib/gcp-bootstrap.sh`).
2. `openclaw onboard` needs a TTY and the user's provider choices, so an unattended `install.sh` cannot succeed. `bootstrap` now stops at a prepared host and prints the exact interactive `gcloud compute ssh -t ... ./scripts/install.sh` line. Docs corrected.
3. SSH failure output showed only IAP/NumPy noise. Output is now filtered to the real error lines.

### Not exercised
- HA and distributed topologies against real GCP (only the single-Border shape was created live; the others are fake-runner tested).
- The acknowledged VS Code click-through and the `install.sh` entry prompt in a full installer run (the menu function itself was driven in a pty).
- Member roles and HA/etcd bootstrap on a real node.

## Known limits
- `bootstrap` prepares the host over IAP SSH (Node, uv, checkout); `install.sh` stays interactive; Risk enrollment is the existing Member/Border flow; HA bootstrap (etcd/authority) and the OpenShell/DefenseClaw stack from R09A are not generalized into `bootstrap`. HA and distributed topologies therefore provision the infrastructure correctly but are not claimed to produce a running HA Risk without the manual enrollment/HA steps.
- Cloud provisioning is outside the Spec153 effect engine (research D1); it uses its own plan hash and cost/list gates.
- No authentication exists; this spec only warns.
