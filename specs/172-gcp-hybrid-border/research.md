# R03 research decisions

Research completed2026-11-02 against accepted R02 `96cbdf0f`. Full sanitized
research receipts are private under `~/.local/share/netclaw/roadmap-r03-20261102/`.

| Decision | Rationale | Alternatives considered |
|---|---|---|
| Separate control-only Border/home/state | R01 contains Sonnet/open lab policy; cannot satisfy R03 by relabeling it | Upgrade R01 rejected for preservation and authority mismatch |
| Dedicated production protected Node entrypoint | Existing local server rejects public authority and starts legacy integrations | Dropping Origin/trusting proxy identity rejected; R01 public proxy unsuitable |
| Caddy named HTTPS on small VM | Owner wants anywhere URL; direct ingress avoids LB standing costs | IAP-only browser does not meet owner intent; IAP remains admin path |
| Four exact operations, bounded browser references | Existing wire contract selects complete args; one approval/effect preserved | Batch authority and new history API deferred |
| Immutable device profile selector | One on-prem member, each child remains single-device; concurrent selection isolated | Four separate member homes add identities/services/secrets |
| No cloud inference | Existing protected Border factory has no executor | Fake `runtime=none` would break supported runtime metadata; keep OpenClaw metadata with explicit role |
| Private dormant eN2N registration | Existing strict registry requires iN2N+eN2N; no R06 scope/exposure | Broader listener-contract migration deferred; verify loopback bind and no firewall ingress |
| Finite isolated qualification | Preserve R01, test fresh apply/teardown and contain incremental cost | Permanent deployment is not implied by R03 acceptance |

Four saved devices are IOS-XE/IOL; only R1 is qualified by R02. Actual keys,
initial privilege states, software versions and sole-command transcripts must be
verified individually. Preserve the R02 pinned adapter's no-discovery policy.

Current authenticated CAD prices yield CAD63.04 for744hours of unchanged R01 plus
one proposed R03 e2-small/disk/IP, before tax/traffic/secrets/legacy storage. A48h
R03 base is CAD1.67; stopping leaves disk/IP charges. Actual accrued charges are
not accessible through current tools. Google Compute Engine has no exact native
monetary cutoff; budget alerts and timers alone do not meet the owner's ceiling.
The cloud packet must resolve remaining cost/egress exposure before activation.

Sources: [R03 brief](../../docs/roadmap/issue-310/briefs/R03-gcp-border-onprem-members.md),
[R02 verification](../171-execution-parity/verification.md),
[account SKU pricing](https://docs.cloud.google.com/billing/docs/how-to/get-pricing-information-api),
[Compute runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime),
[spend-cap limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

No cloud or device mutation occurred during research. Startup `pyats_list_devices`
used a credential-free four-device metadata projection; it does not prove health.
The upstream pyATS server no longer supports stdio: an initial mistaken launch
was stopped and the inventory callable executed directly. Never repeat that
server default; it binds0.0.0.0 unless explicitly configured.
