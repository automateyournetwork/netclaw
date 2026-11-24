# Contract: preflight report (`labs/ha/r10_preflight.py --json`)

Read-only. Uses only `az account show`, `az vm list-skus`, `az vm list-usage`, `az consumption budget list`, `az rest` for retail price.
Exit 0 only when subscription is Enabled and all three regions are `go`. Output shape is `PreflightReport` in data-model.md.
Never creates a resource and never prints a secret value (presence booleans only).
