# NetConverter guard

Optional NetClaw-owned stdio guard around the official hosted MCP and
operator-installed Terminal. Eight tools provide readiness, local preparation,
single-use approved submission, local request state, strict reads, finite job
polling and verified private downloads. No upstream Terminal code is bundled.

Use `config/python-components/netconverter.txt` in the selected isolated Python
runtime. Configure `NETCONVERTER_MODE` (`hosted-readonly` or `local-terminal`),
`NETCONVERTER_INSTALLATION_ID`, private `NETCONVERTER_DATA_DIR`,
`NETCONVERTER_ACCOUNT_REF` and secret `NETCONVERTER_API_KEY`. Local mode additionally
requires absolute `NETCONVERTER_WORKSPACE` and `NETCONVERTER_EXECUTABLE` paths.

The human reviews and approves an exact request with
`scripts/netconverter-settings.py`. No MCP tool creates approval. The ledger
reserves one attempt before outbound submission and preserves unknown outcomes
across restart. Reports/configurations stay in private artifacts; returned
metadata is not semantic acceptance or permission to deploy.

Filesystem permissions protect the declared process boundary, not a malicious
process with the same OS identity. Operator-selected Terminal licensing,
dependencies and trust remain operator-managed. Source implementation and live
qualification status are in [Spec162 verification](../../specs/162-netconverterai/verification.md).
