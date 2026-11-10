# Contract: node posture (read-only)

Served by the HUD ingress at `GET /api/hud/posture` (same origin and TLS as the HUD, no new listener) and shown by VS Code ("NetClaw: Show Node Posture").

```json
{ "schema_version": 1, "node": "<code>", "region": "<region>",
  "sandbox": {"name": "netclaw-node", "phase": "Ready", "policy_version": 3, "policy_sha256": "<hex>", "landlock": "hard_requirement"},
  "components": [ {"name": "border-role", "inside_sandbox": true, "state": "running"}, ... ,
                  {"name": "etcd-voter", "inside_sandbox": false, "disposition": "host network; container policy", "state": "running"} ],
  "guard": {"mode": "action", "state": "running", "fail_closed": true, "last_block_ms": null},
  "observed_at_ms": 0 }
```

Rules: components outside the sandbox are listed with their disposition and are never reported as "enforced by OpenShell"; `observed_at_ms` is an observation, not authority; no secret or key material appears.
