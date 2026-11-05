# Enrollment contract v1

## HTTP and private RPC

- `GET /api/hud/mobile/enrollment` → private `mobile.enrollment.info {installation_id}`.
- `POST /api/hud/mobile/enrollment` body `{client_nonce: UUID, replace_client_nonce: UUID|null}` → private `mobile.enrollment.issue`, with server-selected `installation_id`.
- `GET /api/hud/mobile/enrollment/:client_nonce` → private `mobile.enrollment.status {installation_id,client_nonce}`.

All require exact selected installation and allowed origin/local access; no arbitrary proxy path, command, environment or admin route. Existing protected owner access applies where configured; explicit owner open-lab mode adds no sign-in. Mutations require deliberate action and exact Origin. No redirects or automatic POST retry. Readiness may be unavailable, never silently enables a listener.

Readiness: `{schema:1,installation_id,available,reason?,endpoint:{border_host,border_port,claw_domain,ws_path},mode:'protected'|'legacy',enrollment_ttl_seconds:120}`.

Issue/status: `{schema:1,installation_id,client_nonce,status:'absent'|'issued'|'consumed'|'expired'|'replaced',expires_ms:number|null,member_id?:string}`. ONLY the initial successful issue includes `qr_matrix:boolean[][]`, square21..177modules, frontend adds4module quiet zone. Matrix is secret-equivalent; no cache/log/storage/export by default.

TTL120seconds, max one outstanding per installation. Issuance is transactional; repeating nonce returns retained status and no QR. New issuance while outstanding requires `replace_client_nonce` equal to the observed outstanding nonce; atomically invalidate it before minting the new offer. Unknown response uses GET status. No automatic replacement; never clear a consumed enrollment.

QR retains `border_host,border_port,claw_domain,enrollment_token`; adds `installation_id,ws_path`. Existing payloads without additions retain legacy local behavior. Cloud port443/path`/mobile/ws`; trusted TLS validates domain. No raw federation port. Narrow loopback WSS upstream receives only the reviewed ingress path and validates Host/Origin/binding; native clients without Origin still prove device key. Browser wrong-origin/host paths fail closed.

Token purpose is mobile-device enrollment and cannot enroll an agent/member through raw iN2N. Consume atomically with device enrollment, persist provenance and reject expired/spent/wrong-purpose offers. Unknown enrollment uses retained same-key hello, never automatic enrollment retry.
