# Contract: disposition table (filled by R09A evidence, 2026-11-10)

| Component | Result | Evidence |
|---|---|---|
| Border role | **Inside the sandbox** (E3 passed): production launcher runs as the `sandbox` user, bind override on 7443, peers still dial the signed manifest address | `evidence/ha-*.jsonl`, posture `border-role: running` on both nodes |
| HUD ingress | **Inside the sandbox** (E4 passed): ingress on 8443 via `openshell forward`, host 443 REDIRECT scoped to the node IP, public HTTPS with the lego certificate | `https://<node>/api/hud/posture`, `/api/hud/cluster` |
| Workspace backend + chat gateway | **Inside the sandbox**: OpenClaw 2026.7.1-2 embedded agent (`openclaw agent --local`); provider key injected by OpenShell, the sandbox holds only a placeholder. The long-running OpenClaw *gateway daemon* and the workspace backend were **not** started (see verification.md, gaps) | verification.md US2 |
| DefenseClaw sidecar | **Inside the sandbox**, `mode: action`, `hook_fail_mode: closed`; only its binary may reach `api.anthropic.com` | posture `guard`, negative suite, fail-closed test |
| etcd voter / witness | **Outside** (host container, host network); no sandbox attempted (E-experiments: OpenShell has no host networking) | posture `etcd-voter` carries the disposition, never "enforced" |
| Member executor (Docker socket) | **Outside (owner's Mac), exercised in the third window**: hosted subnet-calculator member attached to both sandboxed Borders and completed real operations via the leader and the follower | verification.md |
