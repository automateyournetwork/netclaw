"""
Contract tests for convergence-api.

Pins the response shapes that ui/netclaw-visual/modules/convergence/HomeView.js
depends on, as documented in ui/convergence-api/CONTRACT.md.

Why these exist
---------------
The client tolerates several shapes for the same data (``d.edge || d.firewall``,
``d.devices || d || d.items``). That tolerance meant a contract change showed up
as a quietly empty panel rather than an error, so nothing ever caught it. These
tests make the contract explicit and fail loudly instead.

Running
-------
    CONVERGENCE_API_URL=http://127.0.0.1:3080 pytest tests/contract/test_convergence_api.py -v

The suite skips (rather than fails) when the API is unreachable, so it does not
break a checkout with no stack running. It is therefore a guard for anyone with
the stack up, not a substitute for CI against a fixture — see
``test_contract_doc_exists`` for the part that always runs.
"""

import os
import pytest

requests = pytest.importorskip("requests")
jsonschema = pytest.importorskip("jsonschema")
from jsonschema import validate  # noqa: E402

BASE = os.environ.get("CONVERGENCE_API_URL", "http://127.0.0.1:3080").rstrip("/")
SITE = os.environ.get("CONVERGENCE_TEST_SITE", "home")
TIMEOUT = 20

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTRACT_DOC = os.path.join(REPO_ROOT, "ui", "convergence-api", "CONTRACT.md")


