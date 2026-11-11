import { openMobile } from './views/mobile';
import { Management } from "./state/management";
import {
  WorkspaceFiles,
  openWorkspace,
  workspaceFiles,
} from "./views/workspace";
import { openSecurity } from "./views/security";
import * as vscode from "vscode";
import path from "node:path";
import fs from "node:fs";
import { randomUUID } from "node:crypto";
import { Connection, selectConnectionProfile } from "./connection/connect";
import { Profiles, ConnectionProfile, hostContext } from "./state/profiles";
import { LocalState } from "./state/local";
import { NavigationTree, Navigation } from "./views/overview";
import { domains, Domain, inspect } from "./client/domains";
import { Json } from "./client/hud";
import { openDataView } from "./webview/bridge";
import { openChat } from "./views/chat";
import { openMcp } from "./views/mcp";
import { openTestbed } from "./views/testbed";
import { openRag } from "./views/rag";
import { openCanvas } from "./views/canvas";
import { openIntent, peerChat } from "./views/intent";
import { prepareService } from "./views/services";
import { configureSettings, environment } from "./views/settings";
import { AssistantProvider } from "./assistants/provider";
import { SetupWizard } from "./views/setup-wizard";
import {SetupAssistant} from './setup/assistant-session';
import {distributeSetupSkill} from './setup/skills';
import {createPreset} from './setup/preset';
import {inspectSetupConnection,SetupConnection} from './setup/connections';
import { OwnerWorkflow, assertCloudCommand } from './views/owner';
import { cloudInputOrigin, discoverCloudBorder, cloudExecutionMode, ownerCanonical } from './client/owner';
import { fetchNodePosture, formatPosture } from './client/posture';
import { remoteHudFeatures, remoteDomainFeature, remoteCommandFeature } from "./client/remote-hud";

