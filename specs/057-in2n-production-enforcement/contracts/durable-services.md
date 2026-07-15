# Contract: Durable Services Generator & Fault Isolation

## Generator (`scripts/in2n-services.py`)

```
scripts/in2n-services.py generate         # emit units for the mesh daemon + all always-on members
scripts/in2n-services.py enable            # systemctl --user enable --now each
scripts/in2n-services.py status            # per-unit active/failed (feeds fault isolation)
scripts/in2n-services.py disable <member>  # tear a member's unit down
```

- Idempotent regenerate (FR-015). The mesh unit template is checked into the repo; per-member units are generated from `risk.py` member rows where `managed_by == service`.
- Detects `systemctl --user`; if absent → writes units + prints the documented fallback and posture reports the durability aspect degraded (non-systemd host).

## Unit template — mesh daemon (checked into repo)

```ini
[Unit]
Description=NetClaw mesh daemon (BGP + NCFED eN2N + iN2N Border) — durable, feature 056/057
After=network-online.target

[Service]
Type=simple
WorkingDirectory=<repo>/mcp-servers/protocol-mcp
EnvironmentFile=-<home>/.openclaw/mesh.systemd.env
ExecStart=/usr/bin/python3 <repo>/mcp-servers/protocol-mcp/bgp-daemon-v2.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

## Unit template — per always-on member (generated)

```ini
[Unit]
Description=NetClaw iN2N member <member_id> — durable, feature 057
After=network-online.target netclaw-mesh.service
Wants=netclaw-mesh.service

[Service]
Type=simple
WorkingDirectory=<repo>
EnvironmentFile=-<member_env_file>
# production: ExecStart is sandbox-wrapped inside in2n-member.py via gateway.py (controls.md)
ExecStart=/usr/bin/python3 <repo>/scripts/in2n-member.py       # always-on: NO --idle-exit
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

## Single-owner reconciliation (`service.py::_cold_start`)

```python
launch_cmd, on_demand = self.risk.launch_spec(member_id)
managed_by = self.risk.managed_by(member_id)
if managed_by == "service":
    # never double-launch — ensure the unit is running instead of spawning
    await ensure_unit_active(f"netclaw-member-{slug(member_id)}.service")
    return await self._wait_for_dial(member_id)
# else: cold member — existing 056 behavior, sandbox-wrapped in production
```

## Fault isolation (`service.py` + heartbeat)

`health_report()` returns the HealthFaultReport (data-model §6) with `fault_class` precedence `daemon > member > backend > none`:
- **daemon**: the daemon/listener self-probe fails (or the status tool can't reach it).
- **member**: daemon up; a member channel absent/unhealthy — include `will_cold_start`.
- **backend**: daemon + member up, but a member task result reports its backend/device/API failed.

## Acceptance mapping

- FR-013/014/015/016, SC-005 (durable, generated, recover <60s, single-owner).
- FR-017/018, SC-006 (three distinct fault classes; heartbeat matches actual cause).
