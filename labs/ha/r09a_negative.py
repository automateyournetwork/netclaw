#!/usr/bin/env python3
"""R09A negative isolation suite (spec 183 FR-013, SC-003).

Each case runs a deliberate escape or violation INSIDE a node sandbox via `openshell sandbox exec NAME -- ...` and records
whether it was refused. Every dangerous command prints a fixed marker (`WROTE`, `CONNECTED`, `FOUND:...`) only if the action
actually succeeded, so the verdict never depends on parsing error text:

  refused              no marker, command did not succeed
  UNEXPECTED_SUCCESS   marker seen (the isolation failed) -> suite exits non-zero
  error                the case could not be evaluated (exec failed before running) -> suite exits non-zero

Evidence per case: exit code, bounded stdout/stderr, and the OpenShell sandbox log lines (OCSF NET:FAIL, policy denies,
Landlock) collected after the attempt. No secret value is ever printed or stored: secret detection only reports a location.

  python labs/ha/r09a_negative.py list
  python labs/ha/r09a_negative.py run --sandbox netclaw-node --out DIR [--member-addr HOST:PORT] [--only id,id] [--dry-run]
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SCHEMA_VERSION = 1
MAX_CAPTURE = 4000
SECRET_RE = r"sk-ant-[A-Za-z0-9_-]{10,}"
LOG_RE = re.compile(r"NET:FAIL|NET:OPEN \[[A-Z]+\] DENIED|DENIED|denied|Landlock|policy:", re.I)

# Resolve a Python interpreter inside the sandbox image without assuming a name.
PY = 'PY=$(command -v python3 || command -v python) || { echo NOPYTHON; exit 97; }; '


def _py(code):
    return PY + '"$PY" -c ' + _q(code)


def _q(text):
    return "'" + text.replace("'", "'\"'\"'") + "'"


def _connect(host, port, marker="CONNECTED"):
    return _py(f"import socket,sys\ntry:\n s=socket.create_connection(({host!r},{port}),4); print({marker!r})\nexcept Exception as e:\n print('refused:',type(e).__name__); sys.exit(3)")


def cases(member_addr="198.51.100.7:7444"):
    host, _, port = member_addr.rpartition(":")
    return [
        {"id": "file-read-outside-policy", "title": "Read a path outside the policy",
         "command": 'f=/root/.bash_history; [ -e "$f" ] && cat "$f" >/dev/null 2>&1 && echo FOUND:readable-root-file; for p in /root /home/*/.ssh /var/lib/docker; do ls "$p" >/dev/null 2>&1 && echo FOUND:listable:$p; done; true',
         "marker": "FOUND:", "evidence": ["landlock", "logs"]},
        {"id": "write-frozen-source", "title": "Modify the frozen source closure",
         "command": 'for f in /opt/nc182/source/scripts/protected-role.py /opt/nc183/source/scripts/protected-role.py /app/server.py; do [ -e "$f" ] && { echo x >> "$f" 2>/dev/null && echo WROTE:$f; }; done; true',
         "marker": "WROTE", "evidence": ["landlock", "logs"]},
        {"id": "modify-policy-dir", "title": "Write into the policy/config area",
         "command": 'for d in /etc/openshell /etc/openshell/policies /etc/nc183 /etc; do echo x > "$d/.nc183-probe" 2>/dev/null && echo WROTE:$d && rm -f "$d/.nc183-probe"; done; true',
         "marker": "WROTE", "evidence": ["landlock", "logs"]},
        {"id": "metadata-server", "title": "Reach the cloud metadata server",
         "command": _connect("169.254.169.254", 80), "marker": "CONNECTED", "evidence": ["ocsf-net", "logs"]},
        {"id": "unapproved-egress", "title": "Connect to an unapproved external host",
         "command": _connect("example.com", 443), "marker": "CONNECTED", "evidence": ["ocsf-net", "logs"]},
        {"id": "provider-credential-read", "title": "Find the provider credential from inside the sandbox (env, files, /proc)",
         "command": (f'env | grep -qE {_q(SECRET_RE)} && echo FOUND:env; '
                     f'grep -rIlE {_q(SECRET_RE)} /sandbox /tmp /opt 2>/dev/null | head -3 | sed "s/^/FOUND:file:/"; '
                     f'for p in /proc/[0-9]*/environ; do tr "\\0" "\\n" < "$p" 2>/dev/null | grep -qE {_q(SECRET_RE)} && echo "FOUND:proc:$p"; done; true'),
         "marker": "FOUND:", "evidence": ["logs"]},
        {"id": "member-to-member", "title": "Connect from the node to a member's iN2N listener",
         "command": _connect(host, int(port)), "marker": "CONNECTED", "evidence": ["ocsf-net", "logs"]},
        {"id": "docker-socket", "title": "Reach the Docker socket (host escape)",
         "command": ('for s in /var/run/docker.sock /run/docker.sock; do [ -S "$s" ] && echo FOUND:socket:$s; done; '
                     + _py("import socket,sys\ntry:\n s=socket.socket(socket.AF_UNIX); s.connect('/var/run/docker.sock'); print('CONNECTED')\nexcept Exception as e:\n sys.exit(3)")),
         "marker_any": ["FOUND:", "CONNECTED"], "evidence": ["landlock", "logs"]},
        {"id": "ptrace-other-process", "title": "ptrace-attach or read another process",
         "command": _py("import ctypes,sys\nlibc=ctypes.CDLL(None,use_errno=True)\nr=libc.ptrace(16,1,0,0)\nprint('ATTACHED' if r==0 else 'refused errno %d' % ctypes.get_errno())\nsys.exit(0 if r!=0 else 5)"),
         "marker": "ATTACHED", "evidence": ["logs"]},
    ]


class OpenShellRunner:
    """Real runner: `openshell sandbox exec NAME -- sh -c CMD`; logs via `openshell logs NAME`."""
    def __init__(self, sandbox, openshell="openshell", timeout=45):
        self.sandbox, self.openshell, self.timeout = sandbox, openshell, timeout

    def argv(self, command):
        return [self.openshell, "sandbox", "exec", self.sandbox, "--", "sh", "-c", command]

    def run(self, command):
        try:
            p = subprocess.run(self.argv(command), capture_output=True, text=True, timeout=self.timeout)
            return p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "timeout"
        except FileNotFoundError:
            return 127, "", "openshell not found"

    def logs(self):
        try:
            p = subprocess.run([self.openshell, "logs", self.sandbox], capture_output=True, text=True, timeout=30)
            return p.stdout
        except Exception:
            return ""


def markers(case):
    return list(case.get("marker_any") or [case["marker"]])


def evaluate(case, rc, stdout, stderr):
    """Pure verdict. error = exec could not run the probe; UNEXPECTED_SUCCESS = a marker was printed."""
    text = (stdout or "") + "\n" + (stderr or "")
    if "NOPYTHON" in text or rc in (124, 127) and not (stdout or "").strip():
        return "error", "probe could not run (rc=%s)" % rc
    if rc == 126 or "sandbox not found" in text.lower() or "not found: sandbox" in text.lower() or "no such sandbox" in text.lower():
        return "error", "sandbox exec failed (rc=%s)" % rc
    for m in markers(case):
        if m in (stdout or ""):
            return "UNEXPECTED_SUCCESS", "marker %s seen" % m
    return "refused", "no success marker (rc=%s)" % rc


def evidence_lines(log_text, limit=12):
    return [l[:300] for l in (log_text or "").splitlines() if LOG_RE.search(l)][-limit:]


def run_suite(runner, selected, member_addr, dry_run=False):
    results, started = [], time.time()
    for case in cases(member_addr):
        if selected and case["id"] not in selected:
            continue
        if dry_run:
            results.append({"id": case["id"], "title": case["title"], "outcome": "dry-run", "argv": runner.argv(case["command"]) if hasattr(runner, "argv") else None})
            continue
        before = len((runner.logs() or "").splitlines())
        rc, out, err = runner.run(case["command"])
        outcome, why = evaluate(case, rc, out, err)
        logs = (runner.logs() or "").splitlines()[before:]
        results.append({"id": case["id"], "title": case["title"], "outcome": outcome, "reason": why, "exit_code": rc,
                        "stdout": (out or "")[:MAX_CAPTURE], "stderr": (err or "")[:MAX_CAPTURE],
                        "evidence_wanted": case["evidence"], "log_evidence": evidence_lines("\n".join(logs))})
    summary = {"total": len(results), "refused": sum(r["outcome"] == "refused" for r in results),
               "unexpected_success": sum(r["outcome"] == "UNEXPECTED_SUCCESS" for r in results),
               "error": sum(r["outcome"] == "error" for r in results)}
    return {"schema_version": SCHEMA_VERSION, "started_at": started, "duration_s": round(time.time() - started, 2),
            "summary": summary, "cases": results}


def exit_code(report):
    s = report["summary"]
    return 0 if s["unexpected_success"] == 0 and s["error"] == 0 and s["total"] > 0 else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("--sandbox", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--member-addr", default="198.51.100.7:7444")
    r.add_argument("--only", default="")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--openshell", default="openshell")
    args = parser.parse_args(argv)
    if args.action == "list":
        for c in cases():
            print(f"{c['id']:28s} {c['title']}")
        return 0
    selected = {x for x in args.only.split(",") if x}
    report = run_suite(OpenShellRunner(args.sandbox, args.openshell), selected, args.member_addr, args.dry_run)
    out = Path(args.out)
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    (out / "negative-report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    s = report["summary"]
    print(json.dumps(s))
    return exit_code(report) if not args.dry_run else 0


if __name__ == "__main__":
    sys.exit(main())
