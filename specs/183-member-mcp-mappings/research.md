# Research

## Sources

- **Skill → server binding.** `config/components/catalog.json` `skills[].servers`, generated
  by `scripts/build-catalog.py` and read by the installer and `scripts/verify-catalog-coverage.py`
  (the `catalog` surface of `scripts/reconcile-mcp.py`). It binds each skill to the servers of its
  installer component(s). It is per component, so a skill in a multi-server component (aap, aws,
  gcp, checkpoint, drawio-rfc) is bound to all of that component's servers.
- **What the skill calls.** Each `SKILL.md`: its `## MCP Server` section (command or server
  name), its tool tables and `$MCP_CALL` examples, and, where present, the `netshell.mcp_tools`
  front matter (`- mcp: <server>` plus tool names).
- **What is registered.** `config/openclaw.json` `mcpServers` (126 servers), the template
  `scripts/install-mcp-config.py` writes into the runtime's `mcp.servers`, which is what
  `scripts/in2n-member-home.py` filters.
- **Skills per profile.** `PROFILE_MATCHERS` (`scripts/in2n-profiles.py`) run against
  `workspace/skills/` with `_match_profile`.

Line numbers below are from this branch. `catalog:N` is the line of the skill's `"id"` in
`config/components/catalog.json`; `cfg:N` is the server's line in `config/openclaw.json`.

## Findings

- The comment above `MCP_SERVERS` listed cml, pyats, gtrace, itential, aap, packet, nso, netbox,
  nmap and catalyst-center as "skill-driven (no dedicated MCP server)". Each of these has a
  registered server that the catalog binds to its skills, so members of those profiles got the
  skills and no tools.
- `"github": ["gitlab-mcp"]` gave the GitHub member GitLab's server; `github-ops` is bound to
  `github-mcp` (catalog:24978, cfg:848).
