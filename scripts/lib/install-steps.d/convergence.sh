#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# NetClaw Convergence (080-convergence) — Phase 5 installer components
# Loaded by install-steps.sh via the install-steps.d/ extension mechanism.
# Editing THIS file will never conflict with upstream install-steps.sh changes.
# Function names: component_install_<id with hyphens→underscores>
# ═══════════════════════════════════════════════════════════════════

component_install_convergence_core() {
log_step "Installing Convergence Core (convergence-api + config)..."
echo "  convergence-api: ui/convergence-api/  |  config: config/convergence.example.yaml"
echo "  Deploy (later in setup): Docker deploy/convergence/ or K3s deploy/convergence/k8s/"

HOME_API_DIR="$NETCLAW_DIR/ui/convergence-api"
if [ -f "$HOME_API_DIR/package.json" ]; then
    if command -v npm >/dev/null 2>&1; then
        log_info "Installing convergence-api npm dependencies..."
        (cd "$HOME_API_DIR" && npm install --omit=dev 2>/dev/null) || \
            log_warn "convergence-api npm install failed — run: cd ui/convergence-api && npm install"
    else
        log_warn "npm not found — install Node.js 20+ for convergence-api"
    fi
else
    log_warn "ui/convergence-api not found at $HOME_API_DIR"
fi

# Seed operator config from example if missing
EX_CFG="$NETCLAW_DIR/config/convergence.example.yaml"
DST_CFG="$RUNTIME_HOME/convergence.yaml"
REPO_CFG="$NETCLAW_DIR/config/convergence.yaml"
if [ -f "$EX_CFG" ]; then
    if [ ! -f "$DST_CFG" ] && [ ! -f "$REPO_CFG" ]; then
        mkdir -p "$RUNTIME_HOME"
        cp "$EX_CFG" "$DST_CFG"
        log_info "Wrote $DST_CFG (edit adapters / deploy mode)"
    else
        log_info "Convergence config already present (not overwriting)"
    fi
else
    log_warn "config/convergence.example.yaml missing — re-pull repo"
fi

log_info "Convergence core ready. Set CONVERGENCE_API_URL / CONVERGENCE_API_TOKEN in $RUNTIME_ENV after deploy (HOME_API_* aliases still work)."
echo "  Docs: specs/080-convergence/quickstart.md  deploy/convergence/README.md"
echo ""
}

component_install_convergence_metrics() {
log_step "Installing Convergence Metrics Stack packaging..."
echo "  Docker: deploy/convergence/docker-compose.yml (postgres, prom, am, blackbox, convergence-api)"
echo "  K3s:    deploy/convergence/k8s/ (kustomize greenfield overlay)"

if [ -f "$NETCLAW_DIR/deploy/convergence/docker-compose.yml" ]; then
    log_info "Docker Convergence stack present"
    if command -v docker >/dev/null 2>&1; then
        log_info "docker available — after setup: ./deploy/convergence/render-config.sh && docker compose -f deploy/convergence/docker-compose.yml --env-file deploy/convergence/.env up -d --build"
    else
        log_warn "docker not found — install Docker Engine for Docker deploy mode"
    fi
else
    log_warn "deploy/convergence/docker-compose.yml missing"
fi

if [ -d "$NETCLAW_DIR/deploy/convergence/k8s/base" ]; then
    log_info "K3s Convergence kustomize base present"
    if command -v kubectl >/dev/null 2>&1; then
        if kubectl kustomize "$NETCLAW_DIR/deploy/convergence/k8s/overlays/greenfield" >/dev/null 2>&1; then
            log_info "kustomize greenfield build OK"
        else
            log_warn "kustomize build failed — check deploy/convergence/k8s/"
        fi
    else
        log_info "kubectl not required unless choosing k3s deploy mode"
    fi
else
    log_warn "deploy/convergence/k8s base missing"
fi

# Seed deploy/convergence/.env from example if missing
if [ -f "$NETCLAW_DIR/deploy/convergence/.env.example" ] && [ ! -f "$NETCLAW_DIR/deploy/convergence/.env" ]; then
    cp "$NETCLAW_DIR/deploy/convergence/.env.example" "$NETCLAW_DIR/deploy/convergence/.env"
    log_info "Seeded deploy/convergence/.env from .env.example (edit secrets before compose up)"
fi

echo ""
}

component_install_convergence_unifi() {
log_step "Installing Convergence UniFi adapter packaging..."
echo "  Exporter: deploy/convergence/adapters/unifi/exporter.py"
echo "  Docker profile: docker compose --profile unifi"
echo "  K3s: unifi-exporter in deploy/convergence/k8s base"

if [ -f "$NETCLAW_DIR/deploy/convergence/adapters/unifi/exporter.py" ]; then
    log_info "UniFi exporter present"
else
    log_warn "UniFi exporter missing under deploy/convergence/adapters/unifi/"
fi

log_info "Credentials (setup prompts when this component is selected):"
echo "  UNIFI_HOST=https://<controller>   UNIFI_API_KEY=<Integration API key>"
echo "  Optional: UNIFI_MGMT_URL for HOME Devices/Wi‑Fi deep-links"
echo ""
}

