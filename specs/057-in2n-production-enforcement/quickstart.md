# Quickstart: iN2N Production-Mode Enforcement & Durable Runtime

How an operator turns a risk into an honestly-enforced, durable production risk — and how to verify each guarantee. Assumes a working 056 risk (Border + members) and the installed `defenseclaw` + `openshell` CLIs.

## 1. Make the runtime durable (any mode)

```bash
# Generate + enable the mesh daemon unit and one unit per always-on member
python3 scripts/in2n-services.py generate
python3 scripts/in2n-services.py enable
systemctl --user status 'netclaw-*.service'   # mesh + per-member, all active, Restart=always
```

Verify resilience (SC-005):
```bash
systemctl --user kill netclaw-mesh.service        # simulate a crash
sleep 10 && systemctl --user is-active netclaw-mesh.service   # -> active (auto-restarted)
# log out / reboot -> all netclaw-*.service come back on their own
```

## 2. Turn on production enforcement

```bash
# in ~/.openclaw/mesh.systemd.env (and per-member env)
N2N_RISK_MODE=production
# optional: block on ANY missing control, including audit
# N2N_STRICT_ALL=1
systemctl --user restart netclaw-mesh.service
```

## 3. Check the posture (US1)

```bash
# via the n2n-mcp status tool (or the HUD posture panel / operator heartbeat)
openclaw agent -m "what is my risk posture?"
# -> "production — enforced" with sandbox, model-guard, audit all active
```

Force a degraded state and confirm honesty (SC-001):
```bash
# stop DefenseClaw's guard path, then:
openclaw agent -m "risk posture?"
# -> "production — DEGRADED (model-guard missing)"  (never "enforced")
```

## 4. Verify each control

**Sandbox (US2, SC-002)** — a member runs under OpenShell in production:
```bash
openclaw agent -m "how many snapshots in IP Fabric?"   # routes to the ipfabric member
# the member process is a child of `openshell`; with openshell unavailable the
# delegation is REFUSED (fail-closed), posture -> degraded(sandbox)
```

**Model-guard + scan (US3, SC-003)** — with DefenseClaw down, a delegation fails closed:
```bash
# stop defenseclaw guard, then delegate -> result.enforcement == "refused:model-guard"
# (never silently runs through a direct provider)
```

**GAIT trail (US4, SC-004)** — every federation event is a git commit + a SQLite row:
```bash
git -C ~/.openclaw/n2n/gait log --oneline | head
# one commit per delegation/enrollment/removal/quarantine; SHAs match remote_invocation_record.gait_ref
```

## 5. Degraded policy (SC-008)

| Missing control | Default behavior | result.enforcement |
|-----------------|------------------|--------------------|
| sandbox OR model-guard (containment) | delegation **refused** | `refused:<control>` |
| GAIT (audit only) | delegation **runs**, loudly flagged | `audit-degraded` |
| any, with `N2N_STRICT_ALL=1` | delegation **refused** | `refused:<control>` |

## 6. Fault isolation (US6, SC-006)

```bash
# daemon down  -> heartbeat: "federation-layer/daemon fault"     (not a member flap)
# member down  -> heartbeat: "<member> down (will cold-start)"
# backend down -> a task reports "backend unreachable", NOT a federation fault
```

## 7. Regression guard (SC-007)

```bash
cd /home/johncapobianco/netclaw && pytest tests/n2n/   # 44 eN2N regression + 45 iN2N + new 057 tests all green
```
