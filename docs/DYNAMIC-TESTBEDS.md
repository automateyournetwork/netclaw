# Static and dynamic pyATS testbeds

NetClaw can keep a static testbed file or compose a temporary testbed from selected
inventory sources. Setup chooses the policy; it does not fetch inventory, activate
a testbed, probe a port or log in to a device. This is Spec160, source 1.14.0 and
VS Code extension 1.4.0.

The isolated upstream revision is
[`4a3c1e3404d5ed7a78cb094bf26d2a49065497d9`](https://github.com/automateyournetwork/pyATS_MCP/commit/4a3c1e3404d5ed7a78cb094bf26d2a49065497d9).
It supplies 34 tools, including eight dynamic-testbed tools. NetClaw adds
`netclaw_testbed_compose`, for 35 tools in the managed pyATS server. The MCP server
and skill counts are unchanged. Existing installations need an explicit reviewed
component upgrade to acquire this version; an extension upgrade does not upgrade them.

## Choose the policy

- **VS Code:** Set Up a New NetClaw → select pyATS → **Testbed mode & sources**.
  Choose Static and optionally import reviewed YAML/JSON/CSV, or choose Dynamic
  and select one or more source cards. Save/reload preserves each claw's selection.
  Cancelling the picker changes nothing. Changing to Dynamic removes that claw's
  planned static import only after native confirmation; it never changes the file.
- **Terminal new-claw installer:** `./scripts/install.sh --emit-plan <plan.json>`
  offers the same mode/source choices for selected pyATS claws. Enter `list` at the
  source prompt for source-specific prerequisites. Review the exact plan before apply.
- **Existing-runtime setup:** `./scripts/setup.sh --testbed-only` offers Keep,
  Static or Dynamic for the selected runtime. The ordinary `setup.sh` includes the
  same step. Use the runtime selection environment already supported by the installer
  (for example `NETCLAW_RUNTIME=hermes HERMES_HOME=/absolute/selected/home`). Blank
  or Cancel retains the policy. Static uses the selected runtime's explicit path.

An omitted policy means static compatibility. A schema-1 plan may contain:

```json
"testbed": {"mode": "dynamic", "sources": ["cml", "netbox"]}
```

Dynamic installation writes a private `testbeds/policy.json` and generated env
settings in that claw's home. It creates no dummy YAML. `NETCLAW_TESTBED_MODE` and
`NETCLAW_TESTBED_SOURCES` describe the selection. The dynamic child unsets
`PYATS_TESTBED_PATH` and sets `PYATS_MCP_DYNAMIC_ONLY=1`; an old file cannot silently
become its active inventory. Legacy setup retains the old path for an explicit
return to Static. Other components can still use their separately configured files.

Selection does not install or authenticate every source service. Use the selected
source's existing MCP component, or an explicitly obtained structured export.
Source service credentials stay with that integration. Device credentials remain
separate private environment variables (`NETCLAW_USERNAME`, `NETCLAW_PASSWORD`,
`NETCLAW_ENABLE_PASSWORD` by default). No secrets belong in a plan or envelope.

## Compose through existing sources

Upstream has native fetchers for Itential, NetBox, Nautobot and Catalyst Center.
Its raw fetchers do not supply reliable truncation/completion evidence and have
redirect, credential-copy and mapping hazards. **NetClaw's managed route normalizes
reviewed source records and calls the actual upstream inline builder.** Raw native,
file and REST fetch, arbitrary raw mappings and static credential merge are refused.
`pyats_testbed_sources` explains the selected routes. This is an intentional managed
boundary, not a claim that upstream lacks those capabilities.

Discover the installed source's actual tools/schema before collection. Fetch only
read-only inventory in an explicit scope, account for every page, and retain source
identity and age. A success response or short page alone does not establish completeness.

| Source ID | Reader / extraction | Required facts and limits |
|---|---|---|
| `itential_inventory` | Discover inventory/node tools; Inventory Manager `result.data[]` | Inventory + platform owner, `name`, `attributes.itential_host/platform/port`; verify totalRecords/totalPages. [API](https://docs.itential.com/itential-platform/6/6/api-reference/inventory-manager/get-nodes-by-inventory) |
| `netbox` | `netbox_get_objects` for full `dcim.devices`; extract `results[]` where applicable | Device ID/name, `primary_ip4.address`, `platform.slug`; explicit IPv6 map, count/next/cursor completion. [REST](https://netbox.readthedocs.io/en/stable/integrations/rest-api/) |
| `nautobot` | Bundled `nautobot_get_devices`: `devices[]` | Bundled MCP uses `primary_ip4.address` and `platform.name`; native REST differs (`host`, `network_driver`). Enrich missing identity and prove pagination; page count is not total. [Versioned REST](https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/rest-api/overview/) |
| `catalyst_center` | Discover `catc_find` / `catc_describe_operation`, then `catc_devices`; `response[]` | ID, hostname, managementIpAddress, softwareType; explicit OS mapping and site/scope; all offset pages. Controller reachability is separate evidence. [API](https://developer.cisco.com/docs/catalyst-center/get-device-list/) |
| `cml` | Probe `get_nodes_for_cml_lab` vs older `get_nodes`; inspect node interfaces | Lab + node ID, label, explicit OS mapping, independently observed management endpoint. Serial consoles are not SSH. CML 2.10 pyATS exports can contain credentials. [Tool source](https://github.com/xorrkaz/cml-mcp/blob/main/src/cml_mcp/tools/nodes.py) |
| `containerlab` | `listLabs`, brief `inspectLab`; inspect the API wrapper, select exact lab | container_id/name/ipv4_address or explicit IPv6; kind→OS map. Do not copy Docker environment. Running container does not prove SSH. [Inspect](https://containerlab.dev/cmd/inspect/) |
| `eve_ng` | `eve_list_nodes(lab_path,page,page_size)` | Lab + node ID, name, template→OS map and independent management endpoint. Verify total_count/has_next; console_port is not SSH. [API](https://www.eve-ng.net/index.php/how-to-eve-ng-api/) |
| `gns3` | `gns3_list_nodes(project_id)` | Project + node UUID, independent management endpoint and OS. console_host/console and qemu node_type cannot supply these facts. [Node schema](https://api.gns3.net/en/latest/api/v2/controller/node/projectsprojectidnodesnodeid.html) |
| `servicenow` | Authorized Table API `result[]` export, or capability-probed CMDB read tool | Bundled MCP has no verified CMDB reader. Instance-specific class/fields, sys_id/name/ip_address/os, stable paging and ACL-aware completeness. [API](https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/c_RESTAPI.html) |
| `infrahub` | `get_schema`, then read-only `query_graphql` with explicit JSON projection | Branch/kind/schema scope, stable ID and discovered management relation. No universal device schema. TOON and has_more=null cannot be accepted as complete JSON. [Methods](https://docs.infrahub.app/mcp/references/methods) |
| `ipfabric` | Discover endpoint schema with `ipf_api_endpoint_search/details`, then `api_invoke` inventory table | Concrete snapshot ID/time, stable device ID, hostname, loginIpv4/loginIpv6 and OS family mapping. SDK8 removed loginIp; old versions need explicit mapping. [MCP](https://docs.ipfabric.io/8.0/IP_Fabric_Settings/integration/mcp/) |
| `forward` | Explicit device names and `get_device`, or approved structured export | Explicit network and concrete processed snapshot. Discover endpoint/OS schema; no verified bulk-list/discovery contract. NQE prose is not inventory. [NetClaw reference](FORWARD.md) |
| `structured` | Reviewed JSON records; locally convert CSV/YAML/XML with a trusted parser | Explicit stable ID/name/management_ip/management_port/os. No raw configuration dumps. |
| `rest` | Explicitly permitted existing MCP reader or reviewed REST export | Exact authorized origin, TLS, bounded redirects/response/pagination in the reader. pyATS receives records, never an arbitrary fetch URL or header secret. |

The normalizer defaults are extraction hints, not assertions about every API version.
Use `mapping` for explicit dot paths into each extracted record, limited to
`id`, `name`, `host`, `port`, `os`; use `osMap` for exact source platform values.
Secret/configuration/environment-shaped paths are refused. Only normalized connection
facts and bounded provenance leave normalization; arbitrary source properties are dropped.

## Review envelope

This example is synthetic. Replace timestamps and records with actually observed
inventory; never relabel fixtures or retrieval time as live/snapshot evidence.

```json
{
  "schema": 1,
  "name": "reviewed-lab-20261030",
  "credentials": {
    "username_env": "NETCLAW_USERNAME",
    "password_env": "NETCLAW_PASSWORD",
    "enable_env": "NETCLAW_ENABLE_PASSWORD"
  },
  "sources": [{
    "kind": "structured",
    "owner": "lab-controller-a",
    "scope": {"lab": "selected-lab"},
    "capturedAt": "2026-10-30T12:00:00Z",
    "complete": true,
    "total": 1,
    "records": [{
      "id": "node-1", "name": "r1", "management_ip": "192.0.2.10",
      "management_port": 22, "os": "iosxe"
    }]
  }]
}
```

`complete:true` is collection evidence supplied by the source workflow, not inferred
by the normalizer. `total` must equal the number of collected records. Empty/partial
collections, repeated identities, conflicting names/endpoints and unknown OS values
are refused. There is no last-writer-wins merge. Cross-source enrichment requires
explicit stable identity joins before composition; conflicting facts need resolution.

Lab records without management data may include `endpoints` keyed by their source
record ID, with `host`, `port`, `os` where absent, `observedAt` and an `evidence`
identity. This must come from an independent observation, not a console-address
substitution. A conflicting existing value blocks the join. For sources that omit
SSH port, an operator can explicitly select `defaults:{"port":22}`.

IP Fabric and Forward require `scope.snapshot_id` and `snapshotCapturedAt`; retrieval
time cannot freshen a stale snapshot. Default maximum age is 86400 seconds; an explicit
reviewed `maxAgeSeconds` may range from 1 to 2678400. Bounds are 8 MiB, 5000 devices
and 32 source scopes. Unknown/ambiguous data fails as a whole, with no hidden omissions.

The candidate uses one device credential profile. Three environment references are
required by the upstream builder. If a device does not need a separate enable secret,
explicitly point `enable_env` to the same device password variable; this does not
perform enable/login. Supported references are NETCLAW device names and scoped
`PYATS_DEVICE_*_USERNAME/PASSWORD/ENABLE_PASSWORD` names. Source API secrets are not
accepted as device references. All references must be set before activation.

## MCP lifecycle

1. Use `pyats_testbed_sources` and source MCP discovery to establish the collection route.
2. Call `netclaw_testbed_compose({envelope: ...})`. Review name, digest, counts, provenance,
   OS, management addresses/ports and credential **references**. It builds without activation.
3. Call `pyats_testbed_validate({name, check_reachability:false})`. This runs the real
   pyATS schema loader and checks credential references. A Task receipt is not the result.
4. Explicitly call `pyats_testbed_activate({name})`, then `pyats_list_devices`.
5. Continue authorized pyATS operations in this same MCP process. A successful list
   proves inventory only. Existing baseline, change-control and device verification rules apply.

`pyats_testbed_build` remains available with `source:"inline"` and `data` containing
the same reviewed envelope; the separate name must match. `dry_run:true` previews
without storing. Prefer the simpler compose tool. Names cannot be reused in the
same process. Activation requires completed schema/credential validation, refuses
while operations are in flight, and cannot delete/replace the active candidate.
`pyats_testbed_get` returns safe env references and source provenance; `list` reports
process lifetime. `source_inventories` directs callers to the existing source MCP.

## One-shot calls and restart

The registry belongs to one owned server process. Separate `$MCP_CALL` invocations
start separate processes: build in one invocation cannot feed activate in another.
Use a persistent native MCP client, the explicit foreground session below, or the bounded session helper:

```bash
chmod 600 /absolute/private/candidate.json
python3 scripts/pyats-testbed-session.py \
  --runtime-env /absolute/selected/home/.env \
  --input /absolute/private/candidate.json

# After reviewing that exact envelope, explicitly activate and list in one process:
python3 scripts/pyats-testbed-session.py \
  --runtime-env /absolute/selected/home/.env \
  --input /absolute/private/candidate.json --activate
```

The helper uses the installed isolated Python/MCP runtime. It never probes, logs in
or runs device commands. Its active state ends when it exits. For subsequent device
operations, compose/validate/activate in the persistent native client that will perform
them. Restart always requires rebuild/revalidation/explicit activation; nothing silently
re-fetches changed inventory or replays work. Each process has its own private artifact
and task database directory, avoiding cross-client state and database locks.

### Clients that close STDIO between turns

Actual OpenClaw 2026.7.1-2 qualification showed that its STDIO child ends after
each agent turn. For multi-turn operations, including Terminal Intent's private
candidate review and APPLY phases, explicitly start one managed foreground session.
Use the selected installation's environment and installed pyATS interpreter:

```bash
# Use a fresh descriptor in an owner-only directory. Keep this terminal open.
# These values must match the same selected MCP registration.
export PYATS_VENV=/absolute/selected/home/pyats-venv
export NETCLAW_CHANGE_ROOT=/absolute/selected/home/netclaw-changes
export NETCLAW_TESTBED_MODE=dynamic
export NETCLAW_TESTBED_SOURCES=cml
python3 scripts/pyats-stdio.py \
  --serve-session /absolute/private/session-unique.json
```

Load device credential references through the selected runtime's existing private
environment; never paste secrets into these commands. Add `PYATS_SESSION_FILE`
pointing to that exact descriptor to the same `pyats-mcp` registration's environment.
The registration continues using `pyats-stdio.py` and the original tool identities.
Refresh the runtime registration, then compose, validate and activate through its
tools. The descriptor binds the installation vault, interpreter, upstream and
testbed policy; a different selection fails closed.

The owner process binds only loopback, requires a fresh private bearer on every
HTTP request, and retains inventory when a client disconnects. Default lifetime is
four hours (`--session-seconds`, 60–28800); Ctrl-C stops its child. Private descriptors
must be owned regular files in a 0700 directory and have mode 0600. Do not share
them. Stopped/expired sessions fail closed; there is no auto-start, inventory recovery
or grant replay. Use a new descriptor and rebuild/revalidate/review after restart
or credential changes. Remove the registration's `PYATS_SESSION_FILE` to return to
the default per-client lifetime. Existing private apply grants still expire after
five minutes and bind the same live process, inventory and reviewed candidate.

## Static HUD, collectors and readiness

The HUD/VS Code static editor, Terminal Intent and topology collector keep their
existing static file and endpoint grants. Dynamic MCP activation does not change
that file or grant collector/configuration access. Export/import into a static file,
if desired, is a separate reviewed operation with the existing secret masking and
consent invalidation. The UI labels this distinction.

Readiness distinguishes tool discovery, source selection/access, candidate validation,
activation and execution. Setup reports leave source access, candidate, activation and
execution unverified/not performed. A selected source is not a successful connection.
See [Spec160 verification](../specs/160-dynamic-pyats-testbeds/verification.md) for exact
fixture, actual-process, installer/UI and live/platform qualification.
