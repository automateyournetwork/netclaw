"""Server-side command filtering.

Spec 076 FR-022, FR-023, FR-029. Contract:
specs/076-multivendor-cli-driver/contracts/mcp-tools.md
Safety model ported from the archived, MIT-licensed sydasif/nornir-mcp-server
(research R1).

This is the safety-critical module. Everything else in this server can be wrong
in ways that produce a bad answer; this module being wrong produces a changed or
broken network.

Two properties are non-negotiable:

1. **Enforcement is here, in the server** — never in skill documentation
   (FR-029). Documentation describes policy; it cannot enforce it, because an
   agent can phrase a request any way it likes.

2. **Chaining is rejected FIRST** (contract: "Order is contractual"). This is
   the whole ballgame. `show version; write erase` begins with an allowlisted
   token, so any implementation that checks the allowlist before checking for
   chaining will permit it. That single ordering mistake defeats every other
   rule in this file.

Evaluation order:

    1. reject if the command contains a chaining/redirection construct
    2. reject if the command's first token (or command prefix) is denylisted
    3. in read-only mode, reject unless the first token is allowlisted
    4. permit
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .platform_deny import READ_ONLY_PREFIXES, deny_tokens_for, is_modelled


class Mode(str, Enum):
    READ_ONLY = "read_only"
    WRITE_ENABLED = "write_enabled"


class DenyRule(str, Enum):
    """Which rule rejected a command. Surfaced so an operator can distinguish a
    policy refusal from a device error, and know which knob to turn."""
    CHAINING = "chaining"
    DENYLIST = "denylist"
    NOT_READ_ONLY = "not_read_only"
    EMPTY = "empty"
    TOO_LONG = "too_long"


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    rule: DenyRule | None = None
    detail: str | None = None
    platform_modelled: bool = True

    @property
    def denied_reason(self) -> str | None:
        if self.allowed:
            return None
        return f"{self.rule.value}: {self.detail}"


# Constructs that let one command become several, or reach the filesystem or a
# shell. Each is a bypass of every rule that follows it, which is why this check
# runs first and rejects rather than sanitises.
#
# `|` is deliberately NOT here. On network devices a single pipe is a display
# filter (`show running-config | include bgp`) and blocking it would break
# ordinary read-only use. `||` IS blocked, as shell-style OR.
CHAINING_PATTERNS: tuple[tuple[str, str], ...] = (
    (";", "command separator"),
    ("&&", "shell AND"),
    ("||", "shell OR"),
    ("`", "command substitution (backtick)"),
    ("$(", "command substitution"),
    (">", "output redirection"),
    ("<", "input redirection"),
    ("\n", "embedded newline"),
    ("\r", "embedded carriage return"),
    ("&", "background execution"),
)

MAX_COMMAND_LEN = 512

# CLI wrappers: a host-shell command that hands a *network* command to a router
# CLI. FRR is the motivating case — `vtysh -c "show ip route"` is the ONLY way to
# read FRR over SSH, and netmiko drives it with the `linux` driver.
#
# These must be UNWRAPPED and their inner command evaluated, not allowlisted.
# Adding "vtysh" to READ_ONLY_PREFIXES would have been the obvious fix and is
# badly wrong: it permits `vtysh -c "configure terminal"`, turning the wrapper
# into a config escape. Found by testing against a real FRR container rather than
# by reading the code.
CLI_WRAPPERS: tuple[str, ...] = (
    "vtysh -c",      # FRR
    "vtysh -c ",
    "cli -c",        # assorted Linux-based NOSes
    "birdc",         # BIRD
)

MAX_UNWRAP_DEPTH = 2


def _normalise(command: str) -> str:
    """Collapse whitespace and lowercase for comparison.

    Not a sanitiser — nothing here makes an unsafe command safe. Normalisation
    exists so `SHOW   VERSION` and `show version` are treated identically, so a
    denylist cannot be evaded by case or spacing.
    """
    return re.sub(r"\s+", " ", command.strip()).lower()


def _first_token(normalised: str) -> str:
    return normalised.split(" ", 1)[0] if normalised else ""


def _unwrap(command: str) -> tuple[str, str | None]:
    """Strip a recognised CLI wrapper, returning (inner_command, wrapper_used).

    Returns the command unchanged with wrapper=None when nothing matched.
    """
    normalised = _normalise(command)
    for wrapper in CLI_WRAPPERS:
        w = wrapper.strip()
        if normalised.startswith(w + " "):
            inner = command.strip()[len(w):].strip()
            # strip one layer of surrounding quotes
            if len(inner) >= 2 and inner[0] == inner[-1] and inner[0] in "\"'":
                inner = inner[1:-1]
            return inner.strip(), w
    return command, None


def evaluate(command: str, platform: str | None = None,
             mode: Mode = Mode.READ_ONLY,
             _depth: int = 0) -> Verdict:
    """Evaluate one command against policy. Returns a Verdict, never raises.

    `mode` defaults to READ_ONLY so a caller that forgets to pass it gets the
    safe behaviour rather than the permissive one (FR-022).
    """
    modelled = is_modelled(platform)

    if not command or not command.strip():
        return Verdict(False, DenyRule.EMPTY, "empty command", modelled)

    if len(command) > MAX_COMMAND_LEN:
        return Verdict(False, DenyRule.TOO_LONG,
                       f"command exceeds {MAX_COMMAND_LEN} characters", modelled)

    # ---- Step 1: chaining. MUST be first. See module docstring. ----
    for token, description in CHAINING_PATTERNS:
        if token in command:
            return Verdict(
                False, DenyRule.CHAINING,
                f"contains {description} ({token!r}); send commands separately",
                modelled,
            )

    # ---- Step 1b: unwrap a CLI wrapper and judge what it actually runs ----
    # Runs AFTER the chaining check so `vtysh -c "show x"; reload` is already
    # rejected, and BEFORE the denylist so the inner command is what gets judged.
    inner, wrapper = _unwrap(command)
    if wrapper is not None:
        if _depth >= MAX_UNWRAP_DEPTH:
            return Verdict(False, DenyRule.CHAINING,
                           f"nested CLI wrappers beyond depth {MAX_UNWRAP_DEPTH}", modelled)
        if not inner:
            return Verdict(False, DenyRule.EMPTY,
                           f"{wrapper!r} with no command to run", modelled)
        verdict = evaluate(inner, platform, mode, _depth + 1)
        if verdict.allowed:
            return verdict
        return Verdict(verdict.allowed, verdict.rule,
                       f"via {wrapper!r}: {verdict.detail}", modelled)

    normalised = _normalise(command)
    first = _first_token(normalised)

    # ---- Step 2: denylist, on the first token or a multi-word prefix ----
    for denied in deny_tokens_for(platform):
        if " " in denied:
            # multi-word destructive form, e.g. "write erase", "/system reset-configuration"
            if normalised == denied or normalised.startswith(denied + " "):
                return Verdict(False, DenyRule.DENYLIST,
                               f"{denied!r} is destructive on platform {platform!r}",
                               modelled)
        elif first == denied:
            return Verdict(False, DenyRule.DENYLIST,
                           f"{denied!r} is a destructive verb", modelled)

    # ---- Step 3: read-only allowlist ----
    if mode is Mode.READ_ONLY and first not in READ_ONLY_PREFIXES:
        return Verdict(
            False, DenyRule.NOT_READ_ONLY,
            f"{first!r} is not a read-only verb; server is in read-only mode",
            modelled,
        )

    # ---- Step 4: permit ----
    return Verdict(True, None, None, modelled)


def assert_allowed(command: str, platform: str | None = None,
                   mode: Mode = Mode.READ_ONLY) -> None:
    """Raise PermissionError unless the command is allowed.

    For call sites that must not proceed. Used by the tool layer *before* a
    connection is opened, so a denied command never establishes a session
    (FR-029, contract mcp-tools.md).
    """
    verdict = evaluate(command, platform, mode)
    if not verdict.allowed:
        raise PermissionError(verdict.denied_reason)
