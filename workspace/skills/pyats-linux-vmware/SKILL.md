---
name: pyats-linux-vmware
description: "VMware ESXi host operations via pyATS — VM inventory, snapshot management, hypervisor inspection across ESXi hosts in the testbed"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# VMware ESXi Host Operations

Manage and inspect VMware ESXi hypervisors in the pyATS testbed using `pyats_run_linux_command`. This skill covers VM inventory listing and snapshot inspection using the ESXi `vim-cmd` interface.

## Testbed Requirements

ESXi hosts must be defined in the pyATS testbed with `os: linux` (ESXi shell is Linux-based):

```yaml
devices:
  esxi-host-01:
    os: linux
    type: esxi
    connections:
      cli:
        protocol: ssh
        ip: 10.0.0.100
        port: 22
    credentials:
      default:
        username: "%ENV{NETCLAW_USERNAME}"
        password: "%ENV{NETCLAW_PASSWORD}"
```

**Note:** SSH must be enabled on the ESXi host (disabled by default). Enable via vSphere Client → Host → Configure → System → Services → SSH → Start.

## How to Call

All commands use `pyats_run_linux_command`:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"esxi-host-01","command":"<command>"}'
```

## Commands

### VM Inventory

#### List All Virtual Machines

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"esxi-host-01","command":"vim-cmd vmsvc/getallvms"}'
```

Returns a table of all VMs on the ESXi host:

| Column | Description |
|--------|-------------|
| **Vmid** | Unique VM identifier (used as parameter for other vim-cmd operations) |
| **Name** | VM display name |
| **File** | Path to the VMX configuration file on the datastore |
| **Guest OS** | Configured guest OS type (e.g., `ubuntu64Guest`, `windows9Server64Guest`) |
| **Version** | Virtual hardware version (e.g., `vmx-19`, `vmx-20`) |
| **Annotation** | VM description/notes |

**What to check:**
- All expected VMs are present and registered
- VMX file paths reference expected datastores
- Virtual hardware versions are current (old versions may lack features)
- Guest OS type matches actual installed OS
- No orphaned or unexpected VMs

### Snapshot Management

#### Get VM Snapshots

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"esxi-host-01","command":"vim-cmd vmsvc/snapshot.get 1"}'
```

The parameter is the **Vmid** from `vim-cmd vmsvc/getallvms`. Returns the snapshot tree for that VM:
- Snapshot name and description
- Snapshot ID
- Creation timestamp
- Whether it's the current snapshot (the "you are here" marker)
- Parent/child snapshot hierarchy

**What to check:**
- **Stale snapshots** — snapshots older than 72 hours degrade performance (growing delta disks)
- **Snapshot chains** — deep chains (>3 levels) cause I/O performance degradation
- **Pre-change snapshots** — verify a snapshot was taken before maintenance windows
- **Disk space** — snapshot delta files consume datastore space proportional to guest write activity

---

## Workflows

### 1. VMware Inventory Audit
```
pyats_list_devices → identify ESXi hosts in testbed
→ vim-cmd vmsvc/getallvms per host → collect all VMs
→ Cross-reference with NetBox/Nautobot → flag undocumented VMs
→ Check virtual hardware versions → flag outdated versions
→ GAIT
```

### 2. Snapshot Health Check
```
pyats_list_devices → identify ESXi hosts
→ vim-cmd vmsvc/getallvms per host → get VM IDs
→ vim-cmd vmsvc/snapshot.get per VM → collect snapshot trees
→ Flag: snapshots > 72 hours old, chains > 3 deep, orphaned snapshots
→ Severity-sort (stale snapshots = WARNING, deep chains = CRITICAL)
→ GAIT
```

### 3. Pre-Change VM Verification
```
ServiceNow CR must be in Implement state
→ vim-cmd vmsvc/getallvms → identify target VM by name → get Vmid
→ vim-cmd vmsvc/snapshot.get {vmid} → verify pre-change snapshot exists
→ If no snapshot: STOP — snapshot must be taken before changes
→ Record baseline state in GAIT
```

### 4. Multi-Host VM Inventory
```
pyats_list_devices → identify all ESXi hosts
→ vim-cmd vmsvc/getallvms per host (parallel) → collect fleet-wide VM inventory
→ Aggregate: total VMs, VMs per host, hardware version distribution
→ Cross-reference with vCenter inventory (if available)
→ GAIT
```

---

## Parallel Operations

Run VM inventory across multiple ESXi hosts concurrently:

```bash
# ESXi Host 1
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"esxi-host-01","command":"vim-cmd vmsvc/getallvms"}'

# ESXi Host 2
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"esxi-host-02","command":"vim-cmd vmsvc/getallvms"}'

# ESXi Host 3
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"esxi-host-03","command":"vim-cmd vmsvc/getallvms"}'
```

For snapshot checks, first collect VM IDs per host, then run snapshot queries in parallel across all VMs.

---

## vim-cmd Quick Reference

| Command | Description |
|---------|-------------|
| `vim-cmd vmsvc/getallvms` | List all registered VMs (ID, name, file, OS, version) |
| `vim-cmd vmsvc/snapshot.get {vmid}` | Get snapshot tree for a specific VM |
| `vim-cmd vmsvc/power.getstate {vmid}` | Get VM power state (on/off/suspended) |
| `vim-cmd vmsvc/get.summary {vmid}` | Get VM summary (CPU, memory, tools status) |

**Note:** Only `getallvms` and `snapshot.get` are covered by this skill. The reference above is for context — expand to other vim-cmd operations as needed.

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-linux-system** | System-level commands on the ESXi host (ps, ls, docker stats) |
| **pyats-linux-network** | ESXi host networking (interfaces, routes) — useful for vmkernel adapter inspection |
| **pyats-network** | Network device show commands complement ESXi host-level views |
| **pyats-parallel-ops** | pCall pattern for fleet-wide ESXi operations |
| **netbox-reconcile** | Cross-reference VM inventory with NetBox virtualization records |
| **nautobot-sot** | Validate ESXi host and VM data against Nautobot |
| **servicenow-change-workflow** | Gate snapshot operations behind ServiceNow Change Requests |
| **gait-session-tracking** | Every vim-cmd execution logged in GAIT |
| **nvd-cve** | Check ESXi versions against NVD vulnerability database |
| **cml-lab-lifecycle** | CML labs may run on ESXi — correlate VM inventory with CML topology |

---

## Guardrails

- **Always call `pyats_list_devices` first** — verify ESXi hosts exist in the testbed
- **Read-only operations only** — `getallvms` and `snapshot.get` are read-only
- **Never create/delete snapshots via this skill** — snapshot creation/deletion impacts VM performance and requires a ServiceNow CR
- **Never power-cycle VMs** — `vim-cmd vmsvc/power.*` operations are destructive and require explicit authorization
- **Validate Vmid before use** — always get the Vmid from `getallvms` output; never guess or hardcode
- **Flag stale snapshots** — any snapshot > 72 hours should be flagged as WARNING; > 7 days as CRITICAL
- **SSH access concerns** — ESXi SSH is often disabled in production; document that it must be enabled for pyATS access
- **Record in GAIT** — every vim-cmd execution must be logged
