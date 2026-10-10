"""Exercise the prerequisite path without package installation or operator state."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def test_prerequisites_do_not_disable_pep668(tmp_path):
    env = os.environ.copy()
    env.pop('PIP_BREAK_SYSTEM_PACKAGES', None)
    script = r'''
set -eu
NETCLAW_DIR="$PWD"
source scripts/lib/install-steps.sh
log_step() { :; }
log_info() { :; }
log_warn() { :; }
log_error() { return 1; }
check_command() { return 0; }
node() { echo v24.16.0; }
# The actual PEP668 detector sees a managed interpreter.
python3() { return 0; }
NETCLAW_PY=python3
core_prereqs
test -z "${PIP_BREAK_SYSTEM_PACKAGES+x}"
'''
    result = subprocess.run(['bash', '-c', script], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr + result.stdout
