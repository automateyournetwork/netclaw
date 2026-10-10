#!/usr/bin/env bash
# Read-only platform probes; Bash 3.2 compatible. No install commands here.

netclaw_detect_platform() {
    NETCLAW_OS="$(uname -s)" || return 1
    NETCLAW_ARCH="$(uname -m)" || return 1
    case "$NETCLAW_ARCH" in aarch64) NETCLAW_ARCH=arm64 ;; amd64) NETCLAW_ARCH=x86_64 ;; esac
    NETCLAW_OS_VERSION="$(uname -r)" || return 1
    if [ "$NETCLAW_OS" = Darwin ] && command -v sw_vers >/dev/null 2>&1; then
        NETCLAW_OS_VERSION="$(sw_vers -productVersion)" || return 1
    fi
    export NETCLAW_OS NETCLAW_ARCH NETCLAW_OS_VERSION
}

netclaw_choose_component_python() {
    [ "${NETCLAW_PY_EXPLICIT:-0}" = 1 ] && return 0
    local candidate
    for candidate in "$(command -v python3.12 2>/dev/null || true)" \
        /opt/homebrew/opt/python@3.12/bin/python3.12 \
        /usr/local/opt/python@3.12/bin/python3.12; do
        if [ -n "$candidate" ] && [ -x "$candidate" ] && \
            "$candidate" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else 1)' >/dev/null 2>&1; then
            NETCLAW_PY="$candidate"
            export NETCLAW_PY
            return 0
        fi
    done
    return 0
}

netclaw_platform_banner() {
    log_info "Host: $NETCLAW_OS $NETCLAW_OS_VERSION / $NETCLAW_ARCH; Bash $BASH_VERSION"
    log_info "Component Python: $NETCLAW_PY"
}

netclaw_platform_reason() {
    printf '%s\n' "${NETCLAW_UNSUPPORTED_COMPONENTS:-}" | \
        awk -F '|' -v component="$1" '$1 == component { print $2 }'
}

netclaw_component_preflight() {
    python3 "$SCRIPT_DIR/installer-preflight.py" --os "$NETCLAW_OS" \
        --arch "$NETCLAW_ARCH" --python "$NETCLAW_PY" --components "$SELECTED"
}
