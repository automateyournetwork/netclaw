/*
 * NetClaw Canvas Chat
 *
 * The spatial conversation workflow is adapted from Jack Rabbit by Tech
 * Built Right. NetClaw-specific transport, branding, and gateway behavior are
 * modifications. See LICENSE in this directory for the upstream MIT terms.
 */
import React, { useState, useRef, useEffect, useLayoutEffect, useCallback } from "react";
import { createPortal } from "react-dom";

// ---- theme ---------------------------------------------------------------
const C = {
  canvas: "var(--canvas)", ink: "var(--ink)", muted: "var(--muted)", card: "var(--card)",
  cardAlt: "var(--cardAlt)", hairline: "var(--hairline)", userBubble: "var(--userBubble)",
  trunk: "var(--trunk)", codeBg: "var(--codeBg)", relBg: "var(--relBg)", relBorder: "var(--relBorder)", relText: "var(--relText)",
};
// light/dark palettes injected as CSS custom properties on the root container
const LIGHT = { "--canvas": "#FBFAF6", "--ink": "#1C2433", "--muted": "#6B7280", "--card": "#FFFFFF", "--cardAlt": "#F6F2E7", "--hairline": "#E3DECF", "--userBubble": "#EEF1F6", "--trunk": "#1B2A4A", "--codeBg": "#F4F1E8", "--relBg": "#F4F1FB", "--relBorder": "#D9CFF0", "--relText": "#5B4B9E", "--ring": "rgba(28,36,51,0.13)", "--shadow": "rgba(0,0,0,0.12)",
  "--codeText": "#1F2937", "--codeKw": "#6F42C1", "--codeStr": "#0A6E20", "--codeFn": "#005CC5", "--codeNum": "#B5651D", "--codeCmt": "#7A8290" };
const DARK = { "--canvas": "#0F1216", "--ink": "#E7EAF0", "--muted": "#8B93A4", "--card": "#181C22", "--cardAlt": "#1F242C", "--hairline": "#2A2F39", "--userBubble": "#232A36", "--trunk": "#6098F0", "--codeBg": "#1B2028", "--relBg": "#221E30", "--relBorder": "#3A3350", "--relText": "#BBA9EC", "--ring": "rgba(255,255,255,0.16)", "--shadow": "rgba(0,0,0,0.5)",
  "--codeText": "#CFD2D8", "--codeKw": "#C678DD", "--codeStr": "#98C379", "--codeFn": "#61AFEF", "--codeNum": "#E5C07B", "--codeCmt": "#6A7380" };
const BRANCH = ["#0E7C7B", "#B5651D", "#5B4B9E", "#A8324E", "#2F6FB0", "#7A6A1F"];
const ALLCOLORS = [C.trunk, ...BRANCH];
const depthColor = (d) => (d === 0 ? C.trunk : BRANCH[(d - 1) % BRANCH.length]);
const markerId = (color) => "mk" + ALLCOLORS.indexOf(color);

// Build an SVG path from a right-angle polyline, rounding each corner.
function roundedElbow(pts, r) {
  if (pts.length < 2) return "";
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 1; i < pts.length - 1; i++) {
    const prev = pts[i - 1], cur = pts[i], next = pts[i + 1];
    const inDx = Math.sign(cur.x - prev.x), inDy = Math.sign(cur.y - prev.y);
    const outDx = Math.sign(next.x - cur.x), outDy = Math.sign(next.y - cur.y);
    const rIn = Math.min(r, Math.hypot(cur.x - prev.x, cur.y - prev.y) / 2);
    const rOut = Math.min(r, Math.hypot(next.x - cur.x, next.y - cur.y) / 2);
    d += ` L ${cur.x - inDx * rIn} ${cur.y - inDy * rIn} Q ${cur.x} ${cur.y} ${cur.x + outDx * rOut} ${cur.y + outDy * rOut}`;
  }
  const last = pts[pts.length - 1];
  d += ` L ${last.x} ${last.y}`;
  return d;
}

// Orthogonal connector that nudges its vertical channel clear of any box sitting
// in the gap between parent and child (heuristic, not a full maze router).
function orthPath(p, c, obstacles) {
  const M = 16, rightward = (c.x + c.w / 2) >= (p.x + p.w / 2);
  const sx = rightward ? p.x + p.w : p.x;
  const ex = rightward ? c.x : c.x + c.w;
  const sy = p.y + p.h / 2;
  const ey = c.y + c.h / 2;

  let chx = (sx + ex) / 2;
  const yTop = Math.min(sy, ey), yBot = Math.max(sy, ey);
  const blockers = obstacles.filter((o) => o.x < chx && chx < o.x + o.w && o.y < yBot && o.y + o.h > yTop);
  if (blockers.length) {
    const gapLo = Math.min(sx, ex), gapHi = Math.max(sx, ex);
    const leftEdge = Math.min(...blockers.map((o) => o.x)) - M;
    const rightEdge = Math.max(...blockers.map((o) => o.x + o.w)) + M;
    if (rightEdge < gapHi) chx = rightEdge;
    else if (leftEdge > gapLo) chx = leftEdge;
    else chx = rightward ? gapHi - M : gapLo + M;
  }
  return roundedElbow([{ x: sx, y: sy }, { x: chx, y: sy }, { x: chx, y: ey }, { x: ex, y: ey }], 8);
}

const DEF_W = 360, DEF_H = 460, MIN_W = 260, MIN_H = 220, GAP = 130;

// Compute "tidy" positions for every visible node, organizing them into depth columns.
// Returns a Map(id -> {x, y}). Closed nodes are skipped. Within each column nodes are
// stacked vertically; parents are vertically centered across their direct children.
function computeTidyLayout(nodes, opts = {}) {
  const X0 = opts.x0 ?? 40;
  const Y0 = opts.y0 ?? 40;
  const COL_GAP = opts.colGap ?? GAP;
  const ROW_GAP = opts.rowGap ?? 24;
  const visible = nodes.filter((n) => !n.closed);
  if (!visible.length) return new Map();
  // depth -> max width seen in that column, used so wide nodes don't bleed across columns
  const colMaxW = [];
  visible.forEach((n) => {
    colMaxW[n.depth] = Math.max(colMaxW[n.depth] || 0, n.w || DEF_W);
  });
  const colX = [X0];
  for (let d = 1; d < colMaxW.length; d++) colX[d] = colX[d - 1] + (colMaxW[d - 1] || DEF_W) + COL_GAP;
  // index of children, ordered by current y to preserve user intent where possible
  const children = new Map();
  visible.forEach((n) => {
    const p = n.parentId || null;
    if (!children.has(p)) children.set(p, []);
    children.get(p).push(n);
  });
  for (const arr of children.values()) arr.sort((a, b) => (a.y - b.y) || String(a.id).localeCompare(String(b.id)));
  const positions = new Map();
  function placeSubtree(node, yCursor) {
    const nodeH = node.min ? 48 : (node.h || DEF_H);
    const x = colX[node.depth] != null ? colX[node.depth] : X0;
    const kids = children.get(node.id) || [];
    if (!kids.length) { positions.set(node.id, { x, y: yCursor }); return { top: yCursor, bottom: yCursor + nodeH }; }
    let kidY = yCursor;
    let firstKidTop = null, lastKidBottom = yCursor;
    kids.forEach((k) => {
      const r = placeSubtree(k, kidY);
      if (firstKidTop === null) firstKidTop = r.top;
      lastKidBottom = r.bottom;
      kidY = r.bottom + ROW_GAP;
    });
    const mid = (firstKidTop + lastKidBottom) / 2;
    const myY = Math.max(yCursor, mid - nodeH / 2);
    positions.set(node.id, { x, y: myY });
    return { top: yCursor, bottom: Math.max(myY + nodeH, lastKidBottom) };
  }
  const roots = (children.get(null) || []).slice();
  roots.sort((a, b) => (a.y - b.y) || String(a.id).localeCompare(String(b.id)));
  let cursor = Y0;
  roots.forEach((r) => { const out = placeSubtree(r, cursor); cursor = out.bottom + ROW_GAP; });
  return positions;
}

const zbtn = { width: 28, height: 28, border: "none", background: "transparent", color: C.ink, cursor: "pointer", fontSize: 16, lineHeight: 1, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" };

const COLLAPSED_H = 48;               // height of a minimized lane
const STORE_KEY = "netclaw-canvas-v1"; // legacy localStorage key, migrated on first run

// ---- IndexedDB persistence ----------------------------------------------
// Sessions live in IDB instead of localStorage so capacity scales to ~half the disk
// and we can keep an indefinite history of past investigations.
const DB_NAME = "netclaw-canvas";
const DB_VER = 2;
const SESS_STORE = "sessions";
const KV_STORE = "kv";

function idbOpen() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") return reject(new Error("no indexedDB"));
    const req = indexedDB.open(DB_NAME, DB_VER);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(SESS_STORE)) {
        const s = db.createObjectStore(SESS_STORE, { keyPath: "id" });
        s.createIndex("updatedAt", "updatedAt");
      }
      if (!db.objectStoreNames.contains(KV_STORE)) db.createObjectStore(KV_STORE, { keyPath: "k" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
const idb = {
  async put(s) { const db = await idbOpen(); return new Promise((res, rej) => { const tx = db.transaction(SESS_STORE, "readwrite"); tx.objectStore(SESS_STORE).put(s); tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error); }); },
  async get(id) { const db = await idbOpen(); return new Promise((res, rej) => { const r = db.transaction(SESS_STORE).objectStore(SESS_STORE).get(id); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); }); },
  async list() { const db = await idbOpen(); return new Promise((res, rej) => { const r = db.transaction(SESS_STORE).objectStore(SESS_STORE).getAll(); r.onsuccess = () => res(r.result || []); r.onerror = () => rej(r.error); }); },
  async del(id) { const db = await idbOpen(); return new Promise((res, rej) => { const tx = db.transaction(SESS_STORE, "readwrite"); tx.objectStore(SESS_STORE).delete(id); tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error); }); },
  async kvGet(k) { const db = await idbOpen(); return new Promise((res, rej) => { const r = db.transaction(KV_STORE).objectStore(KV_STORE).get(k); r.onsuccess = () => res(r.result ? r.result.v : null); r.onerror = () => rej(r.error); }); },
  async kvPut(k, v) { const db = await idbOpen(); return new Promise((res, rej) => { const tx = db.transaction(KV_STORE, "readwrite"); tx.objectStore(KV_STORE).put({ k, v }); tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error); }); },
  async kvDel(k) { const db = await idbOpen(); return new Promise((res, rej) => { const tx = db.transaction(KV_STORE, "readwrite"); tx.objectStore(KV_STORE).delete(k); tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error); }); },
};

const sessId = () => "s-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
const fmtAgo = (ts) => {
  const s = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago";
  return Math.floor(s / 86400) + "d ago";
};
function deriveSessionTitle(nodes) {
  if (!Array.isArray(nodes) || !nodes.length) return "New session";
  const root = nodes.find((n) => n.depth === 0 && !n.closed) || nodes.find((n) => n.depth === 0);
  if (root) {
    const u = (root.messages || []).find((m) => m.role === "user" && !m.relate);
    if (u && u.content) {
      const s = String(u.content).replace(/\s+/g, " ").trim();
      return s.length > 60 ? s.slice(0, 59).trimEnd() + "…" : s;
    }
  }
  return "New session";
}

// ---- api -----------------------------------------------------------------
// NetClaw owns model/provider selection. The canvas sends branch-isolated
// context to the same local API used by the existing Visual HUD chat drawer.
const apiError = async (res) => { let detail = ""; try { const j = await res.json(); detail = j.error?.message || j.message || JSON.stringify(j.error || j); } catch {} return new Error("API " + res.status + (detail ? ": " + detail : "")); };

// --- per-provider call shims; each returns assistant text or throws ---
async function callNetClaw({ messages }) {
  const context = messages.map((m) => ({ role: m.role, content: openaiContent(m) }));
  const latestUser = [...context].reverse().find((m) => m.role === "user");
  const latestText = typeof latestUser?.content === "string"
    ? latestUser.content
    : (latestUser?.content || []).filter((part) => part.type === "text").map((part) => part.text).join("\n");
  const requestText = latestText.endsWith("\n\n" + TAB_SYSTEM)
    ? latestText.slice(0, -(TAB_SYSTEM.length + 2)).trim()
    : latestText;
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // `message` drives NetClaw's activation visualization; `messages` carries
    // the complete branch context (including the answer-format instruction).
    body: JSON.stringify({ message: requestText, messages: context }),
  });
  if (!res.ok) throw await apiError(res);
  const data = await res.json();
  return String(data.response || "").trim();
}

async function callLLM(messages) {
  const text = await callNetClaw({ messages });
  if (!text) throw new Error("empty response from NetClaw");
  return text;
}

// ---- image attachments (vision) ------------------------------------------
// Read a File into { mediaType, data(base64), name }, downscaling very large images so the payload
// stays within provider limits (~1568px on the long edge is the recommended sweet spot).
function prepImage(file, maxDim = 1568) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    const parse = (u) => { const m = String(u).match(/^data:([^;]+);base64,(.*)$/); return m ? { mediaType: m[1], data: m[2] } : null; };
    reader.onerror = () => reject(reader.error || new Error("read failed"));
    reader.onload = () => {
      const dataUrl = String(reader.result);
      const img = new Image();
      img.onerror = () => { const p = parse(dataUrl); p ? resolve({ ...p, name: file.name }) : reject(new Error("decode failed")); };
      img.onload = () => {
        const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
        if (scale >= 1 || !img.width) { const p = parse(dataUrl); return p ? resolve({ ...p, name: file.name }) : reject(new Error("bad image")); }
        try {
          const cw = Math.max(1, Math.round(img.width * scale)), ch = Math.max(1, Math.round(img.height * scale));
          const canvas = document.createElement("canvas"); canvas.width = cw; canvas.height = ch;
          canvas.getContext("2d").drawImage(img, 0, 0, cw, ch);
          const p = parse(canvas.toDataURL("image/jpeg", 0.85));
          p ? resolve({ ...p, name: file.name }) : reject(new Error("encode failed"));
        } catch (e) { reject(e); }
      };
      img.src = dataUrl;
    };
    reader.readAsDataURL(file);
  });
}
const imgDataUrl = (im) => `data:${im.mediaType};base64,${im.data}`;

// ---- text / data / code file attachments ---------------------------------
const TEXT_FILE_EXT = /\.(json|jsonl|ndjson|txt|text|md|markdown|mdx|csv|tsv|log|ya?ml|toml|xml|svg|html?|css|scss|less|js|jsx|mjs|cjs|ts|tsx|py|go|rs|java|kt|kts|c|cc|cpp|cxx|h|hpp|rb|php|swift|scala|sh|bash|zsh|sql|graphql|gql|ini|conf|cfg|env|properties|gradle|dockerfile|makefile|ipynb|tex|rst|vue|svelte|dart|lua|r|pl|ps1)$/i;
function isTextFile(f) {
  const t = String(f.type || "");
  if (t.startsWith("text/")) return true;
  if (/(json|xml|javascript|typescript|x-yaml|yaml|x-sh|x-python|csv|markdown|graphql|toml)/i.test(t)) return true;
  return TEXT_FILE_EXT.test(f.name || "");
}
const MAX_ATTACH_TEXT = 1_000_000; // ~1MB cap so a huge file can't blow the context/payload
function readTextFile(f) {
  return new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(String(r.result)); r.onerror = () => reject(r.error || new Error("read failed")); r.readAsText(f); });
}

// Materialize message attachments for NetClaw's OpenAI-compatible gateway.
function openaiContent(m) {
  if (!m.images || !m.images.length) return m.content || "";
  const parts = [];
  if (m.content) parts.push({ type: "text", text: m.content });
  m.images.forEach((im) => parts.push({ type: "image_url", image_url: { url: imgDataUrl(im) } }));
  return parts;
}

function toAPIMessages(msgs) {
  const merged = [];
  for (const m of msgs) {
    const role = m.role === "user" ? "user" : "assistant";
    // a quoted snippet the user attached rides in front of their question so the model sees it as context
    let content = m.quote ? `Quoting from the conversation:\n"""\n${m.quote}\n"""\n\n${m.content || ""}` : (m.content || "");
    // attached text/data/code files are appended so the model can read them
    if (m.files && m.files.length) content += m.files.map((f) => `\n\n----- Attached file: ${f.name}${f.truncated ? " (truncated)" : ""} -----\n${f.text}`).join("");
    const images = m.images && m.images.length ? m.images : null;
    if (merged.length && merged[merged.length - 1].role === role) {
      const prev = merged[merged.length - 1];
      prev.content += "\n" + content;
      if (images) prev.images = [...(prev.images || []), ...images];
    } else merged.push({ role, content, ...(images ? { images } : {}) });
  }
  if (merged.length && merged[0].role !== "user") merged.unshift({ role: "user", content: "Context:" });
  return merged;
}

// The model returns answers in three delimited sections, rendered as tabs.
const TAB_SYSTEM = `Your reply is displayed in four tabs. Respond in EXACTLY this format, with nothing before the first delimiter and nothing after the last section:

===CONTEXT===
The full explanation. Keep it focused: a few short paragraphs, not an essay.

===SUMMARY===
2 to 3 sentences capturing the key point in plain language.

===AUTHORITATIVE SOURCE===
The most authoritative references for this topic, named explicitly: exact RFC numbers and titles, official standards bodies, or vendor documentation. Only cite sources you are confident exist; never invent an identifier. If no authoritative source applies, say so and tell the reader what to verify.

===SUGGESTED ACTION===
Concrete next steps to investigate or resolve this, as a short prioritized list. Be specific and operational (commands to run, things to check, what to rule out). If nothing actionable applies, say so.

Use those literal delimiter lines. Do not output any other section headers.`;

function parseTabs(raw) {
  const t = String(raw);
  const mC = t.match(/===\s*CONTEXT\s*===/i);
  const mS = t.match(/===\s*SUMMARY\s*===/i);
  const mA = t.match(/===\s*AUTHORITATIVE\s*SOURCE\s*===/i);
  const mX = t.match(/===\s*SUGGESTED\s*ACTION\s*===/i);
  if (!mC || !mS || !mA || !mX) return null;
  if (!(mC.index < mS.index && mS.index < mA.index && mA.index < mX.index)) return null;
  return {
    context: t.slice(mC.index + mC[0].length, mS.index).trim(),
    summary: t.slice(mS.index + mS[0].length, mA.index).trim(),
    sources: t.slice(mA.index + mA[0].length, mX.index).trim(),
    action: t.slice(mX.index + mX[0].length).trim(),
  };
}

let _seq = 0;

