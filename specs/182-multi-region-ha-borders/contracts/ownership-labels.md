# Contract: ownership labels and teardown

- Every GCP resource: label `netclaw-spec=182`; names prefixed `nc182-`.
- Teardown lists resources by label (`netclaw-spec=182`), prints the exact list, and needs a separate owner confirmation. It never uses wildcards and never touches resources without the label (old VM, equinix-*, pyats-mcp, gateway5, drawio-mcp).
- Docker resources on any host: remove only those labelled `netclaw.spec=182`.
