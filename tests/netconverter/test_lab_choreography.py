"""Execute the skill's CML choreography through a controlled official MCP peer.

The harness supplies the reviewed fixture decisions; this is not an autonomous
LLM evaluation or evidence that a real provider/image accepted these parameters.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/lib'))
from migration_artifacts import Rehearsal, digest, pack

class LabChoreography(unittest.IsolatedAsyncioTestCase):
    async def exercise(self,lose=False):
        from mcp.client.client import Client
        from mcp.client.stdio import StdioServerParameters,stdio_client
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryFile(mode='w+') as diagnostics:
            root=Path(folder).resolve();run=Rehearsal(root,uuid.uuid4().hex)
            if lose:(root/'lose-response').touch()
            params=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).with_name('lab_peer.py')),str(root)],env={'PATH':os.defpath})
            async with Client(stdio_client(params,errlog=diagnostics),mode='legacy') as client:
                names={t.name for t in (await client.list_tools()).tools}
                async def call(name,args):
                    self.assertIn(name,names)
                    result=await client.session.call_tool(name,args,allow_input_required=True,allow_claimed=True)
                    return result
                def payload(result):
                    self.assertFalse(result.is_error)
                    return result.structured_content or json.loads(result.content[0].text)
                definition=payload(await call('get_cml_node_definitions',{}))['definitions'][0]
                run.begin('controlled-cml',{'isolated':True,'image':definition['image'],'authorization':'fixture only'},['identity','boot','positive','negative'])
                attempt=run.attempt('create_empty_lab',digest(pack({'title':'synthetic-run'})))
                ownership={'run_id':run.root.name,'attempt_id':attempt}
                result=await call('create_empty_lab',{'title':'synthetic-run','description':json.dumps(ownership)})
                if lose:
                    self.assertTrue(result.is_error)
                    labs=payload(await call('get_cml_labs',{}))['labs']
                    lab=next(l for l in labs if l['ownership']==ownership)
                else:lab=payload(result)
                run.reconcile(attempt,lab['id'],lab['ownership'])
                await call('add_node_to_cml_lab',{'lab_id':lab['id'],'node_definition':definition['id'],'label':'fixture-target'})
                await call('start_cml_lab',{'lab_id':lab['id']})
                observed=payload(await call('get_nodes_for_cml_lab',{'lab_id':lab['id']}))
                self.assertEqual(observed['nodes'][0]['state'],'BOOTED')
                run.evidence('boot state','passed','controlled-peer',{'provider_id':observed['nodes'][0]['id']})
            calls=[json.loads(line) for line in (root/'calls.jsonl').read_text().splitlines()]
            self.assertEqual(sum(c['tool']=='create_empty_lab' for c in calls),1)
            self.assertEqual(calls[-2]['tool'],'start_cml_lab');self.assertEqual(calls[-1]['tool'],'get_nodes_for_cml_lab')
            self.assertFalse(any('config' in c['arguments'] for c in calls))
    async def test_actual_discover_create_boot_inspect_sequence(self):await self.exercise()
    async def test_unknown_creation_is_reconciled_without_duplicate(self):await self.exercise(True)

if __name__=='__main__':unittest.main()
