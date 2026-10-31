# Plan

Coordinator owns spec, catalog/installer/config/docs/skill, integration qualification,
release metadata and publication. WorkerA owns mcp-servers/convergence-read-mcp and
tests/convergence-read Python connector tests. WorkerB owns ui/netclaw-visual route,
view/wiring and tests. After both finish, independently review the integrated diff.

Shared contract: tools return {ok:true,data:validated_service_payload} or
{ok:false,error:{code,message}} with fixed sanitized messages. Codes: disabled,
not_configured, invalid_argument, unauthorized, unavailable, timeout, compatibility.
Summary/evidence retain the existing service status and coverage within data.
Environment: CONVERGENCE_ENABLED=false, CONVERGENCE_API_URL, CONVERGENCE_API_TOKEN,
CONVERGENCE_SITE, CONVERGENCE_EXPORTERS (comma-separated IPs), and explicit
CONVERGENCE_ALLOW_LOOPBACK_HTTP=false. Endpoint/token never reach browser or errors.
MCP component id convergence-read, two names as spec. HUD routes
/api/hud/convergence/flows and /api/hud/convergence/flows/records; server-side MCP
invocation only. UI feature enabled status comes from trusted server configuration.

Pin public external service f54bafca; keep its compose/data out of this upstream tree.
Fresh private fixture projects qualify source->MCP->upstream browser without models.
Run affected connector, HUD, installer, catalogue, reconciliation/spec/release gates;
add native Linux CI qualification. Publishing a PR is authorized; do not merge an
upstream contribution before review/required gates.
