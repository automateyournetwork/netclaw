---
name: pyats-f5-ltm
description: "F5 BIG-IP LTM/GTM operations via pyATS iControl REST — virtual servers, pools, nodes, monitors, profiles, iRules, persistence, GTM wide IPs, DNS, data groups"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# F5 BIG-IP LTM/GTM Operations via pyATS

Query F5 BIG-IP Local Traffic Manager (LTM) and Global Traffic Manager (GTM) objects via pyATS using the iControl REST API (`/mgmt/tm/ltm/*` and `/mgmt/tm/gtm/*`). This complements the F5 BIG-IP MCP server with comprehensive REST API coverage for traffic management objects.

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
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"bigip-01","command":"show ltm virtual"}'
```

Or for direct REST endpoints, the pyATS F5 connection maps these to iControl REST GETs.

---

## LTM Endpoints

### Virtual Servers

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/virtual` | All virtual servers — name, destination, pool, profiles, status |
| `/mgmt/tm/ltm/virtual-address` | Virtual server IP addresses and availability |
| `/mgmt/tm/ltm/traffic-matching-criteria` | Traffic matching rules for virtual servers |
| `/mgmt/tm/ltm/traffic-class` | Traffic classification rules |

### Pools & Nodes

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/pool` | All pools — name, members, monitor, load balancing method |
| `/mgmt/tm/ltm/node` | All nodes — address, state (enabled/disabled), monitor status |
| `/mgmt/tm/ltm/default-node-monitor` | Default monitor for nodes |

### Monitors

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/monitor/http` | HTTP health monitors |
| `/mgmt/tm/ltm/monitor/https` | HTTPS health monitors |
| `/mgmt/tm/ltm/monitor/tcp` | TCP health monitors |
| `/mgmt/tm/ltm/monitor/tcp-half-open` | TCP half-open monitors |
| `/mgmt/tm/ltm/monitor/tcp-echo` | TCP echo monitors |
| `/mgmt/tm/ltm/monitor/udp` | UDP health monitors |
| `/mgmt/tm/ltm/monitor/icmp` | ICMP (ping) monitors |
| `/mgmt/tm/ltm/monitor/gateway-icmp` | Gateway ICMP monitors |
| `/mgmt/tm/ltm/monitor/dns` | DNS monitors |
| `/mgmt/tm/ltm/monitor/ftp` | FTP monitors |
| `/mgmt/tm/ltm/monitor/sip` | SIP monitors |
| `/mgmt/tm/ltm/monitor/smtp` | SMTP monitors |
| `/mgmt/tm/ltm/monitor/pop3` | POP3 monitors |
| `/mgmt/tm/ltm/monitor/imap` | IMAP monitors |
| `/mgmt/tm/ltm/monitor/ldap` | LDAP monitors |
| `/mgmt/tm/ltm/monitor/mysql` | MySQL monitors |
| `/mgmt/tm/ltm/monitor/mssql` | MSSQL monitors |
| `/mgmt/tm/ltm/monitor/oracle` | Oracle monitors |
| `/mgmt/tm/ltm/monitor/postgresql` | PostgreSQL monitors |
| `/mgmt/tm/ltm/monitor/radius` | RADIUS monitors |
| `/mgmt/tm/ltm/monitor/radius-accounting` | RADIUS accounting monitors |
| `/mgmt/tm/ltm/monitor/snmp-dca` | SNMP DCA monitors |
| `/mgmt/tm/ltm/monitor/snmp-dca-base` | SNMP DCA base monitors |
| `/mgmt/tm/ltm/monitor/external` | External (script-based) monitors |
| `/mgmt/tm/ltm/monitor/scripted` | Scripted monitors |
| `/mgmt/tm/ltm/monitor/inband` | Inband (passive) monitors |
| `/mgmt/tm/ltm/monitor/real-server` | Real server monitors |
| `/mgmt/tm/ltm/monitor/firepass` | FirePass monitors |
| `/mgmt/tm/ltm/monitor/wmi` | WMI monitors |
| `/mgmt/tm/ltm/monitor/wap` | WAP monitors |
| `/mgmt/tm/ltm/monitor/soap` | SOAP monitors |
| `/mgmt/tm/ltm/monitor/nntp` | NNTP monitors |
| `/mgmt/tm/ltm/monitor/smb` | SMB monitors |
| `/mgmt/tm/ltm/monitor/rpc` | RPC monitors |
| `/mgmt/tm/ltm/monitor/sasp` | SASP monitors |
| `/mgmt/tm/ltm/monitor/diameter` | Diameter monitors |
| `/mgmt/tm/ltm/monitor/mqtt` | MQTT monitors |
| `/mgmt/tm/ltm/monitor/module-score` | Module score monitors |
| `/mgmt/tm/ltm/monitor/virtual-location` | Virtual location monitors |
| `/mgmt/tm/ltm/monitor/none` | No monitor (placeholder) |

