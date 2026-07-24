'use strict';

const express = require('express');
const router = express.Router();
const { instantQuery } = require('../lib/queryEngine');
const { vmInstantQuery } = require('../lib/queryEngine');
const { formatUptime } = require('../lib/formatters');
const { getSiteConfig } = require('../lib/config');

/**
 * GET /api/devices?site=X
 * Equipment status: WAN probes, edge/firewall, UniFi APs/switches/gateways,
 * optional Cisco switches from VictoriaMetrics SNMP (pilot).
 */
router.get('/', async (req, res) => {
  const site = req.site;
  const config = getSiteConfig(site);

  try {
    const [
      probeStatus, probeDuration,
      edgeStatus, edgeDuration,
      apStatus, apClients, apCpu, apMemory, apUptime,
      gwStatus, gwCpu, gwMemory, gwUptime,
      swUnifiStatus, swUnifiCpu, swUnifiMemory, swUnifiUptime,
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
      // Cisco switches from pilot VictoriaMetrics SNMP (optional; fails soft on Docker)
      vmInstantQuery(`count by (device_name) (interface_status{device_name=~"HomeSwitch.*"} == 1)`),
      vmInstantQuery(`count by (device_name) (interface_status{device_name=~"HomeSwitch.*"})`),
      vmInstantQuery(`sum by (device_name) (rate(interface_errors_in_total{device_name=~"HomeSwitch.*"}[5m]) + rate(interface_errors_out_total{device_name=~"HomeSwitch.*"}[5m]))`)
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
        edge.push({
          name,
          role: 'firewall',
          model: r.metric.model || 'pfSense / edge',
          status: parseFloat(r.value[1]) === 1 ? 'online' : 'offline',
          endpoint: r.metric.instance || key,
          latencyMs: edgeDur.get(key) ?? edgeDur.get(r.metric.instance) ?? null,
          source: 'blackbox'
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
          source: 'unifi'
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
          mac: r.metric.mac || ''
        });
      }
    }

    // Switches: UniFi first, then Cisco SNMP via VictoriaMetrics (pilot)
    const switches = [];

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
        switches.push({
          name,
          model: r.metric.model || 'UniFi Switch',
          status: parseFloat(r.value[1]) === 1 ? 'online' : 'offline',
          mac: r.metric.mac || '',
          cpu: Math.round(cpuMap.get(name) || 0),
          memory: Math.round(memMap.get(name) || 0),
          uptime: formatUptime(upMap.get(name)),
          source: 'unifi'
        });
      }
    }

    const switchModels = {
      HomeSwitch01: 'Cisco WS-C3850-48P',
      HomeSwitch02: 'Cisco WS-C3850-48P',
      HomeSwitch04: 'Cisco WS-C3650-48P'
    };

    if (switchIfUp.status === 'fulfilled') {
      const totalMap = new Map();
      const errorMap = new Map();

      if (switchIfTotal.status === 'fulfilled') {
        for (const r of switchIfTotal.value) {
          totalMap.set(r.metric.device_name, parseInt(r.value[1], 10));
        }
      }
      if (switchErrors.status === 'fulfilled') {
        for (const r of switchErrors.value) {
          errorMap.set(r.metric.device_name, parseFloat(r.value[1]));
        }
      }

      for (const r of switchIfUp.value) {
        const name = r.metric.device_name;
        const ifUp = parseInt(r.value[1], 10);
        const ifTotal = totalMap.get(name) || ifUp;
        const errorRate = errorMap.get(name) || 0;

        switches.push({
          name,
          model: switchModels[name] || 'Cisco Switch',
          status: 'online',
          interfacesUp: ifUp,
          interfacesTotal: ifTotal,
          portsUp: ifUp,
          portsTotal: ifTotal,
          errorRate: Math.round(errorRate * 100) / 100,
          source: 'snmp'
        });
      }
    }

    switches.sort((a, b) => String(a.name).localeCompare(String(b.name)));
    accessPoints.sort((a, b) => String(a.name).localeCompare(String(b.name)));

    res.json({
      site,
      wanProbes,
      edge,
      firewall: edge, // alias for older UI
      accessPoints,
      switches,
      sources: {
        unifi: accessPoints.length > 0 || switches.some((s) => s.source === 'unifi'),
        snmpSwitches: switches.some((s) => s.source === 'snmp'),
        edgeProbe: edge.some((e) => e.source === 'blackbox')
      }
    });
  } catch (err) {
    console.error('Devices endpoint error:', err.message);
    res.status(502).json({ error: 'Failed to fetch device status', detail: err.message });
  }
});

module.exports = router;
