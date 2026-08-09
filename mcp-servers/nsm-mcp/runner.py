"""Container invocation for Zeek and Suricata, plus the log parsing they need.

Both tools run from digest-pinned containers rather than host packages. That was not a style
choice: `zeek` has no Ubuntu 26.04 apt candidate at all, and `suricata` needs root to install
while this host has no passwordless sudo. Containers need neither, and pinning by digest
matches spec 084's handling of the Kubernetes binary.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time

# Pinned by digest, with the human-readable version recorded alongside. A floating tag would
# let the analysis change under an operator with no signal, which for a security tool is worse
# than being out of date.
ZEEK_IMAGE = ("zeek/zeek@sha256:"
              "eca2b3915d3e067cbb4a904f23f4c4f461ea2b60613ab30f7ee77bbc707c87c7")
ZEEK_VERSION = "8.2.1"
SURICATA_IMAGE = ("jasonish/suricata@sha256:"
                  "81468a22f0b685f3d7e0c1646ab4fdb9a67c1b3dfa3357c52b1434dd4f39dc49")
SURICATA_VERSION = "8.0.6"

# Where fetched rules and analysis output live. Under the OpenClaw workspace, never in the
# repository, and never a foreign home directory (the defect spec 075 was written for and
# spec 090 found a fourth instance of).
NSM_HOME = os.environ.get(
    "NSM_HOME", os.path.join(os.path.expanduser("~"), ".openclaw", "nsm"))
RULES_DIR = os.path.join(NSM_HOME, "rules")
WORK_DIR = os.path.join(NSM_HOME, "runs")

TIMEOUT = int(os.environ.get("NSM_TIMEOUT", "600"))


class NsmError(RuntimeError):
    """A failure that should reach the caller as an error, not as an empty result."""


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def _run(argv: list[str], timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise NsmError(f"timed out after {timeout}s: {' '.join(argv[:4])}…") from exc


def resolve_pcap(path: str) -> str:
    """Absolute path to an existing, readable capture, or a clear error.

    Deliberately refuses a directory and a zero-byte file: both would otherwise produce an
    empty analysis that looks exactly like 'nothing was in the capture'.
    """
    p = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(p):
        raise NsmError(f"capture not found: {p}")
    if os.path.isdir(p):
        raise NsmError(f"{p} is a directory, not a capture file")
    if os.path.getsize(p) == 0:
        raise NsmError(f"{p} is empty (0 bytes) — an empty analysis would be indistinguishable "
                       "from a capture containing nothing")
    return p


# ── Zeek ──────────────────────────────────────────────────────────────────────

_ZEEK_CHECKSUM_HINT = re.compile(r"invalid TCP checksums|checksum offloading", re.I)


def run_zeek(pcap: str, ignore_checksums: bool = True) -> tuple[str, bool, str]:
    """Analyse a capture with Zeek. Returns (output_dir, invalid_checksums_seen, stderr).

    `ignore_checksums` defaults to **True**, which is the opposite of Zeek's own default, and
    the reason is measured rather than assumed: with validation on, the reference fixture
    produced no http.log at all and a conn.log with 3 rows instead of 2. Defaulting to Zeek's
    behaviour would mean this server's out-of-the-box answer is silently incomplete for any
    capture taken from a NIC with checksum offloading -- which is most of them, including
    NetClaw's own capture skills' output.
    """
    out = os.path.join(WORK_DIR, f"zeek-{int(time.time() * 1000)}")
    os.makedirs(out, exist_ok=True)
    argv = ["docker", "run", "--rm",
            "-v", f"{os.path.dirname(pcap)}:/pcap:ro",
            "-v", f"{out}:/out", "-w", "/out", ZEEK_IMAGE,
            "zeek"]
    if ignore_checksums:
        argv.append("-C")
    argv += ["-r", f"/pcap/{os.path.basename(pcap)}"]

    proc = _run(argv)
    stderr = proc.stderr or ""
    # Zeek emits the checksum warning even when -C suppresses the discarding, so the hint is
    # recorded independently of whether packets were actually dropped. The posture helper
    # combines the two.
    invalid = bool(_ZEEK_CHECKSUM_HINT.search(stderr))
    if proc.returncode != 0 and not os.listdir(out):
        raise NsmError(f"zeek failed (exit {proc.returncode}): {stderr.strip()[:400]}")
    return out, invalid, stderr


def zeek_logs(out_dir: str) -> list[str]:
    return sorted(f[:-4] for f in os.listdir(out_dir) if f.endswith(".log"))


def read_zeek_log(out_dir: str, name: str, limit: int = 200) -> tuple[list[dict], int]:
    """Parse a Zeek TSV log into dicts. Returns (rows, total_rows_before_limit)."""
    path = os.path.join(out_dir, f"{name}.log")
    if not os.path.exists(path):
        raise NsmError(f"no {name}.log in this analysis (available: {', '.join(zeek_logs(out_dir))})")
    fields: list[str] = []
    rows: list[dict] = []
    total = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#fields"):
                fields = line.split("\t")[1:]
                continue
            if line.startswith("#") or not line:
                continue
            total += 1
            if len(rows) < limit:
                vals = line.split("\t")
                rows.append({f: v for f, v in zip(fields, vals)})
    return rows, total


# ── Suricata ──────────────────────────────────────────────────────────────────

_SIG_COUNT = re.compile(r"([0-9]+) signatures processed")
_NO_RULES = re.compile(r"no rules were loaded|No rule files match", re.I)


def ruleset_state() -> tuple[bool, int | None]:
    """(ruleset_present, age_in_days)."""
    f = os.path.join(RULES_DIR, "suricata.rules")
    if not os.path.exists(f) or os.path.getsize(f) == 0:
        return False, None
    age = int((time.time() - os.path.getmtime(f)) // 86400)
    return True, age


def update_rules() -> dict:
    """Fetch the ET Open ruleset via suricata-update. Requires network access."""
    os.makedirs(RULES_DIR, exist_ok=True)
    proc = _run(["docker", "run", "--rm",
                 "-v", f"{RULES_DIR}:/var/lib/suricata/rules",
                 SURICATA_IMAGE, "suricata-update", "--no-test"], timeout=max(TIMEOUT, 600))
    blob = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"total: ([0-9]+); enabled: ([0-9]+)", blob)
    present, age = ruleset_state()
    if not present:
        raise NsmError("suricata-update did not produce a ruleset. "
                       f"Network access is required. Output: {blob.strip()[-400:]}")
    return {"total": int(m.group(1)) if m else None,
            "enabled": int(m.group(2)) if m else None,
            "ruleset_present": present, "ruleset_age_days": age}


def run_suricata(pcap: str) -> tuple[str, int, bool, str]:
    """Analyse a capture with Suricata. Returns (out_dir, signatures, no_rules, log_text).

    The signature count is extracted and returned as a first-class value rather than left in
    a log file, because it is the only thing that distinguishes "no alerts, and it looked"
    from "no alerts, because it was inert".
    """
    out = os.path.join(WORK_DIR, f"suricata-{int(time.time() * 1000)}")
    os.makedirs(out, exist_ok=True)
    argv = ["docker", "run", "--rm",
            "-v", f"{os.path.dirname(pcap)}:/pcap:ro",
            "-v", f"{out}:/out"]
    present, _ = ruleset_state()
    if present:
        argv += ["-v", f"{RULES_DIR}:/var/lib/suricata/rules:ro"]
    argv += [SURICATA_IMAGE, "-r", f"/pcap/{os.path.basename(pcap)}",
             "-l", "/out", "--runmode", "single"]

    proc = _run(argv)
    log_path = os.path.join(out, "suricata.log")
    log_text = ""
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            log_text = fh.read()
    blob = log_text + (proc.stderr or "") + (proc.stdout or "")

    m = _SIG_COUNT.search(blob)
    signatures = int(m.group(1)) if m else 0
    no_rules = bool(_NO_RULES.search(blob))
    if not os.path.exists(os.path.join(out, "eve.json")) and proc.returncode != 0:
        raise NsmError(f"suricata failed (exit {proc.returncode}): {blob.strip()[-400:]}")
    return out, signatures, no_rules, blob


def read_eve(out_dir: str, event_type: str | None = None,
             limit: int = 200) -> tuple[list[dict], dict, int]:
    """Parse eve.json. Returns (events, counts_by_type, total_matching)."""
    path = os.path.join(out_dir, "eve.json")
    if not os.path.exists(path):
        return [], {}, 0
    counts: dict[str, int] = {}
    events: list[dict] = []
    total = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            et = ev.get("event_type", "unknown")
            counts[et] = counts.get(et, 0) + 1
            if event_type is None or et == event_type:
                total += 1
                if len(events) < limit:
                    events.append(ev)
    return events, counts, total
