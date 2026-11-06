"""Keyless official DefenseClaw configuration checks for the pinned R05 model.

Adapted from Thermidor guard_adapter._safe_configuration. This is not a provider
proxy: native DefenseClaw routes the trusted fixed loopback target. The host's
persistent inference claims and runner-wide latch surround every guard dispatch.
"""
import hashlib
import re
from pathlib import Path
from protected_provider import ProviderRefused, private_read, require

MODEL = 'qwen3:0.6b'
TARGET = 'http://127.0.0.1:11434'


def verify_config(home, expected):
    import yaml
    raw = private_read(Path(home)/'config.yaml', 1024*1024)
    require(isinstance(expected, str) and re.fullmatch('[a-f0-9]{64}', expected)
            and hashlib.sha256(raw).hexdigest() == expected, 'ollama_guard_config_changed', 503)
    try:
        class StrictLoader(yaml.SafeLoader):
            def construct_mapping(self, node, deep=False):
                values = {}
                for key_node, value_node in node.value:
                    key = self.construct_object(key_node, deep=deep)
                    require(isinstance(key, str) and key not in values, 'ollama_guard_config_duplicate', 503)
                    values[key] = self.construct_object(value_node, deep=deep)
                return values
        require(not any(isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for token in yaml.scan(raw)), 'ollama_guard_config_alias', 503)
        cfg = yaml.load(raw, Loader=StrictLoader)
        require(isinstance(cfg, dict), 'ollama_guard_config_invalid', 503)
        guard = cfg.get('guardrail')
        require(type(cfg.get('config_version')) is int and cfg['config_version'] == 9
                and cfg.get('deployment_mode') == 'server' and isinstance(guard, dict), 'ollama_guard_config_unqualified', 503)
        expected_guard = {'enabled': True, 'mode': 'action', 'scanner_mode': 'local', 'connector': 'openclaw',
            'host': '0.0.0.0', 'port': 4000, 'rule_pack': 'strict', 'hook_fail_mode': 'closed',
            'detection_strategy': 'regex_only', 'allow_unknown_llm_domains': False, 'allow_empty_providers': False,
            'model': 'ollama/'+MODEL, 'model_name': MODEL}
        require(all(type(guard.get(k)) is type(v) and guard[k] == v for k,v in expected_guard.items()), 'ollama_guard_config_unqualified', 503)
        llm = {'model': 'ollama/'+MODEL, 'forward_custom_headers': False}
        require(guard.get('llm') == cfg.get('llm') == llm and not guard.get('api_key_env') and not guard.get('api_base'), 'ollama_guard_route_refused', 503)
        for name in ('hilt', 'judge'):
            require(isinstance(guard.get(name), dict) and guard[name].get('enabled') is False, 'ollama_guard_config_unqualified', 503)
        for name in ('connectors', 'profiles', 'profile_assignments', 'default_profile', 'custom_packs', 'rules',
                     'rule_pack_dir', 'allow_private_upstreams', 'block_at', 'alert_at'):
            require(not guard.get(name), 'ollama_guard_overlay_refused', 503)
        for name in ('detection_strategy_prompt', 'detection_strategy_completion', 'detection_strategy_tool_call'):
            require(guard.get(name) in (None, '', 'regex_only'), 'ollama_guard_config_unqualified', 503)
        require(guard.get('judge_sweep', False) is False, 'ollama_guard_config_unqualified', 503)
        cisco = cfg.get('cisco_ai_defense', {})
        require(isinstance(cisco, dict) and cisco.get('enabled', False) is False, 'ollama_guard_config_unqualified', 503)
        require(not cfg.get('application_protection') and not cfg.get('routing', {}).get('enabled', False), 'ollama_guard_overlay_refused', 503)
        gateway = cfg.get('gateway', {})
        require(isinstance(gateway, dict) and gateway.get('api_bind') == '127.0.0.1'
                and type(gateway.get('api_port')) is int and gateway['api_port'] == 18970
                and gateway.get('tls_skip_verify', False) is False, 'ollama_guard_listener_refused', 503)
        require(str(cfg.get('data_dir')) == str(home), 'guard_data_directory_mismatch', 503)
        def forbidden(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    require(key not in ('api_key', 'api_key_env', 'base_url', 'api_base', 'allow_private_upstreams') or child in (None, False, ''), 'ollama_guard_credentials_or_route_refused', 503)
                    forbidden(child)
            elif isinstance(value, list):
                for child in value: forbidden(child)
        forbidden(cfg)
    except ProviderRefused:
        raise
    except Exception:
        raise ProviderRefused('ollama_guard_config_invalid', 503) from None
    return expected
