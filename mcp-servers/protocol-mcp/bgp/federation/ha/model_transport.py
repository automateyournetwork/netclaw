"""Fresh HA model handoff through an owned, unpatched guard namespace helper.

The host and Linux helper do not share a monotonic clock origin. READY precedes
the host's input write; the helper's entire elapsed READY-to-HTTP interval must
fit the host's remaining admission budget minus a conservative clock allowance.
This double-counts part of the transfer and cannot extend the original permit.
No helper/SDK/DefenseClaw retry, new grant or member consensus access is added.
"""
import asyncio
from contextlib import suppress
import os
import signal
import time

import anyio

from ..protected_runtime import RuntimeRefused, RuntimeUnknown, canonical
from .config import check
from .effect import scope

READY = b'NETCLAW_HA_MODEL_READY_V1\n'
MAX_INPUT = 32768
MAX_REQUEST = 13312
MAX_RESPONSE = 1048576
CLOCK_ALLOWANCE_MS = 250

# Passed as the pinned python -c source to the existing owned Linux container.
# Its capability arrives only on stdin. No model/guard port is published and no
# extra image, source mount or DefenseClaw modification is needed.
MODEL_HELPER = r'''import http.client,json,os,select,signal,socket,sys,time
MAX_INPUT=32768
MAX_REQUEST=13312
MAX_RESPONSE=1048576
def _mono():
 return time.clock_gettime(time.CLOCK_BOOTTIME) if hasattr(time,'CLOCK_BOOTTIME') else time.monotonic()
def _wall():return time.time()
def _deadline(*unused):raise TimeoutError('completion_deadline')
def _fresh(start,budget):
 elapsed=(_mono()-start[0])*1000
 wall=(_wall()-start[1])*1000
 if type(budget) is not int or not 0<budget<=3000 or elapsed<0 or elapsed>budget or abs(wall-elapsed)>250:
  raise ValueError('admission_expired_or_clock_uncertain')
 return elapsed
def _read_input(start):
 raw=bytearray()
 while True:
  remaining=(3000-_fresh(start,3000))/1000
  if not select.select([0],[],[],max(0,remaining))[0]:raise ValueError('input_deadline')
  part=os.read(0,min(4096,MAX_INPUT+1-len(raw)))
  if not part:break
  raw.extend(part)
  if len(raw)>MAX_INPUT:raise ValueError('input_bound')
 return bytes(raw)
def _run():
 connection=socket.create_connection(('127.0.0.1',4000),timeout=1)
 try:
  connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
  start=(_mono(),_wall())
  sys.stdout.buffer.write(b'NETCLAW_HA_MODEL_READY_V1\n');sys.stdout.buffer.flush()
  body=json.loads(_read_input(start))
  if set(body)!={'request','guard_token','admission_ms','completion_ms'}:raise ValueError('input_fields')
  if type(body['admission_ms']) is not int or not 0<body['admission_ms']<=2750:raise ValueError('admission_bound')
  if type(body['completion_ms']) is not int or not 0<body['completion_ms']<=60000:raise ValueError('completion_bound')
  token=body['guard_token']
  if not isinstance(token,str) or not 1<=len(token)<=4096 or any(not 33<=ord(c)<=126 for c in token):raise ValueError('token_bound')
  data=json.dumps(body['request'],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
  if len(data)>MAX_REQUEST:raise ValueError('request_bound')
  frame=(b'POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:4000\r\n'
   b'Content-Type: application/json\r\nConnection: close\r\nX-DC-Auth: '+token.encode()+
   b'\r\nX-DC-Target-URL: http://127.0.0.1:11434\r\nContent-Length: '+str(len(data)).encode()+b'\r\n\r\n'+data)
  connection.setblocking(False)
  # A single wall-time alarm also bounds header/body reads: socket timeouts
  # alone would restart on every trickled byte and could exceed the deadline.
  signal.signal(signal.SIGALRM,_deadline)
  completion=(body['completion_ms']-_fresh(start,body['admission_ms']))/1000
  if completion<=0:raise ValueError('completion_expired')
  signal.setitimer(signal.ITIMER_REAL,completion)
  # Serialization and connection setup are complete. This is the last check
  # before one nonblocking socket send; partial/blocked writes never retry.
  _fresh(start,body['admission_ms'])
  if connection.send(frame)!=len(frame):raise ValueError('partial_handoff_unknown')
  connection.settimeout(completion)
  response=http.client.HTTPResponse(connection,method='POST');response.begin()
  if response.status!=200:raise ValueError('guard_status')
  result=response.read(MAX_RESPONSE+1)
  if len(result)>MAX_RESPONSE:raise ValueError('response_bound')
  json.loads(result)
  sys.stdout.buffer.write(result);sys.stdout.buffer.flush()
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  connection.close()
if __name__=='__main__':
 try:_run()
 except BaseException:raise SystemExit(70)
'''


