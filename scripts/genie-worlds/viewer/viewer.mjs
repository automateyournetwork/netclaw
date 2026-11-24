const $ = (id) => document.getElementById(id),
  canvas = $("world"),
  ctx = canvas.getContext("2d");
let csrf,
  selectedProjection,
  mode = "fixture",
  operation,
  ws,
  sequence = 0,
  rendered = 0,
  decoding = 0,
  recorder,
  recordingStream,
  recordingFailure = null,
  finalFlushUnconfirmed = false,
  failureReport = Promise.resolve(),
  upload = Promise.resolve(),
  heartbeat,
  hasBaseline = false,
  baselinePending = false,
  postBaselineFrame = false,
  active = false,
  stopping = false,
  terminal = false,
  endedStatus = null,
  mediaFailure = false,
  mediaDisconnected = false,
  eventSendAcknowledged = false,
  postEventFrame = false,
  frameMeta = null,
  byteCount = 0;
const held = new Map();
const completedControls = new Set();
const captures = new Map();
const keys = {
  w: "w",
  a: "a",
  s: "s",
  d: "d",
  ArrowLeft: "arrow_left",
  ArrowRight: "arrow_right",
  ArrowUp: "arrow_up",
  ArrowDown: "arrow_down",
};
async function api(path, body, options = {}) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      ...(body === undefined
        ? {}
        : { "Content-Type": "application/json", "X-CSRF-Token": csrf }),
      ...options.headers,
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    ...options,
  });
  const result = await response.json();
  if (!response.ok) throw Error(result.error || "Request failed");
  return result;
}
function show(message) {
  const reasons = { recording_start_failed: "recorder could not start", recording_failed: "recorder error",
    recording_upload_failed: "recording could not be saved", recording_limit: "recording size limit" };
  $("status").textContent = recordingFailure ? `Recording incomplete (${reasons[recordingFailure]}) · ${message}`
    : finalFlushUnconfirmed ? `Recording final confirmation unavailable · ${message}` : message;
}
function renderMediaStatus() {
  const source = mode === 'evidence' ? 'RETAINED EVIDENCE · No generation' : mode === 'google' ? 'GOOGLE MODE' : 'OFFLINE TRANSPORT FIXTURE · No Google generation';
  const state = mediaFailure ? (rendered ? 'MEDIA / CAPTURE FAILURE · Last decoded frame retained' : 'MEDIA / CAPTURE FAILURE · No frame decoded')
    : terminal ? (rendered ? 'VIEWING ENDED · Last decoded frame retained' : 'VIEWING ENDED · No frame decoded')
    : mediaDisconnected ? (rendered ? 'DISCONNECTED · Last decoded frame retained' : 'DISCONNECTED · No frame decoded')
    : rendered ? 'ILLUSTRATION FRAME DECODED · Visual quality unreviewed'
    : 'AWAITING MEDIA · No frame decoded';
  $('mode').textContent = `${source} · ${state} · ${selectedProjection?.classification==='private_derived' ? 'FROZEN REAL NETWORK · Generated illustration; historical facts retained locally' : 'Independent synthetic network · No measured device data'}`;
}
function canInteract() {
  return active && hasBaseline && rendered > 0 && ws?.readyState === WebSocket.OPEN &&
    !terminal && !stopping && !mediaFailure && !mediaDisconnected && !recordingFailure;
}
function renderInteractionControls() {
  const enabled = canInteract();
  for (const id of ['event', 'navshot', 'eventshot']) $(id).disabled = !enabled || completedControls.has(id);
  $('navshot').disabled ||= captures.has('navigation') || !postBaselineFrame;
  $('eventshot').disabled ||= captures.has('event');
  $('eventshot').disabled ||= !eventSendAcknowledged || !postEventFrame;
  renderCaptureStatus();
  if (!enabled && held.size) release();
}
function failRecording(code) {
  if (recordingFailure) return;
  recordingFailure = code;
  for (const id of ["event", "navshot", "eventshot"]) $(id).disabled = true;
  endRecording();
  clearInterval(heartbeat);
  release();
  control({ type: "stop" });
  show("Stopping session; capture cannot support acceptance.");
  // Evidence reporting cannot block the independent stop paths/deadline.
  failureReport = api(`/v1/sessions/${operation}/recording-failure`, { code }, { signal: AbortSignal.timeout(3000) })
    .catch(() => show("Failure report unconfirmed; retain original operation and inspect evidence."));
  void stop();
}
function control(value) {
  if (ws?.readyState === WebSocket.OPEN)
    ws.send(JSON.stringify({ ...value, seq: ++sequence }));
}
function release() {
  held.clear();
  control({ type: "release" });
}
function recording() {
  if (
    !window.MediaRecorder ||
    !MediaRecorder.isTypeSupported("video/webm;codecs=vp8")
  )
    throw Error("Browser recording codec unavailable; no session started");
  recordingStream = canvas.captureStream(24);
  recorder = new MediaRecorder(recordingStream, {
    mimeType: "video/webm;codecs=vp8",
    videoBitsPerSecond: 2000000,
  });
  recorder.ondataavailable = ({ data }) => {
    if (!data.size || recordingFailure) return;
    byteCount += data.size;
    if (byteCount > 60 * 1024 * 1024) {
      failRecording("recording_limit");
      return;
    }
    upload = upload
      .then(async () => {
        if (recordingFailure) return;
        const response = await fetch(`/v1/sessions/${operation}/recording`, {
          method: "POST",
          headers: { "Content-Type": "video/webm", "X-CSRF-Token": csrf },
          body: data,
          signal: AbortSignal.timeout(3000),
        });
        if (!response.ok) throw Error("Recording persistence failed");
      })
      .catch(() => failRecording("recording_upload_failed"));
  };
  recorder.onerror = () => {
    failRecording("recording_failed");
  };
  // onstop follows the final dataavailable event. A terminal provider receipt
  // alone says nothing about whether this browser's last chunk was retained.
  recorder.onstop = () => {
    upload = upload.then(async () => {
      if (recordingFailure) return;
      try {
        await api(`/v1/sessions/${operation}/recording-final`, { size_bytes: byteCount },
          { signal: AbortSignal.timeout(3000) });
      } catch {
        // A lost reply is not a failed chunk. Read the original durable receipt
        // once; never replay uploads, finalization or provider creation.
        finalFlushUnconfirmed = true;
        try {
          const evidence = await api(`/v1/sessions/${operation}/evidence`, undefined,
            { signal: AbortSignal.timeout(3000) });
          finalFlushUnconfirmed = !(evidence.recording?.state === "final_flush_acknowledged" &&
            evidence.recording.receipt?.size_bytes === byteCount);
        } catch { /* Manager loss leaves confirmation unavailable, not failed bytes. */ }
        show(finalFlushUnconfirmed ? "Retain original operation and inspect evidence."
          : "Recording final receipt recovered; inspect session evidence for remaining checks.");
      }
    }).catch(() => failRecording("recording_failed"));
  };
  recorder.start(1000);
}
async function checkpoint(name, options = {}) {
  if (!operation || (name !== "baseline" && !canInteract())) return false;
  if (name === 'navigation' && !postBaselineFrame) return false;
  if (name === "event" && (!eventSendAcknowledged || !postEventFrame || completedControls.has("eventshot"))) return false;
  const data = canvas.toDataURL("image/jpeg", 0.8).split(",")[1];
  await api(`/v1/sessions/${operation}/checkpoint`, { name, data,
    ...(['event', 'navigation'].includes(name) ? { frame_sequence: rendered } : {}) }, options);
  return true;
}
function renderCaptureStatus() {
  const statuses = [...captures].filter(([name, state]) => name !== 'baseline' || state !== 'saved').map(([name, state]) =>
    `${name === 'baseline' ? 'Baseline' : name === 'navigation' ? 'Navigation' : 'Event'}: ${state === 'pending' ? 'Saving' : state === 'saved' ? 'Saved' :
      'Unconfirmed; inspect original session evidence. Do not repeat capture or event.'}`);
  if (hasBaseline && !captures.has('navigation')) statuses.unshift(
    `Navigation: ${postBaselineFrame ? 'Subsequent frame decoded; inspect before capturing.' : 'Waiting for subsequent media.'}`);
  $('capture-status').textContent = statuses.join(' · ') || 'Navigation and event checkpoints not captured.';
}
async function captureCheckpoint(name) {
  if (!canInteract() || captures.has(name) ||
      (name === 'navigation' && !postBaselineFrame) ||
      (name === 'event' && (!eventSendAcknowledged || !postEventFrame))) return;
  // Claim before awaiting HTTP. Status/media updates and direct handlers share
  // this guard; a lost reply cannot authorize replacement evidence.
  captures.set(name, 'pending');
  renderInteractionControls();
  renderCaptureStatus();
  try {
    if (await checkpoint(name, { signal: AbortSignal.timeout(3000) })) captures.set(name, 'saved');
    else captures.delete(name);
  } catch {
    // HTTP errors/timeouts do not prove whether the server retained the image.
    captures.set(name, 'unconfirmed');
  }
  renderCaptureStatus();
  renderInteractionControls();
}
function endRecording() {
  try { if (recorder?.state === "recording") recorder.stop(); }
  catch { return false; }
  finally { recordingStream?.getTracks().forEach((track) => track.stop()); }
  return true;
}
function renderBounds(bounds) {
  if (!bounds) throw Error('Reviewed session bounds unavailable');
  const { policy, accounting_mode, campaign_limits } = bounds;
  const usd = (value) => `US$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 6 })}`;
  const label = accounting_mode === 'fixture' ? 'Offline fixture' : accounting_mode === 'campaign-v1' ? 'Campaign session' : 'Legacy session';
  $('bounds').textContent = `${label} · ${policy.target_seconds}-second target · ${policy.deadline_seconds_from_send}-second local deadline. Missing terminal evidence remains unresolved.`;
  $('cost').textContent = accounting_mode === 'fixture'
    ? `Fixture cost ${usd(bounds.estimated_usd)} · reservation ${usd(bounds.reservation_usd)}. Google execution is disabled.`
    : `${bounds.estimated_video_usd == null ? '' : `Video estimate ${usd(bounds.estimated_video_usd)}; `}total estimate ${usd(bounds.estimated_usd)}; reservation ${usd(bounds.reservation_usd)}. Estimates and reservations are not billed usage. ${campaign_limits ? `Campaign soft admission stop ${usd(campaign_limits.soft_stop_usd)}; hard ceiling ${usd(campaign_limits.hard_stop_usd)}. ` : ''}Local deadline is not a provider spending cap.`;
}
function update(session) {
  renderBounds(session.session_bounds);
  // HTTP stop replies and streamed statuses can arrive out of order. Retain
  // ended lifecycle evidence, but allow the original unknown operation's later
  // receipt and same-terminal usage reconciliation to advance the display.
  const incoming = { state: session.state, terminal_confirmed: session.terminal_confirmed,
    usage_state: session.usage_state };
  if (!endedStatus && ["terminal", "unknown", "failed_pre_send"].includes(incoming.state)) {
    endedStatus = incoming;
  } else if (endedStatus?.state === "unknown" && incoming.state === "terminal") {
    endedStatus = incoming;
  } else if (endedStatus?.state === incoming.state) {
    endedStatus = { ...incoming,
      terminal_confirmed: endedStatus.terminal_confirmed || incoming.terminal_confirmed,
      usage_state: endedStatus.usage_state === "reconciled" ? "reconciled" : incoming.usage_state };
  }
  const lifecycle = endedStatus || incoming;
  active = lifecycle.state === "active";
  // The original session's ledger owns the single fixed event across viewer/MCP.
  // Its send result is not proof that the generated scene visibly changed.
  if (session.event_state === "sent") {
    eventSendAcknowledged = true;
    completedControls.add("event");
  }
  if (eventSendAcknowledged) $('event-status').textContent = postEventFrame
    ? 'Send acknowledged · Subsequent frame decoded · Visible effect unassessed; inspect before capturing.'
    : 'Send acknowledged · Waiting for subsequent media · Visible effect unassessed.';
  else if (completedControls.has('event') || session.event_state === 'send_marked')
    $('event-status').textContent = 'Event requested · Send unconfirmed · Retain original event; do not replay.';
  terminal = Boolean(endedStatus);
  renderMediaStatus();
  show(
    `${lifecycle.state} · ${lifecycle.terminal_confirmed ? "provider receipt retained" : "no terminal receipt"} · usage ${lifecycle.usage_state}`,
  );
  renderInteractionControls();
  $("stop").disabled = terminal;
  $("evidence").disabled = false;
  if (terminal) {
    clearInterval(heartbeat);
    release();
    if (!endRecording()) failRecording("recording_failed");
  }
}
async function stop() {
  watchCancelled = true;
  stopping = true;
  renderInteractionControls();
  release();
  if (operation)
    try {
      update(await api(`/v1/sessions/${operation}/stop`, {}));
    } catch (e) {
      show(`Stop outcome unresolved: ${e.message}`);
    }
}
function attach(session) {
  if (ws) throw Error('Viewer already attached; inspect the original operation.');
    update(session);
    ws = new WebSocket(
      `${location.origin.replace("http:", "ws:")}/v1/view/${operation}`,
    );
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      renderInteractionControls();
      if (terminal || stopping) return;
      heartbeat = setInterval(() => control({ type: "heartbeat" }), 1000);
      control({ type: "heartbeat" });
      try { recording(); }
      catch { failRecording("recording_start_failed"); return; }
      canvas.focus();
    };
    ws.onmessage = async (event) => {
      if (typeof event.data === "string") {
        const message = JSON.parse(event.data);
        if (message.type === "status") update(message.session);
        else if (message.type === "frame_meta") frameMeta = message;
        else if (message.type === "error") show(message.code);
        return;
      }
      if (decoding >= 2) return;
      const seq = frameMeta?.sequence || 0;
      // Media already decoding when the receipt arrives cannot establish ordering.
      const receivedAfterEventAck = eventSendAcknowledged;
      const receivedAfterBaselineAck = hasBaseline;
      decoding++;
      let bitmap;
      try {
        bitmap = await createImageBitmap(
          new Blob([event.data], { type: "image/jpeg" }),
        );
        if (seq > rendered && !terminal && !stopping && !mediaFailure && !mediaDisconnected) {
          ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
          rendered = seq;
          if (receivedAfterBaselineAck) postBaselineFrame = true;
          if (receivedAfterEventAck) {
            postEventFrame = true;
            $('event-status').textContent = 'Send acknowledged · Subsequent frame decoded · Visible effect unassessed; inspect before capturing.';
          }
          renderMediaStatus();
          if (!hasBaseline && !baselinePending && !captures.has('baseline')) {
            baselinePending = true;
            captures.set('baseline', 'pending');
            renderCaptureStatus();
            try {
              await checkpoint("baseline", { signal: AbortSignal.timeout(3000) });
              hasBaseline = true;
              captures.set('baseline', 'saved');
            } catch (error) {
              // Timeout/lost reply cannot prove whether the original JPEG was
              // saved. Retain the claim; later media must never replay it.
              captures.set('baseline', 'unconfirmed');
              throw error;
            } finally { baselinePending = false; renderCaptureStatus(); }
          }
          renderInteractionControls();
        }
      } catch {
        mediaFailure = true;
        renderMediaStatus();
        renderInteractionControls();
        show("Frame or checkpoint failure");
        void stop();
      } finally {
        bitmap?.close();
        decoding--;
      }
    };
    ws.onclose = () => {
      mediaDisconnected = true;
      renderMediaStatus();
      renderInteractionControls();
      clearInterval(heartbeat);
      release();
      endRecording();
      if (!terminal)
        show("Viewer disconnected. Read original status; do not restart.");
    };
}
let watchCancelled = false;
$('member-review').onclick = async () => {
  $('member-review').disabled = true; $('start').disabled = true;
  try {
    if (!MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) throw Error('Required recording codec unavailable');
    const prepared = await api('/v1/drafts', { request_id: crypto.randomUUID(),
      ...(selectedProjection.classification==='private_derived' ? {private_snapshot_ref:selectedProjection.snapshot_ref} : {synthetic_fixture_id:'synthetic-museum-v1'}) });
    const review = await api('/v1/reviews', { projection_sha256: prepared.projection_sha256, provider: mode });
    operation = crypto.randomUUID();
    sessionStorage.setItem('genie_last_operation', operation);
    $('result').textContent = JSON.stringify({ tool: 'genie_world_start', arguments: {
      request_id: operation, projection_ref: prepared.projection_ref, review_ref: review.id,
    }, provider: mode, expires_at: review.expires_at }, null, 2);
    show('Review ready. Watching this original ID for a member start; no generation has started.');
    $('stop').disabled = false;
    const end = Date.now() + 60000;
    while (!watchCancelled && Date.now() < end) {
      try {
        const session = await api(`/v1/sessions/${operation}`);
        if (!watchCancelled) attach(session);
        return;
      } catch (error) {
        if (error.message !== 'not_found') throw error;
      }
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    show('Member watch ended. Inspect the original operation; do not issue a replacement.');
  } catch (error) { show(`Member review unavailable: ${error.message}`); }
};
$("start").onclick = async () => {
  $("start").disabled = true;
  $("member-review").disabled = true;
  try {
    if (!MediaRecorder.isTypeSupported("video/webm;codecs=vp8"))
      throw Error("Required recording codec unavailable");
    const draft = await api("/v1/draft");
    const review = await api("/v1/reviews", {
      projection_sha256: draft.projection.sha256,
      provider: mode,
    });
    operation = crypto.randomUUID();
    sessionStorage.setItem("genie_last_operation", operation);
    // Request ID exists before transport: a lost response can be queried using it.
    const session = await api("/v1/sessions", {
      request_id: operation,
      review_ref: review.id,
    });
    attach(session);
  } catch (e) {
    show(e.message);
    if (operation) {
      try {
        update(await api(`/v1/sessions/${operation}`));
      } catch {
        show("Start outcome unresolved. Original ID retained: " + operation);
      }
    }
  }
};
$("stop").onclick = stop;
$("event").onclick = () => {
  if (!canInteract() || completedControls.has("event")) return;
  control({ type: "event_ready", event_id: selectedProjection.event_id });
  control({ type: "event", event_id: selectedProjection.event_id });
  completedControls.add("event");
  $("event-status").textContent = "Event requested · Send unconfirmed · Retain original event; do not replay.";
  renderInteractionControls();
};
$("navshot").onclick = () => captureCheckpoint("navigation");
$("eventshot").onclick = () => captureCheckpoint("event");
$("evidence").onclick = async () => {
  await upload;
  await failureReport;
  try {
    $("result").textContent = JSON.stringify(
      await api(`/v1/sessions/${operation}/evidence`),
      null,
      2,
    );
  } catch (e) {
    show(e.message);
  }
};
canvas.onkeydown = (event) => {
  if (event.key === "Escape") {
    release();
    return;
  }
  if (!canInteract()) return;
  const key = keys[event.key] || keys[event.key.toLowerCase()];
  if (!key) return;
  // Held arrows still trigger native page scrolling on repeated keydown.
  // Suppress that default without sending duplicate movement commands.
  event.preventDefault();
  // Modifiers/layout changes can alter event.key before keyup. Retain the
  // command selected on keydown under its stable physical identity.
  const identity = event.code || event.key.toLowerCase();
  if (!event.repeat && !held.has(identity)) {
    held.set(identity, key);
    control({ type: "key", key, down: true });
  }
};
window.addEventListener("keyup", (event) => {
  const identity = event.code || event.key.toLowerCase();
  const key = held.get(identity);
  if (key) {
    held.delete(identity);
    control({ type: "key", key, down: false });
  }
});
canvas.onblur = release;
window.addEventListener("blur", release);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) release();
});
try {
  const bootstrap = location.hash.slice(1);
  history.replaceState(null, "", location.pathname);
  const response = await fetch(bootstrap ? "/v1/bootstrap" : "/v1/client", bootstrap ? {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: bootstrap }),
  } : {});
  const login = await response.json();
  if (!response.ok) throw Error(login.error);
  csrf = login.csrf;
  mode = login.mode;
  renderMediaStatus();
  if (mode === "google") {
    $("start").textContent = "Start authorized Google trial";
    $("controls-hint").textContent = "Focus the world. WASD moves; arrow keys look. Escape releases movement. Scene geometry and text may drift.";
    canvas.width = 1280; canvas.height = 720;
  }
  const draft = await api("/v1/draft");
  selectedProjection=draft.projection;
  renderMediaStatus();
  renderBounds(draft.session_bounds);
  $("prompt").textContent =
    draft.projection.text +
    "\n\nFictional event:\n" +
    draft.projection.event_text;
  for (const item of draft.facts.structures) {
    const p = document.createElement("p");
    p.textContent = `${item.label} — ${selectedProjection.classification==='private_derived'?'historically observed':'fictional'} ${item.role}`;
    $("facts").append(p);
  }
  $("start").disabled = mode === 'evidence';
  $("member-review").disabled = mode === 'evidence';
  const snapshots = await api('/v1/snapshots');
  $('snapshot-status').textContent = snapshots.length ? 'Choose a sealed historical snapshot.' : 'No local snapshot registered.';
  for (const snapshot of snapshots) {
    const button = document.createElement('button');
    button.textContent = `${snapshot.devices} devices · ${snapshot.physical_links} links · ${snapshot.snapshot_ref}`;
    button.onclick = async () => {
      try {
        const prepared = await api('/v1/drafts', { request_id: crypto.randomUUID(), private_snapshot_ref: snapshot.snapshot_ref });
        const retained = await api(`/v1/drafts/${prepared.projection_ref}/facts`);
        const designs = await api(`/v1/drafts/${prepared.projection_ref}/styles`);
        $('snapshot-status').textContent = `FROZEN HISTORICAL SNAPSHOT · ${retained.summary.files_verified} files verified · ${retained.facts.coverage_limits.join(' ')}`;
        $('snapshot-items').replaceChildren(); $('world-designs').replaceChildren();
        const items = [...retained.facts.devices.map(d => [d.id, d]), ...retained.facts.physical_links.map(l => [l.id, l]),
          ['Routing protocols', retained.facts.logical_relations], ['VLAN / trunk / STP', retained.facts.vlans],
          ['Counters and limits', retained.facts.counter_samples], ['Collection coverage', retained.coverage]];
        for (const [name, value] of items) {
          const b = document.createElement('button'); b.textContent = name;
          b.onclick = () => { $('snapshot-fact').textContent = JSON.stringify(value, null, 2); };
          $('snapshot-items').append(b);
        }
        for (const design of designs) {
          const b = document.createElement('button'); b.textContent = `${design.order}. ${design.title}`;
          b.onclick = () => { $('world-design').textContent = JSON.stringify(design, null, 2); };
          $('world-designs').append(b);
        }
        $('snapshot-fact').textContent = JSON.stringify(retained.summary, null, 2);
        $('world-design').textContent = '';
      } catch (error) { $('snapshot-status').textContent = `Snapshot unavailable: ${error.message}`; }
    };
    $('snapshots').append(button);
  }
  show(
    mode === 'evidence' ? 'Retained evidence only. Preparation, generation and controls are disabled; use the original operation ID with status/evidence.' : mode === "google" ? "Ready for the authorized Google recording." : "Ready to review the exact synthetic fixture. Google execution is disabled.",
  );
} catch (e) {
  show(
    `Local session unavailable: ${e.message}. Reopen from the owner launcher.`,
  );
}
