"""Rate limiting and caching, proven from an observed request timeline.

Spec 081, SC-016a/SC-017a/SC-017b, FR-023/023a/023b/026.

**No external network.** The client's HTTP call is monkeypatched with a stub that
records the wall-clock moment of every request, so the assertion is about the
*timeline the limiter produces*, not about a remote service's behaviour.

SC-016a demands exactly this: the limit is asserted from an observed timeline
rather than by reading the code. A rate limiter that is correct by inspection and
wrong under concurrency is the normal failure mode.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "bgp-intel-mcp"))

import http_client  # noqa: E402
from http_client import PoliteClient  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class _StubAsyncClient:
    """Records (source-ish url, start, end) for every request."""

    timeline: list[tuple[str, float, float]] = []
    concurrent_now = 0
    max_concurrent = 0

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None, headers=None):
        cls = type(self)
        cls.concurrent_now += 1
        cls.max_concurrent = max(cls.max_concurrent, cls.concurrent_now)
        start = time.monotonic()
        # A real request takes time; without this the limiter's spacing would be
        # the only thing separating calls and overlap would be undetectable.
        await asyncio.sleep(0.02)
        end = time.monotonic()
        cls.concurrent_now -= 1
        cls.timeline.append((url, start, end))
        return _Resp({"ok": True, "url": url})


def _install_stub() -> None:
    _StubAsyncClient.timeline = []
    _StubAsyncClient.max_concurrent = 0
    _StubAsyncClient.concurrent_now = 0
    http_client.httpx.AsyncClient = _StubAsyncClient  # type: ignore[assignment]


def test_requests_to_one_source_are_never_concurrent() -> None:
    """FR-023a. The rule most likely to be broken by a later 'make it faster'
    change, which is why it is tested rather than documented."""
    _install_stub()
    client = PoliteClient()

    async def run():
        await asyncio.gather(*[
            client.get_json("rpki", f"https://example.test/{i}") for i in range(6)
        ])

    asyncio.run(run())
    check("6 requests were made", len(_StubAsyncClient.timeline) == 6,
          str(len(_StubAsyncClient.timeline)))
    check("max concurrency to one source is 1",
          _StubAsyncClient.max_concurrent == 1,
          f"observed {_StubAsyncClient.max_concurrent}")

    # No two intervals overlap.
    spans = sorted((s, e) for _, s, e in _StubAsyncClient.timeline)
    overlaps = sum(1 for i in range(1, len(spans)) if spans[i][0] < spans[i - 1][1])
    check("no overlapping request intervals", overlaps == 0, f"{overlaps} overlaps")


def test_no_one_second_window_exceeds_the_ceiling() -> None:
    """FR-023, asserted as the actual invariant: **no sliding one-second window
    contains more than 4 requests to a source.**

    Note what is deliberately NOT asserted: `total_requests / total_elapsed`. That
    average is not the guarantee and is misleading at the start of a burst — with a
    correct sliding window, requests 1-4 fire immediately and the 5th waits for the
    1st to age out, giving an *average* near 4.9/s while every actual window holds
    exactly 4. An earlier version of this test asserted the average, failed, and
    the real finding was that the limiter enforced only a minimum *gap* — which
    bounds the rate asymptotically but lets five requests land inside one second.
    The limiter now enforces the window; this asserts that directly.
    """
    _install_stub()
    client = PoliteClient()

    async def run():
        for i in range(9):
            await client.get_json("routing", f"https://example.test/r{i}")

    asyncio.run(run())
    starts = sorted(s for _, s, _ in _StubAsyncClient.timeline)
    check("9 requests were made", len(starts) == 9, str(len(starts)))

    worst = 0
    worst_at = 0.0
    for origin in starts:
        in_window = sum(1 for s in starts if origin <= s < origin + 1.0)
        if in_window > worst:
            worst, worst_at = in_window, origin
    check("no 1s window holds more than 4 requests", worst <= 4,
          f"found {worst} requests within one second starting at t={worst_at:.3f}")

    # Sanity: the ceiling is actually being reached, so the test is not passing
    # merely because everything was slow.
    check("the ceiling is genuinely exercised", worst == 4, f"observed max {worst}")


def test_different_sources_are_not_serialised_against_each_other() -> None:
    """The limit is per source. Serialising *everything* globally would be
    needlessly slow without being any politer to a given service."""
    _install_stub()
    client = PoliteClient()

    async def run():
        await asyncio.gather(
            client.get_json("rpki", "https://example.test/a"),
            client.get_json("rdap", "https://example.test/b"),
            client.get_json("peeringdb", "https://example.test/c"),
        )

    t0 = time.monotonic()
    asyncio.run(run())
    elapsed = time.monotonic() - t0
    check("three different sources proceed in parallel", elapsed < 0.5,
          f"{elapsed:.2f}s — sources appear globally serialised")


def test_cache_hit_avoids_a_request_and_reports_age() -> None:
    """FR-026/026b."""
    _install_stub()
    client = PoliteClient()

    async def run():
        a = await client.get_json("rdap", "https://example.test/same")
        b = await client.get_json("rdap", "https://example.test/same")
        return a, b

    (_, c1, _), (_, c2, age2) = asyncio.run(run())
    check("first call is not cached", c1 is False)
    check("second call is cached", c2 is True)
    check("cached call reports an age", age2 is not None and age2 >= 0, str(age2))
    check("only one request actually left", len(_StubAsyncClient.timeline) == 1,
          str(len(_StubAsyncClient.timeline)))


def test_fresh_bypasses_the_cache() -> None:
    """FR-026c. For when a ROA was just published and the 5-minute TTL is the only
    thing between the operator and the truth."""
    _install_stub()
    client = PoliteClient()

    async def run():
        await client.get_json("rpki", "https://example.test/x")
        await client.get_json("rpki", "https://example.test/x", fresh=True)

    asyncio.run(run())
    check("fresh=True issued a second request", len(_StubAsyncClient.timeline) == 2,
          str(len(_StubAsyncClient.timeline)))


def test_ttls_are_per_source() -> None:
    """FR-026/SC-017b. A single TTL would be wrong for at least one source: a ROA
    can appear in minutes, an RIR allocation changes in months."""
    ttl = http_client.TTL_SECONDS
    check("RPKI TTL is 5 minutes", ttl["rpki"] == 300.0, str(ttl.get("rpki")))
    check("RDAP TTL is 24 hours", ttl["rdap"] == 86400.0, str(ttl.get("rdap")))
    check("RPKI expires far sooner than RDAP", ttl["rpki"] < ttl["rdap"] / 100)
    check("routing sits between them", ttl["rpki"] < ttl["routing"] < ttl["rdap"])


def test_max_rps_cannot_be_raised() -> None:
    """An operator may be more polite; raising the ceiling is not supported."""
    os.environ["BGP_INTEL_MAX_RPS"] = "100"
    check("attempt to raise is clamped", http_client._max_rps() == 4.0,
          str(http_client._max_rps()))
    os.environ["BGP_INTEL_MAX_RPS"] = "1"
    check("lowering is honoured", http_client._max_rps() == 1.0)
    del os.environ["BGP_INTEL_MAX_RPS"]


def main() -> int:
    print("rate limit + cache contract tests (stubbed transport, no external network)")
    for fn in (
        test_requests_to_one_source_are_never_concurrent,
        test_no_one_second_window_exceeds_the_ceiling,
        test_different_sources_are_not_serialised_against_each_other,
        test_cache_hit_avoids_a_request_and_reports_age,
        test_fresh_bypasses_the_cache,
        test_ttls_are_per_source,
        test_max_rps_cannot_be_raised,
    ):
        print(f"\n{fn.__name__}")
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all rate-limit and cache contract tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
