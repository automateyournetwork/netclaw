import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import r10_cleanup as c


class Cleanup(unittest.TestCase):
    def test_export_requires_bytes_and_confined_paths(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'evidence').write_bytes(b'exported')
            doc = {'files': {'evidence': hashlib.sha256(b'exported').hexdigest()}}
            (p / 'manifest.json').write_text(json.dumps(doc))
            c.exported(p / 'manifest.json')
            (p / 'evidence').write_bytes(b'changed')
            with self.assertRaises(ValueError): c.exported(p / 'manifest.json')
            doc['files'] = {'../elsewhere': '0' * 64}
            (p / 'manifest.json').write_text(json.dumps(doc))
            with self.assertRaises(ValueError): c.exported(p / 'manifest.json')

    def test_inventory_refuses_foreign_group_and_firewall(self):
        m = {'run_id': 'r10-fresh', 'azure_groups': ['rg-nc198-x'], 'az': 'az', 'subscription_id': 'sub'}
        with patch.object(c, 'command', return_value=[{'name': 'rg-nc198-x', 'tags': {'run-id': 'other'}}]):
            with self.assertRaisesRegex(ValueError, 'ownership'): c.inventory(m)
        m.update(azure_groups=[], gcp={'project': 'p', 'gcloud': 'gcloud', 'firewalls': ['nc198-x']})
        with patch.object(c, 'command', side_effect=[[], [], [], [{'name': 'nc198-x', 'description': 'other'}]]):
            with self.assertRaisesRegex(ValueError, 'ownership'): c.inventory(m)

    def test_replaced_resource_not_deleted(self):
        m = {'run_id': 'r', 'gcp': {'project': 'p', 'gcloud': 'gcloud'}}
        before = {'azure_groups': [], 'gcp': {'instances': [{'id': 'original', 'name': 'nc198-a'}], 'disks': [], 'addresses': [], 'firewall-rules': []}}
        with patch.object(c, 'command', side_effect=[[{'id': 'replacement', 'name': 'nc198-a'}], [], [], []]) as cmd:
            c.retire(m, before)
            self.assertTrue(all('delete' not in call.args[0] for call in cmd.call_args_list))


if __name__ == '__main__': unittest.main()
