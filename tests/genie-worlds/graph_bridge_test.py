import copy
import json
import subprocess
import unittest
import neighbors_test as neighbors
import facts_test as counters
facts = neighbors.facts

NODE = '/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node'

class GraphBridgeTests(unittest.TestCase):
    setUp = neighbors.NeighborsTests.setUp
    claim = neighbors.NeighborsTests.claim
    def graph(self, claims, **kw):
        devices = [dict(d, label='Synthetic '+d['id'], role='unknown') for d in self.devices]
        ports = [dict(p, label='Ethernet1', status='unknown') for p in self.ports]
        records = {}
        for d in devices + ports:
            for i in d['identities']:
                p = i['evidence']; records[p['observation_id']] = dict(p, id=p['observation_id'], started_at='2026-11-22T11:59:00Z', finished_at='2026-11-22T11:59:01Z')
        for c in claims:
            p = c['evidence']; records[p['observation_id']] = dict(p, id=p['observation_id'], started_at=c['started_at'], finished_at=c['finished_at'])
        if 'state' in kw:
            state=kw['state']; ports[0].update(status='down',state_evidence=state)
            if state: records[state['observation_id']]=dict(state,id=state['observation_id'],started_at='2026-11-22T12:00:02Z',finished_at='2026-11-22T12:00:03Z')
        records['failed'] = dict(id='failed',device_ref='c',outcome='timeout',source='synthetic-test',command='show cdp neighbors detail',parser_version='fixture',sha256=None,capture_outcome_unknown=True,started_at='2026-11-22T12:00:00Z',finished_at='2026-11-22T12:00:01Z')
        for entry in kw.get('counters',[]):
            for source in [entry.get('first'),entry.get('second'),entry.get('continuity'),entry.get('capacity')]:
                if source and source.get('evidence'):
                    p=source['evidence']
                    records[p['observation_id']]=dict(p,id=p['observation_id'],device_ref='a',outcome='observed',started_at=source.get('started_at','2026-11-22T00:00:00Z'),finished_at=source.get('finished_at','2026-11-22T00:00:12Z'))
        return facts.local_graph(devices, ports, claims, list(records.values()), graph_id='synthetic-bridge', now=kw.get('now','2026-11-22T12:00:10Z'), counters=kw.get('counters',[]))

    def test_bridge_preserves_unresolved_and_coverage_without_geometry(self):
        g = self.graph([self.claim(), self.claim('c','missing','cx')])
        self.assertEqual(len(g['links']),1)
        self.assertEqual(g['discovery'][1]['reason'],'unmatched_identity')
        self.assertIsNone(g['discovery'][1]['remote_interface_id'])
        self.assertEqual(g['coverage'][-1]['outcome'],'timeout')
        self.assertIsNone(g['coverage'][-1]['sha256'])
        self.assertEqual(g['discovery'][1]['remote_identities'][0]['value'],'missing')
        self.assertTrue(g['coverage'][-1]['capture_outcome_unknown'])
        self.assertEqual(len(g['devices']),3)
        self.assertTrue(g['links'][0]['evidence_ids'])
        self.assertEqual(g['classification'],'private')

    def test_actual_javascript_contract_layout_and_immutability(self):
        g = self.graph([self.claim(), self.claim('b','a','ba')])
        code = "import {localGraph,graphLayout} from './scripts/genie-worlds/viewer/network-graph.mjs';import fs from 'node:fs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));if(!Object.isFrozen(g.discovery[0])||graphLayout(g).links.length!==1)throw Error('bridge');console.log('validated');"
        p = subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(g),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.strip(),'validated')

    def test_stale_and_conflicting_claims_are_retained(self):
        self.assertEqual(self.graph([self.claim()],now='2026-11-22T12:06:00Z')['links'][0]['certainty'],'unknown')
        g=self.graph([self.claim(),self.claim('a','c','ac')])
        self.assertTrue(all(l['certainty']=='conflict' for l in g['links']))
        self.assertTrue(all(c['reason']=='competing_peer_claims' for c in g['discovery']))

    def test_discovery_proof_cannot_establish_port_health(self):
        self.ports[0]['status']='up'
        # graph() deliberately defaults to unknown. Exercise a direct amended input.
        devices=[dict(d,label=d['id'],role='unknown') for d in self.devices]
        ports=[dict(p,label='Ethernet1',status='up',state_evidence=p['identities'][0]['evidence']) for p in self.ports]
        observations=[]
        for d in devices+ports:
            p=d['identities'][0]['evidence']
            observations.append(dict(p,id=p['observation_id'],started_at='2026-11-22T12:00:00Z',finished_at='2026-11-22T12:00:01Z'))
        with self.assertRaises(ValueError): facts.local_graph(devices,ports,[],observations,graph_id='test',now='2026-11-22T12:00:10Z')

    def test_missing_or_mismatched_source_record_is_rejected(self):
        with self.assertRaises(ValueError): facts.local_graph(self.devices,self.ports,[self.claim()],[],graph_id='test',now='2026-11-22T12:00:10Z')
        claim=self.claim();claim['evidence']['observation_id']='a';claim['evidence']['sha256']='b'*64
        with self.assertRaises(ValueError): self.graph([claim])

    def test_state_and_discovery_proofs_stay_separate_through_javascript(self):
        state=neighbors.proof('state','a'); state['command']='show interfaces'
        g=self.graph([self.claim()],state=state)
        p=g['interfaces'][0]; c=g['discovery'][0]
        self.assertNotEqual(p['state_evidence_id'],c['discovery_evidence_id'])
        code="import {localGraph} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';import fs from 'node:fs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));const d=selectionDetails(g,g.links[0].id,Date.parse('2026-11-22T12:00:10Z'));if(d.raw.stateComparisons.length!==1||d.raw.stateComparisons[0].relation!=='after discovery'||g.links[0].certainty!=='one_sided')throw Error('state separation');"
        r=subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(g),text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr)
        state['device_ref']='b'
        with self.assertRaises(ValueError):self.graph([self.claim()],state=state)
        with self.assertRaises(ValueError):self.graph([self.claim()],state={})

