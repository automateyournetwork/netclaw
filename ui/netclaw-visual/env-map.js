// Generated from config/components/catalog.json by scripts/build-catalog.py.
export const ENV_MAP = {
  "security": {
    "env": [
      "NETCLAW_LAB_MODE",
      "N2N_RISK_MODE",
      "N2N_STRICT_ALL",
      "DEFENSECLAW_GUARD_PORT"
    ],
    "files": [
      "~/.openclaw/config/openclaw.json",
      "~/.defenseclaw/config.yaml",
      "scripts/in2n-services.py",
      "scripts/netclaw-secure-start.sh"
    ],
    "notes": "Security mode values appear in Security. Presence here does not establish live enforcement. DefenseClaw security.mode belongs in ~/.openclaw/config/openclaw.json, not the gateway config."
  },
  "rag": {
    "env": [
      "RAG_DATA_DIR",
      "RAG_EMBEDDING_MODEL",
      "RAG_RERANKER_MODEL",
      "RAG_RERANK_ENABLED",
      "RAG_RELEVANCE_FLOOR",
      "RAG_MAX_DOC_MB",
      "RAG_MAX_DOC_PAGES",
      "RAG_CRAWL_MAX_PAGES",
      "RAG_SNAPSHOT_WARN_DAYS",
      "RAG_MAX_ROUNDS"
    ],
    "files": [
      "mcp-servers/rag-mcp/config.py"
    ],
    "notes": "Local retrieval and indexing configuration. Defaults apply to unset optional variables."
  },
  "jev": {
    "env": [
      "JEV_ENABLED",
      "TYPESAFE_API_KEY",
      "JEV_API_KEY",
      "JEV_BASE_URL",
      "JEV_MODEL",
      "JEV_COMPATIBLE_API_KEY",
      "JEV_COMPATIBLE_KEY_ENDPOINT",
      "JEV_DAILY_LIMIT_USD",
      "JEV_CASE_LIMIT_USD",
      "JEV_TIMEOUT_SECONDS",
      "JEV_DATA_DIR"
    ],
    "files": [
      "config/openclaw.json"
    ],
    "notes": "Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration."
  },
  "pyats": {
    "env": [
      "NETCLAW_USERNAME",
      "NETCLAW_PASSWORD",
      "NETCLAW_ENABLE_PASSWORD",
      "PYATS_TESTBED_PATH",
      "PYATS_MCP_SCRIPT",
      "PYATS_VENV",
      "PYATS_UPSTREAM_SCRIPT"
    ],
    "files": [
      "testbed/testbed.yaml"
    ],
    "notes": "Device credentials are referenced by testbed.yaml via %ENV{} syntax. Click \"Edit Testbed\" below to view/modify device inventory."
  },
  "aci": {
    "env": [
      "APIC_URL",
      "USERNAME",
      "PASSWORD",
      "ACI_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "APIC controller endpoint and admin credentials. Per-MCP .env at mcp-servers/ACI_MCP/aci_mcp/.env is also loaded."
  },
  "ise": {
    "env": [
      "ISE_BASE",
      "ISE_USERNAME",
      "ISE_PASSWORD",
      "ISE_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "ISE admin node REST API access."
  },
  "f5": {
    "env": [
      "F5_IP_ADDRESS",
      "F5_AUTH_STRING",
      "F5_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "BIG-IP iControl REST endpoint. Auth string is base64(user:pass)."
  },
  "junos": {
    "env": [
      "JUNOS_DEVICES_FILE",
      "JUNOS_TIMEOUT"
    ],
    "files": [],
    "notes": "PyEZ/NETCONF device inventory JSON path."
  },
  "asa": {
    "env": [
      "NETCLAW_USERNAME",
      "NETCLAW_PASSWORD",
      "NETCLAW_ENABLE_PASSWORD"
    ],
    "files": [
      "testbed/testbed.yaml"
    ],
    "notes": "ASA firewall credentials via pyATS testbed."
  },
  "netbox": {
    "env": [
      "NETBOX_URL",
      "NETBOX_TOKEN",
      "NETBOX_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "NetBox instance URL and API token."
  },
  "nautobot": {
    "env": [
      "NAUTOBOT_URL",
      "NAUTOBOT_TOKEN"
    ],
    "files": [],
    "notes": "Nautobot instance URL and API token."
  },
  "infrahub": {
    "env": [
      "INFRAHUB_ADDRESS",
      "INFRAHUB_API_TOKEN"
    ],
    "files": [],
    "notes": "Infrahub GraphQL endpoint and API token."
  },
  "infoblox": {
    "env": [
      "INFOBLOX_URL",
      "INFOBLOX_USERNAME",
      "INFOBLOX_PASSWORD"
    ],
    "files": [],
    "notes": "Infoblox WAPI endpoint."
  },
  "servicenow": {
    "env": [
      "SERVICENOW_INSTANCE_URL",
      "SERVICENOW_USERNAME",
      "SERVICENOW_PASSWORD",
      "SERVICENOW_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "ServiceNow ITSM instance credentials."
  },
  "gait": {
    "env": [
      "GAIT_MCP_SCRIPT",
      "GAIT_VENV"
    ],
    "files": [],
    "notes": "GAIT uses local Git — no external credentials needed."
  },
  "github": {
    "env": [
      "GITHUB_PERSONAL_ACCESS_TOKEN"
    ],
    "files": [],
    "notes": "GitHub PAT for issues, PRs, code search, and Actions."
  },
  "gitlab": {
    "env": [
      "GITLAB_PERSONAL_ACCESS_TOKEN",
      "GITLAB_API_URL",
      "GITLAB_READ_ONLY_MODE"
    ],
    "files": [],
    "notes": "GitLab PAT (api or read_api scope). GITLAB_API_URL defaults to gitlab.com; override for self-hosted."
  },
  "chrome-devtools": {
    "env": [],
    "files": [],
    "notes": "No credentials, no env vars — chrome-devtools-mcp takes config as CLI flags only. Target-site auth is a one-time manual sign-in into its default persistent profile (see mcp-servers/chrome-devtools-mcp/README.md)."
  },
  "computer-use": {
    "env": [],
    "files": [],
    "notes": "No credentials, no env vars — installed via `openclaw skills install --global computer-use`, not config/openclaw.json. Live-viewing service (VNC 5900, noVNC 6080) is enforced loopback-only by the installer (see specs/050-computer-use-desktop/research.md R5)."
  },
  "jenkins": {
    "env": [
      "JENKINS_URL",
      "JENKINS_USERNAME",
      "JENKINS_API_TOKEN",
      "JENKINS_AUTH_BASE64"
    ],
    "files": [],
    "notes": "Jenkins API token via HTTP Basic Auth. Remote HTTP transport at /mcp-server/mcp. Requires Jenkins 2.533+ with MCP Server plugin."
  },
  "atlassian": {
    "env": [
      "JIRA_URL",
      "JIRA_USERNAME",
      "JIRA_API_TOKEN",
      "CONFLUENCE_URL",
      "CONFLUENCE_USERNAME",
      "CONFLUENCE_API_TOKEN"
    ],
    "files": [],
    "notes": "Atlassian Cloud: API token from id.atlassian.com. Server/DC: Personal Access Token. At least one product (Jira or Confluence) required."
  },
  "halo": {
    "env": [
      "HALO_BASE_URL",
      "HALO_CLIENT_ID",
      "HALO_CLIENT_SECRET",
      "HALO_TENANT",
      "HALO_SCOPE"
    ],
    "files": [],
    "notes": "HaloPSA/HaloITSM OAuth2 client-credentials. Create an API application in Halo (Configuration > Integrations > Halo API). HALO_BASE_URL is the tenant host, e.g. https://<tenant>.halopsa.com."
  },
  "meraki": {
    "env": [
      "MERAKI_API_KEY",
      "MERAKI_ORG_ID",
      "ENABLE_CACHING",
      "CACHE_TTL_SECONDS",
      "READ_ONLY_MODE"
    ],
    "files": [],
    "notes": "Meraki Dashboard API key and org ID."
  },
  "sdwan": {
    "env": [
      "VMANAGE_IP",
      "VMANAGE_USERNAME",
      "VMANAGE_PASSWORD",
      "SDWAN_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "vManage controller credentials (read-only)."
  },
  "nso": {
    "env": [
      "NSO_SCHEME",
      "NSO_ADDRESS",
      "NSO_PORT",
      "NSO_USERNAME",
      "NSO_PASSWORD"
    ],
    "files": [],
    "notes": "NSO RESTCONF endpoint credentials."
  },
  "itential": {
    "env": [
      "ITENTIAL_MCP_PLATFORM_HOST",
      "ITENTIAL_MCP_PLATFORM_CLIENT_ID",
      "ITENTIAL_MCP_PLATFORM_CLIENT_SECRET"
    ],
    "files": [],
    "notes": "Itential Automation Platform OAuth 2.0 credentials."
  },
  "evpn": {
    "env": [],
    "files": [],
    "notes": "Uses pyATS device credentials from testbed."
  },
  "protocol": {
    "env": [
      "NETCLAW_ROUTER_ID",
      "NETCLAW_LOCAL_AS",
      "NETCLAW_BGP_PEERS",
      "NETCLAW_LAB_MODE",
      "NETCLAW_MESH_OPEN",
      "NETCLAW_LOCAL_IPV6",
      "BGP_LISTEN_PORT",
      "PROTOCOL_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "BGP/OSPF protocol participation parameters."
  },
  "arista": {
    "env": [
      "CVP",
      "CVPTOKEN"
    ],
    "files": [],
    "notes": "CloudVision Portal hostname and service account token."
  },
  "bgp-intel": {
    "env": [
      "BGP_INTEL_MCP_CMD",
      "BGP_INTEL_USER_AGENT",
      "BGP_INTEL_MAX_RPS",
      "BGP_INTEL_AUDIT_LOG"
    ],
    "files": [
      "mcp-servers/bgp-intel-mcp/server.py"
    ],
    "notes": "No credentials required — all five sources are public unauthenticated APIs. Read-only. Self-imposed 4 req/s serial ceiling against volunteer-funded infrastructure (RIPE NCC, PeeringDB). Every response carries its source and is GAIT-audited. RPKI not-found means no ROA exists and is NOT a finding."
  },
  "zabbix": {
    "env": [
      "ZABBIX_MCP_CMD",
      "ZABBIX_URL",
      "ZABBIX_TOKEN",
      "READ_ONLY",
      "VERIFY_SSL",
      "ZABBIX_API_BLACKLIST"
    ],
    "files": [
      "mcp-servers/zabbix-mcp/vendor/zabbix-mcp-server/src/zabbix_mcp_server/server.py"
    ],
    "notes": "Vendored third-party (mpeirone/zabbix-mcp-server, GPL-3.0, pinned 0722f48), adopted UNMODIFIED and run from a dedicated virtualenv because it needs fastmcp 3.x while five NetClaw servers pin <3. Strictly read-only: NetClaw FORCES READ_ONLY=true because the upstream launcher inverts that default, plus a destructive-method deny-list as a second layer. Three tools, 589-token manifest. NOTE: this is a generic passthrough, so the two silent-wrong-answer traps (history.get defaults to the wrong value_type; raw history ages out into hourly trends) are enforced by the SKILLS, not by code — the first NetClaw integration where that is true. No per-call GAIT audit."
  },
  "anta": {
    "env": [
      "ANTA_USERNAME",
      "ANTA_PASSWORD",
      "ANTA_ENABLE_PASSWORD",
      "ANTA_VERIFY_TLS",
      "ANTA_TIMEOUT"
    ],
    "files": [
      "mcp-servers/anta-mcp/server.py",
      "mcp-servers/anta-mcp/verdict.py"
    ],
    "notes": "NetClaw-authored thin server over ANTA 1.9.0 (Apache-2.0, Arista Networks) run from its OWN VIRTUALENV -- not a preference: a system install moves cryptography 46.0.5 -> 50.0.0 and four installed distributions depend on it with no upper bound (Authlib, pygnmi, service-identity, sshsig), including NetClaw federation TLS (spec 060). Measured by pip dry-run BEFORE installing, per spec 076. THE ASSERTION LAYER: everything else reads state, this asserts on it. 208 tests / 33 modules behind 4 tools = 1,272/5,000 tokens; one tool per test would be ~58,000 (11.6x), the Catalyst Center failure. Discovery tools contact NO device. SILENT WRONG ANSWER, reproduced live on clab-mandible-veos1: ANTA reports a test for an unconfigured feature as FAILURE -- VerifyBGPPeerCount returns \"BGP inactive\" as a failure on a switch with no BGP -- so the server reclassifies to not_applicable with a deliberately NARROW rule that never hides a real failure, preserving the original message. Five verdicts counted separately and a health percentage is REFUSED (passed/total is meaningless with not_applicable in the denominator). Unreachable device => error with zero results, never test failures. Read-only: ANTA tests, it never configures. No per-call GAIT audit."
  },
  "elastic": {
    "env": [
      "ES_URL",
      "ES_API_KEY",
      "ES_USERNAME",
      "ES_PASSWORD",
      "ES_SSL_SKIP_VERIFY"
    ],
    "files": [
      "workspace/skills/elasticsearch-logs/SKILL.md"
    ],
    "notes": "Adopted third-party (docker.elastic.co/mcp/elasticsearch, Apache-2.0, image 0.4.6 on rmcp 0.2.1), run as a digest-pinned container — NetClaw authors no server code and installs no cluster. Strictly read-only: 5 tools, 1,094/5,000 tokens, and the manifest contains no index/update/delete/reindex verb, so writes are unreachable regardless of credential. UPSTREAM IS DEPRECATED and adopted deliberately: the successor (Agent Builder MCP endpoint) is ENTERPRISE-tier on self-managed, so the supported path is paywalled while this one is Apache-2.0 and already published. Pinned by digest so a security-only update cannot change answers. SILENT WRONG ANSWER, reproduced live: Elasticsearch caps hits.total at 10,000 and marks it relation:\"gte\"; this server renders only the integer, so a capped floor reads as exact — 10,075 real documents reported as 10,000, and the error is unbounded (a million-doc index still says 10,000). Enforced by the SKILL, not by code: count via esql or search+track_total_hits, both verified to return 10,075. ES_URL resolves INSIDE the container — a host cluster is host.docker.internal, never localhost. No per-call GAIT audit."
  },
  "k8s": {
    "env": [
      "K8S_MCP_CMD",
      "K8S_KUBECONFIG"
    ],
    "files": [
      "mcp-servers/k8s-mcp/config.toml"
    ],
    "notes": "Vendored third-party (containers/kubernetes-mcp-server v0.0.66, Apache-2.0 — licence-identical to NetClaw), a pinned statically-linked Go binary verified against a recorded SHA-256. Zero runtime deps, so it cannot collide with the fastmcp<3 pins. STRICTLY READ-ONLY, trimmed to 7 tools / 1,643 tokens — the upstream DEFAULT is 21 tools / 5,716 and busts the ceiling. Secrets denied by config AND by the ServiceAccount RBAC. Requires an EXPLICIT kubeconfig: every candidate otherwise defaults to the ambient current-context, which may be production. KNOWN UPSTREAM BEHAVIOUR: on insufficient RBAC it rewrites a cluster-wide query to one namespace and returns it with no error (resources.go:34-38) — reproduced live. Mitigated by mandating a cluster-wide-read ServiceAccount plus a skill preflight. No per-call GAIT audit."
  },
  "catc": {
    "env": [
      "CATALYST_CENTER_HOST",
      "CATALYST_CENTER_USERNAME",
      "CATALYST_CENTER_PASSWORD",
      "CATALYST_CENTER_VERIFY_SSL"
    ],
    "files": [
      "mcp-servers/catc-mcp/server.py"
    ],
    "notes": "Strictly read-only: all 514 GET operations from Cisco official catc-mcp-oss catalogue (Apache-2.0, release/2.3.7.11), the single POST excluded. Reached via 8 grouped dispatchers + catc_find + catc_describe_operation = 1,821 tokens; inlining all 515 upstream tools measures 64,420 (12.9x the ceiling). NetClaw uses the CATALOGUE not the runtime, which avoids upstream unbounded fastmcp>=2.0.0 (collides with five servers pinning <3), its port-7001 HTTP transport, and a container. Every response is stamped at a chokepoint with WHICH APPLIANCE answered and WHEN — not cosmetic: sandboxdnac and sandboxdnac2 share credentials and one has zero devices. Empty results and ZERO COUNTS both carry an explicit caveat that they describe the controller, not the network."
  },
  "document": {
    "env": [
      "DOCUMENT_MCP_CMD",
      "DOCUMENT_OUTPUT_DIR",
      "DOCUMENT_MAX_ROWS",
      "DOCUMENT_MAX_BLOCKS",
      "DOCUMENT_MAX_SLIDES",
      "DOCUMENT_AUDIT_LOG"
    ],
    "files": [
      "mcp-servers/document-mcp/server.py"
    ],
    "notes": "No credentials required — this server writes files and touches no device and no ticket. Every document carries its generation time, NetClaw attribution and a per-element source, stamped at a single chokepoint and GAIT-audited. A value without a source is refused; a missing value renders as NOT AVAILABLE, never as a blank. Office templates are refused (scratch-only); PDF form filling is supported because form fields are explicitly named. Output is timestamped in workspace/output/document-mcp/ and never overwritten."
  },
  "fortinet": {
    "env": [
      "FORTINET_MCP_CMD",
      "FORTIMANAGER_HOST",
      "FORTIMANAGER_API_TOKEN",
      "FORTIGATE_HOST",
      "FORTIGATE_API_TOKEN",
      "FORTIANALYZER_HOST",
      "FORTIANALYZER_API_TOKEN",
      "FORTINET_VERIFY_SSL",
      "FORTINET_ALLOW_WRITES"
    ],
    "files": [
      "mcp-servers/fortinet-mcp/server.py"
    ],
    "notes": "Three planes, token auth per plane. Every response carries plane + scope and is GAIT-audited. Read-only unless FORTINET_ALLOW_WRITES=true, and writes still require human approval AND an approved ServiceNow change record."
  },
  "paloalto": {
    "env": [
      "PANORAMA_URL",
      "PANORAMA_API_KEY",
      "PANOS_MCP_CMD"
    ],
    "files": [],
    "notes": "Panorama endpoint and API key."
  },
  "fmc": {
    "env": [
      "FMC_BASE_URL",
      "FMC_USERNAME",
      "FMC_PASSWORD",
      "FMC_VERIFY_SSL",
      "FMC_PROFILES_DIR",
      "FMC_PROFILE_DEFAULT"
    ],
    "files": [],
    "notes": "Cisco Secure Firewall Management Center API."
  },
  "nmap": {
    "env": [
      "NMAP_ALLOWED_CIDRS",
      "NMAP_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "CIDR allowlist for nmap scope enforcement."
  },
  "nvd": {
    "env": [
      "NVD_API_KEY",
      "NVD_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "NVD API key (optional but increases rate limits)."
  },
  "grafana": {
    "env": [
      "GRAFANA_URL",
      "GRAFANA_SERVICE_ACCOUNT_TOKEN",
      "GRAFANA_USERNAME",
      "GRAFANA_PASSWORD",
      "GRAFANA_ORG_ID"
    ],
    "files": [],
    "notes": "Grafana instance URL and service account or basic auth."
  },
  "prometheus": {
    "env": [
      "PROMETHEUS_URL",
      "PROMETHEUS_USERNAME",
      "PROMETHEUS_PASSWORD",
      "PROMETHEUS_TOKEN",
      "PROMETHEUS_URL_SSL_VERIFY",
      "PROMETHEUS_REQUEST_TIMEOUT",
      "PROMETHEUS_DISABLE_LINKS"
    ],
    "files": [],
    "notes": "Direct Prometheus endpoint with auth options."
  },
  "thousandeyes": {
    "env": [
      "TE_TOKEN"
    ],
    "files": [],
    "notes": "ThousandEyes OAuth bearer token."
  },
  "kubeshark": {
    "env": [
      "KUBESHARK_MCP_URL",
      "KUBESHARK_MCP_PORT"
    ],
    "files": [],
    "notes": "Kubeshark in-cluster MCP endpoint."
  },
  "gtrace": {
    "env": [
      "GTRACE_MCP_BIN"
    ],
    "files": [],
    "notes": "gtrace Go binary path."
  },
  "suzieq": {
    "env": [
      "SUZIEQ_API_URL",
      "SUZIEQ_API_KEY",
      "SUZIEQ_VERIFY_SSL",
      "SUZIEQ_TIMEOUT"
    ],
    "files": [],
    "notes": "SuzieQ REST API URL and access token."
  },
  "aws": {
    "env": [
      "AWS_ACCESS_KEY_ID",
      "AWS_SECRET_ACCESS_KEY",
      "AWS_REGION",
      "AWS_PROFILE"
    ],
    "files": [],
    "notes": "IAM credentials or named AWS CLI profile."
  },
  "gcp": {
    "env": [
      "GCP_PROJECT_ID",
      "GOOGLE_APPLICATION_CREDENTIALS"
    ],
    "files": [],
    "notes": "GCP project ID and service account JSON key path."
  },
  "cml": {
    "env": [
      "CML_URL",
      "CML_USERNAME",
      "CML_PASSWORD",
      "CML_VERIFY_SSL"
    ],
    "files": [],
    "notes": "Cisco Modeling Labs API endpoint."
  },
  "clab": {
    "env": [
      "CLAB_API_SERVER_URL",
      "CLAB_API_USERNAME",
      "CLAB_API_PASSWORD",
      "CLAB_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "ContainerLab API server credentials."
  },
  "radkit": {
    "env": [
      "RADKIT_IDENTITY",
      "RADKIT_DEFAULT_SERVICE_SERIAL"
    ],
    "files": [],
    "notes": "Cisco RADKit identity and service serial."
  },
  "msgraph": {
    "env": [
      "AZURE_TENANT_ID",
      "AZURE_CLIENT_ID",
      "AZURE_CLIENT_SECRET"
    ],
    "files": [],
    "notes": "Azure AD app registration for Microsoft Graph API."
  },
  "azure-network": {
    "env": [
      "AZURE_TENANT_ID",
      "AZURE_CLIENT_ID",
      "AZURE_CLIENT_SECRET",
      "AZURE_SUBSCRIPTION_ID"
    ],
    "files": [],
    "notes": "Azure service principal with Reader role on target subscriptions."
  },
  "slack": {
    "env": [
      "SLACK_BOT_TOKEN",
      "SLACK_APP_TOKEN"
    ],
    "files": [],
    "notes": "Slack bot and app-level tokens. Also configured in ~/.openclaw/openclaw.json channels.slack."
  },
  "webex": {
    "env": [
      "WEBEX_BOT_TOKEN",
      "WEBEX_ALERTS_ROOM_ID",
      "WEBEX_REPORTS_ROOM_ID",
      "WEBEX_INCIDENTS_ROOM_ID",
      "WEBEX_WEBHOOK_URL",
      "WEBEX_WEBHOOK_SECRET"
    ],
    "files": [],
    "notes": "WebEx bot token from developer.webex.com. Webhook URL required for inbound @mentions (ngrok for dev, public HTTPS for prod). Also configured in ~/.openclaw/openclaw.json channels.webex."
  },
  "drawio": {
    "env": [],
    "files": [],
    "notes": "draw.io MCP runs via npx — no external config."
  },
  "uml": {
    "env": [
      "KROKI_SERVER",
      "PLANTUML_SERVER",
      "MCP_OUTPUT_DIR"
    ],
    "files": [],
    "notes": "Kroki/PlantUML rendering server URLs."
  },
  "markmap": {
    "env": [
      "MARKMAP_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "Markmap mind-map generation."
  },
  "wiki": {
    "env": [
      "WIKIPEDIA_MCP_SCRIPT",
      "SUBNET_MCP_SCRIPT",
      "PACKET_BUDDY_MCP_SCRIPT"
    ],
    "files": [],
    "notes": "Reference tools — Wikipedia, subnet calc, packet analysis."
  },
  "aap": {
    "env": [
      "AAP_URL",
      "AAP_TOKEN",
      "EDA_URL",
      "EDA_TOKEN"
    ],
    "files": [],
    "notes": "Red Hat Ansible Automation Platform API endpoint and tokens. EDA token can match AAP token."
  },
  "fwrule": {
    "env": [
      "FWRULE_MCP_DIR"
    ],
    "files": [],
    "notes": "Firewall rule analyzer — no credentials needed. Works on config text input. Supports PAN-OS, ASA, FTD, IOS, IOS-XR, Check Point, SRX, Junos, Nokia SR OS."
  },
  "batfish": {
    "env": [
      "BATFISH_HOST",
      "BATFISH_PORT",
      "BATFISH_NETWORK"
    ],
    "files": [
      "mcp-servers/batfish-mcp/batfish_mcp_server.py"
    ],
    "notes": "Batfish offline config analysis via Docker container. Requires: docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish"
  },
  "gnmi": {
    "env": [
      "GNMI_TARGETS",
      "GNMI_TLS_CA_CERT",
      "GNMI_TLS_CLIENT_CERT",
      "GNMI_TLS_CLIENT_KEY",
      "GNMI_TLS_SKIP_VERIFY",
      "GNMI_DEFAULT_PORT",
      "GNMI_MAX_RESPONSE_SIZE",
      "GNMI_MAX_SUBSCRIPTIONS"
    ],
    "files": [
      "mcp-servers/gnmi-mcp/gnmi_mcp_server.py"
    ],
    "notes": "gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory."
  },
  "gns3": {
    "env": [
      "GNS3_URL",
      "GNS3_USER",
      "GNS3_PASSWORD",
      "GNS3_VERIFY_SSL",
      "GNS3_TOKEN_TTL"
    ],
    "files": [
      "mcp-servers/gns3-mcp-server/gns3_mcp_server.py"
    ],
    "notes": "GNS3 network simulation server. URL is the GNS3 server address (e.g., http://localhost:3080). User/Password for authentication."
  },
  "prisma-sdwan": {
    "env": [
      "PAN_CLIENT_ID",
      "PAN_CLIENT_SECRET",
      "PAN_TSG_ID",
      "PAN_REGION"
    ],
    "files": [
      "mcp-servers/prisma-sdwan-mcp/prisma_sdwan_mcp_server.py"
    ],
    "notes": "Palo Alto Networks Prisma SD-WAN via OAuth2. Region is americas or europe. TSG_ID is the Tenant Service Group ID."
  },
  "globalping": {
    "env": [
      "GLOBALPING_TOKEN"
    ],
    "files": [
      "config/openclaw.json (remote endpoint — no vendored server)"
    ],
    "notes": "Official jsDelivr remote MCP at https://mcp.globalping.dev/mcp, bearer token, streamable HTTP + SSE. No local server by design (spec 079 R1). 5 measurement tools (ping/traceroute/dns/mtr/http) plus limits/locations; 6 of the 12 advertised tools take only the analytics `context` argument. Budget is 500 probe-measurements/hour authenticated (250 anonymous per IP) and is charged PER PROBE — limit:20 spends 20 — so right-size limit rather than maximising it. Public targets only: RFC1918/loopback/link-local are refused locally BEFORE calling out, so internal addressing is never transmitted. Location syntax: + is AND (London+UK), arrays for multiple places, world for a global spread, AS3320 for an ASN; a comma inside one string fails, and AS13335 (the vendor's own schema example) never returns probes because Cloudflare hosts none. Every tool requires a natural-language `context` field the vendor uses for intent analytics — NetClaw sends a generic task-shaped value only."
  },
  "topolograph": {
    "env": [
      "TOPOLOGRAPH_API_TOKEN",
      "TOPOLOGRAPH_MCP_URL"
    ],
    "files": [
      "config/openclaw.json (remote endpoint — no vendored server)"
    ],
    "notes": "Remote HTTP MCP (spec 119 IGP, spec 120 BGP) against the operator's OWN Topolograph instance — TOPOLOGRAPH_MCP_URL overrides the default hosted endpoint, bearer TOPOLOGRAPH_API_TOKEN, 401 without it. Fronts an operator-run HTTP API developed upstream, so it is registered by url in config/openclaw.json rather than vendored (same shape as globalping). 27 read-only analysis tools: 13 IGP (get_all_graphs/get_graph_by_time/get_graph_status, get_nodes/get_edges/get_network_by_graph_time/get_lsps, get_shortest_path/get_cspf_path, get_edge_failure_reaction (failure simulation), get_network_events/get_adjacency_events/get_events_timeline) plus 14 BGP (list_bgp_graphs/get_bgp_graph, list_bgp_nodes/list_bgp_sessions, search_bgp_routes, get_bgp_node_route_summary/get_bgp_route_state, compare_bgp_routes, get_bgp_events_timeline, list_bgp_bindings/get_bgp_binding, resolve_route, get_vrf_inventory/list_vpn_routers — requires Topolograph >= 2.69). The server runs TOPOLOGRAPH_MCP_READ_ONLY=true so upload_graph and the *_lsp mutation tools are absent from tools/list; the client allowlist is set with `defenseclaw tool allow topolograph-mcp <tool>` (never toolFilter in config). Every result is over a STORED graph_time/bgp_graph_time — report its age — and get_edge_failure_reaction / get_cspf_path / resolve_route are predictions, not events. Boundary: reasons over the whole area LSDB or BGP RIB as a graph; per-device RIB/LSDB stays with pyats-routing / pyats-junos-routing / multivendor-device-query."
  },
  "zoom-rtms": {
    "env": [
      "ZOOM_CLIENT_ID",
      "ZOOM_CLIENT_SECRET",
      "ZOOM_ACCOUNT_ID",
      "ZOOM_RTMS_WEBHOOK_SECRET",
      "N2N_ZOOM_CHANNEL_PORT",
      "N2N_ZOOM_CHANNEL_SECRET"
    ],
    "files": [
      "mcp-servers/zoom-rtms-mcp/server.py"
    ],
    "notes": "NetClaw for Zoom — Meeting Intelligence (spec 118). Realtime Media Streams (not a Meeting SDK bot) feed a deterministic extractor that recognizes network-investigation questions and routes them into the existing Border/NCFED path via a new loopback-only bgp/federation/zoom_channel.py channel. Feeds the Zoom App side panel (avatar + live status) with an optional Layers API camera overlay. No new device-write approval mechanism — reuses NetClaw's existing gate unchanged."
  },
  "cisco-psirt": {
    "env": [
      "CISCO_CLIENT_ID",
      "CISCO_CLIENT_SECRET",
      "CISCO_PSIRT_CACHE_DIR",
      "CISCO_PSIRT_CACHE_TTL_S"
    ],
    "files": [
      "mcp-servers/cisco-psirt-mcp/server.py"
    ],
    "notes": "Cisco PSIRT openVuln API via OAuth2 client credentials (id.cisco.com, 3600s token, refreshed proactively at 60s remaining). Read-only and device-free — versions are supplied by the caller from pyATS or multivendor-cli. Rate budget is 5/sec and 30/min shared, so lookups de-duplicate by version and cache for 6h on disk. Version format differs per family and contradicts across them: iosxe wants 17.3.1 and rejects 17.3(1), while ios wants 15.2(4)E and rejects 15.2.4E; aci wants the SWITCH image version 15.2(3e), not the APIC version. NOT available: iosxr (404, not an OSType), Bug/EoX/Case/Serial (403 under this grant), CX Cloud (504)."
  },
  "multivendor-cli": {
    "env": [
      "MULTIVENDOR_INVENTORY_SOURCE",
      "MULTIVENDOR_INVENTORY_PATH",
      "MULTIVENDOR_WRITE_ENABLED",
      "MULTIVENDOR_MAX_WORKERS",
      "MULTIVENDOR_TIMEOUT_S",
      "MULTIVENDOR_USERNAME",
      "MULTIVENDOR_PASSWORD"
    ],
    "files": [
      "mcp-servers/multivendor-cli-mcp/server.py"
    ],
    "notes": "Read-only by default; write tools absent from tools/list unless MULTIVENDOR_WRITE_ENABLED. Runs from its OWN virtualenv because napalm/netmiko resolve cryptography 49.x while the system carries 46.x, which NCFED uses for X.509 issuance. Writes are single-pathed per platform: refuses config change on Cisco/Junos and names the owning server."
  },
  "telemetry-receivers": {
    "env": [
      "SYSLOG_UDP_PORT",
      "SNMP_TRAP_PORT",
      "IPFIX_PORT",
      "TELEMETRY_BUFFER_SIZE"
    ],
    "files": [
      "mcp-servers/telemetry-mcp/telemetry_mcp_server.py"
    ],
    "notes": "Real-time telemetry receivers. Ports default to 514 (syslog), 162 (SNMP traps), 4739 (IPFIX). Buffer size controls in-memory retention."
  },
  "config-archive": {
    "env": [
      "CONFIG_ARCHIVE_PATH",
      "CONFIG_ARCHIVE_RETENTION_DAYS"
    ],
    "files": [],
    "notes": "Configuration archive storage path and retention policy. Used for backup verification and drift detection."
  },
  "datadog": {
    "env": [
      "DD_API_KEY",
      "DD_APP_KEY",
      "DD_SITE"
    ],
    "files": [],
    "notes": "Datadog MCP Server via remote HTTP. API/App keys from Datadog organization settings. Site defaults to datadoghq.com (use datadoghq.eu for EU)."
  },
  "pagerduty": {
    "env": [
      "PAGERDUTY_USER_API_KEY",
      "PAGERDUTY_API_HOST"
    ],
    "files": [],
    "notes": "PagerDuty MCP Server via uvx. User API key from PagerDuty API settings. API host defaults to US (use api.eu.pagerduty.com for EU)."
  },
  "splunk": {
    "env": [
      "SPLUNK_HOST",
      "SPLUNK_TOKEN",
      "SPLUNK_VERIFY_SSL"
    ],
    "files": [],
    "notes": "Splunk MCP Server via uvx. Host is the Splunk management port URL (e.g., https://splunk:8089). Token is a Splunk auth token."
  },
  "terraform": {
    "env": [
      "TFC_TOKEN",
      "TFC_ORG",
      "TFC_HOST"
    ],
    "files": [],
    "notes": "Terraform Cloud MCP Server via remote HTTP. API token from Terraform Cloud settings. Host defaults to app.terraform.io."
  },
  "vault": {
    "env": [
      "VAULT_ADDR",
      "VAULT_TOKEN",
      "VAULT_NAMESPACE"
    ],
    "files": [],
    "notes": "HashiCorp Vault MCP Server via remote HTTP. Server address and auth token. Namespace is for Vault Enterprise only."
  },
  "zscaler": {
    "env": [
      "ZSCALER_ZIA_API_KEY",
      "ZSCALER_ZIA_USERNAME",
      "ZSCALER_ZIA_PASSWORD",
      "ZSCALER_ZIA_CLOUD",
      "ZSCALER_ZPA_CLIENT_ID",
      "ZSCALER_ZPA_CLIENT_SECRET",
      "ZSCALER_ZPA_CUSTOMER_ID"
    ],
    "files": [],
    "notes": "Zscaler MCP Server via remote HTTP. ZIA credentials for internet access, ZPA credentials for private access. Multiple clouds supported."
  },
  "equinix": {
    "env": [
      "EQUINIX_ENABLED",
      "EQUINIX_ALLOW_WRITES",
      "EQUINIX_AUTH_DIR",
      "EQUINIX_SERVICENOW_URL",
      "EQUINIX_SERVICENOW_USERNAME",
      "EQUINIX_SERVICENOW_PASSWORD"
    ],
    "files": [
      "scripts/equinix-stdio.py",
      "docs/EQUINIX.md"
    ],
    "notes": "Browser OAuth required. Viewer for reads; Operator/Manager plus exact approved Implement CR, baseline and GAIT for writes. OAuth cache is member-isolated. Configured does not mean authenticated; no delete tools."
  },
  "cloudflare": {
    "env": [
      "CLOUDFLARE_API_TOKEN",
      "CLOUDFLARE_ACCOUNT_ID",
      "CLOUDFLARE_ZONE_ID"
    ],
    "files": [],
    "notes": "Cloudflare MCP Servers (5 domain-specific). API token from Cloudflare dashboard. Account ID required, Zone ID optional."
  },
  "checkpoint": {
    "env": [
      "CHKP_MGMT_HOST",
      "CHKP_MGMT_PORT",
      "CHKP_MGMT_API_KEY",
      "CHKP_MGMT_USERNAME",
      "CHKP_MGMT_PASSWORD",
      "CHKP_MGMT_DOMAIN",
      "CHKP_S1C_API_KEY",
      "CHKP_S1C_URL",
      "CHKP_REPUTATION_API_KEY",
      "CHKP_SASE_API_KEY",
      "CHKP_SASE_MGMT_HOST",
      "CHKP_TE_API_KEY",
      "CHKP_SPARK_API_KEY",
      "CHKP_ARGOS_API_KEY",
      "CHKP_TELEMETRY_DISABLED",
      "CHKP_LOG_LEVEL"
    ],
    "files": [
      "mcp-servers/checkpoint-mcp-servers/"
    ],
    "notes": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh"
  },
  "auvik": {
    "env": [
      "AUVIK_USERNAME",
      "AUVIK_API_KEY",
      "AUVIK_BASE_URL"
    ],
    "files": [],
    "notes": "Auvik user email + API key (HTTP Basic). AUVIK_BASE_URL defaults to the us1 cluster; override for other regions."
  },
  "claroty": {
    "env": [
      "CLAROTY_API_URL",
      "CLAROTY_API_TOKEN",
      "CLAROTY_VERIFY_SSL",
      "CLAROTY_TIMEOUT",
      "CLAROTY_RATE_LIMIT_PER_MIN",
      "NETCLAW_LAB_MODE"
    ],
    "files": [
      "mcp-servers/claroty-mcp/.env"
    ],
    "notes": "Claroty xDome MCP — OT / IoT / IoMT visibility. Bearer token from xDome Admin Settings > User Management. Writes require a ServiceNow CR; NETCLAW_LAB_MODE=true skips the state check (shared with gnmi-mcp)."
  },
  "threejs-viz": {
    "env": [
      "SKETCHFAB_API_KEY",
      "SKETCHFAB_USERNAME"
    ],
    "files": [
      "mcp-servers/sketchfab-mcp-server/"
    ],
    "notes": "Only needed for optional real-3D-model stencil mode. Token from https://sketchfab.com/settings/password. Procedural-shape rendering works with zero configuration."
  },
  "comfyui-viz": {
    "env": [
      "COMFYUI_URL"
    ],
    "files": [
      "mcp-servers/comfyui-mcp/",
      "mcp-servers/topology-diagram-mcp/",
      "mcp-servers/image-style-mcp/"
    ],
    "notes": "Endpoint of a separately-running ComfyUI instance (not installed/managed by NetClaw). Requires at least one image-generation checkpoint installed in ComfyUI itself — reports a distinct, actionable message if none is found rather than failing silently. The federated path (spec 121) additionally requires the johns-risk/viz federation member to be live."
  },
  "worldlabs-viz": {
    "env": [
      "WLT_API_KEY"
    ],
    "files": [
      "mcp-servers/worldlabs-marble-mcp/",
      "workspace/skills/worldlabs-topology-viz/"
    ],
    "notes": "Only needed for the generate step (spends real World Labs credits, ~5 minutes per world) — the free preview mode needs no credential at all. Requires a funded World Labs account (platform.worldlabs.ai/billing). generate_world itself refuses to run without an explicit user_confirmed=true argument, in addition to the conversational confirmation the skill also requires."
  },
  "convergence-read": {
    "env": [
      "CONVERGENCE_ENABLED",
      "CONVERGENCE_API_URL",
      "CONVERGENCE_API_TOKEN",
      "CONVERGENCE_SITE",
      "CONVERGENCE_EXPORTERS",
      "CONVERGENCE_ALLOW_LOOPBACK_HTTP"
    ],
    "files": [
      "mcp-servers/convergence-read-mcp/server.py"
    ],
    "notes": "Optional read-only retained-flow connector."
  }
};
export const COMPONENT_ALIASES = {
  "security": [],
  "rag": [
    "rag-mcp"
  ],
  "jev": [
    "jev"
  ],
  "pyats": [
    "pyats"
  ],
  "aci": [
    "aci"
  ],
  "ise": [
    "ise"
  ],
  "f5": [
    "f5"
  ],
  "junos": [
    "junos"
  ],
  "asa": [
    "pyats"
  ],
  "netbox": [
    "netbox"
  ],
  "nautobot": [
    "nautobot"
  ],
  "infrahub": [
    "infrahub"
  ],
  "infoblox": [
    "infoblox"
  ],
  "servicenow": [
    "servicenow"
  ],
  "gait": [
    "gait"
  ],
  "github": [
    "github"
  ],
  "gitlab": [
    "gitlab"
  ],
  "chrome-devtools": [
    "chrome-devtools"
  ],
  "computer-use": [
    "computer-use"
  ],
  "jenkins": [
    "jenkins"
  ],
  "atlassian": [
    "atlassian"
  ],
  "halo": [
    "halo"
  ],
  "meraki": [
    "meraki"
  ],
  "sdwan": [
    "sdwan"
  ],
  "nso": [
    "nso"
  ],
  "itential": [
    "itential"
  ],
  "evpn": [
    "pyats"
  ],
  "protocol": [
    "protocol",
    "n2n"
  ],
  "arista": [
    "arista-cvp"
  ],
  "bgp-intel": [
    "bgp-intel"
  ],
  "zabbix": [
    "zabbix"
  ],
  "anta": [
    "anta"
  ],
  "elastic": [
    "elastic"
  ],
  "k8s": [
    "k8s"
  ],
  "catc": [
    "catc"
  ],
  "document": [
    "document"
  ],
  "fortinet": [
    "fortinet"
  ],
  "paloalto": [
    "panorama"
  ],
  "fmc": [
    "fmc"
  ],
  "nmap": [
    "nmap"
  ],
  "nvd": [
    "nvd-cve"
  ],
  "grafana": [
    "grafana"
  ],
  "prometheus": [
    "prometheus"
  ],
  "thousandeyes": [
    "te-official",
    "te-community"
  ],
  "kubeshark": [
    "kubeshark"
  ],
  "gtrace": [
    "gtrace"
  ],
  "suzieq": [
    "suzieq"
  ],
  "aws": [
    "aws"
  ],
  "gcp": [
    "gcp"
  ],
  "cml": [
    "cml"
  ],
  "clab": [
    "containerlab"
  ],
  "radkit": [
    "radkit"
  ],
  "msgraph": [
    "msgraph"
  ],
  "azure-network": [
    "azure"
  ],
  "slack": [],
  "webex": [],
  "drawio": [
    "drawio-rfc"
  ],
  "uml": [
    "uml"
  ],
  "markmap": [
    "markmap"
  ],
  "wiki": [
    "wikipedia"
  ],
  "aap": [
    "aap"
  ],
  "fwrule": [
    "fwrule"
  ],
  "batfish": [
    "batfish"
  ],
  "gnmi": [
    "gnmi"
  ],
  "gns3": [
    "gns3"
  ],
  "prisma-sdwan": [
    "prisma-sdwan"
  ],
  "globalping": [
    "globalping"
  ],
  "topolograph": [
    "topolograph"
  ],
  "zoom-rtms": [
    "zoom-rtms"
  ],
  "cisco-psirt": [
    "cisco-psirt"
  ],
  "multivendor-cli": [
    "multivendor-cli"
  ],
  "telemetry-receivers": [
    "telemetry-receivers"
  ],
  "config-archive": [],
  "datadog": [
    "datadog"
  ],
  "pagerduty": [
    "pagerduty"
  ],
  "splunk": [
    "splunk"
  ],
  "terraform": [
    "terraform"
  ],
  "vault": [
    "vault"
  ],
  "zscaler": [
    "zscaler"
  ],
  "equinix": [
    "equinix"
  ],
  "cloudflare": [
    "cloudflare"
  ],
  "checkpoint": [
    "checkpoint"
  ],
  "auvik": [
    "auvik"
  ],
  "claroty": [
    "claroty"
  ],
  "threejs-viz": [
    "threejs-viz"
  ],
  "comfyui-viz": [
    "comfyui-viz"
  ],
  "worldlabs-viz": [
    "worldlabs-marble"
  ],
  "convergence-read": [
    "convergence-read"
  ]
};
export const COMPONENT_SETTINGS = {
  "hermes-hud": [
    {
      "key": "HERMES_HOME",
      "label": "Hermes Home",
      "help": "Generated for this selected installation by the scoped adapter. HERMES_HOME is consumed by the selected Hermes HUD bridge registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "mcp-servers/hermes-hud-mcp/federation_server.py#L14",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_HERMES_HUD_API_KEY",
      "label": "Netclaw Hermes Hud Api Key",
      "help": "Generated for this selected installation by the scoped adapter. NETCLAW_HERMES_HUD_API_KEY is consumed by the selected Hermes HUD bridge registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_HUD_INSTALLATION_ID",
      "label": "Netclaw Hud Installation Id",
      "help": "Generated for this selected installation by the scoped adapter. NETCLAW_HUD_INSTALLATION_ID is consumed by the selected Hermes HUD bridge registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "mcp-servers/hermes-hud-mcp/server.py#L20",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "pyats": [
    {
      "key": "NETCLAW_ENABLE_PASSWORD",
      "label": "Netclaw Enable Password",
      "help": "Device login reference for static and dynamic testbeds. Separate from inventory-source credentials; missing references block dynamic activation.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#pyats-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_PASSWORD",
      "label": "Netclaw Password",
      "help": "Device login reference for static and dynamic testbeds. Separate from inventory-source credentials; missing references block dynamic activation.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#pyats-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_USERNAME",
      "label": "Netclaw Username",
      "help": "Device login reference for static and dynamic testbeds. Separate from inventory-source credentials; missing references block dynamic activation.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#pyats-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PYATS_MCP_SCRIPT",
      "label": "Pyats Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Device credentials are referenced by testbed.yaml via %ENV{} syntax. Click \"Edit Testbed\" below to view/modify device inventory. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "./scripts/pyats-stdio.py",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#pyats-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PYATS_TESTBED_PATH",
      "label": "Pyats Testbed Path",
      "help": "Static inventory path, used only in static mode. Dynamic MCP candidates are separate from the HUD static editor and collector.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "./testbed/testbed.yaml",
      "sharedWith": [
        "netbox"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#pyats-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PYATS_UPSTREAM_SCRIPT",
      "label": "Pyats Upstream Script",
      "help": "Generated for this selected installation by the scoped adapter. Device credentials are referenced by testbed.yaml via %ENV{} syntax. Click \"Edit Testbed\" below to view/modify device inventory. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "~/.openclaw/pyats-venv/upstream/pyats_mcp_server.py",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "scripts/pyats-stdio.py#L79",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#pyats-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PYATS_VENV",
      "label": "Pyats Venv",
      "help": "Generated for this selected installation by the scoped adapter. Device credentials are referenced by testbed.yaml via %ENV{} syntax. Click \"Edit Testbed\" below to view/modify device inventory. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "~/.openclaw/pyats-venv",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "scripts/pyats-stdio.py#L76",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#pyats-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_TESTBED_MODE",
      "label": "Testbed mode",
      "help": "Static file or dynamic MCP inventory. Change through installer Testbed mode, not this generated field.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "static",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "scripts/lib/pyats_testbeds.py",
          "checkedAt": "2026-10-30",
          "note": "Selected installation policy; source access and active inventory are separate."
        }
      ]
    },
    {
      "key": "NETCLAW_TESTBED_SOURCES",
      "label": "Dynamic source selection",
      "help": "Selected source IDs. Existing source MCP or reviewed export; no fetch or activation during setup.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "netbox,cml",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "scripts/lib/pyats_testbeds.py",
          "checkedAt": "2026-10-30",
          "note": "Selected installation policy; source access and active inventory are separate."
        }
      ]
    },
    {
      "key": "PYATS_MCP_DYNAMIC_ONLY",
      "label": "Dynamic-only runtime",
      "help": "Managed from mode. Dynamic child clears static path and requires explicit build, validation and activation.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "1",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "scripts/lib/pyats_testbeds.py",
          "checkedAt": "2026-10-30",
          "note": "Selected installation policy; source access and active inventory are separate."
        }
      ]
    }
  ],
  "junos": [
    {
      "key": "JUNOS_DEVICES_FILE",
      "label": "Junos Devices File",
      "help": "Juniper JunOS (PyEZ/NETCONF device automation — 10 tools)",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "devices.json",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#junos-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JUNOS_TIMEOUT",
      "label": "Junos Timeout",
      "help": "PyEZ/NETCONF device inventory JSON path.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "360",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#junos-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "arista-cvp": [
    {
      "key": "CVP",
      "label": "Cvp",
      "help": "Arista CloudVision Portal (CVP) — inventory, events, connectivity, tags (4 tools)",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "www.arista.io",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#arista-cvp-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CVPTOKEN",
      "label": "Cvptoken",
      "help": "CloudVision Portal hostname and service account token.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#arista-cvp-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "f5": [
    {
      "key": "F5_AUTH_STRING",
      "label": "F5 Auth String",
      "help": "BIG-IP iControl REST endpoint. Auth string is base64(user:pass).",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "F5_IP_ADDRESS",
      "label": "F5 Ip Address",
      "help": "BIG-IP iControl REST endpoint. Auth string is base64(user:pass).",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "F5_MCP_SCRIPT",
      "label": "F5 Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. BIG-IP iControl REST endpoint. Auth string is base64(user:pass). Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MCP_CALL",
      "label": "Mcp Call",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "catc",
        "cisco-psirt",
        "mempalace",
        "nvd-cve",
        "subnet-calc"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "catc": [
    {
      "key": "CATALYST_CENTER_HOST",
      "label": "Catalyst Center Host",
      "help": "NOTE the DevNet always-on sandboxes share credentials and are NOT equivalent: sandboxdnac.cisco.com   -> 4 devices, 25 sites   (use this one) sandboxdnac2.cisco.com  -> 0 devices,  1 site    (authenticates, but empty) An inventory answer from the second looks identical to a real empty estate, which is why every response names the appliance it came from.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/catc-mcp/server.py#L53",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#catc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CATALYST_CENTER_PASSWORD",
      "label": "Catalyst Center Password",
      "help": "Strictly read-only: all 514 GET operations from Cisco official catc-mcp-oss catalogue (Apache-2.0, release/2.3.7.11), the single POST excluded. Reached via 8 grouped dispatchers + catc_find + catc_describe_operation = 1,821 tokens; inlining all 515 upstream tools measures 64,420 (12.9x the ceiling). NetClaw uses the CATALOGUE not the runtime, which avoids upstream unbounded fastmcp>=2.0.0 (collides with five servers pinning <3), its port-7001 HTTP transport, and a container. Every response is stamped at a chokepoint with WHICH APPLIANCE answered and WHEN — not cosmetic: sandboxdnac and sandboxdnac2 share credentials and one has zero devices. Empty results and ZERO COUNTS both carry an explicit caveat that they describe the controller, not the network.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/catc-mcp/server.py#L113",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#catc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CATALYST_CENTER_USERNAME",
      "label": "Catalyst Center Username",
      "help": "Use a DEDICATED, LEAST-PRIVILEGE, READ-ONLY account. The upstream project is explicit that its catalogue \"does not enforce read-only access\"; NetClaw's curation is one control and this account's RBAC is the other.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/catc-mcp/server.py#L113",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#catc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CATALYST_CENTER_VERIFY_SSL",
      "label": "Catalyst Center Verify Ssl",
      "help": "TLS verification. Defaults to true. The DevNet sandboxes use self-signed certificates, so a lab needs false — never disable it against production. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/catc-mcp/server.py#L140",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#catc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CATC_MCP_SCRIPT",
      "label": "Catc Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#catc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MCP_CALL",
      "label": "Mcp Call",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "cisco-psirt",
        "f5",
        "mempalace",
        "nvd-cve",
        "subnet-calc"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#catc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "aruba-cx": [
    {
      "key": "ARUBA_CX_CONFIG",
      "label": "Aruba Cx Config",
      "help": "ARUBA_CX_CONFIG is consumed by the selected Aruba CX registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aruba-cx-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ARUBA_CX_TARGETS",
      "label": "Aruba Cx Targets",
      "help": "Aruba CX MCP Server (16 tools: 11 read-only, 5 write for HPE Aruba CX switches) Community server: https://github.com/slientnight/aruba-cx-mcp-server Read: system info, interfaces, VLANs, configs, routing, LLDP, MAC table, DOM, ISSU, firmware, VSF Write: interface config, VLAN management, config save, ISSU upgrade, firmware (requires ITSM CR)",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aruba-cx-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ARUBA_CX_TIMEOUT",
      "label": "Aruba Cx Timeout",
      "help": "ARUBA_CX_TIMEOUT is consumed by the selected Aruba CX registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "30",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aruba-cx-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITSM_ENABLED",
      "label": "Itsm Enabled",
      "help": "ITSM_ENABLED is consumed by the selected Aruba CX registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [
        "nautobot",
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aruba-cx-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITSM_LAB_MODE",
      "label": "Itsm Lab Mode",
      "help": "ITSM_LAB_MODE is consumed by the selected Aruba CX registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [
        "nautobot",
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aruba-cx-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "gnmi": [
    {
      "key": "GNMI_DEFAULT_PORT",
      "label": "Gnmi Default Port",
      "help": "gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "6030",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/gnmi_client.py#L76",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNMI_MAX_RESPONSE_SIZE",
      "label": "Gnmi Max Response Size",
      "help": "gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "1048576",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/gnmi_client.py#L125",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNMI_MAX_SUBSCRIPTIONS",
      "label": "Gnmi Max Subscriptions",
      "help": "gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "50",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/gnmi_mcp_server.py#L103",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNMI_TARGETS",
      "label": "Gnmi Targets",
      "help": "gNMI Streaming Telemetry MCP Server (10 tools: Get, Set, Subscribe, Capabilities, Browse, Compare) The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/gnmi_client.py#L56",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNMI_TLS_CA_CERT",
      "label": "Gnmi Tls Ca Cert",
      "help": "gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/gnmi_client.py#L72",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNMI_TLS_CLIENT_CERT",
      "label": "Gnmi Tls Client Cert",
      "help": "gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/gnmi_client.py#L73",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNMI_TLS_CLIENT_KEY",
      "label": "Gnmi Tls Client Key",
      "help": "gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/gnmi_client.py#L74",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNMI_TLS_SKIP_VERIFY",
      "label": "Gnmi Tls Skip Verify",
      "help": "gNMI streaming telemetry for multi-vendor devices. GNMI_TARGETS is a JSON array of target devices. TLS is mandatory.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/gnmi_client.py#L75",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_LAB_MODE",
      "label": "Netclaw Lab Mode",
      "help": "NETCLAW_LAB_MODE is consumed by the selected gNMI Telemetry registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [
        "claroty",
        "n2n",
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/itsm_gate.py#L57",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_INSTANCE_URL",
      "label": "Servicenow Instance Url",
      "help": "SERVICENOW_INSTANCE_URL is consumed by the selected gNMI Telemetry registration. Leave unset only when using the documented native/default configuration. The consumer has an explicit fallback; Configure later preserves that fallback. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/itsm_gate.py#L117",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_PASSWORD",
      "label": "Servicenow Password",
      "help": "SERVICENOW_PASSWORD is consumed by the selected gNMI Telemetry registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/itsm_gate.py#L119",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_USERNAME",
      "label": "Servicenow Username",
      "help": "SERVICENOW_USERNAME is consumed by the selected gNMI Telemetry registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gnmi-mcp/itsm_gate.py#L118",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gnmi-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "radkit": [
    {
      "key": "RADKIT_DEFAULT_SERVICE_SERIAL",
      "label": "Radkit Default Service Serial",
      "help": "Cisco RADKit identity and service serial.",
      "classification": "public",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#radkit-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RADKIT_IDENTITY",
      "label": "Radkit Identity",
      "help": "Cisco RADKit (cloud-relayed remote device access)",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#radkit-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "multivendor-cli": [
    {
      "key": "MULTIVENDOR_INVENTORY_PATH",
      "label": "Multivendor Inventory Path",
      "help": "Operator-authored inventory. The server NEVER writes to this file.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/inventory/sources.py#L224",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MULTIVENDOR_INVENTORY_SOURCE",
      "label": "Multivendor Inventory Source",
      "help": "--------------------------------------------------------------------------- Multivendor CLI Driver (spec 076) — ~90 platform families via Nornir/NAPALM/Netmiko Read-only by default. Cisco/Juniper stay with pyATS/junos-mcp. --------------------------------------------------------------------------- Inventory source: live_sot | generated | operator | auto (default auto)",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/inventory/sources.py#L220",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MULTIVENDOR_KNOWN_HOSTS",
      "label": "Multivendor Known Hosts",
      "help": "MULTIVENDOR_KNOWN_HOSTS is consumed by the selected Multivendor CLI Driver registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "/absolute/path/to/verified_known_hosts",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/ssh_security.py#L12",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MULTIVENDOR_MAX_WORKERS",
      "label": "Multivendor Max Workers",
      "help": "Concurrency bound for fleet queries (default 10 — devices often cap sessions at 5-15)",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/tools/fleet.py#L33",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MULTIVENDOR_PASSWORD",
      "label": "Multivendor Password",
      "help": "Read-only by default; write tools absent from tools/list unless MULTIVENDOR_WRITE_ENABLED. Runs from its OWN virtualenv because napalm/netmiko resolve cryptography 49.x while the system carries 46.x, which NCFED uses for X.509 issuance. Writes are single-pathed per platform: refuses config change on Cisco/Junos and names the owning server.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MULTIVENDOR_SSH_STRICT",
      "label": "Multivendor Ssh Strict",
      "help": "Multivendor device identity (verified host keys; Junos uses ~/.ssh/known_hosts)",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/ssh_security.py#L7",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MULTIVENDOR_TIMEOUT_S",
      "label": "Multivendor Timeout S",
      "help": "Per-device timeout in seconds (default 30)",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/tools/change.py#L46",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MULTIVENDOR_USERNAME",
      "label": "Multivendor Username",
      "help": "Credentials. NEVER put these in an inventory file. Vault preferred; these are the documented fallback and are fully supported (Vault is not required).",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MULTIVENDOR_WRITE_ENABLED",
      "label": "Multivendor Write Enabled",
      "help": "Expose write tools at all. Absent from tools/list unless set (default off).",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/server.py#L88",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_INSTANCE_URL",
      "label": "Servicenow Instance Url",
      "help": "SERVICENOW_INSTANCE_URL is consumed by the selected Multivendor CLI Driver registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "gnmi",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/tools/change.py#L150",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_PASSWORD",
      "label": "Servicenow Password",
      "help": "SERVICENOW_PASSWORD is consumed by the selected Multivendor CLI Driver registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "gnmi",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/tools/change.py#L152",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_USERNAME",
      "label": "Servicenow Username",
      "help": "SERVICENOW_USERNAME is consumed by the selected Multivendor CLI Driver registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "gnmi",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/multivendor-cli-mcp/tools/change.py#L151",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#multivendor-cli-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "percepxion": [
    {
      "key": "PERCEPXION_PASSWORD",
      "label": "Percepxion Password",
      "help": "PERCEPXION_PASSWORD is consumed by the selected Lantronix Percepxion registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PERCEPXION_USERNAME",
      "label": "Percepxion Username",
      "help": "both are Lantronix's own actively co-developed repos. See specs/104-percepxion-oob-integration/spec.md and workspace/skills/ percepxion-oob/SKILL.md for the full env var reference and install steps. ───────────────────────────────────────────────────────────────────── percepxion-mcp-server: fleet-wide OOB console-server SaaS",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PERCEPXION_API_URL",
      "label": "Percepxion Api Url",
      "help": "Percepxion API base URL; default https://api.percepxion.ai/api.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "PERCEPXION_CREDENTIAL_PROVIDER",
      "label": "Percepxion Credential Provider",
      "help": "Credential backend. New setup supports explicit env credentials; other providers require separately reviewed native setup and verification.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "PERCEPXION_REQUEST_TIMEOUT",
      "label": "Percepxion Request Timeout",
      "help": "HTTP request timeout in seconds; upstream default 45.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "PERCEPXION_DEFAULT_ORGANIZATION_ID",
      "label": "Percepxion Default Organization Id",
      "help": "Organization used when callers omit organization_id.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    }
  ],
  "slc": [
    {
      "key": "SLC_DEFAULT_IP",
      "label": "Slc Default Ip",
      "help": "Default SLC device address. Per-device identity is selected in the operational request.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "SLC_USERNAME",
      "label": "Slc Username",
      "help": "Default SLC login name; upstream default is sysadmin.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "SLC_PASSWORD",
      "label": "Slc Password",
      "help": "Default SLC password, entered only in the native secret form.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "SLC_TOTP_SECRET",
      "label": "Slc Totp Secret",
      "help": "Optional TOTP seed for 2FA-enabled devices.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "SLC_VERIFY_SSL",
      "label": "Slc Verify Ssl",
      "help": "Verify the SLC TLS certificate; enabled by default.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/percepxion-oob/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    }
  ],
  "netbox": [
    {
      "key": "NETBOX_MCP_SCRIPT",
      "label": "Netbox Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. NetBox instance URL and API token. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#netbox-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETBOX_TOKEN",
      "label": "Netbox Token",
      "help": "NetBox instance URL and API token.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#netbox-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETBOX_URL",
      "label": "Netbox Url",
      "help": "NetBox (DCIM/IPAM source of truth)",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://netbox.example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#netbox-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PYATS_TESTBED_PATH",
      "label": "Pyats Testbed Path",
      "help": "Generated for this selected installation by the scoped adapter. pyATS paths (set automatically by install.sh) Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "./testbed/testbed.yaml",
      "sharedWith": [
        "pyats"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#netbox-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "nautobot": [
    {
      "key": "ITSM_ENABLED",
      "label": "Itsm Enabled",
      "help": "ITSM_ENABLED is consumed by the selected Nautobot registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [
        "aruba-cx",
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/server.py#L58",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITSM_LAB_MODE",
      "label": "Itsm Lab Mode",
      "help": "ITSM_LAB_MODE is consumed by the selected Nautobot registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [
        "aruba-cx",
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/server.py#L59",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_CA_BUNDLE",
      "label": "Nautobot Ca Bundle",
      "help": "NAUTOBOT_CA_BUNDLE is consumed by the selected Nautobot registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/nautobot_client.py#L24",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_TIMEOUT",
      "label": "Nautobot Timeout",
      "help": "NAUTOBOT_TIMEOUT is consumed by the selected Nautobot registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/nautobot_client.py#L26",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_TOKEN",
      "label": "Nautobot Token",
      "help": "Nautobot instance URL and API token.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nautobot-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_URL",
      "label": "Nautobot Url",
      "help": "Nautobot (alternative to NetBox for IPAM/DCIM source of truth)",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://nautobot.example.com",
      "sharedWith": [
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nautobot-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_VERIFY_SSL",
      "label": "Nautobot Verify Ssl",
      "help": "Nautobot API certificate verification (spec 124)",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [
        "nautobot-golden-config",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/nautobot_client.py#L23",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "nautobot-golden-config": [
    {
      "key": "GOLDEN_CONFIG_JOB_TIMEOUT",
      "label": "Golden Config Job Timeout",
      "help": "GOLDEN_CONFIG_JOB_TIMEOUT is consumed by the selected Nautobot Golden Config registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/job_runner.py#L15",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GOLDEN_CONFIG_POLL_INTERVAL",
      "label": "Golden Config Poll Interval",
      "help": "GOLDEN_CONFIG_POLL_INTERVAL is consumed by the selected Nautobot Golden Config registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/job_runner.py#L14",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITSM_ENABLED",
      "label": "Itsm Enabled",
      "help": "ITSM_ENABLED is consumed by the selected Nautobot Golden Config registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [
        "aruba-cx",
        "nautobot",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/server.py#L58",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITSM_LAB_MODE",
      "label": "Itsm Lab Mode",
      "help": "ITSM_LAB_MODE is consumed by the selected Nautobot Golden Config registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [
        "aruba-cx",
        "nautobot",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/server.py#L59",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_CA_BUNDLE",
      "label": "Nautobot Ca Bundle",
      "help": "NAUTOBOT_CA_BUNDLE is consumed by the selected Nautobot Golden Config registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/nautobot_client.py#L24",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_TIMEOUT",
      "label": "Nautobot Timeout",
      "help": "NAUTOBOT_TIMEOUT is consumed by the selected Nautobot Golden Config registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/nautobot_client.py#L26",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_TOKEN",
      "label": "Nautobot Token",
      "help": "NAUTOBOT_TOKEN is consumed by the selected Nautobot Golden Config registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_URL",
      "label": "Nautobot Url",
      "help": "Nautobot (alternative to NetBox for IPAM/DCIM source of truth)",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://nautobot.example.com",
      "sharedWith": [
        "nautobot",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_VERIFY_SSL",
      "label": "Nautobot Verify Ssl",
      "help": "Nautobot API certificate verification (spec 124)",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [
        "nautobot",
        "nautobot-routing"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-golden-config-mcp/nautobot_client.py#L23",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-golden-config-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "nautobot-routing": [
    {
      "key": "ITSM_ENABLED",
      "label": "Itsm Enabled",
      "help": "ITSM_ENABLED is consumed by the selected Nautobot Routing registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [
        "aruba-cx",
        "nautobot",
        "nautobot-golden-config"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-routing-mcp/server.py#L55",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-routing-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITSM_LAB_MODE",
      "label": "Itsm Lab Mode",
      "help": "ITSM_LAB_MODE is consumed by the selected Nautobot Routing registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [
        "aruba-cx",
        "nautobot",
        "nautobot-golden-config"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-routing-mcp/server.py#L56",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-routing-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_CA_BUNDLE",
      "label": "Nautobot Ca Bundle",
      "help": "NAUTOBOT_CA_BUNDLE is consumed by the selected Nautobot Routing registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot",
        "nautobot-golden-config"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-routing-mcp/nautobot_client.py#L24",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-routing-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_TIMEOUT",
      "label": "Nautobot Timeout",
      "help": "NAUTOBOT_TIMEOUT is consumed by the selected Nautobot Routing registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot",
        "nautobot-golden-config"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-routing-mcp/nautobot_client.py#L26",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-routing-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_TOKEN",
      "label": "Nautobot Token",
      "help": "NAUTOBOT_TOKEN is consumed by the selected Nautobot Routing registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [
        "nautobot",
        "nautobot-golden-config"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nautobot-routing-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_URL",
      "label": "Nautobot Url",
      "help": "Nautobot (alternative to NetBox for IPAM/DCIM source of truth)",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://nautobot.example.com",
      "sharedWith": [
        "nautobot",
        "nautobot-golden-config"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nautobot-routing-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NAUTOBOT_VERIFY_SSL",
      "label": "Nautobot Verify Ssl",
      "help": "Nautobot API certificate verification (spec 124)",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [
        "nautobot",
        "nautobot-golden-config"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nautobot-routing-mcp/nautobot_client.py#L23",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nautobot-routing-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "infrahub": [
    {
      "key": "INFRAHUB_ADDRESS",
      "label": "Infrahub Address",
      "help": "OpsMill Infrahub (schema-driven infrastructure source of truth)",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "http://infrahub.example.com:8000",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#infrahub-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "INFRAHUB_API_TOKEN",
      "label": "Infrahub Api Token",
      "help": "Infrahub GraphQL endpoint and API token.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#infrahub-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "infoblox": [
    {
      "key": "INFOBLOX_API_KEY",
      "label": "Infoblox Api Key",
      "help": "INFOBLOX_API_KEY is consumed by the selected Infoblox DDI registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "INFOBLOX_MCP_CMD",
      "label": "Infoblox Mcp Cmd",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "INFOBLOX_PASSWORD",
      "label": "Infoblox Password",
      "help": "Infoblox WAPI endpoint.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "INFOBLOX_URL",
      "label": "Infoblox Url",
      "help": "Infoblox WAPI endpoint.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "INFOBLOX_USERNAME",
      "label": "Infoblox Username",
      "help": "Infoblox WAPI endpoint.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "aci": [
    {
      "key": "ACI_MCP_SCRIPT",
      "label": "Aci Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. APIC controller endpoint and admin credentials. Per-MCP .env at mcp-servers/ACI_MCP/aci_mcp/.env is also loaded. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "APIC_URL",
      "label": "Apic Url",
      "help": "APIC controller endpoint and admin credentials. Per-MCP .env at mcp-servers/ACI_MCP/aci_mcp/.env is also loaded.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PASSWORD",
      "label": "Password",
      "help": "APIC controller endpoint and admin credentials. Per-MCP .env at mcp-servers/ACI_MCP/aci_mcp/.env is also loaded.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_MCP_SCRIPT",
      "label": "Servicenow Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "ise",
        "servicenow"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "USERNAME",
      "label": "Username",
      "help": "APIC controller endpoint and admin credentials. Per-MCP .env at mcp-servers/ACI_MCP/aci_mcp/.env is also loaded.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "nso": [
    {
      "key": "NSO_ADDRESS",
      "label": "Nso Address",
      "help": "NSO RESTCONF endpoint credentials.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "sandbox-nso-1.cisco.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nso-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NSO_PASSWORD",
      "label": "Nso Password",
      "help": "NSO RESTCONF endpoint credentials.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nso-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NSO_PORT",
      "label": "Nso Port",
      "help": "NSO RESTCONF endpoint credentials.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "443",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nso-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NSO_SCHEME",
      "label": "Nso Scheme",
      "help": "Cisco NSO MCP (Network Services Orchestrator)",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "https",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nso-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NSO_TIMEOUT",
      "label": "Nso Timeout",
      "help": "NSO_TIMEOUT is consumed by the selected Cisco NSO registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "10",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nso-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NSO_USERNAME",
      "label": "Nso Username",
      "help": "NSO RESTCONF endpoint credentials.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nso-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "itential": [
    {
      "key": "ITENTIAL_MCP_PLATFORM_CLIENT_ID",
      "label": "Itential Mcp Platform Client Id",
      "help": "Itential Automation Platform OAuth 2.0 credentials.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#itential-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITENTIAL_MCP_PLATFORM_CLIENT_SECRET",
      "label": "Itential Mcp Platform Client Secret",
      "help": "Itential Automation Platform OAuth 2.0 credentials.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#itential-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITENTIAL_MCP_PLATFORM_HOST",
      "label": "Itential Mcp Platform Host",
      "help": "Itential Automation Platform (65+ tools: config mgmt, compliance, workflows, golden config)",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "itential.example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#itential-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITENTIAL_MCP_PLATFORM_PASSWORD",
      "label": "Itential Mcp Platform Password",
      "help": "ITENTIAL_MCP_PLATFORM_PASSWORD is consumed by the selected Itential IAP registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#itential-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITENTIAL_MCP_PLATFORM_PORT",
      "label": "Itential Mcp Platform Port",
      "help": "ITENTIAL_MCP_PLATFORM_PORT is consumed by the selected Itential IAP registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "443",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#itential-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ITENTIAL_MCP_PLATFORM_USER",
      "label": "Itential Mcp Platform User",
      "help": "ITENTIAL_MCP_PLATFORM_USER is consumed by the selected Itential IAP registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#itential-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "meraki": [
    {
      "key": "CACHE_TTL_SECONDS",
      "label": "Cache Ttl Seconds",
      "help": "Meraki Dashboard API key and org ID.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#meraki-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ENABLE_CACHING",
      "label": "Enable Caching",
      "help": "Meraki Dashboard API key and org ID.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#meraki-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MERAKI_API_KEY",
      "label": "Meraki Api Key",
      "help": "Meraki Dashboard API key and org ID.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#meraki-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MERAKI_DASHBOARD_API_KEY",
      "label": "Meraki Dashboard Api Key",
      "help": "Cisco Meraki — official remote MCP (494 read-only Dashboard capabilities, 2 tools) Use a READ-ONLY dashboard key: Dashboard > My Profile > API access. Org and network IDs are discovered at runtime (getOrganizations), not configured here. Writes are structurally absent upstream, so there is no read-only toggle to set.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#meraki-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MERAKI_ORG_ID",
      "label": "Meraki Org Id",
      "help": "Meraki Dashboard API key and org ID.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#meraki-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "READ_ONLY_MODE",
      "label": "Read Only Mode",
      "help": "Meraki Dashboard API key and org ID.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#meraki-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "nsm": [
    {
      "key": "NSM_HOME",
      "label": "Nsm Home",
      "help": "NSM_HOME is consumed by the selected Zeek + Suricata NSM registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nsm-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NSM_TIMEOUT",
      "label": "Nsm Timeout",
      "help": "NSM_TIMEOUT is consumed by the selected Zeek + Suricata NSM registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/nsm-mcp/runner.py#L36",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#nsm-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "analysis": [
    {
      "key": "ANALYSIS_EXTRA_ROOTS",
      "label": "Analysis Extra Roots",
      "help": "ANALYSIS_EXTRA_ROOTS is consumed by the selected DuckDB Analysis registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/analysis-mcp/loader.py#L57",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#analysis-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ANALYSIS_MAX_RESULT_ROWS",
      "label": "Analysis Max Result Rows",
      "help": "ANALYSIS_MAX_RESULT_ROWS is consumed by the selected DuckDB Analysis registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/analysis-mcp/server.py#L54",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#analysis-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ANALYSIS_QUERY_TIMEOUT",
      "label": "Analysis Query Timeout",
      "help": "ANALYSIS_QUERY_TIMEOUT is consumed by the selected DuckDB Analysis registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/analysis-mcp/server.py#L53",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#analysis-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "redfish": [
    {
      "key": "REDFISH_PASSWORD",
      "label": "Redfish Password",
      "help": "REDFISH_PASSWORD is consumed by the selected Redfish BMC registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/redfish-mcp/client.py#L62",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#redfish-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "REDFISH_TIMEOUT",
      "label": "Redfish Timeout",
      "help": "REDFISH_TIMEOUT is consumed by the selected Redfish BMC registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/redfish-mcp/client.py#L41",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#redfish-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "REDFISH_URL",
      "label": "Redfish Url",
      "help": "REDFISH_URL is consumed by the selected Redfish BMC registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/redfish-mcp/client.py#L55",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#redfish-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "REDFISH_USERNAME",
      "label": "Redfish Username",
      "help": "REDFISH_USERNAME is consumed by the selected Redfish BMC registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/redfish-mcp/client.py#L61",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#redfish-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "REDFISH_VERIFY_TLS",
      "label": "Redfish Verify Tls",
      "help": "Redfish BMC transport (spec 124): trust private PKI explicitly.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/redfish-mcp/client.py#L40",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#redfish-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "anta": [
    {
      "key": "ANTA_CA_BUNDLE",
      "label": "Anta Ca Bundle",
      "help": "ANTA_CA_BUNDLE is consumed by the selected Arista ANTA Validation registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/anta-mcp/server.py#L193",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#anta-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ANTA_ENABLE_PASSWORD",
      "label": "Anta Enable Password",
      "help": "NetClaw-authored thin server over ANTA 1.9.0 (Apache-2.0, Arista Networks) run from its OWN VIRTUALENV -- not a preference: a system install moves cryptography 46.0.5 -> 50.0.0 and four installed distributions depend on it with no upper bound (Authlib, pygnmi, service-identity, sshsig), including NetClaw federation TLS (spec 060). Measured by pip dry-run BEFORE installing, per spec 076. THE ASSERTION LAYER: everything else reads state, this asserts on it. 208 tests / 33 modules behind 4 tools = 1,272/5,000 tokens; one tool per test would be ~58,000 (11.6x), the Catalyst Center failure. Discovery tools contact NO device. SILENT WRONG ANSWER, reproduced live on clab-mandible-veos1: ANTA reports a test for an unconfigured feature as FAILURE -- VerifyBGPPeerCount returns \"BGP inactive\" as a failure on a switch with no BGP -- so the server reclassifies to not_applicable with a deliberately NARROW rule that never hides a real failure, preserving the original message. Five verdicts counted separately and a health percentage is REFUSED (passed/total is meaningless with not_applicable in the denominator). Unreachable device => error with zero results, never test failures. Read-only: ANTA tests, it never configures. No per-call GAIT audit.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/anta-mcp/server.py#L82",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#anta-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ANTA_PASSWORD",
      "label": "Anta Password",
      "help": "NetClaw-authored thin server over ANTA 1.9.0 (Apache-2.0, Arista Networks) run from its OWN VIRTUALENV -- not a preference: a system install moves cryptography 46.0.5 -> 50.0.0 and four installed distributions depend on it with no upper bound (Authlib, pygnmi, service-identity, sshsig), including NetClaw federation TLS (spec 060). Measured by pip dry-run BEFORE installing, per spec 076. THE ASSERTION LAYER: everything else reads state, this asserts on it. 208 tests / 33 modules behind 4 tools = 1,272/5,000 tokens; one tool per test would be ~58,000 (11.6x), the Catalyst Center failure. Discovery tools contact NO device. SILENT WRONG ANSWER, reproduced live on clab-mandible-veos1: ANTA reports a test for an unconfigured feature as FAILURE -- VerifyBGPPeerCount returns \"BGP inactive\" as a failure on a switch with no BGP -- so the server reclassifies to not_applicable with a deliberately NARROW rule that never hides a real failure, preserving the original message. Five verdicts counted separately and a health percentage is REFUSED (passed/total is meaningless with not_applicable in the denominator). Unreachable device => error with zero results, never test failures. Read-only: ANTA tests, it never configures. No per-call GAIT audit.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/anta-mcp/server.py#L81",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#anta-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ANTA_TIMEOUT",
      "label": "Anta Timeout",
      "help": "NetClaw-authored thin server over ANTA 1.9.0 (Apache-2.0, Arista Networks) run from its OWN VIRTUALENV -- not a preference: a system install moves cryptography 46.0.5 -> 50.0.0 and four installed distributions depend on it with no upper bound (Authlib, pygnmi, service-identity, sshsig), including NetClaw federation TLS (spec 060). Measured by pip dry-run BEFORE installing, per spec 076. THE ASSERTION LAYER: everything else reads state, this asserts on it. 208 tests / 33 modules behind 4 tools = 1,272/5,000 tokens; one tool per test would be ~58,000 (11.6x), the Catalyst Center failure. Discovery tools contact NO device. SILENT WRONG ANSWER, reproduced live on clab-mandible-veos1: ANTA reports a test for an unconfigured feature as FAILURE -- VerifyBGPPeerCount returns \"BGP inactive\" as a failure on a switch with no BGP -- so the server reclassifies to not_applicable with a deliberately NARROW rule that never hides a real failure, preserving the original message. Five verdicts counted separately and a health percentage is REFUSED (passed/total is meaningless with not_applicable in the denominator). Unreachable device => error with zero results, never test failures. Read-only: ANTA tests, it never configures. No per-call GAIT audit.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "30",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/anta-mcp/server.py#L203",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#anta-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ANTA_USERNAME",
      "label": "Anta Username",
      "help": "Arista ANTA validation (spec 098 / R25 — 4 tools, 208 tests, read-only, own venv) Verdicts are pass/fail/not_applicable/skipped/error. A test for a feature the device does not run reports not_applicable, NEVER a failure. No health percentage is ever emitted.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/anta-mcp/server.py#L80",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#anta-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ANTA_VERIFY_TLS",
      "label": "Anta Verify Tls",
      "help": "NetClaw-authored thin server over ANTA 1.9.0 (Apache-2.0, Arista Networks) run from its OWN VIRTUALENV -- not a preference: a system install moves cryptography 46.0.5 -> 50.0.0 and four installed distributions depend on it with no upper bound (Authlib, pygnmi, service-identity, sshsig), including NetClaw federation TLS (spec 060). Measured by pip dry-run BEFORE installing, per spec 076. THE ASSERTION LAYER: everything else reads state, this asserts on it. 208 tests / 33 modules behind 4 tools = 1,272/5,000 tokens; one tool per test would be ~58,000 (11.6x), the Catalyst Center failure. Discovery tools contact NO device. SILENT WRONG ANSWER, reproduced live on clab-mandible-veos1: ANTA reports a test for an unconfigured feature as FAILURE -- VerifyBGPPeerCount returns \"BGP inactive\" as a failure on a switch with no BGP -- so the server reclassifies to not_applicable with a deliberately NARROW rule that never hides a real failure, preserving the original message. Five verdicts counted separately and a health percentage is REFUSED (passed/total is meaningless with not_applicable in the denominator). Unreachable device => error with zero results, never test failures. Read-only: ANTA tests, it never configures. No per-call GAIT audit.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/anta-mcp/server.py#L163",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#anta-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "elastic": [
    {
      "key": "ES_API_KEY",
      "label": "Es Api Key",
      "help": "Adopted third-party (docker.elastic.co/mcp/elasticsearch, Apache-2.0, image 0.4.6 on rmcp 0.2.1), run as a digest-pinned container — NetClaw authors no server code and installs no cluster. Strictly read-only: 5 tools, 1,094/5,000 tokens, and the manifest contains no index/update/delete/reindex verb, so writes are unreachable regardless of credential. UPSTREAM IS DEPRECATED and adopted deliberately: the successor (Agent Builder MCP endpoint) is ENTERPRISE-tier on self-managed, so the supported path is paywalled while this one is Apache-2.0 and already published. Pinned by digest so a security-only update cannot change answers. SILENT WRONG ANSWER, reproduced live: Elasticsearch caps hits.total at 10,000 and marks it relation:\"gte\"; this server renders only the integer, so a capped floor reads as exact — 10,075 real documents reported as 10,000, and the error is unbounded (a million-doc index still says 10,000). Enforced by the SKILL, not by code: count via esql or search+track_total_hits, both verified to return 10,075. ES_URL resolves INSIDE the container — a host cluster is host.docker.internal, never localhost. No per-call GAIT audit.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#elasticsearch-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ES_PASSWORD",
      "label": "Es Password",
      "help": "Adopted third-party (docker.elastic.co/mcp/elasticsearch, Apache-2.0, image 0.4.6 on rmcp 0.2.1), run as a digest-pinned container — NetClaw authors no server code and installs no cluster. Strictly read-only: 5 tools, 1,094/5,000 tokens, and the manifest contains no index/update/delete/reindex verb, so writes are unreachable regardless of credential. UPSTREAM IS DEPRECATED and adopted deliberately: the successor (Agent Builder MCP endpoint) is ENTERPRISE-tier on self-managed, so the supported path is paywalled while this one is Apache-2.0 and already published. Pinned by digest so a security-only update cannot change answers. SILENT WRONG ANSWER, reproduced live: Elasticsearch caps hits.total at 10,000 and marks it relation:\"gte\"; this server renders only the integer, so a capped floor reads as exact — 10,075 real documents reported as 10,000, and the error is unbounded (a million-doc index still says 10,000). Enforced by the SKILL, not by code: count via esql or search+track_total_hits, both verified to return 10,075. ES_URL resolves INSIDE the container — a host cluster is host.docker.internal, never localhost. No per-call GAIT audit.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "ES_USERNAME"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#elasticsearch-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ES_SSL_SKIP_VERIFY",
      "label": "Es Ssl Skip Verify",
      "help": "Adopted third-party (docker.elastic.co/mcp/elasticsearch, Apache-2.0, image 0.4.6 on rmcp 0.2.1), run as a digest-pinned container — NetClaw authors no server code and installs no cluster. Strictly read-only: 5 tools, 1,094/5,000 tokens, and the manifest contains no index/update/delete/reindex verb, so writes are unreachable regardless of credential. UPSTREAM IS DEPRECATED and adopted deliberately: the successor (Agent Builder MCP endpoint) is ENTERPRISE-tier on self-managed, so the supported path is paywalled while this one is Apache-2.0 and already published. Pinned by digest so a security-only update cannot change answers. SILENT WRONG ANSWER, reproduced live: Elasticsearch caps hits.total at 10,000 and marks it relation:\"gte\"; this server renders only the integer, so a capped floor reads as exact — 10,075 real documents reported as 10,000, and the error is unbounded (a million-doc index still says 10,000). Enforced by the SKILL, not by code: count via esql or search+track_total_hits, both verified to return 10,075. ES_URL resolves INSIDE the container — a host cluster is host.docker.internal, never localhost. No per-call GAIT audit.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#elasticsearch-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ES_URL",
      "label": "Es Url",
      "help": "Elasticsearch Logs (adopted Elastic MCP, 5 tools, read-only — spec 096) ES_URL is resolved INSIDE the container: a cluster on this host is host.docker.internal, NOT localhost. Counting via ESQL or track_total_hits — a bare search total caps at 10,000.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "http://host.docker.internal:9200",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#elasticsearch-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ES_USERNAME",
      "label": "Es Username",
      "help": "Adopted third-party (docker.elastic.co/mcp/elasticsearch, Apache-2.0, image 0.4.6 on rmcp 0.2.1), run as a digest-pinned container — NetClaw authors no server code and installs no cluster. Strictly read-only: 5 tools, 1,094/5,000 tokens, and the manifest contains no index/update/delete/reindex verb, so writes are unreachable regardless of credential. UPSTREAM IS DEPRECATED and adopted deliberately: the successor (Agent Builder MCP endpoint) is ENTERPRISE-tier on self-managed, so the supported path is paywalled while this one is Apache-2.0 and already published. Pinned by digest so a security-only update cannot change answers. SILENT WRONG ANSWER, reproduced live: Elasticsearch caps hits.total at 10,000 and marks it relation:\"gte\"; this server renders only the integer, so a capped floor reads as exact — 10,075 real documents reported as 10,000, and the error is unbounded (a million-doc index still says 10,000). Enforced by the SKILL, not by code: count via esql or search+track_total_hits, both verified to return 10,075. ES_URL resolves INSIDE the container — a host cluster is host.docker.internal, never localhost. No per-call GAIT audit.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "elastic",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#elasticsearch-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "sdwan": [
    {
      "key": "SDWAN_MCP_SCRIPT",
      "label": "Sdwan Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. vManage controller credentials (read-only). Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "VMANAGE_IP",
      "label": "Vmanage Ip",
      "help": "Cisco SD-WAN (vManage read-only monitoring — 12 tools)",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "10.10.10.1",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "VMANAGE_PASSWORD",
      "label": "Vmanage Password",
      "help": "vManage controller credentials (read-only).",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "VMANAGE_USERNAME",
      "label": "Vmanage Username",
      "help": "vManage controller credentials (read-only).",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "prisma-sdwan": [
    {
      "key": "PAN_CLIENT_ID",
      "label": "Pan Client Id",
      "help": "Palo Alto Networks Prisma SD-WAN (15+ tools: sites, elements, topology, status, alarms, config) Read-only visibility into Prisma SD-WAN fabric — no ServiceNow CR gating required Service account from Prisma Access/SASE portal with SD-WAN API permissions",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "name@tsg.iam.panserviceaccount.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prisma-sdwan-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PAN_CLIENT_SECRET",
      "label": "Pan Client Secret",
      "help": "Palo Alto Networks Prisma SD-WAN via OAuth2. Region is americas or europe. TSG_ID is the Tenant Service Group ID.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prisma-sdwan-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PAN_REGION",
      "label": "Pan Region",
      "help": "Palo Alto Networks Prisma SD-WAN via OAuth2. Region is americas or europe. TSG_ID is the Tenant Service Group ID.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "americas",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prisma-sdwan-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PAN_TSG_ID",
      "label": "Pan Tsg Id",
      "help": "Palo Alto Networks Prisma SD-WAN via OAuth2. Region is americas or europe. TSG_ID is the Tenant Service Group ID.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "your-tenant-service-group-id",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prisma-sdwan-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "aap": [
    {
      "key": "AAP_TOKEN",
      "label": "Aap Token",
      "help": "Red Hat Ansible Automation Platform API endpoint and tokens. EDA token can match AAP token.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "AAP_URL"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aap-ansible-mcp,aap-eda-mcp,aap-lint-mcp,aap-docs-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AAP_URL",
      "label": "Aap Url",
      "help": "Red Hat Ansible Automation Platform API endpoint and tokens. EDA token can match AAP token.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aap-ansible-mcp,aap-eda-mcp,aap-lint-mcp,aap-docs-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "EDA_TOKEN",
      "label": "Eda Token",
      "help": "Red Hat Ansible Automation Platform API endpoint and tokens. EDA token can match AAP token.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "EDA_URL"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aap-ansible-mcp,aap-eda-mcp,aap-lint-mcp,aap-docs-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "EDA_URL",
      "label": "Eda Url",
      "help": "Red Hat Ansible Automation Platform API endpoint and tokens. EDA token can match AAP token.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aap-ansible-mcp,aap-eda-mcp,aap-lint-mcp,aap-docs-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "REDHAT_PASSWORD",
      "label": "Redhat Password",
      "help": "REDHAT_PASSWORD is consumed by the selected Ansible Automation Platform registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aap-ansible-mcp,aap-eda-mcp,aap-lint-mcp,aap-docs-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "REDHAT_USERNAME",
      "label": "Redhat Username",
      "help": "REDHAT_USERNAME is consumed by the selected Ansible Automation Platform registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aap-ansible-mcp,aap-eda-mcp,aap-lint-mcp,aap-docs-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "ise": [
    {
      "key": "ISE_BASE",
      "label": "Ise Base",
      "help": "ISE admin node REST API access.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ISE_MCP_SCRIPT",
      "label": "Ise Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. ISE admin node REST API access. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ISE_PASSWORD",
      "label": "Ise Password",
      "help": "ISE admin node REST API access.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ISE_USERNAME",
      "label": "Ise Username",
      "help": "ISE admin node REST API access.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_MCP_SCRIPT",
      "label": "Servicenow Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "aci",
        "servicenow"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "fmc": [
    {
      "key": "FMC_BASE_URL",
      "label": "Fmc Base Url",
      "help": "Cisco FMC (Secure Firewall Management Center)",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://fmc.example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cisco-fmc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FMC_PASSWORD",
      "label": "Fmc Password",
      "help": "Cisco Secure Firewall Management Center API.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cisco-fmc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FMC_PROFILES_DIR",
      "label": "Fmc Profiles Dir",
      "help": "Cisco Secure Firewall Management Center API.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "./profiles",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cisco-fmc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FMC_PROFILE_DEFAULT",
      "label": "Fmc Profile Default",
      "help": "Cisco Secure Firewall Management Center API.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "dc-east",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cisco-fmc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FMC_USERNAME",
      "label": "Fmc Username",
      "help": "Cisco Secure Firewall Management Center API.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "api-user",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cisco-fmc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FMC_VERIFY_SSL",
      "label": "Fmc Verify Ssl",
      "help": "Cisco Secure Firewall Management Center API.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cisco-fmc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "panorama": [
    {
      "key": "PANORAMA_API_KEY",
      "label": "Panorama Api Key",
      "help": "Panorama endpoint and API key.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PANORAMA_URL",
      "label": "Panorama Url",
      "help": "Panorama endpoint and API key.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PANOS_API_KEY",
      "label": "Panos Api Key",
      "help": "PANOS_API_KEY is consumed by the selected Palo Alto Panorama registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PANOS_HOSTNAME",
      "label": "Panos Hostname",
      "help": "PANOS_HOSTNAME is consumed by the selected Palo Alto Panorama registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PANOS_MCP_CMD",
      "label": "Panos Mcp Cmd",
      "help": "Generated for this selected installation by the scoped adapter. Panorama endpoint and API key. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "fortinet": [
    {
      "key": "FORTIANALYZER_API_TOKEN",
      "label": "Fortianalyzer Api Token",
      "help": "Three planes, token auth per plane. Every response carries plane + scope and is GAIT-audited. Read-only unless FORTINET_ALLOW_WRITES=true, and writes still require human approval AND an approved ServiceNow change record.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "FORTIANALYZER_HOST"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FORTIANALYZER_HOST",
      "label": "Fortianalyzer Host",
      "help": "Analyzer plane — FortiAnalyzer (observed traffic: logs, policy activity) Token auth requires FortiAnalyzer 7.2.2 or later",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FORTIGATE_API_TOKEN",
      "label": "Fortigate Api Token",
      "help": "Three planes, token auth per plane. Every response carries plane + scope and is GAIT-audited. Read-only unless FORTINET_ALLOW_WRITES=true, and writes still require human approval AND an approved ServiceNow change record.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "FORTIGATE_HOST"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FORTIGATE_HOST",
      "label": "Fortigate Host",
      "help": "Device plane — FortiGate (observed state: interfaces, routes, VPN, HA)",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FORTIMANAGER_API_TOKEN",
      "label": "Fortimanager Api Token",
      "help": "Three planes, token auth per plane. Every response carries plane + scope and is GAIT-audited. Read-only unless FORTINET_ALLOW_WRITES=true, and writes still require human approval AND an approved ServiceNow change record.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "FORTIMANAGER_HOST"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FORTIMANAGER_HOST",
      "label": "Fortimanager Host",
      "help": "Manager plane — FortiManager (policy intent: ADOMs, packages, objects)",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FORTINET_ALLOW_WRITES",
      "label": "Fortinet Allow Writes",
      "help": "Write path. Defaults to false. Enabling it does NOT authorise a write — it only makes the two gates reachable. Every write additionally requires human approval AND an approved ServiceNow change record.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FORTINET_MCP_CMD",
      "label": "Fortinet Mcp Cmd",
      "help": "Generated for this selected installation by the scoped adapter. Three planes, each independently optional. A plane with no credentials is simply not consulted, and NetClaw says so rather than answering from another plane. ───────────────────────────────────────────────────────────────────── Command the three Fortinet skills invoke (one server serves all planes) Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FORTINET_VERIFY_SSL",
      "label": "Fortinet Verify Ssl",
      "help": "TLS verification. Defaults to true. Fortinet appliances ship self-signed certificates; import the appliance CA rather than disabling this, since disabling it exposes the API token to interception.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_INSTANCE_URL",
      "label": "Servicenow Instance Url",
      "help": "SERVICENOW_INSTANCE_URL is consumed by the selected Fortinet (FortiManager/FortiGate/FortiAnalyzer) registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "gnmi",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/fortinet-mcp/gates.py#L53",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_PASSWORD",
      "label": "Servicenow Password",
      "help": "SERVICENOW_PASSWORD is consumed by the selected Fortinet (FortiManager/FortiGate/FortiAnalyzer) registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "gnmi",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/fortinet-mcp/gates.py#L55",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_USERNAME",
      "label": "Servicenow Username",
      "help": "SERVICENOW_USERNAME is consumed by the selected Fortinet (FortiManager/FortiGate/FortiAnalyzer) registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "gnmi",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/fortinet-mcp/gates.py#L54",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#fortinet-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "checkpoint": [
    {
      "key": "CHKP_ARGOS_API_KEY",
      "label": "Chkp Argos Api Key",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_ARGOS_CUSTOMER_ID",
      "label": "Chkp Argos Customer Id",
      "help": "CHKP_ARGOS_CUSTOMER_ID is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_ARGOS_INTEGRATION_TOKEN",
      "label": "Chkp Argos Integration Token",
      "help": "CHKP_ARGOS_INTEGRATION_TOKEN is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_ARGOS_SERVER_URL",
      "label": "Chkp Argos Server Url",
      "help": "Argos ERM — exposure and risk management platform Authenticates via its own server URL + integration token, NOT a bare API key.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://your-argos-server",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_DOCS_AUTH_URL",
      "label": "Chkp Docs Auth Url",
      "help": "CHKP_DOCS_AUTH_URL is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_DOCS_CLIENT_ID",
      "label": "Chkp Docs Client Id",
      "help": "Documentation Tool — Check Point Documentation Tool API Authenticates via Infinity Portal (client_id / secret_key + auth URL).",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "your-docs-client-id",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_DOCS_REGION",
      "label": "Chkp Docs Region",
      "help": "CHKP_DOCS_REGION is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_DOCS_SECRET_KEY",
      "label": "Chkp Docs Secret Key",
      "help": "CHKP_DOCS_SECRET_KEY is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_GAIA_VERBOSE",
      "label": "Chkp Gaia Verbose",
      "help": "Gaia OS — networking/routing on a gateway; uses interactive dialog auth (prompts for gateway IP/user/password per call, cached ~15 min). No credential env vars.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_LOG_LEVEL",
      "label": "Chkp Log Level",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "standard",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_MGMT_API_KEY",
      "label": "Chkp Mgmt Api Key",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_MGMT_DOMAIN",
      "label": "Chkp Mgmt Domain",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_MGMT_HOST",
      "label": "Chkp Mgmt Host",
      "help": "Management Server (on-premises) — required for policy, logs, threat prevention MCPs",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "192.168.1.100",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_MGMT_PASSWORD",
      "label": "Chkp Mgmt Password",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_MGMT_PORT",
      "label": "Chkp Mgmt Port",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "443",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_MGMT_USERNAME",
      "label": "Chkp Mgmt Username",
      "help": "Alternative: username/password authentication",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_REPUTATION_API_KEY",
      "label": "Chkp Reputation Api Key",
      "help": "Reputation Service — IP/URL/file threat intelligence lookups Contact TCAPI_SUPPORT@checkpoint.com for API key",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_S1C_API_KEY",
      "label": "Chkp S1C Api Key",
      "help": "Smart-1 Cloud (alternative to on-prem management)",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_S1C_URL",
      "label": "Chkp S1C Url",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://your-tenant.maas.checkpoint.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_SASE_API_KEY",
      "label": "Chkp Sase Api Key",
      "help": "Harmony SASE — cloud-delivered security for distributed networks",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_SASE_MGMT_HOST",
      "label": "Chkp Sase Mgmt Host",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "https://api.us1.sase.checkpoint.com/api",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_SASE_ORIGIN",
      "label": "Chkp Sase Origin",
      "help": "CHKP_SASE_ORIGIN is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_SPARK_API_KEY",
      "label": "Chkp Spark Api Key",
      "help": "Check Point Security (15 MCPs). Management Server requires CHKP_MGMT_HOST + API key or username/password. Additional keys for SASE, Threat Emulation, Reputation, Spark, Argos. Enable with ./scripts/checkpoint-enable.sh",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_SPARK_CLIENT_ID",
      "label": "Chkp Spark Client Id",
      "help": "Spark Management — MSP-oriented distributed firewall management Authenticates via Infinity Portal (client_id / secret_key), NOT a bare API key.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "your-spark-client-id",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_SPARK_INFINITY_PORTAL_URL",
      "label": "Chkp Spark Infinity Portal Url",
      "help": "CHKP_SPARK_INFINITY_PORTAL_URL is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://cloudinfra-gw.portal.checkpoint.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_SPARK_REGION",
      "label": "Chkp Spark Region",
      "help": "CHKP_SPARK_REGION is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_SPARK_SECRET_KEY",
      "label": "Chkp Spark Secret Key",
      "help": "CHKP_SPARK_SECRET_KEY is consumed by the selected Check Point registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_TELEMETRY_DISABLED",
      "label": "Chkp Telemetry Disabled",
      "help": "Global Settings",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CHKP_TE_API_KEY",
      "label": "Chkp Te Api Key",
      "help": "Threat Emulation — cloud sandboxing for malware analysis",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#chkp-management,chkp-management-logs,chkp-threat-prevention,chkp-https-inspection,chkp-harmony-sase,chkp-reputation-service,chkp-quantum-gw-cli,chkp-gw-connection-analysis,chkp-threat-emulation,chkp-quantum-gaia,chkp-documentation,chkp-spark-management,chkp-cpinfo-analysis,chkp-argos-erm,chkp-policy-insights",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "zscaler": [
    {
      "key": "ZSCALER_ZIA_API_KEY",
      "label": "Zscaler Zia Api Key",
      "help": "Zscaler MCP Server (300+ tools: ZIA, ZPA, ZDX, identity, insights) Complete Zscaler security platform integration (Zero Trust) Create API keys in Zscaler admin portal (ZIA/ZPA)",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "ZSCALER_ZIA_USERNAME"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zscaler-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZSCALER_ZIA_CLOUD",
      "label": "Zscaler Zia Cloud",
      "help": "Zscaler MCP Server via remote HTTP. ZIA credentials for internet access, ZPA credentials for private access. Multiple clouds supported.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zscaler-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZSCALER_ZIA_PASSWORD",
      "label": "Zscaler Zia Password",
      "help": "Zscaler MCP Server via remote HTTP. ZIA credentials for internet access, ZPA credentials for private access. Multiple clouds supported.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "ZSCALER_ZIA_USERNAME"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zscaler-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZSCALER_ZIA_USERNAME",
      "label": "Zscaler Zia Username",
      "help": "Zscaler MCP Server via remote HTTP. ZIA credentials for internet access, ZPA credentials for private access. Multiple clouds supported.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "admin@example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zscaler-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZSCALER_ZPA_CLIENT_ID",
      "label": "Zscaler Zpa Client Id",
      "help": "Zscaler MCP Server via remote HTTP. ZIA credentials for internet access, ZPA credentials for private access. Multiple clouds supported.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "your_client_id",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zscaler-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZSCALER_ZPA_CLIENT_SECRET",
      "label": "Zscaler Zpa Client Secret",
      "help": "Zscaler MCP Server via remote HTTP. ZIA credentials for internet access, ZPA credentials for private access. Multiple clouds supported.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "ZSCALER_ZPA_CLIENT_ID"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zscaler-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZSCALER_ZPA_CUSTOMER_ID",
      "label": "Zscaler Zpa Customer Id",
      "help": "Zscaler MCP Server via remote HTTP. ZIA credentials for internet access, ZPA credentials for private access. Multiple clouds supported.",
      "classification": "private",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "ZSCALER_ZPA_CLIENT_ID"
      },
      "example": "your_customer_id",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zscaler-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "claroty": [
    {
      "key": "CLAROTY_API_TOKEN",
      "label": "Claroty Api Token",
      "help": "Claroty xDome MCP — OT / IoT / IoMT visibility. Bearer token from xDome Admin Settings > User Management. Writes require a ServiceNow CR; NETCLAW_LAB_MODE=true skips the state check (shared with gnmi-mcp). The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/clients/claroty_client.py#L127",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLAROTY_API_URL",
      "label": "Claroty Api Url",
      "help": "Claroty xDome MCP Server (21 tools: 15 read + 6 ITSM-gated writes) OT / IoT / IoMT visibility, vulnerability triage, alert response, Purdue Model classification Token: Admin Settings > User Management in xDome dashboard Reuses NETCLAW_LAB_MODE for ITSM-gate bypass — do NOT introduce a CLAROTY_LAB_MODE",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://api.medigate.io",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/clients/claroty_client.py#L126",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLAROTY_RATE_LIMIT_PER_MIN",
      "label": "Claroty Rate Limit Per Min",
      "help": "Claroty xDome MCP — OT / IoT / IoMT visibility. Bearer token from xDome Admin Settings > User Management. Writes require a ServiceNow CR; NETCLAW_LAB_MODE=true skips the state check (shared with gnmi-mcp).",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "2000",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/clients/claroty_client.py#L131",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLAROTY_TIMEOUT",
      "label": "Claroty Timeout",
      "help": "Claroty xDome MCP — OT / IoT / IoMT visibility. Bearer token from xDome Admin Settings > User Management. Writes require a ServiceNow CR; NETCLAW_LAB_MODE=true skips the state check (shared with gnmi-mcp).",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "30",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/clients/claroty_client.py#L129",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLAROTY_VERIFY_SSL",
      "label": "Claroty Verify Ssl",
      "help": "Claroty xDome MCP — OT / IoT / IoMT visibility. Bearer token from xDome Admin Settings > User Management. Writes require a ServiceNow CR; NETCLAW_LAB_MODE=true skips the state check (shared with gnmi-mcp).",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/clients/claroty_client.py#L128",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_LAB_MODE",
      "label": "Netclaw Lab Mode",
      "help": "Claroty xDome MCP — OT / IoT / IoMT visibility. Bearer token from xDome Admin Settings > User Management. Writes require a ServiceNow CR; NETCLAW_LAB_MODE=true skips the state check (shared with gnmi-mcp).",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [
        "gnmi",
        "n2n",
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/utils/itsm_gate.py#L63",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_INSTANCE_URL",
      "label": "Servicenow Instance Url",
      "help": "SERVICENOW_INSTANCE_URL is consumed by the selected Claroty xDome registration. Leave unset only when using the documented native/default configuration. The consumer has an explicit fallback; Configure later preserves that fallback. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "fortinet",
        "gnmi",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/utils/itsm_gate.py#L123",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_PASSWORD",
      "label": "Servicenow Password",
      "help": "SERVICENOW_PASSWORD is consumed by the selected Claroty xDome registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "fortinet",
        "gnmi",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/utils/itsm_gate.py#L125",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_USERNAME",
      "label": "Servicenow Username",
      "help": "SERVICENOW_USERNAME is consumed by the selected Claroty xDome registration. Leave unset only when using the documented native/default configuration. Required only for production write workflows; setup verification does not perform network writes.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "fortinet",
        "gnmi",
        "multivendor-cli",
        "servicenow"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/claroty-mcp/utils/itsm_gate.py#L124",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#claroty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "nvd-cve": [
    {
      "key": "MCP_CALL",
      "label": "Mcp Call",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "catc",
        "cisco-psirt",
        "f5",
        "mempalace",
        "subnet-calc"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#nvd-cve-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NVD_API_KEY",
      "label": "Nvd Api Key",
      "help": "NVD API key (optional but increases rate limits).",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nvd-cve-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NVD_MCP_SCRIPT",
      "label": "Nvd Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. NVD API key (optional but increases rate limits). Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#nvd-cve-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "cisco-psirt": [
    {
      "key": "CISCO_CLIENT_ID",
      "label": "Cisco Client Id",
      "help": "Cisco PSIRT openVuln API (spec 078) — is a running version affected by an advisory? Register a SERVICE application with the Client Credentials grant at apiconsole.cisco.com and select \"Cisco PSIRT openVuln API\". Read-only. Never contacts a device — versions come from pyATS/multivendor-cli. ---------------------------------------------------------------------------",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/cisco-psirt-mcp/auth.py#L46",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#cisco-psirt-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CISCO_CLIENT_SECRET",
      "label": "Cisco Client Secret",
      "help": "Cisco PSIRT openVuln API via OAuth2 client credentials (id.cisco.com, 3600s token, refreshed proactively at 60s remaining). Read-only and device-free — versions are supplied by the caller from pyATS or multivendor-cli. Rate budget is 5/sec and 30/min shared, so lookups de-duplicate by version and cache for 6h on disk. Version format differs per family and contradicts across them: iosxe wants 17.3.1 and rejects 17.3(1), while ios wants 15.2(4)E and rejects 15.2.4E; aci wants the SWITCH image version 15.2(3e), not the APIC version. NOT available: iosxr (404, not an OSType), Bug/EoX/Case/Serial (403 under this grant), CX Cloud (504).",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/cisco-psirt-mcp/auth.py#L47",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#cisco-psirt-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CISCO_PSIRT_CACHE_DIR",
      "label": "Cisco Psirt Cache Dir",
      "help": "Advisory cache location (default ~/.openclaw/cisco-psirt). Advisories only — the OAuth token is a credential and is never written to disk.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/cisco-psirt-mcp/cache.py#L29",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#cisco-psirt-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CISCO_PSIRT_CACHE_TTL_S",
      "label": "Cisco Psirt Cache Ttl S",
      "help": "Cache lifetime in seconds (default 21600 = 6h). The rate budget is 5/sec and 30/min shared across every caller, so shortening this has a real cost.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/cisco-psirt-mcp/cache.py#L34",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#cisco-psirt-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CISCO_PSIRT_MCP_SCRIPT",
      "label": "Cisco Psirt Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#cisco-psirt-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MCP_CALL",
      "label": "Mcp Call",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "catc",
        "f5",
        "mempalace",
        "nvd-cve",
        "subnet-calc"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#cisco-psirt-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "nmap": [
    {
      "key": "NMAP_ALLOWED_CIDRS",
      "label": "Nmap Allowed Cidrs",
      "help": "CIDR allowlist for nmap scope enforcement.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#nmap-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NMAP_MCP_SCRIPT",
      "label": "Nmap Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. CIDR allowlist for nmap scope enforcement. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#nmap-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "fwrule": [
    {
      "key": "FWRULE_LOG_LEVEL",
      "label": "Fwrule Log Level",
      "help": "FWRULE_LOG_LEVEL is consumed by the selected Firewall Rule Analyzer registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#fwrule-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "FWRULE_MCP_DIR",
      "label": "Fwrule Mcp Dir",
      "help": "Generated for this selected installation by the scoped adapter. Firewall rule analyzer — no credentials needed. Works on config text input. Supports PAN-OS, ASA, FTD, IOS, IOS-XR, Check Point, SRX, Junos, Nokia SR OS. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#fwrule-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "aws": [
    {
      "key": "AWS_ACCESS_KEY_ID",
      "label": "Aws Access Key Id",
      "help": "AWS Cloud (IAM credentials for 6 AWS MCP servers)",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aws-network-mcp,aws-cloudwatch-mcp,aws-iam-mcp,aws-cloudtrail-mcp,aws-cost-explorer-mcp,aws-diagram-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AWS_PROFILE",
      "label": "Aws Profile",
      "help": "Or use a named profile instead:",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "my-profile",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aws-network-mcp,aws-cloudwatch-mcp,aws-iam-mcp,aws-cloudtrail-mcp,aws-cost-explorer-mcp,aws-diagram-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AWS_REGION",
      "label": "Aws Region",
      "help": "IAM credentials or named AWS CLI profile.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "us-east-1",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aws-network-mcp,aws-cloudwatch-mcp,aws-iam-mcp,aws-cloudtrail-mcp,aws-cost-explorer-mcp,aws-diagram-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AWS_SECRET_ACCESS_KEY",
      "label": "Aws Secret Access Key",
      "help": "IAM credentials or named AWS CLI profile.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#aws-network-mcp,aws-cloudwatch-mcp,aws-iam-mcp,aws-cloudtrail-mcp,aws-cost-explorer-mcp,aws-diagram-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "azure": [
    {
      "key": "AZURE_CLIENT_ID",
      "label": "Azure Client Id",
      "help": "Azure service principal with Reader role on target subscriptions.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "sharedWith": [
        "msgraph"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/azure-network-mcp/clients/azure_client.py#L35",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#azure-network-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AZURE_CLIENT_SECRET",
      "label": "Azure Client Secret",
      "help": "Azure service principal with Reader role on target subscriptions.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [
        "msgraph"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/azure-network-mcp/clients/azure_client.py#L36",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#azure-network-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AZURE_SUBSCRIPTION_ID",
      "label": "Azure Subscription Id",
      "help": "Azure service principal with Reader role on target subscriptions.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/azure-network-mcp/clients/azure_client.py#L37",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#azure-network-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AZURE_TENANT_ID",
      "label": "Azure Tenant Id",
      "help": "Azure Network MCP (19 tools: VNets, NSGs, ExpressRoute, VPN, Firewall, LB, DNS) Create service principal: az ad sp create-for-rbac --name \"netclaw-reader\" --role \"Reader\" --scopes /subscriptions/<sub-id>",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "sharedWith": [
        "msgraph"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/azure-network-mcp/clients/azure_client.py#L34",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#azure-network-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "gcp": [
    {
      "key": "GCP_PROJECT_ID",
      "label": "Gcp Project Id",
      "help": "Google Cloud Platform (4 GCP remote MCP servers)",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "my-project-123",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#gcp-compute-mcp,gcp-monitoring-mcp,gcp-logging-mcp,gcp-resource-manager-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GOOGLE_APPLICATION_CREDENTIALS",
      "label": "Google Application Credentials",
      "help": "GCP project ID and service account JSON key path.",
      "classification": "private",
      "valueType": "path",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#gcp-compute-mcp,gcp-monitoring-mcp,gcp-logging-mcp,gcp-resource-manager-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "equinix": [
    {
      "key": "EQUINIX_ALLOW_WRITES",
      "label": "Equinix Allow Writes",
      "help": "Browser OAuth required. Viewer for reads; Operator/Manager plus exact approved Implement CR, baseline and GAIT for writes. OAuth cache is member-isolated. Configured does not mean authenticated; no delete tools.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/equinix-stdio.py#L245",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#equinix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "EQUINIX_AUTH_DIR",
      "label": "Equinix Auth Dir",
      "help": "Optional private cache base. Member ID partitions it automatically.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#equinix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "EQUINIX_ENABLED",
      "label": "Equinix Enabled",
      "help": "Equinix Fabric + Network Edge (spec 132). Browser OAuth; never put OAuth tokens here.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/equinix-stdio.py#L233",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#equinix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "EQUINIX_SERVICENOW_PASSWORD",
      "label": "Equinix Servicenow Password",
      "help": "Browser OAuth required. Viewer for reads; Operator/Manager plus exact approved Implement CR, baseline and GAIT for writes. OAuth cache is member-isolated. Configured does not mean authenticated; no delete tools.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/lib/equinix/policy.py#L65",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#equinix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "EQUINIX_SERVICENOW_URL",
      "label": "Equinix Servicenow Url",
      "help": "Dedicated read-only ServiceNow verifier account; only required for gated writes.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/lib/equinix/policy.py#L63",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#equinix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "EQUINIX_SERVICENOW_USERNAME",
      "label": "Equinix Servicenow Username",
      "help": "Browser OAuth required. Viewer for reads; Operator/Manager plus exact approved Implement CR, baseline and GAIT for writes. OAuth cache is member-isolated. Configured does not mean authenticated; no delete tools.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/lib/equinix/policy.py#L64",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#equinix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "cloudflare": [
    {
      "key": "CLOUDFLARE_ACCOUNT_ID",
      "label": "Cloudflare Account Id",
      "help": "Cloudflare MCP Servers (5 domain-specific). API token from Cloudflare dashboard. Account ID required, Zone ID optional.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "your_account_id",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cloudflare-dns-analytics,cloudflare-security,cloudflare-zerotrust,cloudflare-analytics,cloudflare-workers",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLOUDFLARE_API_TOKEN",
      "label": "Cloudflare Api Token",
      "help": "Cloudflare MCP Server (5 remote servers: DNS, security, Zero Trust, analytics, Workers) Domain-specific remote MCP servers for complete Cloudflare platform coverage API token from https://dash.cloudflare.com/profile/api-tokens",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cloudflare-dns-analytics,cloudflare-security,cloudflare-zerotrust,cloudflare-analytics,cloudflare-workers",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLOUDFLARE_ZONE_ID",
      "label": "Cloudflare Zone Id",
      "help": "Cloudflare MCP Servers (5 domain-specific). API token from Cloudflare dashboard. Account ID required, Zone ID optional.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "your_zone_id",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cloudflare-dns-analytics,cloudflare-security,cloudflare-zerotrust,cloudflare-analytics,cloudflare-workers",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "terraform": [
    {
      "key": "TFC_HOST",
      "label": "Tfc Host",
      "help": "Terraform Cloud MCP Server via remote HTTP. API token from Terraform Cloud settings. Host defaults to app.terraform.io.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "app.terraform.io",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#terraform-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TFC_ORG",
      "label": "Tfc Org",
      "help": "Terraform Cloud MCP Server via remote HTTP. API token from Terraform Cloud settings. Host defaults to app.terraform.io.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "your-organization",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#terraform-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TFC_TOKEN",
      "label": "Tfc Token",
      "help": "HashiCorp Terraform Cloud MCP Server (40+ tools: workspaces, runs, state, variables) Terraform Cloud/Enterprise integration with workspace management",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#terraform-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "vault": [
    {
      "key": "VAULT_ADDR",
      "label": "Vault Addr",
      "help": "HashiCorp Vault MCP Server (35+ tools: secrets, PKI, auth, transit) Secrets management with multiple auth methods and secret engines",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#vault-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "VAULT_NAMESPACE",
      "label": "Vault Namespace",
      "help": "HashiCorp Vault MCP Server via remote HTTP. Server address and auth token. Namespace is for Vault Enterprise only.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#vault-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "VAULT_TOKEN",
      "label": "Vault Token",
      "help": "HashiCorp Vault MCP Server via remote HTTP. Server address and auth token. Namespace is for Vault Enterprise only.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#vault-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "grafana": [
    {
      "key": "GRAFANA_ORG_ID",
      "label": "Grafana Org Id",
      "help": "Grafana instance URL and service account or basic auth.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "1",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#grafana-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GRAFANA_PASSWORD",
      "label": "Grafana Password",
      "help": "Grafana instance URL and service account or basic auth.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#grafana-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GRAFANA_SERVICE_ACCOUNT_TOKEN",
      "label": "Grafana Service Account Token",
      "help": "Grafana instance URL and service account or basic auth.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#grafana-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GRAFANA_URL",
      "label": "Grafana Url",
      "help": "Grafana (observability platform — 75+ tools: dashboards, Prometheus, Loki, alerting, incidents, OnCall)",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "http://grafana.example.com:3000",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#grafana-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GRAFANA_USERNAME",
      "label": "Grafana Username",
      "help": "Grafana instance URL and service account or basic auth.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#grafana-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "prometheus": [
    {
      "key": "PROMETHEUS_DISABLE_LINKS",
      "label": "Prometheus Disable Links",
      "help": "Direct Prometheus endpoint with auth options.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prometheus-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PROMETHEUS_PASSWORD",
      "label": "Prometheus Password",
      "help": "Direct Prometheus endpoint with auth options.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prometheus-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PROMETHEUS_REQUEST_TIMEOUT",
      "label": "Prometheus Request Timeout",
      "help": "Direct Prometheus endpoint with auth options.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "30",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prometheus-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PROMETHEUS_TOKEN",
      "label": "Prometheus Token",
      "help": "Direct Prometheus endpoint with auth options.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prometheus-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PROMETHEUS_URL",
      "label": "Prometheus Url",
      "help": "Prometheus (direct PromQL queries — 6 tools: instant/range queries, metric discovery, targets, health)",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "http://prometheus:9090",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prometheus-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PROMETHEUS_URL_SSL_VERIFY",
      "label": "Prometheus Url Ssl Verify",
      "help": "Direct Prometheus endpoint with auth options.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prometheus-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PROMETHEUS_USERNAME",
      "label": "Prometheus Username",
      "help": "Direct Prometheus endpoint with auth options.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#prometheus-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "datadog": [
    {
      "key": "DD_API_KEY",
      "label": "Dd Api Key",
      "help": "Datadog MCP Server (16+ tools: logs, metrics, incidents, APM, dashboards) Full observability stack with all optional toolsets (apm, error_tracking, feature_flags, dbm, security, llm_observability) API keys from https://app.datadoghq.com/organization-settings/api-keys",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#datadog-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "DD_APP_KEY",
      "label": "Dd App Key",
      "help": "Datadog MCP Server via remote HTTP. API/App keys from Datadog organization settings. Site defaults to datadoghq.com (use datadoghq.eu for EU).",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#datadog-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "DD_SITE",
      "label": "Dd Site",
      "help": "Datadog MCP Server via remote HTTP. API/App keys from Datadog organization settings. Site defaults to datadoghq.com (use datadoghq.eu for EU).",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#datadog-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "splunk": [
    {
      "key": "SPLUNK_HOST",
      "label": "Splunk Host",
      "help": "Splunk MCP Server (30 tools: search, indexes, saved searches, alerts) Full Splunk Enterprise/Cloud integration with SPL queries",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "https://splunk.example.com:8089",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#splunk-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SPLUNK_TOKEN",
      "label": "Splunk Token",
      "help": "Splunk MCP Server via uvx. Host is the Splunk management port URL (e.g., https://splunk:8089). Token is a Splunk auth token.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#splunk-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SPLUNK_VERIFY_SSL",
      "label": "Splunk Verify Ssl",
      "help": "Splunk MCP Server via uvx. Host is the Splunk management port URL (e.g., https://splunk:8089). Token is a Splunk auth token.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#splunk-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "pagerduty": [
    {
      "key": "PAGERDUTY_API_HOST",
      "label": "Pagerduty Api Host",
      "help": "PagerDuty MCP Server via uvx. User API key from PagerDuty API settings. API host defaults to US (use api.eu.pagerduty.com for EU).",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "https://api.pagerduty.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#pagerduty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PAGERDUTY_USER_API_KEY",
      "label": "Pagerduty User Api Key",
      "help": "PagerDuty MCP Server (70 tools: incidents, on-call, services, event orchestration) Full incident management with read/write operations (--enable-write-tools) API token from https://support.pagerduty.com/docs/api-access-keys",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#pagerduty-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "te-community": [
    {
      "key": "TE_TOKEN",
      "label": "Te Token",
      "help": "Cisco ThousandEyes (community + official MCP servers)",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [
        "te-official"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#thousandeyes-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "te-official": [
    {
      "key": "TE_TOKEN",
      "label": "Te Token",
      "help": "Cisco ThousandEyes (community + official MCP servers)",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [
        "te-community"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#thousandeyes-official-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "ipfabric": [
    {
      "key": "IPFABRIC_HOST",
      "label": "Ipfabric Host",
      "help": "IP Fabric appliance URL.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/ipfabric/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "IPFABRIC_API_TOKEN",
      "label": "Ipfabric Api Token",
      "help": "API token from the appliance settings.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "workspace/skills/ipfabric/SKILL.md",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    }
  ],
  "forward": [
    {
      "key": "FORWARD_AUTH_BASE64",
      "label": "Forward Auth Base64",
      "help": "Base64 of 'accessKey:secret' for a Forward API token (Settings > Account > API tokens), sent as HTTP Basic to /api/mcp. The token's user decides which networks the MCP can reach. `echo -n 'accessKey:secret' | base64`, or run scripts/forward-enable.sh.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#forward-official-mcp",
          "checkedAt": "2026-10-25",
          "note": "Exact selected registration substitutions."
        }
      ]
    },
    {
      "key": "FORWARD_URL",
      "label": "Forward Url",
      "help": "Forward base URL without a path (e.g. https://fwd.app or your self-hosted host). NetClaw appends /api/mcp. A 403 means an admin turned off 'Enable MCP server' or the license expired.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#forward-official-mcp",
          "checkedAt": "2026-10-25",
          "note": "Exact selected registration substitutions."
        }
      ]
    }
  ],
  "suzieq": [
    {
      "key": "SUZIEQ_API_KEY",
      "label": "Suzieq Api Key",
      "help": "SuzieQ REST API URL and access token. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/suzieq-mcp/suzieq_client.py#L41",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#suzieq-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SUZIEQ_API_URL",
      "label": "Suzieq Api Url",
      "help": "SuzieQ (Network Observability — 5 read-only tools: show, summarize, assert, unique, path) The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "http://suzieq-host:8000",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/suzieq-mcp/suzieq_client.py#L40",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#suzieq-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SUZIEQ_TIMEOUT",
      "label": "Suzieq Timeout",
      "help": "SuzieQ REST API URL and access token.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "30",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/suzieq-mcp/suzieq_client.py#L43",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#suzieq-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SUZIEQ_VERIFY_SSL",
      "label": "Suzieq Verify Ssl",
      "help": "SuzieQ REST API URL and access token.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/suzieq-mcp/suzieq_client.py#L42",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#suzieq-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "kubeshark": [
    {
      "key": "KUBESHARK_MCP_PORT",
      "label": "Kubeshark Mcp Port",
      "help": "Kubeshark in-cluster MCP endpoint.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "8898",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#kubeshark-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "KUBESHARK_MCP_URL",
      "label": "Kubeshark Mcp Url",
      "help": "Kubeshark (Kubernetes L4/L7 traffic analysis — 6 tools: capture, pcap export, snapshots, flows, TLS decryption)",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "http://localhost:8898/mcp",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#kubeshark-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "gtrace": [
    {
      "key": "GTRACE_MCP_BIN",
      "label": "Gtrace Mcp Bin",
      "help": "Generated for this selected installation by the scoped adapter. gtrace Go binary path. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#gtrace-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "k8s": [
    {
      "key": "K8S_KUBECONFIG",
      "label": "K8S Kubeconfig",
      "help": "silently ignores the token and authenticates as the cert's identity instead.  Cluster-wide read is required, not optional. With it, the upstream server's silent-narrowing path is unreachable; without it, a cluster-wide question can come back scoped to one namespace with no error and no caveat.",
      "classification": "private",
      "valueType": "path",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#k8s-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "K8S_MCP_CMD",
      "label": "K8S Mcp Cmd",
      "help": "Generated for this selected installation by the scoped adapter. Server: mcp-servers/k8s-mcp  (VENDORED third-party, Apache-2.0, pinned v0.0.66)  STRICTLY READ-ONLY. No write path. Secrets are denied. ───────────────────────────────────────────────────────────────────── Command the three k8s skills invoke (the pinned binary) Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#k8s-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "zabbix": [
    {
      "key": "READ_ONLY",
      "label": "Read Only",
      "help": "Read-only. NetClaw FORCES this to true in config/openclaw.json and you should not override it. The reason it is forced rather than inherited: the upstream library defaults it to true (utils.py:29) but the upstream LAUNCHER defaults it to false (scripts/start_server.py:139), so running it the documented upstream way would enable writes.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zabbix-mcp/vendor/zabbix-mcp-server/scripts/test_server.py#L79",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zabbix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "VERIFY_SSL",
      "label": "Verify Ssl",
      "help": "TLS verification. Defaults to true. Import your CA rather than disabling this — disabling it exposes the API token to interception. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zabbix-mcp/vendor/zabbix-mcp-server/scripts/test_server.py#L82",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zabbix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZABBIX_API_BLACKLIST",
      "label": "Zabbix Api Blacklist",
      "help": "Destructive-method deny-list (regex, comma separated). Second layer, set in config/openclaw.json. Holds even if READ_ONLY is misconfigured.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zabbix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZABBIX_MCP_CMD",
      "label": "Zabbix Mcp Cmd",
      "help": "Generated for this selected installation by the scoped adapter. five NetClaw servers pin fastmcp<3. A shared install breaks all five.  Strictly READ-ONLY. There is no write path in this integration. ───────────────────────────────────────────────────────────────────── Command the three zabbix skills invoke (the venv interpreter) Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#zabbix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZABBIX_TOKEN",
      "label": "Zabbix Token",
      "help": "API TOKEN, not a password. Users -> API tokens in the Zabbix UI. Token auth is required for forward-compatibility: the older in-request credential property still works on 7.0 but is REMOVED in 7.2+.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zabbix-mcp/vendor/zabbix-mcp-server/scripts/start_server.py#L58",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zabbix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZABBIX_URL",
      "label": "Zabbix Url",
      "help": "Base URL of your Zabbix front end, e.g. https://zabbix.example.com (the API lives at <url>/api_jsonrpc.php) The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zabbix-mcp/vendor/zabbix-mcp-server/scripts/start_server.py#L99",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zabbix-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "bgp-intel": [
    {
      "key": "BGP_INTEL_AUDIT_LOG",
      "label": "Bgp Intel Audit Log",
      "help": "GAIT audit trail path. Defaults under ~/.openclaw/gait/",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/bgp-intel-mcp/envelope.py#L206",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#bgp-intel-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "BGP_INTEL_MAX_RPS",
      "label": "Bgp Intel Max Rps",
      "help": "Requests per second per source. Default 4, enforced as a true sliding window. May be LOWERED to be more polite; values above 4 are clamped, not honoured.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/bgp-intel-mcp/http_client.py#L59",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#bgp-intel-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "BGP_INTEL_MCP_CMD",
      "label": "Bgp Intel Mcp Cmd",
      "help": "Generated for this selected installation by the scoped adapter. NO CREDENTIALS REQUIRED. All five sources (RPKI validator, RDAP, RIPEstat, PeeringDB, RIPE Atlas) are public unauthenticated APIs. There is nothing here to leak, rotate or scope — the only variables are optional tuning. ───────────────────────────────────────────────────────────────────── Command the bgp-registry-intel skill invokes Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#bgp-intel-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "BGP_INTEL_USER_AGENT",
      "label": "Bgp Intel User Agent",
      "help": "Contact string sent to public APIs. These are volunteer-funded community services and identifying yourself is the courtesy they ask of automated consumers. Defaults to a NetClaw string with the project URL.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#bgp-intel-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "globalping": [
    {
      "key": "GLOBALPING_TOKEN",
      "label": "Globalping Token",
      "help": "The endpoint returns 401 without a token; the token raises the hourly allowance from 250 to 500 probe-measurements. Charged PER PROBE, so a limit:20 test spends 20 units. Public targets only — private/internal addresses are refused. ---------------------------------------------------------------------------",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#globalping-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "topolograph": [
    {
      "key": "TOPOLOGRAPH_API_TOKEN",
      "label": "Topolograph Api Token",
      "help": "Remote HTTP MCP (spec 119 IGP, spec 120 BGP) against the operator's OWN Topolograph instance — TOPOLOGRAPH_MCP_URL overrides the default hosted endpoint, bearer TOPOLOGRAPH_API_TOKEN, 401 without it. Fronts an operator-run HTTP API developed upstream, so it is registered by url in config/openclaw.json rather than vendored (same shape as globalping). 27 read-only analysis tools: 13 IGP (get_all_graphs/get_graph_by_time/get_graph_status, get_nodes/get_edges/get_network_by_graph_time/get_lsps, get_shortest_path/get_cspf_path, get_edge_failure_reaction (failure simulation), get_network_events/get_adjacency_events/get_events_timeline) plus 14 BGP (list_bgp_graphs/get_bgp_graph, list_bgp_nodes/list_bgp_sessions, search_bgp_routes, get_bgp_node_route_summary/get_bgp_route_state, compare_bgp_routes, get_bgp_events_timeline, list_bgp_bindings/get_bgp_binding, resolve_route, get_vrf_inventory/list_vpn_routers — requires Topolograph >= 2.69). The server runs TOPOLOGRAPH_MCP_READ_ONLY=true so upload_graph and the *_lsp mutation tools are absent from tools/list; the client allowlist is set with `defenseclaw tool allow topolograph-mcp <tool>` (never toolFilter in config). Every result is over a STORED graph_time/bgp_graph_time — report its age — and get_edge_failure_reaction / get_cspf_path / resolve_route are predictions, not events. Boundary: reasons over the whole area LSDB or BGP RIB as a graph; per-device RIB/LSDB stays with pyats-routing / pyats-junos-routing / multivendor-device-query.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#topolograph-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TOPOLOGRAPH_MCP_URL",
      "label": "Topolograph Mcp Url",
      "help": "Remote HTTP MCP against your OWN Topolograph instance, nothing to install. TOPOLOGRAPH_MCP_URL overrides the endpoint (default the hosted one); issue TOPOLOGRAPH_API_TOKEN from that instance. 401 without the token. The server is read-only (mutation tools hidden from tools/list). ---------------------------------------------------------------------------",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#topolograph-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "telemetry-receivers": [
    {
      "key": "IPFIX_PORT",
      "label": "Ipfix Port",
      "help": "Real-time telemetry receivers. Ports default to 514 (syslog), 162 (SNMP traps), 4739 (IPFIX). Buffer size controls in-memory retention.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SNMP_TRAP_PORT",
      "label": "Snmp Trap Port",
      "help": "Real-time telemetry receivers. Ports default to 514 (syslog), 162 (SNMP traps), 4739 (IPFIX). Buffer size controls in-memory retention.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SYSLOG_UDP_PORT",
      "label": "Syslog Udp Port",
      "help": "Real-time telemetry receivers. Ports default to 514 (syslog), 162 (SNMP traps), 4739 (IPFIX). Buffer size controls in-memory retention.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TELEMETRY_BUFFER_SIZE",
      "label": "Telemetry Buffer Size",
      "help": "Real-time telemetry receivers. Ports default to 514 (syslog), 162 (SNMP traps), 4739 (IPFIX). Buffer size controls in-memory retention.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "auvik": [
    {
      "key": "AUVIK_API_KEY",
      "label": "Auvik Api Key",
      "help": "Auvik user email + API key (HTTP Basic). AUVIK_BASE_URL defaults to the us1 cluster; override for other regions. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/auvik-mcp/auvik_mcp_server.py#L44",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#auvik-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AUVIK_BASE_URL",
      "label": "Auvik Base Url",
      "help": "Auvik user email + API key (HTTP Basic). AUVIK_BASE_URL defaults to the us1 cluster; override for other regions.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://auvikapi.us1.my.auvik.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/auvik-mcp/auvik_mcp_server.py#L53",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#auvik-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AUVIK_MAX_PAGES",
      "label": "Auvik Max Pages",
      "help": "AUVIK_MAX_PAGES is consumed by the selected Auvik registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "50",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/auvik-mcp/auvik_mcp_server.py#L48",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#auvik-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AUVIK_RATE_LIMIT",
      "label": "Auvik Rate Limit",
      "help": "AUVIK_RATE_LIMIT is consumed by the selected Auvik registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "600",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/auvik-mcp/auvik_mcp_server.py#L47",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#auvik-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AUVIK_TIMEOUT",
      "label": "Auvik Timeout",
      "help": "AUVIK_TIMEOUT is consumed by the selected Auvik registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "30",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/auvik-mcp/auvik_mcp_server.py#L46",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#auvik-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AUVIK_USERNAME",
      "label": "Auvik Username",
      "help": "Auvik Network Management (20 read-only tools: inventory, alerts, lifecycle/warranty, performance) API credentials from Auvik Settings → API Credentials (requires admin or manager role) Auth: HTTP Basic (user email + API key) — no extra OAuth required The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "your-email@example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/auvik-mcp/auvik_mcp_server.py#L43",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#auvik-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AUVIK_VERIFY_SSL",
      "label": "Auvik Verify Ssl",
      "help": "AUVIK_VERIFY_SSL is consumed by the selected Auvik registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/auvik-mcp/auvik_mcp_server.py#L45",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#auvik-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "cml": [
    {
      "key": "CML_PASSWORD",
      "label": "Cml Password",
      "help": "Cisco Modeling Labs API endpoint.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CML_URL",
      "label": "Cml Url",
      "help": "Cisco Modeling Labs (CML) MCP",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://cml.example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CML_USERNAME",
      "label": "Cml Username",
      "help": "Cisco Modeling Labs API endpoint.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CML_VERIFY_SSL",
      "label": "Cml Verify Ssl",
      "help": "Cisco Modeling Labs API endpoint.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#cml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "gns3": [
    {
      "key": "GNS3_PASSWORD",
      "label": "Gns3 Password",
      "help": "GNS3 network simulation server. URL is the GNS3 server address (e.g., http://localhost:3080). User/Password for authentication. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gns3-mcp-server/gns3_mcp_server.py#L48",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gns3-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNS3_TOKEN_TTL",
      "label": "Gns3 Token Ttl",
      "help": "GNS3 network simulation server. URL is the GNS3 server address (e.g., http://localhost:3080). User/Password for authentication.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "3000",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gns3-mcp-server/gns3_mcp_server.py#L50",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gns3-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNS3_URL",
      "label": "Gns3 Url",
      "help": "GNS3 Network Lab Management (26 tools: projects, nodes, links, captures, snapshots) Lab-only operations — no ServiceNow CR gating required The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "http://localhost:3080",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gns3-mcp-server/gns3_mcp_server.py#L46",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gns3-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNS3_USER",
      "label": "Gns3 User",
      "help": "GNS3 network simulation server. URL is the GNS3 server address (e.g., http://localhost:3080). User/Password for authentication. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "admin",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gns3-mcp-server/gns3_mcp_server.py#L47",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gns3-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GNS3_VERIFY_SSL",
      "label": "Gns3 Verify Ssl",
      "help": "GNS3 network simulation server. URL is the GNS3 server address (e.g., http://localhost:3080). User/Password for authentication.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/gns3-mcp-server/gns3_mcp_server.py#L49",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gns3-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "containerlab": [
    {
      "key": "CLAB_API_PASSWORD",
      "label": "Clab Api Password",
      "help": "ContainerLab API server credentials.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLAB_API_SERVER_URL",
      "label": "Clab Api Server Url",
      "help": "ContainerLab (containerized network labs via API)",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "http://localhost:8080",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLAB_API_USERNAME",
      "label": "Clab Api Username",
      "help": "ContainerLab API server credentials.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "netclaw",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CLAB_MCP_SCRIPT",
      "label": "Clab Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. ContainerLab API server credentials. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "batfish": [
    {
      "key": "BATFISH_HOST",
      "label": "Batfish Host",
      "help": "Batfish (network configuration analysis via Docker container)",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "localhost",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/batfish-mcp/batfish_mcp_server.py#L63",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#batfish-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "BATFISH_NETWORK",
      "label": "Batfish Network",
      "help": "Batfish offline config analysis via Docker container. Requires: docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "netclaw",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/batfish-mcp/batfish_mcp_server.py#L65",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#batfish-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "BATFISH_PORT",
      "label": "Batfish Port",
      "help": "Batfish offline config analysis via Docker container. Requires: docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "9997",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/batfish-mcp/batfish_mcp_server.py#L64",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#batfish-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "protocol": [
    {
      "key": "BGP_DAEMON_API",
      "label": "Bgp Daemon Api",
      "help": "BGP_DAEMON_API is consumed by the selected Protocol MCP registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "n2n"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/server.py#L157",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "BGP_LISTEN_PORT",
      "label": "Bgp Listen Port",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "n2n"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/bgp-daemon-v2.py#L50",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_BGP_PEERS",
      "label": "Netclaw Bgp Peers",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "n2n"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/bgp-daemon-v2.py#L48",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_GRE_TUNNELS",
      "label": "Netclaw Gre Tunnels",
      "help": "NETCLAW_GRE_TUNNELS is consumed by the selected Protocol MCP registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/server.py#L56",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_LAB_MODE",
      "label": "Netclaw Lab Mode",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [
        "claroty",
        "gnmi",
        "n2n"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/server.py#L57",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_LOCAL_AS",
      "label": "Netclaw Local As",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "65001",
      "sharedWith": [
        "n2n"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/bgp-daemon-v2.py#L47",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_LOCAL_IPV6",
      "label": "Netclaw Local Ipv6",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "n2n"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/bgp-daemon-v2.py#L58",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_MESH_OPEN",
      "label": "Netclaw Mesh Open",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "n2n"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/bgp-daemon-v2.py#L51",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_OSPF_AREAS",
      "label": "Netclaw Ospf Areas",
      "help": "NETCLAW_OSPF_AREAS is consumed by the selected Protocol MCP registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/server.py#L55",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_ROUTER_ID",
      "label": "Netclaw Router Id",
      "help": "Protocol Participation (BGP + OSPF + GRE — live control-plane peering)",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "4.4.4.4",
      "sharedWith": [
        "n2n"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/protocol-mcp/bgp-daemon-v2.py#L46",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PROTOCOL_MCP_SCRIPT",
      "label": "Protocol Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. BGP/OSPF protocol participation parameters. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "n2n"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#protocol-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "peering": [],
  "n2n": [
    {
      "key": "BGP_DAEMON_API",
      "label": "Bgp Daemon Api",
      "help": "BGP_DAEMON_API is consumed by the selected N2N Federation registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/n2n-mcp/server.py#L27",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "BGP_LISTEN_PORT",
      "label": "Bgp Listen Port",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_BGP_PEERS",
      "label": "Netclaw Bgp Peers",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_LAB_MODE",
      "label": "Netclaw Lab Mode",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [
        "claroty",
        "gnmi",
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_LOCAL_AS",
      "label": "Netclaw Local As",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "65001",
      "sharedWith": [
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_LOCAL_IPV6",
      "label": "Netclaw Local Ipv6",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_MESH_OPEN",
      "label": "Netclaw Mesh Open",
      "help": "BGP/OSPF protocol participation parameters.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "NETCLAW_ROUTER_ID",
      "label": "Netclaw Router Id",
      "help": "Protocol Participation (BGP + OSPF + GRE — live control-plane peering)",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "4.4.4.4",
      "sharedWith": [
        "protocol"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PROTOCOL_MCP_SCRIPT",
      "label": "Protocol Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. BGP/OSPF protocol participation parameters. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "protocol"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#n2n-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "in2n-production": [],
  "claw-certs": [],
  "servicenow": [
    {
      "key": "SERVICENOW_INSTANCE_URL",
      "label": "Servicenow Instance Url",
      "help": "ServiceNow ITSM instance credentials.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "gnmi",
        "multivendor-cli"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#servicenow-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_MCP_SCRIPT",
      "label": "Servicenow Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. ServiceNow ITSM instance credentials. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "aci",
        "ise"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#servicenow-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_PASSWORD",
      "label": "Servicenow Password",
      "help": "ServiceNow ITSM instance credentials.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "SERVICENOW_INSTANCE_URL"
      },
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "gnmi",
        "multivendor-cli"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#servicenow-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SERVICENOW_USERNAME",
      "label": "Servicenow Username",
      "help": "ServiceNow ITSM instance credentials.",
      "classification": "private",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "SERVICENOW_INSTANCE_URL"
      },
      "example": "",
      "sharedWith": [
        "claroty",
        "fortinet",
        "gnmi",
        "multivendor-cli"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#servicenow-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "github": [
    {
      "key": "GITHUB_PERSONAL_ACCESS_TOKEN",
      "label": "Github Personal Access Token",
      "help": "GitHub MCP (Personal Access Token)",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#github-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "gitlab": [
    {
      "key": "GITLAB_API_URL",
      "label": "Gitlab Api Url",
      "help": "GitLab PAT (api or read_api scope). GITLAB_API_URL defaults to gitlab.com; override for self-hosted.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://gitlab.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#gitlab-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GITLAB_PERSONAL_ACCESS_TOKEN",
      "label": "Gitlab Personal Access Token",
      "help": "GitLab MCP (98+ tools: issues, merge requests, pipelines, repos, wikis, labels, milestones, releases) Community server: @zereight/mcp-gitlab via npx (any GitLab tier, SaaS or self-hosted) PAT scopes: \"api\" for full access, \"read_api\" for read-only",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#gitlab-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GITLAB_READ_ONLY_MODE",
      "label": "Gitlab Read Only Mode",
      "help": "GitLab PAT (api or read_api scope). GITLAB_API_URL defaults to gitlab.com; override for self-hosted.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#gitlab-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "jenkins": [
    {
      "key": "JENKINS_API_TOKEN",
      "label": "Jenkins Api Token",
      "help": "Jenkins API token via HTTP Basic Auth. Remote HTTP transport at /mcp-server/mcp. Requires Jenkins 2.533+ with MCP Server plugin.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jenkins-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JENKINS_AUTH_BASE64",
      "label": "Jenkins Auth Base64",
      "help": "Jenkins API token via HTTP Basic Auth. Remote HTTP transport at /mcp-server/mcp. Requires Jenkins 2.533+ with MCP Server plugin.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jenkins-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JENKINS_URL",
      "label": "Jenkins Url",
      "help": "Jenkins MCP (16 tools: jobs, builds, pipelines, SCM, system health) Official Jenkins plugin — runs natively inside Jenkins via Streamable HTTP Requires: Jenkins 2.533+ with MCP Server plugin v0.158+ installed Auth: HTTP Basic with API token (User → Configure → API Token in Jenkins)",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "https://jenkins.example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jenkins-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JENKINS_USERNAME",
      "label": "Jenkins Username",
      "help": "Jenkins API token via HTTP Basic Auth. Remote HTTP transport at /mcp-server/mcp. Requires Jenkins 2.533+ with MCP Server plugin.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "your-username",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jenkins-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "atlassian": [
    {
      "key": "CONFLUENCE_API_TOKEN",
      "label": "Confluence Api Token",
      "help": "Atlassian Cloud: API token from id.atlassian.com. Server/DC: Personal Access Token. At least one product (Jira or Confluence) required.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "CONFLUENCE_URL"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#atlassian-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CONFLUENCE_URL",
      "label": "Confluence Url",
      "help": "Atlassian Cloud: API token from id.atlassian.com. Server/DC: Personal Access Token. At least one product (Jira or Confluence) required.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://your-domain.atlassian.net/wiki",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#atlassian-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "CONFLUENCE_USERNAME",
      "label": "Confluence Username",
      "help": "Atlassian Cloud: API token from id.atlassian.com. Server/DC: Personal Access Token. At least one product (Jira or Confluence) required.",
      "classification": "private",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "CONFLUENCE_URL"
      },
      "example": "your-email@example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#atlassian-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JIRA_API_TOKEN",
      "label": "Jira Api Token",
      "help": "Atlassian Cloud: API token from id.atlassian.com. Server/DC: Personal Access Token. At least one product (Jira or Confluence) required.",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "JIRA_URL"
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#atlassian-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JIRA_URL",
      "label": "Jira Url",
      "help": "Atlassian MCP (72 tools: Jira issues, transitions, comments, projects, links; Confluence pages, comments, spaces) Community server: mcp-atlassian by sooperset via uvx (Cloud + Server/DC support) Atlassian Cloud: API token from https://id.atlassian.com/manage-profile/security/api-tokens Server/DC: Personal Access Token from Profile → Personal Access Tokens At least one product (Jira or Confluence) must be configured",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://your-domain.atlassian.net",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#atlassian-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JIRA_USERNAME",
      "label": "Jira Username",
      "help": "Atlassian Cloud: API token from id.atlassian.com. Server/DC: Personal Access Token. At least one product (Jira or Confluence) required.",
      "classification": "private",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "present": "JIRA_URL"
      },
      "example": "your-email@example.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#atlassian-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "msgraph": [
    {
      "key": "AZURE_CLIENT_ID",
      "label": "Azure Client Id",
      "help": "Azure AD app registration for Microsoft Graph API.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "sharedWith": [
        "azure"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AZURE_CLIENT_SECRET",
      "label": "Azure Client Secret",
      "help": "Azure AD app registration for Microsoft Graph API.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "azure"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "AZURE_TENANT_ID",
      "label": "Azure Tenant Id",
      "help": "Azure Network MCP (19 tools: VNets, NSGs, ExpressRoute, VPN, Firewall, LB, DNS) Create service principal: az ad sp create-for-rbac --name \"netclaw-reader\" --role \"Reader\" --scopes /subscriptions/<sub-id>",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "sharedWith": [
        "azure"
      ],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "halo": [
    {
      "key": "HALO_BASE_URL",
      "label": "Halo Base Url",
      "help": "HaloPSA / HaloITSM MCP Server (18 tools: change requests + asset/ticket context) OAuth2 client-credentials. Create an API application in Halo: Configuration > Integrations > Halo API > New (Client Credentials) The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://your-tenant.halopsa.com",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L58",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HALO_CLIENT_ID",
      "label": "Halo Client Id",
      "help": "HaloPSA/HaloITSM OAuth2 client-credentials. Create an API application in Halo (Configuration > Integrations > Halo API). HALO_BASE_URL is the tenant host, e.g. https://<tenant>.halopsa.com. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "your-client-id",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L60",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HALO_CLIENT_SECRET",
      "label": "Halo Client Secret",
      "help": "HaloPSA/HaloITSM OAuth2 client-credentials. Create an API application in Halo (Configuration > Integrations > Halo API). HALO_BASE_URL is the tenant host, e.g. https://<tenant>.halopsa.com. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L61",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HALO_MAX_PAGES",
      "label": "Halo Max Pages",
      "help": "HALO_MAX_PAGES is consumed by the selected HaloPSA / HaloITSM registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "20",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L67",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HALO_PAGE_SIZE",
      "label": "Halo Page Size",
      "help": "HALO_PAGE_SIZE is consumed by the selected HaloPSA / HaloITSM registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L66",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HALO_SCOPE",
      "label": "Halo Scope",
      "help": "HaloPSA/HaloITSM OAuth2 client-credentials. Create an API application in Halo (Configuration > Integrations > Halo API). HALO_BASE_URL is the tenant host, e.g. https://<tenant>.halopsa.com.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L62",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HALO_TENANT",
      "label": "Halo Tenant",
      "help": "HaloPSA/HaloITSM OAuth2 client-credentials. Create an API application in Halo (Configuration > Integrations > Halo API). HALO_BASE_URL is the tenant host, e.g. https://<tenant>.halopsa.com.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "your-tenant",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L59",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HALO_TIMEOUT",
      "label": "Halo Timeout",
      "help": "HALO_TIMEOUT is consumed by the selected HaloPSA / HaloITSM registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "30",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L65",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HALO_VERIFY_SSL",
      "label": "Halo Verify Ssl",
      "help": "HALO_VERIFY_SSL is consumed by the selected HaloPSA / HaloITSM registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/halo-mcp/halo_mcp_server.py#L64",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#halo-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "packet-buddy": [
    {
      "key": "PCAP_UPLOAD_DIR",
      "label": "Pcap Upload Dir",
      "help": "Private directory for capture input; must be scoped to this installation.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/packet-buddy-mcp/server.py#L21",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "mcp-servers/packet-buddy-mcp/server.py",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    }
  ],
  "markmap": [
    {
      "key": "MARKMAP_MCP_SCRIPT",
      "label": "Markmap Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Markmap mind-map generation. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#markmap-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "drawio-rfc": [],
  "uml": [
    {
      "key": "KROKI_SERVER",
      "label": "Kroki Server",
      "help": "UML MCP (27+ diagram types via Kroki rendering)",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#uml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "LOG_LEVEL",
      "label": "Log Level",
      "help": "LOG_LEVEL is consumed by the selected UML Diagrams registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#uml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MCP_OUTPUT_DIR",
      "label": "Mcp Output Dir",
      "help": "Kroki/PlantUML rendering server URLs.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "./output",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#uml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "PLANTUML_SERVER",
      "label": "Plantuml Server",
      "help": "Kroki/PlantUML rendering server URLs.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#uml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "USE_LOCAL_KROKI",
      "label": "Use Local Kroki",
      "help": "USE_LOCAL_KROKI is consumed by the selected UML Diagrams registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#uml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "USE_LOCAL_PLANTUML",
      "label": "Use Local Plantuml",
      "help": "USE_LOCAL_PLANTUML is consumed by the selected UML Diagrams registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#uml-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "subnet-calc": [
    {
      "key": "MCP_CALL",
      "label": "Mcp Call",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "catc",
        "cisco-psirt",
        "f5",
        "mempalace",
        "nvd-cve"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#subnet-calc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SUBNET_MCP_SCRIPT",
      "label": "Subnet Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "wikipedia"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#subnet-calc-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "wikipedia": [
    {
      "key": "PACKET_BUDDY_MCP_SCRIPT",
      "label": "Packet Buddy Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Packet Buddy MCP (pcap analysis) Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "./mcp-servers/packet-buddy-mcp/server.py",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#wikipedia-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SUBNET_MCP_SCRIPT",
      "label": "Subnet Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Reference tools — Wikipedia, subnet calc, packet analysis. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "subnet-calc"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#wikipedia-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "WIKIPEDIA_MCP_SCRIPT",
      "label": "Wikipedia Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. Reference tools — Wikipedia, subnet calc, packet analysis. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#wikipedia-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "devnet-content-search": [],
  "blender": [
    {
      "key": "BLENDER_HOST",
      "label": "Blender Host",
      "help": "Blender MCP Server (3D Network Topology Visualization) Community server: blender-mcp via uvx (requires Blender on Windows with addon) Addon: https://github.com/ahujasid/blender-mcp",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#blender-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "ue5": [
    {
      "key": "UE5_MCP_URL",
      "label": "Ue5 Mcp Url",
      "help": "Unreal Engine 5.8 MCP Server (3D Network Topology Visualization) Built-in UE5.8 MCP plugin — no external dependencies required Enable plugin: Edit > Plugins > \"Unreal MCP\" (or \"ModelContextProtocol\") Auto-starts on editor launch or manually: ModelContextProtocol.StartServer in console",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "http://127.0.0.1:8000/mcp",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#unreal-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "threejs-viz": [
    {
      "key": "NETCLAW_SKETCHFAB_ENABLED",
      "label": "Enable Sketchfab stencil mode",
      "help": "Optional: downloads and registers the Sketchfab MCP for real 3D model stencils. False or omitted uses the bundled procedural shapes without Sketchfab downloads.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/lib/setup_special.py",
          "checkedAt": "2026-10-17",
          "note": "Plan-engine opt-in for the legacy optional Sketchfab branch."
        }
      ]
    },
    {
      "key": "SKETCHFAB_API_KEY",
      "label": "Sketchfab Api Key",
      "help": "Sketchfab MCP Server (3D model search/download for real-stencil mode, spec 046) Get an API token from https://sketchfab.com/settings/password (API Tokens section)",
      "classification": "secret",
      "valueType": "string",
      "required": "conditional",
      "condition": {
        "equals": {
          "key": "NETCLAW_SKETCHFAB_ENABLED",
          "value": true
        }
      },
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#sketchfab-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "SKETCHFAB_USERNAME",
      "label": "Sketchfab Username",
      "help": "Only needed for optional real-3D-model stencil mode. Token from https://sketchfab.com/settings/password. Procedural-shape rendering works with zero configuration.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "your_sketchfab_username",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#sketchfab-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "comfyui-viz": [
    {
      "key": "COMFYUI_URL",
      "label": "Comfyui Url",
      "help": "ComfyUI MCP Server (stylized AI topology stills, spec 120) — also consumed by mcp-servers/image-style-mcp/ (spec 121's federated Stage B, on the johns-risk/viz member). Endpoint of your own already-running ComfyUI instance — required, no default is assumed since comfyui-mcp's own built-in defaults (8000 for ComfyUI Desktop, 8188 for a manual install) are easy to mix up. See specs/120-comfyui-topology-viz/quickstart.md for WSL2 reachability notes.",
      "classification": "private",
      "valueType": "url",
      "required": "always",
      "condition": null,
      "example": "http://127.0.0.1:8000",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#comfyui-mcp,topology-diagram-mcp,image-style-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "worldlabs-marble": [
    {
      "key": "WLT_API_KEY",
      "label": "Wlt Api Key",
      "help": "World Labs Marble MCP Server (AI-augmented fantastical topology worlds, spec 122). API key from https://platform.worldlabs.ai/api-keys — requires a funded account (https://platform.worldlabs.ai/billing). Only needed for the credit-spending generate step; the free preview mode (specs/122-worldlabs-topology-viz) needs no credential at all. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/worldlabs-marble-mcp/server.py#L87",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#worldlabs-marble-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "chrome-devtools": [],
  "computer-use": [],
  "tts": [
    {
      "key": "TTS_OUTPUT_DIR",
      "label": "Tts Output Dir",
      "help": "Private generated-audio directory owned by this installation.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/tts-mcp/server.py#L39",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "mcp-servers/tts-mcp/server.py",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    },
    {
      "key": "TTS_DEFAULT_VOICE",
      "label": "Tts Default Voice",
      "help": "Voice identifier; default en-US-GuyNeural.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/tts-mcp/server.py#L42",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "mcp-servers/tts-mcp/server.py",
          "checkedAt": "2026-10-17",
          "note": "Declared setting/consumer; no installed configuration read."
        }
      ]
    }
  ],
  "tavus-pal": [],
  "twitter": [
    {
      "key": "TWITTER_ACCESS_SECRET",
      "label": "Twitter Access Secret",
      "help": "TWITTER_ACCESS_SECRET is consumed by the selected Twitter/X registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twitter-mcp/server.py#L392",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twitter-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWITTER_ACCESS_TOKEN",
      "label": "Twitter Access Token",
      "help": "TWITTER_ACCESS_TOKEN is consumed by the selected Twitter/X registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twitter-mcp/server.py#L391",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twitter-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWITTER_API_KEY",
      "label": "Twitter Api Key",
      "help": "Twitter/X Integration (OAuth 1.0a for posting, OAuth 2.0 for reading) Get these from https://developer.twitter.com/en/portal/projects-and-apps",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twitter-mcp/server.py#L389",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twitter-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWITTER_API_SECRET",
      "label": "Twitter Api Secret",
      "help": "TWITTER_API_SECRET is consumed by the selected Twitter/X registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twitter-mcp/server.py#L390",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twitter-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWITTER_HEARTBEAT_ENABLED",
      "label": "Twitter Heartbeat Enabled",
      "help": "Twitter Heartbeat settings",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twitter-mcp/server.py#L436",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twitter-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWITTER_HEARTBEAT_INTERVAL",
      "label": "Twitter Heartbeat Interval",
      "help": "TWITTER_HEARTBEAT_INTERVAL is consumed by the selected Twitter/X registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twitter-mcp/server.py#L437",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twitter-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "twilio": [
    {
      "key": "TWILIO_ACCOUNT_SID",
      "label": "Twilio Account Sid",
      "help": "Twilio Voice MCP Server (6 tools: emergency calls, on-demand calls, inbound conversations) Bidirectional voice calling for emergency alerts, status updates, and voice commands Get credentials from https://console.twilio.com (Account → API Keys) The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twilio-voice-mcp/alert_triggers.py#L23",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twilio-mcp,twilio-voice-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWILIO_API_KEY_SID",
      "label": "Twilio Api Key Sid",
      "help": "TWILIO_API_KEY_SID is consumed by the selected Twilio registration. Leave unset only when using the documented native/default configuration. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twilio-voice-mcp/server.py#L51",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twilio-mcp,twilio-voice-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWILIO_API_SECRET",
      "label": "Twilio Api Secret",
      "help": "TWILIO_API_SECRET is consumed by the selected Twilio registration. Leave unset only when using the documented native/default configuration. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twilio-voice-mcp/server.py#L52",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twilio-mcp,twilio-voice-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWILIO_PHONE_NUMBER",
      "label": "Twilio Phone Number",
      "help": "TWILIO_PHONE_NUMBER is consumed by the selected Twilio registration. Leave unset only when using the documented native/default configuration. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twilio-voice-mcp/alert_triggers.py#L25",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twilio-mcp,twilio-voice-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TWILIO_WEBHOOK_URL",
      "label": "Twilio Webhook Url",
      "help": "TWILIO_WEBHOOK_URL is consumed by the selected Twilio registration. Leave unset only when using the documented native/default configuration. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://your-domain/webhooks/twilio/voice",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/twilio-voice-mcp/server.py#L54",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#twilio-mcp,twilio-voice-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "zoom-rtms": [
    {
      "key": "N2N_ZOOM_CHANNEL_HOST",
      "label": "N2N Zoom Channel Host",
      "help": "Loopback-only channel between zoom-rtms-mcp and the Border federation daemon (bgp/federation/zoom_channel.py). Both must agree on the same port/secret.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "127.0.0.1",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zoom-rtms-mcp/zoom_channel_client.py#L19",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "N2N_ZOOM_CHANNEL_PORT",
      "label": "N2N Zoom Channel Port",
      "help": "NetClaw for Zoom — Meeting Intelligence (spec 118). Realtime Media Streams (not a Meeting SDK bot) feed a deterministic extractor that recognizes network-investigation questions and routes them into the existing Border/NCFED path via a new loopback-only bgp/federation/zoom_channel.py channel. Feeds the Zoom App side panel (avatar + live status) with an optional Layers API camera overlay. No new device-write approval mechanism — reuses NetClaw's existing gate unchanged. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zoom-rtms-mcp/zoom_channel_client.py#L20",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "N2N_ZOOM_CHANNEL_SECRET",
      "label": "N2N Zoom Channel Secret",
      "help": "NetClaw for Zoom — Meeting Intelligence (spec 118). Realtime Media Streams (not a Meeting SDK bot) feed a deterministic extractor that recognizes network-investigation questions and routes them into the existing Border/NCFED path via a new loopback-only bgp/federation/zoom_channel.py channel. Feeds the Zoom App side panel (avatar + live status) with an optional Layers API camera overlay. No new device-write approval mechanism — reuses NetClaw's existing gate unchanged. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zoom-rtms-mcp/zoom_channel_client.py#L21",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZOOM_ACCOUNT_ID",
      "label": "Zoom Account Id",
      "help": "NetClaw for Zoom — Meeting Intelligence (spec 118). Realtime Media Streams (not a Meeting SDK bot) feed a deterministic extractor that recognizes network-investigation questions and routes them into the existing Border/NCFED path via a new loopback-only bgp/federation/zoom_channel.py channel. Feeds the Zoom App side panel (avatar + live status) with an optional Layers API camera overlay. No new device-write approval mechanism — reuses NetClaw's existing gate unchanged.",
      "classification": "private",
      "valueType": "string",
      "required": "always",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZOOM_CLIENT_ID",
      "label": "Zoom Client Id",
      "help": "--- NetClaw for Zoom: Meeting Intelligence (spec 118) --- Zoom Marketplace app credentials (General App, User-managed OAuth) — see docs/ZOOM-MEETING-INTELLIGENCE.md for setup. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zoom-rtms-mcp/panel_auth.py#L17",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZOOM_CLIENT_SECRET",
      "label": "Zoom Client Secret",
      "help": "NetClaw for Zoom — Meeting Intelligence (spec 118). Realtime Media Streams (not a Meeting SDK bot) feed a deterministic extractor that recognizes network-investigation questions and routes them into the existing Border/NCFED path via a new loopback-only bgp/federation/zoom_channel.py channel. Feeds the Zoom App side panel (avatar + live status) with an optional Layers API camera overlay. No new device-write approval mechanism — reuses NetClaw's existing gate unchanged. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zoom-rtms-mcp/panel_auth.py#L16",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZOOM_MEETING_MCP_CREDENTIAL",
      "label": "Zoom Meeting Mcp Credential",
      "help": "Official Zoom Meetings MCP credential (historical meeting search/assets) — exact shape TBD pending confirmation against Zoom's own connector setup flow.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZOOM_PANEL_FEED_PORT",
      "label": "Zoom Panel Feed Port",
      "help": "ZOOM_PANEL_FEED_PORT is consumed by the selected Zoom Meeting Intelligence registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "8900",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zoom-rtms-mcp/panel_feed.py#L31",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZOOM_RTMS_WEBHOOK_PORT",
      "label": "Zoom Rtms Webhook Port",
      "help": "zoom-rtms-mcp's own local ports (not exposed publicly by NetClaw itself — front with your own HTTPS ingress, e.g. a tunnel or reverse proxy).",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "8899",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zoom-rtms-mcp/webhook.py#L25",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "ZOOM_RTMS_WEBHOOK_SECRET",
      "label": "Zoom Rtms Webhook Secret",
      "help": "Event Subscription secret token — verifies the RTMS webhook handshake. The consumer has an explicit fallback; Configure later preserves that fallback.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/zoom-rtms-mcp/webhook.py#L24",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#zoom-rtms-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "gait": [
    {
      "key": "GAIT_MCP_SCRIPT",
      "label": "Gait Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. GAIT uses local Git — no external credentials needed. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#gait-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "GAIT_VENV",
      "label": "Gait Venv",
      "help": "Generated for this selected installation by the scoped adapter. Optional existing GAIT launcher override for a selected runtime home. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "/path/to/selected-home/gait-venv",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "scripts/gait-stdio.py#L18",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#gait-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "mempalace": [
    {
      "key": "MCP_CALL",
      "label": "Mcp Call",
      "help": "Generated for this selected installation by the scoped adapter. Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [
        "catc",
        "cisco-psirt",
        "f5",
        "nvd-cve",
        "subnet-calc"
      ],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "MEMPALACE_MCP_SCRIPT",
      "label": "Mempalace Mcp Script",
      "help": "Generated for this selected installation by the scoped adapter. MemPalace AI Memory (19 tools: palace read/write, knowledge graph, navigation, agent diary) Persistent, structured, local-only memory across sessions — no API keys required Source: https://github.com/milla-jovovich/mempalace Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "./mcp-servers/mempalace/mempalace/mcp_server.py",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "memory-mcp": [
    {
      "key": "MEMORY_DATA_DIR",
      "label": "Memory Data Dir",
      "help": "MEMORY_DATA_DIR is consumed by the selected Memory MCP registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/memory-mcp/memory_mcp_server.py#L57",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#memory-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "document": [
    {
      "key": "DOCUMENT_AUDIT_LOG",
      "label": "Document Audit Log",
      "help": "GAIT audit trail path. Defaults under ~/.openclaw/gait/",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/document-mcp/envelope.py#L174",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#document-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "DOCUMENT_MAX_BLOCKS",
      "label": "Document Max Blocks",
      "help": "Blocks per Word document before truncation. Default 5000.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#document-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "DOCUMENT_MAX_ROWS",
      "label": "Document Max Rows",
      "help": "Data rows per worksheet before truncation. Default 50000. When a bound is applied it is written INTO the document, not only into the tool response.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#document-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "DOCUMENT_MAX_SLIDES",
      "label": "Document Max Slides",
      "help": "Slides per deck before truncation. Default 200.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#document-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "DOCUMENT_MCP_CMD",
      "label": "Document Mcp Cmd",
      "help": "Generated for this selected installation by the scoped adapter. The four libraries it needs (python-docx, openpyxl, python-pptx, PyMuPDF) are already installed by rag-mcp (feature 062), which READS these formats. This server WRITES them. ───────────────────────────────────────────────────────────────────── Command the two document skills invoke Installer-managed path/binding; shown for review, not a credential prompt.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "generated",
      "provenance": [
        {
          "source": "config/openclaw.json#document-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "DOCUMENT_OUTPUT_DIR",
      "label": "Document Output Dir",
      "help": "Where generated documents land. Defaults to workspace/output/document-mcp/ — persistent, timestamped, and never overwritten, so a regenerated report cannot replace one already attached to a ticket. There is deliberately no fallback to a temp directory: an unwritable path is reported as a failure.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/document-mcp/output.py#L34",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#document-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "rag-mcp": [
    {
      "key": "RAG_CRAWL_MAX_PAGES",
      "label": "Rag Crawl Max Pages",
      "help": "Max same-domain pages listed in a depth-1 URL crawl preview",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "30",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_DATA_DIR",
      "label": "Rag Data Dir",
      "help": "============================================================ RAG Knowledge Base MCP Server (rag-mcp) — Feature 062 Fully offline document knowledge base. No credentials needed. ============================================================ Persistent data directory (ChromaDB + SQLite + BM25 + retained sources)",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "~/.openclaw/rag",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/rag-mcp/config.py#L32",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_EMBEDDING_MODEL",
      "label": "Rag Embedding Model",
      "help": "Local embedding model (downloaded once at install; upgrade: BAAI/bge-base-en-v1.5)",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "BAAI/bge-small-en-v1.5",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/rag-mcp/config.py#L34",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_MAX_DOC_MB",
      "label": "Rag Max Doc Mb",
      "help": "Per-document ingestion soft caps (whichever is hit first)",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "100",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_MAX_DOC_PAGES",
      "label": "Rag Max Doc Pages",
      "help": "Local retrieval and indexing configuration. Defaults apply to unset optional variables.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "1000",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_MAX_ROUNDS",
      "label": "Rag Max Rounds",
      "help": "Hard cap on retrieval rounds per sub-query (initial + refinements)",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "3",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_RELEVANCE_FLOOR",
      "label": "Rag Relevance Floor",
      "help": "Results scoring below this floor are flagged low_confidence (never dropped)",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_RERANKER_MODEL",
      "label": "Rag Reranker Model",
      "help": "Local cross-encoder reranker (upgrade: BAAI/bge-reranker-base)",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "cross-encoder/ms-marco-MiniLM-L-6-v2",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_RERANK_ENABLED",
      "label": "Rag Rerank Enabled",
      "help": "Set false on low-resource hosts to skip reranking (hybrid fusion only)",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "true",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "RAG_SNAPSHOT_WARN_DAYS",
      "label": "Rag Snapshot Warn Days",
      "help": "Snapshots older than this many days are flagged stale (warn only, never auto-deleted)",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "90",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#rag-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "ollama": [
    {
      "key": "OLLAMA_BASE_URL",
      "label": "Ollama Base Url",
      "help": "OLLAMA_BASE_URL is consumed by the selected Ollama Domain Experts registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/ollama-mcp/server.py#L49",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#ollama-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "OLLAMA_TIMEOUT",
      "label": "Ollama Timeout",
      "help": "OLLAMA_TIMEOUT is consumed by the selected Ollama Domain Experts registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/ollama-mcp/server.py#L50",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#ollama-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "jev": [
    {
      "key": "JEV_API_KEY",
      "label": "Jev Api Key",
      "help": "Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/jev-audit/common.py#L23",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_BASE_URL",
      "label": "Jev Base Url",
      "help": "Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "https://api.typesafe.ai",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_CASE_LIMIT_USD",
      "label": "Jev Case Limit Usd",
      "help": "Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "0.25",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_COMPATIBLE_API_KEY",
      "label": "Jev Compatible Api Key",
      "help": "Compatible services never inherit hosted credentials. Bind their own optional key:",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_COMPATIBLE_KEY_ENDPOINT",
      "label": "Jev Compatible Key Endpoint",
      "help": "Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_DAILY_LIMIT_USD",
      "label": "Jev Daily Limit Usd",
      "help": "Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "5",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_DATA_DIR",
      "label": "Jev Data Dir",
      "help": "Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration.",
      "classification": "private",
      "valueType": "path",
      "required": "optional",
      "condition": null,
      "example": "~/.openclaw/jev",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/jev-settings.py#L83",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_ENABLED",
      "label": "Jev Enabled",
      "help": "Optional Science Officer. Use python3 scripts/jev-settings.py setup for provider configuration.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "false",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_INPUT_PRICE_PER_MILLION",
      "label": "Jev Input Price Per Million",
      "help": "JEV_INPUT_PRICE_PER_MILLION is consumed by the selected Jev Science Officer registration. Leave unset only when using the documented native/default configuration.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_MODEL",
      "label": "Jev Model",
      "help": "A compatible endpoint may be a base URL or full /v1/systemone endpoint.",
      "classification": "public",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "jev-1.13.0",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_TASK_ID",
      "label": "Jev Task Id",
      "help": "Trusted runtime task identity; unset uses one conservative shared budget bucket.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "unscoped",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "JEV_TIMEOUT_SECONDS",
      "label": "Jev Timeout Seconds",
      "help": "Custom endpoints require an explicit input price (0 is valid for local models).",
      "classification": "public",
      "valueType": "integer",
      "required": "optional",
      "condition": null,
      "example": "5",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "TYPESAFE_API_KEY",
      "label": "Typesafe Api Key",
      "help": "Jev Science Officer (spec 125): optional; an API key alone never enables calls. Configure interactively: python3 scripts/jev-settings.py setup Credentials use TYPESAFE_API_KEY first, with JEV_API_KEY as an alias.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "scripts/jev-audit/common.py#L23",
          "checkedAt": "2026-10-17",
          "note": "Actual environment consumer."
        },
        {
          "source": "config/openclaw.json#jev-mcp",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "humanrail": [
    {
      "key": "HUMANRAIL_API_KEY",
      "label": "Humanrail Api Key",
      "help": "HUMANRAIL_API_KEY is consumed by the selected HumanRail registration. Leave unset only when using the documented native/default configuration.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    },
    {
      "key": "HUMANRAIL_MCP_URL",
      "label": "Humanrail Mcp Url",
      "help": "HUMANRAIL_MCP_URL is consumed by the selected HumanRail registration. Leave unset only when using the documented native/default configuration.",
      "classification": "private",
      "valueType": "url",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "config/openclaw.json#",
          "checkedAt": "2026-10-17",
          "note": "Exact selected registration substitutions."
        },
        {
          "source": "ui/netclaw-visual/env-map.js",
          "checkedAt": "2026-10-17",
          "note": "Existing card field inventory; requirement and classification reconciled into this catalog."
        }
      ]
    }
  ],
  "convergence-read": [
    {
      "key": "CONVERGENCE_ENABLED",
      "label": "Enabled",
      "help": "Explicitly enable this optional connector; default false.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/convergence-read-mcp/client.py",
          "checkedAt": "2026-10-31",
          "note": "Fixed server-side connector configuration; required when enabled."
        }
      ]
    },
    {
      "key": "CONVERGENCE_API_URL",
      "label": "Api Url",
      "help": "Verified HTTPS origin, or explicit literal loopback HTTP for a local trial.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/convergence-read-mcp/client.py",
          "checkedAt": "2026-10-31",
          "note": "Fixed server-side connector configuration; required when enabled."
        }
      ]
    },
    {
      "key": "CONVERGENCE_API_TOKEN",
      "label": "Api Token",
      "help": "Private API viewer credential restricted to this site.",
      "classification": "secret",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/convergence-read-mcp/client.py",
          "checkedAt": "2026-10-31",
          "note": "Fixed server-side connector configuration; required when enabled."
        }
      ]
    },
    {
      "key": "CONVERGENCE_SITE",
      "label": "Site",
      "help": "One fixed site identifier.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/convergence-read-mcp/client.py",
          "checkedAt": "2026-10-31",
          "note": "Fixed server-side connector configuration; required when enabled."
        }
      ]
    },
    {
      "key": "CONVERGENCE_EXPORTERS",
      "label": "Exporters",
      "help": "Comma-separated allowed exporter IP addresses.",
      "classification": "private",
      "valueType": "string",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/convergence-read-mcp/client.py",
          "checkedAt": "2026-10-31",
          "note": "Fixed server-side connector configuration; required when enabled."
        }
      ]
    },
    {
      "key": "CONVERGENCE_ALLOW_LOOPBACK_HTTP",
      "label": "Allow Loopback Http",
      "help": "Explicit local-development HTTP opt-in; default false.",
      "classification": "public",
      "valueType": "boolean",
      "required": "optional",
      "condition": null,
      "example": "",
      "sharedWith": [],
      "input": "user",
      "provenance": [
        {
          "source": "mcp-servers/convergence-read-mcp/client.py",
          "checkedAt": "2026-10-31",
          "note": "Fixed server-side connector configuration; required when enabled."
        }
      ]
    }
  ]
};
