import express from 'express';
import { WebSocketServer } from 'ws';
import http from 'http';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const app = express();

app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

const SKILLS_DIR = path.join(ROOT, 'workspace/skills');
const TESTBED_FILE = path.join(ROOT, 'testbed/testbed.yaml');
const CONFIG_FILE = path.join(ROOT, 'config/openclaw.json');
const IDENTITY_FILE = path.join(ROOT, 'IDENTITY.md');
const SOUL_FILE = path.join(ROOT, 'SOUL.md');

const INTEGRATION_CATALOG = [
  { id: 'pyats', name: 'pyATS', category: 'Device Automation', prefixes: ['pyats-'], color: '#4cc9f0', transport: 'stdio', toolEstimate: 120, description: 'CLI-first device automation, health checks, routing, topology, and controlled change workflows.' },
  { id: 'aci', name: 'Cisco ACI', category: 'Fabric Control', prefixes: ['aci-'], color: '#ff5d73', transport: 'stdio', toolEstimate: 20, description: 'APIC-backed policy audit and guarded ACI change delivery.' },
  { id: 'ise', name: 'Cisco ISE', category: 'Security', prefixes: ['ise-'], color: '#f94144', transport: 'stdio', toolEstimate: 16, description: 'Identity, posture, and incident-response workflows for endpoints.' },
  { id: 'f5', name: 'F5 BIG-IP', category: 'Load Balancing', prefixes: ['f5-', 'pyats-f5-'], color: '#ff8c42', transport: 'stdio', toolEstimate: 110, description: 'Virtual server, pool, platform, and config-management operations.' },
  { id: 'junos', name: 'JunOS', category: 'Device Automation', prefixes: ['junos-', 'pyats-junos-'], color: '#7bd389', transport: 'stdio', toolEstimate: 60, description: 'Juniper-oriented operational coverage through pyATS and JunOS skills.' },
  { id: 'asa', name: 'Cisco ASA', category: 'Security', prefixes: ['pyats-asa-'], color: '#ef476f', transport: 'stdio', toolEstimate: 20, description: 'Firewall session, failover, and dataplane health views.' },
  { id: 'netbox', name: 'NetBox', category: 'Source of Truth', prefixes: ['netbox-'], color: '#00bbf9', transport: 'stdio', toolEstimate: 12, description: 'Intent reconciliation between live device state and documented truth.' },
  { id: 'nautobot', name: 'Nautobot', category: 'Source of Truth', prefixes: ['nautobot-'], color: '#00f5d4', transport: 'stdio', toolEstimate: 8, description: 'Alternative SoT and IPAM access pattern.' },
  { id: 'infrahub', name: 'Infrahub', category: 'Source of Truth', prefixes: ['infrahub-'], color: '#06d6a0', transport: 'stdio', toolEstimate: 10, description: 'Schema-driven SoT with branch-isolated writes submitted as Proposed Changes.' },
  { id: 'infoblox', name: 'Infoblox', category: 'Source of Truth', prefixes: ['infoblox-'], color: '#73d2de', transport: 'stdio', toolEstimate: 10, description: 'DNS, DHCP, and IPAM operations.' },
  { id: 'servicenow', name: 'ServiceNow', category: 'Governance', prefixes: ['servicenow-'], color: '#ffd166', transport: 'stdio', toolEstimate: 12, description: 'Change gating and ITSM workflow integration.' },
  { id: 'gait', name: 'GAIT', category: 'Governance', prefixes: ['gait-'], color: '#f4a261', transport: 'stdio', toolEstimate: 9, description: 'Git-backed audit history and turn tracking.' },
  { id: 'github', name: 'GitHub', category: 'Governance', prefixes: ['github-'], color: '#cdb4db', transport: 'docker', toolEstimate: 12, description: 'Code search, issues, and PR-aware ops.' },
  { id: 'gitlab', name: 'GitLab', category: 'Governance', prefixes: ['gitlab-'], color: '#e24329', transport: 'npx', toolEstimate: 98, description: 'GitLab DevOps: issues, merge requests, pipelines, repos, wikis, labels, milestones, releases.' },
  { id: 'jenkins', name: 'Jenkins', category: 'Governance', prefixes: ['jenkins-'], color: '#d33833', transport: 'http', toolEstimate: 16, description: 'Jenkins CI/CD: job monitoring, build triggering, log analysis, SCM tracking, pipeline runs.' },
  { id: 'atlassian', name: 'Atlassian', category: 'Governance', prefixes: ['atlassian-'], color: '#0052cc', transport: 'uvx', toolEstimate: 72, description: 'Atlassian ITSM: Jira issues, transitions, comments, projects, links; Confluence pages, comments, spaces.' },
  { id: 'meraki', name: 'Meraki', category: 'Network Platforms', prefixes: ['meraki-'], color: '#9b5de5', transport: 'stdio', toolEstimate: 804, description: 'Dashboard inventory, wireless, switching, and security appliance control.' },
  { id: 'sdwan', name: 'SD-WAN', category: 'Network Platforms', prefixes: ['sdwan-'], color: '#8d99ae', transport: 'stdio', toolEstimate: 12, description: 'vManage monitoring and WAN-state workflows.' },
  { id: 'nso', name: 'Cisco NSO', category: 'Network Platforms', prefixes: ['nso-'], color: '#4361ee', transport: 'stdio', toolEstimate: 18, description: 'Service and device orchestration.' },
  { id: 'itential', name: 'Itential', category: 'Network Platforms', prefixes: ['itential-'], color: '#4895ef', transport: 'stdio', toolEstimate: 65, description: 'Automation platform workflows and orchestration hooks.' },
  { id: 'evpn', name: 'EVPN/VXLAN', category: 'Network Platforms', prefixes: ['evpn-'], color: '#3a86ff', transport: 'stdio', toolEstimate: 14, description: 'Overlay-underlay correlation and fabric troubleshooting.' },
  { id: 'protocol', name: 'Protocol Ops', category: 'Network Platforms', prefixes: ['protocol-'], color: '#577590', transport: 'stdio', toolEstimate: 10, description: 'Intent validation and active protocol participation.' },
  { id: 'catc', name: 'Catalyst Center', category: 'Controller Platforms', prefixes: ['catc-'], color: '#118ab2', transport: 'stdio', toolEstimate: 24, description: 'Controller inventory, client ops, and troubleshooting.' },
  { id: 'arista', name: 'Arista CVP', category: 'Controller Platforms', prefixes: ['arista-'], color: '#06b6d4', transport: 'stdio', toolEstimate: 8, description: 'CloudVision-backed workflow surface.' },
  { id: 'fortimanager', name: 'FortiManager', category: 'Security', prefixes: ['fortimanager-'], color: '#d00000', transport: 'stdio', toolEstimate: 10, description: 'Firewall governance and package review.' },
  { id: 'paloalto', name: 'Palo Alto Panorama', category: 'Security', prefixes: ['paloalto-'], color: '#e76f51', transport: 'stdio', toolEstimate: 10, description: 'Panorama-managed firewall policy lookup.' },
  { id: 'fmc', name: 'Cisco FMC', category: 'Security', prefixes: ['fmc-'], color: '#bc4749', transport: 'http', toolEstimate: 8, description: 'Cisco Secure Firewall policy search.' },
  { id: 'nmap', name: 'Nmap', category: 'Security', prefixes: ['nmap-'], color: '#ff006e', transport: 'stdio', toolEstimate: 18, description: 'Scoped scanning and service detection.' },
  { id: 'nvd', name: 'NVD / CVE', category: 'Security', prefixes: ['nvd-'], color: '#fb5607', transport: 'stdio', toolEstimate: 4, description: 'Vulnerability context matched to operational state.' },
  { id: 'grafana', name: 'Grafana', category: 'Observability', prefixes: ['grafana-', 'flow-'], color: '#f8961e', transport: 'http', toolEstimate: 75, description: 'Dashboards, alerts, incidents, and derived telemetry views.' },
  { id: 'prometheus', name: 'Prometheus', category: 'Observability', prefixes: ['prometheus-'], color: '#faa307', transport: 'stdio', toolEstimate: 6, description: 'Direct metrics and PromQL access.' },
  { id: 'thousandeyes', name: 'ThousandEyes', category: 'Observability', prefixes: ['te-'], color: '#ffb703', transport: 'http', toolEstimate: 29, description: 'Synthetic and path-aware external monitoring.' },
  { id: 'kubeshark', name: 'Kubeshark', category: 'Observability', prefixes: ['kubeshark-'], color: '#ffcb77', transport: 'http', toolEstimate: 6, description: 'Kubernetes packet and flow visibility.' },
  { id: 'gtrace', name: 'gtrace', category: 'Observability', prefixes: ['gtrace-'], color: '#bde0fe', transport: 'stdio', toolEstimate: 6, description: 'Path tracing and IP enrichment.' },
  { id: 'suzieq', name: 'SuzieQ', category: 'Observability', prefixes: ['suzieq-'], color: '#a8dadc', transport: 'stdio', toolEstimate: 5, description: 'Network state queries, assertions, summaries, and path tracing.' },
  { id: 'aws', name: 'AWS', category: 'Cloud', prefixes: ['aws-'], color: '#f77f00', transport: 'http', toolEstimate: 55, description: 'Networking, monitoring, security, cost, and diagram generation in AWS.' },
  { id: 'gcp', name: 'GCP', category: 'Cloud', prefixes: ['gcp-'], color: '#f3722c', transport: 'http', toolEstimate: 40, description: 'Compute, monitoring, and logging coverage for GCP.' },
  { id: 'azure-network', name: 'Azure Network', category: 'Cloud', prefixes: ['azure-'], color: '#0078d4', transport: 'stdio', toolEstimate: 19, description: 'Azure networking: VNets, NSGs, ExpressRoute, VPN, Firewall, LB, DNS.' },
  { id: 'cml', name: 'Cisco CML', category: 'Labs', prefixes: ['cml-'], color: '#90be6d', transport: 'stdio', toolEstimate: 24, description: 'Lab lifecycle, node operations, and packet capture.' },
  { id: 'clab', name: 'Containerlab', category: 'Labs', prefixes: ['clab-'], color: '#52b788', transport: 'stdio', toolEstimate: 10, description: 'Containerized lab operations.' },
  { id: 'radkit', name: 'RADKit', category: 'Remote Access', prefixes: ['radkit-'], color: '#48cae4', transport: 'stdio', toolEstimate: 10, description: 'Cloud-relayed remote reach into on-prem devices.' },
  { id: 'msgraph', name: 'Microsoft Graph', category: 'Collaboration', prefixes: ['msgraph-'], color: '#5e60ce', transport: 'npx', toolEstimate: 16, description: 'Files, Teams, and Visio generation from ops workflows.' },
  { id: 'slack', name: 'Slack', category: 'Collaboration', prefixes: ['slack-'], color: '#b5179e', transport: 'stdio', toolEstimate: 10, description: 'Alerting, incident workflow, reporting, and voice interaction.' },
  { id: 'webex', name: 'Cisco WebEx', category: 'Collaboration', prefixes: ['webex-'], color: '#1a7aba', transport: 'stdio', toolEstimate: 10, description: 'Bidirectional WebEx messaging: Adaptive Card alerts, incident workflow, reports, and voice interaction via @jimiford/webex plugin.' },
  { id: 'drawio', name: 'draw.io', category: 'Visualization', prefixes: ['drawio-'], color: '#f72585', transport: 'npx', toolEstimate: 4, description: 'Diagram generation for network state and layout.' },
  { id: 'uml', name: 'UML / Kroki', category: 'Visualization', prefixes: ['uml-'], color: '#ff4d6d', transport: 'stdio', toolEstimate: 2, description: 'Multi-engine diagram rendering.' },
  { id: 'markmap', name: 'Markmap', category: 'Visualization', prefixes: ['markmap-'], color: '#ff70a6', transport: 'stdio', toolEstimate: 2, description: 'Interactive operational knowledge maps.' },
  { id: 'wiki', name: 'Reference', category: 'Reference', prefixes: ['wikipedia-', 'rfc-', 'subnet-', 'packet-analysis'], color: '#adb5bd', transport: 'mixed', toolEstimate: 12, description: 'RFCs, background research, subnet math, and packet analysis helpers.' },
  { id: 'aap', name: 'Ansible AAP', category: 'Automation', prefixes: ['aap-'], color: '#ee0000', transport: 'stdio', toolEstimate: 66, description: 'Red Hat Ansible Automation Platform — inventories, job templates, projects, EDA, ansible-lint, and Galaxy content.' },
  { id: 'fwrule', name: 'FW Rule Analyzer', category: 'Security', prefixes: ['fwrule-'], color: '#d62828', transport: 'stdio', toolEstimate: 3, description: 'Multi-vendor firewall rule overlap, shadowing, conflict, and duplication analysis across 9 platforms.' },
  { id: 'batfish', name: 'Batfish', category: 'Analysis', prefixes: ['batfish-'], color: '#2ec4b6', transport: 'stdio', toolEstimate: 8, description: 'Offline network configuration analysis — validation, reachability, ACL trace, differential analysis, compliance.' },
  { id: 'gnmi', name: 'gNMI Telemetry', category: 'Device Automation', prefixes: ['gnmi-', 'gnmi_'], color: '#00c49a', transport: 'stdio', toolEstimate: 10, description: 'gNMI streaming telemetry — Get, Set (ITSM-gated), Subscribe, Capabilities, YANG browsing. Cisco IOS-XR, Juniper, Arista, Nokia SR OS.' },
  { id: 'canvas-viz', name: 'Canvas A2UI', category: 'Visualization', prefixes: ['canvas-network-viz', 'canvas-'], color: '#7c3aed', transport: 'none', toolEstimate: 0, description: 'Inline Canvas/A2UI network visualizations — topology maps, dashboards, alerts, change timelines, diffs, path traces, and health scorecards rendered in chat.' },
  { id: 'token-tracker', name: 'Token Tracker', category: 'Observability', prefixes: ['token-'], color: '#10b981', transport: 'none', toolEstimate: 0, description: 'Real-time token counting, cost tracking, TOON serialization savings, and per-tool usage breakdown. Every interaction shows its cost.' },
  { id: 'gns3', name: 'GNS3', category: 'Labs', prefixes: ['gns3-'], color: '#2ecc71', transport: 'stdio', toolEstimate: 23, description: 'GNS3 network simulation — projects, nodes, links, templates, computes, snapshots, and packet capture for lab environments.' },
  { id: 'prisma-sdwan', name: 'Prisma SD-WAN', category: 'Network Platforms', prefixes: ['prisma-sdwan-'], color: '#fa582d', transport: 'stdio', toolEstimate: 16, description: 'Palo Alto Networks Prisma SD-WAN — sites, elements, topology, health, alarms, interfaces, routing, policies, and applications.' },
  { id: 'telemetry-receivers', name: 'Telemetry Receivers', category: 'Observability', prefixes: ['syslog-', 'snmptrap-', 'ipfix-', 'telemetry-'], color: '#9b59b6', transport: 'stdio', toolEstimate: 12, description: 'Real-time telemetry ingestion — syslog, SNMP traps, and IPFIX/NetFlow receivers for event correlation and alerting.' },
  { id: 'config-archive', name: 'Config Archive', category: 'Governance', prefixes: ['config-archive-'], color: '#34495e', transport: 'stdio', toolEstimate: 4, description: 'Configuration archive compliance — backup verification, drift detection, and config restore workflows.' },
  { id: 'datadog', name: 'Datadog', category: 'Observability', prefixes: ['datadog-'], color: '#632ca6', transport: 'http', toolEstimate: 16, description: 'Full observability stack — logs, metrics, incidents, APM, dashboards with error_tracking, feature_flags, dbm, security, llm_observability toolsets.' },
  { id: 'pagerduty', name: 'PagerDuty', category: 'Incident Management', prefixes: ['pagerduty-'], color: '#06ac38', transport: 'stdio', toolEstimate: 70, description: 'Incident management — incidents, on-call schedules, services, escalation policies, event orchestration with read/write capabilities.' },
  { id: 'splunk', name: 'Splunk', category: 'Observability', prefixes: ['splunk-'], color: '#65a637', transport: 'stdio', toolEstimate: 30, description: 'Log analytics and SIEM — SPL search, indexes, saved searches, alerts, dashboards for security and operations.' },
  { id: 'terraform', name: 'Terraform Cloud', category: 'Infrastructure', prefixes: ['terraform-'], color: '#7b42bc', transport: 'http', toolEstimate: 40, description: 'Infrastructure as Code — workspaces, runs, state management, variables, and policy compliance for Terraform Cloud/Enterprise.' },
  { id: 'vault', name: 'HashiCorp Vault', category: 'Security', prefixes: ['vault-'], color: '#000000', transport: 'http', toolEstimate: 35, description: 'Secrets management — KV secrets, PKI certificates, transit encryption, authentication methods, and audit logging.' },
  { id: 'zscaler', name: 'Zscaler', category: 'Security', prefixes: ['zscaler-'], color: '#0090d4', transport: 'http', toolEstimate: 300, description: 'Zero Trust security — ZIA (SWG), ZPA (ZTNA), ZDX (DEM), identity management, and security insights.' },
  { id: 'cloudflare', name: 'Cloudflare', category: 'Edge Platform', prefixes: ['cloudflare-'], color: '#f48120', transport: 'http', toolEstimate: 50, description: 'Edge platform — DNS analytics, WAF/DDoS security, Zero Trust access, traffic analytics, and Workers compute.' },
  { id: 'checkpoint', name: 'Check Point', category: 'Security', prefixes: ['checkpoint-', 'chkp-'], color: '#e21d38', transport: 'stdio', toolEstimate: 60, description: 'Enterprise security — 15 MCPs for policy management, threat intelligence, gateway diagnostics, SASE, threat prevention, malware analysis, HTTPS inspection, and exposure management.' },
  { id: 'claroty', name: 'Claroty xDome', category: 'Security', prefixes: ['claroty-'], color: '#00a3a3', transport: 'stdio', toolEstimate: 21, description: 'OT / IoT / IoMT visibility — asset discovery, Purdue Model classification, alert and vulnerability triage, communication-map topology, all writes ITSM-gated.' },
  { id: 'threejs-viz', name: 'Three.js Network Viz', category: 'Visualization', prefixes: ['threejs-network-viz'], color: '#049ef4', transport: 'stdio', toolEstimate: 3, description: 'Browser-based 3D network topology visualization — single self-contained HTML file, no desktop app/GPU/server required. Optional real-3D-model stencil mode via the vendored sketchfab-mcp-server (3 tools: search, model-details/license-verification, download), filtered to CC0-licensed models only.' },
];

