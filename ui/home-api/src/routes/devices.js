'use strict';

const express = require('express');
const router = express.Router();
const { instantQuery } = require('../lib/queryEngine');
const { vmInstantQuery } = require('../lib/queryEngine');
const { formatUptime } = require('../lib/formatters');
const { getSiteConfig } = require('../lib/config');

/**
 * GET /api/devices?site=X
 * Equipment status table (edge router + switches + APs + WAN probes).
 */
router.get('/', async (req, res) => {
  const site = req.site;
  const config = getSiteConfig(site);

  try {
    const [
      probeStatus, probeDuration,
      apStatus, apClients, apCpu, apMemory, apUptime,
      switchIfUp, switchIfTotal, switchErrors
    ] = await Promise.allSettled([
      instantQuery(`probe_success{job=~"blackbox_wan_tcp|blackbox_wan_http|blackbox_wan_dns|blackbox_http"}`),
      instantQuery(`probe_duration_seconds{job=~"blackbox_wan_tcp|blackbox_wan_http|blackbox_wan_dns|blackbox_http"}`),
      instantQuery(`unifi_device_up{role="ap", site="${site}"}`),
      instantQuery(`unifi_ap_clients{site="${site}"}`),
      instantQuery(`unifi_device_cpu_pct{role="ap", site="${site}"}`),
      instantQuery(`unifi_device_memory_pct{role="ap", site="${site}"}`),
      instantQuery(`unifi_device_uptime_seconds{role="ap", site="${site}"}`),
      // Switch interface counts (from VictoriaMetrics SNMP data)
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
          uptime: formatUptime(uptimeMap.get(name))
        });
      }
    }

    // Build switches table
    const switches = [];
    const switchModels = {
      'HomeSwitch01': 'Cisco WS-C3850-48P',
      'HomeSwitch02': 'Cisco WS-C3850-48P',
      'HomeSwitch04': 'Cisco WS-C3650-48P'
    };

    if (switchIfUp.status === 'fulfilled') {
      const totalMap = new Map();
      const errorMap = new Map();

      if (switchIfTotal.status === 'fulfilled') {
        for (const r of switchIfTotal.value) {
          totalMap.set(r.metric.device_name, parseInt(r.value[1]));
        }
      }
      if (switchErrors.status === 'fulfilled') {
        for (const r of switchErrors.value) {
          errorMap.set(r.metric.device_name, parseFloat(r.value[1]));
        }
      }

      for (const r of switchIfUp.value) {
        const name = r.metric.device_name;
        const ifUp = parseInt(r.value[1]);
        const ifTotal = totalMap.get(name) || ifUp;
        const errorRate = errorMap.get(name) || 0;

        switches.push({
          name,
          model: switchModels[name] || 'Cisco Switch',
          status: 'online', // If we're getting SNMP data, it's responding
          interfacesUp: ifUp,
          interfacesTotal: ifTotal,
          errorRate: Math.round(errorRate * 100) / 100
        });
      }
    }

    // Sort switches by name
    switches.sort((a, b) => a.name.localeCompare(b.name));

    res.json({ site, wanProbes, accessPoints, switches });
  } catch (err) {
    console.error('Devices endpoint error:', err.message);
    res.status(502).json({ error: 'Failed to fetch device status', detail: err.message });
  }
});

module.exports = router;
