# Forward MCP Integration Guide

NetClaw uses the upstream Forward MCP server to query Forward
snapshots, paths, device inventory, NQE results, NQE diffs, snapshot diffs,
configuration search, config diffs, checks, vulnerabilities, blast radius,
missing-device evidence, collection tasks, app-aware paths, and lifecycle
support data.

Source: <https://github.com/forwardnetworks/forward-mcp>

## Install

For an existing NetClaw install:

```bash
./scripts/forward-enable.sh
```

The script clones `forwardnetworks/forward-mcp`, builds the Go stdio MCP server,
creates local cache/lock directories, writes Forward environment variables to
`~/.openclaw/.env`, and runs a local `get_default_settings` smoke test.

By default, NetClaw installs the `netclaw` branch of Forward MCP. Override the
repo or ref when needed:

```bash
FORWARD_MCP_REPO=https://github.com/forwardnetworks/forward-mcp.git \
FORWARD_MCP_REF=main \
./scripts/forward-enable.sh
```

## Requirements

- Go 1.25 or later
- CGO enabled
- Git
- Network access from the NetClaw host to the Forward API
- Forward credentials

Forward MCP enforces TLS certificate verification. For private CA deployments,
set `FORWARD_CA_CERT_PATH`; do not disable verification.

## Environment

Store credentials in `~/.openclaw/.env`, not in repository files:

```bash
FORWARD_API_BASE_URL=https://fwd.app
FORWARD_API_KEY=your-api-key-or-username
FORWARD_API_SECRET=your-api-secret-or-password
FORWARD_INSTANCE_ID=your-account-or-org-label
FORWARD_DEFAULT_NETWORK_ID=
FORWARD_DEFAULT_SNAPSHOT_ID=
FORWARD_COLLECTION_NETWORK_ID=
FORWARD_CA_CERT_PATH=
FORWARD_LOCK_DIR=$HOME/.openclaw/forward/locks
FORWARD_BLOOM_INDEX_PATH=$HOME/.openclaw/forward/bloom-indexes
FORWARD_SEMANTIC_CACHE_DISK_PATH=$HOME/.openclaw/forward/cache
```

Upstream Forward MCP sends `FORWARD_API_KEY:FORWARD_API_SECRET` as Basic Auth.
Use the Forward credential form your deployment supports.

For Forward SaaS, use `FORWARD_API_BASE_URL=https://fwd.app`. Set
`FORWARD_INSTANCE_ID` when you use more than one SaaS account or org from the
same NetClaw host; upstream uses this value to partition local NQE/cache state.
Use `FORWARD_DEFAULT_NETWORK_ID` for the safe read-only demo network. Use
`FORWARD_COLLECTION_NETWORK_ID` only for an admin/test network where collection
setup and collection-start workflows are allowed.

## SaaS Read-Only Workflow

Use this path to validate a Forward SaaS account without writing credentials to
the repo or shell history:

```bash
read -r -p "Forward username or API key: " FORWARD_API_KEY
read -r -s -p "Forward password or API secret: " FORWARD_API_SECRET
echo

export FORWARD_API_BASE_URL=https://fwd.app
export FORWARD_API_KEY
export FORWARD_API_SECRET
export FORWARD_INSTANCE_ID=forward-saas
export FORWARD_DEFAULT_NETWORK_ID=<network-id>
export FORWARD_LOCK_DIR=$HOME/.openclaw/forward/locks
export FORWARD_BLOOM_ENABLED=false
export FORWARD_SEMANTIC_CACHE_ENABLED=false

python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp \
  get_default_settings '{}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp \
  list_networks '{"limit":5}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp \
  get_latest_snapshot '{"network_id":"<network-id>"}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp \
  list_devices '{"network_id":"<network-id>","limit":5}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp \
  get_device_basic_info '{"network_id":"<network-id>","snapshot_id":"<snapshot-id>","options":{"limit":5}}'

unset FORWARD_API_KEY FORWARD_API_SECRET
```

Expected result: the server returns defaults, at least one accessible network,
the latest processed snapshot for the selected network, a bounded device list,
and a bounded NQE-backed device inventory result.

## MCP Registration

NetClaw registers the server as `forward-mcp` in `config/openclaw.json`:

