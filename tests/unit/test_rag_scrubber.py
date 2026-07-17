"""Unit tests for the snapshot secret scrubber (FR-072). Fully offline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "rag-mcp"))

from scrubber import SECRET_TYPES, scrub  # noqa: E402

CONFIG_SAMPLE = """hostname PE1
enable secret 5 $1$abcd$WxYz1234567890abcdef
username admin privilege 15 secret 9 $9$fLbCdEf/GhIjKlMnOpQrStUvWx
snmp-server community s3cr3tRO RO
snmp-server community s3cr3tRW RW
tacacs-server host 10.0.0.5 key 7 08351F1B1D431516475E
radius-server host 10.0.0.6 key myRadiusKey
router bgp 65000
 neighbor 10.0.0.1 password 7 095C4F1A0A1218000F
interface GigabitEthernet0/0/1
 ip ospf authentication-key ospfSecret
 ip ospf message-digest-key 1 md5 md5Secret
key chain BGP-KEYS
 key 1
  key-string 7 keychainSecret
crypto isakmp key MyPresharedKey address 192.0.2.1
line vty 0 4
 password plainTextPass
"""


def test_all_secret_classes_redacted():
    scrubbed, counts = scrub(CONFIG_SAMPLE)
    for leaked in (
        "$1$abcd$WxYz1234567890abcdef",
        "$9$fLbCdEf/GhIjKlMnOpQrStUvWx",
        "s3cr3tRO",
        "s3cr3tRW",
        "08351F1B1D431516475E",
        "myRadiusKey",
        "095C4F1A0A1218000F",
        "ospfSecret",
        "md5Secret",
        "keychainSecret",
        "MyPresharedKey",
        "plainTextPass",
    ):
        assert leaked not in scrubbed, f"secret leaked: {leaked}"
    assert counts["enable_secret"] >= 1
    assert counts["user_secret"] >= 1
    assert counts["snmp_community"] == 2
    assert counts["aaa_key"] >= 2
    assert counts["routing_auth_key"] >= 4
    assert counts["pre_shared_key"] >= 1
    assert counts["password"] >= 1


def test_username_adjacent_to_secret_redacted():
    scrubbed, counts = scrub("username admin privilege 15 secret 9 $9$abcdefghij\n")
    assert "admin" not in scrubbed
    assert "<REDACTED:username_adjacent>" in scrubbed
    assert counts["username_adjacent"] == 1


def test_juniper_dollar9_redacted():
    scrubbed, counts = scrub(
        'system { root-authentication { encrypted-password "$9$AbCdEfGhIjKlMnOp"; } }'
    )
    assert "$9$AbCdEfGhIjKlMnOp" not in scrubbed
    assert counts["juniper_secret"] >= 1


def test_redaction_placeholder_format():
    scrubbed, _ = scrub("snmp-server community topsecret RO\n")
    assert "snmp-server community <REDACTED:snmp_community>" in scrubbed


def test_zero_counts_reported_explicitly():
    scrubbed, counts = scrub("show ip route\n10.0.0.0/8 via 192.0.2.1\n")
    assert scrubbed.startswith("show ip route")
    assert set(counts.keys()) == set(SECRET_TYPES)
    assert all(v == 0 for v in counts.values())


def test_non_secret_content_untouched():
    text = "interface Gi0/0/1\n description uplink to core\n mtu 9000\n"
    scrubbed, counts = scrub(text)
    assert scrubbed == text
    assert sum(counts.values()) == 0
