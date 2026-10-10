#!/usr/bin/env bash
# Single installation path for every NetClaw Python dependency.
#
# Spec 077 (roadmap R0a) FR-003, FR-003a, FR-003b.
#
# WHY THIS EXISTS
#
# `pip3` and `python3` are not guaranteed to be the same interpreter. Observed on
# a real development host:
#
#     python3 -> /usr/bin/python3        3.14.4   cryptography 46.0.5
#     pip3    -> ~/.local/bin/pip3       3.13     cryptography 45.0.2
#
# A bare `pip3 install` there lands in a stranded site-packages that `python3`
# cannot import from. The install reports success and the server dies at first use
# with ModuleNotFoundError — the worst kind of failure, because nothing looks wrong
# until much later.
#
# Before this helper, 130 install sites each decided independently where packages
# went. Exactly one was interpreter-scoped, and it was written by hand only because
# its author had just been burned by this. That is not a repeatable safeguard, which
# is why enforcement is mechanical now: `scripts/check-dependency-pins.py` fails on
# any new bare invocation.
#
# Constitution Principle XV ("new dependencies MUST be isolated") is unenforceable
# while each call site picks its own target.
#
# USAGE
#
#   netclaw_pip_install <args...>                  # into NETCLAW_PY (default python3)
#   NETCLAW_VENV=/path/to/.venv netclaw_pip_install <args...>   # into that venv
#   netclaw_venv_create /path/to/.venv             # create a venv that actually works
#
# Shared installs enforce tracked compatibility constraints; dedicated venvs
# use their own requirements. Distro-managed Python is never overridden.

# Interpreter that NetClaw's servers actually run under. Overridable for testing.
: "${NETCLAW_PY:=$(command -v python3)}"
NETCLAW_SHARED_CONSTRAINTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../config" && pwd)/python-shared-constraints.txt"
NETCLAW_PREFLIGHT_POLICY="$(dirname "$NETCLAW_SHARED_CONSTRAINTS")/installer-preflight.json"

_netclaw_python_supported() {
    "$1" -c 'import sys,json
if not (sys.version_info >= (3, 10)): sys.exit(1)
if not sys.argv[2]: sys.exit(0)
policy=json.load(open(sys.argv[1]))
rule={**policy["defaults"], **policy["components"].get(sys.argv[2], {})}
version=sys.version_info[:2]
sys.exit(0 if version >= tuple(rule["python_min"]) and ("python_max_exclusive" not in rule or version < tuple(rule["python_max_exclusive"])) else 1)
' "$NETCLAW_PREFLIGHT_POLICY" "${NETCLAW_INSTALL_COMPONENT:-}" >/dev/null 2>&1
}

_netclaw_require_python() {
    _netclaw_python_supported "$1" && return 0
    echo "NetClaw requires Python 3.10+ and the selected component's version bounds; unsupported interpreter: $1 ($("$1" --version 2>&1 || true))" >&2
    echo "  Select a compatible NETCLAW_PY and put its python3 on PATH; see docs/PYTHON-RUNTIME-MIGRATION.md." >&2
    return 1
}

_netclaw_check_runtime_target() {
    if [ -L "$1" ] || { [ -e "$1" ] && [ ! -f "$1/.netclaw-managed" ]; }; then
        echo "Refusing to adopt an unmanaged Python environment: $1" >&2
        return 1
    fi
}

# Select a component's conventional source venv without rebuilding it in place.
# Existing compatible source venvs retain their path; old Python is preserved.
netclaw_component_venv() {
    NETCLAW_COMPONENT_VENV="$1"
    if [ -x "$1/bin/python" ]; then
        _netclaw_python_supported "$1/bin/python" && return 0
        _netclaw_require_python "$NETCLAW_PY" || return 1
        local version
        version="$("$NETCLAW_PY" -c 'import sys; print("%s.%s" % sys.version_info[:2])')" || return 1
        NETCLAW_COMPONENT_VENV="$1-py$version"
        echo "Keeping unsupported Python environment at $1; using $NETCLAW_COMPONENT_VENV" >&2
    fi
    _netclaw_check_runtime_target "$NETCLAW_COMPONENT_VENV" || return 1
    if [ ! -x "$NETCLAW_COMPONENT_VENV/bin/python" ]; then
        _netclaw_require_python "$NETCLAW_PY" || return 1
        mkdir -p "$NETCLAW_COMPONENT_VENV" || return 1
        printf '%s\n' "${NETCLAW_INSTALL_COMPONENT:-component}" > "$NETCLAW_COMPONENT_VENV/.netclaw-managed" || return 1
        netclaw_venv_create "$NETCLAW_COMPONENT_VENV" || return 1
    fi
    _netclaw_require_python "$NETCLAW_COMPONENT_VENV/bin/python"
}

