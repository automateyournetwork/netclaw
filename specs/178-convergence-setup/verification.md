# Verification

Qualification VM (Ubuntu 24.04 amd64, OpenClaw 2026.10.9, DefenseClaw 1.0.4, Risk in
production mode) and one Proxmox VE node. No credentials are recorded here.

## Service (convergence-platform)

- `v0.1.0` (`40c179a`) and `v0.1.1` (`b468b4d`, same code plus the release-workflow fix).
  Its CI on both: setup/cluster/chart tests, service and agent tests, API Node tests.
  `v0.1.1` published `ghcr.io/byrn-baker/convergence-api:0.1.1` and
  `convergence-ids-ingest:0.1.1` (amd64, arm64); both pull anonymously. `v0.1.0`'s image
  job failed (wrong build context) and published nothing; its notes say so.
- Docker trial from the release on the VM: `setup.py prepare/run`, `verify.py --canary`
  11/11, synthetic flow demo retained and returned.
- New K3s cluster on Proxmox VE: `proxmox.py plan/apply` created VMIDs 7000–7002 (3
  servers, VLAN 3, static addresses, API VIP); re-running `apply` changed nothing.
  `site.yml` built K3s v1.35.6 with embedded etcd and a keepalived VIP. Stopping K3s on
  the VIP holder moved the VIP within 15 s with the API reachable. Argo CD 10.11.6 deployed
  Convergence from the repository: Synced/Healthy after a chart fix (Grafana volume claim
  template kind); `verify.py --canary` 13/13. `destroy` removed only the three tagged VMs;
  the read-only deploy key was removed afterwards.

## NetClaw

- `tests/convergence-read/test_connector.py` (pinned component dependencies): 21 tests, 3 new,
  including the VM Security path, fixed GET/site, heartbeats dropped, `not_configured` vs
  `unavailable` vs `unauthorized`, and 14 out-of-contract mutations (site, missing
  `synthetic`, synthetic data labelled live, unknown pattern or severity, threshold, tap,
  timestamp, VM, counts, sampling, NIC, duplicate source) all rejected as `compatibility`.
  The fixture is the service's real demo output. `test_members.py`: 15 passed.
- HUD: `src/hud-server/convergence.test.js` and `src/dashboard/convergence.test.js` (18
  tests: route guards, no arguments, cross-site rejection, loads only when opened,
  synthetic label, advisory wording, stale on failed refresh, not-configured). Full HUD
  unit suite: 519 passed.
- Real integration (`tests/convergence-read-integration/run-tests.py`, the same steps as
  the CI workflow) on the VM against the pinned release: isolated install, repeat install,
  viewer scope; demo and host flow evidence through the real API, store, MCP and HUD in
  Chromium; VM Security through MCP and the browser (synthetic findings in demo mode,
  `not_configured` in host mode). Result: see below.
- Catalog: `build-catalog.py --check`, `check-catalog-metadata.py`, new links
  (`check-catalog-links.py --base-ref`) PASS. `reconcile-mcp.py`: catalog, dependencies,
  docs, packages and portability PASS; `startup` lists only servers whose Python modules
  are not installed on the development host (unchanged by this branch).
- Setup skill, NetClaw-driven (test VM NetClaw on Claude Sonnet 5.5, shell denied by its
  production policy): DefenseClaw scanned the text-only skill CLEAN (0 findings). Turn 1
  read the skill, named the pinned release and asked only the skill's questions (secrets
  in private files, VMID range and prefix), promising a plan before changes. Turn 2, with
  the answers, read the release's procedures and helpers and wrote a cluster spec and
  ordered commands with every step labelled read-only, local or infrastructure-changing.
  That spec passed `proxmox.py check` and a live read-only `plan` (three clean creates);
  it was not applied.

## Not verified

macOS and WSL2; Hermes; the plain Helm install on an existing cluster (service tests
only); a live Proxmox VE VM Security source end to end through NetClaw (the service's own
tests and its operator's deployment cover the observer); a NetClaw run with shell enabled
that executes the cluster path itself.
