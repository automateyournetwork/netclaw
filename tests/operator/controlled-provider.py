"""Reuse the repository's deterministic loopback provider; stdin closes it."""
import importlib.util
import json
from pathlib import Path
import sys

source = Path(__file__).resolve().parents[1] / 'hermes-hud/fixtures/provider.py'
spec = importlib.util.spec_from_file_location('provider150', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
provider = module.Provider()
try:
    print(json.dumps({'url': provider.start()}), flush=True)
    for line in sys.stdin:
        if line.strip() == 'count':
            print(json.dumps({'requests': len(provider.calls)}), flush=True)
        else:
            break
finally:
    provider.close()
