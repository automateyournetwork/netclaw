"""Execute the production functions with controlled Batfish answers (no daemon)."""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[2]
class Frame:
    def __init__(self,rows):self.rows=rows;self.empty=not rows
    def iterrows(self):return enumerate(self.rows)
class BF:
    def __init__(self,parse='PASSED',fail=None,routes=None):
        self.parse=parse;self.fail=fail;self.routes=routes or {};self.snapshot='a'
        self.q=SimpleNamespace(**{k:(lambda name=k:self.query(name)) for k in ('fileParseStatus','nodeProperties','initIssues','routes','differentialReachability')})
    def set_network(self,x):pass
    def set_snapshot(self,x):self.snapshot=x
    def set_reference_snapshot(self,x):pass
    def list_snapshots(self):return ['a','b']
    def query(self,name):
        if name==self.fail:raise RuntimeError('controlled query failure')
        rows=[]
        if name=='fileParseStatus' and self.parse:rows=[{'Status':self.parse,'File_Name':'synthetic.cfg','Nodes':[]}]
        if name=='routes':rows=self.routes.get(self.snapshot,[])
        return SimpleNamespace(answer=lambda:SimpleNamespace(frame=lambda:Frame(rows)))

class CoverageTests(unittest.TestCase):
    def functions(self,bf):
        source=ast.parse((ROOT/'mcp-servers/batfish-mcp/batfish_mcp_server.py').read_text())
        functions=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('batfish_validate_config','batfish_diff_configs')]
        for n in functions:n.decorator_list=[]
        module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+functions,type_ignores=[])
        scope={'BATFISH_NETWORK':'synthetic','_get_bf_session':lambda:bf,'_gcf_dumps':json.dumps,'json':json,
               '_gait_log':lambda **kw:None,'datetime':datetime,'timezone':timezone}
        exec(compile(ast.fix_missing_locations(module),'<production-batfish-functions>','exec'),scope)
        return scope
    def test_partial_empty_and_parse_failure_are_inconclusive(self):
        for status,failed in [('PARTIALLY_UNRECOGNIZED',None),(None,None),('PASSED','fileParseStatus')]:
            f=self.functions(BF(status,failed));r=json.loads(f['batfish_diff_configs']('a','b'))
            self.assertEqual(r['comparison_status'],'inconclusive');self.assertFalse(r['behavioral_equivalence'])
    def test_differential_failure_is_not_zero_differences(self):
        r=json.loads(self.functions(BF(fail='differentialReachability'))['batfish_diff_configs']('a','b'))
        self.assertEqual(r['query_status']['reachability'],'failed');self.assertEqual(r['comparison_status'],'inconclusive')
    def test_identical_snapshot_still_checks_queries(self):
        r=json.loads(self.functions(BF(fail='routes'))['batfish_diff_configs']('a','a'))
        self.assertEqual(r['comparison_status'],'inconclusive')
    def test_no_queries_is_not_equality_and_success_is_scoped(self):
        f=self.functions(BF())
        self.assertEqual(json.loads(f['batfish_diff_configs']('a','b',False,False))['comparison_status'],'inconclusive')
        r=json.loads(f['batfish_diff_configs']('a','b'));self.assertEqual(r['comparison_status'],'no_differences_in_requested_queries');self.assertFalse(r['behavioral_equivalence'])
    def test_ecmp_and_vrf_changes_not_lost(self):
        def route(hop,vrf='default'):return {'Node':'r','VRF':vrf,'Network':'192.0.2.0/24','Protocol':'ospf','Next_Hop':hop}
        r=json.loads(self.functions(BF(routes={'a':[route('one'),route('two')],'b':[route('two')]}))['batfish_diff_configs']('a','b'))
        self.assertEqual(r['summary']['changed'],1)
    def test_partial_and_empty_validation_fail(self):
        for status in ('PARTIALLY_UNRECOGNIZED',None):
            r=json.loads(self.functions(BF(status))['batfish_validate_config']('a'))
            self.assertEqual(r['overall_status'],'FAIL');self.assertEqual(r['parse_coverage'],'incomplete')

if __name__=='__main__':unittest.main()
