"""Per-family version normalisation, and the OSType support table.

Spec 078 FR-004, FR-004a, FR-004b, FR-009, FR-009a. Research R1, R3.

**This module carries the most dangerous failure mode in the feature**, so the
rule that prevents it lives here rather than in the tool layer:

    A normalisation failure MUST NEVER be reported as an empty advisory list.

An empty list reads as *"this device is not vulnerable."* A parse failure means
*"the question was never asked."* Those are entirely different claims, and
collapsing them tells an operator a device is safe when nothing was checked. So
`normalise()` returns an explicit failure rather than a falsy value — a caller
cannot accidentally send a blank version and read the empty response as good news.

## The version format is per-family, and the families disagree

Measured against the live API on 2026-07-31, every row a real call:

| OSType  | accepted            | rejected           | evidence      |
|---------|---------------------|--------------------|---------------|
| `iosxe` | `17.3.1`, `17.03.01`, `17.3.1a` | `17.3(1)` | 122, 122, 107 |
| `ios`   | `15.2(4)E`, `15.2(4)E10` | `15.2.4E`     | 74, 30        |
| `nxos`  | `9.3(5)`            | `9.3.5`            | 33            |
| `asa`   | `9.16.1`            | `9.16(1)`          | 65            |
| `ftd`   | `7.0.1`             | `7.2(0)`           | 90            |
| `fmc`   | `7.0.1`             | —                  | 34            |
| `aci`   | `15.2(3e)`, `16.0(3e)` | `5.2(3e)`, `5.2.3` | 10, 8      |

Two consequences that a single global rule would have got wrong:

1. **The conversion runs in both directions.** `iosxe`/`asa`/`ftd`/`fmc` want
   `A.B(C)` folded to `A.B.C`; `ios`/`nxos`/`aci` want the exact opposite. An
   earlier draft applied the dotted conversion to all seven, which would have
   broken `ios` and `nxos` on every call.
2. **`aci` means the switch image version, not the APIC version.** `15.2(3e)` and
   `16.0(3e)` return advisories; the APIC-style `5.2(3e)` does not. An operator
   reading a version off an APIC will hand over something this API rejects, so the
   skill has to say which number to collect.

A wrong format returns HTTP 406 `"<OS> version not found"`, which surfaces as
`api_error` — never as an empty list. That is the safety net working: the format
being wrong and Cisco having published nothing stay distinguishable.

Note that 406 `version not found` is also what a *correctly formatted* but untracked
version returns, so it means "Cisco has no record of this version", not necessarily
"you formatted it wrongly". Either way the question went unanswered, so either way it
is an error rather than a reassuring empty result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# How each family wants its build number expressed. Every entry is backed by a live
# 200 in the table above.
DOTTED = "dotted"        # 17.3.1    — parenthesised build folded into a dotted part
PARENTHESISED = "paren"  # 15.2(4)E  — build in parentheses, letter suffix OUTSIDE
PAREN_INNER = "paren_in"  # 15.2(3e)  — build in parentheses, letter suffix INSIDE

# Suffix placement is family-specific too, not just parenthesisation: `ios` accepts
# 15.2(4)E and `aci` accepts 15.2(3e), while `aci` rejects 15.2(3)e. Three formats,
# each backed by a live 200.
OSTYPE_FORMAT: dict[str, str] = {
    "iosxe": DOTTED,
    "asa": DOTTED,
    "ftd": DOTTED,
    "fmc": DOTTED,
    "ios": PARENTHESISED,
    "nxos": PARENTHESISED,
    "aci": PAREN_INNER,
}

SUPPORTED_OSTYPES: tuple[str, ...] = tuple(OSTYPE_FORMAT)

# Families whose normaliser has been confirmed by a live 200 with a real-world
# version string. All seven, as of the probe above.
#
# The spec drafted this as "iosxe only", because at specification time the other six
# were untestable. They turned out to be testable directly against the API, and
# testing them is what exposed the bidirectional rule — so the set is wider than
# planned, and wider in the safe direction. `normaliser_verified` stays on every
# result regardless: an unverified family may reappear if Cisco adds an OSType.
VERIFIED_OSTYPES: frozenset[str] = frozenset(SUPPORTED_OSTYPES)

# Example of a version string each family actually accepts, for error messages.
FORMAT_EXAMPLE: dict[str, str] = {
    "iosxe": "17.3.1", "asa": "9.16.1", "ftd": "7.0.1", "fmc": "7.0.1",
    "ios": "15.2(4)E", "nxos": "9.3(5)", "aci": "15.2(3e)",
}

# Families where the number an operator is most likely to read off the box is NOT
# the number this API wants.
COLLECTION_NOTE: dict[str, str] = {
    "aci": ("ACI expects the switch image version (e.g. 15.2(3e) or 16.0(3e)), not the "
            "APIC controller version (5.2(3e) is rejected). Collect it from the "
            "switch, not the controller."),
}

# OSTypes an operator may plausibly ask for, with the reason they are unavailable
# and what to do instead. Better than a bare "unsupported".
KNOWN_UNSUPPORTED: dict[str, str] = {
    "iosxr": ("IOS-XR is not an OSType on the PSIRT API — it returns HTTP 404 for every "
              "version tried (7.5.2, 6.6.3, 24.1.1) against an iosxe 200 control in the "
              "same session. Use check_cve, or advisory lookup by product ID, for IOS-XR "
              "devices. NetClaw can reach IOS-XR via pyATS, so this gap is surprising "
              "but real."),
    "ios-xr": "see 'iosxr' — IOS-XR is not supported by this API at all.",
    "nx-os": "use 'nxos'",
    "ios-xe": "use 'iosxe'",
    "asa-os": "use 'asa'",
    "apic": "use 'aci', with the switch image version rather than the APIC version.",
}


@dataclass(frozen=True)
class Normalised:
    """Outcome of normalising one version string.

    `ok=False` is a *failure to ask the question*, never an answer to it. Callers
    must surface it as `normalisation_failed` and never as an empty result
    (FR-009a).
    """
    ok: bool
    value: str | None = None
    raw: str = ""
    reason: str | None = None

    @property
    def failed(self) -> bool:
        return not self.ok


def is_supported(ostype: str | None) -> bool:
    return (ostype or "").strip().lower() in OSTYPE_FORMAT


def is_verified(ostype: str | None) -> bool:
    """Whether this family's normaliser is confirmed by a live 200 (FR-004a)."""
    return (ostype or "").strip().lower() in VERIFIED_OSTYPES


