# Research: Multi-Region HA Borders (R09)

All figures below are **estimates to be replaced by measurement** (D2). Nothing here required a billed resource.

## D1. Region metadata without a manifest change
- **Decision**: derive a display region from the DNS label (`<region-code>-<id>.automateyournetwork.com`); do not add a field to the signed manifest.
- **Rationale**: `Manifest` in `mcp-servers/protocol-mcp/bgp/federation/ha/config.py` validates node keys with `exact(...)`, and the same strict check is duplicated in `ui/netclaw-visual/src/shared/cluster-binding.js`, the extension and the Mobile `cluster_trust.dart`. A schema change forces a coordinated bump of all four validators and breaks already-shipped clients.
- **Alternatives**: add `region` to the node (rejected: contract break, version bump, re-signing); a side file for labels (rejected: unsigned, spoofable, but display-only anyway, so same trust as parsing).
- **Consequence**: the label is not authority. Clients still trust only the signed manifest endpoints (FR-018).

## D2. Latency and admission window
- **Estimated inter-region RTT** (typical public GCP numbers, to be measured): Montreal-Belgium ~85-95 ms; Belgium-Singapore ~160-180 ms; Montreal-Singapore ~220-250 ms.
- **R08 fact**: injected 300 ms quorum latency exceeded `admission_ms` = 3 s and was safely refused, so an admission needs many sequential quorum round trips (roughly ten). Working model: admission time ~ N x (RTT to nearest follower), with N~10 to be measured.
- **Implication**: NA- or EU-led: ~90 ms x 10 = ~0.9 s (fits 3 s). Asia-led: ~170 ms x 10 = ~1.7 s (fits but thin once the guard and clock uncertainty are added). Worst reported pair 250 ms x 10 = 2.5 s (borderline).
- **Decision**: prefer leader in NA or EU (etcd `move-leader` after election); set `admission_ms` from measurement, expected 5000-6000 ms (manifest bound is 100-10000). Raising it widens the stale-proof window, so it is justified by data and recorded in the evidence matrix. If measured values do not fit even at 10000, report safe refusal and bring the owner options (different third region). No availability claim before measurement.
- **Measurement method (no billed resources before G1)**: offline table from public data in `scripts/ha-rtt-estimate.py` for planning only. Authoritative measurement is the first Deploy task after G1, on the real Borders, before any admission is enabled.

## D3. DNS and certificates
- **Domain**: `automateyournetwork.com` at GoDaddy (owner instruction). Note spec 060's reference used `.ca`; confirm the .com zone is owned and managed at GoDaddy before G1.
- **Scheme**: `<region-code>-<id6>.automateyournetwork.com` for Borders (e.g. `nne1-3fa9c2`, `ew1-b71d04`, `ase1-9c2e55`), where `<id6>` is the first six hex characters of the Border `installation_id`; members `netbox-<id6>`. Unique per cluster generation, so a restore generation never reuses a name.
- **Certificates**: lego DNS-01 using the existing `scripts/lib/godaddy-acme-hook.sh` with a GoDaddy Personal Access Token (spec 060 quickstart B.1). A records via the GoDaddy v1 records API with a `plan` (GET only) default and an explicit `--apply`.
- **Credentials**: absent today (`GODADDY_PAT`, `N2N_ACME_DNS_PROVIDER`, `N2N_CLAW_DOMAIN` not set). Owner supplies them in `~/.openclaw/.env`; never in the repo.

## D4. Infrastructure tooling
- **Decision (revised 2026-11-08, owner asked why OpenTofu)**: no OpenTofu. Use `gcloud` driven by a small Python script `scripts/ha-gcp-multiregion.py` with `plan` (read-only describe, prints what would be created) and `apply` (idempotent describe-before-create, owner-gated). Teardown lists by label `netclaw-spec=182`.
- **Rationale**: about 20 resources (1 VPC, 4 subnets, ~6 firewall rules, 4 IPs, 4 VMs, snapshot schedule). A new tool and local state file add a dependency for little gain at this size; gcloud is already installed and authenticated.
- **Trade-off accepted**: no automatic diff/drift detection; compensated by the label inventory and a post-apply verification task.
- **Alternatives**: OpenTofu/Terraform (plan/diff, state-based teardown; rejected as not worth a new dependency here).
## D5. Network design
- New VPC `netclaw-r09` with a subnet per region; Borders use static external IPs (needed for DNS and clients). Etcd and NCFED ports are allowed only between the three Border IPs (/32). Public ingress is only 443 (HTTPS/WSS) and the iN2N port for member attach. Admin by IAP (35.235.240.0/20 tcp 22), no 0.0.0.0/0 ssh or rdp.
- The old environment and the default network are left untouched (FR-023).

## D6. Closing R08 limits with real faults
| R08 limit | R09 method | Observer |
|---|---|---|
| 1 etcd-path-only partitions; Border-to-Border NCFED cut not exercised | GCP firewall deny rules between exact Border /32s, per port (cluster/NCFED vs etcd), applied and healed by `real_wan_faults.py`; every rule labelled and removed on heal | Border status reads plus VPC flow logs (sampled) |
| 2 clock: forward step only | chrony: `chronyc makestep` with an offset (forward and backward), `timedatectl set-ntp false` skew, process SIGSTOP/SIGCONT for suspend | Border admission refusal codes |
| 5 reply drop client-side | drop the reply with a firewall rule on the member/Border return path after commit | etcd revision plus claim read |
| 7 fenced restore Phase 2 not run | stand up a new-generation Border on an additional labelled VM in an existing region, then operator Phase 2 attempt | restore verify tool |
| 8 native effect not independently observed | native tool writes to NetBox; NetBox's change log counts effects independently of the Border | NetBox changelog API |
- Limits 3, 4, 6, 9-13 are restated per row as in the R08 acceptance packet unless new evidence closes them.

## D7. Client work
- **VS Code (1.6.1)**: already pins the signed manifest and has cluster states. Add region label, per-Border health, and a clear failover indication across the 3 endpoints; add-by-DNS flow must show manifest cluster identity. Version bump and build, hold for approval.
- **Mobile (1.0.4+7)**: enrollment against a 3-endpoint descriptor, `select-node` across regions, background/cold recovery against WAN latency (timeouts tuned from measurement).
- **HUD (1.20.0 on main)**: serve the fixed enrollment route from every Border; region label display only.

## D8. Cost
See [cost-model.md](cost-model.md): about $235/month for the recommended shape, about $165 for the small shape, $300 ceiling, with the old VM adding about $25 while it remains.

## D9. Model (owner decision 2026-11-08): foundation model, no Ollama on Borders
- **Decision**: Borders call a hosted foundation model (Sonnet 5.5, `claude-sonnet-5-5`) over the Anthropic API; no Ollama or local model on any Border.
- **Finding**: the Spec 179 HA execution path is Ollama-specific. `ha/model_transport.py` pins the DefenseClaw guard to `docker-exec://<model_container_id>` and forwards to `http://127.0.0.1:11434`; `config`/`factory` carry `executor.ollama`. A hosted-model transport is therefore **new product code inside the guarded boundary**, not configuration.
- **Consequence**: new task block (design the transport so DefenseClaw guard inspection, admission freshness and the independent model-request counter still hold; egress to the API from each Border; API key only in `.env`/secret store). Qualification of the R08 REAL rows does not transfer and needs fresh evidence for this transport.
- **Cost**: Anthropic API usage is billed by Anthropic, not GCP, and is outside the $300 GCP ceiling unless the owner says otherwise (open question Q-model-budget).
