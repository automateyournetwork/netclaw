"""Synthetic lifecycle checks; no native transport or device operation."""
import hashlib
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_session', ROOT/'scripts/genie-worlds/native_session.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'.spec200-local/tests')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.root.chmod(0o700)
        policy = self.root/'policy.py'; policy.write_text('def validate_show_command(command):\n    return None\n')
        spec = importlib.util.spec_from_file_location('synthetic_policy', policy)
        self.server = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.server)
        self.digest = hashlib.sha256(policy.read_bytes()).hexdigest()
        self.events = []
        self.device = SimpleNamespace(os='iosxe', mit=True, operating_mode=True,
            learn_os=False, learn_tokens=False, learn_hostname=False, reconnect=False,
            settings=SimpleNamespace(LEARN_DEVICE_TOKENS=False),
            state_machine=SimpleNamespace(current_state='enable'), is_connected=lambda:True,
            connect=lambda **kw:self.events.append(('connect',kw)),
            execute=lambda command,**kw:self.events.append(('execute',command)) or 'synthetic raw',
            disconnect=lambda:self.events.append(('disconnect',None)))
        self.prepared = SimpleNamespace(device=self.device, connection_options=lambda timeout:{
            'log_stdout':False,'connection_timeout':timeout,'init_exec_commands':[],
            'init_config_commands':[], 'reconnect':False})

    def capture(self, **kw):
        return native.connected_capture(self.prepared,self.server,kw.get('command','show interfaces'),
            timeout=3,source_sha256=kw.get('digest',self.digest),logfile=kw.get('logfile',self.root/'connection.log'))

    def test_raw_is_available_for_preservation_before_cleanup(self):
        with self.capture() as raw:
            self.assertEqual(raw,'synthetic raw')
            self.events.append(('persist',None))
            log=self.root/'connection.log'
            self.assertEqual(log.stat().st_mode & 0o777,0o600)
        self.assertEqual([e[0] for e in self.events],['connect','execute','persist','disconnect'])
        options=self.events[0][1]
        self.assertFalse(options['log_stdout']); self.assertFalse(options['reconnect'])
        self.assertEqual(options['init_exec_commands'],[])

    def test_policy_refusal_has_no_connection_or_log_effect(self):
        for options in [{'command':'show running-config'},{'digest':'0'*64}]:
            with self.assertRaises(native.read.ReadRefused):
                with self.capture(**options): self.fail('capture admitted')
        self.assertEqual(self.events,[])
        self.assertFalse((self.root/'connection.log').exists())

    def test_existing_symlink_public_directory_and_hardlink_are_refused(self):
        target=self.root/'target';target.write_text('retained'); target.chmod(0o600)
        for kind in ['existing','symlink','hardlink','public']:
            log=self.root/kind
            if kind=='existing':log.write_text('retained')
            if kind=='symlink':log.symlink_to(target)
            if kind=='hardlink':os.link(target,log)
            if kind=='public':self.root.chmod(0o755)
            with self.assertRaises(native.SessionRefused):
                with self.capture(logfile=log): self.fail('unsafe log admitted')
            self.root.chmod(0o700)
        self.assertEqual(self.events,[]); self.assertEqual(target.read_text(),'retained')

    def test_connect_failure_still_disconnects_once_without_capture(self):
        def fail(**kw):self.events.append(('connect',None));raise RuntimeError('private detail')
        self.device.connect=fail
        with self.assertRaisesRegex(native.SessionRefused,'^native_capture_failed$'):
            with self.capture():self.fail('failed connect yielded')
        self.assertEqual([e[0] for e in self.events],['connect','disconnect'])

    def test_execute_failure_never_retries_and_disconnects(self):
        def fail(*a,**kw):self.events.append(('execute',None));raise TimeoutError('private detail')
        self.device.execute=fail
        with self.assertRaisesRegex(native.SessionRefused,'^native_capture_failed$'):
            with self.capture():self.fail('failed execute yielded')
        self.assertEqual([e[0] for e in self.events],['connect','execute','disconnect'])

    def test_preservation_failure_is_not_masked_by_disconnect_failure(self):
        def fail():self.events.append(('disconnect',None));raise RuntimeError('private cleanup')
        self.device.disconnect=fail
        with self.assertRaisesRegex(OSError,'synthetic preservation failure') as caught:
            with self.capture():raise OSError('synthetic preservation failure')
        self.assertEqual(caught.exception.__notes__,['native_disconnect_failed'])
        self.assertEqual([e[0] for e in self.events],['connect','execute','disconnect'])

    def test_cleanup_failure_cannot_report_success_after_raw_preserved(self):
        def fail():self.events.append(('disconnect',None));raise RuntimeError('private cleanup')
        self.device.disconnect=fail
        retained=[]
        with self.assertRaisesRegex(native.SessionRefused,'^native_disconnect_failed$'):
            with self.capture() as raw:retained.append(raw)
        self.assertEqual(retained,['synthetic raw'])
        self.assertEqual(len(self.events),3)

    def test_connection_posture_failure_prevents_execute(self):
        self.device.reconnect=True
        with self.assertRaisesRegex(native.read.ReadRefused,'connection_policy_not_applied'):
            with self.capture():self.fail('unsafe posture yielded')
        self.assertEqual([e[0] for e in self.events],['connect','disconnect'])


if __name__=='__main__':unittest.main()
