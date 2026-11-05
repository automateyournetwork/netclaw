export const escape = (value: string) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
const purposes: Record<string, string> = {
  overview: "Your network workbench. One connection, a clear place to begin.",
  estate: "Members, roles and risk posture reported by this federation.",
  peers: "External peers and their reported federation state.",
  mobile: "Enroll your phone with a QR code and view connected mobile devices.",
  science: "Configured advisors and their reported roles.",
  network: "Manage configured devices in your pyATS testbed.",
  testbed: "Build your inventory. Review every change before saving.",
  topology:
    "Explore reported BGP sessions. These links are not physical cabling.",
  operations: "Approvals and replication work, organized by outcome.",
  gait: "Reported federation audit activity and its source.",
  integrations: "Find an integration, configure its fields and review setup.",
  skills: "Explore the skills installed in this NetClaw.",
  settings: "Selected provider, model and MCP registrations.",
  configuration: "Connection details and credentials, grouped by integration.",
  mcp: "Configure this integration in the selected installation.",
  tokenomics: "Recorded model usage with explicit coverage and cost limits.",
  budget: "Review the configured limits for this installation.",
  security: "Review security posture, tool rules and enforcement settings.",
  openshell: "Review sandbox status, network policy and security logs.",
  knowledge: "Find your knowledge collections and open retrieval.",
  documentation: "Guides for the tools and workflows you use.",
  reference: "Browse CLI, API and MCP interfaces.",
  logs: "Read bounded installation logs and their collection scope.",
  intent: "Review the request, selected endpoints and change-control outcome.",
  peerChat: "A response from the selected federation peer.",
  chat: "Ask NetClaw. Keep the conversation and its context together.",
  avatar: "Your NetClaw companion, with the same conversation controls.",
  rag: "Search your knowledge, inspect citations and carry context forward.",
  canvas: "Give an investigation room to grow. Keep each branch in context.",
};
export const viewPurpose = (kind: string) =>
  purposes[kind] || "Explore the selected NetClaw installation.";
const actions: Record<string, string> = {
  chat: "netclaw.openChat",
  testbed: "netclaw.openNetwork",
  integrations: "netclaw.openIntegrations",
  knowledge: "netclaw.openRag",
  mcp: "netclaw.configureMcp",
  settings: "netclaw.configureSettings",
  documentation: "netclaw.openDocumentation",
};
export const actionCommand = (action: string) =>
  Object.hasOwn(actions, action) ? actions[action] : undefined;
export function pageHeader(
  kind: string,
  title: string,
  label: string,
  runtime: string,
) {
  return `<header class="page-header"><div class="page-heading"><p class="eyebrow"><span class="brand-dot" aria-hidden="true"></span> NETCLAW / WORKBENCH</p><h1>${escape(title)}</h1><p class="page-purpose">${escape(viewPurpose(kind))}</p></div><div id="binding" class="connection-badge"><span class="badge-label">SELECTED CONNECTION</span><strong>${escape(label || "Disconnected")}</strong><span>${escape(runtime || "No runtime")}</span></div></header>`;
}
