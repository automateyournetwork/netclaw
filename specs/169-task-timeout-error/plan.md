# Plan

T001 `gateway.py` embedded path: after killing and reaping the process, re-raise a
timeout as `asyncio.TimeoutError` naming the session and budget (chained from the
original). Other exceptions, including cancellation, re-raise unchanged.
T002 `tasks.py`: record `str(e) or type(e).__name__` as the stored error and in the
failure log line.
T003 Tests: a hung fake CLI with a 1 s budget (`tests/n2n/test_gateway_result_transport.py`)
and a worker raising a bare `TimeoutError` (`tests/n2n/test_tasks.py`); both fail on main.
Check against the real OpenClaw CLI. Release 1.18.2, PR.
