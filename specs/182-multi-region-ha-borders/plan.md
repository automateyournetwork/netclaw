# Implementation Plan: Multi-Region HA Borders (R09)

**Branch**: `182-multi-region-ha-borders` | **Date**: 2026-11-08 | **Spec**: [spec.md](spec.md)
**Input**: `specs/182-multi-region-ha-borders/spec.md`; R08 closure docs in `specs/179-border-ha-authority/`.

## Summary

Deploy the Spec 179 three-voter Border cluster across northamerica-northeast1, europe-west1 and
asia-southeast1 in `netclaw-506315`, each Border at a unique DNS name under `automateyournetwork.com`
(GoDaddy DNS, lego DNS-01 certificates from spec 060). Add a NetBox cloud member and on-prem pyATS and CML
members that attach outbound over iN2N. Prove it with real WAN faults (GCP firewall cuts, chrony clock steps,
owned-process stops), then update VS Code, Mobile and HUD under the R09 release gate.

Key design findings (see [research.md](research.md)):
- The signed manifest already supports up to 3 Borders with `host`, `server_name`, `https` and `wss` per node,
  and clients already select among at most three verified manifest endpoints. **No manifest schema change is
  needed.** Region is display-only metadata parsed from the DNS label, so the signed contract and every
  validator (Python, TypeScript, Dart, JS) stay compatible (Constitution XV).
- Latency, not region count, is the risk. R08's safe refusal at 300 ms quorum latency shows an admission
  needs many sequential quorum round trips. Leader placement (NA or EU) plus a measured `admission_ms`
  (manifest bound 100-10000 ms) decides feasibility. An Asia-led state is tested as a degraded mode.
- Real WAN cuts need no production seam: GCP firewall deny rules between exact Border IPs cut the cluster
  and NCFED ports. This closes R08 limit 1 (NCFED Border-to-Border cut) with real network behaviour.
- NetBox's own change log is an independent observer of native effects (closes R08 limit 8).

## Technical Context

**Language/Version**: Python 3.10+ (Border source `mcp-servers/protocol-mcp/bgp/federation/ha/*`, contract
envs 3.12), TypeScript (VS Code extension 1.6.1), Dart/Flutter (Mobile 1.0.4+7), JS/Node (HUD), Bash, gcloud
(scripted) for infrastructure.
**Model**: hosted foundation model (Sonnet 5.5) via Anthropic API; no Ollama on Borders (needs a new model transport, research D9).
**Primary Dependencies**: etcd (3 voters, per Spec 179), lego (ACME DNS-01), GoDaddy API (Personal Access
Token + existing `scripts/lib/godaddy-acme-hook.sh`), chrony, Docker, NetBox, pyATS and CML MCP members, GCP
Compute (VPC, firewall, static IP, IAP). No new Python packages.
**Storage**: Existing etcd/SQLite/GAIT stores; per-Border persistent disk. No new datastore.
**Testing**: pytest on python3.10 locally (Linux CI differs from macOS: /proc, ps lstart), extension and
HUD node tests, Flutter tests, `scripts/ha-gcp-multiregion.py plan` (read-only, no apply), real WAN matrix runs.
**Target Platform**: GCP Compute Engine Linux VMs (3 regions); on-prem Linux/WSL2 members; clients on macOS/iOS.
**Project Type**: infrastructure + multi-client (server, VS Code extension, mobile app, web HUD).
**Performance Goals**: admission completes inside the signed `admission_ms`; leader failover completes within
the lease; targets set from measured RTT (not assumed).
**Constraints**: total <= $300/month; no billed resource before owner confirms the estimate; no publish or
push-live without owner approval; one budget slot per unknown, never reset.
**Scale/Scope**: 3 Borders, 3-4 members, 3 client builds, one evidence matrix.

## Constitution Check

