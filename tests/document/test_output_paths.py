"""Output paths. Spec 082, FR-016..FR-020, SC-012/013/014.

The requirement that matters most here: an existing file is NEVER opened for writing.
Feature 046's convention relies on timestamp uniqueness alone, which collides for two
documents produced in the same second — and a regenerated report silently replacing the
one already attached to a ticket is the failure this prevents.
"""

from __future__ import annotations

import hashlib
import os
import stat

from _harness import FAILURES, check, cleanup, run, sandbox  # noqa: F401

import output  # noqa: E402


def _sha(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_same_second_writes_do_not_collide():
    d = sandbox()
    try:
        p1, s1 = output.reserve("docx", "report")
        p1.write_bytes(b"first")
        digest_before = _sha(p1)

        p2, s2 = output.reserve("docx", "report")
        p2.write_bytes(b"second")

        check("two writes produce two distinct paths", p1 != p2, f"{p1} == {p2}")
        check("the first file still exists", p1.exists())
        check(
            "the first file is byte-identical after the second write",
            _sha(p1) == digest_before,
            "the first file was modified — a regenerated report replaced an attached one",
        )
        check("the first write has no collision suffix", s1 is None, str(s1))
        check("the second write records a collision suffix", s2 == 2, str(s2))
        check("the second file carries the suffix in its name", "-2." in p2.name, p2.name)
    finally:
        cleanup(d)


def test_reported_path_is_the_real_one():
    d = sandbox()
    try:
        p, s = output.reserve("xlsx", "audit")
        p.write_bytes(b"x" * 17)
        art = output.finalize(p, s)
        check("the reported path exists on disk", os.path.exists(art.path) or os.path.exists(
            os.path.join(os.getcwd(), art.path)), art.path)
        check("the reported size matches", art.bytes == 17, str(art.bytes))
        check("created_at is stamped", art.created_at.endswith("Z"), art.created_at)
    finally:
        cleanup(d)


def test_filenames_are_timestamped_and_sanitised():
    d = sandbox()
    try:
        p, _ = output.reserve("pptx", "../../etc/passwd; rm -rf /")
        check("path traversal is sanitised out of the filename", "/" not in p.name[:-5], p.name)
        check("the kind prefixes the filename", p.name.startswith("pptx-"), p.name)
        check("a UTC timestamp is present", "Z-" in p.name, p.name)
        check("the file landed in the output dir", p.parent == output.output_dir(), str(p.parent))
    finally:
        cleanup(d)


def test_unwritable_directory_is_reported_not_worked_around():
    d = sandbox()
    try:
        blocked = os.path.join(d, "blocked")
        os.makedirs(blocked, exist_ok=True)
        os.chmod(blocked, stat.S_IRUSR | stat.S_IXUSR)  # r-x, not writable
        os.environ["DOCUMENT_OUTPUT_DIR"] = blocked

        raised = None
        try:
            output.reserve("docx", "x")
        except output.OutputUnwritable as exc:
            raised = exc

        if os.geteuid() == 0:
            print("  SKIP  running as root — an unwritable directory cannot be simulated")
            return

        check("an unwritable output dir raises OutputUnwritable", raised is not None,
              "it silently succeeded")
        check(
            "nothing was written to a fallback location",
            not os.listdir(blocked),
            f"files appeared in {blocked} — or worse, in a temp dir the operator will never find",
        )
    finally:
        try:
            os.chmod(os.path.join(d, "blocked"), stat.S_IRWXU)
        except OSError:
            pass
        cleanup(d)


def test_list_outputs():
    d = sandbox()
    try:
        for kind in ("docx", "xlsx", "docx"):
            p, _ = output.reserve(kind, "x")
            p.write_bytes(b"data")
        allx = output.list_outputs()
        check("all outputs are listed", len(allx) == 3, str(len(allx)))
        docx = output.list_outputs("docx")
        check("filtering by kind works", len(docx) == 2, str(len(docx)))
        check("entries carry a kind", all(e["kind"] == "docx" for e in docx), str(docx))
    finally:
        cleanup(d)


TESTS = [
    test_same_second_writes_do_not_collide,
    test_reported_path_is_the_real_one,
    test_filenames_are_timestamped_and_sanitised,
    test_unwritable_directory_is_reported_not_worked_around,
    test_list_outputs,
]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "output path"))
