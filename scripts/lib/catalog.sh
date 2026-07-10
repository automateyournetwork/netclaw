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
    "catalyst-center|Device Automation|Cisco Catalyst Center|DNA Center — devices, clients, sites"
    "aruba-cx|Device Automation|Aruba CX|Switch management — 16 tools (11 read, 5 write)"
    "gnmi|Device Automation|gNMI Telemetry|Streaming telemetry — Get/Set/Subscribe, YANG (bundled)"
    "radkit|Device Automation|Cisco RADKit|Cloud-relayed remote CLI, SNMP, inventory (5 tools)"

    "netbox|Source of Truth|NetBox|DCIM/IPAM source of truth (read-write)"
    "nautobot|Source of Truth|Nautobot|IPAM — IPs, prefixes, VRF/tenant/site (5 tools)"
    "nautobot-golden-config|Source of Truth|Nautobot Golden Config|Golden-config compliance job runner for Nautobot"
    "nautobot-routing|Source of Truth|Nautobot Routing|BGP/routing data queries against Nautobot"
    "infrahub|Source of Truth|OpsMill Infrahub|Schema-driven SoT, branch-isolated writes (10 tools)"
    "infoblox|Source of Truth|Infoblox DDI|DNS records, DHCP scopes/leases, IPAM utilization"

    "aci|Fabric & Orchestration|Cisco ACI|APIC fabric management"
    "nso|Fabric & Orchestration|Cisco NSO|Device config, sync, services via RESTCONF (Python 3.12+)"
    "itential|Fabric & Orchestration|Itential IAP|Config mgmt, compliance, workflows, golden config (65+ tools)"
    "meraki|Fabric & Orchestration|Cisco Meraki|Dashboard API (~804 endpoints)"
    "sdwan|Fabric & Orchestration|Cisco SD-WAN|vManage read-only monitoring (12 tools)"
    "prisma-sdwan|Fabric & Orchestration|Prisma SD-WAN|Palo Alto SASE — sites, topology, alarms (15+ tools)"
    "aap|Fabric & Orchestration|Ansible Automation Platform|Controller, EDA, ansible-lint, Red Hat docs (4 servers)"

    "ise|Security|Cisco ISE|Identity, posture, TrustSec"
    "fmc|Security|Cisco FMC|Secure Firewall policy search, FTD targeting"
    "panorama|Security|Palo Alto Panorama|Device groups, templates, policy, commit validation"
    "fortimanager|Security|FortiManager|ADOM inventory, policy packages, install preview"
    "checkpoint|Security|Check Point|Policy, threat intel, gateway, SASE (15 servers, interactive)"
    "zscaler|Security|Zscaler|Zero Trust — ZIA, ZPA, ZDX (remote, 300+ tools)"
    "claroty|Security|Claroty xDome|OT/IoT/IoMT assets, alerts, vulns (bundled, 21 tools)"
    "nvd-cve|Security|NVD CVE|NIST vulnerability database lookups"
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
    "telemetry-receivers|Observability|Telemetry Receivers|SNMP trap, syslog, IPFIX/NetFlow receivers over UDP (3 servers)"

    "cml|Labs & Simulation|Cisco CML|Lab lifecycle, topology, packet capture (Python 3.12+)"
    "gns3|Labs & Simulation|GNS3|Projects, nodes, links, templates, snapshots, packet capture (23 tools)"
    "containerlab|Labs & Simulation|ContainerLab|Containerized labs — SR Linux, cEOS, FRR"
    "batfish|Labs & Simulation|Batfish|Offline config analysis, reachability, ACL trace (bundled)"
    "protocol|Labs & Simulation|Protocol MCP|Live BGP/OSPF peering + GRE tunnels (10 tools)"
    "peering|Labs & Simulation|Protocol Peering Wizard|Configure BGP/OSPF participation + NetClaw Mesh (interactive)"
    "n2n|Labs & Simulation|N2N Federation|Peer NetClaws: capability exchange, remote tool/skill invocation, claw-to-claw chat"

    "servicenow|ITSM & DevOps|ServiceNow|Incidents, changes, CMDB"
    "github|ITSM & DevOps|GitHub|Issues, PRs, code search, Actions (Docker)"
    "gitlab|ITSM & DevOps|GitLab|Projects, MRs, issues via @zereight/mcp-gitlab"
    "jenkins|ITSM & DevOps|Jenkins|Jobs and builds via Jenkins MCP Server plugin (remote)"
    "atlassian|ITSM & DevOps|Atlassian|Jira + Confluence (Cloud and Server/DC)"
    "msgraph|ITSM & DevOps|Microsoft Graph|OneDrive, SharePoint, Visio, Teams"

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
    "chrome-devtools|Analysis & Diagrams|Chrome DevTools|Browser automation/inspection — visualization QA, controller GUI gap-fill, API discovery, Watch Mode (2 servers)"
    "computer-use|Analysis & Diagrams|Computer Use|Full-desktop automation for API-less/browser-less targets — Xvfb+XFCE virtual desktop, 17 actions, VNC Watch Mode (via ClawHub)"

    "tts|Voice & Social|Text-to-Speech|edge-tts voice replies for Slack/WebEx (2 tools)"
    "twitter|Voice & Social|Twitter/X|Tweet posting, threads, heartbeat (bundled)"
    "twilio|Voice & Social|Twilio|Core API (SMS/messaging) plus bidirectional voice calls, emergency alerts (2 servers)"

    "gait|Platform Services|GAIT Audit Trail|Git-based AI audit trail (recommended for all installs)"
    "mempalace|Platform Services|MemPalace Memory|Local AI memory — 19 tools, no API keys"
    "memory-mcp|Platform Services|Memory MCP|Hybrid persistent memory — structured facts (SQLite), semantic search (ChromaDB), decision log"
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

PROFILE_RECOMMENDED="pyats gait netbox servicenow nvd-cve subnet-calc wikipedia markmap \
drawio-rfc uml packet-buddy nmap gtrace suzieq batfish protocol n2n tts chrome-devtools"

PROFILE_CISCO="pyats gait netbox servicenow aci ise catalyst-center meraki sdwan cml fmc \
radkit te-community te-official nvd-cve subnet-calc drawio-rfc uml packet-buddy"

PROFILE_MULTIVENDOR="pyats junos arista-cvp aruba-cx f5 netbox nautobot gait servicenow \
fwrule subnet-calc drawio-rfc uml packet-buddy"

PROFILE_CLOUD="aws azure gcp cloudflare terraform vault github gait drawio-rfc uml subnet-calc"

PROFILE_SECURITY="ise fmc panorama fortimanager checkpoint claroty zscaler nvd-cve nmap \
fwrule gait servicenow"

PROFILE_LABS="cml containerlab batfish protocol peering n2n suzieq gait subnet-calc drawio-rfc uml"

PROFILE_OBSERVABILITY="grafana prometheus datadog splunk pagerduty te-community te-official \
suzieq kubeshark gtrace gait"

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
