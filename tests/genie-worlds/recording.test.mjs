import test from "node:test";
import assert from "node:assert/strict";
import { writeFileSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { createBrowserFixture } from "./browser-fixture.mjs";
import { createManager } from "../../scripts/genie-worlds/manager.mjs";
import { chromium } from "../../scripts/genie-worlds/node_modules/playwright-core/index.mjs";

for (const fault of ["final_response_loss", "evidence_response_loss", "browser_death"]) {
  test(`actual Chrome recording receipt recovery: ${fault}`, {
    skip: !process.env.NETCLAW_BROWSER_EXECUTABLE, timeout: 15000,
  }, async (t) => {
    const { root, m, server, browser } = await createBrowserFixture(t, "receipt-recovery-", {
      launchServer: options => chromium.launchServer(options),
    });
    const page = await browser.newPage();
    const requests = [], errors = [], external = [];
    page.on("request", r => {
      requests.push({ path: new URL(r.url()).pathname, method: r.method() });
      if (!r.url().startsWith(m.origin)) external.push(r.url());
    });
    page.on("pageerror", e => errors.push(e.message));
    await page.addInitScript((fault) => {
      const realFetch = window.fetch;
      window.capture = { uploaded: 0, finalCommitted: false };
      window.fetch = async (url, options) => {
        if (fault === "evidence_response_loss" && String(url).endsWith("/evidence"))
          throw new TypeError("Synthetic recovery response loss");
        const response = await realFetch(url, options);
        if (String(url).endsWith("/recording") && response.ok) window.capture.uploaded += options.body.size;
        if (String(url).endsWith("/recording-final") && response.ok) {
          // Server has committed, but the viewer never receives the reply.
          await response.arrayBuffer(); window.capture.finalCommitted = true;
          throw new TypeError("Synthetic final acknowledgement response loss");
        }
        return response;
      };
    }, fault);
    await page.goto(m.origin + "/#" + m.bootstrap);
    await page.getByRole("button", { name: "Review and start fixture" }).click();
    await page.waitForFunction(() => window.capture.uploaded > 0);
    const id = m.ledger.list()[0].operation_id;
    let capture, receipt;
    if (fault !== "browser_death") {
      await page.getByRole("button", { name: "Stop session", exact: true }).click();
      await page.waitForFunction(() => window.capture.finalCommitted);
      if (fault === "final_response_loss") {
        await page.getByRole("button", { name: "View evidence" }).click();
        await page.waitForFunction(() => document.querySelector("#result").textContent.includes("live_world_proven"));
        receipt = JSON.parse(await page.locator("#result").innerText()).recording.receipt;
      } else await page.waitForFunction(() => document.querySelector("#status").textContent.includes("Recording final confirmation unavailable"));
      capture = await page.evaluate(() => window.capture);
    } else {
      capture = await page.evaluate(() => window.capture);
      const child = server.process();
      const exited = new Promise(resolve => child.once("exit", resolve));
      child.kill("SIGKILL"); await exited;
      assert.equal(capture.finalCommitted, false);
    }
    await m.close();
    const restarted = await createManager({ root });
    let evidence;
    try {
      evidence = await (await fetch(`${restarted.origin}/v1/sessions/${id}/evidence`, {
        headers: { Authorization: `Bearer ${restarted.owner}` },
      })).json();
      assert.equal(restarted.ledger.list().length, 1);
      assert.equal(restarted.workers.size, 0);
    } finally { await restarted.close(); }
    if (process.env.NETCLAW_BROWSER_EVIDENCE) writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,
      `receipt-recovery-${fault}.json`), JSON.stringify({ capture, requests, evidence, errors, external,
        actual_browser: true, synthetic_provider: true, google_calls: 0 }, null, 2), { mode: 0o600 });
    assert.equal(evidence.session.operation_id, id);
    assert.equal(evidence.recording.state, fault !== "browser_death" ? "final_flush_acknowledged" : "unconfirmed");
    assert.deepEqual(evidence.recording_failures, []);
    assert.equal(evidence.live_world_proven, false);
    assert.equal(requests.filter(r => r.path === "/v1/sessions" && r.method === "POST").length, 1);
    assert.equal(requests.filter(r => r.path.endsWith("/recording-final")).length, fault !== "browser_death" ? 1 : 0);
    const media = evidence.manifest.find(a => a.mime === "video/webm");
    assert(media.size_bytes > 0);
    if (fault !== "browser_death") {
      if (receipt) assert.deepEqual(evidence.recording.receipt, receipt);
      assert.equal(media.sha256, evidence.recording.receipt.sha256);
      assert.equal(media.size_bytes, capture.uploaded);
      assert.equal(evidence.recording.receipt.size_bytes, capture.uploaded);
    } else assert.equal(evidence.recording.receipt, null);
    assert.deepEqual(errors, []); assert.deepEqual(external, []);
  });
}

