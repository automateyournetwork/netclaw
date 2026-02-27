---
name: pyats-linux-system
description: "Linux host system operations via pyATS — process monitoring, filesystem inspection, Docker container stats, package/tool verification across fleet hosts"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Linux Host System Operations

Manage and inspect Linux hosts in the pyATS testbed using `pyats_run_linux_command`. This skill covers process monitoring, filesystem inspection, Docker container resource usage, and system tool verification.

## Testbed Requirements

Linux hosts must be defined in the pyATS testbed with `os: linux`:

```yaml
devices:
  linux-host-01:
    os: linux
    type: linux
    connections:
      cli:
        protocol: ssh
        ip: 10.0.0.50
        port: 22
    credentials:
      default:
        username: "%ENV{NETCLAW_USERNAME}"
        password: "%ENV{NETCLAW_PASSWORD}"
```

## How to Call

All commands use `pyats_run_linux_command`:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"<command>"}'
```

## Commands

### Process Monitoring

#### List All Running Processes

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"ps -ef"}'
```

Returns full process listing: UID, PID, PPID, CPU time, start time, command. Use for capacity planning, runaway process detection, and baseline comparison.

#### Search for Specific Processes

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"ps -ef | grep nginx"}'
```

Filter processes by name. Common targets:
- `ps -ef | grep python` — Python services (MCP servers, automation agents)
- `ps -ef | grep docker` — Docker daemon and containers
- `ps -ef | grep ssh` — SSH connections
- `ps -ef | grep java` — Java applications (Kafka, Elasticsearch)
- `ps -ef | grep node` — Node.js services (MCP servers)

### Docker Container Operations

#### Container Resource Usage

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"docker stats --no-stream"}'
```

Returns point-in-time container stats: CPU %, memory usage/limit, network I/O, block I/O, PIDs. The `--no-stream` flag captures a single snapshot (no continuous output).

**What to check:**
- CPU > 80% sustained — container may need resource limits or horizontal scaling
- Memory near limit — risk of OOM kill
- Network I/O spikes — correlate with application traffic patterns
- High PID count — possible fork bomb or thread leak

### Filesystem Inspection

#### List Files (Current Directory)

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"ls -l"}'
```

#### List Files (Specific Directory)

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"ls -l /var/log"}'
```

Common directories to inspect:
- `/var/log` — System and application logs (check sizes, rotation)
- `/etc` — Configuration files (verify expected configs exist)
- `/tmp` — Temporary files (check for disk space issues)
- `/opt` — Third-party applications
- `/home` — User home directories

### System Tool Verification

#### Check curl Version and Capabilities

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"curl -V"}'
```

Returns curl version, supported protocols (HTTP, HTTPS, FTP, SFTP, etc.), and TLS library info. Use to verify:
- curl is installed and functional
- HTTPS/TLS support is available (needed for API calls)
- Protocol support matches requirements (e.g., HTTP/2, SFTP)

---

## Workflows

### 1. Linux Host Health Check
```
pyats_list_devices → identify Linux hosts in testbed
→ pyats_run_linux_command(host, "ps -ef") → check for expected services
→ pyats_run_linux_command(host, "docker stats --no-stream") → container resource usage
→ pyats_run_linux_command(host, "ls -l /var/log") → check log file sizes
→ Severity-sort findings → GAIT
```

### 2. Docker Fleet Monitoring
```
pyats_list_devices → identify all Docker hosts
→ pyats_run_linux_command per host ("docker stats --no-stream") → collect stats
→ Aggregate: CPU hotspots, memory pressure, network I/O
→ Flag containers approaching resource limits
→ GAIT
```

### 3. Process Audit
```
pyats_list_devices → identify target Linux hosts
→ pyats_run_linux_command per host ("ps -ef") → collect all processes
→ Compare against expected process baseline
→ Flag unexpected processes (security concern) or missing processes (service failure)
→ GAIT
```

### 4. System Readiness Check
```
pyats_run_linux_command(host, "curl -V") → verify curl/TLS
→ pyats_run_linux_command(host, "ls -l /opt/application") → verify app installed
→ pyats_run_linux_command(host, "ps -ef | grep application") → verify app running
→ pyats_run_linux_command(host, "docker stats --no-stream") → verify containers healthy
→ GAIT
```

---

## Parallel Operations

Run the same command across multiple Linux hosts concurrently using the pCall pattern:

```bash
# Host 1
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"docker stats --no-stream"}'

# Host 2
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-02","command":"docker stats --no-stream"}'

# Host 3
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-03","command":"docker stats --no-stream"}'
```

All hosts execute concurrently. Results aggregated by the agent.

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-network** | `pyats_run_linux_command` is tool 7 in the pyATS MCP — same server, different target OS |
| **pyats-parallel-ops** | pCall pattern for fleet-wide Linux host operations |
| **pyats-health-check** | Extend network health checks to include Linux host health |
| **pyats-linux-network** | Network-focused Linux commands (ifconfig, ip route, netstat, route) |
| **pyats-linux-vmware** | VMware ESXi host operations (vim-cmd) for hypervisor management |
| **netbox-reconcile** | Cross-reference Linux host inventory with NetBox DCIM records |
| **gait-session-tracking** | Every Linux command execution logged in GAIT |

---

## Guardrails

- **Always call `pyats_list_devices` first** — verify Linux hosts exist in the testbed before running commands
- **Read-only by default** — all commands in this skill are read-only (ps, ls, docker stats, curl -V)
- **No destructive commands** — never use kill, rm, shutdown, reboot, or service stop via this skill
- **Gate write operations behind ServiceNow** — if extending to write operations, require a Change Request
- **Sanitize grep patterns** — when using `ps -ef | grep`, ensure the pattern doesn't contain shell metacharacters
- **Record in GAIT** — every Linux command execution must be logged
