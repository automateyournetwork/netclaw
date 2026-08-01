#!/usr/bin/env bash
# NetClaw Convergence — catalog fragment (080-convergence).
# Loaded by catalog.sh via the catalog.d/ extension mechanism.
# Editing THIS file will never conflict with upstream catalog.sh changes.

# ── Convergence components ────────────────────────────────────────
CATALOG+=(
    "convergence-core|Convergence|Convergence Core|convergence-api + CONVERGENCE tab config (080) — diary API, inventory SoT, shared adapter config"
    "convergence-metrics|Convergence|Convergence Metrics Stack|Prometheus + Alertmanager + blackbox (Docker or K3s deploy/convergence)"
    "convergence-unifi|Convergence|Convergence UniFi Adapter|UniFi Integration API exporter + UNIFI_* env for Wi‑Fi metrics"
    "convergence-pfsense|Convergence|Convergence pfSense Adapter|Edge firewall deep-links + optional pfSense MCP for investigations"
    "convergence-sot-nautobot|Convergence|Convergence SoT (Nautobot)|Stub: bind Convergence inventory to Nautobot (requires nautobot component)"
    "convergence-sot-netbox|Convergence|Convergence SoT (NetBox)|Stub: bind Convergence inventory to NetBox (requires netbox component)"
    "convergence-device-snmp|Convergence|Device SNMP (switches)|Greenfield campus switch IF-MIB via snmp_exporter (profile device-snmp)"
    "convergence-device-syslog|Convergence|Device Syslog|Greenfield syslog→Loki for switches/firewall (requires full logs)"
    "convergence-agent-metrics|Convergence|Agent Metrics|Host openclaw-token-exporter + Prom scrape (netclaw_model_*)"
    "convergence-agent-logs|Convergence|Agent Logs|rsyslog/journal ship NetClaw gateway/mesh/alerts → Loki"
    "convergence-grafana-dashboards|Convergence|Grafana Dashboards|Provision network + NetClaw quota dashboards (full profile)"
    "visual-hud|Convergence|Visual HUD|NetClaw Visual HUD (COMMAND|CONVERGENCE) on :3001 + systemd user unit"
)

# ── Convergence profile ───────────────────────────────────────────
# NetClaw Convergence pipeline (080): OBS + convergence-api + HUD + investigator path.
# n2n is included so risk/guardian-claw ensure can enroll the investigator member.
PROFILE_CONVERGENCE="convergence-core convergence-metrics convergence-unifi convergence-pfsense visual-hud \
prometheus gait n2n rag-mcp"

# Register with PROFILE_NAMES (appends if not already present)
[[ "$PROFILE_NAMES" == *convergence* ]] || PROFILE_NAMES="${PROFILE_NAMES} convergence"
