"""Investigation policy loader and tier resolution (067 Phase 9).

Policy file is data the operator edits as alert hygiene improves.
Missing/invalid file → T0 (fail-safe, no multi-tool auto-investigation).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("alert-receiver.policy")

DEFAULT_POLICY_PATH = Path(
    os.getenv(
        "INVESTIGATION_POLICY_PATH",
        os.path.expanduser("~/.openclaw/investigation-policy.yaml"),
    )
)
POLICY_CACHE_TTL = float(os.getenv("INVESTIGATION_POLICY_CACHE_TTL", "30"))

_VALID_TIERS = ("T0", "T1", "T2")


@dataclass
class TierDecision:
    tier: str  # T0 | T1 | T2
    rule: str
    budgets: dict = field(default_factory=dict)
    raw_policy: dict = field(default_factory=dict)


@dataclass
class _Cache:
    path: Path
    mtime: float
    loaded_at: float
    data: dict
    fail_safe: bool


_cache: Optional[_Cache] = None

# Budget state (process-local)
_t2_hour_stamps: list[float] = []
_t2_in_flight: int = 0


def _empty_failsafe_policy() -> dict:
    return {
        "version": 1,
        "default_tier": "T0",
        "allow_t2": [],
        "allow_t1": [],
        "force_t0": [
            {"alertname": "SwitchIdlePortsPresent"},
            {"alertname": "SwitchInterfaceDown"},
            {"label": "investigate=false"},
        ],
        "budgets": {
            "max_t2_per_hour": 3,
            "max_concurrent_t2": 2,
            "dedup_ttl_seconds": 1800,
        },
        "degrade": {"force_max_tier": None},
        "_fail_safe": True,
    }


def load_policy(path: Optional[Path] = None, *, force: bool = False) -> dict:
    """Load policy YAML with mtime + TTL cache. Fail-safe to T0 defaults."""
    global _cache
    path = path or DEFAULT_POLICY_PATH
    now = time.monotonic()

    if (
        not force
        and _cache is not None
        and _cache.path == path
        and (now - _cache.loaded_at) < POLICY_CACHE_TTL
    ):
        try:
            st = path.stat()
            if st.st_mtime == _cache.mtime:
                return _cache.data
        except OSError:
            return _cache.data

    if not path.is_file():
        log.warning(
            "investigation_policy missing at %s — fail-safe T0 (no multi-tool auto)",
            path,
        )
        data = _empty_failsafe_policy()
        _cache = _Cache(path=path, mtime=0.0, loaded_at=now, data=data, fail_safe=True)
        return data

    try:
        import yaml  # type: ignore

        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("policy root must be a mapping")
        data.setdefault("default_tier", "T0")
        data.setdefault("allow_t2", [])
        data.setdefault("allow_t1", [])
        data.setdefault("force_t0", [])
        data.setdefault(
            "budgets",
            {
                "max_t2_per_hour": 3,
                "max_concurrent_t2": 2,
                "dedup_ttl_seconds": 1800,
            },
        )
        data.setdefault("degrade", {"force_max_tier": None})
        data["_fail_safe"] = False
        st = path.stat()
        _cache = _Cache(
            path=path, mtime=st.st_mtime, loaded_at=now, data=data, fail_safe=False
        )
        return data
    except Exception as e:
        log.warning(
            "investigation_policy invalid at %s (%s) — fail-safe T0", path, e
        )
        data = _empty_failsafe_policy()
        _cache = _Cache(path=path, mtime=0.0, loaded_at=now, data=data, fail_safe=True)
        return data


def _norm_tier(t: Any) -> str:
    s = str(t or "T0").strip().upper()
    if s not in _VALID_TIERS:
        return "T0"
    return s


def _clamp_tier(tier: str, max_tier: Optional[str]) -> str:
    if not max_tier:
        return tier
    order = {"T0": 0, "T1": 1, "T2": 2}
    m = _norm_tier(max_tier)
    if order.get(tier, 0) > order.get(m, 0):
        return m
    return tier


def _rule_matches(rule: Any, alertname: str, severity: str, labels: dict) -> bool:
    if not isinstance(rule, dict):
        return False
    # alertname exact (case-sensitive as Prom names usually are)
    if "alertname" in rule and rule["alertname"] and rule["alertname"] != alertname:
        return False
    if "severity" in rule and rule["severity"]:
        if str(rule["severity"]).lower() != severity.lower():
            return False
    # label: investigate=false  or  label: {key: value}
    if "label" in rule and rule["label"] is not None:
        lab = rule["label"]
        if isinstance(lab, str):
            if "=" in lab:
                k, v = lab.split("=", 1)
                if str(labels.get(k.strip(), "")).lower() != v.strip().lower():
                    return False
            else:
                # bare key must be present and truthy-ish
                if not labels.get(lab):
                    return False
        elif isinstance(lab, dict):
            for k, v in lab.items():
                if str(labels.get(k, "")).lower() != str(v).lower():
                    return False
    return True


def _alert_labels_dict(alert) -> dict:
    """Build flat label map from pydantic Alert labels."""
    labels = {}
    lab = getattr(alert, "labels", None)
    if lab is None:
        return labels
    if hasattr(lab, "model_dump"):
        try:
            labels.update({k: str(v) for k, v in lab.model_dump().items() if v is not None})
        except Exception:
            pass
    for key in ("alertname", "instance", "severity", "job", "site", "device_name"):
        v = getattr(lab, key, None)
        if v is not None and str(v) != "":
            labels[key] = str(v)
    extra = getattr(lab, "model_extra", None) or {}
    for k, v in extra.items():
        if v is not None:
            labels[str(k)] = str(v)
    return labels


def resolve_tier(alert) -> TierDecision:
    """Return tier decision for a firing alert object."""
    policy = load_policy()
    budgets = dict(policy.get("budgets") or {})
    labels = _alert_labels_dict(alert)
    alertname = labels.get("alertname") or getattr(
        getattr(alert, "labels", None), "alertname", ""
    )
    severity = (labels.get("severity") or "warning").strip().lower()

    # Resolved alerts never investigate (caller should skip before this)
    if getattr(alert, "status", "firing") != "firing":
        return TierDecision(tier="T0", rule="resolved", budgets=budgets, raw_policy=policy)

    # 1) force_t0
    for rule in policy.get("force_t0") or []:
        if _rule_matches(rule, alertname, severity, labels):
            return TierDecision(
                tier="T0",
                rule=f"force_t0:{_rule_id(rule)}",
                budgets=budgets,
                raw_policy=policy,
            )

    # investigate=false always T0 even without force_t0 entry
    inv = (labels.get("investigate") or "").strip().lower()
    if inv in ("false", "no", "0", "never", "off"):
        return TierDecision(
            tier="T0", rule="label:investigate=false", budgets=budgets, raw_policy=policy
        )

    # 2) allow_t2
    for rule in policy.get("allow_t2") or []:
        if _rule_matches(rule, alertname, severity, labels):
            tier = "T2"
            rule_s = f"allow_t2:{_rule_id(rule)}"
            break
    else:
        # 3) allow_t1
        tier = None
        rule_s = None
        for rule in policy.get("allow_t1") or []:
            if _rule_matches(rule, alertname, severity, labels):
                tier = "T1"
                rule_s = f"allow_t1:{_rule_id(rule)}"
                break
        if tier is None:
            # 4) default
            tier = _norm_tier(policy.get("default_tier", "T0"))
            rule_s = f"default_tier:{tier}"

    # 5) degrade clamp
    degrade = policy.get("degrade") or {}
    max_tier = degrade.get("force_max_tier")
    clamped = _clamp_tier(tier, max_tier)
    if clamped != tier:
        rule_s = f"{rule_s}+degrade:{max_tier}"
        tier = clamped

    return TierDecision(
        tier=tier, rule=rule_s or "default", budgets=budgets, raw_policy=policy
    )


def _rule_id(rule: dict) -> str:
    if rule.get("alertname"):
        return str(rule["alertname"])
    if rule.get("label"):
        return f"label={rule['label']}"
    if rule.get("severity"):
        return f"severity={rule['severity']}"
    return "rule"


def admit_t2(budgets: dict) -> tuple[bool, str]:
    """Check T2 hourly + concurrent budgets. Caller must release_t2() after work."""
    global _t2_in_flight, _t2_hour_stamps
    now = time.monotonic()
    max_hour = int(budgets.get("max_t2_per_hour") or 3)
    max_conc = int(budgets.get("max_concurrent_t2") or 2)

    _t2_hour_stamps = [t for t in _t2_hour_stamps if now - t < 3600.0]
    if len(_t2_hour_stamps) >= max_hour:
        return False, "hourly"
    if _t2_in_flight >= max_conc:
        return False, "concurrent"
    _t2_in_flight += 1
    _t2_hour_stamps.append(now)
    return True, "admitted"


def release_t2() -> None:
    global _t2_in_flight
    _t2_in_flight = max(0, _t2_in_flight - 1)


def t2_in_flight() -> int:
    return _t2_in_flight


def policy_fail_safe() -> bool:
    return bool((_cache.data if _cache else {}).get("_fail_safe"))
