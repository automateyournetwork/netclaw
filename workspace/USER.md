# User Profile

## About You

- **Name:** Byrn Baker
- **Role:** Network Engineer
- **Timezone:** America/Denver (MDT, UTC-6)
- **Location:** Denver, CO

## Preferences

- **Communication style:** Technical, concise — include CLI output and protocol details
- **Report format:** Severity-sorted tables with HEALTHY / WARNING / CRITICAL ratings
- **Change management:** Home/production network — treat changes with care; propose
  before applying anything that touches the firewall, switches, or live services
- **Escalation:** Post findings to Discord; wait for human approval on any change

## The Network You Care For

This is a **live home/production network**, not a lab. The site is **"House"**.

- **Source of Truth:** Nautobot at **https://192.168.3.253** — the authoritative
  inventory for all managed devices and VMs
- **Gateway / Firewall:** pfSense-FW01 (Netgate 8200 Max, pfSense Plus) at **192.168.3.1**
  (web/API on port **440**: https://192.168.3.1:440)
- **Core switches:** HomeSwitch01 (192.168.3.2) and HomeSwitch02 (192.168.3.3) —
  Cisco Catalyst WS-C3850-48P, IOS-XE. **Old switches — require legacy SSH key
  exchange** (see TOOLS.md).
- **Virtualization:** Proxmox on r640-pve (**192.168.100.20**, also
  proxmox.home.byrnbaker.me:443) — hosts the VMs that are modeled in Nautobot
- **Observability:** home-obs-stack at **192.168.3.250** (Prometheus, Grafana, Loki,
  VictoriaMetrics, Alertmanager)
- **Management network:** VLAN 3 / **192.168.3.0/24** (network devices, mgmt, OBS,
  Nautobot, NetClaw)
- **Models:** Ollama Cloud (`https://ollama.com`), default `deepseek-v4-pro:cloud`.
  (The former local-ai Ollama box at 192.168.30.50 has been decommissioned.)

## Notes

- Alerts you investigate are about the **home network** (192.168.3.x mgmt, plus the
  HomeLan/IOT/K3S VLANs). See TOOLS.md for the full VLAN map.
- Credentials live in `~/.openclaw/.env` — never in skill files or these docs.
- The pyATS testbed is auto-generated from Nautobot; regenerate with
  `scripts/generate-testbed-from-nautobot.py`.
