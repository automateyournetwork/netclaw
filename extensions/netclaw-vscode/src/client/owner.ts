import { createHash, randomUUID } from "node:crypto";
import type { Runtime, Json } from "./hud";

export const ownerIdentifier = (v: unknown): v is string => typeof v === "string" && /^[A-Za-z0-9_.:-]{1,200}$/.test(v);
export const installationIdentifier = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(v);
const object = (v: any): v is Json => v !== null && typeof v === "object" && !Array.isArray(v);
const token = (v: unknown): v is string => typeof v === "string" && /^[A-Za-z0-9_-]{43}$/.test(v);
export function ownerCanonical(value: unknown, depth = 0): string {
  if (depth > 32) throw Error("Protected JSON exceeds its depth limit.");
  if (value === null || typeof value === "boolean" || typeof value === "string" || typeof value === "number" && Number.isSafeInteger(value)) return JSON.stringify(value);
  if (Array.isArray(value) && value.length <= 10000) return "[" + value.map(v => ownerCanonical(v, depth + 1)).join(",") + "]";
  if (object(value) && Object.keys(value).length <= 10000 && Object.keys(value).every(k => /^[\x00-\x7f]{0,200}$/.test(k))) return "{" + Object.keys(value).sort().map(k => JSON.stringify(k) + ":" + ownerCanonical(value[k], depth + 1)).join(",") + "}";
  throw Error("Protected JSON is invalid.");
}
export function ownerOrigin(value: string): string {
  let u: URL;
  try { u = new URL(value); } catch { throw Error("Enter the Border's canonical HTTPS origin."); }
  if (u.protocol !== "https:" || u.username || u.password || value !== u.origin || !u.hostname || /[\s\\]/.test(value))
    throw Error("Use a canonical HTTPS origin without a path, credentials, query or fragment.");
  return u.origin;
}
export type OwnerSession = { authenticated: true; installation_id: string; principal: Json; expires_ms: number };
export class OwnerError extends Error {
  constructor(message: string, readonly status = 0, readonly notSubmitted = false) { super(message); }
}