// ── ENV variable mapping per integration ────────────────────────────
// Maps integration IDs to their relevant .env keys and testbed fields.
const ENV_MAP = {
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
  fortimanager: {
    env: ['FORTIMANAGER_URL', 'FORTIMANAGER_USERNAME', 'FORTIMANAGER_PASSWORD', 'FORTIMANAGER_MCP_CMD'],
    files: [],
    notes: 'FortiManager API credentials.',
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
};

// ── Env file locations (OpenClaw .env is the real source of truth) ──
const OPENCLAW_ENV = path.join(process.env.HOME || '/root', '.openclaw', '.env');
const ROOT_ENV = path.join(ROOT, '.env');

// Ordered list — first file wins per key, but we merge all
const ENV_FILES = [OPENCLAW_ENV, ROOT_ENV];

function parseOneEnvFile(filePath) {
  const text = readText(filePath);
  if (!text) return {};
  const vars = {};
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIndex = trimmed.indexOf('=');
    if (eqIndex < 1) continue;
    const key = trimmed.slice(0, eqIndex).trim();
    const value = trimmed.slice(eqIndex + 1).trim();
    vars[key] = value;
  }
  return vars;
}

function parseEnvFile() {
  const merged = {};
  // Read in reverse order so first file wins (later spreads override earlier)
  for (const file of [...ENV_FILES].reverse()) {
    Object.assign(merged, parseOneEnvFile(file));
  }
  return merged;
}

