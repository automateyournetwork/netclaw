import * as vscode from "vscode";
import path from "node:path";
import { Connection } from "../connection/connect";
import { Conversation, terminalStates, Json } from "../client/hud";
import { LocalState } from "../state/local";
import { panel } from "../webview/panel";
const active = new Map<
  string,
  { view: vscode.WebviewPanel; avatar: boolean; busy: () => boolean }
>();
export function selectedContext(connection: Connection, ids: unknown): string {
  if (
    !Array.isArray(ids) ||
    ids.length > 20 ||
    ids.some((id) => typeof id !== "string" || !connection.contexts.has(id))
  )
    throw Error("Selected context is unavailable. Review the selection.");
  return ids
    .map((id) => {
      const c = connection.contexts.get(id)!;
      return `${c.name}\n${c.content}`;
    })
    .join("\n\n");
}
export async function modelSettings(
  connection: Connection,
): Promise<Json | undefined> {
  const b = connection.bound(),
    data = await b.run(() =>
      b.client.request("GET", "/api/chat/models", undefined, connection.profile?.mode === "remote-border" ? 90000 : 30000),
    );
  const choices = [
    { label: "Configured NetClaw default", id: "", efforts: [] },
    ...(data.models || []),
  ];
  const model = await vscode.window.showQuickPick(
    choices.map((m: Json) => ({ label: m.label, model: m })),
    { title: "Model for a new conversation" },
  );
  if (!model) return;
  const selected = model as { model: Json };
  b.current();
  let effort = "";
  if (selected.model.efforts?.length) {
    const choice = await vscode.window.showQuickPick(
      ["Configured default", ...selected.model.efforts] as string[],
      { title: "Reasoning effort" },
    );
    if (choice === undefined) return;
    effort = choice === "Configured default" ? "" : choice;
  }
  return { chatModel: selected.model.id, chatEffort: effort };
}
export function openChat(
  context: vscode.ExtensionContext,
  connection: Connection,
  avatar = false,
) {
  const key = `chat.${connection.profile?.id}.${connection.identity?.installationId}`;
  const existing = active.get(key);
  if (existing) {
    if (existing.avatar === avatar || existing.busy()) {
      existing.view.reveal();
      return existing.view;
    }
    existing.view.dispose();
  }
  const local = new LocalState(
    path.join(context.globalStorageUri.fsPath, "conversations"),
  );
  let saved = local.get<{
      conversation?: Conversation;
      draft?: string;
      retain?: boolean;
    }>(key, {}),
    busy = false;
  const p = panel(
    context,
    connection,
    avatar ? "avatar" : "chat",
    avatar ? "NetClaw Avatar" : "NetClaw Chat",
    `
    <div class="toolbar"><button id="refresh">Check status</button><button id="new">New conversation</button><button id="history">Owned history</button><button id="settings">New with model settings</button><button id="cancel">Request stop</button></div>
    <p id="status" role="status" aria-live="polite">Loading owned conversation…</p><div class="${avatar ? "avatar-layout" : "chat-layout"}">${avatar ? '<div id="avatar" data-assets="{{AVATAR_ASSETS}}"></div>' : ""}<div class="conversation">
    <section id="transcript" aria-label="Conversation"></section><form id="composer"><label for="prompt">Message to NetClaw</label><textarea id="prompt" rows="5" maxlength="65536" placeholder="Ask your selected NetClaw…"></textarea><fieldset id="context"><legend>Explicitly staged context</legend><div id="contexts"></div></fieldset><label><input id="retain" type="checkbox"> Keep this draft on this editor host</label><p class="hint">Requests use this installation’s existing provider, tools and approval rules. Selected context is sent only when you submit. Closing this view does not cancel work.</p><button id="send" type="submit">Send to NetClaw</button></form></div></div>`,
    ["resources/chat.js", ...(avatar ? ["dist/avatar.js"] : [])],
  );
  const { client, current } = p.bound;
  active.set(key, { view: p.view, avatar, busy: () => busy });
  p.view.onDidDispose(() => {
    if (active.get(key)?.view === p.view) active.delete(key);
  });
  const persist = async () => {
    current();
    await local.update(key, saved);
  };
  const load = async (initial = false) => {
    current();
    const c = saved.conversation;
    if (
      c?.state === "submitting" &&
      !busy &&
      client.runtime?.kind === "openclaw"
    ) {
      c.state = "unknown";
      await persist();
    }
    if (c?.nonce && client.runtime?.kind === "hermes" && !busy) {
      await p.bound.run(() => client.status(c));
      await persist();
    }
    await p.post({
      type: "state",
      initial,
      saved: {
        ...saved,
        pendingNonce:
          c && !terminalStates.has(c.state || "completed")
            ? c.nonce
            : undefined,
        operationId: c?.requestId || c?.thread,
      },
      messages: c?.messages || [],
      contexts: [...connection.contexts.values()].map(
        ({ content, ...rest }) => rest,
      ),
      busy,
      state: c?.state || "completed",
      canStop: client.runtime?.kind === "hermes" && Boolean(c?.requestId),
      runtime: client.runtime?.kind,
    });
  };
  p.onMessage(
    [
      "ready",
      "refresh",
      "new",
      "settings",
      "history",
      "draft",
      "cancel",
      "send",
    ],
    async (m) => {
      if (m.type === "draft") {
        if (
          typeof m.payload?.text !== "string" ||
          m.payload.text.length > 65536
        )
          return;
        saved = {
          ...saved,
          retain: m.payload.retain === true,
          draft: m.payload.retain === true ? m.payload.text : undefined,
        };
        await persist();
        return;
      }
      if (busy) return;
      if (["ready", "refresh"].includes(m.type)) {
        await load(m.type === "ready");
        return;
      }
      busy = true;
      try {
        if (m.type === "history") {
          await p.bound.run(() => client.session());
          const list = await p.bound.run(() =>
            client.request("GET", "/api/chat/conversations", undefined, 30000),
          );
          const item = await vscode.window.showQuickPick<
            vscode.QuickPickItem & { id: string }
          >(
            (list.conversations || []).map((c: Json) => ({
              label: c.title || "Conversation",
              description: c.id,
              id: c.id,
            })),
            { title: "This extension’s owned conversations" },
          );
          if (!item) return;
          current();
          const previous = saved.conversation,
            reopened = await p.bound.run(() =>
              client.openConversation(item.id),
            );
          saved.conversation =
            previous?.thread === reopened.thread
              ? { ...previous, messages: reopened.messages }
              : { ...reopened, state: reopened.state || "unknown" };
          await persist();
        }
        if (m.type === "new" || m.type === "settings") {
          const previous = saved.conversation;
          if (
            previous?.state &&
            !terminalStates.has(previous.state) &&
            (await vscode.window.showWarningMessage(
              "A previous request is unresolved. A new conversation will not cancel it.",
              { modal: true },
              "Start separate conversation",
            )) !== "Start separate conversation"
          )
            return;
          const settings =
            m.type === "settings" ? await modelSettings(connection) : {};
          if (!settings) return;
          current();
          saved.conversation = await p.bound.run(() =>
            client.newConversation(
              settings,
              previous?.state && !terminalStates.has(previous.state)
                ? previous.requestId
                : undefined,
            ),
          );
          await persist();
        }
        if (m.type === "cancel" && saved.conversation) {
          const result = await p.bound.run(() =>
            client.stop(saved.conversation!),
          );
          await p.post({
            type: "notice",
            message: `Stop requested: ${result.state || "check status"}.`,
          });
        }
        if (m.type === "send") {
          if (typeof m.payload?.text !== "string")
            throw Error("Invalid message.");
          const content = selectedContext(
            connection,
            m.payload.contextIds || [],
          );
          if (!saved.conversation)
            saved.conversation = await p.bound.run(() =>
              client.newConversation(),
            );
          try {
            await p.bound.run(() =>
              client.send(
                saved.conversation!,
                m.payload.text,
                content,
                persist,
              ),
            );
            saved.draft = undefined;
            await p.post({ type: "sent" });
          } finally {
            await persist();
          }
        }
      } finally {
        busy = false;
        await load(["new", "settings", "history"].includes(m.type));
      }
    },
  );
  return p.view;
}
