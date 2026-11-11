# Quickstart: spec 190

```text
n2n_classify(target_type="tool", target_name="cml-mcp/list_labs", access="read")
n2n_classify(target_type="tool", target_name="cml-mcp/start_lab", access="write")
n2n_grant(peer="as65007-7.7.7.7", target_type="tool", target_name="cml-mcp/list_labs", access_class="read")
n2n_grant(peer="as65007-7.7.7.7", target_type="tool", target_name="cml-mcp/start_lab", access_class="read")
#   -> the second grant exists but every call is refused (NOT_ALLOWLISTED) until the peer's class is read_write
```
Test: `/private/tmp/claude-503/ra-venv/bin/python -m pytest -q tests/n2n/test_grant_access_class_190.py`