function writeEnvFile(updates) {
  // Write to the OpenClaw .env (primary config) — fall back to root .env
  const targetFile = fs.existsSync(OPENCLAW_ENV) ? OPENCLAW_ENV : ROOT_ENV;
  let text = readText(targetFile);
  if (!text) text = '';

  for (const [key, value] of Object.entries(updates)) {
    const regex = new RegExp(`^${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*=.*$`, 'm');
    const newLine = `${key}=${value}`;
    if (regex.test(text)) {
      text = text.replace(regex, newLine);
    } else {
      text = text.trimEnd() + '\n' + newLine + '\n';
    }
  }

  fs.writeFileSync(targetFile, text, 'utf8');
}

function maskValue(value) {
  if (!value || value.length <= 6) return '******';
  return value.slice(0, 3) + '*'.repeat(Math.min(value.length - 3, 20));
}

const FALLBACK_INTEGRATION = {
  id: 'misc',
  name: 'Misc',
  category: 'Unmapped',
  color: '#94a3b8',
  transport: 'stdio',
  toolEstimate: 0,
  description: 'Skills that are present in the workspace but not yet mapped into a named integration cluster.',
};

function readText(file) {
  try {
    return fs.readFileSync(file, 'utf8');
  } catch {
    return '';
  }
}

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function extractFrontmatter(source) {
  const match = source.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) return {};
  try {
    return yaml.load(match[1]) || {};
  } catch {
    return {};
  }
}

