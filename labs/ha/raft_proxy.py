"""Stdlib opaque Raft byte proxy for a fresh, owned Docker fixture only.

Run inside the pinned proxy image. /control is an owner-private mount containing
policy.json, never a network administration API. No TLS keys enter this container.
"""
import asyncio
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import time


class RaftProxy:
    def __init__(self, control):
        self.control = Path(control)
        self.tasks, self.counters, self.server = set(), {}, None
        self.policy_generation, self.policy_sha256 = 0, None

    def policy(self):
        raw = (self.control / 'policy.json').read_bytes()
        if len(raw) > 65536: raise ValueError('policy_capacity')
        value = json.loads(raw)
        if set(value) != {'schema_version', 'generation', 'owner', 'target', 'peers', 'rules'}:
            raise ValueError('invalid_policy')
        if value['schema_version'] != 1 or type(value['generation']) is not int or value['generation'] < self.policy_generation:
            raise ValueError('stale_policy')
        if value['target'] not in ('v0', 'v1', 'v2') or not value['owner'].startswith('netclaw-r08-'):
            raise ValueError('invalid_policy')
        if set(value['peers']) != set(value['rules']) or not set(value['peers']) <= {'v0', 'v1', 'v2'}:
            raise ValueError('invalid_policy')
        for name, address in value['peers'].items():
            ipaddress.IPv4Address(address)
            rule = value['rules'][name]
            if set(rule) != {'request', 'response', 'delay_ms'} or any(rule[k] not in ('pass', 'drop') for k in ('request', 'response')):
                raise ValueError('invalid_policy')
            if type(rule['delay_ms']) is not int or not 0 <= rule['delay_ms'] <= 300:
                raise ValueError('invalid_policy')
        digest = hashlib.sha256(raw).hexdigest()
        if value['generation'] == self.policy_generation and self.policy_sha256 not in (None, digest):
            raise ValueError('policy_generation_reused')
        self.policy_generation, self.policy_sha256 = value['generation'], digest
        return value

    async def copy(self, reader, writer, peer, direction):
        key = peer + '-' + direction
        counter = self.counters.setdefault(key, {'received_bytes': 0, 'forwarded_bytes': 0, 'dropped_bytes': 0})
        while data := await reader.read(16384):
            rule = self.policy()['rules'][peer]
            counter['received_bytes'] += len(data)
            if rule['delay_ms']: await asyncio.sleep(rule['delay_ms']/1000)
            if self.policy()['rules'][peer][direction] == 'drop':
                counter['dropped_bytes'] += len(data)
            else:
                writer.write(data); await writer.drain(); counter['forwarded_bytes'] += len(data)

    async def accept(self, reader, writer):
        task, upstream, copies = asyncio.current_task(), None, []
        if len(self.tasks) >= 32:
            writer.close(); return
        self.tasks.add(task)
        try:
            policy = self.policy()
            source_ip = writer.get_extra_info('peername')[0]
            names = [name for name, address in policy['peers'].items() if address == source_ip]
            if len(names) != 1: raise ValueError('unowned_raft_source')
            source = names[0]
            upstream_reader, upstream = await asyncio.wait_for(asyncio.open_connection(policy['target'], 2380), 3)
            copies = [asyncio.create_task(self.copy(reader, upstream, source, 'request')),
                      asyncio.create_task(self.copy(upstream_reader, writer, source, 'response'))]
            await asyncio.wait(copies, return_when=asyncio.FIRST_COMPLETED)
        except (OSError, ValueError, asyncio.TimeoutError):
            pass
        finally:
            for copy in copies: copy.cancel()
            if copies: await asyncio.gather(*copies, return_exceptions=True)
            for stream in (writer, upstream):
                if stream:
                    stream.close()
                    try: await stream.wait_closed()
                    except OSError: pass
            self.tasks.discard(task)

    def metrics(self):
        value = {'schema_version': 1, 'policy_generation': self.policy_generation,
                 'policy_sha256': self.policy_sha256, 'observed_at_ms': int(time.time()*1000),
                 'connections': len(self.tasks), 'directions': self.counters}
        temporary = self.control / 'metrics.next'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, self.control / 'metrics.json')

    async def run(self):
        self.policy()
        self.server = await asyncio.start_server(self.accept, '0.0.0.0', 2380)
        observed_generation = self.policy_generation
        while True:
            generation = self.policy()['generation']
            if generation != observed_generation:
                # A policy change closes only these owned relay connections so
                # corrupted TLS byte streams cannot survive a heal or new cut.
                for task in list(self.tasks): task.cancel()
                if self.tasks: await asyncio.gather(*list(self.tasks), return_exceptions=True)
                observed_generation = generation
            self.metrics(); await asyncio.sleep(.1)


if __name__ == '__main__':
    asyncio.run(RaftProxy('/control').run())
