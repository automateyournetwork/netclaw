import * as vscode from "vscode";
import fs from "node:fs";
import path from "node:path";
import { Connection } from "../connection/connect";
import { readRegistration, Registration } from "./service";
export const quote = (value: string) => `'${value.replaceAll("'", "'\\''")}'`;
export class AssistantProvider
  implements vscode.McpServerDefinitionProvider, vscode.Disposable
{
  private changes = new vscode.EventEmitter<void>();
  readonly onDidChangeMcpServerDefinitions = this.changes.event;
  private labels = new Map<string, string>();
  private listener: vscode.Disposable;
  constructor(
    readonly context: vscode.ExtensionContext,
    private connection: Connection,
  ) {
    this.listener = connection.changed.event(() => this.refresh());
  }
  get directory() {
    return path.join(
      this.context.globalStorageUri.fsPath,
      "assistant-registrations",
    );
  }
  file(client: string) {
    if (!this.connection.profile) throw Error("Connect first.");
    return path.join(
      this.directory,
      `${this.connection.profile.id}-${client}.json`,
    );
  }
  refresh() {
    this.changes.fire();
  }
  provideMcpServerDefinitions() {
    this.labels.clear();
    if (!this.connection.ready || this.connection.profile?.mode === "remote-border" || !vscode.workspace.isTrusted) return [];
    try {
      const file = this.file("copilot"),
        r = readRegistration(file);
      if (r.installationId !== this.connection.identity?.installationId)
        return [];
      const label = `NetClaw · ${this.connection.profile?.label}`;
      this.labels.set(label, file);
      return [this.definition(label, file, r)];
    } catch {
      return [];
    }
  }
  private definition(label: string, file: string, r: Registration) {
    return new vscode.McpStdioServerDefinition(
      label,
      process.execPath,
      [
        vscode.Uri.joinPath(this.context.extensionUri, "dist/assistant.mjs")
          .fsPath,
        "--registration",
        file,
      ],
      { ELECTRON_RUN_AS_NODE: "1" },
      `${this.context.extension.packageJSON.version}:${r.delegate}`,
    );
  }
  resolveMcpServerDefinition(definition: vscode.McpStdioServerDefinition) {
    if (!this.connection.ready || this.connection.profile?.mode === "remote-border" || !vscode.workspace.isTrusted) return undefined;
    const file = this.labels.get(definition.label);
    if (!file) return undefined;
    const r = readRegistration(file);
    if (
      r.installationId !== this.connection.identity?.installationId ||
      r.url !== this.connection.profile?.url
    )
      return undefined;
    return this.definition(definition.label, file, r);
  }
  async setup() {
    const b = this.connection.bound(),
      profile = this.connection.profile!;
    const selected = await vscode.window.showQuickPick(
      ["copilot", "claude-code", "codex"],
      { title: "Connect an assistant" },
    );
    if (!selected) return;
    const action = await vscode.window.showQuickPick(
      [
        "Enable inspection and draft proposals",
        "Enable inspection, delegation and draft proposals",
        "Disable this registration",
      ],
      { title: selected },
    );
    if (!action) return;
    const enabled = !action.startsWith("Disable"),
      delegate = action.includes("delegation");
    if (
      enabled &&
      (await vscode.window.showInformationMessage(
        `Allow ${selected} to access ${profile.label}?`,
        {
          modal: true,
          detail: `Installation: ${this.connection.identity!.installationId}\nRead summaries and answers may be disclosed to this assistant’s provider.\n${delegate ? "Delegation sends prompts to your existing NetClaw and may invoke its tools under its existing approval rules. This is not enforced read-only delegation." : "No work requests; inspection and inert proposals only."}\nNo approval/apply tools are exposed. This adapter is not a sandbox for unrestricted same-user terminal access.`,
        },
        "Enable",
      )) !== "Enable"
    )
      return;
    b.current();
    fs.mkdirSync(this.directory, { recursive: true, mode: 0o700 });
    const file = this.file(selected),
      r: Registration = {
        id: profile.id + "-" + selected,
        client: selected,
        url: profile.url,
        installationId: this.connection.identity!.installationId,
        enabled,
        delegate,
      };
    const temp = file + ".tmp";
    fs.writeFileSync(temp, JSON.stringify(r, null, 2) + "\n", { mode: 0o600 });
    fs.renameSync(temp, file);
    this.refresh();
    if (!enabled) {
      void vscode.window.showInformationMessage(
        "Registration disabled. Cached adapter calls will be refused; already submitted backend work may still run.",
      );
      return;
    }
    if (selected === "copilot") {
      void vscode.window.showInformationMessage(
        "NetClaw is available in VS Code MCP discovery. Review its tools and start it; VS Code manages MCP trust and Copilot sign-in.",
      );
      return;
    }
    const name = "netclaw-" + profile.id.slice(0, 8),
      adapter = vscode.Uri.joinPath(
        this.context.extensionUri,
        "dist/assistant.mjs",
      ).fsPath;
    const command =
      selected === "codex"
        ? `codex mcp add ${quote(name)} -- node ${quote(adapter)} --registration ${quote(file)}`
        : `claude mcp add --transport stdio ${quote(name)} -- node ${quote(adapter)} --registration ${quote(file)}`;
    const doc = await vscode.workspace.openTextDocument({
      language: "shellscript",
      content: `# Run on this same ${vscode.env.remoteName || "local"} extension host. Requires Node >=22.\n# Review first; preserves other registered servers.\n${command}\n\n# Remove this client registration when done:\n${selected === "codex" ? "codex" : "claude"} mcp remove ${quote(name)}\n# Re-run setup after an extension update if its installation path changes.\n`,
    });
    await vscode.window.showTextDocument(doc, { preview: false });
  }
  dispose() {
    this.listener.dispose();
    this.changes.dispose();
  }
}