function getIntegrationForSkill(skillId) {
  return INTEGRATION_CATALOG.find((entry) => entry.prefixes.some((prefix) => skillId.startsWith(prefix))) || FALLBACK_INTEGRATION;
}

function parseSkills() {
  const items = [];
  if (!fs.existsSync(SKILLS_DIR)) return items;

  const dirs = fs.readdirSync(SKILLS_DIR, { withFileTypes: true }).filter((entry) => entry.isDirectory());
  for (const dir of dirs) {
    const skillId = dir.name;
    const skillFile = path.join(SKILLS_DIR, skillId, 'SKILL.md');
    const frontmatter = extractFrontmatter(readText(skillFile));
    const integration = getIntegrationForSkill(skillId);
    const requires = frontmatter?.metadata?.openclaw?.requires || {};
    items.push({
      id: skillId,
      name: frontmatter.name || skillId,
      description: frontmatter.description || '',
      integrationId: integration.id,
      category: integration.category,
      requiredBins: requires.bins || [],
      requiredEnv: requires.env || [],
      hasSkillFile: fs.existsSync(skillFile),
    });
  }

  return items.sort((a, b) => a.name.localeCompare(b.name));
}

// ── Full SKILL.md parser for tool dashboards ────────────────────────
function parseMarkdownTable(lines) {
  if (lines.length < 2) return null;
  const headers = lines[0].split('|').map((s) => s.trim()).filter(Boolean);
  if (headers.length === 0) return null;
  const rows = lines.slice(2).map((line) =>
    line.split('|').map((s) => s.trim()).filter(Boolean),
  ).filter((row) => row.length > 0);
  return { headers, rows };
}

