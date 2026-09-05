import express from 'express';
import { WebSocketServer } from 'ws';
import http from 'http';
import cors from 'cors';
import fs from 'fs';
import os from 'os';
import path from 'path';
import yaml from 'js-yaml';
import multer from 'multer';
import { execFile } from 'child_process';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const app = express();

app.use(cors());
// The branching canvas can include a compact image or an attached text file in
// its context. Keep the cap explicit so those requests work without making the
// API an unbounded JSON sink.
app.use(express.json({ limit: '4mb' }));

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
  { id: 'halo', name: 'HaloPSA / HaloITSM', category: 'Governance', prefixes: ['halo-'], color: '#1a7f8c', transport: 'stdio', toolEstimate: 18, description: 'HaloPSA/HaloITSM: open change requests (gated confirm-before-submit) and review assets and their related tickets for context.' },
  { id: 'meraki', name: 'Meraki', category: 'Network Platforms', prefixes: ['meraki-'], color: '#9b5de5', transport: 'stdio', toolEstimate: 804, description: 'Dashboard inventory, wireless, switching, and security appliance control.' },
  { id: 'sdwan', name: 'SD-WAN', category: 'Network Platforms', prefixes: ['sdwan-'], color: '#8d99ae', transport: 'stdio', toolEstimate: 12, description: 'vManage monitoring and WAN-state workflows.' },
  { id: 'nso', name: 'Cisco NSO', category: 'Network Platforms', prefixes: ['nso-'], color: '#4361ee', transport: 'stdio', toolEstimate: 18, description: 'Service and device orchestration.' },
  { id: 'itential', name: 'Itential', category: 'Network Platforms', prefixes: ['itential-'], color: '#4895ef', transport: 'stdio', toolEstimate: 65, description: 'Automation platform workflows and orchestration hooks.' },
  { id: 'evpn', name: 'EVPN/VXLAN', category: 'Network Platforms', prefixes: ['evpn-'], color: '#3a86ff', transport: 'stdio', toolEstimate: 14, description: 'Overlay-underlay correlation and fabric troubleshooting.' },
  { id: 'protocol', name: 'Protocol Ops', category: 'Network Platforms', prefixes: ['protocol-'], color: '#577590', transport: 'stdio', toolEstimate: 10, description: 'Intent validation and active protocol participation.' },
  { id: 'catc', name: 'Catalyst Center', category: 'Controller Platforms', prefixes: ['catc-'], color: '#118ab2', transport: 'stdio', toolEstimate: 24, description: 'Controller inventory, client ops, and troubleshooting.' },
  { id: 'arista', name: 'Arista CVP', category: 'Controller Platforms', prefixes: ['arista-'], color: '#06b6d4', transport: 'stdio', toolEstimate: 8, description: 'CloudVision-backed workflow surface.' },
  { id: 'fortinet', name: 'Fortinet', category: 'Security', prefixes: ['fmg_', 'fgt_', 'faz_', 'fortinet_'], color: '#d00000', transport: 'stdio', toolEstimate: 21, description: 'Three planes: FortiManager policy intent, FortiGate observed state, FortiAnalyzer traffic. Read-only default, writes behind approval + change record.' },
  { id: 'paloalto', name: 'Palo Alto Panorama', category: 'Security', prefixes: ['paloalto-'], color: '#e76f51', transport: 'stdio', toolEstimate: 10, description: 'Panorama-managed firewall policy lookup.' },
  { id: 'fmc', name: 'Cisco FMC', category: 'Security', prefixes: ['fmc-'], color: '#bc4749', transport: 'http', toolEstimate: 8, description: 'Cisco Secure Firewall policy search.' },
  { id: 'nmap', name: 'Nmap', category: 'Security', prefixes: ['nmap-'], color: '#ff006e', transport: 'stdio', toolEstimate: 18, description: 'Scoped scanning and service detection.' },
  { id: 'nvd', name: 'NVD / CVE', category: 'Security', prefixes: ['nvd-'], color: '#fb5607', transport: 'stdio', toolEstimate: 4, description: 'Vulnerability context matched to operational state.' },
  { id: 'cisco-psirt', name: 'Cisco PSIRT', category: 'Security', prefixes: ['psirt-', 'check_version', 'check_cve'], color: '#d62828', transport: 'stdio', toolEstimate: 6, description: 'Whether a running Cisco version is affected by a published advisory — IOS, IOS-XE, NX-OS, ASA, FTD, FMC, ACI. Read-only; never contacts a device. An empty result means Cisco published nothing, not that the device is secure.' },
  { id: 'grafana', name: 'Grafana', category: 'Observability', prefixes: ['grafana-', 'flow-'], color: '#f8961e', transport: 'http', toolEstimate: 75, description: 'Dashboards, alerts, incidents, and derived telemetry views.' },
  { id: 'prometheus', name: 'Prometheus', category: 'Observability', prefixes: ['prometheus-'], color: '#faa307', transport: 'stdio', toolEstimate: 6, description: 'Direct metrics and PromQL access.' },
  { id: 'thousandeyes', name: 'ThousandEyes', category: 'Observability', prefixes: ['te-'], color: '#ffb703', transport: 'http', toolEstimate: 29, description: 'Synthetic and path-aware external monitoring.' },
  { id: 'kubeshark', name: 'Kubeshark', category: 'Observability', prefixes: ['kubeshark-'], color: '#ffcb77', transport: 'http', toolEstimate: 6, description: 'Kubernetes packet and flow visibility.' },
  { id: 'gtrace', name: 'gtrace', category: 'Observability', prefixes: ['gtrace-'], color: '#bde0fe', transport: 'stdio', toolEstimate: 6, description: 'Path tracing and IP enrichment.' },
  { id: 'bgp-intel', name: 'BGP & Registry Intel', category: 'Observability', prefixes: ['rpki_', 'registry_', 'routing_', 'peering_', 'atlas_', 'resource_'], color: '#8ac926', transport: 'stdio', toolEstimate: 10, description: 'RPKI origin validation, RDAP ownership, PeeringDB peering, routing visibility. Public APIs, no credentials. not-found is NOT invalid.' },
  { id: 'zabbix', name: 'Zabbix NMS', category: 'Observability', prefixes: ['zabbix_'], color: '#d40000', transport: 'stdio', toolEstimate: 3, description: 'Self-hosted SNMP-poller NMS — polled metric history, problems, device availability. Read-only, vendored third-party (GPL-3.0) in its own venv. The only source of POLLED HISTORY: what something was doing over time. An empty history result is usually the wrong value_type, not an absence.' },
  { id: 'anta', name: 'Arista ANTA Validation', category: 'Observability', prefixes: ['anta_'], color: '#f7931e', transport: 'stdio', toolEstimate: 4, description: 'The ASSERTION layer — 208 ANTA tests behind 4 tools, 1,272-token manifest, read-only, EOS only. Five verdicts that never merge: pass/fail/not_applicable/skipped/error. ANTA natively calls a test for an UNCONFIGURED feature a failure; this reclassifies it to not_applicable, because counting it claims a BGP fault on a box with no BGP. No health percentage is ever emitted.' },
  { id: 'elastic', name: 'Elasticsearch Logs', category: 'Observability', prefixes: ['list_indices', 'get_mappings', 'search', 'esql', 'get_shards'], color: '#00bfb3', transport: 'stdio', toolEstimate: 5, description: 'Read-only log search over an operator-supplied Elasticsearch 8.x/9.x. Adopted Apache-2.0 image, digest-pinned, 1,094-token manifest. NEVER report a count from an unguarded search: Elasticsearch caps totals at 10,000 and this server discards the relation:"gte" marker, so a capped floor is indistinguishable from an exact count. Count with esql or track_total_hits.' },
  { id: 'k8s', name: 'Kubernetes (read-only)', category: 'Observability', prefixes: ['pods_', 'resources_', 'namespaces_', 'events_'], color: '#326ce5', transport: 'stdio', toolEstimate: 7, description: 'Read-only Kubernetes API — pods, services, ingresses, EndpointSlices, NetworkPolicies. Vendored Apache-2.0 Go binary, pinned and checksummed, 1,643-token manifest. Secrets denied at two layers. An empty list is NOT evidence of absence: the server silently narrows a cluster-wide query on insufficient RBAC.' },
  { id: 'catc', name: 'Catalyst Center (read-only)', category: 'Device Automation', prefixes: ['catc_'], color: '#00bceb', transport: 'stdio', toolEstimate: 10, description: 'All 514 read-only Catalyst Center operations behind 8 grouped dispatchers plus find/describe — 1,821-token manifest where inlining every tool would cost 64,420. Adopts Cisco official catalogue (Apache-2.0), not its runtime. An empty inventory is a statement about the controller, never about the network.' },
  { id: 'document', name: 'Document Generation', category: 'Platform Services', prefixes: ['docx_', 'xlsx_', 'pptx_', 'pdf_', 'list_documents'], color: '#4c956c', transport: 'stdio', toolEstimate: 6, description: 'Change-record .docx, audit .xlsx, exec .pptx and PDF form filling from real NetClaw data. No credentials, writes files only. Per-element provenance at a chokepoint — a missing value renders as NOT AVAILABLE, never as a blank.' },
  { id: 'globalping', name: 'Globalping', category: 'Observability', prefixes: ['globalping-'], color: '#00b4d8', transport: 'http', toolEstimate: 12, description: 'Outside-in measurement from ~4,800 probes across ~1,390 ASNs — ping, traceroute, DNS, MTR and HTTP toward a public target. The only vantage point NetClaw has outside its own administrative domain. Public endpoints only; "no probes matched" is not "the service is down".' },
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
  { id: 'multivendor-cli', name: 'Multivendor CLI Driver', category: 'Device Automation', prefixes: ['multivendor-'], color: '#16a085', transport: 'stdio', toolEstimate: 10, description: 'Nornir/NAPALM/Netmiko reach to ~90 platform families no other NetClaw server covers — MikroTik, VyOS, SONiC, Nokia SR Linux, Extreme, Huawei, Dell, EdgeOS. Read-only by default; Cisco stays with pyATS and Junos with junos-mcp.' },
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
  { id: 'auvik', name: 'Auvik', category: 'Observability', prefixes: ['auvik-'], color: '#0a9396', transport: 'stdio', toolEstimate: 20, description: 'Read-only Auvik network monitoring — inventory, alerts, lifecycle/warranty, and performance statistics across MSP tenants.' },
  { id: 'claroty', name: 'Claroty xDome', category: 'Security', prefixes: ['claroty-'], color: '#00a3a3', transport: 'stdio', toolEstimate: 21, description: 'OT / IoT / IoMT visibility — asset discovery, Purdue Model classification, alert and vulnerability triage, communication-map topology, all writes ITSM-gated.' },
  { id: 'threejs-viz', name: 'Three.js Network Viz', category: 'Visualization', prefixes: ['threejs-network-viz'], color: '#049ef4', transport: 'stdio', toolEstimate: 3, description: 'Browser-based 3D network topology visualization — single self-contained HTML file, no desktop app/GPU/server required. Optional real-3D-model stencil mode via the vendored sketchfab-mcp-server (3 tools: search, model-details/license-verification, download), filtered to CC0-licensed models only.' },
  { id: 'comfyui-viz', name: 'ComfyUI Topology Viz', category: 'Visualization', prefixes: ['comfyui-topology-viz', 'topology-diagram-mcp', 'image-style-mcp'], color: '#8a3ffc', transport: 'stdio', toolEstimate: 8, description: 'AI-generated stylized still images of a network topology. Spec 121 federated path (preferred, live topology sources): a deterministic diagram (topology-diagram-mcp, real role icons/labels/connections, no diffusion) restyled by an image-edit diffusion pass (image-style-mcp), both run on the johns-risk/viz federation member via n2n/tools/call. Falls back to the original comfyui-mcp Flux+ControlNet path (6 of its 41 tools used) for freeform requests or when that member is unreachable. Stills only in v1.' },
  { id: 'worldlabs-viz', name: 'World Labs Fantastical Viz', category: 'Visualization', prefixes: ['worldlabs-topology-viz', 'worldlabs-marble-mcp'], color: '#ff6b9d', transport: 'stdio', toolEstimate: 3, description: 'AI-augmented, explorable 3D "world" visualization of a real network topology via World Labs Marble (spec 122). Free, instant, no-cost themed prompt preview; a real credit-spending generation only runs after explicit two-layer confirmation (conversational and a required user_confirmed argument the tool itself validates). Explicitly decorative — reuses topology-diagram-mcp\'s accurate diagram as the authoritative artifact, standalone on Border, no federation member required.' },
  { id: 'chrome-devtools', name: 'Chrome DevTools', category: 'Browser Automation', prefixes: ['chrome-devtools-', 'browser-viz-verify', 'browser-gui-inspect'], color: '#4285f4', transport: 'npx', toolEstimate: 20, description: 'Controlled browser automation/inspection — visualization render QA, controller GUI gap-filling, undocumented vendor API discovery via network-request capture, general web-GUI automation. No credentials; auth via one-time manual sign-in into a persistent Chrome profile.' },
  { id: 'computer-use', name: 'Computer Use', category: 'Desktop Automation', prefixes: ['desktop-gui-inspect'], color: '#f9ab00', transport: 'script', toolEstimate: 17, description: 'Full-desktop automation for legacy tools with no browser or API path — virtual Xvfb+XFCE desktop, 17 xdotool-driven actions, VNC/noVNC Watch Mode (loopback-only). No credentials; installed via OpenClaw\'s ClawHub skill mechanism, not a vendored MCP server.' },
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
      // Mesh claws appear two ways: inbound sessions keyed "mesh-as<N>", and
      // outbound sessions keyed by their ngrok hostname (anything that isn't
      // a bare IPv4/IPv6 literal).
      const isMesh = p.peer.startsWith('mesh-') || !/^[0-9a-fA-F:.]+$/.test(p.peer);

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

