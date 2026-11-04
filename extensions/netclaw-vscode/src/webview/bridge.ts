import * as vscode from "vscode";
import { randomBytes, randomUUID } from "node:crypto";
import { pageHeader, escape, actionCommand } from "./shell";
import { Connection } from "../connection/connect";
import { remoteHudFeatures, remoteCommandFeature } from "../client/remote-hud";

export interface ViewDefinition {
  title: string;
  kind: string;
  load: () => Promise<unknown>;
}
export function openDataView(
  context: vscode.ExtensionContext,
  connection: Connection,
  view: ViewDefinition,
): vscode.WebviewPanel {
  const panel = vscode.window.createWebviewPanel(
    `netclaw.${view.kind}`,
    view.title,
    vscode.ViewColumn.One,
    {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.joinPath(context.extensionUri, "resources"),
        vscode.Uri.joinPath(context.extensionUri, "dist"),
      ],
    },
  );
  const nonce = randomBytes(24).toString("base64"),
    viewId = randomUUID(),
    generation = connection.generation;
  const css = panel.webview.asWebviewUri(
    vscode.Uri.joinPath(context.extensionUri, "resources", "workbench.css"),
  );
  const script = panel.webview.asWebviewUri(
    vscode.Uri.joinPath(context.extensionUri, "resources", "data.js"),
  );
  const messaging = panel.webview.asWebviewUri(
    vscode.Uri.joinPath(context.extensionUri, "resources", "messaging.js"),
  );
  const resource = (file: string) =>
    panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, file));
  panel.webview.html = `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${panel.webview.cspSource}; style-src ${panel.webview.cspSource}; script-src 'nonce-${nonce}';"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="${css}"></head><body class="data-view" data-kind="${escape(view.kind)}" data-view-id="${viewId}">${pageHeader(view.kind, view.title, connection.profile?.label || "Disconnected", connection.identity?.kind || "")}<main><div class="filter-bar"><div class="search-field"><label for="filter">Search this view</label><input id="filter" type="search" maxlength="200" placeholder="Find a device, integration or entry…" aria-describedby="filter-hint"></div><button id="refresh" type="button" class="secondary">Refresh</button></div><p id="filter-hint" class="hint">Search loaded entries · 50 per page. Source information stays visible.</p><p id="status" role="status" aria-live="polite">Loading…</p>${view.kind === "overview" ? `<div class="welcome-art" aria-hidden="true"><img src="${resource("resources/brand/network-core.png")}" alt=""></div>` : ""}<div id="content"></div></main><script nonce="${nonce}" src="${messaging}"></script><script nonce="${nonce}" src="${resource("resources/presenters.js")}"></script><script nonce="${nonce}" src="${script}"></script>${view.kind === "topology" ? `<script nonce="${nonce}" src="${resource("dist/topology.js")}"></script>` : ""}</body></html>`;
  const remoteActions = connection.profile?.mode === "remote-border" ? ["chat", "integrations", "knowledge", "documentation"].filter(action => {
    const command = actionCommand(action)?.replace("netclaw.", "");
    return command && remoteHudFeatures(connection.identity).has(remoteCommandFeature[command]!);
  }) : undefined;
  let disposed = false,
    loading = false,
    received = 0;
  const load = async () => {
    if (loading || disposed) return;
    loading = true;
    try {
      if (connection.generation !== generation)
        throw Error(
          "Connection changed. Reopen this view for the selected installation.",
        );
      const data = await view.load();
      if (connection.generation !== generation || disposed) return;
      if (Buffer.byteLength(JSON.stringify(data)) > 1024 * 1024)
        throw Error(
          "Observation exceeds the display limit. Narrow the source selection.",
        );
      await panel.webview.postMessage({ viewId, data, ...(remoteActions ? { availableActions: remoteActions } : {}) });
    } catch (error) {
      if (!disposed)
        await panel.webview.postMessage({
          viewId,
          error: error instanceof Error ? error.message : "Source unavailable",
          ...(connection.generation !== generation
            ? { invalidated: true }
            : {}),
        });
    } finally {
      loading = false;
    }
  };
  panel.webview.onDidReceiveMessage((message: unknown) => {
    if (!message || typeof message !== "object") return;
    const m = message as Record<string, unknown>;
    if (
      (m.type === "action"
        ? Object.keys(m).some(
            (k) => !["requestId", "type", "viewId", "action", "id"].includes(k),
          )
        : Object.keys(m).sort().join(",") !== "requestId,type,viewId") ||
      !["ready", "refresh", "action"].includes(String(m.type)) ||
      m.viewId !== viewId ||
      typeof m.requestId !== "string" ||
      !/^\d{1,12}$/.test(m.requestId) ||
      Number(m.requestId) <= received
    )
      return;
    received = Number(m.requestId);
    if (!vscode.workspace.isTrusted) return;
    if (connection.generation !== generation) return;
    if (m.type === "action") {
      const command =
        typeof m.action === "string" ? actionCommand(m.action) : undefined;
      if (
        !command || (remoteActions && !remoteActions.includes(String(m.action))) ||
        (m.id !== undefined &&
          (typeof m.id !== "string" || !/^[a-z0-9_-]{1,100}$/.test(m.id)))
      )
        return;
      void vscode.commands.executeCommand(command, m.id);
    } else void load();
  });
  const changed = connection.changed.event(() => {
    if (!disposed && connection.generation !== generation)
      void panel.webview.postMessage({
        viewId,
        error:
          "Connection changed. Reopen this view for the selected installation.",
        invalidated: true,
      });
  });
  panel.onDidDispose(() => {
    disposed = true;
    changed.dispose();
  });
  return panel;
}
