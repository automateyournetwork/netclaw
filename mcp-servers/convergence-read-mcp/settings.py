"""Shared stdlib-only Convergence configuration and scope validation."""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import os
import re
from urllib.parse import urlsplit

MESSAGES = {
    "disabled": "Convergence is disabled for this installation.",
    "not_configured": "Configure the Convergence endpoint, site, viewer credential and exporters on the server.",
    "invalid_argument": "Choose an allowed range, exporter, IP address and ordered time window of at most 24 hours.",
    "unauthorized": "Convergence denied access to the configured site.",
    "unavailable": "Convergence is unavailable; no fresh observation was obtained.",
    "timeout": "Convergence did not complete the read within the allowed time.",
    "compatibility": "Convergence returned an unsupported or out-of-scope response.",
}


class ReadError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(MESSAGES[code])


def ip(value, code="compatibility") -> str:
    if not isinstance(value, str) or len(value) > 45 or "%" in value:
        raise ReadError(code)
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise ReadError(code) from None


@dataclass(frozen=True)
class Settings:
    endpoint: str = field(repr=False)
    token: str = field(repr=False)
    site: str
    exporters: tuple[str, ...]

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        if env.get("CONVERGENCE_ENABLED", "false").lower() != "true":
            raise ReadError("disabled")
        endpoint = env.get("CONVERGENCE_API_URL", "")
        token = env.get("CONVERGENCE_API_TOKEN", "")
        site = env.get("CONVERGENCE_SITE", "")
        exporters = env.get("CONVERGENCE_EXPORTERS", "")
        if not all(isinstance(x, str) and x for x in (endpoint, token, site, exporters)):
            raise ReadError("not_configured")
        if len(endpoint) > 2048 or any(c.isspace() for c in endpoint) or "\\" in endpoint:
            raise ReadError("not_configured")
        try:
            url = urlsplit(endpoint)
            port = url.port
            if (not url.hostname or url.username is not None or url.password is not None
                    or url.query or url.fragment or url.path not in ("", "/")
                    or (port is not None and not 1 <= port <= 65535)):
                raise ValueError()
            if url.scheme != "https":
                if (url.scheme != "http" or env.get("CONVERGENCE_ALLOW_LOOPBACK_HTTP", "false").lower() != "true"
                        or not ipaddress.ip_address(url.hostname).is_loopback):
                    raise ValueError()
        except (ValueError, TypeError):
            raise ReadError("not_configured") from None
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", site):
            raise ReadError("not_configured")
        if len(token) > 8192 or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ReadError("not_configured")
        selected = tuple(dict.fromkeys(part.strip() for part in exporters.split(",")))
        if not 1 <= len(selected) <= 128:
            raise ReadError("not_configured")
        for value in selected:
            ip(value, "not_configured")
        return cls(endpoint.rstrip("/"), token, site, selected)

    def exporter(self, value):
        if value is None or value == "":
            return None
        canonical = ip(value, "invalid_argument")
        for allowed in self.exporters:
            if ip(allowed) == canonical:
                return allowed
        raise ReadError("invalid_argument")
