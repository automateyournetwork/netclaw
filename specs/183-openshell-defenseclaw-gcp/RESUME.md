# R09A (spec 183) resume pickup, updated 2026-11-10 (session 2)

Owner instruction: drive R09A to 100%, then TEAR EVERYTHING DOWN automatically after evidence is committed (G1 approved: e2-standard-2, ~$0.20/h).
Standing rules: no publish/push-live/announce without owner approval; owner reviews qualified-code changes (list in PR); remove only exactly-owned resources (GCP label `netclaw-spec=183`, prefix `nc183-`); never touch equinix-*, pyats-mcp, gateway5, drawio-mcp; secrets only in `~/.openclaw/.env` (Anthropic key in `~/netclaw/.env`), never printed/committed; never read exit codes through pipes; python3.10 for pytest; use `bash`, not zsh, for loops.

## Live state (billing)
- Project netclaw-506315, zone northamerica-northeast1-c, VMs: nc183-border-a (10.183.2.2), nc183-border-b (10.183.2.3), nc183-witness. Static IPs x2, 3 firewalls, network nc183-r09a + subnet.
- DNS (automateyournetwork.com): current nne1-387185, nne2-737761 (older set nne1-e19e5e, nne2-a97585 also exists, delete both at teardown). Certs via lego in `~/.local/share/netclaw/r09a2-20261110/lego-*`.
- Each Border VM runs sandbox `netclaw-node` (image `nc183-node:3`, policy /tmp/policy.yaml v5) with Border role + HUD ingress; forwards 7443 (node IP), 7444, 8443; host 443->8443 REDIRECT scoped `-d <node ip>`. etcd voters (host containers) on port 12379; witness voter on nc183-witness. Cluster: nne1 leader, nne2 follower. Public posture works: `https://nne1-387185.automateyournetwork.com/api/hud/posture` (and nne2-737761).
- Helpers: scratchpad `.../scratchpad/n183.sh <a|b|w> "<cmd>"` (IAP ssh wrapper) if still present; otherwise `gcloud compute ssh nc183-border-a --zone=northamerica-northeast1-c --project=netclaw-506315 --tunnel-through-iap`. Local artifacts: `~/.local/share/netclaw/r09a2-20261110/` (summary.json, bundles, node-*.tar, policy/v5-*, hud-source.tar, source.tar, workspace-backend.tar). Recreate-sandbox recipe: delete sandbox, `openshell sandbox create --name netclaw-node --from nc183-node:3 --policy /tmp/policy.yaml -- bash -c "wait for /sandbox/nc182/START; exec /opt/nc182/venv/bin/python -B /sandbox/nc182/bin/r09a_node_run.py"`, `openshell sandbox upload netclaw-node ~/stage/nc182 /sandbox`, forwards, `openshell sandbox exec -n netclaw-node -- touch /sandbox/nc182/START`. Runner control: touch `/sandbox/nc182/CTL/stop-border` / `start-border`.
- Last commit: 8266e1fb on branch 183-openshell-defenseclaw-gcp (stacked on PR #340).

## Done
Spec/plan/research/tasks T001-T015; offline tooling; two sandboxed Borders form HA cluster; posture endpoint verified publicly; image build fixed (redirect scope).

## Remaining (tasks.md T016-T045)
1. DefenseClaw sidecar (action mode, fail closed) + OpenClaw gateway/workspace backend inside the sandbox; Anthropic key via OpenShell provider injection (agent cannot read it); one real guarded chat turn; in-band block test with guard token; fail-closed test (stop sidecar, zero provider calls); scan-before-enable test (T023-T027). Update policy/image/runner as needed.
2. Member enrollment window (stop-border, enroll new member identity against 2-node manifest, start-border) and a real operation through each Border (T021).
3. Negative suite `labs/ha/r09a_negative.py` (T028-T029); HA matrix: stopped Border, 7443 cut, isolation `no_quorum`, restart/rejoin with original identity, overhead vs admission window, 2-node majority limit + witness (T030-T034).
4. VS Code posture command evidence/G12, G13 Mobile disposition, audit export, node upgrade test (T035-T038).
5. Add the scoped 443 redirect to `scripts/ha-r09a-deploy.sh`/bootstrap (currently set by hand); fill `contracts/disposition-table.md`.
6. Docs (DEFENSECLAW.md, N2N-RISK.md), roadmap brief outcome, qualified-code change list, cost vs estimate, `verification.md`, memory/GAIT (T039-T043); commit evidence.
7. Then AUTOMATIC TEARDOWN of exactly owned resources: 3 VMs + disks, 2 static IPs, 3 firewalls, network/subnet, both DNS record sets, local `~/.local/share/netclaw/r09a*` dirs, stray Docker objects labeled netclaw.spec. Verify nothing labeled netclaw-spec=183 remains. Open the 183 PR (stacked on #340). No publish.
8. Afterwards R09B survey (brief only), then Azure (R10).

## Session 2 progress (T023-T026 core proven; update, supersedes the "Remaining" item 1 above)
- Provider: OpenShell profile `anthropic` (endpointless, `auth_style: header`, `header_name: x-api-key`) + provider `nc183-anthropic` on BOTH VMs. The policy endpoint carries `credential_binding: {provider: nc183-anthropic}`; the sandbox sees only the placeholder `ANTHROPIC_API_KEY=openshell:resolve:...` (entrypoint env only, not `exec`). Only `/usr/local/bin/defenseclaw-gateway` may reach api.anthropic.com (no bypass).
- Image `nc183-node:4` (dc-home perms fixed). Policy v8 (`policy/v8-nne1|nne2`, protocol `rest`, guard-only egress). Recreate: `/tmp/recreate2.sh <node-ip> <policy-sha>` on each VM (uses `~/stage/nc182`, `/tmp/policy.yaml`, forwards via `-d`, redirect output to files: a pipe on `forward start -d` hangs). Then upload `~/stage/guard-config.yaml` to `/sandbox/`, and run `labs/ha/r09a_guard_up.sh` through the runner hook: upload it to `/sandbox/nc182/CTL/run-script` (lab-only hook; log `/sandbox/nc182/logs/script.log`).
- Node guard config = qualified R04A file + 3 deviations (`labs/ha/r09a_defenseclaw.py render_node_config`).
- Verified on A and B: benign OpenClaw turn returns `ok` through DefenseClaw; prompt-extraction prompt blocked (`[DefenseClaw] This request was blocked ... TRUST-PROMPT-EXTRACT`), alert recorded; on A sidecar stopped -> ECONNREFUSED, no new NET:OPEN/HTTP:POST to Anthropic in `openshell logs`.
- Still open: tool-call block, scan-before-enable, enrollment window + real operation, T028-T045, final teardown.
- Commit b2631b95 plus later commits on branch 183-openshell-defenseclaw-gcp.
