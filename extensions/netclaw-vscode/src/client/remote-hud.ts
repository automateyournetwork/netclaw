import type { Runtime } from "./hud";
import { labAccess } from "./owner";

export const remoteHudFeatureNames = ["overview", "chat", "canvas", "rag", "members", "peers", "skills", "runtime", "tokenomics", "documentation", "reference", "logs", "operations"] as const;
export type RemoteHudFeature = typeof remoteHudFeatureNames[number];
/** Server-advertised panel support is separate from the protected-operation API. */
export function remoteHudFeatures(runtime?: Runtime): Set<RemoteHudFeature> {
  const capability = runtime?.capabilities?.remoteHud;
  if (!runtime || runtime.kind !== "openclaw" || runtime.role !== "border" ||
      capability?.schema !== 1 || !Array.isArray(capability.features) || capability.features.length > 32 ||
      !capability.features.includes("overview") || capability.features.some((f: unknown) => typeof f !== "string"))
    throw Error("This Border does not advertise a compatible remote NetClaw workspace.");
  if (capability.features.includes("canvas") && !capability.features.includes("chat")) throw Error("The remote Canvas feature requires Chat support.");
  labAccess(runtime.access);
  return new Set(capability.features.filter((f: string) => (remoteHudFeatureNames as readonly string[]).includes(f)));
}
const routes: [RemoteHudFeature, string, RegExp][] = [
  ["members", "GET", /^\/api\/n2n$/],
  ["peers", "GET", /^\/api\/n2n$/],
  ["operations", "GET", /^\/api\/n2n$/],
  ["skills", "GET", /^\/api\/graph$/],
  ["chat", "GET", /^\/api\/chat\/(models|conversations)$/],
  ["chat", "POST", /^\/api\/chat$/],
  ["chat", "POST", /^\/api\/chat\/conversations\/(?:[A-Za-z0-9_.:-]|%3A){1,128}\/open$/],
  ["rag", "GET", /^\/api\/rag\/(stats|documents)$/],
  ["rag", "POST", /^\/api\/rag\/(search|upload)$/],
  ["runtime", "GET", /^\/api\/hud\/runtime$/],
  ["tokenomics", "GET", /^\/api\/hud\/tokenomics$/],
  ["documentation", "GET", /^\/api\/hud\/documentation(\/(?:[A-Za-z0-9_.:-]|%3A){1,128})?$/],
  ["reference", "GET", /^\/api\/hud\/reference$/],
  ["logs", "GET", /^\/api\/hud\/logs(\/(?:[A-Za-z0-9_.:-]|%3A){1,128})?$/],
];
export function remoteHudRoute(runtime: Runtime | undefined, method: string, route: string) {
  if (method === "GET" && route === "/api/runtime") return;
  const features = remoteHudFeatures(runtime), pathname = route.split("?")[0]!;
  if (pathname.includes("..")) throw Error("Invalid remote HUD item path.");
  if (route.includes("?")) {
    const query = new URLSearchParams(route.slice(route.indexOf("?") + 1));
    if (method !== "GET" || !/^\/api\/hud\/logs\/(?:[A-Za-z0-9_.:-]|%3A){1,128}$/.test(pathname) ||
        [...query.keys()].some(k => !["q", "severity"].includes(k) || query.getAll(k).length !== 1) ||
        (query.get("q") || "").length > 200 || query.has("severity") && !["all", "error", "warning", "info", "debug", "unknown"].includes(query.get("severity")!))
      throw Error("This remote HUD query is unavailable.");
  }
  if (!routes.some(([feature, verb, path]) => features.has(feature) && method === verb && path.test(pathname)))
    throw Error("This cloud Border does not expose that action through its remote workspace.");
}
export const remoteDomainFeature: Record<string, RemoteHudFeature> = {
  overview: "overview", estate: "members", peers: "peers", mobile: "members", science: "members", operations: "operations", gait: "operations",
  integrations: "skills", skills: "skills", settings: "runtime", tokenomics: "tokenomics", knowledge: "rag", documentation: "documentation", reference: "reference", logs: "logs",
};
export const remoteCommandFeature: Record<string, RemoteHudFeature> = {
  openChat: "chat", openAvatar: "chat", openCanvas: "canvas", addSelectedContext: "chat", searchMemory: "chat", analyzeContext: "chat", openMeetings: "chat",
  openRag: "rag", exportGait: "operations", exportDiagnostics: "overview", openLogs: "logs", openDocumentation: "documentation",
  openOverview: "overview", openOperations: "operations", openSettings: "runtime", openTokenomics: "tokenomics", openGait: "operations", openIntegrations: "skills", openSkills: "skills", openPeers: "peers", openScience: "members", openMobile: "members",
};
