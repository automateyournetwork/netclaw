"""
EVE-NG HTTP client, error types, response helpers, pagination, GAIT logging,
path/ID utilities, and the get_client() singleton.

Imports this module to access all shared infrastructure.
"""

import json
import os
import logging
import os
import sys
import time
import zipfile
from functools import wraps
from typing import Any, Optional
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

# Allow importing netclaw_tokens from the monorepo src/ tree
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("eve-ng-mcp")

try:
    import httpx
except ImportError as e:
    log.error("Missing required dependency: %s. Install with: pip install httpx", e)
    sys.exit(1)

# =============================================================================
# Configuration
# =============================================================================

EVE_URL               = os.getenv("EVE_URL", "http://127.0.0.1")
EVE_USER              = os.getenv("EVE_USER", "")
EVE_PASSWORD          = os.getenv("EVE_PASSWORD", "")
EVE_VERIFY_SSL        = os.getenv("EVE_VERIFY_SSL", "true").lower() == "true"
EVE_SESSION_TTL       = int(os.getenv("EVE_SESSION_TTL", "1800"))
EVE_HTML5             = int(os.getenv("EVE_HTML5", "-1"))
EVE_CACHE_TTL         = int(os.getenv("EVE_CACHE_TTL", "30"))
EVE_CACHE_MAX_ENTRIES = int(os.getenv("EVE_CACHE_MAX_ENTRIES", "256"))
EVE_MAX_PAGE_SIZE     = int(os.getenv("EVE_MAX_PAGE_SIZE", "200"))

# =============================================================================
# EVE-NG HTTP Client
# =============================================================================

