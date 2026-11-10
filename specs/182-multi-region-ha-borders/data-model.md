# Data model: Multi-Region HA Borders

No new persistent store. Entities are configuration and evidence records.

- **RegionPlacement** (`scripts/ha-gcp-multiregion.py` config): `region`, `zone`, `code` (nne1|ew1|ase1), `border_id6`, `dns_name`, `static_ip`, `leader_preference` (0-2). Rule: exactly 3, one per region; `dns_name` = `<code>-<id6>.automateyournetwork.com`.
- **DnsRecordPlan**: `name`, `type=A`, `ttl`, `target_ip`, `state` (planned|applied|verified). Rule: apply requires explicit flag and a verified zone read.
- **CostEstimate**: `lines[] {item, qty, unit_usd, total_usd}`, `total_usd`, `ceiling_usd=300`, `owner_confirmed_at`. Rule: infra apply refuses when `owner_confirmed_at` is empty or total > ceiling.
- **OwnershipLabel**: `netclaw-spec=182`, plus `netclaw-role` (border|member|net). Rule: teardown enumerates by label and state only.
- **LatencyRecord**: `from`, `to`, `rtt_ms[]`, `p50`, `p95`, `source` (estimate|measured). Rule: `admission_ms` must cite measured records.
- **FaultRun**: `row`, `method`, `applied_at`, `healed_at`, `observer`, `budget_slot`, `outcome`. Rule: unknown outcomes keep the slot; never reset.
- **ReleaseApproval**: `client` (vscode|mobile|hud), `version`, `action` (publish|push|announce), `approved_by`, `approved_at`. Rule: no outward action without a record; absent for agents.
- **Manifest** (existing, unchanged): nodes <= 3, `endpoints {cluster,in2n,https,wss}`, `limits.admission_ms` in 100..10000.