// Short title and one-line essence for the branch index.
function clip(s, n) { s = String(s || "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s; }
function nodeTitle(n) {
  if (n.title) return n.title;   // user-set custom thread/window name wins
  if (n.synthFrom && n.synthFrom.length) {
    const u = n.messages.find((m) => m.role === "user" && !m.relate);
    return u && u.content ? clip(u.content, 40) : `Synthesis of ${n.synthFrom.length}`;
  }
  if (n.depth === 0) {
    const u = n.messages.find((m) => m.role === "user" && !m.relate);
    return u && u.content ? clip(u.content, 40) : "New thread";
  }
  return n.sourceQuote || "Branch";
}
// depth-first pre-order so each node is listed directly beneath its parent
function orderTree(list) {
  const kids = {};
  list.forEach((n) => { const k = n.parentId || "·root"; (kids[k] = kids[k] || []).push(n); });
  const out = [];
  const walk = (key) => { (kids[key] || []).forEach((n) => { out.push(n); walk(n.id); }); };
  walk("·root");
  list.forEach((n) => { if (!out.includes(n)) out.push(n); });
  return out;
}
function nodeEssence(n) {
  const s = [...n.messages].reverse().find((m) => m.tabs && m.tabs.summary);
  if (s) return s.tabs.summary;
  const a = n.messages.find((m) => m.role === "assistant" && !m.streaming && !m.relate);
  if (a && a.content) return a.content;
  return n.depth === 0 ? "" : "pending…";
}
const uid = () => "n" + ++_seq;

const ROOT = {
  id: "root", parentId: null, depth: 0, sourceQuote: null,
  loading: false, error: null, x: 40, y: 40, w: DEF_W, h: DEF_H, z: 10,
  messages: [],
};

export default function App() {
  const [nodes, setNodes] = useState([ROOT]);
  const [active, setActive] = useState("root");
  const [branchHint, setBranchHint] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [quotes, setQuotes] = useState({});   // per-node pending quote attached to the next question
  const [attachments, setAttachments] = useState({});   // per-node pending image attachments
  const interaction = useRef(null);   // {type, id, mx, my, x, y, w, h}
  const viewportRef = useRef(null);
  const panRef = useRef(null);        // { sx, sy, sl, st } while panning the canvas
  const fileInputRef = useRef(null);
  const firstSave = useRef(true);
  const [panning, setPanning] = useState(false);
  const [indexOpen, setIndexOpen] = useState(true);
  const [dark, setDark] = useState(() => { try { return localStorage.getItem("nc-canvas-theme") === "dark"; } catch { return false; } });
  // ---- user preferences ----
  const [showPrefs, setShowPrefs] = useState(false);
  // which answer tab opens first on a new reply
  const [defaultTab, setDefaultTab] = useState(() => { try { const v = localStorage.getItem("nc-canvas-default-tab"); return ["context", "summary", "sources", "action"].includes(v) ? v : "context"; } catch { return "context"; } });
  useEffect(() => { try { localStorage.setItem("nc-canvas-default-tab", defaultTab); } catch {} }, [defaultTab]);
  const [lanesLocked, setLanesLocked] = useState(() => { try { return localStorage.getItem("nc-canvas-lanes") === "1"; } catch { return false; } });
  useEffect(() => { try { localStorage.setItem("nc-canvas-lanes", lanesLocked ? "1" : "0"); } catch {} }, [lanesLocked]);
  const [showTutorial, setShowTutorial] = useState(false);
  const [interacting, setInteracting] = useState(false); // true during drag/resize; suspends position transitions
  const [overview, setOverview] = useState(false);       // topology overview mode
  const overviewRef = useRef(false);
  useEffect(() => { overviewRef.current = overview; }, [overview]);
  // In-app confirm dialog. window.confirm() is blocked in sandboxed preview iframes,
  // so all destructive actions route through this instead.
  const [confirmState, setConfirmState] = useState(null); // { title, message, okLabel, danger, onOk }
  const askConfirm = (opts) => setConfirmState({ okLabel: "OK", danger: false, ...opts });

  const [gatewayOnline, setGatewayOnline] = useState(null);
  const [gatewayIssue, setGatewayIssue] = useState(null);

  useEffect(() => {
    let disposed = false;
    let timer;
    const check = async () => {
      try {
        const res = await fetch("/api/gateway/status");
        const data = await res.json();
        if (!disposed) {
          setGatewayOnline(!!data.online);
          setGatewayIssue(data.reason || null);
        }
      } catch {
        if (!disposed) {
          setGatewayOnline(false);
          setGatewayIssue("gateway-unreachable");
        }
      }
      if (!disposed) timer = window.setTimeout(check, 15000);
    };
    check();
    return () => { disposed = true; window.clearTimeout(timer); };
  }, []);

  const zc = useRef(10);
  const laneRefs = useRef({});
  const hintRef = useRef(null);

  const [sel, setSel] = useState([]);            // multi-selection (node ids)
  const [synthSeenHint, setSynthSeenHint] = useState(() => { try { return localStorage.getItem("nc-canvas-synth-seen") === "1"; } catch { return true; } });
  const [zoom, setZoom] = useState(1);
  const [marquee, setMarquee] = useState(null);  // {x0,y0,x1,y1} world coords while rubber-band selecting
  const [guides, setGuides] = useState([]);      // alignment guide lines while dragging
  const selRef = useRef([]);
  const nodesRef = useRef([ROOT]);
  const zoomRef = useRef(1);
  const pastRef = useRef([]);
  const futureRef = useRef([]);
  const zoomAnchor = useRef(null);
  const pendingFit = useRef(null);
  const marqueeRef = useRef(null);
  const viewRestored = useRef(false);
  const viewReady = useRef(false);
  useEffect(() => { nodesRef.current = nodes; });
  useEffect(() => { selRef.current = sel; }, [sel]);

  const patch = useCallback((id, p) => {
    setNodes((ns) => ns.map((n) => (n.id === id ? { ...n, ...(typeof p === "function" ? p(n) : p) } : n)));
  }, []);
  const append = useCallback((id, msg) => {
    setNodes((ns) => ns.map((n) => (n.id === id ? { ...n, messages: [...n.messages, msg] } : n)));
  }, []);

  const bringFront = (id) => { zc.current += 1; patch(id, { z: zc.current }); setActive(id); };

  // ---- undo / redo (snapshots of the nodes array; layout-only churn is excluded) ----
  const commit = useCallback(() => { pastRef.current.push(nodesRef.current); if (pastRef.current.length > 120) pastRef.current.shift(); futureRef.current = []; }, []);
  const undo = useCallback(() => { if (!pastRef.current.length) return; futureRef.current.push(nodesRef.current); setNodes(pastRef.current.pop()); }, []);
  const redo = useCallback(() => { if (!futureRef.current.length) return; pastRef.current.push(nodesRef.current); setNodes(futureRef.current.pop()); }, []);

  // Apply tidy positions: one shot on the tidy button, or automatic in lanes locked mode.
  const applyTidy = useCallback((shouldCommit = true) => {
    if (shouldCommit) { commit(); setTiled(false); }   // Tidy is a re-layout; release the tiled lock
    setNodes((ns) => {
      const positions = computeTidyLayout(ns);
      let changed = false;
      const next = ns.map((n) => {
        const p = positions.get(n.id);
        if (!p) return n;
        if (Math.abs(n.x - p.x) < 0.5 && Math.abs(n.y - p.y) < 0.5) return n;
        changed = true;
        return { ...n, x: p.x, y: p.y };
      });
      return changed ? next : ns;
    });
  }, [commit]);

  // structural fingerprint: triggers auto tidy when locked and the shape changes
  const structureSig = nodes.map((n) => `${n.id}:${n.parentId || ""}:${n.h}:${n.w}:${n.min ? 1 : 0}:${n.closed ? 1 : 0}`).join("|");
  useEffect(() => { if (lanesLocked) applyTidy(false); }, [structureSig, lanesLocked, applyTidy]);

  // Tiled = scroll-locked "fill the canvas" view. While on, the outer canvas can't pan/scroll
  // (only content inside each window scrolls); it auto-releases on any deliberate re-layout.
  const [tiled, setTiled] = useState(false);

  // Tile every open window edge-to-edge to fully fill the visible canvas at 100% zoom —
  // Windows-11-snap style. A balanced grid (fuller rows on top), each row spanning the full
  // width with no gaps; the whole tiling is sized to and scrolled under the current viewport.
  const tileAll = useCallback(() => {
    const openNodes = orderTree(nodesRef.current).filter((n) => !n.closed);
    const N = openNodes.length;
    if (!N) return;
    commit();
    setLanesLocked(false);   // tiling is an explicit manual layout; the lanes lock would auto-tidy over it
    const vp = viewportRef.current;
    const r = vp ? vp.getBoundingClientRect() : { width: 1280, height: 800 };
    const PAD = 20, G = 14, OX = 40, OY = 40;          // screen margin, inter-tile gap, world origin
    const W = Math.max(320, r.width - PAD * 2);        // fill the viewport at zoom 1
    const H = Math.max(320, r.height - PAD * 2);
    const cols = Math.ceil(Math.sqrt(N));
    const rows = Math.ceil(N / cols);
    const base = Math.floor(N / rows), extra = N % rows;   // put the fuller rows first
    const cellH = (H - G * (rows - 1)) / rows;
    const pos = new Map();
    let idx = 0;
    for (let rIdx = 0; rIdx < rows; rIdx++) {
      const k = base + (rIdx < extra ? 1 : 0);         // windows in this row
      const cellW = (W - G * (k - 1)) / k;
      const y = OY + rIdx * (cellH + G);
      for (let c = 0; c < k; c++) {
        const x = OX + c * (cellW + G);
        pos.set(openNodes[idx++].id, { x: Math.round(x), y: Math.round(y), w: Math.round(cellW), h: Math.round(cellH) });
      }
    }
    setNodes((ns) => ns.map((n) => { const p = pos.get(n.id); return p ? { ...n, ...p, min: false, manual: true } : n; }));
    setZoom(1);
    setTiled(true);   // lock outer canvas scrolling until the user re-lays-out
    // land the viewport on the tiled region (rAF so worldW/H have grown to the new layout).
    // Done imperatively rather than via pendingFit because setZoom(1) is a no-op when already 100%.
    requestAnimationFrame(() => { const v = viewportRef.current; if (v) { v.scrollLeft = OX - PAD; v.scrollTop = OY - PAD; } });
  }, [commit]);

  // Release the scroll lock as soon as the open-window set changes (a window opened/closed/added):
  // the tiling no longer fills the canvas and any off-screen window must stay reachable.
  const openWinCount = nodes.filter((n) => !n.closed).length;
  const tiledCountRef = useRef(openWinCount);
  useEffect(() => {
    if (tiled && openWinCount !== tiledCountRef.current) setTiled(false);
    tiledCountRef.current = openWinCount;
  }, [openWinCount, tiled]);


  // screen point -> world point (accounts for pan scroll and zoom)
  const toWorld = (clientX, clientY) => {
    const vp = viewportRef.current; if (!vp) return { x: 0, y: 0 };
    const r = vp.getBoundingClientRect(), z = zoomRef.current;
    return { x: (clientX - r.left + vp.scrollLeft) / z, y: (clientY - r.top + vp.scrollTop) / z };
  };

  // snap a dragged box's edges/centers to nearby nodes; returns adjusted pos + guide lines
  const SNAP = 6;
  const snap = (id, x, y, w, h) => {
    const others = nodesRef.current.filter((n) => !n.closed && n.id !== id);
    const myX = [x, x + w / 2, x + w], myY = [y, y + h / 2, y + h];
    let dX = SNAP + 1, dY = SNAP + 1, offX = 0, offY = 0, gx = null, gy = null;
    others.forEach((o) => {
      const oh = o.min ? COLLAPSED_H : o.h;
      [o.x, o.x + o.w / 2, o.x + o.w].forEach((ox) => myX.forEach((mx) => { const d = Math.abs(mx - ox); if (d < dX) { dX = d; offX = ox - mx; gx = ox; } }));
      [o.y, o.y + oh / 2, o.y + oh].forEach((oy) => myY.forEach((my) => { const d = Math.abs(my - oy); if (d < dY) { dY = d; offY = oy - my; gy = oy; } }));
    });
    const g = [];
    if (dX <= SNAP) g.push({ x: gx });
    if (dY <= SNAP) g.push({ y: gy });
    return { x: dX <= SNAP ? x + offX : x, y: dY <= SNAP ? y + offY : y, guides: g };
  };

  const selectNode = (n, e) => {
    bringFront(n.id);
    if (e && e.shiftKey) setSel((s) => (s.includes(n.id) ? s.filter((x) => x !== n.id) : [...s, n.id]));
    else setSel([n.id]);
  };

  const closeMany = (ids) => {
    const set = new Set();
    ids.forEach((id) => subtree(id).forEach((x) => set.add(x)));
    setNodes((ns) => ns.map((n) => (set.has(n.id) ? { ...n, closed: true } : n)));
    setSel([]);
    if (set.has(active)) { const o = nodesRef.current.find((n) => !set.has(n.id) && !n.closed); setActive(o ? o.id : null); }
  };

  // ---- zoom controls ----
  const setZoomAt = (z1) => {
    setTiled(false);   // zooming breaks the exact-fill tiling, so release the lock
    const vp = viewportRef.current;
    z1 = Math.min(2.5, Math.max(0.3, z1));
    if (vp) { const r = vp.getBoundingClientRect(), cx = r.width / 2, cy = r.height / 2, z0 = zoomRef.current; zoomAnchor.current = { wx: (cx + vp.scrollLeft) / z0, wy: (cy + vp.scrollTop) / z0, cx, cy }; }
    setZoom(z1);
  };
  const fitView = (ids) => {
    setTiled(false);   // fitting changes zoom/scroll, so release the tiled lock
    const vp = viewportRef.current; if (!vp) return;
    const list = nodesRef.current.filter((n) => !n.closed && (!ids || ids.includes(n.id)));
    if (!list.length) return;
    const minX = Math.min(...list.map((n) => n.x)), minY = Math.min(...list.map((n) => n.y));
    const maxX = Math.max(...list.map((n) => n.x + n.w)), maxY = Math.max(...list.map((n) => n.y + (n.min ? COLLAPSED_H : n.h)));
    const pad = 60, r = vp.getBoundingClientRect();
    let z1 = Math.min(r.width / ((maxX - minX) + pad * 2), r.height / ((maxY - minY) + pad * 2));
    if (ids && ids.length === 1) z1 = Math.min(1, z1);
    z1 = Math.min(2.5, Math.max(0.3, z1));
    pendingFit.current = { x: minX - pad, y: minY - pad };
    setZoom(z1);
  };
  const saveView = useCallback(() => { if (!viewReady.current) return; const vp = viewportRef.current; if (!vp) return; try { localStorage.setItem("nc-canvas-view", JSON.stringify({ zoom: zoomRef.current, left: vp.scrollLeft, top: vp.scrollTop })); } catch {} }, []);

  // keep scroll fixed under the zoom anchor (cursor or viewport center), or land a fit
  useLayoutEffect(() => {
    zoomRef.current = zoom;
    const vp = viewportRef.current; if (!vp) return;
    if (pendingFit.current) { vp.scrollLeft = pendingFit.current.x * zoom; vp.scrollTop = pendingFit.current.y * zoom; pendingFit.current = null; }
    else if (zoomAnchor.current) { const a = zoomAnchor.current; vp.scrollLeft = a.wx * zoom - a.cx; vp.scrollTop = a.wy * zoom - a.cy; zoomAnchor.current = null; }
    saveView();
  }, [zoom, saveView]);

  // global pointer handling for drag + resize + marquee
  useEffect(() => {
    const move = (e) => {
      const z = zoomRef.current;
      if (panRef.current) {
        const vp = viewportRef.current;
        if (vp) { vp.scrollLeft = panRef.current.sl - (e.clientX - panRef.current.sx); vp.scrollTop = panRef.current.st - (e.clientY - panRef.current.sy); }
        return;
      }
      if (marqueeRef.current) {
        const w = toWorld(e.clientX, e.clientY);
        marqueeRef.current = { ...marqueeRef.current, x1: w.x, y1: w.y };
        setMarquee(marqueeRef.current);
        return;
      }
      const it = interaction.current; if (!it) return;
      if (it.type === "drag") {
        const dx = (e.clientX - it.mx) / z, dy = (e.clientY - it.my) / z;
        if (it.group) {
          setNodes((ns) => ns.map((n) => { const g = it.group[n.id]; return g ? { ...n, x: g.x + dx, y: g.y + dy } : n; }));
        } else {
          const s = snap(it.id, it.x + dx, it.y + dy, it.w, it.h);
          setGuides(s.guides);
          patch(it.id, { x: s.x, y: s.y });
        }
      } else {
        patch(it.id, { w: Math.max(MIN_W, it.w + (e.clientX - it.mx) / z), h: Math.max(MIN_H, it.h + (e.clientY - it.my) / z) });
      }
    };
    const up = () => {
      if (marqueeRef.current) {
        const m = marqueeRef.current; marqueeRef.current = null; setMarquee(null);
        const x0 = Math.min(m.x0, m.x1), x1 = Math.max(m.x0, m.x1), y0 = Math.min(m.y0, m.y1), y1 = Math.max(m.y0, m.y1);
        const hit = nodesRef.current.filter((n) => !n.closed && n.x < x1 && n.x + n.w > x0 && n.y < y1 && n.y + (n.min ? COLLAPSED_H : n.h) > y0).map((n) => n.id);
        setSel(hit); if (hit.length) setActive(hit[hit.length - 1]);
      }
      interaction.current = null; panRef.current = null; setPanning(false); setGuides([]); setInteracting(false); document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
  }, [patch]);

  const startDrag = (e, n) => {
    if (lanesLocked) { e.preventDefault(); bringFront(n.id); return; } // drag disabled in lock mode
    e.preventDefault(); e.stopPropagation();
    setTiled(false);   // rearranging by hand releases the tiled scroll lock
    commit(); bringFront(n.id);
    let s = selRef.current;
    if (e.shiftKey) { s = s.includes(n.id) ? s.filter((x) => x !== n.id) : [...s, n.id]; setSel(s); }
    else if (!s.includes(n.id)) { s = [n.id]; setSel(s); }
    const group = s.length > 1 && s.includes(n.id)
      ? Object.fromEntries(nodesRef.current.filter((m) => s.includes(m.id)).map((m) => [m.id, { x: m.x, y: m.y }]))
      : null;
    interaction.current = { type: "drag", id: n.id, mx: e.clientX, my: e.clientY, x: n.x, y: n.y, w: n.w, h: n.min ? COLLAPSED_H : n.h, group };
    setInteracting(true);
    document.body.style.userSelect = "none";
  };
  const startResize = (e, n) => { e.preventDefault(); e.stopPropagation(); setTiled(false); commit(); bringFront(n.id); patch(n.id, { manual: true }); interaction.current = { type: "resize", id: n.id, mx: e.clientX, my: e.clientY, w: n.w, h: n.h }; setInteracting(true); document.body.style.userSelect = "none"; };

  const startPan = (e) => {
    if (e.target !== e.currentTarget) return; // only the bare canvas, not a lane
    if (e.shiftKey) { // shift+drag the background = rubber-band select
      const w = toWorld(e.clientX, e.clientY);
      marqueeRef.current = { x0: w.x, y0: w.y, x1: w.x, y1: w.y };
      setMarquee(marqueeRef.current);
      document.body.style.userSelect = "none";
      return;
    }
    setSel([]);
    if (tiled) return;   // outer canvas pan/scroll is locked in tiled mode
    const vp = viewportRef.current; if (!vp) return;
    panRef.current = { sx: e.clientX, sy: e.clientY, sl: vp.scrollLeft, st: vp.scrollTop };
    setPanning(true);
    document.body.style.userSelect = "none";
  };

  // ctrl/cmd + wheel (and trackpad pinch) = zoom centered on the cursor; plain wheel pans natively
  useEffect(() => {
    const vp = viewportRef.current; if (!vp) return;
    const onWheel = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      setTiled(false);   // pinch/ctrl-wheel zoom releases the tiled scroll lock
      const r = vp.getBoundingClientRect(), z0 = zoomRef.current;
      const z1 = Math.min(2.5, Math.max(0.3, z0 * Math.exp(-e.deltaY * 0.0015)));
      if (z1 === z0) return;
      const cx = e.clientX - r.left, cy = e.clientY - r.top;
      zoomAnchor.current = { wx: (cx + vp.scrollLeft) / z0, wy: (cy + vp.scrollTop) / z0, cx, cy };
      setZoom(z1);
    };
    const onScroll = () => { if (vp._t) cancelAnimationFrame(vp._t); vp._t = requestAnimationFrame(saveView); };
    vp.addEventListener("wheel", onWheel, { passive: false });
    vp.addEventListener("scroll", onScroll, { passive: true });
    return () => { vp.removeEventListener("wheel", onWheel); vp.removeEventListener("scroll", onScroll); };
  }, [saveView]);

  // restore the saved viewport (zoom + pan) once, after first paint
  useEffect(() => {
    if (viewRestored.current) return; viewRestored.current = true;
    let v = null; try { v = JSON.parse(localStorage.getItem("nc-canvas-view") || "null"); } catch {}
    if (v) {
      setZoom(v.zoom || 1);
      requestAnimationFrame(() => { const vp = viewportRef.current; if (vp) { vp.scrollLeft = v.left || 0; vp.scrollTop = v.top || 0; } viewReady.current = true; });
    } else { viewReady.current = true; }
  }, []);

  // keyboard layer: undo/redo, delete, select all, escape, nudge, fit
  useEffect(() => {
    const onKey = (e) => {
      const t = e.target, typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
      const mod = e.metaKey || e.ctrlKey;
      if (mod && (e.key === "z" || e.key === "Z")) { if (typing) return; e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
      if (mod && (e.key === "y" || e.key === "Y")) { if (typing) return; e.preventDefault(); redo(); return; }
      if (mod && (e.key === "a" || e.key === "A")) { if (typing) return; e.preventDefault(); setSel(nodesRef.current.filter((n) => !n.closed).map((n) => n.id)); return; }
      if (mod && (e.key === "j" || e.key === "J")) { if (typing) return; e.preventDefault(); if (selRef.current.length >= 2) createSynthesis(selRef.current); return; }
      if (mod && (e.key === "n" || e.key === "N")) { if (typing) return; e.preventDefault(); newMainThread(); return; }
      if (typing) return;
      if (e.key === "Escape") { if (overviewRef.current) { setOverview(false); return; } setSel([]); setBranchHint(null); return; }
      if (e.key === "o" || e.key === "O") { if (typing) return; e.preventDefault(); setOverview((v) => !v); return; }
      if (e.key === "Delete" || e.key === "Backspace") { const ids = selRef.current.length ? selRef.current : (active ? [active] : []); if (ids.length) { e.preventDefault(); commit(); closeMany(ids); } return; }
      if (e.key === "f" || e.key === "F") { if (active) fitView([active]); return; }
      if (e.key === "t" || e.key === "T") { e.preventDefault(); tileAll(); return; }
      if (e.key.indexOf("Arrow") === 0) {
        const ids = selRef.current.length ? selRef.current : (active ? [active] : []); if (!ids.length) return;
        e.preventDefault();
        const step = e.shiftKey ? 10 : 1;
        const dx = e.key === "ArrowLeft" ? -step : e.key === "ArrowRight" ? step : 0;
        const dy = e.key === "ArrowUp" ? -step : e.key === "ArrowDown" ? step : 0;
        commit();
        setNodes((ns) => ns.map((n) => (ids.includes(n.id) ? { ...n, x: n.x + dx, y: n.y + dy } : n)));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo, active, commit, tileAll]);

  const focusNode = (id) => {
    const n = nodes.find((x) => x.id === id);
    if (n && n.closed) reopenNode(id);
    bringFront(id); setSel([id]);
    setTimeout(() => laneRefs.current[id]?.scrollIntoView({ behavior: "smooth", inline: "center", block: "center" }), 0);
  };

  // Jump to a specific main thread from the sidebar; opens its session first if it isn't current.
  const pendingFocusRef = useRef(null);
  const openThread = (sessId, threadId) => {
    if (currentSession && currentSession.id === sessId) { focusNode(threadId); return; }
    pendingFocusRef.current = threadId;
    openSession(sessId);
  };
  // once the just-opened session's nodes are in place, focus the requested thread
  useEffect(() => {
    const id = pendingFocusRef.current;
    if (id && nodes.some((n) => n.id === id)) { pendingFocusRef.current = null; setTimeout(() => focusNode(id), 40); }
  }, [nodes]); // eslint-disable-line

  // x-overlap between two boxes; we treat two siblings as "in the same column" when their
  // horizontal ranges intersect by at least half the narrower one. Lets us auto-shift stacked
  // branches without dragging unrelated windows around.
  const colOverlap = (a, b) => {
    const ov = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
    return ov >= Math.min(a.w, b.w) * 0.5;
  };

  const toggleMin = (id) => {
    const me = nodesRef.current.find((n) => n.id === id);
    if (!me) return;
    const next = !me.min;
    const oldEff = me.min ? COLLAPSED_H : me.h;
    const newEff = next ? COLLAPSED_H : me.h;
    const delta = newEff - oldEff;
    // toggle the node and all its descendants (keeps a deep subtree consistent)
    const set = new Set([id]);
    let grew = true;
    while (grew) { grew = false; nodesRef.current.forEach((n) => { if (n.parentId && set.has(n.parentId) && !set.has(n.id)) { set.add(n.id); grew = true; } }); }
    setNodes((ns) => ns.map((n) => {
      if (set.has(n.id)) return { ...n, min: next };
      if (!n.closed && n.parentId === me.parentId && n.y > me.y && colOverlap(me, n)) return { ...n, y: n.y + delta };
      return n;
    }));
  };

  // Bulk expand walks top-to-bottom and pushes each subsequent sibling down by the previous
  // one's growth, so opening all three at once still lays them out without overlap.
  const toggleChildren = (id) => {
    const kids = nodes.filter((n) => n.parentId === id && !n.closed);
    if (!kids.length) return;
    const anyCollapsed = kids.some((k) => k.min);
    if (!anyCollapsed) { // collapse all in place; don't touch positions
      const ids = new Set(kids.map((k) => k.id));
      setNodes((ns) => ns.map((n) => (ids.has(n.id) ? { ...n, min: true } : n)));
      return;
    }
    setNodes((ns) => {
      const next = ns.map((n) => ({ ...n }));
      const byId = Object.fromEntries(next.map((n) => [n.id, n]));
      const order = kids.filter((k) => k.min).sort((a, b) => a.y - b.y).map((k) => k.id);
      order.forEach((kid) => {
        const node = byId[kid]; if (!node) return;
        const delta = node.h - COLLAPSED_H;
        node.min = false;
        next.forEach((m) => {
          if (m.id === kid || m.closed || m.parentId !== node.parentId) return;
          if (m.y > node.y && colOverlap(node, m)) m.y += delta;
        });
      });
      return next;
    });
  };

  // Autofit handler: only push siblings on growth. Shrink is silent so it does not jerk
  // the column while content streams in.
  const setHeightAndPush = (id, h) => {
    setNodes((ns) => {
      const me = ns.find((n) => n.id === id);
      if (!me || me.h === h) return ns;
      const delta = h - me.h;
      return ns.map((n) => {
        if (n.id === id) return { ...n, h };
        if (delta > 0 && !n.closed && !me.min && n.parentId === me.parentId && n.y > me.y && colOverlap(me, n)) return { ...n, y: n.y + delta };
        return n;
      });
    });
  };

  // collect a node id plus all its descendants
  const subtree = (id) => {
    const set = new Set([id]);
    let grew = true;
    while (grew) { grew = false; nodesRef.current.forEach((n) => { if (n.parentId && set.has(n.parentId) && !set.has(n.id)) { set.add(n.id); grew = true; } }); }
    return set;
  };

  // close = remove from the canvas only; the node stays in the sidebar and can be reopened
  const closeNode = (id) => {
    commit();
    const set = subtree(id);
    setNodes((ns) => ns.map((n) => (set.has(n.id) ? { ...n, closed: true } : n)));
    if (set.has(active)) {
      const stillOpen = nodesRef.current.find((n) => !set.has(n.id) && !n.closed);
      setActive(stillOpen ? stillOpen.id : null);
    }
  };

  // reopen a node and its whole subtree, plus its ancestors so the path is coherent
  const reopenNode = (id) => {
    commit();
    const set = subtree(id);
    let cur = nodesRef.current.find((n) => n.id === id);
    cur = cur ? nodesRef.current.find((n) => n.id === cur.parentId) : null;
    while (cur) { set.add(cur.id); cur = nodesRef.current.find((n) => n.id === cur.parentId); }
    setNodes((ns) => ns.map((n) => (set.has(n.id) ? { ...n, closed: false } : n)));
  };

  // Permanent delete: remove the node and every descendant from state entirely.
  // Committed to the undo stack so ⌘Z can recover during this session; if the user
  // reloads or moves to another session, it's gone.
  const deleteNodeForever = (id) => {
    const target = nodesRef.current.find((n) => n.id === id);
    if (!target) return;
    const set = subtree(id);
    const desc = set.size - 1;
    const label = nodeTitle(target);
    const message = (desc === 0
      ? `Permanently delete "${label}"?`
      : `Permanently delete "${label}" and ${desc} descendant thread${desc === 1 ? "" : "s"}?`)
      + "\n\n⌘Z will undo this during the current session.";
    askConfirm({
      title: "Delete permanently?",
      message,
      okLabel: "Delete",
      danger: true,
      onOk: () => {
        commit();
        setNodes((ns) => ns.filter((n) => !set.has(n.id)));
        setSel((s) => s.filter((sid) => !set.has(sid)));
        if (set.has(active)) {
          const surviving = nodesRef.current.find((n) => !set.has(n.id));
          setActive(surviving ? surviving.id : null);
        }
      },
    });
  };

  const newMainThread = () => {
    commit();
    const id = uid();
    const vis = nodesRef.current.filter((n) => !n.closed);
    const y = vis.length ? Math.max(...vis.map((n) => n.y + n.h)) + GAP : 40;
    const x = vis.length ? Math.min(...vis.map((n) => n.x)) : 40;
    const node = { id, parentId: null, depth: 0, sourceQuote: null, loading: false, error: null, closed: false, x, y, w: DEF_W, h: DEF_H, z: (zc.current += 1), messages: [] };
    setNodes((ns) => [...ns, node]);
    setActive(id); setSel([id]);
    setTimeout(() => laneRefs.current[id]?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" }), 60);
  };

  const relateToOrigin = async (nodeId, quote) => {
    const chain = [];
    let cur = nodes.find((n) => n.id === nodeId);
    while (cur) { chain.unshift(cur); cur = nodes.find((n) => n.id === cur.parentId); }
    const ctx = chain.flatMap((n) => n.messages.filter((m) => !m.relate)).map((m) => ({ role: m.role, content: m.content }));
    const focus = quote ? ` Focus specifically on this point from the branch: "${quote}".` : "";
    const instruction = { role: "user", content: `Step back from the detail. The messages above began in the main thread and branched down into this tangent.${focus} In 2 to 4 sentences, explain plainly how this connects back to what was originally being investigated: what it clarified, confirmed, changed, or added, and name the concrete link. Do not restate the branch; bridge it to the origin.` };
    patch(nodeId, { loading: true, error: null });
    try {
      const text = await callLLM(toAPIMessages([...ctx, instruction]));
      append(nodeId, { role: "assistant", relate: true, content: text });
    } catch (e) { patch(nodeId, { error: String(e.message || e) }); }
    finally { patch(nodeId, { loading: false }); }
  };

  // --- local persistence (works in your offline build; the claude.ai preview sandboxes storage) ---
  const serialize = () => ({
    v: 1, active,
    nodes: nodes.map((n) => ({ ...n, loading: false, error: null, messages: n.messages.map((m) => (m.streaming ? { ...m, done: true } : m)) })),
  });

  const loadState = (obj) => {
    if (!obj || !Array.isArray(obj.nodes)) return;
    let mx = 0;
    obj.nodes.forEach((n) => { const m = /^n(\d+)$/.exec(n.id || ""); if (m) mx = Math.max(mx, +m[1]); });
    _seq = mx;
    let loaded = obj.nodes.map((n) => ({ ...n, loading: false, error: null }));
    // if every window in this session was closed, reopen its main threads so the canvas isn't
    // blank (otherwise the chat shows "no threads open" with no way to bring them back)
    if (loaded.length && loaded.every((n) => n.closed)) loaded = loaded.map((n) => (n.depth === 0 ? { ...n, closed: false } : n));
    setNodes(loaded);
    const firstOpen = loaded.find((n) => !n.closed);
    setActive(obj.active && loaded.some((n) => n.id === obj.active && !n.closed) ? obj.active : (firstOpen ? firstOpen.id : null));
  };

  const saveToFile = () => {
    try {
      const blob = new Blob([JSON.stringify(serialize(), null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "netclaw-canvas.json";
      a.target = "_blank";   // keep a sandboxed preview from navigating the app away
      a.rel = "noopener";
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { /* download blocked in sandbox; localStorage still persists in your build */ }
  };

  const openFile = (e) => {
    const f = e.target.files && e.target.files[0]; if (!f) return;
    const reader = new FileReader();
    reader.onload = () => { try { loadState(JSON.parse(String(reader.result))); } catch {} };
    reader.readAsText(f);
    e.target.value = "";
  };

  // ---- session persistence (IndexedDB) ----
  const [currentSession, setCurrentSession] = useState(null); // { id, createdAt }
  const [showSessions, setShowSessions] = useState(false);
  const [sessionList, setSessionList] = useState([]);
  const [sessSearch, setSessSearch] = useState("");
  const saveTimerRef = useRef(null);

  // ---- projects / folders for organizing sessions ----
  // Folder metadata and the session→folder mapping live in localStorage, so the
  // IndexedDB session records themselves stay untouched. A session with no entry
  // in sessionFolder (or one pointing at a deleted folder) is treated as "Unfiled".
  const [folders, setFolders] = useState(() => { try { const j = JSON.parse(localStorage.getItem("nc-canvas-folders") || "null"); return Array.isArray(j) ? j : []; } catch { return []; } });
  const [sessionFolder, setSessionFolder] = useState(() => { try { const j = JSON.parse(localStorage.getItem("nc-canvas-session-folder") || "null"); return j && typeof j === "object" ? j : {}; } catch { return {}; } });
  const [collapsedFolders, setCollapsedFolders] = useState({}); // ui-only
  const [renamingFolder, setRenamingFolder] = useState(null);   // folder id being renamed
  const [renamingSession, setRenamingSession] = useState(null); // session id being renamed
  const [renamingThread, setRenamingThread] = useState(null);   // main-thread node id being renamed
  const [dropTarget, setDropTarget] = useState(null);           // folder id (or "__unfiled") hovered during drag
  const [dragSessId, setDragSessId] = useState(null);           // session id being dragged
  // custom chat names. Session titles otherwise auto-derive from the first message on
  // every save, so a user rename is stored separately here to survive autosave.
  const [sessionTitles, setSessionTitles] = useState(() => { try { const j = JSON.parse(localStorage.getItem("nc-canvas-session-titles") || "null"); return j && typeof j === "object" ? j : {}; } catch { return {}; } });
  useEffect(() => { try { localStorage.setItem("nc-canvas-folders", JSON.stringify(folders)); } catch {} }, [folders]);
  useEffect(() => { try { localStorage.setItem("nc-canvas-session-folder", JSON.stringify(sessionFolder)); } catch {} }, [sessionFolder]);
  useEffect(() => { try { localStorage.setItem("nc-canvas-session-titles", JSON.stringify(sessionTitles)); } catch {} }, [sessionTitles]);
  // display name for a session: custom rename wins, else the derived title, else a placeholder
  const sessTitle = (s) => sessionTitles[s.id] || s.title || "(untitled)";
  const renameSession = (id, name) => setSessionTitles((m) => { const out = { ...m }; const v = (name || "").trim(); if (v) out[id] = v; else delete out[id]; return out; });
  // rename a specific main thread (stored on the node itself; empty reverts to the derived title)
  const renameThread = (sessionId, nodeId, name) => {
    const val = (name || "").trim() || undefined;
    if (currentSession && currentSession.id === sessionId) { patch(nodeId, { title: val }); return; }
    setSessionList((ls) => ls.map((s) => (s.id === sessionId ? { ...s, nodes: (s.nodes || []).map((n) => (n.id === nodeId ? { ...n, title: val } : n)) } : s)));
    idb.get(sessionId).then((sess) => { if (sess) idb.put({ ...sess, nodes: (sess.nodes || []).map((n) => (n.id === nodeId ? { ...n, title: val } : n)) }); }).catch(() => {});
  };
  // Safety net: a mousedown anywhere outside an open rename field commits and closes it, so the
  // rename caret can never linger in the sidebar — even when the click lands on something that
  // suppresses the input's own blur (window headers, menus, etc. call preventDefault on mousedown).
  useEffect(() => {
    if (renamingSession == null && renamingFolder == null && renamingThread == null) return;
    const onDown = (e) => {
      const inp = document.querySelector("input[data-rename]");
      if (inp && e.target === inp) return;   // still interacting with the field
      if (inp) {
        const kind = inp.getAttribute("data-rename"), id = inp.getAttribute("data-id"), val = inp.value;
        if (kind === "session") renameSession(id, val);
        else if (kind === "folder") { const v = (val || "").trim(); if (v) renameFolder(id, v); }
        else if (kind === "thread") renameThread(inp.getAttribute("data-sess"), id, val);
      }
      setRenamingSession(null); setRenamingFolder(null); setRenamingThread(null);
    };
    const tid = setTimeout(() => document.addEventListener("mousedown", onDown, true), 0);
    return () => { clearTimeout(tid); document.removeEventListener("mousedown", onDown, true); };
  }, [renamingSession, renamingFolder, renamingThread]); // eslint-disable-line
  const [chatQuery, setChatQuery] = useState("");

  const createFolder = () => {
    const id = "fld-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    setFolders((fs) => [...fs, { id, name: "New folder", createdAt: Date.now() }]);
    setCollapsedFolders((c) => ({ ...c, [id]: false }));
    setRenamingFolder(id);
  };
  const renameFolder = (id, name) => setFolders((fs) => fs.map((f) => (f.id === id ? { ...f, name } : f)));
  const removeFolder = (id) => {
    setFolders((fs) => fs.filter((f) => f.id !== id));
    // unfile its sessions rather than deleting them
    setSessionFolder((m) => { const out = { ...m }; Object.keys(out).forEach((sid) => { if (out[sid] === id) delete out[sid]; }); return out; });
    if (renamingFolder === id) setRenamingFolder(null);
  };
  const assignSession = (sessId, folderId) => setSessionFolder((m) => {
    const out = { ...m };
    if (folderId) out[sessId] = folderId; else delete out[sessId];
    return out;
  });

  const reloadSessionList = useCallback(async () => {
    try { const all = await idb.list(); all.sort((a, b) => b.updatedAt - a.updatedAt); setSessionList(all); } catch {}
  }, []);

  // mount: open DB, migrate legacy localStorage, load newest session or seed an empty one
  useEffect(() => {
    (async () => {
      try {
        let all = []; try { all = await idb.list(); } catch {}
        if (!all.length) {
          let legacy = null;
          try { const raw = localStorage.getItem(STORE_KEY); if (raw) legacy = JSON.parse(raw); } catch {}
          if (legacy && Array.isArray(legacy.nodes) && legacy.nodes.length) {
            const id = sessId();
            const now = Date.now();
            const sess = { id, title: deriveSessionTitle(legacy.nodes), createdAt: now, updatedAt: now, nodes: legacy.nodes, active: legacy.active };
            try { await idb.put(sess); localStorage.removeItem(STORE_KEY); } catch {}
            setCurrentSession({ id, createdAt: now });
            loadState(legacy);
            firstSave.current = true;
            await reloadSessionList();
            return;
          }
          // first-time user: create a fresh session record so subsequent saves have a target
          const id = sessId(); const now = Date.now();
          setCurrentSession({ id, createdAt: now });
          await reloadSessionList();
          return;
        }
        const newest = all.reduce((a, b) => (a.updatedAt > b.updatedAt ? a : b));
        setCurrentSession({ id: newest.id, createdAt: newest.createdAt });
        loadState({ nodes: newest.nodes, active: newest.active });
        firstSave.current = true;
        setSessionList(all);
      } catch (e) { console.warn("session init failed", e); }
    })();
  }, []); // eslint-disable-line

  // debounced autosave on any nodes/active change
  useEffect(() => {
    if (firstSave.current) { firstSave.current = false; return; }
    if (!currentSession) return;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      const data = serialize();
      const now = Date.now();
      idb.put({ id: currentSession.id, title: deriveSessionTitle(data.nodes), createdAt: currentSession.createdAt, updatedAt: now, nodes: data.nodes, active: data.active })
        .then(() => setSessionList((ls) => { const others = ls.filter((s) => s.id !== currentSession.id); return [{ id: currentSession.id, title: deriveSessionTitle(data.nodes), createdAt: currentSession.createdAt, updatedAt: now, nodes: data.nodes, active: data.active }, ...others]; }))
        .catch(() => {});
    }, 400);
  }, [nodes, active, currentSession]); // eslint-disable-line

  const newSession = async () => {
    // flush any pending save of the current session first
    if (saveTimerRef.current) { clearTimeout(saveTimerRef.current); saveTimerRef.current = null; }
    if (currentSession) {
      const data = serialize();
      try { await idb.put({ id: currentSession.id, title: deriveSessionTitle(data.nodes), createdAt: currentSession.createdAt, updatedAt: Date.now(), nodes: data.nodes, active: data.active }); } catch {}
    }
    const id = sessId(); const now = Date.now();
    setCurrentSession({ id, createdAt: now });
    pastRef.current = []; futureRef.current = [];
    _seq = 0;
    setNodes([{ ...ROOT, messages: [] }]);
    setActive("root");
    setSel([]);
    firstSave.current = true;
    setShowSessions(false);
    reloadSessionList();
  };

  const openSession = async (id) => {
    if (saveTimerRef.current) { clearTimeout(saveTimerRef.current); saveTimerRef.current = null; }
    if (currentSession) {
      const data = serialize();
      try { await idb.put({ id: currentSession.id, title: deriveSessionTitle(data.nodes), createdAt: currentSession.createdAt, updatedAt: Date.now(), nodes: data.nodes, active: data.active }); } catch {}
    }
    try {
      const sess = await idb.get(id); if (!sess) return;
      setCurrentSession({ id: sess.id, createdAt: sess.createdAt });
      pastRef.current = []; futureRef.current = [];
      loadState({ nodes: sess.nodes, active: sess.active });
      firstSave.current = true;
      setShowSessions(false);
      reloadSessionList();
    } catch {}
  };

  const deleteSession = async (id) => {
    try { await idb.del(id); } catch {}
    setSessionFolder((m) => { if (!(id in m)) return m; const out = { ...m }; delete out[id]; return out; });
    setSessionTitles((m) => { if (!(id in m)) return m; const out = { ...m }; delete out[id]; return out; });
    if (currentSession && currentSession.id === id) await newSession();
    else reloadSessionList();
  };

  useEffect(() => { try { localStorage.setItem("nc-canvas-theme", dark ? "dark" : "light"); } catch {} }, [dark]);

  // dismiss branch chip on outside click
  useEffect(() => {
    const h = (e) => { if (hintRef.current && !hintRef.current.contains(e.target)) setBranchHint(null); };
    document.addEventListener("mousedown", h, true);
    return () => document.removeEventListener("mousedown", h, true);
  }, []);

  const onSelect = (nodeId) => {
    const sel = window.getSelection();
    const text = sel && sel.toString().replace(/\s+/g, " ").trim();
    if (!text || text.length < 2) return;
    const r = sel.getRangeAt(0).getBoundingClientRect();
    setBranchHint({ nodeId, quote: text, x: r.left + r.width / 2, y: r.top - 8 });
  };

  async function run(nodeId, apiMessages) {
    patch(nodeId, { loading: true, error: null });
    try {
      const msgs = toAPIMessages(apiMessages);
      const last = msgs[msgs.length - 1];
      if (last && last.role === "user") last.content += "\n\n" + TAB_SYSTEM;
      else msgs.push({ role: "user", content: TAB_SYSTEM });

      // Tool selection and execution stay inside NetClaw/OpenClaw. The browser
      // contributes only this branch's conversation context and attachments.
      const raw = await callLLM(msgs);
      const tabs = parseTabs(raw);
      append(nodeId, tabs ? { role: "assistant", content: tabs.context, tabs } : { role: "assistant", content: raw });
    }
    catch (e) { patch(nodeId, { error: String(e.message || e) }); }
    finally { patch(nodeId, { loading: false }); }
  }

  function createBranch(parentId, quote) {
    commit();
    const parent = nodes.find((n) => n.id === parentId);
    const siblings = nodes.filter((n) => n.parentId === parentId).length;
    const id = uid();
    const node = {
      id, parentId, depth: parent.depth + 1, sourceQuote: quote, loading: false, error: null, min: true,
      x: parent.x + parent.w + GAP, y: parent.y + siblings * (COLLAPSED_H + 8),
      w: DEF_W, h: DEF_H, z: (zc.current += 1), messages: [],
    };
    setNodes((ns) => [...ns, node]);
    setActive(id);
    setBranchHint(null);
    window.getSelection()?.removeAllRanges();
    setTimeout(() => laneRefs.current[id]?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" }), 60);
  }

  // Attach the selected text to this node's composer as context for the next question in the thread.
  function quoteAsContext(nodeId, quote) {
    const q = String(quote || "").replace(/\s+/g, " ").trim();
    if (!q) return;
    setQuotes((qs) => ({ ...qs, [nodeId]: q }));
    setActive(nodeId);
    setBranchHint(null);
    window.getSelection()?.removeAllRanges();
    setTimeout(() => laneRefs.current[nodeId]?.querySelector('input[data-composer="1"]')?.focus(), 40);
  }
  const clearQuote = (nodeId) => setQuotes((qs) => { if (!(nodeId in qs)) return qs; const o = { ...qs }; delete o[nodeId]; return o; });

  // ---- pending attachments for the next question: images (vision) or text/data/code files ----
  const addFiles = async (nodeId, files) => {
    const items = [];
    for (const f of Array.from(files || [])) {
      if (!f) continue;
      if (String(f.type).startsWith("image/")) { try { items.push({ kind: "image", ...(await prepImage(f)) }); } catch {} }
      else if (isTextFile(f)) {
        try { let text = await readTextFile(f); const truncated = text.length > MAX_ATTACH_TEXT; if (truncated) text = text.slice(0, MAX_ATTACH_TEXT); items.push({ kind: "file", name: f.name || "file", text, ...(truncated ? { truncated: true } : {}) }); } catch {}
      }
      // other binary types are skipped
    }
    if (items.length) setAttachments((a) => ({ ...a, [nodeId]: [...(a[nodeId] || []), ...items] }));
  };
  const removeImage = (nodeId, idx) => setAttachments((a) => { const cur = a[nodeId] || []; const next = cur.filter((_, i) => i !== idx); const o = { ...a }; if (next.length) o[nodeId] = next; else delete o[nodeId]; return o; });
  const clearImages = (nodeId) => setAttachments((a) => { if (!(nodeId in a)) return a; const o = { ...a }; delete o[nodeId]; return o; });

  // Spawn a synthesis node that ingests N source threads at once. The new node sits to the
  // right of the rightmost source, vertically centered across the source span. Its messages
  // are empty; the API chain is composed from every source's chain when send() runs.
  function createSynthesis(sourceIds) {
    const sources = sourceIds.map((sid) => nodes.find((n) => n.id === sid)).filter(Boolean);
    if (sources.length < 2) return;
    commit();
    const maxDepth = Math.max(...sources.map((s) => s.depth));
    const rightEdge = Math.max(...sources.map((s) => s.x + s.w));
    const topEdge = Math.min(...sources.map((s) => s.y));
    const botEdge = Math.max(...sources.map((s) => s.y + (s.min ? COLLAPSED_H : s.h)));
    const id = uid();
    const node = {
      id, parentId: sources[0].id, synthFrom: sources.map((s) => s.id),
      depth: maxDepth + 1, sourceQuote: null, loading: false, error: null, min: false,
      x: rightEdge + GAP, y: Math.max(40, (topEdge + botEdge) / 2 - DEF_H / 2),
      w: DEF_W, h: DEF_H, z: (zc.current += 1), messages: [],
    };
    setNodes((ns) => [...ns, node]);
    setActive(id);
    setSel([]);
    try { localStorage.setItem("nc-canvas-synth-seen", "1"); } catch {}
    setSynthSeenHint(true);
    setTimeout(() => laneRefs.current[id]?.scrollIntoView({ behavior: "smooth", inline: "center", block: "center" }), 60);
  }

  // ancestor nodes (root .. parent), excluding the node itself
  const lineage = (nodeId) => {
    const chain = [];
    let cur = nodes.find((n) => n.id === nodeId);
    cur = cur ? nodes.find((n) => n.id === cur.parentId) : null;
    while (cur) { chain.unshift(cur); cur = nodes.find((n) => n.id === cur.parentId); }
    return chain;
  };

  // Compose the full API message chain for a synthesis node: walk each source's lineage
  // (root → source), prefix with a labeled separator, dedupe shared ancestors so we don't
  // double feed the trunk N times when sources share it.
  function synthChain(node) {
    const seen = new Set();
    const out = [];
    const sources = (node.synthFrom || []).map((sid) => nodes.find((n) => n.id === sid)).filter(Boolean);
    sources.forEach((s, i) => {
      const lineageNodes = [...lineage(s.id), s];
      const label = nodeTitle(s) || ("thread " + (i + 1));
      const fresh = lineageNodes.filter((n) => !seen.has(n.id));
      if (!fresh.length) return;
      out.push({ role: "user", content: `--- source ${i + 1} of ${sources.length}: ${label} ---` });
      fresh.forEach((n) => { seen.add(n.id); n.messages.filter((m) => !m.relate).forEach((m) => out.push(m)); });
    });
    out.push({ role: "user", content: `--- end of sources; now synthesize across all ${sources.length} above ---` });
    return out;
  }

  function send(nodeId) {
    const text = (drafts[nodeId] || "").trim();
    const items = attachments[nodeId] || [];
    const imgs = items.filter((it) => it.kind === "image").map(({ mediaType, data, name }) => ({ mediaType, data, name }));
    const files = items.filter((it) => it.kind === "file").map(({ name, text, truncated }) => ({ name, text, ...(truncated ? { truncated: true } : {}) }));
    if (!text && !imgs.length && !files.length) return;
    commit();
    const node = nodes.find((n) => n.id === nodeId);
    const quote = (quotes[nodeId] || "").trim();
    const msg = { role: "user", content: text, ...(quote ? { quote } : {}), ...(imgs.length ? { images: imgs } : {}), ...(files.length ? { files } : {}) };
    append(nodeId, msg);
    setDrafts((d) => ({ ...d, [nodeId]: "" }));
    if (quote) clearQuote(nodeId);
    if (items.length) clearImages(nodeId);
    bringFront(nodeId);
    // synthesis nodes feed the union of every source's full chain; branches walk the parent lineage
    const ctx = node.synthFrom ? synthChain(node) : lineage(nodeId).flatMap((n) => n.messages.filter((m) => !m.relate));
    run(nodeId, [...ctx, ...node.messages.filter((m) => !m.relate), msg]);
  }

  // breadcrumb path
  const path = []; { let cur = nodes.find((n) => n.id === active); while (cur) { path.unshift(cur); cur = nodes.find((n) => n.id === cur.parentId); } }

  // world extent (only nodes visible on the canvas)
  const open = nodes.filter((n) => !n.closed);
  const worldW = (open.length ? Math.max(...open.map((n) => n.x + n.w)) : 0) + 240;
  const worldH = (open.length ? Math.max(...open.map((n) => n.y + n.h)) : 0) + 240;

  // connector geometry: regular branches draw one arrow from parent; synthesis nodes draw one arrow per source, colored by the source's depth
  const eff = (n) => (n.min ? { ...n, h: COLLAPSED_H } : n);
  const connectors = [];
  nodes.filter((n) => !n.closed).forEach((c) => {
    const parentIds = c.synthFrom && c.synthFrom.length ? c.synthFrom : (c.parentId ? [c.parentId] : []);
    parentIds.forEach((pid, idx) => {
      const p = nodes.find((n) => n.id === pid);
      if (!p || p.closed) return;
      const obstacles = nodes.filter((n) => n.id !== c.id && n.id !== p.id && !n.closed).map(eff);
      const color = c.synthFrom ? depthColor(p.depth) : depthColor(c.depth);
      connectors.push({ id: c.id + "-p" + idx, d: orthPath(eff(p), eff(c), obstacles), color, synth: !!c.synthFrom });
    });
  });

  return (
    <div style={{ ...(dark ? DARK : LIGHT), height: "100dvh", minHeight: 480, display: "flex", flexDirection: "column", background: C.canvas, color: C.ink, fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif" }}>
      <style>{`@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
        @keyframes synthPulse{0%,100%{box-shadow:0 8px 22px rgba(0,0,0,0.3),0 0 0 0 rgba(27,42,74,0.55)}50%{box-shadow:0 8px 22px rgba(0,0,0,0.3),0 0 0 10px rgba(27,42,74,0)}}
        @keyframes laneIn{from{opacity:0;transform:scale(.94) translateY(8px)}to{opacity:1;transform:none}}
        @keyframes pathDraw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
        @keyframes connPulse{0%,100%{stroke-width:2.5}50%{stroke-width:5}}
        @keyframes fadeIn{from{opacity:0}to{opacity:1}}
        @keyframes dotIn{from{opacity:0;r:0}to{opacity:1}}
        .lane-in{animation:laneIn .28s cubic-bezier(.22,1,.36,1)}
        .conn{stroke-dasharray:1;stroke-dashoffset:0;animation:pathDraw .5s cubic-bezier(.22,1,.36,1)}
        .synthconn{stroke-dasharray:1;stroke-dashoffset:0;animation:pathDraw .5s cubic-bezier(.22,1,.36,1),connPulse 1.3s ease-in-out .5s 2}
        .ov-dot{cursor:pointer;transition:transform .15s ease-out}
        .ov-dot:hover{transform:scale(1.35)}
        .sb-row{position:relative}
        .sb-row .sb-act,.sb-row .sb-del{opacity:0;transition:opacity .12s,background .12s,color .12s}
        .sb-row:hover .sb-act,.sb-row:hover .sb-del{opacity:1}
        .sb-del:hover{background:#A8324E!important;color:#fff!important;border-color:#A8324E!important}
        @media(max-width:900px){.hud-back-label{display:none}}`}</style>

      {/* top bar */}
      <div style={{ flexShrink: 0, padding: "8px 14px", borderBottom: `1px solid ${C.hairline}`, background: C.canvas, display: "flex", alignItems: "center", gap: 10, zIndex: 100 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <a href="/" title="Return to the NetClaw Visual HUD"
            style={{ display: "flex", alignItems: "center", gap: 8, color: C.ink, textDecoration: "none" }}>
            <img src="/logos/netclaw.png" alt="NetClaw" style={{ height: 32, width: 32, objectFit: "contain", display: "block" }} />
            <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.05 }}>
              <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 11, fontWeight: 800, letterSpacing: 1.1 }}>NETCLAW CANVAS</span>
              <span style={{ color: C.muted, fontSize: 9.5, marginTop: 3 }}>branching workspace</span>
            </span>
          </a>
        </div>
        <a href="/" className="hud-back" aria-label="Back to NetClaw Visual HUD" title="Back to the normal NetClaw interface"
          style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 5, minWidth: 28, height: 28, padding: "0 7px", borderRadius: 7, border: `1px solid ${C.hairline}`, background: C.card, color: C.ink, textDecoration: "none", fontSize: 11, fontWeight: 700, flexShrink: 0 }}>
          <span aria-hidden="true">←</span>
          <span className="hud-back-label">Visual HUD</span>
        </a>

        {/* menu bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 0, flexShrink: 0 }}>
          <Menu label="File" items={[
            { type: "item", label: "New thread", shortcut: "⌘N", action: newMainThread },
            { type: "item", label: "Sessions…", action: () => { reloadSessionList(); setShowSessions(true); } },
            { type: "separator" },
            { type: "item", label: "Preferences…", action: () => setShowPrefs(true) },
          ]} />
          <Menu label="Edit" items={[
            { type: "item", label: "Undo", shortcut: "⌘Z", action: undo, disabled: !pastRef.current.length },
            { type: "item", label: "Redo", shortcut: "⇧⌘Z", action: redo, disabled: !futureRef.current.length },
            { type: "separator" },
            { type: "item", label: "Select all windows", shortcut: "⌘A", action: () => setSel(nodesRef.current.filter((n) => !n.closed).map((n) => n.id)) },
            { type: "item", label: "Clear selection", shortcut: "Esc", action: () => setSel([]), disabled: !sel.length },
            { type: "separator" },
            { type: "item", label: sel.length > 1 ? `Close ${sel.length} selected` : "Close active", shortcut: "Del", action: () => { const ids = sel.length ? sel : (active ? [active] : []); if (ids.length) { commit(); closeMany(ids); } }, disabled: !active && !sel.length },
          ]} />
          <Menu label="View" items={[
            { type: "item", label: "Overview", shortcut: "O", checked: overview, action: () => setOverview((v) => !v) },
            { type: "separator" },
            { type: "item", label: "Tidy", action: () => applyTidy(true) },
            { type: "item", label: "Tile (fill canvas)", shortcut: "T", action: () => tileAll() },
            { type: "item", label: "Lock to lanes", checked: lanesLocked, action: () => { commit(); setLanesLocked((v) => !v); } },
            { type: "separator" },
            { type: "item", label: "Branches sidebar", checked: indexOpen, action: () => setIndexOpen((o) => !o) },
            { type: "item", label: "Dark mode", checked: dark, action: () => setDark((d) => !d) },
            { type: "separator" },
            { type: "item", label: "Zoom in", shortcut: "⌘=", action: () => setZoomAt(zoom * 1.25) },
            { type: "item", label: "Zoom out", shortcut: "⌘-", action: () => setZoomAt(zoom * 0.8) },
            { type: "item", label: "Reset zoom", action: () => setZoomAt(1) },
            { type: "item", label: "Fit all", shortcut: "F", action: () => fitView() },
          ]} />
          <Menu label="Tools" items={[
            { type: "item", label: sel.length >= 2 ? `Synthesize ${sel.length} selected` : "Synthesize (shift+click 2+ windows)", shortcut: "⌘J", action: () => createSynthesis(sel), disabled: sel.length < 2 },
          ]} />
          <Menu label="Help" items={[
            { type: "item", label: "Tutorial…", action: () => setShowTutorial(true) },
            { type: "separator" },
            { type: "item", label: "About NetClaw Canvas", action: () => alert("NetClaw Canvas · a branching workspace for the local OpenClaw gateway · workflow adapted from Jack Rabbit.") },
          ]} />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, overflow: "hidden", flex: 1, marginLeft: 4 }}>
          {path.map((n, i) => (
            <React.Fragment key={n.id}>
              {i > 0 && <span style={{ color: C.muted, fontSize: 12 }}>›</span>}
              <button onClick={() => { bringFront(n.id); laneRefs.current[n.id]?.scrollIntoView({ behavior: "smooth", inline: "center" }); }}
                style={{ fontFamily: "ui-monospace, monospace", fontSize: 11, padding: "2px 8px", borderRadius: 5, border: "none", cursor: "pointer", background: n.id === active ? depthColor(n.depth) : "transparent", color: n.id === active ? "#fff" : depthColor(n.depth), whiteSpace: "nowrap", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis" }}>
                {n.depth === 0 ? clip(nodeTitle(n), 22) : `"${n.sourceQuote}"`}
              </button>
            </React.Fragment>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
          {/* tiled / scroll-locked indicator — click to release */}
          {tiled && (
            <button onClick={() => setTiled(false)} title="canvas scrolling is locked while tiled — click to unlock (or drag/zoom a window)"
              style={{ display: "flex", alignItems: "center", gap: 6, background: C.card, border: `1px solid ${C.trunk}`, borderRadius: 7, padding: "4px 9px", cursor: "pointer", color: C.ink, fontSize: 11, fontWeight: 600, flexShrink: 0 }}>
              <span style={{ color: C.trunk }}>▤ Tiled</span>
              <span style={{ color: C.muted, fontWeight: 500 }}>scroll locked</span>
              <span style={{ color: C.muted, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 10, borderLeft: `1px solid ${C.hairline}`, paddingLeft: 6 }}>unlock ✕</span>
            </button>
          )}
          {/* zoom control */}
          <div style={{ display: "flex", alignItems: "center", gap: 1, border: `1px solid ${C.hairline}`, borderRadius: 7, padding: 2, background: C.card, flexShrink: 0 }}>
            <button onClick={() => setZoomAt(zoom * 0.8)} title="zoom out" style={{ ...zbtn, width: 24, height: 24, fontSize: 15 }}>－</button>
            <button onClick={() => setZoomAt(1)} title="reset to 100%" style={{ ...zbtn, width: 40, height: 24, fontSize: 10.5, fontFamily: "ui-monospace, monospace" }}>{Math.round(zoom * 100)}%</button>
            <button onClick={() => setZoomAt(zoom * 1.25)} title="zoom in" style={{ ...zbtn, width: 24, height: 24, fontSize: 15 }}>＋</button>
            <button onClick={() => fitView()} title="zoom to fit (F fits the active window)" style={{ ...zbtn, width: 24, height: 24, fontSize: 13 }}>⤢</button>
          </div>
          <span title={gatewayOnline
            ? "OpenClaw gateway and chat compatibility endpoint are ready"
            : gatewayIssue === "chat-completions-disabled"
              ? "OpenClaw is reachable, but /v1/chat/completions is disabled"
              : "OpenClaw gateway is unavailable; requests use NetClaw's local heuristic fallback"}
            style={{ fontSize: 9.5, padding: "4px 8px", borderRadius: 999, border: `1px solid ${gatewayOnline ? "#0E7C7B" : gatewayOnline === false ? "#BA7517" : C.hairline}`, background: gatewayOnline ? "#0E7C7B11" : gatewayOnline === false ? "#BA751711" : C.card, color: gatewayOnline ? "#0E7C7B" : gatewayOnline === false ? "#BA7517" : C.muted, fontFamily: "ui-monospace, Menlo, monospace", fontWeight: 700, letterSpacing: 0.5 }}>
            {gatewayOnline
              ? "GATEWAY LIVE"
              : gatewayIssue === "chat-completions-disabled"
                ? "CHAT API DISABLED"
                : gatewayOnline === false
                  ? "GATEWAY OFFLINE"
                  : "CHECKING GATEWAY"}
          </span>
          <span title="Model and credentials are managed by NetClaw's OpenClaw gateway"
            style={{ fontSize: 10, padding: "4px 8px", borderRadius: 6, border: `1px solid ${C.hairline}`, background: C.card, color: C.muted, fontFamily: "ui-monospace, Menlo, monospace", letterSpacing: 0.4 }}>
            OPENCLAW
          </span>
          <input ref={fileInputRef} type="file" accept="application/json,.json" onChange={openFile} style={{ display: "none" }} />
        </div>
      </div>

      {/* body: branch index + canvas */}
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>

        {/* branch index (left panel) */}
        {indexOpen ? (
          <div style={{ width: 232, flexShrink: 0, borderRight: `1px solid ${C.hairline}`, background: C.cardAlt, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "7px 10px", borderBottom: `1px solid ${C.hairline}` }}>
              <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 9, letterSpacing: 1.1, textTransform: "uppercase", color: C.muted }}>Chats</span>
              <button onClick={() => setIndexOpen(false)} title="hide" style={{ marginLeft: "auto", border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 12, lineHeight: 1 }}>‹</button>
            </div>

            {(
              <>
                <div style={{ display: "flex", gap: 6, padding: "8px 8px 4px" }}>
                  <button onClick={newSession} title="start a new chat" style={{ flex: 1, fontSize: 11.5, padding: "6px 8px", borderRadius: 7, border: "none", background: C.trunk, color: "#fff", fontWeight: 600, cursor: "pointer" }}>＋ New chat</button>
                  <button onClick={createFolder} title="new folder" style={{ fontSize: 12, padding: "6px 9px", borderRadius: 7, border: `1px solid ${C.hairline}`, background: C.card, color: C.ink, cursor: "pointer" }}>🗀</button>
                </div>
                <div style={{ padding: "0 8px 6px" }}>
                  <input value={chatQuery} onChange={(e) => setChatQuery(e.target.value)} placeholder="search chats…"
                    style={{ width: "100%", boxSizing: "border-box", border: `1px solid ${C.hairline}`, borderRadius: 7, padding: "5px 8px", fontSize: 11.5, outline: "none", color: C.ink, background: C.canvas }} />
                </div>
                <div style={{ flex: 1, overflowY: "auto", padding: "2px 0" }}>
                  {(() => {
                    const q = chatQuery.trim().toLowerCase();
                    const matches = !q ? sessionList : sessionList.filter((s) => {
                      if (sessTitle(s).toLowerCase().includes(q)) return true;
                      return (s.nodes || []).some((n) => (n.messages || []).some((m) => String(m.content || "").toLowerCase().includes(q)));
                    });
                    const byFolder = new Map();
                    const unfiled = [];
                    matches.forEach((s) => {
                      const fid = sessionFolder[s.id];
                      if (fid && folders.some((f) => f.id === fid)) { if (!byFolder.has(fid)) byFolder.set(fid, []); byFolder.get(fid).push(s); }
                      else unfiled.push(s);
                    });

                    const kkey = (fid) => fid || "__unfiled";
                    const dropProps = (fid) => ({
                      onDragOver: (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; if (dropTarget !== kkey(fid)) setDropTarget(kkey(fid)); },
                      onDragLeave: () => setDropTarget((t) => (t === kkey(fid) ? null : t)),
                      onDrop: (e) => { e.preventDefault(); const id = e.dataTransfer.getData("text/plain") || dragSessId; if (id) assignSession(id, fid); setDropTarget(null); setDragSessId(null); },
                    });
                    const chatRow = (s, indented) => {
                      const isCurrent = currentSession && currentSession.id === s.id;
                      const editing = renamingSession === s.id;
                      return (
                        <div key={s.id} className="sb-row" draggable={!editing}
                          onDragStart={(e) => { e.dataTransfer.setData("text/plain", s.id); e.dataTransfer.effectAllowed = "move"; setDragSessId(s.id); }}
                          onDragEnd={() => { setDragSessId(null); setDropTarget(null); }}
                          onClick={() => { if (editing) return; if (!isCurrent) openSession(s.id); }} title={editing ? undefined : sessTitle(s)}
                          style={{ display: "flex", alignItems: "center", gap: 6, padding: `5px 8px 5px ${indented ? 22 : 10}px`, cursor: editing ? "default" : (isCurrent ? "default" : "pointer"), opacity: dragSessId === s.id ? 0.4 : 1, background: isCurrent ? C.userBubble : "transparent", borderLeft: `2px solid ${isCurrent ? C.trunk : "transparent"}` }}>
                          <span style={{ width: 6, height: 6, borderRadius: "50%", background: isCurrent ? C.trunk : C.hairline, flexShrink: 0 }} />
                          {editing ? (
                            <input autoFocus data-rename="session" data-id={s.id} defaultValue={sessionTitles[s.id] || s.title || ""} onClick={(e) => e.stopPropagation()}
                              onBlur={(e) => { renameSession(s.id, e.target.value); setRenamingSession(null); }}
                              onKeyDown={(e) => { if (e.key === "Enter") e.target.blur(); if (e.key === "Escape") setRenamingSession(null); }}
                              placeholder="chat name…"
                              style={{ flex: 1, minWidth: 0, border: `1px solid ${C.trunk}`, borderRadius: 4, padding: "1px 5px", fontSize: 11.5, fontWeight: 600, color: C.ink, background: C.canvas, outline: "none" }} />
                          ) : (
                            <span style={{ flex: 1, minWidth: 0, fontSize: 11.5, color: C.ink, fontWeight: isCurrent ? 600 : 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{sessTitle(s)}</span>
                          )}
                          {!editing && (
                            <button className="sb-del" onClick={(e) => { e.stopPropagation(); setRenamingSession(s.id); }}
                              title="rename chat" style={{ border: "none", background: "transparent", color: C.muted, fontSize: 10, lineHeight: 1, padding: "2px 2px", cursor: "pointer", flexShrink: 0 }}>✎</button>
                          )}
                          {!editing && (
                            <button className="sb-del" onClick={(e) => { e.stopPropagation(); askConfirm({ title: "Delete chat?", message: `Delete "${sessTitle(s)}"? This cannot be undone.`, okLabel: "Delete", danger: true, onOk: () => deleteSession(s.id) }); }}
                              title="delete chat" style={{ border: "none", background: "transparent", color: "#A8324E", fontSize: 12, lineHeight: 1, padding: "2px 3px", cursor: "pointer", flexShrink: 0 }}>×</button>
                          )}
                        </div>
                      );
                    };

                    // a chat/session row plus, when its canvas holds more than one main thread,
                    // those threads listed beneath it (click to jump to it, reopening if it was closed).
                    // Closed main threads stay listed (dimmed) so closing a window doesn't make a thread
                    // vanish from its folder — clicking one reopens it on the canvas.
                    const sessionAndThreads = (s, indented) => {
                      const isCur = currentSession && currentSession.id === s.id;
                      const src = isCur ? nodes : (s.nodes || []);
                      const threads = src.filter((n) => n.depth === 0);
                      return (
                        <React.Fragment key={s.id}>
                          {chatRow(s, indented)}
                          {threads.length > 1 && threads.map((t) => {
                            const on = isCur && active === t.id;
                            const tEditing = renamingThread === t.id;
                            const tClosed = !!t.closed;
                            return (
                              <div key={s.id + "/" + t.id} className="sb-row" onClick={() => { if (tEditing) return; openThread(s.id, t.id); }} title={tEditing ? undefined : (tClosed ? nodeTitle(t) + " (closed — click to reopen)" : nodeTitle(t))}
                                style={{ display: "flex", alignItems: "center", gap: 6, padding: `3px 8px 3px ${(indented ? 22 : 10) + 14}px`, cursor: tEditing ? "default" : "pointer", opacity: tClosed && !on ? 0.5 : 1, background: on ? C.userBubble : "transparent", borderLeft: `2px solid ${on ? depthColor(0) : "transparent"}` }}>
                                <span style={{ width: 4, height: 4, borderRadius: "50%", background: depthColor(0), flexShrink: 0, opacity: 0.75 }} />
                                {tEditing ? (
                                  <input autoFocus data-rename="thread" data-id={t.id} data-sess={s.id} defaultValue={t.title || nodeTitle(t)} onClick={(e) => e.stopPropagation()}
                                    onBlur={(e) => { renameThread(s.id, t.id, e.target.value); setRenamingThread(null); }}
                                    onKeyDown={(e) => { if (e.key === "Enter") e.target.blur(); if (e.key === "Escape") setRenamingThread(null); }}
                                    placeholder="thread name…"
                                    style={{ flex: 1, minWidth: 0, border: `1px solid ${C.trunk}`, borderRadius: 4, padding: "1px 5px", fontSize: 10.5, fontWeight: 600, color: C.ink, background: C.canvas, outline: "none" }} />
                                ) : (
                                  <span style={{ flex: 1, minWidth: 0, fontSize: 10.5, color: on ? C.ink : C.muted, fontWeight: on ? 600 : 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{nodeTitle(t)}</span>
                                )}
                                {!tEditing && tClosed && <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 7.5, letterSpacing: 0.3, textTransform: "uppercase", color: C.muted, border: `1px solid ${C.hairline}`, borderRadius: 3, padding: "0 3px", flexShrink: 0 }}>hidden</span>}
                                {!tEditing && (
                                  <button className="sb-del" onClick={(e) => { e.stopPropagation(); setRenamingThread(t.id); }}
                                    title="rename thread" style={{ border: "none", background: "transparent", color: C.muted, fontSize: 9.5, lineHeight: 1, padding: "2px 2px", cursor: "pointer", flexShrink: 0 }}>✎</button>
                                )}
                              </div>
                            );
                          })}
                        </React.Fragment>
                      );
                    };

                    return (
                      <>
                        {folders.map((f) => {
                          const list = byFolder.get(f.id) || [];
                          if (q && !list.length) return null;
                          const collapsed = !q && collapsedFolders[f.id];
                          const isDrop = dropTarget === f.id;
                          return (
                            <div key={f.id}>
                              <div className="sb-row" {...dropProps(f.id)}
                                style={{ display: "flex", alignItems: "center", gap: 4, padding: "5px 8px", background: isDrop ? C.userBubble : "transparent", outline: isDrop ? `1px dashed ${C.trunk}` : "none", outlineOffset: -1 }}>
                                <button onClick={() => setCollapsedFolders((c) => ({ ...c, [f.id]: !c[f.id] }))} title={collapsed ? "expand" : "collapse"}
                                  style={{ border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 9, width: 10, flexShrink: 0 }}>{collapsed ? "▸" : "▾"}</button>
                                <span style={{ fontSize: 11, flexShrink: 0 }}>🗀</span>
                                {renamingFolder === f.id ? (
                                  <input autoFocus data-rename="folder" data-id={f.id} defaultValue={f.name} onClick={(e) => e.stopPropagation()}
                                    onBlur={(e) => { const v = e.target.value.trim(); if (v) renameFolder(f.id, v); setRenamingFolder(null); }}
                                    onKeyDown={(e) => { if (e.key === "Enter") e.target.blur(); if (e.key === "Escape") setRenamingFolder(null); }}
                                    style={{ flex: 1, minWidth: 0, border: `1px solid ${C.trunk}`, borderRadius: 4, padding: "1px 5px", fontSize: 11, fontWeight: 600, color: C.ink, background: C.canvas, outline: "none" }} />
                                ) : (
                                  <span onDoubleClick={() => setRenamingFolder(f.id)} title="double-click to rename"
                                    style={{ flex: 1, minWidth: 0, fontSize: 11, fontWeight: 600, color: C.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
                                )}
                                <span style={{ fontSize: 9, color: C.muted, fontFamily: "ui-monospace, Menlo, monospace", flexShrink: 0 }}>{list.length}</span>
                                <button className="sb-del" onClick={() => setRenamingFolder(f.id)} title="rename" style={{ border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 10, padding: "0 2px", flexShrink: 0 }}>✎</button>
                                <button className="sb-del" onClick={() => askConfirm({ title: "Delete folder?", message: `Delete folder "${f.name}"? Its ${list.length} chat${list.length === 1 ? "" : "s"} won't be deleted — they'll move to Unfiled.`, okLabel: "Delete folder", danger: true, onOk: () => removeFolder(f.id) })}
                                  title="delete folder (chats move to Unfiled)" style={{ border: "none", background: "transparent", color: "#A8324E", cursor: "pointer", fontSize: 11, padding: "0 2px", flexShrink: 0 }}>×</button>
                              </div>
                              {!collapsed && (list.length ? list.map((s) => sessionAndThreads(s, true))
                                : <div style={{ padding: "5px 8px 5px 24px", fontSize: 9.5, color: C.muted, fontStyle: "italic" }}>drop chats here</div>)}
                            </div>
                          );
                        })}

                        {folders.length > 0 && (
                          <div>
                            <div {...dropProps(null)}
                              style={{ display: "flex", alignItems: "center", gap: 4, padding: "7px 8px 3px", outline: dropTarget === "__unfiled" ? `1px dashed ${C.trunk}` : "none", outlineOffset: -1 }}>
                              <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 8.5, letterSpacing: 0.8, textTransform: "uppercase", color: C.muted, flex: 1 }}>Unfiled</span>
                              <span style={{ fontSize: 9, color: C.muted, fontFamily: "ui-monospace, Menlo, monospace" }}>{unfiled.length}</span>
                            </div>
                            {unfiled.map((s) => sessionAndThreads(s, false))}
                          </div>
                        )}
                        {folders.length === 0 && unfiled.map((s) => sessionAndThreads(s, false))}
                        {!matches.length && !folders.length && <div style={{ padding: "16px 12px", textAlign: "center", color: C.muted, fontSize: 11 }}>{q ? "no matches" : "no chats yet"}</div>}
                      </>
                    );
                  })()}
                </div>
              </>
            )}
          </div>
        ) : (
          <button onClick={() => setIndexOpen(true)} title="show panel" style={{ flexShrink: 0, width: 22, border: "none", borderRight: `1px solid ${C.hairline}`, background: C.cardAlt, color: C.muted, cursor: "pointer", fontSize: 12 }}>›</button>
        )}

        {/* canvas viewport */}
        <div style={{ flex: 1, position: "relative", minHeight: 0 }}>
        <div ref={viewportRef} style={{ position: "absolute", inset: 0, overflow: tiled ? "hidden" : "auto" }}>
        <div style={{ position: "relative", width: worldW * zoom, height: worldH * zoom, minWidth: "100%", minHeight: "100%" }}>
        <div onMouseDown={startPan} style={{ position: "absolute", top: 0, left: 0, width: worldW, height: worldH,
            // At 100% drop the transform entirely: a `scale(1)` still makes this a transformed
            // ancestor, and Chromium mispaints text-input carets inside transformed containers
            // (the caret lands away from the input — the "cursor in the wrong place" bug). No
            // transform at 100% (the default and what Tile uses) = caret renders correctly.
            transform: zoom === 1 ? "none" : `scale(${zoom})`, transformOrigin: "0 0",
            cursor: panning ? "grabbing" : (tiled ? "default" : "grab") }}>

          {/* connector + overlay layer (behind windows) */}
          <svg width={worldW} height={worldH} style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 1 }}>
            <defs>
              {ALLCOLORS.map((color) => (
                <marker key={color} id={markerId(color)} markerWidth="14" markerHeight="14" refX="9" refY="5" orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M0,0 L10,5 L0,10 L3,5 Z" fill={color} />
                </marker>
              ))}
            </defs>
            {connectors.map((c) => (
              <path key={c.id} d={c.d} pathLength={1} className={c.synth ? "synthconn" : "conn"} fill="none" stroke={c.color} strokeWidth={2.5} markerEnd={`url(#${markerId(c.color)})`} opacity={0.92} />
            ))}
            {guides.map((g, i) => g.x != null
              ? <line key={"gx" + i} x1={g.x} y1={0} x2={g.x} y2={worldH} stroke={C.trunk} strokeWidth={1 / zoom} strokeDasharray="5 5" opacity={0.7} />
              : <line key={"gy" + i} x1={0} y1={g.y} x2={worldW} y2={g.y} stroke={C.trunk} strokeWidth={1 / zoom} strokeDasharray="5 5" opacity={0.7} />)}
            {marquee && <rect x={Math.min(marquee.x0, marquee.x1)} y={Math.min(marquee.y0, marquee.y1)} width={Math.abs(marquee.x1 - marquee.x0)} height={Math.abs(marquee.y1 - marquee.y0)} fill={C.trunk} fillOpacity={0.08} stroke={C.trunk} strokeWidth={1 / zoom} strokeDasharray="4 4" />}
          </svg>

          {/* windows (closed nodes are hidden from the canvas but kept in the sidebar) */}
          {nodes.filter((n) => !n.closed).map((n) => (
            <Lane key={n.id} node={n} color={depthColor(n.depth)} isActive={n.id === active} selected={sel.includes(n.id)}
              animate={!interacting}
              dark={dark}
              defaultTab={defaultTab}
              highlights={nodes.filter((c) => c.parentId === n.id && !c.closed && c.sourceQuote).map((c) => ({ quote: c.sourceQuote, color: depthColor(c.depth) }))}
              synthSources={n.synthFrom ? n.synthFrom.map((pid) => { const p = nodes.find((x) => x.id === pid); return p ? { id: p.id, color: depthColor(p.depth), title: nodeTitle(p) } : null; }).filter(Boolean) : null}
              laneRef={(el) => (laneRefs.current[n.id] = el)}
              onFocus={(e) => selectNode(n, e)}
              onDragStart={(e) => startDrag(e, n)}
              onResizeStart={(e) => startResize(e, n)}
              onSelect={() => onSelect(n.id)}
              onToggleMin={() => toggleMin(n.id)}
              onDelete={() => closeNode(n.id)}
              draft={drafts[n.id] || ""} setDraft={(v) => setDrafts((d) => ({ ...d, [n.id]: v }))}
              pendingQuote={quotes[n.id] || null} onClearQuote={() => clearQuote(n.id)}
              attachments={attachments[n.id] || null} onAddFiles={(files) => addFiles(n.id, files)} onRemoveImage={(idx) => removeImage(n.id, idx)}
              onSend={() => send(n.id)}
              onAutoHeight={(h) => setHeightAndPush(n.id, h)}
              onAutoFit={() => patch(n.id, { manual: false })} />
          ))}

          {/* synthesis chip: appears whenever 2+ visible nodes are selected. Anchored to the
              right edge of the selection bounding box so it follows the user's eye to the
              place the new synthesis node will land. */}
          {(() => {
            const picked = sel.map((id) => nodes.find((n) => n.id === id)).filter((n) => n && !n.closed);
            if (picked.length < 2) return null;
            const rightEdge = Math.max(...picked.map((n) => n.x + n.w));
            const topEdge = Math.min(...picked.map((n) => n.y));
            const botEdge = Math.max(...picked.map((n) => n.y + (n.min ? COLLAPSED_H : n.h)));
            const midY = (topEdge + botEdge) / 2;
            const colors = picked.map((n) => depthColor(n.depth));
            return (
              <div style={{ position: "absolute", left: rightEdge + 18, top: midY, transform: "translate(0, -50%)", zIndex: 60, pointerEvents: "auto" }}>
                <button onClick={() => createSynthesis(sel)}
                  style={{ display: "flex", alignItems: "center", gap: 8, background: C.trunk, color: "#fff", border: "none", borderRadius: 9, padding: "9px 14px", fontSize: 12.5, fontWeight: 600, cursor: "pointer", boxShadow: "0 8px 22px rgba(0,0,0,0.3)", whiteSpace: "nowrap", animation: synthSeenHint ? "none" : "synthPulse 1.6s ease-in-out infinite" }}>
                  <span style={{ display: "inline-flex", gap: 2 }}>
                    {colors.slice(0, 5).map((c, i) => <span key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: c, display: "inline-block" }} />)}
                  </span>
                  <span>⊕ Synthesize these {picked.length} →</span>
                  <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 10, opacity: 0.75, marginLeft: 4, padding: "1px 5px", borderRadius: 4, background: "rgba(255,255,255,0.18)" }}>⌘J</span>
                </button>
                {!synthSeenHint && (
                  <div style={{ marginTop: 6, padding: "5px 10px", background: C.card, color: C.muted, border: `1px solid ${C.hairline}`, borderRadius: 7, fontSize: 11, lineHeight: 1.4, maxWidth: 240, boxShadow: "0 4px 12px var(--shadow)" }}>
                    Merge these threads into one synthesis node that ingests all their context.
                  </div>
                )}
              </div>
            );
          })()}
        </div>
        </div>
        </div>

        {open.length === 0 && (
          <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: C.muted, pointerEvents: "none" }}>
            <div style={{ fontSize: 14 }}>No threads open.</div>
            <button onClick={newMainThread} style={{ background: C.trunk, color: "#fff", border: "none", borderRadius: 8, padding: "8px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer", pointerEvents: "auto" }}>＋ New main thread</button>
          </div>
        )}
        </div>
      </div>

      {/* overview: full screen topology map of the reasoning graph */}
      {overview && (() => {
        const open = nodes.filter((n) => !n.closed);
        if (!open.length) return (
          <div onClick={() => setOverview(false)} style={{ position: "fixed", inset: 0, zIndex: 250, background: C.canvas, display: "flex", alignItems: "center", justifyContent: "center", color: C.muted, fontSize: 13, animation: "fadeIn .18s ease-out" }}>no open threads · press O or Esc to exit</div>
        );
        const cx = (n) => n.x + n.w / 2, cy = (n) => n.y + (n.min ? COLLAPSED_H : n.h) / 2;
        const minX = Math.min(...open.map(cx)), maxX = Math.max(...open.map(cx));
        const minY = Math.min(...open.map(cy)), maxY = Math.max(...open.map(cy));
        const vw = typeof window !== "undefined" ? window.innerWidth : 1200;
        const vh = typeof window !== "undefined" ? window.innerHeight : 800;
        const padX = 120, padTop = 110, padBot = 90;
        const spanX = Math.max(1, maxX - minX), spanY = Math.max(1, maxY - minY);
        const k = Math.min((vw - padX * 2) / spanX, (vh - padTop - padBot) / spanY, 1.2);
        const ox = (vw - spanX * k) / 2 - minX * k;
        const oy = padTop + ((vh - padTop - padBot) - spanY * k) / 2 - minY * k;
        const P = (n) => ({ x: cx(n) * k + ox, y: cy(n) * k + oy });
        const links = [];
        open.forEach((c) => {
          const pids = c.synthFrom && c.synthFrom.length ? c.synthFrom : (c.parentId ? [c.parentId] : []);
          pids.forEach((pid, i) => {
            const p = open.find((n) => n.id === pid); if (!p) return;
            links.push({ id: c.id + "-" + i, a: P(p), b: P(c), color: c.synthFrom ? depthColor(p.depth) : depthColor(c.depth) });
          });
        });
        return (
          <div onClick={() => setOverview(false)} style={{ position: "fixed", inset: 0, zIndex: 250, background: C.canvas, animation: "fadeIn .18s ease-out", cursor: "zoom-out" }}>
            <div style={{ position: "absolute", top: 24, left: 0, right: 0, textAlign: "center", pointerEvents: "none" }}>
              <div style={{ fontFamily: "Georgia, 'Iowan Old Style', serif", fontStyle: "italic", fontSize: 19, color: C.ink }}>The shape of this exploration</div>
              <div style={{ fontSize: 11.5, color: C.muted, marginTop: 3 }}>{open.length} threads · click a node to jump · O or Esc to exit</div>
            </div>
            <svg width={vw} height={vh} style={{ display: "block" }}>
              {links.map((l) => (
                <line key={l.id} x1={l.a.x} y1={l.a.y} x2={l.b.x} y2={l.b.y} stroke={l.color} strokeWidth={1.6} opacity={0.55} />
              ))}
              {open.map((n) => {
                const p = P(n);
                const r = Math.min(16, 7 + n.messages.length * 0.7);
                const isSyn = !!(n.synthFrom && n.synthFrom.length);
                return (
                  <g key={n.id} className="ov-dot" style={{ transformOrigin: `${p.x}px ${p.y}px` }}
                    onClick={(e) => { e.stopPropagation(); setOverview(false); setTimeout(() => focusNode(n.id), 60); }}>
                    <title>{nodeTitle(n)}</title>
                    {n.id === active && <circle cx={p.x} cy={p.y} r={r + 6} fill="none" stroke={depthColor(n.depth)} strokeWidth={1.5} opacity={0.5} />}
                    <circle cx={p.x} cy={p.y} r={r} fill={depthColor(n.depth)} opacity={0.92} />
                    {isSyn && <circle cx={p.x} cy={p.y} r={r - 3.5} fill="none" stroke="#fff" strokeWidth={1.6} opacity={0.9} />}
                    {n.depth === 0 && (
                      <text x={p.x + r + 8} y={p.y + 4} fontSize={11.5} fill={C.ink} fontFamily="ui-sans-serif, system-ui, sans-serif" style={{ pointerEvents: "none" }}>{clip(nodeTitle(n), 34)}</text>
                    )}
                  </g>
                );
              })}
            </svg>
            <div style={{ position: "absolute", bottom: 22, left: 24, display: "flex", alignItems: "center", gap: 14, pointerEvents: "none" }}>
              {[0, 1, 2, 3].map((d) => (
                <span key={d} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 10.5, color: C.muted }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: depthColor(d), display: "inline-block" }} />
                  {d === 0 ? "trunk" : "depth " + d}
                </span>
              ))}
              <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 10.5, color: C.muted }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: C.muted, display: "inline-block", boxShadow: "inset 0 0 0 1.5px " + C.canvas, outline: `1.5px solid ${C.muted}`, outlineOffset: -4 }} />
                synthesis
              </span>
            </div>
          </div>
        );
      })()}

      {/* tutorial */}
      {showTutorial && <Tutorial onClose={() => setShowTutorial(false)} />}

      {/* generic confirm dialog (in app; native confirm() is blocked in sandboxed iframes) */}
      {confirmState && (
        <div onMouseDown={(e) => { if (e.target === e.currentTarget) setConfirmState(null); }}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 400, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
          <div role="alertdialog" style={{ background: C.card, border: `1px solid ${C.hairline}`, borderRadius: 10, padding: 18, width: 420, maxWidth: "100%", boxShadow: "0 20px 50px rgba(0,0,0,0.35)" }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: C.ink, marginBottom: 8 }}>{confirmState.title}</div>
            <div style={{ fontSize: 13, color: C.ink, lineHeight: 1.5, whiteSpace: "pre-wrap", marginBottom: 14 }}>{confirmState.message}</div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setConfirmState(null)} autoFocus
                style={{ fontSize: 12.5, padding: "6px 14px", borderRadius: 7, border: `1px solid ${C.hairline}`, background: C.card, color: C.ink, cursor: "pointer", fontWeight: 500 }}>Cancel</button>
              <button onClick={() => { const cb = confirmState.onOk; setConfirmState(null); if (cb) cb(); }}
                style={{ fontSize: 12.5, padding: "6px 14px", borderRadius: 7, border: "none", background: confirmState.danger ? "#A8324E" : C.trunk, color: "#fff", cursor: "pointer", fontWeight: 600 }}>{confirmState.okLabel}</button>
            </div>
          </div>
        </div>
      )}

      {/* sessions library */}
      {showSessions && (
        <div onMouseDown={(e) => { if (e.target === e.currentTarget) setShowSessions(false); }}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 300, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
          <div style={{ background: C.card, border: `1px solid ${C.hairline}`, borderRadius: 12, padding: 18, width: 600, maxWidth: "100%", maxHeight: "85vh", display: "flex", flexDirection: "column", boxShadow: "0 20px 50px rgba(0,0,0,0.3)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: C.ink }}>Sessions</div>
                <div style={{ fontSize: 11, color: C.muted }}>Stored in this browser's IndexedDB; capacity ~half the disk.</div>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button onClick={newSession} title="start a fresh session" style={{ fontSize: 12, padding: "5px 10px", borderRadius: 7, border: "none", background: C.trunk, color: "#fff", fontWeight: 600, cursor: "pointer" }}>＋ New</button>
                <button onClick={createFolder} title="create a project folder" style={{ fontSize: 12, padding: "5px 10px", borderRadius: 7, border: `1px solid ${C.hairline}`, background: C.card, color: C.ink, cursor: "pointer" }}>🗀 Folder</button>
                <button onClick={saveToFile} title="export current session to a JSON file" style={{ fontSize: 12, padding: "5px 10px", borderRadius: 7, border: `1px solid ${C.hairline}`, background: C.card, color: C.ink, cursor: "pointer" }}>↓ Export</button>
                <button onClick={() => fileInputRef.current && fileInputRef.current.click()} title="import a JSON file" style={{ fontSize: 12, padding: "5px 10px", borderRadius: 7, border: `1px solid ${C.hairline}`, background: C.card, color: C.ink, cursor: "pointer" }}>↑ Import</button>
              </div>
            </div>
            <input value={sessSearch} onChange={(e) => setSessSearch(e.target.value)} placeholder="search titles and message content…" autoFocus
              style={{ width: "100%", boxSizing: "border-box", border: `1px solid ${C.hairline}`, borderRadius: 8, padding: "8px 10px", fontSize: 13, outline: "none", color: C.ink, background: C.canvas, marginBottom: 8 }} />
            <div style={{ flex: 1, overflowY: "auto", border: `1px solid ${C.hairline}`, borderRadius: 8 }}>
              {(() => {
                const q = sessSearch.trim().toLowerCase();
                const matches = !q ? sessionList : sessionList.filter((s) => {
                  if ((s.title || "").toLowerCase().includes(q)) return true;
                  return (s.nodes || []).some((n) => (n.messages || []).some((m) => String(m.content || "").toLowerCase().includes(q)));
                });

                // group the (filtered) sessions by folder; unknown/missing folder → Unfiled
                const byFolder = new Map();
                const unfiled = [];
                matches.forEach((s) => {
                  const fid = sessionFolder[s.id];
                  if (fid && folders.some((f) => f.id === fid)) {
                    if (!byFolder.has(fid)) byFolder.set(fid, []);
                    byFolder.get(fid).push(s);
                  } else unfiled.push(s);
                });

                if (!matches.length && !folders.length) return <div style={{ padding: "20px 14px", textAlign: "center", color: C.muted, fontSize: 12 }}>{q ? "no matches" : "no sessions yet"}</div>;

                // one session row, draggable onto folder headers
                const sessionRow = (s, idx) => {
                  const isCurrent = currentSession && currentSession.id === s.id;
                  const threadCount = (s.nodes || []).filter((n) => !n.closed).length;
                  const previewMsg = (s.nodes || []).flatMap((n) => n.messages || []).find((m) => m.role === "user" && !m.relate);
                  const preview = previewMsg ? String(previewMsg.content || "").replace(/\s+/g, " ").trim() : "";
                  return (
                    <div key={s.id} draggable
                      onDragStart={(e) => { e.dataTransfer.setData("text/plain", s.id); e.dataTransfer.effectAllowed = "move"; setDragSessId(s.id); }}
                      onDragEnd={() => { setDragSessId(null); setDropTarget(null); }}
                      onClick={() => !isCurrent && openSession(s.id)}
                      style={{ padding: "9px 12px 9px 14px", borderTop: idx === 0 ? "none" : `1px solid ${C.hairline}`, cursor: isCurrent ? "default" : "grab", opacity: dragSessId === s.id ? 0.4 : 1, background: isCurrent ? C.userBubble : "transparent", display: "flex", alignItems: "flex-start", gap: 8 }}>
                      <span title="drag to a folder" style={{ color: C.muted, fontSize: 12, lineHeight: "16px", marginTop: 2, flexShrink: 0, cursor: "grab", userSelect: "none" }}>⋮⋮</span>
                      <span style={{ width: 7, height: 7, borderRadius: "50%", background: isCurrent ? C.trunk : C.hairline, marginTop: 6, flexShrink: 0 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: isCurrent ? 600 : 500, color: C.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title || "(untitled)"}</div>
                        {preview && preview !== s.title && <div style={{ fontSize: 11.5, color: C.muted, marginTop: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{preview}</div>}
                        <div style={{ fontSize: 10.5, color: C.muted, marginTop: 3, fontFamily: "ui-monospace, Menlo, monospace" }}>{threadCount} thread{threadCount === 1 ? "" : "s"} · updated {fmtAgo(s.updatedAt)}</div>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); askConfirm({ title: "Delete session?", message: `Delete "${s.title || "(untitled)"}"? This cannot be undone.`, okLabel: "Delete", danger: true, onOk: () => deleteSession(s.id) }); }}
                        title="delete session"
                        style={{ flexShrink: 0, border: "none", background: "transparent", color: "#A8324E", cursor: "pointer", fontSize: 14, lineHeight: 1, padding: "4px 6px", borderRadius: 4 }}>×</button>
                    </div>
                  );
                };

                // drop-zone handlers shared by folder headers and the Unfiled header
                const key = (fid) => fid || "__unfiled";
                const dropProps = (fid) => ({
                  onDragOver: (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; if (dropTarget !== key(fid)) setDropTarget(key(fid)); },
                  onDragLeave: () => setDropTarget((t) => (t === key(fid) ? null : t)),
                  onDrop: (e) => { e.preventDefault(); const id = e.dataTransfer.getData("text/plain") || dragSessId; if (id) assignSession(id, fid); setDropTarget(null); setDragSessId(null); },
                });
                const headerBase = { display: "flex", alignItems: "center", gap: 6, padding: "6px 10px", background: C.cardAlt, borderTop: `1px solid ${C.hairline}`, position: "sticky", top: 0, zIndex: 1 };

                return (
                  <>
                    {folders.map((f) => {
                      const list = byFolder.get(f.id) || [];
                      if (q && !list.length) return null; // hide empty folders while searching
                      const collapsed = !q && collapsedFolders[f.id];
                      const isDrop = dropTarget === f.id;
                      return (
                        <div key={f.id}>
                          <div {...dropProps(f.id)}
                            style={{ ...headerBase, outline: isDrop ? `2px dashed ${C.trunk}` : "none", outlineOffset: -2 }}>
                            <button onClick={() => setCollapsedFolders((c) => ({ ...c, [f.id]: !c[f.id] }))} title={collapsed ? "expand" : "collapse"}
                              style={{ border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 10, width: 12, flexShrink: 0 }}>{collapsed ? "▸" : "▾"}</button>
                            <span style={{ fontSize: 12, flexShrink: 0 }}>🗀</span>
                            {renamingFolder === f.id ? (
                              <input autoFocus defaultValue={f.name}
                                onClick={(e) => e.stopPropagation()}
                                onBlur={(e) => { const v = e.target.value.trim(); if (v) renameFolder(f.id, v); setRenamingFolder(null); }}
                                onKeyDown={(e) => { if (e.key === "Enter") e.target.blur(); if (e.key === "Escape") setRenamingFolder(null); }}
                                style={{ flex: 1, minWidth: 0, border: `1px solid ${C.trunk}`, borderRadius: 5, padding: "2px 6px", fontSize: 12, fontWeight: 600, color: C.ink, background: C.canvas, outline: "none" }} />
                            ) : (
                              <span onDoubleClick={() => setRenamingFolder(f.id)} title="double-click to rename"
                                style={{ flex: 1, minWidth: 0, fontSize: 12, fontWeight: 600, color: C.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
                            )}
                            <span style={{ fontSize: 10, color: C.muted, fontFamily: "ui-monospace, Menlo, monospace", flexShrink: 0 }}>{list.length}</span>
                            <button onClick={() => setRenamingFolder(f.id)} title="rename folder"
                              style={{ border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 11, padding: "2px 3px", flexShrink: 0 }}>✎</button>
                            <button onClick={() => askConfirm({ title: "Delete folder?", message: `Delete folder "${f.name}"? Its ${list.length} chat${list.length === 1 ? "" : "s"} won't be deleted — they'll move to Unfiled.`, okLabel: "Delete folder", danger: true, onOk: () => removeFolder(f.id) })}
                              title="delete folder (chats move to Unfiled)"
                              style={{ border: "none", background: "transparent", color: "#A8324E", cursor: "pointer", fontSize: 13, lineHeight: 1, padding: "2px 4px", flexShrink: 0 }}>×</button>
                          </div>
                          {!collapsed && (list.length ? list.map((s, i) => sessionRow(s, i))
                            : <div style={{ padding: "10px 14px", fontSize: 11, color: C.muted, fontStyle: "italic" }}>Drag chats here to add them.</div>)}
                        </div>
                      );
                    })}

                    {/* Unfiled bucket + drop zone to pull a chat back out of any folder.
                        Only shown once folders exist; with no folders the list stays flat. */}
                    {folders.length > 0 && (
                      <div>
                        <div {...dropProps(null)}
                          style={{ ...headerBase, outline: dropTarget === "__unfiled" ? `2px dashed ${C.trunk}` : "none", outlineOffset: -2 }}>
                          <span style={{ width: 12, flexShrink: 0 }} />
                          <span style={{ fontSize: 11, fontFamily: "ui-monospace, Menlo, monospace", letterSpacing: 0.6, textTransform: "uppercase", color: C.muted, flex: 1 }}>Unfiled</span>
                          <span style={{ fontSize: 10, color: C.muted, fontFamily: "ui-monospace, Menlo, monospace" }}>{unfiled.length}</span>
                        </div>
                        {unfiled.map((s, i) => sessionRow(s, i))}
                      </div>
                    )}
                    {!folders.length && unfiled.map((s, i) => sessionRow(s, i))}
                    {q && !matches.length && <div style={{ padding: "20px 14px", textAlign: "center", color: C.muted, fontSize: 12 }}>no matches</div>}
                  </>
                );
              })()}
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10 }}>
              <button onClick={() => setShowSessions(false)}
                style={{ fontSize: 12, padding: "6px 14px", borderRadius: 7, border: `1px solid ${C.hairline}`, background: C.card, color: C.ink, cursor: "pointer" }}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* preferences dialog */}
      {showPrefs && (
        <div onMouseDown={(e) => { if (e.target === e.currentTarget) setShowPrefs(false); }}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 300, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
          <div style={{ background: C.card, border: `1px solid ${C.hairline}`, borderRadius: 12, padding: 18, width: 460, maxWidth: "100%", maxHeight: "90vh", overflowY: "auto", boxShadow: "0 20px 50px rgba(0,0,0,0.3)" }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: C.ink, marginBottom: 4 }}>Preferences</div>
            <div style={{ fontSize: 11, color: C.muted, marginBottom: 16 }}>Saved in this browser and applied on every load.</div>

            {(() => {
              const seg = (opts, current, onPick) => (
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {opts.map(([val, lbl]) => {
                    const on = current === val;
                    return (
                      <button key={val} onClick={() => onPick(val)}
                        style={{ flex: "1 1 auto", minWidth: 0, padding: "7px 10px", borderRadius: 8, border: `1px solid ${on ? C.trunk : C.hairline}`, background: on ? C.trunk : C.card, color: on ? "#fff" : C.ink, fontWeight: on ? 600 : 500, fontSize: 12.5, cursor: "pointer", whiteSpace: "nowrap" }}>{lbl}</button>
                    );
                  })}
                </div>
              );
              return (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, color: C.muted, marginBottom: 6, fontFamily: "ui-monospace, monospace", letterSpacing: 0.5, textTransform: "uppercase" }}>Theme</div>
                    {seg([["light", "☀ Light"], ["dark", "☾ Dark"]], dark ? "dark" : "light", (v) => setDark(v === "dark"))}
                  </div>

                  <div style={{ marginBottom: 4 }}>
                    <div style={{ fontSize: 11, color: C.muted, marginBottom: 6, fontFamily: "ui-monospace, monospace", letterSpacing: 0.5, textTransform: "uppercase" }}>Default answer tab</div>
                    {seg([["context", "Context"], ["summary", "Summary"], ["sources", "Source"], ["action", "Action"]], defaultTab, setDefaultTab)}
                    <div style={{ fontSize: 10.5, color: C.muted, marginTop: 6 }}>Which tab opens first on a new reply. Applies to answers generated from now on.</div>
                  </div>
                </>
              );
            })()}

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 18 }}>
              <button onClick={() => setShowPrefs(false)}
                style={{ fontSize: 12.5, padding: "6px 14px", borderRadius: 7, border: "none", background: C.trunk, color: "#fff", cursor: "pointer", fontWeight: 600 }}>Done</button>
            </div>
          </div>
        </div>
      )}

      {/* floating selection actions */}
      {branchHint && (
        <div ref={hintRef} style={{ position: "fixed", left: branchHint.x, top: branchHint.y, transform: "translate(-50%,-100%)", zIndex: 200, display: "flex", gap: 4 }}>
          <button onMouseDown={(e) => e.preventDefault()} onClick={() => createBranch(branchHint.nodeId, branchHint.quote)}
            style={{ background: "#1f2430", color: "#fff", border: "none", borderRadius: 7, padding: "7px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer", boxShadow: "0 6px 18px rgba(0,0,0,0.22)", whiteSpace: "nowrap" }}>
            ⎇ Branch this →
          </button>
          <button onMouseDown={(e) => e.preventDefault()} onClick={() => quoteAsContext(branchHint.nodeId, branchHint.quote)}
            title="attach this text as context for your next question in this thread"
            style={{ background: C.trunk, color: "#fff", border: "none", borderRadius: 7, padding: "7px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer", boxShadow: "0 6px 18px rgba(0,0,0,0.22)", whiteSpace: "nowrap" }}>
            ❝ Quote as context
          </button>
          {(nodes.find((n) => n.id === branchHint.nodeId)?.depth > 0) && (
            <button onMouseDown={(e) => e.preventDefault()} onClick={() => { relateToOrigin(branchHint.nodeId, branchHint.quote); setBranchHint(null); window.getSelection()?.removeAllRanges(); }}
              style={{ background: "#5B4B9E", color: "#fff", border: "none", borderRadius: 7, padding: "7px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer", boxShadow: "0 6px 18px rgba(0,0,0,0.22)", whiteSpace: "nowrap" }}>
              ⤴ Relate to origin
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---- minimal markdown ----------------------------------------------------
// Wrap occurrences of each highlight phrase in a tinted span colored to match the branch arrow.
// Earliest match wins; on ties, the longer phrase wins so nested quotes still resolve sensibly.
function applyHighlights(text, highlights, kp) {
  const t = String(text);
  const ranges = findHighlightRanges(t, highlights);
  if (!ranges.length) return t;
  const out = [];
  let cursor = 0;
  ranges.forEach((range, n) => {
    if (range.start > cursor) out.push(t.slice(cursor, range.start));
    out.push(
      <mark key={kp + "-hl-" + n} title="branched from here"
        style={{ background: range.color + "4D", color: "inherit", boxShadow: `inset 0 -3px 0 ${range.color}`, fontWeight: 600, padding: "1px 3px", borderRadius: 3 }}>
        {t.slice(range.start, range.end)}
      </mark>
    );
    cursor = range.end;
  });
  if (cursor < t.length) out.push(t.slice(cursor));
  return out;
}

// Match the visible selection against raw Markdown. Browser selections collapse
// layout whitespace and omit Markdown delimiters, so an exact substring search
// loses branch-source highlighting whenever the quote crosses formatting.
function canonicalHighlightText(value) {
  const source = String(value || "");
  let text = "";
  const map = [];
  let pendingSpace = false;
  for (let i = 0; i < source.length; i++) {
    const ch = source[i];
    if (/\s/.test(ch)) {
      pendingSpace = text.length > 0;
      continue;
    }
    if ("*_`~".includes(ch)) continue;
    if (pendingSpace && text && !text.endsWith(" ")) {
      text += " ";
      map.push(i);
    }
    pendingSpace = false;
    text += ch.toLocaleLowerCase();
    map.push(i);
  }
  return { text: text.trim(), map };
}

function expandMarkdownRange(text, start, end) {
  const pairs = ["**", "__", "~~", "*", "_", "`"];
  for (const token of pairs) {
    if (start >= token.length
      && text.slice(start - token.length, start) === token
      && text.slice(end, end + token.length) === token) {
      return { start: start - token.length, end: end + token.length };
    }
  }
  return { start, end };
}

function findHighlightRanges(text, highlights) {
  if (!highlights || !highlights.length) return [];
  const source = canonicalHighlightText(text);
  if (!source.text || !source.map.length) return [];
  const candidates = [];
  highlights.forEach((highlight) => {
    const quote = canonicalHighlightText(highlight.quote).text;
    if (quote.length < 2) return;
    let offset = 0;
    while (offset < source.text.length) {
      const index = source.text.indexOf(quote, offset);
      if (index < 0) break;
      const rawStart = source.map[index];
      const rawEnd = source.map[index + quote.length - 1] + 1;
      const expanded = expandMarkdownRange(text, rawStart, rawEnd);
      candidates.push({ ...expanded, color: highlight.color, length: quote.length });
      offset = index + Math.max(1, quote.length);
    }
  });
  candidates.sort((a, b) => a.start - b.start || b.length - a.length);
  const accepted = [];
  candidates.forEach((candidate) => {
    if (!accepted.some((range) => candidate.start < range.end && candidate.end > range.start)) {
      accepted.push(candidate);
    }
  });
  return accepted.sort((a, b) => a.start - b.start);
}

function highlightedMarkdownInline(text, kp, highlights) {
  const source = String(text);
  const ranges = findHighlightRanges(source, highlights);
  if (!ranges.length) return mdInline(source, kp);
  const out = [];
  let cursor = 0;
  ranges.forEach((range, index) => {
    if (range.start > cursor) out.push(...mdInline(source.slice(cursor, range.start), kp + "-pre-" + index));
    out.push(
      <mark key={kp + "-mark-" + index} title="branched from here"
        style={{ background: range.color + "4D", color: "inherit", boxShadow: `inset 0 -3px 0 ${range.color}`, fontWeight: 600, padding: "1px 3px", borderRadius: 3 }}>
        {mdInline(source.slice(range.start, range.end), kp + "-hit-" + index)}
      </mark>
    );
    cursor = range.end;
  });
  if (cursor < source.length) out.push(...mdInline(source.slice(cursor), kp + "-post"));
  return out;
}

function mdInline(text, kp = "x", highlights) {
  const out = []; let rest = String(text); let k = 0;
  const re = /(\*\*([^*]+?)\*\*)|(`([^`]+?)`)|(\*([^*]+?)\*)|(_([^_]+?)_)/;
  while (rest.length) {
    const m = rest.match(re);
    if (!m) { out.push(rest); break; }
    if (m.index > 0) out.push(rest.slice(0, m.index));
    const key = kp + k++;
    if (m[1]) out.push(<strong key={key} style={{ fontWeight: 700 }}>{m[2]}</strong>);
    else if (m[3]) out.push(<code key={key} style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: "0.86em", background: C.codeBg, padding: "1px 4px", borderRadius: 4 }}>{m[4]}</code>);
    else out.push(<em key={key}>{m[6] || m[8]}</em>);
    rest = rest.slice(m.index + m[0].length);
  }
  if (!highlights || !highlights.length) return out;
  const final = [];
  out.forEach((piece, i) => {
    if (typeof piece === "string") {
      const hl = applyHighlights(piece, highlights, kp + "h" + i);
      if (Array.isArray(hl)) final.push(...hl); else final.push(hl);
    } else final.push(piece);
  });
  return final;
}

function renderMarkdown(text, highlights) {
  const lines = String(text).split(/\n/);
  const blocks = []; let list = null; let codeBuf = null;
  const flush = () => { if (list) { blocks.push(list); list = null; } };
  for (let li = 0; li < lines.length; li++) {
    const line = lines[li];
    // Fenced code block: ``` or ```lang
    const fence = line.match(/^\s*```(\w[\w+.-]*)?\s*$/);
    if (fence) {
      if (codeBuf == null) { flush(); codeBuf = { lang: (fence[1] || "").toLowerCase(), lines: [] }; }
      else { blocks.push({ type: "code", lang: codeBuf.lang, lines: codeBuf.lines }); codeBuf = null; }
      continue;
    }
    if (codeBuf) { codeBuf.lines.push(line); continue; }
    // Horizontal rule
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) { flush(); blocks.push({ type: "hr" }); continue; }
    const b = line.match(/^\s*[-*•]\s+(.*)$/);
    const n = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const h = line.match(/^\s*(#{1,3})\s+(.*)$/);
    if (b) { if (!list || list.type !== "ul") { flush(); list = { type: "ul", items: [] }; } list.items.push(b[1]); }
    else if (n) { if (!list || list.type !== "ol") { flush(); list = { type: "ol", items: [] }; } list.items.push(n[1]); }
    else { flush(); if (h) blocks.push({ type: "h", text: h[2] }); else blocks.push({ type: line.trim() ? "p" : "sp", text: line }); }
  }
  if (codeBuf) blocks.push({ type: "code", lang: codeBuf.lang, lines: codeBuf.lines }); // unterminated fence
  flush();
  return blocks.map((bl, i) => {
    if (bl.type === "ul") return <ul key={i} style={{ margin: "4px 0", paddingLeft: 18 }}>{bl.items.map((it, j) => <li key={j} style={{ marginBottom: 3 }}>{highlightedMarkdownInline(it, i + "-" + j, highlights)}</li>)}</ul>;
    if (bl.type === "ol") return <ol key={i} style={{ margin: "4px 0", paddingLeft: 20 }}>{bl.items.map((it, j) => <li key={j} style={{ marginBottom: 3 }}>{highlightedMarkdownInline(it, i + "-" + j, highlights)}</li>)}</ol>;
    if (bl.type === "h") return <div key={i} style={{ fontWeight: 700, margin: "6px 0 2px" }}>{highlightedMarkdownInline(bl.text, "h" + i, highlights)}</div>;
    if (bl.type === "hr") return <hr key={i} style={{ border: "none", borderTop: "1px solid var(--hairline)", margin: "10px 0" }} />;
    if (bl.type === "code") return <CodeBlock key={i} lang={bl.lang} lines={bl.lines} highlights={highlights} />;
    if (bl.type === "sp") return <div key={i} style={{ height: 6 }} />;
    return <div key={i} style={{ marginBottom: 4 }}>{highlightedMarkdownInline(bl.text, "p" + i, highlights)}</div>;
  });
}

// ---- Single-branch export to portable note formats (OneNote, Obsidian, Notion, Evernote, …) ----
// Facet bodies are already markdown, so markdown is the canonical export and HTML is derived from
// it. Rich HTML placed on the clipboard pastes into OneNote / Word / Notion / Evernote with
// formatting intact; the .md download imports cleanly into Obsidian / Logseq / Bear / Joplin.
const EXPORT_FACETS = [["context", "Context"], ["summary", "Summary"], ["sources", "Authoritative source"], ["action", "Suggested action"]];

function escHtml(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

// inline markdown → html, mirroring mdInline: **bold**, `code`, *italic*, _italic_
function mdInlineHtml(text) {
  const codes = [];
  let s = escHtml(text).replace(/`([^`]+?)`/g, (m, a) => { codes.push(a); return " " + (codes.length - 1) + " "; });
  s = s.replace(/\*\*([^*]+?)\*\*/g, (m, a) => "<strong>" + a + "</strong>");
  s = s.replace(/\*([^*]+?)\*/g, (m, a) => "<em>" + a + "</em>");
  s = s.replace(/_([^_]+?)_/g, (m, a) => "<em>" + a + "</em>");
  s = s.replace(/ (\d+) /g, (m, i) => "<code>" + codes[+i] + "</code>");
  return s;
}

// block markdown → html. Headings shift +2 so a facet body's own headings stay subordinate
// to the note skeleton (h1 title / h2 section / h3 facet).
function mdBlockHtml(md) {
  const lines = String(md).split(/\n/); const out = []; let list = null, code = null;
  const closeList = () => { if (list) { out.push("</" + list + ">"); list = null; } };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fence = line.match(/^\s*```(\w[\w+.-]*)?\s*$/);
    if (fence) { if (code == null) { closeList(); code = []; } else { out.push("<pre><code>" + code.map(escHtml).join("\n") + "</code></pre>"); code = null; } continue; }
    if (code) { code.push(line); continue; }
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) { closeList(); out.push("<hr>"); continue; }
    const b = line.match(/^\s*[-*•]\s+(.*)$/), n = line.match(/^\s*\d+[.)]\s+(.*)$/), h = line.match(/^\s*(#{1,3})\s+(.*)$/);
    if (b) { if (list !== "ul") { closeList(); out.push("<ul>"); list = "ul"; } out.push("<li>" + mdInlineHtml(b[1]) + "</li>"); }
    else if (n) { if (list !== "ol") { closeList(); out.push("<ol>"); list = "ol"; } out.push("<li>" + mdInlineHtml(n[1]) + "</li>"); }
    else if (h) { closeList(); const lvl = Math.min(6, h[1].length + 2); out.push("<h" + lvl + ">" + mdInlineHtml(h[2]) + "</h" + lvl + ">"); }
    else if (line.trim()) { closeList(); out.push("<p>" + mdInlineHtml(line) + "</p>"); }
    else closeList();
  }
  if (code) out.push("<pre><code>" + code.map(escHtml).join("\n") + "</code></pre>");
  closeList();
  return out.join("\n");
}

