"""Cross-process ownership for the shared local RAG indexes (Linux/macOS/WSL)."""
import fcntl
import os
import stat
import threading
from contextlib import contextmanager
from pathlib import Path


class StoreLock:
    def __init__(self, directory):
        self.path = Path(directory) / '.operations.lock'
        self._mutex = threading.RLock()
        self._depth = 0

    @contextmanager
    def hold(self, blocking=True):
        with self._mutex:
            if self._depth:
                self._depth += 1
                try:
                    yield True
                finally:
                    self._depth -= 1
                return
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise PermissionError('RAG operation lock must be private and locally owned')
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
                except BlockingIOError:
                    yield False
                    return
                self._depth = 1
                try:
                    yield True
                finally:
                    self._depth = 0
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
