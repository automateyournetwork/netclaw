import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import socket
ROOT=Path(__file__).resolve().parents[2]
class LaunchTests(unittest.TestCase):
    def test_selection_survives_clean_shell_and_status_does_not_create_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner=Path(tmp);home=owner/'Hermes Home';home.mkdir();(home/'config.yaml').write_text('{}')
            env={'PATH':os.environ['PATH'],'HOME':tmp,'NETCLAW_RUNTIME':'hermes','HERMES_HOME':str(home)}
            command=['node',str(ROOT/'scripts/hud-launch.mjs')]
            result=subprocess.run(command+['status'],env=env,cwd='/tmp',capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertFalse((home/'netclaw-hud').exists())
            result=subprocess.run(command+['select','hermes',str(home)],env=env,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run(command+['status'],env={'PATH':env['PATH'],'HOME':tmp},cwd='/tmp',capture_output=True,text=True)
            self.assertEqual(json.loads(result.stdout)['home'],str(home.resolve()));self.assertFalse((owner/'.openclaw').exists())
    def test_invalid_descriptor_fails_without_creating_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'.config/netclaw/runtime.json';file.parent.mkdir(parents=True);file.write_text('bad');file.chmod(0o600)
            result=subprocess.run(['node',str(ROOT/'scripts/hud-launch.mjs'),'status'],env={'PATH':os.environ['PATH'],'HOME':tmp},capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse((Path(tmp)/'.openclaw').exists())
    def test_occupied_ports_refuse_before_any_child_or_credential_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'Hermes Home';home.mkdir();(home/'config.yaml').write_text('{}')
            sockets=[socket.socket() for _ in range(3)]
            try:
                for sock in sockets:sock.bind(('127.0.0.1',0))
                ports=[sock.getsockname()[1] for sock in sockets]
                for sock in sockets:sock.close()
                env={'PATH':os.environ['PATH'],'HOME':tmp,'NETCLAW_RUNTIME':'hermes','HERMES_HOME':str(home),
                     'HUD_PORT':str(ports[0]),'HUD_UI_PORT':str(ports[1]),'NETCLAW_HERMES_HUD_PORT':str(ports[2])}
                for port in ports:
                    with self.subTest(port=port),socket.socket() as listener:
                        listener.bind(('127.0.0.1',port));listener.listen()
                        result=subprocess.run(['node',str(ROOT/'scripts/hud-launch.mjs')],env=env,capture_output=True,text=True,timeout=10)
                        self.assertNotEqual(result.returncode,0);self.assertIn(f'port {port} is unavailable',result.stderr)
                        self.assertFalse((home/'netclaw-hud/companion-auth.json').exists())
                        self.assertFalse((home/'netclaw-hud/hermes').exists())
                        with socket.create_connection(('127.0.0.1',port),timeout=1):pass
            finally:
                for sock in sockets:sock.close()
if __name__=='__main__':unittest.main()
