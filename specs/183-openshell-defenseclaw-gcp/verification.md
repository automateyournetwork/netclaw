# R09A (spec 183) verification, 2026-11-10

Two Border VMs plus one etcd witness in `northamerica-northeast1-c` (project `netclaw-506315`), each Border running the production Border role and HUD ingress inside an OpenShell 0.1.7 sandbox with DefenseClaw 1.0.4 and OpenClaw 2026.7.1-2. No fixture results are claimed here: everything below was observed live on those VMs. Nothing was published, pushed live or announced.

## What was verified (observed)

| Area | Result | Evidence |
|---|---|---|
| US1 two sandboxed Borders form an HA cluster | Leader election, followers, public posture and cluster endpoints on both nodes | `labs/ha/r09a_probe.py`, `evidence/ha-*.jsonl` |
| US2 key mediation | OpenShell injects the Anthropic key at egress. The sandbox environment holds only `ANTHROPIC_API_KEY=openshell:resolve:...`; the credential is bound by `credential_binding.provider` in the node policy | direct call with the placeholder returned 200; `evidence/audit-export-summary.json` (0 secret hits in OCSF logs) |
| US2 guarded chat turn | Benign OpenClaw turn returns `ok` through DefenseClaw on both nodes | node A and node B turn logs (this session) |
| US2 in-band block (prompt) | Prompt-extraction prompt refused with `[DefenseClaw] This request was blocked ... TRUST-PROMPT-EXTRACT`, alert recorded, `audit_events` row `block`, `last_block_ms` visible in posture | `audit-export-summary.json` (`block: 1` per node) |
| US2 in-band block (tool call) | `defenseclaw tool block exec --connector openclaw`: the agent reported the `exec` call blocked; audit actions `tool-block`, `inspect-tool-block` | node A audit export |
| US2 fail-closed | Sidecar stopped: the turn failed with `ECONNREFUSED` on loopback and OpenShell logged **no** new `NET:OPEN`/`HTTP:POST` to Anthropic. The policy now also allows only the DefenseClaw binary to reach Anthropic, so a bypass is not possible at the network layer | node A, before/after OCSF log |
| US2 scan-before-enable | A malicious skill dropped into the skills folder was detected, scanned and **quarantined** (alert HIGH, audit `install-detected`, `install-blocked`, `quarantine`, `watcher-block`) before it could be enabled | node A audit export |
| US3 isolation | `labs/ha/r09a_negative.py`: 9 of 9 refused, 0 unexpected successes, 0 errors on **both** nodes (out-of-policy file read, frozen-source write, policy-dir write, metadata server, unapproved egress, provider-credential read, member-to-member connection, others in the driver) | `evidence/neg-a`, `evidence/neg-b` |
| US4 stopped leader | Leader Border stopped: survivor `no_quorum` for about 2 s, then leader at epoch 13 about 13 s after the loss; restarted Border rejoined as follower at epoch 13 with its original identity | `evidence/ha-stop-leader.jsonl` |
| US4 7443 cut | Blocking 7443 between the Borders for about 45 s produced **no** authority change (authority is etcd-based). Data-path effects on the peer channel were not measured | `evidence/ha-cut-7443.jsonl` |
| US4 isolation | Node A cut from the two remote etcd voters: `no_quorum` about 3 s after the fault, node B became leader (epoch 15) about 15 s after; after healing A returned as follower and **did not reclaim** authority (one 2 s `no_quorum` flap during rejoin) | `evidence/ha-isolate-etcd2.jsonl` (`ha-isolate-etcd.jsonl` is a first attempt where the fault did not take effect: rules were on FORWARD, the supervisor connects from the host OUTPUT chain) |
| US4 witness | Witness etcd stopped for about 40 s: both Borders unchanged (2 of 3 voters). The two-Border limit: losing one Border host together with the witness leaves one voter and no quorum (same condition as the isolation test) | `evidence/ha-witness-down.jsonl` |
| US4 overhead | TCP connect to the forwarded 7443 listener vs a direct host port: median 0.34 ms vs 0.38 ms locally, 0.65 ms vs 0.66 ms to the peer host (`evidence/overhead.json`). This measures only the host-side accept, **not** a full round trip through the sandbox tunnel, so an end-to-end per-hop overhead against the signed 4500 ms admission window was **not** measured. Observed isolation detection (`no_quorum` about 3 s) is below the window | `evidence/overhead.json`, probe output |
| US5 node upgrade | Node A (follower) and node B (leader) were upgraded by recreating their sandboxes with a new runner: identity preserved, A returned as follower at the same epoch; B (leader) returned as leader at epoch 17 about 51 s later with no split brain | `evidence/ha-upgrade-*.jsonl` |
| US5 posture | `GET /api/hud/posture` now observes the guard (mode `action`, state from sidecar health, last block from the audit DB) on both nodes; the VS Code "NetClaw: Show Node Posture" command and its tests exist and pass (5/5) | `extensions/netclaw-vscode/test/posture.test.mjs` |
| US5 audit export | DefenseClaw `audit.db` and the OpenShell OCSF log exported from both nodes before teardown (kept under `~/.local/share/netclaw/r09a-evidence`, not committed) | `evidence/audit-export-summary.json` |

