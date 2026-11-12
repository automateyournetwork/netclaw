#!/usr/bin/env bash
# NetClaw in GCP: TUI step (spec 193 / R09C). Sourced by install.sh; shells out to scripts/netclaw-gcp.py so option names,
# warning text and gates are identical on every install path. Nothing is created without the plan hash + cost confirmation.

gcp_warning() {
    echo ""
    echo -e "${RED:-}${BOLD:-}"
    cat "$NETCLAW_DIR/scripts/lib/gcp_warning.txt"
    echo -e "${NC:-}"
}

gcp_deploy_menu() {
    local py="${PYTHON:-python3}" topo project region regions=() cidr out dep sha
    local gcp="$NETCLAW_DIR/scripts/netclaw-gcp.py"
    local ids=(gcp-border gcp-member gcp-border-onprem-members onprem-border-gcp-members ha-risk distributed-risk)
    local opts=(
        "GCP Border              — one Border in GCP"
        "GCP Member              — one Member in GCP (attach to any Border)"
        "GCP Border + on-prem Members — Border in GCP, attach on-prem pyATS/CML Members"
        "On-prem Border + GCP Members — two Members in GCP for your on-prem Border"
        "HA Risk                 — two Borders + etcd witness in one region"
        "Distributed Risk        — a Border in each of three regions"
        "Not now"
    )
    gcp_warning
    tui_yesno "I understand this deployment has NO authentication and its URLs must stay private" "n" || { log_info "Skipped GCP deployment."; return 0; }
    tui_menu "Deploy NetClaw to GCP: choose a topology" "${opts[@]}" || return 0
    [ "$TUI_CHOICE" -ge "${#ids[@]}" ] && return 0
    topo="${ids[$TUI_CHOICE]}"
    command -v gcloud >/dev/null 2>&1 || { log_error "gcloud CLI not found: https://cloud.google.com/sdk/docs/install"; return 1; }
    project="$(gcloud config get-value project 2>/dev/null || true)"
    read -r -p "GCP project id [${project}]: " in; project="${in:-$project}"
    if [ "$topo" = distributed-risk ]; then
        read -r -p "Three regions (space separated, e.g. us-central1 europe-west1 asia-southeast1): " in; regions=($in)
    else
        read -r -p "Region [us-central1]: " in; regions=("${in:-us-central1}")
    fi
    local myip; myip="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
    read -r -p "CIDR allowed to reach HTTPS 443 [${myip:+$myip/32}]: " in; cidr="${in:-${myip:+$myip/32}}"
    local args=(plan --topology "$topo" --project "$project" --https-cidr "$cidr" --ack-no-auth)
    for region in "${regions[@]}"; do args+=(--region "$region"); done
    out="$("$py" "$gcp" "${args[@]}")" || { echo "$out"; log_error "GCP plan refused; nothing was created."; return 1; }
    echo "$out"
    dep="$(echo "$out" | sed -n 's/.*deployment \([0-9a-f]\{6\}\),.*/\1/p' | head -1)"
    sha="$(echo "$out" | sed -n 's/^plan sha256: //p' | tail -1)"
    tui_yesno "Create exactly this plan now? It is billed while it exists" "n" || { log_info "Declined. Nothing was created."; return 0; }
    "$py" "$gcp" apply --deployment "$dep" --plan-sha256 "$sha" --confirm-cost || return 1
    if tui_yesno "Install NetClaw on the new node(s) now?" "y"; then
        "$py" "$gcp" bootstrap --deployment "$dep"
    fi
    log_info "Tear down any time: python3 scripts/netclaw-gcp.py teardown --deployment $dep"
}
