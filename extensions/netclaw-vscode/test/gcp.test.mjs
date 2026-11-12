import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { load } from "./load.mjs";
const { GCP_TOPOLOGIES, gcpPlanCommand, validateGcpChoices } = await load("src/setup/gcp.ts");
const ok = { topology: "gcp-border", project: "my-test-project", regions: ["us-central1"], httpsCidr: "203.0.113.7/32" };
test("topology ids match the provisioner", () => {
  const py = fs.readFileSync(path.resolve("../../scripts/lib/gcp_topology.py"), "utf8");
  for (const t of GCP_TOPOLOGIES) assert.match(py, new RegExp(`"${t.id}":`));
  assert.equal(GCP_TOPOLOGIES.length, 6);
});
test("plan command never carries the acknowledgement or any default project", () => {
  const c = gcpPlanCommand("/src/netclaw", ok);
  assert.match(c, /netclaw-gcp\.py' plan --topology gcp-border --project 'my-test-project'/);
  assert.doesNotMatch(c, /ack-no-auth|netclaw-506315/);
});
test("hostile input is quoted or refused", () => {
  assert.throws(() => gcpPlanCommand("/s", { ...ok, project: "x; rm -rf /" }));
  assert.throws(() => validateGcpChoices({ ...ok, httpsCidr: "0.0.0.0/0" }), /no authentication/);
  assert.throws(() => validateGcpChoices({ ...ok, topology: "distributed-risk" }), /three/);
  assert.throws(() => validateGcpChoices({ ...ok, project: "" }));
});
test("command is contributed and warning text file exists", () => {
  const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
  assert.ok(pkg.contributes.commands.some((c) => c.command === "netclaw.deployGcp"));
  assert.match(fs.readFileSync(path.resolve("../../scripts/lib/gcp_warning.txt"), "utf8"), /NOT BEHIND ANY AUTHENTICATION/);
});
