import { execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs";
import path from "node:path";
export function nativeExecutable(name, env = process.env) {
  for (const dir of (env.PATH || "").split(path.delimiter)) {
    if (!path.isAbsolute(dir)) continue;
    const p = path.join(dir, name);
    try {
      fs.accessSync(p, fs.constants.X_OK);
      return fs.realpathSync(p);
    } catch {}
  }
  throw Error(`The ${name} executable is unavailable on this HUD host.`);
}

// `openclaw agents list --json` takes 10 s or more of CPU on slower hosts, and
// GET /api/hud/management needs it on every call. Keep the parsed list for
// this HUD process until the CLI, its environment or the OpenClaw config file
// changes, with a maximum age as a backstop for changes the key can't see.
// Concurrent callers share one run; failures are never kept.
export const AGENT_CATALOG_MAX_AGE_MS = 10 * 60 * 1000;
let agentCatalog;

function fileSignature(file) {
  try {
    const s = fs.statSync(file);
    return [s.ino, s.size, s.mtimeMs, s.ctimeMs];
  } catch {
    return "missing";
  }
}

function agentCatalogKey(cli, env) {
  return JSON.stringify([
    cli,
    fileSignature(cli),
    process.cwd(),
    env.HOME,
    env.OPENCLAW_HOME,
    env.OPENCLAW_STATE_DIR,
    env.OPENCLAW_PROFILE,
    env.OPENCLAW_CONFIG_PATH,
    env.OPENCLAW_CONFIG_PATH ? fileSignature(env.OPENCLAW_CONFIG_PATH) : null,
  ]);
}

async function listAgents(cli, env) {
  const { stdout } = await promisify(execFile)(
    cli,
    ["agents", "list", "--json"],
    { env, cwd: process.cwd(), timeout: 15000, maxBuffer: 2 * 1048576 },
  );
  const agents = JSON.parse(stdout);
  if (!Array.isArray(agents))
    throw Error("Native agent catalog is unavailable.");
  return agents;
}

export function openclawAgents(
  cli,
  env = process.env,
  { run = listAgents, now = Date.now } = {},
) {
  const key = agentCatalogKey(cli, env);
  const entry = agentCatalog;
  if (entry?.key === key) {
    if (entry.pending) return entry.pending;
    if (now() - entry.at < AGENT_CATALOG_MAX_AGE_MS)
      return Promise.resolve(entry.value);
  }
  const pending = Promise.resolve()
    .then(() => run(cli, env))
    .then(
      (agents) => {
        // Keep only the binding fields (spec 152 research: project the native
        // output immediately), frozen because callers share one array.
        const value = Object.freeze(
          agents.map(({ id, isDefault, workspace }) =>
            Object.freeze({ id, isDefault, workspace }),
          ),
        );
        if (agentCatalog?.pending === pending)
          agentCatalog = { key, at: now(), value };
        return value;
      },
      (error) => {
        if (agentCatalog?.pending === pending) agentCatalog = undefined;
        throw error;
      },
    );
  agentCatalog = { key, pending };
  return pending;
}

export function clearAgentCatalog() {
  agentCatalog = undefined;
}
export async function managementDiscovery(
  installation,
  root,
  agentId,
  env = process.env,
) {
  let cli, expectedWorkspace;
  if (installation.kind === "openclaw") {
    cli = nativeExecutable("openclaw", env);
    const agents = await openclawAgents(cli, env);
    agentId =
      agentId ||
      agents.find((a) => a.isDefault)?.id ||
      (agents.length === 1 ? agents[0].id : undefined);
    const matches = agents.filter((a) => a.id === agentId);
    if (matches.length !== 1 || typeof matches[0].workspace !== "string")
      throw Error("Selected native agent is ambiguous.");
    expectedWorkspace = fs.realpathSync(matches[0].workspace);
  }
  return {
    schemaVersion: 1,
    kind: installation.kind,
    installationId: installation.installationId,
    home: installation.home,
    configPath: installation.configPath,
    agentId: installation.kind === "openclaw" ? agentId : "main",
    root: fs.realpathSync(root),
    node: fs.realpathSync(process.execPath),
    cli,
    expectedWorkspace,
    launch: {
      cwd: fs.realpathSync(process.cwd()),
      home: fs.realpathSync(env.HOME),
      ...(installation.kind === "openclaw"
        ? { openclawHome: env.OPENCLAW_HOME, profile: env.OPENCLAW_PROFILE }
        : {}),
    },
  };
}
