import { randomId } from '../shared/random-id.js';
// Extracted from NetClaw Canvas; see LICENSE for the adapted workflow.
import { escHtml, nodeTitle, downloadTextFile, branchFileName } from "./canvas-export.js";
import React, { useRef, useState, useCallback, useEffect, useMemo } from "react";
import TerminalEnrichmentPopover, { useTerminalEnrichmentHover } from "./TerminalEnrichmentPopover.jsx";
import { terminalContentColumns } from "./enrichment-layout.js";
import { normalizeTerminalIntentHistory, normalizeTerminalCommandOutput, buildTerminalIntentMessages, parseTerminalIntentResponse, shouldAutoRunTerminalIntent, terminalCommandsToInput } from "./terminal-intent.js";
import { detectTerminalEnrichmentObjects } from "./terminal-enrichment.js";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { installTerminalMouseCoordinates } from "./terminal-mouse-coordinates.js";
import { apiError, callTerraTerminal } from "./terminal-api.js";
import TerminalIntentExecution, { executionResultText, TerminalIntentLiveActivity } from "./TerminalIntentExecution.jsx";
import { artifactFormat, buildTerminalArtifact, ARTIFACT_FORMATS } from "./artifact-formats.js";
import { COLLAPSED_H, C, DARK, LIGHT } from "./canvas-theme.js";
import { createPortal } from "react-dom";
import TerminalEnrichmentDemo from "./TerminalEnrichmentDemo.jsx";
import { TopologySettings, TopologyRouteContext } from "./TopologyContext.jsx";
import { ObservabilitySettings, ObservabilityContext } from "./ObservabilityContext.jsx";
import { topologyDiagramKey } from "./topology-image-store.js";
import GenieJsonOutput from "./GenieJsonOutput.jsx";
import TerminalChangeControl from "./TerminalChangeControl.jsx";
import TerminalIntentActivity from "./TerminalIntentActivity.jsx";
import "@xterm/xterm/css/xterm.css";
import "./TerminalChrome.css";

import { TERMINAL_TRANSCRIPT_LIMIT } from "./terminal-constants.js";

function terminalSocketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

