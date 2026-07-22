"""Shared fixtures for N2N federation tests (feature 052)."""

import asyncio
import os
import sys
import tempfile

import pytest

# Make the protocol-mcp package importable
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))


@pytest.fixture
def fed_base(tmp_path):
    """A fresh ~/.openclaw/n2n-style base dir."""
    return str(tmp_path / "n2n")


@pytest.fixture
def manager(fed_base):
    from bgp.federation.manager import FederationManager
    m = FederationManager(base_dir=fed_base)
    yield m
    m.close()


async def _await_terminal(svc, task_id, tries=200, interval=0.01):
    """Poll a TaskManager job (feature 053/065) until it reaches a terminal
    state. Must be awaited from within an already-running event loop —
    `ReplicationManager.start()`/`.resync()` call `asyncio.create_task()`
    internally, so callers need a loop active before triggering the job too
    (wrap the whole test body in one `asyncio.run(main())`, not per-call)."""
    for _ in range(tries):
        st = svc.tasks.status(task_id)
        if st["state"] in ("completed", "failed", "cancelled"):
            return st
        await asyncio.sleep(interval)
    return svc.tasks.status(task_id)