```json
{
  "command": "mcp-servers/forward-mcp/forward-mcp",
  "env": {
    "FORWARD_API_BASE_URL": "${FORWARD_API_BASE_URL}",
    "FORWARD_API_KEY": "${FORWARD_API_KEY}",
    "FORWARD_API_SECRET": "${FORWARD_API_SECRET}",
    "FORWARD_INSTANCE_ID": "${FORWARD_INSTANCE_ID}"
  }
}
```

## Primary Workflows

| Workflow | Preferred tools |
|----------|-----------------|
| Networks and defaults | `list_networks`, `get_default_settings`, `set_default_network` |
| Collection setup | `list_classic_devices`, `upsert_classic_devices`, `list_cli_credentials`, `create_cli_credential` |
| Collection control | `get_collector_status`, `start_collection_task`, `get_collector_task`, `wait_for_latest_snapshot`, `start_collection`, `cancel_collection` |
| Snapshots | `list_snapshots`, `get_latest_snapshot` |
| Devices | `list_devices`, `get_device_basic_info`, `get_missing_devices` |
| Paths | `list_l7_applications`, `search_paths_bulk`, `search_paths` |
| Topology | `get_snapshot_topology`, `search_nqe_queries`, `run_nqe_query_by_id` |
| NQE | `search_nqe_queries`, `list_nqe_queries`, `run_nqe_query_by_id`, `run_nqe_query`, `start_nqe_query`, `get_nqe_query_status`, `get_nqe_query_result` |
| Checks and intent | `list_predefined_checks`, `list_checks`, `get_check` |
| CVE posture | `search_nqe_queries`, `run_nqe_query_by_id`, `get_nqe_diff`, `get_snapshot_diff` |
| NQE and intent/check diffs | `get_nqe_diff` |
| Snapshot diffs | `get_snapshot_diff_summary`, `get_snapshot_diff` |
| Large NQE results | `get_nqe_result_summary`, `get_nqe_result_chunks`, `analyze_nqe_result_sql` |
| Configs | `search_configs`, `get_config_diff` |
| Lifecycle support | `get_device_hardware`, `get_hardware_support`, `get_os_support` |
| Locations | `list_locations`, `get_device_locations` |

NQE note: first-class tools such as `get_device_basic_info`,
`get_device_hardware`, `get_hardware_support`, and `get_os_support` work
without query-library discovery. Query discovery tools may need a local index
first. In a persistent OpenClaw session, run `hydrate_database` and then
`refresh_query_index` if `search_nqe_queries` or `list_nqe_queries` reports an
empty query index. With one-shot `scripts/mcp-call.py`, prefer first-class tools
or a known query ID because upstream hydration runs in the background.

NQE catalog note: Forward MCP ships a bundled NQE catalog in its own
`spec/NQELibrary.json`. NetClaw should not maintain a separate copy of that
catalog. Use `search_nqe_queries` or `list_nqe_queries` to find the built-in
`FQ_...` query ID, then execute it with `run_nqe_query_by_id`. For topology
work, start with `get_snapshot_topology` for native directed links, then enrich
with NQE when protocol or neighbor evidence is needed. The built-in
`/L2/CDP and LLDP` query is commonly useful:
`FQ_08cb4fd1d50cb521e25a43714e85f23c1e664b34`. Forward also models protocol
peer relationships in NQE, so topology and relationship workflows should include
relevant peer queries such as `/L3/BGP/Established BGP Peerings`
(`FQ_e3d40e190d769a6221ddcc21555473cf04e1384e`) when those protocols are in
use.

Ad-hoc NQE note: use `run_nqe_query` only when no built-in query fits and the
expected result is small enough for a bounded synchronous call. Use
`start_nqe_query`, then poll `get_nqe_query_status` and fetch
`get_nqe_query_result`, for long-running NQE or large result sets. These tools
run raw NQE source or query IDs through Forward's native NQE APIs and do not
save raw source to the NQE Library. Keep ad-hoc queries narrow, set limits, and
use `all_results: true` only when the user needs the complete table.

NQE construction note: build raw NQE incrementally and prefer schema-native
surfaces over custom wrappers. Useful surfaces for demo questions are:

- On-prem VIPs and backend rewrites:
  `network.devices[].natEntries[]`, filtered with `natType == NatType.LB`, then
  `headerMatches` and `rewrites`.