function parseSkillMarkdown(skillId) {
  const filePath = path.join(SKILLS_DIR, skillId, 'SKILL.md');
  const raw = readText(filePath);
  if (!raw) return null;

  const frontmatter = extractFrontmatter(raw);
  const body = raw.replace(/^---\n[\s\S]*?\n---\n?/, '');

  // Split body into H2 sections
  const sections = [];
  const h2Parts = body.split(/^## /m);

  for (let i = 1; i < h2Parts.length; i++) {
    const part = h2Parts[i];
    const nlIndex = part.indexOf('\n');
    const title = nlIndex >= 0 ? part.slice(0, nlIndex).trim() : part.trim();
    const content = nlIndex >= 0 ? part.slice(nlIndex + 1) : '';

    const tables = [];
    const codeBlocks = [];
    const subSections = [];
    const textParts = [];

    // Extract fenced code blocks first
    const stripped = content.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
      codeBlocks.push({ lang: lang || 'text', code: code.trim() });
      return '';
    });

    // Split remaining by H3 sub-sections
    const h3Parts = stripped.split(/^### /m);
    const mainContent = h3Parts[0] || '';

    // Extract tables from main content
    const mainLines = mainContent.split('\n');
    let tableBuffer = [];
    for (const line of mainLines) {
      if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
        tableBuffer.push(line.trim());
      } else {
        if (tableBuffer.length >= 3) {
          const table = parseMarkdownTable(tableBuffer);
          if (table) tables.push(table);
        }
        tableBuffer = [];
        const trimmed = line.trim();
        if (trimmed && !trimmed.match(/^\|?-+\|?$/)) {
          textParts.push(trimmed);
        }
      }
    }
    if (tableBuffer.length >= 3) {
      const table = parseMarkdownTable(tableBuffer);
      if (table) tables.push(table);
    }

    // Process H3 sub-sections
    for (let j = 1; j < h3Parts.length; j++) {
      const subPart = h3Parts[j];
      const subNl = subPart.indexOf('\n');
      const subTitle = subNl >= 0 ? subPart.slice(0, subNl).trim() : subPart.trim();
      const subContent = subNl >= 0 ? subPart.slice(subNl + 1).trim() : '';

      const subTables = [];
      const subCodeBlocks = [];
      const subText = [];

      const subStripped = subContent.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        subCodeBlocks.push({ lang: lang || 'text', code: code.trim() });
        return '';
      });

      const subLines = subStripped.split('\n');
      let subTableBuf = [];
      for (const line of subLines) {
        if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
          subTableBuf.push(line.trim());
        } else {
          if (subTableBuf.length >= 3) {
            const table = parseMarkdownTable(subTableBuf);
            if (table) subTables.push(table);
          }
          subTableBuf = [];
          const trimmed = line.trim();
          if (trimmed) subText.push(trimmed);
        }
      }
      if (subTableBuf.length >= 3) {
        const table = parseMarkdownTable(subTableBuf);
        if (table) subTables.push(table);
      }

      subSections.push({
        title: subTitle,
        text: subText.join('\n'),
        tables: subTables,
        codeBlocks: subCodeBlocks,
      });
    }

    sections.push({
      title,
      text: textParts.filter((t) => t.length > 0).join('\n'),
      tables,
      codeBlocks,
      subSections,
    });
  }

  const integration = getIntegrationForSkill(skillId);
  return {
    id: skillId,
    integrationId: integration.id,
    frontmatter,
    rawMarkdown: body,
    sections,
  };
}

function parseDevices() {
  const source = readText(TESTBED_FILE);
  if (!source) return [];

  try {
    const testbed = yaml.load(source);
    return Object.entries(testbed?.devices || {}).map(([name, device]) => ({
      id: slugify(name),
      name,
      alias: device.alias || name,
      type: device.type || 'device',
      os: device.os || 'unknown',
      platform: device.platform || 'unknown',
      protocol: device.connections?.cli?.protocol || 'ssh',
      ip: device.connections?.cli?.ip || 'N/A',
      port: device.connections?.cli?.port || 22,
    }));
  } catch {
    return [];
  }
}

function parseConfig() {
  try {
    return JSON.parse(readText(CONFIG_FILE));
  } catch {
    return {};
  }
}

function parseIdentity() {
  const raw = readText(IDENTITY_FILE) || readText(SOUL_FILE);
  return {
    name: 'NetClaw',
    title: 'CCIE-level digital coworker',
    badge: 'CCIE R&S #AI-001',
    summary: 'Network engineering agent with MCP-backed workflows, pyATS automation, and governance gates.',
    raw,
  };
}

function buildIntegrations(skills) {
  const usedIds = new Set(skills.map((skill) => skill.integrationId));
  const integrations = INTEGRATION_CATALOG
    .filter((entry) => usedIds.has(entry.id))
    .map((entry) => {
      const relatedSkills = skills.filter((skill) => skill.integrationId === entry.id);
      return {
        ...entry,
        skillCount: relatedSkills.length,
        active: relatedSkills.length > 0,
      };
    });

  if (usedIds.has(FALLBACK_INTEGRATION.id)) {
    integrations.push({
      ...FALLBACK_INTEGRATION,
      skillCount: skills.filter((skill) => skill.integrationId === FALLBACK_INTEGRATION.id).length,
      active: true,
    });
  }

  return integrations.sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name));
}

function buildSettings(config, devices) {
  const modelPrimary = config?.agents?.defaults?.model?.primary || 'unknown';
  const modelFallbacks = config?.agents?.defaults?.model?.fallbacks || [];
  return [
    { label: 'Gateway Mode', value: config?.gateway?.mode || 'unknown' },
    { label: 'Primary Model', value: modelPrimary.replace('anthropic/', '') },
    { label: 'Fallback Models', value: modelFallbacks.length ? modelFallbacks.join(', ').replaceAll('anthropic/', '') : 'none' },
    { label: 'Workspace', value: config?.agents?.defaults?.workspace || 'unknown' },
    { label: 'Command Mode', value: config?.commands?.native || 'unknown' },
    { label: 'Devices in Testbed', value: String(devices.length) },
  ];
}

function buildGraph() {
  const identity = parseIdentity();
  const config = parseConfig();
  const skills = parseSkills();
  const devices = parseDevices();
  const integrations = buildIntegrations(skills);

  const categories = [...new Set(integrations.map((entry) => entry.category))].map((category) => ({
    id: slugify(category),
    name: category,
    count: integrations.filter((entry) => entry.category === category).length,
    color: integrations.find((entry) => entry.category === category)?.color || '#94a3b8',
  }));

  return {
    identity,
    config,
    settings: buildSettings(config, devices),
    integrations,
    skills,
    devices,
    categories,
    stats: {
      integrationCount: integrations.length,
      skillCount: skills.length,
      deviceCount: devices.length,
      categoryCount: categories.length,
      toolEstimate: integrations.reduce((sum, entry) => sum + entry.toolEstimate, 0),
    },
    generatedAt: new Date().toISOString(),
  };
}

export { buildGraph };

app.get('/api/health', (req, res) => {
  res.json({ ok: true, service: 'netclaw-visual-api', generatedAt: new Date().toISOString() });
});

