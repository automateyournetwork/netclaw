#!/usr/bin/env python3
"""Launch the mesh daemon with literal, selected dotenv settings."""
import importlib.util
import os
from pathlib import Path
import sys


def environment(path):
    spec = importlib.util.spec_from_file_location('env_writer', Path(__file__).with_name('write-env.py'))
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    values = writer.values(Path(path).read_text())
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp-servers/protocol-mcp'))
    from bgp.federation.runtime import selected
    return selected().environment({**os.environ, **{key: value for key, value in values.items()
            if key.startswith(('NETCLAW_', 'N2N_', 'BGP_'))}})


if __name__ == '__main__':
    try:
        env = environment(sys.argv[1])
    except (OSError, ValueError, IndexError):
        sys.exit('Cannot read mesh environment; daemon was not started.')
    os.execve(sys.executable, [sys.executable, sys.argv[2]], env)
