# Protected production HUD contract

The dedicated Node entrypoint accepts an explicit selected installation, private
protected bridge descriptor, fixed loopback listen address/port, one exact HTTPS
origin and immutable built-asset manifest. It refuses malformed/missing/conflicting
configuration, ambient `.env`/home fallback, symlink escapes and non-Border role.
No import/start of legacy server, model gateway, Vite, tools or subprocess API.

Require loopback peer, exact configured Host and exact Origin when present;
reject duplicate authority/origin headers. Mutations require Origin plus existing
owner session/CSRF/install checks. Ignore forwarded/edge headers as authority.
Caddy preserves Host/Origin, strips spoofable forwarding identity, redirects to
fixed HTTPS hostname, and never serves protected APIs over plaintext. No wildcard
CORS or WebSocket upgrade. Secure __Host- cookies derive from configured HTTPS.

Public routes: `/`, `/index.html`, explicitly manifested immutable build assets,
minimal `/api/runtime` metadata and existing owner bootstrap/sign-in entrypoints.
Operational catalog/review/status/result/decision routes require the existing
Python owner authority. Unknown methods/routes and all legacy APIs fail closed.
No paths, owner identity, member inventory or results in public bootstrap.

Bound bodies/headers/connections/deadlines/login attempts. Page/API no-store,
nosniff, no-referrer, DENY framing and actual qualified CSP. No ticket/body/cookie/
CSRF in logs. Production asset closure excludes alternate pages, maps/private
files/dotfiles and path traversal. Real trusted-HTTPS browser tests supplement
Node fixtures; source tests alone cannot qualify DNS/TLS/edge behavior.

Four independent immutable reviews; bounded reference collection and full receipt
inspection. Parsed versions come only from verified structured tool output;
missing/unsupported fields stay unavailable. No implicit fan-out, approve-all,
autoreplay or model-derived device facts. Cross-browser history API deferred.

Reference capacity is32. At capacity, preparation refuses until the owner removes
a terminal reference; unresolved references cannot be evicted. Typed retained
operation-ID recovery calls authenticated status, obtains the server nonce/ID,
and persists only that reference; it never prepares a replacement operation.
Version projection requires result.verified===true and
result.evidence.output.tool.parsed===true. Display bounded string fields
result.evidence.output.tool.output.version.version and .os only when present
in a plain structured object. Otherwise show unavailable and full receipt.
A reference is removable only for refused/denied/revoked-before-dispatch (zero
attempts, may_have_executed=false, no reconciliation and no receipt), or a verified
terminal receipt with durable ACK and ack_delivery_pending=false. No unknown,
reconciliation_required, audit_pending or unresolved dispatch may be evicted.

Exact anonymous API allowlist: GET `/api/runtime`; POST
`/api/hud/owner/session` with the existing installation/Origin/bootstrap header
and ticket schema. GET/DELETE owner session require authentication. Existing
operations routes are exactly catalog, prepare, nonce/ID status and ID decision/
reconcile/revoke; all are authenticated. HEAD may serve only document/assets;
Express implicit HEAD must not create an alternate operational response path.

Initial bounds: existing72KiB JSON body and64KiB argument limits;10 valid-shaped
login attempts per60seconds process-wide;16KiB request headers;10second header
and30second complete-request deadlines;5second keep-alive;64 concurrent sockets.
Asset manifest maximum256 entries,8MiB per asset and32MiB total. Limits are fixed
trusted deployment inputs or constants, never request-controlled. Actual loading
and latency qualification may tighten these values; any increase needs an updated
contract and focused boundary tests before deployment.
