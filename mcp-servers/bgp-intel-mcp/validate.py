"""Input refusal, before anything leaves the machine. Spec 081, FR-028/029/030.

THIS IS A DISCLOSURE CONTROL, NOT A VALIDATION NICETY.

Sending `10.0.0.1` or an internal hostname to a public registry is a disclosure
even if the query then fails — the third party has already seen it. So private,
reserved and bogon input is refused **locally**, with no outbound request. Spec 079
applied exactly this reasoning to Globalping, and the same logic holds here.

The secondary benefit is honesty: these ranges have no meaningful registry or RPKI
answer, so forwarding them would produce a confusing empty result rather than a
clear explanation.

IPv4 and IPv6 throughout (FR-029) — verified live against RPKI, RDAP and RIPEstat.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

#: IPv4 ranges with no public registry meaning. `ipaddress` covers most of these
#: via its own flags, but the documentation ranges and CGNAT need naming
#: explicitly, and an explicit table is easier to audit than a chain of flags.
_V4_REFUSED = [
    (ipaddress.ip_network("0.0.0.0/8"), "unspecified / this-network"),
    (ipaddress.ip_network("10.0.0.0/8"), "RFC1918 private"),
    (ipaddress.ip_network("100.64.0.0/10"), "RFC6598 CGNAT shared address space"),
    (ipaddress.ip_network("127.0.0.0/8"), "loopback"),
    (ipaddress.ip_network("169.254.0.0/16"), "link-local"),
    (ipaddress.ip_network("172.16.0.0/12"), "RFC1918 private"),
    (ipaddress.ip_network("192.0.0.0/24"), "IETF protocol assignments"),
    (ipaddress.ip_network("192.0.2.0/24"), "RFC5737 documentation (TEST-NET-1)"),
    (ipaddress.ip_network("192.168.0.0/16"), "RFC1918 private"),
    (ipaddress.ip_network("198.18.0.0/15"), "RFC2544 benchmarking"),
    (ipaddress.ip_network("198.51.100.0/24"), "RFC5737 documentation (TEST-NET-2)"),
    (ipaddress.ip_network("203.0.113.0/24"), "RFC5737 documentation (TEST-NET-3)"),
    (ipaddress.ip_network("224.0.0.0/4"), "multicast"),
    (ipaddress.ip_network("240.0.0.0/4"), "reserved"),
]

_V6_REFUSED = [
    (ipaddress.ip_network("::/128"), "unspecified"),
    (ipaddress.ip_network("::1/128"), "loopback"),
    (ipaddress.ip_network("fc00::/7"), "RFC4193 unique-local"),
    (ipaddress.ip_network("fe80::/10"), "link-local"),
    (ipaddress.ip_network("2001:db8::/32"), "RFC3849 documentation"),
    (ipaddress.ip_network("ff00::/8"), "multicast"),
]

_ASN_RE = re.compile(r"^(?:AS)?(\d+)$", re.IGNORECASE)


class InputRefused(ValueError):
    """Refused locally. No request was made."""


@dataclass(frozen=True)
class Prefix:
    network: ipaddress.IPv4Network | ipaddress.IPv6Network

    def __str__(self) -> str:
        return str(self.network)

    @property
    def version(self) -> int:
        return self.network.version


def normalise_asn(value: str | int) -> str:
    """Return a canonical `ASnnnn` string, or refuse. FR-030.

    AS0 is refused: RFC 7607 reserves it and it cannot legitimately originate a
    route, so a query about it is always a mistake worth naming.
    """
    raw = str(value).strip()
    match = _ASN_RE.match(raw)
    if not match:
        raise InputRefused(
            f"{raw!r} is not a valid AS number. Expected a number, optionally "
            "prefixed with 'AS' — for example 'AS13335' or '13335'."
        )
    number = int(match.group(1))
    if number == 0:
        raise InputRefused(
            "AS0 is reserved by RFC 7607 and cannot originate a route, so there is "
            "nothing to look up."
        )
    if number > 4294967295:
        raise InputRefused(f"AS{number} exceeds the 32-bit AS number range.")
    return f"AS{number}"


def parse_prefix(value: str) -> Prefix:
    """Parse an IP or CIDR prefix, refusing anything with no public meaning.

    Accepts a bare address (treated as a host prefix) or CIDR notation, v4 or v6.
    """
    raw = str(value).strip()
    if not raw:
        raise InputRefused("No address or prefix was supplied.")

    try:
        network = ipaddress.ip_network(raw, strict=False)
    except ValueError:
        try:
            network = ipaddress.ip_network(ipaddress.ip_address(raw))
        except ValueError:
            raise InputRefused(
                f"{raw!r} is not a valid IP address or CIDR prefix. Note that a "
                "mixed address family (an IPv4 address with an IPv6 prefix length, "
                "or vice versa) is rejected."
            ) from None

    table = _V4_REFUSED if network.version == 4 else _V6_REFUSED
    for refused_net, why in table:
        if network.subnet_of(refused_net) or refused_net.subnet_of(network):
            raise InputRefused(
                f"{network} falls in {refused_net} ({why}), which has no public "
                "registry or RPKI record. This was refused locally and no request "
                "was sent to any external service — sending internal addressing to "
                "a public registry would be a disclosure even if the lookup failed. "
                "For internal address space use NetClaw's own IPAM or device tooling."
            )

    return Prefix(network)


def parse_resource(value: str) -> tuple[str, str]:
    """Classify a free-form resource as `('asn', 'ASnnn')` or `('prefix', 'a/b')`.

    Used by the tools that accept "an IP, prefix, or ASN" so a caller does not
    have to pre-classify.
    """
    raw = str(value).strip()
    if _ASN_RE.match(raw):
        return "asn", normalise_asn(raw)
    return "prefix", str(parse_prefix(raw))


def parse_country(value: str) -> str:
    """ISO 3166-1 alpha-2, upper-cased. FR-030."""
    raw = str(value).strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", raw):
        raise InputRefused(
            f"{value!r} is not a two-letter ISO 3166-1 country code — for example "
            "'NL' or 'CA'."
        )
    return raw