// walk a node's messages into ordered { kind, label, body(markdown) } sections for export
function branchSections(node) {
  const secs = [];
  (node.messages || []).forEach((m) => {
    if (m.role === "user" && !m.relate) { if ((m.content || "").trim()) secs.push({ kind: "q", label: "You asked", body: m.content }); }
    else if (m.role === "tool") { /* verbose tool output omitted from notes */ }
    else if (m.tabs) { EXPORT_FACETS.forEach(([k, lbl]) => { const body = (m.tabs[k] || "").trim(); if (body) secs.push({ kind: "facet", label: lbl, body }); }); }
    else if (m.relate) { if ((m.content || "").trim()) secs.push({ kind: "relate", label: "Relates back to origin", body: m.content }); }
    else if ((m.content || "").trim()) secs.push({ kind: "a", label: "Answer", body: m.content });
  });
  return secs;
}

function branchToMarkdown(node) {
  const L = ["# " + (nodeTitle(node) || "Untitled branch"), ""];
  if (node.sourceQuote) L.push("> Branched from: “" + node.sourceQuote + "”", "");
  branchSections(node).forEach((s) => { L.push((s.kind === "facet" ? "### " : "## ") + s.label, "", s.body.trim(), ""); });
  L.push("---", "*Exported from NetClaw Canvas*");
  return L.join("\n");
}

