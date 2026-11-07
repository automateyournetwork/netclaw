# Verification

Qualification VM (Ubuntu 24.04 amd64, OpenClaw 2026.10.9, DefenseClaw 1.0.4, Risk in
production mode) and one Proxmox VE node. No credentials are recorded here.

## Service (convergence-platform)

- Pinned release `v0.1.2` (`1e7900f`). Its CI passed (setup/cluster/chart tests, service
  and agent tests, API Node tests) and published `ghcr.io/byrn-baker/convergence-api:0.1.2`
  and `convergence-ids-ingest:0.1.2` (amd64, arm64). Earlier: `v0.1.0` (`40c179a`, image
  job failed, nothing published) and `v0.1.1` (`b468b4d`, first published images).
- Docker trial from the release on the VM: `setup.py prepare/run`, `verify.py --canary`
  11/11, synthetic flow demo retained and returned.
- New K3s cluster on Proxmox VE: `proxmox.py plan/apply` created VMIDs 7000–7002 (3
  servers, VLAN 3, static addresses, API VIP); re-running `apply` changed nothing.
  `site.yml` built K3s v1.35.6 with embedded etcd and a keepalived VIP. Stopping K3s on
  the VIP holder moved the VIP within 15 s with the API reachable. Argo CD 10.11.6 deployed
  Convergence from the repository: Synced/Healthy after a chart fix (Grafana volume claim
  template kind); `verify.py --canary` 13/13. `destroy` removed only the three tagged VMs;
  the read-only deploy key was removed afterwards.
- Full-stack qualification on a rebuilt three-node test cluster and the VM, from the new
  repository only (fixes went into `v0.1.2`):
  - plain Helm install with the public images, `verify.py --canary` 13/13;
  - Alertmanager -> alert receiver -> case; real Suricata (canary signature) -> shipper ->
    IDS ingest -> case, Loki and VictoriaLogs; host heartbeat agent reporting;
  - device syslog (UDP and TCP) and SNMP with the right device name and site, after
    fixing NodePort source-address rewriting and a dropped same-number TCP port;
  - a second release prepared with `k3s.py --receiver-url`: Alertmanager in the cluster
    reached the receiver (installed by `setup/receiver.py`) with the mounted token;
  - NetClaw investigations wired by the service's `setup/netclaw.py` (DefenseClaw scanned
    its `alert-triage` skill CLEAN): admitted test alerts went alert -> case -> restricted
    `alert` agent -> `case_get`/Prometheus/`case_update` -> resolved, with cited evidence;
    an operator "Need more" re-investigation answered the feedback and escalated where
    evidence was missing; the API reached the receiver for JEV (not enabled: no key);
    `remove` restored the previous OpenClaw config and a re-`apply` worked again.
  Fixes found on the way: first-boot package lock in the cluster build, the install guard
  mistaking the IDS volume for release data, `.env` git-ignore, receiver unit paths, and
  silent hourly investigation-budget trips.

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
  `not_configured` in host mode). Result: PASS against `v0.1.2` (`1e7900f`, a fresh clone
  of the tag), demo and host; earlier PASS against `v0.1.1` and `v0.1.0`. The first VM run only lacked Chromium's system
  libraries, which CI installs with `--with-deps`.
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
  it was not applied. The `v0.1.2` skill text (pin plus the optional investigations row)
  also scanned CLEAN.

## Not verified

macOS and WSL2; Hermes; a live Proxmox VE VM Security source end to end through NetClaw
(the service's own tests and its operator's deployment cover the observer); a NetClaw run
with shell enabled that executes the cluster path itself; JEV reviews with a provider key;
IP context with a provider token; a real switch mirror feeding the IDS sensor.
