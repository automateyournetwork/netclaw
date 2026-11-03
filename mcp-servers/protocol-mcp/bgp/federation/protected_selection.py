"""Immutable local execution selection; no new authority or recovery store.

The trusted service validates the current private catalog/configuration before
admission and again at the effect boundary. Each executor keeps its own frozen
single-device configuration while sharing the existing durable operation namespace.
"""
import ipaddress
import os
from pathlib import Path
import re
import stat

from .protected_contract import (MAX_ENVELOPE, ProtectedError, decode, encode,
                                 exact, ident, require, validate_catalog_entry,
                                 validate_model, validate_tool)
from .protected_runtime import RuntimeRefused


def _snapshot(value):
    raw = encode(value)
    require(len(raw) <= MAX_ENVELOPE, 'execution_profiles_too_large', 413)
    return raw


def _selection(model, tool):
    return encode({'model_profile': model, 'tool_call': tool})


def _private_path(value, *, directory=False, may_be_absent=False):
    require(isinstance(value, str), 'unsafe_execution_profile_path', 503)
    path = Path(value)
    require(path.is_absolute() and str(path) == value and path == path.resolve(),
            'unsafe_execution_profile_path', 503)
    if may_be_absent and not path.exists():
        return
    info = path.lstat()
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and info.st_uid == os.getuid() and not info.st_mode & 0o077,
            'unsafe_execution_profile_path', 503)


class ProfiledExecutor:
    """Select a full approved model/tool pair from bounded private snapshots."""

    def __init__(self, config, *, manager):
        from .protected_docker import DockerExecutor, validate_execution_bindings

        self._configuration = _snapshot(config)
        copied = decode(self._configuration)
        exact(copied, 'schemaVersion profiles')
        require(type(copied['schemaVersion']) is int and copied['schemaVersion'] == 1,
                'unsupported_execution_profiles', 503)
        profiles = copied['profiles']
        require(isinstance(profiles, list) and 1 <= len(profiles) <= 16,
                'execution_profile_bound', 503)
        models, calls, selections, states, snapshots = {}, {}, set(), set(), []
        # Validate the entire packet before any child creates private state.
        for item in profiles:
            exact(item, 'model_profile_id tool_call runtime')
            ident(item['model_profile_id'])
            tool, runtime = item['tool_call'], item['runtime']
            validate_tool(tool)
            require(isinstance(runtime, dict) and isinstance(runtime.get('model_profile'), dict),
                    'invalid_execution_profile', 503)
            model = runtime['model_profile']
            validate_model(model)
            require(item['model_profile_id'] == model['profile_id'], 'model_profile_id_mismatch', 503)
            model_bytes, tool_bytes = encode(model), encode(tool)
            call = (tool['tool'], encode(tool['arguments']))
            require(model['profile_id'] not in models or models[model['profile_id']] == model_bytes,
                    'inconsistent_model_profile', 503)
            require(call not in calls or calls[call] == tool_bytes, 'inconsistent_tool_profile', 503)
            models[model['profile_id']], calls[call] = model_bytes, tool_bytes
            key = _selection(model, tool)
            require(key not in selections, 'duplicate_execution_profile', 503)
            selections.add(key)
            try:
                validate_execution_bindings(runtime, {'model_profile': model, 'tool_call': tool})
                _private_path(runtime['state_dir'], directory=True, may_be_absent=True)
                states.add(runtime['state_dir'])
                pool = ipaddress.IPv4Network(runtime['sandbox_address_pool'])
                require(pool.prefixlen <= 24 and pool.subnet_of(ipaddress.IPv4Network('198.18.0.0/15')),
                        'reviewed_benchmark_address_pool_required', 503)
                token_name = runtime['guard_token_env']
                require(isinstance(token_name, str) and re.fullmatch(r'NETCLAW_[A-Z0-9_]+', token_name)
                        and os.environ.get(token_name), 'guard_credential_unavailable', 503)
                for field in ('config_file', 'env_file'):
                    _private_path(runtime['guard'][field])
                    require(',' not in runtime['guard'][field], 'unsafe_guard_binding', 503)
                for field in ('testbed', 'known_hosts'):
                    _private_path(runtime['pyats'][field])
                require(tool['arguments']['timeout'] <= 120, 'unsupported_tool_policy', 503)
            except ProtectedError:
                raise
            except (OSError, KeyError, TypeError, ValueError):
                raise RuntimeRefused('invalid_execution_profile', 503) from None
            snapshots.append((key, encode(runtime)))
        require(len(states) == 1, 'shared_execution_state_required', 503)
        self._snapshots = tuple(snapshots)
        self._children, self._catalog = {}, None
        self._catalog_valid, self._closed, self._invalidated = False, False, False
        try:
            for key, snapshot in self._snapshots:
                self._children[key] = DockerExecutor(decode(snapshot), manager=manager)
        except BaseException:
            self.close()
            raise

    def validate_catalog(self, catalog, *, runtime_config):
        """A failed configuration/catalog check requires a fresh service start."""
        self._catalog_valid = False
        require(not self._closed, 'execution_profiles_closed', 503)
        require(not self._invalidated, 'execution_profiles_restart_required', 503)
        try:
            require(_snapshot(runtime_config) == self._configuration, 'execution_profiles_changed', 409)
            validate_catalog_entry(catalog)
            require(len(catalog['model_profiles']) * len(catalog['tools']) == len(self._snapshots),
                    'execution_catalog_mismatch', 503)
            advertised = {_selection(model, {key: value for key, value in tool.items() if key != 'limits'})
                          for model in catalog['model_profiles'] for tool in catalog['tools']}
            require(advertised == set(self._children), 'execution_catalog_mismatch', 503)
            snapshot = _snapshot(catalog)
            require(self._catalog is None or self._catalog == snapshot, 'execution_catalog_changed', 409)
            self._catalog = snapshot
            self._catalog_valid = True
        except BaseException:
            # Restoring old bytes is not authorization to resume a running
            # selector after an observed private configuration change.
            self.invalidate()
            raise

    def invalidate(self):
        """Latch failures reading/decoding the private profile before validation."""
        self._invalidated, self._catalog_valid = True, False

    async def run(self, payload, gate):
        from .protected_docker import validate_execution_bindings

        require(not self._closed and self._catalog_valid, 'execution_catalog_unvalidated', 503)
        copied = decode(_snapshot(payload))
        require(isinstance(copied, dict) and 'model_profile' in copied and 'tool_call' in copied,
                'execution_profile_not_supported', 403)
        validate_model(copied['model_profile'])
        validate_tool(copied['tool_call'])
        key = _selection(copied['model_profile'], copied['tool_call'])
        child = self._children.get(key)
        require(child is not None, 'execution_profile_not_supported', 403)
        # Also catch accidental mutation of a live child by trusted integration
        # code. No caller can change the selected endpoint while another awaits.
        snapshot = next(raw for selected, raw in self._snapshots if selected == key)
        if encode(child.config) != snapshot:
            self.invalidate()
            raise RuntimeRefused('execution_profiles_changed', 409)
        try:
            validate_execution_bindings(decode(snapshot), copied)
        except ProtectedError:
            self.invalidate()
            raise
        except (OSError, KeyError, TypeError, ValueError):
            self.invalidate()
            raise RuntimeRefused('execution_profiles_changed', 409) from None
        return await child.run(copied, gate)

    def close(self):
        """Service has already cancelled/awaited workers; close only owned DBs."""
        if self._closed:
            return
        self._closed, self._catalog_valid = True, False
        for child in self._children.values():
            child.fence.close()
