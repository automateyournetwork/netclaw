#!/usr/bin/env bash
# NetClaw installer — component catalog and install profiles.
# Format: "id|Category|Name|Short description"
# The install function for id "foo-bar" is component_install_foo_bar()
# in lib/install-steps.sh. Order here = display order in the checklist.

CATALOG=(
    "pyats|Device Automation|Cisco pyATS|Cisco device CLI + Genie parsers (core device automation)"
    "junos|Device Automation|Juniper JunOS|PyEZ/NETCONF CLI, config mgmt, Jinja2 templates (10 tools)"
    "arista-cvp|Device Automation|Arista CloudVision|Device inventory, events, connectivity monitor, tags (4 tools)"
    "f5|Device Automation|F5 BIG-IP|iControl REST — virtuals, pools, iRules"
    "catc|Device Automation|Cisco Catalyst Center (read-only)|All 514 read-only API operations behind 8 grouped dispatchers. Official Cisco catalogue, Apache-2.0. An empty inventory is not an empty network"
    "aruba-cx|Device Automation|Aruba CX|Switch management — 16 tools (11 read, 5 write)"
    "gnmi|Device Automation|gNMI Telemetry|Streaming telemetry — Get/Set/Subscribe, YANG (bundled)"
    "radkit|Device Automation|Cisco RADKit|Cloud-relayed remote CLI, SNMP, inventory (5 tools)"
    "multivendor-cli|Device Automation|Multivendor CLI Driver|Nornir/NAPALM/Netmiko — ~90 platform families Cisco/Juniper servers cannot reach (read-only)"

    "percepxion|Out-of-Band|Lantronix Percepxion|Fleet-wide OOB console-server SaaS — device inventory, firmware compliance/rollout, config mgmt, Smart Groups, security audit, async CLI dispatch (37 tools, external/on-demand)"
    "slc|Out-of-Band|Lantronix SLC direct|Direct, synchronous single-device OOB console-server access — port status, session mgmt, sync CLI output, cellular status (37 tools, external/on-demand)"

    "netbox|Source of Truth|NetBox|DCIM/IPAM source of truth (read-write)"
    "nautobot|Source of Truth|Nautobot|IPAM — IPs, prefixes, VRF/tenant/site (5 tools)"
    "nautobot-golden-config|Source of Truth|Nautobot Golden Config|Golden-config compliance job runner for Nautobot"
    "nautobot-routing|Source of Truth|Nautobot Routing|BGP/routing data queries against Nautobot"
    "infrahub|Source of Truth|OpsMill Infrahub|Schema-driven SoT, branch-isolated writes (10 tools)"
    "infoblox|Source of Truth|Infoblox DDI|DNS records, DHCP scopes/leases, IPAM utilization"

    "aci|Fabric & Orchestration|Cisco ACI|APIC fabric management"
    "nso|Fabric & Orchestration|Cisco NSO|Device config, sync, services via RESTCONF (Python 3.12+)"
    "itential|Fabric & Orchestration|Itential IAP|Config mgmt, compliance, workflows, golden config (65+ tools)"
    "meraki|Fabric & Orchestration|Cisco Meraki|Official remote MCP — 494 read-only Dashboard capabilities via 2 tools"
    "nsm|Observability & Telemetry|Zeek + Suricata NSM|Offline PCAP analysis — session metadata and IDS alerting (6 tools)"
    "analysis|Observability & Telemetry|DuckDB Analysis|Read-only SQL over exported network data, sandboxed (3 tools)"
    "redfish|Observability & Telemetry|Redfish BMC|Out-of-band hardware health, thermal/power, firmware, SEL (6 tools, read-only)"
    "anta|Observability & Telemetry|Arista ANTA Validation|Structured network-state validation for EOS — 208 tests behind 4 tools, read-only. A test for a feature the device does not run reports not_applicable, never a failure"
    "elastic|Observability & Telemetry|Elasticsearch Logs|Log search over an existing Elasticsearch 8.x/9.x (5 tools, read-only). Counts go through ESQL — a search total silently caps at 10,000 and reads as exact"
    "sdwan|Fabric & Orchestration|Cisco SD-WAN|vManage read-only monitoring (12 tools)"
    "prisma-sdwan|Fabric & Orchestration|Prisma SD-WAN|Palo Alto SASE — sites, topology, alarms (15+ tools)"
    "aap|Fabric & Orchestration|Ansible Automation Platform|Controller, EDA, ansible-lint, Red Hat docs (4 servers)"

    "ise|Security|Cisco ISE|Identity, posture, TrustSec"
    "fmc|Security|Cisco FMC|Secure Firewall policy search, FTD targeting"
    "panorama|Security|Palo Alto Panorama|Device groups, templates, policy, commit validation"
    "fortinet|Security|Fortinet (FortiManager/FortiGate/FortiAnalyzer)|Three planes: policy intent, device state, traffic logs. Read-only default, gated writes"
    "checkpoint|Security|Check Point|Policy, threat intel, gateway, SASE (15 servers, interactive)"
    "zscaler|Security|Zscaler|Zero Trust — ZIA, ZPA, ZDX (remote, 300+ tools)"
    "claroty|Security|Claroty xDome|OT/IoT/IoMT assets, alerts, vulns (bundled, 21 tools)"
    "nvd-cve|Security|NVD CVE|NIST vulnerability database lookups"
    "cisco-psirt|Security|Cisco PSIRT Advisories|Is a running version affected? IOS/XE/NX-OS/ASA/FTD/FMC/ACI (6 tools)"
    "nmap|Security|nmap Scanning|Host discovery, port/service/OS scanning (14 tools)"
    "fwrule|Security|Firewall Rule Analyzer|Multi-vendor overlap/shadowing/conflict analysis (9 vendors)"

    "aws|Cloud|AWS|VPC, Transit GW, CloudWatch, IAM, CloudTrail, costs (6 servers)"
    "azure|Cloud|Azure Network|VNets, NSGs, ExpressRoute, VPN, Firewall, LB, DNS (bundled)"
    "gcp|Cloud|Google Cloud|Compute, Monitoring, Logging, Resource Manager (4 remote)"
    "cloudflare|Cloud|Cloudflare|DNS analytics, security, Zero Trust, Workers (remote)"
    "terraform|Cloud|Terraform Cloud|Workspaces, runs, state, variables (remote)"
    "vault|Cloud|HashiCorp Vault|KV, PKI, transit, auth methods (remote)"

    "grafana|Observability|Grafana|Dashboards, Prometheus, Loki, alerting, OnCall (75+ tools)"
    "prometheus|Observability|Prometheus|PromQL queries, metric discovery, target health (6 tools)"
    "datadog|Observability|Datadog|Logs, metrics, incidents, APM (remote, 16+ tools)"
    "splunk|Observability|Splunk|SPL search, indexes, saved searches, alerts (30 tools)"
    "pagerduty|Observability|PagerDuty|Incidents, on-call schedules, services (70 tools)"
    "te-community|Observability|ThousandEyes (community)|Tests, agents, path vis, dashboards (9 tools)"
    "te-official|Observability|ThousandEyes (official)|Alerts, outages, BGP, instant tests (remote, ~20 tools)"
    "ipfabric|Observability|IP Fabric|Health assessment, path analysis, diagrams (interactive)"
    "forward|Observability|Forward Networks|Snapshot assurance, path search, NQE (Go 1.25+, interactive)"
    "suzieq|Observability|SuzieQ|Network state queries, assertions, path tracing (bundled)"
    "kubeshark|Observability|Kubeshark|K8s L4/L7 traffic analysis, TLS decryption (remote)"
    "gtrace|Observability|gtrace|Traceroute (MPLS/ECMP/NAT), MTR, GlobalPing, ASN, geo (6 tools)"
    "k8s|Observability|Kubernetes (read-only)|Pods, services, ingresses, EndpointSlices and NetworkPolicies. Strictly read-only, Secrets denied. An empty list is not evidence of absence — the server narrows silently on insufficient RBAC"
    "zabbix|Observability|Zabbix SNMP-Poller NMS|Polled metric history, problems and device availability from a self-hosted Zabbix. Read-only. Answers what something WAS doing over time — the layer NetClaw had no source for"
    "bgp-intel|Observability|BGP & Registry Intelligence|RPKI origin validation, RDAP ownership, PeeringDB peering, routing visibility (public APIs, no credentials)"
    "globalping|Observability|Globalping|Outside-in measurement from ~4800 global probes — ping, traceroute, DNS, MTR, HTTP (remote, no install)"
    "telemetry-receivers|Observability|Telemetry Receivers|SNMP trap, syslog, IPFIX/NetFlow receivers over UDP (3 servers)"
    "auvik|Observability|Auvik|Read-only network monitoring — inventory, alerts, lifecycle, performance (bundled, 20 tools)"

    "cml|Labs & Simulation|Cisco CML|Lab lifecycle, topology, packet capture (Python 3.12+)"
    "gns3|Labs & Simulation|GNS3|Projects, nodes, links, templates, snapshots, packet capture (23 tools)"
    "containerlab|Labs & Simulation|ContainerLab|Containerized labs — SR Linux, cEOS, FRR"
    "batfish|Labs & Simulation|Batfish|Offline config analysis, reachability, ACL trace (bundled)"
    "protocol|Labs & Simulation|Protocol MCP|Live BGP/OSPF peering + GRE tunnels (10 tools)"
    "peering|Labs & Simulation|Protocol Peering Wizard|Configure BGP/OSPF participation + NetClaw Mesh (interactive)"
    "n2n|Labs & Simulation|N2N Federation|Peer NetClaws: capability exchange, remote tool/skill invocation, claw-to-claw chat"
    "in2n-production|Labs & Simulation|iN2N Production Enforcement|Enforce production mode (OpenShell sandbox, DefenseClaw guard, GAIT audit) + durable systemd services with honest posture"
    "claw-certs|Labs & Simulation|Claw Certification|TLS channel security for N2N: mutual auth, risk CA hub attestation, ACME domain identity + automatic cert rotation"

    "servicenow|ITSM & DevOps|ServiceNow|Incidents, changes, CMDB"
    "github|ITSM & DevOps|GitHub|Issues, PRs, code search, Actions (Docker)"
    "gitlab|ITSM & DevOps|GitLab|Projects, MRs, issues via @zereight/mcp-gitlab"
    "jenkins|ITSM & DevOps|Jenkins|Jobs and builds via Jenkins MCP Server plugin (remote)"
    "atlassian|ITSM & DevOps|Atlassian|Jira + Confluence (Cloud and Server/DC)"
    "msgraph|ITSM & DevOps|Microsoft Graph|OneDrive, SharePoint, Visio, Teams"
    "halo|ITSM & DevOps|HaloPSA / HaloITSM|Change requests (gated) + asset/ticket context (bundled, 18 tools)"

    "packet-buddy|Analysis & Diagrams|Packet Buddy|pcap/pcapng analysis via tshark"
    "markmap|Analysis & Diagrams|Markmap|Mind map visualization"
    "drawio-rfc|Analysis & Diagrams|Draw.io + RFC|Topology diagrams + IETF RFC lookup (npx, no install)"
    "uml|Analysis & Diagrams|UML Diagrams|27+ diagram types via Kroki"
    "subnet-calc|Analysis & Diagrams|Subnet Calculator|IPv4 + IPv6 CIDR calculator"
    "wikipedia|Analysis & Diagrams|Wikipedia|Technology context and history"
    "devnet-content-search|Analysis & Diagrams|DevNet Content Search|Cisco DevNet API doc search — Meraki, Catalyst Center (remote, 3 tools)"
    "blender|Analysis & Diagrams|Blender 3D|3D network topology rendering (requires Blender)"
    "ue5|Analysis & Diagrams|Unreal Engine 5|3D digital twin (requires UE5.8+ with MCP plugin)"
    "threejs-viz|Analysis & Diagrams|Three.js Network Viz|Browser-based 3D topology, no desktop app/GPU (optional Sketchfab real-stencil mode)"
    "comfyui-viz|Analysis & Diagrams|ComfyUI Topology Visualization|AI-generated stylized topology stills via a self-hosted ComfyUI instance"
    "worldlabs-marble|Analysis & Diagrams|World Labs Fantastical Topology Viz|Free themed prompt preview + (credits-spending, confirmation-gated) explorable 3D world generation via World Labs Marble (spec 122)"
    "chrome-devtools|Analysis & Diagrams|Chrome DevTools|Browser automation/inspection — visualization QA, controller GUI gap-fill, API discovery, Watch Mode (2 servers)"
    "computer-use|Analysis & Diagrams|Computer Use|Full-desktop automation for API-less/browser-less targets — Xvfb+XFCE virtual desktop, 17 actions, VNC Watch Mode (via ClawHub)"

    "tts|Voice & Social|Text-to-Speech|edge-tts voice replies for Slack/WebEx (2 tools)"
    "twitter|Voice & Social|Twitter/X|Tweet posting, threads, heartbeat (bundled)"
    "twilio|Voice & Social|Twilio|Core API (SMS/messaging) plus bidirectional voice calls, emergency alerts (2 servers)"
    "zoom-rtms|Voice & Social|Zoom Meeting Intelligence|Realtime Media Streams meeting listener, live investigation routing, Zoom App panel + camera-overlay avatar (spec 118, 9 tools)"

    "gait|Platform Services|GAIT Audit Trail|Git-based AI audit trail (recommended for all installs)"
    "mempalace|Platform Services|MemPalace Memory|Local AI memory — 19 tools, no API keys"
    "memory-mcp|Platform Services|Memory MCP|Hybrid persistent memory — structured facts (SQLite), semantic search (ChromaDB), decision log"
    "document|Platform Services|Document Generation|Change-record .docx, audit .xlsx, exec .pptx and PDF form filling from real NetClaw data — per-element provenance, never fabricates a blank"
    "rag-mcp|Platform Services|RAG Knowledge Base|Offline document knowledge base — hybrid retrieval, citations, opt-in snapshots (ChromaDB + BM25 + local reranker)"
    "ollama|Platform Services|Ollama Domain Experts|Delegates structured tasks to local Ollama models on your own GPU (10 tools)"
    "humanrail|Platform Services|HumanRail|Human-in-the-loop escalation and approvals"
)

