# Quickstart: R09A validation

1. Offline: `python -m pytest tests/n2n/test_ha_bind_183.py tests/n2n/test_ha_sandbox_183.py`.
2. Owner confirms the cost estimate (specs/183.../cost-model.md); then `scripts/ha-r09a-deploy.sh` creates two Border VMs plus an etcd witness in one region from Ubuntu 24.04.
3. Per node: `ha-r09a-vm-bootstrap.sh` (Docker >= 28, OpenShell 0.1.7, DefenseClaw 1.0.4, linger, `OPENSHELL_COMPUTE_DRIVER=docker`), then the node sandbox from the generated image/policy and the host forwards.
4. Verify: `GET https://<node>/api/hud/posture`, a real operation through each Border, `labs/ha/r09a_negative.py`, the R09 failure matrix.
5. Teardown only on the owner's request, by exact list (label `netclaw-spec=183` / prefix `nc183-`).
