import * as vscode from "vscode";
import { randomUUID } from "node:crypto";
import { Connection } from "../connection/connect";
import { LocalState } from "../state/local";
import { OwnerOperations, catalogChoices, reviewText, unexpiredReview } from "../client/owner";
import { CombinedOwnerOperations, combinedCatalogChoices } from "../client/combined";
import type { Json, Runtime } from "../client/hud";
import { remoteHudFeatures, remoteDomainFeature, remoteCommandFeature } from "../client/remote-hud";

const allowed = new Set(["addConnection", "selectConnection", "disconnect", "renameConnection", "removeConnection", "ownerSignIn", "ownerSignOut", "ownerPrepare", "ownerRecover", "refresh", "help"]);
export function assertCloudCommand(name: string, remote: boolean, args: unknown[] = [], runtime?: Runtime) {
  if (!remote || allowed.has(name)) return;
  if (runtime?.capabilities?.remoteHud) {
    const feature = name === "openDomain" ? remoteDomainFeature[String(args[0])] : remoteCommandFeature[name];
    if (feature && remoteHudFeatures(runtime).has(feature)) return;
    throw Error("This action is unavailable on the selected cloud Border. Host filesystem, lifecycle and setup controls require a local profile.");
  }
  if (["openOverview", "openOperations"].includes(name) || name === "openDomain" && ["overview", "operations"].includes(String(args[0]))) return;
  throw Error("This cloud Border supports protected owner operations. Select a local profile for workspace, lifecycle, Chat, MCP and setup controls.");
}
export function ownerDecisionDetail(origin: string, installation: string, operation: Json) {
  reviewText(operation);
  const args = JSON.stringify(operation.review.tool_call.arguments);
  return `${origin}\nInstallation: ${installation}\nOperation: ${operation.operation_id}\nRevision: ${operation.revision}\nReview SHA-256: ${operation.review_digest}\nMember: ${operation.review.member.member_id}\nCall: ${operation.review.tool_call.tool}\nArguments: ${args.length <= 500 ? args : "See complete immutable review"}\n\nThe complete owner, Border, member, model, call arguments and limits are in the read-only Cloud-Border.json review. This decision uses exactly that revision and digest.`;
}