### Profiles

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/profile/http` | HTTP profiles (X-Forwarded-For, compression, pipelining) |
| `/mgmt/tm/ltm/profile/http2` | HTTP/2 profiles |
| `/mgmt/tm/ltm/profile/http-compression` | HTTP compression profiles |
| `/mgmt/tm/ltm/profile/http-proxy-connect` | HTTP proxy connect profiles |
| `/mgmt/tm/ltm/profile/httprouter` | HTTP router profiles |
| `/mgmt/tm/ltm/profile/tcp` | TCP profiles (congestion, timeouts, MSS) |
| `/mgmt/tm/ltm/profile/tcp-analytics` | TCP analytics profiles |
| `/mgmt/tm/ltm/profile/udp` | UDP profiles |
| `/mgmt/tm/ltm/profile/fastl4` | FastL4 profiles (layer 4 acceleration) |
| `/mgmt/tm/ltm/profile/fasthttp` | FastHTTP profiles |
| `/mgmt/tm/ltm/profile/client-ssl` | Client SSL profiles (certs, ciphers, TLS versions) |
| `/mgmt/tm/ltm/profile/server-ssl` | Server SSL profiles |
| `/mgmt/tm/ltm/profile/one-connect` | OneConnect profiles (connection pooling) |
| `/mgmt/tm/ltm/profile/web-acceleration` | Web acceleration / caching profiles |
| `/mgmt/tm/ltm/profile/dns` | DNS profiles |
| `/mgmt/tm/ltm/profile/dns-logging` | DNS logging profiles |
| `/mgmt/tm/ltm/profile/ftp` | FTP profiles |
| `/mgmt/tm/ltm/profile/sip` | SIP profiles |
| `/mgmt/tm/ltm/profile/diameter` | Diameter profiles |
| `/mgmt/tm/ltm/profile/fix` | FIX protocol profiles |
| `/mgmt/tm/ltm/profile/mqtt` | MQTT profiles |
| `/mgmt/tm/ltm/profile/rtsp` | RTSP profiles |
| `/mgmt/tm/ltm/profile/sctp` | SCTP profiles |
| `/mgmt/tm/ltm/profile/socks` | SOCKS proxy profiles |
| `/mgmt/tm/ltm/profile/pptp` | PPTP profiles |
| `/mgmt/tm/ltm/profile/tftp` | TFTP profiles |
| `/mgmt/tm/ltm/profile/gtp` | GTP profiles |
| `/mgmt/tm/ltm/profile/html` | HTML profiles (content modification) |
| `/mgmt/tm/ltm/profile/xml` | XML profiles |
| `/mgmt/tm/ltm/profile/rewrite` | URL rewrite profiles |
| `/mgmt/tm/ltm/profile/stream` | Stream profiles |
| `/mgmt/tm/ltm/profile/websocket` | WebSocket profiles |
| `/mgmt/tm/ltm/profile/icap` | ICAP profiles |
| `/mgmt/tm/ltm/profile/ipother` | IP-other profiles |
| `/mgmt/tm/ltm/profile/ipsecalg` | IPsec ALG profiles |
| `/mgmt/tm/ltm/profile/request-adapt` | Request adapt profiles |
| `/mgmt/tm/ltm/profile/response-adapt` | Response adapt profiles |
| `/mgmt/tm/ltm/profile/request-log` | Request logging profiles |
| `/mgmt/tm/ltm/profile/statistics` | Statistics profiles |
| `/mgmt/tm/ltm/profile/smtps` | SMTPS profiles |
| `/mgmt/tm/ltm/profile/pop3` | POP3 profiles |
| `/mgmt/tm/ltm/profile/imap` | IMAP profiles |
| `/mgmt/tm/ltm/profile/ntlm` | NTLM profiles |
| `/mgmt/tm/ltm/profile/radius` | RADIUS profiles |
| `/mgmt/tm/ltm/profile/client-ldap` | Client LDAP profiles |
| `/mgmt/tm/ltm/profile/server-ldap` | Server LDAP profiles |
| `/mgmt/tm/ltm/profile/dhcpv4` | DHCPv4 profiles |
| `/mgmt/tm/ltm/profile/dhcpv6` | DHCPv6 profiles |
| `/mgmt/tm/ltm/profile/netflow` | NetFlow profiles |
| `/mgmt/tm/ltm/profile/ocsp-stapling-params` | OCSP stapling profiles |
| `/mgmt/tm/ltm/profile/certificate-authority` | CA profiles |
| `/mgmt/tm/ltm/profile/connector` | Connector profiles |
| `/mgmt/tm/ltm/profile/qoe` | Quality of Experience profiles |
| `/mgmt/tm/ltm/profile/mblb` | Message-based load balancing profiles |
| `/mgmt/tm/ltm/profile/service` | Service profiles |
| `/mgmt/tm/ltm/profile/splitsessionclient` | Split session client profiles |
| `/mgmt/tm/ltm/profile/splitsessionserver` | Split session server profiles |

### Persistence

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/persistence/cookie` | Cookie persistence |
| `/mgmt/tm/ltm/persistence/source-addr` | Source address persistence |
| `/mgmt/tm/ltm/persistence/dest-addr` | Destination address persistence |
| `/mgmt/tm/ltm/persistence/ssl` | SSL session ID persistence |
| `/mgmt/tm/ltm/persistence/sip` | SIP call-ID persistence |
| `/mgmt/tm/ltm/persistence/hash` | Hash persistence |
| `/mgmt/tm/ltm/persistence/host` | Host persistence |
| `/mgmt/tm/ltm/persistence/msrdp` | MS RDP persistence |
| `/mgmt/tm/ltm/persistence/universal` | Universal persistence (iRule-based) |
| `/mgmt/tm/ltm/persistence/persist-records` | Active persistence records |
| `/mgmt/tm/ltm/persistence/global-settings` | Persistence global settings |

