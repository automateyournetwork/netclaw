# Research: VM Security as a second read-only observation

Inspected on 2026-11-06: upstream `main` at `db0c9682` (1.18.6) and the Convergence
service at fork revision
[`024821c8`](https://github.com/byrn-baker/netclaw-convergence/tree/024821c842616eb2d4997889064c74c4e7e716c5).

## What upstream already has

| Capability | Where | Relation to this proposal |
|---|---|---|
| Retained flow summary and evidence | `convergence-read-mcp`, `Convergence.jsx`, spec 162 | Same component, settings, transport and HUD access. This proposal adds one tool and one panel to it. |
| Offline PCAP analysis with Zeek and Suricata | `nsm-mcp`, spec 091, `nsm-ids-triage` skill | Analyses a capture file on disk. No continuous, per-VM observation. |
| Active scanning | nmap skills | Probes targets. Does not observe what a VM itself sends. |
| Grafana, Loki, Prometheus queries | existing observability skills | Could query raw logs, but leaves the pattern rules, VM attribution and coverage limits to the user or model. |

None of these says which VM looked like a scanner in the last five minutes, or how
complete that observation was.

## The service side

- **Analysis:** `services/ids-ingest/vm_security.py` reads at most 10,000 admitted
  observation rows per source over the trailing 300 seconds and computes the three
  patterns. Default configuration enables only the two scan patterns; protected-network
  contact needs an explicit per-source policy.
- **Contract:** `services/ids-ingest/VM-SECURITY-CONTRACT.md` defines the response
  shape, the states and their meaning ("no patterns" is never an all-clear; a null
  counter change is unknown, not zero).
- **Public route:** `ui/convergence-api/src/routes/security.js` exposes
  `GET /api/security/vms` behind the same `authMiddleware` as `/api/flows`, so a
  site-scoped viewer key can read it. `src/lib/vmSecurity.js` already validates the
  internal response strictly before returning it. The route adds a `hostTelemetry`
  block (guest heartbeats), which this proposal leaves out.
- **Observer:** `services/proxmox-observer/collector.py` runs on a Proxmox VE node.
  It is the only live source today.
- **Tests:** the fork has unit tests for the analysis (`test_vm_security.py`), the
  API projection (`test-vm-security.cjs`) and its own HUD panel
  (`convergence-vm-security.mjs`). They exercise the service, not a NetClaw
  integration.

## Gaps this proposal makes explicit

1. **No synthetic source.** Every current source is a real Proxmox node. Spec 161's
   equipment-free rule needs a labeled synthetic source in the service, and a field
   in the response that says so. This is service work and a prerequisite (spec US3).
2. **No recorded qualification.** The VM Security images are pinned in the
   contributor's home-cluster profile, but the fork has no verification record for
   them. The implementation spec must record a real run, as spec 163 did for flows.
3. **Proxmox only.** Other hypervisors have no observer.
4. **Publication.** The service is still published from the fork, as it was when
   spec 162 pinned it. The implementation pins an exact public revision again.

## Alternatives considered

- **Also show guest heartbeats and firewall/IDS summaries.** The service already
  returns them, but each has its own trust model (guest heartbeats are claims made
  by the guest). They would roughly triple the contract to validate. Left for later
  proposals.
- **Let the model query the service directly.** It would have to rebuild the pattern
  rules and coverage limits each time, and would need a broader credential.
- **Link to the service's own dashboard.** Cheapest, and a reasonable maintainer
  choice. It keeps the findings out of NetClaw's sessions and hand-off, though.

## Sensitive data

Findings include internal addresses, ports, VM ids and UUIDs. That is the same kind
of data the flow tools already return, under the same site-scoped viewer key. Values
reach the browser and, on an explicit hand-off, the model. They are never logged by
the connector, and credentials never leave the server.
