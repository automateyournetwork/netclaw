import { createHash, randomUUID } from "node:crypto";
import { OwnerClient, OwnerError, ownerIdentifier, ownerCanonical, reviewText, unexpiredReview, withOwnerState } from "./owner";
import type { OwnerStorage } from "./owner";
import type { Json } from "./hud";
export type CombinedReference = { client_nonce: string; parent_id?: string; children?: { operation_id: string; decision_sent?: true }[]; cancel_sent?: true; not_submitted?: true };
const plain = (v: any): v is Json => v !== null && typeof v === "object" && !Array.isArray(v);
export function validateReference(value: any): asserts value is CombinedReference {
  if (!plain(value) || !ownerIdentifier(value.client_nonce) || Object.keys(value).some(k => !["client_nonce", "parent_id", "children", "cancel_sent", "not_submitted"].includes(k)) || value.parent_id !== undefined && !ownerIdentifier(value.parent_id) || value.cancel_sent !== undefined && (value.cancel_sent !== true || !value.parent_id) || value.not_submitted !== undefined && (value.not_submitted !== true || value.parent_id || value.children || value.cancel_sent)) throw Error("Combined reference is invalid. Preserve it for recovery.");
  if (value.parent_id && !value.children || value.children !== undefined && (!value.parent_id || !Array.isArray(value.children) || value.children.length !== 2 || value.children.some((c: any) => !plain(c) || !ownerIdentifier(c.operation_id) || Object.keys(c).some(k => !["operation_id", "decision_sent"].includes(k)) || c.decision_sent !== undefined && c.decision_sent !== true) || value.children[0].operation_id === value.children[1].operation_id)) throw Error("Combined child references are invalid.");
}
export function combinedCatalogChoices(catalog: Json): Record<number, Json[]> {
  const choices: Record<number, Json[]> = { 4: [], 6: [] };
  if (!Array.isArray(catalog.capabilities) || !catalog.capabilities.includes("calculator_combined_v1")) return choices;
  if (!Array.isArray(catalog.members) || catalog.members.length > 100) throw Error("Combined catalog is unavailable.");
  for (const entry of catalog.members) for (const family of [4, 6]) {
    if (!plain(entry.member) || typeof entry.member.member_id !== "string" || entry.member.member_id.length > 200 || !Array.isArray(entry.model_profiles) || !Array.isArray(entry.tools)) throw Error("Combined catalog is invalid.");
    for (const profile of entry.model_profiles) if (profile.profile_id === `ollama-cpu-ipv${family}` && profile.provider === "ollama" && ownerIdentifier(profile.profile_revision)) {
      for (const tool of entry.tools) if (tool.tool === (family === 4 ? "subnet_calculator" : "subnet_calculator_v6") && plain(tool.arguments) && Object.keys(tool.arguments).join() === "cidr" && typeof tool.arguments.cidr === "string" && tool.arguments.cidr.length <= 100) {
        choices[family]!.push({ family, member_id: entry.member.member_id, profile_revision: profile.profile_revision, cidr: tool.arguments.cidr });
        if (choices[family]!.length > 100) throw Error("Combined catalog exceeds the selection bound.");
      }
    }
  }
  return choices;
}
export const combinedReferencesKey = (origin: string, installation: string, principal: Json) => "owner-combined." + createHash("sha256").update(origin + "|" + installation + "|" + ownerCanonical(principal)).digest("hex");
export function mergedCombinedReference(old: CombinedReference | undefined, incoming: CombinedReference | undefined): CombinedReference | undefined {
  if (old) validateReference(old); if (incoming) validateReference(incoming);
  if (!old || !incoming) return structuredClone(old || incoming);
  if (old.client_nonce !== incoming.client_nonce || old.parent_id && incoming.parent_id && old.parent_id !== incoming.parent_id || old.not_submitted && incoming.parent_id || incoming.not_submitted && old.parent_id || old.children && incoming.children && old.children.some((c, i) => c.operation_id !== incoming.children![i]!.operation_id)) throw Error("Combined references conflict. Preserve both endpoints.");
  const children = incoming.children || old.children;
  const next = { ...old, ...incoming, ...(old.parent_id ? { parent_id: old.parent_id } : {}), ...(old.cancel_sent || incoming.cancel_sent ? { cancel_sent: true as const } : {}), ...(children ? { children: children.map((c, i) => ({ ...c, ...(old.children?.[i]?.decision_sent || incoming.children?.[i]?.decision_sent ? { decision_sent: true as const } : {}) })) } : {}) };
  validateReference(next); return next;
}