class CounterGraphTests(unittest.TestCase):
    setUp = GraphBridgeTests.setUp
    graph = GraphBridgeTests.graph
    def entry(self):
        case=counters.CounterTests();case.setUp()
        for s in [case.first,case.second,case.capacity]:
            s.update(device_id='a',interface_id=self.ports[0]['id'])
        for s in [case.first,case.second,case.continuity,case.capacity]:
            s['evidence']['command']='show interfaces'
        return dict(id='in-rate',interface_id=self.ports[0]['id'],field='in_octets',direction='in',first=case.first,second=case.second,continuity=case.continuity,capacity=case.capacity)

    def test_counter_pair_survives_actual_js_boundary_and_inspector(self):
        g=self.graph([],counters=[self.entry()]);r=g['counters'][0]
        self.assertEqual((r['delta'],r['value'],r['utilization_percent']),('1000',100,10))
        self.assertEqual(len(r['sample_evidence_ids']),2)
        code="import {localGraph} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';import fs from 'node:fs';const g=localGraph(JSON.parse(fs.readFileSync(0,'utf8')));const d=selectionDetails(g,g.interfaces[0].id);if(!Object.isFrozen(g.counters[0])||!d.rows.some(([k,v])=>v.includes('100 bytes/s'))||d.raw.counters[0].delta!=='1000')throw Error('counter binding');"
        p=subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(g),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_raw_counts_survive_unknown_timing_and_missing_pair(self):
        e=self.entry();e['first'].update(value='18446744073709551615',sampled_at=None,incarnation=None)
        e['second']=None;e['continuity']=None;e['capacity']=None
        g=self.graph([],counters=[e]);r=g['counters'][0]
        self.assertIsNone(r['value'])
        self.assertEqual(r['observed_samples'][0]['value'],'18446744073709551615')
        self.assertIsNone(r['observed_samples'][0]['sampled_at'])
        code="""import {localGraph} from './scripts/genie-worlds/viewer/network-graph.mjs';import {selectionDetails} from './scripts/genie-worlds/viewer/selection.mjs';import fs from 'node:fs';const input=JSON.parse(fs.readFileSync(0,'utf8'));const g=localGraph(input);const d=selectionDetails(g,g.interfaces[0].id);if(!d.rows.some(([k,v])=>v.includes('18446744073709551615 bytes'))||!d.rows.some(([k,v])=>v.includes('sample instant unknown'))||!d.rows.some(([k,v])=>v.includes('No qualified observation')))throw Error('raw sample lost');for(const mutate of [s=>s.value=18446744073709551615,s=>s.value='18446744073709551616',s=>s.evidence_id='foreign',s=>s.started_at='2026-01-01T00:00:00Z']){const bad=structuredClone(input);mutate(bad.counters[0].observed_samples[0]);let refused=false;try{localGraph(bad)}catch{refused=true}if(!refused)throw Error('invalid raw sample accepted')}"""
        p=subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(g),text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_raw_missing_counter_is_unknown_not_zero(self):
        e=self.entry();e['first'].update(value=None,outcome='unknown',sampled_at=None,incarnation=None)
        r=self.graph([],counters=[e])['counters'][0]
        self.assertIsNone(r['value']);self.assertIsNone(r['observed_samples'][0]['value'])
        self.assertEqual(r['observed_samples'][0]['outcome'],'unknown')

    def test_unknown_reset_and_capacity_conflict_remain_distinct(self):
        e=self.entry();e['second']['value']='1'
        r=self.graph([],counters=[e])['counters'][0]
        self.assertIsNone(r['value']);self.assertEqual(r['reason'],'counter_decreased')
        e=self.entry();e['capacity']['value']='1'
        r=self.graph([],counters=[e])['counters'][0]
        self.assertEqual(r['value'],100);self.assertIsNone(r['utilization_percent']);self.assertEqual(r['utilization_reason'],'capacity_conflict')
        code="import {localGraph} from './scripts/genie-worlds/viewer/network-graph.mjs';import fs from 'node:fs';localGraph(JSON.parse(fs.readFileSync(0,'utf8')));"
        for c in [e,dict(self.entry(),continuity=None)]:
            result=subprocess.run([NODE,'--input-type=module','-e',code],input=json.dumps(self.graph([],counters=[c])),text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
        e=self.entry();e['second']=None
        r=self.graph([],counters=[e])['counters'][0];self.assertIsNone(r['value']);self.assertEqual(r['reason'],'missing_sample')

    def test_foreign_owner_and_noninterface_sample_are_refused(self):
        for change in ('owner','command','unknown_port','direction','field'):
            e=self.entry()
            if change=='owner':e['first']['device_id']='b'
            elif change=='command':e['first']['evidence']['command']='show version'
            elif change=='unknown_port':e['interface_id']='invented'
            else:e[change]='out' if change=='direction' else 'out_octets'
            with self.subTest(change=change),self.assertRaises(ValueError):self.graph([],counters=[e])

if __name__ == '__main__': unittest.main()
