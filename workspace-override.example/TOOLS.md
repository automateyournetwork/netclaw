# TOOLS.md — Local Infrastructure Notes

Skills define *how* tools work. This file is for *your* specifics — the environment details that are unique to your deployment.

## Network Devices

Devices are defined in `testbed/testbed.yaml`. Update that file with your SSH-accessible Cisco devices.

```
### Example Device Map
- R1 → 10.1.1.1, Core Router, IOS-XE 17.9
- R2 → 10.1.1.2, Distribution Router, IOS-XE 17.9
- SW1 → 10.1.2.1, Access Switch, IOS-XE 17.9
- SW2 → 10.1.2.2, Access Switch, IOS-XE 17.9
```

## Platform Credentials

All credentials are in `~/.openclaw/.env`. Never put credentials in skill files or this document.

```
### Batfish Configuration Analysis (reference only — actual values in .env)
- Batfish Host        → BATFISH_HOST (default: localhost)
- Batfish Port        → BATFISH_PORT (default: 9997)
- Batfish Network     → BATFISH_NETWORK (default: netclaw)
- Docker Container    → batfish/batfish (ports 9997, 9996)

### Connection Details (reference only — actual values in .env)
- pyATS Testbed       → PYATS_TESTBED_PATH
- NetBox              → NETBOX_URL, NETBOX_TOKEN
- ServiceNow          → SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD
- Cisco APIC          → APIC_URL, APIC_USERNAME, APIC_PASSWORD
- Cisco ISE           → ISE_BASE, ISE_USERNAME, ISE_PASSWORD
- NVD API             → NVD_API_KEY
- F5 BIG-IP           → F5_IP_ADDRESS, F5_AUTH_STRING
- Catalyst Center     → CCC_HOST, CCC_USER, CCC_PWD
- Microsoft Graph     → AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
- SuzieQ              → SUZIEQ_API_URL, SUZIEQ_API_KEY
- gNMI Telemetry      → GNMI_TARGETS (JSON), GNMI_TLS_CA_CERT, GNMI_TLS_CLIENT_CERT, GNMI_TLS_CLIENT_KEY
- Azure Network MCP   → AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID
- Canvas/A2UI Viz     → No new credentials (uses existing MCP server connections)
- Token Optimization  → ANTHROPIC_API_KEY (reused), NETCLAW_TOKEN_PRICING_OVERRIDE (optional)
- GitLab MCP          → GITLAB_PERSONAL_ACCESS_TOKEN, GITLAB_API_URL (default: gitlab.com)
- Jenkins MCP         → JENKINS_URL, JENKINS_AUTH_BASE64 (remote HTTP, Basic Auth)
```

## GitLab MCP Server

The GitLab MCP server (`@zereight/mcp-gitlab`) provides 98+ tools for GitLab operations via stdio transport:
- **Issues**: list_issues, get_issue, create_issue, update_issue, add_issue_comment, list_issue_comments
- **Merge Requests**: list_merge_requests, get_merge_request, create_merge_request, update_merge_request, merge_merge_request, add_merge_request_comment
- **Pipelines**: list_pipelines, get_pipeline, get_pipeline_jobs, get_pipeline_job_log, create_pipeline, retry_pipeline, cancel_pipeline
- **Repository**: list_repository_tree, get_file_content, list_commits, get_commit, compare_branches
- **Projects**: list_projects, get_project, search_projects
- **Labels**: list_labels, create_label, update_label, delete_label
- **Milestones**: list_milestones, create_milestone, update_milestone
- **Releases**: list_releases, get_release, create_release
- **Wiki**: list_wiki_pages, get_wiki_page, create_wiki_page, update_wiki_page, delete_wiki_page
- Supports gitlab.com and self-hosted instances via `GITLAB_API_URL`
- Read-only mode available via `GITLAB_READ_ONLY_MODE=true`

## Jenkins MCP Server

The Jenkins MCP server (official Jenkins plugin) provides 16 tools via Streamable HTTP transport:
- **Job Management**: getJob, getJobs, triggerBuild, getQueueItem
- **Build Operations**: getBuild, updateBuild, getBuildLog, searchBuildLog
- **SCM Integration**: getJobScm, getBuildScm, getBuildChangeSets, findJobsWithScmUrl
- **System**: whoAmI, getStatus
- **Pipeline**: getPipelineRuns, getPipelineRunLog
- Remote HTTP server running inside Jenkins (Streamable HTTP at `/mcp-server/mcp`)
- Auth: HTTP Basic with Jenkins API token (Base64-encoded username:token)
- Requires Jenkins 2.533+ with MCP Server plugin v0.158+

