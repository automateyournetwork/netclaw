import contextlib
import io
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))
import cisco_iq  # noqa: E402

CANARY = "test-canary-key-0123456789"


class Result:
    def __init__(self, rc, out, err):
        self.rc, self.out, self.err = rc, out, err

    @property
    def text(self):
        return self.out + self.err


def run(argv, stdin=None, home=None):
    """Run the CLI in-process. Returns captured output; clears registered secrets first."""
    cisco_iq._known_secrets.clear()
    out, err = io.StringIO(), io.StringIO()
    old_in = sys.stdin
    sys.stdin = io.StringIO(stdin or "")
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cisco_iq.main(list(argv) + (["--home", str(home)] if home else []))
    finally:
        sys.stdin = old_in
    return Result(rc, out.getvalue(), err.getvalue())


def fixture_home(with_config=True):
    d = Path(tempfile.mkdtemp(prefix="ciq-"))
    if with_config:
        (d / "openclaw.json").write_text(json.dumps({"mcpServers": {"other": {"url": "https://x"}}}))
    return d


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)
