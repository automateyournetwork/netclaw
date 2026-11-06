(() => {
  "use strict";
  const definitions = {
    overview: [
      "Your connected workspace",
      "Start a conversation, shape your inventory or prepare an integration.",
      [],
      ["kind", "readiness", "installationId"],
    ],
    estate: [
      "Federation members",
      "Membership and roles reported by Risk / iN2N.",
      [["Members", "members"]],
      ["available", "risk.mode", "identity.name"],
    ],
    peers: [
      "External peers",
      "Reported federation relationships; an advertisement is not a device health check.",
      [["Peers", "peers"]],
      ["available", "posture"],
    ],
    mobile: [
      "At the edge",
      "Edge-node observations and push outcomes are shown separately.",
      [
        ["Edge nodes", "edgeNodes"],
        ["Recent pushes", "recentPushes"],
      ],
      ["available"],
    ],
    science: [
      "Your advisors",
      "Configured roles, models and limits reported by the federation.",
      [["Advisors", "advisors"]],
      ["available"],
    ],
    network: [
      "Testbed inventory",
      "Configured devices, not observed network reachability.",
      [["Devices", "devices"]],
      [],
    ],
    topology: [
      "BGP sessions",
      "Reported local-to-peer sessions · not physical cabling.",
      [
        ["Peer sessions", "peers"],
        ["Routing information", "rib"],
      ],
      ["local.as", "local.routerId", "ribCount"],
    ],
    operations: [
      "Federation work",
      "Review approvals and replication outcomes without changing their authority.",
      [
        ["Approvals", "approvals"],
        ["Replication jobs", "replicationJobs"],
      ],
      ["available"],
    ],
    gait: [
      "Audit activity",
      "Federation-reported audit evidence; this may not be the complete local trail.",
      [["Audit events", "gait"]],
      ["available"],
    ],
    integrations: [
      "Build your toolset",
      "Installed skills indicate available guidance. They do not prove a running endpoint.",
      [["Integrations", "integrations"]],
      [],
    ],
    skills: [
      "Installed skills",
      "Find a workflow and inspect the guidance bundled with this installation.",
      [["Skills", "skills"]],
      [],
    ],
    settings: [
      "Provider & runtime",
      "Configuration describes intended behavior; execution can differ.",
      [
        ["Registered MCPs", "mcp_servers"],
        ["Runtime settings", "settings"],
      ],
      ["llm.primary_model", "runtime", "source"],
    ],
    configuration: [
      "Configure in context",
      "Each integration keeps its connection and credential fields together.",
      [["Integrations", "integrations"]],
      ["environmentFile"],
    ],
    tokenomics: [
      "Recorded usage",
      "Input, output and cache usage remain separate. Recorded cost is not an invoice.",
      [["Models & providers", "groups"]],
      ["records", "missingUsage", "malformed", "skippedFiles", "scope"],
    ],
    budget: [
      "Budget limits",
      "Review configured spending limits before changing them.",
      [],
      [
        "budget.sessionBudgetUsd",
        "budget.maxToolCallsPerTurn",
        "budget.contextWarningTokens",
        "budget.allowOverride",
        "budget.overrideIncrementUsd",
      ],
    ],
    security: [
      "Policy & controls",
      "Configured modes do not establish running enforcement.",
      [],
      [
        "labMode",
        "labExplicit",
        "riskMode",
        "strictAll",
        "defenseMode",
        "guardMode",
        "guardPort",
        "source",
      ],
    ],
    openshell: [
      "Sandbox probes",
      "Bounded local command observations, with explicit availability.",
      [["Probes", "commands"]],
      ["available", "source"],
    ],
    knowledge: [
      "Knowledge collections",
      "Explore recorded collections, then search with citations.",
      [["Collections", "collections"]],
      ["totalDocuments", "totalChunks", "available"],
    ],
    documentation: [
      "Your guide library",
      "Find practical setup and workflow documentation.",
      [["Guides", "documents"]],
      [],
    ],
    reference: [
      "Interface reference",
      "Declared interfaces, not a claim of current tool availability.",
      [
        ["CLI commands", "cli"],
        ["HTTP API", "api"],
        ["MCP tools", "mcp"],
      ],
      [],
    ],
    logs: [
      "Installation logs",
      "Latest bounded source observations; read the scope before interpreting gaps.",
      [
        ["Log sources", "sources"],
        ["Log entries", "rows"],
      ],
      ["source", "readAt", "truncated", "scope"],
    ],
    intent: [
      "Terminal intent",
      "Endpoints and execution outcomes retain their existing change-control rules.",
      [
        ["Endpoints", "devices"],
        ["Steps", "steps"],
        ["Targets", "targets"],
      ],
      ["status", "mode", "requestId", "summary"],
    ],
    peerChat: [
      "Peer response",
      "The selected peer’s reply and reported outcome.",
      [],
      ["source", "trust", "text", "request_id", "session_id", "peer", "status", "response", "message", "elapsedMs"],
    ],
  };
  const label = (key) =>
    ({
      isSet: "Configured",
      active: "Related skills installed",
      os: "Operating system",
      id: "ID",
      ip: "Address",
      kind: "Runtime",
      input: "Input tokens",
      output: "Output tokens",
      cacheRead: "Cache read tokens",
      cacheWrite: "Cache write tokens",
      costUsd: "Recorded cost (USD)",
      local: "Local speaker",
      readiness: "Reported readiness",
      installationId: "Installation ID",
      as: "AS number",
      asn: "AS number",
    })[key] ||
    key
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/[_-]/g, " ")
      .replace(/^./, (c) => c.toUpperCase());
  const get = (value, key) => key.split(".").reduce((v, k) => v?.[k], value);
  const value = (v) =>
    v === undefined || v === null
      ? "Not reported"
      : typeof v === "object"
        ? Array.isArray(v)
          ? `${v.length} entries`
          : Object.entries(v)
              .filter(([, x]) => x === null || typeof x !== "object")
              .slice(0, 6)
              .map(
                ([k, x]) => `${label(k)}: ${x === null ? "Not reported" : x}`,
              )
              .join(" · ") || "See source details"
        : String(v);
  const fields = [
    "identity",
    "channel_state",
    "chat_enabled",
    "inventory_version",
    "stale",
    "alias",
    "description",
    "summary",
    "role",
    "state",
    "status",
    "category",
    "os",
    "platform",
    "type",
    "host",
    "ip",
    "address",
    "port",
    "protocol",
    "asn",
    "as",
    "uptime",
    "prefixesReceived",
    "model",
    "provider",
    "enabled",
    "active",
    "skillCount",
    "tools",
    "toolEstimate",
    "isSet",
    "requirement",
    "calls",
    "input",
    "output",
    "cacheRead",
    "cacheWrite",
    "costUsd",
    "costRecords",
    "incompleteTokenRecords",
    "timestamp",
    "time",
    "lastSeen",
    "outcome",
    "severity",
    "message",
    "command",
    "available",
    "output",
    "path",
    "notes",
    "transport",
    "value",
  ];
  const names = [
    "name",
    "display_name",
    "title",
    "label",
    "hostname",
    "id",
    "identity",
    "peer",
    "neighbor",
    "model",
    "key",
    "command",
    "timestamp",
    "path",
    "method",
  ];
  function card(item, index, kind, group) {
    const object = item && typeof item === "object" ? item : { value: item };
    const title = value(
      names
        .map((k) => object[k])
        .find((v) => typeof v === "string" || typeof v === "number") ??
        `${group} ${index + 1}`,
    );
    let facts = fields
      .filter((k) => Object.hasOwn(object, k))
      .map((k) => ({
        label: label(k),
        value:
          ["notes", "description", "summary"].includes(k) &&
          typeof object[k] === "string" &&
          object[k].length > 260
            ? object[k].slice(0, 260) + "…"
            : value(object[k]),
      }));
    if (kind === "configuration" && Array.isArray(object.fields))
      facts = [
        {
          label: "Configured fields",
          value: `${object.fields.filter((f) => f.isSet).length} of ${object.fields.length}`,
        },
        ...facts,
      ];
    const actions =
      ["integrations", "configuration"].includes(kind) &&
      typeof object.id === "string"
        ? [{ id: "mcp", target: object.id, label: "Configure & set up" }]
        : [];
    return { title, facts, actions, source: item };
  }
  function present(kind, observation) {
    const def = definitions[kind] || [
      "Source observation",
      "This response shape has no specialized presenter.",
      [],
      [],
    ];
    const data = observation?.data ?? observation ?? {};
    const notices = [
      observation?.note,
      data.scope,
      data.reason,
      data.error,
    ].filter((v) => typeof v === "string");
    if (data.available === false)
      notices.unshift(
        "This source is unavailable. No healthy or empty state is implied.",
      );
    const sections = [];
    let groups = def[2];
    if (kind === "openshell" && Array.isArray(data)) groups = [["Probes", ""]];
    if (kind === "intent" && Array.isArray(data)) groups = [["Endpoints", ""]];
    for (const [title, key] of groups) {
      let rows = key ? get(data, key) : data;
      if (rows && !Array.isArray(rows) && typeof rows === "object")
        rows = Object.entries(rows).map(([id, v]) =>
          typeof v === "object" ? { id, ...v } : { id, value: v },
        );
      sections.push({
        title,
        known: Array.isArray(rows),
        cards: Array.isArray(rows)
          ? rows.map((r, i) => card(r, i, kind, title))
          : [],
      });
    }
    const facts = def[3].map((k) => ({
      label: label(k.split(".").at(-1)),
      value: value(get(data, k)),
    }));
    if (facts.length || !sections.length)
      sections.unshift({
        title: def[0],
        known: true,
        cards: [
          {
            title: kind === "overview" ? "Selected runtime" : def[0],
            facts,
            source: data,
            actions: [],
          },
        ],
      });
    const actions =
      kind === "overview"
        ? [
            { id: "chat", label: "Open Chat" },
            { id: "testbed", label: "Manage testbed" },
            { id: "integrations", label: "MCP integrations" },
          ]
        : kind === "knowledge"
          ? [{ id: "knowledge", label: "Search knowledge" }]
          : kind === "network"
            ? [{ id: "testbed", label: "Manage testbed" }]
            : [];
    return {
      title: def[0],
      description: def[1],
      sections,
      notices,
      actions,
      provenance: {
        source: observation?.source || data.source || "Selected installation",
        observedAt: observation?.observedAt || data.generatedAt || data.readAt,
      },
      source: data,
    };
  }
  window.netclawPresenters = { definitions, present, label, value };
})();
