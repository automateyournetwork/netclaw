# Jev audit findings

Branch: `jev-audit`. Disposable analysis harness in `scripts/jev-audit/`, throwaway tooling —
not integrated into NetClaw. Uses TypeSafe's Jev (System One model) to gut-check the 227 skills
in `workspace/skills/` for health, overlap, and coverage gaps. All findings below are Jev's
probabilistic judgments, not certainties — treat as a prioritized list to investigate, not a
verdict.

## Methodology summary

| Sweep | Design | Calls | Real cost |
| --- | --- | --- | --- |
| 1: skill health | 1 call/skill, 4-question noul battery | 462 (227 primary + 235 self-consistency) | $0.0541 |
| 2: overlap matrix | anchor-batched, 25,651 pairs in 630 calls | 10,900 (630 primary + 10,270 self-consistency) | $0.3569 |
| 3: coverage gaps | 60 candidates x 227 existing skills, chunked | 530 (300 primary + 230 self-consistency) | $0.0702 |
| **Total** | | **11,892** | **$0.4812** |

All three sweeps stayed far under the $1.50-per-sweep stop threshold (of a $5 total budget).

**Bugs hit and fixed live**, in case this harness is ever resurrected:
1. A naive one-call-per-pair design for sweep 2 would have been 25,651 calls; batched by anchor
   skill instead (one call, many questions) per Jev's own "batch questions, not calls" guidance —
   227 calls for the same coverage.
2. The first batched version repeated a long boilerplate paragraph in every question's
   `instructions`; the largest anchor's request hit ~58k tokens, right at Jev's 64k context
   ceiling, and stalled outbound (TCP send queue never drained, no exception, no timeout firing).
   Fixed by stating the rubric once in `state` and hard-chunking to 50 comparisons/call.
3. Self-consistency reruns were originally run synchronously inside each batched call's worker
   thread — a chunk with many mid-confidence answers could serialize up to 250 sequential calls,
   which starved the progress counter identically to a real stall. Fixed by splitting into two
   independently-parallelized phases (primary answers, then a separate concurrent pass over only
   the mid-band questions), and by firing each question's 5 self-consistency reruns concurrently
   instead of in a sequential loop.
4. Added a hard wall-clock guard (`common.py`) around every HTTP call, independent of `requests`'
   own timeout, after observing a stall that `timeout=` never caught.

---

## Fixes applied on this branch

Per operator direction, findings above were acted on (not left purely as a to-review list):

- **123 skills** got a tailored `## Failure Behavior` section (generated per-skill from its own
  referenced env vars and read-only-vs-write-capable tool set, not one paragraph pasted 123 times) —
  `scripts/jev-audit/fix_failure_behavior.py`.
- **3 genuine stale-machine assumptions fixed**: a Cisco DevNet sandbox hostname hardcoded in
  `pyats-network`, the operator's own name baked into federation-member paths in `comfyui-topology-viz`,
  and a hardcoded Twitter handle in `twitter-respond`. 5 other flagged skills were checked and correctly
  left alone as false positives (already using env vars / generic examples).
