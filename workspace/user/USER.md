# User Profile

## About You

- **Name:** (your name here)
- **Role:** Network Engineer
- **Timezone:** (your timezone, e.g., America/New_York)

## Preferences

- **Communication style:** Technical, concise — include CLI output and protocol details
- **Report format:** Severity-sorted tables with HEALTHY / WARNING / CRITICAL ratings
- **Change management:** Lab mode — no ServiceNow CR required for demo devices
- **Escalation:** Not applicable for demo environment

## Your Network

- **Lab:** byrn-baker/Nautobot-Workshop — 20-node ContainerLab topology
- **Management subnet:** 192.168.220.0/24 (ContainerLab `clab-mgmt` network)
- **SP Core:** Cisco IOL 17.12.01 — P1-P4, PE1-PE3, CE1-CE2, RR1 (OSPF + MPLS + BGP)
- **DC Fabric:** Arista cEOS 4.34.0F — West/East spine-leaf with EVPN/VXLAN
- **Source of Truth:** Nautobot 2.4.10 (localhost:8080, admin/admin)
- **Golden Config:** nautobot-golden-config plugin with Design Builder data model
- **Testbed:** Defined in `testbed/testbed.yaml`

## Notes

- All devices are in the ContainerLab demo lab — relaxed change control
- Nautobot is populated via Design Builder (initial_design job)
- Device configs deployed via Ansible roles from the workshop repo
- IOL devices use admin/admin credentials
- cEOS devices use admin/admin credentials
