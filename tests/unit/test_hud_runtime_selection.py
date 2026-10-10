import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class SelectionTests(unittest.TestCase):
    def test_golden_python_and_node_agree(self):
        spec = importlib.util.spec_from_file_location('selection', ROOT / 'scripts/runtime-selection.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for case in json.loads((ROOT / 'tests/hermes-hud/fixtures/selection.json').read_text()):
            with self.subTest(case=case['name']):
                try:
                    py = module.resolve_values(case['env'], '/owner', case['descriptor'])
                except ValueError:
                    py = {'error': True}
                proc = subprocess.run(['node', str(ROOT / 'scripts/runtime-selection.mjs'), '--fixture'],
                    input=json.dumps(case), text=True, capture_output=True, check=True)
                js = json.loads(proc.stdout)
                self.assertEqual(py, js)
                self.assertEqual(py, {'error': True} if case.get('error') else case['expected'])

    def test_invalid_descriptor_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / '.config/netclaw'
            directory.mkdir(parents=True, mode=0o700)
            file = directory / 'runtime.json'; file.write_text('{bad'); file.chmod(0o600)
            proc = subprocess.run(['node', str(ROOT / 'scripts/runtime-selection.mjs')],
                env={**os.environ, 'HOME': tmp, 'XDG_CONFIG_HOME': str(Path(tmp)/'.config')}, capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn(b'Bearer', proc.stderr)

if __name__ == '__main__': unittest.main()
