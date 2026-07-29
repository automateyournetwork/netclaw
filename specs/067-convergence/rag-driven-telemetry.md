# RAG-driven telemetry setup (Phase 12)

**Status**: Draft  
**Depends on**: Phase 11 complete (OTel Collector as telemetry hub)  
**Input**: Operator wants to monitor a device whose platform has no hardcoded OID
set in the generator. Instead of failing or emitting only IF-MIB, the setup wizard
queries the knowledge RAG for vendor-specific telemetry profiles and, when none
exists, tells the operator exactly what to provide and where to put it.

## The problem today

`render-convergence-telemetry.py` has one global metric list (`OTEL_IF_METRICS`)
applied to every device regardless of role or platform. A lab with routers gets
interface counters but no BGP peer state, no OSPF adjacencies, no CPU/memory.
Adding a new platform means editing the Python script — which is the definition of
"does not scale to a customer who has gear we have never seen."

## The design

```text
                     convergence.yaml
                           │
                    ┌──────▼──────┐
                    │  Generator  │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │ for each device:│                  │
         │ platform = ?    │                  │
         ▼                 ▼                  ▼
  ┌─────────────┐  ┌─────────────────┐  ┌────────────┐
  │ IF-MIB base │  │ RAG lookup:     │  │ hardcoded  │
  │ (always)    │  │ "OID profile    │  │ overrides  │
  │             │  │  for <platform>"│  │ (optional) │
  └──────┬──────┘  └────────┬────────┘  └─────┬──────┘
         │                   │                  │
         └───────────┬───────┘──────────────────┘
                     ▼
          OTel receiver block (merged)
```

### How it works

1. **IF-MIB is always collected.** Interface status, octets, errors, admin status.
   This is the baseline that every SNMP device exposes and the existing boards
   depend on. Never gated on RAG.

2. **Platform-specific metrics come from RAG.** The setup wizard (or the generator
   in `--rag` mode) asks:

   > "What SNMP OIDs should I collect for a device with platform `<network_driver>`
   > and role `<role>`? Return a structured list: metric name, OID, unit, type
   > (gauge or counter), and any resource attributes."

   The LLM reads from the RAG knowledge base — documents that describe per-vendor
   MIB mappings, tested and verified.

3. **If RAG has no answer, the wizard tells the operator:**

   ```
   ⚠ No telemetry profile found for platform "juniper_junos" (role: router).

   IF-MIB collection (interfaces, status, errors) will work out of the box.
   For protocol-specific metrics (BGP, OSPF, CPU, memory), add a vendor
   knowledge document to the RAG:

     Path:  ~/.openclaw/rag/intake/vendor-telemetry/juniper_junos.md
     Format: see deploy/convergence/docs/vendor-telemetry-template.md

   After adding the document:
     1. Ingest:  scripts/rag-ingest.sh
     2. Re-run:  scripts/convergence-telemetry-setup.sh --apply

   The device will be monitored with IF-MIB only until the profile is available.
   ```

4. **RAG answers are validated, not blindly emitted.** The LLM returns structured
   JSON (metric name, OID, unit, type). The generator validates:
   - OID format (dotted integers, starts with 1.3.6)
   - metric name is a legal OTel instrument name
   - unit is one of the known set (By, {errors}, {state}, {peers}, 1, %)
   - type is gauge or sum

   Invalid entries are logged and skipped, not emitted into the collector config.
   A single bad OID must not take down the whole device's collection.

5. **Verified profiles can be cached.** Once a profile for `cisco_nxos` is
   generated and the operator confirms it works (data appears in Prometheus), it
   can be written to `deploy/convergence/otel/profiles/<platform>.yaml` as a
   static override that does not need RAG on subsequent runs. The generator checks
   the static file first, then RAG, then falls back to IF-MIB only.

### Resolution order (per device)

```
1. Static profile override (profiles/<platform>.yaml)  →  use it
2. RAG query for platform + role                       →  validate, use it
3. Neither available                                   →  IF-MIB only + guidance message
```

## Vendor knowledge document format

```markdown
# Telemetry profile: cisco_nxos

Platform: cisco_nxos
Network driver: cisco_nxos
Tested on: Nexus 9300v (NX-OS 10.4)

## SNMP metrics (beyond IF-MIB)

| Metric name | OID | Unit | Type | Resource attributes | Notes |
|---|---|---|---|---|---|
| bgp.peer.state | 1.3.6.1.2.1.15.3.1.2 | {state} | gauge | bgp.peer.address (1.3.6.1.2.1.15.3.1.7) | BGP4-MIB cbgpPeer2State |
| bgp.peer.prefixes.received | 1.3.6.1.4.1.9.9.187.1.2.4.1.1 | {prefixes} | gauge | bgp.peer.address | CISCO-BGP4-MIB |
| cpu.utilization | 1.3.6.1.4.1.9.9.109.1.1.1.1.8 | % | gauge | | cpmCPUTotal5minRev |
| memory.used | 1.3.6.1.4.1.9.9.48.1.1.1.5 | By | gauge | | ciscoMemoryPoolUsed |

## Syslog format

NX-OS emits: `<priority> YYYY Mmm DD HH:MM:SS hostname %FACILITY-SEV-MNEMONIC: message`

Regex: `^<(?P<priority>\d+)>\d{4} (?P<device_time>[A-Z][a-z]{2} +\d+ [\d:]+) (?P<hostname>\S+) %(?P<mnemonic>[A-Z0-9_]+-(?P<sev_level>\d)-[A-Z0-9_]+): (?P<message>.*)$`
```

