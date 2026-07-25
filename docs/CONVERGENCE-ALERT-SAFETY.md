# Convergence alert → investigation safety

**Incident (2026-07-25):** Phase 8 rule `SwitchInterfaceDown` fired once per
admin-up / oper-down switch port (normal idle access ports). Alertmanager
webhooked each fingerprint to `alert-receiver`, which opened an OpenClaw
`hook:alert:{{fingerprint}}` session **per port**. Each session’s
`bundle-tools` phase eagerly started the full MCP set (~26 processes). Under
OOM, `openclaw-gateway` restarted and **main-session-restart-recovery** resumed
orphaned alert sessions → death spiral on a 16 GiB host with no swap.

This document is the permanent control plane so that class of failure does not
recur when we add metrics/alerts—not by “turning monitoring off.”

---

## Defense in depth

| Layer | What it does | Where |
|-------|----------------|-------|
| **1. Alert design** | Never page/investigate high-cardinality idle state | `prometheus/alerts/device.rules.yml` |
| **2. AM grouping** | Coarse `group_by`; separate route for `investigate=false` / `info` | `alertmanager/alertmanager.yml` |
| **3. Receiver policy** | Honor `investigate` label, deny-list, min severity | `services/alert-receiver/server.py` |
| **4. Admission control** | Dedup TTL, max/min, concurrency semaphore (no queue) | same |
| **5. Metrics** | `netclaw_investigations_suppressed_*` for visibility | `/metrics` on :8099 |

### Correct switch SNMP signals

| Alert | When | `investigate` |
|-------|------|----------------|
| `DeviceSnmpExporterDown` | scrape target down 10m | `true` |
| `SwitchLinkLost` | oper was **up** 15m ago, now down, admin up | `true` |
| `SwitchIdlePortsPresent` | count of admin-up/oper-down > 0 (aggregate) | **`false`** |
| ~~`SwitchInterfaceDown`~~ | **removed** — idle-port storm | — |

Idle ports never satisfy `offset 15m == 1`, so they do not produce `SwitchLinkLost`.

---

## Authoring checklist (new alerts)

Before merging a Prom rule that can reach NetClaw:

1. **Cardinality** — does the alert series key include `ifIndex`, `client`, `src_ip`, etc.?
   - If yes: aggregate (`count by (device_name)`) **or** edge-detect (was healthy, now bad).
2. **Label `investigate`**
   - `"true"` only if a human/agent should open a full tool session.
   - `"false"` for inventory/info/dashboard signals.
3. **Severity** — `info` never auto-investigates by default (`INVESTIGATE_MIN_SEVERITY=warning`).
4. **`for:`** — ≥ a few minutes; avoid flapping into hooks.
5. **Receiver knobs** (env on alert-receiver):

| Env | Default | Role |
|-----|---------|------|
| `MAX_CONCURRENT_INVESTIGATIONS` | `2` | In-flight OpenClaw hooks |
| `MAX_INVESTIGATIONS_PER_MINUTE` | `3` | Burst cap |
| `INVESTIGATION_DEDUP_TTL` | `1800` | Same fingerprint silence (s) |
| `INVESTIGATE_MIN_SEVERITY` | `warning` | Floor for auto-hook |
| `INVESTIGATE_DENY_ALERTNAMES` | includes legacy `SwitchInterfaceDown` | Hard deny |
| `INVESTIGATE_REQUIRE_LABEL` | `false` | If `true`, only `investigate=true` hooks |

Admission **suppresses** (diary only) rather than **queues** when at capacity—queues would replay storms after OOM recovery.

---

## Why OpenClaw multiplies load

- Hook mapping: `sessionKey: hook:alert:{{fingerprint}}` → one session per fingerprint.
- Session prep runs `bundle-tools` → starts **all** `mcp.servers` for that session.
- `Restart=always` + **main-session-restart-recovery** resumes interrupted alert sessions after crash.

Receiver admission limits **new** hooks. Alert design prevents hundreds of fingerprints. Both are required.

---

## Operator recovery (if it happens again)

```bash
# 1) Stop fuel
sudo systemctl stop netclaw-alert-receiver   # or block AM webhook
# silence bad alertname in AM / fix Prom rule and reload

# 2) Clear process storm
systemctl --user restart openclaw-gateway   # KillMode=control-group

# 3) Confirm rails
curl -s localhost:8099/metrics | grep netclaw_investigations
# suppressed_* should climb under abuse; in_flight ≤ MAX_CONCURRENT

# 4) Bring receiver back
sudo systemctl start netclaw-alert-receiver
```

Do **not** restart the gateway while hundreds of orphaned `hook:alert:*` sessions
are still “running” and the bad rule still fires—fix the rule first.

---

## Related

- `services/alert-receiver/README.md`
- `deploy/convergence/adapters/device-snmp/README.md`
- `specs/067-convergence/device-telemetry-greenfield.md`
