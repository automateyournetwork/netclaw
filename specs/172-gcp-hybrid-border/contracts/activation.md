# Role activation and cloud packet contract

A provider-neutral role contract selects an owned installation/home and pinned
source, profile and interpreter. For R03 Border: runtime metadata OpenClaw,
protected mode mandatory, role persisted before start, control-only executor=None,
no provider/device key inputs, no Docker/gateway/model/tool services. Startup env
is an explicit allowlist, not inherited repository `.env`. Private startup secret
projection contains only Border identity/owner/bridge/federation material.

Separate non-root federation and HUD services bind only required listeners. Keep
admin/routing/broker interfaces loopback and eN2N registered but loopback/dormant;
public direct iN2N is distinct. System units use UMask0077, NoNewPrivileges,
PrivateTmp, ProtectSystem=strict, ProtectHome and precise writable state paths,
no capabilities and bounded resources. Actual systemd inspection/restart is
required; templates alone are not qualification.

GCP IaC lives in `labs/cloud/gcp/r03`, uses explicit project and fresh private state,
unique names/labels/expiry, VPC/subnet/VM/disk/IP/workload identity/scoped secret and
only reviewed firewall ingress. No R01 import/change, no cloud-to-LAN routes,
public MCP/model/routing/admin, new build service or shared credential bundle.
Admin SSH uses IAP. DNS A/TTL/HTTPS source and binary hashes are separately named.

Before apply: frozen saved-plan digest/resource diff, cost/actual-charge visibility,
48h-or-shorter expiry, finite traffic controls and residual costs, rollback and
exact reviewed teardown scope. Source implementation grants no cloud mutation.
Before runtime activation: exact source/secret/key/transfer/unit/DNS operations and
approved repairs/restarts. Before destroy: verified exported evidence and exact
R03-only destroy plan. A prior R01 delegation is not a new R03 delegation.