- Cloud load balancers:
  `network.cloudAccounts[].vpcs[].loadBalancers[]` and, for GCP external load
  balancers, `network.cloudAccounts[].externalLoadBalancers[]`.
- VIP route propagation:
  `network.devices[].networkInstances[].afts.ipv4Unicast.ipEntries[]`, filtered
  with `targetVip in route.prefix`, then `route.nextHops[]`.

Example for VIPs in the same subnet:

```nqe
targetSubnet = ipSubnet("110.240.240.0/24");
foreach device in network.devices
foreach natEntry in device.natEntries
where natEntry.natType == NatType.LB
foreach vip in natEntry.headerMatches.ipv4Dst
where vip in targetSubnet
foreach rewrite in natEntry.rewrites
select {
  LoadBalancer: device.name,
  Vip: vip,
  Ports: natEntry.headerMatches.tpDst,
  Backends: rewrite.ipv4Dst
}
```

Example for how a VIP is propagated through routing:

```nqe
targetVip = ipSubnet("110.240.240.240/32");
foreach device in network.devices
foreach vrf in device.networkInstances
where isPresent(vrf.afts.ipv4Unicast)
foreach route in vrf.afts.ipv4Unicast.ipEntries
where targetVip in route.prefix
where length(route.prefix) >= 24
foreach nextHop in route.nextHops
select {
  Device: device.name,
  Vrf: vrf.name,
  Prefix: route.prefix,
  OriginProtocol: nextHop.originProtocol,
  NextHopType: nextHop.nextHopType,
  NextHopIp: nextHop.ipAddress,
  Interface: nextHop.interfaceName
}
```

Diff note: use `get_snapshot_diff_summary` for a broad snapshot overview across
generally available route, ACL, NAT, ARP, MAC, interface, file/config, check,
inventory-query, routing-loop, and vulnerability domains. Use
`get_snapshot_diff` for a focused domain such as `routes`, `acl`, `nat`,
`interfaces`, `checks`, or `vulnerabilities`. Use `get_nqe_diff` for arbitrary
query-result drift between two snapshots, including intent/check-style NQE
queries. Use `get_config_diff` when the request is specifically configuration
drift. `get_nqe_diff` supports filtering and sorting on the `ChangeType` column
for `ADDED`, `DELETED`, and `MODIFIED` rows.

## Query Examples by Use Case

### Network and Snapshot Discovery

```
/forward list networks
/forward show current Forward defaults
/forward use network 101 by default
/forward show latest snapshot for network 101
/forward list the five most recent snapshots for network 101
```

### Path Analysis

```
/forward search paths from 10.0.1.10 to 10.0.2.20
/forward trace a TCP path from 10.0.1.10 to 10.0.2.20 port 443
/forward list L7 applications and trace SSH from 10.0.1.10 to 10.0.2.20
/forward find violations only for traffic from 10.0.1.10 to 10.0.2.20
```

Use `search_paths_bulk` first for agent workflows because it handles one or
many path queries with bounded result controls. Use `search_paths` only for a
single one-off trace.

### Blast Radius

```
/forward find blast-radius sources matching leaf01
/forward show blast radius from leaf01 to 0.0.0.0/0 in snapshot 123
/forward show host-centric blast radius from leaf01 to 10.0.0.0/8
```

Use `suggest_blast_radius_sources` when the source location is uncertain. Use
`get_blast_radius` with `source_device` for a device source, or with raw Forward
`LocationFilter` JSON in `source` when the source is not a single device. Keep
destination subnets, timeout, and paging bounded.

### Device, Config, and Lifecycle Posture

```
/forward list first 10 devices in snapshot 123
/forward show missing devices for network 101 in snapshot 123
/forward show basic device inventory for snapshot 123
/forward search configs for "router bgp"
/forward check hardware support for snapshot 123
/forward check OS support for snapshot 123
```

### Checks and CVEs

```
/forward show failed checks for snapshot 123
/forward get details for check check-1 in snapshot 123
/forward show CVE violations by device for network 101
/forward show CVE-2024-12345 exposure using the Forward CVE NQE queries
```

Use `list_checks` first for snapshot intent status, then `get_check` for a
specific failed or warning check. Use `list_predefined_checks` when the user
asks what built-in checks are available.