// ── N2N Federation endpoint (feature 052) ─────────────────────────
// Aggregates the mesh daemon's /n2n/* state for the HUD federation view.
// Mirrors the /api/bgp pattern; degrades gracefully when N2N is disabled.
async function fetchN2NState() {
  try {
    const statusRes = await fetch(`${BGP_API}/n2n/status`, { signal: AbortSignal.timeout(3000) });
    if (!statusRes.ok) return { available: false, peers: [] };
    const status = await statusRes.json();
    if (!status || status.enabled === false) return { available: false, peers: [] };

    // Enrich each federated peer with its cached inventory
    const peers = await Promise.all((status.peers || []).map(async (p) => {
      let inventory = null;
      if (p.state === 'federated' && p.inventory_version != null) {
        try {
          const invRes = await fetch(`${BGP_API}/n2n/peers/${encodeURIComponent(p.identity)}/inventory`,
            { signal: AbortSignal.timeout(3000) });
          if (invRes.ok) inventory = await invRes.json();
        } catch { /* peer inventory optional */ }
      }
      return { ...p, inventory };
    }));

    let approvals = [];
    try {
      const aRes = await fetch(`${BGP_API}/n2n/approvals`, { signal: AbortSignal.timeout(3000) });
      if (aRes.ok) approvals = (await aRes.json()).pending || [];
    } catch { /* approvals optional */ }

    // 053 US6: fold per-peer channel health + in-flight tasks into each peer
    try {
      const hRes = await fetch(`${BGP_API}/n2n/health`, { signal: AbortSignal.timeout(3000) });
      if (hRes.ok) {
        const health = (await hRes.json()).peers || [];
        const byId = Object.fromEntries(health.map((h) => [h.identity, h]));
        peers.forEach((p) => {
          const h = byId[p.identity];
          if (h) {
            p.channel_state = h.channel_state;
            p.last_seen = h.last_seen;
            p.endpoint_updated_at = h.endpoint_updated_at;
            p.in_flight_tasks = h.in_flight_tasks || [];
          }
        });
      }
    } catch { /* health optional */ }

    // 056 iN2N: fold this claw's risk role + (on a Border) its members so the
    // HUD can render the hub-and-spoke risk view alongside eN2N peers.
    let risk = null;
    let members = [];
    let posture = null;
    try {
      const rRes = await fetch(`${BGP_API}/n2n/risk`, { signal: AbortSignal.timeout(3000) });
      if (rRes.ok) risk = await rRes.json();
      if (risk && risk.role === 'border') {
        const mRes = await fetch(`${BGP_API}/n2n/members`, { signal: AbortSignal.timeout(3000) });
        if (mRes.ok) members = (await mRes.json()).members || [];
      }
    } catch { /* iN2N optional (standalone/pre-056 daemon) */ }

    // 057: production posture (enforced/degraded/testing) for the risk panel.
    try {
      const pRes = await fetch(`${BGP_API}/n2n/posture`, { signal: AbortSignal.timeout(3000) });
      if (pRes.ok) posture = await pRes.json();
    } catch { /* posture optional (pre-057 daemon) */ }

    // 057: GAIT immutable audit trail (recent federation events) for the risk panel.
    let gait = [];
    try {
      const gRes = await fetch(`${BGP_API}/n2n/gait`, { signal: AbortSignal.timeout(3000) });
      if (gRes.ok) gait = (await gRes.json()).events || [];
    } catch { /* gait optional (pre-057 daemon) */ }

    // 065: chroma-to-chroma replication jobs, so the HUD can show in-flight
    // and recent replicate/resync activity without the operator polling
    // n2n_task_status manually — reuses the existing /n2n/tasks list, just
    // filtered to this feature's target_type.
    let replicationJobs = [];
    try {
      const tRes = await fetch(`${BGP_API}/n2n/tasks`, { signal: AbortSignal.timeout(3000) });
      if (tRes.ok) {
        const tasks = (await tRes.json()).tasks || [];
        replicationJobs = tasks.filter((t) => t.target_type === 'knowledge_replicate');
      }
    } catch { /* replication optional (pre-065 daemon) */ }

    // 066: NetClaw Mobile edge nodes are just members with node_type='edge'
    // (already present in `members` above) and their recent pushes are just
    // audit rows with target_type='edge_push' — reuse the existing queries
    // rather than adding new endpoints.
    const edgeNodes = members.filter((m) => m.node_type === 'edge');
    let recentPushes = [];
    try {
      const aRes = await fetch(`${BGP_API}/n2n/audit`, { signal: AbortSignal.timeout(3000) });
      if (aRes.ok) {
        const records = (await aRes.json()).records || [];
        recentPushes = records.filter((r) => r.target_type === 'edge_push');
      }
    } catch { /* edge push audit optional (pre-066 daemon) */ }

    return { available: true, identity: status.identity, peers, approvals,
             risk, members, posture, gait, replicationJobs, edgeNodes, recentPushes,
             generatedAt: new Date().toISOString() };
  } catch {
    return { available: false, peers: [], risk: null, members: [],
             replicationJobs: [], edgeNodes: [], recentPushes: [],
             generatedAt: new Date().toISOString() };
  }
}