function branchToHtmlFragment(node) {
  const P = ["<h1>" + escHtml(nodeTitle(node) || "Untitled branch") + "</h1>"];
  if (node.sourceQuote) P.push("<blockquote><em>Branched from: “" + escHtml(node.sourceQuote) + "”</em></blockquote>");
  branchSections(node).forEach((s) => {
    P.push(s.kind === "facet" ? "<h3>" + escHtml(s.label) + "</h3>" : "<h2>" + escHtml(s.label) + "</h2>");
    P.push(mdBlockHtml(s.body));
  });
  P.push("<hr><p><small>Exported from NetClaw Canvas</small></p>");
  return P.join("\n");
}

function branchToHtmlDoc(node) {
  const title = escHtml(nodeTitle(node) || "Untitled branch");
  return `<!doctype html>
<html><head><meta charset="utf-8"><title>${title}</title>
<style>body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.55;max-width:760px;margin:40px auto;padding:0 20px;color:#1a1a1a}h1{font-size:1.6em}h2{margin-top:1.4em;font-size:1.2em}h3{margin-top:1em;font-size:1.02em;color:#444}blockquote{border-left:3px solid #ccc;margin:0 0 1em;padding-left:12px;color:#666}code{background:#f2f2f2;padding:1px 4px;border-radius:4px;font-size:.9em}pre{background:#f6f6f6;padding:10px;border-radius:6px;overflow:auto}pre code{background:none;padding:0}hr{border:none;border-top:1px solid #e5e5e5;margin:24px 0}small{color:#888}</style>
</head><body>
${branchToHtmlFragment(node)}
</body></html>`;
}