catalog_field() {
    # catalog_field <id> <n>   (2=category 3=name 4=description)
    local id="$1" n="$2" entry
    for entry in "${CATALOG[@]}"; do
        if [ "${entry%%|*}" = "$id" ]; then
            echo "$entry" | cut -d'|' -f"$n"
            return 0
        fi
    done
    return 1
}

catalog_ids() {
    local entry
    for entry in "${CATALOG[@]}"; do echo "${entry%%|*}"; done
}

catalog_has() {
    local id="$1" entry
    for entry in "${CATALOG[@]}"; do
        [ "${entry%%|*}" = "$id" ] && return 0
    done
    return 1
}

# ── profiles ─────────────────────────────────────────────────────
PROFILE_MINIMAL="pyats gait subnet-calc drawio-rfc"

PROFILE_RECOMMENDED="bgp-intel pyats gait netbox servicenow nvd-cve subnet-calc wikipedia markmap \
drawio-rfc uml packet-buddy nmap gtrace globalping suzieq batfish protocol n2n tts chrome-devtools rag-mcp document"

PROFILE_CISCO="pyats gait netbox servicenow aci ise catc meraki sdwan cml fmc \
radkit te-community te-official nvd-cve cisco-psirt subnet-calc drawio-rfc uml packet-buddy"

