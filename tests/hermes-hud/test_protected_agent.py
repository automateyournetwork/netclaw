import contextvars
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'mcp-servers/hermes-hud-mcp'))
from ledger import Ledger,HudError,digest
from policy import ToolPolicy
from protected_agent import protected_class
class Base:
    def __init__(self,**kwargs):self.tools=[];self.options=kwargs
    def _build_api_kwargs(self):return {'tools':self.tools}
class ProtectedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        path=Path(self.tmp.name);config=path/'config';config.write_text('{}')
        import hashlib
        self.policy=ToolPolicy({},config,hashlib.sha256(b'{}').hexdigest())
        self.ledger=Ledger(path/'private/ledger.db','test');self.ledger.open('c');self.ledger.admit('c','r','n','text',1000)
        self.context=contextvars.ContextVar('request',default='r')
        registry=types.SimpleNamespace(get_entry=lambda name:None)
        self.patch=patch.dict(sys.modules,{'tools.registry':types.SimpleNamespace(registry=registry)})
        self.patch.start();self.addCleanup(self.patch.stop)
        self.Agent=protected_class(Base,self.policy,self.ledger,self.context)
    def test_forbidden_handlers_and_alternate_providers_never_execute(self):
        agent=self.Agent()
        for name in ['terminal','execute_code','delegate_task','memory','session_search','read_file','hermes_hud_submit']:
            with self.assertRaises(HudError):agent._invoke_tool(name,{},'task',tool_call_id='call')
        self.assertEqual(self.ledger.events('c','r'),[])
        for provider in ['codex','claude-code','acp','command']:
            with self.assertRaises(HudError):self.Agent(provider=provider)
    def test_schema_refresh_and_config_drift_fail_before_inference(self):
        agent=self.Agent();agent.tools.append({'name':'terminal'})
        with self.assertRaises(HudError):agent._build_api_kwargs()
        agent=self.Agent();agent._skip_mcp_refresh=False
        with self.assertRaises(HudError):agent._build_api_kwargs()
        self.policy.config_file.write_text('{"changed":true}')
        with self.assertRaises(HudError):self.Agent()
    def test_memory_context_and_fallback_are_disabled(self):
        agent=self.Agent(memory_manager=object(),fallback_model='other',skip_memory=False)
        self.assertTrue(agent.options['skip_memory']);self.assertTrue(agent.options['skip_context_files'])
        self.assertIsNone(agent.options['memory_manager']);self.assertIsNone(agent.options['fallback_model'])
        self.assertEqual(agent.options['enabled_toolsets'],[])
    def test_unexpected_native_tool_blocks_agent(self):
        class Bad(Base):
            def __init__(self,**kwargs):self.tools=[{'name':'terminal'}]
        with self.assertRaises(HudError):protected_class(Bad,self.policy,self.ledger,self.context)()
    def test_failed_audit_or_changed_handler_never_dispatches(self):
        import hashlib
        entry={'source':str(self.policy.config_file),'sourceHash':hashlib.sha256(b'{}').hexdigest(),'argumentPolicy':'fixture-echo'}
        self.policy=ToolPolicy({'mcp__fixture__echo':entry},self.policy.config_file,hashlib.sha256(b'{}').hexdigest())
        calls=[];registered=types.SimpleNamespace(toolset='mcp-fixture',schema={'name':'mcp__fixture__echo'},handler=lambda:None)
        registry=types.SimpleNamespace(get_entry=lambda _:registered,dispatch=lambda *a,**k:calls.append(a))
        with patch.dict(sys.modules,{'tools.registry':types.SimpleNamespace(registry=registry)}):
            agent=protected_class(Base,self.policy,self.ledger,self.context)()
            with patch.object(self.ledger,'record',side_effect=OSError('audit unavailable')):
                with self.assertRaises(OSError):agent._invoke_tool('mcp__fixture__echo',{'text':'safe'},'t',tool_call_id='call')
            registered.handler=lambda:None
            with self.assertRaises(HudError):agent._build_api_kwargs()
        self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
