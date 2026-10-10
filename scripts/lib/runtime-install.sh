#!/usr/bin/env bash
# Rootless, per-install npm options. Never rewrite global npm configuration.
netclaw_install_openclaw() {
    local policy="$NETCLAW_DIR/scripts/runtime-policy.py" npm_options option prefix probe
    local npm_args=()
    python3 "$policy" --runtime openclaw --node "$(node --version)" || return 1
    npm_options="$(python3 "$policy" --npm "$(npm --version)")" || return 1
    while IFS= read -r option; do npm_args+=("$option"); done <<< "$npm_options"
    prefix="$(npm config get prefix)" || return 1
    [ -n "$prefix" ] && [ "$prefix" != undefined ] || { log_error "Cannot determine npm prefix"; return 1; }
    probe="$prefix/lib/node_modules"
    while [ ! -e "$probe" ] && [ "$probe" != / ]; do probe="$(dirname "$probe")"; done
    if [ ! -w "$probe" ] || { [ -e "$prefix/bin/openclaw" ] && [ ! -w "$prefix/bin/openclaw" ]; }; then
        prefix="$HOME/.local"
        log_info "npm's global prefix is not writable; installing OpenClaw with --prefix $prefix"
        npm_args+=(--prefix "$prefix")
    fi
    if ! npm "${npm_args[@]}"; then
        log_error "OpenClaw npm installation failed. Review npm's error above; no sudo retry was attempted."
        log_info "For EACCES, use a user-owned Node version manager or npm --prefix \"\$HOME/.local\"."
        return 1
    fi
    export PATH="$prefix/bin:$PATH"
    hash -r
    if ! command -v openclaw >/dev/null 2>&1 || ! openclaw --version; then
        log_error "OpenClaw executable verification failed after npm install."
        return 1
    fi
    log_info "OpenClaw installed. Keep $prefix/bin on PATH in new shells."
}
