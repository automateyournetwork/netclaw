#!/usr/bin/env python3
"""Fixed-route relay from an isolated agent network to the trusted host.

No credential, upstream URL or filesystem path is accepted from a request.
The host rechecks operation capabilities and owns all inference/tool claims.
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import socket
import stat
from pathlib import Path


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost", timeout=180)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def trusted_socket(value):
    path = Path(value)
    info = path.lstat()
    if (str(path) != "/broker/broker.sock" or path.resolve() != path
            or not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise ValueError("Invalid trusted socket")
    return str(path)


class Relay(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        if self.path not in ("/v1/chat/completions", "/mcp"):
            self.reject(404)
            return
        if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
            self.reject(400)
            return
        try:
            size = int(self.headers["Content-Length"])
        except (ValueError, TypeError):
            self.reject(400)
            return
        if not 1 <= size <= 1048576:
            self.reject(413)
            return
        allowed = ("authorization", "content-type", "accept", "mcp-protocol-version")
        headers = {}
        for key in allowed:
            values = self.headers.get_all(key, [])
            if len(values) > 1:
                self.reject(400)
                return
            if values:
                headers[key] = values[0]
        if not headers.get("content-type", "").startswith("application/json"):
            self.reject(415)
            return
        body = self.rfile.read(size)
        if len(body) != size:
            self.reject(400)
            return
        # The MCP SDK's enabled localhost rebinding defense requires an explicit
        # port in its allowed authority pattern. This is a fixed virtual HTTP
        # authority over AF_UNIX, never a caller-selected host or TCP connection.
        headers["Host"] = "localhost:80" if SOCKET else "127.0.0.1:" + str(PORT)
        # Host is constant, port is trusted container startup configuration.
        connection = UnixHTTPConnection(SOCKET) if SOCKET else http.client.HTTPConnection("host.docker.internal", PORT, timeout=180)
        try:
            connection.request("POST", self.path, body, headers)
            response = connection.getresponse()
            output = response.read(2097153)
            if len(output) > 2097152:
                self.reject(502)
                return
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(output)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(output)
        except Exception:
            self.reject(502)
        finally:
            connection.close()

    def reject(self, code):
        self.close_connection = True
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def setup(self):
        super().setup()
        self.connection.settimeout(180)

    def log_message(self, *args):
        pass  # No request or bearer logging.


SOCKET = None


if __name__ == "__main__":
    if "NETCLAW_TRUSTED_SOCKET" in os.environ:
        if "NETCLAW_TRUSTED_PORT" in os.environ: raise SystemExit("Ambiguous trusted transport")
        SOCKET = trusted_socket(os.environ["NETCLAW_TRUSTED_SOCKET"])
        PORT = None
    else:
        PORT = int(os.environ["NETCLAW_TRUSTED_PORT"])
        if not 1 <= PORT <= 65535:
            raise SystemExit("Invalid trusted port")
    ThreadingHTTPServer(("0.0.0.0", 8090), Relay).serve_forever()
