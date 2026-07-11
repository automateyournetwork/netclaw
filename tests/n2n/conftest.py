"""Shared fixtures for N2N federation tests (feature 052)."""

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