## G13 Mobile disposition
No Mobile change is required by this stage: the app reaches a Border over the same HTTPS origin (443 to the sandbox ingress on 8443, edge WebSocket behind it), with the same domain-verified certificate; sandboxing changed no wire contract. It was **not** exercised with a real device or an installed build in R09A, and client-build release stays gated by the owner (R09 client-build release gate).

## Gaps and findings (stated plainly)
1. **Member enrollment and a member-executed operation were not done in R09A** (T021 second half). Leader election and a real model operation (guarded chat turn) ran through each Border; the R09 member executor sits outside the sandbox by design (D1) and was not rebuilt on these VMs.
2. The long-running **OpenClaw gateway daemon and workspace backend** were not run; the guarded turn uses the embedded agent (`openclaw agent --local`) with the DefenseClaw plugin. The runner's `CTL/run-script` hook used to start these pieces is a **lab-only** backdoor and must not ship in a production node.
3. The node guard configuration is the qualified R04A file with three documented deviations (`r09a_defenseclaw.py NODE_DEVIATIONS`): `data_dir` to `/sandbox/.defenseclaw`, the per-operation provider fence `base_url` removed, `forward_custom_headers: true` (else Anthropic returns 400 `anthropic-version header is required`). Mode, fail-closed, regex-only detection and the strict rule pack are unchanged. **This is a second guard topology** (no per-operation call fence or two-call counter); owner review needed.
4. OpenShell facts learned live: protocol must be `rest` (not `https`); `forward start -d` output must go to a file; provider env placeholders require an endpointless profile plus `credential_binding` in policy; supervisor egress originates from the host OUTPUT chain; the DefenseClaw CLI venv needed `go+rX` in the image (fixed in `r09a_image.py`, image `nc183-node:4`).
5. During the leader upgrade the surviving follower did not take leadership before the old leader returned (leader came back at epoch 17); the epoch jumped 15 to 17 without an observed leader on A. Not diagnosed.
6. The posture `etcd-voter` state is `unknown` by design (outside the sandbox).

## Qualified-code changes for owner review (FR-024)
- `mcp-servers/protocol-mcp/bgp/federation/ha/config.py`, `factory.py`, `node.py`: optional default-off `listen` block (bind address separate from the signed advertised endpoint); `scripts/lib/protected_role.py`: accepts that block. Tests: `tests/n2n/test_ha_bind_183.py`.
- `labs/ha/hud_ingress_r09.mjs`: `GET /api/hud/posture`; `labs/ha/r09_prepare.py`, `r09_vm_etcd_bootstrap.py`, `scripts/ha-dns-godaddy.py`: R09A support.
- Not changed: protected-guard/provider-fence code, the authority/etcd protocol, NCFED.

## Cost
VMs ran from 17:17Z to the end of validation (about 5 h): about $0.20/h estimated, so about $1.0 of compute plus a few cents of egress against the $1.8 six-hour estimate; Anthropic usage was a handful of short turns. Teardown follows this document.
