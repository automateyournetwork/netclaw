#!/usr/bin/env python3
# Pure-stdlib UniFi Integration API -> Prometheus exporter. No pip deps.
# Canonical Docker source: deploy/home/adapters/unifi/exporter.py
# Kustomize cannot load files outside base/; keep this copy in sync.
import json, os, ssl, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ["UNIFI_HOST"].rstrip("/")
API_KEY = os.environ["UNIFI_API_KEY"]
SITE_LABEL = os.environ.get("SITE_LABEL", "home")
PORT = int(os.environ.get("LISTEN_PORT", "9899"))
GUEST_TYPES = {t.strip().upper() for t in os.environ.get("GUEST_ACCESS_TYPES", "GUEST,HOTSPOT").split(",") if t.strip()}
BASE = HOST + "/proxy/network/integration/v1"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def api(path):
    req = urllib.request.Request(BASE + path, headers={"X-API-Key": API_KEY, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
        return json.loads(r.read().decode())

def api_paged(path):
    items, offset = [], 0
    while True:
        sep = "&" if "?" in path else "?"
        page = api(f"{path}{sep}offset={offset}&limit=200")
        data = page.get("data", [])
        items.extend(data)
        total = page.get("totalCount", len(items))
        offset += len(data)
        if not data or offset >= total:
            break
    return items

def esc(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"') if v is not None else ""

def role_of(dev):
    feats = dev.get("features") or {}
    if "accessPoint" in feats:
        return "ap"
    if "switching" in feats:
        return "switch"
    return "gateway"

def collect():
    lines, ok = [], 1
    def emit(name, labels, value):
        lbl = ",".join(f'{k}="{esc(v)}"' for k, v in labels.items())
        lines.append(f'{name}{{{lbl}}} {value}')
    try:
        sites = api("/sites").get("data", [])
        for site in sites:
            sid = site["id"]
            sname = site.get("internalReference") or site.get("name") or "default"
            base_lbl = {"site": SITE_LABEL, "unifi_site": sname}
            devices = api_paged(f"/sites/{sid}/devices")
            dev_by_id = {}
            for d in devices:
                did = d.get("id")
                dev_by_id[did] = d
                role = role_of(d)
                l = dict(base_lbl, device=d.get("name"), model=d.get("model"), role=role, mac=d.get("macAddress"))
                emit("unifi_device_up", l, 1 if str(d.get("state")).upper() == "ONLINE" else 0)
                try:
                    st = api(f"/sites/{sid}/devices/{did}/statistics/latest")
                except Exception:
                    st = {}
                if st.get("cpuUtilizationPct") is not None:
                    emit("unifi_device_cpu_pct", l, st["cpuUtilizationPct"])
                if st.get("memoryUtilizationPct") is not None:
                    emit("unifi_device_memory_pct", l, st["memoryUtilizationPct"])
                if st.get("uptimeSec") is not None:
                    emit("unifi_device_uptime_seconds", l, st["uptimeSec"])
                up = st.get("uplink") or {}
                if up.get("rxRateBps") is not None:
                    emit("unifi_device_uplink_rx_bps", l, up["rxRateBps"])
                if up.get("txRateBps") is not None:
                    emit("unifi_device_uplink_tx_bps", l, up["txRateBps"])
                for radio in ((st.get("interfaces") or {}).get("radios") or []):
                    if radio.get("txRetriesPct") is not None:
                        band = f'{radio.get("frequencyGHz","?")}GHz'
                        emit("unifi_radio_tx_retries_pct", dict(base_lbl, device=d.get("name"), band=band), radio["txRetriesPct"])
            # clients: totals + per-AP association
            clients = api_paged(f"/sites/{sid}/clients")
            wireless = wired = guest = 0
            per_ap = {}
            for c in clients:
                ctype = str(c.get("type")).upper()
                if ctype == "WIRELESS":
                    wireless += 1
                    ap_id = c.get("uplinkDeviceId")
                    if ap_id:
                        per_ap[ap_id] = per_ap.get(ap_id, 0) + 1
                elif ctype == "WIRED":
                    wired += 1
                acc = (c.get("access") or {}).get("type")
                if acc and str(acc).upper() in GUEST_TYPES:
                    guest += 1
            emit("unifi_site_clients_total", base_lbl, len(clients))
            emit("unifi_site_clients_wireless", base_lbl, wireless)
            emit("unifi_site_clients_wired", base_lbl, wired)
            emit("unifi_site_clients_guest", base_lbl, guest)
            for ap_id, n in per_ap.items():
                d = dev_by_id.get(ap_id, {})
                emit("unifi_ap_clients", dict(base_lbl, device=d.get("name") or ap_id, mac=d.get("macAddress")), n)
    except Exception as e:
        ok = 0
        lines.append(f'# collect error: {esc(e)}')
    header = [
        "# HELP unifi_up 1 if the exporter reached the UniFi controller on the last scrape",
        "# TYPE unifi_up gauge",
        f'unifi_up{{site="{SITE_LABEL}"}} {ok}',
    ]
    return "\n".join(header + lines) + "\n"

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/metrics"):
            body = collect().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(200); self.end_headers()
            self.wfile.write(b"unifi-exporter: GET /metrics\n")
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print(f"unifi-exporter listening on :{PORT}, target {BASE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
