---
name: forward
description: Forward snapshot assurance, path search, app-aware path search, NQE, checks, vulnerabilities, diffs, configuration, lifecycle, collection, and topology workflows through the upstream forward-mcp server.
version: 1.0.0
license: Apache-2.0
author: forward
tags: [forward, assurance, nqe, paths, diffs, collection]
mcp_servers: [forward-mcp]
metadata:
  openclaw:
    requires:
      bins:
        - mcp-servers/forward-mcp/forward-mcp
      env:
        - FORWARD_API_BASE_URL
        - FORWARD_API_KEY
        - FORWARD_API_SECRET
        - FORWARD_INSTANCE_ID
        - FORWARD_DEFAULT_NETWORK_ID
---

# Forward Skill

**Skill**: `/forward`
**MCP Server**: `forward-mcp`
**Source**: <https://github.com/forwardnetworks/forward-mcp>

## Use When

Use this skill for Forward snapshot assurance, collection, and analysis:

- Discover Forward networks, snapshots, and devices
- Verify paths and reachability
- Discover and run NQE checks
- Review predefined checks, failed checks, and vulnerability analysis
- Compare NQE, snapshot, and config diffs
- Search configurations
- Analyze blast radius for a source location to destination IPv4 subnets
- Review hardware and OS lifecycle support
- Find missing devices inferred during collection
- Support lab or real-network collection workflows

## Startup

1. Start with `get_default_settings` to see configured defaults.
2. If no default network is set, use `list_networks` with a small limit and ask
   the user which network to use.
3. Prefer explicit `network_id` and `snapshot_id` values for repeatable results.
4. Use bounded limits by default. Use `all_results` only when the user needs the
   complete dataset.
5. In Forward SaaS, prefer `FORWARD_API_BASE_URL=https://fwd.app` and set
   `FORWARD_INSTANCE_ID` for local cache partitioning when multiple SaaS orgs or
   accounts are used on the same NetClaw host.

## Tool Routing

| User intent | Preferred tools |
|-------------|-----------------|
| "List Forward networks" | `list_networks` |
| "Use this network by default" | `set_default_network` |
| "Show collection sources" | `list_classic_devices`, `get_classic_device` |
| "Add lab devices" | `upsert_classic_devices` |
| "Show collector status" | `get_collector_status` |
| "Start collection" | `start_collection_task`, `get_collector_task`, then `wait_for_latest_snapshot`; use `start_collection` only for legacy flows |
| "Show snapshots" | `list_snapshots`, `get_latest_snapshot` |
| "List devices" | `list_devices`, `get_device_basic_info` |
| "Find missing collection neighbors" | `get_missing_devices` |
| "Trace paths" | `search_paths_bulk`, then `search_paths` for one-off traces |
| "Trace app-aware paths" | `list_l7_applications`, then `search_paths_bulk` or `search_paths` with `app_id`, `url`, or `domain` |
| "Show blast radius" | `suggest_blast_radius_sources`, then `get_blast_radius` |
| "Find NQE checks" | `search_nqe_queries`, `list_nqe_queries` |
| "Run an NQE check" | `run_nqe_query_by_id`; use `start_nqe_query` for long-running checks |
| "Write or run ad-hoc NQE" | Prefer `search_nqe_queries` first; use `run_nqe_query` only when no built-in query fits and async NQE for long-running or large results |
| "Show predefined checks" | `list_predefined_checks` |
| "Show failed checks or intent status" | `list_checks`, then `get_check` |
| "Show vulnerabilities or CVE exposure" | `search_nqe_queries`, then `run_nqe_query_by_id` with the `/Security/CVEs/...` query IDs |
| "Draw topology from Forward" | `get_snapshot_topology`, then search NQE for CDP/LLDP and protocol-peer evidence when needed |
| "Summarize large results" | `get_nqe_result_summary`, `get_nqe_result_chunks`, `analyze_nqe_result_sql` |
| "Search configs" | `search_configs` |
| "Compare NQE or intent/check results" | `get_nqe_diff` |
| "Summarize snapshot diffs" | `get_snapshot_diff_summary` |
| "Show route, ACL, NAT, interface, check, or vulnerability diffs" | `get_snapshot_diff` |
| "Compare snapshots/configs" | `get_config_diff` |
| "Check hardware or OS support" | `get_device_hardware`, `get_hardware_support`, `get_os_support` |
| "Show locations" | `list_locations`, `get_device_locations` |