def collection_note(ostype: str | None) -> str | None:
    """Guidance where the obvious version to collect is the wrong one."""
    return COLLECTION_NOTE.get((ostype or "").strip().lower())


def unsupported_reason(ostype: str | None) -> str:
    """Explain an unsupported OSType, with the alternative where one exists."""
    key = (ostype or "").strip().lower()
    if key in KNOWN_UNSUPPORTED:
        return KNOWN_UNSUPPORTED[key]
    return (f"{ostype!r} is not a PSIRT OSType. Supported: "
            f"{', '.join(SUPPORTED_OSTYPES)}.")


# What a complete version looks like, anchored. Used with `fullmatch`, never `search`.
#
# **Anchoring is the whole safety property here.** A `search` that can stop early will
# stop early: on `17.3(1)garbage!!` an unanchored pattern happily returns `17.3`,
# because the regex engine backtracks past the parenthesised build to find *something*
# that matches. That truncated version then queries the API perfectly cleanly and
# comes back with a plausible advisory count for a version the device is not running.
# Both offline tests and a live call caught this. A version that does not match in its
# entirety must fail, not be salvaged.
_FULL = re.compile(
    r"\d+(?:\.\d+)*(?:\(\d+[a-zA-Z]*\))?(?:\.\d+)*[a-zA-Z]{0,2}\d{0,2}")

# A maximal run of characters that could belong to a version, so trailing junk is
# captured and rejected rather than trimmed away. Requires at least one digit.
_CANDIDATE = re.compile(r"\b[\dA-Za-z().]*\d[\dA-Za-z().]*")


def _whole_token(candidate: str) -> str | None:
    """Accept a candidate only if it is a version in its entirety.

    Also requires a dot or a parenthesis: every one of the seven families' formats
    has one, and demanding it stops a bare model-number fragment (`24T` out of
    `C9300-24T`) from being mistaken for a version.
    """
    candidate = candidate.strip().rstrip(",;")
    if not candidate or not _FULL.fullmatch(candidate):
        return None
    if "." not in candidate and "(" not in candidate:
        return None
    return candidate