for (const finalDelay of [0, 250, 1250]) {
  test(`actual Chrome final recorder flush during manager shutdown: ${finalDelay}ms upload delay`, {
    skip: !process.env.NETCLAW_BROWSER_EXECUTABLE, timeout: 15000,
  }, async (t) => {
    const { root, m, browser } = await createBrowserFixture(t, "shutdown-recording-");
    const page = await browser.newPage();
    const errors = [], external = [];
    page.on("pageerror", e => errors.push(e.message));
    page.on("request", r => { if (!r.url().startsWith(m.origin)) external.push(r.url()); });
    await page.addInitScript((finalDelay) => {
      const Real = window.MediaRecorder;
      window.capture = { chunks: [], uploads: [] };
      window.MediaRecorder = class extends Real {
        constructor(...args) {
          super(...args); window.testRecorder = this;
          this.addEventListener("dataavailable", e => {
            if (e.data.size) window.capture.chunks.push({ bytes: e.data.size, final: this.state === "inactive" });
          });
        }
      };
      const realFetch = window.fetch;
      window.fetch = async (url, options) => {
        if (!String(url).endsWith("/recording")) return realFetch(url, options);
        const row = { bytes: options.body.size, final: window.testRecorder.state === "inactive" };
        window.capture.uploads.push(row);
        if (row.final && finalDelay) await new Promise(r => setTimeout(r, finalDelay));
        try { const response = await realFetch(url, options); row.status = response.status; return response; }
        catch (e) { row.error = e.name; throw e; }
      };
    }, finalDelay);
    await page.goto(m.origin + "/#" + m.bootstrap);
    await page.getByRole("button", { name: "Review and start fixture" }).click();
    await page.waitForFunction(() => window.capture.uploads.some(x => x.status === 200));
    const id = m.ledger.list()[0].operation_id;
    await m.close();
    await page.waitForFunction(() => window.capture.uploads.some(x => x.final && (x.status || x.error)));
    const capture = await page.evaluate(() => window.capture);
    if (finalDelay > 1000) await page.waitForFunction(() => document.querySelector("#status").textContent.includes("Recording incomplete"));
    const status = await page.locator("#status").innerText();
    // Reopen the same ledger through a fresh manager, without starting a session.
    const restarted = await createManager({ root });
    let evidence;
    try {
      evidence = await (await fetch(`${restarted.origin}/v1/sessions/${id}/evidence`, {
        headers: { Authorization: `Bearer ${restarted.owner}` },
      })).json();
      assert.equal(restarted.ledger.list().length, 1);
      assert.equal(restarted.workers.size, 0);
    } finally { await restarted.close(); }
    if (process.env.NETCLAW_BROWSER_EVIDENCE) writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,
      `shutdown-recording-${finalDelay}.json`), JSON.stringify({ capture, status, evidence, errors, external, google_calls: 0 }, null, 2), { mode: 0o600 });
    assert.equal(evidence.recording.state, finalDelay <= 1000 ? "final_flush_acknowledged" : "unconfirmed");
    if (finalDelay <= 1000) {
      const media = evidence.manifest.find(x => x.mime === "video/webm");
      assert.equal(evidence.recording.receipt.sha256, media.sha256);
      assert.equal(evidence.recording.receipt.size_bytes, media.size_bytes);
    } else assert.equal(evidence.recording.reason, "final_flush_unconfirmed");
    assert(capture.chunks.some(x => x.final && x.bytes > 0), "real MediaRecorder emits final bytes");
    if (finalDelay <= 1000) assert(capture.uploads.every(x => x.status === 200), "all real recording chunks retained at shutdown");
    else {
      assert(capture.uploads.some(x => x.final && x.error), "late upload cannot extend bounded shutdown");
      assert(status.includes("Recording incomplete"), "late loss is explicitly unsuccessful evidence");
    }
    assert.deepEqual(errors, []); assert.deepEqual(external, []);
    assert.equal(readFileSync(join(root, "artifacts", id, "viewer.webm")).length,
      capture.uploads.filter(x => x.status === 200).reduce((sum, x) => sum + x.bytes, 0));
    if (finalDelay <= 1000) assert.equal(capture.chunks.reduce((sum, x) => sum + x.bytes, 0),
      capture.uploads.reduce((sum, x) => sum + x.bytes, 0));
  });
}

