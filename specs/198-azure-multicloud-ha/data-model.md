# Data Model: R10 Azure

> Current resumption: [resume-20261124.md](resume-20261124.md). The owner resumed
> bounded work on November24. Its scope, budget gate and measured latency finding
> supersede the historical status, topology and sequencing below. No new live
> acceptance is implied. The binding peer contract uses ONE group per member.

All state is files; nothing is stored in a database.

- **Phase** `{id: p1-preflight|p2-single|p3-ha|p4-mesh, resource_group, regions[], status: planned|go|up|verified|down, go_at, down_at, est_cost_usd, tag: netclaw-spec=198, phase=<id>}`
- **Ledger** (`r10-ledger.json`, 0600) `{ceiling_usd:25, pause_usd:15, entries:[{phase, resource, rate_usd_per_h, started_at, stopped_at|null, est_usd}], total_est_usd, paused:boolean}`; rule: new billable entry refused when `total_est_usd + projected_next_hour >= 15` until owner approval recorded as `approved_over_pause_at`; hard refusal at 25.
- **PreflightReport** `{subscription_state, regions:[{region, size, available, quota_free_vcpus, verdict: go|blocked, reason, substitute|null}], budget_alert: present|missing, secrets_present:{godaddy, anthropic, netbox}}` (booleans only, never values)
- **EvidenceRecord** (appended to `verification.md`) `{phase, what_ran, passed[], failed[], measured_cost_usd, teardown_verified:boolean}`
- **Run identity** `{generation, nodes:[{code, region, dns_name, public_ip}]}` as produced by existing `r09_prepare.py`.
