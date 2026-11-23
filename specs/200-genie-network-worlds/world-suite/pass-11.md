# Pass11 — world2: versioned campaign live packet

Implemented one bounded prerequisite for full-duration Google execution in
`live-packet.mjs`: explicit schema2 binds CAMPAIGN_SESSION_POLICY (120s), exact
integer reservation_microusd and derived allowance_usd, world_number, and the
review artifact SHA256. The operator-pinned launch descriptor selects the review;
packet fields cannot nominate a replacement. Source closure, authority, review
and retained service/input-text evidence are reloaded before credential access.
Schema1 retains its historical20s/$15 format; no stored packet is rewritten.

Validation:87/87 affected supported-Node tests pass, zero skipped. Four added
regressions cover exact versioned binding without admission, policy downgrade /
amount / world / review mismatches, absent review pin and changed evidence before
credential access, and unchanged historical bytes / unsupported schema refusal.
Existing source-closure, campaign accounting, provider, worker, manager and
original-ID recovery tests also pass. Synthetic test credentials only; no owner
credential file, Google endpoint or device was accessed.

Private evidence: `.spec200-local/tests/world-pass-11/affected-tests.log`,
`hashes.json`, native GAIT start/final and retained `gait-log.json`. Existing audit
root/branch reused. No new runtime module; reviewed closure remains29files.
Every old paid packet remains source-stale. No coordinator control, allowance,
acceptance, PROGRESS or sealed-snapshot record changed.

Partial T013 only; no checkbox closure (15/30). No generated visual, visual drift
review, actual provider-cap, installed Risk-member or human acceptance. No camera
or fantasy projection claim follows from packet validation. Manager still uses
historical review/admission and only propagates authority pins; Google sends remain
fail-closed. Next: wire schema2 into manager with frozen four-pin environment,
full-duration review, exact allowance and post-audit reload before
admitReviewedCampaign; exercise audit-await tampering with zero sends.