### iRules, Policies & Data Groups

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/rule` | iRules — custom traffic management logic |
| `/mgmt/tm/ltm/rule-profiler` | iRule profiler (performance stats) |
| `/mgmt/tm/ltm/policy` | LTM policies (L7 routing decisions) |
| `/mgmt/tm/ltm/policy-strategy` | Policy strategies |
| `/mgmt/tm/ltm/data-group/internal` | Internal data groups (key-value lists) |
| `/mgmt/tm/ltm/data-group/external` | External data groups (file-based) |
| `/mgmt/tm/ltm/ifile` | iFiles (iRule-accessible files) |

### SNAT & NAT

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/snat` | SNAT configurations |
| `/mgmt/tm/ltm/snat-translation` | SNAT translation addresses |
| `/mgmt/tm/ltm/snatpool` | SNAT pools |
| `/mgmt/tm/ltm/nat` | NAT configurations |

### Authentication (LTM-specific)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/auth/profile` | LTM auth profiles |
| `/mgmt/tm/ltm/auth/ldap` | LTM LDAP auth |
| `/mgmt/tm/ltm/auth/radius` | LTM RADIUS auth |
| `/mgmt/tm/ltm/auth/radius-server` | LTM RADIUS servers |
| `/mgmt/tm/ltm/auth/tacacs` | LTM TACACS auth |
| `/mgmt/tm/ltm/auth/ssl-cc-ldap` | SSL client cert LDAP auth |
| `/mgmt/tm/ltm/auth/ssl-crldp` | SSL CRLDP auth |
| `/mgmt/tm/ltm/auth/ssl-ocsp` | SSL OCSP auth |
| `/mgmt/tm/ltm/auth/crldp-server` | CRLDP server |
| `/mgmt/tm/ltm/auth/kerberos-delegation` | Kerberos delegation |
| `/mgmt/tm/ltm/auth/ocsp-responder` | OCSP responder |

