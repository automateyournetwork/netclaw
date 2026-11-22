"""Spec 198 live finding: member admissions go to the NEAREST authenticated Border, not the lowest node id."""
import types

from bgp.federation.ha.internal import nearest_channels


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