_netclaw_modern_component_pip() {
    local py="$1"
    # pip 21.2 (Apple ensurepip) cannot build modern editable pyprojects.
    "$py" -c 'import re,sys; from importlib.metadata import version; v=re.match(r"(\d+)\.(\d+)", version("pip")); sys.exit(0 if v and tuple(map(int,v.groups())) >= (21,3) else 1)' >/dev/null 2>&1 && return 0
    # Never bootstrap/upgrade system pip, even for an explicitly selected base.
    if ! "$py" -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)' >/dev/null 2>&1; then
        echo "Refusing to upgrade system pip; select an isolated component runtime." >&2
        return 1
    fi
    echo "Upgrading obsolete pip inside component runtime: $py" >&2
    "$py" -m pip install --upgrade 'pip>=23' || return 1
}

_netclaw_resolve_py() {
    # An explicit venv always wins.
    if [ -n "${NETCLAW_VENV:-}" ]; then
        if [ -x "$NETCLAW_VENV/bin/python" ]; then
            printf '%s' "$NETCLAW_VENV/bin/python"; return 0
        fi
        echo "netclaw_pip_install: NETCLAW_VENV=$NETCLAW_VENV has no bin/python" >&2
        return 1
    fi
    if [ -x "$NETCLAW_PY" ]; then printf '%s' "$NETCLAW_PY"; return 0; fi
    # Fall back to whatever python3 resolves to, but only if it is real.
    if command -v python3 >/dev/null 2>&1; then
        printf '%s' "$(command -v python3)"; return 0
    fi
    return 1
}

# Install packages into the interpreter the target will actually run under.
#
# FR-003b: fails loudly rather than silently falling back to a bare `pip`. A silent
# fallback would reintroduce the exact bug this helper exists to prevent, while
# looking like it had been fixed.
_netclaw_pip_install() {
    local py
    # Source patches are reviewed and hash-checked before package resolution.
    # Never apply a speculative substitution to an upstream/operator-edited clone.
    if [ -n "${NETCLAW_INSTALL_COMPONENT:-}" ] && [ -n "${NETCLAW_DIR:-}" ]; then
        python3 "$(dirname "$NETCLAW_SHARED_CONSTRAINTS")/../scripts/apply-fastmcp-patches.py" \
            --root "$NETCLAW_DIR" --component "$NETCLAW_INSTALL_COMPONENT" || return 1
    fi
    # Installer calls have a component context. Never fall through to distro
    # Python for these calls; manual helper callers retain explicit selection.
    if [ -n "${NETCLAW_INSTALL_COMPONENT:-}" ] && [ -z "${NETCLAW_VENV:-}" ]; then
        local target="$NETCLAW_RUNTIME_ROOT/$NETCLAW_INSTALL_COMPONENT"
        if [ -f "$(dirname "$NETCLAW_SHARED_CONSTRAINTS")/python-components/$NETCLAW_INSTALL_COMPONENT.txt" ]; then
            # Do not upgrade a partially installed legacy SDK in place. Its
            # distributions may share import names with the newer SDK.
            target="$target-component-bounds"
        fi
        _netclaw_check_runtime_target "$target" || return 1
        if [ -x "$target/bin/python" ] && ! _netclaw_python_supported "$target/bin/python"; then
            local base version
            base="$(_netclaw_resolve_py)" || return 1
            _netclaw_require_python "$base" || return 1
            version="$("$base" -c 'import sys; print("%s.%s" % sys.version_info[:2])')" || return 1
            echo "Keeping unsupported Python environment at $target; using $target-py$version" >&2
            target="$target-py$version"
            _netclaw_check_runtime_target "$target" || return 1
        fi
        if [ ! -x "$target/bin/python" ] || ! "$target/bin/python" -m pip --version >/dev/null 2>&1; then
            mkdir -p "$target" || return 1
            printf '%s\n' "$NETCLAW_INSTALL_COMPONENT" > "$target/.netclaw-managed"
            netclaw_venv_create "$target" || return 1
        fi
        py="$target/bin/python"
    elif ! py="$(_netclaw_resolve_py)"; then
        echo "netclaw_pip_install: cannot determine a Python interpreter." >&2
        echo "  Set NETCLAW_PY to the interpreter your servers run under," >&2
        echo "  or NETCLAW_VENV to a virtualenv. Refusing to fall back to bare pip," >&2
        echo "  which on a split-toolchain host installs where nothing can import it." >&2
        return 1
    fi
    _netclaw_require_python "$py" || return 1
    if ! "$py" -m pip --version >/dev/null 2>&1; then
        echo "netclaw_pip_install: $py has no usable pip module." >&2
        echo "  Remedy: $py -m ensurepip --upgrade   (or install the matching *-venv package)" >&2
        return 1
    fi
    if [ -n "${NETCLAW_INSTALL_COMPONENT:-}" ]; then
        _netclaw_modern_component_pip "$py" || return 1
    fi
    # PEP 668 protects distro packages. Report refusal with a venv remedy;
    # never silently override it or claim the component was installed.
    # Constrain the shared legacy runtime. Dedicated environments carry their
    # own manifests and must not inherit incompatible shared MCP1 constraints.
    if [ -z "${NETCLAW_VENV:-}" ]; then
        local constraints="$NETCLAW_SHARED_CONSTRAINTS"
        # A newer SDK may be used only in its automatic isolated runtime.
        # Keep the legacy shared contract for manual/system helper calls.
        if [ -n "${NETCLAW_INSTALL_COMPONENT:-}" ]; then
            local component_constraints="$(dirname "$NETCLAW_SHARED_CONSTRAINTS")/python-components/$NETCLAW_INSTALL_COMPONENT.txt"
            [ ! -f "$component_constraints" ] || constraints="$component_constraints"
        fi
        if [ ! -f "$constraints" ]; then
            echo "Missing tracked shared Python constraints; refusing unbounded install." >&2
            return 1
        fi
        if [ "$constraints" = "$NETCLAW_SHARED_CONSTRAINTS" ]; then
            set -- -c "$NETCLAW_SHARED_CONSTRAINTS" "$@"
        else
            set -- -c "$constraints" "$@"
        fi
    fi
    local out rc
    out="$("$py" -m pip install "$@" 2>&1)"; rc=$?
    if [ "$rc" -eq 0 ]; then
        printf '%s\n' "$out"
        if [ -n "${NETCLAW_INSTALL_COMPONENT:-}" ]; then
            mkdir -p "$NETCLAW_RUNTIME_ROOT/records" || return 1
            printf '%s\n' "$py" > "$NETCLAW_RUNTIME_ROOT/records/$NETCLAW_INSTALL_COMPONENT"
            PATH="$(dirname "$py"):$PATH"
            export PATH
        fi
        return 0
    fi

    if printf '%s' "$out" | grep -q 'externally-managed-environment'; then
        echo "netclaw_pip_install: $py is externally managed (PEP 668)." >&2
        echo "  Refusing to override system packages. Create a venv with netclaw_venv_create," >&2
        echo "  set NETCLAW_VENV to it, and configure the server to use that interpreter." >&2

    fi

    # FR-003c (spec 090): never swallow the reason. The whole point of a single install
    # path is that a failure is legible; discarding stderr defeats it.
    echo "netclaw_pip_install: FAILED installing: $*" >&2
    printf '%s\n' "$out" >&2
    return "$rc"
}