def _discover_token():
    """
    The API authenticates with a Bearer key from API_KEYS; the HUD proxy injects
    it so the browser never holds it. These tests talk to the API directly, so
    they resolve it the same way the rest of the stack does: environment first,
    then the .env files, so a developer with a running stack needs no setup.
    """
    tok = os.environ.get("CONVERGENCE_API_TOKEN") or os.environ.get("HOME_API_TOKEN")
    if tok:
        return tok.strip()
    candidates = [
        os.path.join(REPO_ROOT, "deploy", "convergence", ".env"),
        os.path.join(REPO_ROOT, ".env"),
        os.path.expanduser("~/.openclaw/.env"),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            for line in open(path, encoding="utf-8", errors="replace"):
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                if key.strip() in ("CONVERGENCE_API_TOKEN", "HOME_API_TOKEN"):
                    val = val.strip().strip("'\"")
                    if val:
                        return val
        except OSError:
            continue
    return None


TOKEN = _discover_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


# ---------------------------------------------------------------- helpers

def _get(path):
    try:
        r = requests.get(f"{BASE}{path}", timeout=TIMEOUT, headers=HEADERS)
    except requests.RequestException as exc:
        pytest.skip(f"convergence-api unreachable at {BASE}: {exc}")
    if r.status_code == 401:
        pytest.skip(
            "convergence-api rejected the API key. Set CONVERGENCE_API_TOKEN to a "
            "value present in the API's API_KEYS."
        )
    return r


@pytest.fixture(scope="module")
def api():
    """Skip the whole module unless the API answers /healthz."""
    try:
        r = requests.get(f"{BASE}/healthz", timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"convergence-api unreachable at {BASE}: {exc}")
    if r.status_code != 200:
        pytest.skip(f"convergence-api /healthz returned {r.status_code}")
    return r.json()


# Several assertions below only bite when a feature is actually degraded, which
# means they can pass vacuously against a healthy stack — a mutation that broke
# the degraded contract went undetected until the store was genuinely stopped.
#
# Set CONVERGENCE_EXPECT_DEGRADED=1 to assert the degraded contract *is* being
# exercised. Use it when deliberately testing the fallback path:
#
#     docker compose stop postgres
#     CONVERGENCE_EXPECT_DEGRADED=1 pytest tests/contract/test_convergence_api.py
EXPECT_DEGRADED = os.environ.get("CONVERGENCE_EXPECT_DEGRADED", "").lower() in ("1", "true", "yes")


def _require_degraded(condition, what):
    """Skip when not degraded, unless the caller demanded the degraded path."""
    if condition:
        return
    if EXPECT_DEGRADED:
        pytest.fail(
            f"CONVERGENCE_EXPECT_DEGRADED is set but {what} is healthy — "
            "the degraded contract was not exercised, so this run proves nothing "
            "about it."
        )
    pytest.skip(f"{what} is healthy; this asserts the degraded path")


def nullable(*types):
    """A value that may legitimately be absent. Absent is null, never 0."""
    return {"type": [*types, "null"]}


THRESHOLD_STATUS = {"type": ["string", "null"]}

METRIC = {
    "type": "object",
    "properties": {
        "value": nullable("number", "string"),
        "unit": nullable("string"),
        "status": THRESHOLD_STATUS,
    },
}


# ---------------------------------------------------------------- always runs

def test_contract_doc_exists():
    """The contract must be written down, not just asserted in code."""
    assert os.path.isfile(CONTRACT_DOC), f"missing {CONTRACT_DOC}"
    text = open(CONTRACT_DOC, encoding="utf-8").read()
    # The sections these tests enforce.
    for endpoint in ("/api/health", "/api/devices", "/api/sites",
                     "/api/events", "/healthz"):
        assert endpoint in text, f"{endpoint} is untested-but-undocumented"


# ---------------------------------------------------------------- /healthz

def test_healthz_shape(api):
    validate(api, {
        "type": "object",
        "required": ["status", "features", "database"],
        "properties": {
            "status": {"const": "ok"},
            "features": {
                "type": "object",
                "required": ["diary"],
                "properties": {
                    "diary": {"enum": ["available", "unavailable"]},
                },
            },
            "database": {
                "type": "object",
                "required": ["enabled", "available"],
                "properties": {
                    "enabled": {"type": "boolean"},
                    "available": {"type": "boolean"},
                    "reason": nullable("string"),
                },
            },
        },
    })


def test_healthz_stays_ok_when_diary_is_unavailable(api):
    """
    Postgres is optional. /healthz must not fail the container over it, or an
    optional dependency becomes a restart loop.
    """
    assert api["status"] == "ok", "an optional dependency must not fail the healthcheck"
    if api["features"]["diary"] == "unavailable":
        assert api["database"]["available"] is False
        assert api["database"].get("reason"), "unavailable without a reason is unactionable"
    elif EXPECT_DEGRADED:
        pytest.fail("CONVERGENCE_EXPECT_DEGRADED is set but the diary is available")


# ---------------------------------------------------------------- /api/health

def test_health_shape(api):
    r = _get(f"/api/health?site={SITE}")
    assert r.status_code == 200, r.text
    body = r.json()
    validate(body, {
        "type": "object",
        "required": ["site", "healthScore"],
        "properties": {
            "site": {"type": "string"},
            "healthScore": {
                "type": "object",
                "required": ["value", "status"],
                "properties": {
                    "value": {"type": "number", "minimum": 0, "maximum": 100},
                    "status": {"type": "string"},
                },
            },
            "wanLatency": METRIC,
            "wanLoss": METRIC,
            "speedtest": {"type": ["object", "null"]},
            "alertCount": {"type": ["object", "null"]},
        },
    })
    assert body["site"] == SITE, "site must be echoed so the client can trust the scope"


# ---------------------------------------------------------------- /api/devices

def test_devices_shape(api):
    r = _get(f"/api/devices?site={SITE}")
    assert r.status_code == 200, r.text
    body = r.json()
    validate(body, {
        "type": "object",
        "required": ["site", "switches"],
        "properties": {
            "site": {"type": "string"},
            "switches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "model", "status"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "model": {"type": "string", "minLength": 1},
                        "status": {"type": "string"},
                        "portsUp": nullable("integer"),
                        "portsTotal": nullable("integer"),
                        "errorRate": nullable("number"),
                        "source": nullable("string"),
                    },
                },
            },
            "edge": {"type": ["array", "null"]},
            "firewall": {"type": ["array", "null"]},
            "accessPoints": {"type": ["array", "null"]},
            "wanProbes": {"type": ["array", "null"]},
        },
    })


def test_devices_switches_is_always_an_array(api):
    """The view iterates this directly; an object or null blanks the table."""
    body = _get(f"/api/devices?site={SITE}").json()
    assert isinstance(body.get("switches"), list)


