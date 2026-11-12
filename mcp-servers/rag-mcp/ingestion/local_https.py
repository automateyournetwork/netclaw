"""Bounded HTTP/2 negotiation for local HTTPS appliances using optional curl."""

import ipaddress
import shutil
import subprocess
import tempfile
from functools import lru_cache
from urllib.parse import urlparse


def _local_https(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return host == "localhost" or host.endswith((".local", ".lan", ".home.arpa", ".internal"))


@lru_cache(maxsize=1)
def _http2_curl():
    exe = shutil.which("curl")
    if exe:
        result = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)
        if any("HTTP2" in line.split() for line in result.stdout.splitlines() if line.startswith("Features:")):
            return exe
    return None


def fetch_local_https(url, timeout, max_bytes, verify_ssl):
    """Return None when the ordinary HTTP transport should handle the URL."""
    if not _local_https(url):
        return None
    exe = _http2_curl()
    if not exe:
        return None
    # --disable must be first to keep ~/.curlrc from changing transport policy.
    # Keep the decoded body on a pipe: Content-Length and --max-filesize alone
    # cannot cap a compressed response or chunked response on older curl builds.
    args = [exe, "--disable", "--globoff", "--silent", "--http2", "--compressed",
            "--proto", "=https", "--proto-redir", "=https", "--noproxy", "*",
            "--max-time", str(timeout), "--max-filesize", str(max_bytes),
            "--write-out", "%{stderr}%{response_code} %{content_type}"]
    if verify_ssl:
        args.extend(["--location", "--max-redirs", "20"])
    else:
        args.append("--insecure")
    with tempfile.TemporaryFile() as metadata:
        with subprocess.Popen([*args, "--", url], stdout=subprocess.PIPE, stderr=metadata) as proc:
            try:
                body = proc.stdout.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ValueError(f"Document exceeds the {max_bytes}-byte download limit")
            except BaseException:
                proc.kill()
                raise
            code = proc.wait()
        metadata.seek(0)
        status, _, media = metadata.read(4096).decode(errors="replace").partition(" ")
    if code == 63:
        raise ValueError(f"Document exceeds the {max_bytes}-byte download limit")
    if code:
        raise ValueError(f"Local HTTPS fetch failed (curl exit {code})")
    if status[:1] != "2":
        raise ValueError(f"Local HTTPS fetch returned HTTP {status}")
    return body, media.split(";")[0].strip().lower()