## Atlassian MCP Server

The Atlassian MCP server (community mcp-atlassian by sooperset) provides 72 tools via stdio transport:
- **Jira Issues**: jira_search, jira_get_issue, jira_create_issue, jira_update_issue, jira_delete_issue, jira_add_comment, jira_batch_create_issues
- **Jira Transitions**: jira_get_transitions, jira_transition_issue
- **Jira Projects/Fields**: jira_get_projects, jira_get_project, jira_get_fields, jira_get_issue_types
- **Jira Links**: jira_link_issues, jira_get_issue_links, jira_get_link_types
- **Confluence Pages**: confluence_search, confluence_get_page, confluence_create_page, confluence_update_page, confluence_delete_page
- **Confluence Comments**: confluence_get_page_comments, confluence_add_comment
- **Confluence Spaces**: confluence_get_spaces, confluence_get_space
- Supports Atlassian Cloud and Server/Data Center deployments
- Auth: API token (Cloud) or Personal Access Token (Server/DC)
- Runs via `uvx mcp-atlassian`

## Token Optimization Infrastructure

The `netclaw_tokens` shared library (`src/netclaw_tokens/`) provides token counting, TOON serialization, and cost tracking:
- **counter.py** — Token counting via Anthropic `count_tokens()` API with `len/4` fallback
- **toon_serializer.py** — TOON format serialization for MCP responses (40-60% savings on tabular data)
- **cost_calculator.py** — Model-aware pricing: Opus ($5/$25), Sonnet ($3/$15), Haiku ($1/$5) per 1M tokens
- **session_ledger.py** — Thread-safe cumulative session tracking with per-tool breakdown
- **footer.py** — Mandatory token/cost footer formatter for every interaction
- **toon_wrapper.py** — TOON conversion wrapper for community/remote MCP servers
- Pricing override via `NETCLAW_TOKEN_PRICING_OVERRIDE` env var (JSON format)
- Prompt caching discount: 90% off cached input tokens

## gNMI Infrastructure

The gNMI MCP server provides 10 tools for streaming telemetry and model-driven configuration:
- **gnmi_get** / **gnmi_set** / **gnmi_subscribe** / **gnmi_unsubscribe** / **gnmi_get_subscriptions** / **gnmi_get_subscription_updates** / **gnmi_capabilities** / **gnmi_browse_yang_paths** / **gnmi_compare_with_cli** / **gnmi_list_targets**
- Supported vendors: Cisco IOS-XR (port 57400), Juniper (32767), Arista (6030), Nokia SR OS (57400)
- YANG models: OpenConfig and vendor-native
- TLS mandatory, mTLS supported, max 50 concurrent subscriptions

## Slack Integration

```
### Channels
- #netclaw-alerts     → P1/P2 critical alerts
- #netclaw-reports    → Scheduled health reports, audit results
- #netclaw-general    → General queries, P3/P4 notifications
- #incidents          → Active incident threads
```

## Microsoft Teams Integration

```
### Teams Channels (if using Microsoft Graph for Teams delivery)
- #netclaw-alerts     → P1/P2 critical alerts, CVE exposure
- #netclaw-reports    → Health reports, audit results, reconciliation
- #netclaw-changes    → Change request updates, completion notices
- #network-general    → P3/P4 notifications, topology updates

### SharePoint Sites
- Network Engineering → Topology diagrams, audit reports, config backups
```

## SSH Access

```
### Jump Hosts / Bastion
- (your bastion host, if applicable)

### Console Servers
- (your console server, if applicable)
```

## Site Information

```
### Sites
- Site-A → Primary data center
- Site-B → DR site
- Lab    → Non-production test environment (relaxed change control)
```

## MemPalace AI Memory

19 MCP tools for persistent, structured, local-only AI memory across sessions ([source](https://github.com/milla-jovovich/mempalace)):
- **Palace**: status, wings, rooms, taxonomy, search, duplicates, AAAK spec, add/delete drawers
- **Knowledge Graph**: entity query, add/invalidate temporal triples, timeline, stats
- **Navigation**: room traversal, cross-wing tunnels, graph stats
- **Agent Diary**: write/read specialist agent journals (AAAK-compressed)
- Transport: stdio, Python 3.9+, no credentials, fully offline
- `MEMPALACE_MCP_SCRIPT` → cloned repo `mcp_server.py`

## Notes

- Add whatever helps NetClaw do its job — device nicknames, maintenance windows, ISP circuit IDs, TAC case numbers, anything environment-specific.
- This file is yours. Skills are shared. Keeping them apart means you can update skills without losing your notes.
