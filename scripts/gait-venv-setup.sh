#!/usr/bin/env bash
# gait-venv-setup.sh - Create the dedicated GAIT virtualenv
#
# Usage: ./scripts/gait-venv-setup.sh
#
# The 25 skills that record to the GAIT audit trail invoke the server as
# `python3 -u $GAIT_MCP_SCRIPT`. When a distro upgrade moves `python3` to a new
# minor version, the previously installed `gait-ai` is stranded in the old
# site-packages and every one of those skills fails with
# `ModuleNotFoundError: No module named 'gait'`.
#
# This script pins GAIT's dependencies into a venv that survives interpreter
# upgrades. scripts/gait-stdio.py re-execs into it automatically when `gait` is
# not importable, so no skill needs to change.
#
# Re-run this after a Python upgrade.

set -euo pipefail

GAIT_VENV="${GAIT_VENV:-${HOME}/.openclaw/gait-venv}"

echo "=== GAIT venv setup ==="
echo ""

if ! command -v uv &> /dev/null; then
    echo "ERROR: uv not found. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "(uv is required because Debian/Ubuntu ship python3 without ensurepip,"
    echo " so 'python3 -m venv' cannot bootstrap pip on this host.)"
    exit 1
fi

# Prefer the system interpreter so the venv tracks the OS Python, not a
# uv-managed prerelease.
PYTHON_BIN="$(command -v python3)"
echo "Base interpreter: ${PYTHON_BIN} ($("${PYTHON_BIN}" -V 2>&1))"
echo "Target venv     : ${GAIT_VENV}"
echo ""

if [ -d "${GAIT_VENV}" ]; then
    echo "Removing existing venv..."
    rm -rf "${GAIT_VENV}"
fi

uv venv "${GAIT_VENV}" --python "${PYTHON_BIN}"

# Dependencies mirror mcp-servers/gait_mcp/pyproject.toml
# Bounds are LOAD-BEARING. mcp 2.0.0 removed mcp.server.fastmcp, and gait_mcp
# imports it (with a fallback to the standalone fastmcp, so either works — but
# only if both are constrained to a major that still provides the API).
#
# This install was previously FULLY UNBOUNDED and sits OUTSIDE any
# requirements.txt, so the spec-077 audit of requirements files missed it
# entirely; it was found only by grepping for venv creation. GAIT is the audit
# trail Constitution Principle IV makes non-negotiable, so it failing on a fresh
# install is not cosmetic.
VIRTUAL_ENV="${GAIT_VENV}" uv pip install gait-ai 'mcp>=1.0.0,<2' 'fastmcp>=2.0.0,<3'

echo ""
echo "Verifying..."
"${GAIT_VENV}/bin/python" -c "import gait, mcp, fastmcp; print('  gait   :', gait.__file__)"

# The venv only covers callers that go through scripts/gait-stdio.py. Some
# long-running servers import gait *directly* in-process and cannot re-exec:
#   mcp-servers/memory-mcp/memory_mcp_server.py  (gait_log)
#   mcp-servers/rag-mcp/rag_mcp_server.py        (gait_log)
# Both wrap the import in `except Exception: pass`, so a missing gait makes
# their audit logging a silent no-op rather than an error. Ensure the default
# interpreter can import it too.
echo ""
if "${PYTHON_BIN}" -c "import gait" 2>/dev/null; then
    echo "Direct importers: ${PYTHON_BIN} can already import gait."
else
    echo "Installing gait-ai for ${PYTHON_BIN} (direct in-process importers)..."
    "${PYTHON_BIN}" -m pip install --user --break-system-packages -q gait-ai \
        || echo "  WARNING: could not install gait-ai for ${PYTHON_BIN};" \
                "memory-mcp and rag-mcp audit logging will silently no-op."
    "${PYTHON_BIN}" -c "import gait; print('  ok:', gait.__file__)" 2>/dev/null || true
fi

echo ""
echo "GAIT venv ready. scripts/gait-stdio.py will re-exec into it as needed."
