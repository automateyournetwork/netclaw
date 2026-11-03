#!/usr/bin/env python3
"""Fixed-route relay from an isolated agent network to the trusted host.

No credential, upstream URL or filesystem path is accepted from a request.
The host rechecks operation capabilities and owns all inference/tool claims.
"""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os


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
        headers["Host"] = "127.0.0.1:" + str(PORT)
        # Host is constant, port is trusted container startup configuration.
        connection = http.client.HTTPConnection("host.docker.internal", PORT, timeout=180)
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


if __name__ == "__main__":
    PORT = int(os.environ["NETCLAW_TRUSTED_PORT"])
    if not 1 <= PORT <= 65535:
        raise SystemExit("Invalid trusted port")
    ThreadingHTTPServer(("0.0.0.0", 8090), Relay).serve_forever()
