# Research

- `asyncio.wait_for` raises a bare `TimeoutError` (`asyncio.TimeoutError` is the builtin
  since Python 3.11); `str()` of it is `''`. Python 3.10's `asyncio.TimeoutError` is a
  separate class, also without a message; `isinstance(e, asyncio.TimeoutError)` matches
  both.
- The Border relays the member's stored result: `TaskManager.result` returns the stored
  `error` (`tasks.py`), so fixing the member side fixes what the Border reports.
- `gateway.py`'s WS path already raises `asyncio.TimeoutError("agent turn for session
  '…' timed out — …")`; the embedded message follows that wording, without the
  scope-approval hint, which only applies to the gateway path.
- Observed in spec168's final live run: the visualization member hit its 600 s budget
  and the Border's task showed `failed` with an empty error.
