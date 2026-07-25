'use strict';

const express = require('express');
const router = express.Router();
const { instantQuery, extractScalar } = require('../lib/queryEngine');
const { queryAlertmanager } = require('../lib/queryEngine');
const { getSiteConfig, getPrimaryProvider, getThresholdStatus } = require('../lib/config');

/**
 * GET /api/health?site=X
 * Returns dashboard KPIs in a single call.
 * Throughput KPI now shows speedtest aggregate (line capacity), not live utilization.
 */
router.get('/', async (req, res) => {
  const site = req.site;
  const config = getSiteConfig(site);

  if (!config) {
    return res.status(404).json({ error: `Site '${site}' not configured` });
  }

  try {
    // Parallel queries for all KPIs
    const [healthResult, latencyResult, lossResult, speedDl, speedUl, alerts, uptime30d, lastIncident,
      snmpDevices, snmpIfUp, snmpIfTotal] = await Promise.allSettled([
      instantQuery(`convergence:health_score{site="${site}"}`),
      instantQuery(`convergence:wan_latency_ms:avg{site="${site}"}`),
      instantQuery(`100 * convergence:wan_loss_ratio:5m{site="${site}"}`),
      // Speedtest aggregate: average across all servers for the most recent test
      instantQuery(`avg(speedtest_download_bits_per_second{site="${site}"})`),
      instantQuery(`avg(speedtest_upload_bits_per_second{site="${site}"})`),
      queryAlertmanager({ site }),
      // 30-day uptime: % of time health score was >= 70 (not degraded/unhealthy)
      instantQuery(`avg_over_time((convergence:health_score{site="${site}"} >= bool 70)[30d:5m]) * 100`),
      // Last incident: most recent alert start time (from Alertmanager resolved alerts)
      queryAlertmanager({}),
      // Optional Overview KPI — greenfield device_snmp (Phase 8 T087)
      instantQuery(`count(count by (device_name) (up{job="device_snmp"} == 1))`),
      instantQuery(`count(ifOperStatus{job="device_snmp"} == 1)`),
      instantQuery(`count(ifOperStatus{job="device_snmp"})`)
    ]);

    const healthScore = healthResult.status === 'fulfilled' ? extractScalar(healthResult.value) : null;
    const latency = latencyResult.status === 'fulfilled' ? extractScalar(latencyResult.value) : null;
    const loss = lossResult.status === 'fulfilled' ? extractScalar(lossResult.value) : null;
    const avgDownBps = speedDl.status === 'fulfilled' ? extractScalar(speedDl.value) : null;
    const avgUpBps = speedUl.status === 'fulfilled' ? extractScalar(speedUl.value) : null;
    const uptimePct = uptime30d.status === 'fulfilled' ? extractScalar(uptime30d.value) : null;
    const snmpDeviceCount = snmpDevices.status === 'fulfilled' ? extractScalar(snmpDevices.value) : null;
    const snmpPortsUp = snmpIfUp.status === 'fulfilled' ? extractScalar(snmpIfUp.value) : null;
    const snmpPortsTotal = snmpIfTotal.status === 'fulfilled' ? extractScalar(snmpIfTotal.value) : null;

    // Calculate time since last incident from Alertmanager resolved alerts
    let timeSinceIncident = null;
    if (lastIncident.status === 'fulfilled' && Array.isArray(lastIncident.value)) {
      const resolved = lastIncident.value
        .filter(a => a.status?.state !== 'active' && a.labels?.site === site && a.endsAt)
        .map(a => new Date(a.endsAt))
        .sort((a, b) => b - a);
      if (resolved.length > 0) {
        const msSince = Date.now() - resolved[0].getTime();
        const daysSince = Math.floor(msSince / 86400000);
        const hoursSince = Math.floor(msSince / 3600000);
        timeSinceIncident = daysSince > 0 ? `${daysSince}d` : `${hoursSince}h`;
      }
    }

    // Count alerts by severity
    let alertCount = { firing: 0, warning: 0, critical: 0 };
    if (alerts.status === 'fulfilled' && Array.isArray(alerts.value)) {
      const firingAlerts = alerts.value.filter(a => a.status && a.status.state === 'active');
      alertCount.firing = firingAlerts.length;
      alertCount.warning = firingAlerts.filter(a => a.labels?.severity === 'warning').length;
      alertCount.critical = firingAlerts.filter(a => a.labels?.severity === 'critical').length;
    }

    // Determine health status
    let healthStatus = 'unknown';
    if (healthScore !== null) {
      if (healthScore >= 90) healthStatus = 'healthy';
      else if (healthScore >= 70) healthStatus = 'degraded';
      else healthStatus = 'unhealthy';
    }

    const thresholds = config.thresholds || {};
    const provider = getPrimaryProvider(site);
    const slaTarget = provider ? provider.speedtestTarget : 1e9;

    // Speedtest status based on % of SLA
    let speedStatus = 'unknown';
    if (avgDownBps !== null) {
      const pct = avgDownBps / slaTarget;
      if (pct >= 0.9) speedStatus = 'healthy';
      else if (pct >= 0.7) speedStatus = 'degraded';
      else speedStatus = 'unhealthy';
    }

    // ISP provider name from config
    const ispName = provider ? provider.name : 'ISP';

    res.json({
      site,
      timestamp: new Date().toISOString(),
      healthScore: {
        value: healthScore !== null ? Math.round(healthScore * 10) / 10 : null,
        status: healthStatus
      },
      uptime: {
        pct30d: uptimePct !== null ? Math.round(uptimePct * 100) / 100 : null,
        timeSinceIncident
      },
      wanLatency: {
        value: latency !== null ? Math.round(latency * 10) / 10 : null,
        unit: 'ms',
        status: latency !== null ? getThresholdStatus(latency, thresholds.latency) : 'unknown'
      },
      wanLoss: {
        value: loss !== null ? Math.round(loss * 100) / 100 : null,
        unit: '%',
        status: loss !== null ? getThresholdStatus(loss, thresholds.loss) : 'unknown'
      },
      speedtest: {
        download: avgDownBps !== null ? Math.round(avgDownBps / 1e6) : null,
        upload: avgUpBps !== null ? Math.round(avgUpBps / 1e6) : null,
        unit: 'Mbps',
        status: speedStatus,
        ispName
      },
      alertCount,
      // Present only when device_snmp has series (optional Overview KPI)
      devices: snmpDeviceCount != null && snmpDeviceCount > 0
        ? {
            snmpSwitches: Math.round(snmpDeviceCount),
            portsUp: snmpPortsUp != null ? Math.round(snmpPortsUp) : null,
            portsTotal: snmpPortsTotal != null ? Math.round(snmpPortsTotal) : null,
            status: snmpPortsTotal != null && snmpPortsUp != null && snmpPortsTotal > 0
              ? (snmpPortsUp / snmpPortsTotal >= 0.9 ? 'healthy'
                : snmpPortsUp / snmpPortsTotal >= 0.5 ? 'degraded' : 'unhealthy')
              : 'healthy'
          }
        : null
    });
  } catch (err) {
    console.error('Health endpoint error:', err.message);
    res.status(502).json({ error: 'Failed to fetch health data', detail: err.message });
  }
});

module.exports = router;