component_install_convergence_pfsense() {
log_step "Installing Convergence pfSense / edge firewall adapter packaging..."
echo "  Management GUI links: PFSENSE_MGMT_URL / EDGE_MGMT_URL (convergence-api + HUD)"
echo "  Investigations: pfsense-mcp when present under mcp-servers/ (optional)"

if [ -d "$MCP_DIR/pfsense-mcp" ] || [ -d "$HOME/pfsense-mcp" ] || [ -d "/home/ubuntu/pfsense-mcp" ]; then
    log_info "pfSense MCP tree found (use for alert-triage investigations)"
else
    log_info "pfSense MCP not required for metrics path — edge blackbox probe uses HTTPS mgmt URL"
fi

log_info "Configure in setup: PFSENSE_MGMT_URL (default often https://192.168.x.x:440)"
echo ""
}

component_install_convergence_sot_nautobot() {
log_step "Convergence SoT Nautobot adapter..."
echo "  Live adapter (T070): ui/convergence-api/src/lib/adapters/sot.js"
if component_selected nautobot 2>/dev/null || [ ! -f "${NETCLAW_MANIFEST:-/dev/null}" ]; then
    log_info "Prefer installing catalog component 'nautobot' for live SoT MCP"
fi
log_info "convergence.yaml sot.type: nautobot  (env: NAUTOBOT_URL / NAUTOBOT_TOKEN)"
echo ""
}

component_install_convergence_sot_netbox() {
log_step "Convergence SoT NetBox stub..."
echo "  v1: inventory binding stub — NetBox adapter is a stub in sot.js (Nautobot is the live path)"
if component_selected netbox 2>/dev/null || [ ! -f "${NETCLAW_MANIFEST:-/dev/null}" ]; then
    log_info "Prefer installing catalog component 'netbox' for live SoT MCP"
fi
log_info "convergence.yaml sot.type: netbox  (env: NETBOX_URL / NETBOX_TOKEN)"
echo ""
}

component_install_convergence_device_snmp() {
log_step "Convergence device SNMP (campus switches)..."
echo "  Phase 8 plumbing + Phase 10 setup/apply — IF-MIB via snmp_exporter"
echo "  Docs: deploy/convergence/adapters/device-snmp/README.md"
echo "  Spec: specs/080-convergence/telemetry-setup.md"
_setup="$NETCLAW_DIR/scripts/convergence-telemetry-setup.sh"
_apply="$NETCLAW_DIR/scripts/convergence-telemetry-apply.sh"
# Wire setup/apply (T130): auto when CONVERGENCE_TELEMETRY_SETUP=yes; else prompt if yesno exists
if [ -f "$_setup" ] && [ "${CONVERGENCE_TELEMETRY_SETUP:-}" != "skip" ]; then
    _run_setup=0
    if [ "${CONVERGENCE_TELEMETRY_SETUP:-}" = "yes" ]; then
        _run_setup=1
    elif command -v yesno >/dev/null 2>&1 && [ -t 0 ]; then
        if yesno "Run telemetry inventory setup wizard (manual|nautobot|netbox|yaml)?" "y"; then
            _run_setup=1
        fi
    fi
    if [ "$_run_setup" -eq 1 ]; then
        log_info "Running $_setup"
        ( cd "$NETCLAW_DIR" && bash "$_setup" ) || log_warn "telemetry setup exited non-zero"
        if [ -f "$_apply" ] && [ "${CONVERGENCE_TELEMETRY_APPLY:-}" != "no" ]; then
            _run_apply=0
            if [ "${CONVERGENCE_TELEMETRY_APPLY:-}" = "yes" ]; then
                _run_apply=1
            elif command -v yesno >/dev/null 2>&1 && [ -t 0 ]; then
                if yesno "Apply inventory to Prometheus/snmp_exporter now?" "y"; then
                    _run_apply=1
                fi
            fi
            if [ "$_run_apply" -eq 1 ]; then
                log_info "Running $_apply"
                ( cd "$NETCLAW_DIR" && bash "$_apply" ) || log_warn "telemetry apply exited non-zero"
            fi
        fi
    fi
fi
log_info "Setup:  ./scripts/convergence-telemetry-setup.sh   # manual|nautobot|netbox|yaml"
log_info "Apply:  ./scripts/convergence-telemetry-apply.sh"
log_info "Secret: SNMP_COMMUNITY in deploy/convergence/.env"
log_info "Smoke:  ./deploy/convergence/smoke-telemetry-setup.sh && ./deploy/convergence/smoke-device-snmp.sh"
log_info "K3s:    kubectl apply -k deploy/convergence/k8s/overlays/greenfield-device-telemetry"
echo ""
}

component_install_convergence_device_syslog() {
log_step "Convergence device syslog..."
echo "  Greenfield Phase 8 — Promtail UDP :1514 → Loki"
echo "  Docs: deploy/convergence/adapters/device-syslog/README.md"
echo "  K3s:  deploy/convergence/k8s/components/device-syslog/ (T091)"
log_info "Docker: compose -f docker-compose.yml -f docker-compose.full.yml --profile full --profile device-syslog up -d"
log_info "K3s:    include components/device-syslog (requires full-stack Loki)"
log_info "Point switches: logging host <this-host|node-ip> transport udp port 1514"
echo ""
}

