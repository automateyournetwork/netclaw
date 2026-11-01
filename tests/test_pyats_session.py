"""Persistent session boundary tests; synthetic state only."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/lib'))
from pyats_session import BearerAuth, binding, publish, read


class SessionTests(unittest.TestCase):
    def test_binding_private_file_expiry_and_no_implicit_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'session.json'
            identity=binding({'NETCLAW_CHANGE_ROOT':directory},Path(sys.executable),Path(__file__))
            value={'schema':1,'pid':os.getpid(),'port':20481,'token':'a'*64,'binding':identity,'expires':time.time()+60}
            publish(path,value)
            self.assertEqual(read(path,identity),value)
            with self.assertRaises(FileExistsError):publish(path,value)
            with self.assertRaises(ValueError):read(path,'another-installation')
            path.chmod(0o644)
            with self.assertRaises(ValueError):read(path,identity)
            path.chmod(0o600)
            value['expires']=time.time()-1;path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):read(path,identity)
            link=path.with_name('linked.json');link.symlink_to(path)
            with self.assertRaises(OSError):read(link,identity)

    def test_auth_precedes_all_mcp_methods(self):
        async def run():
            called=[];sent=[]
            async def app(scope,receive,send):called.append(scope['type'])
            async def send(value):sent.append(value)
            auth=BearerAuth(app,'b'*64)
            for headers in ([],[(b'authorization',b'Bearer wrong')],
                            [(b'authorization',b'Bearer '+b'b'*64)]*2):
                sent.clear();await auth({'type':'http','headers':headers},None,send)
                self.assertEqual(sent[0]['status'],401);self.assertEqual(called,[])
            await auth({'type':'http','headers':[(b'authorization',b'Bearer '+b'b'*64)]},None,send)
            await auth({'type':'lifespan'},None,send)
            self.assertEqual(called,['http','lifespan'])
        asyncio.run(run())


if __name__=='__main__':unittest.main()
