#!/usr/bin/env python3
"""Wrapper to run GAIT MCP server in stdio mode (default is SSE).

The 25 skills that record to GAIT all invoke this as `python3 -u $GAIT_MCP_SCRIPT`,
so whichever interpreter `python3` resolves to must be able to import `gait`
(the `gait-ai` package). A distro Python upgrade moves `python3` to a new minor
version and strands the old site-packages, which breaks every one of those
skills with `ModuleNotFoundError: No module named 'gait'`.

To stay upgrade-proof, re-exec into the dedicated GAIT venv when `gait` is not
importable under the current interpreter. Create that venv with
`scripts/gait-venv-setup.sh`. Set GAIT_VENV to override its location.
"""
import os
import sys

DEFAULT_VENV = os.path.expanduser(
    os.environ.get("GAIT_VENV", "~/.openclaw/gait-venv"))


def _reexec_into_venv() -> None:
    """Re-exec under the GAIT venv interpreter. Returns only if that is
    impossible, leaving the caller to fail with the original ImportError."""
    if os.environ.get("_GAIT_STDIO_REEXEC"):
        return  # already re-execed once; do not loop
    # Compare paths literally, not with samefile(): a venv's bin/python is a
    # symlink to the same real interpreter binary, so samefile() would report a
    # match and skip the re-exec. It is the *path* we invoke that sets
    # sys.prefix and therefore which site-packages get imported.
    venv_python = os.path.join(DEFAULT_VENV, "bin", "python")
    if not os.path.exists(venv_python) or venv_python == sys.executable:
        return
    os.environ["_GAIT_STDIO_REEXEC"] = "1"
    os.execv(venv_python, [venv_python, os.path.abspath(__file__), *sys.argv[1:]])


try:
    import gait  # noqa: F401
except ImportError:
    _reexec_into_venv()
    raise SystemExit(
        f"GAIT unavailable: cannot import 'gait' under {sys.executable} and no "
        f"usable venv at {DEFAULT_VENV}. Run scripts/gait-venv-setup.sh."
    )

import asyncio  # noqa: E402

# Add the gait_mcp directory to path
gait_dir = os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "gait_mcp")
sys.path.insert(0, gait_dir)

# Import the FastMCP instance from the GAIT server
from gait_mcp import mcp  # noqa: E402

if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