# Trailing qualifiers that appear in `show version` output and are not part of the
# version PSIRT wants.
#
# NOTE: no `Cisco\s+IOS.*` alternative here. It looked like a way to drop a trailing
# product fragment, but `re.sub` is unanchored at the left, so on a real banner
# (`Cisco IOS Software [Amsterdam], Version 17.3(1), ...`) it matched from the very
# first word and deleted the whole string — normalisation then failed on valid input.
_TRAILING_NOISE = re.compile(r"[,\s]*(RELEASE\s+SOFTWARE.*|\(fc\d+\))$", re.I)

_PAREN_FORM = re.compile(r"^(\d+(?:\.\d+)*)\((\d+[a-zA-Z]*)\)([a-zA-Z]*\d*)$")
_DOTTED_FORM = re.compile(r"^(\d+(?:\.\d+)*)\.(\d+)([a-zA-Z]*\d*)$")


def _extract_token(raw: str) -> str | None:
    """Pull a version token out of a bare string or a full `show version` banner.

    Every path validates the *whole* candidate. Nothing here trims a token down until
    it matches — see `_FULL` for why that distinction is the safety property.
    """
    text = _TRAILING_NOISE.sub("", raw.strip())

    # Prefer the token that follows the word "Version", which is how banners read and
    # which sidesteps model numbers appearing earlier in the same line.
    after_version = re.search(r"[Vv]ersion\s+([^\s,]+)", text)
    if after_version:
        token = _whole_token(after_version.group(1))
        if token:
            return token

    # Otherwise scan maximal candidate runs left to right, accepting the first that is
    # a complete version. A run carrying trailing junk fails rather than being trimmed.
    for match in _CANDIDATE.finditer(text):
        token = _whole_token(match.group(0))
        if token:
            return token
    return None


def _to_dotted(token: str) -> str:
    """`17.3(1)` -> `17.3.1`; `17.3.1a` unchanged. For iosxe/asa/ftd/fmc."""
    m = _PAREN_FORM.match(token)
    if not m:
        return token
    major, build, suffix = m.groups()
    return f"{major}.{build}{suffix}"


def _to_parenthesised(token: str, inner_suffix: bool = False) -> str:
    """`15.2.4E` -> `15.2(4)E`, or `15.2(3e)` when the family wants the letter inside.

    `ios`/`nxos` take the suffix outside the parentheses; `aci` requires it inside
    and rejects `15.2(3)e`. Already-parenthesised input is left alone, since it is
    almost certainly how the operator read it off the device.
    """
    if _PAREN_FORM.match(token):
        return token
    m = _DOTTED_FORM.match(token)
    if not m:
        return token
    major, build, suffix = m.groups()
    return f"{major}({build}{suffix})" if inner_suffix and suffix \
        else f"{major}({build}){suffix}"


def normalise(ostype: str, raw: str | None) -> Normalised:
    """Normalise a version string for the given OS family.

    Returns an explicit failure rather than an empty value, so a caller cannot send
    a blank version and read the resulting empty list as "not vulnerable".
    """
    key = (ostype or "").strip().lower()

    if raw is None or not str(raw).strip():
        return Normalised(False, raw=str(raw or ""),
                          reason="no version supplied. This server never infers or "
                                 "defaults a version — collect it from the device first "
                                 "(pyATS for Cisco, multivendor-cli otherwise).")

    raw_s = str(raw).strip()
    token = _extract_token(raw_s)
    if not token:
        example = FORMAT_EXAMPLE.get(key, "17.3.1")
        return Normalised(False, raw=raw_s,
                          reason=f"could not find a version in {raw_s[:80]!r}. Pass a bare "
                                 f"version like {example!r}, or the full 'show version' "
                                 f"output.")

    form = OSTYPE_FORMAT.get(key, DOTTED)
    if form == DOTTED:
        value = _to_dotted(token)
    else:
        value = _to_parenthesised(token, inner_suffix=(form == PAREN_INNER))

    # Guard against a normaliser bug producing something that is not a version at
    # all. Refusing beats sending it: a malformed query can return an empty list,
    # and an empty list reads as "not vulnerable".
    if not re.match(r"^\d+(?:\.\d+)*(?:\(\d+[a-zA-Z]*\))?[a-zA-Z]{0,2}\d{0,2}$", value):
        return Normalised(False, raw=raw_s,
                          reason=f"normalised {raw_s[:40]!r} to {value!r}, which is not a "
                                 f"valid version shape. Refusing to query rather than risk "
                                 f"an empty result that would read as 'not vulnerable'.")

    return Normalised(True, value=value, raw=raw_s)