/** Only the existing protected owner API; no generic HTTP, model or admin API. */
export class OwnerClient {
  readonly base: string;
  readonly cookieName: string;
  runtime?: Runtime;
  sessionState?: OwnerSession;
  private cookie = "";
  private csrf = "";
  private closed = false;
  private pending = new Set<AbortController>();
  private current() { if (this.closed) throw new OwnerError("Cloud connection closed. Recover the same operation after reconnecting."); }
  assertOpen() { this.current(); }
  constructor(origin: string, readonly expectedId: string, private saveCookie: (value: string) => Promise<void> = async () => {}, private sessionLost: () => void = () => {}) {
    this.base = ownerOrigin(origin);
    if (!installationIdentifier(expectedId)) throw Error("Supply the expected Border installation UUID from its operator.");
    this.cookieName = "__Host-nc_owner_" + expectedId;
  }
  restoreCookie(value: string) {
    this.current();
    if (value && (value.split("=").length !== 2 || value.split("=")[0] !== this.cookieName || !token(value.split("=")[1])))
      throw Error("The saved owner session does not match this Border.");
    this.cookie = value;
  }
  private async forget() {
    this.cookie = ""; this.csrf = ""; this.sessionState = undefined;
    this.sessionLost(); await this.saveCookie("");
  }
  async connect(): Promise<Runtime> {
    const r = await this.request("/api/runtime");
    this.current();
    if (r.installationId !== this.expectedId || r.kind !== "openclaw" || r.role !== "border" ||
      !["protectedProfile", "protectedOperations", "protectedProduction"].every(k => r.capabilities?.[k] === true)) {
      await this.forget(); this.close(); throw Error("The endpoint is not the expected protected cloud Border. Review its identity and capabilities.");
    }
    this.runtime = r as Runtime;
    return this.runtime;
  }
  private acceptSession(value: Json): OwnerSession {
    this.current();
    const p = value.principal;
    if (value.authenticated !== true || value.installation_id !== this.expectedId || !token(value.csrf_token) ||
      !Number.isSafeInteger(value.expires_ms) || value.expires_ms <= Date.now() || !object(p) || p.issuer !== "local" ||
      Object.keys(p).sort().join(",") !== "display_name,issuer,roles,subject" ||
      !ownerIdentifier(p.subject) || typeof p.display_name !== "string" || p.display_name.length > 200 ||
      !Array.isArray(p.roles) || p.roles.length !== 1 || p.roles[0] !== "owner")
      throw Error("The Border did not return a valid unexpired owner session.");
    this.csrf = value.csrf_token;
    this.sessionState = { authenticated: true, installation_id: this.expectedId, principal: p, expires_ms: value.expires_ms };
    return this.sessionState;
  }
  async inspectSession(): Promise<OwnerSession> {
    await this.connect();
    this.current();
    try { return this.acceptSession(await this.request("/api/hud/owner/session")); }
    catch (error) { await this.forget(); throw error; }
  }
  async login(ticket: string): Promise<OwnerSession> {
    if (!token(ticket)) throw Error("Enter the one-use owner ticket supplied by the Border operator.");
    await this.connect();
    this.current();
    try {
      const value = await this.request("/api/hud/owner/session", "POST", { ticket }, true);
      if (!this.cookie) throw Error("No owner session was established.");
      return this.acceptSession(value);
    } catch (error) { await this.forget(); throw error; }
  }
  async logout() {
    try { await this.inspectSession(); await this.request("/api/hud/owner/session", "DELETE", {}); }
    finally { await this.forget(); }
  }
  async catalog(): Promise<Json> { await this.inspectSession(); return this.request("/api/hud/operations/catalog"); }
  async prepare(body: Json): Promise<Json> { await this.inspectSession(); return this.request("/api/hud/operations", "POST", body); }
  async status(ref: OperationReference): Promise<Json> {
    validReference(ref); await this.inspectSession();
    return this.request(ref.operation_id ? "/api/hud/operations/" + ref.operation_id : "/api/hud/operations?client_nonce=" + encodeURIComponent(ref.client_nonce));
  }
  async decision(id: string, revision: number, digest: string, decision: "approve" | "deny"): Promise<Json> {
    if (!ownerIdentifier(id) || !Number.isSafeInteger(revision) || revision < 0 || !/^[a-f0-9]{64}$/.test(digest) || !["approve", "deny"].includes(decision)) throw Error("The exact operation review is unavailable.");
    await this.inspectSession();
    return this.request("/api/hud/operations/" + id + "/decision", "POST", { revision, review_digest: digest, decision });
  }
  async reconcile(id: string): Promise<Json> {
    if (!ownerIdentifier(id)) throw Error("Operation identity is unavailable.");
    await this.inspectSession(); return this.request("/api/hud/operations/" + id + "/reconcile", "POST", {});
  }
  private async request(route: string, method = "GET", body?: Json, bootstrap = false): Promise<Json> {
    this.current();
    const controller = new AbortController(); this.pending.add(controller);
    const timer = setTimeout(() => controller.abort(), 35000);
    try {
      const headers: Record<string, string> = { Accept: "application/json", "X-NetClaw-Installation": this.expectedId };
      if (this.cookie && route !== "/api/runtime") headers.Cookie = this.cookie;
      if (method !== "GET") {
        headers.Origin = this.base; headers["Content-Type"] = "application/json";
        if (bootstrap) headers["X-NetClaw-Owner-Bootstrap"] = "1";
        else headers["X-NetClaw-CSRF"] = this.csrf;
      }
      const response = await fetch(this.base + route, { method, headers, redirect: "error", cache: "no-store", signal: controller.signal,
        ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
      this.current();
      if (!response.headers.get("content-type")?.includes("application/json")) throw Error("Invalid response");
      const reader = response.body?.getReader(); if (!reader) throw Error("Empty response");
      const chunks: Uint8Array[] = []; let bytes = 0;
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        this.current();
        bytes += value.length;
        if (bytes > 4 * 1024 * 1024) { await reader.cancel(); throw Error("Oversized response"); }
        chunks.push(value);
      }
      const data = JSON.parse(Buffer.concat(chunks).toString("utf8"));
      this.current();
      if (!object(data)) throw Error("Invalid response");
      if (!response.ok) {
        if (response.status === 401 || response.status === 409 && data.code === "installation_changed") await this.forget();
        const notSubmitted = route === "/api/hud/operations" && method === "POST" && data.admission === "not_submitted";
        throw new OwnerError(response.status === 401 ? "Owner session expired or was revoked. Sign in again to recover existing work." :
          response.status === 409 && data.code === "installation_changed" ? "Border identity changed. Disconnect and review the destination." :
          notSubmitted ? "The review was rejected before submission. Nothing executed." :
          `The Border refused this request (HTTP ${response.status}). Check the same operation before continuing; nothing was resent.`, response.status, notSubmitted);
      }
      const cookies = response.headers.getSetCookie();
      if (cookies.length) {
        if (route !== "/api/hud/owner/session" || !["POST", "DELETE"].includes(method) || cookies.length !== 1) throw Error("Unexpected cookie");
        const pair = cookies[0]!.split(";")[0]!;
        const attrs = cookies[0]!.split(";").slice(1).map(v => v.trim().toLowerCase());
        if (!attrs.includes("secure") || !attrs.includes("httponly") || !attrs.includes("path=/") || !attrs.includes("samesite=strict") || attrs.some(v => v.startsWith("domain="))) throw Error("Invalid cookie scope");
        if (method === "DELETE" && pair === this.cookieName + "=") this.cookie = "";
        else this.restoreCookie(pair);
        await this.saveCookie(this.cookie);
        this.current();
      }
      this.current();
      return data;
    } catch (error) {
      if (error instanceof OwnerError) throw error;
      // Never repeat a mutation or include URL, ticket, cookie, response or socket errors.
      throw new OwnerError("The Border response was not confirmed. Check its HTTPS identity and the same operation's status; nothing was resent.");
    } finally { clearTimeout(timer); this.pending.delete(controller); }
  }
  close() { this.closed = true; this.csrf = ""; this.cookie = ""; this.runtime = undefined; this.sessionState = undefined; for (const c of this.pending) c.abort(); this.pending.clear(); this.sessionLost(); }
}

export type OperationReference = { client_nonce: string; operation_id?: string; decision_sent?: true };
export type OwnerStorage = { get<T>(key: string, fallback: T): T; update<T>(key: string, value: T): Promise<void> };
const validReference = (r: OperationReference) => {
  if (!object(r) || !ownerIdentifier(r.client_nonce) || r.operation_id !== undefined && !ownerIdentifier(r.operation_id) ||
    r.decision_sent !== undefined && (r.decision_sent !== true || !r.operation_id) || Object.keys(r).some(k => !["client_nonce", "operation_id", "decision_sent"].includes(k))) throw Error("Retained operation identity is invalid. Preserve it for recovery.");
};
export function catalogChoices(catalog: Json): Json[] {
  if (!ownerIdentifier(catalog.revision) && !Number.isSafeInteger(catalog.revision) || !Array.isArray(catalog.members) || catalog.members.length > 100) throw Error("The protected catalog is unavailable.");
  const choices: Json[] = [];
  for (const row of catalog.members) {
    if (!object(row.member) || typeof row.member.member_id !== "string" || row.member.member_id.length > 200 || !Array.isArray(row.tools) || !Array.isArray(row.model_profiles)) throw Error("The protected catalog is invalid.");
    for (const model of row.model_profiles) for (const tool of row.tools) {
      if (!ownerIdentifier(model.profile_id) || !ownerIdentifier(tool.tool) || !object(tool.arguments) || Buffer.byteLength(JSON.stringify(tool.arguments)) > 65536) throw Error("The protected catalog is invalid.");
      choices.push({ catalog_revision: catalog.revision, member_id: row.member.member_id, model_profile_id: model.profile_id, tool: tool.tool, arguments: tool.arguments });
      if (choices.length > 1000) throw Error("The protected catalog exceeds the selection limit.");
    }
  }
  return choices;
}
export function reviewText(op: Json): string {
  if (!ownerIdentifier(op.operation_id) || !ownerIdentifier(op.client_nonce) || !Number.isSafeInteger(op.revision) || op.revision < 0 || !/^[a-f0-9]{64}$/.test(op.review_digest) || !object(op.review) ||
    !["principal", "border", "member", "model_profile", "tool_call", "limits"].every(k => object(op.review[k])) || !Object.hasOwn(op.review, "change_request_ref") ||
    createHash("sha256").update(ownerCanonical(op.review)).digest("hex") !== op.review_digest) throw Error("The complete immutable review is unavailable or its digest changed.");
  return JSON.stringify({ operation_id: op.operation_id, revision: op.revision, review_digest: op.review_digest, review: op.review }, null, 2);
}

/** Durable identifiers only. A sent-decision bit prevents replay after a lost reply/restart. */
export class OwnerOperations {
  private busy = false;
  private readonly key: string;
  constructor(readonly client: OwnerClient, private storage: OwnerStorage) {
    this.key = "owner-operations." + createHash("sha256").update(client.base + "|" + client.expectedId).digest("hex");
  }
  references(): OperationReference[] {
    const rows = this.storage.get<OperationReference[]>(this.key, []);
    if (!Array.isArray(rows) || rows.length > 32) throw Error("Retained operation references are invalid.");
    rows.forEach(validReference);
    if (new Set(rows.map(r => r.client_nonce)).size !== rows.length || new Set(rows.filter(r => r.operation_id).map(r => r.operation_id)).size !== rows.filter(r => r.operation_id).length) throw Error("Retained operation references conflict.");
    return structuredClone(rows);
  }
  private async put(ref: OperationReference) {
    validReference(ref);
    const rows = this.references(), i = rows.findIndex(r => r.client_nonce === ref.client_nonce);
    if (rows.some((r, n) => n !== i && r.operation_id && r.operation_id === ref.operation_id) || i >= 0 && rows[i]!.operation_id && rows[i]!.operation_id !== ref.operation_id) throw Error("Operation identity changed. Nothing was resent.");
    if (i < 0) { if (rows.length >= 32) throw Error("32 operation references are retained. Recover existing work before preparing more."); rows.push(ref); }
    else rows[i] = { ...rows[i], ...ref };
    await this.storage.update(this.key, rows);
  }
  private async accept(ref: OperationReference, op: Json) {
    if (!ownerIdentifier(op.operation_id) || op.client_nonce !== ref.client_nonce || ref.operation_id && op.operation_id !== ref.operation_id ||
      op.review?.border?.installation_id !== this.client.expectedId || !this.client.sessionState || ownerCanonical(op.review?.principal) !== ownerCanonical(this.client.sessionState.principal)) throw Error("Returned operation does not belong to this owner and Border. Nothing was resent.");
    reviewText(op);
    await this.put({ ...ref, operation_id: op.operation_id });
    this.client.assertOpen();
    return op;
  }
  private async exclusive<T>(work: () => Promise<T>): Promise<T> {
    if (this.busy) throw Error("An owner action is already in progress. Check its status before continuing.");
    this.busy = true; try { return await work(); } finally { this.busy = false; }
  }
  async prepare(selection: Json): Promise<Json> {
    return this.exclusive(async () => {
      for (const ref of this.references()) {
        const previous = await this.accept(ref, await this.client.status(ref));
        const unexecuted = ["refused", "revoked", "denied"].includes(previous.state) && previous.attempt_count === 0 && previous.may_have_executed === false && !previous.result;
        const received = ["completed", "refused", "failed"].includes(previous.state) && previous.result?.verified === true && previous.result?.durable_ack === true && previous.result?.ack_delivery_pending === false;
        if (previous.reconciliation_required !== false || !unexecuted && !received) throw Error("Existing cloud work is unresolved. Recover that operation before preparing another read.");
      }
      const choices = catalogChoices(await this.client.catalog());
      const selected = choices.find(c => ownerCanonical(c) === ownerCanonical(selection));
      if (!selected) throw Error("Catalog selection changed. Select the read again.");
      const ref = { client_nonce: randomUUID() };
      await this.put(ref); // Must succeed before the first prepare request.
      return this.accept(ref, await this.client.prepare({ client_nonce: ref.client_nonce, ...selected }));
    });
  }
  async recover(reference: OperationReference): Promise<Json> {
    return this.exclusive(async () => {
      const ref = this.references().find(r => r.client_nonce === reference.client_nonce);
      if (!ref) throw Error("Select a retained operation reference.");
      return this.accept(ref, await this.client.status(ref));
    });
  }
  async decide(reviewed: Json, decision: "approve" | "deny"): Promise<Json> {
    return this.exclusive(async () => {
      const ref = this.references().find(r => r.client_nonce === reviewed.client_nonce && r.operation_id === reviewed.operation_id);
      if (!ref || ref.decision_sent) throw Error("This decision was already submitted or is unavailable. Recover the same operation; nothing was resent.");
      const current = await this.accept(ref, await this.client.status(ref));
      if (reviewText(current) !== reviewText(reviewed) || current.state !== "review_pending" || !current.allowed_actions?.includes(decision)) throw Error("The operation review changed or is no longer available. Recover and review it again.");
      await this.put({ ...ref, decision_sent: true });
      return this.accept({ ...ref, decision_sent: true }, await this.client.decision(current.operation_id, current.revision, current.review_digest, decision));
    });
  }
  async reconcile(reference: OperationReference): Promise<Json> {
    return this.exclusive(async () => {
      const ref = this.references().find(r => r.client_nonce === reference.client_nonce);
      if (!ref?.operation_id) throw Error("Recover the operation ID first.");
      const current = await this.accept(ref, await this.client.status(ref));
      if (!current.allowed_actions?.includes("reconcile")) throw Error("Reconciliation is unavailable for this operation.");
      return this.accept(ref, await this.client.reconcile(ref.operation_id));
    });
  }
}