netclaw_pip_install() {
    local rc=0 output
    if [ -n "${NETCLAW_INSTALL_FAILURE_FILE:-}" ]; then
        output="$(mktemp "${NETCLAW_INSTALL_FAILURE_FILE}.output.XXXXXX")" || return 1
        _netclaw_pip_install "$@" > "$output" 2>&1 || rc=$?
        cat "$output"
        if [ "$rc" -ne 0 ]; then
            # Survive subshells, warning handlers and stderr suppression while
            # retaining the actual package/venv error for the final report.
            printf 'Python dependency installation failed (exit %s).\n' "$rc" >> "$NETCLAW_INSTALL_FAILURE_FILE"
            cat "$output" >> "$NETCLAW_INSTALL_FAILURE_FILE"
        fi
        rm -f "$output"
    else
        _netclaw_pip_install "$@" || rc=$?
    fi
    return "$rc"
}

# Create a virtualenv that works even where `ensurepip` is unavailable.
#
# Python 3.14 on Ubuntu has no ensurepip unless python3.14-venv is installed, and
# that needs root — so `python3 -m venv` fails outright with a message about
# apt-installing a package the operator may not be able to install. `virtualenv`
# bundles pip and needs no root, so it is tried first (spec 077 FR-004, FR-005;
# discovered in spec 076 research R12).
netclaw_venv_create() {
    local dest="$1"; shift || true
    local base="${NETCLAW_PY}"
    [ -x "$base" ] || base="$(command -v python3 2>/dev/null)"
    if [ -z "$base" ]; then
        echo "netclaw_venv_create: no base interpreter found" >&2; return 1
    fi
    _netclaw_require_python "$base" || return 1

    if command -v virtualenv >/dev/null 2>&1; then
        virtualenv -q -p "$base" "$dest" "$@" && return 0
        echo "netclaw_venv_create: virtualenv failed for $dest" >&2
    fi

    # Only try stdlib venv if ensurepip is actually present — otherwise it fails
    # with a confusing apt message rather than something actionable.
    if "$base" -c 'import ensurepip' >/dev/null 2>&1; then
        "$base" -m venv "$dest" && return 0
    fi

    if command -v uv >/dev/null 2>&1; then
        uv venv --seed --python "$base" "$dest" && return 0
    fi

    echo "netclaw_venv_create: cannot create a virtualenv at $dest" >&2
    echo "  $base has no ensurepip and 'virtualenv' is not installed." >&2
    echo "  Install uv or virtualenv, or your distribution's matching python3-venv package." >&2
    return 1
}
