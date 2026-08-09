"""Input refusal as a disclosure control. Spec 081, SC-015, FR-028/029/030.

No network — and that is the point. The property under test is that **no request is
made**, which is only meaningful if the test itself makes none.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "bgp-intel-mcp"))

import validate  # noqa: E402
from validate import InputRefused  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def refuses(value: str, label: str) -> None:
    try:
        validate.parse_prefix(value)
        check(f"refuses {label} ({value})", False, "accepted")
    except InputRefused as exc:
        msg = str(exc).lower()
        check(f"refuses {label} ({value})", True)
        if "no request was sent" not in msg and "refused locally" not in msg:
            FAILURES.append(f"{label}: refusal does not state no request was sent")
            print(f"  FAIL  {label} refusal omits the disclosure statement")


def test_private_and_reserved_v4_refused() -> None:
    """The whole point: sending 10.0.0.1 to a public registry is a disclosure even
    if the lookup then fails."""
    for value, label in [
        ("10.0.0.1", "RFC1918 /8"),
        ("192.168.2.130", "RFC1918 /16"),
        ("172.16.5.5", "RFC1918 /12"),
        ("127.0.0.1", "loopback"),
        ("169.254.1.1", "link-local"),
        ("100.64.0.1", "CGNAT"),
        ("224.0.0.1", "multicast"),
        ("192.0.2.5", "TEST-NET-1 documentation"),
        ("198.51.100.5", "TEST-NET-2 documentation"),
        ("203.0.113.5", "TEST-NET-3 documentation"),
        ("0.0.0.0", "this-network"),
    ]:
        refuses(value, label)


def test_private_and_reserved_v6_refused() -> None:
    """FR-029 — IPv6 gets the same treatment, not an afterthought."""
    for value, label in [
        ("::1", "v6 loopback"),
        ("fc00::1", "v6 unique-local"),
        ("fe80::1", "v6 link-local"),
        ("2001:db8::1", "v6 documentation"),
        ("ff02::1", "v6 multicast"),
    ]:
        refuses(value, label)


def test_public_addresses_accepted() -> None:
    """The refusal must not be so broad it blocks the feature's actual purpose."""
    for value in ("8.8.8.8", "1.1.1.0/24", "193.0.6.139", "2606:4700::/32", "2001:67c:2e8::"):
        try:
            p = validate.parse_prefix(value)
            check(f"accepts public {value}", True)
        except InputRefused as exc:
            check(f"accepts public {value}", False, str(exc)[:80])


def test_malformed_input_rejected_with_a_reason() -> None:
    """FR-030. Named problems, not a generic failure."""
    for value, label in [
        ("not-an-ip", "garbage"),
        ("1.1.1.1/99", "impossible v4 prefix length"),
        ("", "empty"),
        ("999.1.1.1", "octet out of range"),
    ]:
        try:
            validate.parse_prefix(value)
            check(f"rejects {label}", False, "accepted")
        except InputRefused:
            check(f"rejects {label}", True)


def test_asn_normalisation() -> None:
    check("AS13335 -> AS13335", validate.normalise_asn("AS13335") == "AS13335")
    check("13335 -> AS13335", validate.normalise_asn("13335") == "AS13335")
    check("as13335 -> AS13335", validate.normalise_asn("as13335") == "AS13335")
    for bad, label in [("AS0", "AS0 reserved by RFC 7607"),
                       ("ASfoo", "non-numeric"),
                       ("AS4294967296", "beyond 32-bit")]:
        try:
            validate.normalise_asn(bad)
            check(f"rejects {label}", False, "accepted")
        except InputRefused:
            check(f"rejects {label}", True)


def test_resource_classification() -> None:
    check("ASN classified", validate.parse_resource("AS13335") == ("asn", "AS13335"))
    kind, val = validate.parse_resource("8.8.8.8")
    check("IP classified as prefix", kind == "prefix", kind)
    check("bare IP becomes host prefix", val == "8.8.8.8/32", val)


def test_country_codes() -> None:
    check("nl -> NL", validate.parse_country("nl") == "NL")
    for bad in ("NLD", "N", "12"):
        try:
            validate.parse_country(bad)
            check(f"rejects {bad!r}", False, "accepted")
        except InputRefused:
            check(f"rejects {bad!r}", True)


def main() -> int:
    print("input refusal contract tests (no network — that IS the test)")
    for fn in (
        test_private_and_reserved_v4_refused,
        test_private_and_reserved_v6_refused,
        test_public_addresses_accepted,
        test_malformed_input_rejected_with_a_reason,
        test_asn_normalisation,
        test_resource_classification,
        test_country_codes,
    ):
        print(f"\n{fn.__name__}")
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all validation contract tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
