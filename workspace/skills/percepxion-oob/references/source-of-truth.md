# NetBox, Nautobot and Ansible

Percepxion knows what each console server reports: its ports, their state, and the device each
port sees. NetBox or Nautobot holds the intent: which device's console should be cabled to which
console server port. With both, an agent can find a device's console path by the name the source of
truth uses, check it against the hardware, and grade a whole change's console coverage before it
starts.

This skill only reads NetBox and Nautobot. The Lantronix plugins and Ansible playbooks below do the
writing, on the operator's schedule.

## Public Lantronix integrations

| Integration | What it maintains or provides | Where |
|---|---|---|
| **netbox-lantronix** (NetBox plugin) | Console servers created from Percepxion with the right device type; console server port labels (the name set on the unit) and descriptions (attached device hostname); optional console cables that follow what each port reports; an **Open console** button using each port's configured SSH port; the `ConsoleCoverageGate` script | `pip install netbox-lantronix`; https://github.com/Lantronix/netbox-lantronix |
| **nautobot-app-ssot-lantronix** (Nautobot SSoT app) | The **Percepxion to Nautobot** job: the same inventory, with Percepxion facts in custom fields; optional console cables; **Open console**; the **AOOB console coverage gate** job | `pip install nautobot-app-ssot-lantronix`; https://github.com/Lantronix/nautobot-app-ssot-lantronix |
| **lantronix.oob** (Ansible collection, 1.4.0 or later) | `playbooks/combo/netbox_sync.yml` (fills NetBox, including a `percepxion_device_id` custom field); the `oob_coverage_gate` role, which runs either gate; the `percepxion_events` Event-Driven Ansible source and `percepxion_console_events` rulebook; a Percepxion inventory plugin | Red Hat Automation Hub, or a release tag from https://github.com/Lantronix/ansible-collection-oob |
| **Device types** | SLC 9000 types in the NetBox community device-type library; SLC 8000 and EMG types in each plugin's `docker/device-types` folder | https://github.com/netbox-community/devicetype-library |

Both plugins read Percepxion with a `tenant_user` account and never write to Percepxion or to a
console server.

### Fields this skill reads

| Source | Object | Field | Meaning |
|---|---|---|---|
| Nautobot | Console server | `percepxion_device_id`, `lx_mgmt_ip`, `lx_firmware_version` | Percepxion `device_id`, management address, firmware |
| Nautobot | Console server port | `lx_port_state`, `lx_attached_hostname`, `lx_attached_serial`, `lx_ssh_port` | Port state, attached device, and the port's SSH port (`off` when SSH to it is disabled) |
| NetBox | Console server | `custom_fields.percepxion_device_id` | Present when `lantronix.oob`'s NetBox playbook manages the unit |
| NetBox | Console server port | `label`, `description` | Name set on the unit; attached device hostname (netbox-lantronix) |

Without these fields the workflows still work: match the console server to Percepxion by serial
number or name.

## W9: Console path from NetBox or Nautobot