def test_devices_ports_absent_is_null_not_zero(api):
    """
    null means "the exporter has no IF-MIB data"; 0 means "measured zero ports
    up", which is an outage. Conflating them misreports health.
    """
    for sw in _get(f"/api/devices?site={SITE}").json().get("switches", []):
        up, total = sw.get("portsUp"), sw.get("portsTotal")
        if up is None:
            assert total is None, f"{sw['name']}: portsUp null but portsTotal set"
        if total is not None:
            assert total >= 0
            if up is not None:
                assert up <= total, f"{sw['name']}: portsUp {up} > portsTotal {total}"


def test_devices_model_is_not_a_hardcoded_lab_name(api):
    """
    Regression guard. Switch models were hardcoded to one lab's device names, so
    the table was wrong or empty for every other deployment. Models must now come
    from site config or a metric label.
    """
    body = _get(f"/api/devices?site={SITE}").json()
    src = open(
        os.path.join(REPO_ROOT, "ui", "convergence-api", "src", "routes", "devices.js"),
        encoding="utf-8",
    ).read()
    assert "HomeSwitch" not in src, "hardcoded device names are back in devices.js"
    for sw in body.get("switches", []):
        assert sw["model"], f"{sw['name']} has an empty model"


# ---------------------------------------------------------------- /api/sites

def test_sites_shape(api):
    r = _get("/api/sites")
    assert r.status_code == 200, r.text
    body = r.json()
    validate(body, {
        "type": "object",
        "required": ["sites"],
        "properties": {
            "sites": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "name": nullable("string"),
                        "healthy": {"type": ["boolean", "null"]},
                    },
                },
            },
        },
    })


def test_sites_is_non_empty_and_ordered(api):
    """
    The client falls back to sites[0] when its stored site is not on offer, so
    order is part of the contract and an empty list leaves it with nowhere to go.
    """
    sites = _get("/api/sites").json()["sites"]
    assert len(sites) >= 1, "at least one site must be offered"
    ids = [s["id"] for s in sites]
    assert len(ids) == len(set(ids)), f"duplicate site ids: {ids}"


# ---------------------------------------------------------------- /api/events

@pytest.mark.parametrize("path", ["/api/events", "/api/events/escalated"])
def test_events_shape(api, path):
    r = _get(f"{path}?site={SITE}&limit=5")
    assert r.status_code == 200, r.text
    body = r.json()
    validate(body, {
        "type": "object",
        "required": ["site", "events"],
        "properties": {
            "site": {"type": "string"},
            "events": {"type": "array"},
            "unavailable": {"type": ["boolean", "null"]},
            "reason": nullable("string"),
        },
    })


@pytest.mark.parametrize("path", ["/api/events", "/api/events/escalated"])
def test_events_unavailable_always_carries_a_reason(api, path):
    """
    An empty diary and an unreachable diary are indistinguishable without this,
    which is exactly the silent-degradation bug the flag was added to fix.
    """
    # Read the body first and judge degradation from that same response, so the
    # assertion cannot race the breaker half-opening between two requests.
    body = _get(f"{path}?site={SITE}").json()
    _require_degraded(bool(body.get("unavailable")), "the event store")
    assert body.get("reason"), "unavailable set without a reason"
    assert body["events"] == [], "unavailable must not also return events"


def test_events_degrade_never_500(api):
    """
    Reads degrade to 200 + unavailable; they must not surface a driver error as a
    server error, because the panel is optional by design.
    """
    assert _get(f"/api/events?site={SITE}").status_code == 200


def test_event_write_returns_503_not_500_when_store_is_down(api):
    """
    Writes cannot degrade, but they must say so actionably. Skipped when the
    store is healthy — this asserts the failure mode, not the happy path.
    """
    # Re-read state instead of trusting the module-scoped fixture. The breaker
    # half-opens after 15s, so a fixture captured while the store was down can be
    # stale by the time this runs — that raced and produced a false failure.
    fresh = _get("/healthz").json()
    _require_degraded(fresh["features"]["diary"] == "unavailable", "the diary")
    r = requests.post(
        f"{BASE}/api/events?site={SITE}",
        json={"message": "contract test", "severity": "info",
              "category": "test", "source": "contract-test"},
        timeout=TIMEOUT,
        headers={**HEADERS, "Content-Type": "application/json"},
    )
    assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("error")
    assert body.get("hint"), "a 503 without a hint is not actionable"
