#!/usr/bin/env python3
"""Offline tests for the cache, rate budget, and outcome typing.

Spec 078 T024 and the outcome half of T018. No network anywhere in this file — the
API client is replaced by a counting stub, so the default suite never spends any of
the 30 calls/minute (T004, T040).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

SERVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "..", "mcp-servers", "cisco-psirt-mcp")
sys.path.insert(0, SERVER_DIR)

# Point the cache at a throwaway directory BEFORE importing the server, so no test
# can touch a real operator's ~/.openclaw/cisco-psirt.
_TMP = tempfile.mkdtemp(prefix="psirt-test-")
os.environ["CISCO_PSIRT_CACHE_DIR"] = _TMP
os.environ.setdefault("CISCO_CLIENT_ID", "test-id-not-a-real-credential")
os.environ.setdefault("CISCO_CLIENT_SECRET", "test-secret-not-a-real-credential")

from cache import AdvisoryCache, key_to_filename  # noqa: E402
from ratelimit import RateLimiter, dedupe  # noqa: E402

import server  # noqa: E402

PASS = FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        print(f"  ok   {label}")
        PASS += 1
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1


# --- a counting stand-in for the API ------------------------------------------

class StubClient:
    """Records every call so tests can assert on call COUNT, which is the whole
    point of de-duplication and caching."""

    def __init__(self, advisories=None):
        self.calls: list[tuple] = []
        self.advisories = advisories if advisories is not None else [
            {"advisory_id": "cisco-sa-test-AAAA", "severity": "High",
             "cvss_base_score": "7.5", "cves": ["CVE-2026-00001"]}]

    def by_os_version(self, ostype, version):
        self.calls.append((ostype, version))
        return list(self.advisories), f"OSType/{ostype}"

    def by_cve(self, cve):
        self.calls.append(("cve", cve))
        return list(self.advisories), f"cve/{cve}"


def fresh_server(advisories=None, tmp=None):
    """Rebind the server's module-level singletons to test doubles."""
    directory = Path(tmp or tempfile.mkdtemp(prefix="psirt-test-"))
    server._cache = AdvisoryCache(directory=directory, ttl=21600)
    server._limiter = RateLimiter()
    stub = StubClient(advisories)
    server._client = stub
    return stub, directory


print("### FR-012: cache round trip ###")
stub, cdir = fresh_server()
first = server.check_version("iosxe", "17.3.1")
check("first lookup is a miss", first["cache"] == "miss", first["cache"])
check("first lookup called the API", len(stub.calls) == 1, str(stub.calls))
second = server.check_version("iosxe", "17.3.1")
check("repeat lookup is a hit", second["cache"] == "hit", second["cache"])
check("repeat lookup did NOT call the API", len(stub.calls) == 1, str(stub.calls))
check("hit reports cache_age_seconds", "cache_age_seconds" in second)
check("hit returns the same advisories",
      second["advisories"] == first["advisories"])

print("\n### FR-012: the cache survives a restart ###")
stub2, _ = fresh_server(tmp=cdir)          # new client + limiter, same directory
after_restart = server.check_version("iosxe", "17.3.1")
check("served from disk after restart", after_restart["cache"] == "hit",
      after_restart["cache"])
check("no API call after restart", len(stub2.calls) == 0, str(stub2.calls))

print("\n### FR-012a/c: refresh bypasses AND says so ###")
refreshed = server.check_version("iosxe", "17.3.1", refresh=True)
check("refresh reports cache=refreshed", refreshed["cache"] == "refreshed",
      refreshed["cache"])
check("refresh did call the API", len(stub2.calls) == 1, str(stub2.calls))

print("\n### FR-012b: an expired entry is a miss ###")
stub3, cdir3 = fresh_server()
server.check_version("iosxe", "17.3.1")
stale = Path(cdir3) / key_to_filename("iosxe", "17.3.1")
data = json.loads(stale.read_text())
data["fetched_at"] = time.time() - 21601        # one second past the 6h default
stale.write_text(json.dumps(data))
expired = server.check_version("iosxe", "17.3.1")
check("expired entry is a miss", expired["cache"] == "miss", expired["cache"])
check("expired entry triggered a refetch", len(stub3.calls) == 2, str(stub3.calls))

print("\n### A corrupt cache file must never fail a lookup ###")
stub4, cdir4 = fresh_server()
(Path(cdir4) / key_to_filename("iosxe", "17.3.1")).write_text("{not json")
corrupt = server.check_version("iosxe", "17.3.1")
check("corrupt entry falls back to a live call", corrupt["cache"] == "miss")
check("corrupt entry still returns advisories",
      corrupt["outcome"] == "advisories_found")