Read-only throughout. Use it when the operator names a managed device ("get me a console on
core-rtr-01") and NetBox or Nautobot records its console cabling.

### From NetBox (`netbox-mcp`; call conventions are in `netbox-reconcile`)

1. `netbox_get_objects` with `object_type` `dcim.consoleport`, `filters` `{"device": "core-rtr-01"}`
   and `brief: false`. `connected_endpoints` names the console server port at the far end, through
   any patch panels; `link_peers` names only the directly cabled one. The port number is the number
   in the port's name (`Port-02` is port 2). No console port or no cable means NetBox doesn't record
   a console path: say so and stop.
2. `netbox_get_objects` with `object_type` `dcim.device` and the console server's name. Read its
   serial, primary IP and, when present, `custom_fields.percepxion_device_id`.
3. Go to "Confirm in Percepxion" below.

### From Nautobot (`nautobot-mcp`)

1. `nautobot_graphql` with:

   ```graphql
   query ($name: [String]) {
     devices(name: $name) {
       name
       serial
       console_ports {
         name
         connected_console_server_port {
           name
           cf_lx_port_state
           cf_lx_attached_hostname
           cf_lx_ssh_port
           device { name serial cf_percepxion_device_id cf_lx_mgmt_ip primary_ip4 { address } }
         }
       }
     }
   }
   ```

   with variables `{"name": ["core-rtr-01"]}`. An empty `connected_console_server_port` means
   Nautobot doesn't record a console path.
2. `cf_lx_ssh_port` is the port's SSH port, or `off`. The Percepxion `device_id` is
   `cf_percepxion_device_id`.

### Confirm in Percepxion

1. Resolve the console server: `get_device_details(device_id=<percepxion_device_id>)`, or
   `get_device_details(serial_num=<serial>)`, or `get_device_list(search_query=<console server
   name>)`. The plugins keep the name in step with Percepxion.
2. W2 steps 1 and 2: the unit is online, and `get_port_telemetry` on that port reports the device
   the source of truth expects (hostname, and serial when known).
3. If they disagree, stop and report both sides, for example "NetBox: core-rtr-01 on Port-02;
   the console server reports edge-rtr-09 there". Send the discrepancy to `netbox-reconcile` and
   don't hand out the path. With console cables managed by the plugin, the next sync may already
   correct it.
4. Return `ssh -p <SSH port> <user>@<address>`. Use the address from the source of truth, or the
   management IP from `get_device_details`. Use `lx_ssh_port` when Nautobot has it; otherwise the
   factory port is 3000 + N, and `show deviceport port N` through W3 confirms the unit's setting.
   SSH that's off on the port is the operator's configuration change, not this workflow's.

Prompts: "Get me a console on core-rtr-01." "Which console server port is edge-fw-02 on, and is it
reachable now?"

## W10: Console coverage gate

Grades every device a change will touch: does each have a console cable in the source of truth to a
synced console server port that's in a ready state (Managed or Identified by default)? Run it before
the change and stop when any device has no way back. Both gates report in the same schema,
`aoob.console-coverage/v1`.

### Nautobot

1. `nautobot_list_jobs` with `q` `"console coverage"` finds **AOOB console coverage gate**; enable it
   with `nautobot_enable_job` if needed.
2. `nautobot_run_job` with the job's ID and `data` such as `{"devices": "core-rtr-01,dist-sw-07"}`
   (comma-separated; `ready_states` and `include_console_servers` are optional). NetClaw's Nautobot
   server gates job runs on a change request, so pass the change's `cr_number`.
3. `nautobot_get_job_result`: the job fails when any device isn't covered, and its `result` holds
   the JSON report. Nautobot also keeps it as the job's `console-coverage.json` file.

### NetBox

NetClaw's NetBox server reads objects but can't run scripts, so run the gate one of two ways:

- **Ansible:** a playbook with `lantronix.oob.oob_coverage_gate` (`oob_coverage_gate_source:
  netbox`, `oob_coverage_gate_devices` listing the targets) runs `ConsoleCoverageGate` and fails the
  play when a device isn't covered. Launch it through `aap-automation` when it's a job template, or
  ask the operator to run it.
- **NetBox UI:** the operator runs **ConsoleCoverageGate** under Customization > Scripts.

For a handful of devices, W9 per device gives the same answer without the gate.

### Reasons a device isn't covered

| Reason | Meaning | Usual fix |
|---|---|---|
| `no_console_port`, `no_console_cable` | The source of truth has no console port, or no cable on it | Record the cable, or enable cable management in the plugin |
| `peer_not_visible` | The requesting user can't see the console server end | Permissions in NetBox or Nautobot |
| `peer_not_console_server`, `slc_not_synced` | The cable ends somewhere that isn't a synced console server port | Fix the cable, or sync the console server |
| `port_state_unknown`, `port_state_not_ready` | Percepxion hasn't reported the port, or it isn't Managed or Identified | W2 and W3 on that port |
| `ssh_disabled` | SSH to that port is off on the console server | Operator enables SSH on the port |
| `port_name_unparsed`, `no_slc_host` | The port name or the console server's address can't be read | Fix the record |

## Events from Percepxion

The `lantronix.oob.percepxion_console_events` rulebook (see `aap-eda`) emits
`percepxion.device.status_changed` when a device's connection status changes and
`percepxion.port.attached_changed` when the device on a console port appears, changes or goes away.
A device going offline is a reason to start W8. A port change is a reason to re-run W9 for that
device, or W10 before the next change; its shipped playbooks only report.

## Keeping the source of truth current

The plugins sync on their own schedules. To refresh before a check, with the operator's approval:

- Nautobot: run **Percepxion to Nautobot** with `{"dryrun": true}` first to see the diff, then without
  it. It writes to Nautobot.
- NetBox: **Sync now** on the source under Lantronix > Percepxion > Sources, or the plugin's sync API.
  This is an operator action; NetClaw's NetBox server is read-only.
