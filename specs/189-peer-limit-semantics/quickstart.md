# Quickstart

```sh
VENV=<python3.12 venv with requirements + pytest + pytest-asyncio + pyyaml>
cd netclaw && $VENV/bin/python -m pytest -q tests/n2n/test_peer_limits_189.py tests/n2n/test_authorization.py
$VENV/bin/python -m pytest -q tests/n2n          # full regression
```
Operator (Python): `authz.set_policy(peer, action="teardown", restart_timer_s=300, daily_requests=100)`; `authz.limit_status(peer)`; `authz.reset_limits(peer, actor="ops")`. See docs/N2N-PEER-LIMITS.md.
