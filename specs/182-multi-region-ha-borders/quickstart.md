# Quickstart / verification flow

Offline (no cloud, no owner gate):
1. `python3.10 -m pytest tests/n2n/test_ha_multiregion_182.py` and the extension, HUD and Flutter tests.
2. `python3 scripts/ha-rtt-estimate.py` prints the estimated RTT table and admission budget.
3. `python3 scripts/ha-gcp-multiregion.py plan` (read-only) and `python3 scripts/ha-cost-estimate.py` (fails above $300).
4. `python3 scripts/ha-dns-godaddy.py plan` (needs token; GET only).

Gate G1 (owner): confirm cost table, domain ownership, token location.
Deploy: apply, DNS, certificates, etcd bootstrap, measure real RTT, set admission_ms, NetBox, members.
Gate G2 (owner): add the 3 DNS names in VS Code, screenshot.
Then qualification, release gate, teardown only on request.
Never read an exit code through a pipe; remove only exactly-owned resources.
