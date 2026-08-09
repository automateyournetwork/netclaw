"""Minimal read-only Redfish client.

Redfish is a DMTF standard with a stable, self-describing shape, so this is a thin HTTP layer
rather than a vendor SDK. Built rather than adopted because both candidate MCP servers are
unvendorable: `carlosedp/redfish-mcp-server` has **no license file at all**, and
`fredriksknese/mcp-redfish` resolves to `NOASSERTION` — not a recognised OSS licence. Spec 082
rejected an upstream on exactly that ground.

**Read-only is enforced here, at the transport.** `get()` is the only verb implemented. Redfish
exposes `#ComputerSystem.Reset` as a POST action on every system, and a power cycle on the wrong
box is an outage — so there is no code path in this server that can issue one. Under
Principle III that write would need ITSM gating; the safer answer is not to build it.
"""

from __future__ import annotations

import logging
import os
from typing import Any

# Guarded so the pure-logic parts of this module -- endpoint refusal and the TLS disclosure --
# work where httpx is absent (CI installs nothing, spec 075 SC-013). Only get() needs the
# library, and it raises a clear BmcUnreachable if asked to run without it. Spec 092 learned
# this the same way: a top-level import made stdlib-only assertions fail instead of skip.
try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - exercised by the CI path
    httpx = None

# httpx logs every request at INFO. On a STDIO transport anything written to stdout corrupts
# the JSON-RPC stream, and the handler FastMCP installs is not guaranteed to keep it off there.
# Silencing at the source is the only reliable fix; measured, these lines were being emitted.
if httpx is not None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

# BMCs ship self-signed certificates almost universally, and an operator cannot fix that from
# here. Verification is therefore OFF by default but the choice is reported in every response's
# gaps, so it is a visible decision rather than a silent one. Set REDFISH_VERIFY_TLS=true where
# the BMC has a real certificate.
VERIFY_TLS = os.environ.get("REDFISH_VERIFY_TLS", "false").lower() in ("1", "true", "yes")
TIMEOUT = float(os.environ.get("REDFISH_TIMEOUT", "15"))


class BmcUnreachable(RuntimeError):
    """The BMC could not be reached or refused the credentials.

    Deliberately distinct from "the host is down": callers must translate this into an
    unreachable verdict, never a host verdict. See verdict.py.
    """


class RedfishClient:
    def __init__(self, base_url: str | None = None,
                 username: str | None = None, password: str | None = None) -> None:
        self.base = (base_url or os.environ.get("REDFISH_URL", "")).rstrip("/")
        if not self.base:
            raise BmcUnreachable(
                "no BMC endpoint configured. Set REDFISH_URL (e.g. https://10.0.0.5) or pass "
                "base_url. This server never guesses an address — probing an unknown BMC is "
                "how you end up querying someone else's hardware.")
        self.user = username or os.environ.get("REDFISH_USERNAME") or ""
        self.password = password or os.environ.get("REDFISH_PASSWORD") or ""

    def _client(self):
        if httpx is None:
            raise BmcUnreachable(
                "the httpx package is not installed; install "
                "mcp-servers/redfish-mcp/requirements.txt")
        auth = (self.user, self.password) if self.user else None
        return httpx.Client(base_url=self.base, auth=auth, timeout=TIMEOUT,
                            verify=VERIFY_TLS, follow_redirects=True)

    def get(self, path: str) -> Any:
        """GET one Redfish resource. The only verb this client implements."""
        if not path.startswith("/"):
            path = "/" + path
        try:
            with self._client() as c:
                resp = c.get(path)
        except BmcUnreachable:
            raise
        except Exception as exc:
            # Broad rather than httpx.HTTPError so this still reports honestly when httpx is
            # absent and the class cannot be named.
            raise BmcUnreachable(f"{type(exc).__name__}: {exc}") from exc

        if resp.status_code in (401, 403):
            # An auth rejection proves the BMC is ALIVE -- it answered. Collapsing it into
            # "unreachable" would lose that, and "unreachable" wrongly nudges a reader toward
            # "the host is down". Same trap spec 087 hit with httpx.HTTPStatusError.
            raise BmcUnreachable(
                f"the BMC answered but rejected the credentials (HTTP {resp.status_code}). "
                "It is reachable — this is a credential problem, not a dead box.")
        if resp.status_code == 404:
            raise BmcUnreachable(f"the BMC has no resource at {path} (HTTP 404). "
                                 "Vendors implement different subsets of Redfish.")
        if resp.status_code >= 400:
            raise BmcUnreachable(f"HTTP {resp.status_code} from {path}")
        try:
            return resp.json()
        except ValueError as exc:
            raise BmcUnreachable(f"{path} did not return JSON") from exc

    def members(self, collection_path: str) -> list[str]:
        """The @odata.id list from a Redfish collection."""
        body = self.get(collection_path)
        return [m["@odata.id"] for m in (body.get("Members") or []) if "@odata.id" in m]

    def tls_note(self) -> str | None:
        if not VERIFY_TLS:
            return ("TLS certificate verification is DISABLED (REDFISH_VERIFY_TLS is not set). "
                    "BMCs almost always ship self-signed certificates, so this is the workable "
                    "default — but the transport is not authenticated, and on an untrusted "
                    "network the answers could be forged.")
        return None