### Cipher & Eviction

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/cipher/group` | Cipher groups |
| `/mgmt/tm/ltm/cipher/rule` | Cipher rules |
| `/mgmt/tm/ltm/eviction-policy` | Cache eviction policies |

### DNS (LTM)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/dns/analytics/global-settings` | DNS analytics settings |
| `/mgmt/tm/ltm/dns/cache/resolver` | DNS resolver cache |
| `/mgmt/tm/ltm/dns/cache/transparent` | DNS transparent cache |
| `/mgmt/tm/ltm/dns/cache/validating-resolver` | DNSSEC validating resolver cache |
| `/mgmt/tm/ltm/dns/dnssec/key` | DNSSEC keys |
| `/mgmt/tm/ltm/dns/nameserver` | DNS nameservers |
| `/mgmt/tm/ltm/dns/tsig-key` | TSIG keys |
| `/mgmt/tm/ltm/dns/zone` | DNS zones |

### Message Routing

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/message-routing/diameter/peer` | Diameter peers |
| `/mgmt/tm/ltm/message-routing/diameter/profile` | Diameter routing profiles |
| `/mgmt/tm/ltm/message-routing/generic/protocol` | Generic message protocol |
| `/mgmt/tm/ltm/message-routing/generic/route` | Generic message routes |
| `/mgmt/tm/ltm/message-routing/generic/transport-config` | Generic transport config |
| `/mgmt/tm/ltm/message-routing/sip` | SIP message routing |
| `/mgmt/tm/ltm/message-routing/mqtt/profile/router` | MQTT router profile |
| `/mgmt/tm/ltm/message-routing/mqtt/profile/session` | MQTT session profile |

### HTML Rules & TACDB

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/html-rule/tag-append-html` | HTML tag append rules |
| `/mgmt/tm/ltm/html-rule/tag-prepend-html` | HTML tag prepend rules |
| `/mgmt/tm/ltm/html-rule/tag-remove` | HTML tag remove rules |
| `/mgmt/tm/ltm/html-rule/tag-remove-attribute` | HTML tag attribute remove |
| `/mgmt/tm/ltm/html-rule/tag-raise-event` | HTML tag raise event |
| `/mgmt/tm/ltm/html-rule/comment-raise-event` | HTML comment raise event |
| `/mgmt/tm/ltm/html-rule/comment-remove` | HTML comment remove |
| `/mgmt/tm/ltm/tacdb/customdb` | Custom TACDB |
| `/mgmt/tm/ltm/tacdb/licenseddb` | Licensed TACDB |
| `/mgmt/tm/ltm/tacdb/query` | TACDB query |

