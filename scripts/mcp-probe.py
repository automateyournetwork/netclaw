#!/usr/bin/env python3
"""Bounded, read-only stdio discovery. Never invokes a device/provider tool."""
import json
import os
import select
import signal
import subprocess
import tempfile
import time


class ProbeError(Exception):
    pass


def stop(proc):
    # Include owned bridge children; never stop an unrelated daemon.
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        # macOS can refuse killpg for an already exiting group; reap first.
        if proc.poll() is not None:
            return
        proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


def discover(command, env, cwd, timeout=20, expected=()):
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=errors, env=env, cwd=cwd, start_new_session=True, bufsize=0)
        buffer = b''
        total = 0

        def send(message):
            proc.stdin.write((json.dumps(message)+'\n').encode())

        def response(identifier):
            nonlocal buffer, total
            while time.monotonic() < deadline:
                if b'\n' not in buffer:
                    if not select.select([proc.stdout], [], [], max(0, deadline-time.monotonic()))[0]:
                        break
                    chunk = os.read(proc.stdout.fileno(), 65536)
                    if not chunk:
                        raise ProbeError('server_closed')
                    total += len(chunk)
                    if total > 8 * 1024 * 1024:
                        raise ProbeError('response_too_large')
                    buffer += chunk
                    continue
                line, buffer = buffer.split(b'\n', 1)
                try:
                    data = json.loads(line)
                except (ValueError, UnicodeError):
                    # Ignore banners, but do not confuse them with protocol success.
                    continue
                if not isinstance(data, dict) or data.get('id') != identifier:
                    continue
                if 'error' in data or not isinstance(data.get('result'), dict):
                    raise ProbeError('protocol_error')
                return data['result']
            raise ProbeError('timeout')

        try:
            send({'jsonrpc':'2.0','id':0,'method':'initialize','params':{
                'protocolVersion':'2025-06-18','capabilities':{},
                'clientInfo':{'name':'netclaw-readiness','version':'1'}}})
            init = response(0)
            if not init.get('protocolVersion') or not isinstance(init.get('capabilities'), dict):
                raise ProbeError('invalid_initialize')
            send({'jsonrpc':'2.0','method':'notifications/initialized'})
            names, cursor = set(), None
            for identifier in range(1, 21):
                send({'jsonrpc':'2.0','id':identifier,'method':'tools/list',
                      'params':{'cursor':cursor} if cursor else {}})
                result = response(identifier)
                if not isinstance(result.get('tools'), list):
                    raise ProbeError('invalid_tool_list')
                for tool in result['tools']:
                    if not isinstance(tool, dict) or not isinstance(tool.get('name'), str):
                        raise ProbeError('invalid_tool_list')
                    names.add(tool['name'])
                cursor = result.get('nextCursor')
                if not cursor:
                    break
            else:
                raise ProbeError('pagination_limit')
            if not names or not set(expected) <= names:
                raise ProbeError('expected_tools_missing')
            return {'status':'verified', 'tool_count':len(names), 'tools':sorted(names)}
        except (OSError, ProbeError) as error:
            return {'status':'failed', 'reason':str(error) if isinstance(error, ProbeError) else 'process_io_error'}
        finally:
            stop(proc)