app.get('/api/graph', (req, res) => {
  res.json(buildGraph());
});

// ── BGP topology endpoint ─────────────────────────────────────────
const BGP_API = 'http://127.0.0.1:8179';

async function fetchBGPState() {
  try {
    const [peersRes, ribRes, statusRes] = await Promise.all([
      fetch(`${BGP_API}/peers`, { signal: AbortSignal.timeout(3000) }),
      fetch(`${BGP_API}/rib`, { signal: AbortSignal.timeout(3000) }),
      fetch(`${BGP_API}/status`, { signal: AbortSignal.timeout(3000) }),
    ]);
    const peers = await peersRes.json();
    const rib = await ribRes.json();
    const status = await statusRes.json();

    // Enrich peers with adj-rib-in route counts, ASN, router-id, and type
    const enrichedPeers = (peers.peers || []).map((p) => {
      const adjRoutes = rib.adj_rib_in?.[p.peer] || [];
      const isMesh = p.peer.startsWith('mesh-');

      // Extract ASN: from peer key "mesh-as65002" or from adj-rib-in AS paths
      let peerAs = null;
      const meshMatch = p.peer.match(/^mesh-as(\d+)$/);
      if (meshMatch) {
        peerAs = parseInt(meshMatch[1]);
      } else if (adjRoutes.length > 0 && adjRoutes[0].as_path?.length > 0) {
        peerAs = adjRoutes[0].as_path[0]; // first AS in path = neighbor AS
      }

      // Extract router-id from loc-rib entries that came from this peer
      let routerId = null;
      for (const route of Object.values(rib.loc_rib || {})) {
        if (route.peer_ip === p.peer && route.peer_id) {
          routerId = route.peer_id;
          break;
        }
      }
      // Fallback: derive router-id from adj-rib-in next_hop (IPv4 next_hop = router-id)
      if (!routerId && adjRoutes.length > 0) {
        for (const r of adjRoutes) {
          if (r.next_hop && !r.next_hop.includes(':') && r.next_hop !== '0.0.0.0') {
            routerId = r.next_hop;
            break;
          }
        }
      }

      return {
        ...p,
        as: peerAs,
        routerId,
        peerIp: p.peer,
        type: isMesh ? 'claw' : 'router',
        routesReceived: adjRoutes.length,
        adjRibIn: adjRoutes,
      };
    });

    return {
      available: true,
      local: {
        as: parseInt(process.env.NETCLAW_LOCAL_AS) || 65001,
        routerId: process.env.NETCLAW_ROUTER_ID || '4.4.4.4',
        listenPort: parseInt(process.env.BGP_LISTEN_PORT) || 1179,
      },
      peers: enrichedPeers,
      rib: rib.loc_rib || {},
      ribCount: rib.loc_rib_count || 0,
      injected: rib.injected || {},
      kernelRoutes: rib.kernel_routes || [],
      generatedAt: new Date().toISOString(),
    };
  } catch {
    return { available: false, peers: [], rib: {}, ribCount: 0, generatedAt: new Date().toISOString() };
  }
}

app.get('/api/bgp', async (req, res) => {
  res.json(await fetchBGPState());
});

// ── Gateway status endpoint ───────────────────────────────────────
app.get('/api/gateway/status', async (req, res) => {
  const gw = getGatewayConfig();
  try {
    const health = await fetch(`http://127.0.0.1:${gw.port}/v1/models`, {
      signal: AbortSignal.timeout(2000),
    });
    res.json({ online: health.ok, port: gw.port });
  } catch {
    res.json({ online: false, port: gw.port });
  }
});

// ── Full SKILL.md detail endpoint ──────────────────────────────────
app.get('/api/skill/:skillId', (req, res) => {
  const result = parseSkillMarkdown(req.params.skillId);
  if (!result) return res.status(404).json({ error: 'Skill not found or no SKILL.md' });
  res.json(result);
});

// ── ENV config per integration ─────────────────────────────────────
app.get('/api/env/:integrationId', (req, res) => {
  const mapping = ENV_MAP[req.params.integrationId];
  if (!mapping) return res.status(404).json({ error: 'Unknown integration' });

  const envVars = parseEnvFile();
  const fields = mapping.env.map((key) => ({
    key,
    value: envVars[key] || '',
    masked: envVars[key] ? maskValue(envVars[key]) : '',
    isSet: key in envVars && envVars[key] !== '',
  }));

  res.json({
    integrationId: req.params.integrationId,
    fields,
    files: mapping.files,
    notes: mapping.notes,
  });
});

