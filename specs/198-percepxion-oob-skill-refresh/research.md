# Research

- **Installed revisions.** `clone_or_pull` checks out the reviewed commit recorded in
  `config/fastmcp-external-patches.json`: percepxion-mcp-server `533fdc98` (1.2.0) and slc-mcp-server
  `c5ba7f6b` (1.1.0), patched to `fastmcp==4.0.11`. The latest releases (2.2.0 and 1.4.0) have the same
  38 and 37 tools with identical signatures (compared by parsing each `server.py`); they add Streamable
  HTTP and SSE transports, the `azure` and `command` credential providers and `_FILE` variables. The
  references describe the installed baseline and name what newer releases add.
- **Parameter errors in the current skill**, from the installed `server.py`:
  `request_device_syslog_upload(device_ids: list[str], log_type, log_level, from_date, to_date)`;
  `query_device_access_log(device_id, log_level, limit, offset)` with no `query`;
  `search_job_groups(search_string, job_type, subtype, ...)`. The server's `docs/tools.md` lists
  `update_device_config` and `clone_device_config` as job-creating.
- **Missing skills.** `netbox-source-of-truth` and `itential-orchestration` don't exist; the
  equivalents are `netbox-reconcile` and `itential-automation`.
- **NetBox.** NetClaw's `netbox-mcp` (netboxlabs `netbox-mcp-server` at `14ec2fe7`) supports
  `dcim.consoleport` and `dcim.consoleserverport`, is read-only, and can't run scripts. A console
  port's `connected_endpoints` gives the console server port at the far end of the path, through
  patch panels; `link_peers` gives only the direct peer.
- **Nautobot.** NetClaw's `nautobot-mcp` has `nautobot_graphql`, `nautobot_list_jobs`,
  `nautobot_run_job` (change-request gated) and `nautobot_get_job_result`. `nautobot_get_cables`
  resolves only interface terminations, so console paths need GraphQL. Nautobot 3.2 exposes
  `connected_console_server_port` on console ports and custom fields with the `cf_` prefix.
- **Lantronix NetBox plugin** (`netbox-lantronix`, NetBox 4.6 to 4.7): console servers from Percepxion,
  port labels and descriptions, optional console cables, Open console with each port's configured SSH
  port, `ConsoleCoverageGate` script. It keeps the SSH port in its own models, which `netbox-mcp`
  doesn't read.
- **Lantronix Nautobot app** (`nautobot-app-ssot-lantronix`, Nautobot 3.1+): the "Percepxion to
  Nautobot" job, custom fields `percepxion_device_id`, `lx_mgmt_ip`, `lx_firmware_version` on the
  console server and `lx_port_state`, `lx_attached_*`, `lx_ssh_port` on its ports, and the "AOOB
  console coverage gate" job, which returns its `aoob.console-coverage/v1` report as the job result.
- **lantronix.oob.** NetBox playbook since 1.3.0 (adds `percepxion_device_id`); `oob_coverage_gate`
  role and `percepxion_events` source since 1.4.0. The role runs either gate by name
  (`oob_coverage_gate_source: netbox | nautobot`).
- **Device types.** SLC 9000 types are merged in the NetBox community device-type library; SLC 8000
  and EMG types ship in both plugins' `docker/device-types` folders.
- **Skill limits.** `check-skill-limits.py` reported prompt characters at 80% before this change; the
  new description is about 170 characters longer.
- **Deployment.** `scripts/deploy-skills.py` copies each skill directory recursively, so `references/`
  reaches the runtime, as it does for `kepner-tregoe-network-troubleshooting`.
