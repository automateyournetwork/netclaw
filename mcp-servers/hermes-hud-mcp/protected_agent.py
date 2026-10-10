"""Construct a protected subclass only inside the dedicated companion process."""
import copy
import json
from ledger import HudError, digest
from bridge import sanitize

def protected_class(base, policy, ledger, request_context):
    class ProtectedAIAgent(base):
        def __init__(self,*args,**kwargs):
            self._hud_request=request_context.get()
            if not self._hud_request:raise HudError('owner_invalid')
            policy.check_sources()
            kwargs.update(skip_memory=True,skip_background_review=True,memory_manager=None,
                          skip_context_files=True,load_soul_identity=False,
                          enabled_toolsets=[],disabled_toolsets=[],fallback_model=None,
                          reasoning_callback=None,checkpoints_enabled=False)
            if kwargs.get('provider') in ('codex','claude-code','acp','command'):raise HudError('capability_unsupported')
            kwargs['ephemeral_system_prompt']=(kwargs.get('ephemeral_system_prompt') or '')+'\nNetClaw HUD: only qualified read-only tools are available. Never claim an operation ran without a tool result. Configuration, shell, delegation, file/history access and memory tools are unavailable. Report unsupported work explicitly.'+getattr(policy,'skill_context','')
            super().__init__(*args,**kwargs)
            # Native discovery has no operational authority. Only explicitly qualified
            # MCP schemas are advertised; the protected dispatch below has no fallback.
            if self.tools:raise HudError('policy_unverified','Unexpected native tool schema.')
            from tools.registry import registry
            self.tools=[];self._hud_handlers={}
            for name in sorted(policy.names):
                entry=registry.get_entry(name)
                if entry is None or not entry.toolset.startswith('mcp-'):raise HudError('policy_unverified')
                self.tools.append({'type':'function','function':copy.deepcopy(entry.schema)})
                self._hud_handlers[name]=entry.handler
            self.valid_tool_names=set(policy.names)
            self._hud_schema=digest(self.tools)
            self._skip_mcp_refresh=True
        def _hud_check(self):
            policy.check_sources()
            if digest(self.tools)!=self._hud_schema or self.valid_tool_names!=policy.names or not self._skip_mcp_refresh:raise HudError('policy_unverified')
            from tools.registry import registry
            if any(registry.get_entry(name) is None or registry.get_entry(name).handler is not handler for name,handler in self._hud_handlers.items()):raise HudError('policy_unverified')
        def _build_api_kwargs(self,*args,**kwargs):
            self._hud_check()
            return super()._build_api_kwargs(*args,**kwargs)
        def _invoke_tool(self,function_name,function_args,effective_task_id,tool_call_id=None,**kwargs):
            self._hud_check();policy.check_arguments(function_name,function_args)
            if not tool_call_id:raise HudError('input_invalid')
            ledger.record(self._hud_request,tool_call_id,function_name,'running')
            # Directly invoke the frozen MCP registry entry. Optional native plugin
            # middleware/inline shell executors never receive this dispatch.
            from tools.registry import registry
            result=registry.dispatch(function_name,function_args,task_id=effective_task_id)
            text=result if isinstance(result,str) else json.dumps(result)
            text=sanitize(text)
            try: failed=bool(json.loads(text).get('error'))
            except (ValueError,AttributeError):failed=False
            ledger.record(self._hud_request,tool_call_id,function_name,'failed' if failed else 'completed',text)
            if not failed:
                with ledger.db() as db:db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',('verified-policy',policy.fingerprint))
            return text
        def _execute_tool_calls(self,assistant_message,messages,effective_task_id,api_call_count=0):
            self._hud_check()
            # Validate the entire batch before any invocation; never execute a safe
            # prefix of a mixed safe/forbidden batch.
            calls=[]
            if len(assistant_message.tool_calls)>16:raise HudError('input_invalid')
            for call in assistant_message.tool_calls:
                args=json.loads(call.function.arguments or '{}')
                policy.check_arguments(call.function.name,args)
                calls.append((call,args))
            for call,args in calls:
                if getattr(self,'_interrupt_requested',False):
                    result='{"error":"cancelled before invocation"}'
                else:result=self._invoke_tool(call.function.name,args,effective_task_id,tool_call_id=call.id)
                messages.append({'role':'tool','tool_call_id':call.id,'name':call.function.name,'content':result})
    return ProtectedAIAgent
