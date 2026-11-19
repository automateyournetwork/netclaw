---
name: percepxion-oob
description: "Lantronix out-of-band console servers (SLC 9000, SLC 8000, EMG) through the Percepxion and SLC MCP servers: confirm a device's console path before a change, find the console path for a device named in NetBox or Nautobot, run SLC CLI diagnostics, and manage the console-server fleet (inventory, firmware, configuration, access audit). Use when a task touches a console server, a serial console path, or Percepxion. Not for the managed router's or switch's own CLI (pyats skills) or for reconciling NetBox itself (netbox-reconcile)."
version: 1.1.0
license: Apache-2.0
user-invocable: true
tags: [lantronix, percepxion, oob, out-of-band, console-server, slc9000, slc8000, emg, serial-console, preflight, netbox, nautobot, network-automation]
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PERCEPXION_USERNAME", "PERCEPXION_PASSWORD"] } } }
---

# Percepxion OOB

Lantronix console servers (SLC 9000, SLC 8000, EMG) are cabled to the console ports of routers,
switches, firewalls and servers, and Percepxion manages the console servers as a fleet. This skill
gives an agent three things: a verified console path to a device before it changes that device,
fleet operations on the console servers themselves, and an audit trail for both. The same path is
the way in when a device's in-band management is down.

Setup, environment variables and credential providers: [references/setup.md](references/setup.md).
Step-by-step workflows and tool parameters: [references/workflows.md](references/workflows.md).
NetBox, Nautobot and Ansible integration: [references/source-of-truth.md](references/source-of-truth.md).

## Two kinds of device

Every request involves one or both of these, and they are different identity spaces:

| Term | What it is | How tools refer to it |
|---|---|---|
| **Console server** (OOB device) | The Lantronix unit Percepxion manages | `device_id` in every Percepxion tool, from `get_device_list` or `get_device_details` |
| **Managed device** (attached device) | The router, switch, firewall or server whose console port is cabled to a console server port | Reported per port by `get_port_telemetry` (one port) or `get_security_telemetry` (all ports): hostname, model, serial, IP, OS |

`device_id` is always the console server. `send_direct_cli_command` runs on the console server's
own CLI (`show deviceport port 4`, `show portstatus`, `show sysstatus`, `diag ping <ip>`), never on
the managed device, so Cisco or Junos syntax fails there. When an operator says "run this on the
device" and it isn't clear which one, ask.

## Which server answers

| Need | Use |
|---|---|
| Anything across the fleet: inventory, firmware compliance and rollout, Smart Groups, configuration, audit logs, CLI jobs through the cloud | **percepxion-mcp-server** (asynchronous: job, then fetch output) |
| One unit the agent can reach on its management IP: synchronous CLI output, sessions, cellular status, firmware bootbanks | **slc-mcp-server** (optional; no fleet concept) |
| Which console server port a managed device is cabled to, as recorded intent | **NetBox** (`netbox-mcp`) or **Nautobot** (`nautobot-mcp`), when the Lantronix sync plugins or `lantronix.oob` keep them current |

Every Percepxion workflow below works with percepxion-mcp-server alone. Use slc-mcp-server when the
answer has to come straight from the unit, or when Percepxion doesn't expose the capability.

## Rules

1. **Authenticate first.** Call `login_with_env` before any other Percepxion tool. It works for
   every credential provider, not only environment variables.
2. **Confirm the target before acting.** Resolve the console server with `get_device_details`, then
   confirm which managed device is on the port with `get_port_telemetry`. `list_device_ports`
   reports port state only, not who is attached, and an empty result from it doesn't mean nothing
   is attached.
3. **Get explicit operator approval for anything that changes state**, naming the unit and the
   effect: firmware pushes, configuration updates and clones, reboots, removal from the platform,
   user suspension (`set_user_access`), and write-mode CLI. Rebooting a console server drops console
   access to every device on it. Production changes follow the change-request process in
   `servicenow-change-workflow`.
4. **Track every job to the end.** `send_direct_cli_command`, `update_firmware_by_smart_group`,
   `reboot_device` and `request_device_syslog_upload` return a job group ID. Poll `get_job_group`
   until it reports Completed or Failed. CLI text comes only from `get_cli_command_output` with the
   same `job_group_id` and `device_id`; `get_job_group` never contains it. An empty result before
   completion means "not yet", so wait and retry. For a job across several units, use
   `get_job_results_by_device`. Report success from the device's own output, never from job status.
