import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_read', ROOT / 'scripts/genie-worlds/native_read.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeReadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.spec200-local/tests')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'selected_policy.py'
        self.path.write_text('def validate_show_command(command):\n    return None\n')
        spec = importlib.util.spec_from_file_location('selected_policy', self.path)
        self.server = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.server)
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.calls = []
        self.device = SimpleNamespace(os='iosxe', mit=True, operating_mode=True,
            learn_os=False, learn_tokens=False, learn_hostname=False, reconnect=False,
            settings=SimpleNamespace(LEARN_DEVICE_TOKENS=False),
            state_machine=SimpleNamespace(current_state='enable'), is_connected=lambda: True,
            execute=lambda command, **kw: self.calls.append((command, kw)) or 'synthetic raw')

    def capture(self, command='show interfaces', **kw):
        return native.capture_once(self.server, self.device, command, timeout=kw.get('timeout', 3),
                                   source_sha256=kw.get('digest', self.digest))

    def test_every_frozen_read_executes_exactly_once_without_live_parse(self):
        self.device.parse = lambda *a, **kw: self.fail('live parser was used')
        for command in native.COMMANDS:
            self.assertEqual(self.capture(command), 'synthetic raw')
        self.assertEqual(len(self.calls), 5)
        self.assertTrue(all(kw == {'timeout': 3} for _, kw in self.calls))

    def test_policy_and_allowlist_refuse_before_io(self):
        for command in ['show interfaces | include x', 'show interfaces\n', 'show running-config', 'reload']:
            with self.assertRaisesRegex(native.ReadRefused, 'unqualified_command'): self.capture(command)
        with self.assertRaisesRegex(native.ReadRefused, 'native_read_policy_changed'): self.capture(digest='0'*64)
        self.assertEqual(self.calls, [])

    def test_native_denial_and_exception_are_final_and_sanitized(self):
        for body in ["return 'private native denial'", 'return False', "raise RuntimeError('private error')"]:
            self.path.write_text('def validate_show_command(command):\n    '+body+'\n')
            exec(compile(self.path.read_text(), str(self.path), 'exec'), self.server.__dict__)
            self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(native.ReadRefused, '^native_read_policy_(refused|failed)$'): self.capture()
        self.assertEqual(self.calls, [])

    def test_changed_validator_function_is_not_the_selected_policy(self):
        self.server.validate_show_command = lambda command: None
        with self.assertRaisesRegex(native.ReadRefused, 'native_read_policy_changed'): self.capture()
        self.assertEqual(self.calls, [])

    def test_connection_state_and_timeout_refuse_without_execute(self):
        for timeout in [True, 0, -1, 31, float('nan'), float('inf')]:
            with self.assertRaisesRegex(native.ReadRefused, 'read_timeout'): self.capture(timeout=timeout)
        for field in ['mit','operating_mode','learn_os','learn_tokens','learn_hostname','reconnect']:
            old = getattr(self.device,field); setattr(self.device,field,not old)
            with self.assertRaisesRegex(native.ReadRefused, 'connection_policy_not_applied'): self.capture()
            setattr(self.device,field,old)
        self.device.state_machine.current_state='disable'
        with self.assertRaisesRegex(native.ReadRefused, 'connection_policy_not_applied'): self.capture()
        self.assertEqual(self.calls, [])

    def test_execute_failure_never_retries_or_parses(self):
        def fail(*a, **kw):
            self.calls.append(1); raise TimeoutError('synthetic timeout')
        self.device.execute=fail
        with self.assertRaises(TimeoutError): self.capture()
        self.assertEqual(self.calls,[1])

    def test_offline_parser_cannot_fall_back_to_device_io_even_for_empty_output(self):
        class Parser:
            def __init__(self,device): self.device=device
            def parse(self,*,output): return self.device.execute('show interfaces')
        with patch.object(native.importlib,'import_module',return_value=SimpleNamespace(ShowInterfaces=Parser)):
            for output in ['', 'synthetic raw']:
                with self.assertRaisesRegex(native.ReadRefused,'offline_parser_execution_refused'):
                    native.parse_captured('show interfaces',output=output)
        self.assertEqual(self.calls,[])

    def test_offline_output_is_exact(self):
        class Parser:
            def __init__(self,device): self.device=device
            def parse(self,*,output): return {'exact':output}
        with patch.object(native.importlib,'import_module',return_value=SimpleNamespace(ShowInterfaces=Parser)):
            self.assertEqual(native.parse_captured('show interfaces',output=' raw\n'),{'exact':' raw\n'})


if __name__ == '__main__': unittest.main()