Use NQE for CVE posture wherever possible. Useful built-in query paths include:

- `/Security/CVEs/CVE violations by CVE`
- `/Security/CVEs/CVE violations by device`
- `/Security/CVEs/CVE violation details by device`
- `/Security/CVEs/Vendor CVE metadata`
- `/Security/CVEs/CVE Configuration Analysis Statistics`

Use `search_nqe_queries` to discover the current query IDs, then
`run_nqe_query_by_id` with bounded result options. Use `get_nqe_diff` for CVE
query drift between snapshots. Use `get_snapshot_diff` with
`diff_type: "vulnerabilities"` when the user asks for the Forward vulnerability
diff domain.

### Snapshot Diff Analysis

```
/forward summarize diffs between snapshots 123 and 124
/forward show route diff prefixes between snapshots 123 and 124
/forward show ACL diffs between snapshots 123 and 124
/forward show interface diffs for device leaf01 between snapshots 123 and 124
/forward show check diff counts between snapshots 123 and 124
```

Recommended flow:

1. Run `get_snapshot_diff_summary` with a bounded `include` list.
2. Pick the interesting domain and run `get_snapshot_diff`.
3. For route diffs, use `view: "prefixes"` or `view: "devices"` with a limit.
4. For arbitrary NQE or intent-style checks, use `get_nqe_diff`.
5. For literal config text drift, use `get_config_diff`.

### Collection Readiness and Lab Onboarding

```
/forward show collector status for network 101
/forward list collection sources for network 101
/forward list CLI credentials for network 101
/forward add lab devices to network 101
/forward start a collection task for network 101
/forward show collector task task-123
/forward wait for the latest snapshot for network 101
```

Collection tools are intended for lab/admin networks. Before starting a
collection, verify collector assignment with `get_collector_status`, verify
sources with `list_classic_devices`, and confirm the user expects a new
collection run. Prefer `start_collection_task` and `get_collector_task` for new
workflows; keep `start_collection` for legacy deployments.

Collector bootstrap is separate from collection control. Anyone can install or
onboard a collector, but a network admin must assign that collector to the
target network before collection can use it. The stable Linux collector download
URL is `https://fwd.app/api/software/client?type=LINUX`.

### Lab Topology Drawing

Use this path when the user asks NetClaw to recreate or draw a real or
emulated network shape:

1. Use the available source system to identify node names, management IPs, and
   physical links. This may be a lab backend, source of truth, device discovery,
   or existing inventory.
2. Verify a Forward collector is assigned and can reach the target management
   network. If no collector is assigned or routed to the devices, install a
   collector if needed and have a network admin assign it to the network.
3. Use Forward MCP collection tools to onboard those nodes and create a
   processed snapshot.
4. Use Forward NQE discovery for link and peer evidence. Prefer
   `search_nqe_queries` for CDP/LLDP and protocol peers, or run the built-in
   `/L2/CDP and LLDP` and relevant peer query IDs when available.
5. If Forward returns only management-plane neighbors or incomplete link data,
   use the originating topology source as the edge source and Forward as the
   collected assurance source.
6. Render the normalized node/edge list with Draw.io, Markmap, or another
   NetClaw diagram skill. Do not infer links from device names or management
   IPs.

## Snapshot Handling

Forward tools use explicit snapshot IDs for repeatable answers. Prefer this
sequence:

1. `list_networks` or `get_default_settings` to establish the network.
2. `get_latest_snapshot` for the active point in time.
3. `list_snapshots` when a comparison needs a before/after pair.
4. Pass both snapshot IDs explicitly to diff tools.

For pre/post change demos, record the selected snapshots outside the query
result and keep the diff call bounded with `limit`, `offset`, and domain
filters.

## Cross-Platform Composition

Forward data can be combined with other NetClaw skills:

| Integration | Forward Provides | Partner Provides | Use Case |
|-------------|------------------|------------------|----------|
| Lab or inventory source | Collection target, snapshot, NQE, path, and diff validation | Device list, management reachability, credentials, and physical link facts | Collect a real or emulated network, validate it, and draw the topology |
| Batfish | Snapshot and path results | Offline config analysis | Compare modeled reachability with config-derived expectations |
| pyATS | Assurance snapshot and diffs | Live CLI verification | Confirm a Forward finding against device show commands |
| NetBox | Device and location facts | Source-of-truth intent | Reconcile discovered devices and metadata |
| Draw.io | Structured topology facts | Diagram rendering | Produce human-readable topology or change diagrams |

