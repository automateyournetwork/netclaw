"""Fresh HA handoff to a hosted-model DefenseClaw guard on loopback (spec 182).

One request, no retry, no redirect, no proxy environment. The host and the guard
share this process's clock domain, so no cross-clock helper is needed: the single
admission handoff happens after the connection is open and immediately before the
one write. Every failure after that point is an unknown outcome and keeps the
caller's fence. The provider credential never enters this process: it reaches the
guard only through the guard's own read-only env file. Errors carry fixed codes.
Gaps (upstream target, egress filtering, confinement proof) are documented in
specs/182-multi-region-ha-borders/model-transport.md and are NOT closed here.
"""
import asyncio
from contextlib import suppress
import json
import re
import time

from ..protected_hosted import HostedRefused, validate_profile
from ..protected_runtime import RuntimeRefused, RuntimeUnknown, canonical
from .config import check
from .effect import scope

MAX_REQUEST = 13312
MAX_RESPONSE = 1048576
MAX_HEADER = 16384
CLOCK_ALLOWANCE_MS = 250
_GUARD_URL = re.compile(r'http://127\.0\.0\.1:([1-9][0-9]{0,4})')
_COUNTED = re.compile(r'(?m)^(?:.*?\s)?POST /v1/chat/completions(?:[\s?]|$)')


def _guard_port(guard_url):
    match = _GUARD_URL.fullmatch(guard_url) if isinstance(guard_url, str) else None
    if match is None or int(match.group(1)) > 65535:
        raise RuntimeRefused('hosted_guard_binding_invalid')
    return int(match.group(1))


async def _read_response(reader):
    """Bounded HTTP/1.1 read; content-length or chunked; status must be 200."""
    head = await reader.readuntil(b'\r\n\r\n')
    if len(head) > MAX_HEADER:
        raise ValueError('header_bound')
    lines = head.decode('latin-1').split('\r\n')
    parts = lines[0].split(' ', 2)
    if len(parts) < 2 or parts[1] != '200':
        raise ValueError('status')
    headers = {}
    for line in lines[1:]:
        if line:
            name, _, value = line.partition(':')
            headers[name.strip().lower()] = value.strip()
    if headers.get('transfer-encoding', '').lower() == 'chunked':
        body = bytearray()
        while True:
            size = int((await reader.readuntil(b'\r\n')).strip().split(b';')[0], 16)
            if size == 0:
                break
            if len(body) + size > MAX_RESPONSE:
                raise ValueError('response_bound')
            body.extend(await reader.readexactly(size))
            if await reader.readexactly(2) != b'\r\n':
                raise ValueError('chunk')
        return bytes(body)
    length = headers.get('content-length')
    if length is None or not length.isdigit() or int(length) > MAX_RESPONSE:
        raise ValueError('response_bound')
    return await reader.readexactly(int(length))


async def ha_hosted_model_forward(executor, payload, request, guard_url):
    """One model request; return the raw guarded response for existing validation.

    The caller validates execution bindings and completes inspect_model first.
    Only the existing consumed EffectScope may authorize this invocation.
    """
    permit = scope('model')
    profile = getattr(executor, 'hosted', None)
    check(isinstance(profile, dict), 'ha_runtime_unqualified', 503)
    try:
        validate_profile(profile)
    except HostedRefused:
        raise RuntimeRefused('hosted_profile_invalid') from None
    port = _guard_port(guard_url)
    encoded = canonical(request)
    check(len(encoded) <= MAX_REQUEST, 'model_request_bound', 503)
    token = executor.guard_token
    check(isinstance(token, str) and 1 <= len(token) <= 4096
          and all(33 <= ord(char) <= 126 for char in token), 'model_capability_invalid', 503)
    timeout = min((payload['limits']['expires_at_ms'] - int(time.time() * 1000)) / 1000,
                  payload['limits']['inference_timeout_ms'] / 1000)
    check(0 < timeout <= profile['call_timeout_seconds'], 'model_deadline_invalid', 503)
    frame = (b'POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:' + str(port).encode()
             + b'\r\nContent-Type: application/json\r\nConnection: close\r\nX-DC-Auth: ' + token.encode()
             + b'\r\nContent-Length: ' + str(len(encoded)).encode() + b'\r\n\r\n' + encoded)
    # Refuse a stale or nearly spent budget before any connection exists.
    check(CLOCK_ALLOWANCE_MS < permit.check('model'), 'admission_expired', 403)
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection('127.0.0.1', port), min(timeout, 1))
    except (OSError, asyncio.TimeoutError):
        raise RuntimeRefused('model_guard_unavailable') from None
    try:
        remaining = permit.handoff('model')
        check(type(remaining) is int and CLOCK_ALLOWANCE_MS < remaining <= 10000, 'admission_expired', 403)
        started = time.monotonic()
        try:
            writer.write(frame)

            async def exchange():
                await writer.drain()
                return await _read_response(reader)
            body = await asyncio.wait_for(exchange(), max(0.001, timeout - (time.monotonic() - started)))
            if len(body) > MAX_RESPONSE:
                raise ValueError('response_bound')
            json.loads(body)
            return body
        except asyncio.CancelledError:
            raise
        except Exception:
            # The request may have reached the provider; never retry or fabricate.
            raise RuntimeUnknown('model_handoff_unknown') from None
    finally:
        writer.close()
        with suppress(Exception):
            await asyncio.wait_for(writer.wait_closed(), 1)


def count_guard_requests(log):
    """Independent request counter: guard-ingress POSTs in the guard container's own log.

    Read by the qualification harness (`docker logs`), never by the process under test.
    """
    text = log.decode('utf-8', errors='replace') if isinstance(log, (bytes, bytearray)) else str(log)
    return len(_COUNTED.findall(text))
