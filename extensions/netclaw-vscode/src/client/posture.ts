/** Node posture (spec 183 / R09A, contracts/node-posture.md): what a Border reports about its own confinement.
 *  Read-only. It is the node's self-report over the already verified HTTPS origin, never proof of enforcement. */
import { regionLabel } from "./cluster";

type Json = Record<string, any>;
export type PostureComponent = { name: string; inside_sandbox: boolean; state: string; disposition?: string };
export type NodePosture = {
  schema_version: 1; node: string; region: string;
  sandbox: { name: string; phase: string; policy_version: number; policy_sha256: string; landlock: string };
  components: PostureComponent[];
  guard: { mode: "observe" | "action"; state: string; fail_closed: boolean; last_block_ms: number | null };
  observed_at_ms: number;
};
export class PostureError extends Error {}

const MAX_BYTES = 16 * 1024;
const STATES = new Set(["running", "starting", "stopped", "failed", "unknown"]);
const PHASES = new Set(["Ready", "Provisioning", "Starting", "Stopped", "Error", "Unknown"]);
const SECRET_LOOKING = /sk-ant-|nbt_|gd_pat_|ghp_|AKIA[0-9A-Z]{16}|-----BEGIN|api[_-]?key|passw(or)?d|secret|bearer |private[_ -]?key/i;
const object = (v: unknown): v is Json => v !== null && typeof v === "object" && !Array.isArray(v);
const exact = (v: unknown, keys: string): v is Json => object(v) && Object.keys(v).sort().join() === keys.split(" ").sort().join();
const token = (v: unknown, max = 64): v is string => typeof v === "string" && v.length >= 1 && v.length <= max && /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(v);
const nonNegative = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number) >= 0;

/** Same rules as the ingress that serves it: exact keys, no secret-looking text, outside components carry a disposition and never claim enforcement. */
export function validatePosture(value: unknown): NodePosture {
  const bad = () => new PostureError("The Border returned a node posture that does not match the contract; it is ignored.");
  if (!exact(value, "schema_version node region sandbox components guard observed_at_ms") || value.schema_version !== 1) throw bad();
  if (!token(value.node, 32) || !token(value.region, 40)) throw bad();
  const s = value.sandbox;
  if (!exact(s, "name phase policy_version policy_sha256 landlock") || !token(s.name) || !PHASES.has(s.phase) || !Number.isSafeInteger(s.policy_version) || s.policy_version < 1 ||
    typeof s.policy_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(s.policy_sha256) || !["hard_requirement", "best_effort", "unavailable"].includes(s.landlock)) throw bad();
  if (!Array.isArray(value.components) || value.components.length < 1 || value.components.length > 32) throw bad();
  const names = new Set<string>();
  for (const c of value.components) {
    if (!object(c) || typeof c.inside_sandbox !== "boolean") throw bad();
    if (!exact(c, c.inside_sandbox ? "name inside_sandbox state" : "name inside_sandbox disposition state") || !token(c.name) || !STATES.has(c.state) || names.has(c.name)) throw bad();
    names.add(c.name);
    if (!c.inside_sandbox && !(typeof c.disposition === "string" && c.disposition.length >= 1 && c.disposition.length <= 200 && /^[\x20-\x7e]+$/.test(c.disposition) && !/enforc/i.test(c.disposition))) throw bad();
  }
  const g = value.guard;
  if (!exact(g, "mode state fail_closed last_block_ms") || !["observe", "action"].includes(g.mode) || !STATES.has(g.state) || typeof g.fail_closed !== "boolean" ||
    !(g.last_block_ms === null || nonNegative(g.last_block_ms))) throw bad();
  if (!nonNegative(value.observed_at_ms)) throw bad();
  const walk = (item: unknown) => {
    if (typeof item === "string") { if (SECRET_LOOKING.test(item)) throw bad(); }
    else if (object(item)) for (const [k, v] of Object.entries(item)) { if (SECRET_LOOKING.test(k)) throw bad(); walk(v); }
    else if (Array.isArray(item)) item.forEach(walk);
  };
  walk(value);
  return value as unknown as NodePosture;
}

/** GET <origin>/api/hud/posture with the same fetch hygiene as the owner client: no redirects, no cache, no cookies, bounded size, JSON only. */
export async function fetchNodePosture(origin: string, fetchImpl: typeof fetch = fetch, timeoutMs = 15000): Promise<NodePosture> {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    let response: Response;
    try {
      response = await fetchImpl(origin + "/api/hud/posture", { method: "GET", headers: { Accept: "application/json" }, redirect: "error", cache: "no-store", signal: controller.signal });
    } catch { throw new PostureError("Could not reach the Border to read its node posture. Check the connection."); }
    if (response.status === 404) throw new PostureError("This Border does not publish a node posture (it may predate R09A or has none configured). Nothing is implied about its confinement.");
    if (!response.ok) throw new PostureError("The Border could not provide a valid node posture right now. Nothing is implied about its confinement.");
    if (!response.headers.get("content-type")?.includes("application/json") || response.headers.getSetCookie().length) throw new PostureError("The Border returned an unexpected node posture response; it is ignored.");
    const reader = response.body?.getReader();
    if (!reader) throw new PostureError("The Border returned an empty node posture response.");
    const chunks: Uint8Array[] = []; let bytes = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.length;
      if (bytes > MAX_BYTES) { await reader.cancel(); throw new PostureError("The node posture response is larger than allowed; it is ignored."); }
      chunks.push(value);
    }
    let parsed: unknown;
    try { parsed = JSON.parse(Buffer.concat(chunks).toString("utf8")); } catch { throw new PostureError("The Border returned a node posture that is not valid JSON; it is ignored."); }
    return validatePosture(parsed);
  } finally { clearTimeout(timer); }
}

/** Readable summary. Components outside the sandbox are shown with their disposition; nothing here says "enforced". */
export function formatPosture(p: NodePosture, origin: string): string {
  const inside = p.components.filter(c => c.inside_sandbox), outside = p.components.filter(c => !c.inside_sandbox);
  const line = (c: PostureComponent) => `  - ${c.name} (${c.state})${c.disposition ? " — " + c.disposition : ""}`;
  const region = regionLabel(origin);
  return [
    `Node posture — ${p.node}${region && region !== "Unknown region" ? " · " + region : ""} (${p.region})`,
    `Origin: ${origin}`,
    `Observed: ${new Date(p.observed_at_ms).toISOString()} (an observation reported by the node, not authority)`,
    "",
    `Sandbox: ${p.sandbox.name} · phase ${p.sandbox.phase} · policy v${p.sandbox.policy_version} · sha256 ${p.sandbox.policy_sha256} · Landlock ${p.sandbox.landlock}`,
    "",
    `Inside the sandbox (${inside.length}):`, ...(inside.length ? inside.map(line) : ["  - none reported"]),
    "",
    `Outside the sandbox (${outside.length}):`, ...(outside.length ? outside.map(line) : ["  - none reported"]),
    "",
    `Guard: mode ${p.guard.mode} · ${p.guard.state} · fail-closed ${p.guard.fail_closed ? "yes" : "no"} · last block ${p.guard.last_block_ms === null ? "none recorded" : new Date(p.guard.last_block_ms).toISOString()}`,
    "",
    "This is what the node reported about itself. Components outside the sandbox are not covered by OpenShell confinement; this view is not proof that any control is enforced.",
    "",
  ].join("\n");
}
