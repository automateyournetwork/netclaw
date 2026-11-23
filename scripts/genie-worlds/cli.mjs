import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { createManager } from "./manager.mjs";
import { nativeAudit } from "./audit.mjs";
import { need, supportedRuntime } from "./model.mjs";
import { loadLivePacket } from "./live-packet.mjs";
supportedRuntime();
const [command, ...args] = process.argv.slice(2);
try {
  const root = resolve(
    process.env.NETCLAW_GENIE_STATE_DIR || ".spec200-local/worlds",
  );
  if (["serve", "live-serve"].includes(command)) {
    const auditRoot = process.env.NETCLAW_GENIE_GAIT_ROOT;
    const audit = auditRoot ? (event) => nativeAudit(auditRoot, event) : null;
    const packetPath = command === "live-serve" ? resolve(args[0] || "") : null;
    const live = packetPath ? loadLivePacket(packetPath) : null;
    const server = await createManager({ root: live?.state_root || root, audit, livePacketPath: packetPath, snapshotRegistryPath: process.env.NETCLAW_GENIE_SNAPSHOT_REGISTRY || null });
    console.log(
      `${live ? "Authorized single Google trial" : "Offline fixture viewer"}: ${server.origin}/#${server.bootstrap}`,
    );
    console.log(live ? `One reviewed attempt; 120-second target; US$${live.allowance_usd} reserved within the shared campaign.` : "Google generation disabled. State: " + root);
    process.on("SIGINT", () => server.close().then(() => process.exit(0)));
    process.on("SIGTERM", () => server.close().then(() => process.exit(0)));
  } else if (["status", "evidence", "stop"].includes(command)) {
    const service = JSON.parse(
      readFileSync(join(root, "service.json"), "utf8"),
    );
    const id = args[0];
    need(id, "operation_id_required");
    const suffix = command === "status" ? "" : "/" + command;
    const response = await fetch(
      `${service.origin}/v1/sessions/${id}${suffix}`,
      {
        method: command === "stop" ? "POST" : "GET",
        headers: { Authorization: `Bearer ${service.owner}` },
      },
    );
    const data = await response.json();
    need(response.ok, data.error || "request_failed");
    console.log(JSON.stringify(data, null, 2));
  } else {
    console.log(
      "Usage: node cli.mjs serve | status <operation-id> | evidence <operation-id> | stop <operation-id>",
    );
    process.exitCode = 1;
  }
} catch (e) {
  console.error(e.code || e.message);
  process.exitCode = 1;
}