PROFILE_MULTIVENDOR="pyats junos anta arista-cvp aruba-cx f5 fortinet multivendor-cli netbox nautobot gait servicenow \
fwrule subnet-calc drawio-rfc uml packet-buddy percepxion slc"

PROFILE_CLOUD="aws azure gcp cloudflare terraform vault github gait drawio-rfc uml subnet-calc"

PROFILE_SECURITY="ise fmc panorama fortinet bgp-intel checkpoint claroty zscaler nvd-cve cisco-psirt nmap \
fwrule gait servicenow"

PROFILE_LABS="cml containerlab batfish protocol peering n2n in2n-production suzieq gait subnet-calc drawio-rfc uml"

PROFILE_OBSERVABILITY="grafana prometheus datadog splunk pagerduty te-community te-official \
suzieq kubeshark gtrace globalping auvik gait zabbix k8s elastic anta"

profile_components() {
    case "$1" in
        minimal)        echo "$PROFILE_MINIMAL" ;;
        recommended)    echo "$PROFILE_RECOMMENDED" ;;
        cisco)          echo "$PROFILE_CISCO" ;;
        multivendor)    echo "$PROFILE_MULTIVENDOR" ;;
        cloud)          echo "$PROFILE_CLOUD" ;;
        security)       echo "$PROFILE_SECURITY" ;;
        labs)           echo "$PROFILE_LABS" ;;
        observability)  echo "$PROFILE_OBSERVABILITY" ;;
        full)           catalog_ids | tr '\n' ' ' ;;
        *)              return 1 ;;
    esac
}

PROFILE_NAMES="minimal recommended cisco multivendor cloud security labs observability full"