This is what gets ingested into RAG. Human-readable, version-controlled, and
testable. The LLM reads it and returns the metrics table as structured JSON when
the generator asks.

## What comes from Nautobot vs what comes from RAG

| Data | Source | Populated by |
|---|---|---|
| Device name, IP, role, location | Nautobot | Operator (or network discovery) |
| Platform / network_driver | Nautobot | Operator |
| Manufacturer, model, serial | Nautobot | Operator |
| **Which OIDs to poll for this platform** | RAG | Network engineer (once per platform) |
| **Syslog format regex for this platform** | RAG | Network engineer (once per platform) |
| IF-MIB baseline (universal) | Hardcoded | Always available |
| Thresholds and alert rules | Configuration | Operator |

**Nautobot tells you WHAT devices you have. RAG tells you HOW to monitor them.**

## User experience

### Happy path (profile exists)

```
$ ./scripts/convergence-telemetry-setup.sh --mode nautobot --apply

Querying Nautobot...
  Found 22 devices (8 router, 12 switch, 2 firewall)
  Platforms: cisco_xe (12), cisco_nxos (8), pfsense (2)

Looking up telemetry profiles...
  ✓ cisco_xe    — IF-MIB + BGP + OSPF + CPU (from RAG, verified 2026-07-15)
  ✓ cisco_nxos  — IF-MIB + BGP + CPU + memory (from profiles/cisco_nxos.yaml)
  ✓ pfsense     — IF-MIB only (no SNMP extensions)

Generating collector config...
  22 SNMP receivers, 154 metrics per cisco_xe device, 26 device map entries
  Config valid ✓

Applying...
  otel-collector restarted
  prometheus reloaded
  Done. Grafana: http://127.0.0.1:3300
```

### Missing profile (graceful degradation)

```
$ ./scripts/convergence-telemetry-setup.sh --mode nautobot --apply

Querying Nautobot...
  Found 25 devices (8 router, 12 switch, 2 firewall, 3 juniper)
  Platforms: cisco_xe (12), cisco_nxos (8), pfsense (2), juniper_junos (3)

Looking up telemetry profiles...
  ✓ cisco_xe    — IF-MIB + BGP + OSPF + CPU
  ✓ cisco_nxos  — IF-MIB + BGP + CPU + memory
  ✓ pfsense     — IF-MIB only
  ⚠ juniper_junos — no profile found, using IF-MIB only

  To add Juniper-specific metrics (BGP, routing engine, etc.):
    1. Create: ~/.openclaw/rag/intake/vendor-telemetry/juniper_junos.md
       (template: deploy/convergence/docs/vendor-telemetry-template.md)
    2. Ingest: scripts/rag-ingest.sh
    3. Re-run: scripts/convergence-telemetry-setup.sh --apply

  The 3 Juniper devices will be monitored with interfaces only until then.

Generating collector config...
  25 SNMP receivers (22 with extended metrics, 3 IF-MIB only)
  Config valid ✓
```

## Why this works and stays honest

- **Never blocks setup.** A missing profile degrades to IF-MIB, which still gives
  you interface status, traffic, and errors on every device. The operator can add
  knowledge incrementally.
- **Never hallucinates OIDs.** The LLM reads from ingested, human-verified
  documents. If the document does not exist, it says so rather than inventing.
  Validation catches format errors before they reach the collector.
- **Scales without code changes.** Supporting a new vendor = write one markdown
  document and ingest it. No Python edits, no PR needed.
- **Auditable.** The generated config carries a comment per device saying which
  profile it used and when it was verified. The RAG source documents are in git.

## Scope for Phase 12

| Task | Description |
|---|---|
| T160 | Vendor telemetry document template + example (`cisco_xe.md`) |
| T161 | Generator `--rag` mode: query RAG for platform profile, validate, merge with IF-MIB |
| T162 | Graceful degradation path: IF-MIB only + guidance message when no profile |
| T163 | Static profile cache (`profiles/<platform>.yaml`) as first-check override |
| T164 | Wizard UX: show which platforms resolved, which are IF-MIB-only |
| T165 | Role-aware alert rules (generated or selected per role from RAG) |
| T166 | NX-OS and IOS-XR syslog parser operators (from RAG syslog format docs) |
| T167 | Stagger fix (`initial_delay = i * interval / device_count`) |
| T168 | Smoke: lab-sized inventory (20+ devices, 3+ platforms), end-to-end |

## Out of scope (Phase 12)

- Auto-discovery of devices (Nautobot or manual remains the inventory source)
- Auto-generation of vendor knowledge documents from MIB files (possible later)
- Real-time RAG queries during collector operation (profile resolution is at
  setup/apply time only, not on every poll)
- Multi-collector sharding (document the threshold, don't build an orchestrator)

## Assumptions

- RAG ingest and query infrastructure already exists (`scripts/rag-ingest.sh`,
  `~/.openclaw/rag/`)
- The LLM can return structured JSON when given a clear schema and source documents
- Vendor telemetry docs are a one-time cost per platform, maintained by the
  operator or NetClaw community
- IF-MIB is genuinely universal across all managed SNMP devices