async function copyRich(html, text) {
  try {
    if (navigator.clipboard && typeof window !== "undefined" && window.ClipboardItem) {
      await navigator.clipboard.write([new window.ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" }),
      })]);
      return true;
    }
  } catch {}
  try { await navigator.clipboard.writeText(text); return true; } catch {}
  return false;
}

function downloadTextFile(name, mime, content) {
  try {
    const url = URL.createObjectURL(new Blob([content], { type: mime }));
    const a = document.createElement("a");
    a.href = url; a.download = name; a.target = "_blank"; a.rel = "noopener"; a.style.display = "none";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return true;
  } catch { return false; }
}

function branchFileName(node) {
  const t = (nodeTitle(node) || "branch").replace(/[\\/:*?"<>|]+/g, " ").replace(/\s+/g, " ").trim().slice(0, 60);
  return t || "branch";
}

// Tool call + result block. Renders MCP style tool output (read_file, list_dir, search_files)
// as a dark monospace card with structured rendering per tool. Selectable text so the
// existing highlight to branch chip works on tool output unchanged.
function ToolBlock({ msg, color, onSelect, onBranchLine }) {
  const [open, setOpen] = useState(true);
  const args = msg.input ? Object.entries(msg.input).map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`).join(" ") : "";
  let parsed = null;
  if (!msg.running && msg.content && !msg.error) { try { parsed = JSON.parse(msg.content); } catch {} }
  const bgDark = "#0F1116", surfDark = "#14171C", lineDark = "#2A2E35", txtPrim = "#CFD2D8", txtMute = "#6F7884", numCol = "#4A5260", kwCol = "#C678DD", strCol = "#98C379", fnCol = "#61AFEF", numLit = "#E5C07B";
  const subtitle = msg.toolName === "read_file" && parsed ? `${parsed.path} · ${parsed.truncated ? "truncated · " : ""}${parsed.bytes} bytes`
    : msg.toolName === "list_dir" && Array.isArray(parsed) ? `${parsed.length} entr${parsed.length === 1 ? "y" : "ies"}`
    : msg.toolName === "search_files" && parsed ? `query "${parsed.query}" · ${parsed.matches?.length || 0} matches`
    : args || "";
  return (
    <div style={{ alignSelf: "stretch", width: "100%", background: bgDark, borderRadius: 8, border: "1px solid " + lineDark, overflow: "hidden" }}>
      <div onClick={() => setOpen((o) => !o)} style={{ background: surfDark, padding: "6px 11px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: open ? "1px solid " + lineDark : "none", cursor: "pointer", userSelect: "none" }}>
        <div style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 11, color: "#9CB1D2", letterSpacing: 0.5 }}>
          <span style={{ color: msg.error ? "#E24B4A" : msg.running ? "#E5C07B" : "#5FCAA5", marginRight: 6 }}>{msg.running ? "◌" : msg.error ? "✕" : "⚙"}</span>
          TOOL · local · {msg.toolName}
          {msg.running && <span style={{ color: txtMute, marginLeft: 8, fontStyle: "italic" }}>running…</span>}
        </div>
        <span style={{ fontFamily: "ui-monospace, monospace", fontSize: 10, color: txtMute }}>{open ? "▾" : "▸"}</span>
      </div>
      {subtitle && open && (
        <div style={{ background: surfDark, padding: "3px 11px", fontFamily: "ui-monospace, Menlo, monospace", fontSize: 10.5, color: txtMute, borderBottom: "1px solid " + lineDark }}>{subtitle}</div>
      )}
      {open && (
        <div onMouseUp={onSelect} style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12, lineHeight: 1.55, color: txtPrim, padding: "6px 0", maxHeight: 360, overflowY: "auto", cursor: "text" }}>
          {msg.error ? (
            <div style={{ padding: "4px 12px", color: "#E24B4A" }}>{msg.content}</div>
          ) : msg.toolName === "read_file" && parsed && parsed.content ? (
            (() => {
              const lines = parsed.content.split("\n");
              const pad = String(lines.length).length;
              return (
                <>
                  {lines.map((ln, i) => (
                    <div key={i} style={{ display: "flex", padding: "0 12px", whiteSpace: "pre" }}>
                      <span style={{ color: numCol, width: pad * 8 + 6, textAlign: "right", marginRight: 12, flexShrink: 0, userSelect: "none" }}>{i + 1}</span>
                      <span style={{ color: txtPrim }}>{syntaxLine(ln, parsed.path, { kwCol, strCol, fnCol, numLit, txtPrim })}</span>
                    </div>
                  ))}
                  {parsed.truncated && <div style={{ textAlign: "center", padding: "6px 0", color: numCol, fontSize: 11, borderTop: "1px dashed " + lineDark, marginTop: 4 }}>… file truncated at {FSA_MAX_FILE_BYTES} bytes</div>}
                </>
              );
            })()
          ) : msg.toolName === "list_dir" && Array.isArray(parsed) ? (
            parsed.map((e, i) => (
              <div key={i} style={{ display: "flex", padding: "0 12px", whiteSpace: "pre" }}>
                <span style={{ color: e.kind === "directory" ? "#5FCAA5" : numCol, marginRight: 8, width: 14, flexShrink: 0 }}>{e.kind === "directory" ? "▸" : "·"}</span>
                <span style={{ color: e.kind === "directory" ? "#5FCAA5" : txtPrim }}>{e.name}{e.kind === "directory" ? "/" : ""}</span>
              </div>
            ))
          ) : msg.toolName === "search_files" && parsed && Array.isArray(parsed.matches) ? (
            parsed.matches.length === 0 ? <div style={{ padding: "4px 12px", color: txtMute }}>no matches</div> :
            parsed.matches.map((m, i) => (
              <div key={i} style={{ display: "flex", padding: "0 12px", whiteSpace: "pre", borderBottom: i < parsed.matches.length - 1 ? "1px dotted " + lineDark : "none", paddingBottom: 2, paddingTop: 2 }}>
                <span style={{ color: fnCol, marginRight: 10, flexShrink: 0 }}>{m.path}:{m.line}</span>
                <span style={{ color: txtPrim }}>{m.text}</span>
              </div>
            ))
          ) : msg.content ? (
            <div style={{ padding: "0 12px", whiteSpace: "pre-wrap" }}>{msg.content}</div>
          ) : (
            <div style={{ padding: "4px 12px", color: txtMute, fontStyle: "italic" }}>…</div>
          )}
        </div>
      )}
    </div>
  );
}

// extremely light syntax tinting for common code; not a real lexer
// Aliases the model uses in code fences for common languages
const LANG_ALIAS = { python: "py", javascript: "js", typescript: "ts", node: "js", "node.js": "js", bash: "sh", shell: "sh", zsh: "sh", "c++": "cpp", "objective-c": "c", golang: "go", rust: "rs", ruby: "rb", html: "xml" };
const CODE_EXTS = new Set(["js", "jsx", "ts", "tsx", "py", "go", "rs", "java", "c", "cpp", "h", "rb", "sh", "yml", "yaml", "json", "css", "xml", "kt", "swift", "php", "sql"]);

// Theme aware default colors driven by CSS vars; light/dark variants live in LIGHT/DARK.
const SYNTAX_DEFAULT = { kwCol: "var(--codeKw)", strCol: "var(--codeStr)", fnCol: "var(--codeFn)", numLit: "var(--codeNum)", txtPrim: "var(--codeText)", cmtCol: "var(--codeCmt)" };

function syntaxLine(line, pathOrLang, c) {
  c = c || SYNTAX_DEFAULT;
  const raw = String(pathOrLang || "").toLowerCase();
  const stem = raw.includes(".") ? raw.split(".").pop() : raw;
  const ext = LANG_ALIAS[stem] || stem;
  if (!CODE_EXTS.has(ext)) return line;
  const KW = ["import", "from", "export", "default", "function", "const", "let", "var", "return", "if", "else", "for", "while", "in", "of", "class", "def", "async", "await", "new", "try", "catch", "throw", "true", "false", "null", "None", "True", "False", "package", "func", "type", "struct", "interface", "switch", "case", "break", "continue", "with", "as", "lambda", "yield", "raise", "pass", "self", "this", "void", "int", "float", "string", "bool", "string", "fn", "pub", "mod", "use", "go", "defer", "chan", "select", "range", "make", "map"];
  const cmtColor = c.cmtCol || (c.txtPrim ? c.txtPrim : "currentColor");
  const cmtOpacity = c.cmtCol ? 1 : 0.55;
  const parts = [];
  let buf = ""; let i = 0; let key = 0;
  const flush = () => { if (buf) { parts.push(<span key={"t" + key++}>{buf}</span>); buf = ""; } };
  while (i < line.length) {
    const ch = line[i];
    if (ch === '"' || ch === "'" || ch === "`") {
      flush();
      let j = i + 1;
      while (j < line.length && line[j] !== ch) { if (line[j] === "\\") j++; j++; }
      parts.push(<span key={"s" + key++} style={{ color: c.strCol }}>{line.slice(i, j + 1)}</span>);
      i = j + 1; continue;
    }
    if (ch === "#" && (ext === "py" || ext === "sh" || ext === "yml" || ext === "yaml" || ext === "rb")) { flush(); parts.push(<span key={"c" + key++} style={{ color: cmtColor, opacity: cmtOpacity }}>{line.slice(i)}</span>); return parts; }
    if (ch === "/" && line[i + 1] === "/") { flush(); parts.push(<span key={"c" + key++} style={{ color: cmtColor, opacity: cmtOpacity }}>{line.slice(i)}</span>); return parts; }
    if (/[A-Za-z_]/.test(ch)) {
      let j = i;
      while (j < line.length && /[A-Za-z0-9_]/.test(line[j])) j++;
      const word = line.slice(i, j);
      flush();
      if (KW.includes(word)) parts.push(<span key={"k" + key++} style={{ color: c.kwCol }}>{word}</span>);
      else if (line[j] === "(") parts.push(<span key={"f" + key++} style={{ color: c.fnCol }}>{word}</span>);
      else parts.push(<span key={"w" + key++}>{word}</span>);
      i = j; continue;
    }
    if (/[0-9]/.test(ch)) {
      let j = i;
      while (j < line.length && /[0-9.]/.test(line[j])) j++;
      flush();
      parts.push(<span key={"n" + key++} style={{ color: c.numLit }}>{line.slice(i, j)}</span>);
      i = j; continue;
    }
    buf += ch; i++;
  }
  flush();
  return parts;
}