### Global Settings

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/ltm/global-settings/connection` | Connection global settings |
| `/mgmt/tm/ltm/global-settings/general` | General global settings |
| `/mgmt/tm/ltm/global-settings/rule` | iRule global settings |
| `/mgmt/tm/ltm/global-settings/traffic-control` | Traffic control global settings |

---

## GTM Endpoints

### Wide IPs (GSLB)

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/gtm/wideip/a` | A record wide IPs |
| `/mgmt/tm/gtm/wideip/aaaa` | AAAA record wide IPs |
| `/mgmt/tm/gtm/wideip/cname` | CNAME record wide IPs |
| `/mgmt/tm/gtm/wideip/mx` | MX record wide IPs |
| `/mgmt/tm/gtm/wideip/naptr` | NAPTR record wide IPs |
| `/mgmt/tm/gtm/wideip/srv` | SRV record wide IPs |

### GTM Pools

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/gtm/pool/a` | A record pools |
| `/mgmt/tm/gtm/pool/aaaa` | AAAA record pools |
| `/mgmt/tm/gtm/pool/cname` | CNAME record pools |
| `/mgmt/tm/gtm/pool/mx` | MX record pools |
| `/mgmt/tm/gtm/pool/naptr` | NAPTR record pools |
| `/mgmt/tm/gtm/pool/srv` | SRV record pools |

### GTM Infrastructure

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/gtm/datacenter` | GTM data centers |
| `/mgmt/tm/gtm/server` | GTM servers (virtual server discovery) |
| `/mgmt/tm/gtm/prober-pool` | Prober pools |
| `/mgmt/tm/gtm/listener` | GTM listeners |
| `/mgmt/tm/gtm/link` | GTM links (ISP connections) |
| `/mgmt/tm/gtm/distributed-app` | Distributed applications |
| `/mgmt/tm/gtm/iquery` | iQuery connections between GTM devices |
| `/mgmt/tm/gtm/ldns` | LDNS probes |
| `/mgmt/tm/gtm/path` | GTM paths |
| `/mgmt/tm/gtm/region` | GTM regions (topology-based routing) |
| `/mgmt/tm/gtm/topology` | GTM topology records |
| `/mgmt/tm/gtm/rule` | GTM iRules |
| `/mgmt/tm/gtm/persist` | GTM persistence |
| `/mgmt/tm/gtm/traffic` | GTM traffic statistics |
| `/mgmt/tm/gtm/sync-status` | GTM sync status |

