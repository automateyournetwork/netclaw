# Device-side SNMP / syslog snippets (Phase 10 T131)

Generated checklists (`deploy/convergence/generated/device-config-checklist.md`)
embed site-specific host/port. This file is the **canonical vendor MoP** used by
operators and by the checklist generator.

Secrets: set community in env `SNMP_COMMUNITY` only — never commit values.

## Variables

| Placeholder | Meaning |
|-------------|---------|
| `<COMMUNITY>` | Value of `SNMP_COMMUNITY` on the NetClaw host |
| `<CONVERGENCE_HOST>` | IP of the host running snmp_exporter / promtail |
| `<SYSLOG_PORT>` | Default **1514** (UDP) for Convergence promtail |

---

## Cisco IOS / IOS-XE

### SNMP (read-only)

```text
configure terminal
snmp-server community <COMMUNITY> RO
! optional source interface / ACL
! snmp-server community <COMMUNITY> RO 99
! access-list 99 permit <CONVERGENCE_HOST>
end
write memory
```

### Syslog

```text
configure terminal
logging host <CONVERGENCE_HOST> transport udp port <SYSLOG_PORT>
logging trap informational
logging origin-id hostname
end
write memory
```

### Verify on box

```text
show snmp community
show logging
```

---

## pfSense

### SNMP

1. **Services → SNMP**
2. Enable SNMP daemon
3. Read community string = `<COMMUNITY>` (same as `SNMP_COMMUNITY`)
4. Bind interfaces: LAN / management only
5. Ensure firewall rule allows **UDP/161** from `<CONVERGENCE_HOST>`

### Syslog

1. **Status → System Logs → Settings** (or **Services → Syslog**)
2. Enable remote logging
3. Remote log servers: `<CONVERGENCE_HOST>`
4. Port: `<SYSLOG_PORT>` (UDP)
5. Save / apply

### Verify

- Diagnostics → Routes / packet capture optional
- From Convergence host:  
  `curl -sG 'http://127.0.0.1:9117/snmp' --data-urlencode 'target=<PFSENSE_IP>' --data-urlencode 'module=pfsense' --data-urlencode 'auth=public_v2' | head`

---

## Generic IF-MIB device

Enable SNMPv2c read-only community `<COMMUNITY>` on the management VRF/interface.
Point syslog at `<CONVERGENCE_HOST>:<SYSLOG_PORT>` if the OS supports remote syslog.

Use inventory `template: generic`.

---

## After device config

```bash
./scripts/convergence-telemetry-apply.sh
./deploy/convergence/smoke-device-snmp.sh
```

See also: `specs/067-convergence/telemetry-setup.md`,  
`docs/CONVERGENCE-ALERT-SAFETY.md`.
