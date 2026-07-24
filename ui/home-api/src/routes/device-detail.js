'use strict';

const express = require('express');
const router = express.Router();
const { vmInstantQuery, vmRangeQuery } = require('../lib/queryEngine');
const { extractTimeSeries, instantQuery } = require('../lib/queryEngine');
const { NAUTOBOT_URL, NAUTOBOT_TOKEN } = require('../lib/config');

/**
 * Fetch interface descriptions and cable peers from Nautobot GraphQL.
 */
async function fetchNautobotInterfaces(deviceName) {
  if (!NAUTOBOT_URL || !NAUTOBOT_TOKEN) return new Map();

  const query = `{ devices(name:"${deviceName}") { name interfaces { name description connected_interface { name device { name } } } } }`;

  try {
    const res = await fetch(`${NAUTOBOT_URL}/api/graphql/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Token ${NAUTOBOT_TOKEN}`
      },
      body: JSON.stringify({ query }),
      signal: AbortSignal.timeout(10000)
    });

    if (!res.ok) return new Map();
    const data = await res.json();
    const devices = data?.data?.devices || [];
    if (devices.length === 0) return new Map();

    const map = new Map();
    for (const iface of devices[0].interfaces || []) {
      const conn = iface.connected_interface;
      map.set(iface.name, {
        description: iface.description || '',
        cablePeer: conn ? `${conn.device?.name || ''}:${conn.name || ''}` : ''
      });
    }
    return map;
  } catch (err) {
    console.error('Nautobot GraphQL error:', err.message);
    return new Map();
  }
}

/**
 * GET /api/device/:name?site=X
 * Returns detailed interface-level data for a specific device.
 * For switches/pfSense: SNMP data from VictoriaMetrics.
 * For APs: UniFi exporter metrics from Prometheus.
 */
router.get('/:name', async (req, res) => {
  const site = req.site;
  const deviceName = req.params.name;

  // Check if this is a UniFi AP (name contains "U6" or "UAP" or similar)
  const isAP = deviceName.toLowerCase().includes('u6') || deviceName.toLowerCase().includes('uap') || deviceName.toLowerCase().includes('pro');

  // WAN probes is not a real device
  if (deviceName === 'wan-probes') {
    return handleWanProbesDetail(req, res, site);
  }

  if (isAP) {
    return handleAPDetail(req, res, site, deviceName);
  }

  // Standard SNMP device (switches, pfSense)
  try {
    const [ifStatus, ifOctetsIn, ifOctetsOut, ifErrorsIn, ifErrorsOut, nautobotData] = await Promise.allSettled([
      vmInstantQuery(`interface_status{device_name="${deviceName}"}`),
      vmInstantQuery(`rate(interface_octets_in_bytes_total{device_name="${deviceName}"}[5m]) * 8`),
      vmInstantQuery(`rate(interface_octets_out_bytes_total{device_name="${deviceName}"}[5m]) * 8`),
      vmInstantQuery(`rate(interface_errors_in_total{device_name="${deviceName}"}[5m])`),
      vmInstantQuery(`rate(interface_errors_out_total{device_name="${deviceName}"}[5m])`),
      fetchNautobotInterfaces(deviceName)
    ]);

    const nautobotMap = nautobotData.status === 'fulfilled' ? nautobotData.value : new Map();

    const interfaces = [];

    if (ifStatus.status === 'fulfilled') {
      // Build maps for throughput and errors
      const inBpsMap = new Map();
      const outBpsMap = new Map();
      const errInMap = new Map();
      const errOutMap = new Map();

      if (ifOctetsIn.status === 'fulfilled') {
        for (const r of ifOctetsIn.value) {
          inBpsMap.set(r.metric.interface_name, parseFloat(r.value[1]));
        }
      }
      if (ifOctetsOut.status === 'fulfilled') {
        for (const r of ifOctetsOut.value) {
          outBpsMap.set(r.metric.interface_name, parseFloat(r.value[1]));
        }
      }
      if (ifErrorsIn.status === 'fulfilled') {
        for (const r of ifErrorsIn.value) {
          errInMap.set(r.metric.interface_name, parseFloat(r.value[1]));
        }
      }
      if (ifErrorsOut.status === 'fulfilled') {
        for (const r of ifErrorsOut.value) {
          errOutMap.set(r.metric.interface_name, parseFloat(r.value[1]));
        }
      }

      for (const r of ifStatus.value) {
        const ifName = r.metric.interface_name;
        const statusVal = parseInt(r.value[1]);
        // ifOperStatus: 1=up, 2=down, 3=testing
        const status = statusVal === 1 ? 'up' : statusVal === 2 ? 'down' : 'other';
        const inBps = inBpsMap.get(ifName) || 0;
        const outBps = outBpsMap.get(ifName) || 0;
        const errIn = errInMap.get(ifName) || 0;
        const errOut = errOutMap.get(ifName) || 0;

        interfaces.push({
          name: ifName,
          status,
          description: (nautobotMap.get(ifName) || {}).description || '',
          cablePeer: (nautobotMap.get(ifName) || {}).cablePeer || '',
          inBps: Math.round(inBps),
          outBps: Math.round(outBps),
          errorsIn: Math.round(errIn * 1000) / 1000,
          errorsOut: Math.round(errOut * 1000) / 1000
        });
      }
    }

    // Sort: up interfaces first, then by name
    interfaces.sort((a, b) => {
      if (a.status === 'up' && b.status !== 'up') return -1;
      if (b.status === 'up' && a.status !== 'up') return 1;
      return a.name.localeCompare(b.name);
    });

    // Summary stats
    const summary = {
      totalInterfaces: interfaces.length,
      up: interfaces.filter(i => i.status === 'up').length,
      down: interfaces.filter(i => i.status === 'down').length,
      totalInBps: interfaces.reduce((sum, i) => sum + i.inBps, 0),
      totalOutBps: interfaces.reduce((sum, i) => sum + i.outBps, 0),
      totalErrors: interfaces.reduce((sum, i) => sum + i.errorsIn + i.errorsOut, 0)
    };

    res.json({ site, device: deviceName, summary, interfaces });
  } catch (err) {
    console.error('Device detail error:', err.message);
    res.status(502).json({ error: 'Failed to fetch device details', detail: err.message });
  }
});