class EVEClient:
    """HTTP client for EVE-NG REST API with cookie-based session caching."""

    RETRYABLE_CODES = {401, 412}

    def __init__(self, base_url: str, username: str, password: str,
                 verify_ssl: bool = True, session_ttl: int = 1800, html5: int = -1):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.html5 = html5
        self.session_ttl = session_ttl
        self.cache_ttl = max(0, EVE_CACHE_TTL)
        self.cache_max_entries = max(1, EVE_CACHE_MAX_ENTRIES)
        self._response_cache: dict[str, tuple[float, int, bytes, dict[str, str]]] = {}
        self._session_expires: float = 0
        self._client = httpx.Client(
            verify=verify_ssl,
            timeout=30.0,
            headers={"Accept": "application/json", "User-Agent": "eve-ng-mcp/1.0"},
        )

    def _cache_key(self, method: str, url: str, kwargs: dict[str, Any]) -> str:
        params = kwargs.get("params")
        return json.dumps({"method": method, "url": url, "params": params}, sort_keys=True, default=str)

    def _cache_get(self, method: str, url: str, kwargs: dict[str, Any]) -> Optional[httpx.Response]:
        if method.upper() != "GET" or self.cache_ttl <= 0:
            return None
        key = self._cache_key(method, url, kwargs)
        cached = self._response_cache.get(key)
        if not cached:
            return None
        expires_at, status_code, content, headers = cached
        if time.time() >= expires_at:
            self._response_cache.pop(key, None)
            return None
        log.debug("Cache hit for %s", url)
        return httpx.Response(
            status_code=status_code,
            content=content,
            headers=headers,
            request=httpx.Request(method, url),
        )

    def _cache_put(self, method: str, url: str, kwargs: dict[str, Any], response: httpx.Response):
        if method.upper() != "GET" or self.cache_ttl <= 0 or response.status_code not in (200, 201):
            return
        if len(self._response_cache) >= self.cache_max_entries:
            oldest_key = min(self._response_cache.items(), key=lambda item: item[1][0])[0]
            self._response_cache.pop(oldest_key, None)
        key = self._cache_key(method, url, kwargs)
        self._response_cache[key] = (
            time.time() + self.cache_ttl,
            response.status_code,
            bytes(response.content),
            dict(response.headers),
        )

    def invalidate_cache(self):
        self._response_cache.clear()

    def _login(self):
        """Authenticate and cache session cookie."""
        log.info("Authenticating with EVE-NG...")
        resp = self._client.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.username, "password": self.password, "html5": self.html5},
        )
        if resp.status_code not in (200, 204):
            raise EVEError("EVE_AUTH_FAILED", f"Login failed: HTTP {resp.status_code}", resp.status_code)
        self._session_expires = time.time() + self.session_ttl
        log.info("EVE-NG authentication successful")

    def _ensure_auth(self):
        if time.time() >= self._session_expires:
            self._login()

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Authenticated request with one auto-retry on session errors."""
        self._ensure_auth()
        url = f"{self.base_url}{path}"
        method = method.upper()
        no_cache = bool(kwargs.pop("no_cache", False))
        # EVE-NG uses GET for several mutating node lifecycle endpoints.
        # Never serve/cache those as read-only calls, otherwise verification can
        # read stale node state immediately after start/stop/wipe.
        mutating_get = method == "GET" and any(path.endswith(suffix) for suffix in ("/start", "/stop", "/wipe"))
        try:
            if mutating_get:
                self.invalidate_cache()
            cached = None if (no_cache or mutating_get) else self._cache_get(method, url, kwargs)
            if cached is not None:
                return cached
            resp = self._client.request(method, url, **kwargs)
            if resp.status_code in self.RETRYABLE_CODES:
                log.info("Session error %s — re-authenticating", resp.status_code)
                self._session_expires = 0
                self._login()
                resp = self._client.request(method, url, **kwargs)
            if mutating_get and resp.status_code in (200, 201, 204):
                self.invalidate_cache()
            elif method == "GET" and not no_cache:
                self._cache_put(method, url, kwargs, resp)
            elif method in {"POST", "PUT", "DELETE"} and resp.status_code in (200, 201, 204):
                self.invalidate_cache()
            return resp
        except httpx.ConnectError:
            raise EVEError("EVE_UNREACHABLE", f"Cannot connect to EVE-NG at {self.base_url}", -1)
        except httpx.TimeoutException:
            raise EVEError("EVE_UNREACHABLE", "Request to EVE-NG timed out", -1)

    def get(self, path: str, **kw) -> httpx.Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> httpx.Response:
        return self.request("POST", path, **kw)

    def put(self, path: str, **kw) -> httpx.Response:
        return self.request("PUT", path, **kw)

    def delete(self, path: str, **kw) -> httpx.Response:
        return self.request("DELETE", path, **kw)


# =============================================================================
# Error Handling
# =============================================================================

class EVEError(Exception):
    """Structured EVE-NG error with code and HTTP status."""

    def __init__(self, error_code: str, message: str, status_code: int = 500):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "success": False,
            "error": self.message,
            "error_code": self.error_code,
            "status_code": self.status_code,
        }


_HTTP_ERROR_MAP = {
    400: "EVE_VALIDATION",
    401: "EVE_AUTH_FAILED",
    404: "EVE_NOT_FOUND",
    409: "EVE_CONFLICT",
    412: "EVE_SESSION_EXPIRED",
    500: "EVE_SERVER_ERROR",
}


def handle_eve_response(response: httpx.Response, success_codes: list | None = None) -> Any:
    """Parse EVE-NG API response. Unwraps the {'status':'success','data':{}} envelope."""
    success_codes = success_codes or [200, 201, 204]
    if response.status_code in success_codes:
        if response.status_code == 204 or not response.content:
            return None
        body = response.json()
        # EVE-NG sometimes returns HTTP 200 with a failure body — check application status.
        if isinstance(body, dict) and body.get("status") == "fail":
            eve_code = body.get("code", "")
            msg = body.get("message") or str(body)
            raise EVEError("EVE_SERVER_ERROR", f"EVE error {eve_code}: {msg}", response.status_code)
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    code = _HTTP_ERROR_MAP.get(response.status_code, "EVE_SERVER_ERROR")
    try:
        body = response.json()
        msg = body.get("message") or body.get("data") or str(body)
        if isinstance(msg, dict):
            msg = json.dumps(msg)
    except Exception:
        msg = response.text or f"HTTP {response.status_code}"
    raise EVEError(code, str(msg), response.status_code)


def _serialize_payload(payload: Any) -> str:
    try:
        from netclaw_tokens.gcf_serializer import serialize_response

        return serialize_response(payload, use_session=True, use_delta=True)["encoded_data"]
    except Exception:
        return json.dumps(payload, indent=2, default=str)


def success_response(
    data: Any = None,
    message: str | None = None,
    count: int | None = None,
    total_count: int | None = None,
    pagination: dict[str, Any] | None = None,
) -> str:
    result: dict = {"success": True}
    if data is not None:
        result["data"] = data
    if message:
        result["message"] = message
    if count is not None:
        result["count"] = count
    if total_count is not None:
        result["total_count"] = total_count
    if pagination is not None:
        result["pagination"] = pagination
    return _serialize_payload(result)


def error_response(error: Exception) -> str:
    if isinstance(error, EVEError):
        return _serialize_payload(error.to_dict())
    return _serialize_payload({
        "success": False,
        "error": str(error),
        "error_code": "EVE_SERVER_ERROR",
        "status_code": 500,
    })


# =============================================================================
# Pagination
# =============================================================================

def normalize_pagination(page: int = 1, page_size: int = 50) -> tuple[int, int]:
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 50), EVE_MAX_PAGE_SIZE))
    return page, page_size


def paginate_sequence(items: list[Any], page: int = 1, page_size: int = 50) -> tuple[list[Any], dict[str, Any]]:
    page, page_size = normalize_pagination(page, page_size)
    total_count = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    sliced = items[start:end]
    return sliced, {
        "page": page,
        "page_size": page_size,
        "returned": len(sliced),
        "total_count": total_count,
        "total_pages": max(1, (total_count + page_size - 1) // page_size),
        "has_next": end < total_count,
    }


# =============================================================================
# GAIT Audit Logging
# =============================================================================

def with_gait_logging(operation: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log.info("GAIT: Starting %s", operation)
            try:
                result = func(*args, **kwargs)
                log.info("GAIT: Completed %s", operation)
                return result
            except Exception as exc:
                log.error("GAIT: Failed %s — %s", operation, exc)
                raise
        return wrapper
    return decorator


# =============================================================================
# Path and ID Helpers
# =============================================================================

def normalize_lab_path(path: str) -> str:
    """Ensure lab path has leading slash and .unl extension."""
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith(".unl"):
        path += ".unl"
    return path


def split_lab_path(path: str) -> tuple[str, str]:
    """Return (folder, normalized lab path)."""
    lab_path = normalize_lab_path(path)
    folder = os.path.dirname(lab_path) or "/"
    return folder, lab_path


def normalize_folder_path(path: str) -> str:
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    return path


def collect_labs(client: EVEClient, folder: str = "/") -> list:
    """Recursively collect all .unl lab paths from folder tree."""
    folder = normalize_folder_path(folder)
    try:
        raw = client.get(f"/api/folders{folder}").json()
    except Exception:
        return []
    payload = raw.get("data") if isinstance(raw, dict) else raw
    if not isinstance(payload, dict):
        return []
    labs: list = []
    prefix = "" if folder == "/" else folder.rstrip("/")
    for lab in payload.get("labs") or []:
        name = lab.get("file") or lab.get("name", "")
        if name:
            labs.append(f"{prefix}/{name}")
    for sub in payload.get("folders") or []:
        fname = sub.get("name", "")
        if fname and fname not in (".", ".."):
            sub_path = f"/{fname}" if folder == "/" else f"{folder.rstrip('/')}/{fname}"
            labs.extend(collect_labs(client, sub_path))
    return labs


def resolve_node_id(client: EVEClient, lab_path: str, node_ref: str) -> str:
    """Resolve node name or numeric string to numeric ID string."""
    if str(node_ref).isdigit():
        return str(node_ref)
    response = client.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes", no_cache=True)
    data = handle_eve_response(response)
    if isinstance(data, dict):
        for nid, node in data.items():
            if isinstance(node, dict) and node.get("name", "").lower() == str(node_ref).lower():
                return str(nid)
        available = [n.get("name", nid) for nid, n in data.items() if isinstance(n, dict)]
    else:
        available = []
    raise EVEError("EVE_NOT_FOUND", f"Node '{node_ref}' not found. Available: {available}", 404)


def resolve_network_id(client: EVEClient, lab_path: str, net_ref: str) -> str:
    """Resolve network name or numeric string to numeric ID string."""
    if str(net_ref).isdigit():
        return str(net_ref)
    response = client.get(f"/api/labs{normalize_lab_path(lab_path)}/networks")
    data = handle_eve_response(response)
    if isinstance(data, dict):
        for nid, net in data.items():
            if isinstance(net, dict) and net.get("name", "").lower() == str(net_ref).lower():
                return str(nid)
        available = [n.get("name", nid) for nid, n in data.items() if isinstance(n, dict)]
    else:
        available = []
    raise EVEError("EVE_NOT_FOUND", f"Network '{net_ref}' not found. Available: {available}", 404)


def node_is_running(node: dict) -> bool:
    try:
        return int(node.get("status", 0)) != 0
    except Exception:
        return False


def _is_local_eve_url(base_url: str) -> bool:
    """Return True when this MCP server can safely inspect local EVE runtime files."""
    try:
        host = (urlparse(base_url).hostname or "").lower()
    except Exception:
        return False
    return host in {"127.0.0.1", "localhost", "::1"}


def _local_lab_file(lab_path: str) -> Path:
    return Path("/opt/unetlab/labs") / normalize_lab_path(lab_path).lstrip("/")


def local_lab_uuid(lab_path: str) -> str | None:
    """Read the local .unl lab UUID, if available."""
    try:
        root = ET.parse(_local_lab_file(lab_path)).getroot()
        return root.get("id")
    except Exception:
        return None


def _proc_cwd_matches(node_dir: Path) -> bool:
    """Check whether any live process has cwd inside this node runtime dir."""
    node_dir_s = str(node_dir)
    try:
        entries = list(Path("/proc").iterdir())
    except Exception:
        return False
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            cwd = os.readlink(entry / "cwd")
        except Exception:
            continue
        if cwd == node_dir_s or cwd.startswith(node_dir_s + os.sep):
            return True
    return False


def local_node_runtime_running(lab_path: str, node_id: str) -> bool | None:
    """Return local runtime truth for a node, or None when not inspectable.

    EVE's API can leak running status across labs that reuse the same node IDs.
    Local runtime state is scoped by lab UUID under /opt/unetlab/tmp/0/<uuid>/<node_id>,
    so use that as the source of truth when talking to the local EVE host.
    """
    lab_uuid = local_lab_uuid(lab_path)
    if not lab_uuid:
        return None
    node_dir = Path("/opt/unetlab/tmp/0") / lab_uuid / str(node_id)
    if not node_dir.exists():
        return False
    return _proc_cwd_matches(node_dir)


def correct_local_node_status(client: EVEClient, lab_path: str, node_id: str, node: dict) -> dict:
    """Patch EVE API node status with local runtime truth when possible."""
    if not _is_local_eve_url(client.base_url):
        return node
    runtime_running = local_node_runtime_running(lab_path, node_id)
    if runtime_running is None:
        return node
    corrected = dict(node)
    if runtime_running:
        if not node_is_running(corrected):
            corrected["status"] = 2
    else:
        corrected["status"] = 0
        corrected.pop("url", None)
    corrected["running"] = runtime_running
    corrected["runtime_status_source"] = "local_runtime"
    return corrected


def correct_local_nodes_status(client: EVEClient, lab_path: str, nodes: dict) -> dict:
    if not isinstance(nodes, dict):
        return nodes
    return {
        str(nid): correct_local_node_status(client, lab_path, str(nid), node) if isinstance(node, dict) else node
        for nid, node in nodes.items()
    }


def ensure_nodes_stopped_for_link_edit(client: EVEClient, lab_path: str, node_refs: list[str], polls: int = 8, interval: float = 2.0) -> dict:
    """Refuse link edits when any referenced node is still running after polling."""
    last = {}
    for _ in range(polls):
        response = client.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes", no_cache=True)
        data = handle_eve_response(response)
        if not isinstance(data, dict):
            return {}
        last = data
        by_id = {str(nid): node for nid, node in data.items() if isinstance(node, dict)}
        by_name = {str(node.get("name", "")).lower(): (str(nid), node) for nid, node in data.items() if isinstance(node, dict)}
        running = []
        for ref in node_refs:
            ref_s = str(ref)
            if ref_s.isdigit():
                node = by_id.get(ref_s)
                node_id = ref_s
            else:
                resolved = by_name.get(ref_s.lower())
                if not resolved:
                    continue
                node_id, node = resolved
            if node and node_is_running(node):
                running.append({"node": node.get("name", node_id), "node_id": node_id, "status": node.get("status")})
        if not running:
            return data
        time.sleep(interval)
    names = ", ".join(item["node"] for item in running)
    raise EVEError(
        "EVE_CONFLICT",
        f"Link edits require affected endpoint nodes to be stopped first. Still running: {names}",
        409,
    )


def poll_node_status(client: EVEClient, lab_path: str, node_id: str,
                     expect_running: bool, polls: int = 5, interval: float = 2.0) -> dict:
    """Poll until node reaches expected state. Returns final nodes dict."""
    last: dict = {}
    for _ in range(polls):
        try:
            data = handle_eve_response(client.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes", no_cache=True))
            if isinstance(data, dict):
                data = correct_local_nodes_status(client, lab_path, data)
                last = data
                node = data.get(str(node_id), {})
                if isinstance(node, dict) and node_is_running(node) == expect_running:
                    break
        except Exception:
            pass
        time.sleep(interval)
    return last


def build_verification(action: str, node_id: str, before: dict, after: dict) -> dict:
    bn = before.get(str(node_id), {})
    an = after.get(str(node_id), {})
    before_run = node_is_running(bn) if isinstance(bn, dict) else None
    after_run  = node_is_running(an) if isinstance(an, dict) else None
    verified = bool(after_run) if action == "start" else (after_run is False)
    return {
        "verified": verified,
        "before_running": before_run,
        "after_running": after_run,
        "note": "EVE-NG node status can lag; polling applied after action.",
    }


def get_console_port(client: EVEClient, lab_path: str, node_id: str) -> int:
    """Get console port from node data; fall back to 32768+id formula."""
    try:
        data = handle_eve_response(client.get(f"/api/labs{normalize_lab_path(lab_path)}/nodes/{node_id}", no_cache=True))
        if isinstance(data, dict):
            port = data.get("console")
            if port and int(port) > 0:
                return int(port)
    except Exception:
        pass
    return 32768 + int(node_id)


# =============================================================================
# Client Singleton
# =============================================================================

_client: Optional[EVEClient] = None


def get_client() -> EVEClient:
    global _client
    if _client is None:
        if not EVE_USER or not EVE_PASSWORD:
            raise EVEError("EVE_AUTH_FAILED",
                           "EVE_USER and EVE_PASSWORD environment variables are required", 401)
        _client = EVEClient(EVE_URL, EVE_USER, EVE_PASSWORD, EVE_VERIFY_SSL, EVE_SESSION_TTL, EVE_HTML5)
    return _client
