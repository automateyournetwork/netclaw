# Verification

Ubuntu 24.04 amd64, Python 3.12, OpenClaw 2026.10.9. Commands ran with `umask 077`.
No credentials or topology are recorded here.

## T001/T002 implementation

- `gateway.py`: the embedded path's `except BaseException` still kills and reaps the
  process, then re-raises a timeout as `asyncio.TimeoutError("agent turn for session
  '<session>' timed out after <timeout_s>s")` chained from the original. Cancellation and
  other exceptions re-raise unchanged.
- `tasks.py`: the stored error and the failure log line use `str(e) or type(e).__name__`.

## T003 tests

- `tests/n2n/test_gateway_result_transport.py::test_timed_out_turn_names_the_timeout`: a
  fake CLI that sleeps 30 s with a 1 s budget raises the named timeout.
- `tests/n2n/test_tasks.py::test_task_error_without_text_records_its_type`: a worker
  raising a bare `asyncio.TimeoutError()` leaves the task `failed` with error
  `TimeoutError`.
- Both fail with the source changes stashed (empty error, unmatched message) and pass
  with them.
- `tests/n2n`: 766 passed, 5 skipped, 1 failed. The failure,
  `test_hermes_internal_149::test_official_n2n_mcp_operator_permit_and_owned_handle`, is
  inherited and fails identically on main (recorded in spec168).
- `ruff check --select F,E9` on changed Python, `git diff --check`,
  `prepare-release.py --check` (1.18.2) and `verify-spec-artifacts.py` pass.

## Real CLI check

`run_agent_turn(local=True, timeout_s=1)` against the installed OpenClaw 2026.10.9 CLI,
in a throwaway home with no credentials, so the real process is still starting when the
budget expires:

| Source | Exception | Message | Elapsed |
|---|---|---|---|
| 1.18.1 | `TimeoutError` | (empty) | 1.8 s |
| 1.18.2 | `TimeoutError` | `agent turn for session 'n2n-probe' timed out after 1s` | 2.2 s |

No OpenClaw process for that home remained afterwards.

## Not covered

A routed task reaching a live member's full 600-second budget was not repeated: the
path is the same `run_agent_turn` call, and the earlier occurrence cost the visualization
member's model several million tokens.