component_install_convergence_agent_metrics() {
log_step "Convergence agent metrics (openclaw-token-exporter)..."
EXP_SRC="$NETCLAW_DIR/scripts/openclaw-metrics"
UNIT_SRC="$EXP_SRC/openclaw-token-exporter.service"
UNIT_DST="$HOME/.config/systemd/user/openclaw-token-exporter.service"
if [ -f "$UNIT_SRC" ]; then
    mkdir -p "$HOME/.config/systemd/user"
    # Point WorkingDirectory at repo openclaw-metrics if unit uses placeholders
    cp "$UNIT_SRC" "$UNIT_DST" 2>/dev/null || true
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload 2>/dev/null || true
        systemctl --user enable --now openclaw-token-exporter 2>/dev/null && \
            log_info "openclaw-token-exporter enabled (:9110)" || \
            log_warn "Could not start openclaw-token-exporter — see scripts/openclaw-metrics/README.md"
    fi
else
    log_warn "scripts/openclaw-metrics unit not found"
fi
log_info "Prometheus already scrapes host.docker.internal:9110 (job netclaw-openclaw)"
echo ""
}

component_install_convergence_agent_logs() {
log_step "Convergence agent log forward..."
echo "  Greenfield template: scripts/rsyslog-netclaw-convergence.conf → Promtail :1514"
echo "  Pilot OBS template (legacy): scripts/rsyslog-netclaw-forward.conf"
if [ -f "$NETCLAW_DIR/scripts/rsyslog-netclaw-convergence.conf" ]; then
    log_info "Install: sudo cp $NETCLAW_DIR/scripts/rsyslog-netclaw-convergence.conf /etc/rsyslog.d/60-netclaw-convergence.conf && sudo systemctl restart rsyslog"
else
    log_warn "rsyslog-netclaw-convergence.conf missing"
fi
echo ""
}

component_install_convergence_grafana_dashboards() {
log_step "Convergence Grafana dashboards..."
echo "  Provisioned under deploy/convergence/grafana/provisioning/dashboards/"
echo "  Enable: docker compose -f docker-compose.yml -f docker-compose.full.yml --profile full up -d"
log_info "NetClaw quota board: grafana/provisioning/dashboards/json/netclaw-quota.json"
log_info "Campus switches:     grafana/provisioning/dashboards/json/device-snmp-switches.json"
echo ""
}

component_install_visual_hud() {
log_step "Installing Visual HUD (COMMAND | HOME)..."
echo "  Path: ui/netclaw-visual/  default port 3001"

HUD_DIR="$NETCLAW_DIR/ui/netclaw-visual"
if [ ! -f "$HUD_DIR/package.json" ]; then
    log_warn "ui/netclaw-visual not found"
    echo ""
    return 0
fi

if ! command -v npm >/dev/null 2>&1; then
    log_warn "npm not found — install Node.js 20+ then re-run visual-hud install"
    echo ""
    return 0
fi

log_info "npm install + build..."
(cd "$HUD_DIR" && npm install 2>/dev/null && npm run build 2>/dev/null) || \
    log_warn "HUD npm install/build failed — fix Node and re-run"

# Install systemd user unit from checked-in template
UNIT_TMPL="$NETCLAW_DIR/scripts/systemd/netclaw-hud.service"
UNIT_DST="$HOME/.config/systemd/user/netclaw-hud.service"
if [ -f "$UNIT_TMPL" ]; then
    mkdir -p "$HOME/.config/systemd/user"
    NODE_BIN="$(command -v node || true)"
    if [ -z "$NODE_BIN" ] && [ -x "$HOME/.nvm/versions/node" ]; then
        NODE_BIN="$(find "$HOME/.nvm/versions/node" -type f -name node 2>/dev/null | sort -V | tail -1)"
    fi
    NODE_BIN="${NODE_BIN:-/usr/bin/node}"
    NODE_DIR="$(dirname "$NODE_BIN")"
    sed -e "s|@REPO@|$NETCLAW_DIR|g" \
        -e "s|@HOME@|$HOME|g" \
        -e "s|@NODE@|$NODE_BIN|g" \
        -e "s|@NODE_DIR@|$NODE_DIR|g" \
        "$UNIT_TMPL" > "$UNIT_DST"
    log_info "Wrote $UNIT_DST"
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload 2>/dev/null || true
        systemctl --user enable --now netclaw-hud.service 2>/dev/null || \
            log_warn "Could not enable netclaw-hud.service (start later: systemctl --user enable --now netclaw-hud)"
        log_info "Visual HUD service: systemctl --user status netclaw-hud"
    fi
else
    log_warn "Missing template scripts/systemd/netclaw-hud.service"
fi

echo "  Open http://localhost:3001 → COMMAND | HOME"
echo "  Point HOME at API: CONVERGENCE_API_URL + CONVERGENCE_API_TOKEN in $RUNTIME_ENV"
echo ""
}
