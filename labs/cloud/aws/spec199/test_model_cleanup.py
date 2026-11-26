import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
import qualify as q


class ModelCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.root.chmod(0o700)
        self.export=self.root/'export';self.export.mkdir(mode=0o700);p=self.export/'state.json';p.write_bytes(b'{}');p.chmod(0o600)
        owner='netclaw-r08-r199-012345abcdef-12abcd';name=owner+'-model'
        self.owned={'schema_version':1,'owner_spec':199,'owner_name':owner,'image':'sha256:'+'d'*64,
                    'model_name':name,'probe_name':name+'-peer','network_name':name+'-net',
                    'model_id':'a'*64,'probe_id':'b'*64,'network_id':'c'*64}
        self.stopped={'objects_and_evidence_preserved':True,'stopped_container_ids':['a'*64,'b'*64],'network_retained':'c'*64}
        self.manifest={'schema':1,'quiescent':True,'resource_ids':['a'*64,'b'*64,'c'*64],
                       'files':[{'path':'state.json','size':2,'sha256':hashlib.sha256(b'{}').hexdigest()}]}
        self.plan=q.model_removal_plan(self.owned,self.stopped,self.export,self.manifest)
        self.calls=[];self.rows={}
        for action in self.plan['actions']:
            raw={'Id':action['id'],'Name':('/' if action['kind']=='container' else '')+action['name']}
            labels={'netclaw.spec':'199','netclaw.owner':owner}
            if action['kind']=='container':raw.update(Image=self.owned['image'],State={'Running':False},Config={'Labels':labels})
            else:raw.update(Labels=labels,Internal=True,Containers={})
            self.rows[action['id']]={'query_succeeded':True,'absent':False,'observed_at':time.time(),'raw':raw}
    def tearDown(self):self.tmp.cleanup()
    def observe(self,action):return self.rows[action['id']]
    def invoke(self,args):self.calls.append(args);return {'returncode':0}
    def test_stop_alone_and_missing_export_do_not_authorize_removal(self):
        for field,value in [('objects_and_evidence_preserved',False),('network_retained','f'*64)]:
            with self.assertRaises(ValueError):q.model_removal_plan(self.owned,dict(self.stopped,**{field:value}),self.export,self.manifest)
        (self.export/'state.json').write_bytes(b'changed')
        with self.assertRaises(ValueError):q.remove_model_once(self.root,self.plan,0,self.observe,self.invoke)
        self.assertFalse(self.calls)
    def test_foreign_running_stale_or_failed_inspection_never_sends(self):
        original=copy.deepcopy(self.rows['b'*64])
        for change in ('foreign','running','stale','query'):
            row=copy.deepcopy(original)
            if change=='foreign':row['raw']['Config']['Labels']['netclaw.owner']='foreign'
            if change=='running':row['raw']['State']['Running']=True
            if change=='stale':row['observed_at']=0
            if change=='query':row['query_succeeded']=False
            self.rows['b'*64]=row
            with self.assertRaises(ValueError):q.remove_model_once(self.root,self.plan,0,self.observe,self.invoke)
        self.assertFalse(self.calls)
    def test_lost_reply_preserves_send_intent_and_blocks_replay(self):
        def lost(args):self.calls.append(args);raise TimeoutError('fixture')
        with self.assertRaises(TimeoutError):q.remove_model_once(self.root,self.plan,0,self.observe,lost)
        with self.assertRaises(FileExistsError):q.remove_model_once(self.root,self.plan,0,self.observe,self.invoke)
        self.assertEqual(self.calls,[['rm','b'*64]])
    def test_network_requires_prior_absence_and_empty_exact_network(self):
        with self.assertRaises(ValueError):q.remove_model_once(self.root,self.plan,2,self.observe,self.invoke)
        for i in ('a'*64,'b'*64):self.rows[i].update(absent=True)
        self.rows['c'*64]['raw']['Containers']={'foreign':{}}
        with self.assertRaises(ValueError):q.remove_model_once(self.root,self.plan,2,self.observe,self.invoke)
        self.rows['c'*64]['raw']['Containers']={}
        q.remove_model_once(self.root,self.plan,2,self.observe,self.invoke)
        self.assertEqual(self.calls,[['network','rm','c'*64]])
