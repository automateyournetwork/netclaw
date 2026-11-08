import * as vscode from "vscode";
import { randomUUID } from "node:crypto";
import { LocalState } from "./local";
import { endpoint } from "../client/hud";
import { ownerOrigin, cloudInputOrigin, installationIdentifier, cloudExecutionMode, labAccess, ownerCanonical, ownerReferencesKey, mergedOwnerReferences, withOwnerState } from "../client/owner";
import { combinedReferencesKey, mergedCombinedReference } from "../client/combined";
import type { Json } from "../client/hud";
import { ClusterBinding, verifyClusterRuntime } from "../client/cluster";
export type ConnectionProfile = {
  id: string;
  label: string;
  url: string;
  mode?: "local" | "remote-border";
  access?: "open-lab";
  context: string;
  installationId?: string;
  cloudExecution?: "ordinary" | "protected";
  cloudPrincipal?: Json;
  cluster?: ClusterBinding;
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
  async saveCloud(label: string, url: string, installationId: string, runtime?: Json, acceptedAnchor?: string) {
    const origin = cloudInputOrigin(url);
    if (runtime && (runtime.installationId !== installationId || runtime.kind !== "openclaw" || runtime.role !== "border")) throw Error("Cloud installation identity changed.");
    const known = this.list().filter(p => p.mode === "remote-border" && p.url === origin);
    if (known.some(p => p.installationId !== installationId)) throw Error("This Border's installation identity changed. The saved connection and retained operations are unchanged.");
    const existing = known[0];
    if (runtime && existing?.cloudExecution && (existing.cloudExecution !== cloudExecutionMode(runtime) || ownerCanonical(existing.cloudPrincipal) !== ownerCanonical(labAccess(runtime.access).principal))) throw Error("This Border's execution mode or operator changed. Saved references are unchanged.");
    if (Boolean(existing?.cluster) !== Boolean(runtime?.cluster) && existing) throw Error("The cluster enrollment changed. Preserve this connection and explicitly enroll a new profile.");
    const cluster = runtime?.cluster ? await verifyClusterRuntime(runtime, {origin, ...(existing?.cluster ? {pin:existing.cluster.pin} : {acceptedAnchor})}) : undefined;
    return this.save({ ...(cluster ? {cluster} : {}), id: existing?.id, label, url: origin, installationId, mode: "remote-border", access: "open-lab", harness: "openclaw", ...(runtime ? { cloudExecution: cloudExecutionMode(runtime), cloudPrincipal: labAccess(runtime.access).principal } : existing?.cloudExecution ? { cloudExecution: existing.cloudExecution, cloudPrincipal: existing.cloudPrincipal } : {}) });
  }
  async replaceCloudEndpoint(previous: ConnectionProfile, url: string, runtime: Json) {
    return withOwnerState(this.local, async () => {
    const current = () => {
      const row = this.list().find(p => p.id === previous.id);
      if (!row || ownerCanonical(row) !== ownerCanonical(previous)) throw Error("The saved connection changed. Review its endpoint again.");
    };
    current(); const origin = cloudInputOrigin(url);
    if (previous.mode !== "remote-border" || previous.access !== "open-lab" || !previous.installationId || !previous.cloudExecution || !previous.cloudPrincipal) throw Error("Connect this cloud profile once to record its identity and execution mode before replacing its endpoint.");
    if ((!previous.cluster && runtime.installationId !== previous.installationId) || runtime.kind !== "openclaw" || runtime.role !== "border") throw Error("Destination installation identity changed. Saved references are unchanged.");
    if (cloudExecutionMode(runtime) !== previous.cloudExecution || ownerCanonical(labAccess(runtime.access).principal) !== ownerCanonical(previous.cloudPrincipal)) throw Error("Destination execution mode or operator changed. Saved references are unchanged.");
    if (Boolean(previous.cluster) !== Boolean(runtime.cluster)) throw Error("Destination cluster mode changed. Saved references remain unchanged.");
    const cluster = previous.cluster ? await verifyClusterRuntime(runtime, {pin:previous.cluster.pin,origin}) : undefined;
    if (origin === previous.url) return previous;
    if (this.list().some(p => p.id !== previous.id && p.mode === "remote-border" && p.url === origin)) throw Error("The destination already has a saved profile. Preserve both connections and recover their references first.");
    if (cluster) {
      current();
      // Cluster/principal reference namespace is unchanged; no copies or retries.
      return this.save({...previous,url:origin,installationId:runtime.installationId,cluster});
    }
    const oldKey = ownerReferencesKey(previous.url, previous.installationId), newKey = ownerReferencesKey(origin, previous.installationId);
    const oldCombined = combinedReferencesKey(previous.url, previous.installationId, previous.cloudPrincipal), newCombined = combinedReferencesKey(origin, previous.installationId, previous.cloudPrincipal);
    const sourceRefs = this.local.get(oldKey, []), sourceCombined = this.local.get(oldCombined, undefined);
    const refs = mergedOwnerReferences(this.local.get(newKey, []), sourceRefs);
    const combined = mergedCombinedReference(this.local.get(newCombined, undefined), sourceCombined);
    // Copy identifiers before switching the profile; failures keep the old usable
    // binding. Source references remain as evidence, and no cookie is transferred.
    if (refs.length) await this.local.update(newKey, refs);
    current();
    if (combined) await this.local.update(newCombined, combined);
    current();
    if (JSON.stringify(this.local.get(oldKey, [])) !== JSON.stringify(sourceRefs) || JSON.stringify(this.local.get(oldCombined, undefined)) !== JSON.stringify(sourceCombined) || JSON.stringify(this.local.get(newKey, [])) !== JSON.stringify(refs) || JSON.stringify(this.local.get(newCombined, undefined)) !== JSON.stringify(combined)) throw Error("Operation references changed during endpoint replacement. The original profile is retained; recover before trying again.");
    return this.save({ ...previous, url: origin });
    });
  }
  private clusterUpdates: Promise<unknown> = Promise.resolve();
  async updateCluster(previous: ConnectionProfile, cluster: ClusterBinding) {
    const work = async () => {
      const current = this.list().find(p => p.id === previous.id);
      if (!current?.cluster || current.url !== previous.url || current.installationId !== previous.installationId) throw Error("The selected cluster endpoint changed. Nothing was submitted.");
      const runtime = {kind:"openclaw",role:"border",installationId:current.installationId,access:{mode:"open-lab",principal:current.cloudPrincipal},capabilities:{protectedOperations:true,protectedProduction:true},cluster:cluster.descriptor};
      const verified = await verifyClusterRuntime(runtime, {pin:current.cluster.pin,origin:current.url});
      const latest = this.list().find(p => p.id === previous.id);
      if (ownerCanonical(latest) !== ownerCanonical(current)) throw Error("Saved cluster connection changed during verification.");
      if (ownerCanonical(current.cluster) !== ownerCanonical(verified)) await this.save({...current,cluster:verified});
    };
    const next = this.clusterUpdates.catch(() => {}).then(work); this.clusterUpdates = next; return next;
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
    if (p.cloudExecution !== undefined && (p.mode !== "remote-border" || !["ordinary", "protected"].includes(p.cloudExecution))) throw Error("Unsupported saved cloud execution mode.");
    if (p.cloudPrincipal !== undefined) labAccess({ mode: "open-lab", principal: p.cloudPrincipal });
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
