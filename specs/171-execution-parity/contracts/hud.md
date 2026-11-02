# Protected owner HUD contract — R02

Status: coordinator-adopted. No general multi-user/SSO delivery or R01 exposure.

A single owner is provisioned explicitly in private selected-installation config.
Python `protected_owner.py` andthefixedprivatebridge own the durable authority
store and atomic ticket/session operations (schema/methods inexecution.md). Node
adds no dependency or competing owner database. Legacyconversationbindings cannot
authorize newprotectedroutes. Ownercookie is independent and must be read before
existingservermiddleware rewrites cookieheaders.

A local trusted CLI creates a 256-bit ticket (10minute expiry), shown only through
the trusted operator channel. No ticket in command args, URL, logs or transcripts.
At login create an independent owner cookie (32randombytes base64url); store only
its hash. Cookie name `nc_owner_<installationid>` locally; `__Host-nc_owner_...`
on configured HTTPS; HttpOnly/SameSiteStrict/Path=/, noDomain, Secure forHTTPS.
Absolute expiry8hours and idle30minutes; logout and local revoke-all. Private
config generation invalidates old sessions/tickets. Missing config fails closed.

Require exact configured Origin on all mutations, including login; reject absent,
null, multiple, cross-site and malformed origins. R02 only explicit loopback
origins; laterR03 explicitHTTPSorigin, not arbitrary proxy headers. Login requires
application/json and X-NetClaw-Owner-Bootstrap:1. Other mutations require a
session synchronizer X-NetClaw-CSRF token. All requests require selected
X-NetClaw-Installation matchingserver. No wildcard CORS. Reject duplicate cookies,
unknown fields, unbounded payloads and client-supplied principal/roles/signatures.
Apply no-store and frame protections. Recheck session after upstream I/O; expired
or revoked sessions never receive private results.

Routes:
- GET/POST/DELETE `/api/hud/owner/session`: inspect/login/logout.
- GET `/api/hud/operations/catalog`: owned eligible profiles.
- POST `/api/hud/operations`: prepare body `{client_nonce,catalog_revision,
  member_id,model_profile_id,tool,arguments}`; no execution.
- GET `/api/hud/operations?client_nonce=...`: recover same prepare identity.
- GET `/api/hud/operations/:id`: owned operation/status/result.
- POST `/api/hud/operations/:id/decision`: `{revision,review_digest,decision}`.
- POST `/api/hud/operations/:id/reconcile`: empty object; no replay.
- POST `/api/hud/operations/:id/revoke`: empty object; no new execution.

Server derives auth_context (principal, auth_generation, session_hash) from the
active owner session for every fixed-method private bridge call
(contracts/execution.md). No generic tool/daemon forwarding route. Operation
ownership is installation+principal issuer/subject; a fresh authenticated session
for the same owner may recover history after expiry. Foreign identities404.
Error mapping401session,403origin/CSRF/policy,404foreign/missing,409conflict,
413bound,503required service unavailable. Preserve operation IDs on uncertain
outcome and direct the user to status/reconcile. Do not automatically resubmit
failed decisions, recreate operations or restartmodel. Repeated exactclientnonce
must return originaloperation; changedbody409.

`/api/runtime` advertises `capabilities.protectedOperations` only on explicit
profile activation. Add OwnerSessionGate and ApprovedOperationsView to the normal
HUD navigation. Display immutable principal, member identity, model profile, tool,
all exact arguments, digests/expiry and decision. Default protected profile to
operationreview; retain otherHUD features and do not silently enable profile for
existing installations. No protected controls in static/publicR01lab mode.

Render results as server-verified structuredevidence with received/verified/
durableACK distinctions. Unknown status stays visible with sameoperation. Store
only operation/clientnonce in installation-scoped sessionStorage; no auth tokens,
CSRF, provider/device secrets or immutable authority in browserstorage. Use React
text nodes, no untrustedHTML. Ticket/session/rate-limit/error handling have focused
negative tests; browserqualification correlates actualapproval throughmembertool.

Shared owner schema, lock, CLI and private authmethods are inexecution.md.
Node calls owner.login/session/logout; only the native trustedCLI issues tickets.
HTTPmutations compare synchronizerCSRF from owner.session inconstanttime before
operationbridgecall. Expose no general bridge/authmethod proxy. Configuredorigins,
HTTPSmode andinstallation are trustedserverconfiguration. Every private bridge operation validates the active session, installation,
generation, expiry and revocation; a matching principal alone is insufficient.
The browser may not submit auth_context. The backend holds its owner lock through
final active-session checks and durable decision/dispatch claims, and rechecks
read access after external I/O before returning private data.

## R02 protected profile isolation

The explicitly selected protected profile reads only its selected installation
environment, never the repository .env fallback. Its API exposes runtime bootstrap
metadata and the authenticated owner/operation routes only; legacy API and
WebSocket execution is refused even if owner/origin configuration is missing.
The protected navigation presents approved operations and does not poll legacy
local runtimes. Existing unselected profiles, including R01's owner-authorized
lab, remain unchanged. Member-backed broader HUD features belong to subsequent
roadmap acceptance; this profile must not silently invoke a local model/tool.