| Gate | Status | Note |
|---|---|---|
| I Safety-First / VIII Verify | PASS | Read-only inventory first; apply only after owner confirmation; post-deploy verification tasks. |
| IV Immutable audit trail | PASS | GAIT log per session; evidence exported before any removal. |
| V MCP-native | PASS | No new capability bypasses MCP; NetBox/pyATS/CML are existing MCP members. |
| IX Security by default | PASS | No world-open ssh/rdp; IAP admin; scoped firewall; members hold no consensus credentials. |
| XI Artifact coherence | ACTION | Docs/README/installer touchpoints listed in tasks; counts via `scripts/reconcile-mcp.py` if any MCP is added. |
| XIII Credential safety | PASS | GoDaddy token and GCP keys only in `.env` / secret store, never in repo or specs. |
| XIV Human-in-the-loop | PASS | Owner approves cost, DNS writes, deploy, teardown, every release step. |
| XV Backwards compatibility | PASS | No manifest schema change; region is derived display metadata; old clients keep working. |
| XVI Spec-driven | PASS | This spec folder and branch. |

Post-design re-check: PASS (no new violations; see Complexity Tracking, empty).

## Phases

0. **Research and estimate** (done in [research.md](research.md), no billed resources): RTT estimates from public
   data, cost model, DNS scheme, IaC tooling, fault methods.
1. **Design** ([data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)).
2. **Source work, offline** (no cloud): region display parser in the 4 validators' client layers, VS Code
   multi-endpoint UX, Mobile enrollment against a 3-endpoint descriptor, HUD route check, fault tooling
   (firewall cut driver, clock-step driver), cost/IaC/DNS scripts with dry-run modes, tests on Linux and macOS.
3. **Owner gate G1 (cost + DNS)**: owner confirms line-item estimate and provides the GoDaddy token location.
4. **Deploy** (billed, after G1): gcloud apply for VPC, firewalls, IPs, VMs; GoDaddy A records; lego certs;
   etcd 3-voter bootstrap; measure real RTT FIRST; set `admission_ms` and leader placement; NetBox; members.
5. **Owner gate G2 (screenshot)**: owner adds the 3 Borders by DNS name in VS Code and captures the screenshot.
   Old environment untouched.
6. **Qualification**: real WAN matrix (one-region loss, 3-way cut, Border-to-Border NCFED cut, clock
   forward/backward/suspend, fenced restore Phase 2, independent effect counts via NetBox). Unknown-producing
   scenarios last, one per run.
7. **Release gate**: bump versions, build VS Code/Mobile/HUD; STOP for owner approval of each outward step;
   re-run journeys against published builds.
8. **Teardown** (only on the owner's request, with exact resource list and separate confirmation).

## Project Structure

### Documentation (this feature)

```text
specs/182-multi-region-ha-borders/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── cost-model.md
├── contracts/
│   ├── dns-naming.md
│   ├── region-display.md
│   └── ownership-labels.md
├── checklists/requirements.md
└── tasks.md            # next: /speckit.tasks
```

### Source Code (repository root)

```text
scripts/ha-gcp-multiregion.py   # NEW: gcloud plan/apply/teardown by label (plan only until G1)
labs/ha/real_wan_faults.py      # NEW: firewall cut/heal + chrony clock-step drivers (qualification-only)
scripts/ha-dns-godaddy.py       # NEW: GoDaddy A-record plan/apply with --dry-run default
scripts/ha-cost-estimate.py     # NEW: line-item estimate from infra plan, fails if > ceiling
scripts/ha-rtt-estimate.py      # NEW: offline RTT table + admission budget calculator
extensions/netclaw-vscode/src/client/cluster.ts       # region label + multi-endpoint status
mobile/netclaw-mobile/lib/ncfed/endpoint_recovery.dart  # region label + select-node across regions
ui/netclaw-visual/src/shared/cluster-binding.js       # region label (display only)
tests/n2n/test_ha_multiregion_182.py                  # NEW
```

**Structure Decision**: infrastructure script in `scripts/`, qualification drivers beside the R08 labs in
`labs/ha/`, clients extended in place. Product Border code under `mcp-servers/protocol-mcp/bgp/federation/ha/`
is not changed unless task T-seam proves a seam is unavoidable.

## Complexity Tracking

None.