## NQE Discovery Notes

Forward MCP owns the NQE catalog. Do not copy catalog contents into NetClaw.
For natural-language NQE requests:

1. Prefer first-class tools when they match the intent, such as
   `get_device_basic_info`, `get_device_hardware`, `get_hardware_support`, or
   `get_os_support`.
2. Otherwise use `search_nqe_queries` with the user's intent.
3. Use `list_nqe_queries` only when the directory or query family is already
   known.
4. Preserve the returned `FQ_...` query ID in the answer and execute it with
   `run_nqe_query_by_id`.
5. Keep limits bounded unless the user asks for complete data.

Use `run_nqe_query` for ad-hoc NQE source only after checking whether a
built-in query already answers the question and the expected result fits a
bounded synchronous call. For long-running or large queries, use
`start_nqe_query`, poll `get_nqe_query_status`, then fetch rows with
`get_nqe_query_result`. These execute raw NQE or query IDs through Forward's
native NQE APIs; they do not create or save a new query in the NQE Library. Keep
ad-hoc queries narrow, set limits by default, and explain when the result is
from custom source rather than a built-in Forward query. Use `all_results: true`
only when the user needs the complete table.

### Constructing Ad-Hoc NQE

Prefer built-in query IDs when they fit. When a question needs raw NQE, build it
incrementally and execute it through Forward MCP:

1. Start with a tiny selector such as
   `foreach d in network.devices select { Name: d.name }`.
2. Add one model surface at a time, then run `start_nqe_query`, poll
   `get_nqe_query_status`, and page with `get_nqe_query_result`.
3. Keep filters inside NQE instead of post-processing large result sets.
4. Use schema-native types and OneOf patterns. Enumerations can be compared as
   `NatType.LB`; data-bearing OneOf values use `when ... is`.

Useful raw NQE patterns:

On-prem load balancer VIPs, DNAT-style rewrites, and backend targets:

```nqe
foreach device in network.devices
foreach natEntry in device.natEntries
where natEntry.natType == NatType.LB
foreach rewrite in natEntry.rewrites
select {
  LoadBalancer: device.name,
  Vip: natEntry.headerMatches.ipv4Dst,
  Ports: natEntry.headerMatches.tpDst,
  Backends: rewrite.ipv4Dst,
  BackendPorts: rewrite.tpDst
}
```

Other VIPs in the same subnet:

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

Cloud VPC load balancers:

```nqe
foreach cloudAccount in network.cloudAccounts
foreach vpc in cloudAccount.vpcs
foreach loadBalancer in vpc.loadBalancers
foreach rule in loadBalancer.loadBalancerRules
foreach backend in rule.backends
let server = when backend is
               server(backendServerData) -> backendServerData;
               otherwise -> null : BackendServer
where isPresent(server)
select {
  CloudAccount: cloudAccount.name,
  Vpc: vpc.name,
  LoadBalancer: loadBalancer.name,
  FrontendIps: rule.frontendIps,
  FrontendPorts: rule.frontendPorts,
  BackendIps: server.backendIps,
  BackendPorts: server.backendPorts
}
```

VIP route propagation:

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

For topology, start with `get_snapshot_topology` for native directed links.
Then search for both link evidence and protocol-peer evidence when needed.
CDP/LLDP can describe physical neighbors; peer queries such as BGP can describe
relationships Forward models beyond discovery protocols.

If `search_nqe_queries` or `list_nqe_queries` reports that the query index is
empty, do this only in a persistent OpenClaw session and only after user
confirmation:

1. Run `hydrate_database` with `regenerate_embeddings: false`.
2. Run `refresh_query_index`.
3. Retry `search_nqe_queries` or `list_nqe_queries`.

## Safety Rules

