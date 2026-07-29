'use strict';

const express = require('express');
const router = express.Router();
const { instantQuery } = require('../lib/queryEngine');
const { vmInstantQuery } = require('../lib/queryEngine');
const { formatUptime } = require('../lib/formatters');
const {
  getSiteConfig, getMgmtUrls, getSwitchConfig, promqlLabelValue,
} = require('../lib/config');

/**
 * GET /api/devices?site=X
 * Equipment status: WAN probes, edge/firewall, UniFi APs/switches/gateways,
 * greenfield device_snmp (ifOperStatus via Prometheus), and optional pilot
 * VictoriaMetrics SNMP (interface_status).
 */
router.get('/', async (req, res) => {
  const site = req.site;
  const config = getSiteConfig(site);
  const mgmt = getMgmtUrls(site);
  // device_name matcher for the pilot VictoriaMetrics SNMP queries. Escaped
  // because it lands inside a PromQL label matcher.
  const switchMatch = promqlLabelValue(getSwitchConfig(site).match);

  try {
    const [
      probeStatus, probeDuration,
      edgeStatus, edgeDuration,
      apStatus, apClients, apCpu, apMemory, apUptime,
      gwStatus, gwCpu, gwMemory, gwUptime,
      swUnifiStatus, swUnifiCpu, swUnifiMemory, swUnifiUptime,
      // Greenfield Phase 8: snmp_exporter IF-MIB in Convergence Prometheus
      gfIfUp, gfIfTotal, gfErrors, gfSnmpUp,
      // Pilot OBS VictoriaMetrics (optional dual-run; fails soft on Docker-only)
      switchIfUp, switchIfTotal, switchErrors
    ] = await Promise.allSettled([
      instantQuery(`probe_success{job=~"blackbox_wan_tcp|blackbox_wan_http|blackbox_wan_dns|blackbox_http"}`),
      instantQuery(`probe_duration_seconds{job=~"blackbox_wan_tcp|blackbox_wan_http|blackbox_wan_dns|blackbox_http"}`),
      // Edge firewall (blackbox_edge) or any probe labeled role=firewall / device_name=pfsense
      instantQuery(`probe_success{job="blackbox_edge"} or probe_success{role="firewall"} or probe_success{device_name="pfsense"}`),
      instantQuery(`probe_duration_seconds{job="blackbox_edge"} or probe_duration_seconds{role="firewall"} or probe_duration_seconds{device_name="pfsense"}`),
      instantQuery(`unifi_device_up{role="ap", site="${site}"}`),
      instantQuery(`unifi_ap_clients{site="${site}"}`),
      instantQuery(`unifi_device_cpu_pct{role="ap", site="${site}"}`),
      instantQuery(`unifi_device_memory_pct{role="ap", site="${site}"}`),
      instantQuery(`unifi_device_uptime_seconds{role="ap", site="${site}"}`),
      instantQuery(`unifi_device_up{role="gateway", site="${site}"}`),
      instantQuery(`unifi_device_cpu_pct{role="gateway", site="${site}"}`),
      instantQuery(`unifi_device_memory_pct{role="gateway", site="${site}"}`),
      instantQuery(`unifi_device_uptime_seconds{role="gateway", site="${site}"}`),
      instantQuery(`unifi_device_up{role="switch", site="${site}"}`),
      instantQuery(`unifi_device_cpu_pct{role="switch", site="${site}"}`),
      instantQuery(`unifi_device_memory_pct{role="switch", site="${site}"}`),
      instantQuery(`unifi_device_uptime_seconds{role="switch", site="${site}"}`),
      // Greenfield: ifOperStatus 1=up (job device_snmp; site label optional)
      instantQuery(`count by (device_name) (ifOperStatus{job="device_snmp"} == 1)`),
      instantQuery(`count by (device_name) (ifOperStatus{job="device_snmp"})`),
      instantQuery(`sum by (device_name) (rate(ifInErrors{job="device_snmp"}[5m]) + rate(ifOutErrors{job="device_snmp"}[5m]))`),
      instantQuery(`up{job="device_snmp"}`),
      // Pilot VictoriaMetrics SNMP. The device_name matcher comes from site
      // config (switches.match, default ".*") — it was hardcoded to one lab's
      // naming scheme, which left this table empty everywhere else.
      vmInstantQuery(`count by (device_name) (interface_status{device_name=~"${switchMatch}"} == 1)`),
      vmInstantQuery(`count by (device_name) (interface_status{device_name=~"${switchMatch}"})`),
      vmInstantQuery(`sum by (device_name) (rate(interface_errors_in_total{device_name=~"${switchMatch}"}[5m]) + rate(interface_errors_out_total{device_name=~"${switchMatch}"}[5m]))`)
    ]);

    // Build WAN probes table
    const wanProbes = [];
    if (probeStatus.status === 'fulfilled') {
      const durations = new Map();
      if (probeDuration.status === 'fulfilled') {
        for (const r of probeDuration.value) {
          const key = r.metric.instance || r.metric.target || '';
          durations.set(key, parseFloat(r.value[1]) * 1000);
        }
      }

      for (const r of probeStatus.value) {
        const target = r.metric.target || r.metric.instance || 'unknown';
        const status = parseFloat(r.value[1]) === 1 ? 'online' : 'offline';
        const key = r.metric.instance || r.metric.target || '';
        const latencyMs = durations.get(key) || null;

        wanProbes.push({
          target: r.metric.device_name || r.metric.target || target,
          endpoint: target,
          type: r.metric.job?.includes('tcp') ? 'TCP' : r.metric.job?.includes('dns') ? 'DNS' : 'HTTPS',
          status,
          latencyMs: latencyMs !== null ? Math.round(latencyMs * 10) / 10 : null
        });
      }
    }

    // Edge / firewall (pfSense blackbox + UniFi gateways)
    const edge = [];
    const edgeDur = new Map();
    if (edgeDuration.status === 'fulfilled') {
      for (const r of edgeDuration.value) {
        const key = r.metric.instance || r.metric.device_name || '';
        edgeDur.set(key, Math.round(parseFloat(r.value[1]) * 1000 * 10) / 10);
      }
    }
    if (edgeStatus.status === 'fulfilled') {
      for (const r of edgeStatus.value) {
        const name = r.metric.device_name || config?.deviceName || 'edge';
        const key = r.metric.instance || name;
        const endpoint = r.metric.instance || key;
        edge.push({
          name,
          role: 'firewall',
          model: r.metric.model || 'pfSense / edge',
          status: parseFloat(r.value[1]) === 1 ? 'online' : 'offline',
          endpoint,
          latencyMs: edgeDur.get(key) ?? edgeDur.get(r.metric.instance) ?? null,
          source: 'blackbox',
          // Prefer dedicated mgmt URL; fall back to probe target if https
          mgmtUrl: mgmt.pfsense || (/^https?:\/\//i.test(String(endpoint)) ? String(endpoint) : null)
        });
      }
    }
    // UniFi gateway appliances (UDM etc.) if present
    if (gwStatus.status === 'fulfilled') {
      const cpuMap = new Map();
      const memMap = new Map();
      const upMap = new Map();
      if (gwCpu.status === 'fulfilled') {
        for (const r of gwCpu.value) cpuMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      if (gwMemory.status === 'fulfilled') {
        for (const r of gwMemory.value) memMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      if (gwUptime.status === 'fulfilled') {
        for (const r of gwUptime.value) upMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      for (const r of gwStatus.value) {
        const name = r.metric.device || 'gateway';
        edge.push({
          name,
          role: 'gateway',
          model: r.metric.model || 'UniFi Gateway',
          status: parseFloat(r.value[1]) === 1 ? 'online' : 'offline',
          mac: r.metric.mac || '',
          cpu: Math.round(cpuMap.get(name) || 0),
          memory: Math.round(memMap.get(name) || 0),
          uptime: formatUptime(upMap.get(name)),
          source: 'unifi',
          mgmtUrl: mgmt.unifi || null
        });
      }
    }

    // Build AP table
    const accessPoints = [];
    if (apStatus.status === 'fulfilled') {
      const clientsMap = new Map();
      const cpuMap = new Map();
      const memMap = new Map();
      const uptimeMap = new Map();

      if (apClients.status === 'fulfilled') {
        for (const r of apClients.value) clientsMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      if (apCpu.status === 'fulfilled') {
        for (const r of apCpu.value) cpuMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      if (apMemory.status === 'fulfilled') {
        for (const r of apMemory.value) memMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      if (apUptime.status === 'fulfilled') {
        for (const r of apUptime.value) uptimeMap.set(r.metric.device, parseFloat(r.value[1]));
      }

      for (const r of apStatus.value) {
        const name = r.metric.device || 'unknown';
        accessPoints.push({
          name,
          model: r.metric.model || 'unknown',
          status: parseFloat(r.value[1]) === 1 ? 'online' : 'offline',
          clients: clientsMap.get(name) || 0,
          cpu: Math.round(cpuMap.get(name) || 0),
          memory: Math.round(memMap.get(name) || 0),
          uptime: formatUptime(uptimeMap.get(name)),
          mac: r.metric.mac || '',
          // UniFi Network app has no stable per-AP public deep link; open controller
          mgmtUrl: mgmt.unifi || null
        });
      }
    }

    // Switches: UniFi first, then greenfield device_snmp, then pilot VM SNMP
    const switches = [];
    const seenSwitchNames = new Set();

    if (swUnifiStatus.status === 'fulfilled') {
      const cpuMap = new Map();
      const memMap = new Map();
      const upMap = new Map();
      if (swUnifiCpu.status === 'fulfilled') {
        for (const r of swUnifiCpu.value) cpuMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      if (swUnifiMemory.status === 'fulfilled') {
        for (const r of swUnifiMemory.value) memMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      if (swUnifiUptime.status === 'fulfilled') {
        for (const r of swUnifiUptime.value) upMap.set(r.metric.device, parseFloat(r.value[1]));
      }
      for (const r of swUnifiStatus.value) {
        const name = r.metric.device || 'switch';
        seenSwitchNames.add(name);
        switches.push({
          name,
          model: r.metric.model || 'UniFi Switch',
          status: parseFloat(r.value[1]) === 1 ? 'online' : 'offline',
          mac: r.metric.mac || '',
          cpu: Math.round(cpuMap.get(name) || 0),
          memory: Math.round(memMap.get(name) || 0),
          uptime: formatUptime(upMap.get(name)),
          source: 'unifi',
          mgmtUrl: mgmt.unifi || null
        });
      }
    }

    // Display labels only. Operator-supplied via site config (switches.models);
    // anything absent falls back to a label the metrics carry, then to a generic
    // string. Never a hardcoded per-device guess.
    const switchModels = getSwitchConfig(site).models;
    const modelFor = (name, metric, fallback) => (
      switchModels[name]
      || metric?.model
      || metric?.device_model
      || metric?.hardware
      || fallback
    );

    // Map device_name → scrape up (exporter path healthy) for greenfield
    const gfScrapeUp = new Map();
    if (gfSnmpUp.status === 'fulfilled') {
      for (const r of gfSnmpUp.value) {
        const name = r.metric.device_name || r.metric.instance || '';
        if (name) gfScrapeUp.set(name, parseFloat(r.value[1]) === 1);
      }
    }

    function pushSnmpSwitches(ifUpResult, ifTotalResult, errResult, source) {
      if (ifUpResult.status !== 'fulfilled') return;
      const totalMap = new Map();
      const errorMap = new Map();
      if (ifTotalResult.status === 'fulfilled') {
        for (const r of ifTotalResult.value) {
          totalMap.set(r.metric.device_name, parseInt(r.value[1], 10));
        }
      }
      if (errResult.status === 'fulfilled') {
        for (const r of errResult.value) {
          errorMap.set(r.metric.device_name, parseFloat(r.value[1]));
        }
      }
      for (const r of ifUpResult.value) {
        const name = r.metric.device_name;
        if (!name || seenSwitchNames.has(name)) continue;
        seenSwitchNames.add(name);
        const ifUp = parseInt(r.value[1], 10);
        const ifTotal = totalMap.get(name) || ifUp;
        const errorRate = errorMap.get(name) || 0;
        const scrapeOk = source === 'snmp-greenfield'
          ? (gfScrapeUp.has(name) ? gfScrapeUp.get(name) : true)
          : true;
        switches.push({
          name,
          model: modelFor(name, r.metric, 'Switch'),
          status: scrapeOk ? 'online' : 'offline',
          interfacesUp: ifUp,
          interfacesTotal: ifTotal,
          portsUp: ifUp,
          portsTotal: ifTotal,
          errorRate: Math.round(errorRate * 100) / 100,
          source
        });
      }
    }

    // Prefer greenfield Prometheus metrics when present
    pushSnmpSwitches(gfIfUp, gfIfTotal, gfErrors, 'snmp-greenfield');
    // Pilot dual-run residual (names already present are skipped)
    pushSnmpSwitches(switchIfUp, switchIfTotal, switchErrors, 'snmp');

    // Devices that only appear as scrape targets (exporter up, no ifOperStatus yet)
    if (gfSnmpUp.status === 'fulfilled') {
      for (const r of gfSnmpUp.value) {
        const name = r.metric.device_name;
        if (!name || seenSwitchNames.has(name)) continue;
        seenSwitchNames.add(name);
        switches.push({
          name,
          model: modelFor(name, r.metric, 'SNMP switch'),
          status: parseFloat(r.value[1]) === 1 ? 'online' : 'offline',
          interfacesUp: null,
          interfacesTotal: null,
          portsUp: null,
          portsTotal: null,
          errorRate: null,
          source: 'snmp-greenfield'
        });
      }
    }

    switches.sort((a, b) => String(a.name).localeCompare(String(b.name)));
    accessPoints.sort((a, b) => String(a.name).localeCompare(String(b.name)));

    const snmpSwitches = switches.filter((s) => s.source === 'snmp' || s.source === 'snmp-greenfield');

    res.json({
      site,
      wanProbes,
      edge,
      firewall: edge, // alias for older UI
      accessPoints,
      switches,
      summary: {
        switchCount: switches.length,
        snmpSwitchCount: snmpSwitches.length,
        snmpPortsUp: snmpSwitches.reduce((n, s) => n + (s.portsUp || 0), 0),
        snmpPortsTotal: snmpSwitches.reduce((n, s) => n + (s.portsTotal || 0), 0),
        apCount: accessPoints.length,
        edgeCount: edge.length
      },
      mgmt,
      sources: {
        unifi: accessPoints.length > 0 || switches.some((s) => s.source === 'unifi'),
        snmpSwitches: snmpSwitches.length > 0,
        snmpGreenfield: switches.some((s) => s.source === 'snmp-greenfield'),
        edgeProbe: edge.some((e) => e.source === 'blackbox')
      }
    });
  } catch (err) {
    console.error('Devices endpoint error:', err.message);
    res.status(502).json({ error: 'Failed to fetch device status', detail: err.message });
  }
});

module.exports = router;
