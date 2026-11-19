# Workflows W1 to W8

Tool names and parameters match percepxion-mcp-server. Only parameters that are required or easy
to get wrong are shown; the server's tool schemas carry the rest. `<sid>` is a console server's
Percepxion `device_id`. Project Admin sessions add `organization_id` to job, telemetry, content,
Smart Group and audit calls; it takes the organization's ID or its exact name.

Calls that start a job: `send_direct_cli_command`, `update_device_config`, `clone_device_config`,
`update_firmware_by_smart_group`, `reboot_device`, `request_device_syslog_upload`. Track each with
`get_job_group(job_group_id)` until Completed or Failed, or find recent ones with
`search_job_groups(search_string, job_type)`.

## W1: Discovery and inventory

1. `login_with_env`.
2. `get_device_list(search_query="*")` lists console servers, not managed devices. Filter by
   hostname or model with `search_query`; page with `limit` and `offset`.
3. Several organizations: `list_organizations`, then `get_devices_by_organization(organization_id)`.
4. One unit: `get_device_details(device_id=<sid>)`, or `serial_num` when the ID isn't known. It
   returns name, model, firmware, address, status and last check-in.
5. What's attached: `get_security_telemetry(<sid>)` lists every port's managed device.

Prompts: "Which console servers haven't checked in today?", "What's cabled to the SLC in rack B4?"

## W2: Preflight, console path ready before a change

Run before any automated or risky change to a managed device that has a console server.

1. `get_device_details(<sid>)`: status online and a recent check-in. Otherwise stop: there's no
   console path.
2. `get_port_telemetry(<sid>, port_number=N)`: a managed device is attached and matches the change
   target by hostname, and by serial when one is known. For every port at once, use
   `get_security_telemetry(<sid>)`.
3. Optional: `send_direct_cli_command(<sid>, "show deviceport port N")`, then
   `get_cli_command_output` for signals, the port mode and whether direct SSH is enabled.
4. Result: **pass**, or **fail** with one reason (console server offline, nothing attached, a
   different device attached, port not ready). Stop on a fail unless the operator overrides it. An
   override goes into the `description` of every later call; it doesn't loosen the server's CLI
   policy.

For a change touching many devices, W10 grades them all in one report from NetBox or Nautobot.

## W3: SLC CLI diagnostics

All commands run on the console server's CLI through `send_direct_cli_command(<sid>, command,
description)`, followed by `get_job_group`, then `get_cli_command_output(job_group_id, <sid>)`.

| Question | Command |
|---|---|
| Console server health | `show sysstatus` |
| One port's signals, speed and mode | `show deviceport port N` |
| Every port at a glance | `show portstatus` |
| Port names | `show deviceport names` |
| Firmware | `admin version` |
| Can the console server reach the managed device's management IP | `diag ping <ip>`, `diag traceroute <ip>` |

`no carrier` on a port means the attached device is powered off or the cable is out. If the console
server can ping the managed device's management IP while the production path can't, the fault is in
the production network rather than the device. Afterwards, collect `get_device_syslogs(<sid>)` and
`query_device_access_log(<sid>, log_level)` for the record.

The command reference is chapter 18 of the SLC 9000 user guide:
https://cdn.lantronix.com/wp-content/uploads/pdf/PMD-00347A-SLC9K-UG-release.pdf

With slc-mcp-server registered and the unit reachable, `apply_config_commands` returns the same
output in one call.

## W4: Firmware compliance and rollout

1. One unit: `get_device_firmware_status(<sid>)`.
2. Fleet: `firmware_compliance_report(expected_firmware_version="<target>", model_filter="SLC9000")`
   splits units into compliant, non-compliant and unknown.
3. Packages already in Percepxion: `list_firmware_content`.
4. Target group: `create_smart_group(name, query=... or device_ids=[...], temporary=true)`. Use a
   query or an ID list, not both. Membership is evaluated when the job runs.
5. Present the group, its member count, current and target versions and the local firmware file,
   then wait for approval.
6. `update_firmware_by_smart_group(firmware_file_path, smart_group_ids=[...], content_name,
   version, description)`. The file must be on the MCP server's disk, inside
   `PERCEPXION_FIRMWARE_DIR` when that's set.
7. Track with `get_job_group`; `get_job_results_by_device(job_group_id)` shows which units
   succeeded. Report each failure with its reason.
8. `delete_smart_group(smart_group_id)` once the job is done.

## W5: Access audit

- `investigate_audit_logs(search_string, from_date, to_date, usernames=[...])` searches the
  platform audit trail. It has no `device_id`: put the unit's name or address in `search_string`.
  Without dates it searches all history.
- `investigate_user_audit_logs(user_filter)` returns users with their last audited action. It
  takes no date range.
- `query_device_access_log(<sid>, log_level)` pages through the unit's own access log, and
  `download_device_access_log(<sid>)` exports it for a SIEM or evidence file.
- `get_security_telemetry(<sid>)` adds the unit's console manager, firmware, network and audit
  records.
- `set_user_access(usernames=[...], enabled=false)` suspends Percepxion users (`true` resumes them).
  It's a change: confirm the names and the reason first.

## W6: Console server configuration

1. `get_device_config(<sid>)` reads the stored configuration.
2. `update_device_config(<sid>, property_name, new_value)` for one setting, or `items=[{"name",
   "value"}, ...]` for several. `apply_now=true` (the default) pushes it to the unit as a job. Show
   the proposed change and get approval first.
3. `clone_device_config(source_device_id, target_device_id, record_names=[...])` copies named
   records. Read the source first to choose `record_names`, and confirm both units with the
   operator.
4. `list_templates` and `delete_template(template_id)` manage saved templates.

## W7: Console server lifecycle

- `import_and_assign_devices(devices=[{device_id, device_name, serial_num}], organization_id)`
  onboards units. `device_description` is optional per unit.
- `reboot_device(<sid>, description)` restarts the unit and drops console access to every device
  on it until it's back. Confirm the hostname and the window first.
- `unassign_devices(device_ids=[...])` removes units from an organization and keeps them on the
  platform. `remove_device_from_platform(<sid>)` removes one entirely and can't be undone; confirm
  the hostname first.
- `request_device_syslog_upload(device_ids=[...])` asks units to upload their logs; dates are
  RFC 3339. Read the result with `get_device_syslogs(<sid>)`.

## W8: Incident evidence and remediation

Starts when an alert or orchestrator (PagerDuty, Itential, ServiceNow) reports a managed device
unreachable in-band. Steps 1 to 5 and 7 are read-only; step 6 needs write mode on the server and
operator or orchestrator approval.

1. Find the console server: `get_device_list(search_query="<site or device name>")`, or W9 from
   NetBox or Nautobot.
2. `get_device_details(<sid>)`. Console server offline: stop and escalate to a person.
3. W2 steps 2 and 3 for the target port. Record a missing carrier or a different device as a
   finding.
4. Before-state evidence: `get_device_syslogs(<sid>)`.
5. Diagnostics from W3, each with the incident ID in `description`. The output from
   `get_cli_command_output` goes into the incident record.
6. Remediation on the console server, only when approved and write mode is on. Confirm the effect
   from the command output.
7. After-state evidence: `investigate_audit_logs(search_string="<unit name>")` shows the actions in
   Percepxion's audit trail.
8. Return to the caller: job group IDs, the before-state summary, the audit entries, and one
   outcome: `remediated`, `diagnosed-only` or `escalate-to-human`.

Collect steps 4 and 7 even when step 6 fails. Agent-initiated actions appear in the same audit
trail as a person's, attributed to the MCP server's Percepxion account, with `description` as the
stated reason.
