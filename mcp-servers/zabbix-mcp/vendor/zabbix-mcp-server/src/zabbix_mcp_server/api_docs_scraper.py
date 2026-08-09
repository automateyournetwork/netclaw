"""
Zabbix API Docs Scraper
Retrieves description and parameters for a Zabbix method from official docs
and returns them as structured text readable by an LLM.
"""

import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from .client import get_zabbix_client


def _get_docs_base(version: str = "current") -> str:
    return f"https://www.zabbix.com/documentation/{version}/en/manual/api/reference"


def _get_user_agent() -> str:
    return f"ZabbixMCP/v2 (Documentation Fetcher; +https://github.com/mpeirone/zabbix-mcp-server)"


HEADERS = {"User-Agent": _get_user_agent()}


_LINK_RE = re.compile(
    r'/manual/api/reference/([a-z][a-z0-9_]+)/([a-z][a-z0-9_]+)(?=["\s])'
)

_scrape_cache: dict[str, dict[str, list[str]]] = {}


def _resolve_version(version: str = None) -> str:
    """Resolve Zabbix version from parameter or server.

    Args:
        version: Optional version string (e.g., "7.0"). If None, uses server version.

    Returns:
        Resolved version string.
    """
    if version is not None:
        return version

    try:
        client = get_zabbix_client()
        server_version = str(getattr(client, "version", None))

        if server_version:
            parts = server_version.split(".")
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
    except Exception:
        # Fall back to "current" if client initialization fails
        pass

    return "current"


def scrape_zabbix_api(version: str = None, timeout: int = 10) -> dict[str, list[str]]:
    """Scrape Zabbix API reference and return {resource: [methods]}.

    Args:
        version: Zabbix version, e.g., "7.0", "6.0". If None, uses server version.
        timeout: HTTP timeout in seconds

    Returns:
        {"host": ["create", "delete", "get", ...], "item": [...], ...}
    """
    version = _resolve_version(version)

    if version in _scrape_cache:
        return _scrape_cache[version]

    url = _get_docs_base(version)
    try:
        with requests.get(url, headers=HEADERS, timeout=timeout) as response:
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code} for {url}")
            response_text = response.text
    except requests.RequestException as exc:
        raise RuntimeError(f"Network error: {exc}") from exc

    result: dict[str, list[str]] = {}
    for resource, method in _LINK_RE.findall(response_text):
        if method == "object":
            continue
        methods = result.setdefault(resource, [])
        if method not in methods:
            methods.append(method)

    result = dict(sorted(result.items()))
    _scrape_cache[version] = result
    return result


@dataclass
class Parameter:
    name: str
    type: str
    required: bool
    description: str


@dataclass
class ZabbixMethodDocs:
    method: str
    description: str
    parameters: list[Parameter] = field(default_factory=list)
    returns: str = ""
    doc_url: str = ""


def _build_url(method: str, version: str = "current") -> str:
    parts = method.strip().lower().split(".", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid format: '{method}'. Expected 'object.action' (e.g. host.get)"
        )
    obj, action = parts
    base = _get_docs_base(version)
    return f"{base}/{obj}/{action}"


def _parse_description(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1:
        for sibling in h1.find_next_siblings():
            if sibling.name == "p":
                text = sibling.get_text(separator=" ", strip=True)
                if text:
                    return text
    for p in soup.find_all("p"):
        text = p.get_text(separator=" ", strip=True)
        if len(text) > 40:
            return text
    return ""


def _clean_description(desc: str) -> str:
    desc = desc.replace(" .", ".").replace(" ,", ",")
    if "Possible values:" in desc:
        parts = desc.split("Possible values:", 1)
        desc = parts[0].strip()
        if len(parts) > 1:
            values = parts[1].strip()
            desc = f"{desc}\n  Possible values: {values}"
    return desc


def _parse_parameters_table(table: BeautifulSoup) -> list[Parameter]:
    params = []
    rows = table.find_all("tr")
    if not rows:
        return params

    headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
    col = {
        "name": next(
            (i for i, h in enumerate(headers) if "parameter" in h or "name" in h), 0
        ),
        "type": next((i for i, h in enumerate(headers) if "type" in h), 1),
        "required": next(
            (i for i, h in enumerate(headers) if "mandatory" in h or "required" in h),
            None,
        ),
        "desc": next((i for i, h in enumerate(headers) if "description" in h), -1),
    }

    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        def cell_text(idx):
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx].get_text(separator=" ", strip=True)

        name = cell_text(col["name"])
        if not name:
            continue

        ptype = cell_text(col["type"]) or "unknown"
        desc = _clean_description(cell_text(col["desc"]))

        if col["required"] is not None:
            required = cell_text(col["required"]).lower() in (
                "yes",
                "true",
                "1",
                "mandatory",
            )
        else:
            required = "(required)" in desc.lower() or "(mandatory)" in desc.lower()

        params.append(
            Parameter(name=name, type=ptype, required=required, description=desc)
        )

    return params


