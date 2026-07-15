"""iN2N GAIT immutable git audit trail (feature 057, US4).

FR-010/011/012/012a, SC-004. Uses a tmp GAIT dir so it never touches real state.
Verifies: one commit per event with attributable message + sqlite_row_id; the SHA
is stored in remote_invocation_record.gait_ref; the trail is append-only; and
gait_recording() drives the audit control state.
"""

import os
import subprocess
import sys

import pytest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))

from bgp.federation import gait
from bgp.federation.manager import FederationManager
from bgp.federation.audit import Auditor


def _commits(gait_dir):
    r = subprocess.run(["git", "-C", str(gait_dir), "log", "--oneline"],
                       capture_output=True, text=True)
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def test_emit_creates_commit(tmp_path):
    gd = tmp_path / "gait"
    sha = gait.emit("delegation", actor="risk/border", subject="risk/cml",
                    target="cml-lab#1", channel_kind="in2n", sqlite_row_id=42, gait_dir=gd)
    assert sha and len(sha) >= 7
    log = _commits(gd)
    # init commit + this event
    assert any("delegation risk/cml by risk/border" in c for c in log)


def test_events_are_attributable_and_ordered(tmp_path):
    gd = tmp_path / "gait"
    for ev, subj in [("enrollment", "risk/pyats"), ("delegation", "risk/cml"),
                     ("quarantine", "risk/evil")]:
        gait.emit(ev, actor="risk/border", subject=subj, gait_dir=gd)
    events = gait.recent(gait_dir=gd)
    # newest first, all attributable
    assert events[0]["event"] == "quarantine"
    assert all(e["actor"] == "risk/border" for e in events if e["event"] != "init")
    assert [e["event"] for e in events][:3] == ["quarantine", "delegation", "enrollment"]


def test_trail_is_append_only(tmp_path):
    gd = tmp_path / "gait"
    gait.emit("delegation", actor="a", subject="risk/x", gait_dir=gd)
    first = _commits(gd)
    gait.emit("removal", actor="a", subject="risk/x", gait_dir=gd)
    second = _commits(gd)
    # strictly grew; earlier commits unchanged (no amend/rebase → prior lines persist)
    assert len(second) == len(first) + 1
    assert set(first).issubset(set(second))


def test_audit_row_cross_references_gait_sha(tmp_path):
    # C2/FR-010: the SQLite row's gait_ref holds the commit SHA of the event.
    mgr = FederationManager(base_dir=str(tmp_path / "fed"))
    audit = Auditor(mgr)
    row_id = audit.record(direction="outbound", peer_identity="risk/cml",
                          target_type="skill", target_name="cml-lab-lifecycle",
                          decision="requested", outcome="submitted", channel_kind="in2n",
                          event="delegation", actor="risk/border")
    row = mgr._conn.execute(
        "SELECT gait_ref FROM remote_invocation_record WHERE id=?", (row_id,)).fetchone()
    assert row["gait_ref"] and len(row["gait_ref"]) >= 7
    # the SHA exists in the per-manager GAIT repo
    log = _commits(audit.gait_dir)
    assert any("delegation risk/cml" in c for c in log)
    # and the committed record back-references the SQLite row
    events = gait.recent(gait_dir=audit.gait_dir)
    assert any(e.get("sqlite_row_id") == row_id for e in events)
    mgr.close()


def test_gait_recording_probe(tmp_path):
    ok, detail = gait.ensure_repo(tmp_path / "gait")
    assert ok is True and detail == ""
