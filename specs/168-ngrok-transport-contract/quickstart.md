> Current R01 pilot: DNS/HTTPS, foundation/runtime activation and actual IP
> relocation/recovery are verified. The owner fully delegated these changes and
> requested the full open lab HUD, Anthropic Sonnet and a scoped on-prem subnet
> demonstration. Users/SSO/RBAC remain R15–R17. Use resume.md and verification.md
> for current receipts. Earlier preparation commands below are historical;
> never replay initial activation over the running pilot.

# R01 qualification workflow

Choose [deployment topology](../../specs/168-ngrok-transport-contract/deferred-docs/DEPLOYMENT-TOPOLOGIES.md), then
[direct cloud/private transport](../../specs/168-ngrok-transport-contract/deferred-docs/REMOTE-TRANSPORT.md) or retained
[optional ngrok](../../specs/168-ngrok-transport-contract/deferred-docs/NGROK-TRANSPORT.md). Work in new isolated homes.

1. Use the private Python3.12 environment and pinned protocol dependencies.
2. Run `tests/n2n/test_*168.py` for direct sockets, optional forwarders, identity
   and protocol refusals, owned lifecycle, registry CAS/recovery and migration.
3. Run full federation, affected installer/catalog/HUD and VS Code checks. Preserve
   skips and classify local/fixture results separately from live acceptance.
4. Prepare the [fresh cloud pilot](fresh-pilot.md) and exact saved IaC/cost/expiry/
   budget/teardown review. Cloud mutations remain explicitly gated.
5. After approval, follow [live-runbook.md](live-runbook.md). Capture actual
   Mac↔GCP enrollment/NCFED, all refusals, restart and IP relocation results.
6. Reconcile verification/task evidence, daily memory and GAIT. Stop after R01.

No ngrok API key or paid subscription is required for direct mode. Optional ngrok
retains its two reserved endpoints and owned agent rules. A private/air-gapped
network needs no public endpoint; its offline artifacts/models and real deployment
qualification remain separate from a local socket test. Full runtime migration,
operational cloud workloads and multi-region/multi-cloud acceptance stay in the roadmap.