def _parse_return_value(soup: BeautifulSoup) -> str:
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "return" in heading.get_text(strip=True).lower():
            parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ["h2", "h3", "h4"]:
                    break
                if sibling.name == "ul":
                    for li in sibling.find_all("li", recursive=False):
                        text = li.get_text(separator=" ", strip=True)
                        if text:
                            parts.append(f"- {text}")
                elif sibling.name == "p":
                    text = sibling.get_text(separator=" ", strip=True)
                    if text:
                        parts.append(text)
            return "\n".join(parts)
    return ""


def get_zabbix_api_docs(
    method: str, version: str = "current", timeout: int = 10
) -> ZabbixMethodDocs:
    """Fetches raw documentation data for a Zabbix method."""
    url = _build_url(method, version)
    try:
        with requests.get(url, headers=HEADERS, timeout=timeout) as response:
            if response.status_code == 404:
                raise RuntimeError(f"Method '{method}' not found ({url})")
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code} for {url}")
            response_text = response.text
    except requests.RequestException as e:
        raise RuntimeError(f"Network error: {e}") from e

    soup = BeautifulSoup(response_text, "html.parser")
    description = _parse_description(soup)

    all_params: list[Parameter] = []
    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue
        header_text = header_row.get_text(strip=True).lower()
        if "parameter" in header_text or "type" in header_text:
            all_params.extend(_parse_parameters_table(table))

    return ZabbixMethodDocs(
        method=method,
        description=description,
        parameters=all_params,
        returns=_parse_return_value(soup),
        doc_url=url,
    )


def get_method_docs(method: str, version: str = None, timeout: int = 10) -> str:
    """Returns Zabbix method documentation as structured text
    optimized for reading and interpretation by an LLM.

    Args:
        method: Zabbix method in 'object.action' format, e.g. 'host.get'
        version: Zabbix version, e.g., '7.0', '6.0'. If None, uses server version.
        timeout: HTTP timeout in seconds

    Returns:
        Text string with description, parameters and return value.

    Example:
        >>> text = get_method_docs("host.get")
        >>> text = get_method_docs("host.get", version="7.0")
        >>> print(text)
    """
    version = _resolve_version(version)

    docs = get_zabbix_api_docs(method, version, timeout)

    required = [p for p in docs.parameters if p.required]
    optional = [p for p in docs.parameters if not p.required]

    lines = [
        f"METHOD: {docs.method}",
        f"URL: {docs.doc_url}",
        "",
        f"DESCRIPTION:",
        docs.description or "Not available.",
        "",
    ]

    if required:
        lines.append("REQUIRED PARAMETERS:")
        for p in required:
            lines.append(f"  {p.name} ({p.type}):")
            for line in p.description.split("\n"):
                lines.append(f"    {line}")
            lines.append("")

    if optional:
        lines.append("OPTIONAL PARAMETERS:")
        for p in optional:
            lines.append(f"  {p.name} ({p.type}):")
            for line in p.description.split("\n"):
                lines.append(f"    {line}")
            lines.append("")

    if docs.returns:
        lines.append("RETURN VALUE:")
        for line in docs.returns.split("\n"):
            lines.append(f"  {line}")
        lines.append("")

    return "\n".join(lines)