function decodeTerminalBytes(encoded) {
  const binary = window.atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function terminalBufferText(terminal) {
  const buffer = terminal?.buffer?.normal || terminal?.buffer?.active;
  if (!buffer) return "";
  const lines = [];
  for (let row = 0; row < buffer.length; row += 1) {
    lines.push(buffer.getLine(row)?.translateToString(true) || "");
  }
  return lines.join("\n").replace(/\s+$/, "");
}

function terminalTranscriptHtml(node, transcript) {
  const title = escHtml(nodeTitle(node) || "SSH Terminal");
  return `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title>
<style>body{margin:0;padding:28px;background:#090e14;color:#d6deeb;font-family:"Cascadia Mono",Consolas,monospace}h1{font:600 18px system-ui,sans-serif;color:#7fdbca;margin:0 0 18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.45;font-size:13px}</style>
</head><body><h1>${title}</h1><pre>${escHtml(transcript)}</pre></body></html>`;
}

function TerminalLane({ node, color, isActive, selected, animate, dark, laneRef, onFocus, onDragStart, onResizeStart, onToggleMin, onDelete, highlights, onSelect, onAutoFit, onOpenConfigReview, onCreateResult, onPatch }) {
  const terminalHostRef = useRef(null);
  const terminalRef = useRef(null);
  const fitRef = useRef(null);
  const socketRef = useRef(null);
  const credentialOverrideRef = useRef(null);
  const manualCloseRef = useRef(false);
  const transcriptRef = useRef(node.terminalTranscript || "");
  const transcriptTimerRef = useRef(null);
  const transcriptDecoderRef = useRef(new TextDecoder());
  const transcriptLimitReachedRef = useRef((node.terminalTranscript || "").length >= TERMINAL_TRANSCRIPT_LIMIT);
  const decorationsRef = useRef([]);
  const enrichmentDecorationsRef = useRef([]);
  const enrichmentRecordsRef = useRef(new Map());
  const enrichmentRequestedRef = useRef(new Set());
  const enrichmentScanTimerRef = useRef(null);
  const enrichmentScanRef = useRef(() => {});
  const exportBtnRef = useRef(null);
  const intentLogRef = useRef(null);
  const readOnlyCaptureRef = useRef(null);
  const readOnlyCaptureTimerRef = useRef(null);
  const readOnlyCaptureSequenceRef = useRef(0);
  const [devices, setDevices] = useState([]);
  const [deviceId, setDeviceId] = useState(node.terminalDevice || "");
  const [status, setStatus] = useState("idle");
  const [statusMessage, setStatusMessage] = useState("Choose a testbed device to begin.");
  const [legacyKexEnabled, setLegacyKexEnabled] = useState(node.terminalLegacySshCompatibility === true);
  const [legacyKexRetryAvailable, setLegacyKexRetryAvailable] = useState(false);
  const [credentialsOpen, setCredentialsOpen] = useState(false);
  const [credentialsReady, setCredentialsReady] = useState(false);
  const [credentialsError, setCredentialsError] = useState("");
  const [credentialsForm, setCredentialsForm] = useState({
    username: "",
    password: "",
  });
  const [hostKey, setHostKey] = useState(null);
  const [hostKeyResetBusy, setHostKeyResetBusy] = useState(false);
  const [traditionalTerminalOverlayOpen, setTraditionalTerminalOverlayOpen] = useState(false);
  const [enrichmentEnabled, setEnrichmentEnabled] = useState(node.terminalEnrichmentEnabled !== false);
  const enrichmentHover = useTerminalEnrichmentHover();
  const enrichmentPopover = enrichmentHover.card?.data;
  const [topologyOpen, setTopologyOpen] = useState(false);
  const [topologyImageContext, setTopologyImageContext] = useState(null);
  const [observabilityOpen, setObservabilityOpen] = useState(false);
  const closeObservability = useCallback(() => setObservabilityOpen(false), []);
  const openObservability = useCallback(() => { enrichmentHover.close(false); setObservabilityOpen(true); }, [enrichmentHover.close]);
  const closeTopologySettings = useCallback(() => setTopologyOpen(false), []);
  const openTopologySettings = useCallback(() => { enrichmentHover.close(false); setTopologyOpen(true); }, [enrichmentHover.close]);
  const getEnrichmentContentRight = useCallback(() => {
    const terminal = terminalRef.current;
    const screen = terminalHostRef.current?.querySelector(".xterm-screen");
    const columns = terminalContentColumns(terminal);
    if (!screen || columns == null || !terminal.cols) return null;
    const rect = screen.getBoundingClientRect();
    return rect.left + (rect.width / terminal.cols) * columns;
  }, []);
  const [exportOpen, setExportOpen] = useState(false);
  const [enrichmentSpaceUnavailable, setEnrichmentSpaceUnavailable] = useState(false);
  const [exportPos, setExportPos] = useState(null);
  const [exportMessage, setExportMessage] = useState(null);
  const [terminalView, setTerminalView] = useState("terminal");
  const [structuredFormat, setStructuredFormat] = useState(node.terminalStructuredFormat || "json");
  const [structuredSelection, setStructuredSelection] = useState(null);
  const [geniePreview, setGeniePreview] = useState(null);
  useEffect(() => {
    const request = node.terminalGenieRequest;
    if (!request) return;
    setStructuredFormat('json');
    setStructuredSelection({ quote: request.source, range: request.range, sourceType: 'selection' });
    setTerminalView('structured');
    onPatch({ terminalGenieRequest: null });
  }, [node.terminalGenieRequest?.id]);
  const [terminalAssistantMode, setTerminalAssistantMode] = useState(
    node.terminalAssistantMode === "terra" ? "terra" : "netclaw",
  );
  const [terraStatus, setTerraStatus] = useState({ checked: false, configured: false, model: "chat-latest" });
  const [terraConfigOpen, setTerraConfigOpen] = useState(false);
  const [terraApiKey, setTerraApiKey] = useState("");
  const [terraConfigBusy, setTerraConfigBusy] = useState(false);
  const [terraConfigError, setTerraConfigError] = useState("");
  const [intentHistory, setIntentHistory] = useState(() => normalizeTerminalIntentHistory(node.terminalIntentHistory));
  const intentHistoryRef = useRef(normalizeTerminalIntentHistory(node.terminalIntentHistory));
  const [intentPrompt, setIntentPrompt] = useState("");
  const [intentRun, setIntentRun] = useState(() => node.terminalIntentRun
    ? { ...node.terminalIntentRun, status: node.terminalIntentRun.status === 'submitting' ? 'running' : node.terminalIntentRun.status }
    : null);
  const [intentChangeControl, setIntentChangeControl] = useState({ mode: node.terminalChangeMode || 'production', targetDeviceIds: node.terminalChangeDevices || [], policyRevision: null });
  const [intentPhase, setIntentPhase] = useState(['submitting', 'running'].includes(node.terminalIntentRun?.status) ? 'execution' : 'idle');
  const intentBusy = intentPhase !== 'idle';
  const [intentError, setIntentError] = useState("");
  const [approvedIntentId, setApprovedIntentId] = useState(null);
  const [bufferReady, setBufferReady] = useState(0);
  const [profilesBusy, setProfilesBusy] = useState(false);
  const [addDeviceOpen, setAddDeviceOpen] = useState(false);
  const [deviceEditMode, setDeviceEditMode] = useState("add");
  const [addDeviceBusy, setAddDeviceBusy] = useState(false);
  const [addDeviceError, setAddDeviceError] = useState("");
  const [addDeviceForm, setAddDeviceForm] = useState({
    id: "",
    alias: "",
    host: "",
    port: "22",
    type: "device",
    os: "",
    platform: "",
  });

  const persistTranscriptSoon = () => {
    if (transcriptTimerRef.current) window.clearTimeout(transcriptTimerRef.current);
    transcriptTimerRef.current = window.setTimeout(() => {
      transcriptTimerRef.current = null;
      onPatch({ terminalTranscript: transcriptRef.current });
    }, 750);
  };

  const appendTranscript = (text) => {
    if (!text || transcriptLimitReachedRef.current) return;
    const next = transcriptRef.current + text;
    if (next.length > TERMINAL_TRANSCRIPT_LIMIT) {
      transcriptRef.current = `${next.slice(0, TERMINAL_TRANSCRIPT_LIMIT)}\r\n[Local transcript storage limit reached; live output continues.]\r\n`;
      transcriptLimitReachedRef.current = true;
    } else {
      transcriptRef.current = next;
    }
    persistTranscriptSoon();
  };

  const persistTranscriptNow = ({ flushDecoder = false } = {}) => {
    if (flushDecoder) {
      const tail = transcriptDecoderRef.current.decode();
      if (tail) appendTranscript(tail);
      transcriptDecoderRef.current = new TextDecoder();
    }
    if (transcriptTimerRef.current) {
      window.clearTimeout(transcriptTimerRef.current);
      transcriptTimerRef.current = null;
    }
    onPatch({ terminalTranscript: transcriptRef.current });
  };

  const sendSocket = (type, payload = {}) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type, payload }));
      return true;
    }
    return false;
  };

  const clearPendingCredentials = ({ clearUsername = false } = {}) => {
    credentialOverrideRef.current = null;
    setCredentialsReady(false);
    setCredentialsError("");
    setCredentialsForm((current) => ({
      username: clearUsername ? "" : current.username,
      password: "",
    }));
  };

  useEffect(() => {
    let disposed = false;
    fetch("/api/terminal/devices")
      .then((response) => {
        if (!response.ok) throw new Error(`API ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (disposed) return;
        const list = Array.isArray(data.devices) ? data.devices : [];
        setDevices(list);
        const readyDevice = list.find((device) => device.id === deviceId && device.supported)
          || list.find((device) => device.supported);
        if (!deviceId && readyDevice) {
          setDeviceId(readyDevice.id);
          onPatch({ terminalDevice: readyDevice.id, title: `Terminal · ${readyDevice.id}` });
        }
        setStatusMessage(
          readyDevice
            ? `Ready to connect to ${readyDevice.alias || readyDevice.name}.`
            : "No supported SSH profiles were found in testbed.yaml.",
        );
      })
      .catch((error) => {
        if (!disposed) {
          setStatus("error");
          setStatusMessage(`Unable to load testbed devices: ${error.message}`);
        }
      });
    return () => { disposed = true; };
  }, []);

  const refreshTerraStatus = async () => {
    try {
      const response = await fetch("/api/terminal/terra/status");
      const data = response.ok ? await response.json() : { configured: false };
      const configured = data?.configured === true;
      setTerraStatus({ checked: true, configured, model: data?.model || "chat-latest" });
      if (!configured && terminalAssistantMode === "terra") {
        setTerminalAssistantMode("netclaw");
        onPatch({ terminalAssistantMode: "netclaw" });
      }
      return configured;
    } catch {
      setTerraStatus({ checked: true, configured: false, model: "chat-latest" });
      return false;
    }
  };

  useEffect(() => { refreshTerraStatus(); }, []);

  const reloadDeviceProfiles = async () => {
    setProfilesBusy(true);
    try {
      const response = await fetch("/api/terminal/devices");
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `API ${response.status}`);
      const list = Array.isArray(data.devices) ? data.devices : [];
      setDevices(list);
      const readyDevice = list.find((device) => device.id === deviceId && device.supported)
        || list.find((device) => device.supported)
        || null;
      const nextId = readyDevice?.id || "";
      if (nextId !== deviceId) {
        setDeviceId(nextId);
        setLegacyKexEnabled(false);
        setLegacyKexRetryAvailable(false);
        clearPendingCredentials({ clearUsername: true });
        onPatch({
          terminalDevice: nextId || null,
          title: nextId ? `Terminal · ${nextId}` : "SSH Terminal",
          terminalLegacySshCompatibility: false,
        });
      }
      setStatus("idle");
      setStatusMessage(
        readyDevice
          ? `Reloaded testbed.yaml. Ready to connect to ${readyDevice.alias || readyDevice.name}.`
          : "No supported SSH profiles were found in testbed.yaml.",
      );
    } catch (error) {
      setStatus("error");
      setStatusMessage(`Unable to reload testbed devices: ${error.message}`);
    } finally {
      setProfilesBusy(false);
    }
  };

  const setAddDeviceField = (field, value) => {
    setAddDeviceForm((current) => ({ ...current, [field]: value }));
  };

  const openDeviceEditor = (mode) => {
    const device = devices.find(entry => entry.id === deviceId);
    if (mode !== "add" && !device) return;
    setDeviceEditMode(mode);
    setAddDeviceError("");
    setAddDeviceForm(mode === "add"
      ? { id: "", alias: "", host: "", port: "22", type: "device", os: "", platform: "" }
      : { id: device.id, alias: device.alias, host: device.host, port: String(device.port || 22),
        type: device.type || "device", os: device.os, platform: device.platform, revision: device.revision });
    setAddDeviceOpen(true);
  };

  const submitAddDevice = async (event) => {
    event.preventDefault();
    setAddDeviceBusy(true);
    setAddDeviceError("");
    try {
      const response = await fetch(deviceEditMode === "add" ? "/api/terminal/devices"
        : `/api/terminal/devices/${encodeURIComponent(addDeviceForm.id)}`, {
        method: deviceEditMode === "add" ? "POST" : deviceEditMode === "edit" ? "PUT" : "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(deviceEditMode === "remove"
          ? { revision: addDeviceForm.revision, confirmDevice: addDeviceForm.id } : addDeviceForm),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `API ${response.status}`);
      if (deviceEditMode === "remove") {
        setDevices(data.devices || []);
        setDeviceId("");
        clearPendingCredentials({ clearUsername: true });
        setLegacyKexEnabled(false);
        setLegacyKexRetryAvailable(false);
        onPatch({ terminalDevice: null, title: "SSH Terminal", terminalLegacySshCompatibility: false });
        setStatus("idle");
        setStatusMessage(`Removed ${addDeviceForm.alias || addDeviceForm.id} from the testbed and revoked its collection. A local inventory backup was saved. The device itself was not changed.`);
        setAddDeviceOpen(false);
        return;
      }
      if (!data.device) throw new Error("The device was saved but its SSH profile could not be loaded.");
      setDevices((current) => (
        (data.devices || [...current.filter((device) => device.id !== data.device.id), data.device])
          .sort((left, right) => left.id.localeCompare(right.id))
      ));
      setDeviceId(data.device.id);
      setLegacyKexEnabled(false);
      setLegacyKexRetryAvailable(false);
      clearPendingCredentials({ clearUsername: true });
      onPatch({
        terminalDevice: data.device.id,
        title: `Terminal · ${data.device.id}`,
        terminalLegacySshCompatibility: false,
      });
      setStatus("idle");
      setStatusMessage(
        deviceEditMode === "edit"
          ? `Updated ${data.device.alias || data.device.name}. Log in and authorize collection again. A local inventory backup was saved.`
          : `Added ${data.device.alias || data.device.name} to testbed.yaml. No connection was attempted.`,
      );
      setAddDeviceOpen(false);
      setAddDeviceForm({
        id: "",
        alias: "",
        host: "",
        port: "22",
        type: "device",
        os: "",
        platform: "",
      });
    } catch (error) {
      setAddDeviceError(error.message || "Unable to save this device.");
    } finally {
      setAddDeviceBusy(false);
    }
  };

  const clearEnrichmentDecorations = () => {
    enrichmentDecorationsRef.current.forEach((entry) => {
      try { entry.dispose(); } catch {}
    });
    enrichmentDecorationsRef.current = [];
  };

  const addLocalTerminalAlias = async () => {
    const entry = window.prompt("Add a local route or IP alias. Format: 10.50.0.0/16 = Branch WAN");
    if (!entry) return;
    const [key, ...labelParts] = entry.split("=");
    const label = labelParts.join("=").trim();
    if (!key?.trim() || !label) {
      setStatusMessage("Alias not saved. Use: IP-or-prefix = descriptive name.");
      return;
    }
    try {
      const current = await fetch("/api/terminal/enrichment/aliases").then((response) => response.ok ? response.json() : { aliases: {} });
      const response = await fetch("/api/terminal/enrichment/aliases", {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ aliases: { ...(current.aliases || {}), [key.trim()]: label } }),
      });
      if (!response.ok) throw new Error();
      enrichmentRequestedRef.current.clear();
      enrichmentRecordsRef.current.clear();
      enrichmentScanRef.current();
      setStatusMessage(`Saved local alias for ${key.trim()}.`);
    } catch { setStatusMessage("Unable to save the local alias."); }
  };

  const renderEnrichmentDecorations = () => {
    clearEnrichmentDecorations();
    if (!enrichmentEnabled) return;
    const terminal = terminalRef.current;
    const buffer = terminal?.buffer?.normal;
    if (!terminal || !buffer) return;
    const cursorLine = buffer.baseY + buffer.cursorY;
    const firstRow = Math.max(0, buffer.length - 500);
    let routeVrf = null;
    for (let row = firstRow; row < buffer.length; row += 1) {
      const line = buffer.getLine(row)?.translateToString(true) || "";
      const routeCommand = line.match(/[>#]\s*sh(?:ow)?\s+ip\s+ro(?:ute)?(?:\s+vrf\s+(\S+))?\s*$/i);
      if (routeCommand) routeVrf = routeCommand[1] === "*" ? null : (routeCommand[1] || "default");
      const routeTable = line.match(/^Routing Table:\s*(.+?)\s*$/);
      if (routeTable) routeVrf = routeTable[1];
      if (/[>#]\s*\S/.test(line) && !routeCommand) routeVrf = null;
      for (const token of detectTerminalEnrichmentObjects(line)) {
        token.vrf = routeVrf;
        const record = enrichmentRecordsRef.current.get(token.value);
        if (!record || token.start >= terminal.cols) continue;
        const marker = terminal.registerMarker(row - cursorLine);
        if (!marker) continue;
        let decoration = null;
        try {
          decoration = terminal.registerDecoration({
            marker,
            x: token.start,
            width: Math.min(token.length, terminal.cols - token.start),
            backgroundColor: record.resolved ? "#0E7C7B35" : "#64748B2B",
            layer: "bottom",
          });
        } catch {}
        if (!decoration) { try { marker.dispose(); } catch {}; continue; }
        decoration.onRender((element) => {
          element.style.outline = `1px solid ${record.resolved ? "#53D3C866" : "#94A3B855"}`;
          element.style.borderRadius = "2px";
          element.style.cursor = "pointer";
          element.style.pointerEvents = "auto";
          const show = (expanded) => {
            enrichmentHover.open({ key: `${row}:${token.start}:${token.value}:${token.vrf || ""}`, token, record }, element, { pin: expanded });
          };
          element.onmouseenter = () => show(false);
          element.onmouseleave = enrichmentHover.scheduleClose;
          element.onclick = (event) => { event.stopPropagation(); show(true); };
        });
        enrichmentDecorationsRef.current.push({ dispose() { try { decoration.dispose(); } catch {}; try { marker.dispose(); } catch {} } });
      }
    }
  };

  enrichmentScanRef.current = () => {
    if (enrichmentScanTimerRef.current) window.clearTimeout(enrichmentScanTimerRef.current);
    enrichmentScanTimerRef.current = window.setTimeout(async () => {
      enrichmentScanTimerRef.current = null;
      if (!enrichmentEnabled) return;
      const buffer = terminalRef.current?.buffer?.normal;
      if (!buffer) return;
      const discovered = [];
      for (let row = Math.max(0, buffer.length - 500); row < buffer.length; row += 1) {
        const line = buffer.getLine(row)?.translateToString(true) || "";
        discovered.push(...detectTerminalEnrichmentObjects(line));
      }
      renderEnrichmentDecorations();
      const unseen = discovered.filter((token) => !enrichmentRequestedRef.current.has(token.value));
      unseen.forEach((token) => {
        enrichmentRequestedRef.current.add(token.value);
        enrichmentRecordsRef.current.set(token.value, { type: token.type, value: token.value, resolved: false, pending: true, providers: {} });
      });
      renderEnrichmentDecorations();
      if (!unseen.length) return;
      try {
        const response = await fetch("/api/terminal/enrich", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ objects: unseen.map(({ type, value }) => ({ type, value })) }),
        });
        const data = response.ok ? await response.json() : null;
        for (const result of data?.results || []) enrichmentRecordsRef.current.set(result.value, result);
        if (!response.ok) {
          unseen.forEach((token) => enrichmentRecordsRef.current.set(token.value, {
            type: token.type, value: token.value, resolved: false, providers: { "dns-ptr": { status: "unresolved" } },
          }));
        }
        renderEnrichmentDecorations();
      } catch {
        // Failed lookup requests must not affect terminal output or interaction.
        unseen.forEach((token) => enrichmentRecordsRef.current.set(token.value, {
          type: token.type, value: token.value, resolved: false, providers: { "dns-ptr": { status: "unresolved" } },
        }));
        renderEnrichmentDecorations();
      }
    }, 120);
  };

  useEffect(() => {
    const host = terminalHostRef.current;
    if (!host || terminalRef.current) return undefined;

    const terminal = new Terminal({
      allowProposedApi: true,
      cursorBlink: true,
      cursorStyle: "block",
      fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace',
      fontSize: 13,
      lineHeight: 1.12,
      scrollback: 10000,
      tabStopWidth: 8,
      theme: {
        background: "#090E14",
        foreground: "#D6DEEB",
        cursor: "#7FDBCA",
        cursorAccent: "#090E14",
        selectionBackground: "#2F6FB088",
        black: "#111827",
        red: "#EF6B73",
        green: "#7FDBA8",
        yellow: "#F5C06A",
        blue: "#6FA8F7",
        magenta: "#C792EA",
        cyan: "#7FDBCA",
        white: "#D6DEEB",
        brightBlack: "#64748B",
        brightWhite: "#FFFFFF",
      },
    });
    const fit = new FitAddon();
    terminal.loadAddon(fit);
    terminal.open(host);
    const mouseCoordinates = installTerminalMouseCoordinates(terminal);
    terminalRef.current = terminal;
    fitRef.current = fit;

    const fitNow = () => {
      if (!terminalHostRef.current?.clientWidth || !terminalHostRef.current?.clientHeight) return;
      try { fit.fit(); } catch {}
    };
    const frame = window.requestAnimationFrame(fitNow);
    const resizeObserver = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(() => window.requestAnimationFrame(fitNow))
      : null;
    resizeObserver?.observe(host);
    window.addEventListener("resize", fitNow);

    const inputDisposable = terminal.onData((data) => {
      sendSocket("terminal:input", { data });
    });
    const resizeDisposable = terminal.onResize(({ cols, rows }) => {
      sendSocket("terminal:resize", { cols, rows });
    });
    const notifyEnrichmentLayout = () => host.dispatchEvent(new Event('netclaw:terminal-layout'));
    const renderLayoutDisposable = terminal.onRender(notifyEnrichmentLayout);
    const scrollLayoutDisposable = terminal.onScroll(notifyEnrichmentLayout);
    const resizeLayoutDisposable = terminal.onResize(notifyEnrichmentLayout);
    const writeParsedDisposable = terminal.onWriteParsed(() => { notifyEnrichmentLayout(); enrichmentScanRef.current(); });

    terminal.attachCustomKeyEventHandler((event) => {
      if (!(event.ctrlKey || event.metaKey) || !event.shiftKey) return true;
      const key = event.key.toLowerCase();
      if (key === "c" && terminal.hasSelection()) {
        navigator.clipboard?.writeText(terminal.getSelection()).catch(() => {});
        return false;
      }
      if (key === "v") {
        navigator.clipboard?.readText()
          .then((text) => sendSocket("terminal:input", { data: text }))
          .catch(() => {});
        return false;
      }
      return true;
    });

    fitNow();
    if (transcriptRef.current) {
      terminal.write(transcriptRef.current, () => setBufferReady((value) => value + 1));
    } else {
      const intro = "\x1b[1;36mNetClaw Interactive Terminal\x1b[0m\r\nSelect a testbed device and choose Connect.\r\n";
      terminal.write(intro, () => setBufferReady((value) => value + 1));
      transcriptRef.current = intro;
      persistTranscriptSoon();
    }

    return () => {
      window.cancelAnimationFrame(frame);
      resizeObserver?.disconnect();
      window.removeEventListener("resize", fitNow);
      inputDisposable.dispose();
      resizeDisposable.dispose();
      writeParsedDisposable.dispose();
      renderLayoutDisposable.dispose();
      scrollLayoutDisposable.dispose();
      resizeLayoutDisposable.dispose();
      if (enrichmentScanTimerRef.current) window.clearTimeout(enrichmentScanTimerRef.current);
      clearEnrichmentDecorations();
      decorationsRef.current.forEach((decoration) => {
        try { decoration.dispose(); } catch {}
      });
      decorationsRef.current = [];
      if (transcriptTimerRef.current) {
        window.clearTimeout(transcriptTimerRef.current);
        transcriptTimerRef.current = null;
        onPatch({ terminalTranscript: transcriptRef.current });
      }
      cancelReadOnlyCapture();
      const socket = socketRef.current;
      if (socket) {
        socket.onclose = null;
        try { socket.close(); } catch {}
      }
      socketRef.current = null;
      mouseCoordinates.dispose();
      terminal.dispose();
      terminalRef.current = null;
      fitRef.current = null;
    };
  }, []);

  const highlightKey = JSON.stringify((highlights || []).map((highlight) => ({
    id: highlight.id,
    color: highlight.color,
    range: highlight.range,
  })));
  useEffect(() => {
    decorationsRef.current.forEach((entry) => {
      try { entry.dispose(); } catch {}
    });
    decorationsRef.current = [];

    const terminal = terminalRef.current;
    const buffer = terminal?.buffer?.normal;
    if (!terminal || !buffer) return undefined;
    const cursorLine = buffer.baseY + buffer.cursorY;

    for (const highlight of highlights || []) {
      const range = highlight.range;
      if (!range?.start || !range?.end) continue;
      const startY = Math.max(0, Number.parseInt(range.start.y, 10) || 0);
      let endY = Math.max(startY, Number.parseInt(range.end.y, 10) || 0);
      const startX = Math.max(0, Number.parseInt(range.start.x, 10) || 0);
      const endX = Math.max(0, Number.parseInt(range.end.x, 10) || 0);
      if (endY > startY && endX === 0) endY -= 1;

      for (let row = startY; row <= endY; row += 1) {
        const x = row === startY ? startX : 0;
        const end = row === endY && !(range.end.y > startY && endX === 0)
          ? endX
          : terminal.cols;
        const width = Math.min(terminal.cols - x, Math.max(1, end - x));
        if (width <= 0) continue;
        const marker = terminal.registerMarker(row - cursorLine);
        if (!marker) continue;
        let decoration;
        try {
          decoration = terminal.registerDecoration({
            marker,
            x,
            width,
            backgroundColor: /^#[0-9a-f]{6}$/i.test(highlight.color) ? highlight.color : "#B5651D",
            foregroundColor: "#FFFFFF",
            layer: "bottom",
            overviewRulerOptions: {
              color: /^#[0-9a-f]{6}$/i.test(highlight.color) ? highlight.color : "#B5651D",
              position: "full",
            },
          });
        } catch {
          decoration = null;
        }
        if (!decoration) {
          try { marker.dispose(); } catch {}
          continue;
        }
        decorationsRef.current.push({
          dispose() {
            try { decoration.dispose(); } catch {}
            try { marker.dispose(); } catch {}
          },
        });
      }
    }

    return () => {
      decorationsRef.current.forEach((entry) => {
        try { entry.dispose(); } catch {}
      });
      decorationsRef.current = [];
    };
  }, [highlightKey, bufferReady]);

  useEffect(() => {
    if (!enrichmentEnabled) {
      clearEnrichmentDecorations();
      enrichmentHover.close();
      return undefined;
    }
    enrichmentScanRef.current();
    return () => {};
  }, [enrichmentEnabled, bufferReady]);

  useEffect(() => {
    if (terminalView !== "terminal" || node.min) enrichmentHover.close();
  }, [terminalView, node.min, enrichmentHover.close]);

  useEffect(() => {
    if (node.min || terminalView !== "terminal") return;
    const frame = window.requestAnimationFrame(() => {
      try {
        fitRef.current?.fit();
        terminalRef.current?.focus();
      } catch {}
    });
    return () => window.cancelAnimationFrame(frame);
  }, [node.min, node.w, node.h, terminalView]);

  useEffect(() => {
    if (terminalView !== "structured" || structuredFormat !== "intent") return;
    const frame = window.requestAnimationFrame(() => {
      const log = intentLogRef.current;
      if (log) log.scrollTop = log.scrollHeight;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [terminalView, structuredFormat, intentHistory, intentBusy]);

  const disconnect = (message = "Disconnected.") => {
    manualCloseRef.current = true;
    sendSocket("terminal:disconnect");
    const socket = socketRef.current;
    if (socket) {
      socket.onclose = null;
      try { socket.close(); } catch {}
    }
    socketRef.current = null;
    setHostKey(null);
    setStatus("disconnected");
    setStatusMessage(message);
    persistTranscriptNow({ flushDecoder: true });
  };

  const connect = ({ legacySshCompatibility = legacyKexEnabled } = {}) => {
    const selectedDevice = devices.find((device) => device.id === deviceId);
    if (!selectedDevice?.supported) return;
    const useLegacyKex = legacySshCompatibility === true;
    const credentialsForAttempt = credentialOverrideRef.current
      ? { ...credentialOverrideRef.current }
      : null;

    const oldSocket = socketRef.current;
    if (oldSocket) {
      oldSocket.onclose = null;
      try { oldSocket.close(); } catch {}
    }

    const terminal = terminalRef.current;
    persistTranscriptNow({ flushDecoder: true });
    const connectionBanner = `\r\n\x1b[36m── Connecting to ${selectedDevice.alias || selectedDevice.name}${useLegacyKex ? " with Legacy KEX" : ""} ──\x1b[0m\r\n`;
    terminal?.write(connectionBanner);
    appendTranscript(connectionBanner);
    setHostKey(null);
    setLegacyKexEnabled(useLegacyKex);
    setLegacyKexRetryAvailable(false);
    onPatch({ terminalLegacySshCompatibility: useLegacyKex });
    setStatus("connecting");
    setStatusMessage(
      useLegacyKex
        ? `Connecting to ${selectedDevice.host}:${selectedDevice.port} with Legacy KEX compatibility...`
        : `Connecting to ${selectedDevice.host}:${selectedDevice.port}...`,
    );
    manualCloseRef.current = false;

    const socket = new WebSocket(terminalSocketUrl());
    socketRef.current = socket;
    socket.onopen = () => {
      let cols = terminal?.cols || 80;
      let rows = terminal?.rows || 24;
      try {
        fitRef.current?.fit();
        cols = terminal?.cols || cols;
        rows = terminal?.rows || rows;
      } catch {}
      socket.send(JSON.stringify({
        type: "terminal:connect",
        payload: {
          device: deviceId,
          cols,
          rows,
          legacySshCompatibility: useLegacyKex,
          ...(credentialsForAttempt ? { credentials: credentialsForAttempt } : {}),
        },
      }));
      if (credentialsForAttempt) {
        credentialsForAttempt.password = "";
        clearPendingCredentials();
      }
    };
    socket.onmessage = (event) => {
      let message;
      try { message = JSON.parse(event.data); } catch { return; }
      if (message.type === "terminal:data" && message.payload?.data) {
        try {
          const bytes = decodeTerminalBytes(message.payload.data);
          terminalRef.current?.write(bytes);
          const decoded = transcriptDecoderRef.current.decode(bytes, { stream: true });
          appendTranscript(decoded);
          captureReadOnlyTerminalData(decoded);
        } catch {}
        return;
      }
      if (message.type === "terminal:status") {
        const next = message.payload || {};
        setStatus(next.status || "idle");
        setStatusMessage(next.message || "");
        if (next.status === "host-key") setHostKey(next);
        if (next.status === "connected") {
          setHostKey(null);
          setLegacyKexEnabled(next.legacySshCompatibility === true);
          clearPendingCredentials();
          onPatch({ terminalLegacySshCompatibility: next.legacySshCompatibility === true });
          window.requestAnimationFrame(() => terminalRef.current?.focus());
        }
        if (next.status === "error") {
          setLegacyKexRetryAvailable(
            next.code === "KEX_MISMATCH" && next.legacyRetryAvailable === true,
          );
          if (next.code === "AUTH_FAILED" && next.credentialPromptAvailable === true) {
            clearPendingCredentials();
            setCredentialsOpen(true);
          }
          const errorLine = `\r\n\x1b[31m${next.message || "SSH session failed."}\x1b[0m\r\n`;
          terminalRef.current?.write(errorLine);
          appendTranscript(errorLine);
        }
      }
    };
    socket.onerror = () => {
      setStatus("error");
      setStatusMessage("The NetClaw terminal WebSocket could not be opened.");
    };
    socket.onclose = () => {
      socketRef.current = null;
      persistTranscriptNow({ flushDecoder: true });
      if (!manualCloseRef.current) {
        setStatus((current) => current === "error" ? current : "disconnected");
        setStatusMessage((current) => current || "Terminal WebSocket closed.");
      }
    };
  };

  const closeCredentials = () => {
    setCredentialsOpen(false);
    setCredentialsError("");
    setCredentialsForm((current) => ({ ...current, password: "" }));
  };

  const submitCredentials = (event) => {
    event.preventDefault();
    const username = credentialsForm.username.trim();
    const password = credentialsForm.password;
    if (!username || !password) {
      setCredentialsError("Username and password are required.");
      return;
    }
    if (username.length > 256 || /[\r\n\0]/.test(username)) {
      setCredentialsError("Username contains unsupported characters or is too long.");
      return;
    }
    if (password.length > 4096 || password.includes("\0")) {
      setCredentialsError("Password contains unsupported characters or is too long.");
      return;
    }

    credentialOverrideRef.current = { username, password };
    setCredentialsReady(true);
    setCredentialsError("");
    setCredentialsOpen(false);
    setCredentialsForm({ username, password: "" });
    connect();
  };

  const respondToHostKey = (accept) => {
    sendSocket("terminal:hostkey-response", { accept });
    if (!accept) {
      setHostKey(null);
      setStatus("error");
      setStatusMessage("SSH host key was not trusted.");
    }
  };

  const resetTrustedHostKey = async () => {
    const selectedDevice = devices.find((device) => device.id === deviceId);
    if (!selectedDevice?.supported || status === "connected" || busy) return;
    setHostKeyResetBusy(true);
    try {
      const response = await fetch(`/api/terminal/devices/${encodeURIComponent(deviceId)}/host-key`, {
        method: "DELETE",
        headers: { Accept: "application/json" },
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Unable to reset the saved SSH host key.");
      setHostKey(null);
      setStatusMessage(
        result.removed
          ? `Saved host key cleared for ${result.host}:${result.port}. Connect again and verify the new fingerprint.`
          : `No saved host key exists for ${result.host}:${result.port}. Connect to verify the device fingerprint.`,
      );
    } catch (error) {
      setStatus("error");
      setStatusMessage(error.message || "Unable to reset the saved SSH host key.");
    } finally {
      setHostKeyResetBusy(false);
    }
  };

  const copySelection = () => {
    const selection = terminalRef.current?.getSelection() || "";
    if (selection) navigator.clipboard?.writeText(selection).catch(() => {});
  };

  const pasteClipboard = () => {
    navigator.clipboard?.readText()
      .then((text) => sendSocket("terminal:input", { data: text }))
      .catch(() => {});
  };

  const clearTerminal = () => {
    const intro = "\x1b[1;36mNetClaw Interactive Terminal\x1b[0m\r\nTranscript cleared. Select output to branch into a chat.\r\n";
    decorationsRef.current.forEach((entry) => {
      try { entry.dispose(); } catch {}
    });
    decorationsRef.current = [];
    terminalRef.current?.reset();
    terminalRef.current?.write(intro, () => setBufferReady((value) => value + 1));
    transcriptDecoderRef.current = new TextDecoder();
    transcriptRef.current = intro;
    transcriptLimitReachedRef.current = false;
    setStructuredSelection(null);
    setTerminalView("terminal");
    onPatch({ terminalTranscript: intro, terminalHighlightRanges: {} });
  };

  const useTraditionalTerminalOnly = () => {
    setTerminalView("terminal");
    setIntentError("");
    setTraditionalTerminalOverlayOpen(true);
    setStatusMessage(
      status === "connected"
        ? "Traditional terminal mode active. Commands execute directly in the SSH session."
        : "Traditional terminal mode active. Connect to begin an SSH session.",
    );
    window.requestAnimationFrame(() => {
      try { fitRef.current?.fit(); } catch {}
      terminalRef.current?.focus();
    });
  };

  const closeTraditionalTerminalOverlay = () => {
    setTraditionalTerminalOverlayOpen(false);
    window.requestAnimationFrame(() => terminalRef.current?.focus());
  };

  const handleTerminalSelection = (event) => {
    const x = event.clientX;
    const y = event.clientY - 8;
    // xterm finalizes its selection in a document-level mouseup listener, after
    // React sees this event. Read it on the next frame so the exact range is ready.
    window.requestAnimationFrame(() => {
      const terminal = terminalRef.current;
      if (!terminal?.hasSelection()) return;
      const quote = terminal.getSelection().replace(/\s+$/, "");
      const range = terminal.getSelectionPosition();
      if (!quote.trim() || !range) return;
      const selection = {
        quote,
        sourceType: "selection",
        range: {
          start: { x: range.start.x, y: range.start.y },
          end: { x: range.end.x, y: range.end.y },
          cols: terminal.cols,
        },
        x,
        y,
      };
      setStructuredSelection(selection);
      onSelect(selection);
    });
  };

  const flashExport = (message) => {
    setExportMessage(message);
    window.setTimeout(() => setExportMessage(null), 2400);
  };

  const openExport = () => {
    if (exportOpen) {
      setExportOpen(false);
      return;
    }
    const rect = exportBtnRef.current?.getBoundingClientRect();
    if (rect) {
      setExportPos({
        top: rect.bottom + 4,
        right: Math.max(8, window.innerWidth - rect.right),
      });
    }
    setExportOpen(true);
  };

  const currentTranscript = () => terminalBufferText(terminalRef.current);
  const saveIntentHistory = (history) => {
    const normalized = normalizeTerminalIntentHistory(history);
    intentHistoryRef.current = normalized;
    setIntentHistory(normalized);
    onPatch({ terminalIntentHistory: normalized });
    return normalized;
  };
  useEffect(() => {
    if (!intentRun?.id || intentRun.status === 'submitting') return;
    let stopped = false, timer;
    const controller = new AbortController();
    const poll = async () => {
      try {
        const response = await fetch(`/api/terminal/intent/runs/${encodeURIComponent(intentRun.id)}`, { signal: controller.signal });
        if (!response.ok) throw await apiError(response);
        const run = await response.json();
        if (stopped) return;
        setIntentRun(run);
        onPatch({ terminalIntentRun: run });
        setIntentPhase(run.status === 'running' ? 'execution' : 'idle');
        if (run.status === 'running') { timer = window.setTimeout(poll, 1500); return; }
        const messageId = `execution-${run.id}`;
        if (!intentHistoryRef.current.some(m => m.id === messageId)) {
          saveIntentHistory([...intentHistoryRef.current, { id: messageId, role: 'assistant',
            content: `NetClaw execution: ${run.status}\n\n${executionResultText(run)}` }]);
        }
      } catch (error) {
        if (stopped) return;
        const run = { ...intentRun, status: 'uncertain', report: {
          summary: `${error.message || 'Cannot read execution status.'} No request was replayed. The agent may still be working; verify live state before retrying.`,
        } };
        setIntentRun(run);
        onPatch({ terminalIntentRun: run });
        setIntentPhase('idle');
      }
    };
    void poll();
    return () => { stopped = true; controller.abort(); window.clearTimeout(timer); };
  }, [intentRun?.id, intentRun?.status === 'submitting']);

  const executeTerminalIntent = async (requestText) => {
    if (intentChangeControl.mode === 'local-lab' && (!intentChangeControl.policyRevision || !intentChangeControl.targetDeviceIds.length)) {
      setIntentError('In Change control, authorize your lab devices and select the devices for this request first.');
      return;
    }
    const id = randomId();
    const previousMode = intentRun?.changeControl?.mode || 'production';
    const sameChangeScope = previousMode === intentChangeControl.mode && (previousMode !== 'local-lab' ||
      (intentRun?.changeControl?.revision === intentChangeControl.policyRevision &&
       JSON.stringify(intentRun.changeControl.devices.map(d => d.id).sort()) === JSON.stringify([...intentChangeControl.targetDeviceIds].sort())));
    const continueFrom = sameChangeScope && ['needs_input', 'blocked', 'incomplete', 'uncertain'].includes(intentRun?.status) ? intentRun.id : undefined;
    const history = intentHistoryRef.current;
    saveIntentHistory([...history, { id: `intent-user-${id}`, role: 'user', content: requestText }]);
    setIntentPrompt('');
    setIntentError('');
    setIntentPhase('execution');
    const pending = { id, status: 'submitting', startedAt: new Date().toISOString(), steps: [] };
    setIntentRun(pending);
    onPatch({ terminalIntentRun: pending });
    let response;
    try {
      const hudSession=await fetch('/api/hud/session',{method:'POST'});
      if(!hudSession.ok)throw Error('Private HUD session unavailable.');
      response = await fetch('/api/terminal/intent/runs', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, request: requestText, deviceId, transcript: intentTerminalContext(), history, continueFrom,
          changeMode: intentChangeControl.mode, targetDeviceIds: intentChangeControl.targetDeviceIds, policyRevision: intentChangeControl.policyRevision }),
      });
      if (!response.ok) throw await apiError(response);
      const run = await response.json();
      setIntentRun(run);
      onPatch({ terminalIntentRun: run });
    } catch (error) {
      if (response && !response.ok) {
        setIntentRun(null);
        onPatch({ terminalIntentRun: null });
        setIntentError(response.status === 404
          ? 'Restart the NetClaw API to enable Intent execution. This request was not submitted.'
          : error.message);
      } else {
        // An ambiguous POST is checked by ID, never retried automatically.
        const unknown = { ...pending, status: 'uncertain' };
        setIntentRun(unknown);
        onPatch({ terminalIntentRun: unknown });
      }
      setIntentPhase('idle');
    }
  };
  const intentTerminalContext = () => {
    const terminal = terminalRef.current;
    if (terminal?.hasSelection()) return terminal.getSelection().replace(/\s+$/, "");
    return String(structuredSelection?.quote || currentTranscript() || "").replace(/\s+$/, "");
  };
  const cancelReadOnlyCapture = () => {
    if (readOnlyCaptureTimerRef.current) {
      window.clearTimeout(readOnlyCaptureTimerRef.current);
      readOnlyCaptureTimerRef.current = null;
    }
    readOnlyCaptureRef.current = null;
    readOnlyCaptureSequenceRef.current += 1;
    setIntentPhase('idle');
  };
  const finishReadOnlyCapture = async (sequence) => {
    const capture = readOnlyCaptureRef.current;
    if (!capture || capture.sequence !== sequence) return;
    if (readOnlyCaptureTimerRef.current) {
      window.clearTimeout(readOnlyCaptureTimerRef.current);
      readOnlyCaptureTimerRef.current = null;
    }
    readOnlyCaptureRef.current = null;
    const output = normalizeTerminalCommandOutput(capture.output);
    if (!output) {
      setIntentError("The read-only command was sent, but no terminal output was captured.");
      setIntentPhase('idle');
      return;
    }

    setIntentPhase('summary');
    setIntentError("");
    try {
      const selected = devices.find((candidate) => candidate.id === deviceId) || {};
      const commandText = capture.commands.join("; ");
      const modelCall = terminalAssistantMode === "terra" ? callTerraTerminal : callLLM;
      const raw = await modelCall(buildTerminalIntentMessages({
        request: `The read-only CLI command "${commandText}" has completed. Explain the captured terminal output as structured English intent. State what the device reported, call out important findings, and do not propose another command.`,
        transcript: output,
        device: {
          ...selected,
          id: deviceId || selected.id || "",
          connectionStatus: status,
        },
        history: intentHistoryRef.current,
        explainOnly: true,
      }));
      if (sequence !== readOnlyCaptureSequenceRef.current) return;
      const parsed = parseTerminalIntentResponse(raw);
      const result = { ...parsed, commands: [], risk: "read-only" };
      saveIntentHistory([
        ...intentHistoryRef.current,
        {
          id: `intent-result-${Date.now().toString(36)}`,
          role: "assistant",
          content: result.explanation,
          proposal: result,
          executedCommands: capture.commands,
          terminalOutput: output,
        },
      ]);
    } catch (error) {
      if (sequence === readOnlyCaptureSequenceRef.current) {
        setIntentError(error.message || "The selected terminal assistant could not explain the captured command output.");
      }
    } finally {
      if (sequence === readOnlyCaptureSequenceRef.current) setIntentPhase('idle');
    }
  };
  const scheduleReadOnlyCaptureFinish = (delay = 900) => {
    const capture = readOnlyCaptureRef.current;
    if (!capture) return;
    if (readOnlyCaptureTimerRef.current) window.clearTimeout(readOnlyCaptureTimerRef.current);
    readOnlyCaptureTimerRef.current = window.setTimeout(
      () => finishReadOnlyCapture(capture.sequence),
      delay,
    );
  };
  const beginReadOnlyCapture = (commands) => {
    cancelReadOnlyCapture();
    setIntentPhase('capture');
    const sequence = readOnlyCaptureSequenceRef.current;
    readOnlyCaptureRef.current = {
      sequence,
      commands: [...commands],
      output: "",
    };
    scheduleReadOnlyCaptureFinish(1600);
    return sequence;
  };
  const captureReadOnlyTerminalData = (text) => {
    const capture = readOnlyCaptureRef.current;
    if (!capture || !text) return;
    capture.output = `${capture.output}${text}`.slice(-60_000);
    const normalized = normalizeTerminalCommandOutput(capture.output);
    const promptReturned = /(?:^|\n)[^\n]{1,120}[#>$]\s*$/.test(normalized);
    scheduleReadOnlyCaptureFinish(promptReturned ? 300 : 900);
  };
  const openIntentPane = () => {
    setStructuredOutputFormat("intent");
    setTerminalView("structured");
    setIntentError("");
  };
  const submitTerraConfig = async (event) => {
    event.preventDefault();
    if (!terraApiKey.trim()) return;
    setTerraConfigBusy(true);
    setTerraConfigError("");
    try {
      const response = await fetch("/api/terminal/terra/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apiKey: terraApiKey.trim() }),
      });
      if (!response.ok) throw await apiError(response);
      const configured = await refreshTerraStatus();
      if (!configured) throw new Error("Instant Assist could not confirm the saved API key.");
      setTerminalAssistantMode("terra");
      onPatch({ terminalAssistantMode: "terra" });
      setTerraApiKey("");
      setTerraConfigOpen(false);
      openIntentPane();
    } catch (error) {
      setTerraConfigError(error.message || "Instant Assist could not save the API key.");
    } finally {
      setTerraConfigBusy(false);
    }
  };
  const requestTerminalIntent = async ({ request, explainOnly = false } = {}) => {
    if (intentBusy) return;
    const requestText = String(request || "").trim()
      || (explainOnly ? "Explain the visible terminal output in plain English." : "");
    if (!requestText) return;
    if (!explainOnly) return executeTerminalIntent(requestText);
    setIntentRun(null);
    onPatch({ terminalIntentRun: null });

    const userMessage = {
      id: `intent-user-${Date.now().toString(36)}`,
      role: "user",
      content: requestText,
    };
    const baseHistory = saveIntentHistory([...intentHistory, userMessage]);
    setIntentPrompt("");
    setIntentPhase('request');
    setIntentError("");
    setApprovedIntentId(null);
    try {
      const selected = devices.find((candidate) => candidate.id === deviceId) || {};
      const modelCall = terminalAssistantMode === "terra" ? callTerraTerminal : callLLM;
      const raw = await modelCall(buildTerminalIntentMessages({
        request: requestText,
        transcript: intentTerminalContext(),
        device: {
          ...selected,
          id: deviceId || selected.id || "",
          connectionStatus: status,
        },
        history: intentHistory,
        explainOnly,
      }));
      const parsedProposal = parseTerminalIntentResponse(raw);
      const proposal = explainOnly ? { ...parsedProposal, commands: [], risk: 'read-only' } : parsedProposal;
      let execution = null;
      if (!explainOnly && proposal.risk === "read-only" && proposal.commands.length > 0) {
        if (shouldAutoRunTerminalIntent(proposal, { connectionStatus: status })) {
          const input = terminalCommandsToInput(proposal.commands);
          beginReadOnlyCapture(proposal.commands);
          const sent = sendSocket("terminal:input", { data: input });
          if (!sent) cancelReadOnlyCapture();
          execution = sent
            ? {
              status: "sent",
              message: `${proposal.commands.length} verified read-only command${proposal.commands.length === 1 ? "" : "s"} sent automatically. Capturing terminal output...`,
            }
            : {
              status: "not-connected",
              message: "The read-only command was not sent because the terminal connection is unavailable.",
            };
        } else {
          execution = {
            status: "not-connected",
            message: "Connect to the device to run this verified read-only request automatically.",
          };
        }
      }
      saveIntentHistory([
        ...baseHistory,
        {
          id: `intent-assistant-${Date.now().toString(36)}`,
          role: "assistant",
          content: proposal.explanation,
          proposal,
          ...(execution ? { execution } : {}),
        },
      ]);
    } catch (error) {
      setIntentError(error.message || "NetClaw could not interpret this terminal request.");
    } finally {
      // Keep the workflow busy while output capture/explanation continues.
      setIntentPhase(phase => phase === 'request' ? 'idle' : phase);
    }
  };
  const submitTerminalIntent = (event) => {
    event.preventDefault();
    requestTerminalIntent({ request: intentPrompt });
  };
  const copyIntentCommands = async (proposal) => {
    try {
      await navigator.clipboard.writeText((proposal?.commands || []).join("\n"));
      flashExport("Proposed CLI copied");
    } catch {
      flashExport("Copy blocked by browser");
    }
  };
  const sendIntentCommands = (message) => {
    if (!message?.proposal?.commands?.length || approvedIntentId !== message.id) {
      setIntentError("Review and approve the exact CLI before sending it.");
      return;
    }
    if (status !== "connected") {
      setIntentError("Connect to the selected device before sending reviewed commands.");
      return;
    }
    try {
      const input = terminalCommandsToInput(message.proposal.commands);
      if (!sendSocket("terminal:input", { data: input })) {
        throw new Error("The terminal connection is not available.");
      }
      saveIntentHistory(intentHistoryRef.current.map(item => item.id === message.id ? {
        ...item, execution: { status: 'reviewed-sent', message: 'Sent after your review. Verify application in Terminal; success is not yet confirmed.' },
      } : item));
      setApprovedIntentId(null);
      setIntentError("");
      setTerminalView("terminal");
      flashExport(`${message.proposal.commands.length} reviewed command${message.proposal.commands.length === 1 ? "" : "s"} sent`);
    } catch (error) {
      setIntentError(error.message || "Unable to send the reviewed CLI.");
    }
  };
  const clearIntentHistory = () => {
    saveIntentHistory([]);
    setIntentRun(null);
    onPatch({ terminalIntentRun: null });
    setApprovedIntentId(null);
    setIntentError("");
  };
  const setStructuredOutputFormat = (format) => {
    const next = format === "intent" ? "intent" : artifactFormat(format).id;
    setStructuredFormat(next);
    onPatch({ terminalStructuredFormat: next });
  };
  const openStructuredOutput = () => {
    const terminal = terminalRef.current;
    if (terminal?.hasSelection()) {
      const range = terminal.getSelectionPosition();
      if (range) {
        setStructuredSelection({
          quote: terminal.getSelection().replace(/\s+$/, ""),
          sourceType: "selection",
          range: {
            start: { x: range.start.x, y: range.start.y },
            end: { x: range.end.x, y: range.end.y },
            cols: terminal.cols,
          },
        });
      }
    } else {
      const transcript = currentTranscript();
      if (transcript) setStructuredSelection({ quote: transcript, sourceType: "transcript", range: null });
    }
    setTerminalView("structured");
  };
  const createStructuredResult = () => {
    if (structuredFormat === "json") {
      if (!geniePreview || geniePreview.source !== structuredSource || geniePreview.deviceId !== deviceId) {
        flashExport("Parse this output with Genie first");
        return;
      }
      const created = onCreateResult({ source: geniePreview.parsedSource, format: "json",
        device: selectedDevice?.alias || selectedDevice?.name || deviceId || "terminal",
        parsedArtifact: geniePreview.artifact, terminalRange: structuredSelection?.range || null });
      if (created !== null) flashExport("Genie JSON Result created");
      return;
    }
    const terminal = terminalRef.current;
    let selection = structuredSelection;
    if (terminal?.hasSelection()) {
      const range = terminal.getSelectionPosition();
      selection = {
        quote: terminal.getSelection().replace(/\s+$/, ""),
        sourceType: "selection",
        range: range ? {
          start: { x: range.start.x, y: range.start.y },
          end: { x: range.end.x, y: range.end.y },
          cols: terminal.cols,
        } : null,
      };
      setStructuredSelection(selection);
    }
    const source = String(selection?.quote || currentTranscript() || "").replace(/\s+$/, "");
    if (!source.trim()) {
      flashExport("No terminal output to convert");
      return;
    }
    const device = devices.find((candidate) => candidate.id === deviceId);
    if (structuredFormat === "intent") {
      if (!intentResultText.trim()) {
        flashExport("Generate an English intent explanation first");
        return;
      }
      const deviceLabel = device?.alias || device?.name || deviceId || "terminal";
      const created = onCreateResult({
        source: intentResultText,
        format: "raw",
        device: deviceLabel,
        name: `${deviceLabel}-intent`,
        terminalRange: selection?.range || null,
      });
      if (created !== null) flashExport("English intent Result created");
      return;
    }
    const candidate = buildTerminalArtifact({
      source,
      format: structuredFormat,
      device: device?.alias || device?.name || deviceId || "terminal",
    });
    if (candidate.validation.status !== "valid") {
      flashExport(`Result blocked: ${candidate.validation.message || "format validation failed"}`);
      return;
    }
    const created = onCreateResult({
      source,
      format: structuredFormat,
      device: device?.alias || device?.name || deviceId || "terminal",
      terminalRange: selection?.range || null,
    });
    if (created !== null) {
      setTerminalView("structured");
      flashExport(`${artifactFormat(structuredFormat).label} Result created`);
    }
  };
  const openConfigReview = () => {
    const terminal = terminalRef.current;
    const selectedText = terminal?.hasSelection() ? terminal.getSelection() : "";
    const source = (selectedText || currentTranscript()).replace(/\r\n?/g, "\n");
    if (!source.trim()) {
      flashExport("No terminal output to review");
      return;
    }
    onOpenConfigReview({
      source,
      sourceName: `${deviceId || "terminal"}-running-config.txt`,
      device: selectedDevice?.alias || selectedDevice?.name || deviceId || "terminal",
    });
  };
  const copyTranscript = async () => {
    setExportOpen(false);
    const text = currentTranscript();
    if (!text) {
      flashExport("No terminal output to copy");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      flashExport("Terminal transcript copied");
    } catch {
      flashExport("Copy blocked by browser");
    }
  };
  const downloadTranscript = () => {
    setExportOpen(false);
    const text = currentTranscript();
    const ok = text && downloadTextFile(`${branchFileName(node)}.txt`, "text/plain;charset=utf-8", text);
    flashExport(ok ? "Terminal transcript downloaded" : "Download blocked by browser");
  };
  const downloadTranscriptHtml = () => {
    setExportOpen(false);
    const text = currentTranscript();
    const ok = text && downloadTextFile(`${branchFileName(node)}.html`, "text/html;charset=utf-8", terminalTranscriptHtml(node, text));
    flashExport(ok ? "HTML transcript downloaded" : "Download blocked by browser");
  };

  useEffect(() => {
    if (!exportOpen) return undefined;
    const onDown = (event) => {
      if (exportBtnRef.current?.contains(event.target)) return;
      if (event.target.closest?.("[data-terminal-export-menu]")) return;
      setExportOpen(false);
    };
    const onKey = (event) => {
      if (event.key === "Escape") setExportOpen(false);
    };
    document.addEventListener("mousedown", onDown, true);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown, true);
      document.removeEventListener("keydown", onKey);
    };
  }, [exportOpen]);

  const statusColor = status === "connected"
    ? "#22C55E"
    : status === "error"
      ? "#EF4444"
      : ["connecting", "opening", "host-key"].includes(status)
        ? "#F59E0B"
        : "#64748B";
  const busy = ["connecting", "opening", "host-key"].includes(status);
  const selectedDevice = devices.find((device) => device.id === deviceId);
  const terminalMenuSummaryStyle = {
    height: 30, display: "inline-flex", alignItems: "center", border: "1px solid transparent",
    borderRadius: 5, background: "transparent", color: "var(--nt-text)", padding: "0 8px", fontSize: 11.5,
    fontWeight: 500, cursor: "pointer", listStyle: "none", userSelect: "none",
  };
  const terminalMenuPopupStyle = {
    position: "absolute", top: 35, left: 0, zIndex: 12, minWidth: 220, padding: 5,
    display: "grid", gap: 2, background: "var(--nt-menu)", border: "1px solid var(--nt-line)",
    borderRadius: 8, boxShadow: "0 12px 28px rgba(0,0,0,0.24)",
  };
  const closeTerminalMenuAfterAction = (event) => {
    if (event.target.closest("button")) event.currentTarget.removeAttribute("open");
  };
  const closeTerminalMenuAfterChoice = (event) => {
    if (event.target.closest("select")) event.currentTarget.removeAttribute("open");
  };
  const structuredSource = String(structuredSelection?.quote || "");
  const structuredDeviceLabel = selectedDevice?.alias || selectedDevice?.name || deviceId || "terminal";
  // Avoid re-parsing and validating an unchanged capture on every intent
  // keystroke, menu toggle, socket-status update, or canvas drag.
  const structuredPreview = useMemo(() => structuredFormat === "json"
    ? (geniePreview?.source === structuredSource && geniePreview?.deviceId === deviceId ? geniePreview.artifact : null)
    : structuredSource && structuredFormat !== "intent"
    ? buildTerminalArtifact({
      source: structuredSource,
      format: structuredFormat,
      device: structuredDeviceLabel,
    })
    : null, [structuredFormat, structuredSource, structuredDeviceLabel, deviceId, geniePreview]);
  const latestIntentAnswer = [...intentHistory].reverse().find((message) => message.role === "assistant");
  const intentResultText = latestIntentAnswer
    ? [
      latestIntentAnswer.proposal?.intent,
      latestIntentAnswer.content,
      latestIntentAnswer.proposal?.assumptions?.length
        ? `Assumptions: ${latestIntentAnswer.proposal.assumptions.join("; ")}`
        : "",
    ].filter(Boolean).join("\n\n")
    : "";
  const structuredResultReady = structuredFormat === "intent"
    ? Boolean(intentResultText.trim())
    : structuredPreview?.validation.status === "valid";

  return (
    <div ref={laneRef} data-node-kind="terminal" data-node-id={node.id} data-theme={dark ? "dark" : "light"} onMouseDown={onFocus} className="lane-in nc-terminal"
      style={{ position: "absolute", left: node.x, top: node.y, width: node.w, height: node.min ? COLLAPSED_H : node.h, zIndex: node.z,
        transition: animate ? "left .35s cubic-bezier(.22,1,.36,1), top .35s cubic-bezier(.22,1,.36,1), width .3s cubic-bezier(.22,1,.36,1)" : "none",
        display: "flex", flexDirection: "column", borderRadius: 10, background: "var(--nt-surface)",
        borderTop: `1px solid ${isActive ? color : C.hairline}`,
        borderRight: `1px solid ${isActive ? color : C.hairline}`,
        borderBottom: `1px solid ${isActive ? color : C.hairline}`,
        borderLeft: `2px solid ${color}`,
        boxShadow: isActive ? `0 0 0 1px var(--ring), 0 8px 24px var(--shadow)` : `0 4px 14px var(--shadow)`,
        overflow: "hidden", ...(selected && !isActive ? { outline: `2px solid ${color}`, outlineOffset: 1 } : {}) }}>

      <div className="nt-titlebar" onMouseDown={onDragStart} onDoubleClick={(event) => { event.stopPropagation(); onToggleMin(); }}
        title={node.min ? "double-click to expand" : "double-click to collapse"}
        style={{ padding: "8px 12px", borderBottom: node.min ? "none" : `1px solid ${C.hairline}`, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, cursor: "grab", userSelect: "none", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <svg className="nt-terminal-icon" aria-hidden="true" width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="2" y="3" width="16" height="14" rx="3"/><path d="m6 7 3 3-3 3m5 0h3"/></svg>
          <span className="nt-window-title">{terminalView === "demo" ? "Terminal demo" : "SSH terminal"}</span>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: terminalView === "demo" ? "#F5C06A" : statusColor, boxShadow: terminalView !== "demo" && status === "connected" ? `0 0 0 3px ${statusColor}22` : "none" }} />
          <span className="nt-session-name">{terminalView === "demo" ? "Fake data" : (selectedDevice?.alias || deviceId || "testbed session")}</span>
          <span className="nt-connection-badge" data-status={status}>{terminalView === "demo" ? "Demo" : status === "connected" ? "Connected" : busy ? "Connecting" : status === "error" ? "Connection error" : "Not connected"}</span>
        </div>
        <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
          <button ref={exportBtnRef} onMouseDown={(event) => event.stopPropagation()} onClick={openExport} title="export this terminal transcript"
            style={{ display: terminalView === "demo" ? "none" : "block", width: 20, height: 20, border: "none", background: exportOpen ? C.userBubble : "transparent", color: C.muted, cursor: "pointer", fontSize: 13, lineHeight: 1, borderRadius: 4 }}>⇪</button>
          <button onMouseDown={(event) => event.stopPropagation()} onClick={onToggleMin} title={node.min ? "expand" : "minimize"}
            style={{ width: 20, height: 20, border: "none", background: "transparent", color: C.muted, cursor: "pointer", fontSize: 14, lineHeight: 1, borderRadius: 4 }}>{node.min ? "▣" : "–"}</button>
          <button onMouseDown={(event) => event.stopPropagation()} onClick={onDelete} title="close this terminal; stays in the sidebar"
            style={{ width: 20, height: 20, border: "none", background: "transparent", color: "#A8324E", cursor: "pointer", fontSize: 15, lineHeight: 1, borderRadius: 4 }}>×</button>
        </div>
      </div>

      {exportOpen && exportPos && createPortal(
        <div data-terminal-export-menu onMouseDown={(event) => event.stopPropagation()}
          style={{ position: "fixed", top: exportPos.top, right: exportPos.right, zIndex: 600, minWidth: 232, background: C.card, border: `1px solid ${C.hairline}`, borderRadius: 9, boxShadow: "0 12px 32px rgba(0,0,0,0.28)", padding: "5px 0", ...(dark ? DARK : LIGHT) }}>
          <div style={{ padding: "4px 13px 5px", fontFamily: "ui-monospace, Menlo, monospace", fontSize: 9, letterSpacing: 0.7, textTransform: "uppercase", color: C.muted }}>Export terminal transcript</div>
          {[["📋", "Copy transcript", "plain text", copyTranscript],
            ["⤓", "Text (.txt)", "terminal log", downloadTranscript],
            ["⤓", "HTML (.html)", "formatted standalone transcript", downloadTranscriptHtml]].map(([icon, label, detail, action], index) => (
            <button key={index} onClick={action}
              onMouseEnter={(event) => (event.currentTarget.style.background = C.userBubble)}
              onMouseLeave={(event) => (event.currentTarget.style.background = "transparent")}
              style={{ display: "flex", alignItems: "flex-start", gap: 9, width: "100%", textAlign: "left", border: "none", background: "transparent", color: C.ink, cursor: "pointer", padding: "7px 13px" }}>
              <span style={{ fontSize: 13, lineHeight: "16px", flexShrink: 0 }}>{icon}</span>
              <span>
                <span style={{ display: "block", fontSize: 12.5, fontWeight: 500 }}>{label}</span>
                <span style={{ display: "block", fontSize: 10, color: C.muted, marginTop: 1 }}>{detail}</span>
              </span>
            </button>
          ))}
        </div>,
        document.body,
      )}
      {exportMessage && createPortal(
        <div style={{ position: "fixed", bottom: 22, left: "50%", transform: "translateX(-50%)", zIndex: 620, background: C.trunk, color: "#fff", fontSize: 12, padding: "8px 14px", borderRadius: 8, boxShadow: "0 8px 22px rgba(0,0,0,0.32)", ...(dark ? DARK : LIGHT) }}>{exportMessage}</div>,
        document.body,
      )}
      {terraConfigOpen && createPortal(
        <div onMouseDown={(event) => {
          if (event.target === event.currentTarget && !terraConfigBusy) setTerraConfigOpen(false);
        }}
          style={{ position: "fixed", inset: 0, zIndex: 660, display: "grid", placeItems: "center", background: "rgba(3,7,12,0.68)", padding: 20, ...(dark ? DARK : LIGHT) }}>
          <form onSubmit={submitTerraConfig} onMouseDown={(event) => event.stopPropagation()}
            role="dialog" aria-modal="true" aria-labelledby={`terra-config-title-${node.id}`}
            style={{ width: "min(460px, 96vw)", background: C.card, color: C.ink, border: `1px solid #C792EA88`, borderRadius: 12, boxShadow: "0 22px 60px rgba(0,0,0,0.42)", padding: 18 }}>
            <div id={`terra-config-title-${node.id}`} style={{ color: "#9C6BCE", fontSize: 16, fontWeight: 800, marginBottom: 5 }}>Set up Instant Assist</div>
            <div style={{ fontSize: 11.5, color: C.muted, lineHeight: 1.55, marginBottom: 14 }}>
              Paste an OpenAI API key to enable <strong style={{ color: C.ink }}>chat-latest</strong>, the current Instant-model alias, for AI Intent. It is stored only in your local OpenClaw configuration, is never rendered again, and is never included in terminal transcripts or model context.
            </div>
            <label style={{ display: "grid", gap: 5, fontSize: 11.5, fontWeight: 700 }}>
              OpenAI API key
              <input autoFocus required type="password" autoComplete="off" value={terraApiKey}
                onChange={(event) => setTerraApiKey(event.target.value)} maxLength={512}
                placeholder="sk-..."
                style={{ height: 36, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5, fontFamily: "ui-monospace, Menlo, monospace" }} />
            </label>
            {terraConfigError && (
              <div role="alert" style={{ marginTop: 12, padding: "8px 10px", borderRadius: 7, background: "#A8324E18", border: "1px solid #A8324E55", color: "#A8324E", fontSize: 11.5, lineHeight: 1.4 }}>
                {terraConfigError}
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
              <button type="button" disabled={terraConfigBusy} onClick={() => setTerraConfigOpen(false)}
                style={{ height: 32, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.card, color: C.ink, padding: "0 12px", fontSize: 11.5, cursor: "pointer" }}>Cancel</button>
              <button type="submit" disabled={terraConfigBusy || !terraApiKey.trim()}
                style={{ height: 32, border: "none", borderRadius: 7, background: "#6D4AA1", color: "#fff", padding: "0 14px", fontSize: 11.5, fontWeight: 750, cursor: terraConfigBusy || !terraApiKey.trim() ? "default" : "pointer", opacity: terraConfigBusy || !terraApiKey.trim() ? 0.55 : 1 }}>
                {terraConfigBusy ? "Saving..." : "Save and use Terra"}
              </button>
            </div>
          </form>
        </div>,
        document.body,
      )}
      {credentialsOpen && createPortal(
        <div onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeCredentials();
        }}
          style={{ position: "fixed", inset: 0, zIndex: 660, display: "grid", placeItems: "center", background: "rgba(3,7,12,0.68)", padding: 20, ...(dark ? DARK : LIGHT) }}>
          <form onSubmit={submitCredentials} onMouseDown={(event) => event.stopPropagation()}
            role="dialog" aria-modal="true" aria-labelledby={`ssh-credentials-title-${node.id}`}
            style={{ width: "min(420px, 96vw)", background: C.card, color: C.ink, border: `1px solid ${C.hairline}`, borderRadius: 12, boxShadow: "0 22px 60px rgba(0,0,0,0.42)", padding: 18 }}>
            <div id={`ssh-credentials-title-${node.id}`} style={{ fontSize: 16, fontWeight: 800, marginBottom: 5 }}>SSH credentials</div>
            <div style={{ fontSize: 11.5, color: C.muted, lineHeight: 1.5, marginBottom: 14 }}>
              Use a username and password for one connection to <strong style={{ color: C.ink }}>{selectedDevice?.alias || selectedDevice?.name || deviceId}</strong>. They stay in local browser memory only until this attempt starts and are not saved to the testbed, transcript, Canvas, logs, chat, or model context.
            </div>

            <div style={{ display: "grid", gap: 10 }}>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650 }}>
                Username *
                <input autoFocus required autoComplete="off" value={credentialsForm.username}
                  onChange={(event) => setCredentialsForm((current) => ({ ...current, username: event.target.value }))}
                  maxLength={256}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5, fontFamily: "ui-monospace, Menlo, monospace" }} />
              </label>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650 }}>
                Password *
                <input required type="password" autoComplete="off" value={credentialsForm.password}
                  onChange={(event) => setCredentialsForm((current) => ({ ...current, password: event.target.value }))}
                  maxLength={4096}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5, fontFamily: "ui-monospace, Menlo, monospace" }} />
              </label>
            </div>

            {credentialsError && (
              <div role="alert" style={{ marginTop: 12, padding: "8px 10px", borderRadius: 7, background: "#A8324E18", border: "1px solid #A8324E55", color: "#A8324E", fontSize: 11.5, lineHeight: 1.4 }}>
                {credentialsError}
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
              <button type="button" onClick={closeCredentials}
                style={{ height: 32, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.card, color: C.ink, padding: "0 12px", fontSize: 11.5, cursor: "pointer" }}>Cancel</button>
              <button type="submit"
                style={{ height: 32, border: "none", borderRadius: 7, background: color, color: "#fff", padding: "0 14px", fontSize: 11.5, fontWeight: 750, cursor: "pointer" }}>
                Use and connect
              </button>
            </div>
          </form>
        </div>,
        document.body,
      )}
      {addDeviceOpen && createPortal(
        <div onMouseDown={(event) => {
          if (event.target === event.currentTarget && !addDeviceBusy) setAddDeviceOpen(false);
        }}
          style={{ position: "fixed", inset: 0, zIndex: 650, display: "grid", placeItems: "center", background: "rgba(3,7,12,0.68)", padding: 20, ...(dark ? DARK : LIGHT) }}>
          <form onSubmit={submitAddDevice} onMouseDown={(event) => event.stopPropagation()}
            role="dialog" aria-modal="true" aria-labelledby={`add-device-title-${node.id}`}
            style={{ width: "min(520px, 96vw)", maxHeight: "90vh", overflow: "auto", background: C.card, color: C.ink, border: `1px solid ${C.hairline}`, borderRadius: 12, boxShadow: "0 22px 60px rgba(0,0,0,0.42)", padding: 18 }}>
            <div id={`add-device-title-${node.id}`} style={{ fontSize: 16, fontWeight: 800, marginBottom: 5 }}>{deviceEditMode === "add" ? "Add SSH device" : deviceEditMode === "edit" ? "Edit SSH device" : "Remove testbed device?"}</div>
            <div style={{ fontSize: 11.5, color: C.muted, lineHeight: 1.5, marginBottom: 14 }}>
              {deviceEditMode === "add" ? <>
              This appends a profile to the existing <code>devices:</code> mapping in <code>testbed.yaml</code>. It preserves existing entries and uses the testbed&apos;s current default credentials. Adding a profile does not connect to the device.
              </> : deviceEditMode === "edit" ? <>
                Updates this profile only. Credentials, custom fields and other connections are preserved. The device ID stays unchanged; edit its display name below. Collection for this device will stop until you log in and authorize it again. A local backup is saved before writing.
              </> : <>
                Remove <strong>{addDeviceForm.alias || addDeviceForm.id}</strong> (<code>{addDeviceForm.id}</code>) at <code>{addDeviceForm.host}:{addDeviceForm.port}</code> from the testbed? This stops its background collection and clears its collector login. Other devices are unchanged. It does not delete or configure the actual device. A local inventory backup will be saved for recovery.
              </>}
            </div>

            {deviceEditMode !== "remove" && <fieldset disabled={addDeviceBusy} style={{ border: 0, padding: 0, margin: 0, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 12px" }}>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650 }}>
                Device ID *
                <input autoFocus required readOnly={deviceEditMode === "edit"} value={addDeviceForm.id} onChange={(event) => setAddDeviceField("id", event.target.value)}
                  placeholder="CORE-RTR-01" pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,63}" maxLength={64}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5, fontFamily: "ui-monospace, Menlo, monospace" }} />
              </label>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650 }}>
                Display name
                <input value={addDeviceForm.alias} onChange={(event) => setAddDeviceField("alias", event.target.value)}
                  placeholder="Core router 01" maxLength={80}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5 }} />
              </label>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650 }}>
                Host or IP *
                <input required value={addDeviceForm.host} onChange={(event) => setAddDeviceField("host", event.target.value)}
                  placeholder="192.0.2.10" maxLength={253}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5, fontFamily: "ui-monospace, Menlo, monospace" }} />
              </label>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650 }}>
                SSH port *
                <input required type="number" min="1" max="65535" value={addDeviceForm.port} onChange={(event) => setAddDeviceField("port", event.target.value)}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5 }} />
              </label>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650 }}>
                Device type
                <select value={addDeviceForm.type} onChange={(event) => setAddDeviceField("type", event.target.value)}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5 }}>
                  <option value="device">Device</option>
                  <option value="router">Router</option>
                  <option value="switch">Switch</option>
                  <option value="firewall">Firewall</option>
                  <option value="server">Server</option>
                  {!["device", "router", "switch", "firewall", "server"].includes(addDeviceForm.type) && <option value={addDeviceForm.type}>{addDeviceForm.type}</option>}
                </select>
              </label>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650 }}>
                Network OS
                <input value={addDeviceForm.os} onChange={(event) => setAddDeviceField("os", event.target.value)}
                  placeholder="iosxe, nxos, eos..." maxLength={40}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5 }} />
              </label>
              <label style={{ display: "grid", gap: 4, fontSize: 11.5, fontWeight: 650, gridColumn: "1 / -1" }}>
                Platform
                <input value={addDeviceForm.platform} onChange={(event) => setAddDeviceField("platform", event.target.value)}
                  placeholder="c8000v, catalyst, virtual..." maxLength={60}
                  style={{ height: 34, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.cardAlt, color: C.ink, padding: "0 9px", fontSize: 12.5 }} />
              </label>
            </fieldset>}

            {addDeviceError && (
              <div role="alert" style={{ marginTop: 12, padding: "8px 10px", borderRadius: 7, background: "#A8324E18", border: "1px solid #A8324E55", color: "#A8324E", fontSize: 11.5, lineHeight: 1.4 }}>
                {addDeviceError}
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
              <button type="button" disabled={addDeviceBusy} onClick={() => setAddDeviceOpen(false)}
                style={{ height: 32, border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.card, color: C.ink, padding: "0 12px", fontSize: 11.5, cursor: addDeviceBusy ? "default" : "pointer" }}>Cancel</button>
              <button type="submit" disabled={addDeviceBusy}
                style={{ height: 32, border: "none", borderRadius: 7, background: deviceEditMode === "remove" ? "#A8324E" : color, color: "#fff", padding: "0 14px", fontSize: 11.5, fontWeight: 750, cursor: addDeviceBusy ? "default" : "pointer", opacity: addDeviceBusy ? 0.65 : 1 }}>
                {addDeviceBusy ? "Saving..." : deviceEditMode === "add" ? "Append device" : deviceEditMode === "edit" ? "Save changes" : "Remove device"}
              </button>
            </div>
          </form>
        </div>,
        document.body,
      )}

      <div style={{ display: node.min ? "none" : "flex", flex: 1, minHeight: 0, flexDirection: "column", background: "#090E14" }}>
        <div className="nt-toolbar" onMouseDown={(event) => event.stopPropagation()}
          onKeyDown={(event) => { if (event.key === "Escape") { const menu = event.target.closest("details[open]"); if (menu) { event.stopPropagation(); menu.removeAttribute("open"); menu.querySelector("summary")?.focus(); } } }}
          style={{ display: terminalView === "demo" ? "none" : "flex" }}>
          <div className="nt-menu-group">
          <select className="nt-device-select" aria-label="Testbed device" value={deviceId} disabled={status === "connected" || busy}
            onChange={(event) => {
              const value = event.target.value;
              const nextDevice = devices.find((device) => device.id === value);
              setDeviceId(value);
              setLegacyKexEnabled(false);
              setLegacyKexRetryAvailable(false);
              clearPendingCredentials({ clearUsername: true });
              onPatch({
                terminalDevice: value,
                title: value ? `Terminal · ${value}` : "SSH Terminal",
                terminalLegacySshCompatibility: false,
              });
              setStatusMessage(
                nextDevice
                  ? `Ready to connect to ${nextDevice.alias || nextDevice.name}.`
                  : "Choose a testbed device to begin.",
              );
            }}
            title="SSH profiles are loaded from testbed.yaml">
            <option value="">Choose testbed device...</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.alias || device.name} · {device.protocol.toUpperCase()} {device.host}:{device.port}{device.supported ? "" : " (unsupported)"}
              </option>
            ))}
          </select>
          <details name={`terminal-menu-${node.id}`} aria-label="Edit Testbed menu" style={{ position: "relative" }} onClickCapture={closeTerminalMenuAfterAction}>
            <summary title="Add, edit, remove, reload, or provide local credentials for testbed device profiles" style={terminalMenuSummaryStyle}>Edit Testbed</summary>
            <div role="menu" style={terminalMenuPopupStyle}>
          <button onClick={() => openDeviceEditor("add")} disabled={status === "connected" || busy || profilesBusy}
            title="append an SSH profile to the existing testbed.yaml devices mapping"
            style={{ height: 29, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 9px", fontSize: 11, fontWeight: 650, cursor: status === "connected" || busy || profilesBusy ? "default" : "pointer", opacity: status === "connected" || busy || profilesBusy ? 0.55 : 1 }}>+ Device</button>
          <button onClick={() => openDeviceEditor("edit")} disabled={!selectedDevice?.supported || status === "connected" || busy || profilesBusy}
            title="Edit the selected SSH profile; disconnect it in all terminals first. Its collector authorization will be revoked."
            style={{ ...terminalMenuSummaryStyle, listStyle: undefined }}>Edit selected device…</button>
          <button className="nt-danger" onClick={() => openDeviceEditor("remove")} disabled={!selectedDevice || status === "connected" || busy || profilesBusy}
            title="Remove the selected inventory entry after confirmation; the actual device is not changed."
            style={{ ...terminalMenuSummaryStyle, color: "#C74360", listStyle: undefined }}>Remove selected device…</button>
          <button onClick={reloadDeviceProfiles} disabled={status === "connected" || busy || profilesBusy}
            title="reload SSH profiles already present in testbed.yaml"
            style={{ height: 29, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 8px", fontSize: 11, cursor: status === "connected" || busy || profilesBusy ? "default" : "pointer", opacity: status === "connected" || busy || profilesBusy ? 0.5 : 1 }}>
            {profilesBusy ? "Loading..." : "Reload"}
          </button>
          <button onClick={() => {
            setCredentialsError("");
            setCredentialsOpen(true);
          }} disabled={!selectedDevice?.supported || status === "connected" || busy}
            title="enter a username and password for one local SSH connection; credentials are not saved"
            style={{ height: 29, border: `1px solid ${credentialsReady ? color : C.hairline}`, borderRadius: 6, background: credentialsReady ? `${color}18` : C.card, color: credentialsReady ? color : C.ink, padding: "0 9px", fontSize: 11, fontWeight: 650, cursor: !selectedDevice?.supported || status === "connected" || busy ? "default" : "pointer", opacity: !selectedDevice?.supported || status === "connected" || busy ? 0.5 : 1 }}>
            Credentials{credentialsReady ? " ✓" : ""}
          </button>
            </div>
          </details>
          <details name={`terminal-menu-${node.id}`} aria-label="Connection Settings menu" style={{ position: "relative" }} onClickCapture={closeTerminalMenuAfterAction}>
            <summary title="Connect or disconnect, enable legacy SSH compatibility, and reset a saved host key" style={terminalMenuSummaryStyle}>Connection Settings</summary>
            <div role="menu" style={terminalMenuPopupStyle}>
          {status === "connected" ? (
            <button onClick={() => disconnect()} style={{ height: 29, border: "none", borderRadius: 6, background: "#A8324E", color: "#fff", padding: "0 11px", fontSize: 11.5, fontWeight: 700, cursor: "pointer" }}>Disconnect</button>
          ) : (
            <button onClick={() => connect()} disabled={!selectedDevice?.supported || busy}
              style={{ height: 29, border: "none", borderRadius: 6, background: color, color: "#fff", padding: "0 13px", fontSize: 11.5, fontWeight: 700, cursor: !selectedDevice?.supported || busy ? "default" : "pointer", opacity: !selectedDevice?.supported || busy ? 0.5 : 1 }}>
              {legacyKexEnabled ? "Connect · Legacy" : "Connect"}
            </button>
          )}
          {status !== "connected" && (
            <button onClick={() => {
              const nextLegacyKex = !legacyKexEnabled;
              setLegacyKexEnabled(nextLegacyKex);
              setLegacyKexRetryAvailable(false);
              onPatch({ terminalLegacySshCompatibility: nextLegacyKex });
              setStatusMessage(
                nextLegacyKex
                  ? `Legacy KEX enabled for ${selectedDevice?.alias || selectedDevice?.name || deviceId}. Connect will allow DH group14/SHA-1 after modern algorithms.`
                  : `Legacy KEX disabled. Ready to connect to ${selectedDevice?.alias || selectedDevice?.name || deviceId}.`,
              );
            }} disabled={!selectedDevice?.supported || busy}
              title={legacyKexEnabled
                ? "disable the per-terminal DH group14/SHA-1 compatibility exception"
                : "enable DH group14/SHA-1 only for a trusted legacy device; modern key exchanges stay preferred"}
              style={{ height: 29, border: "1px solid #B5651D", borderRadius: 6, background: legacyKexEnabled ? "#B5651D18" : C.card, color: legacyKexEnabled ? (dark ? "#F5C06A" : "#8A4A12") : C.muted, padding: "0 8px", fontSize: 10.5, fontWeight: 700, cursor: !selectedDevice?.supported || busy ? "default" : "pointer", opacity: !selectedDevice?.supported || busy ? 0.5 : 1 }}>
              {legacyKexEnabled ? "Legacy KEX on ×" : "Legacy KEX"}
            </button>
          )}
          <button className="nt-danger" onClick={resetTrustedHostKey} disabled={!selectedDevice?.supported || status === "connected" || busy || hostKeyResetBusy}
            title="remove this device's saved SSH fingerprint; reconnect to verify and trust the current key"
            style={{ height: 29, border: "1px solid #A8324E88", borderRadius: 6, background: C.card, color: "#C94C65", padding: "0 8px", fontSize: 10.5, fontWeight: 700, cursor: !selectedDevice?.supported || status === "connected" || busy || hostKeyResetBusy ? "default" : "pointer", opacity: !selectedDevice?.supported || status === "connected" || busy || hostKeyResetBusy ? 0.5 : 1 }}>
            {hostKeyResetBusy ? "Resetting…" : "Reset host key"}
          </button>
            </div>
          </details>
          </div>
          <div className="nt-menu-group">
          <details name={`terminal-menu-${node.id}`} aria-label="Edit menu" style={{ position: "relative" }} onClickCapture={closeTerminalMenuAfterAction}>
            <summary title="Copy, paste, clear terminal output, or open a configuration review" style={terminalMenuSummaryStyle}>Edit</summary>
            <div role="menu" style={terminalMenuPopupStyle}>
          <button onClick={copySelection} title="copy selected terminal text (Ctrl/Cmd+Shift+C)"
            style={{ height: 29, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 8px", fontSize: 11, cursor: "pointer" }}>Copy</button>
          <button onClick={pasteClipboard} disabled={status !== "connected"} title="paste clipboard (Ctrl/Cmd+Shift+V)"
            style={{ height: 29, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 8px", fontSize: 11, cursor: status === "connected" ? "pointer" : "default", opacity: status === "connected" ? 1 : 0.5 }}>Paste</button>
          <button onClick={clearTerminal} title="clear the saved terminal transcript and source highlights"
            style={{ height: 29, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 8px", fontSize: 11, cursor: "pointer" }}>Clear</button>
          <button onClick={openConfigReview} title="open selected terminal output, or the full visible buffer, in an immutable configuration review"
            style={{ height: 29, border: "none", borderRadius: 6, background: "#B5651D", color: "#fff", padding: "0 9px", fontSize: 11, fontWeight: 700, cursor: "pointer" }}>Review config</button>
            </div>
          </details>
          <details name={`terminal-menu-${node.id}`} aria-label="AI settings menu" style={{ position: "relative" }} onClickCapture={closeTerminalMenuAfterAction} onChangeCapture={closeTerminalMenuAfterChoice}>
            <summary title="Choose the terminal assistant, configure Instant Assist, or open the AI Intent panel" style={terminalMenuSummaryStyle}>AI settings</summary>
            <div role="menu" style={{ ...terminalMenuPopupStyle, minWidth: 245 }}>
          <label title={terraStatus.configured
            ? "Choose the model that translates terminal context into English intent and CLI proposals"
            : "Choose Set up Instant Assist to save a local API key and enable the Instant model"}
            style={{ display: "inline-flex", alignItems: "center", gap: 5, color: C.muted, fontSize: 10, fontWeight: 700 }}>
            AI
            <select aria-label="Terminal AI mode" value={terminalAssistantMode} onChange={(event) => {
              const nextMode = event.target.value;
              setTerminalAssistantMode(nextMode);
              setIntentError("");
              onPatch({ terminalAssistantMode: nextMode });
            }}
              style={{ height: 29, border: `1px solid ${terminalAssistantMode === "terra" ? "#C792EA88" : C.hairline}`, borderRadius: 6, background: C.card, color: terminalAssistantMode === "terra" ? "#9C6BCE" : C.ink, padding: "0 7px", fontSize: 10.5, fontWeight: 700 }}>
              <option value="netclaw">NetClaw Gateway</option>
              <option value="terra" disabled={!terraStatus.configured}>
                {terraStatus.configured ? "Instant Assist" : "Instant Assist (API key required)"}
              </option>
            </select>
          </label>
          <button onClick={() => {
            setTerraConfigError("");
            setTerraConfigOpen(true);
          }}
            title="configure the local Instant Assist API key"
            style={{ height: 29, border: `1px solid #C792EA88`, borderRadius: 6, background: terraStatus.configured ? "#C792EA12" : C.card, color: "#9C6BCE", padding: "0 8px", fontSize: 10.5, fontWeight: 700, cursor: "pointer" }}>
            {terraStatus.configured ? "Instant settings" : "Set up Instant Assist"}
          </button>
          <button onClick={openIntentPane}
            title="open the AI Intent panel beside the terminal output"
            style={{ height: 29, border: "none", borderRadius: 6, background: "#6D4AA1", color: "#fff", padding: "0 9px", fontSize: 10.5, fontWeight: 750, cursor: "pointer" }}>
            AI Intent
          </button>
            </div>
          </details>
          <details name={`terminal-menu-${node.id}`} aria-label="Extra Features menu" style={{ position: "relative" }} onClickCapture={closeTerminalMenuAfterAction}>
            <summary title="Open optional terminal features, including traditional terminal mode" style={terminalMenuSummaryStyle}>Extra Features</summary>
            <div role="menu" style={terminalMenuPopupStyle}>
          <button onClick={useTraditionalTerminalOnly} aria-pressed={terminalView === "terminal"}
            title="close AI and structured-output views and use the standard interactive SSH terminal"
            style={{ height: 29, border: `1px solid ${terminalView === "terminal" ? `${color}88` : C.hairline}`, borderRadius: 6, background: terminalView === "terminal" ? `${color}16` : C.card, color: terminalView === "terminal" ? color : C.ink, padding: "0 9px", fontSize: 10.5, fontWeight: 750, cursor: "pointer" }}>
            Use traditional terminal only
          </button>
          <label title="Resolve host IP addresses in the presentation layer. Raw SSH output, selection, copy, and logs are unchanged."
            style={{ display: "flex", alignItems: "center", gap: 6, minHeight: 29, padding: "0 2px", color: C.ink, fontSize: 10.5, fontWeight: 650, cursor: "pointer" }}>
            <input type="checkbox" checked={enrichmentEnabled} onChange={(event) => {
              const enabled = event.target.checked;
              setEnrichmentEnabled(enabled);
              onPatch({ terminalEnrichmentEnabled: enabled });
            }} />
            Inline DNS enrichment
          </label>
          <button onClick={addLocalTerminalAlias} title="Save a local label for an IP address or route prefix when DNS or inventory does not have one"
            style={{ height: 29, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 9px", fontSize: 10.5, fontWeight: 700, cursor: "pointer" }}>
            Add local alias
          </button>
          <button onClick={openTopologySettings} title="Authorize autonomous read-only collection and cross-router route correlation"
            style={{ height: 29, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 9px", fontSize: 10.5, fontWeight: 700, cursor: "pointer" }}>
            Automatic topology context
          </button>
          <button onClick={openObservability} title="Configure optional read-only provider context and OpenTelemetry health export"
            style={{ height: 29, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 9px", fontSize: 10.5, fontWeight: 700, cursor: "pointer" }}>
            Observability integrations
          </button>
            </div>
          </details>
          </div>
        </div>

        <div className="nt-outputbar" role="tablist" aria-label="Terminal output views" onMouseDown={(event) => event.stopPropagation()}>
          <button role="tab" aria-selected={terminalView === "terminal"} onClick={() => setTerminalView("terminal")}
            style={{ height: 26, border: "none", borderBottom: `2px solid ${terminalView === "terminal" ? color : "transparent"}`, background: "transparent", color: terminalView === "terminal" ? color : C.muted, padding: "0 9px", fontSize: 10.5, fontWeight: 750, cursor: "pointer" }}>
            Terminal
          </button>
          <button role="tab" aria-selected={terminalView === "structured"} onClick={openStructuredOutput}
            style={{ height: 26, border: "none", borderBottom: `2px solid ${terminalView === "structured" ? color : "transparent"}`, background: "transparent", color: terminalView === "structured" ? color : C.muted, padding: "0 9px", fontSize: 10.5, fontWeight: 750, cursor: "pointer" }}>
            Structured output
          </button>
          <button role="tab" aria-selected={terminalView === "demo"} onClick={() => {
            enrichmentHover.close();
            setExportOpen(false);
            setTerminalView("demo");
          }} title="Explore fictional NetBox and ServiceNow data. Demonstration only; no live integrations or commands."
            style={{ height: 26, border: "none", borderBottom: `2px solid ${terminalView === "demo" ? "#B5651D" : "transparent"}`, background: "transparent", color: terminalView === "demo" ? (dark ? "#F5C06A" : "#8A4A12") : C.muted, padding: "0 9px", fontSize: 10.5, fontWeight: 750, cursor: "pointer" }}>
            NetBox / SNOW demo
          </button>
          {terminalView !== "demo" && <>
          <select aria-label="Structured output format" value={structuredFormat} onChange={(event) => {
            const nextFormat = event.target.value;
            setStructuredOutputFormat(nextFormat);
            openStructuredOutput();
            if (nextFormat === "intent") {
              window.setTimeout(() => requestTerminalIntent({ explainOnly: true }), 0);
            }
          }}
            style={{ height: 26, border: `1px solid ${C.hairline}`, borderRadius: 6, background: C.card, color: C.ink, padding: "0 7px", fontSize: 10.5, fontWeight: 700 }}>
            {ARTIFACT_FORMATS.map((format) => <option key={format.id} value={format.id}>Output: {format.label}</option>)}
            <option value="intent">Output: English intent</option>
          </select>
          <button onClick={createStructuredResult}
            disabled={!structuredResultReady}
            title={structuredFormat === "intent"
              ? (structuredResultReady ? "create a text Result from the English explanation" : "generate an English intent explanation first")
              : structuredPreview?.validation.status === "invalid"
                ? `Result blocked: ${structuredPreview.validation.message || "format validation failed"}`
                : "create a connected, persisted Result from the validated selection or terminal transcript"}
            style={{ height: 26, border: "none", borderRadius: 6, background: color, color: "#fff", padding: "0 10px", fontSize: 10.5, fontWeight: 750, cursor: structuredResultReady ? "pointer" : "default", opacity: structuredResultReady ? 1 : 0.45 }}>
            ▤ Create Result
          </button>
          <span className="nt-selection-hint">
            {structuredFormat === "intent" && terminalView === "structured"
              ? "terminal output translated into English"
              : structuredSelection?.quote
              ? `${structuredSelection.quote.split(/\n/).length} ${structuredSelection.range ? "selected" : "transcript"} line${structuredSelection.quote.split(/\n/).length === 1 ? "" : "s"}`
              : "uses full transcript when nothing is selected"}
          </span>
          </>}
        </div>

        <div className="nt-statusbar">
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: terminalView === "demo" ? "#F5C06A" : statusColor, flexShrink: 0 }} />
          <span className="nt-status-message" title={statusMessage} role="status">{terminalView === "demo" ? "SYNTHETIC DEMO · NetBox + ServiceNow" : statusMessage}</span>
          {legacyKexRetryAvailable && terminalView !== "demo" && (
            <button onClick={() => connect({ legacySshCompatibility: true })}
              title="retry this trusted device with DH group14/SHA-1 appended after modern key exchanges"
              style={{ flexShrink: 0, height: 22, border: "1px solid #B5651D", borderRadius: 5, background: "#B5651D", color: "#fff", padding: "0 8px", fontSize: 10, fontWeight: 750, cursor: "pointer" }}>
              Retry legacy KEX
            </button>
          )}
          <span className="nt-workflow-hint">
            {terminalView === "terminal" && enrichmentSpaceUnavailable
              ? "Widen the terminal to show network context without covering output."
              : terminalView === "demo"
              ? "demo sends no commands"
              : terminalView === "terminal"
              ? "select output to branch or create a Result · commands execute immediately"
              : structuredFormat === "intent"
                ? "Intent executes through NetClaw tools · existing change controls apply"
                : structuredFormat === "json" ? "JSON · local pyATS / Genie parser"
                : `${artifactFormat(structuredFormat).label} preview · local transformation`}
          </span>
        </div>

        <div ref={terminalHostRef} onMouseDown={(event) => event.stopPropagation()} onMouseUpCapture={handleTerminalSelection}
          style={{ position: "relative", flex: 1, minHeight: 0, padding: "7px 8px", background: "#090E14", overflow: "hidden", display: terminalView === "terminal" ? "block" : "none" }} />
        {terminalView === "demo" && <TerminalEnrichmentDemo onReturnToTerminal={() => setTerminalView("terminal")} />}
        {topologyOpen && <TopologySettings onClose={closeTopologySettings} />}
        {observabilityOpen && <ObservabilitySettings onClose={closeObservability} />}
        {terminalView === "terminal" && enrichmentPopover && <TerminalEnrichmentPopover {...enrichmentHover.popoverProps}
          dockRef={terminalHostRef} getContentRight={getEnrichmentContentRight}
          onSpaceUnavailable={setEnrichmentSpaceUnavailable}
          topologyImage={{ storageKey: topologyDiagramKey({ deviceId }),
            activeDeviceId: deviceId, devices, token: enrichmentPopover.token, context: topologyImageContext,
            temporary: node.terminalPreviewOnly === true }}
          title={enrichmentPopover.token.value} subtitle={enrichmentPopover.token.type === "prefix" ? "Route / network" : "Host address"}>
          <div className="tep-tile-grid">
            <TopologyRouteContext token={enrichmentPopover.token} activeDeviceId={deviceId} onOpenSettings={openTopologySettings} onContextChange={setTopologyImageContext} />
            <ObservabilityContext token={enrichmentPopover.token} onOpenSettings={openObservability} />
            <section className="tep-tile">
              <h4>{enrichmentPopover.token.type === "prefix" ? "Route prefix" : "IP address"}</h4>
              <p>{enrichmentPopover.token.value}</p>
              <p>Source: terminal output.</p>
            </section>
            {enrichmentPopover.record.providers?.["local-alias"]?.status === "resolved" && <section className="tep-tile">
              <h4>Local alias</h4>
              <p>{enrichmentPopover.record.providers["local-alias"].alias}</p>
              <p>Source: locally saved alias.</p>
            </section>}
            {enrichmentPopover.token.type !== "prefix" && <section className="tep-tile">
              <h4>DNS / PTR</h4>
              {enrichmentPopover.record.pending ? <p>Looking up PTR record…</p>
                : enrichmentPopover.record.providers?.["dns-ptr"]?.status === "resolved" ? <>
                  <p>Hostname: {enrichmentPopover.record.providers["dns-ptr"].hostname}</p>
                  <p>FQDN: {enrichmentPopover.record.providers["dns-ptr"].fqdn}</p>
                </> : <p>No PTR information available.</p>}
            </section>}
          </div>
        </TerminalEnrichmentPopover>}

        {terminalView === "structured" && structuredFormat === "json" && (
          <GenieJsonOutput source={structuredSource} deviceId={deviceId}
            deviceLabel={selectedDevice?.alias || selectedDevice?.name || deviceId || "terminal"}
            deviceOs={selectedDevice?.os} onParsed={setGeniePreview} />
        )}
        {terminalView === "structured" && structuredFormat !== "intent" && structuredFormat !== "json" && (
          <div onMouseDown={(event) => event.stopPropagation()}
            style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", background: "#090E14", overflow: "hidden" }}>
            {structuredPreview ? (
              <>
                <div style={{ padding: "7px 10px", display: "flex", alignItems: "center", gap: 7, borderBottom: "1px solid #1F2937", color: "#94A3B8", fontSize: 10, flexShrink: 0 }}>
                  <span style={{ color: "#7FDBCA", fontWeight: 800 }}>{structuredPreview.label}</span>
                  <span>{structuredPreview.records} records</span>
                  <span style={{ color: structuredPreview.structure === "hierarchical" ? "#7FDBCA" : "#94A3B8", fontWeight: 700 }}>
                    {structuredPreview.structure === "hierarchical" ? "Hierarchy detected" : structuredPreview.structure === "flat" ? "Flat structure" : "Native structure"}
                  </span>
                  <span style={{ color: structuredPreview.validation.status === "valid" ? "#7FDBA8" : "#EF6B73", fontWeight: 700 }}>
                    {structuredPreview.validation.status === "valid" ? "✓ Validated" : "⚠ Invalid"}
                  </span>
                  <span style={{ marginLeft: "auto", fontFamily: "ui-monospace, Menlo, monospace" }}>{structuredPreview.name}</span>
                </div>
                {structuredPreview.validation.status === "valid" ? (
                  <pre aria-label={`Validated ${structuredPreview.label} preview`}
                    style={{ margin: 0, flex: 1, minHeight: 0, overflow: "auto", padding: "10px 12px", whiteSpace: "pre-wrap", overflowWrap: "anywhere", color: "#D6DEEB", fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, monospace', fontSize: 12, lineHeight: 1.5 }}>
                    {structuredPreview.content}
                  </pre>
                ) : (
                  <div role="alert" style={{ flex: 1, display: "grid", placeItems: "center", padding: 24, color: "#EF6B73", textAlign: "center", fontSize: 12, lineHeight: 1.55 }}>
                    Preview withheld because validation failed: {structuredPreview.validation.message || "invalid structured output"}
                  </div>
                )}
              </>
            ) : (
              <div style={{ flex: 1, display: "grid", placeItems: "center", padding: 24, color: "#94A3B8", textAlign: "center", fontSize: 12, lineHeight: 1.55 }}>
                Select terminal output, then open Structured output. If nothing is selected, Create Result uses the full visible transcript.
              </div>
            )}
          </div>
        )}

        {terminalView === "structured" && structuredFormat === "intent" && (
          <div onMouseDown={(event) => event.stopPropagation()}
            style={{ flex: 1, minHeight: 0, display: "flex", background: "#090E14", color: "#D6DEEB", overflow: "hidden" }}>
            <div style={{ flex: 1, minWidth: 0, minHeight: 0, display: "flex", flexDirection: "column" }}>
            <div style={{ padding: "7px 9px", display: "flex", alignItems: "center", gap: 7, flexWrap: "wrap", borderBottom: "1px solid #1F2937", background: "#0D141D", flexShrink: 0 }}>
              <span style={{ color: "#C792EA", fontSize: 10.5, fontWeight: 800, letterSpacing: 0.5 }}>ENGLISH INTENT · {terminalAssistantMode === "terra" ? "INSTANT ASSIST" : "NETCLAW"}</span>
              <span style={{ color: "#94A3B8", fontSize: 9.5 }}>Requests execute through NetClaw tools. Required approvals and missing decisions are surfaced here.</span>
              <button onClick={() => requestTerminalIntent({ explainOnly: true })} disabled={intentBusy}
                title="explain the selected terminal output, or the visible transcript, in plain English"
                style={{ marginLeft: "auto", height: 25, border: "1px solid #C792EA66", borderRadius: 6, background: "#C792EA18", color: "#D8B4FE", padding: "0 8px", fontSize: 10, fontWeight: 700, cursor: intentBusy ? "default" : "pointer", opacity: intentBusy ? 0.55 : 1 }}>
                Explain output
              </button>
              <button onClick={clearIntentHistory} disabled={!intentHistory.length || intentBusy}
                style={{ height: 25, border: "1px solid #2A3442", borderRadius: 6, background: "transparent", color: "#94A3B8", padding: "0 8px", fontSize: 10, cursor: !intentHistory.length || intentBusy ? "default" : "pointer", opacity: !intentHistory.length || intentBusy ? 0.45 : 1 }}>
                Clear
              </button>
            </div>

            <div ref={intentLogRef} role="log" aria-label="Terminal intent conversation"
              style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "10px 12px", display: "flex", flexDirection: "column", gap: 9 }}>
              {!intentHistory.length && !intentBusy && (
                <div style={{ margin: "auto", maxWidth: 500, color: "#94A3B8", textAlign: "center", fontSize: 12, lineHeight: 1.6 }}>
                  Ask in English, such as “Why is this interface down?” or “Show me the BGP neighbor state.”
                  {' NetClaw pursues the requested outcome through its tools. Explain output is available separately.'}
                </div>
              )}
              {intentHistory.map((message) => {
                const proposal = message.proposal;
                const hasCommands = proposal?.commands?.length > 0;
                const requiresApproval = hasCommands && proposal.risk !== "read-only" && message.execution?.status !== 'reviewed-sent';
                const riskColor = proposal?.risk === "destructive"
                  ? "#EF6B73"
                  : proposal?.risk === "configuration" || proposal?.risk === "unknown"
                    ? "#F5C06A"
                    : "#7FDBA8";
                return (
                  <div key={message.id} style={{
                    alignSelf: message.role === "user" ? "flex-end" : "stretch",
                    maxWidth: message.role === "user" ? "82%" : "100%",
                    border: `1px solid ${message.role === "user" ? "#2F6FB066" : "#2A3442"}`,
                    borderRadius: 9,
                    background: message.role === "user" ? "#2F6FB022" : "#111821",
                    padding: "9px 10px",
                  }}>
                    <div style={{ color: message.role === "user" ? "#9CC6FF" : "#C792EA", fontSize: 9, fontWeight: 800, letterSpacing: 0.7, textTransform: "uppercase", marginBottom: 5 }}>
                      {message.role === "user" ? "You" : message.terminalOutput ? "Read-only command result" : "NetClaw intent"}
                    </div>
                    {message.executedCommands?.length > 0 && (
                      <div style={{ marginBottom: 6, color: "#7FDBA8", fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, monospace', fontSize: 10.5 }}>
                        Executed: {message.executedCommands.join(" · ")}
                      </div>
                    )}
                    {proposal?.intent && (
                      <div style={{ color: "#FFFFFF", fontSize: 12, fontWeight: 750, marginBottom: 5 }}>{proposal.intent}</div>
                    )}
                    <div style={{ color: "#D6DEEB", fontSize: 11.5, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>{message.content}</div>
                    {proposal?.assumptions?.length > 0 && (
                      <div style={{ marginTop: 7, color: "#94A3B8", fontSize: 10.5, lineHeight: 1.45 }}>
                        Assumptions: {proposal.assumptions.join(" · ")}
                      </div>
                    )}
                    {message.terminalOutput && (
                      <details style={{ marginTop: 8, border: "1px solid #2A3442", borderRadius: 6, background: "#070B10", overflow: "hidden" }}>
                        <summary style={{ padding: "6px 8px", color: "#94A3B8", fontSize: 10, fontWeight: 700, cursor: "pointer" }}>
                          Exact terminal output
                        </summary>
                        <pre aria-label="Captured terminal output"
                          style={{ margin: 0, padding: "8px 10px", borderTop: "1px solid #2A3442", overflowX: "auto", color: "#D6DEEB", fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, monospace', fontSize: 10.5, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                          {message.terminalOutput}
                        </pre>
                      </details>
                    )}
                    {hasCommands && (
                      <div style={{ marginTop: 9, border: `1px solid ${riskColor}55`, borderRadius: 7, overflow: "hidden" }}>
                        <div style={{ minHeight: 28, padding: "5px 8px", display: "flex", alignItems: "center", gap: 7, background: "#0D141D", borderBottom: "1px solid #2A3442" }}>
                          <span style={{ color: riskColor, fontSize: 9.5, fontWeight: 800, textTransform: "uppercase" }}>{proposal.risk} proposal</span>
                          <span style={{ color: "#94A3B8", fontSize: 9.5 }}>
                            {proposal.commands.length} command{proposal.commands.length === 1 ? "" : "s"} · {message.execution?.status === 'reviewed-sent' ? 'sent after review — not verified' : message.execution?.status === "sent" ? "sent automatically" : requiresApproval ? "awaiting review" : "waiting for connection"}
                          </span>
                        </div>
                        <pre aria-label="Proposed terminal commands"
                          style={{ margin: 0, padding: "8px 10px", overflowX: "auto", color: "#D6DEEB", background: "#070B10", fontFamily: '"Cascadia Mono", "SFMono-Regular", Consolas, monospace', fontSize: 11.5, lineHeight: 1.55, whiteSpace: "pre-wrap" }}>
                          {proposal.commands.join("\n")}
                        </pre>
                        <div style={{ padding: "7px 8px", display: "flex", alignItems: "center", gap: 7, flexWrap: "wrap", background: "#0D141D", borderTop: "1px solid #2A3442" }}>
                          <button onClick={() => copyIntentCommands(proposal)}
                            style={{ height: 25, border: "1px solid #2A3442", borderRadius: 5, background: "transparent", color: "#D6DEEB", padding: "0 8px", fontSize: 10, cursor: "pointer" }}>
                            Copy CLI
                          </button>
                          {requiresApproval ? (
                            <>
                              <label style={{ display: "inline-flex", alignItems: "center", gap: 5, color: "#CBD5E1", fontSize: 10, cursor: "pointer" }}>
                                <input type="checkbox" checked={approvedIntentId === message.id}
                                  onChange={(event) => setApprovedIntentId(event.target.checked ? message.id : null)} />
                                I reviewed the exact CLI
                              </label>
                              <button onClick={() => sendIntentCommands(message)}
                                disabled={approvedIntentId !== message.id || status !== "connected" || intentBusy}
                                title={status === "connected" ? "send the reviewed configuration CLI to this terminal session" : "connect to the device before sending configuration commands"}
                                style={{ marginLeft: "auto", height: 26, border: "none", borderRadius: 5, background: riskColor, color: "#081018", padding: "0 9px", fontSize: 10, fontWeight: 800, cursor: approvedIntentId === message.id && status === "connected" && !intentBusy ? "pointer" : "default", opacity: approvedIntentId === message.id && status === "connected" && !intentBusy ? 1 : 0.4 }}>
                                Send configuration
                              </button>
                            </>
                          ) : (
                            <span style={{ marginLeft: "auto", color: message.execution?.status === "sent" ? "#7FDBA8" : "#94A3B8", fontSize: 10 }}>
                              {message.execution?.message || "Verified read-only request"}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
              {intentRun && <TerminalIntentLiveActivity key={intentRun.id} run={intentRun} />}
              {intentBusy && !intentRun && (
                <div role="status" style={{ alignSelf: "stretch", border: "1px solid #2A3442", borderRadius: 9, background: "#111821", padding: "10px", color: "#C792EA", fontSize: 11.5 }}>
                  {intentPhase === 'execution' ? 'NetClaw is working on the requested outcome…' : intentPhase === 'capture' ? 'Collecting read-only output…' : intentPhase === 'summary' ? 'Waiting for an explanation of the captured output…' : 'Waiting for the AI response…'} See workflow status on the right.
                </div>
              )}
              {intentError && (
                <div role="alert" style={{ border: "1px solid #EF6B7355", borderRadius: 7, background: "#EF6B7312", padding: "8px 9px", color: "#EF8B92", fontSize: 10.5 }}>
                  {intentError}
                </div>
              )}
            </div>
            </div>

            <form onSubmit={submitTerminalIntent}
              style={{ width: "clamp(230px, 29vw, 350px)", minWidth: 230, overflowY: 'auto', padding: "14px 12px", display: "flex", flexDirection: "column", alignItems: "stretch", gap: 9, borderLeft: "1px solid #1F2937", background: "#0D141D", flexShrink: 0 }}>
              <div>
                <div style={{ color: "#C792EA", fontSize: 10.5, fontWeight: 800, letterSpacing: 0.55, textTransform: "uppercase" }}>AI Intent</div>
                <div style={{ marginTop: 5, color: "#94A3B8", fontSize: 10.5, lineHeight: 1.5 }}>
                  Describe the outcome in English. NetClaw will use its tools to discover, act and verify across the requested devices.
                </div>
              </div>
              <TerminalChangeControl devices={devices} value={intentChangeControl} busy={intentBusy} onChange={value => {
                setIntentChangeControl(value); onPatch({ terminalChangeMode: value.mode, terminalChangeDevices: value.targetDeviceIds });
              }} />
              {intentRun ? <TerminalIntentExecution run={intentRun} /> :
                <TerminalIntentActivity phase={intentPhase} error={intentError} executionEnabled
                  message={intentHistory[intentHistory.length - 1]} connected={status === 'connected'} />}
              <textarea aria-label="Terminal intent request" value={intentPrompt} onChange={(event) => setIntentPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    if (!intentBusy && intentPrompt.trim()) requestTerminalIntent({ request: intentPrompt });
                  }
                }}
                placeholder="Ask about the output or describe what you want the device to do…"
                rows={8}
                style={{ width: "100%", boxSizing: "border-box", minWidth: 0, resize: "vertical", border: "1px solid #2A3442", borderRadius: 7, background: "#070B10", color: "#D6DEEB", padding: "8px 9px", fontFamily: "inherit", fontSize: 11.5, lineHeight: 1.45, outline: "none" }} />
              <button type="submit" disabled={intentBusy || !intentPrompt.trim()}
                style={{ width: "100%", height: 35, border: "none", borderRadius: 7, background: "#C792EA", color: "#111827", padding: "0 11px", fontSize: 10.5, fontWeight: 800, cursor: intentBusy || !intentPrompt.trim() ? "default" : "pointer", opacity: intentBusy || !intentPrompt.trim() ? 0.45 : 1 }}>
                {intentBusy ? 'Working…' : 'Ask NetClaw'}
              </button>
              <div style={{ color: "#64748B", fontSize: 9.5, lineHeight: 1.45 }}>
                Submitting authorizes work within your request, subject to NetClaw's existing controls. Action requests use the tool-enabled NetClaw Gateway; Instant Assist is used only for Explain output. A browser SSH session is not required, but the agent needs device access.
              </div>
            </form>
          </div>
        )}

        {traditionalTerminalOverlayOpen && (
          <div role="dialog" aria-modal="true" aria-label="Traditional terminal mode"
            onMouseDown={(event) => event.stopPropagation()}
            style={{ position: "absolute", inset: 0, zIndex: 19, display: "grid", placeItems: "center", padding: 16, background: "rgba(3, 9, 22, 0.88)" }}>
            <div style={{ width: "min(900px, 96%)", maxHeight: "94%", overflow: "auto", border: "1px solid #6EA9FF", borderRadius: 10, background: "#031D73", boxShadow: "0 18px 55px rgba(0,0,0,0.55)", padding: 12 }}>
              <img src="/netclaw_adam.gif" alt="NetClaw Canvas traditional terminal mode animation"
                style={{ display: "block", width: "100%", maxHeight: "min(68vh, 650px)", objectFit: "contain", borderRadius: 5 }} />
              <div style={{ marginTop: 10, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, color: "#DCE9FF", fontFamily: '"Cascadia Mono", Consolas, monospace', fontSize: 11 }}>
                <span>Traditional terminal mode is active.</span>
                <button onClick={closeTraditionalTerminalOverlay}
                  style={{ border: "1px solid #A8C7FF", borderRadius: 6, background: "#FFFFFF", color: "#08215D", padding: "7px 11px", fontSize: 11, fontWeight: 800, cursor: "pointer" }}>
                  Continue to terminal
                </button>
              </div>
            </div>
          </div>
        )}

        {hostKey && (
          <div onMouseDown={(event) => event.stopPropagation()}
            style={{ position: "absolute", inset: 0, zIndex: 20, display: "grid", placeItems: "center", background: "rgba(3,7,12,0.82)", padding: 20 }}>
            <div style={{ width: "min(500px, 92%)", background: C.card, color: C.ink, border: `1px solid ${hostKey.changed ? "#A8324E" : "#B5651D"}`, borderRadius: 11, boxShadow: "0 18px 50px rgba(0,0,0,0.45)", padding: 16 }}>
              <div style={{ fontSize: 13.5, fontWeight: 800, color: hostKey.changed ? "#A8324E" : "#B5651D", marginBottom: 7 }}>
                {hostKey.changed ? "SSH host key changed" : "Trust this SSH host key?"}
              </div>
              <div style={{ fontSize: 12, color: C.muted, lineHeight: 1.45, marginBottom: 10 }}>
                {hostKey.changed
                  ? "The key no longer matches the value previously trusted for this endpoint. Verify it out of band before continuing."
                  : "Like PuTTY's first-connection prompt, verify this fingerprint before saving it locally."}
              </div>
              <div style={{ background: C.codeBg, border: `1px solid ${C.hairline}`, borderRadius: 7, padding: "8px 10px", fontFamily: "ui-monospace, Menlo, monospace", fontSize: 11, overflowWrap: "anywhere", marginBottom: 12 }}>
                <div style={{ color: C.muted, marginBottom: 3 }}>{hostKey.keyType} · {hostKey.host}:{hostKey.port}</div>
                <div>{hostKey.fingerprint}</div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 7 }}>
                <button onClick={() => respondToHostKey(false)}
                  style={{ border: `1px solid ${C.hairline}`, borderRadius: 7, background: C.card, color: C.ink, padding: "7px 11px", fontSize: 11.5, cursor: "pointer" }}>Cancel</button>
                <button onClick={() => respondToHostKey(true)}
                  style={{ border: "none", borderRadius: 7, background: hostKey.changed ? "#A8324E" : color, color: "#fff", padding: "7px 12px", fontSize: 11.5, fontWeight: 700, cursor: "pointer" }}>
                  {hostKey.changed ? "Trust changed key" : "Trust and connect"}
                </button>
              </div>
            </div>
          </div>
        )}

        <div data-terminal-resize onMouseDown={onResizeStart} onDoubleClick={onAutoFit} title="drag to resize · double-click to reset terminal size"
          style={{ position: "absolute", right: 0, bottom: 0, width: 18, height: 18, cursor: "nwse-resize", background: `linear-gradient(135deg, transparent 50%, ${color} 50%)`, borderBottomRightRadius: 10, opacity: 0.75 }} />
      </div>
    </div>
  );
}

export { TerminalLane };
export default TerminalLane;
