import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import { load } from "./load.mjs";
const require = createRequire(
  new URL("../../../ui/netclaw-visual/package.json", import.meta.url),
);
const { JSDOM } = require("jsdom");
test("shell escapes identity, uses shared semantic purpose and fixed action names", async () => {
  const { pageHeader, viewPurpose, actionCommand } = await load(
    "src/webview/shell.ts",
  );
  const html = pageHeader("overview", "<Overview>", "<lab>", "hermes");
  assert.ok(html.includes("&lt;lab&gt;"));
  assert.ok(!html.includes("<lab>"));
  assert.ok(html.includes(viewPurpose("overview")));
  assert.equal(actionCommand("testbed"), "netclaw.openNetwork");
  assert.equal(actionCommand("workbench.action.terminal.new"), undefined);
});
test("all domain presenters supply useful sections and distinguish unknown/false/zero", () => {
  const dom = new JSDOM("", { runScripts: "outside-only" });
  dom.window.eval(fs.readFileSync("resources/presenters.js", "utf8"));
  const { present, definitions } = dom.window.netclawPresenters;
  assert.equal(Object.keys(definitions).length, 23);
  for (const kind of Object.keys(definitions)) {
    const model = present(kind, { data: {}, source: "/fixture" });
    assert.ok(model.description, kind);
    assert.ok(model.sections.length, kind);
  }
  const overview = present("overview", {
    data: {
      kind: "hermes",
      readiness: false,
      installationId: "fixture",
      capabilities: { writes: false },
    },
  });
  assert.ok(JSON.stringify(overview).includes("false"));
  const tokenomics = present("tokenomics", {
    data: { groups: [{ model: "fixture", input: 0, output: 2 }] },
  });
  assert.ok(JSON.stringify(tokenomics).includes("0"));
  assert.ok(
    !JSON.stringify(
      present("integrations", {
        data: { integrations: [{ id: "x", name: "Example", active: true }] },
      }),
    ).includes("Online"),
  );
  dom.window.close();
});

test("ordinary federation reply shows native text and peer trust attribution", () => {
  const dom = new JSDOM("", { runScripts: "outside-only" });
  dom.window.eval(fs.readFileSync("resources/presenters.js", "utf8"));
  const result = { source: "as65177-192.0.2.1", trust: "remote-untrusted", text: "A native peer reply", request_id: "request-177", session_id: "session-177" };
  const model = dom.window.netclawPresenters.present("peerChat", result);
  const facts = model.sections[0].cards[0].facts;
  for (const value of Object.values(result)) assert.ok(facts.some(f => f.value === value), value);
  assert.equal(model.provenance.source, result.source);
  const peers = dom.window.netclawPresenters.present("peers", { peers: [{ identity: result.source, display_name: "Organization A", state: "federated", channel_state: "up", chat_enabled: true, inventory_version: 2, stale: false }] });
  const card = peers.sections.find(s => s.title === "Peers").cards[0];
  assert.equal(card.title, "Organization A");
  for (const value of [result.source, "up", "true", "2", "false"]) assert.ok(card.facts.some(f => f.value === value), value);
  dom.window.close();
});

test("500 cards filter and paginate with distinct empty states and literal markup", async () => {
  const dom = new JSDOM(
    '<body data-kind="integrations" data-view-id="v"><input id="filter"><button id="refresh"></button><div id="status"></div><main><div id="content"></div></main></body>',
    { runScripts: "outside-only" },
  );
  const w = dom.window;
  w.TextEncoder = TextEncoder;
  let state;
  w.acquireVsCodeApi = () => ({
    getState: () => state,
    setState: (x) => (state = x),
    postMessage: () => {},
  });
  for (const file of ["messaging.js", "presenters.js", "data.js"])
    w.eval(fs.readFileSync("resources/" + file, "utf8"));
  const data = {
    source: "/fixture",
    data: {
      integrations: Array.from({ length: 500 }, (_, i) => ({
        id: "entry-" + i,
        name: "Integration " + i,
        description:
          i === 499
            ? "<script>privateMarkup()</script>"
            : "Synthetic integration",
        active: false,
      })),
    },
  };
  w.dispatchEvent(
    new w.MessageEvent("message", { data: { viewId: "v", data } }),
  );
  assert.equal(w.document.querySelectorAll("article").length, 50);
  const filter = w.document.getElementById("filter"),
    start = performance.now();
  filter.value = "entry-499";
  filter.dispatchEvent(new w.Event("input"));
  await new Promise((r) => setTimeout(r, 110));
  const elapsed = performance.now() - start - 80;
  assert.equal(w.document.querySelectorAll("article").length, 1);
  assert.ok(
    w.document
      .getElementById("content")
      .textContent.includes("<script>privateMarkup()</script>"),
  );
  assert.equal(w.document.querySelectorAll("script").length, 0);
  assert.ok(elapsed < 250);
  console.log(
    JSON.stringify({
      measurement: "500-card filter settled-to-render upper bound",
      ms: Math.round(elapsed),
      host: process.platform + " " + process.arch,
      node: process.version,
      renderer: "JSDOM; actual editor measured separately",
    }),
  );
  filter.value = "absent";
  filter.dispatchEvent(new w.Event("input"));
  await new Promise((r) => setTimeout(r, 110));
  assert.match(
    w.document.getElementById("content").textContent,
    /No loaded entries match/,
  );
  w.dispatchEvent(
    new w.MessageEvent("message", {
      data: { viewId: "v", error: "Connection changed", invalidated: true },
    }),
  );
  assert.equal(filter.disabled, true);
  assert.equal(w.document.getElementById("content").textContent, "");
  dom.window.close();
});

test("normal remote panels expose only actions supported by their host transport", () => {
  const dom = new JSDOM('<body data-kind="integrations" data-view-id="remote"><input id="filter"><button id="refresh"></button><div id="status"></div><main><div id="content"></div></main></body>', {runScripts:"outside-only"});
  const w=dom.window; w.TextEncoder=TextEncoder; w.acquireVsCodeApi=()=>({getState:()=>undefined,setState:()=>{},postMessage:()=>{}});
  for(const file of ["messaging.js","presenters.js","data.js"])w.eval(fs.readFileSync("resources/"+file,"utf8"));
  w.dispatchEvent(new w.MessageEvent("message",{data:{viewId:"remote",availableActions:["chat","integrations"],data:{data:{integrations:[{id:"netbox",name:"NetBox",active:true}]}}}}));
  assert.ok(w.document.getElementById("content").textContent.includes("NetBox"));
  assert.equal([...w.document.querySelectorAll("#content button")].some(b=>/Configure/i.test(b.textContent)),false);
  dom.window.close();
});
