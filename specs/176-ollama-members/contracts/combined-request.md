# Combined request and client contract

Add `calculator_combined_v1` capability to the existing protected catalog. Keep
existing single-operation endpoints and records compatible. HUD, VS Code and
Mobile show unavailable when the capability is absent; no fallback POST sequence.

## Minimal route additions

All routes inherit current selected-installation, origin/CSRF where applicable,
open-lab/owner/device principal, HTTPS and body-size controls. No new login scheme.
Device WSS equivalents use the same authorization service and stable nonce.

| Method/route | Request | Response / behavior |
|---|---|---|
| POST `/api/hud/operations/combined` | `client_nonce`, `children` containing exactly `{family,member_id,profile_revision,cidr}` for IPv4 then IPv6 | Atomic durable parent + two existing child reviews; no inference/tool execution |
| GET `/api/hud/operations/combined?client_nonce=…` | Persisted pre-submit nonce | Same parent/children or authoritative absence; never creates work |
| GET `/api/hud/operations/combined/{parent_id}` | Parent reference | Bounded immutable plan, child states/review digests, results/evidence references |
| POST `/api/hud/operations/combined/{parent_id}/cancel` | Empty object | Revoke pending children using existing authority; retain finished/unknown evidence |

Child decisions continue through existing
`POST /api/hud/operations/{operation_id}/decision` with exact
`{revision,review_digest,decision}`. Never add an approve-all route. IPv4 is reviewed
first, then IPv6 after the first decision is durably known; the first child's runtime
completion is not a precondition for the second decision. Denial/failure of one child
does not approve, cancel or corrupt the other. Parent cancellation forbids any later
approval and preserves outcomes of already dispatched work.

Mobile equivalents: `n2n/edge/operations/combined_prepare`, `combined_status`,
`combined_cancel`; existing `decision` remains child-scoped. Methods must be explicitly
allowlisted; bodies cannot choose URL, backend, tool code or operator identity.

## State and idempotency

Server derives tool, full model profile, placement, limits, principal and current
authority from the selected catalog. Exactly one child per family; reject duplicates,
extra fields/children, changed member/profile, unsupported family or invalid CIDR.
Parent and child nonce associations are committed atomically, before the response.
Same principal+nonce+canonical request returns the same records; changed request under
the nonce conflicts. Foreign principal/installation references deny access.

Parent plan expiry is15min from creation, clipped to applicable authority/deployment
expiry. Existing child review expiration remains authoritative: if it expires before
decision, refuse; never silently refresh it. Approved child execution is at most180s
and clipped to parent/deployment bounds. Longer idle review requires explicit new work.

Parent status is a display aggregation, not authority: `awaiting_decisions`,
`running`, `complete`, `partial`, `failed`, `cancelled`, `unknown`.
Any unresolved dispatched child makes aggregate `unknown`; both succeeded makes
`complete`; one succeeded plus a final refused/failed/cancelled sibling makes
`partial`. Nonterminal children keep their visible own state. An earlier failed
attempt cannot be relabeled by a later successful operation.

Persist before submission: selected installation, principal/device binding,
parent client nonce; then parent ID and exactly two child IDs plus per-child
decision-submitted markers. No prompt/CIDR/result/secrets in durable client storage.
Network errors and missing replies are uncertain; recover by GET/status only.
Duplicate clicks are suppressed locally and idempotent server-side. Reconnect,
background, view reopen, profile switching and process restart never repeat POST.
Reconciliation may inspect signed evidence but cannot issue a new execution claim.

## Presentation and acceptance

Show both children with exact CIDR, executor, hosting and inference location, model,
limits, review expiry and separate approval actions. Show authoritative arithmetic
before explanation, per-child time/usage, API charge0 with compute-cost distinction,
failure/unknown reason and retained result/ACK references. Large counts remain strings.

G12: actual installed Mac VS Code, existing Name + URL selection, combined review,
two approvals/results, one-child failure and restart/status-only recovery.
G13: existing enrolled device key/QR binding, native iPhone simulator combined flow,
one-child failure, cold/background reconnect and unchanged original effect counts.
Physical camera/SecureEnclave and untested platforms remain unqualified.
