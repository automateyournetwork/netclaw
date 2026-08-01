"""Per-platform destructive-command vocabulary.

Spec 076 FR-023, research R6.

Why this file exists: the NetClaw Constitution names `write erase`, `reload` and
`format flash:` as forbidden operations. Those are all **Cisco** syntax. This
server reaches ~90 platform families whose destructive commands look nothing
like that — VyOS wipes config with `delete`, MikroTik with
`/system reset-configuration`, SR Linux with `tools system configuration`, SONiC
with `config erase`. A Cisco-shaped denylist would therefore be worse than
useless here: it would look like protection while blocking nothing on the very
platforms this server exists to reach.

Two layers, because neither alone is sufficient:

  UNIVERSAL_DENY   destructive verbs common enough to block everywhere, even on
                   a platform we have not explicitly modelled. This is the
                   fail-safe for the long tail: a platform absent from
                   PLATFORM_DENY still gets baseline protection.

  PLATFORM_DENY    per-family additions, keyed by the platform identifier used
                   in the inventory.

Matching is on the command's **first token** (after normalisation), not a
substring search. `show reload-reason` must not be blocked because it contains
"reload"; `reload` as the verb must be. Chaining is handled separately and
earlier — see policy/filter.py, which rejects it before any of this runs.
"""

from __future__ import annotations

# Destructive verbs blocked on every platform, including unmodelled ones.
# Deliberately conservative: a false positive costs an operator one retry with
# write mode enabled, a false negative can cost a network.
UNIVERSAL_DENY: frozenset[str] = frozenset({
    # Constitution's explicit forbidden operations
    "reload", "reboot", "restart", "halt", "shutdown", "poweroff",
    # config destruction
    "erase", "format", "wipe", "zeroize", "factory-reset", "factory-default",
    # filesystem destruction
    "rm", "rmdir", "delete", "del", "purge", "destroy",
    # shell escape — a shell is an unbounded bypass of every other rule here
    "bash", "sh", "shell", "start-shell", "run", "system",
})

# Per-platform additions. Keys are inventory platform identifiers.
#
# Multi-word entries are matched against the normalised command prefix rather
# than a single token, because several platforms express destruction as a path
# (`/system reset-configuration`) or a verb pair (`request system zeroize`).
PLATFORM_DENY: dict[str, frozenset[str]] = {
    "cisco_ios": frozenset({"write erase", "format flash:", "erase startup-config"}),
    "cisco_xe": frozenset({"write erase", "format flash:", "erase startup-config"}),
    "cisco_nxos": frozenset({"write erase", "load-config", "erase startup-config"}),
    "cisco_xr": frozenset({"commit replace", "erase", "install remove"}),

    "juniper_junos": frozenset({
        "request system zeroize", "request system reboot",
        "request system power-off", "load override",
    }),

    "vyos": frozenset({
        # `delete` is a first-class config verb on VyOS, not just a file op
        "delete", "reset", "generate", "load", "reboot", "poweroff",
    }),

    "mikrotik_routeros": frozenset({
        "/system reset-configuration", "/system reboot", "/system shutdown",
        "/file remove", "/system package downgrade",
    }),

    "nokia_srlinux": frozenset({
        "tools system configuration", "tools platform", "/tools system",
    }),
    "nokia_sros": frozenset({"admin reboot", "admin save", "clear"}),

    "dell_sonic": frozenset({"config erase", "config reload", "sonic-clear"}),
    "dell_os10": frozenset({"delete startup-configuration", "reload", "image delete"}),

    "extreme_exos": frozenset({"unconfigure switch", "reboot", "rm"}),
    "extreme_vsp": frozenset({"reset", "boot", "remove"}),

    "huawei_vrp": frozenset({"reset saved-configuration", "reboot", "delete"}),

    "ubiquiti_edge": frozenset({"delete", "reboot", "poweroff", "format"}),

    "arista_eos": frozenset({"write erase", "delete flash:", "reload"}),

    "linux": frozenset({"rm", "dd", "mkfs", "shutdown", "reboot", "init"}),
}

# Read-only verbs. A command must begin with one of these when the server is in
# its default read-only mode (FR-022). Kept small on purpose — an over-broad
# allowlist is how read-only modes quietly stop being read-only.
READ_ONLY_PREFIXES: frozenset[str] = frozenset({
    "show", "display", "get", "fetch", "list", "dir", "more", "cat",
    "ping", "traceroute", "trace", "monitor", "check", "validate",
    "info", "print", "status", "version", "who", "uptime",
})


# Platform identifiers vary between the netmiko driver name, the inventory
# string an operator writes, and the vendor's own wording. Without normalisation
# a device keyed `nokia_srl` silently misses the `nokia_srlinux` denylist and is
# protected only by the universal baseline.
#
# That bug was real and shipped: SR Linux devices were not being checked against
# `tools system configuration`, their actual config-destruction command. It
# surfaced only when a live SR Linux node was tested, because nothing in the code
# or the unit tests connected the two spellings.
PLATFORM_ALIASES: dict[str, str] = {
    "nokia_srl": "nokia_srlinux",
    "srl": "nokia_srlinux",
    "srlinux": "nokia_srlinux",
    "nokia_sr_linux": "nokia_srlinux",
    "sros": "nokia_sros",
    "nokia_sr_os": "nokia_sros",
    "frr": "linux",
    "frrouting": "linux",
    "cisco_iosxe": "cisco_xe",
    "cisco_ios_xe": "cisco_xe",
    "cisco_iosxr": "cisco_xr",
    "cisco_ios_xr": "cisco_xr",
    "junos": "juniper_junos",
    "juniper": "juniper_junos",
    "sonic": "dell_sonic",
    "vyatta": "vyos",
    "eos": "arista_eos",
    "routeros": "mikrotik_routeros",
    "mikrotik": "mikrotik_routeros",
    "exos": "extreme_exos",
    "vrp": "huawei_vrp",
    "huawei": "huawei_vrp",
    "edgeos": "ubiquiti_edge",
}


def canonical(platform: str | None) -> str:
    """Normalise a platform identifier to its canonical deny-table key."""
    p = (platform or "").strip().lower()
    return PLATFORM_ALIASES.get(p, p)


def deny_tokens_for(platform: str | None) -> frozenset[str]:
    """Effective denylist for a platform: universal plus platform-specific.

    An unknown or missing platform still receives UNIVERSAL_DENY. Returning an
    empty set for an unrecognised platform would mean the long tail of supported
    devices — the ones this server exists for — got no protection at all.
    """
    specific = PLATFORM_DENY.get(canonical(platform), frozenset())
    return UNIVERSAL_DENY | specific


def is_modelled(platform: str | None) -> bool:
    """Whether this platform has explicit destructive-syntax modelling.

    Surfaced so callers can tell an operator that a device is protected only by
    the universal baseline — useful information, not a reason to refuse.
    """
    return bool(platform) and canonical(platform) in PLATFORM_DENY
