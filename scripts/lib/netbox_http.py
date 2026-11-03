"""Managed NetBox MCP HTTP compatibility; protected mode never accepts caller routing.

Copied into the existing upstream package by netbox-compat.py. All MCP tool
implementations remain upstream. The policy is trusted broker startup data.
"""
import json
import hashlib
import tempfile
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
import requests

MAX_RESPONSE = 256 * 1024


def auth_header(token):
    if not isinstance(token, str) or not token or not token.isascii() or any(ord(c) < 33 or ord(c) == 127 for c in token):
        raise ValueError('netbox_token_invalid')
    if token.startswith('nbt_'):
        if not re.fullmatch(r'nbt_[A-Za-z0-9]+\.[A-Za-z0-9]+', token):
            raise ValueError('netbox_token_invalid')
        return 'Bearer ' + token
    return 'Token ' + token


def load_policy(filename):
    path = Path(filename)
    info = path.lstat()
    if (not path.is_absolute() or path.resolve() != path or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or not path.is_file() or info.st_size > 16384):
        raise ValueError('netbox_policy_invalid')
    policy = json.loads(path.read_text())
    if not isinstance(policy, dict): raise ValueError('netbox_policy_invalid')
    readiness = policy.get('schemaVersion') == 2
    expected = {'schemaVersion', 'url', 'params'} | ({'purpose'} if readiness else set())
    if set(policy) != expected or type(policy['schemaVersion']) is not int or policy['schemaVersion'] not in (1,2):
        raise ValueError('netbox_policy_invalid')
    url = urlsplit(policy['url'])
    if (url.scheme != 'https' or url.username or url.password or url.query or url.fragment
            or url.port not in (None, 443) or not url.hostname):
        raise ValueError('netbox_policy_invalid')
    if readiness:
        fields = {'/api/dcim/devices/':'id,name,status,site,device_type,last_updated',
                  '/api/ipam/prefixes/':'id,prefix,status,vrf,last_updated'}
        if (policy['purpose'] != 'readiness' or url.path not in fields
                or policy['params'] != {'fields':fields[url.path], 'limit':1, 'offset':0, 'ordering':'id'}
                or type(policy['params']['limit']) is not int or type(policy['params']['offset']) is not int):
            raise ValueError('netbox_policy_invalid')
    else:
        if not re.fullmatch(r'/api/(dcim/devices|ipam/prefixes)/[1-9][0-9]*/', url.path):
            raise ValueError('netbox_policy_invalid')
        if not isinstance(policy['params'], dict) or set(policy['params']) != {'fields'} or not isinstance(policy['params']['fields'], str):
            raise ValueError('netbox_policy_invalid')
    return policy


class ProtectedSession(requests.Session):
    def __init__(self, policy, token, receipt=None):
        super().__init__()
        self.trust_env = False
        self.policy = policy
        self._token = token
        self._spent = False
        self.receipt = receipt
        self.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))

    def record(self, value):
        if self.receipt is None: return
        fd, temporary = tempfile.mkstemp(prefix='.netbox-http-', dir=self.receipt.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream, sort_keys=True); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.receipt)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def request(self, method, url, **kwargs):
        if (self._spent or method.upper() != 'GET' or url != self.policy['url']
                or kwargs.get('params') != self.policy['params'] or kwargs.get('verify') is not True
                or set(kwargs) - {'params', 'verify', 'allow_redirects'}
                or kwargs.get('allow_redirects') not in (None, True, False)):
            raise ValueError('netbox_request_refused')
        self._spent = True
        response = None
        started = time.monotonic()
        receipt = {'schemaVersion':1, 'method':'GET', 'url':url, 'params':kwargs['params'],
                   'http_requests':1, 'state':'claimed', 'started_at_ms':int(time.time()*1000)}
        self.record(receipt)
        try:
            response = super().request('GET', url, params=kwargs['params'], verify=True,
                allow_redirects=False, timeout=(10, 30), stream=True)
            if response.status_code != 200:
                receipt.update(state='failed', status=response.status_code, captured_at_ms=int(time.time()*1000))
                raise ValueError('netbox_read_failed')
            if not response.headers.get('Content-Type', '').lower().startswith('application/json'):
                raise ValueError('netbox_response_invalid')
            if int(response.headers.get('Content-Length', '0')) > MAX_RESPONSE:
                raise ValueError('netbox_response_bound')
            raw = bytearray()
            for block in response.iter_content(8192):
                raw.extend(block)
                if len(raw) > MAX_RESPONSE or time.monotonic() - started > 30:
                    raise ValueError('netbox_response_bound')
            if self._token.encode() in raw:
                raise ValueError('netbox_response_invalid')
            # Validate JSON here so neither HTML nor duplicate keys can reach a model.
            def pairs(items):
                out = {}
                for key, value in items:
                    if key in out: raise ValueError('duplicate_json_key')
                    out[key] = value
                return out
            value = json.loads(bytes(raw), object_pairs_hook=pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))
            if not isinstance(value, dict): raise ValueError('netbox_response_invalid')
            receipt.update(state='finished', status=200, captured_at_ms=int(time.time()*1000),
                           response_sha256=hashlib.sha256(bytes(raw)).hexdigest())
            self.record(receipt)
            response._content = bytes(raw)
            response._content_consumed = True
            return response
        except Exception:
            receipt.update(state='failed' if receipt.get('state')=='failed' else 'unknown', error_code='netbox_read_failed_or_unknown')
            self.record(receipt)
            raise ValueError('netbox_read_failed_or_unknown') from None
        finally:
            if response is not None: response.close()


def create_session(token):
    auth_header(token)
    policy = os.environ.get('NETCLAW_NETBOX_POLICY')
    return ProtectedSession(load_policy(policy), token, Path(policy).parent / "netbox-http-receipt.json") if policy else requests.Session()
