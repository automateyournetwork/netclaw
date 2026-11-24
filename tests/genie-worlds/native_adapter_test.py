"""Synthetic composition tests; real SSH and installed capability remain gated."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

import native_session_test

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_adapter', ROOT/'scripts/genie-worlds/native_adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
spec = importlib.util.spec_from_file_location('adapter_collector', ROOT/'scripts/genie-worlds/collector.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class NativeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_session_test.NativeSessionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.document = {'synthetic': 'frozen'}
        self.prepare = self.enterContext(patch.object(adapter.connection, 'prepare_device',
            side_effect=lambda *args, **kw:self.f.events.append(('prepare', args[0])) or self.f.prepared))
        self.parse = self.enterContext(patch.object(adapter.session.read, 'parse_captured',
            side_effect=lambda *args, **kw:self.f.events.append(('parse',None)) or {'synthetic':True}))
        self.binding = adapter.FrozenCapture(self.document,'fixture',
            document_sha256=adapter.connection.digest(self.document),endpoint_sha256='0'*64,
            server=self.f.server,source_sha256=self.f.digest)

    def capture(self, device='fixture', command='show interfaces'):
        return self.binding.capture_context(device,command,timeout=3,evidence_directory=self.f.root)

    def parse_raw(self, **kw):
        return self.binding.parse_captured(kw.get('device','fixture'),kw.get('command','show interfaces'),
                                          output=kw.get('output','synthetic raw'))

    def test_frozen_copy_and_preserve_cleanup_parse_order(self):
        self.document['synthetic']='mutated after construction'
        with self.capture() as raw:
            self.assertEqual(raw,'synthetic raw')
            with self.assertRaisesRegex(adapter.AdapterRefused,'clean_capture_required'):self.parse_raw()
            (self.f.root/'raw').write_text(raw)
            self.f.events.append(('persist',None))
        self.assertEqual(self.parse_raw(),{'synthetic':True})
        self.assertEqual([e[0] for e in self.f.events],
                         ['prepare','connect','execute','persist','disconnect','parse'])
        self.assertEqual(self.prepare.call_args.args[0],{'synthetic':'frozen'})

    def test_device_refusal_before_preparation(self):
        with self.assertRaises(ValueError):
            with self.capture('other'):self.fail('unexpected capture')
        self.prepare.assert_not_called()
        self.assertEqual(self.f.events,[])
        with self.assertRaisesRegex(adapter.AdapterRefused,'attempt_already_started'):
            with self.capture():self.fail('retry admitted')

    def test_policy_refusal_before_preparation(self):
        with self.assertRaises(ValueError):
            with self.capture(command='show running-config'):self.fail('unexpected capture')
        self.prepare.assert_not_called()

    def test_cleanup_failure_preserves_raw_but_forbids_parse_and_retry(self):
        def fail():raise RuntimeError('synthetic cleanup')
        self.f.device.disconnect=fail
        with self.assertRaisesRegex(adapter.session.SessionRefused,'native_disconnect_failed'):
            with self.capture() as raw:(self.f.root/'raw').write_text(raw)
        self.assertEqual((self.f.root/'raw').read_text(),'synthetic raw')
        with self.assertRaises(adapter.AdapterRefused):self.parse_raw()
        self.parse.assert_not_called()
        with self.assertRaisesRegex(adapter.AdapterRefused,'attempt_already_started'):
            with self.capture():self.fail('retry admitted')

    def test_preservation_failure_forbids_parse(self):
        with self.assertRaises(OSError):
            with self.capture():raise OSError('synthetic sink')
        with self.assertRaises(adapter.AdapterRefused):self.parse_raw()
        self.assertEqual(self.f.events[-1][0],'disconnect')

    def test_parser_requires_exact_device_command_and_bytes(self):
        with self.capture():pass
        for args in [{'device':'other'},{'command':'show version'},{'output':'changed'},{'output':None}]:
            with self.assertRaises(adapter.AdapterRefused):self.parse_raw(**args)
        self.parse.assert_not_called()

    def test_source_change_refuses_before_preparation(self):
        (self.f.root/'policy.py').write_text('def validate_show_command(command):\n    return False\n')
        with self.assertRaisesRegex(adapter.session.read.ReadRefused,'native_read_policy_changed'):
            with self.capture():self.fail('changed source admitted')
        self.prepare.assert_not_called()

    def test_module_does_not_advertise_qualification(self):
        self.assertFalse(getattr(adapter,'qualified_read_only_capture',False))
        self.assertFalse(getattr(self.binding,'qualified_read_only_capture',False))

    def test_actual_child_preserves_raw_before_disconnect_and_marks_before_parse(self):
        directory=self.f.root
        budget=directory/'budget';budget.write_text('1024')
        request=directory/'request'
        request.write_text(json.dumps({'adapter':'synthetic-only','device':'fixture',
            'command':'show interfaces','timeout':3,'budget':str(budget)}))
        def disconnect():
            self.assertEqual((directory/'raw').read_text(),'synthetic raw')
            self.assertFalse((directory/'lifecycle-finished').exists())
        self.f.device.disconnect=disconnect
        def parse(*args,**kw):
            self.assertTrue((directory/'lifecycle-finished').exists())
            return {'synthetic':True}
        self.parse.side_effect=parse
        # Substitute only module loading; exercise the actual child and binding.
        shim=SimpleNamespace(qualified_read_only_capture=True,
            capture_context=self.binding.capture_context,parse_captured=self.binding.parse_captured)
        fake_spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
        with patch.object(collector.importlib.util,'spec_from_file_location',return_value=fake_spec), \
                patch.object(collector.importlib.util,'module_from_spec',return_value=shim):
            collector._child(request)
        self.assertEqual(json.loads((directory/'result').read_text())['outcome'],'observed')
        self.assertEqual((directory/'raw').stat().st_mode & 0o777,0o600)


if __name__=='__main__':unittest.main()