app.put('/api/env', (req, res) => {
  const { updates } = req.body;
  if (!updates || typeof updates !== 'object') {
    return res.status(400).json({ error: 'Expected { updates: { KEY: "value", ... } }' });
  }

  try {
    writeEnvFile(updates);
    // Broadcast config change to all WS clients
    broadcastWS('config:updated', { keys: Object.keys(updates), generatedAt: new Date().toISOString() });
    res.json({ ok: true, updatedKeys: Object.keys(updates) });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── Testbed device config ──────────────────────────────────────────
app.get('/api/testbed/raw', (req, res) => {
  res.type('text/yaml').send(readText(TESTBED_FILE) || '# No testbed found');
});

app.put('/api/testbed/raw', (req, res) => {
  const { content } = req.body;
  if (!content) return res.status(400).json({ error: 'Expected { content: "yaml string" }' });

  try {
    yaml.load(content); // validate it's valid YAML
    fs.writeFileSync(TESTBED_FILE, content, 'utf8');
    broadcastWS('config:updated', { keys: ['testbed'], generatedAt: new Date().toISOString() });
    res.json({ ok: true });
  } catch (err) {
    res.status(400).json({ error: `Invalid YAML: ${err.message}` });
  }
});

// ── Chat / natural language interface ──────────────────────────────
// Proxies to the running OpenClaw gateway, falling back to a local
// heuristic response if the gateway is unavailable.
const chatHistory = [];

// Read OpenClaw gateway config for auth
function getGatewayConfig() {
  try {
    const configPath = path.join(process.env.HOME || '/root', '.openclaw', 'openclaw.json');
    const config = JSON.parse(readText(configPath));
    return {
      port: config?.gateway?.port || 18789,
      token: config?.gateway?.auth?.token || '',
    };
  } catch {
    return { port: 18789, token: '' };
  }
}

app.post('/api/chat', async (req, res) => {
  const { message } = req.body;
  if (!message) return res.status(400).json({ error: 'Expected { message: "..." }' });

  const timestamp = new Date().toISOString();
  chatHistory.push({ role: 'user', text: message, timestamp });

  // Analyze the message to determine which integrations/skills are relevant
  const graph = buildGraph();
  const activations = resolveActivations(message, graph);

  // Broadcast activation events to all WS clients so the 3D scene lights up
  broadcastWS('chat:activations', {
    message,
    activations,
    timestamp,
  });

  // Try to proxy through the real OpenClaw gateway with streaming
  let responseText = '';
  let fromGateway = false;
  const gw = getGatewayConfig();

  try {
    const gwRes = await fetch(`http://127.0.0.1:${gw.port}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${gw.token}`,
        'Content-Type': 'application/json',
        'x-openclaw-agent-id': 'main',
      },
      body: JSON.stringify({
        model: 'openclaw',
        messages: chatHistory
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .slice(-10)
          .map((m) => ({ role: m.role, content: m.text || m.response || '' })),
        stream: false,
      }),
      signal: AbortSignal.timeout(300000),
    });

    if (gwRes.ok) {
      const gwData = await gwRes.json();
      responseText = gwData.choices?.[0]?.message?.content || gwData.choices?.[0]?.text || '';
      fromGateway = true;
    }
  } catch {
    // Gateway not reachable — fall back to local heuristic
  }

  if (!responseText) {
    responseText = buildChatResponse(message, activations, graph);
  }

  chatHistory.push({ role: 'assistant', text: responseText, timestamp: new Date().toISOString() });

  // After gateway response, scan latest transcript for tool_use events
  if (fromGateway) {
    setTimeout(() => extractAndBroadcastToolCalls(graph), 500);
  }

  // After a delay, send deactivation
  setTimeout(() => {
    broadcastWS('chat:deactivate', { timestamp: new Date().toISOString() });
  }, 6000);

  res.json({
    response: responseText,
    activations,
    fromGateway,
    timestamp,
  });
});

app.get('/api/chat/history', (req, res) => {
  res.json(chatHistory.slice(-50));
});

// ── Session transcript tool call extraction (Section H) ─────────
const SESSIONS_DIR = path.join(process.env.HOME || '/root', '.openclaw', 'agents', 'main', 'sessions');

function getLatestSessionFile() {
  try {
    const files = fs.readdirSync(SESSIONS_DIR)
      .filter((f) => f.endsWith('.jsonl'))
      .map((f) => ({ name: f, mtime: fs.statSync(path.join(SESSIONS_DIR, f)).mtimeMs }))
      .sort((a, b) => b.mtime - a.mtime);
    return files.length > 0 ? path.join(SESSIONS_DIR, files[0].name) : null;
  } catch {
    return null;
  }
}

function extractToolCalls(sessionFile, sinceMs = 0) {
  try {
    const text = fs.readFileSync(sessionFile, 'utf8');
    const lines = text.trim().split('\n');
    const toolCalls = [];

    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        if (entry.type !== 'message' || !entry.message) continue;
        // Skip entries older than sinceMs
        if (sinceMs > 0 && entry.timestamp && new Date(entry.timestamp).getTime() < sinceMs) continue;

        const msg = entry.message;

        // Look for toolCall content blocks in assistant messages
        if (msg.role === 'assistant' && Array.isArray(msg.content)) {
          for (const block of msg.content) {
            if (block.type === 'toolCall') {
              toolCalls.push({
                tool: block.name || 'unknown',
                input: block.input ? Object.keys(block.input).slice(0, 4) : [],
                id: block.id || '',
              });
            }
          }
        }
        // Look for tool result entries (role=tool with toolCallId)
        if (msg.toolCallId && msg.toolName) {
          const matchingCall = toolCalls.find((tc) => tc.id === msg.toolCallId);
          if (matchingCall) {
            let output = '';
            if (typeof msg.content === 'string') {
              output = msg.content;
            } else if (Array.isArray(msg.content)) {
              output = msg.content.map((b) => typeof b === 'string' ? b : (b.text || JSON.stringify(b))).join('\n');
            }
            matchingCall.output = output.slice(0, 500);
          }
        }
      } catch { /* skip malformed lines */ }
    }
    return toolCalls;
  } catch {
    return [];
  }
}

let lastToolScanMs = Date.now();

function extractAndBroadcastToolCalls(graph) {
  const sessionFile = getLatestSessionFile();
  if (!sessionFile) return;

  const calls = extractToolCalls(sessionFile, lastToolScanMs);
  lastToolScanMs = Date.now();

  calls.forEach((call, index) => {
    // Match tool name to integration
    const matchedIntegration = INTEGRATION_CATALOG.find((entry) =>
      entry.prefixes.some((prefix) => call.tool.startsWith(prefix.replace('-', '_')) || call.tool.startsWith(prefix))
    );

    setTimeout(() => {
      broadcastWS('chat:tool_call', {
        tool: call.tool,
        integration: matchedIntegration?.id || 'pyats',
        input: call.input,
        output: call.output || '',
        timestamp: new Date().toISOString(),
      });
    }, index * 300);
  });
}

// API endpoints for session tool calls
app.get('/api/sessions', (req, res) => {
  try {
    const files = fs.readdirSync(SESSIONS_DIR)
      .filter((f) => f.endsWith('.jsonl'))
      .map((f) => ({
        id: f.replace('.jsonl', ''),
        mtime: fs.statSync(path.join(SESSIONS_DIR, f)).mtimeMs,
      }))
      .sort((a, b) => b.mtime - a.mtime)
      .slice(0, 20);
    res.json(files);
  } catch {
    res.json([]);
  }
});

app.get('/api/session/:id/tools', (req, res) => {
  const sessionFile = path.join(SESSIONS_DIR, `${req.params.id}.jsonl`);
  if (!fs.existsSync(sessionFile)) return res.status(404).json({ error: 'Session not found' });
  const calls = extractToolCalls(sessionFile);
  res.json(calls);
});