Default to read-only Forward tools. Require explicit human confirmation before
tools that create, update, delete, clear, hydrate, rebuild, start/cancel
collection, or set persistent defaults. This includes collector/source,
credential, network, snapshot, location, entity/relation, observation, local
cache/index, and `set_default_network` operations. Creating new Forward
networks requires full org admin privileges; do not use `create_network` unless
the user explicitly confirms that role. Updating an existing Forward network
requires network admin privileges.

Never put Forward credentials in repository files. Use `~/.openclaw/.env`.
For private CA deployments, use `FORWARD_CA_CERT_PATH`; do not disable TLS
verification.

## Workflows

### Diffs

1. Use `get_snapshot_diff_summary` first for a bounded overview.
2. Use `get_snapshot_diff` for focused route, ACL, NAT, interface, check,
   file/config, inventory-query, routing-loop, or vulnerability diffs.
3. Use `get_nqe_diff` for arbitrary NQE and intent-style query diffs.
4. Use `get_config_diff` when the user specifically asks for config text drift.

### Blast Radius

1. Use `suggest_blast_radius_sources` if the source name or location filter is
   uncertain.
2. Use `get_blast_radius` with `source_device` for a device source, or `source`
   when the prompt already supplies Forward `LocationFilter` JSON.
3. Keep `dst_subnets`, `timeout_seconds`, and `paging_options` bounded.
4. Use blast radius for security/exposure questions; use NQE for tabular
   snapshot facts and `search_paths_bulk` for specific path traces.

### Checks and CVEs

1. Use `list_checks` with `statuses` such as `FAIL`, `WARN`, or `ERROR` to
   triage intent/check state for a snapshot.
2. Use `get_check` for the detailed rows behind a specific failed check.
3. Use `list_predefined_checks` when the user asks what built-in checks exist.
4. Use NQE for CVE posture. Prefer `search_nqe_queries` for natural-language
   discovery, then `run_nqe_query_by_id`.
5. Useful built-in CVE query paths include `/Security/CVEs/CVE violations by
   CVE`, `/Security/CVEs/CVE violations by device`,
   `/Security/CVEs/CVE violation details by device`, and
   `/Security/CVEs/Vendor CVE metadata`.
6. Use `get_nqe_diff` for CVE query drift between snapshots. Use
   `get_snapshot_diff` with `diff_type: "vulnerabilities"` for the Forward
   vulnerability diff domain.

### Collection and Lab Demo

1. Treat collection setup and start/cancel actions as admin workflows.
2. Use them only on lab/admin networks or after explicit user confirmation.
3. Treat collector installation/onboarding as a separate prerequisite. Anyone
   can install or onboard a collector, but a network admin must assign that
   collector to the target network. The stable Linux collector download URL is
   `https://fwd.app/api/software/client?type=LINUX`.
4. Before starting collection, run `get_collector_status` and
   `list_classic_devices`.
5. Prefer `start_collection_task`, poll it with `get_collector_task`, then use
   `wait_for_latest_snapshot`. Use `start_collection` only when task creation is
   unavailable in the target deployment.

### Topology Drawing

1. Prefer Forward NQE evidence for collected topology questions: link queries
   plus relevant protocol-peer queries.
2. If the NQE result only shows management-plane neighbors or incomplete links in
   a real or emulated network, use the originating topology source as the edge
   source and Forward as the collected assurance source.
3. Use the available lab backend, source-of-truth, inventory, or discovery tool
   to identify device names, management IPs, physical links, and credentials
   before Forward collection.
4. Before `start_collection`, confirm the assigned Forward collector can reach
   the target management network. If not, the missing step is collector
   installation, assignment, or routing.
5. Render a normalized node/edge list with Draw.io, Markmap, or another diagram
   skill. Never infer links from names or management IPs alone.

## Result Discipline

- Summarize large tables before presenting them.
- Preserve network IDs, snapshot IDs, query IDs, and device names in the answer.
- When a path or NQE result is inconclusive, say what data was missing and which
  next read-only Forward tool should be run.
- For config and NQE diffs, separate intended changes from unexpected changes.
- For snapshot diffs, start with counts/summary and drill into the changed
  domain that matters.
