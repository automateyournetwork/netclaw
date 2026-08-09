"""What a BMC answer does and does not tell you about the host.

R15 exists to answer one question NetClaw could not answer at all: **"is the box dead, or is it
the network?"** A BMC is the only vantage point that can distinguish them, because it answers
when the operating system cannot.

But the distinction is *symmetric*, and each direction is a different wrong answer:

    BMC unreachable            -> you learned NOTHING about the host.
                                  Not "the host is down". The BMC path failed, and the BMC
                                  path is a different network, NIC, and credential from the
                                  host's. Reporting "host down" here is the exact mistake
                                  out-of-band access exists to prevent.

    BMC reachable, Off         -> the host IS powered off. This is a FACT, not an inference,
                                  and it is the whole value of out-of-band.

    BMC reachable, On          -> the host has power. It does NOT mean the OS booted, the
                                  network is up, or the application is serving. A hung box
                                  reports PowerState: On forever.

    BMC reachable, health bad  -> a hardware fault is asserted. Still says nothing about
                                  whether the OS is running.

So this module makes the host verdict a first-class, mandatory field rather than something a
skill infers from raw JSON. `host_verdict()` refuses to produce a host claim from a failed BMC
reach, and every response that mentions power or health carries the verdict that qualifies it.

Same chokepoint shape as nsm-mcp's posture (spec 091), document-mcp's emit (082) and catc-mcp's
envelope (087): the qualifier cannot be separated from the finding, because there is no code
path that emits one without the other.
"""

from __future__ import annotations

import datetime
from typing import Any

# Redfish PowerState values that mean "the host has power applied".
_POWERED = {"On", "PoweringOn"}
_UNPOWERED = {"Off", "PoweringOff"}


class VerdictError(RuntimeError):
    """A response would state something about the host that the BMC did not establish.

    A programming error in this server, never caller-triggerable. It fails loudly during
    development so the claim cannot reach an operator as a confident wrong answer.
    """


def unreachable_verdict(reason: str) -> dict:
    """The verdict when the BMC itself could not be reached."""
    return {
        "bmc_reachable": False,
        "host_state": "UNKNOWN",
        "means": ("The BMC did not answer, so nothing was learned about the host. The BMC has "
                  "its own NIC, network path and credentials, all separate from the host's — "
                  "a BMC timeout is not evidence that the host is down."),
        "do_not_conclude": "host is down",
        "reason": reason,
    }


def host_verdict(power_state: str | None, health: str | None,
                 bmc_reachable: bool = True, reason: str = "") -> dict:
    """Turn a BMC reading into an explicit statement about the host.

    Raises VerdictError if asked to produce a host state from an unreachable BMC — the caller
    must use `unreachable_verdict()`, which is the honest shape for that case.
    """
    if not bmc_reachable:
        raise VerdictError(
            "refusing to derive a host state from an unreachable BMC. A failed BMC reach "
            "establishes nothing about the host; use unreachable_verdict().")

    if power_state in _UNPOWERED:
        state = "POWERED_OFF"
        means = ("The host is powered off. This is a fact reported by the BMC, not an "
                 "inference — which is precisely what out-of-band access is for.")
        caveat = None
    elif power_state in _POWERED:
        state = "POWERED_ON"
        means = ("The host has power applied. This does NOT mean the OS booted, the network "
                 "is up, or any service is responding — a hung machine reports On indefinitely.")
        caveat = "powered on is not the same as healthy or reachable in band"
    else:
        state = "POWER_STATE_UNREPORTED"
        means = (f"The BMC answered but reported PowerState={power_state!r}. Treat the host's "
                 "power state as unknown rather than guessing from it.")
        caveat = "the BMC is reachable; only the power field is unusable"

    v = {
        "bmc_reachable": True,
        "host_state": state,
        "hardware_health": health or "not reported",
        "means": means,
    }
    if caveat:
        v["caveat"] = caveat
    if health and health not in ("OK", "not reported"):
        v["hardware_fault"] = (
            f"The BMC asserts hardware health {health!r}. That is a hardware condition and is "
            "independent of whether the OS is running.")
    if reason:
        v["reason"] = reason
    return v


def emit(operation: str, *, endpoint: str | None = None, data: Any = None,
         verdict: dict | None = None, host_claim: Any = "__absent__",
         gaps: list[str] | None = None, error: str | None = None) -> dict:
    """The single response shape. Refuses a host claim that has no verdict behind it."""
    if host_claim != "__absent__" and verdict is None:
        raise VerdictError(
            f"{operation}: refusing to report host power or health without a verdict. A caller "
            "cannot tell 'the host is off' from 'the BMC did not answer' by looking at the "
            "reading alone, and those require opposite responses.")

    env: dict[str, Any] = {
        "operation": operation,
        "observed_at": datetime.datetime.now(datetime.timezone.utc)
                               .replace(microsecond=0).isoformat(),
        "source": "redfish-mcp (out-of-band BMC, read-only)",
    }
    if endpoint is not None:
        env["bmc_endpoint"] = endpoint
    if verdict is not None:
        env["verdict"] = verdict
    if host_claim != "__absent__":
        env["host"] = host_claim
    if data is not None:
        env["data"] = data
    if gaps:
        env["gaps"] = gaps
    if error is not None:
        env["error"] = error
    return env
