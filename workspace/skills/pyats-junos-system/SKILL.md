---
name: pyats-junos-system
description: "JunOS system operations via pyATS — chassis health, hardware inventory, system info, NTP, SNMP, files/logs, firewall counters, DDoS protection, services accounting"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# JunOS System Operations via pyATS

Inspect Juniper device chassis health, hardware inventory, system state, NTP, SNMP, firewall counters, DDoS protection, and services accounting using pyATS `pyats_run_show_command`. This complements the JunOS MCP server (PyEZ/NETCONF) with SSH/CLI-based operational commands and Genie parser support.

## Testbed Requirements

Juniper devices in the pyATS testbed with `os: junos`:

```yaml
devices:
  juniper-rtr-01:
    os: junos
    type: router
    connections:
      cli:
        protocol: ssh
        ip: 10.0.0.1
        port: 22
    credentials:
      default:
        username: "%ENV{NETCLAW_USERNAME}"
        password: "%ENV{NETCLAW_PASSWORD}"
```

## How to Call

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"<command>"}'
```

---

## Commands

### Chassis Health & Hardware

#### Chassis Alarms
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis alarms"}'
```
Active alarms on the chassis. **Check first** — any active alarm indicates a hardware or environmental issue.

#### Chassis Environment
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis environment"}'
```
Temperature, fan speed, power supply status across all components. Variants:
- `show chassis environment fpc` — FPC-specific temperature and status
- `show chassis environment routing-engine` — RE temperature and status
- `show chassis environment {component}` — Specific component (e.g., `cb0`, `pem0`)

#### Chassis FPC (Flexible PIC Concentrators)
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis fpc"}'
```
FPC slot status, state (Online/Offline), temperature, CPU/memory utilization. Variants:
- `show chassis fpc detail` — Extended FPC details including uptime
- `show chassis fpc pic-status` — PIC status within each FPC slot

#### Chassis PIC
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis pic fpc-slot 0 pic-slot 0"}'
```
Specific PIC details — port types, speeds, operational state.

#### Chassis Hardware
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis hardware"}'
```
Hardware inventory: model, serial numbers, descriptions for all components (RE, FPC, PIC, PEM, fan trays). Variants:
- `show chassis hardware detail` — Extended details with part numbers
- `show chassis hardware detail no-forwarding` — Skip forwarding engine details
- `show chassis hardware extensive` — Maximum hardware detail
- `show chassis hardware extensive no-forwarding` — Extensive without forwarding

#### Chassis Fabric
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis fabric summary"}'
```
Switch fabric plane status. Also: `show chassis fabric plane` for per-plane details.

#### Chassis Firmware
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis firmware"}'
```
Firmware versions on all components. Also: `show chassis firmware no-forwarding`.

#### Chassis Power
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis power"}'
```
Power supply status, input/output watts, capacity, redundancy mode.

#### Chassis Routing Engine
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show chassis routing-engine"}'
```
RE slot, status, model, memory, CPU utilization, uptime, load averages. Also: `show chassis routing-engine no-forwarding`.

### System Information

#### Version
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show version"}'
```
JunOS version, hostname, model, serial number. Variants:
- `show version detail` — Build info, kernel version
- `show version detail no-forwarding` — Skip forwarding engine
- `show version invoke-on all-routing-engines` — Version on all REs (dual RE systems)

#### System Uptime
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system uptime"}'
```
Current time, uptime, last configured timestamp, boot time, protocol daemon restart. Also: `show system uptime no-forwarding`.

#### System Information
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system information"}'
```
Hardware model, serial, hostname, domain.

#### System Users
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system users"}'
```
Currently logged-in users — terminal, login time, idle time, source IP.

#### System Commit History
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system commit"}'
```
Configuration commit history — who committed, when, commit comment.

#### System Storage
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system storage"}'
```
Filesystem usage — /dev/gpt, /var, /config. Also: `show system storage no-forwarding`.

#### System Buffers
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system buffers"}'
```
Kernel buffer pool statistics. Also: `show system buffers no-forwarding`.

#### System Queues
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system queues"}'
```
Packet queue statistics. Also: `show system queues no-forwarding`.

#### System Statistics
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system statistics"}'
```
Protocol statistics (IP, ICMP, TCP, UDP counters). Also: `show system statistics no-forwarding`.

#### System Connections
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system connections"}'
```
Active TCP/UDP connections on the RE — useful for verifying management sessions.

#### System Core Dumps
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show system core-dumps"}'
```
Core dump files — indicates past crashes. Also: `show system core-dumps no-forwarding`.

#### Task Memory & Replication
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show task memory"}'
```
Routing protocol daemon memory usage per task (BGP, OSPF, IS-IS, etc.). Also: `show task replication` for GRES/NSR replication state.

### NTP

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ntp associations"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ntp status"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show configuration system ntp"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show configuration system ntp | display set"}'
```

### SNMP

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show snmp statistics"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show snmp mib walk system"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show configuration snmp"}'
```

### Files & Logs

#### File Listing
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"file list"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"file list /var/log detail"}'
```
Browse filesystem — check log sizes, config backups, core dumps.

#### Log Files
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show log messages"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show log messages | match OSPF"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show log messages | match BGP | except Peer"}'
```
Flexible log filtering with match/except pipes.

### Firewall Filters

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show firewall"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show firewall log"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show firewall counter filter my-filter block"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show firewall counter filter my-filter my-counter"}'
```

### DDoS Protection

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ddos-protection statistics"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ddos-protection protocols ospf"}'
```

### Services Accounting

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show services accounting status"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show services accounting flow"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show services accounting usage"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show services accounting memory"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show services accounting errors"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show services accounting aggregation template template-name my-template extensive"}'
```

### Security

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show security policies hit-count"}'
```

---

## Workflows

### 1. JunOS Chassis Health Check
```
pyats_list_devices → identify JunOS devices
→ show chassis alarms → active alarms (CRITICAL if any)
→ show chassis environment → temperature, fans, power
→ show chassis fpc → FPC online/offline, CPU/memory
→ show chassis routing-engine → RE status, load averages
→ show chassis hardware → hardware inventory baseline
→ Severity-sort → GAIT
```

### 2. JunOS System Audit
```
show version → JunOS version, model, serial
→ show system uptime → device stability
→ show system commit → recent config changes
→ show system storage → disk usage (>80% = WARNING)
→ show system core-dumps → crash history (any = WARNING)
→ show ntp associations → time sync (stratum, offset)
→ Cross-reference version with NVD CVE → vulnerability exposure
→ GAIT
```

### 3. JunOS Security Posture
```
show firewall → active filters
→ show firewall log → recent filter hits
→ show ddos-protection statistics → DDoS protection state
→ show security policies hit-count → policy utilization
→ show snmp statistics → SNMP polling load
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **junos-network** | JunOS MCP (PyEZ/NETCONF) for config management; pyATS for operational CLI show commands |
| **pyats-junos-interfaces** | Interface-specific commands complement chassis/system view |
| **pyats-junos-routing** | Routing protocol commands complement system/hardware view |
| **pyats-health-check** | Extend standard health checks to include JunOS chassis metrics |
| **netbox-reconcile** | Cross-reference chassis hardware (serial, model) with NetBox DCIM |
| **nvd-cve** | Scan JunOS versions from `show version` against NVD |
| **gait-session-tracking** | Every command logged in GAIT |

---

## Guardrails

- **All commands are read-only** — show, file list, and status commands only
- **Always check `show chassis alarms` first** — active alarms take priority
- **Cross-reference with SoT** — compare hardware inventory with NetBox/Nautobot
- **Record in GAIT** — every command execution must be logged