/**
 * GET /api/device/:name/interface/:ifName?site=X&range=1h
 * Returns time-series data for a specific interface (for charts).
 */
router.get('/:name/interface/:ifName', async (req, res) => {
  const site = req.site;
  const deviceName = req.params.name;
  const ifName = req.params.ifName;
  const range = req.query.range || '1h';
  const step = req.query.step || '5m';

  try {
    const [inResult, outResult] = await Promise.allSettled([
      vmRangeQuery(`rate(interface_octets_in_bytes_total{device_name="${deviceName}", interface_name="${ifName}"}[5m]) * 8`, range, step),
      vmRangeQuery(`rate(interface_octets_out_bytes_total{device_name="${deviceName}", interface_name="${ifName}"}[5m]) * 8`, range, step)
    ]);

    const inSeries = inResult.status === 'fulfilled' ? extractTimeSeries(inResult.value) : { timestamps: [], values: [] };
    const outSeries = outResult.status === 'fulfilled' ? extractTimeSeries(outResult.value) : { timestamps: [], values: [] };

    res.json({ site, device: deviceName, interface: ifName, range, inBps: inSeries, outBps: outSeries });
  } catch (err) {
    console.error('Interface detail error:', err.message);
    res.status(502).json({ error: 'Failed to fetch interface data', detail: err.message });
  }
});

/**
 * Handle WAN probes detail - shows all probe targets with status and latency.
 */
async function handleWanProbesDetail(req, res, site) {
  try {
    const [probeStatus, probeDuration] = await Promise.allSettled([
      instantQuery(`probe_success{job=~"blackbox_wan_tcp|blackbox_wan_http|blackbox_wan_dns|blackbox_http"}`),
      instantQuery(`probe_duration_seconds{job=~"blackbox_wan_tcp|blackbox_wan_http|blackbox_wan_dns|blackbox_http"}`)
    ]);

    const probes = [];
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
        const success = parseFloat(r.value[1]) === 1;
        const key = r.metric.instance || r.metric.target || '';
        const latencyMs = durations.get(key) || null;
        const job = r.metric.job || '';

        let probeType = 'TCP';
        if (job.includes('http')) probeType = 'HTTPS';
        else if (job.includes('dns')) probeType = 'DNS';

        probes.push({
          name: r.metric.device_name || r.metric.target || target,
          target,
          type: probeType,
          status: success ? 'up' : 'down',
          latencyMs: latencyMs !== null ? Math.round(latencyMs * 10) / 10 : null
        });
      }
    }

    // Sort: online first, then by latency
    probes.sort((a, b) => {
      if (a.status === 'up' && b.status !== 'up') return -1;
      if (b.status === 'up' && a.status !== 'up') return 1;
      return (a.latencyMs || 999) - (b.latencyMs || 999);
    });

    const online = probes.filter(p => p.status === 'up').length;
    const avgLatency = probes.filter(p => p.latencyMs).reduce((sum, p) => sum + p.latencyMs, 0) / (probes.filter(p => p.latencyMs).length || 1);

    res.json({
      site,
      device: 'wan-probes',
      deviceType: 'probes',
      summary: {
        totalInterfaces: probes.length,
        up: online,
        down: probes.length - online,
        totalInBps: 0,
        totalOutBps: 0,
        totalErrors: probes.length - online,
        avgLatencyMs: Math.round(avgLatency * 10) / 10
      },
      interfaces: probes.map(p => ({
        name: p.name,
        status: p.status,
        description: p.target + ' (' + p.type + ')',
        cablePeer: '',
        inBps: 0,
        outBps: p.latencyMs || 0, // repurpose outBps to show latency in the table
        errorsIn: p.status === 'down' ? 1 : 0,
        errorsOut: 0,
        latencyMs: p.latencyMs
      }))
    });
  } catch (err) {
    console.error('WAN probes detail error:', err.message);
    res.status(502).json({ error: 'Failed to fetch probe data', detail: err.message });
  }
}