## Troubleshooting

| Error | Cause | Resolution |
|-------|-------|------------|
| "forward-mcp binary is not installed" | Server was not built | Run `./scripts/forward-enable.sh` |
| "Another instance is already running" | Forward MCP instance lock is active | Use a unique `FORWARD_LOCK_DIR` for one-shot tests or stop the old process |
| "Authentication failed" | Invalid key/secret or unsupported credential form | Regenerate the API credential and update `~/.openclaw/.env` |
| "TLS certificate" | Private deployment uses an untrusted CA | Set `FORWARD_CA_CERT_PATH` to the CA bundle |
| Empty query index | Local NQE query library has not hydrated | Use first-class NQE tools or hydrate in a persistent OpenClaw session |
| No processed snapshot | Collection has not completed | Check collector status, sources, and schedules, then wait for a processed snapshot |

## Safety

Default Forward workflows in NetClaw should be read-only. Require explicit
human confirmation before using any Forward tool that creates, updates, deletes,
clears, or rebuilds remote data.

Mutating or sensitive tools include:

- `create_network`, `update_network`
- `upsert_classic_devices`, `delete_classic_devices`
- `create_cli_credential`, `delete_cli_credential`
- `start_collection_task`, `start_collection`, `cancel_collection`
- `delete_snapshot`
- `create_location`, `update_location`, `delete_location`
- `update_device_locations`, `create_locations_bulk`
- `create_entity`, `delete_entity`, `create_relation`, `delete_relation`
- `add_observation`, `delete_observation`
- `clear_cache`
- `initialize_query_index`, `hydrate_database`, `refresh_query_index`,
  `build_bloom_filter`, `set_default_network`

Creating new Forward networks requires full org admin privileges. Updating an
existing Forward network requires network admin privileges. Installing or
onboarding a collector is not org-admin-only, but assigning that collector to a
target network requires network admin privileges.

## Security Considerations

- Store credentials in `~/.openclaw/.env`; never commit them.
- Use `FORWARD_INSTANCE_ID` to partition local cache state across SaaS accounts
  or orgs.
- Use read-only credentials for discovery, path, NQE, diff, and lifecycle
  workflows.
- Use admin credentials only for lab/admin networks that need collection source
  or collection-start workflows.
- Treat topology, config, and path data as sensitive network information.

## Verification

Local build and smoke test:

```bash
cd mcp-servers/forward-mcp
make test-quick
CGO_ENABLED=1 go build -o forward-mcp ./cmd/server
cd ../..
mkdir -p "$HOME/.openclaw/forward/locks"
python3 scripts/mcp-call.py \
  "FORWARD_LOCK_DIR=$HOME/.openclaw/forward/locks ./mcp-servers/forward-mcp/forward-mcp" \
  get_default_settings '{}'
```

Credentialed read-only smoke tests:

```bash
set -a
source ~/.openclaw/.env
set +a

python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp list_networks '{"limit":5}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp get_latest_snapshot '{"network_id":"<network-id>"}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp list_devices '{"network_id":"<network-id>","limit":5}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp get_device_basic_info '{"network_id":"<network-id>","snapshot_id":"<snapshot-id>","options":{"limit":5}}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp list_l7_applications '{}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp list_checks '{"snapshot_id":"<snapshot-id>","statuses":["FAIL"]}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp get_missing_devices '{"network_id":"<network-id>","snapshot_id":"<snapshot-id>"}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp get_snapshot_diff_summary '{"before_snapshot":"<before-snapshot-id>","after_snapshot":"<after-snapshot-id>","include":["files","interfaces","acl","routes","checks","vulnerabilities"]}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp get_snapshot_diff '{"before_snapshot":"<before-snapshot-id>","after_snapshot":"<after-snapshot-id>","diff_type":"routes","view":"prefixes","limit":5}'
python3 scripts/mcp-call.py ./mcp-servers/forward-mcp/forward-mcp get_nqe_diff '{"before_snapshot":"<before-snapshot-id>","after_snapshot":"<after-snapshot-id>","query_id":"<query-id>","options":{"limit":5}}'
```