function resolveActivations(message, graph) {
  const lower = message.toLowerCase();
  const activated = {
    integrations: [],
    skills: [],
    devices: [],
  };

  // Match integrations by name or keyword (word-boundary for short tokens)
  for (const integration of graph.integrations) {
    const names = [integration.name.toLowerCase(), integration.id];
    // Only include prefix tokens that are 4+ chars to avoid false positives (e.g. "te" matching "interfaces")
    const safePrefixes = (integration.prefixes || []).map((p) => p.replace('-', '')).filter((p) => p.length >= 4);
    const allNames = [...names, ...safePrefixes];
    if (allNames.some((n) => {
      if (n.length <= 3) {
        return new RegExp(`\\b${n}\\b`, 'i').test(lower);
      }
      return lower.includes(n);
    }) || lower.includes(integration.category.toLowerCase())) {
      activated.integrations.push(integration.id);
    }
  }

  // Match skills by name
  for (const skill of graph.skills) {
    if (lower.includes(skill.id.replace(/-/g, ' ')) || lower.includes(skill.id)) {
      activated.skills.push(skill.id);
      if (!activated.integrations.includes(skill.integrationId)) {
        activated.integrations.push(skill.integrationId);
      }
    }
  }

  // Match devices by name
  for (const device of graph.devices) {
    if (lower.includes(device.name.toLowerCase()) || lower.includes(device.alias?.toLowerCase())) {
      activated.devices.push(device.id);
    }
  }

  // Keyword heuristics
  const keywords = {
    'health check': ['pyats'],
    'routing': ['pyats', 'protocol'],
    'ospf': ['pyats', 'protocol'],
    'bgp': ['pyats', 'protocol'],
    'topology': ['pyats'],
    'security': ['ise', 'nmap', 'nvd', 'fmc'],
    'audit': ['pyats', 'nvd', 'gait'],
    'firewall': ['asa', 'fmc', 'paloalto', 'fortimanager', 'checkpoint'],
    'check point': ['checkpoint'],
    'checkpoint': ['checkpoint'],
    'threat emulation': ['checkpoint'],
    'sandblast': ['checkpoint'],
    'harmony sase': ['checkpoint'],
    'clusterxl': ['checkpoint'],
    'smartconsole': ['checkpoint'],
    'vpn': ['asa', 'sdwan', 'meraki'],
    'change': ['servicenow', 'gait'],
    'diagram': ['drawio', 'uml', 'markmap'],
    'cloud': ['aws', 'gcp'],
    'aws': ['aws'],
    'gcp': ['gcp'],
    'meraki': ['meraki'],
    'wireless': ['meraki', 'catc'],
    'monitoring': ['grafana', 'prometheus'],
    'thousandeyes': ['thousandeyes'],
    'thousand eyes': ['thousandeyes'],
    'alert': ['grafana', 'slack', 'webex'],
    'log': ['grafana'],
    'kubernetes': ['kubeshark'],
    'k8s': ['kubeshark'],
    'packet': ['wiki'],
    'pcap': ['wiki'],
    'lab': ['cml', 'clab'],
    'netbox': ['netbox'],
    'nautobot': ['nautobot'],
    'traceroute': ['gtrace'],
    'scan': ['nmap'],
    'cve': ['nvd'],
    'vulnerability': ['nvd'],
    'voice': ['slack', 'webex'],
    'slack': ['slack'],
    'webex': ['webex'],
    'adaptive card': ['webex'],
    'teams': ['msgraph'],
    'visio': ['msgraph'],
    'rfc': ['wiki'],
    'subnet': ['wiki'],
  };

  for (const [keyword, ids] of Object.entries(keywords)) {
    if (lower.includes(keyword)) {
      for (const id of ids) {
        if (!activated.integrations.includes(id)) activated.integrations.push(id);
      }
    }
  }

  // If nothing matched, activate the core (pyats) as default
  if (activated.integrations.length === 0) {
    activated.integrations.push('pyats');
  }

  return activated;
}

function buildChatResponse(message, activations, graph) {
  const integrationNames = activations.integrations
    .map((id) => graph.integrations.find((i) => i.id === id)?.name || id)
    .join(', ');

  const skillNames = activations.skills
    .map((id) => graph.skills.find((s) => s.id === id)?.name || id)
    .join(', ');

  const deviceNames = activations.devices
    .map((id) => graph.devices.find((d) => d.id === id)?.name || id)
    .join(', ');

  let response = `Routing to: ${integrationNames}.`;
  if (skillNames) response += ` Skills: ${skillNames}.`;
  if (deviceNames) response += ` Devices: ${deviceNames}.`;
  response += '\n\nOpenClaw gateway is offline. Run `openclaw gateway run` to enable live responses and tool execution.';

  return response;
}

function broadcastWS(type, payload) {
  const msg = JSON.stringify({ type, payload });
  for (const socket of sockets) {
    if (socket.readyState === socket.OPEN) socket.send(msg);
  }
}

const sockets = new Set();

wss.on('connection', (socket) => {
  sockets.add(socket);
  socket.send(JSON.stringify({ type: 'graph:init', payload: buildGraph() }));

  const timer = setInterval(async () => {
    if (socket.readyState !== socket.OPEN) return;
    socket.send(JSON.stringify({
      type: 'graph:heartbeat',
      payload: {
        generatedAt: new Date().toISOString(),
        stats: buildGraph().stats,
      },
    }));
    // BGP state push
    try {
      const bgp = await fetchBGPState();
      if (bgp.available) {
        socket.send(JSON.stringify({ type: 'bgp:state', payload: bgp }));
      }
    } catch { /* daemon not running — skip */ }
  }, 5000);

  socket.on('close', () => {
    sockets.delete(socket);
    clearInterval(timer);
  });
});

const PORT = process.env.HUD_PORT || 3001;
server.listen(PORT, () => {
  console.log(`NetClaw visual API listening on http://localhost:${PORT}`);
  console.log(`WebSocket available at ws://localhost:${PORT}/ws`);
});
