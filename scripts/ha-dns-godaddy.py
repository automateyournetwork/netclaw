#!/usr/bin/env python3
"""GoDaddy A-record plan/apply for the spec 182 Borders (T011).

plan   (default) GET only: reads zone A records and reports create / noop / CONFLICT per name.
apply  needs --apply: PUT A records; refuses CONFLICT (existing name with another target) and bad names.
Names: <code>-<id6>.automateyournetwork.com, code in nne1|nne2|ew1|ase1, id6 = 6 lowercase hex.
Credentials only from ~/.openclaw/.env: GODADDY_PAT (Bearer) or GODADDY_API_KEY + GODADDY_API_SECRET (sso-key).
Secrets are never printed. Never read an exit code through a pipe.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

ZONE = "automateyournetwork.com"
API = "https://api.godaddy.com"
CODES = ("nne1", "nne2", "ew1", "ase1")
LABEL_RE = re.compile(r"^(nne1|nne2|ew1|ase1)-[0-9a-f]{6}$")
TTL = 600


def load_env(path=None):
    path = path or os.path.expanduser("~/.openclaw/.env")
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip().removeprefix("export ").strip()] = v.strip().strip("'\"")
    except OSError:
        pass
    for k in ("GODADDY_PAT", "GODADDY_API_KEY", "GODADDY_API_SECRET"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def auth_header(env):
    if env.get("GODADDY_PAT"):
        return "Bearer " + env["GODADDY_PAT"]
    if env.get("GODADDY_API_KEY") and env.get("GODADDY_API_SECRET"):
        return "sso-key " + env["GODADDY_API_KEY"] + ":" + env["GODADDY_API_SECRET"]
    return None


def parse_id6(items):
    out = {}
    for item in items or []:
        code, _, id6 = item.partition("=")
        label = f"{code}-{id6}"
        if code not in CODES or not LABEL_RE.match(label):
            raise ValueError(f"bad border id: {item!r} (want code in {CODES} and 6 lowercase hex)")
        out[code] = id6
    return out


def parse_ips(items):
    out = {}
    for item in items or []:
        code, _, ip = item.partition("=")
        if code not in CODES or not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
            raise ValueError(f"bad ip mapping: {item!r}")
        out[code] = ip
    return out


def wanted(id6, ips):
    """[(label, fqdn, ip)]; refuses names outside the pattern."""
    recs = []
    for code in CODES:
        if code not in id6 and code not in ips:
            continue  # only the codes supplied are managed (R09A uses nne1+nne2)
        if code not in id6 or code not in ips:
            raise ValueError(f"need both --id6 and --ip for {code}")
        label = f"{code}-{id6[code]}"
        if not LABEL_RE.match(label):
            raise ValueError(f"name refused: {label}")
        recs.append((label, f"{label}.{ZONE}", ips[code]))
    return recs


class Client:
    def __init__(self, header, opener=urllib.request.urlopen):
        self.header, self.opener = header, opener

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(API + path, data=data, method=method, headers={
            "Authorization": self.header, "Accept": "application/json", "Content-Type": "application/json"})
        try:
            with self.opener(req, timeout=20) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, None  # body deliberately not echoed

    def a_records(self):
        status, body = self._req("GET", f"/v1/domains/{ZONE}/records/A")
        if status != 200:
            raise RuntimeError(f"GoDaddy GET rejected (http {status})")
        return {r["name"]: r["data"] for r in body or []}

    def put_a(self, label, ip):
        status, _ = self._req("PUT", f"/v1/domains/{ZONE}/records/A/{label}", [{"data": ip, "ttl": TTL}])
        return status


def plan_actions(existing, recs):
    acts = []
    for label, fqdn, ip in recs:
        cur = existing.get(label)
        acts.append((label, fqdn, ip, "noop" if cur == ip else ("create" if cur is None else "CONFLICT")))
    return acts


def main(argv=None, client=None, env=None, out=print):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("plan", "apply"), nargs="?", default="plan")
    ap.add_argument("--id6", action="append", help="code=hex6, e.g. nne1=3fa9c2 (repeat for all 3)")
    ap.add_argument("--ip", action="append", help="code=ipv4 (repeat for all 3)")
    ap.add_argument("--apply", action="store_true", help="required for apply (DNS writes)")
    args = ap.parse_args(argv)
    try:
        recs = wanted(parse_id6(args.id6), parse_ips(args.ip))
    except ValueError as e:
        out(f"REFUSED: {e}")
        return 2
    if client is None:
        header = auth_header(env if env is not None else load_env())
        if not header:
            out("No GoDaddy credential in ~/.openclaw/.env (GODADDY_PAT or GODADDY_API_KEY+GODADDY_API_SECRET).")
            return 3
        client = Client(header)
    try:
        acts = plan_actions(client.a_records(), recs)
    except RuntimeError as e:
        out(f"ERROR: {e}")
        return 1
    for label, fqdn, ip, act in acts:
        out(f"  [{act:8s}] A {fqdn} -> {ip} ttl {TTL}")
    if any(a[3] == "CONFLICT" for a in acts):
        out("REFUSED: a name already exists with another target; nothing written.")
        return 2
    if args.cmd == "plan" or not args.apply:
        out("plan only (GET); no DNS written." + ("" if args.cmd == "plan" else " apply needs --apply."))
        return 0 if args.cmd == "plan" else 2
    for label, fqdn, ip, act in acts:
        if act == "create":
            st = client.put_a(label, ip)
            out(f"  PUT {fqdn}: http {st}")
            if st not in (200, 201):
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