// Same tokenizer as syntaxLine but returns [{text, style}] intervals so a caller can
// splice highlight ranges through them without losing the syntax tinting.
function syntaxTokens(line, pathOrLang) {
  const raw = String(pathOrLang || "").toLowerCase();
  const stem = raw.includes(".") ? raw.split(".").pop() : raw;
  const ext = LANG_ALIAS[stem] || stem;
  if (!CODE_EXTS.has(ext)) return [{ text: line, style: {} }];
  const KW = ["import", "from", "export", "default", "function", "const", "let", "var", "return", "if", "else", "for", "while", "in", "of", "class", "def", "async", "await", "new", "try", "catch", "throw", "true", "false", "null", "None", "True", "False", "package", "func", "type", "struct", "interface", "switch", "case", "break", "continue", "with", "as", "lambda", "yield", "raise", "pass", "self", "this", "void", "int", "float", "string", "bool", "fn", "pub", "mod", "use", "go", "defer", "chan", "select", "range", "make", "map"];
  const tokens = [];
  let buf = "";
  const flushBuf = () => { if (buf) { tokens.push({ text: buf, style: {} }); buf = ""; } };
  let i = 0;
  while (i < line.length) {
    const ch = line[i];
    if (ch === '"' || ch === "'" || ch === "`") {
      flushBuf();
      let j = i + 1;
      while (j < line.length && line[j] !== ch) { if (line[j] === "\\") j++; j++; }
      tokens.push({ text: line.slice(i, j + 1), style: { color: "var(--codeStr)" } });
      i = j + 1; continue;
    }
    if (ch === "#" && (ext === "py" || ext === "sh" || ext === "yml" || ext === "yaml" || ext === "rb")) { flushBuf(); tokens.push({ text: line.slice(i), style: { color: "var(--codeCmt)" } }); return tokens; }
    if (ch === "/" && line[i + 1] === "/") { flushBuf(); tokens.push({ text: line.slice(i), style: { color: "var(--codeCmt)" } }); return tokens; }
    if (/[A-Za-z_]/.test(ch)) {
      let j = i;
      while (j < line.length && /[A-Za-z0-9_]/.test(line[j])) j++;
      const word = line.slice(i, j);
      flushBuf();
      if (KW.includes(word)) tokens.push({ text: word, style: { color: "var(--codeKw)" } });
      else if (line[j] === "(") tokens.push({ text: word, style: { color: "var(--codeFn)" } });
      else tokens.push({ text: word, style: {} });
      i = j; continue;
    }
    if (/[0-9]/.test(ch)) {
      let j = i;
      while (j < line.length && /[0-9.]/.test(line[j])) j++;
      flushBuf();
      tokens.push({ text: line.slice(i, j), style: { color: "var(--codeNum)" } });
      i = j; continue;
    }
    buf += ch; i++;
  }
  flushBuf();
  return tokens;
}

