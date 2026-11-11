# Research: Cisco IQ Remote MCP

## R1. Official contract
- Decision: use issue #346 text as the contract. Rationale: `https://iq.cisco.com/apidocs/mcp-server` returns HTTP 403 to automated fetch (verified with curl and a web fetch tool on 2026-11-11); search results only echo the issue. Alternatives: scrape alternate mirrors (rejected: unofficial, e.g. third-party "Cisco IQ MCP" servers use a different PAT-to-token exchange that the issue says is not needed).
- Verified: all three hostnames answer unauthenticated POST/GET with HTTP 401, `application/problem+json`, `www-authenticate: Session realm="Cisco IQ"`, `UNAUTHENTICATED` code. NOT verified: tool list, schemas, Bearer acceptance with a real key, service-account behaviour, key expiry details.

## R2. Registration mechanism
- Decision: runtime `openclaw.json` entry `mcpServers.cisco-iq-mcp = {url, headers:{Authorization:"Bearer ${CISCO_IQ_API_KEY}"}, env:{CISCO_IQ_API_KEY:"${CISCO_IQ_API_KEY}"}}`, mirroring `meraki-mcp`. Not pre-seeded in repo config because a region is mandatory. Classified external (remote) in `EXTERNAL_INTEGRATIONS`.
- Open point: the runtime config shape used by this install (top-level `mcpServers` vs nested) is detected from existing file; script refuses to guess if neither is found and creates the `mcpServers` container only in a file it has just created.

## R3. Credential handling
- Decision: key only in `.env` (0600) via private atomic writer; read by stdin/no-echo prompt; header template references the variable. Redaction: central `redact()` replaces the key value, any `Bearer <token>` and `Authorization:` values; tests grep every output for a canary key.
- Alternatives: OS keychain (rejected, no existing NetClaw pattern); key inline in config (rejected by issue).

## R4. Region
- Decision: `CISCO_IQ_REGION` in `emea|us|apjc` (case-insensitive aliases `eu`, `eu-central-1` etc. rejected to keep one canonical form). No geolocation, locale or DNS inference anywhere (a test asserts the module imports none of `locale`, `socket.gethostbyname` for inference).

## R5. Diagnose transport
- Decision: stdlib `urllib` POST JSON-RPC `initialize` (+ `notifications/initialized`) then `tools/list` with `Accept: application/json, text/event-stream`; parse JSON or first SSE `data:` event; handle `Mcp-Session-Id`. Live mode opt-in. Findings enum: NOT_ENABLED, KEY_UNSET, ENV_PERMISSIONS, TRANSPORT_FAILURE, AUTH_FAILURE, ZERO_TOOLS, OK.
- Alternatives: MCP Python SDK (rejected: new dependency, spec says stdlib).

## R6. Policy enforcement
- Decision: `config/cisco-iq-policy.json` (mode `deny-by-default`, `allow: []`, `deny_patterns` for create/update/delete/write/set/modify/execute/run/apply/push/remove verbs). `policy-check` classifies a tool list (from `--tools-file` or live) into allowed/denied/unlisted and emits DefenseClaw `tool block` commands. Default allowlist entries are none (we do not know names); admin adds names after reviewing `tools/list`.
- Honest limit: no hard per-tool gate in native client.

## R7. Disable / rotate / update semantics
Per spec Clarifications. Backups: 0600 copies with timestamp; journal stores sha256 digests only.

## R8. Validation without credentials
Mock server on 127.0.0.1 (HTTP allowed only for loopback via an explicit test flag `--allow-insecure-loopback`); contract tests on all subcommands with fixture HOME. Live check: `cisco-iq-enable.sh diagnose --live`, never in CI.