5. **Pass `organization_id` when the account is a Project Admin.** Project Admin sessions span every
   organization in the project, so job, telemetry, content, Smart Group and audit tools need it
   (`list_organizations` finds it). Tenant Admin and Tenant User sessions are scoped automatically.
   Inventory tools (`get_device_list`, `get_device_details`, `list_device_ports`) never need it.
6. **The CLI policy belongs to the operator.** Both servers start read-only and keep a deny list for
   destructive commands. Only the person who runs the server can enable writes, and the agent never
   edits those settings. When the operator authorizes a write, record that in the call's
   `description`.
7. **Put the reason in every `description`.** It lands in Percepxion's audit trail next to the
   command, so include the change request, incident or orchestrator execution ID. Log the session in
   GAIT (`gait-session-tracking`).
8. **Keep secrets out of output.** Never echo credentials, tokens or session IDs, and use the
   production API URL unless the operator names another instance.

## Workflows

| # | Workflow | Use it when |
|---|---|---|
| W1 | Discovery and inventory | Starting a session, or asked what console servers exist, where, and on what firmware |
| W2 | **Preflight: console path ready** | Before any automated or risky change to a managed device. Run it first |
| W3 | SLC CLI diagnostics | Checking console server health, a port's signals, or reachability from the console server |
| W4 | Firmware compliance and rollout | Compliance reviews, maintenance windows, coordinated patching |
| W5 | Access audit | Who reached which console server, when, and what they ran |
| W6 | Console server configuration | Reading, updating or cloning console server settings |
| W7 | Console server lifecycle | Onboarding, reboot, decommission, syslog upload |
| W8 | Incident evidence and remediation | An orchestrator or alert hands over a device that's unreachable in-band |
| W9 | Console path from NetBox or Nautobot | The operator names a device the way the source of truth knows it |
| W10 | Console coverage gate | A change touches several devices and each needs a ready console path |

W1 to W8 are in [references/workflows.md](references/workflows.md); W9 and W10 are in
[references/source-of-truth.md](references/source-of-truth.md).

### W2 in brief

1. `get_device_details` on the console server: online, recent check-in. Offline means there's no
   console path; stop and report.
2. `get_port_telemetry` on the port: a managed device is attached and its hostname (and serial,
   when known) matches the change target. No device, or a different one, means stop.
3. Optional detail: `send_direct_cli_command` with `show deviceport port <N>` for signals and the
   port's SSH setting.
4. Pass, or fail with the specific reason. If the operator overrides a failure, record the override
   in the `description` of every later call; it doesn't bypass the server's CLI policy.

When the change target has no console server at all, preflight doesn't apply; that isn't a failure.
When a console server exists but its path isn't ready, say so before the change starts.

## Reaching a managed device's console

The skill finds the path; the interactive session belongs to the operator. Neither MCP server opens
an interactive serial session.

1. Find the port: W9 from NetBox or Nautobot, or `list_device_ports` with the managed device's name
   as `device_id` (it searches port names and labels and returns `parent_device_id` and
   `port_number`).
2. Confirm it with W2 steps 1 and 2.
3. Return `ssh -p <SSH port> <user>@<console server management IP>`. The factory SSH port is
   3000 + the port number; a unit can change it per port, and the Lantronix NetBox and Nautobot
   plugins record the configured value. Direct SSH is off per port by default, so a refused
   connection usually means it hasn't been enabled. Turning it on is the operator's configuration
   change.

## Related skills

- `netbox-reconcile`: a mismatch between NetBox and what the console server reports goes there as a
  discrepancy. This skill doesn't write to NetBox or Nautobot.
- `nautobot-sot`: Nautobot IPAM lookups. Console cabling and the coverage gate job are covered in W9
  and W10.
- `aap-automation`, `aap-eda`: run the `lantronix.oob` coverage gate role and the
  `percepxion_events` rulebook from Ansible Automation Platform.
- `servicenow-change-workflow`, `gait-session-tracking`: change approval and the audit record.
- `pagerduty-incidents`, `itential-automation`: alerts and orchestrations that start W8, and where
  its result goes back.
- `kepner-tregoe-network-troubleshooting`: the diagnostic method when the fault isn't obvious; W3
  and W8 supply the console-side evidence.
- `pyats-troubleshoot` and the other pyATS skills: the managed device's own CLI once it's reachable.
