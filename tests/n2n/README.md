# NCFED test environments

Run unit and transport tests in an isolated Python3.12 environment with
`mcp-servers/protocol-mcp/requirements.txt`, pytest, pytest-asyncio and PyYAML.
The system Python is not a federation runtime selector.

Spec149 real Hermes fixtures additionally require:

- `NETCLAW_HERMES_PYTHON`: isolated Python3.14 Hermes companion interpreter.
- `NETCLAW_HERMES_SOURCE`: the complete pinned source from `config/hermes-hud-compatibility.json`.
- `NETCLAW_SUBNET_PYTHON`: isolated Python3.12 interpreter for the reviewed subnet component.

Fixtures use temporary private homes and a loopback controlled provider. They do
not read owner transcripts or send requests to a real model provider. A skipped
real fixture is not execution qualification. Host production confinement requires
separate Linux/WSL evidence; Mac functional execution does not imply confinement.

```sh
python -m pytest -q tests/n2n
python -m pytest -q tests/hermes-hud
```

Real process qualification uses `python tests/n2n/hermes_acceptance_149.py --workdir /tmp/netclaw149-check --tests tests/n2n/test_hermes_lifecycle_149.py tests/n2n/test_hermes_external_149.py tests/n2n/test_hermes_mobile_149.py`. Set the three fixture variables above first. Add `NETCLAW_OPENCLAW_BIN` (absolute executable) and `tests/n2n/test_mixed_runtime_149.py` for all four internal pairs and bidirectional mixed external execution. The runner copies and installer-patches subnet source in its synthetic checkout; when running `--tests tests/hermes-hud`, it also copies Hermes source before drift/fault tests. Do not run those source-mutating tests against an owner runtime. Run families separately to avoid Python module-name collisions.
