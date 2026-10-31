# Spec 162: Optional Convergence retained flow evidence

Created 2026-10-31. User-authorized implementation of accepted proposal161/PR309.
Base upstream4d791a36; no fork runtime history is imported. Follow checked-in Spec
Kit artifact order manually; proposal161 supplies the agreed scenarios and bounds.

## Acceptance

1. Two read-only stdio MCP tools: convergence_flow_summary(range, exporter?) and
convergence_flow_evidence(address, start, end, exporter?). The service URL, site,
viewer token and exporter allowlist are private fixed configuration. Only GET
/api/flows and /api/flows/records are reachable; no model, collector or write tool.
2. Summary ranges15m/1h/6h/24h; evidence IP and ordered ISO interval at most24h;
exporters must belong to fixed allowlist. HTTPS certificate verification, explicit
loopback-only HTTP opt-in, no URL credentials/redirects, 20-second wall bound and
1MiB decoded payload limit. Reject wrong-site/malformed/unsupported responses and
never reflect secrets or backend bodies in errors.
3. Optional upstream HUD view/routes use these same MCP tools and require the
existing trusted-origin/interface and installation-bound owned-session controls.
Default disabled; no background calls when disabled. Preserve exact summary window
and exporter selection into evidence. Render escaped strings, coverage, provenance,
receipt times, direction and latest100 limit; subset never reconstructs total.
4. Empty, not configured, unauthorized and unavailable remain distinct. Failed
refresh may retain explicitly stale cached data. Receipt age alone is not failure.
5. Installation is isolated and optional, private settings survive upgrades, disable
stops requests and leaves external data intact. Complete coherent catalog/config,
operator skill/docs and release metadata. No charts/service/database/mutation port.
6. Test actual connector/MCP/upstream HUD against disposable retained demo and Linux
host flow evidence, browser interaction and negative access. Linux amd64/arm64 are
the initial matrix; report unexecuted macOS/WSL/Hermes/gateway cases explicitly.

External service is pinned to public fork f54bafca82f339d8573c55c53795fa05bd9dd843.
Its home-lab guide supports an isolated demo without Cisco, Proxmox, K3s or model
access. Synthetic/host/network coverage must survive all connector/UI layers.
