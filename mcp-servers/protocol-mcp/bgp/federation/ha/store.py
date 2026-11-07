"""Private etcd v3 coordination, with no blind retry of ambiguous mutations.

This is not an application transport. NCFED nodes alone own scoped credentials;
members and external organizations reach the existing federation execution gates.
"""
import base64
import re
import ssl
import threading
import uuid
from urllib.parse import urlsplit

import httpx

from ..protected_contract import decode, encode, ProtectedError
from .config import HAError, check

MAX_VALUE = 64 * 1024
MAX_RESPONSE = 4 * 1024 * 1024


def b64(value):
    return base64.b64encode(value).decode('ascii')


class EtcdStore:
    def __init__(self, endpoints, *, prefix, ca, certificate, private_key,
                 username, password, timeout=2.0):
        check(isinstance(prefix, str) and re.fullmatch(
            r'/netclaw/ha/[0-9a-f\-]{36}/[0-9a-f\-]{36}/', prefix), 'invalid_etcd_scope')
        try:
            check(all(str(uuid.UUID(value)) == value for value in prefix.split('/')[3:5]), 'invalid_etcd_scope')
        except ValueError:
            raise HAError('invalid_etcd_scope') from None
        check(isinstance(endpoints, list) and 1 <= len(endpoints) <= 3, 'invalid_etcd_endpoints')
        check(len(set(endpoints)) == len(endpoints), 'invalid_etcd_endpoints')
        for endpoint in endpoints:
            url = urlsplit(endpoint)
            check(url.scheme == 'https' and url.hostname and not url.username
                  and not url.password and not url.path and not url.query and not url.fragment,
                  'etcd_tls_required')
            check(url.port is not None and 0 < url.port <= 65535, 'invalid_etcd_endpoints')
        check(isinstance(username, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', username), 'etcd_user_required')
        check(isinstance(password, str) and 16 <= len(password) <= 256, 'etcd_credential_required')
        check(type(timeout) in (float, int) and 0 < timeout <= 10, 'invalid_timeout')
        context = ssl.create_default_context(cafile=str(ca))
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(str(certificate), str(private_key))
        self.client = httpx.Client(verify=context, timeout=timeout, trust_env=False,
                                  follow_redirects=False,
                                  limits=httpx.Limits(max_connections=12, max_keepalive_connections=6))
        self.endpoints, self.prefix = tuple(endpoints), prefix
        self._username, self._password = username, password
        self._token, self._index = None, 0
        self._authentication = threading.Lock()

    def close(self):
        self.client.close()

    def _key(self, key):
        check(isinstance(key, str) and len(key) <= 240
              and re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', key), 'invalid_etcd_key')
        return b64((self.prefix + key).encode())

    def _authenticate(self):
        if self._token is not None:
            return
        check(self._authentication.acquire(timeout=.25), 'etcd_authentication_busy', 503)
        try:
            if self._token is None:
                response = self._request('/v3/auth/authenticate',
                                         {'name': self._username, 'password': self._password},
                                         read_only=True, login=True)
                token = response.get('token')
                check(isinstance(token, str) and 0 < len(token) <= 16384, 'etcd_authentication_failed', 503)
                self._token = token
        finally:
            self._authentication.release()

    def _request(self, path, body, *, read_only=False, login=False):
        __tracebackhide__ = True
        if not login:
            self._authenticate()
        # A read may move to a healthy endpoint. A mutation is never resent,
        # including when the connection failed before an HTTP response arrived.
        for attempt in range(len(self.endpoints) if read_only else 1):
            index = self._index
            try:
                headers = {} if login else {'Authorization': self._token}
                with self.client.stream('POST', self.endpoints[index] + path,
                                        json=body, headers=headers) as response:
                    if response.status_code in (401, 403):
                        self._token = None
                        raise HAError('etcd_access_refused', 503)
                    if response.status_code >= 500 or response.status_code == 429:
                        if not read_only:
                            raise HAError('commit_unknown', 503)
                        self._index = (index + 1) % len(self.endpoints)
                        if attempt + 1 == len(self.endpoints):
                            raise HAError('no_quorum', 503)
                        continue
                    check(response.status_code == 200, 'etcd_request_refused', 503)
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        check(len(raw) <= MAX_RESPONSE, 'etcd_response_capacity' if read_only else 'commit_unknown', 503)
                        if path == '/v3/lease/keepalive' and b'\n' in raw:
                            raw = raw[:raw.index(b'\n')]
                            break
                    try:
                        result = decode(bytes(raw), MAX_RESPONSE)
                    except ProtectedError:
                        raise HAError('invalid_etcd_response' if read_only else 'commit_unknown', 503) from None
                    check(isinstance(result, dict) and 'error' not in result,
                          'etcd_request_refused' if read_only else 'commit_unknown', 503)
                    return result
            except httpx.HTTPError:
                self._index = (index + 1) % len(self.endpoints)
                if not read_only:
                    raise HAError('commit_unknown', 503) from None
                if attempt + 1 == len(self.endpoints):
                    raise HAError('no_quorum', 503) from None

    @staticmethod
    def _range(reply):
        try:
            rows = reply.get('kvs', [])
            check(isinstance(rows, list) and len(rows) <= 1, 'invalid_etcd_response', 503)
            if not rows:
                return None, 0
            raw = base64.b64decode(rows[0]['value'], validate=True)
            value = decode(raw, MAX_VALUE)
            revision = int(rows[0]['mod_revision'])
            check(0 < revision <= 2**53 - 1, 'invalid_etcd_response', 503)
            return value, revision
        except HAError:
            raise
        except (ProtectedError, ValueError, KeyError, TypeError):
            raise HAError('invalid_etcd_response', 503) from None

    def read(self, key):
        return self._range(self._request('/v3/kv/range',
                                        {'key': self._key(key), 'serializable': False}, read_only=True))

    def read_many(self, keys):
        check(isinstance(keys, (list, tuple)) and 1 <= len(keys) <= 16
              and len(set(keys)) == len(keys), 'invalid_read_batch')
        response = self._request('/v3/kv/txn', {
            'compare': [], 'success': [{'request_range': {'key': self._key(k), 'serializable': False}}
                                       for k in keys], 'failure': []}, read_only=True)
        try:
            rows = response['responses']
            check(isinstance(rows, list) and len(rows) == len(keys), 'invalid_etcd_response', 503)
            return {key: self._range(row['response_range']) for key, row in zip(keys, rows)}
        except (KeyError, TypeError):
            raise HAError('invalid_etcd_response', 503) from None

    def txn(self, comparisons, writes):
        check(len(comparisons) <= 32 and 1 <= len(writes) <= 16, 'transaction_capacity')
        compare, success = [], []
        for key, kind, expected in comparisons:
            row = {'key': self._key(key), 'result': 'EQUAL'}
            if kind == 'revision':
                check(type(expected) is int and 0 <= expected <= 2**53 - 1)
                row.update(target='MOD', mod_revision=str(expected))
            elif kind == 'value':
                raw = encode(expected)
                check(len(raw) <= MAX_VALUE, 'state_capacity')
                row.update(target='VALUE', value=b64(raw))
            else:
                raise HAError('invalid_comparison')
            compare.append(row)
        seen = set()
        for key, value, lease in writes:
            check(key not in seen, 'duplicate_transaction_key')
            seen.add(key)
            raw = encode(value)
            check(len(raw) <= MAX_VALUE, 'state_capacity', 503)
            put = {'key': self._key(key), 'value': b64(raw)}
            if lease is not None:
                check(key == 'leader', 'durable_record_cannot_expire')
                check(isinstance(lease, str) and re.fullmatch(r'[1-9][0-9]{0,19}', lease), 'invalid_lease')
                put['lease'] = lease
            success.append({'request_put': put})
        response = self._request('/v3/kv/txn', {'compare': compare, 'success': success, 'failure': []})
        try:
            check(type(response['succeeded']) is bool, 'invalid_etcd_response', 503)
            revision = int(response['header']['revision'])
            check(0 < revision <= 2**53 - 1, 'invalid_etcd_response', 503)
            return response['succeeded'], revision
        except (KeyError, ValueError, TypeError):
            # The mutation may have committed despite an invalid acknowledgement.
            raise HAError('commit_unknown', 503) from None

    def lease(self, ttl=12):
        check(type(ttl) is int and 6 <= ttl <= 60, 'invalid_lease')
        response = self._request('/v3/lease/grant', {'TTL': ttl})
        identifier = str(response.get('ID', ''))
        check(re.fullmatch(r'[1-9][0-9]{0,19}', identifier), 'invalid_lease', 503)
        return identifier

    def keepalive(self, lease):
        check(isinstance(lease, str) and re.fullmatch(r'[1-9][0-9]{0,19}', lease), 'invalid_lease')
        response = self._request('/v3/lease/keepalive', {'ID': lease}).get('result', {})
        try:
            check(str(response['ID']) == lease and int(response['TTL']) > 0, 'authority_expired', 503)
        except (KeyError, ValueError, TypeError):
            raise HAError('authority_expired', 503) from None

    def revoke_lease(self, lease):
        check(isinstance(lease, str) and re.fullmatch(r'[1-9][0-9]{0,19}', lease), 'invalid_lease')
        self._request('/v3/lease/revoke', {'ID': lease})
