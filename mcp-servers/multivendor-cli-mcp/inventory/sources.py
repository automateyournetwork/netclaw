"""Device inventory from exactly three sources, with attribution.

Spec 076 FR-017 through FR-017e, FR-020, FR-021. Clarified with the maintainer
2026-07-30.

    live_sot   NetBox / Nautobot / Infrahub, queried at call time. Preferred,
               because it cannot drift.
    generated  Rendered FROM a source of truth for offline/air-gapped use.
               A CACHE — the server overwrites it on refresh.
    operator   Written and maintained by the operator, for operators with no
               source of truth. The server NEVER writes to it.

The distinction between the two file-based sources is the part that matters, and
the reason it is enforced in code rather than documented in prose: conflating
them is what produces "the refresh wiped my edits". A generated file carries a
marker; an operator file must not. Refresh only ever touches the former.

`pyATS`'s `testbed.yaml` is explicitly NOT a source (FR-017e). It assumes Cisco,
and its `os:` values are precisely the platforms routing sends elsewhere — so
deriving inventory from it would mostly yield devices this server declines to
act on.

No source may contain credential material (FR-017d). Records carrying
secret-shaped fields are rejected, naming the device and field.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from credentials import looks_like_secret_field

# Marker written into generated inventories so a refresh can distinguish its own
# output from an operator's file. Without this, "regenerate" is indistinguishable
# from "destroy the operator's work".
GENERATED_MARKER = "_netclaw_generated"


class Source(str, Enum):
    LIVE_SOT = "live_sot"
    GENERATED = "generated"
    OPERATOR = "operator"


class InventoryError(RuntimeError):
    """Inventory could not be loaded, or contains something it must not."""


@dataclass
class Device:
    name: str
    hostname: str
    platform: str | None
    credential_ref: str = "default"
    groups: list[str] = field(default_factory=list)
    source: Source = Source.OPERATOR
    owning_server: str = "multivendor-cli"

    def public(self) -> dict:
        """Non-secret representation for tool results. Never includes a secret,
        because the record never held one."""
        return {
            "name": self.name,
            "hostname": self.hostname,
            "platform": self.platform,
            "groups": list(self.groups),
            "credential_ref": self.credential_ref,
            "source": self.source.value,
            "owning_server": self.owning_server,
        }


def _reject_secrets(name: str, record: dict) -> None:
    """Reject an inventory record carrying credential material (FR-017d)."""
    offending = [k for k in record if looks_like_secret_field(k)]
    if offending:
        raise InventoryError(
            f"device {name!r} carries credential field(s) {offending} in its inventory "
            f"record. Credentials must never appear in any inventory source — use "
            f"'credential_ref' and supply the secret via Vault or a gitignored .env "
            f"(Constitution Principle XIII)."
        )


def _parse_records(raw: dict, source: Source) -> list[Device]:
    devices: list[Device] = []
    from routing import owner_of  # local import: avoids a cycle at module load

    for name, record in raw.items():
        if name == GENERATED_MARKER:
            continue
        if not isinstance(record, dict):
            raise InventoryError(f"device {name!r}: expected a mapping, got {type(record).__name__}")
        _reject_secrets(name, record)
        hostname = record.get("hostname") or record.get("ip") or record.get("address")
        if not hostname:
            raise InventoryError(f"device {name!r}: no hostname/ip/address")
        platform = record.get("platform") or record.get("os") or record.get("device_type")
        devices.append(Device(
            name=name,
            hostname=str(hostname),
            platform=str(platform) if platform else None,
            credential_ref=str(record.get("credential_ref", "default")),
            groups=list(record.get("groups", []) or []),
            source=source,
            owning_server=owner_of(platform),
        ))
    return devices


def _load_file(path: Path, source: Source) -> list[Device]:
    if not path.is_file():
        raise InventoryError(f"inventory file not found: {path}")
    text = path.read_text()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        raw = _minimal_yaml(text, path)
    if not isinstance(raw, dict):
        raise InventoryError(f"{path}: expected a mapping of device-name -> record")
    return _parse_records(raw, source)


def _minimal_yaml(text: str, path: Path) -> dict:
    """Parse the small YAML subset an inventory needs, without a YAML dependency.

    Supports two levels of `key: value` plus `[a, b]` lists — which is the whole
    shape documented in quickstart.md. PyYAML is deliberately not a dependency of
    this module: inventory loading is on the safety-critical path and the fewer
    parsers involved, the fewer surprises. A richer document is a signal the
    operator wants the live source instead.
    """
    result: dict = {}
    current: dict | None = None
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if ":" not in stripped:
            raise InventoryError(f"{path}:{lineno}: expected 'key: value', got {stripped!r}")
        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()
        if indent == 0:
            current = {}
            result[key] = current if value == "" else value
            if value != "":
                current = None
            continue
        if current is None:
            raise InventoryError(f"{path}:{lineno}: indented entry with no parent device")
        if value.startswith("[") and value.endswith("]"):
            current[key] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        else:
            current[key] = value.strip("'\"")
    return result


def is_generated(path: Path) -> bool:
    """Whether a file was produced by this server (and may be overwritten)."""
    if not path.is_file():
        return False
    return GENERATED_MARKER in path.read_text()


def load_operator(path: Path) -> list[Device]:
    """Load an operator-authored inventory. Read-only, always (FR-017b)."""
    devices = _load_file(path, Source.OPERATOR)
    if is_generated(path):
        raise InventoryError(
            f"{path} carries the generated marker {GENERATED_MARKER!r}, so it is a cache "
            f"this server overwrites on refresh — not a file to hand-maintain. Point "
            f"MULTIVENDOR_INVENTORY_PATH at a file you own, or use "
            f"MULTIVENDOR_INVENTORY_SOURCE=generated."
        )
    return devices


def load_generated(path: Path) -> list[Device]:
    """Load a generated inventory cache."""
    devices = _load_file(path, Source.GENERATED)
    if not is_generated(path):
        raise InventoryError(
            f"{path} lacks the generated marker, so it looks operator-authored. Refusing "
            f"to treat it as a cache — a refresh would destroy it. Use "
            f"MULTIVENDOR_INVENTORY_SOURCE=operator."
        )
    return devices


def load_live_sot() -> list[Device]:
    """Query NetBox / Nautobot at call time (see inventory/live_sot.py).

    Raises rather than returning [] when no source is reachable, so `auto` falls
    through to a file tier with a reason — an empty inventory and an unreachable
    source of truth must never look the same (FR-017b/c).
    """
    from inventory import live_sot
    return live_sot.load()


@dataclass
class Resolution:
    devices: list[Device]
    source: Source
    fallback_reason: str | None = None


def resolve(preferred: str | None = None) -> Resolution:
    """Resolve inventory from the configured source, falling back in order.

    Order is live -> generated -> operator (FR-017b). The result always names the
    source that answered, and gives a reason when it was not the preferred one,
    so a stale cache is never mistaken for live data (FR-017c).
    """
    preferred = (preferred or os.environ.get("MULTIVENDOR_INVENTORY_SOURCE") or "auto").lower()
    gen_path = Path(os.environ.get(
        "MULTIVENDOR_GENERATED_PATH",
        os.path.expanduser("~/.openclaw/multivendor/inventory.generated.yaml")))
    op_path_raw = os.environ.get("MULTIVENDOR_INVENTORY_PATH")
    op_path = Path(op_path_raw) if op_path_raw else None

    if preferred == Source.LIVE_SOT.value:
        return Resolution(load_live_sot(), Source.LIVE_SOT)
    if preferred == Source.GENERATED.value:
        return Resolution(load_generated(gen_path), Source.GENERATED)
    if preferred == Source.OPERATOR.value:
        if op_path is None:
            raise InventoryError(
                "MULTIVENDOR_INVENTORY_SOURCE=operator but MULTIVENDOR_INVENTORY_PATH is unset")
        return Resolution(load_operator(op_path), Source.OPERATOR)

    # auto: try each in order, recording why we moved on.
    reasons: list[str] = []
    for loader, source in ((load_live_sot, Source.LIVE_SOT),
                           (lambda: load_generated(gen_path), Source.GENERATED),
                           (lambda: load_operator(op_path), Source.OPERATOR) if op_path
                           else (None, Source.OPERATOR)):
        if loader is None:
            reasons.append("operator: MULTIVENDOR_INVENTORY_PATH unset")
            continue
        try:
            devices = loader()
        except InventoryError as exc:
            reasons.append(f"{source.value}: {exc}")
            continue
        return Resolution(
            devices, source,
            fallback_reason="; ".join(reasons) if reasons else None,
        )

    raise InventoryError("no inventory source available — tried: " + "; ".join(reasons))


def find(devices: list[Device], name: str) -> Device:
    """Look up one device, reporting absence rather than guessing (FR-021)."""
    for d in devices:
        if d.name == name:
            return d
    raise InventoryError(
        f"device {name!r} is not present in any inventory source; it is not guessed at "
        f"or defaulted. Add it to your source of truth or inventory file."
    )
