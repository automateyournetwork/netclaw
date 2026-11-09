"""Spec 182: the Border asks its members for their catalogs concurrently (live finding on the 3-region cluster:
sequential asks grew with member count and WAN distance and exceeded the far follower's budget)."""
import asyncio
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'mcp-servers/protocol-mcp'))

from bgp.federation import protected_contract as c  # noqa: E402
from bgp.federation.ha import border as border_module  # noqa: E402


def make(delays, failing=()):
    ops = object.__new__(border_module.ClusterBorderOperations)
    channels = {}
    for index, delay in enumerate(delays):
        binding = {'member_id': f'm{index}', 'installation_id': f'i{index}'}
        channels[binding['member_id']] = SimpleNamespace(protected_peer_binding=binding, delay=delay)
    ops.member_channels = channels
    ops.manifest = SimpleNamespace(audience={'cluster_id': 'c', 'generation': 'g'})
    ops.node = SimpleNamespace(node_id='n', authority=SimpleNamespace(epoch=7))

    async def send(binding, method, params):
        channel = channels[binding['member_id']]
        await asyncio.sleep(channel.delay)
        if binding['member_id'] in failing:
            raise RuntimeError('member down')
        return {'member': binding}
    ops._send = send
    return ops


def test_catalog_latency_is_the_slowest_member_not_the_sum(monkeypatch):
    monkeypatch.setattr(c, 'validate_catalog_entry', lambda entry: None)
    ops = make([0.3, 0.3, 0.3])
    started = time.monotonic()
    result = asyncio.run(ops._local_catalog({'auth_context': {}}) if False else _call(ops))
    assert time.monotonic() - started < 0.7  # sequential would be ~0.9 s
    assert [m['member']['member_id'] for m in result['members']] == ['m0', 'm1', 'm2']


def test_failed_member_is_skipped_and_order_is_stable(monkeypatch):
    monkeypatch.setattr(c, 'validate_catalog_entry', lambda entry: None)
    ops = make([0.05, 0.01, 0.02], failing={'m1'})
    result = asyncio.run(_call(ops))
    assert [m['member']['member_id'] for m in result['members']] == ['m0', 'm2']


async def _call(ops):
    monkey_exact = c.exact
    c.exact = lambda params, fields: None
    try:
        return await ops._local_catalog({'auth_context': {}})
    finally:
        c.exact = monkey_exact
