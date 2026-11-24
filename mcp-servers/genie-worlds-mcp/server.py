#!/usr/bin/env python3
"""Canonical stdio entry point; all controls use the one Genie backend."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/genie-worlds/mcp_server.py'), run_name='__main__')