print("\n### Cache keys cannot escape the cache directory ###")
name = key_to_filename("iosxe", "../../../etc/passwd")
check("path traversal is neutralised", "/" not in name and ".." not in name, name)

print("\n### FR-013: de-duplication before anything else (SC-004/004a) ###")
groups = dedupe([("iosxe", "17.3.1"), ("iosxe", "17.3.1"), ("ios", "15.2(4)E")])
check("dedupe collapses duplicates", len(groups) == 2, str(groups))
check("dedupe records every position",
      groups[("iosxe", "17.3.1")] == [0, 1], str(groups))

# SC-004: 60 devices, 12 distinct versions -> 12 lookups, not 60.
stub5, _ = fresh_server()
fleet = [{"name": f"dev{i:02d}", "ostype": "iosxe", "version": f"17.{i % 12}.1"}
         for i in range(60)]
sweep = server.check_versions(fleet)
check("60 devices produce 60 results", len(sweep["devices"]) == 60,
      str(len(sweep["devices"])))
check("12 distinct versions reported", sweep["distinct_versions"] == 12,
      str(sweep["distinct_versions"]))
check("only 12 API calls made, not 60", len(stub5.calls) == 12, str(len(stub5.calls)))
check("saving is reported", sweep["api_calls_saved_by_dedup"] == 48,
      str(sweep["api_calls_saved_by_dedup"]))
check("every device names itself",
      all(d.get("device") for d in sweep["devices"]))
check("sweep warns that none_published is not 'secure'",
      "not a device confirmed secure" in sweep["note"])

print("\n### FR-011: one device's failure does not abort the sweep ###")
stub6, _ = fresh_server()
mixed = [{"name": "good", "ostype": "iosxe", "version": "17.3.1"},
         {"name": "unparseable", "ostype": "iosxe", "version": "garbage"},
         {"name": "wrongos", "ostype": "iosxr", "version": "7.5.2"},
         {"name": "alsogood", "ostype": "ios", "version": "15.2(4)E"}]
result = server.check_versions(mixed)
outcomes = {d["device"]: d["outcome"] for d in result["devices"]}
check("good device answered", outcomes["good"] == "advisories_found", str(outcomes))
check("unparseable device -> normalisation_failed",
      outcomes["unparseable"] == "normalisation_failed", str(outcomes))
check("iosxr device -> unsupported_ostype",
      outcomes["wrongos"] == "unsupported_ostype", str(outcomes))
check("the fourth device still ran",
      outcomes["alsogood"] == "advisories_found", str(outcomes))

print("\n### The five outcomes, and the distinction that matters (SC-006/008b) ###")
stub7, _ = fresh_server(advisories=[])          # Cisco published nothing
empty = server.check_version("iosxe", "17.3.1")
check("empty list -> none_published", empty["outcome"] == "none_published",
      empty["outcome"])
check("none_published carries a caveat", bool(empty["caveat"]))
check("caveat denies 'secure' explicitly",
      "NOT a statement that the device is secure" in empty["caveat"],
      empty["caveat"])

bad = server.check_version("iosxe", "17.3(1)garbage!!")
check("unparseable -> normalisation_failed",
      bad["outcome"] == "normalisation_failed", bad["outcome"])
check("normalisation_failed has NO version_normalised",
      bad["version_normalised"] is None)
check("normalisation_failed says nothing was checked",
      "NOTHING WAS CHECKED" in (bad["caveat"] or ""), str(bad.get("caveat")))
check("normalisation_failed is NOT none_published",
      bad["outcome"] != "none_published")
check("normalisation_failed suggests the right format",
      bad.get("expected_format") == "17.3.1", str(bad.get("expected_format")))

xr = server.check_version("iosxr", "7.5.2")
check("iosxr -> unsupported_ostype", xr["outcome"] == "unsupported_ostype")
check("iosxr lists the supported set", len(xr.get("supported_ostypes", [])) == 7)

junos = server.check_version("junos", "21.4R3")
check("non-Cisco -> unsupported_ostype (FR-010)",
      junos["outcome"] == "unsupported_ostype")
check("non-Cisco names the vendor and points at nvd-cve",
      "Juniper" in junos["caveat"] and "nvd-cve" in junos["caveat"],
      junos["caveat"])

