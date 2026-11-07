"""Bounded HA stdio transport through the official MCP session stream seam.

The SDK's stock stdio transport queues messages to another task. That queue
cannot enforce admission freshness at the later pipe write. This adapter keeps
the official ClientSession and wire types, and writes tools/call in the calling
task immediately after the final admission check. No SDK internals are patched.
Only the explicitly qualified asyncio/POSIX runtime is supported in HA.
"""
import asyncio
from contextlib import asynccontextmanager, suppress
import json
import os
import signal

import anyio
from mcp.client.stdio import get_default_environment
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage
from pydantic import TypeAdapter

from .config import HAError, check
from .effect import scope

MAX_FRAME_BYTES = 512 * 1024
MAX_SETUP_BYTES = 16384
MAX_TOOL_BYTES = 4096
_METHODS = frozenset(('initialize', 'tools/list', 'tools/call', 'ping',
                      'notifications/initialized', 'notifications/cancelled'))
_MESSAGE = TypeAdapter(JSONRPCMessage)


class HAStdioWriter:
    """Official WriteStream implementation with no background send queue."""
    def __init__(self, stdin, *, atomic_limit):
        check(type(atomic_limit) is int and atomic_limit >= 512, 'native_pipe_unqualified', 503)
        self.stdin, self.transport = stdin, stdin.transport
        self.atomic_limit = min(atomic_limit, MAX_TOOL_BYTES)
        self.closed, self.sending, self.tool_attempted = False, False, False

    async def __aenter__(self):
        check(not self.closed, 'native_transport_closed', 503)
        return self

    async def __aexit__(self, *_):
        await self.aclose()

    async def aclose(self):
        self.closed = True
        self.stdin.close()

    async def send(self, message):
        check(not self.closed and not self.stdin.is_closing(), 'native_transport_closed', 503)
        check(not self.sending, 'native_handoff_unavailable', 503)
        self.sending = True
        try:
            check(isinstance(message, SessionMessage), 'native_message_invalid')
            # Complete serialization before checking the time. The effect scope
            # is acquired at send time, after initialize/list_tools preflight.
            serialized = message.message.model_dump_json(by_alias=True, exclude_unset=True)
            data = serialized.encode('utf-8') + b'\n'
            check(len(data) <= MAX_SETUP_BYTES, 'native_frame_bound', 503)
            body = json.loads(serialized)
            check(isinstance(body, dict), 'native_message_invalid')
            method = body.get('method')
            check(method is None or method in _METHODS, 'native_method_refused', 403)
            if method == 'tools/call':
                check(not self.tool_attempted, 'native_handoff_spent', 409)
                self.tool_attempted = True
                check(len(data) <= self.atomic_limit, 'native_frame_bound', 503)
                check(self.transport.get_write_buffer_size() == 0, 'native_handoff_unavailable', 503)
                # No await, queue or preflight lies between final freshness and
                # synchronous pipe handoff. PIPE_BUF bounds make a nonblocking
                # pipe write atomic: all bytes enter the pipe, or none do.
                scope('tool').handoff('tool')
                self.stdin.write(data)
                if self.transport.get_write_buffer_size() != 0:
                    # Full OS pipe: asyncio queued the complete atomic frame.
                    # Abort synchronously before the event loop can flush it.
                    self.closed = True
                    self.transport.abort()
                    raise HAError('native_handoff_unavailable', 503)
                return
            self.stdin.write(data)
            await asyncio.wait_for(self.stdin.drain(), 2)
        finally:
            self.sending = False


async def _read(stdout, output):
    async with output:
        try:
            while True:
                line = await stdout.readline()
                if not line:
                    return
                check(len(line) <= MAX_FRAME_BYTES and line.endswith(b'\n'), 'native_frame_bound', 503)
                try:
                    message = _MESSAGE.validate_json(line)
                except Exception:
                    raise HAError('native_message_invalid', 503) from None
                await output.send(SessionMessage(message))
        except (anyio.BrokenResourceError, anyio.ClosedResourceError):
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Never pass upstream parse text/partial payloads into diagnostics.
            error = exc if isinstance(exc, HAError) else HAError('native_frame_bound', 503)
            with suppress(anyio.BrokenResourceError, anyio.ClosedResourceError):
                await output.send(error)


def _signal_group(process, sig):
    with suppress(ProcessLookupError):
        os.killpg(process.pid, sig)


async def _stop(process, writer, reader_task, timeout):
    await writer.aclose()
    reader_task.cancel()
    await asyncio.gather(reader_task, return_exceptions=True)
    async def discard_stdout():
        while await process.stdout.read(65536):
            pass
    discard = asyncio.create_task(discard_stdout())
    try:
        try:
            await asyncio.wait_for(process.wait(), timeout)
        except asyncio.TimeoutError:
            _signal_group(process, signal.SIGTERM)
            try:
                await asyncio.wait_for(process.wait(), timeout)
            except asyncio.TimeoutError:
                _signal_group(process, signal.SIGKILL)
                await asyncio.wait_for(process.wait(), timeout)
        # A child may exit leaving descendants in its owned session. Never let
        # those keep an inherited pipe or escape this bounded invocation.
        _signal_group(process, signal.SIGKILL)
    finally:
        discard.cancel()
        await asyncio.gather(discard, return_exceptions=True)
        if not writer.transport.is_closing():
            writer.transport.abort()


@asynccontextmanager
async def ha_stdio_client(server, errlog=None, *, shutdown_seconds=1.0):
    """Yield official SessionMessage streams for one owned native invocation.

    Admission is intentionally unnecessary for initialize/list_tools. The caller
    acquires its single tool admission after those awaits and before call_tool.
    The tool stream resolves that scope only at the final write boundary.
    """
    check(os.name == 'posix' and server.encoding == 'utf-8'
          and server.encoding_error_handler == 'strict', 'native_transport_unqualified', 503)
    check(isinstance(shutdown_seconds, (int, float)) and 0 < shutdown_seconds <= 2,
          'native_shutdown_bound')
    process = await asyncio.create_subprocess_exec(server.command, *server.args,
        env=get_default_environment() | (server.env or {}), cwd=server.cwd,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL if errlog is None else errlog,
        start_new_session=True, limit=MAX_FRAME_BYTES)
    writer, reader_task = None, None
    output, reader = anyio.create_memory_object_stream(0)
    try:
        pipe = process.stdin.transport.get_extra_info('pipe')
        atomic_limit = os.fpathconf(pipe.fileno(), 'PC_PIPE_BUF')
        writer = HAStdioWriter(process.stdin, atomic_limit=atomic_limit)
        reader_task = asyncio.create_task(_read(process.stdout, output))
        yield reader, writer
    finally:
        # Also cover transport setup failures after successful child creation.
        if writer is None:
            writer = HAStdioWriter(process.stdin, atomic_limit=512)
        if reader_task is None:
            reader_task = asyncio.create_task(asyncio.sleep(0))
        cleanup = asyncio.create_task(_stop(process, writer, reader_task, shutdown_seconds))
        cancelled = None
        with anyio.CancelScope(shield=True):
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError as exc:
                    cancelled = exc
            cleanup.result()
            await output.aclose()
            await reader.aclose()
        if cancelled is not None:
            raise cancelled