async def _stop_client(process):
    # Killing the Docker client cannot prove an already handed-off inference
    # stopped. The caller retains its unknown fence; the helper has its own
    # pre-effect and completion bounds inside the owned container.
    if process.returncode is None:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    if process.stdin is not None and not process.stdin.transport.is_closing():
        process.stdin.transport.abort()
    with suppress(asyncio.TimeoutError):
        await asyncio.wait_for(process.communicate(), 2)


async def ha_model_forward(executor, payload, request, guard_url):
    """One model request; return raw guarded response for existing validation.

    The caller validates execution bindings and completes inspect_model first.
    Only the existing consumed EffectScope may authorize this invocation.
    """
    permit = scope('model')
    from ..protected_docker import _public_bytes, _docker_host
    check(os.name == 'posix' and guard_url == 'docker-exec://' + executor.ollama['model_container_id']
          + '/127.0.0.1:4000', 'ha_runtime_unqualified', 503)
    if (_public_bytes(executor.docker_config/'config.json') != b'{}'
            or _docker_host(executor.config['docker_host']) != executor.docker_host):
        raise RuntimeRefused('native_docker_configuration_changed')
    encoded_request = canonical(request)
    check(len(encoded_request) <= MAX_REQUEST, 'model_request_bound', 503)
    token = executor.guard_token
    check(isinstance(token, str) and 1 <= len(token) <= 4096
          and all(33 <= ord(char) <= 126 for char in token), 'model_capability_invalid', 503)
    suffix = b',"request":' + encoded_request + b',"guard_token":' + canonical(token)
    expires = payload['limits']['expires_at_ms']
    timeout = min((expires-int(time.time()*1000))/1000,
                  payload['limits']['inference_timeout_ms']/1000)
    check(0 < timeout <= 60, 'model_deadline_invalid', 503)
    permit.check('model')
    process = None
    try:
        async with asyncio.timeout(timeout):
            process = await asyncio.create_subprocess_exec(executor.docker, '--host', executor.docker_host,
                '--config', str(executor.docker_config), 'exec', '--interactive', '--user',
                str(executor.ollama['guard_uid']), executor.ollama['model_container_id'],
                'python3', '-c', MODEL_HELPER, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                env={'PATH':os.defpath, 'HOME':str(executor.docker_config)},
                start_new_session=True, limit=MAX_RESPONSE)
            check(await asyncio.wait_for(process.stdout.readline(), min(timeout, 2)) == READY,
                  'model_helper_unavailable', 503)
            completion_ms = min(expires-int(time.time()*1000), payload['limits']['inference_timeout_ms'])
            check(type(completion_ms) is int and 0 < completion_ms <= 60000, 'model_deadline_invalid', 503)
            # Preparing the fixed suffix precedes final freshness. The tiny
            # numeric budget prefix is formed without any await after handoff.
            packet_tail = suffix + b',"completion_ms":' + str(completion_ms).encode() + b'}'
            check(len(packet_tail)+32 <= MAX_INPUT, 'model_request_bound', 503)
            remaining = permit.handoff('model')
            check(type(remaining) is int and CLOCK_ALLOWANCE_MS < remaining <= 3000,
                  'admission_expired', 403)
            packet = b'{"admission_ms":' + str(remaining-CLOCK_ALLOWANCE_MS).encode() + packet_tail
            process.stdin.write(packet)
            process.stdin.close()
            # Docker plumbing may buffer stdin. The helper's final relative
            # clock gate rejects delayed bytes instead of turning them into a
            # later HTTP effect. No fresh claim or second write is attempted.
            output = bytearray()
            while part := await process.stdout.read(65536):
                output.extend(part)
                check(len(output) <= MAX_RESPONSE, 'model_response_bound', 503)
            check(await process.wait() == 0, 'model_handoff_unknown', 503)
            return bytes(output)
    except asyncio.CancelledError:
        raise
    except Exception:
        raise RuntimeUnknown('model_handoff_unknown') from None
    finally:
        if process is not None:
            cleanup = asyncio.create_task(_stop_client(process))
            cancelled = None
            with anyio.CancelScope(shield=True):
                while not cleanup.done():
                    try:
                        await asyncio.shield(cleanup)
                    except asyncio.CancelledError as exc:
                        cancelled = exc
                cleanup.result()
            if cancelled is not None:
                raise cancelled
