import { createHash } from "node:crypto";
import type { Json } from "./hud";
export type ClusterBinding = { descriptor: Json; pin: Json };
// Dynamic import is bundled into the native extension; the same verifier runs in HUD.
export async function verifyClusterRuntime(runtime: Json, options: Json): Promise<ClusterBinding> {
  return (await import("../../../../ui/netclaw-visual/src/shared/cluster-binding.js")).verifyClusterRuntime(runtime, options);
}
export const clusterReferencesKey = (c: Json, p: Json) => "owner-cluster-operations." + createHash("sha256").update([c.cluster_id, c.generation, p.issuer, p.subject].join("|")).digest("hex");
export const clusterCanAdmit = (c?: Json) => !c || ["leader", "follower"].includes(c.authority?.state) && Number.isSafeInteger(c.authority?.epoch) && c.authority.epoch > 0;
export function clusterReviewMatches(c: Json, review: Json) {
  const r = review?.cluster, node = c.manifest.manifest.nodes.find((n: Json) => n.node_id === r?.issuer_node_id);
  return Boolean(r && Object.keys(r).sort().join(",") === "authority_epoch,cluster_id,generation,issuer_node_id,manifest_revision" && r.cluster_id === c.cluster_id && r.generation === c.generation && Number.isSafeInteger(r.manifest_revision) && r.manifest_revision > 0 && r.manifest_revision <= c.manifest_revision && Number.isSafeInteger(r.authority_epoch) && r.authority_epoch > 0 && node && node.installation_id === review.border?.installation_id && node.key_id === review.border?.key_id);
}
export const clusterCanDecide = (c: Json | undefined, op: Json) => !c || clusterCanAdmit(c) && clusterReviewMatches(c, op.review) && op.review.cluster.authority_epoch === c.authority.epoch;
export function clusterStatus(c?: Json) {
  if (!c) return undefined;
  return ({leader:"This Border holds execution authority.",follower:"This Border forwards protected requests to the current authority.",no_quorum:"Quorum is unavailable. New protected work is stopped; recover retained work.",fenced:"Cluster fenced. New protected work is stopped.",retired:"Border retired. Select a trusted active cluster endpoint."} as Record<string,string>)[c.authority?.state] || "Authority is unavailable.";
}
export const clusterError = (code: string): string | undefined => ({no_quorum:"Quorum is unavailable. Recover the same operation after authority returns.",quorum_unavailable:"Quorum is unavailable. Recover the same operation after authority returns.",stale_authority:"Authority changed. Recover the same operation; nothing was resent.",stale_review:"This review belongs to an earlier authority. Recover the same operation; nothing was resent.",node_retired:"This Border is retired. Select a trusted cluster endpoint.",cluster_changed:"Cluster identity or generation changed. Original references remain retained.",stale_manifest:"This endpoint advertised an older manifest. The saved binding remains unchanged."} as Record<string,string>)[code];
// Spec 182 region display. Display-only: never selects, trusts or pins an endpoint (contracts/region-display.md).
const REGION_LABELS: Record<string, string> = { nne1: "Montreal", ew1: "Belgium", ase1: "Singapore" };
export function regionLabel(endpointOrHost: unknown): string {
  let host = String(endpointOrHost ?? "");
  try { host = new URL(host).hostname; } catch { /* bare host */ }
  const m = /^(nne1|ew1|ase1)-[0-9a-f]{6}\.automateyournetwork\.com$/.exec(host);
  return m ? (REGION_LABELS[m[1] as string] ?? "Unknown region") : "Unknown region";
}
export function clusterNodeRegion(c: Json | undefined, nodeId: string): string {
  const node = c?.manifest?.manifest?.nodes?.find((n: Json) => n.node_id === nodeId);
  return node ? regionLabel(node.endpoints?.https) : "Unknown region";
}
export function clusterFailoverNotice(c?: Json): string | undefined {
  const a = c?.authority;
  if (!a) return undefined;
  if (["leader", "follower"].includes(a.state) && a.leader_node_id && a.leader_node_id !== c?.node_id) return `Forwarding to the ${clusterNodeRegion(c, a.leader_node_id)} authority.`;
  if (a.state === "no_quorum") return "No quorum: new protected work is stopped. Select another enrolled endpoint explicitly.";
  return undefined;
}