// Render one line of code with both syntax tinting AND highlight underlines. Walks
// through the tokens and the highlight ranges together; when a highlight crosses a
// token boundary, both spans get their piece of the highlight underline plus their
// own syntax color. This preserves per keyword tinting under branched substrings.
function renderCodeLineWithHighlights(line, langHint, highlights, kp) {
  const tokens = syntaxTokens(line, langHint);
  // Find every occurrence of every highlight quote in the line
  const ranges = [];
  if (highlights && highlights.length) {
    for (const h of highlights) {
      if (!h || !h.quote) continue;
      let idx = 0;
      while ((idx = line.indexOf(h.quote, idx)) !== -1) {
        ranges.push({ start: idx, end: idx + h.quote.length, color: h.color });
        idx += h.quote.length || 1;
      }
    }
  }
  if (!ranges.length) return tokens.map((t, i) => <span key={kp + "-t" + i} style={t.style}>{t.text}</span>);
  // Drop overlaps: earlier start wins, longer wins on tie
  ranges.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));
  const clean = [];
  for (const r of ranges) if (!clean.length || clean[clean.length - 1].end <= r.start) clean.push(r);
  // Walk tokens and slice on range boundaries
  const out = [];
  let pos = 0, key = 0;
  for (const tok of tokens) {
    const tStart = pos, tEnd = pos + tok.text.length;
    const overlaps = clean.filter((r) => r.start < tEnd && r.end > tStart);
    if (!overlaps.length) { out.push(<span key={kp + "-t" + (key++)} style={tok.style}>{tok.text}</span>); pos = tEnd; continue; }
    let cursor = tStart;
    for (const r of overlaps) {
      const rs = Math.max(r.start, tStart), re = Math.min(r.end, tEnd);
      if (cursor < rs) out.push(<span key={kp + "-t" + (key++)} style={tok.style}>{tok.text.slice(cursor - tStart, rs - tStart)}</span>);
      const seg = tok.text.slice(rs - tStart, re - tStart);
      const hlStyle = { ...tok.style, background: r.color + "4D", boxShadow: `inset 0 -3px 0 ${r.color}`, fontWeight: 600, borderRadius: 2 };
      out.push(<span key={kp + "-h" + (key++)} title="branched from here" style={hlStyle}>{seg}</span>);
      cursor = re;
    }
    if (cursor < tEnd) out.push(<span key={kp + "-t" + (key++)} style={tok.style}>{tok.text.slice(cursor - tStart)}</span>);
    pos = tEnd;
  }
  return out;
}

// Block level renderer for a fenced code block in chat markdown.
function CodeBlock({ lang, lines, highlights }) {
  return (
    <div style={{ position: "relative", margin: "8px 0", background: "var(--codeBg)", border: "1px solid var(--hairline)", borderRadius: 8, overflow: "hidden" }}>
      {lang && (
        <div style={{ position: "absolute", top: 4, right: 8, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 10, color: "var(--muted)", letterSpacing: 0.5, textTransform: "uppercase", pointerEvents: "none" }}>{lang}</div>
      )}
      <div style={{ padding: "8px 12px", overflowX: "auto", fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12.5, lineHeight: 1.55, color: "var(--codeText)" }}>
        {lines.length === 0 ? <div style={{ color: "var(--muted)" }}>&nbsp;</div> : lines.map((ln, i) => (
          <div key={i} style={{ whiteSpace: "pre" }}>{renderCodeLineWithHighlights(ln, lang, highlights, "c" + i) || "\u00A0"}</div>
        ))}
      </div>
    </div>
  );
}

function TabbedAnswer({ tabs, color, onSelect, highlights, defaultTab }) {
  const [tab, setTab] = useState(() => (["context", "summary", "sources", "action"].includes(defaultTab) ? defaultTab : "context"));
  const labels = [["context", "Context"], ["summary", "Summary"], ["sources", "Authoritative source"], ["action", "Suggestive action"]];
  const body = tabs[tab] || "";
  // colors of any branches whose source text lives inside this tab (deduped)
  const tabColors = (key) => {
    const t = tabs[key] || ""; if (!highlights || !t) return [];
    const seen = new Set(), out = [];
    highlights.forEach((h) => { if (h.quote && t.indexOf(h.quote) !== -1 && !seen.has(h.color)) { seen.add(h.color); out.push(h.color); } });
    return out;
  };
  return (
    <div style={{ alignSelf: "stretch", width: "100%", background: C.card, border: `1px solid ${C.hairline}`, borderRadius: "10px 10px 10px 2px", overflow: "hidden" }}>
      <div style={{ display: "flex", borderBottom: `1px solid ${C.hairline}` }}>
        {labels.map(([k, lbl]) => {
          const dots = tabColors(k);
          return (
            <button key={k} onClick={() => setTab(k)}
              style={{ flex: 1, minWidth: 0, padding: "5px 4px", border: "none", borderBottom: tab === k ? `2px solid ${color}` : "2px solid transparent", background: tab === k ? C.card : C.cardAlt, color: tab === k ? C.ink : C.muted, fontSize: 9.5, fontWeight: tab === k ? 600 : 500, cursor: "pointer", fontFamily: "ui-monospace, Menlo, monospace", letterSpacing: 0.1, lineHeight: 1.15, textAlign: "center" }}
              title={dots.length ? `${dots.length} branch${dots.length > 1 ? "es" : ""} sourced from here` : undefined}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                <div style={{ display: "flex", gap: 2, height: 5 }}>
                  {dots.map((c, ix) => <span key={ix} style={{ width: 5, height: 5, borderRadius: "50%", background: c, boxShadow: `0 0 0 1px ${c}55` }} />)}
                </div>
                <span>{lbl}</span>
              </div>
            </button>
          );
        })}
      </div>
      <div onMouseUp={onSelect} style={{ padding: "9px 11px", fontSize: 13.5, lineHeight: 1.5, color: C.ink, cursor: "text" }}>
        {body ? renderMarkdown(body, highlights) : <span style={{ color: C.muted, fontStyle: "italic", fontSize: 12 }}>none provided</span>}
      </div>
    </div>
  );
}

