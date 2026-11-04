import * as vscode from "vscode";
import { randomUUID } from "node:crypto";
import { LocalState } from "./local";
import { endpoint } from "../client/hud";
import { ownerOrigin, cloudInputOrigin, installationIdentifier } from "../client/owner";
export type ConnectionProfile = {
  id: string;
  label: string;
  url: string;
  mode?: "local" | "remote-border";
  access?: "open-lab";
  context: string;
  installationId?: string;
  harness?: "openclaw" | "hermes";
  assistantEnabled?: boolean;
  delegationEnabled?: boolean;
};
export function hostContext() {
  return `${vscode.env.remoteName || "local"}:${process.platform}:${process.env.WSL_DISTRO_NAME || ""}`;
}
export class Profiles {
  constructor(private local: LocalState) {}
  list(): ConnectionProfile[] {
    return this.local
      .get<ConnectionProfile[]>("profiles", [])
      .filter((p) => p.context === hostContext());
  }
  async saveCloud(label: string, url: string, installationId: string) {
    const origin = cloudInputOrigin(url);
    const known = this.list().filter(p => p.mode === "remote-border" && p.url === origin);
    if (known.some(p => p.installationId !== installationId)) throw Error("This Border's installation identity changed. The saved connection and retained operations are unchanged.");
    const existing = known[0];
    return this.save({ id: existing?.id, label, url: origin, installationId, mode: "remote-border", access: "open-lab", harness: "openclaw" });
  }
  async save(
    p: Omit<ConnectionProfile, "id" | "context"> &
      Partial<Pick<ConnectionProfile, "id" | "context">>,
  ): Promise<ConnectionProfile> {
    if (!p.label.trim() || p.label.length > 100)
      throw Error("Use a connection label of 1–100 characters.");
    if (p.mode !== undefined && !["local", "remote-border"].includes(p.mode)) throw Error("Unsupported connection mode.");
    if (p.access !== undefined && (p.access !== "open-lab" || p.mode !== "remote-border")) throw Error("Unsupported cloud access mode.");
    if (p.mode === "remote-border" && (!installationIdentifier(p.installationId) || p.harness !== "openclaw" || p.assistantEnabled || p.delegationEnabled))
      throw Error("A cloud Border profile requires its expected installation UUID and protected OpenClaw owner mode.");
    const result = {
      ...p,
      id: p.id || randomUUID(),
      context: p.context || hostContext(),
      url: p.mode === "remote-border" ? ownerOrigin(p.url) : endpoint(p.url),
    };
    const all = this.local.get<ConnectionProfile[]>("profiles", []);
    await this.local.update("profiles", [
      ...all.filter((x) => x.id !== result.id),
      result,
    ]);
    return result;
  }
  async remove(id: string) {
    await this.local.update(
      "profiles",
      this.local
        .get<ConnectionProfile[]>("profiles", [])
        .filter((p) => p.id !== id),
    );
  }
}
