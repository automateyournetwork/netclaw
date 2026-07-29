"""Tests for utils/rate_limiter.py (sliding window + Retry-After parsing)."""

import time

import pytest

from utils.rate_limiter import SlidingWindowRateLimiter, parse_retry_after


async def test_sliding_window_limits_calls():
    """Three acquire() calls with max_calls=2, period=0.2 should take >=0.2s."""
    limiter = SlidingWindowRateLimiter(max_calls=2, period=0.2)
    start = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    # Third call must wait for the window to slide
    await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.18, f"Expected >=0.18s, got {elapsed:.3f}s"


async def test_sliding_window_two_calls_are_fast():
    """Two acquire() calls within max_calls=2 should complete quickly."""
    limiter = SlidingWindowRateLimiter(max_calls=2, period=1.0)
    start = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.5, f"Expected <0.5s for 2 calls, got {elapsed:.3f}s"


def test_parse_retry_after_valid():
    assert parse_retry_after({"Retry-After": "5"}) == 5


def test_parse_retry_after_missing():
    assert parse_retry_after({}) is None


def test_parse_retry_after_unparsable():
    assert parse_retry_after({"Retry-After": "abc"}) is None


def test_parse_retry_after_zero():
    assert parse_retry_after({"Retry-After": "0"}) == 0


def test_parse_retry_after_case_insensitive_header():
    """Both header spellings resolve.

    A plain ``dict(response.headers)`` lowercases header names, so the helper
    must not depend on the canonical capitalization.
    """
    assert parse_retry_after({"Retry-After": "10"}) == 10
    assert parse_retry_after({"retry-after": "10"}) == 10
