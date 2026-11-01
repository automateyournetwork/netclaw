"""Controlling-PTY tests with synthetic accounts/files; no real upload approval."""
import errno
import fcntl
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import termios
import time
import unittest
import test_core

ROOT=Path(__file__).resolve().parents[2]
class NativeTerminalTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_core.CoreTest();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.env=self.fixture.root/'.env'
        c=self.fixture.config
        self.env.write_text('\n'.join(f'{k}="{v}"' for k,v in {
            'NETCLAW_PASSWORD':'NEIGHBOR_CANARY','NETCONVERTER_MODE':c.mode,'NETCONVERTER_INSTALLATION_ID':c.installation,
            'NETCONVERTER_DATA_DIR':c.state_dir,'NETCONVERTER_WORKSPACE':c.workspace,'NETCONVERTER_EXECUTABLE':c.executable,
            'NETCONVERTER_API_KEY':c.key,'NETCONVERTER_ACCOUNT_REF':c.account}.items())+'\n');self.env.chmod(0o600)
    def terminal(self,args,steps,exit_code=0):
        master,slave=pty.openpty()
        def controlling():os.setsid();fcntl.ioctl(slave,termios.TIOCSCTTY,0)
        process=subprocess.Popen([sys.executable,*args],stdin=slave,stdout=slave,stderr=slave,cwd=ROOT,preexec_fn=controlling,
            env={'PATH':os.defpath,'HOME':str(self.fixture.root)})
        os.close(slave);pending=b'';transcript=b'';index=0;deadline=time.monotonic()+20
        try:
            while process.poll() is None:
                self.assertLess(time.monotonic(),deadline,'Synthetic PTY timed out')
                if not select.select([master],[],[],.05)[0]:continue
                try:chunk=os.read(master,65536)
                except OSError as e:
                    if e.errno==errno.EIO:break
                    raise
                pending+=chunk;transcript+=chunk
                if index<len(steps) and steps[index][0].encode() in pending:
                    os.write(master,(steps[index][1]+'\n').encode());index+=1;pending=b''
            process.wait(timeout=5);self.assertEqual(process.returncode,exit_code);self.assertEqual(index,len(steps))
            return transcript.decode(errors='replace')
        finally:
            os.close(master)
            if process.poll() is None:process.kill();process.wait()
    def test_actual_mode_picker_cancel_and_save_preserve_neighbor(self):
        args=['scripts/configure-netconverter.py','--env',str(self.env),'--home',str(self.fixture.root),'--interactive']
        before=self.env.read_bytes();self.terminal(args,[('[cancel]:','cancel')]);self.assertEqual(self.env.read_bytes(),before)
        for mode in ('hosted-readonly','local-terminal'):
            steps=[('[cancel]:',mode),('reference (not a credential):','synthetic account')]
            if mode=='local-terminal':steps += [('workspace:',str(self.fixture.workspace)),('executable:',str(self.fixture.exe))]
            steps += [('key now?','n'),('selected runtime?','y')]
            transcript=self.terminal(args,steps)
            self.assertNotIn('NEIGHBOR_CANARY',transcript);self.assertIn('NEIGHBOR_CANARY',self.env.read_text())
            self.assertIn(f'NETCONVERTER_MODE={mode}',self.env.read_text())
            self.assertEqual(self.env.stat().st_mode&0o777,0o600)
    def test_actual_native_review_decline_and_synthetic_grant(self):
        request=self.fixture.prepare()
        args=['scripts/netconverter-settings.py','--env-file',str(self.env),'approve-submission',request['request_id'],'--digest',request['review_digest']]
        transcript=self.terminal(args,[('type the full review digest:','decline')],2)
        self.assertEqual(self.fixture.ledger.status(request['request_id'])['state'],'prepared')
        transcript+=self.terminal(args,[('type the full review digest:',request['review_digest'])])
        self.assertEqual(self.fixture.ledger.status(request['request_id'])['state'],'approved')
        self.assertNotIn('PRIVATE_CONFIG_CANARY',transcript);self.assertNotIn('synthetic-key',transcript)
        self.assertFalse((self.fixture.workspace/'attempts.jsonl').exists())

if __name__=='__main__':unittest.main()
