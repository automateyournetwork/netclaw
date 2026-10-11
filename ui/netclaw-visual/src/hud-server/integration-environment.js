// Shared static catalog. Reading this module never starts the HUD.
export const ENV_MAP = {
  security: {
    env: ['NETCLAW_LAB_MODE', 'N2N_RISK_MODE', 'N2N_STRICT_ALL', 'DEFENSECLAW_GUARD_PORT'],
    files: ['~/.openclaw/config/openclaw.json', '~/.defenseclaw/config.yaml', 'scripts/in2n-services.py', 'scripts/netclaw-secure-start.sh'],
    notes: 'Security mode values appear in Security. Presence here does not establish live enforcement. DefenseClaw security.mode belongs in ~/.openclaw/config/openclaw.json, not the gateway config.',
  },
  rag: {
    env: ['RAG_DATA_DIR', 'RAG_EMBEDDING_MODEL', 'RAG_RERANKER_MODEL', 'RAG_RERANK_ENABLED', 'RAG_RELEVANCE_FLOOR', 'RAG_MAX_DOC_MB', 'RAG_MAX_DOC_PAGES', 'RAG_CRAWL_MAX_PAGES', 'RAG_SNAPSHOT_WARN_DAYS', 'RAG_MAX_ROUNDS'],
    files: ['mcp-servers/rag-mcp/config.py'],
    notes: 'Local retrieval and indexing configuration. Defaults apply to unset optional variables.',
  },
  jev: {
    env: ['JEV_ENABLED', 'TYPESAFE_API_KEY', 'JEV_API_KEY', 'JEV_BASE_URL', 'JEV_MODEL', 'JEV_COMPATIBLE_API_KEY', 'JEV_COMPATIBLE_KEY_ENDPOINT', 'JEV_DAILY_LIMIT_USD', 'JEV_CASE_LIMIT_USD', 'JEV_TIMEOUT_SECONDS', 'JEV_DATA_DIR'],
    files: ['config/openclaw.json'],
    notes: 'Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration.',
  },
  pyats: {
    env: ['NETCLAW_USERNAME', 'NETCLAW_PASSWORD', 'NETCLAW_ENABLE_PASSWORD', 'PYATS_TESTBED_PATH', 'PYATS_MCP_SCRIPT'],
    files: ['testbed/testbed.yaml'],
    notes: 'Device credentials are referenced by testbed.yaml via %ENV{} syntax. Click "Edit Testbed" below to view/modify device inventory.',
  },
  aci: {
    env: ['APIC_URL', 'USERNAME', 'PASSWORD', 'ACI_MCP_SCRIPT'],
    files: [],
    notes: 'APIC controller endpoint and admin credentials. Per-MCP .env at mcp-servers/ACI_MCP/aci_mcp/.env is also loaded.',
  },
  ise: {
    env: ['ISE_BASE', 'ISE_USERNAME', 'ISE_PASSWORD', 'ISE_MCP_SCRIPT'],
    files: [],
    notes: 'ISE admin node REST API access.',
  },
  f5: {
    env: ['F5_IP_ADDRESS', 'F5_AUTH_STRING', 'F5_MCP_SCRIPT'],
    files: [],
    notes: 'BIG-IP iControl REST endpoint. Auth string is base64(user:pass).',
  },
  junos: {
    env: ['JUNOS_DEVICES_FILE', 'JUNOS_TIMEOUT'],
    files: [],
    notes: 'PyEZ/NETCONF device inventory JSON path.',
  },
  asa: {
    env: ['NETCLAW_USERNAME', 'NETCLAW_PASSWORD', 'NETCLAW_ENABLE_PASSWORD'],
    files: ['testbed/testbed.yaml'],
    notes: 'ASA firewall credentials via pyATS testbed.',
  },
  netbox: {
    env: ['NETBOX_URL', 'NETBOX_TOKEN', 'NETBOX_MCP_SCRIPT'],
    files: [],
    notes: 'NetBox instance URL and API token.',
  },
  nautobot: {
    env: ['NAUTOBOT_URL', 'NAUTOBOT_TOKEN'],
    files: [],
    notes: 'Nautobot instance URL and API token.',
  },
  infrahub: {
    env: ['INFRAHUB_ADDRESS', 'INFRAHUB_API_TOKEN'],
    files: [],
    notes: 'Infrahub GraphQL endpoint and API token.',
  },
  infoblox: {
    env: ['INFOBLOX_URL', 'INFOBLOX_USERNAME', 'INFOBLOX_PASSWORD'],
    files: [],
    notes: 'Infoblox WAPI endpoint.',
  },
  servicenow: {
    env: ['SERVICENOW_INSTANCE_URL', 'SERVICENOW_USERNAME', 'SERVICENOW_PASSWORD', 'SERVICENOW_MCP_SCRIPT'],
    files: [],
    notes: 'ServiceNow ITSM instance credentials.',
  },
  gait: {
    env: ['GAIT_MCP_SCRIPT'],
    files: [],
    notes: 'GAIT uses local Git — no external credentials needed.',
  },
  github: {
    env: ['GITHUB_PERSONAL_ACCESS_TOKEN'],
    files: [],
    notes: 'GitHub PAT for issues, PRs, code search, and Actions.',
  },
  gitlab: {
    env: ['GITLAB_PERSONAL_ACCESS_TOKEN', 'GITLAB_API_URL', 'GITLAB_READ_ONLY_MODE'],
    files: [],
    notes: 'GitLab PAT (api or read_api scope). GITLAB_API_URL defaults to gitlab.com; override for self-hosted.',
  },
  'chrome-devtools': {
    env: [],
    files: [],
    notes: 'No credentials, no env vars — chrome-devtools-mcp takes config as CLI flags only. Target-site auth is a one-time manual sign-in into its default persistent profile (see mcp-servers/chrome-devtools-mcp/README.md).',
  },
  'computer-use': {
    env: [],
    files: [],
    notes: 'No credentials, no env vars — installed via `openclaw skills install --global computer-use`, not config/openclaw.json. Live-viewing service (VNC 5900, noVNC 6080) is enforced loopback-only by the installer (see specs/050-computer-use-desktop/research.md R5).',
  },
  jenkins: {
    env: ['JENKINS_URL', 'JENKINS_USERNAME', 'JENKINS_API_TOKEN', 'JENKINS_AUTH_BASE64'],
    files: [],
    notes: 'Jenkins API token via HTTP Basic Auth. Remote HTTP transport at /mcp-server/mcp. Requires Jenkins 2.533+ with MCP Server plugin.',
  },
  atlassian: {
    env: ['JIRA_URL', 'JIRA_USERNAME', 'JIRA_API_TOKEN', 'CONFLUENCE_URL', 'CONFLUENCE_USERNAME', 'CONFLUENCE_API_TOKEN'],
    files: [],
    notes: 'Atlassian Cloud: API token from id.atlassian.com. Server/DC: Personal Access Token. At least one product (Jira or Confluence) required.',
  },
  halo: {
    env: ['HALO_BASE_URL', 'HALO_CLIENT_ID', 'HALO_CLIENT_SECRET', 'HALO_TENANT', 'HALO_SCOPE'],
    files: [],
    notes: 'HaloPSA/HaloITSM OAuth2 client-credentials. Create an API application in Halo (Configuration > Integrations > Halo API). HALO_BASE_URL is the tenant host, e.g. https://<tenant>.halopsa.com.',
  },
  meraki: {
    env: ['MERAKI_API_KEY', 'MERAKI_ORG_ID', 'ENABLE_CACHING', 'CACHE_TTL_SECONDS', 'READ_ONLY_MODE'],
    files: [],
    notes: 'Meraki Dashboard API key and org ID.',
  },
  sdwan: {
    env: ['VMANAGE_IP', 'VMANAGE_USERNAME', 'VMANAGE_PASSWORD', 'SDWAN_MCP_SCRIPT'],
    files: [],
    notes: 'vManage controller credentials (read-only).',
  },
  nso: {
    env: ['NSO_SCHEME', 'NSO_ADDRESS', 'NSO_PORT', 'NSO_USERNAME', 'NSO_PASSWORD'],
    files: [],
    notes: 'NSO RESTCONF endpoint credentials.',
  },
  itential: {
    env: ['ITENTIAL_MCP_PLATFORM_HOST', 'ITENTIAL_MCP_PLATFORM_CLIENT_ID', 'ITENTIAL_MCP_PLATFORM_CLIENT_SECRET'],
    files: [],
    notes: 'Itential Automation Platform OAuth 2.0 credentials.',
  },
  evpn: { env: [], files: [], notes: 'Uses pyATS device credentials from testbed.' },
  protocol: {
    env: ['NETCLAW_ROUTER_ID', 'NETCLAW_LOCAL_AS', 'NETCLAW_BGP_PEERS', 'NETCLAW_LAB_MODE', 'NETCLAW_MESH_OPEN', 'NETCLAW_LOCAL_IPV6', 'BGP_LISTEN_PORT', 'PROTOCOL_MCP_SCRIPT'],
    files: [],
    notes: 'BGP/OSPF protocol participation parameters.',
  },
  catc: {
    env: ['CCC_HOST', 'CCC_USER', 'CCC_PWD', 'CATC_MCP_SCRIPT'],
    files: [],
    notes: 'Catalyst Center (DNA-C) API credentials.',
  },
  arista: {
    env: ['CVP', 'CVPTOKEN'],
    files: [],
    notes: 'CloudVision Portal hostname and service account token.',
  },
  'bgp-intel': {
    env: ['BGP_INTEL_MCP_CMD', 'BGP_INTEL_USER_AGENT', 'BGP_INTEL_MAX_RPS', 'BGP_INTEL_AUDIT_LOG'],
    files: ['mcp-servers/bgp-intel-mcp/server.py'],
    notes: 'No credentials required — all five sources are public unauthenticated APIs. Read-only. Self-imposed 4 req/s serial ceiling against volunteer-funded infrastructure (RIPE NCC, PeeringDB). Every response carries its source and is GAIT-audited. RPKI not-found means no ROA exists and is NOT a finding.',
  },
  zabbix: {
    env: ['ZABBIX_MCP_CMD', 'ZABBIX_URL', 'ZABBIX_TOKEN', 'READ_ONLY', 'VERIFY_SSL', 'ZABBIX_API_BLACKLIST'],
    files: ['mcp-servers/zabbix-mcp/vendor/zabbix-mcp-server/src/zabbix_mcp_server/server.py'],
    notes: 'Vendored third-party (mpeirone/zabbix-mcp-server, GPL-3.0, pinned 0722f48), adopted UNMODIFIED and run from a dedicated virtualenv because it needs fastmcp 3.x while five NetClaw servers pin <3. Strictly read-only: NetClaw FORCES READ_ONLY=true because the upstream launcher inverts that default, plus a destructive-method deny-list as a second layer. Three tools, 589-token manifest. NOTE: this is a generic passthrough, so the two silent-wrong-answer traps (history.get defaults to the wrong value_type; raw history ages out into hourly trends) are enforced by the SKILLS, not by code — the first NetClaw integration where that is true. No per-call GAIT audit.',
  },
  anta: {
    env: ['ANTA_USERNAME', 'ANTA_PASSWORD', 'ANTA_ENABLE_PASSWORD', 'ANTA_VERIFY_TLS', 'ANTA_TIMEOUT'],
    files: ['mcp-servers/anta-mcp/server.py', 'mcp-servers/anta-mcp/verdict.py'],
    notes: 'NetClaw-authored thin server over ANTA 1.9.0 (Apache-2.0, Arista Networks) run from its OWN VIRTUALENV -- not a preference: a system install moves cryptography 46.0.5 -> 50.0.0 and four installed distributions depend on it with no upper bound (Authlib, pygnmi, service-identity, sshsig), including NetClaw federation TLS (spec 060). Measured by pip dry-run BEFORE installing, per spec 076. THE ASSERTION LAYER: everything else reads state, this asserts on it. 208 tests / 33 modules behind 4 tools = 1,272/5,000 tokens; one tool per test would be ~58,000 (11.6x), the Catalyst Center failure. Discovery tools contact NO device. SILENT WRONG ANSWER, reproduced live on clab-mandible-veos1: ANTA reports a test for an unconfigured feature as FAILURE -- VerifyBGPPeerCount returns "BGP inactive" as a failure on a switch with no BGP -- so the server reclassifies to not_applicable with a deliberately NARROW rule that never hides a real failure, preserving the original message. Five verdicts counted separately and a health percentage is REFUSED (passed/total is meaningless with not_applicable in the denominator). Unreachable device => error with zero results, never test failures. Read-only: ANTA tests, it never configures. No per-call GAIT audit.',
  },
  elastic: {
    env: ['ES_URL', 'ES_API_KEY', 'ES_USERNAME', 'ES_PASSWORD', 'ES_SSL_SKIP_VERIFY'],
    files: ['workspace/skills/elasticsearch-logs/SKILL.md'],
    notes: 'Adopted third-party (docker.elastic.co/mcp/elasticsearch, Apache-2.0, image 0.4.6 on rmcp 0.2.1), run as a digest-pinned container — NetClaw authors no server code and installs no cluster. Strictly read-only: 5 tools, 1,094/5,000 tokens, and the manifest contains no index/update/delete/reindex verb, so writes are unreachable regardless of credential. UPSTREAM IS DEPRECATED and adopted deliberately: the successor (Agent Builder MCP endpoint) is ENTERPRISE-tier on self-managed, so the supported path is paywalled while this one is Apache-2.0 and already published. Pinned by digest so a security-only update cannot change answers. SILENT WRONG ANSWER, reproduced live: Elasticsearch caps hits.total at 10,000 and marks it relation:"gte"; this server renders only the integer, so a capped floor reads as exact — 10,075 real documents reported as 10,000, and the error is unbounded (a million-doc index still says 10,000). Enforced by the SKILL, not by code: count via esql or search+track_total_hits, both verified to return 10,075. ES_URL resolves INSIDE the container — a host cluster is host.docker.internal, never localhost. No per-call GAIT audit.',
  },
  k8s: {
    env: ['K8S_MCP_CMD', 'K8S_KUBECONFIG'],
    files: ['mcp-servers/k8s-mcp/config.toml'],
    notes: 'Vendored third-party (containers/kubernetes-mcp-server v0.0.66, Apache-2.0 — licence-identical to NetClaw), a pinned statically-linked Go binary verified against a recorded SHA-256. Zero runtime deps, so it cannot collide with the fastmcp<3 pins. STRICTLY READ-ONLY, trimmed to 7 tools / 1,643 tokens — the upstream DEFAULT is 21 tools / 5,716 and busts the ceiling. Secrets denied by config AND by the ServiceAccount RBAC. Requires an EXPLICIT kubeconfig: every candidate otherwise defaults to the ambient current-context, which may be production. KNOWN UPSTREAM BEHAVIOUR: on insufficient RBAC it rewrites a cluster-wide query to one namespace and returns it with no error (resources.go:34-38) — reproduced live. Mitigated by mandating a cluster-wide-read ServiceAccount plus a skill preflight. No per-call GAIT audit.',
  },
  catc: {
    env: ['CATALYST_CENTER_HOST', 'CATALYST_CENTER_USERNAME', 'CATALYST_CENTER_PASSWORD', 'CATALYST_CENTER_VERIFY_SSL'],
    files: ['mcp-servers/catc-mcp/server.py'],
    notes: 'Strictly read-only: all 514 GET operations from Cisco official catc-mcp-oss catalogue (Apache-2.0, release/2.3.7.11), the single POST excluded. Reached via 8 grouped dispatchers + catc_find + catc_describe_operation = 1,821 tokens; inlining all 515 upstream tools measures 64,420 (12.9x the ceiling). NetClaw uses the CATALOGUE not the runtime, which avoids upstream unbounded fastmcp>=2.0.0 (collides with five servers pinning <3), its port-7001 HTTP transport, and a container. Every response is stamped at a chokepoint with WHICH APPLIANCE answered and WHEN — not cosmetic: sandboxdnac and sandboxdnac2 share credentials and one has zero devices. Empty results and ZERO COUNTS both carry an explicit caveat that they describe the controller, not the network.',
  },
  document: {
    env: ['DOCUMENT_MCP_CMD', 'DOCUMENT_OUTPUT_DIR', 'DOCUMENT_MAX_ROWS', 'DOCUMENT_MAX_BLOCKS', 'DOCUMENT_MAX_SLIDES', 'DOCUMENT_AUDIT_LOG'],
    files: ['mcp-servers/document-mcp/server.py'],
    notes: 'No credentials required — this server writes files and touches no device and no ticket. Every document carries its generation time, NetClaw attribution and a per-element source, stamped at a single chokepoint and GAIT-audited. A value without a source is refused; a missing value renders as NOT AVAILABLE, never as a blank. Office templates are refused (scratch-only); PDF form filling is supported because form fields are explicitly named. Output is timestamped in workspace/output/document-mcp/ and never overwritten.',
  },
  fortinet: {
    env: [
      'FORTINET_MCP_CMD',
      'FORTIMANAGER_HOST', 'FORTIMANAGER_API_TOKEN',
      'FORTIGATE_HOST', 'FORTIGATE_API_TOKEN',
      'FORTIANALYZER_HOST', 'FORTIANALYZER_API_TOKEN',
      'FORTINET_VERIFY_SSL', 'FORTINET_ALLOW_WRITES',
    ],
    files: ['mcp-servers/fortinet-mcp/server.py'],
    notes: 'Three planes, token auth per plane. Every response carries plane + scope and is GAIT-audited. Read-only unless FORTINET_ALLOW_WRITES=true, and writes still require human approval AND an approved ServiceNow change record.',
  },
  paloalto: {
    env: ['PANORAMA_URL', 'PANORAMA_API_KEY', 'PANOS_MCP_CMD'],
    files: [],
    notes: 'Panorama endpoint and API key.',
  },
  fmc: {
    env: ['FMC_BASE_URL', 'FMC_USERNAME', 'FMC_PASSWORD', 'FMC_VERIFY_SSL', 'FMC_PROFILES_DIR', 'FMC_PROFILE_DEFAULT'],
    files: [],
    notes: 'Cisco Secure Firewall Management Center API.',
  },
  nmap: {
    env: ['NMAP_ALLOWED_CIDRS', 'NMAP_MCP_SCRIPT'],
    files: [],
    notes: 'CIDR allowlist for nmap scope enforcement.',
  },
  nvd: {
    env: ['NVD_API_KEY', 'NVD_MCP_SCRIPT'],
    files: [],
    notes: 'NVD API key (optional but increases rate limits).',
  },
  grafana: {
    env: ['GRAFANA_URL', 'GRAFANA_SERVICE_ACCOUNT_TOKEN', 'GRAFANA_USERNAME', 'GRAFANA_PASSWORD', 'GRAFANA_ORG_ID'],
    files: [],
    notes: 'Grafana instance URL and service account or basic auth.',
  },
  prometheus: {
    env: ['PROMETHEUS_URL', 'PROMETHEUS_USERNAME', 'PROMETHEUS_PASSWORD', 'PROMETHEUS_TOKEN', 'PROMETHEUS_URL_SSL_VERIFY', 'PROMETHEUS_REQUEST_TIMEOUT', 'PROMETHEUS_DISABLE_LINKS'],
    files: [],
    notes: 'Direct Prometheus endpoint with auth options.',
  },
  thousandeyes: {
    env: ['TE_TOKEN'],
    files: [],
    notes: 'ThousandEyes OAuth bearer token.',
  },
  kubeshark: {
    env: ['KUBESHARK_MCP_URL', 'KUBESHARK_MCP_PORT'],
    files: [],
    notes: 'Kubeshark in-cluster MCP endpoint.',
  },
  gtrace: {
    env: ['GTRACE_MCP_BIN'],
    files: [],
    notes: 'gtrace Go binary path.',
  },
  suzieq: {
    env: ['SUZIEQ_API_URL', 'SUZIEQ_API_KEY', 'SUZIEQ_VERIFY_SSL', 'SUZIEQ_TIMEOUT'],
    files: [],
    notes: 'SuzieQ REST API URL and access token.',
  },
  aws: {
    env: ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'AWS_PROFILE'],
    files: [],
    notes: 'IAM credentials or named AWS CLI profile.',
  },
  gcp: {
    env: ['GCP_PROJECT_ID', 'GOOGLE_APPLICATION_CREDENTIALS'],
    files: [],
    notes: 'GCP project ID and service account JSON key path.',
  },
  cml: {
    env: ['CML_URL', 'CML_USERNAME', 'CML_PASSWORD', 'CML_VERIFY_SSL'],
    files: [],
    notes: 'Cisco Modeling Labs API endpoint.',
  },
  clab: {
    env: ['CLAB_API_SERVER_URL', 'CLAB_API_USERNAME', 'CLAB_API_PASSWORD', 'CLAB_MCP_SCRIPT'],
    files: [],
    notes: 'ContainerLab API server credentials.',
  },
  radkit: {
    env: ['RADKIT_IDENTITY', 'RADKIT_DEFAULT_SERVICE_SERIAL'],
    files: [],
    notes: 'Cisco RADKit identity and service serial.',
  },
  msgraph: {
    env: ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET'],
    files: [],
    notes: 'Azure AD app registration for Microsoft Graph API.',
  },
  'azure-network': {
    env: ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_SUBSCRIPTION_ID'],
    files: [],
    notes: 'Azure service principal with Reader role on target subscriptions.',
  },
  slack: {
    env: ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN'],
    files: [],
    notes: 'Slack bot and app-level tokens. Also configured in ~/.openclaw/openclaw.json channels.slack.',
  },
  webex: {
    env: ['WEBEX_BOT_TOKEN', 'WEBEX_ALERTS_ROOM_ID', 'WEBEX_REPORTS_ROOM_ID', 'WEBEX_INCIDENTS_ROOM_ID', 'WEBEX_WEBHOOK_URL', 'WEBEX_WEBHOOK_SECRET'],
    files: [],
    notes: 'WebEx bot token from developer.webex.com. Webhook URL required for inbound @mentions (ngrok for dev, public HTTPS for prod). Also configured in ~/.openclaw/openclaw.json channels.webex.',
  },
  drawio: { env: [], files: [], notes: 'draw.io MCP runs via npx — no external config.' },
  uml: {
    env: ['KROKI_SERVER', 'PLANTUML_SERVER', 'MCP_OUTPUT_DIR'],
    files: [],
    notes: 'Kroki/PlantUML rendering server URLs.',
  },
  markmap: {
    env: ['MARKMAP_MCP_SCRIPT'],
    files: [],
    notes: 'Markmap mind-map generation.',
  },
  wiki: {
    env: ['WIKIPEDIA_MCP_SCRIPT', 'SUBNET_MCP_SCRIPT', 'PACKET_BUDDY_MCP_SCRIPT'],
    files: [],
    notes: 'Reference tools — Wikipedia, subnet calc, packet analysis.',
  },
  aap: {
    env: ['AAP_URL', 'AAP_TOKEN', 'EDA_URL', 'EDA_TOKEN'],
    files: [],
    notes: 'Red Hat Ansible Automation Platform API endpoint and tokens. EDA token can match AAP token.',
  },
  fwrule: {
    env: ['FWRULE_MCP_DIR'],
    files: [],
    notes: 'Firewall rule analyzer — no credentials needed. Works on config text input. Supports PAN-OS, ASA, FTD, IOS, IOS-XR, Check Point, SRX, Junos, Nokia SR OS.',
  },
  batfish: {
    env: ['BATFISH_HOST', 'BATFISH_PORT', 'BATFISH_NETWORK'],
    files: ['mcp-servers/batfish-mcp/batfish_mcp_server.py'],
    notes: 'Batfish offline config analysis via Docker container. Requires: docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish',
  },
  gnmi: {
    env: ['GNMI_TARGETS', 'GNMI_TLS_CA_CERT', 'GNMI_TLS_CLIENT_CERT', 'GNMI_TLS_CLIENT_KEY', 'GNMI_TLS_SKIP_VERIFY', 'GNMI_DEFAULT_PORT', 'GNMI_MAX_RESPONSE_SIZE', 'GNMI_MAX_SUBSCRIPTIONS'],
    files: ['mcp-servers/gnmi-mcp/gnmi_mcp_server.py'],
    notes: 'gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory.',
  },
  gns3: {
    env: ['GNS3_URL', 'GNS3_USER', 'GNS3_PASSWORD', 'GNS3_VERIFY_SSL', 'GNS3_TOKEN_TTL'],
    files: ['mcp-servers/gns3-mcp-server/gns3_mcp_server.py'],
    notes: 'GNS3 network simulation server. URL is the GNS3 server address (e.g., http://localhost:3080). User/Password for authentication.',
  },
  'prisma-sdwan': {
    env: ['PAN_CLIENT_ID', 'PAN_CLIENT_SECRET', 'PAN_TSG_ID', 'PAN_REGION'],
    files: ['mcp-servers/prisma-sdwan-mcp/prisma_sdwan_mcp_server.py'],
    notes: 'Palo Alto Networks Prisma SD-WAN via OAuth2. Region is americas or europe. TSG_ID is the Tenant Service Group ID.',
  },
  'globalping': {
    env: ['GLOBALPING_TOKEN'],
    files: ['config/openclaw.json (remote endpoint — no vendored server)'],
    notes: 'Official jsDelivr remote MCP at https://mcp.globalping.dev/mcp, bearer token, streamable HTTP + SSE. No local server by design (spec 079 R1). 5 measurement tools (ping/traceroute/dns/mtr/http) plus limits/locations; 6 of the 12 advertised tools take only the analytics `context` argument. Budget is 500 probe-measurements/hour authenticated (250 anonymous per IP) and is charged PER PROBE — limit:20 spends 20 — so right-size limit rather than maximising it. Public targets only: RFC1918/loopback/link-local are refused locally BEFORE calling out, so internal addressing is never transmitted. Location syntax: + is AND (London+UK), arrays for multiple places, world for a global spread, AS3320 for an ASN; a comma inside one string fails, and AS13335 (the vendor\'s own schema example) never returns probes because Cloudflare hosts none. Every tool requires a natural-language `context` field the vendor uses for intent analytics — NetClaw sends a generic task-shaped value only.',
  },
  'topolograph': {
    env: ['TOPOLOGRAPH_API_TOKEN', 'TOPOLOGRAPH_MCP_URL'],
    files: ['config/openclaw.json (remote endpoint — no vendored server)'],
    notes: 'Remote HTTP MCP (spec 119 IGP, spec 120 BGP) against the operator\'s OWN Topolograph instance — TOPOLOGRAPH_MCP_URL overrides the default hosted endpoint, bearer TOPOLOGRAPH_API_TOKEN, 401 without it. Fronts an operator-run HTTP API developed upstream, so it is registered by url in config/openclaw.json rather than vendored (same shape as globalping). 27 read-only analysis tools: 13 IGP (get_all_graphs/get_graph_by_time/get_graph_status, get_nodes/get_edges/get_network_by_graph_time/get_lsps, get_shortest_path/get_cspf_path, get_edge_failure_reaction (failure simulation), get_network_events/get_adjacency_events/get_events_timeline) plus 14 BGP (list_bgp_graphs/get_bgp_graph, list_bgp_nodes/list_bgp_sessions, search_bgp_routes, get_bgp_node_route_summary/get_bgp_route_state, compare_bgp_routes, get_bgp_events_timeline, list_bgp_bindings/get_bgp_binding, resolve_route, get_vrf_inventory/list_vpn_routers — requires Topolograph >= 2.69). The server runs TOPOLOGRAPH_MCP_READ_ONLY=true so upload_graph and the *_lsp mutation tools are absent from tools/list; the client allowlist is set with `defenseclaw tool allow topolograph-mcp <tool>` (never toolFilter in config). Every result is over a STORED graph_time/bgp_graph_time — report its age — and get_edge_failure_reaction / get_cspf_path / resolve_route are predictions, not events. Boundary: reasons over the whole area LSDB or BGP RIB as a graph; per-device RIB/LSDB stays with pyats-routing / pyats-junos-routing / multivendor-device-query.',
  },
  'zoom-rtms': {
    env: ['ZOOM_CLIENT_ID', 'ZOOM_CLIENT_SECRET', 'ZOOM_ACCOUNT_ID', 'ZOOM_RTMS_WEBHOOK_SECRET',
          'N2N_ZOOM_CHANNEL_PORT', 'N2N_ZOOM_CHANNEL_SECRET'],
    files: ['mcp-servers/zoom-rtms-mcp/server.py'],
    notes: 'NetClaw for Zoom — Meeting Intelligence (spec 118). Realtime Media Streams (not a '
      + 'Meeting SDK bot) feed a deterministic extractor that recognizes network-investigation '
      + 'questions and routes them into the existing Border/NCFED path via a new loopback-only '
      + 'bgp/federation/zoom_channel.py channel. Feeds the Zoom App side panel (avatar + live '
      + 'status) with an optional Layers API camera overlay. No new device-write approval '
      + 'mechanism — reuses NetClaw\'s existing gate unchanged.',
  },
  'cisco-psirt': {
    env: ['CISCO_CLIENT_ID', 'CISCO_CLIENT_SECRET', 'CISCO_PSIRT_CACHE_DIR', 'CISCO_PSIRT_CACHE_TTL_S'],
    files: ['mcp-servers/cisco-psirt-mcp/server.py'],
    notes: 'Cisco PSIRT openVuln API via OAuth2 client credentials (id.cisco.com, 3600s token, refreshed proactively at 60s remaining). Read-only and device-free — versions are supplied by the caller from pyATS or multivendor-cli. Rate budget is 5/sec and 30/min shared, so lookups de-duplicate by version and cache for 6h on disk. Version format differs per family and contradicts across them: iosxe wants 17.3.1 and rejects 17.3(1), while ios wants 15.2(4)E and rejects 15.2.4E; aci wants the SWITCH image version 15.2(3e), not the APIC version. NOT available: iosxr (404, not an OSType), Bug/EoX/Case/Serial (403 under this grant), CX Cloud (504).',
  },
  'multivendor-cli': {
    env: ['MULTIVENDOR_INVENTORY_SOURCE', 'MULTIVENDOR_INVENTORY_PATH', 'MULTIVENDOR_WRITE_ENABLED', 'MULTIVENDOR_MAX_WORKERS', 'MULTIVENDOR_TIMEOUT_S', 'MULTIVENDOR_USERNAME', 'MULTIVENDOR_PASSWORD'],
    files: ['mcp-servers/multivendor-cli-mcp/server.py'],
    notes: 'Read-only by default; write tools absent from tools/list unless MULTIVENDOR_WRITE_ENABLED. Runs from its OWN virtualenv because napalm/netmiko resolve cryptography 49.x while the system carries 46.x, which NCFED uses for X.509 issuance. Writes are single-pathed per platform: refuses config change on Cisco/Junos and names the owning server.',
  },
  'telemetry-receivers': {
    env: ['SYSLOG_UDP_PORT', 'SNMP_TRAP_PORT', 'IPFIX_PORT', 'TELEMETRY_BUFFER_SIZE'],
    files: ['mcp-servers/telemetry-mcp/telemetry_mcp_server.py'],
    notes: 'Real-time telemetry receivers. Ports default to 514 (syslog), 162 (SNMP traps), 4739 (IPFIX). Buffer size controls in-memory retention.',
  },
  'config-archive': {
    env: ['CONFIG_ARCHIVE_PATH', 'CONFIG_ARCHIVE_RETENTION_DAYS'],
    files: [],
    notes: 'Configuration archive storage path and retention policy. Used for backup verification and drift detection.',
  },
  datadog: {
    env: ['DD_API_KEY', 'DD_APP_KEY', 'DD_SITE'],
    files: [],
    notes: 'Datadog MCP Server via remote HTTP. API/App keys from Datadog organization settings. Site defaults to datadoghq.com (use datadoghq.eu for EU).',
  },
  pagerduty: {
    env: ['PAGERDUTY_USER_API_KEY', 'PAGERDUTY_API_HOST'],
    files: [],
    notes: 'PagerDuty MCP Server via uvx. User API key from PagerDuty API settings. API host defaults to US (use api.eu.pagerduty.com for EU).',
  },
  splunk: {
    env: ['SPLUNK_HOST', 'SPLUNK_TOKEN', 'SPLUNK_VERIFY_SSL'],
    files: [],
    notes: 'Splunk MCP Server via uvx. Host is the Splunk management port URL (e.g., https://splunk:8089). Token is a Splunk auth token.',
  },
  terraform: {
    env: ['TFC_TOKEN', 'TFC_ORG', 'TFC_HOST'],
    files: [],
    notes: 'Terraform Cloud MCP Server via remote HTTP. API token from Terraform Cloud settings. Host defaults to app.terraform.io.',
  },
  vault: {
    env: ['VAULT_ADDR', 'VAULT_TOKEN', 'VAULT_NAMESPACE'],
    files: [],
    notes: 'HashiCorp Vault MCP Server via remote HTTP. Server address and auth token. Namespace is for Vault Enterprise only.',
  },
  zscaler: {
    env: ['ZSCALER_ZIA_API_KEY', 'ZSCALER_ZIA_USERNAME', 'ZSCALER_ZIA_PASSWORD', 'ZSCALER_ZIA_CLOUD', 'ZSCALER_ZPA_CLIENT_ID', 'ZSCALER_ZPA_CLIENT_SECRET', 'ZSCALER_ZPA_CUSTOMER_ID'],
    files: [],
    notes: 'Zscaler MCP Server via remote HTTP. ZIA credentials for internet access, ZPA credentials for private access. Multiple clouds supported.',
  },
  equinix: {
    env: ['EQUINIX_ENABLED', 'EQUINIX_ALLOW_WRITES', 'EQUINIX_AUTH_DIR', 'EQUINIX_SERVICENOW_URL', 'EQUINIX_SERVICENOW_USERNAME', 'EQUINIX_SERVICENOW_PASSWORD'],
    files: ['scripts/equinix-stdio.py', 'docs/EQUINIX.md'],
    notes: 'Browser OAuth required. Viewer for reads; Operator/Manager plus exact approved Implement CR, baseline and GAIT for writes. OAuth cache is member-isolated. Configured does not mean authenticated; no delete tools.',
  },
  cloudflare: {
    env: ['CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_ZONE_ID'],
    files: [],
    notes: 'Cloudflare MCP Servers (5 domain-specific). API token from Cloudflare dashboard. Account ID required, Zone ID optional.',
  },
  checkpoint: {
    env: ['CHKP_MGMT_HOST', 'CHKP_MGMT_PORT', 'CHKP_MGMT_API_KEY', 'CHKP_MGMT_USERNAME', 'CHKP_MGMT_PASSWORD', 'CHKP_MGMT_DOMAIN', 'CHKP_S1C_API_KEY', 'CHKP_S1C_URL', 'CHKP_REPUTATION_API_KEY', 'CHKP_SASE_API_KEY', 'CHKP_SASE_MGMT_HOST', 'CHKP_TE_API_KEY', 'CHKP_SPARK_API_KEY', 'CHKP_ARGOS_API_KEY', 'CHKP_TELEMETRY_DISABLED', 'CHKP_LOG_LEVEL'],
    files: ['mcp-servers/checkpoint-mcp-servers/'],
    notes: 'Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh',
  },
  auvik: {
    env: ['AUVIK_USERNAME', 'AUVIK_API_KEY', 'AUVIK_BASE_URL'],
    files: [],
    notes: 'Auvik user email + API key (HTTP Basic). AUVIK_BASE_URL defaults to the us1 cluster; override for other regions.',
  },
  claroty: {
    env: ['CLAROTY_API_URL', 'CLAROTY_API_TOKEN', 'CLAROTY_VERIFY_SSL', 'CLAROTY_TIMEOUT', 'CLAROTY_RATE_LIMIT_PER_MIN', 'NETCLAW_LAB_MODE'],
    files: ['mcp-servers/claroty-mcp/.env'],
    notes: 'Claroty xDome MCP — OT / IoT / IoMT visibility. Bearer token from xDome Admin Settings > User Management. Writes require a ServiceNow CR; NETCLAW_LAB_MODE=true skips the state check (shared with gnmi-mcp).',
  },
  'threejs-viz': {
    env: ['SKETCHFAB_API_KEY', 'SKETCHFAB_USERNAME'],
    files: ['mcp-servers/sketchfab-mcp-server/'],
    notes: 'Only needed for optional real-3D-model stencil mode. Token from https://sketchfab.com/settings/password. Procedural-shape rendering works with zero configuration.',
  },
  'comfyui-viz': {
    env: ['COMFYUI_URL'],
    files: ['mcp-servers/comfyui-mcp/', 'mcp-servers/topology-diagram-mcp/', 'mcp-servers/image-style-mcp/'],
    notes: 'Endpoint of a separately-running ComfyUI instance (not installed/managed by NetClaw). Requires at least one image-generation checkpoint installed in ComfyUI itself — reports a distinct, actionable message if none is found rather than failing silently. The federated path (spec 121) additionally requires the johns-risk/viz federation member to be live.',
  },
  'worldlabs-viz': {
    env: ['WLT_API_KEY'],
    files: ['mcp-servers/worldlabs-marble-mcp/', 'workspace/skills/worldlabs-topology-viz/'],
    notes: 'Only needed for the generate step (spends real World Labs credits, ~5 minutes per world) — the free preview mode needs no credential at all. Requires a funded World Labs account (platform.worldlabs.ai/billing). generate_world itself refuses to run without an explicit user_confirmed=true argument, in addition to the conversational confirmation the skill also requires.',
  },
};
