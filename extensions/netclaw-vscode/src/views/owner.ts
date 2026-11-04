import * as vscode from "vscode";
import { randomUUID } from "node:crypto";
import { Connection } from "../connection/connect";
import { LocalState } from "../state/local";
import { OwnerOperations, catalogChoices, reviewText, unexpiredReview } from "../client/owner";
import type { Json } from "../client/hud";

const allowed = new Set(["addConnection", "selectConnection", "disconnect", "renameConnection", "removeConnection", "openOverview", "openOperations", "ownerSignIn", "ownerSignOut", "ownerPrepare", "ownerRecover", "refresh", "help", "openDocumentation"]);
export function assertCloudCommand(name: string, remote: boolean, args: unknown[] = []) {
  if (remote && !allowed.has(name) && !(name === "openDomain" && ["overview", "operations"].includes(String(args[0]))))
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
  private generation = -1;
  constructor(private connection: Connection, private local: LocalState) {
    this.subscriptions = [this.events, vscode.workspace.registerTextDocumentContentProvider("netclaw-owner", {
      onDidChange: this.events.event,
      provideTextDocumentContent: uri => uri.toString() === this.uri?.toString() ? this.text : "This owner view is no longer available.",
    }), connection.changed.event(() => {
      if (this.generation !== connection.generation || !connection.owner?.sessionState) this.clear();
    })];
  }
  private clear() { this.text = "Owner view cleared. Reconnect and recover the same operation."; if (this.uri) this.events.fire(this.uri); }
  private scope() {
    const bound = this.connection.ownerBound();
    if (!this.operations || this.generation !== this.connection.generation) {
      this.operations = new OwnerOperations(bound.client, this.local); this.generation = this.connection.generation;
    }
    return { ...bound, operations: this.operations };
  }
  private async exclusive<T>(work: () => Promise<T>): Promise<T> {
    if (this.busy) throw Error("An owner workflow is already open. Finish or cancel it first.");
    this.busy = true; try { return await work(); } finally { this.busy = false; }
  }
  private async signInBound(bound: ReturnType<OwnerWorkflow["scope"]>) {
    const ticket = await vscode.window.showInputBox({ title: "Sign in to cloud Border", prompt: `One-use owner ticket for ${bound.client.base}. Installation ${bound.client.expectedId}.`, password: true, ignoreFocusOut: true });
    if (!ticket) return false;
    bound.current(); await bound.run(() => bound.client.login(ticket));
    this.connection.changed.fire(); return true;
  }
  async signIn() { return this.exclusive(() => this.signInBound(this.scope())); }
  async signOut() { return this.exclusive(async () => { const b = this.scope(); await b.run(() => b.client.logout()); this.clear(); this.connection.changed.fire(); }); }
  private async authenticated(b: ReturnType<OwnerWorkflow["scope"]>) {
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
    await this.document({ origin: b.client.base, installationId: b.client.expectedId, role: "border", owner: b.client.sessionState || "Sign in with an owner ticket", capabilities: b.client.runtime?.capabilities,
      workflow: "Use Prepare cloud read or Recover cloud operation. Local lifecycle, legacy Chat, MCP and model controls are unavailable." }, "Cloud Border identity", b.current);
  }
  async open() {
    const selected = await vscode.window.showQuickPick([
      { label: "Prepare cloud read", action: () => this.prepare() },
      { label: "Recover cloud operation", action: () => this.recover() },
      { label: "Sign in to cloud Border", action: () => this.signIn() },
      { label: "Sign out of cloud Border", action: () => this.signOut() },
    ], { title: "Protected cloud operations" });
    return selected?.action();
  }
  async prepare() {
    return this.exclusive(async () => {
      const b = this.scope(); if (!await this.authenticated(b)) return;
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
    if (operation.state !== "review_pending" || reference?.decision_sent || !operation.allowed_actions?.includes("approve")) { await this.showResult(b, operation); return operation; }
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
    await this.document({ origin: b.client.base, installationId: b.client.expectedId, principal: b.client.sessionState?.principal,
      state: operation.state, verification: { signedResultVerified: operation.result?.verified === true, durableAcknowledgement: operation.result?.durable_ack === true, acknowledgementDeliveryPending: operation.result?.ack_delivery_pending },
      operation, next: "Recover this same operation to check status or reconcile. No preparation or approval is retried." }, "Cloud operation status and audit evidence", b.current);
  }
  async recover() {
    return this.exclusive(async () => {
      const b = this.scope(); if (!await this.authenticated(b)) return;
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
  dispose() { this.clear(); this.subscriptions.forEach(d => d.dispose()); }
}
