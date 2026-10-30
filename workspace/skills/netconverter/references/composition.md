# Composition contracts

| Input or consumer | Appropriate contribution | Boundary |
|---|---|---|
| NetBox, Nautobot, OpsMill/Infrahub | Scoped device/interface/VLAN/VRF selection and intended state | Inventory does not supply running configuration or change permission |
| ServiceNow, Catalyst Center | CI/change context and actual inventory/export | Use supported readers; do not invent a missing CMDB tool |
| pyATS / vendor MCP / NetConverter collectors | Authorized configuration artifact with device/time/hash provenance | Prefer metadata-only private output; inline-only adapters remain unavailable for private automated handoff |
| IP Fabric, Forward Networks | Snapshot/path/behavior evidence and selection context | Snapshot age and modeled scope remain visible; no invented source configuration |
| CML, containerlab, EVE-NG, GNS3 | Exact image-backed topology, lifecycle and observed management endpoints | Console ports are not inferred SSH endpoints; templates do not prove image availability |
| NetConverter | Supported format conversion, validation/optimization and evidence | Account-specific direction; output is a reviewed candidate |
| Batfish | Parse/feature coverage and successful static/differential queries | Partial parse or failed query cannot become equivalence |
| pyATS, ANTA, vendor tools | Actual device identity, commit/readback and behavior assertions | Appropriate platform and existing authorization; ANTA is EOS-specific |
| Jev | Enabled, bounded advisory review of permitted evidence | Separate disclosure consent/budget; agreement does not authorize production |
| Diagram/document/ticket skills | Evidence-linked observed/proposed views and draft change package | No private hosted sharing or ticket creation without applicable authorization |

For a managed dynamic pyATS inventory, compose reviewed source records, validate
with real pyATS and credential references, then explicitly activate. Activation
and subsequent device operations must share one MCP process. This inventory does
not automatically change HUD static inventory, collector grants or Terminal
Intent endpoint authorization.

For private collection, capability-probe the optional artifact output on the
existing `pyats_show_running_config` identity. If absent, ask the operator to stage
the file locally; do not relay raw output through the model. Other collector
adapters require separate qualification. An export from a lab converts according
to its contained OS configuration, not according to the lab vendor.

For Junos application, qualify the existing Junos or pyATS configuration route's
commit and readback semantics. The existence of a Cisco artifact adapter cannot
prove that Junos commits are supported. Do not convert unsupported target formats
by silently asking another model to rewrite them and labeling the result
NetConverter output.