/** Exactly one retained parent per operator/installation. Only identifiers persist. */
export class CombinedOwnerOperations {
  private busy = false;
  value?: Json;
  uncertain = false;
  constructor(readonly client: OwnerClient, private storage: OwnerStorage) {}
  private key() {
    if (!this.client.operationsReady || !this.client.principal) throw Error("Connect the selected Border before recovering combined work.");
    return combinedReferencesKey(this.client.base, this.client.expectedId, this.client.principal);
  }
  reference(): CombinedReference | undefined {
    const row = this.storage.get<CombinedReference | undefined>(this.key(), undefined);
    if (row !== undefined) validateReference(row);
    return row && structuredClone(row);
  }
  private async put(ref: CombinedReference) {
    validateReference(ref); const old = this.reference();
    if (old && (old.client_nonce !== ref.client_nonce || old.parent_id && old.parent_id !== ref.parent_id || old.cancel_sent && !ref.cancel_sent || old.children?.some((c, i) => c.operation_id !== ref.children?.[i]?.operation_id || c.decision_sent && !ref.children?.[i]?.decision_sent))) throw Error("Combined identity changed. Nothing was resent.");
    await this.storage.update(this.key(), ref); this.client.assertOpen();
  }
  private async accept(value: Json) {
    const ref = this.reference();
    if (!ref || value.schemaVersion !== 1 || !ownerIdentifier(value.parent_id) || value.client_nonce !== ref.client_nonce || ref.parent_id && value.parent_id !== ref.parent_id || !["awaiting_decisions", "running", "complete", "partial", "failed", "cancelled", "unknown"].includes(value.state) || !Number.isSafeInteger(value.expires_at_ms) || !Array.isArray(value.children) || value.children.length !== 2) throw Error("Combined response changed. Recover the same parent.");
    value.children.forEach((child: Json, i: number) => {
      if (child.index !== i || child.family !== [4, 6][i] || ref.children && ref.children[i]!.operation_id !== child.operation_id || child.review?.border?.installation_id !== this.client.expectedId || !this.client.reviewPrincipalMatches(child.review?.principal) || !Array.isArray(child.allowed_actions)) throw Error("Combined child identity does not match this operator and Border.");
      reviewText(child);
    });
    if (value.children[0].operation_id === value.children[1].operation_id) throw Error("Combined children must be distinct.");
    await this.put({ ...ref, parent_id: value.parent_id, children: value.children.map((c: Json, i: number) => ({ operation_id: c.operation_id, ...(ref.children?.[i]?.decision_sent ? { decision_sent: true } : {}) })) });
    this.value = value; this.uncertain = false; return value;
  }
  private async exclusive<T>(action: () => Promise<T>): Promise<T> { if (this.busy) throw Error("A combined action is already in progress."); this.busy = true; try { return await withOwnerState(this.storage, action); } finally { this.busy = false; } }
  private async status() { const ref = this.reference(); if (!ref || ref.not_submitted) throw Error("Recover an existing submitted combined reference."); this.uncertain = true; return this.accept(await this.client.combinedStatus(ref)); }
  recover() { return this.exclusive(() => this.status()); }
  prepare(children: Json[]) { return this.exclusive(async () => {
    if (this.reference()) throw Error("Recover the retained combined request first.");
    const choices = combinedCatalogChoices(await this.client.catalog());
    if (children.length !== 2 || children.some((c, i) => c.family !== [4, 6][i] || !choices[c.family]!.some(v => ownerCanonical(v) === ownerCanonical(c)))) throw Error("Combined selection changed.");
    const ref = { client_nonce: randomUUID() }; await this.put(ref); this.uncertain = true;
    try { return await this.accept(await this.client.prepareCombined({ ...ref, children })); }
    catch (error) { if (error instanceof OwnerError && error.notSubmitted) { await this.put({ ...ref, not_submitted: true }); this.uncertain = false; } throw error; }
  }); }
  decide(reviewed: Json, index: number, decision: "approve" | "deny") { return this.exclusive(async () => {
    if (![0, 1].includes(index) || !["approve", "deny"].includes(decision) || this.uncertain) throw Error("Recover the exact combined review first.");
    const current = await this.status(), ref = this.reference()!, child = current.children[index];
    if (reviewed.parent_id !== current.parent_id || ref.cancel_sent || ref.children![index]!.decision_sent || reviewText(child) !== reviewText(reviewed.children[index]) || child.state !== "review_pending" || !child.allowed_actions.includes(decision) || decision === "approve" && (!unexpiredReview(child) || current.expires_at_ms <= Date.now())) throw Error("This child decision changed, expired or was already sent.");
    ref.children![index]!.decision_sent = true; await this.put(ref); this.uncertain = true;
    await this.client.decision(child.operation_id, child.revision, child.review_digest, decision, child.review.limits.expires_at_ms);
    return this.status();
  }); }
  cancel() { return this.exclusive(async () => { const ref = this.reference(); if (!ref?.parent_id || ref.cancel_sent) throw Error("Recover the existing combined cancellation."); await this.put({ ...ref, cancel_sent: true }); this.uncertain = true; await this.client.cancelCombined(ref.parent_id); return this.status(); }); }
  async discard() {
    const ref = this.reference(), resolved = this.value && ["complete", "partial", "failed", "cancelled"].includes(this.value.state) && this.value.children.every((c: Json) => c.reconciliation_required === false && (!c.may_have_executed || c.result?.verified === true && c.result?.durable_ack === true && c.result?.ack_delivery_pending === false));
    if (this.busy || this.uncertain || !ref || !ref.not_submitted && !resolved) throw Error("Unresolved combined references must be retained.");
    await this.storage.update(this.key(), undefined); this.value = undefined;
  }
}