/** Native input/review; virtual documents contain private output in memory only. */
export class OwnerWorkflow implements vscode.Disposable {
  private busy = false;
  private text = "";
  private uri?: vscode.Uri;
  private events = new vscode.EventEmitter<vscode.Uri>();
  private subscriptions: vscode.Disposable[];
  private operations?: OwnerOperations;
  private combined?: CombinedOwnerOperations;
  private generation = -1;
  constructor(private connection: Connection, private local: LocalState) {
    this.subscriptions = [this.events, vscode.workspace.registerTextDocumentContentProvider("netclaw-owner", {
      onDidChange: this.events.event,
      provideTextDocumentContent: uri => uri.toString() === this.uri?.toString() ? this.text : "This owner view is no longer available.",
    }), connection.changed.event(() => {
      if (this.generation !== connection.generation || !connection.owner?.operationsReady) this.clear();
    })];
  }
  private clear() { this.text = "Owner view cleared. Reconnect and recover the same operation."; if (this.uri) this.events.fire(this.uri); }
  private scope() {
    const bound = this.connection.ownerBound();
    if (!this.operations || this.generation !== this.connection.generation) {
      this.operations = new OwnerOperations(bound.client, this.local); this.combined = new CombinedOwnerOperations(bound.client, this.local); this.generation = this.connection.generation;
    }
    return { ...bound, operations: this.operations, combined: this.combined! };
  }
  private async exclusive<T>(work: () => Promise<T>): Promise<T> {
    if (this.busy) throw Error("An owner workflow is already open. Finish or cancel it first.");
    this.busy = true; try { return await work(); } finally { this.busy = false; }
  }
  private async signInBound(bound: ReturnType<OwnerWorkflow["scope"]>) {
    if (bound.client.openLab) throw Error("This lab Border connects without sign-in.");
    const ticket = await vscode.window.showInputBox({ title: "Sign in to cloud Border", prompt: `One-use owner ticket for ${bound.client.base}. Installation ${bound.client.expectedId}.`, password: true, ignoreFocusOut: true });
    if (!ticket) return false;
    bound.current(); await bound.run(() => bound.client.login(ticket));
    this.connection.changed.fire(); return true;
  }
  async signIn() { return this.exclusive(() => this.signInBound(this.scope())); }
  async signOut() { return this.exclusive(async () => { const b = this.scope(); if (b.client.openLab) throw Error("This lab Border does not use sign-in."); await b.run(() => b.client.logout()); this.clear(); this.connection.changed.fire(); }); }
  private async ensureReady(b: ReturnType<OwnerWorkflow["scope"]>) {
    if (b.client.openLab) { await b.run(() => b.client.inspectAccess()); return true; }
    if (!b.client.sessionState && !await this.signInBound(b)) return false;
    await b.run(() => b.client.inspectSession()); return true;
  }
  private async document(value: unknown, title: string, current: () => void) {
    current();
    // One virtual, read-only document; never an untitled backup or saved workspace file.
    if (!this.uri) this.uri = vscode.Uri.parse(`netclaw-owner:/${randomUUID()}/Cloud-Border.json`);
    this.text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    this.events.fire(this.uri);
    const doc = await vscode.workspace.openTextDocument(this.uri);
    current();
    await vscode.window.showTextDocument(doc, { preview: true });
    void vscode.window.setStatusBarMessage(title, 6000);
  }
  async overview() {
    const b = this.scope(); await b.run(() => b.client.connect());
    await this.document({ origin: b.client.base, installationId: b.client.expectedId, role: "border", ...(b.client.openLab ? { access: b.client.access } : { owner: b.client.sessionState || "Sign in with an owner ticket" }), capabilities: b.client.runtime?.capabilities,
      workflow: "Use Prepare cloud read or Recover cloud operation. Local lifecycle, legacy Chat, MCP and model controls are unavailable." }, "Cloud Border identity", b.current);
  }
  async open() {
    const lab = this.connection.owner?.openLab;
    const selected = await vscode.window.showQuickPick([
      { label: "Prepare cloud read", action: () => this.prepare() },
      { label: "Recover cloud operation", action: () => this.recover() },
      { label: "Prepare local IPv4 + cloud IPv6", action: () => this.prepareCombined() },
      { label: "Recover combined subnet request", action: () => this.recoverCombined() },
      ...(!lab ? [
        { label: "Sign in to cloud Border", action: () => this.signIn() },
        { label: "Sign out of cloud Border", action: () => this.signOut() },
      ] : []),
    ], { title: lab ? "Cloud operations" : "Protected cloud operations" });
    return selected?.action();
  }
  async prepare() {
    return this.exclusive(async () => {
      const b = this.scope(); if (!await this.ensureReady(b)) return;
      const choices = catalogChoices(await b.run(() => b.client.catalog()));
      const selected = await vscode.window.showQuickPick(choices.map(selection => ({ label: selection.tool as string, description: `${selection.member_id} · ${selection.model_profile_id}`, detail: JSON.stringify(selection.arguments), selection })), { title: "Select an exact catalog read", matchOnDescription: true, matchOnDetail: true, ignoreFocusOut: true });
      if (!selected) return;
      b.current();
      const operation = await b.run(() => b.operations.prepare(selected.selection));
      return this.review(b, operation);
    });
  }
  private async review(b: ReturnType<OwnerWorkflow["scope"]>, operation: Json): Promise<Json> {
    const fullReview = reviewText(operation);
    await this.document(fullReview, "Complete immutable cloud operation review", b.current);
    const reference = b.operations.references().find(r => r.operation_id === operation.operation_id);
    if (operation.state !== "review_pending" || reference?.decision_sent || !operation.allowed_actions?.includes("approve") ||
      b.client.openLab && !b.client.reviewPrincipalMatches(operation.review?.principal)) { await this.showResult(b, operation); return operation; }
    const ready = await vscode.window.showInformationMessage("The complete immutable review is open in Cloud-Border.json. Read it before reviewing a decision.", "Review decision");
    b.current();
    if (ready !== "Review decision") return operation;
    const expired = !unexpiredReview(operation);
    const choice = await vscode.window.showInformationMessage(expired ? "This cloud review has expired" : "Review this exact cloud read", { modal: true,
      detail: `${ownerDecisionDetail(b.client.base, b.client.expectedId, operation)}\n\n${expired ? "Approval is unavailable. Deny this expired review to resolve it without execution." : "Approve submits this exact revision and digest once."} Cancel keeps the review for recovery.` }, ...(expired ? ["Deny"] : ["Approve once", "Deny"]));
    b.current();
    if (choice !== "Approve once" && choice !== "Deny") return operation;
    const result = await b.run(() => b.operations.decide(operation, choice === "Approve once" ? "approve" : "deny"));
    await this.showResult(b, result); return result;
  }
  private async showResult(b: ReturnType<OwnerWorkflow["scope"]>, operation: Json) {
    b.current();
    const evidence = { origin: b.client.base, installationId: b.client.expectedId, principal: operation.review?.principal,
      state: operation.state, verification: { signedResultVerified: operation.result?.verified === true, durableAcknowledgement: operation.result?.durable_ack === true, acknowledgementDeliveryPending: operation.result?.ack_delivery_pending },
      operation, next: "Recover this same operation to check status or reconcile. No preparation or approval is retried." };
    const verified = operation.result?.verified === true, acknowledged = operation.result?.durable_ack === true && operation.result?.ack_delivery_pending === false;
    const message = `Cloud operation ${operation.operation_id}: ${String(operation.state).replaceAll("_", " ")}. ${verified ? "Signed result verified." : "No verified result yet."} ${acknowledged ? "Delivery acknowledged." : "Delivery is not yet acknowledged."}`;
    void vscode.window.showInformationMessage(message, "View evidence").then(async selected => {
      if (selected !== "View evidence") return;
      try { b.current(); await this.document(evidence, "Cloud operation evidence", b.current); } catch { /* The selected connection may have changed while the message was open. */ }
    });
  }
  async recover() {
    return this.exclusive(async () => {
      const b = this.scope(); if (!await this.ensureReady(b)) return;
      const refs = b.operations.references();
      if (!refs.length) { void vscode.window.showInformationMessage("No retained operations for this Border."); return; }
      const selected = await vscode.window.showQuickPick(refs.map(ref => ({ label: ref.operation_id || "Unconfirmed preparation", description: ref.client_nonce, ref })), { title: "Recover the same cloud operation", ignoreFocusOut: true });
      if (!selected) return;
      b.current();
      if (selected.ref.not_submitted) {
        const action = await vscode.window.showInformationMessage("Discard this rejected preparation?", { modal: true, detail: `${b.client.base}\nInstallation: ${b.client.expectedId}\nNonce: ${selected.ref.client_nonce}\nThe exact prepare response proved rejection before admission. No operation or execution was submitted. Only this local reference will be removed.` }, "Discard rejected preparation");
        if (action === "Discard rejected preparation") { b.current(); await b.run(() => b.operations.discardUnsubmitted(selected.ref)); }
        return;
      }
      let operation = await b.run(() => b.operations.recover(selected.ref));
      if (operation.state === "review_pending" && !selected.ref.decision_sent) return this.review(b, operation);
      await this.showResult(b, operation);
      if (operation.allowed_actions?.includes("reconcile") && (operation.result?.durable_ack !== true || operation.result?.ack_delivery_pending !== false)) {
        const action = await vscode.window.showInformationMessage("Check member evidence for this same operation?", { modal: true, detail: `${b.client.base}\n${operation.operation_id}\nThis reconciles existing work; it does not prepare or approve another execution.` }, "Reconcile existing work");
        if (action === "Reconcile existing work") { b.current(); operation = await b.run(() => b.operations.reconcile(selected.ref)); await this.showResult(b, operation); }
      }
      return operation;
    });
  }
  async prepareCombined() {
    return this.exclusive(async () => {
      const b = this.scope(); if (!await this.ensureReady(b)) return;
      const choices = combinedCatalogChoices(await b.run(() => b.client.catalog())), children: Json[] = [];
      if (!choices[4]!.length || !choices[6]!.length) throw Error("This Border does not advertise two qualified Ollama calculator members.");
      for (const family of [4, 6]) {
        const selected = await vscode.window.showQuickPick(choices[family]!.map(selection => ({ label: selection.cidr, description: selection.member_id, detail: `IPv${family} · local Ollama inference · ${selection.profile_revision}`, selection })), { title: `Select exact IPv${family} calculation`, ignoreFocusOut: true });
        if (!selected) return; b.current(); children.push(selected.selection);
      }
      return this.reviewCombined(b, await b.run(() => b.combined.prepare(children)));
    });
  }
  private async reviewCombined(b: ReturnType<OwnerWorkflow["scope"]>, value: Json): Promise<Json> {
    await this.document(value, "Combined subnet request — two separate approvals", b.current);
    const ref = b.combined.reference()!;
    const options = value.children.filter((child: Json) => child.state === "review_pending" && !ref.children?.[child.index]?.decision_sent && child.allowed_actions?.some((a: string) => ["approve", "deny"].includes(a))).map((child: Json) => ({ label: `Review IPv${child.family}`, description: child.review.member.member_id, detail: child.review.tool_call.arguments.cidr, child }));
    const selected = await vscode.window.showQuickPick([...options, { label: "Keep for recovery", child: null }], { title: `Combined request: ${value.state}`, ignoreFocusOut: true });
    if (!selected?.child) return value;
    const child = selected.child; b.current(); await this.document(reviewText(child), `Complete IPv${child.family} review`, b.current);
    const ready = await vscode.window.showInformationMessage(`The complete immutable IPv${child.family} review is open in Cloud-Border.json. Read it before deciding.`, "Review decision");
    b.current(); if (ready !== "Review decision") return value;
    const expired = !unexpiredReview(child);
    const decision = await vscode.window.showInformationMessage(`Review IPv${child.family} only`, { modal: true, detail: `${ownerDecisionDetail(b.client.base, b.client.expectedId, child)}\nProvider/model: ${child.review.model_profile.provider} / ${child.review.model_profile.model}\n\nThe other child requires its own separate approval. Provider API charge is zero; compute costs remain.` }, ...(expired ? ["Deny"] : ["Approve once", "Deny"]));
    b.current(); if (!["Approve once", "Deny"].includes(decision || "")) return value;
    const updated = await b.run(() => b.combined.decide(value, child.index, decision === "Approve once" ? "approve" : "deny"));
    await this.document(updated, "Combined result and retained child evidence", b.current);
    // The next child always requires a new native review and distinct decision.
    return this.reviewCombined(b, updated);
  }
  async recoverCombined() {
    return this.exclusive(async () => {
      const b = this.scope(); if (!await this.ensureReady(b)) return;
      const ref = b.combined.reference(); if (!ref) { void vscode.window.showInformationMessage("No retained combined request for this Border/operator."); return; }
      if (ref.not_submitted) {
        const chosen = await vscode.window.showInformationMessage("Discard the confirmed unsubmitted combined reference?", { modal: true, detail: "No work was admitted. Only the local reference will be removed." }, "Discard");
        if (chosen === "Discard") await b.run(() => b.combined.discard()); return;
      }
      const value = await b.run(() => b.combined.recover());
      await this.document(value, "Combined status recovered without replay", b.current);
      const chosen = await vscode.window.showQuickPick(["Review one pending child", "Keep reference", "Cancel remaining children", "Remove resolved reference"], { title: `Combined request: ${value.state}` });
      b.current();
      if (chosen === "Review one pending child") return this.reviewCombined(b, value);
      if (chosen === "Cancel remaining children") return this.document(await b.run(() => b.combined.cancel()), "Combined cancellation", b.current);
      if (chosen === "Remove resolved reference") await b.run(() => b.combined.discard());
      return value;
    });
  }
  dispose() { this.clear(); this.subscriptions.forEach(d => d.dispose()); }
}
