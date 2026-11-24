import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { Ledger } from "./ledger.mjs";
import { projection, sessionPolicy, hash, KEYS, need, WORKER_SHUTDOWN_DRAIN_MS } from "./model.mjs";
import { FixtureProvider } from "./fixture-provider.mjs";
import { loadLivePacket, loadCredential } from "./live-packet.mjs";
import { openGoogle } from "./provider.mjs";

export function createSessionWorker({
  ledger,
  id,
  open,
  emit = () => {},
  policy,
}) {
  const admitted = ledger.get(id);
  const selectedPolicy = sessionPolicy(admitted);
  // Short clocks belong to fixture tests only, never a live launch override.
  need(policy === undefined || admitted.provider === 'fixture', 'live_policy_override');
  policy = Object.freeze({ ...(policy ?? selectedPolicy) });
  let session,
    receiver,
    stopping = false,
    finished = false,
    uncertain = false,
    firstFrame = null,
    stopAt = null;
  const nowAtStart = performance.now();
  const admittedAgo = Math.max(
    0,
    Date.now() - Date.parse(ledger.get(id).send_marked_at),
  );
  const start = nowAtStart - admittedAgo;
  let viewerAt = nowAtStart,
    managerAt = nowAtStart,
    readyUntil = 0;
  const keys = new Set();
  let keyWindow = start,
    keyCount = 0,
    seq = 0,
    controls = Promise.resolve();
  const status = () => emit({ type: "status", session: ledger.get(id) });
  let endLocal;
  const localEnd = new Promise((resolve) => { endLocal = resolve; });
  const ended = Symbol("local transport ended");
  const bounded = (promise) => Promise.race([promise, localEnd.then(() => ended)]);
  const pendingCleanup = new Set();
  const track = (promise) => {
    pendingCleanup.add(promise);
    promise.then(() => pendingCleanup.delete(promise), () => pendingCleanup.delete(promise));
    return promise;
  };
  const bestEffort = (fn) => track(Promise.resolve().then(fn).catch(() => {}));
  async function drain() {
    // This grace is for retaining late original results and attempting cleanup,
    // never a provider stop guarantee or permission to restart the operation.
    let timer;
    const deadline = new Promise(resolve => { timer = setTimeout(() => resolve(false), WORKER_SHUTDOWN_DRAIN_MS); });
    try {
      while (pendingCleanup.size) {
        if (!await Promise.race([Promise.allSettled([...pendingCleanup]).then(() => true), deadline]))
          return false;
      }
      return true;
    } finally { clearTimeout(timer); }
  }
  function cleanup() {
    if (finished) return;
    unknown("terminal_receipt_missing");
    finished = true;
    endLocal();
    void bestEffort(() => session?.cancel());
  }
  function unknown(reason) {
    if (finished || uncertain) return;
    uncertain = true;
    try {
      ledger.transition(id, "unknown", { reason });
    } finally {
      status();
    }
    // A durable unknown is a hold, not proof that the local receiver has ended.
    void stop(reason);
  }
  async function release() {
    for (const key of keys) {
      if (finished) { keys.clear(); return; }
      // Keep the attempted key identity even if the transport never confirms
      // this send. Removing it locally prevents a second send after uncertainty;
      // it does not prove that the provider released the key.
      ledger.audit("key_release_attempt", { operation_id: id, key, at_ms: Date.now() });
      keys.delete(key);
      try {
        await bounded(session?.send({
          event_type: "user_action",
          action: "key_up",
          input: KEYS[key],
        }));
      } catch (error) {
        if (!finished)
          ledger.audit("key_release_unknown", { operation_id: id, key, at_ms: Date.now() });
        throw error;
      }
    }
  }
  async function stop(reason = "user_stop") {
    if (stopping || finished) return;
    stopping = true;
    stopAt = performance.now();
    if (!uncertain) ledger.transition(id, "stop_requested", { reason });
    status();
    // A blocked key-up must not prevent the independent completion request.
    void release().catch(() => unknown("release_transport_lost"));
    try {
      await bounded(session?.complete());
    } catch {
      unknown("stop_transport_lost");
    }
  }
  async function control(event) {
    if (event.type === "manager_heartbeat") {
      managerAt = performance.now();
      return;
    }
    if (event.type === "heartbeat") {
      viewerAt = performance.now();
      return;
    }
    if (event.type === "stop") {
      await stop();
      return;
    }
    if (event.type === "release") {
      if (finished || stopping) return;
      ledger.audit("control_release", { operation_id: id, at_ms: Date.now() });
      try {
        await release();
      } catch {
        unknown("release_transport_lost");
      }
      return;
    }
    if (event.type === 'event') need(!finished && !stopping && session && ledger.get(id).state === 'active', 'event_unavailable');
    if (finished || stopping || !session || ledger.get(id).state !== "active")
      return;
    const now = performance.now();
    if (event.type === "event_ready") {
      readyUntil = now + 2000;
      ledger.audit("event_ready", { operation_id: id, at_ms: Date.now() });
      return;
    }
    if (event.type === "event") {
      need(now <= readyUntil, "event_target_not_ready");
      readyUntil = 0;
      if (ledger.claimEvent(id, event.event_id)) {
        try {
          const p=projection();
          for(let i=0;i<p.event_send_count;i++){
            if(finished||uncertain||stopping)return;
            const result = await bounded(session.send(p.event_text));
            if (result === ended || finished || uncertain) return;
            if(i+1<p.event_send_count) await bounded(new Promise(resolve=>setTimeout(resolve,150)));
          }
          ledger.eventSent(id);
          status();
        } catch {
          unknown("event_send_unknown");
        }
      }
      return;
    }
    need(
      event.type === "key" &&
        Object.hasOwn(KEYS, event.key) &&
        typeof event.down === "boolean",
      "invalid_control",
    );
    if (event.down) {
      if (keys.has(event.key)) return;
      if (now - keyWindow >= 1000) {
        keyWindow = now;
        keyCount = 0;
      }
      if (++keyCount > 10) {
        await stop("input_rate");
        return;
      }
      keys.add(event.key);
    } else {
      if (!keys.has(event.key)) return;
      keys.delete(event.key);
    }
    ledger.audit("movement", {
      operation_id: id,
      key: event.key,
      down: event.down,
      at_ms: Date.now(),
    });
    try {
      await bounded(session.send({
        event_type: "user_action",
        action: event.down ? "key_down" : "key_up",
        input: KEYS[event.key],
      }));
    } catch {
      unknown("control_send_unknown");
    }
  }
  const enqueue = (event) => {
    const execute = async () => {
      try {
        await control(event);
        if (event.request_id) {
          ledger.settleControl(event.request_id, ledger.get(id).state === 'unknown' ? 'unknown' : 'accepted');
          status();
        }
      } catch (e) {
        if (event.request_id) {
          ledger.settleControl(event.request_id, 'refused', e.code || 'control_error');
          status();
        }
        emit({ type: 'error', code: e.code || 'control_error' });
      }
    };
    // Liveness and stop never queue behind a potentially blocked movement send.
    if (["stop", "heartbeat", "manager_heartbeat"].includes(event.type))
      return execute();
    controls = controls
      .then(execute)
      .catch((e) => emit({ type: "error", code: e.code || "control_error" }));
    return controls;
  };
  async function run() {
    if (admitted.provider === 'google') {
      const current = ledger.get(id);
      sessionPolicy(current);
      need(current.state === 'create_pending' && current.usage_state === 'reserved' &&
        !current.provider_id && hash(current) === hash(admitted), 'campaign_session_changed');
    }
    const timer = setInterval(() => {
      if (finished) return;
      const now = performance.now();
      if (stopping) {
        if (
          stopAt !== null &&
          now - stopAt >= policy.terminal_wait_seconds * 1000
        ) {
          cleanup();
        }
        return;
      }
      const reason =
        now - start >= policy.deadline_seconds_from_send * 1000
          ? "deadline"
          : firstFrame === null &&
              now - start >= policy.first_frame_timeout_seconds * 1000
            ? "first_frame_timeout"
            : firstFrame !== null &&
                now - firstFrame >= policy.target_seconds * 1000
              ? "target_duration"
              : now - viewerAt >= policy.viewer_lost_seconds * 1000
                ? "viewer_lost"
                : now - managerAt >= policy.manager_lost_seconds * 1000
                  ? "manager_lost"
                  : null;
      if (reason) void stop(reason).catch(() => unknown("stop_failed"));
    }, 25);
    try {
      if (Date.now() >= Date.parse(ledger.get(id).deadline_at)) {
        ledger.transition(id, "failed_pre_send", {
          reason: "deadline_before_transport",
        });
        finished = true;
        status();
        return;
      }
      const opening = track(Promise.resolve().then(open));
      // If creation returns after local expiry, close that original transport;
      // do not emit setup, mutate a closed ledger or create another operation.
      opening.then((late) => {
        if (finished) void bestEffort(() => late.cancel());
      }, () => {});
      session = await bounded(opening);
      if (session === ended) { session = null; return; }
      ledger.providerId(id, session.id);
      if (finished) {
        void bestEffort(() => session.cancel());
        return;
      }
      receiver = session.receive()[Symbol.asyncIterator]();
      if (stopping) {
        void bestEffort(() => session.complete());
      } else
        void Promise.resolve().then(() => session.send({
          event_type: "world_setup",
          world_prompt: { text: projection().text },
        })).catch(() => unknown("setup_send_unknown"));
      while (!finished) {
        const next = await bounded(receiver.next());
        if (next === ended || next.done) break;
        const event = next.value;
        if (['interaction.completed', 'interaction.cancelled', 'interaction.canceled'].includes(event.event_type)) {
          ledger.terminal(id, event);
          finished = true;
          endLocal();
          status();
          break;
        }
        if (uncertain) continue;
        if (event.event_type === "error") {
          void stop("provider_error");
          continue;
        }
        if (
          event.event_type === "step.delta" &&
          event.delta?.type === "video"
        ) {
          need(
            typeof event.delta.data === "string" &&
              event.delta.data.length <= 2800000,
            "invalid_media",
          );
          const bytes = Buffer.from(event.delta.data, "base64");
          need(
            bytes.length <= 2 * 1024 * 1024 &&
              bytes[0] === 255 &&
              bytes[1] === 216,
            "invalid_media",
          );
          if (firstFrame === null) {
            firstFrame = performance.now();
            if (!stopping) ledger.transition(id, "active");
            status();
          }
          emit({
            type: "frame",
            sequence: ++seq,
            at: Date.now(),
            data: bytes.toString("base64"),
          });
        }
      }
      if (!finished) unknown("stream_closed_without_receipt");
    } catch {
      unknown("provider_outcome_unknown");
    } finally {
      if (!finished) {
        // Receive/open failure still gives completion a bounded grace period.
        await localEnd;
      }
      clearInterval(timer);
      void bestEffort(() => receiver?.return?.());
      if (session && !finished) unknown("worker_ended");
      emit({ type: "done" });
    }
  }
  return { run, control: enqueue, stop, unknown, drain };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [root, id, provider, packetPath] = process.argv.slice(2);
  const ledger = new Ledger(root);
  const emit = (msg) => {
    if (process.connected) process.send(msg);
  };
  const open = async () => {
    if (provider === "google") {
      const packet = loadLivePacket(packetPath);
      need(packet.state_root === root, "live_packet_mismatch");
      return openGoogle({ ledger, id, apiKey: loadCredential(packet.credential_file) });
    }
    need(provider === "fixture", "live_gate_closed");
    return new FixtureProvider();
  };
  const worker = createSessionWorker({ ledger, id, open, emit });
  process.on("message", (msg) => void worker.control(msg));
  process.on("disconnect", () => void worker.stop("manager_disconnected"));
  process.on("SIGTERM", () => void worker.stop("worker_signal"));
  worker.run().finally(async () => {
    const drained = await worker.drain();
    ledger.audit('worker_shutdown_drain', { operation_id: id, outcome: drained ? 'drained' : 'deadline' });
    ledger.close();
    process.exit(0);
  });
}
