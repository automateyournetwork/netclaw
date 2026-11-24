"""Internal native lifecycle composition; not a qualified collector adapter.

Run only inside the collector's owned child/deadline boundary: native connect,
execute and disconnect may block. Synthetic tests do not qualify SSH command
emission. This module never installs an adapter marker or grants a device read.
"""
from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import stat

_spec = importlib.util.spec_from_file_location('_spec200_session_read',
    Path(__file__).with_name('native_read.py'))
read = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(read)


class SessionRefused(ValueError):
    pass


def _reserve_log(path):
    """Require an owned private parent and a new, exclusive 0600 logfile.

    The native logger reopens this pathname. The caller must exclusively own the
    private directory for the entire child lifetime; no shared writable root.
    """
    try:
        path = Path(path)
        parent = path.parent
        if (not path.is_absolute() or path != path.resolve(strict=False)
                or parent.is_symlink()):
            raise ValueError()
        descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(descriptor)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError()
            log = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                          0o600, dir_fd=descriptor)
            try:
                os.fchmod(log, 0o600)
            finally:
                os.close(log)
        finally:
            os.close(descriptor)
        return str(path)
    except Exception:
        raise SessionRefused('private_fresh_log_required') from None


@contextmanager
def connected_capture(prepared, server, command, *, timeout, source_sha256, logfile):
    """Validate → connect → single raw execute → yield for preservation → cleanup.

    Digests/prepared device/log path are operator-owned local inputs, never tool
    arguments. The caller must durably preserve yielded raw before leaving the
    context and before offline parsing. No cleanup result proves remote command
    termination. Any failure retires the attempt; never retry with a new context.
    """
    read.validate_read(server, command, source_sha256=source_sha256)
    options = prepared.connection_options(timeout)
    options = {**options, 'logfile': _reserve_log(logfile), 'log_stdout': False}
    device = prepared.device
    failure = None
    try:
        try:
            device.connect(**options)
            raw = read.capture_once(server, device, command, timeout=timeout,
                                    source_sha256=source_sha256)
        except read.ReadRefused:
            raise
        except Exception:
            raise SessionRefused('native_capture_failed') from None
        yield raw
    except BaseException as error:
        failure = error
        raise
    finally:
        # A partially established connection also requires one cleanup attempt.
        # Parent process termination remains the bound if disconnect itself hangs.
        try:
            device.disconnect()
        except Exception:
            if failure is not None:
                failure.add_note('native_disconnect_failed')
            else:
                raise SessionRefused('native_disconnect_failed') from None
