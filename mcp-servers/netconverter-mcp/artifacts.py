"""Private, bounded artifacts. No source content is returned by metadata methods."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import stat
import uuid

MAX_BYTES = 20 * 1024 * 1024
IDENTIFIER = re.compile(r'[A-Za-z0-9_-]{1,96}\Z')


class Refused(ValueError):
    """Only fixed, non-content error codes may cross the MCP boundary."""


def identity(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise Refused('invalid_identifier')
    return value


def absolute(path):
    path = Path(path).expanduser()
    if not path.is_absolute() or '..' in path.parts:
        raise Refused('absolute_unambiguous_path_required')
    return path


@contextmanager
def directory(path, *, create=False, private=False):
    """Walk every component with directory descriptors; never resolve symlinks."""
    path = absolute(path)
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try: os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError: pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        info = os.fstat(fd)
        if private and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise Refused('private_owned_directory_required')
        yield fd
    except OSError:
        raise Refused('unsafe_or_unavailable_directory') from None
    finally:
        os.close(fd)


def read_file(path, *, limit=MAX_BYTES):
    path = absolute(path)
    try:
        with directory(path.parent) as parent:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                    before.st_uid != os.getuid() or before.st_size > limit):
                raise Refused('bounded_owned_regular_file_required')
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            if len(data) > limit or any(getattr(before,k) != getattr(after,k) for k in fields):
                raise Refused('file_changed_or_too_large')
            return data, {k.removeprefix('st_'): getattr(after,k) for k in fields}
    except OSError:
        raise Refused('unsafe_or_unavailable_file') from None


def publish_file(path, data, *, mode=0o600):
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        raise Refused('artifact_too_large')
    path = absolute(path)
    try:
        with directory(path.parent, create=True, private=True) as parent:
            fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         mode, dir_fd=parent)
            with os.fdopen(fd,'wb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.fsync(parent)
    except OSError:
        raise Refused('artifact_exists_or_publication_failed') from None


class Artifacts:
    def __init__(self, workspace, installation):
        self.workspace = absolute(workspace)
        with directory(self.workspace): pass
        self.root = self.workspace / '.netclaw-netconverter' / identity(installation)
        with directory(self.root, create=True, private=True): pass

    def path(self, value):
        raw = Path(value)
        path = absolute(raw if raw.is_absolute() else self.workspace / raw)
        try: relative = path.relative_to(self.workspace)
        except ValueError: raise Refused('path_outside_workspace') from None
        if not relative.parts or relative.parts[0] == '.netconverter':
            raise Refused('reserved_workspace_path')
        return path

    def capture(self, source, *, limit=MAX_BYTES):
        path = self.path(source)
        data, info = read_file(path,limit=min(MAX_BYTES,limit))
        frozen = self.publish(uuid.uuid4().hex, data)
        return {'path':str(path), 'sha256':frozen['sha256'], 'bytes':len(data), 'identity':info}, frozen

    def publish(self, artifact_id, data):
        path = self.root / (identity(artifact_id) + '.artifact')
        publish_file(path,data,mode=0o400)
        return {'artifact_id':artifact_id,'relative_path':str(path.relative_to(self.workspace)),
                'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}

    def verify(self, artifact):
        path = self.path(artifact['relative_path'])
        if path.parent != self.root or path.name != identity(artifact['artifact_id']) + '.artifact':
            raise Refused('artifact_not_owned')
        data,_ = read_file(path)
        if len(data) != artifact['bytes'] or hashlib.sha256(data).hexdigest() != artifact['sha256']:
            raise Refused('artifact_integrity_failure')
        return data

    def verify_source(self, source):
        data,info = read_file(self.path(source['path']))
        if info != source['identity'] or len(data) != source['bytes'] or hashlib.sha256(data).hexdigest() != source['sha256']:
            raise Refused('source_changed')