export async function activate(context: vscode.ExtensionContext) {
  const local = new LocalState(
      path.join(context.globalStorageUri.fsPath, "state"),
    ),
    profiles = new Profiles(local),
    connection = new Connection(context.secrets, (p, c) => profiles.updateCluster(p, c)),
    assistants = new AssistantProvider(context, connection);
  const management = new Management(local, () => connection.profile?.mode === "remote-border");
  const ownerWorkflow = new OwnerWorkflow(connection, local);
  context.subscriptions.push(ownerWorkflow);
  const setupWizard = new SetupWizard(context, local);
  const setupAssistant=new SetupAssistant(context,setupWizard);
  context.subscriptions.push(setupWizard,setupAssistant,vscode.lm.registerMcpServerDefinitionProvider('netclaw.setupAssistant',setupAssistant));
  const workspace = new WorkspaceFiles(context, management, connection);
  context.subscriptions.push(management, workspace);
  const output = vscode.window.createOutputChannel("NetClaw"),
    status = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      40,
    );
  status.command = "netclaw.selectConnection";
  const trees: NavigationTree[] = [];
  context.subscriptions.push(
    connection,
    assistants,
    output,
    status,
    vscode.lm.registerMcpServerDefinitionProvider(
      "netclaw.assistant",
      assistants,
    ),
  );
  const refresh = () => {
    void vscode.commands.executeCommand("setContext", "netclaw.cloudOpenLab", connection.owner?.openLab === true);
    for (const t of trees) t.refresh();
    status.text = connection.identity
      ? `$(remote) ${connection.profile?.label} · ${connection.owner ? (connection.owner.openLab ? "Connected" : connection.owner.sessionState ? "Border owner" : "Border · sign in") : connection.identity.kind}`
      : "$(remote) NetClaw: disconnected";
    status.tooltip = connection.identity
      ? `${hostContext()}\n${connection.identity.installationId}`
      : "Connect to existing NetClaw";
    status.show();
  };
  context.subscriptions.push(
    connection.changed.event(refresh),
    management.changed.event(refresh),
  );
  const register = (name: string, fn: (...args: any[]) => unknown) =>
    context.subscriptions.push(
      vscode.commands.registerCommand(
        "netclaw." + name,
        async (...args: any[]) => {
          try {
            assertCloudCommand(name, connection.profile?.mode === "remote-border", args, connection.identity);
            return await fn(...args);
          } catch (error) {
            void vscode.window.showErrorMessage(
              error instanceof Error ? error.message : "NetClaw action failed.",
            );
          }
        },
      ),
    );
  const connect = async (profile: ConnectionProfile) => {
    await management.select(profile);
    const identity = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Connecting to " + profile.label,
      },
      () => connection.connect(profile),
    );
    if (!profile.installationId) {
      if (
        (await vscode.window.showInformationMessage(
          `Bind ${profile.label} to this existing NetClaw?`,
          {
            modal: true,
            detail: `${hostContext()}\n${profile.url}\n${identity.kind}\n${identity.installationId}`,
          },
          "Bind installation",
        )) !== "Bind installation"
      ) {
        connection.disconnect();
        return;
      }
      const saved = await profiles.save({
        ...profile,
        installationId: identity.installationId,
        harness: identity.kind,
      });
      await connection.connect(saved);
    }
    if (connection.owner?.openLab) {
      connection.profile = await profiles.save({ ...(connection.profile || profile), access: "open-lab", cloudExecution: cloudExecutionMode(identity), cloudPrincipal: connection.owner.principal });
    }
    refresh();
  };
  register("setupClaw", () => setupWizard.open());
  register("ownerSignIn", () => ownerWorkflow.signIn());
  register("ownerSignOut", () => ownerWorkflow.signOut());
  register("ownerPrepare", () => ownerWorkflow.prepare());
  register("ownerRecover", () => ownerWorkflow.recover());
  // Read-only node posture (spec 185 / R09A). Registered directly: it is a read of the already verified cloud origin and is
  // deliberately not part of the cloud command allow-list in views/owner.ts. It never implies enforcement.
  context.subscriptions.push(vscode.commands.registerCommand("netclaw.showNodePosture", async () => {
    try {
      if (connection.profile?.mode !== "remote-border") throw Error("Select a cloud Border connection first; node posture is published by cloud Borders.");
      const origin = cloudInputOrigin(connection.profile.url);
      const posture = await fetchNodePosture(origin);
      await vscode.window.showTextDocument(await vscode.workspace.openTextDocument({ language: "markdown", content: formatPosture(posture, origin) }), { preview: true });
    } catch (error) {
      void vscode.window.showErrorMessage(error instanceof Error ? error.message : "Node posture is unavailable.");
    }
  }));
  register('setupAssistant',()=>setupAssistant.enable());
  register('setupSkill',()=>distributeSetupSkill(context));
  register('setupSpec',()=>createPreset(context,local,setupWizard.snapshot().answers));
  register('setupSpecReport',()=>setupWizard.writeDeploymentReport());
  register('setupConnect',async()=>{
    if(!vscode.workspace.isTrusted)throw Error('Trust this workspace first.');
    const candidates:SetupConnection[]=await setupWizard.connectionCandidates();
    if(!candidates.length)throw Error('No claw has verified runtime/HUD readiness. Run local verification first.');
    const selected=await vscode.window.showQuickPick(candidates.map(c=>({label:c.label,description:c.harness+' · '+c.home,c})),{title:'Save a new claw connection'});if(!selected)return;
    const candidate=await inspectSetupConnection(selected.c);
    if((await vscode.window.showInformationMessage('Save this verified claw in Connections?',{modal:true,detail:`${candidate.label}\n${candidate.harness}\n${candidate.home}\n${candidate.url}\n${candidate.installationId}`},'Save connection'))!=='Save connection')return;
    await inspectSetupConnection(candidate);
    const existing=profiles.list().find(p=>p.installationId===candidate.installationId&&p.url===candidate.url);
    const profile=existing||await profiles.save({label:candidate.label,url:candidate.url,harness:candidate.harness,installationId:candidate.installationId});
    await connect(profile);await vscode.commands.executeCommand('netclaw.openOverview');
  });
  register("workspaceControls", async () => {
    if (!management.selected) await management.bind(connection);
    if (management.selected)
      return openWorkspace(context, management, workspace);
  });
  register("bindWorkspace", () => management.bind(connection));
  register("openWorkspaceFile", (name: string) => workspace.open(name));
  register("uploadWorkspaceFile", (name?: string) => workspace.upload(name));
  register("saveRestartClaw", () => workspace.saveAndRestart());
  register("startClaw", () => workspace.lifecycle("start"));
  register("stopClaw", () => workspace.lifecycle("stop"));
  register("restartClaw", () => workspace.lifecycle("restart"));
  register("addConnection", async () => {
    if (!vscode.workspace.isTrusted)
      throw Error("Trust this workspace before connecting.");
    const mode = await vscode.window.showQuickPick([
      { label: "Local installation", description: "HUD on this extension host", mode: "local" as const },
      { label: "Cloud Border", description: "HTTPS Border", mode: "remote-border" as const },
    ], { title: "Connection type" });
    if (!mode) return;
    if (process.platform === "win32" && mode.mode === "local") {
      void vscode.window.showInformationMessage(
        "Open this workspace in WSL before connecting to an existing NetClaw installation.",
      );
      await vscode.commands.executeCommand(
        "workbench.action.quickOpen",
        ">WSL:",
      );
      return;
    }
    const label = await vscode.window.showInputBox({
      title: "Name this connection",
      prompt:
        "Choose a friendly name so you can recognize this NetClaw later. This is not a hostname or URL.",
      placeHolder: "My Mac lab or WSL NetClaw",
      validateInput: (value) =>
        value.trim() ? undefined : "Enter a friendly name for this connection.",
    });
    if (!label) return;
    if (mode.mode === "remote-border") {
      const input = await vscode.window.showInputBox({ title: "Cloud Border URL", placeHolder: "https://border.example.com", validateInput: value => { try { cloudInputOrigin(value); return undefined; } catch { return "Enter an HTTPS Border URL without credentials, a path, query or fragment."; } } });
      if (!input) return;
      const url = cloudInputOrigin(input);
      const runtime = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: "Connecting to " + label }, () => discoverCloudBorder(url));
      let acceptedAnchor: string | undefined;
      if (runtime.cluster) {
        const answer = await vscode.window.showInformationMessage("Trust this cluster enrollment anchor?", {modal:true,detail:`${url}\nCluster: ${runtime.cluster.cluster_id}\nGeneration: ${runtime.cluster.generation}\nAnchor SHA-256: ${runtime.cluster.anchor_key_id}\n\nCompare this fingerprint with the operator enrollment record. This pins the signed manifest and its permitted endpoints.`}, "Trust cluster");
        if (answer !== "Trust cluster") return; acceptedAnchor = runtime.cluster.anchor_key_id;
      }
      const p = await profiles.saveCloud(label, url, runtime.installationId, runtime, acceptedAnchor);
      refresh(); await connect(p); await vscode.commands.executeCommand("netclaw.openOverview"); return;
    }
    const url = await vscode.window.showInputBox({
      title: "NetClaw HUD API address",
      value: "http://127.0.0.1:3001",
      prompt: `Enter the running HUD API address on ${hostContext()}. The usual local address is http://127.0.0.1:3001. For another host, first open its WSL or Remote SSH workspace.`,
    });
    if (!url) return;
    const p = await profiles.save({ label, url });
    refresh();
    await connect(p);
  });
  register("selectConnection", async (id?: string) => {
    const p = id
      ? profiles.list().find((p) => p.id === id)
      : (
          await vscode.window.showQuickPick(
            profiles
              .list()
              .map((p) => ({ label: p.label, description: p.url, profile: p })),
            { title: "Select existing NetClaw" },
          )
        )?.profile;
    if (p) await selectConnectionProfile(p, connection, connect, async () => vscode.commands.executeCommand("netclaw.openOverview"));
    else if (!profiles.list().length)
      await vscode.commands.executeCommand("netclaw.addConnection");
  });
  register("disconnect", () => connection.disconnect());
  register("renameConnection", async () => {
    const item = await vscode.window.showQuickPick(
      profiles.list().map((p) => ({ label: p.label, p })),
    );
    if (!item) return;
    const label = await vscode.window.showInputBox({
      title: "Connection label",
      value: item.p.label,
    });
    if (label) {
      await profiles.save({ ...item.p, label });
      await management.rename(item.p.id, label);
      if (connection.profile?.id === item.p.id)
        connection.profile.label = label;
      refresh();
    }
  });
  let endpointUpdateBusy = false;
  register("replaceCloudEndpoint", async () => {
    if (endpointUpdateBusy) throw Error("An endpoint update is already open.");
    endpointUpdateBusy = true;
    try {
      const item = await vscode.window.showQuickPick(profiles.list().filter(p => p.mode === "remote-border").map(p => ({ label: p.label, description: p.url, profile: p })), { title: "Replace cloud Border endpoint" });
      if (!item) return; const previous = item.profile;
      if (!previous.cloudExecution || !previous.cloudPrincipal) throw Error("Connect this profile once to record its identity and execution mode before replacing its endpoint.");
      const input = await vscode.window.showInputBox({ title: "Replacement cloud Border URL", value: previous.url, validateInput: value => { try { cloudInputOrigin(value); return undefined; } catch { return "Enter a canonical HTTPS Border origin."; } } });
      if (!input) return; const origin = cloudInputOrigin(input);
      const runtime = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: "Verifying replacement Border identity" }, () => discoverCloudBorder(origin, previous.cluster?.pin));
      if ((!previous.cluster && runtime.installationId !== previous.installationId) || cloudExecutionMode(runtime) !== previous.cloudExecution || ownerCanonical(runtime.access?.principal) !== ownerCanonical(previous.cloudPrincipal)) throw Error("Replacement Border identity, execution mode or operator differs. Saved connection and references are unchanged.");
      const answer = await vscode.window.showInformationMessage("Replace this Border's endpoint?", { modal: true, detail: `${previous.label}\nFrom: ${previous.url}\nTo: ${origin}\nInstallation: ${previous.installationId} → ${runtime.installationId}\n${previous.cluster ? `Cluster: ${previous.cluster.pin.cluster_id}\nGeneration: ${previous.cluster.pin.generation}\nManifest revision: ${runtime.cluster?.manifest_revision}\n` : ""}Execution: ${previous.cloudExecution}\n\nKeeps this profile, original operation references and sent decisions. No operation is submitted and no session cookie is transferred.` }, "Replace endpoint");
      if (answer !== "Replace endpoint") return;
      if (connection.profile?.id === previous.id) connection.disconnect();
      const saved = await profiles.replaceCloudEndpoint(previous, origin, runtime);
      refresh(); await connect(saved); await vscode.commands.executeCommand("netclaw.openOverview");
    } finally { endpointUpdateBusy = false; }
  });
  register("removeConnection", async () => {
    const item = await vscode.window.showQuickPick(
      profiles.list().map((p) => ({ label: p.label, p })),
    );
    if (!item) return;
    if (connection.profile?.id === item.p.id) connection.disconnect();
    await profiles.remove(item.p.id);
    await management.forget(item.p.id);
    refresh();
  });
  const openDomain = (key: Domain) => {
    if (!Object.hasOwn(domains, key)) throw Error("Unknown view.");
    if (connection.profile?.mode === "remote-border" && !connection.client) {
      if (key === "overview") return ownerWorkflow.overview();
      if (key === "operations") return ownerWorkflow.open();
      throw Error("This view is unavailable on the protected cloud Border.");
    }
    if (key === "network" && connection.profile?.mode !== "remote-border") return openTestbed(context, connection);
    if (key === "mobile") return openMobile(context, connection);
    const b = connection.bound();
    if (key === "security" || key === "openshell")
      return openSecurity(
        context,
        connection,
        key === "security" ? "defenseclaw" : "openshell",
      );
    return openDataView(context, connection, {
      title: domains[key].title,
      kind: key,
      load: () => b.run(() => inspect(b.client, key)),
    });
  };
  register("openDomain", openDomain);
  register("configureMcp", (id?: string) => openMcp(context, connection, id));
  for (const [name, key] of Object.entries({
    openOverview: "overview",
    openSettings: "settings",
    openTokenomics: "tokenomics",
    openGait: "gait",
    openIntegrations: "integrations",
    openSkills: "skills",
    openOperations: "operations",
    openPeers: "peers",
    openNetwork: "network",
    openScience: "science",
    openMobile: "mobile",
    openSecurity: "security",
    openOpenShell: "openshell",
  }))
    register(name, () => openDomain(key as Domain));
  register("openChat", () => openChat(context, connection));
  register("openAvatar", () => openChat(context, connection, true));
  register("openRag", () => openRag(context, connection));
  register("openCanvas", () => openCanvas(context, connection));
  register("configureSettings", () => configureSettings(connection));
  register("prepareChange", () => environment(connection));
  register("manageAssistants", () => assistants.setup());
  register("addSelectedContext", async () => {
    const b = connection.bound(),
      editor = vscode.window.activeTextEditor,
      text = editor?.document.getText(editor.selection);
    if (!text?.trim()) throw Error("Select the exact text you want to stage.");
    if (Buffer.byteLength(text) > 65536) throw Error("Select at most 64 KiB.");
    if (
      (await vscode.window.showInformationMessage(
        "Stage the selected text for NetClaw?",
        {
          modal: true,
          detail:
            "Only explicitly selected context is sent when you submit Chat or Canvas. It may be disclosed to your configured model provider.",
        },
        "Stage selected text",
      )) !== "Stage selected text"
    )
      return;
    b.current();
    const id = randomUUID();
    connection.contexts.set(id, {
      id,
      name: path.basename(editor!.document.fileName),
      content: text,
      size: Buffer.byteLength(text),
    });
    void vscode.window.showInformationMessage(
      "Text staged. Select it in Chat or Canvas before sending.",
    );
  });
  register("openDocumentation", async () => {
    const b = connection.bound(),
      list = await b.run(() =>
        b.client.request("GET", "/api/hud/documentation"),
      );
    const picked = await vscode.window.showQuickPick<
      vscode.QuickPickItem & { id: string }
    >(
      (list.documents || []).map((d: Json) => ({
        label: d.title || d.name || d.id,
        description: d.path,
        id: d.id,
      })),
      { title: "Existing NetClaw documentation" },
    );
    if (!picked) return;
    b.current();
    const doc = await b.run(() =>
      b.client.request(
        "GET",
        "/api/hud/documentation/" +
          encodeURIComponent((picked as { id: string }).id),
      ),
    );
    await vscode.window.showTextDocument(
      await vscode.workspace.openTextDocument({
        content: doc.content || JSON.stringify(doc, null, 2),
        language: "markdown",
      }),
      { preview: true },
    );
  });
  register("openLogs", async () => {
    const b = connection.bound(),
      list = await b.run(() => b.client.request("GET", "/api/hud/logs"));
    const picked = await vscode.window.showQuickPick<
      vscode.QuickPickItem & { id: string }
    >(
      (list.sources || []).map((d: Json) => ({ label: d.name, id: d.id })),
      { title: "Installation log source" },
    );
    if (!picked) {
      if (!list.sources?.length)
        void vscode.window.showInformationMessage(
          list.reason || "No log source exposed by this runtime.",
        );
      return;
    }
    b.current();
    const query = await vscode.window.showInputBox({
      title: "Filter log text",
      value: "",
    });
    if (query === undefined) return;
    const route =
      "/api/hud/logs/" +
      encodeURIComponent((picked as { id: string }).id) +
      "?q=" +
      encodeURIComponent(query) +
      "&severity=all";
    openDataView(context, connection, {
      title: "Installation logs",
      kind: "logs",
      load: () => b.run(() => b.client.request("GET", route)),
    });
  });
  const investigate = async (prompt: string) => {
    const b = connection.bound();
    const id = randomUUID();
    connection.contexts.set(id, {
      id,
      name: "Requested investigation",
      content: prompt,
      size: Buffer.byteLength(prompt),
    });
    b.current();
    await vscode.commands.executeCommand("netclaw.openChat");
    void vscode.window.showInformationMessage(
      "Investigation context staged. Enter your request and select this context in Chat; no work has been sent.",
    );
  };
  register("searchMemory", () =>
    investigate(
      "Use the installed memory tools to search recorded knowledge for the user’s question. Cite recorded sources and dates.",
    ),
  );
  register("analyzeContext", () =>
    investigate(
      "Use the existing GCF tool to analyze only the explicitly selected context.",
    ),
  );
  register("openMeetings", () =>
    investigate(
      "Inspect existing meeting context available to this NetClaw through its installed tools. Do not start a listener or join a meeting.",
    ),
  );
  register("openPeerChat", () => peerChat(context, connection));
  register("configureService", () => prepareService(connection));
  register("openNativeRuntime", async () => {
    const b = connection.bound(),
      r = await b.run(() => b.client.request("GET", "/api/hud/runtime"));
    const location = r.controlUi;
    if (
      !location?.available ||
      !Number.isInteger(location.port) ||
      location.port < 1 ||
      location.port > 65535 ||
      typeof location.basePath !== "string" ||
      !/^([/][A-Za-z0-9_-]+)*$/.test(location.basePath)
    )
      throw Error(
        location?.reason ||
          "This runtime does not expose a valid native UI location.",
      );
    const raw = `${location.tls ? "https" : "http"}://127.0.0.1:${location.port}${location.basePath}/`;
    const u = new URL(raw);
    if (
      !["127.0.0.1", "localhost", "[::1]"].includes(u.hostname) ||
      !["http:", "https:"].includes(u.protocol)
    )
      throw Error("Native UI URL is not host-local.");
    b.current();
    await vscode.env.openExternal(
      await vscode.env.asExternalUri(vscode.Uri.parse(raw)),
    );
  });
  register("reviewProposal", async () => {
    connection.bound();
    const files = fs.existsSync(assistants.directory)
      ? fs.readdirSync(assistants.directory).filter((f) => f.endsWith(".json"))
      : [];
    const drafts: Json[] = [];
    for (const file of files) {
      const r = JSON.parse(
        fs.readFileSync(path.join(assistants.directory, file), "utf8"),
      );
      if (
        /^[a-zA-Z0-9-]{1,120}$/.test(r.id) &&
        r.installationId === connection.identity?.installationId
      )
        drafts.push(
          ...new LocalState(path.join(assistants.directory, r.id)).get<Json[]>(
            "proposals",
            [],
          ),
        );
    }
    const item = await vscode.window.showQuickPick(
      drafts.map((d) => ({
        label: d.domain + " · " + d.summary.slice(0, 80),
        draft: d,
      })),
      { title: "Assistant drafts — no approval or execution authority" },
    );
    if (!item) return;
    await vscode.window.showTextDocument(
      await vscode.workspace.openTextDocument({
        language: "json",
        content: JSON.stringify(item.draft, null, 2),
      }),
    );
    void vscode.window.showInformationMessage(
      "This is an inert draft. Use Configure Settings or the existing NetClaw workflow to review and initiate any actual change.",
    );
  });
  register("openIntent", () => openIntent(context, connection));
  for (const name of ["exportGait", "exportDiagnostics"])
    register(name, async () => {
      const b = connection.bound(),
        value = await b.run(() =>
          inspect(b.client, name === "exportGait" ? "gait" : "overview"),
        );
      const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(value, null, 2),
        language: "json",
      });
      await vscode.window.showTextDocument(doc);
      const target = await vscode.window.showSaveDialog({
        saveLabel: "Save reviewed observation",
        filters: { JSON: ["json"] },
      });
      if (target)
        await vscode.workspace.fs.writeFile(target, Buffer.from(doc.getText()));
    });
  register("help", async () =>
    vscode.window.showTextDocument(
      await vscode.workspace.openTextDocument(
        vscode.Uri.joinPath(context.extensionUri, "README.md"),
      ),
    ),
  );
  register("refresh", refresh);
  const items = (group: string): Navigation[] => {
    const remote = connection.profile?.mode === "remote-border";
    const features = remote && connection.client ? remoteHudFeatures(connection.identity) : undefined;
    if (remote && group === "connections") return [
      ...profiles.list().map(p => ({ label: p.label, description: connection.profile?.id === p.id ? "Connected" : p.url, command: "netclaw.selectConnection", args: [p.id], icon: "remote" })),
      { label: "Add connection", command: "netclaw.addConnection", icon: "add" },
      { label: "Rename connection", command: "netclaw.renameConnection", icon: "edit" },
      { label: "Replace cloud endpoint", command: "netclaw.replaceCloudEndpoint", icon: "link" },
      { label: "Disconnect", command: "netclaw.disconnect", icon: "debug-disconnect" },
    ];
    if (remote && !features) {
      if (group === "estate") return [{ label: "Cloud Border identity", command: "netclaw.openOverview", icon: "globe" }];
      if (group === "operations") return [
        { label: "Prepare cloud read", command: "netclaw.ownerPrepare", icon: "checklist" },
        { label: "Recover cloud operation", command: "netclaw.ownerRecover", icon: "history" },
        ...(!connection.owner?.openLab ? [
          { label: "Sign in to cloud Border", command: "netclaw.ownerSignIn", icon: "key" },
          { label: "Sign out of cloud Border", command: "netclaw.ownerSignOut", icon: "sign-out" },
        ] : []),
      ];
      return [];
    }
    if (group === "connections")
      return [
        {
          label: "Set up a new NetClaw",
          description: "Separate installation",
          command: "netclaw.setupClaw",
          icon: "new-folder",
        },
        {
          label: "Workspace & Claw",
          description: management.selected?.profile.label || "Enable controls",
          command: "netclaw.workspaceControls",
          icon: "files",
        },
        {
          label: "Select connection",
          command: "netclaw.selectConnection",
          icon: "remote",
        },
        ...(management.selected
          ? [
              ...workspaceFiles.map((name) => ({
                label: name,
                command: "netclaw.openWorkspaceFile",
                args: [name],
                icon: "markdown",
              })),
              {
                label: "Start claw",
                command: "netclaw.startClaw",
                icon: "play",
              },
              {
                label: "Stop claw",
                command: "netclaw.stopClaw",
                icon: "debug-stop",
              },
              {
                label: "Restart claw",
                command: "netclaw.restartClaw",
                icon: "debug-restart",
              },
            ]
          : []),
        ...profiles.list().map((p) => ({
          label: p.label,
          description: connection.profile?.id === p.id ? "Connected" : p.url,
          command: "netclaw.selectConnection",
          args: [p.id],
          icon: "remote",
        })),
        {
          label: "Add existing NetClaw",
          command: "netclaw.addConnection",
          icon: "add",
        },
        {
          label: "Rename connection",
          command: "netclaw.renameConnection",
          icon: "edit",
        },
        { label: "Replace cloud endpoint", command: "netclaw.replaceCloudEndpoint", icon: "link" },
      ];
    const list: Navigation[] = Object.entries(domains)
      .filter(([key, d]) => d.group === group && (!features || features.has(remoteDomainFeature[key]!)))
      .map(([key, d]) => ({
        label: d.title,
        command: "netclaw.openDomain",
        args: [key],
        icon: d.icon,
      }));
    const extras: Record<string, [string, string, string][]> = {
      operations: [
        ["Chat", "openChat", "comment-discussion"],
        ["Canvas", "openCanvas", "preview"],
        ["Avatar", "openAvatar", "person"],
        ["Review installation logs", "openLogs", "output"],
        ["Terminal Intent", "openIntent", "terminal"],
      ],
      knowledge: [
        ["RAG knowledge base", "openRag", "search"],
        ["Search memory", "searchMemory", "history"],
        ["Meeting context", "openMeetings", "comment-discussion"],
      ],
      integrations: [
        ["Configure settings", "configureSettings", "settings-gear"],
        ["Copilot, Claude Code & Codex", "manageAssistants", "hubot"],
        ["Review assistant proposals", "reviewProposal", "checklist"],
      ],
      help: [
        ["Read documentation", "openDocumentation", "book"],
        ["Getting started", "help", "info"],
      ],
    };
    for (const [label, command, icon] of extras[group] || [])
      if (!features || features.has(remoteCommandFeature[command]!) || command === "help") list.push({ label, command: "netclaw." + command, icon });
    if (remote && connection.identity?.capabilities?.protectedOperations === true && group === "operations") list.push(
      { label: "Prepare protected read", command: "netclaw.ownerPrepare", icon: "checklist" },
      { label: "Recover retained operation", command: "netclaw.ownerRecover", icon: "history" },
    );
    return list;
  };
  for (const group of [
    "connections",
    "estate",
    "operations",
    "integrations",
    "knowledge",
    "security",
    "help",
  ]) {
    const tree = new NavigationTree(() => items(group));
    trees.push(tree);
    context.subscriptions.push(
      tree,
      vscode.window.registerTreeDataProvider("netclaw." + group, tree),
    );
  }
  refresh();
  return { connection, profiles, assistants, management, workspace, ownerWorkflow };
}
export function deactivate() {}
