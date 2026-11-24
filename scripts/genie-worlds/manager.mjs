import http from "node:http";
import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  openSync,
  closeSync,
  fsyncSync,
  unlinkSync,
  statSync,
  appendFileSync,
  existsSync,
  lstatSync,
} from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { fork } from "node:child_process";
import { randomBytes, createHash } from "node:crypto";
import { WebSocketServer } from "ws";
import { Ledger } from "./ledger.mjs";
import {
  projection,
  fixtureFacts,
  POLICY,
  CAMPAIGN_SESSION_POLICY,
  MANAGER_SHUTDOWN_GRACE_MS,
  hash,
  UUID,
  closed,
  need,
  supportedRuntime,
} from "./model.mjs";
import { nativeAudit } from "./audit.mjs";
import { loadLivePacket, admitReviewedCampaign } from "./live-packet.mjs";
import { Preparations, loadSnapshotBindings } from "./preparation.mjs";
import { CAMPAIGN_POLICY } from "./campaign-budget.mjs";
const token = () => randomBytes(32).toString("hex");
const terminal = (s) => ["terminal", "unknown", "failed_pre_send"].includes(s);
const security = {
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' blob:; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
};
async function body(req, limit = 16384) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    need(size <= limit, "body_too_large");
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}
function safeStatus(s) {
  const { provider_id, terminal_receipt, newly_created, ...rest } = s;
  return {
    ...rest,
    // A reconciled receipt supersedes the current outcome, without erasing the
    // original timeout/loss reason retained in the ledger and audit history.
    ...(terminal_receipt ? { reason: 'provider_terminal_receipt',
      previous_outcome_reason: s.reason || null } : {}),
    terminal_confirmed: Boolean(terminal_receipt),
    terminal_event_type: terminal_receipt?.event_type || null,
    reported_usage: terminal_receipt?.usage || null,
  };
}
export async function createManager({ root, port = 0, audit = null, livePacketPath = null, snapshotRegistryPath = null, campaignEnv = process.env, readOnly = false }) {
  supportedRuntime();
  need(typeof readOnly === 'boolean' && !(readOnly && livePacketPath), 'evidence_mode_requires_no_live_packet');
  // Operator launch configuration only; never inherit later environment changes
  // or unrelated credentials into a worker.
  const campaignPins = Object.freeze(Object.fromEntries([
    'NETCLAW_GENIE_CAMPAIGN_AUTHORITY', 'NETCLAW_GENIE_CAMPAIGN_AUTHORITY_SHA256',
    'NETCLAW_GENIE_CAMPAIGN_REVIEW', 'NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256',
    'NETCLAW_GENIE_APPROVED_PROJECTION', 'NETCLAW_GENIE_APPROVED_PROJECTION_SHA256',
  ].filter(key => campaignEnv[key] !== undefined).map(key => [key, campaignEnv[key]])));
  const snapshots = loadSnapshotBindings(snapshotRegistryPath);
  const selectedProjection=projection();
  if(selectedProjection.classification==='private_derived') need(
    snapshots[selectedProjection.snapshot_ref]?.summary.manifest_sha256===selectedProjection.manifest_sha256,
    'approved_snapshot_binding_required');
  const live = livePacketPath ? loadLivePacket(livePacketPath, campaignPins) : null;
  if (live) {
    need(live.schema === 2, 'campaign_packet_required');
    need(root === live.state_root && audit, "live_audit_and_state_required");
  }
  const liveDigest = live && hash(live);
  function currentLive() {
    const current = loadLivePacket(livePacketPath, campaignPins);
    need(current.schema === 2 && hash(current) === liveDigest, 'live_packet_changed');
    return current;
  }
  const mode = readOnly ? 'evidence' : live ? "google" : "fixture";
  function sessionBounds(session = null) {
    const packet = !session && live ? currentLive() : null;
    const fixture = session ? session.provider === 'fixture' : !live;
    const campaign = session ? session.accounting_version === 'campaign-v1' : Boolean(packet);
    return {
      accounting_mode: fixture ? 'fixture' : campaign ? 'campaign-v1' : 'legacy',
      policy: session?.session_policy || (campaign ? CAMPAIGN_SESSION_POLICY : POLICY),
      estimated_usd: session?.estimated_usd ?? (packet?.allowance_usd || 0),
      estimated_video_usd: session?.estimated_video_usd ?? (campaign ? CAMPAIGN_POLICY.video_bound_microusd / 1_000_000 : null),
      reservation_usd: session?.reserved_usd ?? (packet?.allowance_usd || 0),
      ...(campaign ? { campaign_limits: {
        soft_stop_usd: CAMPAIGN_POLICY.soft_stop_microusd / 1_000_000,
        hard_stop_usd: CAMPAIGN_POLICY.hard_stop_microusd / 1_000_000,
      } } : {}),
    };
  }
  const ledger = new Ledger(root);
  const drafts = new Preparations(ledger, snapshots);
  const status = (s) => ({ ...safeStatus(s), session_bounds: sessionBounds(s), control_requests: ledger.controlResults(s.operation_id) });
  root = ledger.root;
  const lock = join(root, "manager.lock");
  let lockFd;
  try {
    lockFd = openSync(lock, "wx", 0o600);
    writeFileSync(
      lockFd,
      JSON.stringify({
        pid: process.pid,
        started_at: new Date().toISOString(),
      }),
    );
  } catch {
    ledger.close();
    throw new Error("manager_lock_exists_review_required");
  }
  const owner = token(), controlToken = token(),
    bootstrap = token(),
    bootstrapExpires = Date.now() + 60000;
  let bootstrapUsed = false,
    origin;
  const clients = new Map(),
    workers = new Map(),
    websockets = new Map();
  // Bounded original-worker frame provenance; never reconstructed after restart.
  const frameEvidence = new Map();
  let closing = false;
  let closePromise;
  const pendingAudits = new Set();
  const pendingHandlers = new Set(), sockets = new Set();
  let resolveSocketDrain;
  const wss = new WebSocketServer({ noServer: true, maxPayload: 16384 });
  // A stale process lock is never removed automatically; operator review preserves unknowns.
  for (const s of ledger.list())
    if (!terminal(s.state))
      ledger.transition(s.operation_id, "unknown", {
        reason: "manager_restart_unreconciled",
      });
  for (const row of ledger.db.prepare("SELECT id FROM controls WHERE json_extract(body,'$.status')='pending'").all())
    ledger.settleControl(row.id, 'unknown', 'manager_restart_unreconciled');
  function auth(req, write = false) {
    if (req.headers.authorization === `Bearer ${owner}`) return { owner: true };
    if (req.headers.authorization === `Bearer ${controlToken}`) return { control: true };
    const cookie = req.headers.cookie
      ?.split(";")
      .map((x) => x.trim())
      .find((x) => x.startsWith("genie_session="))
      ?.slice(14);
    const c = clients.get(cookie);
    need(c && c.expires > Date.now(), "unauthorized");
    if (write)
      need(
        req.headers["x-csrf-token"] === c.csrf && req.headers.origin === origin,
        "csrf",
      );
    return c;
  }
  function send(id, message) {
    const worker = workers.get(id);
    if (worker?.connected) worker.send(message, () => {});
  }
  function manifest(id) {
    const dir = join(root, "artifacts", id);
    const names = [
      "baseline.jpg",
      "navigation.jpg",
      "event.jpg",
      "viewer.webm",
    ];
    return names
      .filter((n) => existsSync(join(dir, n)) && lstatSync(join(dir, n)).isFile())
      .map((name) => {
        const b = readFileSync(join(dir, name));
        return {
          artifact_ref: `${id}_${name.replace(".", "_")}`,
          sha256: createHash("sha256").update(b).digest("hex"),
          size_bytes: b.length,
          mime: name.endsWith("jpg") ? "image/jpeg" : "video/webm",
        };
      });
  }
  function artifactDir(id) {
    need(UUID.test(id), "invalid_operation_id");
    ledger.get(id);
    const base = join(root, "artifacts");
    if (existsSync(base))
      need(!lstatSync(base).isSymbolicLink(), "artifact_ownership");
    const p = join(base, id);
    mkdirSync(p, { recursive: true, mode: 0o700 });
    need(!lstatSync(p).isSymbolicLink(), "artifact_ownership");
    return p;
  }
  function spawn(id) {
    const frames = { eventAck: null, baselineBarrier: null, recent: new Map() };
    frameEvidence.set(id, frames);
    const child = fork(
      fileURLToPath(new URL("./worker.mjs", import.meta.url)),
      [root, id, mode, ...(live ? [livePacketPath] : [])],
      {
        execPath: process.execPath,
        execArgv: [],
        stdio: ["ignore", "ignore", "pipe", "ipc"],
        env: {
          PATH: process.env.PATH,
          ...(live ? campaignPins : {}),
        },
      },
    );
    workers.set(id, child);
    let stderrBytes = 0;
    child.stderr.on("data", (chunk) => {
      if (stderrBytes < 8192) {
        const bounded = chunk.subarray(0, 8192 - stderrBytes);
        stderrBytes += bounded.length;
        appendFileSync(join(artifactDir(id), "worker-stderr.txt"), bounded, {
          mode: 0o600,
        });
      }
    });
    child.on("error", () => {
      const s = ledger.get(id);
      if (!terminal(s.state))
        ledger.transition(id, "unknown", { reason: "worker_launch_unknown" });
    });
    child.on("message", (message) => {
      const ws = websockets.get(id);
      if (message.type === "frame") {
        frames.recent.set(message.sequence, { frame_sequence: message.sequence,
          worker_frame_at: message.at, event_ack_observed_at: frames.eventAck,
          worker_frame_sha256: createHash('sha256').update(Buffer.from(message.data, 'base64')).digest('hex'),
          frame_binding: 'viewer_claimed_sequence_observed_by_backend' });
        if (frames.recent.size > 256) frames.recent.delete(frames.recent.keys().next().value);
        if (ws?.readyState === 1 && ws.bufferedAmount < 4 * 1024 * 1024) {
          ws.send(
            JSON.stringify({
              type: "frame_meta",
              sequence: message.sequence,
              at: message.at,
            }),
          );
          ws.send(Buffer.from(message.data, "base64"));
        }
      } else if (message.type === "status") {
        if (message.session.event_state === 'sent' && !frames.eventAck)
          frames.eventAck = new Date().toISOString();
        if (ws?.readyState === 1)
          ws.send(
            JSON.stringify({
              type: "status",
              session: status(message.session),
            }),
          );
        if (audit && terminal(message.session.state)) {
          const pending = audit({
            type: "session_outcome",
            operation_id: id,
            state: message.session.state,
          })
            .then((receipt) => {
              need(receipt?.commit, "audit_unavailable");
              ledger.audit("native_outcome_audit", {
                operation_id: id,
                commit: receipt.commit,
              });
            })
            .catch(() => {
              ledger.audit("native_audit_failed", { operation_id: id });
            })
            .finally(() => pendingAudits.delete(pending));
          pendingAudits.add(pending);
        }
      } else if (message.type === "error" && ws?.readyState === 1)
        ws.send(JSON.stringify(message));
    });
    child.on("exit", () => {
      workers.delete(id);
      for (const request of ledger.controlResults(id))
        if (request.status === 'pending') ledger.settleControl(request.request_id, 'unknown', 'worker_exited_before_ack');
      const s = ledger.get(id);
      if (!terminal(s.state)) {
        ledger.transition(id, "unknown", { reason: "worker_exited" });
        const ws = websockets.get(id);
        if (ws?.readyState === 1)
          ws.send(
            JSON.stringify({
              type: "status",
              session: status(ledger.get(id)),
            }),
          );
      }
    });
  }
  const server = http.createServer(async (req, res) => {
    const handled = Promise.withResolvers();
    pendingHandlers.add(handled.promise);
    let recordingId;
    const json = (code, value) => {
      if (res.destroyed) return;
      res.writeHead(code, { ...security, "Content-Type": "application/json" });
      res.end(JSON.stringify(value));
    };
    try {
      need(req.headers.host === new URL(origin).host, "host");
      if (req.headers.origin) need(req.headers.origin === origin, "origin");
      const url = new URL(req.url, origin);
      need(!url.search, "invalid_query");
      const path = url.pathname;
      if (
        req.method === "GET" &&
        ["/", "/viewer.mjs", "/viewer.css"].includes(path)
      ) {
        const name = path === "/" ? "index.html" : path.slice(1);
        res.writeHead(200, {
          ...security,
          "Content-Type": name.endsWith("html")
            ? "text/html"
            : name.endsWith("css")
              ? "text/css"
              : "text/javascript",
        });
        res.end(readFileSync(new URL("./viewer/" + name, import.meta.url)));
        return;
      }
      if (path === "/v1/bootstrap" && req.method === "POST") {
        need(req.headers.origin === origin, "origin");
        const input = JSON.parse((await body(req)).toString());
        closed(input, ["token"]);
        need(
          !bootstrapUsed &&
            Date.now() < bootstrapExpires &&
            input.token === bootstrap,
          "bootstrap_expired",
        );
        bootstrapUsed = true;
        const c = { csrf: token(), expires: Date.now() + 600000 };
        const sid = token();
        clients.set(sid, c);
        res.setHeader(
          "Set-Cookie",
          `genie_session=${sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=600`,
        );
        json(200, { csrf: c.csrf, mode, live_enabled: Boolean(live) });
        return;
      }
      const client = auth(req, req.method !== "GET");
      need(!readOnly || req.method === 'GET', 'evidence_read_only');
      if (client.control) need(
        (req.method === 'POST' && ['/v1/drafts', '/v1/sessions'].includes(path)) ||
        (req.method === 'GET' && /^\/v1\/sessions\/[a-f0-9-]{36}(\/evidence)?$/i.test(path)) ||
        (req.method === 'POST' && /^\/v1\/sessions\/[a-f0-9-]{36}\/(event|stop)$/i.test(path)),
        'control_scope');
      if (path === '/v1/drafts' && req.method === 'POST') {
        json(200, drafts.prepare(JSON.parse((await body(req)).toString()))); return;
      }
      if (path === '/v1/snapshots' && req.method === 'GET') {
        json(200, Object.entries(snapshots).map(([ref, snapshot]) => ({ ...snapshot.summary, snapshot_ref: ref }))); return;
      }
      const factsPath = path.match(/^\/v1\/drafts\/([a-f0-9-]{36})\/facts$/i);
      if (factsPath && req.method === 'GET') {
        json(200, drafts.localFacts(factsPath[1])); return;
      }
      const stylesPath = path.match(/^\/v1\/drafts\/([a-f0-9-]{36})\/styles$/i);
      if (stylesPath && req.method === 'GET') {
        json(200, drafts.localDesigns(stylesPath[1])); return;
      }
      if (path === "/v1/client" && req.method === "GET") {
        json(200, { csrf: client.csrf, mode, live_enabled: Boolean(live) });
        return;
      }
      if (path === "/v1/draft" && req.method === "GET") {
        json(200, {
          projection: projection(),
          facts: selectedProjection.classification==='private_derived'
            ? {classification:'private_derived',structures:snapshots[selectedProjection.snapshot_ref].localFacts().devices.map(d=>({id:d.id,label:d.id,role:d.role}))}
            : fixtureFacts(),
          policy: live ? CAMPAIGN_SESSION_POLICY : POLICY,
          session_bounds: sessionBounds(),
          mode,
        });
        return;
      }
      if (path === "/v1/reviews" && req.method === "POST") {
        const input = JSON.parse((await body(req)).toString());
        closed(input, ["projection_sha256", "provider"]);
        need(input.provider === mode, "live_gate_closed");
        const packet = live ? currentLive() : null;
        need(input.projection_sha256 === projection().sha256, "review_stale");
        json(200, ledger.review(projection(), live ? CAMPAIGN_SESSION_POLICY : POLICY,
          packet ? packet.allowance_usd : 15, mode));
        return;
      }
      if (path === "/v1/sessions" && req.method === "POST") {
        const input = JSON.parse((await body(req)).toString());
        closed(input, ["request_id", "review_ref", "projection_ref"]);
        if (client.control || input.projection_ref) drafts.eligible(input.projection_ref);
        need(UUID.test(input.request_id), "invalid_request_id");
        let old;
        try {
          old = ledger.get(input.request_id);
        } catch {}
        // Original-ID retrieval is observational: preserve historical bytes and
        // never require renewed spend authority or launch a replacement worker.
        if (old) {
          json(200, status(ledger.admit(input.request_id, projection(), input.review_ref,
            mode, input.projection_ref || null)));
          return;
        }
        need(!closing, "manager_closing");
        if (live) currentLive();
        if (!old && audit) {
          // Track admission audit ownership even if the HTTP client disappears.
          // Shutdown retains the ledger and lock until this continuation ends.
          const pending = Promise.resolve().then(() => audit({
            type: "session_admission",
            operation_id: input.request_id,
            provider: mode,
            projection_sha256: projection().sha256,
          }));
          pendingAudits.add(pending);
          try {
            const receipt = await pending;
            need(!closing, "manager_closing");
            need(receipt?.commit, "audit_unavailable");
            ledger.audit("native_admission_audit", {
              operation_id: input.request_id,
              commit: receipt.commit,
            });
          } finally { pendingAudits.delete(pending); }
        }
        // Audit awaits external work. Reload exact packet, source and retained
        // evidence after that await, immediately before reservation/marker commit.
        if (live) currentLive();
        const admitted = live ? admitReviewedCampaign(ledger, {
          operation_id: input.request_id, projection: projection(), review_id: input.review_ref,
          projection_ref: input.projection_ref || null,
        }, campaignPins) : ledger.admit(
          input.request_id,
          projection(),
          input.review_ref,
          mode,
          input.projection_ref || null,
        );
        if (admitted.newly_created) spawn(admitted.operation_id);
        json(200, status(admitted));
        return;
      }
      const match = path.match(
        /^\/v1\/sessions\/([a-f0-9-]{36})(?:\/(event|stop|evidence|recording|recording-final|recording-failure|checkpoint))?$/i,
      );
      need(match, "not_found");
      const [, id, action] = match;
      const session = ledger.get(id);
      if (req.method === "GET" && !action) {
        json(200, status(session));
        return;
      }
      if (req.method === "GET" && action === "evidence") {
        const artifacts = manifest(id);
        const eventReceipt = ledger.eventCheckpoint(id);
        const eventMatches = eventReceipt && artifacts.some(a => a.artifact_ref === `${id}_event_jpg` &&
          a.sha256 === eventReceipt.sha256 && a.size_bytes === eventReceipt.size_bytes);
        const recording = ledger.recordingStatus(id);
        if (recording.receipt && !artifacts.some(a => a.mime === "video/webm" &&
            a.sha256 === recording.receipt.sha256 && a.size_bytes === recording.receipt.size_bytes)) {
          recording.state = "incomplete"; recording.reason = "recording_artifact_mismatch";
        }
        json(200, {
          session: status(session),
          manifest: artifacts,
          recording,
          recording_failures: ledger.recordingFailures(id),
          event_checkpoint: { state: eventReceipt ? (eventMatches ? 'correlated' : 'incomplete') : 'unconfirmed',
            receipt: eventReceipt },
          acceptance: null,
          live_world_proven: false,
        });
        return;
      }
      if (req.method === "POST" && ['event', 'stop'].includes(action)) {
        const input = JSON.parse((await body(req)).toString() || '{}');
        closed(input, action === 'event' ? ['request_id', 'event_id'] : ['request_id']);
        if (!client.control && action === 'stop' && !input.request_id) {
          send(id, { type: 'stop' }); json(200, status(ledger.get(id))); return;
        }
        const request = ledger.claimControl(input.request_id, id, action, input.event_id);
        if (request.newly_created) {
          if (workers.get(id)?.connected) send(id, { type: action, request_id: input.request_id, event_id: input.event_id });
          else ledger.settleControl(input.request_id, ['terminal', 'failed_pre_send'].includes(session.state) && action === 'stop' ? 'accepted' : 'unknown', 'worker_unavailable');
        }
        const current = ledger.controlResults(id).find(r => r.request_id === input.request_id);
        json(200, { schema_version: 1, request_id: input.request_id, status: current.status, ...status(ledger.get(id)) });
        return;
      }
      if (req.method === "POST" && action === "recording-failure") {
        const input = JSON.parse((await body(req)).toString());
        closed(input, ["code"]);
        try { ledger.recordingFailure(id, input.code); }
        finally { send(id, { type: "stop" }); }
        json(200, { recorded: true });
        return;
      }
      if (req.method === "POST" && action === "recording") {
        need(!ledger.recordingFailures(id).length, "recording_already_failed");
        need(!ledger.recordingStatus(id).receipt, "recording_finalized");
        recordingId = id;
        need(req.headers["content-type"] === "video/webm", "invalid_media");
        const data = await body(req, 4 * 1024 * 1024);
        need(!ledger.recordingStatus(id).receipt, "recording_finalized");
        const p = join(artifactDir(id), "viewer.webm");
        need(
          !existsSync(p) || !lstatSync(p).isSymbolicLink(),
          "artifact_ownership",
        );
        need(
          (existsSync(p) ? statSync(p).size : 0) + data.length <=
            60 * 1024 * 1024,
          "evidence_limit",
        );
        appendFileSync(p, data, { mode: 0o600 });
        json(200, { bytes: data.length });
        return;
      }
      if (req.method === "POST" && action === "recording-final") {
        const input = JSON.parse((await body(req)).toString());
        closed(input, ["size_bytes"]);
        need(Number.isSafeInteger(input.size_bytes) && input.size_bytes > 0 &&
          input.size_bytes <= 60 * 1024 * 1024, "invalid_recording_size");
        const media = manifest(id).find(a => a.mime === "video/webm");
        need(media && media.size_bytes === input.size_bytes, "recording_size_mismatch");
        // Persist the bytes before acknowledging their final flush in SQLite.
        const fd = openSync(join(artifactDir(id), "viewer.webm"), "r");
        try { fsyncSync(fd); } finally { closeSync(fd); }
        json(200, ledger.acknowledgeRecording(id, { size_bytes: media.size_bytes, sha256: media.sha256 }));
        return;
      }
      if (req.method === "POST" && action === "checkpoint") {
        const input = JSON.parse((await body(req, 2800000)).toString());
        closed(input, ["name", "data", "frame_sequence"]);
        need(
          ["baseline", "navigation", "event"].includes(input.name) &&
            typeof input.data === "string",
          "invalid_checkpoint",
        );
        const bytes = Buffer.from(input.data, "base64");
        need(
          bytes.length <= 1024 * 1024 && bytes[0] === 255 && bytes[1] === 216,
          "invalid_media",
        );
        let capture;
        if (input.name === 'navigation') {
          // Body upload may outlive the session; use current state at persistence.
          need(ledger.get(id).state === 'active', 'session_not_active');
          need(manifest(id).some(a => a.artifact_ref === `${id}_baseline_jpg`), 'baseline_required');
          const frames = frameEvidence.get(id);
          need(Number.isSafeInteger(input.frame_sequence) && frames?.baselineBarrier !== null &&
            frames?.recent.has(input.frame_sequence) && input.frame_sequence > frames.baselineBarrier,
          'post_baseline_frame_required');
        }
        if (input.name === 'event') {
          // Re-read after awaiting the body; pre-body state can be stale.
          const current = ledger.get(id);
          need(current.state === 'active' && current.event_state === 'sent', 'event_not_sent');
          need(manifest(id).some(a => a.artifact_ref === `${id}_baseline_jpg`), 'baseline_required');
          capture = Number.isSafeInteger(input.frame_sequence) && frameEvidence.get(id)?.recent.get(input.frame_sequence);
          need(capture?.event_ack_observed_at, 'post_event_frame_required');
        }
        const checkpointPath = join(artifactDir(id), input.name + '.jpg');
        writeFileSync(checkpointPath, bytes, {
          flag: "wx",
          mode: 0o600,
        });
        if (input.name === 'baseline') {
          const frames = frameEvidence.get(id);
          // Conservatively exclude every frame already received when baseline is saved.
          if (frames) frames.baselineBarrier = Math.max(0, ...frames.recent.keys());
        }
        if (capture) {
          const fd = openSync(checkpointPath, 'r');
          try { fsyncSync(fd); } finally { closeSync(fd); }
          ledger.recordEventCheckpoint(id, { ...capture,
            sha256: createHash('sha256').update(bytes).digest('hex'), size_bytes: bytes.length });
        }
        json(200, { recorded: input.name });
        return;
      }
      need(false, "not_found");
    } catch (e) {
      if (recordingId) {
        try {
          ledger.recordingFailure(recordingId, e.code === "evidence_limit" ? "recording_limit" : "recording_upload_failed");
        } catch { /* Persistence failure cannot prevent the stop attempt. */ }
        finally { send(recordingId, { type: "stop" }); }
      }
      if (e.code === "evidence_limit") {
        const id = req.url.split("/")[3];
        send(id, { type: "stop" });
      }
      json(
        e.code === "manager_closing" ? 503 :
        ["unauthorized", "csrf", "origin", "host", "control_scope"].includes(e.code)
          ? 403
          : e.code === "not_found"
            ? 404
            : ["active_or_unsettled", "request_conflict"].includes(e.code)
              ? 409
              : 400,
        { error: e.code || "invalid_request" },
      );
    } finally {
      pendingHandlers.delete(handled.promise);
      handled.resolve();
    }
  });
  server.on("connection", socket => {
    sockets.add(socket);
    socket.once("close", () => {
      sockets.delete(socket);
      if (!sockets.size) resolveSocketDrain?.();
    });
  });
  server.on("upgrade", (req, socket, head) => {
    try {
      need(!readOnly, 'evidence_read_only');
      need(
        req.headers.host === new URL(origin).host &&
          req.headers.origin === origin,
        "origin",
      );
      need(!auth(req).control, 'control_scope');
      const m = req.url.match(/^\/v1\/view\/([a-f0-9-]{36})$/i);
      need(m, "invalid_path");
      const id = m[1];
      ledger.get(id);
      need(!websockets.has(id), "viewer_already_connected");
      wss.handleUpgrade(req, socket, head, (ws) => {
        websockets.set(id, ws);
        let lastSeq = 0;
        ws.on("message", (bytes, isBinary) => {
          try {
            need(!isBinary, "invalid_control");
            const event = JSON.parse(bytes);
            closed(event, ["type", "seq", "key", "down", "event_id"]);
            need(
              Number.isSafeInteger(event.seq) && event.seq > lastSeq,
              "invalid_sequence",
            );
            lastSeq = event.seq;
            need(
              [
                "heartbeat",
                "key",
                "event_ready",
                "event",
                "release",
                "stop",
              ].includes(event.type),
              "invalid_control",
            );
            send(id, event);
          } catch {
            send(id, { type: "stop" });
            ws.close(1008);
          }
        });
        ws.on("close", () => {
          websockets.delete(id);
          send(id, { type: "release" });
        });
        ws.send(
          JSON.stringify({
            type: "status",
            session: status(ledger.get(id)),
          }),
        );
      });
    } catch {
      socket.destroy();
    }
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolve);
  });
  origin = `http://127.0.0.1:${server.address().port}`;
  const beat = setInterval(() => {
    for (const [id] of workers) send(id, { type: "manager_heartbeat" });
  }, 1000);
  const service = {
    origin,
    owner,
    bootstrap,
    pid: process.pid,
    mode,
  };
  writeFileSync(join(root, "service.json"), JSON.stringify(service), {
    mode: 0o600,
  });
  writeFileSync(join(root, 'mcp-control.json'), JSON.stringify({ schema: 1, origin, token: controlToken }), { mode: 0o600, flag: 'w' });
  function close() {
    if (closePromise) return closePromise;
    closing = true;
    closePromise = (async () => {
      for (const [id] of workers) send(id, { type: "stop" });
      const end = performance.now() + MANAGER_SHUTDOWN_GRACE_MS;
      while (workers.size && performance.now() < end)
        await new Promise((r) => setTimeout(r, 50));
      // Grace expiry is local cleanup, never a provider terminal receipt. Reap
      // owned children before closing their shared ledger and removing the lock.
      await Promise.all([...workers].map(([id, child]) => new Promise((resolve) => {
        const s = ledger.get(id);
        if (!terminal(s.state))
          ledger.transition(id, "unknown", { reason: "manager_cleanup_expired" });
        child.once("exit", resolve);
        child.kill("SIGKILL");
      })));
      clearInterval(beat);
      for (const ws of websockets.values()) ws.close();
      // Closing the stream triggers MediaRecorder's asynchronous final flush.
      // Keep the listener open for the full bounded grace, including NEW upload
      // connections: server.close() immediately would reject those final bytes.
      // Admission stays closed; stop/evidence handlers still own this ledger.
      await new Promise(resolve => setTimeout(resolve, 1000));
      const socketDrain = new Promise(resolve => {
        resolveSocketDrain = resolve;
        if (!sockets.size) resolve();
      });
      const httpClosed = new Promise(resolve => server.close(resolve));
      // Grace expiry includes partial headers and upgraded sockets; a peer
      // cannot extend transport cleanup indefinitely.
      for (const socket of sockets) socket.destroy();
      await Promise.all([httpClosed, socketDrain]);
      wss.close();
      // Socket closure is not handler completion: interrupted recording uploads
      // still persist their failure, and disconnected audits still own SQLite.
      await Promise.allSettled([...pendingHandlers]);
      await Promise.allSettled([...pendingAudits]);
      ledger.close();
      closeSync(lockFd);
      unlinkSync(lock);
    })();
    return closePromise;
  }
  return { origin, bootstrap, owner, ledger, close, workers, root };
}
