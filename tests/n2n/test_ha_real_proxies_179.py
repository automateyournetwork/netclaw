"""Source-only tests for the REAL partition forwarders: local echo servers, loopback, no Docker/model."""
import asyncio
import json
from pathlib import Path
import socket
import sys
import threading
import time

import pytest

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
from labs.ha import real_proxies as proxies


def free_ports(count):
    held = [socket.socket() for _ in range(count)]
    for s in held: s.bind(('127.0.0.1', 0))
    ports = [s.getsockname()[1] for s in held]
    for s in held: s.close()
    return ports


class Echo:
    def __init__(self):
        self.loop = asyncio.new_event_loop(); self.port = None; self.ready = threading.Event(); self.received = 0
        threading.Thread(target=self.run, daemon=True).start(); assert self.ready.wait(5)

    def run(self):
        asyncio.set_event_loop(self.loop)
        async def handle(reader, writer):
            try:
                while data := await reader.read(4096):
                    self.received += len(data); writer.write(data); await writer.drain()
            except OSError: pass
            writer.close()
        async def main():
            server = await asyncio.start_server(handle, '127.0.0.1', 0)
            self.port = server.sockets[0].getsockname()[1]; self.ready.set()
            await asyncio.Event().wait()
        self.loop.run_until_complete(main())


@pytest.fixture
def topology(tmp_path):
    tmp_path.chmod(0o700)
    echoes = [Echo() for _ in range(3)]
    ports = free_ports(9)
    spec = {'schema_version': 1, 'owner': 'netclaw-r08-test-proxies',
            'forwarders': [{'name': f'b{i}-v{k}', 'listen_port': ports[i * 3 + k], 'target_port': echoes[k].port}
                           for i in range(3) for k in range(3)]}
    control = proxies.init_control(tmp_path / 'control', spec)
    proxies.start(control)
    yield control, ports, echoes
    try: proxies.stop(control)
    except (proxies.ProxyRefused, OSError): pass


def roundtrip(port, payload=b'ping', timeout=1.0):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=timeout) as s:
            s.settimeout(timeout); s.sendall(payload)
            data = s.recv(4096)
            return data
    except (OSError, socket.timeout):
        return None


def fresh(control):
    time.sleep(.2)        # metrics.json is republished every 50 ms
    return proxies.status(control)


def apply(control, policy):
    return proxies.wait_applied(control, policy['generation'])


def test_pass_by_default_counts_bytes_and_records_owner(topology):
    control, ports, _ = topology
    assert roundtrip(ports[0], b'hello') == b'hello'
    metrics = fresh(control)
    row = metrics['forwarders']['b0-v0']
    assert row['connections_accepted'] >= 1 and row['request']['forwarded_bytes'] == 5 and row['response']['forwarded_bytes'] == 5
    owner = json.loads((control / 'owner.json').read_text())
    assert owner['owner'] == 'netclaw-r08-test-proxies' and owner['start'] and oct((control / 'owner.json').stat().st_mode & 0o777) == '0o600'


def test_cut_blocks_new_and_severs_existing_only_for_selected_border_then_heal(topology):
    control, ports, _ = topology
    held = socket.create_connection(('127.0.0.1', ports[0]), timeout=1); held.settimeout(2)
    held.sendall(b'a'); assert held.recv(10) == b'a'
    other = socket.create_connection(('127.0.0.1', ports[3]), timeout=1); other.settimeout(2)
    other.sendall(b'x'); assert other.recv(10) == b'x'
    policy = proxies.cut(control, proxies.select(proxies.load_spec(control), border=0)); apply(control, policy)
    assert held.recv(10) == b''                      # existing relay severed
    assert roundtrip(ports[0]) in (None, b'')        # new connection refused
    assert roundtrip(ports[2]) in (None, b'')
    assert roundtrip(ports[3]) == b'ping'            # other Border untouched
    other.sendall(b'y'); assert other.recv(10) == b'y'
    metrics = fresh(control)['forwarders']['b0-v0']
    assert metrics['connections_severed'] >= 1 and metrics['connections_refused'] >= 1
    policy = proxies.heal(control, proxies.select(proxies.load_spec(control), border=0)); apply(control, policy)
    assert roundtrip(ports[0]) == b'ping' and roundtrip(ports[2]) == b'ping'
    held.close(); other.close()


