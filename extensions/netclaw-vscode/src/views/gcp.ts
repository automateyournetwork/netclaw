import * as vscode from "vscode";
import fs from "node:fs";
import path from "node:path";
import { GCP_TOPOLOGIES, GCP_SCRIPT, GCP_WARNING_FILE, gcpPlanCommand } from "../setup/gcp";

const source = () => (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath).find((p) => fs.existsSync(path.join(p, GCP_SCRIPT)));

/** NetClaw: Deploy to GCP. Warning first (modal, must acknowledge), then choices, then the reviewed plan in a terminal. */
export async function deployGcp() {
  const root = source();
  if (!root) throw Error("Open your NetClaw checkout as a workspace folder first (scripts/netclaw-gcp.py was not found).");
  const warning = fs.readFileSync(path.join(root, GCP_WARNING_FILE), "utf8").trim();
  if ((await vscode.window.showWarningMessage("NOT BEHIND ANY AUTHENTICATION", { modal: true, detail: warning }, "I understand")) !== "I understand") return;
  const topo = await vscode.window.showQuickPick(GCP_TOPOLOGIES.map((t) => ({ label: t.label, description: t.description, id: t.id })), { title: "Deploy NetClaw to GCP: topology", ignoreFocusOut: true });
  if (!topo) return;
  const ask = (title: string, prompt: string, value?: string) => vscode.window.showInputBox({ title, prompt, value, ignoreFocusOut: true });
  const project = await ask("GCP project", "Your GCP project id (nothing is assumed). Needs billing and the Compute, IAM and IAP APIs.");
  if (!project) return;
  const regionText = await ask("GCP region(s)", topo.id === "distributed-risk" ? "Three regions, space separated" : "One region", topo.id === "distributed-risk" ? "us-central1 europe-west1 asia-southeast1" : "us-central1");
  if (!regionText) return;
  const cidr = await ask("HTTPS source range", "CIDR allowed to reach the HUD on 443 (0.0.0.0/0 is refused). Use your own address, e.g. 203.0.113.7/32");
  if (!cidr) return;
  const command = gcpPlanCommand(root, { topology: topo.id, project: project.trim(), regions: regionText.trim().split(/\s+/), httpsCidr: cidr.trim() });
  const terminal = vscode.window.createTerminal({ name: "NetClaw GCP plan", cwd: root });
  terminal.show();
  // The CLI shows the warning, asks for 'yes', checks prerequisites and prints the plan + cost + hash. Nothing is created.
  terminal.sendText(command, true);
  vscode.window.showInformationMessage("Review the plan in the terminal. To create it, run the `apply` line it prints (adds --confirm-cost). Teardown: netclaw-gcp.py teardown.");
}
