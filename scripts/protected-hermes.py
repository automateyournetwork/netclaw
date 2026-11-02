#!/usr/bin/env python3
"""Pinned Hermes runner inside R02's isolated model container.

Uses the official AIAgent and MCP registry, with a narrow NetClaw adapter. The
trusted broker remains the authority: this process has only operation-scoped
capabilities, never upstream provider or device credentials.
"""
import copy
import json
import os
from pathlib import Path
import sys


def main():
    os.umask(0o077)
    job = json.loads(Path("/run/netclaw/job.json").read_text())
    home = Path("/home/agent/hermes")
    home.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.environ.update(HERMES_HOME=str(home), HERMES_CWD=str(home),
                      HERMES_DISABLE_LAZY_INSTALLS="1", PYTHON_DOTENV_DISABLED="1")
    config = {
        "mcp_servers": {"approved": {"url": job["mcp_url"], "transport": "streamable-http",
                         "headers": {"Authorization": "Bearer ${NETCLAW_OPERATION_TOKEN}"}}},
        "model": {"default": job["model"], "provider": "custom", "base_url": job["base_url"],
                  "api_mode": "chat_completions"},
        "toolsets": [], "tool_search": {"enabled": "off"},
        "memory": {"memory_enabled": False, "user_profile_enabled": False},
        "security": {"allow_lazy_installs": False},
        "auxiliary": {"title_generation": {"enabled": False, "model_upgrade_enabled": False}},
        "compression": {"enabled": False}, "plugins": {"enabled": []},
        "approvals": {"mode": "manual", "unattended_mode": "deny"}}
    # JSON is valid YAML. Credential remains an environment reference.
    (home / "config.yaml").write_text(json.dumps(config))
    os.chdir(home)
    sys.path.insert(0, "/opt/hermes")
    from hermes_cli.plugins_discovery import suppress_plugin_discovery
    with suppress_plugin_discovery():
        import run_agent
        from tools.mcp_tool_discovery import discover_mcp_tools
        from tools.registry import registry
        discovered = discover_mcp_tools(["approved"])
        name = "mcp__approved__pyats_run_show_command"
        if name not in discovered:
            raise ValueError("protected_mcp_tool_not_discovered")
        entry = registry.get_entry(name)
        if entry is None or not entry.toolset.startswith("mcp-"):
            raise ValueError("protected_mcp_registry_mismatch")

        class ProtectedAgent(run_agent.AIAgent):
            def __init__(self):
                super().__init__(base_url=job["base_url"], api_key=os.environ["NETCLAW_OPERATION_TOKEN"],
                                 provider="custom", api_mode="chat_completions", model=job["model"],
                                 max_iterations=2, max_tokens=2048, enabled_toolsets=[], disabled_toolsets=[],
                                 skip_memory=True, skip_background_review=True, skip_context_files=True,
                                 load_soul_identity=False, checkpoints_enabled=False, fallback_model=None,
                                 memory_manager=None, quiet_mode=True, session_id=job["operation_id"],
                                 ephemeral_system_prompt="Use only the exact approved MCP read once, then summarize its evidence.")
                if self.tools:
                    raise ValueError("unexpected_native_tools")
                self.tools = [{"type": "function", "function": copy.deepcopy(entry.schema)}]
                self.valid_tool_names = {name}
                self._skip_mcp_refresh = True
                self._protected_spent = False

            def _invoke_tool(self, function_name, function_args, effective_task_id, tool_call_id=None, **kwargs):
                if function_name != name or function_args != job["arguments"] or self._protected_spent:
                    raise ValueError("protected_tool_changed_or_spent")
                self._protected_spent = True
                if registry.get_entry(name).handler is not entry.handler:
                    raise ValueError("protected_handler_changed")
                result = registry.dispatch(name, function_args, task_id=effective_task_id)
                return result if isinstance(result, str) else json.dumps(result)

            def _execute_tool_calls(self, assistant_message, messages, effective_task_id, api_call_count=0):
                if len(assistant_message.tool_calls) != 1:
                    raise ValueError("single_approved_call_required")
                call = assistant_message.tool_calls[0]
                result = self._invoke_tool(call.function.name, json.loads(call.function.arguments),
                                           effective_task_id, tool_call_id=call.id)
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "name": call.function.name, "content": result})

        agent = ProtectedAgent()
        result = agent.run_conversation("Execute the approved show version read with exact arguments: "
                                        + json.dumps(job["arguments"]) + ". Summarize actual evidence; do not retry.")
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
