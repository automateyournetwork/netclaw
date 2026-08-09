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
# Both are no-ops for behaviour on hosts where pip3 and python3 already agree.

# Interpreter that NetClaw's servers actually run under. Overridable for testing.
: "${NETCLAW_PY:=/usr/bin/python3}"

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
netclaw_pip_install() {
    local py
    if ! py="$(_netclaw_resolve_py)"; then
        echo "netclaw_pip_install: cannot determine a Python interpreter." >&2
        echo "  Set NETCLAW_PY to the interpreter your servers run under," >&2
        echo "  or NETCLAW_VENV to a virtualenv. Refusing to fall back to bare pip," >&2
        echo "  which on a split-toolchain host installs where nothing can import it." >&2
        return 1
    fi
    if ! "$py" -m pip --version >/dev/null 2>&1; then
        echo "netclaw_pip_install: $py has no usable pip module." >&2
        echo "  Remedy: $py -m ensurepip --upgrade   (or install the matching *-venv package)" >&2
        return 1
    fi
    # PEP 668: a distro-managed interpreter refuses installs outright with
    # "error: externally-managed-environment". Spec 090 found this helper had no handling
    # for it, so on Ubuntu 26.04 the one install path spec 077 mandates could not install
    # any new package at all -- which is why three registered servers were dead while the
    # installer reported success.
    #
    # Handled here, once, rather than at 56 call sites that each appended
    # `--break-system-packages` behind `2>/dev/null || log_warn`. That pattern turned a
    # total failure into a single warning line in a long log, and exit 0.
    local out rc
    out="$("$py" -m pip install "$@" 2>&1)"; rc=$?
    if [ "$rc" -eq 0 ]; then
        printf '%s\n' "$out"
        return 0
    fi

    if printf '%s' "$out" | grep -q 'externally-managed-environment'; then
        # Say so. A silent retry here would hide that packages are landing in a
        # distro-managed tree, which the operator may need to know when it breaks.
        echo "netclaw_pip_install: $py is externally managed (PEP 668)." >&2
        echo "  Retrying with --break-system-packages. To avoid this, set NETCLAW_VENV." >&2
        out="$("$py" -m pip install --break-system-packages "$@" 2>&1)"; rc=$?
        if [ "$rc" -eq 0 ]; then
            printf '%s\n' "$out"
            return 0
        fi
    fi

    # FR-003c (spec 090): never swallow the reason. The whole point of a single install
    # path is that a failure is legible; discarding stderr defeats it.
    echo "netclaw_pip_install: FAILED installing: $*" >&2
    printf '%s\n' "$out" >&2
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

    if command -v virtualenv >/dev/null 2>&1; then
        virtualenv -q -p "$base" "$dest" "$@" && return 0
        echo "netclaw_venv_create: virtualenv failed for $dest" >&2
    fi

    # Only try stdlib venv if ensurepip is actually present — otherwise it fails
    # with a confusing apt message rather than something actionable.
    if "$base" -c 'import ensurepip' >/dev/null 2>&1; then
        "$base" -m venv "$dest" && return 0
    fi

    echo "netclaw_venv_create: cannot create a virtualenv at $dest" >&2
    echo "  $base has no ensurepip and 'virtualenv' is not installed." >&2
    echo "  Remedy (no root needed):  $base -m pip install --user virtualenv" >&2
    echo "  Or with root:             apt install python3-venv" >&2
    return 1
}