- Twelve more profiles (meraki, terraform, zscaler, claroty, fortimanager, nautobot, infrahub,
  nvd, fwrule, aws, gcp, and paloalto's FMC skill) had no entry although their servers are
  registered and bound. viz kept two of the seven servers its skills call.
- `ipfabric-mcp` is not in `config/openclaw.json`. `scripts/ipfabric-enable.sh:183-190` checks
  for it and prints the entry for the operator to add under `mcp.servers`; the `ipfabric` skill
  names it (`ipfabric/SKILL.md:9`). The existing mapping is right, and the test allows it by
  name with that script as evidence.
- `splunk` and `gnmi` have `MCP_SERVERS` entries but no `PROFILE_MATCHERS` entry. They are only
  reachable as `in2n-member-home.py --member splunk|gnmi`; both servers are registered. Unchanged.

## Audit

"Calls" lists representative tool names from the skill. ✔ = unchanged and correct.

| Profile | Skills (matched) | Tools called (sample) | Server(s) providing them | Was | Now | Evidence |
|---|---|---|---|---|---|---|
| convergence | convergence-observations | `convergence_flow_summary`, `convergence_flow_evidence` | convergence-read-mcp | convergence-read-mcp | ✔ | catalog:29195, cfg:1485 |
| subnet | subnet-calculator | `subnet_calculator`, `subnet_calculator_v6` | subnet-calc-mcp | subnet-calc-mcp | ✔ | subnet-calculator/SKILL.md:12, cfg:1374 |
| cml | cml-admin, cml-lab-lifecycle, cml-node-operations, cml-packet-capture, cml-topology-builder | `get_cml_labs`, `start_cml_lab`, `get_users` | cml-mcp (`python3 -m cml_mcp`, xorrkaz/cml-mcp) | — | **cml-mcp** | cml-admin/SKILL.md:13 ("Command: `cml-mcp`"), cml-lab-lifecycle/SKILL.md:19,31, catalog:23860, cfg:736 |
| eve-ng | eve-lab-topology-*, eve-ng-* (8) | `eve_get_topology`, `eve_list_node_interfaces` | none registered; no catalog binding | — | — (uncertain) | eve-lab-topology-build/SKILL.md:14,22; no `eve` server in config/openclaw.json |
| gns3 | gns3-* (5) | `gns3_list_links`, `gns3_create_link` | gns3-mcp | gns3-mcp | ✔ | gns3-link-management/SKILL.md:28, cfg:171 |
| containerlab | clab-lab-management | `listLabs`, `deployLab` | `$CLAB_MCP_SCRIPT` via `$MCP_CALL`; not registered | — | — | clab-lab-management/SKILL.md:12,19; catalog binds no server |
| pyats | pyats-* (18) | `pyats_run_show_command`, `pyats_parse_show_command`, `pyats_list_devices`, `pyats_run_dynamic_test` | pyats-mcp | — | **pyats-mcp** | pyats-health-check/SKILL.md:9-16 (`netshell.mcp_tools: - mcp: pyats-mcp`), pyats-asa-firewall/SKILL.md:45, catalog:27112, cfg:1330 |
| ipfabric | ipfabric | `ipf_network_health_assess`, `ipf_pathlookup_unicast` | ipfabric-mcp (operator-registered) | ipfabric-mcp | ✔ | ipfabric/SKILL.md:9, scripts/ipfabric-enable.sh:183-190 |
| suzieq | suzieq-observability | `suzieq_show`, `suzieq_summarize` | suzieq-mcp | suzieq-mcp | ✔ | suzieq-observability/SKILL.md:14, cfg:44 |
| batfish | batfish-config-analysis | `batfish_upload_snapshot`, `batfish_validate_config` | batfish-mcp | batfish-mcp | ✔ | batfish-config-analysis/SKILL.md:15, cfg:75 |
| forward | forward | `get_paths` | forward-official-mcp | forward-official-mcp | ✔ | forward/SKILL.md:20, cfg:34 |
| gtrace | gtrace-ip-enrichment, gtrace-path-analysis | `traceroute`, `mtr`, `asn_lookup`, `geo_lookup` | gtrace-mcp | — | **gtrace-mcp** | gtrace-path-analysis/SKILL.md:12 ("native registration and … MCP_CALL share the installed component launcher"), :17, catalog:25258, cfg:1451 |
| packet | packet-analysis, kubeshark-traffic | `capture_traffic`, `export_pcap`, `create_snapshot`, `apply_filter` | packet-buddy-mcp, kubeshark-mcp | — | **packet-buddy-mcp, kubeshark-mcp** | packet-analysis/SKILL.md:11,15, kubeshark-traffic/SKILL.md:12, catalog:26002, cfg:1429, cfg:965 |
| itential | itential-automation | `get_health`, `get_devices`, `backup_device_configuration` | itential-mcp | — | **itential-mcp** | itential-automation/SKILL.md:12, catalog:25636, cfg:760 |
| aap | aap-automation, aap-eda, aap-lint | `list_inventories`, `get_inventory` (+ EDA, lint, docs) | aap-ansible-mcp, aap-eda-mcp, aap-lint-mcp, aap-docs-mcp | — | **all four** | aap-automation/SKILL.md:13-19 (sibilleb/AAP-Enterprise-MCP-Server), catalog:22564, cfg:1016,1027,1045 |
| nso | nso-device-ops, nso-service-mgmt | `get_device_config`, `check_device_sync` | nso-mcp (`cisco-nso-mcp-server`) | — | **nso-mcp** | nso-device-ops/SKILL.md:13, catalog:26668, cfg:749 |
| terraform | terraform-operations, -registry, -workspaces | `terraform_plan`, `terraform_validate` | terraform-mcp | — | **terraform-mcp** | catalog:28179, cfg:250 |
| aci | aci-change-deploy, aci-fabric-audit | via `$MCP_CALL` with `$ACI_MCP_SCRIPT` | not registered | — | — | aci-fabric-audit/SKILL.md:14; catalog binds no server |
| catalyst-center | catc-client-ops, catc-inventory, catc-troubleshoot | `catc_get_device_list`, `get_api_compatible_time_range` | catc-mcp | — | **catc-mcp** | catc-client-ops/SKILL.md:28, catalog:23436, cfg:1231. catc-inventory's `netshell.mcp_tools` says `catalyst-center-mcp`, a name nothing registers |
| f5 | f5-config-mgmt, f5-health-check, f5-troubleshoot | `list_tool`, `show_stats_tool` | via `$MCP_CALL` with `$F5_MCP_SCRIPT`; not registered | — | — | f5-config-mgmt/SKILL.md:18; catalog binds no server |
| meraki | meraki-* (5) | `execute_api`, `semantic_search` | meraki-mcp (Cisco official, remote) | — | **meraki-mcp** | meraki-monitoring/SKILL.md:13, catalog:26112, cfg:788 |
| sdwan | prisma-sdwan-* (4), sdwan-ops | `get_app_defs`, `get_bgp_peers` | prisma-sdwan-mcp; sdwan-ops uses `$SDWAN_MCP_SCRIPT` (not registered) | prisma-sdwan-mcp | ✔ | prisma-sdwan-apps/SKILL.md:27, sdwan-ops/SKILL.md:15, cfg:185 |
| ise | ise-incident-response, ise-posture-audit | via `$MCP_CALL` with `$ISE_MCP_SCRIPT` | not registered | — | — | ise-incident-response/SKILL.md:30; catalog binds no server |
| asa | pyats-asa-firewall | `pyats_run_show_command` | pyats-mcp | — | — (**uncertain**) | pyats-asa-firewall/SKILL.md:45, catalog:27112. The profile is gated on `ASA_MCP_CMD`/`ASA_HOST` and its env slice is `ASA_` only, so the member would not receive `PYATS_*`; this looks like a placeholder for a dedicated ASA server that does not exist. Left for a decision |
| checkpoint | checkpoint | 15 servers by query type | the 15 `chkp-*` servers | 5 `chkp-*` | ✔ kept (**uncertain**) | checkpoint/SKILL.md:24-44 (table of 15 with credentials), catalog:7927. The kept five are not the skill's "MGMT server" set either; whether to keep all 15 (several need SASE, TE, Spark, Argos or Reputation API keys) is a decision |
| paloalto | fmc-firewall-ops, paloalto-panorama | `find_rules_by_ip_or_fqdn`, `search_access_rules` (FMC) | cisco-fmc-mcp; Panorama uses `$PANOS_MCP_CMD` (not registered) | — | **cisco-fmc-mcp** | fmc-firewall-ops/SKILL.md:11, paloalto-panorama/SKILL.md:15, catalog:24689, cfg:835 |
| fortimanager | fortianalyzer-ops, fortigate-ops, fortimanager-ops | `faz_query_logs`, `faz_policy_activity` | fortinet-mcp | — | **fortinet-mcp** | fortianalyzer-ops/SKILL.md:16-17, catalog:24717, cfg:1146 |
| zscaler | zscaler-* (5) | `list_users`, `list_groups` | zscaler-mcp | — | **zscaler-mcp** | catalog:29027, cfg:266 |
| claroty | claroty-* (3) | `list_devices`, `set_device_purdue_level` | claroty-mcp | — | **claroty-mcp** | claroty-asset-inventory/SKILL.md:28-29, catalog:23616, cfg:594 |
| nmap | nmap-* (3) | `nmap_ping_scan`, `nmap_syn_scan` | nmap-mcp | — | **nmap-mcp** | nmap-network-scan/SKILL.md:12,17, catalog:26528, cfg:1440 |
| nvd | nvd-cve | `get_cve`, `search_cve` | nvd-cve-mcp | — | **nvd-cve-mcp** | nvd-cve/SKILL.md:12,19, catalog:9360, cfg:1363 |
| fwrule | fwrule-analyzer | `analyze_firewall_rule_overlap`, `parse_policy` | fwrule-mcp | — | **fwrule-mcp** | fwrule-analyzer/SKILL.md:13, catalog:24829, cfg:1010 |
| equinix | equinix-fabric-operations, equinix-network-edge | `list_devices`, `list_metros` | equinix-mcp | equinix-mcp | ✔ | catalog:24335, cfg:1315 |
| aws | aws-architecture-diagram, -cloud-monitoring, -cost-ops, -network-ops, -security-audit | `list_vpcs`, `find_ip_address` (network), IAM/CloudTrail, CloudWatch, Cost Explorer, diagram | aws-network, -iam, -cloudtrail, -cloudwatch, -cost-explorer, -diagram (`-mcp`) | — | **all six** | aws-network-ops/SKILL.md (`netshell.mcp_tools: aws-network-mcp`), aws-security-audit/SKILL.md:13-14, aws-cloud-monitoring/SKILL.md:13, aws-cost-ops/SKILL.md:13, aws-architecture-diagram/SKILL.md:13, catalog:23017, cfg:862,888,900 |
| azure | azure-network-ops, azure-security-audit | `azure_list_vnets` | azure-network-mcp | azure-network-mcp | ✔ | azure-network-ops/SKILL.md:13, cfg:108 |
| gcp | gcp-cloud-logging, -cloud-monitoring, -compute-ops | `list_instances`, `list_log_entries` | gcp-compute, -logging, -monitoring, -resource-manager (`-mcp`) | — | **all four** | gcp-compute-ops/SKILL.md:25 (`netshell.mcp_tools: gcp-compute-mcp`), catalog:24885, cfg:931,938,945 |
| netbox | netbox-reconcile | `netbox_get_objects`, `netbox_get_object_by_id` | netbox-mcp | — | **netbox-mcp** | netbox-reconcile/SKILL.md:12,34, catalog:26444, cfg:1341 |
| nautobot | nautobot-sot | `get_ip_addresses`, `get_prefixes`, `search_ip_addresses` | nautobot-mcp (`mcp-servers/nautobot-mcp-v2`) | — | **nautobot-mcp** | nautobot-sot/SKILL.md:11-26, catalog:26416, cfg:336. See tool-name note below |
| infrahub | infrahub-sot | `get_schemas`, `get_related_nodes` | infrahub-mcp | — | **infrahub-mcp** | infrahub-sot/SKILL.md:11, catalog:25504, cfg:242 |
| infoblox | infoblox-ddi | via `$INFOBLOX_MCP_CMD` | not registered | — | — | infoblox-ddi/SKILL.md:15; catalog binds no server |
| github | github-ops | issues, PRs, code search (official GitHub MCP) | github-mcp | **gitlab-mcp** | **github-mcp** | github-ops/SKILL.md:57 (`GITHUB_PERSONAL_ACCESS_TOKEN`), catalog:24978, cfg:848 (`ghcr.io/github/github-mcp-server`) |
| viz | threejs-network-viz, ue5-network-viz, blender-3d-viz, canvas-network-viz, drawio-diagram, markmap-viz, uml-diagram, aws-architecture-diagram | `get_scene_info`, `open_drawio_mermaid`, markmap/UML render, UE5 actors | blender-mcp, sketchfab-mcp, drawio-mcp, markmap-mcp, uml-mcp, unreal-mcp, aws-diagram-mcp | blender-mcp, sketchfab-mcp | **+ drawio-mcp, markmap-mcp, uml-mcp, unreal-mcp, aws-diagram-mcp** | blender-3d-viz/SKILL.md:27, drawio-diagram/SKILL.md:108, markmap-viz/SKILL.md:16, uml-diagram/SKILL.md:12, ue5-network-viz/SKILL.md:462, aws-architecture-diagram/SKILL.md:13, cfg:313,658,1407 |
| splunk (no matcher) | — | — | splunk-mcp | splunk-mcp | ✔ | cfg (registered) |
| gnmi (no matcher) | — | — | gnmi-mcp | gnmi-mcp | ✔ | cfg (registered) |

Not kept although the catalog binds them, each because the binding is per component, not per
skill: `rfc-mcp` for viz (drawio-diagram is in the drawio-rfc component but calls no RFC tool),
and the five non-diagram AWS servers for viz (aws-architecture-diagram's workflows use only the
diagram tool; the `aws` profile keeps all six).

## Env slices

`scripts/in2n-migrate.py` writes a member's `.env` from `env_slice_keys`, which matched only
`ENV_PREFIXES` and `BASE_MEMBER_ENV_PREFIXES`. The member's runtime resolves each kept server's
`${NAME}` references from that `.env`, so any referenced name outside the prefixes was empty.
Against the repository template, kept servers referenced these names outside their profile's
prefixes. All are now included except `SERVICENOW_*`, which is never derived (see Shared
credentials below):

| Profile | Server | Names outside the prefixes |
|---|---|---|
| aap | aap-eda-mcp, aap-docs-mcp | `EDA_TOKEN`, `EDA_URL`, `REDHAT_USERNAME`, `REDHAT_PASSWORD` |
| catalyst-center | catc-mcp | `CATALYST_CENTER_HOST`, `_USERNAME`, `_PASSWORD`, `_VERIFY_SSL` |
| terraform | terraform-mcp | `TFC_HOST`, `TFC_ORG`, `TFC_TOKEN` |
| claroty | claroty-mcp | `NETCLAW_LAB_MODE`, `SERVICENOW_INSTANCE_URL`, `_USERNAME`, `_PASSWORD` |
| fortimanager | fortinet-mcp | `SERVICENOW_INSTANCE_URL`, `_USERNAME`, `_PASSWORD` |
| nautobot | nautobot-mcp | `ITSM_ENABLED`, `ITSM_LAB_MODE` |
| viz | uml-mcp, aws-diagram-mcp | `KROKI_SERVER`, `PLANTUML_SERVER`, `USE_LOCAL_KROKI`, `USE_LOCAL_PLANTUML`, `MCP_OUTPUT_DIR`, `LOG_LEVEL`, `AWS_REGION` |
| sdwan (existing) | prisma-sdwan-mcp | `PAN_CLIENT_ID`, `PAN_CLIENT_SECRET`, `PAN_REGION`, `PAN_TSG_ID` |
| gns3 (existing) | gns3-mcp | `GNS3_URL`, `GNS3_USER`, `GNS3_PASSWORD`, `GNS3_TOKEN_TTL`, `GNS3_VERIFY_SSL` |
| splunk (existing) | splunk-mcp | `SPLUNK_HOST`, `SPLUNK_TOKEN`, `SPLUNK_VERIFY_SSL` |
| gnmi (existing) | gnmi-mcp | `GNMI_*` (8), `NETCLAW_LAB_MODE`, `SERVICENOW_*` (3) |

Rather than widen `ENV_PREFIXES` per profile (which would drift again with the next server),
the slice now adds the names the kept servers reference. The kept set is the one
`in2n-member-home.py` uses (`member_servers`: `MCP_SERVERS` plus `memory-mcp`), so the
slice and the scoped config cannot disagree. No server any profile keeps references a comms
secret; `twilio-mcp`, `twitter-mcp` and the comms plugins are kept by no member.

### Shared credentials (review round 1)

Three kept servers reference the shared ServiceNow account (`SERVICENOW_INSTANCE_URL`,
`_USERNAME`, `_PASSWORD`), a write-capable ITSM credential. Each gate fails closed without it:

- fortinet-mcp `gates.py:59-80` (`check_change_request`): unconfigured ServiceNow returns
  `REFUSED_NO_CHANGE_RECORD` ("Unverified is not approved"); `evaluate` (`:119-163`) needs it
  unless the device is a lab device, and always needs human approval.
- claroty-mcp `utils/itsm_gate.py` (`validate_change_request`): `_check_servicenow_cr_state`
  returns `None` without the account, and the write is blocked ("ServiceNow verification
  unavailable — write blocked"). `NETCLAW_LAB_MODE=true` skips ServiceNow (format check only).
- gnmi-mcp `itsm_gate.py`: the same code (claroty's is a port of it).

Decision: derived references never add `SERVICENOW_*` or a comms secret. Members of these
profiles read and, in lab mode, write; a production write is refused until the operator grants
`SERVICENOW_` through `ENV_PREFIXES`. `NETCLAW_LAB_MODE` (claroty, gnmi) and `ITSM_ENABLED` /
`ITSM_LAB_MODE` (nautobot) stay derived: they carry the Border's posture to the member, and
nautobot-mcp's gate is the one that fails open when they are absent (`ITSM_ENABLED` defaults to
`false`, `nautobot-mcp-v2/server.py:36-46`), so deriving them is the stricter choice.

The comms denylist is the exact keys in `config/components/comms.json` (180 keys) plus the
prefixes `SLACK_`, `DISCORD_`, `WEBEX_`, `TWILIO_`, `TWITTER_`, `MSTEAMS_`, `TEAMS_`, `TELEGRAM_`.

### Runtime paths (review round 1)

`install-mcp-config.py:182-186` adds `NETCLAW_RUNTIME_ROOT=<Border>/python-runtimes` and
`NETCLAW_RUNTIME_ENV=<Border>/.env` to every entry whose args include
`scripts/component-launch.py`; `component-launch.py:29-36` (`environment`) loads every key of
`NETCLAW_RUNTIME_ENV` into the server's environment. With the full component set, 16 installed
entries carry them; among kept servers: pyats-mcp, netbox-mcp, nvd-cve-mcp, nmap-mcp,
gtrace-mcp, packet-buddy-mcp, drawio-mcp, markmap-mcp, subnet-calc-mcp. The Hermes and
Convergence member paths already wrote the member's own paths (`in2n-member-home.py`
`provision_hermes`, `provision_convergence`); the generic OpenClaw path copied the Border's.
`component-launch.py` reads interpreter records from `NETCLAW_RUNTIME_ROOT/records/<component>`
(not needed for pyats, a bridge; gtrace, a binary; drawio, npx; markmap, node), so the member
home gets copies of the ones its entries name.

## Uncertain, left unchanged

- **asa**: see the table. Mapping it to `pyats-mcp` would need `PYATS_` in its env slice too.
- **checkpoint**: the existing five-server subset is kept.
- **eve-ng**: skills name `eve_*` tools, but no EVE-NG server is registered and the catalog binds
  none.

## Related gaps (not changed here)

- **Nautobot tool names.** `nautobot-sot` documents aiopnet/mcp-nautobot's names
  (`get_ip_addresses`, `get_prefixes`); the registered nautobot-mcp (`nautobot-mcp-v2/server.py`)
  serves `nautobot_get_ip_addresses`, `nautobot_get_prefixes` (lines 190, 219).
- **catc-inventory** names `catalyst-center-mcp` in `netshell.mcp_tools`; the registered server
  is `catc-mcp`.

## pyATS change root (review round 2)

`component-launch.py:44-46` sets `NETCLAW_CHANGE_ROOT=<runtime root>/../netclaw-changes` for
pyats, so with the member's runtime root it is `<member home>/netclaw-changes`. Who uses that
vault:

- **Issuer (Border only).** The HUD (`ui/netclaw-visual/server.js:208`) builds its change policy
  with `createLocalChangePolicy({directory: <OPENCLAW_HOME>/netclaw-changes})`;
  `terminal-migration-artifacts.js` reads `inventories/`, `candidates/`, writes `grants/<nonce>.json`
  signed with `<root>/api-signing.key` (`:101-110`), and checks `installation == hash(root())`
  (`:42`). It only ever opens the Border's own vault.
- **Consumer (the pyATS server process).** `scripts/pyats-managed.py:52` opens
  `PrivateMigration(NETCLAW_CHANGE_ROOT)`; `scripts/lib/migration_artifacts.py` `claim()` reads
  the grant, `api-signing.key`, `records/` and `policy.json` from that root and requires
  `claim['installation'] == digest(str(root))` and the process's own harness id.

The Terminal Intent workflow runs through the Border's gateway agent and the Border's pyATS
server, not a member's. A member's vault never receives a grant, so a member's
`pyats_configure_device` private apply is refused (`Refused`, tested). Pointing the member at
the Border's vault instead would configure a member process with the HUD's signing key and
grants and let it publish inventories the HUD lists alongside the Border's (members run as the
same user, so file modes do not separate them). Decision: keep the change root per member, and state that
HUD private-migration change flows are Border-only (spec.md, Known behaviour).

## Member env file (review round 2)

`in2n-migrate.py` stages each slice at `<staging>/members/<member>/.env`; nothing copied it to
`<member home>/.env`, the default `NETCLAW_RUNTIME_ENV`, and the runbook never mentioned
`--member-env`. A component-launched server pointed at a missing file starts with no settings.
`in2n-member-home.py` now refuses in that case, and migrate prints the exact command.

Review round 3: the check accepted the Border's own `.env` (`--member-env ~/.openclaw/.env`, or
`--home ~/.openclaw` with the default `<home>/.env`). It now compares the target with the
selected runtime's env file and the Border config directory's `.env` (`os.path.samefile`, else
resolved paths), and refuses a member home that is the Border's home.
