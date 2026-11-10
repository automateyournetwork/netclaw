# Contract: DNS naming and GoDaddy wiring

- Zone: `automateyournetwork.com` (GoDaddy). Confirm ownership before G1.
- Borders: `<code>-<id6>.automateyournetwork.com`; code in {nne1, ew1, ase1}; `id6` = first 6 hex of `installation_id` (lowercase).
- Members: `netbox-<id6>.automateyournetwork.com` (on-prem members attach outbound and need no public name).
- Record: A, TTL 600, to the Border static IP. No wildcard records.
- Certificates: lego DNS-01 (`_acme-challenge.<name>` TXT), via `scripts/lib/godaddy-acme-hook.sh` and a GoDaddy PAT in `~/.openclaw/.env`.
- Tool: `scripts/ha-dns-godaddy.py plan` (GET only; default) / `apply` (needs `--apply` and owner gate G1). Never prints the token. Refuses names that do not match the pattern or that already exist with another target.
