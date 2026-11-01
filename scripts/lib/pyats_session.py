"""Explicit, installation-bound pyATS session descriptors and HTTP authentication.

The foreground owner keeps one managed process alive across client disconnects.
No inventory/grant is restored after that process exits.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import time


def binding(env, python, upstream):
    root = env.get('NETCLAW_CHANGE_ROOT')
    if not root or not Path(root).is_absolute():
        raise ValueError('Persistent sessions require an explicit NETCLAW_CHANGE_ROOT')
    value = {'change_root': str(Path(root).resolve()), 'python': str(python.resolve()),
             'upstream': str(upstream.resolve()),
             'mode': env.get('NETCLAW_TESTBED_MODE', 'static'),
             'sources': env.get('NETCLAW_TESTBED_SOURCES', ''),
             'static': env.get('PYATS_TESTBED_PATH', '') if env.get('NETCLAW_TESTBED_MODE') != 'dynamic' else ''}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def private_parent(path):
    if not path.is_absolute() or path.parent.is_symlink():
        raise ValueError('Session file requires an absolute private directory')
    st = path.parent.stat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise ValueError('Session directory must be owned and mode 0700')


def publish(path, value):
    private_parent(path)
    # Never replace a live or stale descriptor implicitly. Each session gets a
    # new path, so an old client cannot silently adopt a restarted inventory.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())


def read(path, expected_binding):
    private_parent(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_size > 4096:
            raise ValueError('Session descriptor is not a private owned regular file')
        value = json.load(stream)
    if (value.get('schema') != 1 or value.get('binding') != expected_binding
            or not isinstance(value.get('token'), str) or not re.fullmatch(r'[a-f0-9]{64}', value['token'])
            or type(value.get('port')) is not int or not 1024 <= value['port'] <= 65535
            or type(value.get('pid')) is not int or value['pid'] <= 1
            or type(value.get('expires')) not in (int, float) or not time.time() < value['expires'] <= time.time() + 28800):
        raise ValueError('Session descriptor binding invalid or expired')
    os.kill(value['pid'], 0)
    return value


class BearerAuth:
    """ASGI boundary before the SDK, including initialize and notifications."""
    def __init__(self, app, token):
        if not re.fullmatch(r'[a-f0-9]{64}', token):
            raise ValueError('Invalid session bearer')
        self.app, self.expected = app, ('Bearer ' + token).encode()

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            values = [v for k, v in scope.get('headers', []) if k.lower() == b'authorization']
            if len(values) != 1 or not hmac.compare_digest(values[0], self.expected):
                await send({'type': 'http.response.start', 'status': 401,
                            'headers': [(b'content-type', b'application/json'), (b'cache-control', b'no-store')]})
                await send({'type': 'http.response.body', 'body': b'{"error":"unauthorized"}'})
                return
        await self.app(scope, receive, send)
