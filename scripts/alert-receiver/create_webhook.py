#!/usr/bin/env python3
"""One-shot: create the Nautobot intent-reconcile webhook.

Reads NAUTOBOT_URL/NAUTOBOT_TOKEN from netclaw/.env and the shared
NAUTOBOT_WEBHOOK_SECRET from scripts/alert-receiver/.env, then creates (or
reports) the webhook pointing at the alert receiver. Safe to re-run.
"""
import json
import ssl
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def read_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


root_env = read_env(REPO / ".env")
recv_env = read_env(REPO / "scripts/alert-receiver/.env")

nb = (root_env.get("NAUTOBOT_URL") or "https://192.168.3.253").rstrip("/")
tok = root_env.get("NAUTOBOT_TOKEN", "")
secret = recv_env.get("NAUTOBOT_WEBHOOK_SECRET", "")

assert tok, "NAUTOBOT_TOKEN missing"
assert secret, "NAUTOBOT_WEBHOOK_SECRET missing"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        nb + path, data=data, method=method,
        headers={"Authorization": "Token " + tok,
                 "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]


# Idempotency: does it already exist?
_, existing = api("GET", "/api/extras/webhooks/?name=netclaw-intent-reconcile")
if isinstance(existing, dict) and existing.get("count"):
    w = existing["results"][0]
    print("ALREADY EXISTS id=%s enabled=%s url=%s" % (w.get("id"), w.get("enabled"), w.get("payload_url")))
    raise SystemExit(0)

payload = {
    "name": "netclaw-intent-reconcile",
    "content_types": ["dcim.interface"],
    "enabled": True,
    "type_create": True, "type_update": True, "type_delete": True,
    "payload_url": "http://192.168.3.252:8099/nautobot-webhook",
    "http_method": "POST", "http_content_type": "application/json",
    "secret": secret, "ssl_verification": False,
}
status, d = api("POST", "/api/extras/webhooks/", payload)
print("HTTP", status)
if isinstance(d, dict):
    print("id:", d.get("id"), "| name:", d.get("name"), "| enabled:", d.get("enabled"))
    print("url:", d.get("payload_url"))
    print("events: create=%s update=%s delete=%s" % (d.get("type_create"), d.get("type_update"), d.get("type_delete")))
    print("content_types:", d.get("content_types"))
else:
    print(d)
