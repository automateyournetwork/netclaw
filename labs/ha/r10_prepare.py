"""R10 wrapper around the qualified R09 preparation, with explicit deployment timing.

OpenShell Borders use12379; the diagnostic unsandboxed mode uses2379.
Choose the port here without changing historical R09/R09A code.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labs.ha import r09_prepare

if __name__ == '__main__':
    r09_prepare.ETCD_CLIENT_PORT = 12379 if '--sandbox' in sys.argv else 2379
    r09_prepare.LIMITS = dict(r09_prepare.LIMITS, admission_ms=int(os.environ.get('R10_ADMISSION_MS', '3000')))
    raise SystemExit(r09_prepare.main())