function Lane({ node, color, isActive, selected, highlights, synthSources, animate, dark, defaultTab, laneRef, onFocus, onDragStart, onResizeStart, onSelect, onToggleMin, onDelete, draft, setDraft, pendingQuote, onClearQuote, attachments, onAddFiles, onRemoveImage, onSend, onAutoHeight, onAutoFit }) {
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);
  const contentRef = useRef(null);
  const isSynth = !!(synthSources && synthSources.length);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [node.messages.length, node.loading]);

  // ---- per-branch export (Copy rich / Markdown / HTML) ----
  // The Lane sits inside overflow:hidden + a scaled canvas, so the menu is portalled to
  // document.body and positioned from the button's on-screen rect.
  const exportBtnRef = useRef(null);
  const [expOpen, setExpOpen] = useState(false);
  const [expPos, setExpPos] = useState(null);
  const [expMsg, setExpMsg] = useState(null);
  const flash = (msg) => { setExpMsg(msg); setTimeout(() => setExpMsg(null), 2400); };
  const hasContent = branchSections(node).length > 0;
  const toggleExport = () => {
    if (expOpen) { setExpOpen(false); return; }
    const r = exportBtnRef.current && exportBtnRef.current.getBoundingClientRect();
    if (r) setExpPos({ top: r.bottom + 4, right: Math.max(8, (typeof window !== "undefined" ? window.innerWidth : 0) - r.right) });
    setExpOpen(true);
  };
  const doCopy = async () => { setExpOpen(false); const ok = await copyRich(branchToHtmlFragment(node), branchToMarkdown(node)); flash(ok ? "Copied — paste into OneNote, Notion, Word…" : "Copy blocked by browser"); };
  const doMd = () => { setExpOpen(false); const ok = downloadTextFile(branchFileName(node) + ".md", "text/markdown;charset=utf-8", branchToMarkdown(node)); flash(ok ? "Markdown downloaded" : "Download blocked"); };
  const doHtml = () => { setExpOpen(false); const ok = downloadTextFile(branchFileName(node) + ".html", "text/html;charset=utf-8", branchToHtmlDoc(node)); flash(ok ? "HTML downloaded" : "Download blocked"); };
  useEffect(() => {
    if (!expOpen) return;
    const onDown = (e) => { if (exportBtnRef.current && exportBtnRef.current.contains(e.target)) return; if (e.target.closest && e.target.closest("[data-export-menu]")) return; setExpOpen(false); };
    const onEsc = (e) => { if (e.key === "Escape") setExpOpen(false); };
    document.addEventListener("mousedown", onDown, true);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onDown, true); document.removeEventListener("keydown", onEsc); };
  }, [expOpen]);

  // auto-fit height to content unless the user has manually resized
  useEffect(() => {
    if (node.manual || node.min) return;
    const sc = scrollRef.current, ct = contentRef.current;
    if (!sc || !ct) return;
    const MAXH = Math.round((typeof window !== "undefined" ? window.innerHeight : 900) * 0.82);
    const ideal = Math.round((node.h - sc.clientHeight) + ct.offsetHeight);
    const clamped = Math.max(MIN_H, Math.min(ideal, MAXH));
    if (Math.abs(clamped - node.h) > 1) onAutoHeight(clamped);
  }, [node.messages, node.loading, node.w, node.manual, node.min]);

  // For synthesis nodes, build a sharp-stop linear gradient for the left edge: one band per source.
  const synthEdge = isSynth
    ? `linear-gradient(to bottom, ${synthSources.map((s, i) => `${s.color} ${((i / synthSources.length) * 100).toFixed(2)}%, ${s.color} ${(((i + 1) / synthSources.length) * 100).toFixed(2)}%`).join(", ")})`
    : null;

  return (
    <div ref={laneRef} onMouseDown={onFocus} className="lane-in"
      style={{ position: "absolute", left: node.x, top: node.y, width: node.w, height: node.min ? COLLAPSED_H : node.h, zIndex: node.z,
        transition: animate ? "left .35s cubic-bezier(.22,1,.36,1), top .35s cubic-bezier(.22,1,.36,1), width .3s cubic-bezier(.22,1,.36,1)" : "none",
        display: "flex", flexDirection: "column", borderRadius: 12, background: C.card,
        border: `1px solid ${isActive ? color : C.hairline}`,
        ...(isSynth ? { borderLeft: "none" } : { borderLeft: `4px solid ${color}` }),
        boxShadow: isActive ? `0 0 0 2px var(--ring), 0 12px 30px var(--shadow)` : `0 4px 14px var(--shadow)`, overflow: "hidden",
        ...(selected && !isActive ? { outline: `2px solid ${color}`, outlineOffset: 1 } : {}) }}>

      {/* synthesis multi-band left edge (replaces the single-color border-left) */}
      {isSynth && (
        <div aria-hidden style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 5, background: synthEdge, zIndex: 1, pointerEvents: "none" }} />
      )}

      {/* drag handle / header */}
      <div onMouseDown={onDragStart} onDoubleClick={(e) => { e.stopPropagation(); onToggleMin(); }} title={node.min ? "double-click to expand" : "double-click to collapse"}
        style={{ padding: "9px 12px", paddingLeft: isSynth ? 16 : 12, borderBottom: node.min ? "none" : `1px solid ${C.hairline}`, display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 6, cursor: "grab", userSelect: "none", flexShrink: 0 }}>
        <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ fontFamily: "ui-monospace, monospace", fontSize: 10, letterSpacing: 1, textTransform: "uppercase", color, display: "flex", alignItems: "center", gap: 6 }}>
            <span>{isSynth ? `⊕  synthesis · ${synthSources.length} sources` : (node.depth === 0 ? "⋮⋮  main thread" : `⋮⋮  branch · depth ${node.depth}`)}</span>
            {node.loading && <span title="thinking…" style={{ width: 6, height: 6, borderRadius: "50%", background: color, animation: "pulse 1s infinite", display: "inline-block" }} />}
          </span>
          {isSynth ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 1, marginTop: 2 }}>
              {synthSources.map((s, i) => (
                <span key={i} style={{ fontSize: 11.5, color: C.muted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
                  <span>{s.title}</span>
                </span>
              ))}
            </div>
          ) : (
            node.sourceQuote && <span style={{ fontSize: 12, color: C.muted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>↳ from “{node.sourceQuote}”</span>
          )}
        </div>
        <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
          {hasContent && (
            <button ref={exportBtnRef} onMouseDown={(e) => e.stopPropagation()} onClick={toggleExport} title="export this branch to OneNote, Notion, Obsidian…"
              style={{ width: 20, height: 20, border: "none", background: expOpen ? C.userBubble : "transparent", color: C.muted, cursor: "pointer", fontSize: 13, lineHeight: 1, borderRadius: 4 }}>⇪</button>
          )}
          <button onMouseDown={(e) => e.stopPropagation()} onClick={onToggleMin} title={node.min ? "expand" : "minimize"}
            style={{ width: 20, height: 20, border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 14, lineHeight: 1, borderRadius: 4 }}>{node.min ? "▣" : "–"}</button>
          <button onMouseDown={(e) => e.stopPropagation()} onClick={onDelete} title={node.depth === 0 ? "close this main thread; stays in the sidebar" : "close this branch; stays in the sidebar"}
            style={{ width: 20, height: 20, border: "none", background: "transparent", color: "#A8324E", cursor: "pointer", fontSize: 15, lineHeight: 1, borderRadius: 4 }}>×</button>
        </div>
      </div>

      {/* export menu + toast, portalled to escape the lane's overflow:hidden and the scaled canvas */}
      {expOpen && expPos && createPortal(
        <div data-export-menu onMouseDown={(e) => e.stopPropagation()}
          style={{ position: "fixed", top: expPos.top, right: expPos.right, zIndex: 600, minWidth: 232, background: C.card, border: `1px solid ${C.hairline}`, borderRadius: 9, boxShadow: "0 12px 32px rgba(0,0,0,0.28)", padding: "5px 0", ...(dark ? DARK : LIGHT) }}>
          <div style={{ padding: "4px 13px 5px", fontFamily: "ui-monospace, Menlo, monospace", fontSize: 9, letterSpacing: 0.7, textTransform: "uppercase", color: C.muted }}>Export this branch</div>
          {[["📋", "Copy (rich text)", "OneNote · Notion · Word · Evernote", doCopy],
            ["⤓", "Markdown (.md)", "Obsidian · Logseq · Bear · Joplin", doMd],
            ["⤓", "HTML (.html)", "standalone · insert into OneNote", doHtml]].map(([ic, lbl, sub, fn], i) => (
            <button key={i} onClick={fn}
              onMouseEnter={(e) => (e.currentTarget.style.background = C.userBubble)} onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              style={{ display: "flex", alignItems: "flex-start", gap: 9, width: "100%", textAlign: "left", border: "none", background: "transparent", color: C.ink, cursor: "pointer", padding: "7px 13px" }}>
              <span style={{ fontSize: 13, lineHeight: "16px", flexShrink: 0 }}>{ic}</span>
              <span style={{ minWidth: 0 }}>
                <span style={{ display: "block", fontSize: 12.5, fontWeight: 500 }}>{lbl}</span>
                <span style={{ display: "block", fontSize: 10, color: C.muted, marginTop: 1 }}>{sub}</span>
              </span>
            </button>
          ))}
        </div>, document.body)}
      {expMsg && createPortal(
        <div style={{ position: "fixed", bottom: 22, left: "50%", transform: "translateX(-50%)", zIndex: 620, background: C.trunk, color: "#fff", fontSize: 12, padding: "8px 14px", borderRadius: 8, boxShadow: "0 8px 22px rgba(0,0,0,0.32)", ...(dark ? DARK : LIGHT) }}>{expMsg}</div>,
        document.body)}

      {!node.min && (<>
      {/* messages */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
        <div ref={contentRef} style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
        {node.sourceQuote && (
          <div style={{ alignSelf: "stretch", borderLeft: `3px solid ${color}`, background: C.cardAlt, borderRadius: "0 8px 8px 0", padding: "7px 11px", lineHeight: 1.45 }}>
            <div style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 9.5, letterSpacing: 0.5, textTransform: "uppercase", color, marginBottom: 3 }}>branching from</div>
            <div style={{ fontSize: 12.5, color: C.muted, fontStyle: "italic" }}>“{node.sourceQuote}”</div>
          </div>
        )}
        {node.messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} style={{ alignSelf: "flex-end", maxWidth: "88%", background: C.userBubble, color: C.ink, padding: "8px 11px", borderRadius: "10px 10px 2px 10px", fontSize: 13.5, lineHeight: 1.45 }}>
              {m.quote && (
                <div style={{ borderLeft: `3px solid ${color}`, paddingLeft: 8, marginBottom: 6, fontSize: 12, fontStyle: "italic", color: C.muted, lineHeight: 1.4, maxHeight: 88, overflow: "hidden" }}>“{m.quote}”</div>
              )}
              {m.images && m.images.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: (m.content || (m.files && m.files.length)) ? 6 : 0 }}>
                  {m.images.map((im, k) => (
                    <img key={k} src={imgDataUrl(im)} alt={im.name || "image"} style={{ maxWidth: 160, maxHeight: 160, borderRadius: 8, border: `1px solid ${C.hairline}`, display: "block" }} />
                  ))}
                </div>
              )}
              {m.files && m.files.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: m.content ? 6 : 0 }}>
                  {m.files.map((f, k) => (
                    <span key={k} title={f.name} style={{ display: "inline-flex", alignItems: "center", gap: 5, background: C.card, border: `1px solid ${C.hairline}`, borderRadius: 7, padding: "3px 8px", fontSize: 11.5, color: C.ink, maxWidth: "100%", overflow: "hidden" }}>
                      <span>📄</span><span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}{f.truncated ? " (truncated)" : ""}</span>
                    </span>
                  ))}
                </div>
              )}
              {m.content && applyHighlights(m.content, highlights, "u" + i)}
            </div>
          ) : m.role === "tool" ? (
            <ToolBlock key={i} msg={m} color={color} onSelect={onSelect} />
          ) : m.relate ? (
            <div key={i} style={{ alignSelf: "stretch", width: "100%", background: C.relBg, border: `1px solid ${C.relBorder}`, borderRadius: 10, overflow: "hidden" }}>
              <div style={{ padding: "5px 10px", borderBottom: `1px solid ${C.relBorder}`, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 10, letterSpacing: 0.5, color: C.relText, textTransform: "uppercase" }}>⤴ relates back to origin</div>
              <div onMouseUp={onSelect} style={{ padding: "9px 11px", fontSize: 13.5, lineHeight: 1.5, color: C.ink, cursor: "text" }}>{renderMarkdown(m.content, highlights)}</div>
            </div>
          ) : m.tabs ? (
            <TabbedAnswer key={i} tabs={m.tabs} color={color} onSelect={onSelect} highlights={highlights} defaultTab={defaultTab} />
          ) : (
            <div key={i} onMouseUp={onSelect} style={{ alignSelf: "flex-start", maxWidth: "94%", background: C.card, color: C.ink, padding: "9px 11px", border: `1px solid ${C.hairline}`, borderRadius: "10px 10px 10px 2px", fontSize: 13.5, lineHeight: 1.5, cursor: "text" }}>{renderMarkdown(m.content, highlights)}</div>
          )
        )}
        {node.loading && <div style={{ alignSelf: "flex-start", fontSize: 12, color: C.muted, fontStyle: "italic", display: "flex", gap: 6, alignItems: "center" }}><span style={{ width: 7, height: 7, borderRadius: "50%", background: color, display: "inline-block", animation: "pulse 1s infinite" }} /> thinking…</div>}
        {node.error && <div style={{ fontSize: 12, color: "#A8324E" }}>Couldn’t reach the model: {node.error}. Try again.</div>}
        </div>
      </div>

      {/* input (drop image files here) */}
      <div onDragOver={(e) => { if (Array.from(e.dataTransfer.types || []).includes("Files")) e.preventDefault(); }}
        onDrop={(e) => { if (e.dataTransfer.files && e.dataTransfer.files.length) { e.preventDefault(); onAddFiles(e.dataTransfer.files); } }}
        style={{ padding: 8, borderTop: `1px solid ${C.hairline}`, display: "flex", flexDirection: "column", gap: 6, flexShrink: 0 }}>
        {attachments && attachments.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {attachments.map((it, i) => it.kind === "image" ? (
              <div key={i} title={it.name || "image"} style={{ position: "relative", width: 46, height: 46, borderRadius: 7, overflow: "hidden", border: `1px solid ${C.hairline}`, flexShrink: 0 }}>
                <img src={imgDataUrl(it)} alt={it.name || "image"} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
                <button onClick={() => onRemoveImage(i)} title="remove image"
                  style={{ position: "absolute", top: 1, right: 1, width: 15, height: 15, borderRadius: "50%", border: "none", background: "rgba(0,0,0,0.62)", color: "#fff", cursor: "pointer", fontSize: 11, lineHeight: "15px", padding: 0 }}>×</button>
              </div>
            ) : (
              <div key={i} title={it.name} style={{ display: "flex", alignItems: "center", gap: 6, maxWidth: "100%", background: C.cardAlt, border: `1px solid ${C.hairline}`, borderRadius: 7, padding: "5px 7px", flexShrink: 0 }}>
                <span style={{ fontSize: 13, flexShrink: 0 }}>📄</span>
                <span style={{ fontSize: 11.5, color: C.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 150 }}>{it.name}{it.truncated ? " (truncated)" : ""}</span>
                <button onClick={() => onRemoveImage(i)} title="remove file" style={{ flexShrink: 0, border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 13, lineHeight: 1, padding: "0 1px" }}>×</button>
              </div>
            ))}
          </div>
        )}
        {pendingQuote && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: 6, background: C.cardAlt, border: `1px solid ${C.hairline}`, borderLeft: `3px solid ${color}`, borderRadius: 7, padding: "6px 8px" }}>
            <span style={{ color, fontSize: 12, lineHeight: "16px", flexShrink: 0 }}>❝</span>
            <span style={{ flex: 1, minWidth: 0, fontSize: 12, fontStyle: "italic", color: C.muted, lineHeight: 1.4, maxHeight: 54, overflow: "hidden" }}>{pendingQuote}</span>
            <button onClick={onClearQuote} title="remove quoted context" style={{ flexShrink: 0, border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 13, lineHeight: 1, padding: "0 2px" }}>×</button>
          </div>
        )}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input ref={fileInputRef} type="file" accept="image/*,text/*,application/json,application/xml,.json,.jsonl,.ndjson,.txt,.md,.markdown,.csv,.tsv,.log,.yaml,.yml,.toml,.xml,.html,.css,.js,.jsx,.mjs,.cjs,.ts,.tsx,.py,.go,.rs,.java,.kt,.c,.cc,.cpp,.h,.hpp,.rb,.php,.swift,.sh,.bash,.sql,.graphql,.ini,.conf,.env,.gradle,.ipynb,.tex,.rst,.vue,.svelte" multiple style={{ display: "none" }}
            onChange={(e) => { if (e.target.files && e.target.files.length) onAddFiles(e.target.files); e.target.value = ""; }} />
          <button onClick={() => fileInputRef.current && fileInputRef.current.click()} title="attach a file — image or text/data/code (paste or drop works too)"
            style={{ flexShrink: 0, width: 30, height: 30, border: `1px solid ${C.hairline}`, background: C.card, color: C.muted, borderRadius: 8, cursor: "pointer", fontSize: 14, lineHeight: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>📎</button>
          <input data-composer="1" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") onSend(); }}
            onPaste={(e) => { const files = Array.from(e.clipboardData && e.clipboardData.items || []).filter((it) => it.kind === "file" && it.type.startsWith("image/")).map((it) => it.getAsFile()).filter(Boolean); if (files.length) { e.preventDefault(); onAddFiles(files); } }}
            placeholder={attachments && attachments.length ? "add a note, or just send…" : (pendingQuote ? "ask about the quote…" : (node.depth === 0 ? "ask anything…" : "ask about this…"))}
            // translateZ(0) gives the input its own paint layer so the caret is computed relative to
            // itself — keeps it correctly placed even when the canvas is zoomed to a fractional scale.
            style={{ flex: 1, minWidth: 0, border: `1px solid ${C.hairline}`, borderRadius: 8, padding: "7px 9px", fontSize: 13, outline: "none", color: C.ink, background: C.canvas, transform: "translateZ(0)" }} />
          <button onClick={onSend} disabled={node.loading} style={{ background: color, color: "#fff", border: "none", borderRadius: 8, padding: "0 12px", fontSize: 13, fontWeight: 600, cursor: node.loading ? "default" : "pointer", opacity: node.loading ? 0.5 : 1 }}>↑</button>
        </div>
      </div>

      {/* resize grip */}
      <div onMouseDown={onResizeStart} onDoubleClick={onAutoFit} title="drag to resize · double-click to auto-fit"
        style={{ position: "absolute", right: 0, bottom: 0, width: 18, height: 18, cursor: "nwse-resize",
          background: `linear-gradient(135deg, transparent 50%, ${color} 50%)`, borderBottomRightRadius: 10, opacity: 0.55 }} />
      </>)}
    </div>
  );
}

// ---- Menu and Tutorial components -----------------------------------------
// Generic dropdown menu used by the header menu bar. Click trigger to open;
// clicks outside or Esc close. Items may be { type: "item", label, shortcut,
// action, checked, disabled }, { type: "separator" }, or { type: "header", label }.
function Menu({ label, items }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onEsc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onEsc); };
  }, [open]);
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button onClick={() => setOpen((o) => !o)}
        style={{ fontSize: 13, padding: "5px 10px", borderRadius: 5, border: "none", background: open ? C.userBubble : "transparent", color: C.ink, cursor: "pointer", fontWeight: 500 }}>
        {label}
      </button>
      {open && (
        <div role="menu" style={{ position: "absolute", top: "100%", left: 0, marginTop: 3, minWidth: 240, background: C.card, border: `1px solid ${C.hairline}`, borderRadius: 7, padding: "4px 0", boxShadow: `0 10px 28px var(--shadow)`, zIndex: 500 }}>
          {items.map((it, i) => {
            if (!it) return null;
            if (it.type === "separator") return <div key={i} style={{ height: 1, background: C.hairline, margin: "4px 8px" }} />;
            if (it.type === "header") return <div key={i} style={{ padding: "6px 14px 2px", fontSize: 10, fontFamily: "ui-monospace, Menlo, monospace", letterSpacing: 0.5, textTransform: "uppercase", color: C.muted }}>{it.label}</div>;
            return (
              <button key={i} disabled={it.disabled}
                onClick={() => { if (it.disabled) return; setOpen(false); it.action && it.action(); }}
                onMouseEnter={(e) => { if (!it.disabled) e.currentTarget.style.background = C.userBubble; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, width: "100%", padding: "6px 14px", border: "none", background: "transparent", color: it.disabled ? C.muted : C.ink, cursor: it.disabled ? "not-allowed" : "pointer", fontSize: 13, textAlign: "left", fontFamily: "inherit" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                  <span style={{ width: 14, display: "inline-block", textAlign: "center", flexShrink: 0, color: C.muted }}>{it.checked ? "✓" : ""}</span>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.label}</span>
                </span>
                {it.shortcut && <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 11, color: C.muted, opacity: it.disabled ? 0.5 : 1, flexShrink: 0 }}>{it.shortcut}</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Tutorial walks users through the core concepts. Section IDs anchor the sidebar.
function Tutorial({ onClose }) {
  const sections = [
    { id: "welcome", title: "Welcome" },
    { id: "branching", title: "Threads and branching" },
    { id: "synthesis", title: "Synthesis (the inverse)" },
    { id: "localfiles", title: "Attachments and tools" },
    { id: "layout", title: "Layout: free vs lanes" },
    { id: "sessions", title: "Sessions and persistence" },
    { id: "models", title: "NetClaw gateway" },
    { id: "shortcuts", title: "Keyboard shortcuts" },
  ];
  const scroller = useRef(null);
  const goTo = (id) => { const el = document.getElementById("tut-" + id); if (el && scroller.current) scroller.current.scrollTo({ top: el.offsetTop - 16, behavior: "smooth" }); };

  const H = ({ id, children }) => <h2 id={"tut-" + id} style={{ fontSize: 16, fontWeight: 700, color: C.ink, margin: "22px 0 8px", scrollMarginTop: 16 }}>{children}</h2>;
  const P = ({ children }) => <p style={{ fontSize: 13.5, lineHeight: 1.6, color: C.ink, margin: "6px 0" }}>{children}</p>;
  const K = ({ children }) => <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12, background: "var(--codeBg)", color: "var(--codeText)", padding: "1px 6px", borderRadius: 4, border: `1px solid ${C.hairline}` }}>{children}</span>;
  const Tip = ({ children }) => <div style={{ background: "var(--codeBg)", borderLeft: `3px solid ${C.trunk}`, borderRadius: "0 6px 6px 0", padding: "8px 12px", margin: "10px 0", fontSize: 12.5, color: C.ink, lineHeight: 1.55 }}>{children}</div>;

  return (
    <div onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 320, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ background: C.card, border: `1px solid ${C.hairline}`, borderRadius: 12, width: 880, maxWidth: "100%", height: "85vh", display: "flex", boxShadow: "0 25px 60px rgba(0,0,0,0.35)", overflow: "hidden" }}>
        {/* sidebar */}
        <div style={{ width: 200, flexShrink: 0, borderRight: `1px solid ${C.hairline}`, background: C.cardAlt, display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "14px 16px 8px" }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.ink }}>Tutorial</div>
            <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>NetClaw Canvas in 8 sections</div>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "4px 0" }}>
            {sections.map((s, i) => (
              <button key={s.id} onClick={() => goTo(s.id)}
                style={{ display: "block", width: "100%", textAlign: "left", padding: "7px 16px", border: "none", background: "transparent", color: C.ink, fontSize: 12.5, cursor: "pointer", fontFamily: "inherit" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = C.userBubble)}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                <span style={{ display: "inline-block", width: 18, color: C.muted, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 11 }}>{i + 1}.</span>
                {s.title}
              </button>
            ))}
          </div>
        </div>
        {/* content */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 18px", borderBottom: `1px solid ${C.hairline}` }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: C.ink }}>How to use NetClaw Canvas</div>
            <button onClick={onClose} style={{ border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 18, lineHeight: 1, padding: "2px 6px", borderRadius: 4 }}>×</button>
          </div>
          <div ref={scroller} style={{ flex: 1, overflowY: "auto", padding: "8px 24px 32px" }}>
            <H id="welcome">1. Welcome</H>
            <P>NetClaw Canvas is a branching workspace for the same model and tools used by the Visual HUD. Start one conversation, split an answer into focused side investigations, then merge useful branches into a synthesis node without losing their context.</P>
            <Tip>If you only remember three things: highlight text to branch, shift+click windows to synthesize, and File → Sessions to switch between investigations.</Tip>

            <H id="branching">2. Threads and branching</H>
            <P>Every session starts with one main thread (the trunk). Open more from File → New thread, or with <K>⌘N</K>. Each main thread is independent.</P>
            <P>To branch off an existing answer, highlight any text in it. A floating <K>⎇ Branch this</K> chip appears near your cursor; click it to spawn a child thread. The child inherits the entire parent context plus a focal prompt about the selected text, so you can go deep on one idea without polluting the original thread.</P>
            <P>You can branch from a branch, recursively. The left sidebar shows the full tree.</P>

            <H id="synthesis">3. Synthesis (the inverse)</H>
            <P>Synthesis is the move that makes a tree into a graph. Shift+click two or more windows to select them (or shift+drag a marquee around them). A <K>⊕ Synthesize</K> chip appears next to the selection. Click it, or press <K>⌘J</K>, and a new node spawns to the right with a striped multi-color left edge showing every source it ingested.</P>
            <P>Use it when you've explored multiple angles in parallel and want to ask "what's the common pattern" or "which approach should I take given all three." The model gets the deduplicated union of every selected thread's context.</P>

            <H id="localfiles">4. Attachments and NetClaw tools</H>
            <P>Drop or attach an image, text file, data file, or source file to include it in the next turn. The attachment becomes part of that branch's context and is inherited only by descendants of that branch.</P>
            <P>Network and operational tools are supplied by NetClaw through the OpenClaw gateway. The canvas does not hold provider credentials or replace NetClaw's tool, safety, GAIT, and change-management controls.</P>
            <Tip>Large text attachments are capped before they enter the conversation context. Image support depends on the model configured in the gateway.</Tip>

            <H id="layout">5. Layout: free vs lanes</H>
            <P>By default you drag windows freely. When the canvas gets cluttered, two options under View:</P>
            <P><strong>▦ Tidy</strong> runs a one shot reflow: every visible window snaps into depth columns (trunk left, deeper branches further right), siblings stack vertically under their parent, parents center vertically across their children. Drag remains free afterward.</P>
            <P><strong>▤ Tile</strong> (<K>T</K>) fills the whole canvas: every open window is snapped into a gapless grid that fully covers the viewport at 100%, like Windows snap layouts. Fuller rows sit on top; drag remains free afterward.</P>
            <P><strong>🔒 Lanes</strong> turns Tidy into a persistent lock. New branches auto place, drag is disabled, the layout stays clean. Toggle off to drag freely again.</P>

            <H id="sessions">6. Sessions and persistence</H>
            <P>Every change autosaves to your browser's IndexedDB (capacity is roughly half your disk, so you can keep an indefinite history). File → Sessions opens the library: switch between past sessions, search across them (titles and message contents), export any session as JSON, import one back.</P>
            <P>Sessions are local to this browser. They don't sync across devices. If that matters, export to JSON and re import on the other machine.</P>

            <H id="models">7. NetClaw gateway</H>
            <P>The Canvas uses NetClaw's existing <K>/api/chat</K> proxy, which connects to the local OpenClaw gateway. Model choice, credentials, MCP integrations, skills, and tool execution remain configured in NetClaw.</P>
            <P>The status chip in the header shows whether the gateway is reachable. When it is offline, the server preserves the existing HUD behavior and returns NetClaw's local heuristic response.</P>

            <H id="shortcuts">8. Keyboard shortcuts</H>
            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 16px", margin: "10px 0", fontSize: 13 }}>
              <K>⌘N</K><span>New main thread</span>
              <K>⌘J</K><span>Synthesize selected windows</span>
              <K>⌘Z / ⇧⌘Z</K><span>Undo / redo</span>
              <K>⌘A</K><span>Select all open windows</span>
              <K>F</K><span>Fit active window to view</span>
              <K>O</K><span>Overview: topology map of the whole graph</span>
              <K>Delete / Backspace</K><span>Close selected (stays in sidebar)</span>
              <K>Esc</K><span>Clear selection</span>
              <K>Arrow keys</K><span>Nudge selected (Shift = 10px)</span>
              <K>⌘ + scroll</K><span>Zoom in / out</span>
              <K>drag empty canvas</K><span>Pan the canvas</span>
              <K>shift + drag</K><span>Marquee select</span>
              <K>shift + click window</K><span>Toggle window in selection</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