print("\n### FR-005: every result is attributable ###")
for label, payload in [("check_version", empty), ("sweep", sweep),
                       ("unsupported", xr), ("status", None)]:
    if payload is None:
        continue
    check(f"{label} stamps server=cisco-psirt", payload["server"] == "cisco-psirt")

print("\n### FR-007 / SC-009: no credential in any output ###")
SECRETS = ["test-id-not-a-real-credential", "test-secret-not-a-real-credential"]
status = server.psirt_status()
blob = json.dumps([status, empty, bad, xr, junos, sweep, refreshed])
for secret in SECRETS:
    check(f"{secret[:12]}... absent from every result", secret not in blob)
check("status reports auth state without the token",
      "authenticated" in status and "token" not in json.dumps(status).lower()
      or "token_expires_in_seconds" in status)
check("status exposes the rate budget",
      status["rate_budget"]["per_minute"] == 30)
check("status lists supported and verified sets",
      len(status["supported_ostypes"]) == 7 and status["verified_ostypes"])
check("status declares read_only", status["read_only"] is True)
check("status records what is unavailable and why",
      "iosxr" in status["unavailable"] and "cx_cloud" in status["unavailable"])

print("\n### FR-013: the limiter paces bursts ###")
limiter = RateLimiter(per_second=5, per_minute=30)
start = time.time()
for _ in range(6):
    limiter.acquire()
elapsed = time.time() - start
check("a 6th call within one second is delayed", elapsed >= 0.9, f"{elapsed:.2f}s")
check("remaining budget decreases", limiter.calls_remaining() == 24,
      str(limiter.calls_remaining()))

print("\n### FR-006 / SC-007: a token expiring mid-operation is refreshed silently ###")
# The real risk this guards: a fleet sweep outlives the 3600s token, and an expiry
# discovered via a mid-sweep 401 turns an entirely predictable event into a partial
# failure. Tested with a counting fake in place of the token endpoint, so no live call.
from auth import REFRESH_MARGIN_S, TokenProvider  # noqa: E402

class FakeTokens(TokenProvider):
    def __init__(self):
        super().__init__("fake-id", "fake-secret")
        self.fetches = 0

    def _fetch(self):
        self.fetches += 1
        self._token = f"fake-token-{self.fetches}"
        self._expires_at = time.time() + 3600

tp = FakeTokens()
first_token = tp.bearer()
check("first bearer() acquires a token", tp.fetches == 1, str(tp.fetches))
check("second bearer() reuses it (no wasted call)",
      tp.bearer() == first_token and tp.fetches == 1, str(tp.fetches))

# Wind the clock to inside the refresh margin. The token is still technically valid,
# which is the point: renewal happens BEFORE expiry, not after a 401.
tp._expires_at = time.time() + (REFRESH_MARGIN_S - 1)
second_token = tp.bearer()
check("a token inside the margin is refreshed proactively", tp.fetches == 2,
      str(tp.fetches))
check("the refreshed token is a new one", second_token != first_token)
check("no exception surfaced to the caller", second_token.startswith("fake-token"))

# And an already-expired token still resolves rather than raising.
tp._expires_at = time.time() - 10
third = tp.bearer()
check("an expired token is replaced, not raised on", tp.fetches == 3 and bool(third))

# Genuinely unconfigured: the constructor falls back to the environment when an
# argument is empty, so the environment has to be cleared rather than overridden.
_saved = {k: os.environ.pop(k, None)
          for k in ("CISCO_CLIENT_ID", "CISCO_CLIENT_SECRET")}
unconfigured = TokenProvider()
for _k, _v in _saved.items():
    if _v is not None:
        os.environ[_k] = _v

check("missing credentials are reported by variable NAME",
      "CISCO_CLIENT_ID" in unconfigured.status()["missing_variables"])
try:
    unconfigured.bearer()
    check("unconfigured bearer() raises", False, "no exception")
except Exception as exc:
    msg = str(exc)
    check("unconfigured bearer() raises AuthError naming the variables",
          "CISCO_CLIENT_ID" in msg and "CISCO_CLIENT_SECRET" in msg)
    check("the error tells the operator where to register",
          "apiconsole.cisco.com" in msg)

print("\n### FR-018: the tool surface is read-only ###")
tools = {"check_version", "check_versions", "check_cve", "check_advisory",
         "list_recent", "psirt_status"}
exported = {name for name in dir(server) if not name.startswith("_")}
check("all six tools are present", tools <= exported, str(sorted(tools - exported)))
writes = [t for t in tools if any(w in t for w in
                                  ("set_", "write", "delete", "config", "deploy", "push"))]
check("no tool name implies a write", not writes, str(writes))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
