"""Loopback Streamable-HTTP mock of an MCP endpoint. No network, no credentials."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

GOOD_KEY = "test-canary-key-0123456789"


def make(tools=None, sse=False, require_key=GOOD_KEY, status_override=None):
    seen = {"auth": [], "methods": []}
    tools = [] if tools is None else tools

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            seen["auth"].append(self.headers.get("Authorization"))
            seen["methods"].append(body.get("method"))
            if status_override:
                self.send_response(status_override); self.end_headers(); return
            if self.headers.get("Authorization") != "Bearer " + require_key:
                data = json.dumps({"title": "unauthenticated", "echo": self.headers.get("Authorization")}).encode()
                self.send_response(401)
                self.send_header("Content-Type", "application/problem+json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers(); self.wfile.write(data); return
            method = body.get("method")
            if "id" not in body:
                self.send_response(202); self.end_headers(); return
            result = {"protocolVersion": "2025-03-26", "capabilities": {}} if method == "initialize" else {"tools": tools}
            payload = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result})
            if sse:
                data = ("event: message\ndata: " + payload + "\n\n").encode(); ctype = "text/event-stream"
            else:
                data = payload.encode(); ctype = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Mcp-Session-Id", "sess-1")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d/mcp" % srv.server_address[1], seen
