import * as vscode from "vscode";
import { LocalState } from "./local";
import { ConnectionProfile, hostContext } from "./profiles";
import { Connection } from "../connection/connect";
import { ClawTarget, claw, validateTarget } from "../client/claw";
export type ManagementBinding = {
  profile: ConnectionProfile;
  target: ClawTarget;
  codeHash: string;
  context: string;
};
export class Management implements vscode.Disposable {
  readonly changed = new vscode.EventEmitter<void>();
  private selectedId?: string;
  private serial = 0;
  constructor(private local: LocalState, private remoteSelected: () => boolean = () => false) {
    this.selectedId = local.get<string | undefined>(
      "management-selected",
      undefined,
    );
  }
  get selected() {
    if (this.remoteSelected()) return undefined;
    return this.local
      .get<ManagementBinding[]>("management-bindings", [])
      .find(
        (x) => x.profile.id === this.selectedId && x.context === hostContext(),
      );
  }
  get generation() {
    return this.serial;
  }
  async select(profile: ConnectionProfile) {
    if (this.selectedId !== profile.id) {
      this.serial++;
      this.selectedId = profile.id;
      await this.local.update("management-selected", profile.id);
      this.changed.fire();
    }
  }
  async bind(connection: Connection) {
    const b = connection.bound();
    await b.client.session();
    const target = await b.run(() =>
      b.client.request<ClawTarget>("GET", "/api/hud/management"),
    );
    const p = connection.profile!;
    if (
      target.installationId !== connection.identity?.installationId ||
      target.kind !== connection.identity.kind
    )
      throw Error("Discovery returned a different installation.");
    const codeHash = validateTarget(target);
    const answer = await vscode.window.showInformationMessage(
      "Enable local workspace and claw controls?",
      {
        modal: true,
        detail: `${p.label} · ${target.kind}\n${hostContext()}\nInstallation: ${target.installationId}\nHome: ${target.home}\nConfig: ${target.configPath}\nAgent: ${target.agentId}\nWorkspace: ${target.expectedWorkspace || target.home}\nSource: ${target.root}\nNode: ${target.node}\n\nThis runs the reviewed local management helper. Controls remain available while this installation’s HUD is stopped. File contents stay on this host.\nHelper SHA-256: ${codeHash}`,
      },
      "Enable controls",
    );
    if (answer !== "Enable controls") return;
    b.current();
    if (!vscode.workspace.isTrusted) throw Error("Workspace trust changed.");
    await this.saveBinding({
      profile: p,
      target,
      codeHash,
      context: hostContext(),
    });
  }
  async saveBinding(binding: ManagementBinding) {
    if (this.remoteSelected() || binding.profile.mode === "remote-border") throw Error("Cloud profiles cannot acquire local workspace or lifecycle authority.");
    validateTarget(binding.target);
    if (
      binding.profile.installationId !== binding.target.installationId ||
      binding.context !== hostContext()
    )
      throw Error("Binding identity does not match.");
    await this.local.update("management-bindings", [
      ...this.local
        .get<ManagementBinding[]>("management-bindings", [])
        .filter((x) => x.profile.id !== binding.profile.id),
      binding,
    ]);
    this.serial++;
    this.selectedId = binding.profile.id;
    await this.local.update("management-selected", this.selectedId);
    this.changed.fire();
  }
  async forget(profileId: string) {
    await this.local.update(
      "management-bindings",
      this.local
        .get<ManagementBinding[]>("management-bindings", [])
        .filter((b) => b.profile.id !== profileId),
    );
    if (this.selectedId === profileId) {
      this.selectedId = undefined;
      this.serial++;
      await this.local.update("management-selected", undefined);
    }
    this.changed.fire();
  }
  async rename(profileId: string, label: string) {
    await this.local.update(
      "management-bindings",
      this.local
        .get<ManagementBinding[]>("management-bindings", [])
        .map((b) =>
          b.profile.id === profileId
            ? { ...b, profile: { ...b.profile, label } }
            : b,
        ),
    );
    this.changed.fire();
  }
  bound() {
    const binding = this.selected,
      serial = this.serial;
    if (!binding) throw Error("Connect and enable workspace controls first.");
    const current = () => {
      if (
        this.remoteSelected() ||
        !vscode.workspace.isTrusted ||
        serial !== this.serial ||
        this.selected?.profile.id !== binding.profile.id
      )
        throw Error(
          "Selected installation changed. Reopen the file or panel before continuing.",
        );
    };
    return {
      binding,
      current,
      run: async (op: string, input: Record<string, unknown> = {}) => {
        current();
        const r = await claw(binding.target, binding.codeHash, op, input);
        current();
        return r;
      },
    };
  }
  dispose() {
    this.changed.dispose();
  }
}
