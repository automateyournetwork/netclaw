import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_connection', ROOT / 'scripts/genie-worlds/native_connection.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.spec200-local/tests')
        self.addCleanup(self.temp.cleanup)
        self.pin = Path(self.temp.name) / 'known_hosts'
        self.pin.write_text('synthetic trust fixture\n'); self.pin.chmod(0o600)
        self.document = {'testbed': {'name': 'synthetic', 'credentials': native.CREDENTIALS},
            'devices': {'router': {'os': 'iosxe', 'platform': 'iol', 'type': 'router',
                'connections': {'defaults': {'class': 'unicon.Unicon'}, 'cli': {
                    'protocol': 'ssh', 'ip': '192.0.2.1', 'port': 22,
                    'ssh_options': native.SSH_PREFIX + str(self.pin)}}}}}
        self.digest = native.digest(self.document)
        self.endpoint = native.policy.endpoint_identity('router', SimpleNamespace(os='iosxe', connections=self.document['devices']['router']['connections']))
        self.endpoint_digest = native.digest(self.endpoint)
        self.calls = []
        self.device = SimpleNamespace(os='iosxe', platform='iol', connections=copy.deepcopy(self.document['devices']['router']['connections']),
            is_connected=lambda:False, connect=lambda **kw:self.calls.append(('connect',kw)),
            disconnect=lambda:self.calls.append(('disconnect',None)))
        self.loader = lambda doc: self.calls.append(('load',doc)) or SimpleNamespace(devices={'router':self.device})
        self.patcher = patch.object(native.policy,'validate_native_policy',side_effect=lambda *a:self.calls.append(('policy',None)))
        self.patcher.start(); self.addCleanup(self.patcher.stop)

    def prepare(self, **kw):
        return native.prepare_device(self.document, 'router', document_sha256=self.digest,
            endpoint_sha256=kw.get('endpoint_sha256', self.endpoint_digest), loader=self.loader)

    def test_preparation_checks_policy_before_loader_and_never_connects(self):
        original=copy.deepcopy(self.document)
        prepared=self.prepare()
        self.assertIs(prepared.device,self.device)
        self.assertEqual([x[0] for x in self.calls],['policy','load'])
        self.assertEqual(self.document,original)
        self.assertEqual(prepared.connection_options(5), {**native.policy.connection_policy(),
            'via':'cli','log_stdout':False,'connection_timeout':5})

    def test_document_changes_and_hooks_are_refused_before_load(self):
        self.document['devices']['router']['custom']={'danger':'hook'}
        with self.assertRaises(native.ConnectionRefused):self.prepare()
        self.digest=native.digest(self.document)
        with self.assertRaises(native.ConnectionRefused):self.prepare()
        self.assertEqual(self.calls,[])

    def test_missing_strict_pin_or_changed_pin_refused_before_load(self):
        self.pin.write_text('changed trust\n')
        with self.assertRaises(native.ConnectionRefused):self.prepare()
        self.assertEqual(self.calls,[])
        self.pin.chmod(0o644)
        with self.assertRaises(native.ConnectionRefused):self.prepare()
        self.assertEqual(self.calls,[])

    def test_unqualified_native_plugin_refused_before_loader(self):
        with patch.object(native.policy,'validate_native_policy',side_effect=ValueError('private plugin detail')):
            with self.assertRaisesRegex(native.ConnectionRefused,'^native_connection_policy_refused$'):self.prepare()
        self.assertEqual(self.calls,[])

    def test_loaded_endpoint_change_and_existing_connection_refused(self):
        self.device.connections['cli']['ip']='192.0.2.2'
        with self.assertRaisesRegex(native.ConnectionRefused,'resolved_endpoint_changed'):self.prepare()
        self.device.connections=copy.deepcopy(self.document['devices']['router']['connections'])
        self.device.is_connected=lambda:True
        with self.assertRaisesRegex(native.ConnectionRefused,'fresh_connection_required'):self.prepare()
        self.assertNotIn('connect',[x[0] for x in self.calls])

    def test_loader_mutation_cannot_change_frozen_input(self):
        def mutate(doc):
            doc['devices']['router']['connections']['cli']['ip']='192.0.2.2'
            return SimpleNamespace(devices={'router':self.device})
        self.loader=mutate
        self.prepare()
        self.assertEqual(self.document['devices']['router']['connections']['cli']['ip'],'192.0.2.1')

    def test_scoped_credentials_and_no_connection_credentials(self):
        self.document['testbed']['credentials']={'default':{'username':'private','password':'private'}}
        self.digest=native.digest(self.document)
        with self.assertRaisesRegex(native.ConnectionRefused,'scoped_credential_references_required'):self.prepare()
        self.assertEqual(self.calls,[])

    def test_loader_markup_shell_paths_and_resolved_platform_are_refused(self):
        for field in ['name','type']:
            document=copy.deepcopy(self.document)
            target=self.document['testbed'] if field=='name' else self.document['devices']['router']
            target[field]='%CALLABLE{untrusted.module.function}'
            self.digest=native.digest(self.document)
            with self.assertRaises(native.ConnectionRefused):self.prepare()
            self.document=document
        self.document['devices']['router']['connections']['cli']['ssh_options'] += ';echo'
        self.digest=native.digest(self.document)
        with self.assertRaises(native.ConnectionRefused):self.prepare()
        self.assertEqual(self.calls,[])
        self.document['devices']['router']['connections']['cli']['ssh_options']=native.SSH_PREFIX+str(self.pin)
        self.digest=native.digest(self.document)
        self.device.platform='other'
        with self.assertRaisesRegex(native.ConnectionRefused,'resolved_platform_changed'):self.prepare()

    def test_only_inherited_loaded_credentials_are_accepted(self):
        self.device.connections['cli']['credentials']={'unexpected':'value'}
        with self.assertRaisesRegex(native.ConnectionRefused,'resolved_credentials_changed'):self.prepare()
        self.assertNotIn('connect',[x[0] for x in self.calls])

    def test_prepared_options_recheck_trust_and_endpoint_and_timeout(self):
        prepared=self.prepare()
        for timeout in [True,0,31,float('nan')]:
            with self.assertRaises(native.ConnectionRefused):prepared.connection_options(timeout)
        self.pin.write_text('changed after prepare\n')
        with self.assertRaisesRegex(native.ConnectionRefused,'resolved_endpoint_changed'):prepared.connection_options(5)
        self.assertNotIn('connect',[x[0] for x in self.calls])


if __name__=='__main__':unittest.main()
