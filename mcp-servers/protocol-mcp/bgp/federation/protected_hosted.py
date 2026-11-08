"""Hosted foundation-model execution profile (spec 182); parity-minded, not qualified.

The profile carries no credential: the provider key reaches only the DefenseClaw
guard through its existing read-only env file. Every refusal is a fixed code with
no echo of the offending value. See specs/182-multi-region-ha-borders/model-transport.md
for the gaps this profile does not close (guard upstream target, egress filtering,
confinement proof, REAL evidence).
"""
import hashlib
import json
import re

from .protected_ollama import PROMPT_VERSION, SYSTEM_PROMPT

PROVIDER = 'anthropic'
MODEL = 'claude-sonnet-5-5'
EGRESS_HOST = 'api.anthropic.com'
FIELDS = {'schema_version', 'provider', 'model', 'egress_host', 'max_output_tokens',
          'call_timeout_seconds', 'task_timeout_seconds'}
_CREDENTIAL_VALUE = re.compile(r'sk-[A-Za-z0-9_-]{8,}')


class HostedRefused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(value, code):
    if not value:
        raise HostedRefused(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _bounded(value, low, high):
    return type(value) is int and low <= value <= high


def validate_profile(value):
    need(isinstance(value, dict) and set(value) == FIELDS, 'hosted_profile_fields_invalid')
    need(not any(isinstance(item, str) and _CREDENTIAL_VALUE.search(item) for item in value.values()),
         'hosted_credential_refused')
    need(type(value['schema_version']) is int and value['schema_version'] == 1, 'hosted_profile_invalid')
    need(value['provider'] == PROVIDER and value['model'] == MODEL, 'hosted_profile_unqualified')
    need(value['egress_host'] == EGRESS_HOST, 'hosted_egress_host_refused')
    need(_bounded(value['max_output_tokens'], 1, 4096), 'hosted_limits_invalid')
    need(_bounded(value['call_timeout_seconds'], 1, 120), 'hosted_limits_invalid')
    need(_bounded(value['task_timeout_seconds'], 1, 180), 'hosted_limits_invalid')


def limits(profile):
    validate_profile(profile)
    return {'model': MODEL, 'max_output_tokens': profile['max_output_tokens'], 'max_inference_calls': 2,
            'max_tool_calls': 1, 'call_timeout_seconds': profile['call_timeout_seconds'],
            'task_timeout_seconds': profile['task_timeout_seconds']}


def profile_binding(value):
    validate_profile(value)
    return {'schema': 'netclaw.hosted-profile.v1', 'profile': value, 'limits': limits(value),
            'prompt_version': PROMPT_VERSION, 'prompt_sha256': hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()}


def profile_id(value):
    validate_profile(value)
    return 'hosted-anthropic-' + MODEL
