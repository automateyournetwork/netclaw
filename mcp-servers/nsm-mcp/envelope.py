"""The chokepoint every NSM response passes through.

Why this file exists
--------------------
Zeek and Suricata both have a failure mode where the tool runs successfully, exits 0, and
tells you nothing — while looking exactly like it told you everything. Both were reproduced
live before this server was written (see specs/091-nsm-zeek-suricata/VERIFICATION.md):

1. **Suricata with no ruleset** logs two non-fatal warnings, processes **0 signatures**, and
   reports **0 alerts**. An analyst reads "0 alerts" as "clean traffic". It checked nothing.

2. **Zeek discards packets with invalid TCP checksums by default.** On the same fixture the
   default run produced **no http.log at all** — the HTTP request was invisible — and a
   `conn.log` that was also *wrong* (3 rows instead of the correct 2, because discarded
   packets fragment the flow). Only a warning on stderr marks it. NICs with checksum
   offloading routinely produce such captures, including the ones NetClaw's own
   `cml-packet-capture` and `gns3-packet-capture` skills produce.

Both failures are invisible in the *shape* of the output. A caller cannot tell a real
"nothing found" from "the tool was inert" by looking at the results, so the results must
never travel without the posture that qualifies them.

So this module makes omission structurally impossible rather than merely discouraged:
`emit()` refuses to return an alert verdict without a signature count, and refuses to return
Zeek findings without the checksum posture. A skill author cannot forget, because there is no
code path that lets them.

This is the same chokepoint shape as document-mcp's `emit()` (spec 082) and catc-mcp's
`_envelope()` (spec 087).
"""

from __future__ import annotations

import datetime
from typing import Any


class PostureError(RuntimeError):
    """Raised when a response would carry findings without the posture that qualifies them.

    A programming error in this server, never something a caller can trigger. It fails loudly
    at development time so the omission cannot reach an operator as a confident wrong answer.
    """


# Every value a caller could mistake for "the traffic was clean".
_ZERO_ALERT_VERDICTS = (0, "0", None, [], {}, "none", "no alerts")


def suricata_posture(signatures: int, ruleset_present: bool, ruleset_age_days: int | None) -> dict:
    """Describe whether Suricata was capable of alerting at all."""
    if signatures <= 0:
        state = "INERT"
        meaning = ("Suricata loaded 0 signatures, so it inspected nothing and could not have "
                   "alerted. Zero alerts here means the detector was off, NOT that the "
                   "traffic was clean.")
    elif not ruleset_present:
        state = "UNKNOWN"
        meaning = "Signatures were counted but no ruleset file was located; treat with suspicion."
    else:
        state = "ARMED"
        meaning = f"Suricata loaded {signatures} signatures and was capable of alerting."
    return {
        "state": state,
        "signatures_loaded": signatures,
        "ruleset_present": ruleset_present,
        "ruleset_age_days": ruleset_age_days,
        "meaning": meaning,
        "remedy": None if state == "ARMED" else "Run nsm_update_rules to fetch the ET Open ruleset.",
    }


def zeek_posture(checksum_validation: bool, discarded_hint: bool) -> dict:
    """Describe whether Zeek could see the packets it was given."""
    if checksum_validation and discarded_hint:
        state = "PACKETS_DISCARDED"
        meaning = ("Zeek reported invalid checksums AND checksum validation was on, so matching "
                   "packets were DISCARDED. Protocol logs may be missing entirely and conn.log "
                   "may be wrong. A missing http.log here does NOT mean there was no HTTP.")
    elif checksum_validation:
        state = "VALIDATING"
        meaning = ("Checksum validation was on and nothing was flagged. If this capture came "
                   "from a NIC with checksum offloading, prefer ignore_checksums.")
    else:
        state = "IGNORING_CHECKSUMS"
        meaning = ("Checksum validation was off (-C), so all packets were analysed regardless "
                   "of checksum. This is the correct setting for offloaded captures.")
    return {
        "state": state,
        "checksum_validation": checksum_validation,
        "invalid_checksums_seen": discarded_hint,
        "meaning": meaning,
        "remedy": ("Re-run with ignore_checksums=true to stop discarding packets."
                   if state == "PACKETS_DISCARDED" else None),
    }


def emit(
    operation: str,
    *,
    pcap: str | None = None,
    data: Any = None,
    suricata: dict | None = None,
    zeek: dict | None = None,
    alert_verdict: Any = "__absent__",
    zeek_findings: Any = "__absent__",
    gaps: list[str] | None = None,
    error: str | None = None,
) -> dict:
    """Build the one response shape this server returns.

    Refuses to emit an alert verdict without Suricata posture, or Zeek findings without Zeek
    posture. Those two rules are the entire point of the module.
    """
    if alert_verdict != "__absent__" and suricata is None:
        raise PostureError(
            f"{operation}: refusing to report an alert verdict without Suricata posture. "
            "Zero alerts from a detector that loaded zero signatures is not a clean result, "
            "and a caller cannot tell the difference from the verdict alone."
        )
    if zeek_findings != "__absent__" and zeek is None:
        raise PostureError(
            f"{operation}: refusing to report Zeek findings without checksum posture. "
            "Zeek silently discards packets with invalid checksums, so an absent protocol log "
            "is ambiguous between 'no such traffic' and 'the packets were dropped'."
        )

    # A zero-alert verdict from an inert detector is the exact wrong answer this server
    # exists to prevent. Force it to carry the correction inline, where it cannot be
    # separated from the number by a caller that only reads one field.
    if (alert_verdict != "__absent__"
            and suricata is not None
            and suricata.get("state") == "INERT"):
        looks_clean = (
            alert_verdict in _ZERO_ALERT_VERDICTS
            or (hasattr(alert_verdict, "__len__") and len(alert_verdict) == 0)
        )
        if looks_clean:
            alert_verdict = {
                "alerts": alert_verdict,
                "NOT_A_CLEAN_RESULT": suricata["meaning"],
            }

    env: dict[str, Any] = {
        "operation": operation,
        "observed_at": datetime.datetime.now(datetime.timezone.utc)
                                .replace(microsecond=0).isoformat(),
        "source": "nsm-mcp (Zeek + Suricata, offline PCAP analysis)",
    }
    if pcap is not None:
        env["pcap"] = pcap
    if suricata is not None:
        env["suricata_posture"] = suricata
    if zeek is not None:
        env["zeek_posture"] = zeek
    if alert_verdict != "__absent__":
        env["alerts"] = alert_verdict
    if zeek_findings != "__absent__":
        env["findings"] = zeek_findings
    if data is not None:
        env["data"] = data
    if gaps:
        env["gaps"] = gaps
    if error is not None:
        env["error"] = error
    return env
