# Cloud client contract — November 4 correction

The current owner development pilot uses explicit `access.mode: open-lab`, set in
both private protected profile and HUD configuration. A mismatch fails closed.
User authentication is deferred to later roadmap work; there is no login, ticket,
cookie, CSRF credential, hidden auto-login or access-mode prompt in this flow.
`/api/hud/owner/session` returns404 in this mode.

VS Code uses **Add Connection → Local / Cloud → Cloud → Name → URL → Connected**.
It discovers the installation UUID through system-trusted HTTPS `/api/runtime`,
verifies Border role and protectedProfile/protectedOperations/protectedProduction
capabilities, then pins origin and installation. Redirects are refused. An existing
origin with a different installation is refused; the same origin/installation
updates the existing profile without discarding its operation reference. Selecting
an already active profile opens its view without disconnecting or clearing menus.

Protected requests include `X-NetClaw-Installation`; mutations include the exact
configured `Origin` and JSON content type. Normal Host, origin, installation,
method, body-size and operation-scope checks still apply. Runtime advertises an
installation-bound `Unauthenticated lab operator` principal. This is audit
attribution, not user authentication. New reviews require the complete matching
principal; historical owner-approved work may be inspected/reconciled without
changing its principal, approval, attempt or effect. A historical nonce cannot
create a new authority.

Operations use existing `/api/hud/operations`: GET catalog; POST prepare
`{client_nonce,catalog_revision,member_id,model_profile_id,tool,arguments}`;
GET status by `?client_nonce=` or `/id`; POST `/id/decision`
`{revision,review_digest,decision}`; POST `/id/reconcile` `{}`. Persist the nonce
before prepare and retain it on ambiguity. Present the complete immutable review.
Never automatically repeat preparation, a decision or an effect. A signed failed
receipt plus durable ACK resolves a known failed operation; incomplete or genuinely
unknown work remains blocked. Native handlers enforce the same bindings as the UI.

Internal federation mutual TLS and private service capabilities remain service
transport controls. NetBox/provider credentials stay on the member. Local service
management stays local. This protected cloud service does not expose legacy Ask,
Chat, model choice, general MCP, runtime administration or WebSockets. Existing
Mobile QR device enrollment requires the separately assessed R04b work.

The earlier owner-cookie/ticket contract remains compatibility behavior outside
explicit open-lab mode and is retained in historical November3 evidence. It is not
an installation or sign-in instruction for this owner pilot.
