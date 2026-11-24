"""Spec 198 live finding: member admissions go to the NEAREST authenticated Border, not the lowest node id."""
import types
import pytest

from bgp.federation.ha.internal import MemberAttachments, nearest_channels


def ch(rtt=None, trusted=True, closed=False):
    channel = types.SimpleNamespace(trusted=trusted, _closed=closed)
    if rtt is not None:
        channel.rtt_ms = rtt
    return channel


def test_nearest_measured_border_is_first_even_with_a_higher_id():
    far, near, mid = ch(240), ch(12), ch(90)
    assert nearest_channels({'a-far': far, 'z-near': near, 'm-mid': mid}) == [near, mid, far]


def test_unmeasured_channels_keep_the_previous_lowest_id_order_and_sort_last():
    unmeasured_low, unmeasured_high, measured = ch(), ch(), ch(500)
    order = nearest_channels({'a': unmeasured_low, 'b': unmeasured_high, 'c': measured})
    assert order == [measured, unmeasured_low, unmeasured_high]
    assert nearest_channels({'a': unmeasured_low, 'b': unmeasured_high}) == [unmeasured_low, unmeasured_high]


def test_equal_rtt_breaks_ties_by_node_id_and_closed_or_untrusted_are_never_chosen():
    first, second = ch(30), ch(30)
    dead, untrusted = ch(1, closed=True), ch(1, trusted=False)
    assert nearest_channels({'b': second, 'a': first, 'c': dead, 'd': untrusted}) == [first, second]
    assert nearest_channels({'c': dead, 'd': untrusted}) == []


@pytest.mark.asyncio
async def test_signed_window_wait_does_not_retry_a_lost_admission():
    calls = []
    async def lost(method, request, timeout):
        calls.append((method, request, timeout))
        raise ConnectionError('unknown admission outcome')
    async def forbidden(*args, **kwargs):
        raise AssertionError('must not retry on another Border')
    near, far = ch(12), ch(230)
    near.call, far.call = lost, forbidden
    attachments = object.__new__(MemberAttachments)
    attachments.manifest = types.SimpleNamespace(limits={'admission_ms': 9000})
    attachments.channels = {'a-far': far, 'z-near': near}
    with pytest.raises(ConnectionError, match='unknown admission'):
        await attachments.send_admission({'nonce': 'one-shot'})
    assert calls == [('execution/admission', {'nonce': 'one-shot'}, 9.0)]