/**
 * Handle AP device detail - uses UniFi exporter metrics from Prometheus.
 */
async function handleAPDetail(req, res, site, deviceName) {
  try {
    const [status, cpu, memory, uptime, clients, txRetries, uplinkRx, uplinkTx] = await Promise.allSettled([
      instantQuery(`unifi_device_up{device="${deviceName}", site="${site}"}`),
      instantQuery(`unifi_device_cpu_pct{device="${deviceName}", site="${site}"}`),
      instantQuery(`unifi_device_memory_pct{device="${deviceName}", site="${site}"}`),
      instantQuery(`unifi_device_uptime_seconds{device="${deviceName}", site="${site}"}`),
      instantQuery(`unifi_ap_clients{device="${deviceName}", site="${site}"}`),
      instantQuery(`unifi_radio_tx_retries_pct{device="${deviceName}", site="${site}"}`),
      instantQuery(`unifi_device_uplink_rx_bps{device="${deviceName}", site="${site}"}`),
      instantQuery(`unifi_device_uplink_tx_bps{device="${deviceName}", site="${site}"}`)
    ]);

    const { extractScalar } = require('../lib/queryEngine');
    const { formatUptime } = require('../lib/formatters');

    const isUp = status.status === 'fulfilled' && status.value.length > 0 ? parseFloat(status.value[0].value[1]) === 1 : null;
    const cpuVal = cpu.status === 'fulfilled' ? extractScalar(cpu.value) : null;
    const memVal = memory.status === 'fulfilled' ? extractScalar(memory.value) : null;
    const uptimeVal = uptime.status === 'fulfilled' ? extractScalar(uptime.value) : null;
    const clientCount = clients.status === 'fulfilled' ? extractScalar(clients.value) : null;
    const rxBps = uplinkRx.status === 'fulfilled' ? extractScalar(uplinkRx.value) : null;
    const txBps = uplinkTx.status === 'fulfilled' ? extractScalar(uplinkTx.value) : null;

    // TX retries per band
    const retries = [];
    if (txRetries.status === 'fulfilled') {
      for (const r of txRetries.value) {
        retries.push({
          band: r.metric.band || 'unknown',
          value: parseFloat(r.value[1])
        });
      }
    }

    const summary = {
      status: isUp === true ? 'online' : isUp === false ? 'offline' : 'unknown',
      cpu: cpuVal !== null ? Math.round(cpuVal) : null,
      memory: memVal !== null ? Math.round(memVal) : null,
      uptime: uptimeVal !== null ? formatUptime(uptimeVal) : null,
      clients: clientCount !== null ? Math.round(clientCount) : null,
      uplinkInBps: rxBps !== null ? Math.round(rxBps) : null,
      uplinkOutBps: txBps !== null ? Math.round(txBps) : null
    };

    // Build a pseudo-interface list showing radios and uplink
    const interfaces = [];

    for (const r of retries) {
      interfaces.push({
        name: `Radio ${r.band}`,
        status: 'up',
        description: `Wi-Fi ${r.band} radio`,
        cablePeer: '',
        inBps: 0,
        outBps: 0,
        errorsIn: r.value,
        errorsOut: 0
      });
    }

    interfaces.push({
      name: 'Uplink',
      status: isUp ? 'up' : 'down',
      description: 'Wired uplink to switch',
      cablePeer: '',
      inBps: rxBps || 0,
      outBps: txBps || 0,
      errorsIn: 0,
      errorsOut: 0
    });

    res.json({
      site,
      device: deviceName,
      deviceType: 'ap',
      summary: {
        ...summary,
        totalInterfaces: interfaces.length,
        up: interfaces.filter(i => i.status === 'up').length,
        down: interfaces.filter(i => i.status !== 'up').length,
        totalInBps: rxBps || 0,
        totalOutBps: txBps || 0,
        totalErrors: retries.reduce((sum, r) => sum + r.value, 0)
      },
      interfaces
    });
  } catch (err) {
    console.error('AP detail error:', err.message);
    res.status(502).json({ error: 'Failed to fetch AP details', detail: err.message });
  }
}

module.exports = router;
