---
name: pyats-f5-platform
description: "F5 BIG-IP platform operations via pyATS iControl REST — system, networking, HA/CM, auth, analytics, security, APM, live-update, ADC certs, file management"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# F5 BIG-IP Platform Operations via pyATS

Query F5 BIG-IP platform, system, networking, and cluster management objects via pyATS using the iControl REST API (`/mgmt/tm/sys/*`, `/mgmt/tm/net/*`, `/mgmt/tm/cm/*`, and more). This complements pyats-f5-ltm (traffic management) with full platform visibility.

## Testbed Requirements

F5 BIG-IP devices in the pyATS testbed:

```yaml
devices:
  bigip-01:
    os: bigip
    type: load-balancer
    connections:
      rest:
        class: rest
        ip: 10.0.0.20
        port: 443
        protocol: https
    credentials:
      default:
        username: "%ENV{F5_USERNAME}"
        password: "%ENV{F5_PASSWORD}"
```

## How to Call

Use `pyats_run_show_command` with iControl REST API paths:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"bigip-01","command":"show sys version"}'
```

---

## System Endpoints (`/mgmt/tm/sys/*`)

### Platform & Version

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/version` | BIG-IP software version, build, edition |
| `/mgmt/tm/sys/software/image` | Software images available on disk |
| `/mgmt/tm/sys/software/volume` | Boot volumes and active/standby slots |
| `/mgmt/tm/sys/software/hotfix` | Installed hotfixes |
| `/mgmt/tm/sys/software/update` | Software update status |
| `/mgmt/tm/sys/hardware` | Hardware platform: chassis, CPU model, memory, serial number |
| `/mgmt/tm/sys/hostinfo` | Host information: hostname, memory, CPU count, active/standby |

### CPU, Memory & Disk

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/cpu` | CPU utilization per core — current, 5s, 1m, 5m averages |
| `/mgmt/tm/sys/memory` | Memory usage: TMM, other, host subsystems |
| `/mgmt/tm/sys/disk/logical-disk` | Logical disk partitions: size, free space, mount point |
| `/mgmt/tm/sys/disk/directory` | Disk directory usage |
| `/mgmt/tm/sys/disk/application-volume` | Application volumes |
| `/mgmt/tm/sys/performance/all-stats` | Consolidated performance: throughput, connections, CPU, memory |
| `/mgmt/tm/sys/performance/connection` | Active/new connection stats and trends |
| `/mgmt/tm/sys/performance/throughput` | Client/server throughput stats |
| `/mgmt/tm/sys/performance/system` | System-wide performance aggregation |
| `/mgmt/tm/sys/performance/ramcache` | RAM cache hit/miss/eviction stats |

### System Configuration

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/global-settings` | Hostname, GUI setup, console inactivity, LCD display settings |
| `/mgmt/tm/sys/db` | System database variables (bigdb) — thousands of internal settings |
| `/mgmt/tm/sys/provision` | Module provisioning: LTM, GTM, ASM, APM, AFM allocation levels (nominal/minimum/dedicated) |
| `/mgmt/tm/sys/httpd` | HTTPD settings: SSL protocols, ciphers, access restrictions |
| `/mgmt/tm/sys/sshd` | SSHD settings: allowed ciphers, MACs, login grace time |
| `/mgmt/tm/sys/daemon-ha` | Daemon HA settings |
| `/mgmt/tm/sys/daemon-log-settings/tmm` | TMM daemon log settings |
| `/mgmt/tm/sys/daemon-log-settings/mcpd` | MCPD daemon log settings |
| `/mgmt/tm/sys/daemon-log-settings/clusterd` | Cluster daemon log settings |
| `/mgmt/tm/sys/daemon-log-settings/csyncd` | Config sync daemon log settings |
| `/mgmt/tm/sys/daemon-log-settings/icrd` | ICR daemon log settings |
| `/mgmt/tm/sys/daemon-log-settings/lind` | LIND daemon log settings |
| `/mgmt/tm/sys/outbound-smtp` | Outbound SMTP configuration |

### Time Services

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/ntp` | NTP servers and timezone — **verify NTP sync on every health check** |
| `/mgmt/tm/sys/dns` | DNS resolver configuration: nameservers, search domains |

### Logging & Syslog

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/syslog` | Syslog configuration: remote servers, facility, severity filters |
| `/mgmt/tm/sys/log-config/destination/remote-syslog` | Remote syslog destinations |
| `/mgmt/tm/sys/log-config/destination/remote-high-speed-log` | High-speed logging destinations |
| `/mgmt/tm/sys/log-config/destination/local-syslog` | Local syslog destinations |
| `/mgmt/tm/sys/log-config/destination/local-database` | Local database log destinations |
| `/mgmt/tm/sys/log-config/destination/management-port` | Management port log destinations |
| `/mgmt/tm/sys/log-config/destination/ipfix` | IPFIX log destinations |
| `/mgmt/tm/sys/log-config/destination/splunk` | Splunk log destinations |
| `/mgmt/tm/sys/log-config/destination/arcsight` | ArcSight log destinations |
| `/mgmt/tm/sys/log-config/filter` | Log filters |
| `/mgmt/tm/sys/log-config/publisher` | Log publishers (aggregate multiple destinations) |
| `/mgmt/tm/sys/log-rotate` | Log rotation settings |

### SNMP

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/snmp` | SNMP configuration: communities, trap hosts, sysContact, sysLocation |
| `/mgmt/tm/sys/snmp/communities` | SNMP community strings |
| `/mgmt/tm/sys/snmp/traps` | SNMP trap configurations |
| `/mgmt/tm/sys/snmp/users` | SNMPv3 users |

### Crypto & Certificates

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/crypto/cert` | SSL certificates installed on the system |
| `/mgmt/tm/sys/crypto/key` | SSL private keys |
| `/mgmt/tm/sys/crypto/crl` | Certificate revocation lists |
| `/mgmt/tm/sys/crypto/csr` | Certificate signing requests |
| `/mgmt/tm/sys/crypto/cert-order-manager` | Certificate order management |
| `/mgmt/tm/sys/crypto/cert-validator/ocsp` | OCSP certificate validator |
| `/mgmt/tm/sys/crypto/fips` | FIPS 140-2 status and key management |
| `/mgmt/tm/sys/crypto/master-key` | Master key information |
| `/mgmt/tm/sys/crypto/server` | Crypto server settings |
| `/mgmt/tm/sys/crypto/checkip` | Crypto check-IP settings |

### Licensing

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/license` | Current license: registration key, modules, expiration, feature flags |
| `/mgmt/tm/shared/licensing/registration` | License registration details |

### iCall & iApps

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/icall/handler/periodic` | iCall periodic handlers (scheduled tasks) |
| `/mgmt/tm/sys/icall/handler/triggered` | iCall triggered handlers |
| `/mgmt/tm/sys/icall/handler/perpetual` | iCall perpetual handlers |
| `/mgmt/tm/sys/icall/istats-trigger` | iCall iStats triggers |
| `/mgmt/tm/sys/icall/script` | iCall scripts |
| `/mgmt/tm/sys/application/apl-script` | APL scripts |
| `/mgmt/tm/sys/application/custom-stat` | Custom statistics |
| `/mgmt/tm/sys/application/service` | Application services (iApps) |
| `/mgmt/tm/sys/application/template` | Application templates |

### Monitoring & Health

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/sflow/receiver` | sFlow receiver configuration |
| `/mgmt/tm/sys/sflow/data-source/vlan` | sFlow VLAN data sources |
| `/mgmt/tm/sys/sflow/data-source/interface` | sFlow interface data sources |
| `/mgmt/tm/sys/sflow/data-source/http` | sFlow HTTP data sources |
| `/mgmt/tm/sys/sflow/data-source/system` | sFlow system data sources |
| `/mgmt/tm/sys/ipfix/destination` | IPFIX collector destinations |
| `/mgmt/tm/sys/ipfix/element` | IPFIX information elements |
| `/mgmt/tm/sys/connection` | Active system connections |
| `/mgmt/tm/sys/alert/snmp` | SNMP alert settings |
| `/mgmt/tm/sys/alert/lcd` | LCD alert settings |

### Management Access

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/management-ip` | Management IP address(es) |
| `/mgmt/tm/sys/management-route` | Management routing table |
| `/mgmt/tm/sys/management-ovsdb` | Management OVSDB settings |
| `/mgmt/tm/sys/management-dhcp/sys-dhcp-config` | Management DHCP configuration |

### Miscellaneous System

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/sys/cluster` | Cluster membership and status |
| `/mgmt/tm/sys/dynad/key` | Dynamic advertiser keys |
| `/mgmt/tm/sys/ecm/cloud-provider` | ECM cloud provider settings |
| `/mgmt/tm/sys/feature-module` | Feature module status |
| `/mgmt/tm/sys/folder` | Configuration folders (partitions) |
| `/mgmt/tm/sys/fpga/firmware-config` | FPGA firmware configuration |
| `/mgmt/tm/sys/gepd` | GEPD settings |
| `/mgmt/tm/sys/pfman/consumer` | PF manager consumer settings |
| `/mgmt/tm/sys/pfman/device` | PF manager device settings |
| `/mgmt/tm/sys/state-mirroring` | State mirroring settings |
| `/mgmt/tm/sys/turboflex/profile-config` | TurboFlex profile configuration |
| `/mgmt/tm/sys/url-db/download-schedule` | URL database download schedule |
| `/mgmt/tm/sys/url-db/url-category` | URL categories |
| `/mgmt/tm/sys/datastor` | Data store settings |
| `/mgmt/tm/sys/diags/ihealth` | iHealth diagnostic settings |

---

## Network Endpoints (`/mgmt/tm/net/*`)

### Interfaces & VLANs

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/net/interface` | Physical interfaces: speed, duplex, media type, flow control, status |
| `/mgmt/tm/net/vlan` | VLANs: tag, interfaces, failsafe settings |
| `/mgmt/tm/net/vlan-allowed-list` | VLAN allowed list |
| `/mgmt/tm/net/vlan-group` | VLAN groups |
| `/mgmt/tm/net/self` | Self IPs: address, VLAN, traffic-group, allow-service list |
| `/mgmt/tm/net/self-allow` | Self IP allowed ports/protocols |
| `/mgmt/tm/net/trunk` | Trunk groups (802.3ad LACP) — member interfaces, distribution hash |

### Routing

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/net/route` | Static routes |
| `/mgmt/tm/net/route-domain` | Route domains (VRF equivalent on BIG-IP) |
| `/mgmt/tm/net/routing/bgp` | BGP configuration |
| `/mgmt/tm/net/routing/bfd` | BFD configuration |
| `/mgmt/tm/net/routing/prefix-list` | Prefix lists |
| `/mgmt/tm/net/routing/route-map` | Route maps |
| `/mgmt/tm/net/routing/access-list` | Access lists for routing |

### Tunnels

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/net/tunnels/tunnel` | Tunnel interfaces (GRE, VXLAN, IPsec, etc.) |
| `/mgmt/tm/net/tunnels/gre` | GRE tunnel profiles |
| `/mgmt/tm/net/tunnels/vxlan` | VXLAN tunnel profiles |
| `/mgmt/tm/net/tunnels/ipsec` | IPsec tunnel profiles |
| `/mgmt/tm/net/tunnels/geneve` | Geneve tunnel profiles |
| `/mgmt/tm/net/tunnels/ipip` | IPIP tunnel profiles |
| `/mgmt/tm/net/tunnels/map` | MAP tunnel profiles |
| `/mgmt/tm/net/tunnels/wccp` | WCCP tunnel profiles |
| `/mgmt/tm/net/tunnels/ppp` | PPP tunnel profiles |
| `/mgmt/tm/net/tunnels/tcp-forward` | TCP forward tunnel profiles |
| `/mgmt/tm/net/tunnels/v6rd` | 6rd tunnel profiles |
| `/mgmt/tm/net/tunnels/fec` | FEC (Forward Error Correction) tunnel profiles |
| `/mgmt/tm/net/tunnels/etherip` | EtherIP tunnel profiles |
| `/mgmt/tm/net/tunnels/lw4o6` | Lightweight 4over6 tunnel profiles |

### ARP & NDP

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/net/arp` | ARP table entries |
| `/mgmt/tm/net/ndp` | IPv6 Neighbor Discovery Protocol entries |

### IPsec

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/net/ipsec/ike-daemon` | IKE daemon settings |
| `/mgmt/tm/net/ipsec/ike-peer` | IKE peers |
| `/mgmt/tm/net/ipsec/ipsec-sa` | IPsec Security Associations |
| `/mgmt/tm/net/ipsec/ipsec-policy` | IPsec policies |
| `/mgmt/tm/net/ipsec/manual-security-association` | Manual SAs |
| `/mgmt/tm/net/ipsec/traffic-selector` | IPsec traffic selectors |

### Other Networking

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/net/stp` | Spanning Tree Protocol settings |
| `/mgmt/tm/net/stp-globals` | STP global settings |
| `/mgmt/tm/net/dag-globals` | DAG (Disaggregated) global settings |
| `/mgmt/tm/net/cos/global-settings` | CoS global settings |
| `/mgmt/tm/net/cos/traffic-priority` | CoS traffic priority |
| `/mgmt/tm/net/dns-resolver` | DNS resolver settings |
| `/mgmt/tm/net/lldp-globals` | LLDP global settings |
| `/mgmt/tm/net/multicast-globals` | Multicast global settings |
| `/mgmt/tm/net/packet-filter` | Packet filter rules |
| `/mgmt/tm/net/packet-filter-trusted` | Trusted packet filter rules |
| `/mgmt/tm/net/rate-shaping/class` | Rate shaping classes |
| `/mgmt/tm/net/rate-shaping/drop-policy` | Rate shaping drop policies |
| `/mgmt/tm/net/rate-shaping/queue` | Rate shaping queues |
| `/mgmt/tm/net/rate-shaping/shaping-policy` | Shaping policies |
| `/mgmt/tm/net/timer-policy` | Timer policies |
| `/mgmt/tm/net/fdb/tunnel` | FDB tunnel entries |
| `/mgmt/tm/net/fdb/vlan` | FDB VLAN entries |
| `/mgmt/tm/net/wccp` | WCCP settings |

---

## Cluster Management (`/mgmt/tm/cm/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/cm/device` | Devices in the trust domain — hostname, management IP, version, HA status |
| `/mgmt/tm/cm/device-group` | Device groups — sync-failover, sync-only, type, members |
| `/mgmt/tm/cm/sync-status` | Config sync status — **check this first on any HA pair** |
| `/mgmt/tm/cm/failover-status` | Failover state — active/standby/forced-offline |
| `/mgmt/tm/cm/traffic-group` | Traffic groups — floating IPs, failover order, HA scoring |
| `/mgmt/tm/cm/trust-domain` | Trust domain membership |
| `/mgmt/tm/cm/cert` | CM certificates |
| `/mgmt/tm/cm/key` | CM keys |

---

## Authentication & Authorization (`/mgmt/tm/auth/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/auth/source` | Authentication source (local, remote) |
| `/mgmt/tm/auth/user` | Local user accounts |
| `/mgmt/tm/auth/remote-user` | Remote user default settings |
| `/mgmt/tm/auth/remote-role` | Remote role mapping |
| `/mgmt/tm/auth/ldap` | LDAP authentication configuration |
| `/mgmt/tm/auth/radius` | RADIUS authentication configuration |
| `/mgmt/tm/auth/radius-server` | RADIUS server list |
| `/mgmt/tm/auth/tacacs` | TACACS+ authentication configuration |
| `/mgmt/tm/auth/password-policy` | Password policy: complexity, expiration, lockout |
| `/mgmt/tm/auth/partition` | Administrative partitions |
| `/mgmt/tm/auth/user-role` | User role definitions |

---

## Analytics (`/mgmt/tm/analytics/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/analytics/cpu/report` | CPU analytics reports |
| `/mgmt/tm/analytics/memory/report` | Memory analytics reports |
| `/mgmt/tm/analytics/disk/report` | Disk analytics reports |
| `/mgmt/tm/analytics/http/report` | HTTP analytics: requests, response time, throughput, status codes |
| `/mgmt/tm/analytics/tcp/report` | TCP analytics: connections, retransmissions, round-trip time |
| `/mgmt/tm/analytics/dns/report` | DNS analytics: query types, response codes, latency |
| `/mgmt/tm/analytics/dos-l3/report` | L3 DoS analytics |
| `/mgmt/tm/analytics/dos/report` | DoS analytics: attack vectors, detection, mitigation events |
| `/mgmt/tm/analytics/dos-vis-common/report` | DoS visualization common reports |
| `/mgmt/tm/analytics/asm/report` | ASM (WAF) analytics: violations, attack types, blocked requests |
| `/mgmt/tm/analytics/bot-defense/report` | Bot defense analytics |
| `/mgmt/tm/analytics/ssl-orchestrator/report` | SSL Orchestrator analytics |
| `/mgmt/tm/analytics/swg/report` | Secure Web Gateway analytics |
| `/mgmt/tm/analytics/global-settings` | Analytics global settings |
| `/mgmt/tm/analytics/application-security/report` | Application security reports |
| `/mgmt/tm/analytics/network-firewall/report` | Network firewall analytics |
| `/mgmt/tm/analytics/protocol-inspection/report` | Protocol inspection analytics |

---

## Security (`/mgmt/tm/security/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/security/firewall/management-ip-rules` | Management IP access rules |
| `/mgmt/tm/security/firewall/policy` | AFM firewall policies |
| `/mgmt/tm/security/firewall/address-list` | Firewall address lists |
| `/mgmt/tm/security/firewall/port-list` | Firewall port lists |
| `/mgmt/tm/security/firewall/rule-list` | Firewall rule lists |
| `/mgmt/tm/security/firewall/global-rules` | Global firewall rules |

---

## Access Policy Manager (`/mgmt/tm/access/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/access/acl/stats` | APM ACL statistics |
| `/mgmt/tm/access/profile/stats` | APM profile statistics |
| `/mgmt/tm/access/session-kill-all` | APM session kill control (use with extreme caution) |
| `/mgmt/tm/access/usecase-pack` | APM usecase packs (Guided Configuration) |

---

## Cloud Endpoints (`/mgmt/tm/cloud/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/cloud/device-group` | Cloud device groups |
| `/mgmt/tm/cloud/ltm/virtual-server` | Cloud LTM virtual servers |
| `/mgmt/tm/cloud/ltm/pool` | Cloud LTM pools |
| `/mgmt/tm/cloud/ltm/node` | Cloud LTM nodes |
| `/mgmt/tm/cloud/ltm/monitor` | Cloud LTM monitors |
| `/mgmt/tm/cloud/net/self-ip` | Cloud self IPs |
| `/mgmt/tm/cloud/net/vlan` | Cloud VLANs |
| `/mgmt/tm/cloud/net/route` | Cloud routes |
| `/mgmt/tm/cloud/iapp/service` | Cloud iApp services |
| `/mgmt/tm/cloud/iapp/template` | Cloud iApp templates |

---

## Shared Endpoints (`/mgmt/tm/shared/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/shared/licensing/registration` | License registration details |
| `/mgmt/tm/shared/failover-state` | Shared failover state |

---

## Live Update (`/mgmt/tm/live-update/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/live-update/asm-attack-signatures/installations` | ASM attack signature updates |
| `/mgmt/tm/live-update/bot-signatures/installations` | Bot signature updates |
| `/mgmt/tm/live-update/browser-challenges/installations` | Browser challenge updates |
| `/mgmt/tm/live-update/server-technologies/installations` | Server technology detection updates |
| `/mgmt/tm/live-update/threat-campaigns/installations` | Threat campaign updates |

---

## ADC Certificate Management (`/mgmt/tm/adc/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/adc/field-value/cert/subject` | Certificate subject field values |
| `/mgmt/tm/adc/field-value/cert/issuer` | Certificate issuer field values |
| `/mgmt/tm/adc/field-value/cert/key-type` | Certificate key type values |
| `/mgmt/tm/adc/field-value/cert/serial` | Certificate serial numbers |
| `/mgmt/tm/adc/field-value/key/key-type` | Key type values |
| `/mgmt/tm/adc/field-value/key/key-size` | Key size values |
| `/mgmt/tm/adc/field-value/key/security-type` | Key security type values |
| `/mgmt/tm/adc/field-value/crl/issuer` | CRL issuer values |
| `/mgmt/tm/adc/field-value/csr/subject` | CSR subject values |
| `/mgmt/tm/adc/field-value/csr/key-type` | CSR key type values |

---

## File Management (`/mgmt/tm/file/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/file/apm/aaa/ldap/sso` | APM LDAP SSO files |
| `/mgmt/tm/file/ssl-cert` | SSL certificate files |
| `/mgmt/tm/file/ssl-key` | SSL key files |
| `/mgmt/tm/file/ssl-crl` | SSL CRL files |
| `/mgmt/tm/file/ssl-csr` | SSL CSR files |
| `/mgmt/tm/file/data-group` | External data group files |
| `/mgmt/tm/file/external-monitor` | External monitor script files |
| `/mgmt/tm/file/ifile` | iFile data files |
| `/mgmt/tm/file/dashboard-viewset` | Dashboard viewset files |

---

## CLI Settings (`/mgmt/tm/cli/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/cli/alias` | CLI aliases |
| `/mgmt/tm/cli/global-settings` | CLI global settings: idle timeout, pager, audit log |
| `/mgmt/tm/cli/history` | CLI command history |
| `/mgmt/tm/cli/preference` | CLI user preferences |
| `/mgmt/tm/cli/script` | CLI scripts (tmsh scripts) |

---

## WOM / iSession (`/mgmt/tm/wom/*`)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/wom/local-s2s-application-entry` | WOM local S2S application entries |

---

## Workflows

### 1. BIG-IP Platform Health Check
```
/mgmt/tm/sys/version → software version, build
→ /mgmt/tm/sys/hardware → platform model, serial, memory
→ /mgmt/tm/sys/cpu → CPU utilization per core
→ /mgmt/tm/sys/memory → TMM and host memory usage
→ /mgmt/tm/sys/disk/logical-disk → disk space remaining
→ /mgmt/tm/sys/performance/all-stats → throughput, connections
→ /mgmt/tm/sys/ntp → NTP sync status
→ /mgmt/tm/sys/provision → module allocation (LTM, GTM, ASM, APM)
→ /mgmt/tm/sys/license → license expiration, feature flags
→ Flag: CPU >80%, memory >85%, disk >90%, NTP out of sync, license expiring
→ GAIT
```

### 2. HA / Cluster Verification
```
/mgmt/tm/cm/sync-status → config sync state (In Sync / Changes Pending / Disconnected)
→ /mgmt/tm/cm/failover-status → active/standby/forced-offline
→ /mgmt/tm/cm/device → device trust domain members, versions
→ /mgmt/tm/cm/device-group → sync-failover groups, members, type
→ /mgmt/tm/cm/traffic-group → floating IPs, failover order
→ /mgmt/tm/net/self → self IPs with traffic-group assignments
→ Flag: sync status not "In Sync", mismatched versions, traffic-group imbalance
→ GAIT
```

### 3. Network Infrastructure Audit
```
/mgmt/tm/net/interface → physical interfaces, speed, duplex, status
→ /mgmt/tm/net/vlan → VLANs, tagged interfaces, failsafe
→ /mgmt/tm/net/self → self IPs, VLAN bindings, allow-service
→ /mgmt/tm/net/trunk → LACP trunks, member status, hash
→ /mgmt/tm/net/route → static routes
→ /mgmt/tm/net/route-domain → route domains (VRFs)
→ /mgmt/tm/net/arp → ARP entries (cross-reference with NetBox)
→ /mgmt/tm/net/tunnels/tunnel → active tunnels (GRE, VXLAN, IPsec)
→ Flag: interfaces down, trunk members missing, orphan self IPs
→ GAIT
```

### 4. Security & Certificate Audit
```
/mgmt/tm/sys/crypto/cert → all installed certificates
→ /mgmt/tm/sys/crypto/key → private keys (verify matching)
→ /mgmt/tm/sys/crypto/crl → CRLs (check freshness)
→ /mgmt/tm/auth/source → authentication source (local/remote)
→ /mgmt/tm/auth/password-policy → password complexity and lockout
→ /mgmt/tm/sys/httpd → HTTPS cipher/protocol settings
→ /mgmt/tm/sys/sshd → SSH cipher/MAC settings
→ /mgmt/tm/security/firewall/management-ip-rules → management access rules
→ /mgmt/tm/sys/snmp/communities → SNMP community strings
→ Flag: expiring certs (<30d), weak ciphers, default SNMP communities, no password policy
→ Cross-reference BIG-IP version with NVD CVE
→ GAIT
```

### 5. Analytics Deep Dive
```
/mgmt/tm/analytics/http/report → HTTP request rates, response times, errors
→ /mgmt/tm/analytics/tcp/report → TCP connections, retransmissions, RTT
→ /mgmt/tm/analytics/dns/report → DNS query patterns, response codes
→ /mgmt/tm/analytics/dos/report → DoS detection/mitigation events
→ /mgmt/tm/analytics/asm/report → WAF violations, attack types
→ /mgmt/tm/analytics/cpu/report → CPU utilization trends
→ /mgmt/tm/analytics/memory/report → memory trends
→ Flag: high retransmission rate, rising DoS events, WAF violation spike
→ GAIT
```

### 6. Live Update Status
```
/mgmt/tm/live-update/asm-attack-signatures/installations → ASM sig version, last update
→ /mgmt/tm/live-update/bot-signatures/installations → bot sig freshness
→ /mgmt/tm/live-update/threat-campaigns/installations → threat campaign updates
→ /mgmt/tm/live-update/browser-challenges/installations → browser challenge updates
→ /mgmt/tm/live-update/server-technologies/installations → server tech detection
→ Flag: signatures >7 days old, threat campaigns stale
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-f5-ltm** | LTM/GTM traffic management objects complement platform view |
| **f5-health-check** | F5 MCP for operational monitoring; pyATS REST for full platform inventory |
| **f5-config-mgmt** | F5 MCP for safe config changes; pyATS REST for pre/post platform audit |
| **f5-troubleshoot** | F5 MCP for troubleshooting; pyATS REST for deep platform inspection |
| **nvd-cve** | Scan BIG-IP software version against NVD vulnerability database |
| **netbox-reconcile** | Cross-reference BIG-IP self IPs, interfaces, VLANs with NetBox |
| **servicenow-change-workflow** | Gate all BIG-IP platform changes behind ServiceNow CRs |
| **gait-session-tracking** | Every REST query logged in GAIT |

---

## Guardrails

- **All queries are read-only** — GET requests to iControl REST API only
- **No configuration changes** — never POST/PUT/PATCH/DELETE via this skill
- **Monitor sync-status first** — always check `/mgmt/tm/cm/sync-status` before any HA pair operations
- **Check license expiration** — flag licenses expiring within 30 days
- **Verify NTP** — out-of-sync NTP causes cert validation failures and log correlation issues
- **Gate changes behind ServiceNow** — any platform changes go through f5-config-mgmt with CR
- **Record in GAIT** — every API query must be logged