@pytest.mark.parametrize('direction', ['request', 'response'])
def test_one_way_cut_blackholes_only_that_direction(topology, direction):
    control, ports, echoes = topology
    before = echoes[0].received
    policy = proxies.cut(control, ['b1-v0'], direction); apply(control, policy)
    assert roundtrip(ports[3], timeout=.5) is None
    time.sleep(.1)
    assert (echoes[0].received > before) == (direction == 'response')   # request cut: upstream sees nothing
    row = fresh(control)['forwarders']['b1-v0'][direction]
    assert row['dropped_bytes'] == 4
    assert roundtrip(ports[0]) == b'ping'
    apply(control, proxies.heal(control, ['b1-v0']))
    assert roundtrip(ports[3]) == b'ping'


def test_delay_adds_latency_per_chunk_and_heal_clears_it(topology):
    control, ports, _ = topology
    apply(control, proxies.delay(control, ['b2-v1'], 300))
    start = time.monotonic(); assert roundtrip(ports[7], timeout=3) == b'ping'
    assert time.monotonic() - start >= .55          # one delay each way
    apply(control, proxies.heal(control, ['b2-v1']))
    start = time.monotonic(); assert roundtrip(ports[7]) == b'ping'
    assert time.monotonic() - start < .3


def test_policy_is_validated_and_monotone(topology):
    control, _, _ = topology
    spec = proxies.load_spec(control)
    with pytest.raises(proxies.ProxyRefused): proxies.delay(control, ['b0-v0'], proxies.MAX_DELAY_MS + 1)
    with pytest.raises(proxies.ProxyRefused): proxies.select(spec, forwarders=['b9-v9'])
    with pytest.raises(proxies.ProxyRefused): proxies.select(spec)
    before = json.loads((control / 'policy.json').read_text())['generation']
    apply(control, proxies.cut(control, ['b0-v0']))
    assert json.loads((control / 'policy.json').read_text())['generation'] == before + 1


def test_spec_refuses_non_owned_names_loops_and_bad_ports():
    base = {'schema_version': 1, 'owner': 'netclaw-r08-x', 'forwarders': [{'name': 'b0-v0', 'listen_port': 40000, 'target_port': 40001}]}
    proxies.validate_spec(base)
    for mutate in (lambda s: s.update(owner='other'), lambda s: s['forwarders'][0].update(listen_port=80),
                   lambda s: s['forwarders'][0].update(name='B0'), lambda s: s['forwarders'].append(
                       {'name': 'b0-v1', 'listen_port': 40001, 'target_port': 40002}),
                   lambda s: s['forwarders'][0].update(target_port=40000), lambda s: s.update(extra=1)):
        value = json.loads(json.dumps(base)); mutate(value)
        with pytest.raises(proxies.ProxyRefused): proxies.validate_spec(value)


def test_stop_is_pid_and_start_time_bound_and_final_evidence_is_kept(tmp_path):
    tmp_path.chmod(0o700)
    echo = Echo(); port = free_ports(1)[0]
    control = proxies.init_control(tmp_path / 'c', {'schema_version': 1, 'owner': 'netclaw-r08-stop',
        'forwarders': [{'name': 'b0-v0', 'listen_port': port, 'target_port': echo.port}]})
    proxies.start(control); assert roundtrip(port) == b'ping'
    owner = json.loads((control / 'owner.json').read_text())
    forged = dict(owner, start='Thu Jan  1 00:00:00 1970')
    (control / 'owner.json').write_text(json.dumps(forged))
    with pytest.raises(proxies.ProxyRefused, match='owned_process_changed'): proxies.stop(control)
    (control / 'owner.json').write_text(json.dumps(owner))
    assert proxies.stop(control)['stopped']
    final = json.loads((control / 'final-metrics.json').read_text())
    assert final['forwarders']['b0-v0']['request']['forwarded_bytes'] == 4
    assert (control / 'stopped.json').exists() and (control / 'events.jsonl').exists()
    with pytest.raises(proxies.ProxyRefused): proxies.stop(control)
    assert roundtrip(port, timeout=.3) in (None, b'')