### GTM Monitors

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/gtm/monitor/bigip` | BIG-IP monitor |
| `/mgmt/tm/gtm/monitor/bigip-link` | BIG-IP link monitor |
| `/mgmt/tm/gtm/monitor/http` | GTM HTTP monitor |
| `/mgmt/tm/gtm/monitor/https` | GTM HTTPS monitor |
| `/mgmt/tm/gtm/monitor/gateway-icmp` | GTM ICMP monitor |
| `/mgmt/tm/gtm/monitor/tcp` | GTM TCP monitor |
| `/mgmt/tm/gtm/monitor/tcp-half-open` | GTM TCP half-open monitor |
| `/mgmt/tm/gtm/monitor/udp` | GTM UDP monitor |
| `/mgmt/tm/gtm/monitor/external` | GTM external monitor |
| `/mgmt/tm/gtm/monitor/firepass` | GTM FirePass monitor |
| `/mgmt/tm/gtm/monitor/ftp` | GTM FTP monitor |
| `/mgmt/tm/gtm/monitor/gtp` | GTM GTP monitor |
| `/mgmt/tm/gtm/monitor/imap` | GTM IMAP monitor |
| `/mgmt/tm/gtm/monitor/ldap` | GTM LDAP monitor |
| `/mgmt/tm/gtm/monitor/mssql` | GTM MSSQL monitor |
| `/mgmt/tm/gtm/monitor/mysql` | GTM MySQL monitor |
| `/mgmt/tm/gtm/monitor/nntp` | GTM NNTP monitor |
| `/mgmt/tm/gtm/monitor/oracle` | GTM Oracle monitor |
| `/mgmt/tm/gtm/monitor/pop3` | GTM POP3 monitor |
| `/mgmt/tm/gtm/monitor/postgresql` | GTM PostgreSQL monitor |
| `/mgmt/tm/gtm/monitor/radius` | GTM RADIUS monitor |
| `/mgmt/tm/gtm/monitor/radius-accounting` | GTM RADIUS accounting monitor |
| `/mgmt/tm/gtm/monitor/real-server` | GTM real server monitor |
| `/mgmt/tm/gtm/monitor/scripted` | GTM scripted monitor |
| `/mgmt/tm/gtm/monitor/sip` | GTM SIP monitor |
| `/mgmt/tm/gtm/monitor/smtp` | GTM SMTP monitor |
| `/mgmt/tm/gtm/monitor/snmp` | GTM SNMP monitor |
| `/mgmt/tm/gtm/monitor/snmp-link` | GTM SNMP link monitor |
| `/mgmt/tm/gtm/monitor/soap` | GTM SOAP monitor |
| `/mgmt/tm/gtm/monitor/wap` | GTM WAP monitor |
| `/mgmt/tm/gtm/monitor/wmi` | GTM WMI monitor |
| `/mgmt/tm/gtm/monitor/none` | GTM no monitor |

### GTM Global Settings

| Endpoint | Description |
|----------|-------------|
| `/mgmt/tm/gtm/global-settings/general` | GTM general settings |
| `/mgmt/tm/gtm/global-settings/load-balancing` | GTM LB settings |
| `/mgmt/tm/gtm/global-settings/metrics` | GTM metrics settings |
| `/mgmt/tm/gtm/global-settings/metrics-exclusions` | GTM metrics exclusions |

---

## Workflows

### 1. LTM Application Health Check
```
/mgmt/tm/ltm/virtual → list all virtual servers, status
→ /mgmt/tm/ltm/pool → pool status, member states
→ /mgmt/tm/ltm/node → node availability
→ /mgmt/tm/ltm/persistence/persist-records → active sessions
→ Flag: virtuals down, pools with no available members, nodes offline
→ GAIT
```

### 2. SSL/TLS Certificate Audit
```
/mgmt/tm/ltm/profile/client-ssl → client SSL profiles
→ /mgmt/tm/ltm/profile/server-ssl → server SSL profiles
→ /mgmt/tm/ltm/cipher/group → cipher groups in use
→ /mgmt/tm/ltm/cipher/rule → cipher rules
→ Flag: weak ciphers, TLS 1.0/1.1 enabled, expiring certs
→ GAIT
```

### 3. GTM/GSLB Audit
```
/mgmt/tm/gtm/wideip/a → all A-record wide IPs
→ /mgmt/tm/gtm/pool/a → GTM pool health
→ /mgmt/tm/gtm/datacenter → datacenter status
→ /mgmt/tm/gtm/server → server availability
→ /mgmt/tm/gtm/sync-status → GTM sync state
→ Flag: wide IPs with no available pools, datacenters offline
→ GAIT
```

### 4. iRule Review
```
/mgmt/tm/ltm/rule → list all iRules
→ /mgmt/tm/ltm/rule-profiler → iRule performance stats
→ /mgmt/tm/ltm/virtual → which virtuals use which iRules
→ Flag: iRules with high CPU, unused iRules, deprecated commands
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **f5-health-check** | F5 MCP for operational monitoring; pyATS REST for full object inventory |
| **f5-config-mgmt** | F5 MCP for safe config changes; pyATS REST for pre/post audit |
| **f5-troubleshoot** | F5 MCP for troubleshooting; pyATS REST for deep object inspection |
| **pyats-f5-platform** | Platform/system endpoints complement LTM/GTM traffic management view |
| **nvd-cve** | Scan F5 software version against NVD |
| **gait-session-tracking** | Every REST query logged in GAIT |

---

## Guardrails

- **All queries are read-only** — GET requests to iControl REST API only
- **No configuration changes** — never POST/PUT/PATCH/DELETE via this skill
- **Gate changes behind ServiceNow** — any config changes go through f5-config-mgmt with CR
- **Record in GAIT** — every API query must be logged
