# Device telemetry config checklist — site `home`

Generated: 2026-07-26T04:22:16Z  
By: `scripts/render-convergence-telemetry.py` (Phase 10)  

Secrets stay in env — **never** commit community strings.

## Convergence collector endpoints

| Item | Value |
|------|-------|
| SNMP community env | `SNMP_COMMUNITY` (set in `deploy/convergence/.env`) |
| Syslog destination | `192.168.3.252` UDP port **1514** |
| SNMP poller | Convergence snmp_exporter (compose profile `device-snmp`) |

## Inventory targets

| Name | IP | Role | Vendor | Template |
|------|-----|------|--------|----------|
| HomeSwitch01 | 192.168.3.2 | switch | cisco | cisco |
| HomeSwitch02 | 192.168.3.3 | switch | cisco | cisco |
| HomeSwitch04 | 192.168.3.5 | switch | cisco | cisco |

## SNMP (read-only) — device side

Set a read-only community and put the same value in `SNMP_COMMUNITY` on the NetClaw host.

### Cisco IOS / IOS-XE

```text
snmp-server community <value-from-SNMP_COMMUNITY> RO
! optional: snmp-server location ...
```

### pfSense

1. **Services → SNMP** — enable SNMP, set read community to match `SNMP_COMMUNITY`.
2. Ensure LAN/mgmt ACL allows the Convergence host to poll UDP/161.

## Syslog — device side

Send device syslog to **192.168.3.252:1514** (UDP) when `device_telemetry.syslog.enabled` / profile `device-syslog` is on.

### Cisco

```text
logging host 192.168.3.252 transport udp port 1514
logging trap informational
```

### pfSense

**Status → System Logs → Settings** (or **Services → Syslog**): remote server `192.168.3.252`, port `1514`.

## Verify (after apply)

```bash
./scripts/convergence-telemetry-apply.sh   # if not already applied
./deploy/convergence/smoke-device-snmp.sh
# Named interfaces:
curl -sG 'http://127.0.0.1:9090/api/v1/query' \
  --data-urlencode 'query=count by (device_name,interface_name) (interface_status)'
# Grafana: http://127.0.0.1:3300 → folder Convergence
```

## Non-goals (v1)

- Auto-push of this config onto devices (checklist only).
- Committing real community strings.
