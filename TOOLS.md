# TOOLS.md — Local Infrastructure Notes

Skills define *how* tools work. This file is for *your* specifics — the environment details that are unique to your deployment.

## Network Devices

Devices are defined in `testbed/testbed.yaml`. Update that file with your SSH-accessible Cisco devices.

```
### Example Device Map
- R1 → 10.1.1.1, Core Router, IOS-XE 17.9
- R2 → 10.1.1.2, Distribution Router, IOS-XE 17.9
- SW1 → 10.1.2.1, Access Switch, IOS-XE 17.9
- SW2 → 10.1.2.2, Access Switch, IOS-XE 17.9
```

## Platform Credentials

All credentials are in `~/.openclaw/.env`. Never put credentials in skill files or this document.

```
### Connection Details (reference only — actual values in .env)
- pyATS Testbed       → PYATS_TESTBED_PATH
- NetBox              → NETBOX_URL, NETBOX_TOKEN
- ServiceNow          → SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD
- Cisco APIC          → APIC_URL, APIC_USERNAME, APIC_PASSWORD
- Cisco ISE           → ISE_BASE, ISE_USERNAME, ISE_PASSWORD
- NVD API             → NVD_API_KEY
- F5 BIG-IP           → F5_IP_ADDRESS, F5_AUTH_STRING
- Catalyst Center     → CCC_HOST, CCC_USER, CCC_PWD
```

## Slack Integration

```
### Channels
- #netclaw-alerts     → P1/P2 critical alerts
- #netclaw-reports    → Scheduled health reports, audit results
- #netclaw-general    → General queries, P3/P4 notifications
- #incidents          → Active incident threads
```

## SSH Access

```
### Jump Hosts / Bastion
- (your bastion host, if applicable)

### Console Servers
- (your console server, if applicable)
```

## Site Information

```
### Sites
- Site-A → Primary data center
- Site-B → DR site
- Lab    → Non-production test environment (relaxed change control)
```

## Notes

- Add whatever helps NetClaw do its job — device nicknames, maintenance windows, ISP circuit IDs, TAC case numbers, anything environment-specific.
- This file is yours. Skills are shared. Keeping them apart means you can update skills without losing your notes.