- **21 of the 26 highest-confidence (>=0.85) overlapping pairs disambiguated** via targeted description
  edits (narrowing scope, cross-referencing the sibling skill, or correcting an inaccurate "only tool for
  X" claim). One of these — `memory` vs `mempalace` — turned out to have a real root cause: `memory/SKILL.md`
  had no YAML frontmatter at all, so Jev's (and presumably any other) description extractor saw nothing;
  fixed by adding proper frontmatter. 5 pairs were reviewed and correctly left as intentional design
  (e.g. the `eve-lab-topology-*` discovery -> design -> validation pipeline).
- **Not attempted**: the 310 lower-confidence (0.60-0.85) overlapping pairs, and the 47 confirmed
  sweep-3 coverage gaps. The gaps are net-new skill/MCP integrations against real vendor APIs (Sentinel,
  ClearPass, Consul, etc.) — fabricating those without actual credentials/testing would produce untested
  code presented as working, which is a quality and trust problem no budget number fixes. Treat each as
  a candidate for its own spec, following `docs/ADDING-AN-MCP.md`, if picked up.



## Sweep 1 — Skill health

227 skills checked, one Jev call per skill (full `SKILL.md` as state), a 4-question noul battery per call (ambiguous trigger, no failure behavior, stale machine/path assumptions, prompt-injection smell). Tool/MCP-reference existence is checked deterministically in code (env-var references in the skill text cross-checked against `.env` and `openclaw.json`), not asked to Jev — it has no ground truth for that and stuffing a 227-server registry into every call would violate the "one unit of analysis per call" rule.

Ranked by confidence x impact (sum of `noul x |noul-0.5|x2` over flagged questions; mid-confidence answers were re-run 5x for self-consistency and dropped if unstable rather than trusted at face value).

| Rank | Skill | Score | Flags | Undefined env refs |
| --- | --- | --- | --- | --- |
| 1 | `telemetry-ops` | 1.25 | No failure behavior specified (0.93); Stale machine/path assumptions (0.72) | — |
| 2 | `twitter-check` | 1.15 | No failure behavior specified (0.96) | — |
| 3 | `eve-lab-topology-discovery` | 1.15 | No failure behavior specified (0.96) | — |
| 4 | `pyats-network` | 1.14 | No failure behavior specified (0.88); Stale machine/path assumptions (0.73*) | PYATS_MCP_SCRIPT |
| 5 | `cloudflare-zerotrust` | 1.13 | No failure behavior specified (0.96) | — |
| 6 | `cloudflare-analytics` | 1.11 | No failure behavior specified (0.96) | — |
| 7 | `cloudflare-dns` | 1.11 | No failure behavior specified (0.95) | — |
| 8 | `markmap-viz` | 1.10 | No failure behavior specified (0.96) | MARKMAP_MCP_SCRIPT |
| 9 | `cloudflare-security` | 1.09 | No failure behavior specified (0.96) | — |
| 10 | `vault-secrets` | 1.08 | No failure behavior specified (0.96) | — |
| 11 | `cloudflare-workers` | 1.07 | No failure behavior specified (0.95) | — |
| 12 | `splunk-saved` | 1.07 | No failure behavior specified (0.96) | — |
| 13 | `splunk-indexes` | 1.07 | No failure behavior specified (0.96) | — |
| 14 | `rfc-lookup` | 1.07 | No failure behavior specified (0.97) | — |
| 15 | `zscaler-identity` | 1.06 | No failure behavior specified (0.96) | — |
| 16 | `zscaler-insights` | 1.06 | No failure behavior specified (0.96) | — |
| 17 | `vault-mounts` | 1.06 | No failure behavior specified (0.96) | — |
| 18 | `zscaler-zia` | 1.06 | No failure behavior specified (0.96) | — |
| 19 | `terraform-workspaces` | 1.05 | No failure behavior specified (0.96) | — |
| 20 | `vault-pki` | 1.05 | No failure behavior specified (0.96) | — |
| 21 | `zscaler-zdx` | 1.05 | No failure behavior specified (0.96) | — |
| 22 | `splunk-search` | 1.05 | No failure behavior specified (0.95) | — |
| 23 | `netbox-reconcile` | 1.05 | No failure behavior specified (0.93) | GAIT_MCP_SCRIPT, MARKMAP_MCP_SCRIPT, NETBOX_MCP_SCRIPT, PYATS_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT |
| 24 | `zscaler-zpa` | 1.05 | No failure behavior specified (0.96) | — |
| 25 | `subnet-calculator` | 1.04 | No failure behavior specified (0.96) | PYATS_MCP_SCRIPT, SUBNET_MCP_SCRIPT |
| 26 | `ipfix-receiver` | 1.04 | No failure behavior specified (0.96) | — |
| 27 | `datadog-logs` | 1.04 | No failure behavior specified (0.95) | — |
| 28 | `syslog-receiver` | 1.04 | No failure behavior specified (0.96) | — |
| 29 | `mempalace` | 1.03 | No failure behavior specified (0.94) | GAIT_MCP_SCRIPT, MEMPALACE_MCP_SCRIPT |
| 30 | `twitter-respond` | 1.03 | No failure behavior specified (0.91); Stale machine/path assumptions (0.61*) | — |
| 31 | `datadog-metrics` | 1.03 | No failure behavior specified (0.95) | — |
| 32 | `claroty-ot-topology` | 1.03 | No failure behavior specified (0.95) | — |
| 33 | `nvd-cve` | 1.02 | No failure behavior specified (0.95) | GAIT_MCP_SCRIPT, NVD_MCP_SCRIPT, PYATS_MCP_SCRIPT |
| 34 | `azure-security-audit` | 1.02 | No failure behavior specified (0.94) | — |
| 35 | `suzieq-observability` | 1.02 | No failure behavior specified (0.95) | — |
| 36 | `eve-ng-config-ops` | 1.01 | No failure behavior specified (0.92) | — |
| 37 | `eve-lab-topology-design` | 1.01 | No failure behavior specified (0.93) | — |
| 38 | `eve-ng-lab-management` | 1.01 | No failure behavior specified (0.92) | — |
| 39 | `github-ops` | 1.01 | No failure behavior specified (0.95) | — |
| 40 | `ise-posture-audit` | 1.00 | No failure behavior specified (0.94) | GAIT_MCP_SCRIPT, ISE_MCP_SCRIPT, MARKMAP_MCP_SCRIPT |

`*` = confirmed via 5x self-consistency recheck (was in the 0.30-0.70 mid-band on the first pass).

**58 skills reference an env var not found in `.env` or `openclaw.json`** (may be intentionally operator-supplied — worth a manual look, not an automatic bug):

- `pyats-network`: PYATS_MCP_SCRIPT
- `markmap-viz`: MARKMAP_MCP_SCRIPT
- `netbox-reconcile`: GAIT_MCP_SCRIPT, MARKMAP_MCP_SCRIPT, NETBOX_MCP_SCRIPT, PYATS_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT
- `subnet-calculator`: PYATS_MCP_SCRIPT, SUBNET_MCP_SCRIPT
- `mempalace`: GAIT_MCP_SCRIPT, MEMPALACE_MCP_SCRIPT
- `nvd-cve`: GAIT_MCP_SCRIPT, NVD_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `ise-posture-audit`: GAIT_MCP_SCRIPT, ISE_MCP_SCRIPT, MARKMAP_MCP_SCRIPT
- `ise-incident-response`: GAIT_MCP_SCRIPT, ISE_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT
- `pyats-junos-system`: PYATS_MCP_SCRIPT
- `wikipedia-research`: WIKIPEDIA_MCP_SCRIPT
- `pyats-f5-ltm`: PYATS_MCP_SCRIPT
- `paloalto-panorama`: PANOS_MCP_CMD
- `gait-session-tracking`: GAIT_MCP_SCRIPT
- `nmap-service-detection`: NMAP_MCP_SCRIPT
- `pyats-asa-firewall`: PYATS_MCP_SCRIPT
- `pyats-junos-interfaces`: PYATS_MCP_SCRIPT
- `pyats-linux-system`: PYATS_MCP_SCRIPT
- `pyats-f5-platform`: PYATS_MCP_SCRIPT
- `infoblox-ddi`: INFOBLOX_MCP_CMD
- `pyats-linux-network`: PYATS_MCP_SCRIPT
- `aci-fabric-audit`: ACI_MCP_SCRIPT, APIC_URL, GAIT_MCP_SCRIPT, MARKMAP_MCP_SCRIPT
- `pyats-health-check`: GAIT_MCP_SCRIPT, NETBOX_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `slack-incident-workflow`: GAIT_MCP_SCRIPT, PYATS_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT
- `pyats-junos-routing`: PYATS_MCP_SCRIPT
- `packet-analysis`: PACKET_BUDDY_MCP_SCRIPT
- `nmap-scan-management`: NMAP_MCP_SCRIPT
- `f5-health-check`: F5_MCP_SCRIPT, GAIT_MCP_SCRIPT
- `nmap-network-scan`: NMAP_MCP_SCRIPT
- `webex-incident-workflow`: GAIT_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT
- `webex-network-alerts`: WEBEX_BOT_TOKEN
- `pyats-security`: GAIT_MCP_SCRIPT, ISE_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `f5-troubleshoot`: F5_MCP_SCRIPT, GAIT_MCP_SCRIPT
- `catc-inventory`: CATC_MCP_SCRIPT, CCC_HOST, GAIT_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `pyats-topology`: GAIT_MCP_SCRIPT, NETBOX_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `pyats-linux-vmware`: PYATS_MCP_SCRIPT
- `fortianalyzer-ops`: FORTINET_MCP_CMD
- `servicenow-change-workflow`: GAIT_MCP_SCRIPT, PYATS_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT
- `webex-voice-interface`: TTS_MCP_SCRIPT
- `defenseclaw-ops`: SLACK_WEBHOOK_URL, SPLUNK_HEC_TOKEN, WEBEX_WEBHOOK_URL
- `humanrail-escalation`: HUMANRAIL_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `pyats-dynamic-test`: PYATS_MCP_SCRIPT
- `rag`: RAG_MCP_SCRIPT
- `aci-change-deploy`: ACI_MCP_SCRIPT, APIC_URL, GAIT_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT
- `slack-voice-interface`: TTS_MCP_SCRIPT
- `sdwan-ops`: SDWAN_MCP_SCRIPT
- `f5-config-mgmt`: F5_MCP_SCRIPT, GAIT_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT
- `clab-lab-management`: CLAB_MCP_SCRIPT
- `pyats-troubleshoot`: GAIT_MCP_SCRIPT, NETBOX_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `catc-troubleshoot`: CATC_MCP_SCRIPT, CCC_HOST, GAIT_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `catc-client-ops`: CATC_MCP_SCRIPT, CCC_HOST, GAIT_MCP_SCRIPT
- `pyats-routing`: PYATS_MCP_SCRIPT
- `fortimanager-ops`: FORTINET_MCP_CMD
- `bgp-registry-intel`: BGP_INTEL_MCP_CMD
- `pyats-config-mgmt`: GAIT_MCP_SCRIPT, PYATS_MCP_SCRIPT, SERVICENOW_MCP_SCRIPT
- `document-generation`: DOCUMENT_MCP_CMD
- `pyats-parallel-ops`: PYATS_MCP_SCRIPT
- `cisco-psirt-advisories`: CISCO_PSIRT_MCP_SCRIPT, MULTIVENDOR_MCP_SCRIPT, PYATS_MCP_SCRIPT
- `fortigate-ops`: FORTINET_MCP_CMD


## Sweep 2 — Overlap matrix

All C(227,2) = 25,651 pairs covered. Descriptions only, batched by anchor skill (one skill's description as state, one short noul question per later skill in the sorted list) rather than one call per pair — same coverage, 630 calls instead of 25,651, per Jev's own "batch questions, not calls" guidance.

**336 pairs at noul >= 0.6** (genuine trigger-territory overlap, not just shared keywords; unstable mid-confidence pairs excluded rather than trusted):

| Noul | Skill A | Skill B |
| --- | --- | --- |
| 0.97 | `document-generation` | `network-report-documents` |
| 0.93 | `kepner-tregoe-network-troubleshooting` | `pyats-troubleshoot` |
| 0.93 | `catalyst-center-readonly` | `catc-inventory` |
| 0.92 | `gtrace-path-analysis` | `te-path-analysis` |
| 0.92 | `catc-troubleshoot` | `pyats-troubleshoot` |
| 0.91 | `f5-health-check` | `pyats-f5-ltm` |
| 0.90 | `f5-health-check` | `f5-troubleshoot` |
| 0.90 | `catc-troubleshoot` | `kepner-tregoe-network-troubleshooting` |
| 0.89 | `pyats-junos-routing` | `pyats-routing` |
| 0.89 | `protocol-participation` | `pyats-routing` |
| 0.89 | `globalping-external-checks` | `gtrace-path-analysis` |
| 0.87 | `pyats-routing` | `pyats-troubleshoot` |
| 0.87 | `nmap-network-scan` | `nmap-scan-management` |
| 0.87 | `eve-lab-topology-design` | `eve-lab-topology-discovery` |
| 0.86 | `pyats-troubleshoot` | `te-path-analysis` |
| 0.86 | `grafana-observability` | `prometheus-monitoring` |
| 0.86 | `eve-lab-topology-design` | `eve-lab-topology-validation` |
| 0.86 | `claroty-ot-topology` | `drawio-diagram` |
| 0.85 | `pyats-health-check` | `pyats-junos-system` |
| 0.85 | `pyats-dynamic-test` | `pyats-network` |
| 0.85 | `protocol-participation` | `pyats-junos-routing` |
| 0.85 | `memory` | `mempalace` |
| 0.85 | `itential-automation` | `pyats-config-mgmt` |
| 0.85 | `azure-network-ops` | `azure-security-audit` |
| 0.85 | `auvik-performance` | `zabbix-metrics-history` |
| 0.85 | `anta-validation` | `pyats-dynamic-test` |
| 0.84 | `te-network-monitoring` | `te-path-analysis` |
| 0.84 | `pyats-junos-routing` | `pyats-troubleshoot` |
| 0.84 | `f5-troubleshoot` | `pyats-f5-ltm` |
| 0.83 | `pyats-routing` | `suzieq-observability` |
| 0.83 | `pyats-junos-routing` | `suzieq-observability` |
| 0.83 | `kepner-tregoe-network-troubleshooting` | `te-path-analysis` |
| 0.83 | `f5-health-check` | `pyats-f5-platform` |
| 0.83 | `auvik-performance` | `pyats-health-check` |
| 0.83 | `anta-validation` | `pyats-health-check` |
| 0.82 | `pyats-troubleshoot` | `suzieq-observability` |
| 0.82 | `pyats-config-mgmt` | `pyats-network` |
| 0.82 | `aruba-cx-interfaces` | `suzieq-observability` |
| 0.82 | `aci-change-deploy` | `servicenow-change-workflow` |
| 0.81 | `zabbix-availability` | `zabbix-problem-review` |
| 0.81 | `protocol-participation` | `pyats-troubleshoot` |
| 0.81 | `canvas-network-viz` | `pyats-topology` |
| 0.81 | `anta-validation` | `suzieq-observability` |
| 0.80 | `webex-network-alerts` | `webex-report-delivery` |
| 0.80 | `kepner-tregoe-network-troubleshooting` | `pyats-routing` |
| 0.80 | `junos-network` | `pyats-config-mgmt` |
| 0.80 | `azure-network-ops` | `kepner-tregoe-network-troubleshooting` |
| 0.80 | `aruba-cx-interfaces` | `pyats-health-check` |
| 0.79 | `pyats-dynamic-test` | `pyats-routing` |
| 0.79 | `ipfix-receiver` | `telemetry-ops` |

(286 more below the top 50 not shown here — see `data/sweep2_raw.json`.)

`*` = confirmed via 5x self-consistency recheck.


## Sweep 3 — Coverage gaps

60 candidates (40 skills + 20 MCP servers a CCIE-level network agent should plausibly have, see `candidates.py`) checked against all 227 existing skill descriptions. Confirmed gap = every existing-skill coverage check stays below 0.4 (no existing skill's real scope already covers it).

### Confirmed gaps (47/60)

| Candidate | Kind | Description | Closest existing skill (noul) |
| --- | --- | --- | --- |
| `gremlin-chaos-mcp` | mcp | Gremlin chaos engineering API MCP server for resilience fault injection. | `multivendor-raw-cli` (0.10) |
| `microsoft-sentinel-siem` | skill | Microsoft Sentinel SIEM incident triage, KQL hunting queries, and alert correlation. | `zscaler-insights` (0.11) |
| `entra-id-mcp` | mcp | Microsoft Graph Entra ID API MCP server for conditional access and sign-in logs. | `ise-incident-response` (0.14) |
| `aruba-clearpass-nac` | skill | Aruba ClearPass network access control policy and endpoint profiling. | `ise-posture-audit` (0.16) |
| `cisco-cucm-voice-ops` | skill | Cisco Unified Communications Manager (CUCM) dial-plan and device operations. | `itential-automation` (0.16) |
| `ekahau-wifi-site-survey` | skill | Wi-Fi site survey (Ekahau) import/analysis for RF planning and validation. | `desktop-gui-inspect` (0.16) |
| `hashicorp-consul-service-mesh` | skill | HashiCorp Consul service mesh and service discovery configuration and health. | `multivendor-raw-cli` (0.16) |
| `cisco-umbrella-mcp` | mcp | Cisco Umbrella API MCP server for DNS security policy and investigate lookups. | `browser-gui-inspect` (0.17) |
| `istio-envoy-mcp` | mcp | Istio/Envoy control-plane API MCP server for service mesh traffic policy. | `itential-automation` (0.17) |
| `cisco-cucm-mcp` | mcp | Cisco Unified CM AXL/Serviceability API MCP server for voice/dial-plan operations. | `itential-automation` (0.18) |
| `haproxy-nginx-lb-ops` | skill | HAProxy/Nginx software load balancer config and health checks. | `itential-automation` (0.18) |
| `microsoft-sentinel-mcp` | mcp | Microsoft Sentinel/Log Analytics KQL API MCP server for SIEM queries. | `telemetry-ops` (0.18) |
| `cisco-secure-endpoint-mcp` | mcp | Cisco Secure Endpoint (AMP) API MCP server for malware event triage. | `browser-gui-inspect` (0.19) |
| `chaos-engineering-network-resilience` | skill | Chaos engineering / fault injection testing for network resilience validation. | `topolograph-igp-analysis` (0.20) |
| `cisco-duo-mfa-ops` | skill | Cisco Duo MFA policy, device trust, and authentication log review. | `browser-gui-inspect` (0.20) |
| `entra-id-conditional-access` | skill | Microsoft Entra ID conditional access policy review and sign-in log triage. | `browser-gui-inspect` (0.20) |
| `aruba-central-ops` | skill | Manage HPE Aruba Central cloud dashboard: AP/switch/gateway health, group config, guest access. | `itential-automation` (0.21) |
| `email-security-gateway-ops` | skill | Email security gateway (Proofpoint/Mimecast) threat and quarantine triage. | `browser-gui-inspect` (0.22) |
| `maintenance-window-conflict-checker` | skill | Cross-system change/maintenance window conflict detection across multiple ITSM/change sources. | `servicenow-change-workflow` (0.22) |
| `capacity-bandwidth-forecasting` | skill | Network capacity planning and bandwidth utilization forecasting. | `auvik-performance` (0.23) |
| `hashicorp-consul-mcp` | mcp | HashiCorp Consul HTTP API MCP server for service mesh/discovery. | `multivendor-raw-cli` (0.23) |
| `cisco-secure-endpoint-amp` | skill | Cisco Secure Endpoint (AMP) malware event triage and device isolation. | `ise-incident-response` (0.24) |
| `extreme-cloudiq-ops` | skill | Manage Extreme Networks ExtremeCloud IQ: switch/AP fleet health, ELRP, fabric visibility. | `canvas-network-viz` (0.24) |
| `gigamon-mcp` | mcp | Gigamon GigaVUE-FM API MCP server for packet broker management. | `telemetry-ops` (0.24) |
| `compliance-framework-mapping` | skill | Map network controls to compliance frameworks (PCI-DSS, NIST 800-53, ISO 27001). | `batfish-config-analysis` (0.25) |
| `aruba-central-mcp` | mcp | Aruba Central cloud API MCP server for AP/switch/gateway management. | `itential-automation` (0.26) |
| `citrix-netscaler-adc-ops` | skill | Citrix ADC (NetScaler) load balancer config, vServer health, and troubleshooting. | `itential-automation` (0.26) |
| `corelight-network-detection` | skill | Corelight network detection and response (Zeek-based) alert triage. | `nsm-ids-triage` (0.26) |
| `gigamon-packet-broker-ops` | skill | Gigamon/Ixia network packet broker (TAP/SPAN aggregation) config and health. | `itential-automation` (0.26) |
| `juniper-mist-mcp` | mcp | Juniper Mist cloud API MCP server for wireless/wired/SD-WAN management. | `itential-automation` (0.26) |
| `solarwinds-mcp` | mcp | SolarWinds Orion API MCP server for NPM/NCM monitoring and config backup. | `pyats-parallel-ops` (0.27) |
| `qualys-mcp` | mcp | Qualys VM API MCP server for vulnerability management. | `nmap-service-detection` (0.27) |
| `cisco-umbrella-dns-security` | skill | Cisco Umbrella DNS security policy, block lists, and investigate-console lookups. | `browser-gui-inspect` (0.28) |
| `cisco-duo-mcp` | mcp | Cisco Duo Admin API MCP server for MFA policy and auth log review. | `browser-gui-inspect` (0.29) |
| `cisco-stealthwatch-nsa` | skill | Cisco Secure Network Analytics (Stealthwatch) NetFlow-based threat detection triage. | `telemetry-ops` (0.29) |
| `cisco-wlc-9800-ops` | skill | Cisco Catalyst 9800 / AireOS WLC direct wireless controller operations. | `catc-troubleshoot` (0.29) |
| `iperf-throughput-testing` | skill | iPerf network throughput and latency benchmarking between endpoints. | `eve-ng-console-ops` (0.29) |
| `istio-envoy-service-mesh` | skill | Istio/Envoy service mesh traffic policy and mTLS troubleshooting. | `kubeshark-traffic` (0.29) |
| `catc-sda-fabric-provisioning` | skill | Cisco Catalyst Center SD-Access fabric provisioning (write operations: fabric sites, virtual networks, policy). | `itential-automation` (0.30) |
| `okta-mcp` | mcp | Okta admin API MCP server for identity/SSO management. | `zscaler-identity` (0.33) |
| `juniper-mist-ops` | skill | Manage Juniper Mist cloud-managed wireless/wired/SD-WAN: AP health, RRM insights, Marvis AI troubleshooting. | `kepner-tregoe-network-troubleshooting` (0.34) |
| `solarwinds-npm-ops` | skill | SolarWinds NPM/NCM device monitoring, config backup, and alerting. | `multivendor-fleet-ops` (0.34) |
| `okta-identity-ops` | skill | Okta identity/SSO admin: user lifecycle, app assignment, and MFA policy. | `zscaler-identity` (0.35) |
| `phpipam-mcp` | mcp | phpIPAM REST API MCP server for IP address management. | `infrahub-sot` (0.37) |
| `librenms-mcp` | mcp | LibreNMS REST API MCP server for open-source network monitoring. | `telemetry-ops` (0.37) |
| `cisco-smart-licensing-ops` | skill | Cisco Smart Licensing usage, compliance, and license pool management. | `cml-admin` (0.38) |
| `cilium-hubble-mcp` | mcp | Cilium/Hubble observability API MCP server for eBPF network policy and flow visibility. | `telemetry-ops` (0.40) |

### Borderline (6/60) — partially covered, worth a second look

| Candidate | Kind | Closest existing skill (noul) |
| --- | --- | --- |
| `citrix-netscaler-mcp` | mcp | `itential-automation` (0.40) |
| `tenable-nessus-mcp` | mcp | `nmap-service-detection` (0.40) |
| `qualys-vuln-management` | skill | `nmap-service-detection` (0.42) |
| `phpipam-address-management` | skill | `infrahub-sot` (0.43) |
| `cilium-ebpf-network-policy` | skill | `k8s-network-policy` (0.43) |
| `tenable-nessus-vuln-scan` | skill | `nmap-service-detection` (0.52) |

### Already covered (7/60) — Jev found an existing skill that already does this

| Candidate | Kind | Existing skill (noul) |
| --- | --- | --- |
| `thousandeyes-path-visibility` | skill | `te-network-monitoring` (0.86) |
| `zeek-suricata-nsm` | skill | `nsm-ids-triage` (0.81) |
| `cisco-sdwan-vmanage-ops` | skill | `sdwan-ops` (0.72) |
| `config-drift-detection` | skill | `itential-automation` (0.68) |
| `firmware-upgrade-orchestration` | skill | `itential-automation` (0.61) |
| `dns-diagnostics` | skill | `kepner-tregoe-network-troubleshooting` (0.60) |
| `librenms-observability` | skill | `telemetry-ops` (0.55) |


## Bonus: deterministic cross-check (not Jev-scored)

While picking sweep 3 candidates, an initial name-prefix grep suggested several vendored `mcp-servers/` entries had no skill wiring them up. Checking actual skill *content* (not just directory names) disproved most of those guesses — `te-network-monitoring`/`te-path-analysis` turned out to already be the ThousandEyes skills (`te` = ThousandEyes), `sdwan-ops` already wraps `cisco-sdwan-mcp`, and `hardware-health-check` already wraps `redfish-mcp`. Worth recording as a caution about this exact kind of check: name-matching alone gives false positives, and only actually reading the file content confirms a real gap. What survived that check:

- `mcp-servers/ollama-mcp/` — no skill references it anywhere in `workspace/skills/`.
- `mcp-servers/nautobot-golden-config-mcp/` (the Nautobot Golden Config plugin, drift/compliance against a Nautobot-sourced intended config) has no dedicated skill — `itential-automation`'s "golden config" is Itential's own separate feature, not this plugin.

Confirmed real (also independently surfaced by sweep 2, `catalyst-center-readonly` <-> `catc-inventory` at 0.93): two separately vendored MCP servers for the same product, `mcp-servers/catc-mcp/` and `mcp-servers/catalyst-center-mcp/`, backing four different skills between them — worth checking whether both implementations are still needed.
