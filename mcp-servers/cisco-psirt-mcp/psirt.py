"""Cisco PSIRT openVuln API v2 client.

Spec 078 FR-001, FR-002, FR-016, FR-017. Research R1, R5.

Four query shapes, all verified against the live API on 2026-07-31:

    OSType/<ostype>?version=<v>                       iosxe 17.3.1 -> 200, 122 advisories
    cve/<CVE-ID>
    advisory/<advisory-id>
    severity/<sev>/firstpublished?startDate=&endDate=  critical, 2026 H1 -> 200, 15

**What this client deliberately does NOT reach**, because it was measured, not assumed:

    Bug / EoX / Case / Serial-to-Info      HTTP 403 — the API Console grant does not
                                          include them (FR-016)
    CX Cloud (7 paths tried)               HTTP 504 — the service does not answer;
                                          almost certainly needs a separate tenant
                                          subscription (FR-017, research R2)
    OSType/iosxr (7.5.2, 6.6.3, 24.1.1)    HTTP 404, empty body, against an iosxe 200
                                          control in the same session. Not an OSType.

Those three are stated here as measured facts so nobody re-litigates them from the
documentation, which describes all of them as available.
"""

from __future__ import annotations

import httpx

from auth import AuthError, TokenProvider
from ratelimit import BACKOFF_S, RateLimiter

BASE_URL = "https://apix.cisco.com/security/advisories/v2"
DEFAULT_TIMEOUT = 30


class ApiError(RuntimeError):
    """A live call failed. Message is safe to surface — never contains a secret."""


class PsirtClient:
    def __init__(self, tokens: TokenProvider | None = None,
                 limiter: RateLimiter | None = None):
        self.tokens = tokens or TokenProvider()
        self.limiter = limiter or RateLimiter()

    def _get(self, path: str, params: dict | None = None) -> tuple[list, str]:
        """Issue one paced GET. Returns (advisories, api_path).

        An empty list here means *the API returned no advisories* — a fact about
        Cisco's publications. It never means a failure; failures raise.
        """
        url = f"{BASE_URL}/{path.lstrip('/')}"
        attempts = 0
        while True:
            self.limiter.acquire()
            try:
                token = self.tokens.bearer()
            except AuthError as exc:
                raise ApiError(str(exc)) from exc
            try:
                resp = httpx.get(url,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/json"},
                                 params=params or {}, timeout=DEFAULT_TIMEOUT)
            except httpx.HTTPError as exc:
                raise ApiError(f"could not reach the PSIRT API: "
                               f"{type(exc).__name__}") from exc

            if resp.status_code == 200:
                return _extract_advisories(resp.json()), path

            # No advisories for a valid query. The API uses 404 for this on some
            # paths, which is why it is NOT treated as an error here — except for
            # iosxr, which the caller refuses before ever reaching this method.
            if resp.status_code == 404:
                return [], path

            if resp.status_code == 429:
                if attempts < len(BACKOFF_S):
                    import time
                    time.sleep(BACKOFF_S[attempts])
                    attempts += 1
                    continue
                raise ApiError(
                    f"PSIRT rate limit (429) persisted after {attempts} backoff "
                    f"attempts. The budget is 5/sec and 30/min, shared across every "
                    f"caller of this credential.")

            if resp.status_code in (401, 403):
                # 403 is what the Bug/EoX/Case families return wholesale; on an
                # advisory path it means the grant lost the PSIRT scope.
                raise ApiError(
                    f"PSIRT returned HTTP {resp.status_code}. Confirm the API Console "
                    f"application still has the 'Cisco PSIRT openVuln API' selected. "
                    f"(Bug, EoX, Case and Serial-to-Info return 403 under this grant "
                    f"by design and are out of scope.)")

            detail = _error_detail(resp)
            raise ApiError(f"PSIRT returned HTTP {resp.status_code}"
                           + (f": {detail}" if detail else ""))

    # --- query shapes -----------------------------------------------------

    def by_os_version(self, ostype: str, version: str) -> tuple[list, str]:
        return self._get(f"OSType/{ostype}", {"version": version})

    def by_cve(self, cve: str) -> tuple[list, str]:
        return self._get(f"cve/{cve}")

    def by_advisory(self, advisory_id: str) -> tuple[list, str]:
        return self._get(f"advisory/{advisory_id}")

    def by_severity_range(self, severity: str, start_date: str,
                          end_date: str) -> tuple[list, str]:
        return self._get(f"severity/{severity}/firstpublished",
                         {"startDate": start_date, "endDate": end_date})


def _error_detail(resp: httpx.Response) -> str:
    """Pull a short error string out of a response, without echoing credentials.

    PSIRT's validation errors (`INVALID_IOSXE_VERSION`) are genuinely useful to the
    operator, so they are surfaced — but the body is truncated and only string
    fields are read, so an unexpected echo of the request cannot leak.
    """
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:200].strip()
    if isinstance(body, dict):
        for field in ("errorMessage", "error_description", "error", "message", "title"):
            value = body.get(field)
            if isinstance(value, str):
                return value[:200]
    return ""


def _extract_advisories(body) -> list:
    """Normalise the API's response envelope into a flat advisory list."""
    if isinstance(body, dict):
        for field in ("advisories", "Advisories"):
            value = body.get(field)
            if isinstance(value, list):
                return [_advisory(a) for a in value]
        # A single-advisory response comes back unwrapped.
        if "advisoryId" in body:
            return [_advisory(body)]
        return []
    if isinstance(body, list):
        return [_advisory(a) for a in body]
    return []


def _advisory(raw) -> dict:
    """Project one advisory onto the fields data-model.md defines.

    Trimmed deliberately: the full payload includes long HTML summaries and
    per-platform tables that would dominate an agent's context without changing
    the answer.
    """
    if not isinstance(raw, dict):
        return {"advisory_id": None, "title": str(raw)[:120]}
    cvss = raw.get("cvssBaseScore")
    if isinstance(cvss, str) and cvss.strip().upper() in ("NA", "", "NONE"):
        cvss = None
    cves = raw.get("cves")
    if isinstance(cves, str):
        cves = [cves]
    return {
        "advisory_id": raw.get("advisoryId"),
        "title": raw.get("advisoryTitle"),
        "severity": raw.get("sir"),
        "cvss_base_score": cvss,
        "cves": [c for c in (cves or []) if c and c != "NA"],
        "first_published": raw.get("firstPublished"),
        "last_updated": raw.get("lastUpdated"),
        "publication_url": raw.get("publicationUrl"),
    }