app.get('/api/n2n', async (req, res) => {
  res.json(await fetchN2NState());
});

// Proxy a claw-to-claw chat message from the HUD to the daemon (FR-025)
app.post('/api/n2n/chat', async (req, res) => {
  const { peer, text, session_id } = req.body || {};
  if (!peer || !text) return res.status(400).json({ error: 'expected { peer, text }' });
  try {
    const r = await fetch(`${BGP_API}/n2n/chat/send`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ peer, text, session_id }),
      signal: AbortSignal.timeout(300000),
    });
    res.json(await r.json());
  } catch (e) {
    res.status(502).json({ error: `daemon unreachable: ${e.message}` });
  }
});

// ── Gateway status endpoint ───────────────────────────────────────
app.get('/api/gateway/status', async (req, res) => {
  const gw = getGatewayConfig();
  try {
    // The gateway's /v1 API requires the bearer token — without it we get 401
    // and the HUD falsely shows "offline". Send the token like the chat call does.
    const health = await fetch(`http://127.0.0.1:${gw.port}/v1/models`, {
      headers: gw.token ? { 'Authorization': `Bearer ${gw.token}` } : {},
      signal: AbortSignal.timeout(2000),
    });
    const reachable = health.ok;
    const online = reachable && gw.chatCompletionsEnabled;
    res.json({
      online,
      reachable,
      chatCompletionsEnabled: gw.chatCompletionsEnabled,
      port: gw.port,
      reason: !reachable
        ? 'gateway-unreachable'
        : !gw.chatCompletionsEnabled
          ? 'chat-completions-disabled'
          : null,
    });
  } catch {
    res.json({
      online: false,
      reachable: false,
      chatCompletionsEnabled: gw.chatCompletionsEnabled,
      port: gw.port,
      reason: 'gateway-unreachable',
    });
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
  // Never return the cleartext value. The HUD renders `masked` and `isSet`
  // only, and this endpoint enumerates every credential in .env on an
  // unauthenticated listener that binds all interfaces. To change a key the
  // operator types a new one; PUT /api/env never needs the old value echoed
  // back, so there is no consumer for the plaintext.
  const fields = mapping.env.map((key) => ({
    key,
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

// ── Budget status & configuration (spec 109) ──────────────────────────────────
//
// Budget enforcement lives in the token-tracker skill (Python, src/netclaw_tokens/).
// The HUD provides visibility and configuration — reading the current budget policy
// from openclaw.json and the active session's cost from the sessions directory.

app.get('/api/budget/status', (req, res) => {
  try {
    const config = JSON.parse(readText(path.join(process.env.HOME || '/root', '.openclaw', 'openclaw.json')) || '{}');
    const policy = resolveBudgetPolicy(config);

    // Find the most recent active session and estimate cost from its size/metadata
    const sessionCost = estimateActiveSessionCost();

    const pct = policy.sessionBudgetUsd > 0
      ? Math.min(100, Math.round((sessionCost / policy.sessionBudgetUsd) * 100))
      : 0;

    let status = 'ok';
    if (pct >= 100) status = 'halted';
    else if (pct >= 80) status = 'critical';
    else if (pct >= 50) status = 'warning';

    res.json({
      sessionCostUsd: Math.round(sessionCost * 100) / 100,
      sessionBudgetUsd: policy.sessionBudgetUsd,
      maxToolCallsPerTurn: policy.maxToolCallsPerTurn,
      percentUsed: pct,
      status,
      model: policy.model || null,
      interfaceDefaults: policy.interfaceDefaults || {},
    });
  } catch (err) {
    res.json({
      sessionCostUsd: 0,
      sessionBudgetUsd: 5.0,
      maxToolCallsPerTurn: 20,
      percentUsed: 0,
      status: 'unknown',
      error: err.message,
    });
  }
});

app.get('/api/budget/config', (req, res) => {
  try {
    const config = JSON.parse(readText(path.join(process.env.HOME || '/root', '.openclaw', 'openclaw.json')) || '{}');
    const budget = config?.agents?.defaults?.budget || {};
    const interfaceDefaults = config?.agents?.defaults?.interfaceDefaults || {};
    res.json({
      budget: {
        sessionBudgetUsd: budget.sessionBudgetUsd ?? 5.0,
        maxToolCallsPerTurn: budget.maxToolCallsPerTurn ?? 20,
        contextWarningTokens: budget.contextWarningTokens ?? 100000,
        allowOverride: budget.allowOverride ?? true,
        overrideIncrementUsd: budget.overrideIncrementUsd ?? 2.0,
      },
      interfaceDefaults,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/budget/config', (req, res) => {
  const { budget, interfaceDefaults } = req.body || {};
  if (!budget && !interfaceDefaults) {
    return res.status(400).json({ error: 'Expected { budget: {...} } and/or { interfaceDefaults: {...} }' });
  }

  try {
    const configPath = path.join(process.env.HOME || '/root', '.openclaw', 'openclaw.json');
    const config = JSON.parse(readText(configPath) || '{}');

    // Ensure path exists
    if (!config.agents) config.agents = {};
    if (!config.agents.defaults) config.agents.defaults = {};

    // Merge budget values (only provided fields, don't clobber unset ones)
    if (budget) {
      if (!config.agents.defaults.budget) config.agents.defaults.budget = {};
      const validKeys = ['sessionBudgetUsd', 'maxToolCallsPerTurn', 'contextWarningTokens', 'allowOverride', 'overrideIncrementUsd'];
      for (const key of validKeys) {
        if (budget[key] !== undefined) {
          config.agents.defaults.budget[key] = budget[key];
        }
      }
    }

    // Merge interface defaults
    if (interfaceDefaults) {
      if (!config.agents.defaults.interfaceDefaults) config.agents.defaults.interfaceDefaults = {};
      for (const [iface, settings] of Object.entries(interfaceDefaults)) {
        config.agents.defaults.interfaceDefaults[iface] = {
          ...(config.agents.defaults.interfaceDefaults[iface] || {}),
          ...settings,
        };
      }
    }

    fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + '\n');
    broadcastWS('config:updated', { keys: ['budget'], generatedAt: new Date().toISOString() });
    res.json({ ok: true, budget: config.agents.defaults.budget, interfaceDefaults: config.agents.defaults.interfaceDefaults });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * Resolve budget policy from config (mirrors Python budget_policy.py logic).
 * Returns merged defaults for display purposes.
 */
function resolveBudgetPolicy(config) {
  const defaults = config?.agents?.defaults || {};
  const budget = defaults.budget || {};
  const interfaceDefaults = defaults.interfaceDefaults || {};

  return {
    sessionBudgetUsd: parseFloat(process.env.NETCLAW_SESSION_BUDGET_USD || '') || budget.sessionBudgetUsd || 5.0,
    maxToolCallsPerTurn: budget.maxToolCallsPerTurn || 20,
    contextWarningTokens: budget.contextWarningTokens || 100000,
    allowOverride: budget.allowOverride !== false,
    overrideIncrementUsd: budget.overrideIncrementUsd || 2.0,
    model: null, // Global default; interface-specific in interfaceDefaults
    interfaceDefaults,
  };
}

/**
 * Estimate cost of the most recently active session by reading its JSONL
 * and summing any usage blocks. Returns 0 if no active session or no data.
 */
function estimateActiveSessionCost() {
  try {
    const sessionsDir = path.join(process.env.HOME || '/root', '.openclaw', 'agents', 'main', 'sessions');
    const sessionsJson = path.join(sessionsDir, 'sessions.json');
    if (!fs.existsSync(sessionsJson)) return 0;

    const sessions = JSON.parse(readText(sessionsJson) || '{}');
    // Find the most recently updated session
    let newest = null;
    let newestTime = 0;
    for (const [, sess] of Object.entries(sessions)) {
      const t = sess.updatedAt || 0;
      if (t > newestTime) {
        newestTime = t;
        newest = sess;
      }
    }

    if (!newest || !newest.sessionFile) return 0;
    if (!fs.existsSync(newest.sessionFile)) return 0;

    // Count message lines as a rough proxy for API calls
    // Real cost tracking comes from Prometheus; this is a fast HUD estimate
    const content = readText(newest.sessionFile) || '';
    const lines = content.split('\n').filter(Boolean);
    let assistantTurns = 0;
    for (const line of lines) {
      try {
        const entry = JSON.parse(line);
        if (entry.type === 'message' && entry.message?.role === 'assistant') {
          assistantTurns++;
        }
      } catch { /* skip unparseable lines */ }
    }

    // Rough estimate: each assistant turn ≈ 50K input tokens on Sonnet ($0.15) + 1K output ($0.015)
    // This is intentionally conservative — better to show slightly high than low
    const estimatedCostPerTurn = 0.17;
    return assistantTurns * estimatedCostPerTurn;
  } catch {
    return 0;
  }
}

// ── Testbed device config ──────────────────────────────────────────
app.get('/api/testbed/raw', (req, res) => {
  res.type('text/yaml').send(readText(TESTBED_FILE) || '# No testbed found');
});

// ── Layout persistence (feature 102, US3) ────────────────────────────────────
//
// SCOPED EXCEPTION. Specs 072 and 101 both forbade changing server.js; the operator
// chose server-side persistence so a layout follows them across browsers. FR-032
// narrows the exception to these three routes — /api/n2n and /api/graph are
// untouched — and this is a new route in an existing pattern, since the server
// already accepts writes (PUT /api/env, PUT /api/testbed/raw).
//
// Validation is the SHARED pure module, so the browser cannot construct a payload
// the server would reject and vice versa. A second validator here would drift from
// the client's within a release.
import { validateLayout } from './src/orgchart/layout-payload.js';

// FR-034: a module constant. No path component may derive from a request.
const LAYOUT_FILE = path.join(os.homedir(), '.openclaw', 'netclaw-hud-layout.json');
const LAYOUT_MAX_BYTES = 256 * 1024;

app.get('/api/layout', (req, res) => {
  // Absence is a normal first-run condition, NOT an error — making the client
  // distinguish 404-means-none from 404-means-broken is a needless trap.
  try {
    if (!fs.existsSync(LAYOUT_FILE)) return res.json({ version: 1, empty: true });
    const raw = fs.readFileSync(LAYOUT_FILE, 'utf8');
    const parsed = JSON.parse(raw);
    const check = validateLayout(parsed);
    if (!check.ok) {
      // FR-019: fall back to computed AND say so. A 500 would be indistinguishable
      // from the server being down, and the HUD would render identically either way.
      return res.json({ version: 1, empty: true, warning: `saved layout rejected: ${check.error}` });
    }
    return res.json(parsed);
  } catch (e) {
    return res.json({ version: 1, empty: true, warning: `saved layout unreadable: ${e.message}` });
  }
});

app.put('/api/layout', (req, res) => {
  const body = req.body;
  // FR-033: bound per-route. The global express.json({limit:'4mb'}) is far too
  // permissive for a layout file and must not be relied on as the bound.
  const size = JSON.stringify(body ?? null).length;
  if (size > LAYOUT_MAX_BYTES) {
    return res.status(400).json({ error: `payload ${size} bytes exceeds ${LAYOUT_MAX_BYTES}` });
  }
  const check = validateLayout(body);
  if (!check.ok) return res.status(400).json({ error: check.error });

  // Validate before touching disk, then write atomically: a crash mid-write must not
  // leave a truncated file that fails every subsequent read.
  try {
    fs.mkdirSync(path.dirname(LAYOUT_FILE), { recursive: true });
    const tmp = `${LAYOUT_FILE}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(body, null, 2), 'utf8');
    fs.renameSync(tmp, LAYOUT_FILE);
    return res.json({ saved: true, savedAt: new Date().toISOString() });
  } catch (e) {
    return res.status(507).json({ error: `write failed: ${e.message}` });
  }
});

app.delete('/api/layout', (req, res) => {
  // FR-017: discardable. Without this a bad saved layout is unremovable from the UI,
  // since "reset to computed" only covers the current session.
  try {
    if (fs.existsSync(LAYOUT_FILE)) fs.unlinkSync(LAYOUT_FILE);
    return res.json({ discarded: true });
  } catch (e) {
    return res.status(507).json({ error: `discard failed: ${e.message}` });
  }
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
const CHAT_CONTEXT_LIMIT = 40;

function normalizeChatContent(content) {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return null;

  const parts = content.flatMap((part) => {
    if (!part || typeof part !== 'object') return [];
    if (part.type === 'text' && typeof part.text === 'string') {
      return [{ type: 'text', text: part.text }];
    }
    const imageUrl = part.type === 'image_url' && part.image_url?.url;
    if (typeof imageUrl === 'string') {
      return [{ type: 'image_url', image_url: { url: imageUrl } }];
    }
    return [];
  });

  return parts.length ? parts : null;
}

function normalizeChatContext(messages) {
  if (!Array.isArray(messages)) return null;

  const normalized = messages.slice(-CHAT_CONTEXT_LIMIT).flatMap((entry) => {
    if (!entry || (entry.role !== 'user' && entry.role !== 'assistant')) return [];
    const content = normalizeChatContent(entry.content);
    return content == null ? [] : [{ role: entry.role, content }];
  });

  return normalized.length ? normalized : null;
}

function textFromChatContent(content) {
  if (typeof content === 'string') return content.trim();
  if (!Array.isArray(content)) return '';
  return content
    .filter((part) => part?.type === 'text' && typeof part.text === 'string')
    .map((part) => part.text)
    .join('\n')
    .trim();
}

// Read OpenClaw gateway config for auth
function getGatewayConfig() {
  try {
    const configPath = path.join(process.env.HOME || '/root', '.openclaw', 'openclaw.json');
    const config = JSON.parse(readText(configPath));
    return {
      port: config?.gateway?.port || 18789,
      token: config?.gateway?.auth?.token || '',
      chatCompletionsEnabled:
        config?.gateway?.http?.endpoints?.chatCompletions?.enabled === true,
    };
  } catch {
    return { port: 18789, token: '', chatCompletionsEnabled: false };
  }
}

app.post('/api/chat', async (req, res) => {
  const { message, messages } = req.body || {};
  const contextMessages = normalizeChatContext(messages);
  const latestContextMessage = contextMessages
    ? [...contextMessages].reverse().find((entry) => entry.role === 'user')
    : null;
  const contextText = textFromChatContent(latestContextMessage?.content);
  const userMessage = typeof message === 'string' && message.trim()
    ? message.trim()
    : contextText;

  if (!userMessage && !latestContextMessage) {
    return res.status(400).json({
      error: 'Expected { message: "..." } or { messages: [{ role, content }] }',
    });
  }

  const timestamp = new Date().toISOString();
  const historyText = userMessage || '[attachment]';
  chatHistory.push({ role: 'user', text: historyText, timestamp });

  // Analyze the message to determine which integrations/skills are relevant
  const graph = buildGraph();
  const activations = resolveActivations(historyText, graph);

  // Broadcast activation events to all WS clients so the 3D scene lights up
  broadcastWS('chat:activations', {
    message: historyText,
    activations,
    timestamp,
  });

  // Try to proxy through the real OpenClaw gateway with streaming
  let responseText = '';
  let fromGateway = false;
  const gw = getGatewayConfig();
  let gatewayFallback = gw.chatCompletionsEnabled
    ? 'OpenClaw gateway could not complete the chat request. Check the gateway terminal for details.'
    : 'OpenClaw is reachable, but its chat compatibility endpoint is disabled. Run `openclaw config set gateway.http.endpoints.chatCompletions.enabled true`, then restart the gateway.';

  try {
    if (!gw.chatCompletionsEnabled) throw new Error('chat-completions-disabled');
    const gwRes = await fetch(`http://127.0.0.1:${gw.port}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${gw.token}`,
        'Content-Type': 'application/json',
        'x-openclaw-agent-id': 'main',
      },
      body: JSON.stringify({
        model: 'openclaw',
        // Existing clients keep the shared linear history. Compatibility
        // clients can supply an isolated branch history, which prevents turns
        // from sibling branches (or other browser tabs) bleeding together.
        messages: contextMessages || chatHistory
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
    } else {
      gatewayFallback = `OpenClaw rejected the chat request (HTTP ${gwRes.status}). Check the gateway terminal for details.`;
    }
  } catch (error) {
    if (error?.message !== 'chat-completions-disabled') {
      gatewayFallback = 'OpenClaw gateway could not complete the chat request. Check the gateway terminal for details.';
    }
  }

  if (!responseText) {
    responseText = buildChatResponse(historyText, activations, graph, gatewayFallback);
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
    gatewayIssue: fromGateway ? null : gatewayFallback,
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
    'firewall': ['asa', 'fmc', 'paloalto', 'fortinet', 'checkpoint'],
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

function buildChatResponse(message, activations, graph, gatewayMessage) {
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
  response += `\n\n${gatewayMessage || 'OpenClaw gateway is offline. Run `openclaw gateway run` to enable live responses and tool execution.'}`;

  return response;
}

// ============================================================
// RAG Knowledge Base (Feature 062) — /api/rag/* + WS rag_* events
// All reads and mutations go through rag-mcp tools via the
// mcp-call.py child-process helper (one uniform access path).
// ============================================================
const RAG_MCP_CALL = path.join(ROOT, 'scripts', 'mcp-call.py');
const RAG_SERVER_CMD = `python3 -u ${path.join(ROOT, 'mcp-servers', 'rag-mcp', 'rag_mcp_server.py')}`;
const RAG_DATA_DIR = process.env.RAG_DATA_DIR
  ? process.env.RAG_DATA_DIR.replace(/^~/, os.homedir())
  : path.join(os.homedir(), '.openclaw', 'rag');
const RAG_INTAKE_DIR = path.join(RAG_DATA_DIR, 'intake');
const RAG_MAX_DOC_MB = parseInt(process.env.RAG_MAX_DOC_MB || '100', 10);
const RAG_SUPPORTED_EXT = ['.pdf', '.md', '.markdown', '.html', '.htm', '.txt',
  '.docx', '.xlsx', '.pptx', '.vsdx', '.doc', '.xls', '.ppt', '.vsd'];

function callRagTool(tool, args = {}, timeoutSec = 300) {
  return new Promise((resolve, reject) => {
    execFile(
      'python3',
      [RAG_MCP_CALL, RAG_SERVER_CMD, tool, JSON.stringify(args)],
      {
        timeout: (timeoutSec + 30) * 1000,
        maxBuffer: 64 * 1024 * 1024,
        env: { ...process.env, MCP_CALL_TIMEOUT: String(timeoutSec) },
      },
      (err, stdout, stderr) => {
        if (err) return reject(new Error(stderr || err.message));
        try {
          const result = JSON.parse(stdout);
          // FastMCP: prefer structuredContent, else the JSON text content block
          const payload = result.structuredContent
            || (result.content && result.content[0] && JSON.parse(result.content[0].text))
            || result;
          resolve(payload);
        } catch (parseErr) {
          reject(new Error(`Unparseable rag-mcp response: ${parseErr.message}`));
        }
      }
    );
  });
}

// Progress poller: while any ingest is non-terminal, poll rag_list and
// broadcast per-document status transitions over /ws (FR-062).
let ragPollTimer = null;
const ragLastStatus = new Map();

function ragStartProgressPolling() {
  if (ragPollTimer) return;
  ragPollTimer = setInterval(async () => {
    try {
      const listing = await callRagTool('rag_list', {}, 60);
      const docs = [...(listing.data?.documents || []), ...(listing.data?.snapshots || [])];
      let anyPending = false;
      for (const doc of docs) {
        const prev = ragLastStatus.get(doc.id);
        if (prev !== doc.ingest_status) {
          ragLastStatus.set(doc.id, doc.ingest_status);
          broadcastWS('rag_progress', {
            document_id: doc.id,
            title: doc.title,
            status: doc.ingest_status,
            error: doc.error || null,
          });
        }
        if (!['ready', 'error'].includes(doc.ingest_status)) anyPending = true;
      }
      if (!anyPending) {
        clearInterval(ragPollTimer);
        ragPollTimer = null;
        broadcastWS('rag_update', { documents_changed: true });
      }
    } catch {
      clearInterval(ragPollTimer);
      ragPollTimer = null;
    }
  }, 3000);
}

app.get('/api/rag/documents', async (req, res) => {
  try {
    const result = await callRagTool('rag_list', {}, 60);
    if (!result.success) return res.status(500).json(result.error);
    res.json(result.data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/rag/stats', async (req, res) => {
  try {
    const result = await callRagTool('rag_stats', {}, 60);
    if (!result.success) return res.status(500).json(result.error);
    res.json(result.data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const ragUpload = multer({
  storage: multer.diskStorage({
    destination: (req, file, cb) => {
      fs.mkdirSync(RAG_INTAKE_DIR, { recursive: true });
      cb(null, RAG_INTAKE_DIR);
    },
    filename: (req, file, cb) => cb(null, path.basename(file.originalname)),
  }),
  limits: { fileSize: RAG_MAX_DOC_MB * 1024 * 1024 },
});

app.post('/api/rag/upload', (req, res) => {
  ragUpload.single('file')(req, res, async (err) => {
    if (err) {
      if (err.code === 'LIMIT_FILE_SIZE') {
        return res.status(413).json({
          error: `File exceeds the ${RAG_MAX_DOC_MB} MB cap. Raise RAG_MAX_DOC_MB in .env to override.`,
        });
      }
      return res.status(500).json({ error: err.message });
    }
    if (!req.file) return res.status(400).json({ error: 'No file supplied (field name: file).' });

    const ext = path.extname(req.file.originalname).toLowerCase();
    if (!RAG_SUPPORTED_EXT.includes(ext)) {
      fs.unlink(req.file.path, () => {});
      return res.status(415).json({
        error: `'${ext}' is not supported. Supported: ${RAG_SUPPORTED_EXT.join(', ')}`,
      });
    }

    const docType = req.body.doc_type || 'other';
    const title = req.body.title || null;
    res.status(202).json({ status: 'pending', filename: req.file.originalname });
    ragStartProgressPolling();

    try {
      const result = await callRagTool('rag_ingest', {
        file_path: req.file.path,
        doc_type: docType,
        ...(title ? { title } : {}),
        source: `hud:${req.file.originalname}`,
      }, 600);
      if (result.success) {
        broadcastWS('rag_progress', {
          document_id: result.data.document_id,
          title: result.data.title,
          status: 'ready',
          error: null,
        });
      } else {
        broadcastWS('rag_progress', {
          document_id: null,
          title: req.file.originalname,
          status: 'error',
          error: result.error?.message || 'ingest failed',
        });
      }
    } catch (ingestErr) {
      broadcastWS('rag_progress', {
        document_id: null,
        title: req.file.originalname,
        status: 'error',
        error: ingestErr.message,
      });
    }
    broadcastWS('rag_update', { documents_changed: true });
  });
});

app.delete('/api/rag/documents/:id', async (req, res) => {
  if (req.body?.confirm !== true) {
    return res.status(400).json({ error: 'Deletion requires {"confirm": true} (destructive operation).' });
  }
  try {
    const result = await callRagTool('rag_delete', { document_id: req.params.id, confirmed: true }, 120);
    if (!result.success) {
      const status = result.error?.code === 'NOT_FOUND' ? 404 : 500;
      return res.status(status).json(result.error);
    }
    broadcastWS('rag_update', { documents_changed: true });
    res.json(result.data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/rag/documents/:id/reindex', async (req, res) => {
  if (req.body?.confirm !== true) {
    return res.status(400).json({ error: 'Re-index requires {"confirm": true}.' });
  }
  try {
    const result = await callRagTool('rag_reindex', { document_id: req.params.id, confirmed: true }, 600);
    if (!result.success) {
      const status = result.error?.code === 'NOT_FOUND' ? 404 : 500;
      return res.status(status).json(result.error);
    }
    broadcastWS('rag_update', { documents_changed: true });
    res.json(result.data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

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