for (const fault of ["constructor", "recorder", "upload", "upload_timeout"]) {
  test(`actual Chrome recording failure: ${fault}`, {
    skip: !process.env.NETCLAW_BROWSER_EXECUTABLE, timeout: 15000,
  }, async (t) => {
    const { root, m, browser } = await createBrowserFixture(t, "recording-");
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [], external = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => { if (!r.url().startsWith(m.origin)) external.push(r.url()); });
    await page.addInitScript((fault) => {
      const Real = window.MediaRecorder;
      window.MediaRecorder = class extends Real {
        constructor(...args) {
          if (fault === "constructor") throw Error("synthetic recorder constructor failure");
          super(...args); window.testRecorder = this;
        }
      };
      const fetchReal = window.fetch;
      window.fetch = (url, options) => {
        if (String(url).endsWith("/recording")) {
          window.uploadAttempts = (window.uploadAttempts || 0) + 1;
          if (fault === "upload") return Promise.resolve(new Response("", { status: 503 }));
          if (fault === "upload_timeout") return new Promise((resolve, reject) => {
            options?.signal?.addEventListener("abort", () => reject(new DOMException("Synthetic timeout", "AbortError")), { once: true });
          });
        }
        return fetchReal(url, options);
      };
    }, fault);
    await page.goto(m.origin + "/#" + m.bootstrap);
    await page.getByRole("button", { name: "Review and start fixture" }).click();
    if (fault === "recorder") {
      await page.waitForFunction(() => window.testRecorder?.state === "recording");
      await page.evaluate(() => window.testRecorder.dispatchEvent(new Event("error")));
    }
    await page.waitForFunction(() => document.querySelector("#status").textContent.includes("Recording incomplete"), null, { timeout: 6000 });
    await page.waitForFunction(() => document.querySelector("#status").textContent.includes("· terminal ·"), null, { timeout: 2000 });
    await page.getByRole("button", { name: "View evidence" }).click();
    await page.waitForFunction(() => document.querySelector("#result").textContent.includes("recording_failures"));
    const evidence = JSON.parse(await page.locator("#result").innerText());
    const code = fault === "constructor" ? "recording_start_failed" : fault === "recorder" ? "recording_failed" : "recording_upload_failed";
    assert.deepEqual(evidence.recording_failures.map((f) => f.code), [code]);
    assert.equal(evidence.session.terminal_confirmed, true);
    assert.equal(evidence.live_world_proven, false);
    assert.equal(m.ledger.list().length, 1);
    assert.deepEqual(errors, []); assert.deepEqual(external, []);
    assert(await page.locator("#start").isDisabled());
    if (fault.startsWith("upload")) assert.equal(await page.evaluate(() => window.uploadAttempts), 1);
    if (process.env.NETCLAW_BROWSER_EVIDENCE) writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE, `recording-${fault}.json`), JSON.stringify(evidence, null, 2), { mode: 0o600 });
    if (fault === "recorder" && process.env.NETCLAW_BROWSER_EVIDENCE) {
      for (const width of [1280, 820]) {
        await page.setViewportSize({ width, height: 900 });
        assert.equal(await page.locator("h1").count(), 1);
        await page.locator("#status").scrollIntoViewIfNeeded();
        await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await page.screenshot({ path: join(process.env.NETCLAW_BROWSER_EVIDENCE, `recording-failure-${width}.png`) });
      }
    }
  });
}
