'use strict';

const express = require('express');
const router = express.Router();
const { queryAlertmanager } = require('../lib/queryEngine');

/**
 * GET /api/alerts?site=X
 * Firing + recently resolved alerts.
 */
router.get('/', async (req, res) => {
  const site = req.site;

  try {
    const allAlerts = await queryAlertmanager({ site });

    if (!Array.isArray(allAlerts)) {
      return res.json({ site, firing: [], resolved: [] });
    }

    const firing = [];
    const resolved = [];
    const now = new Date();
    const twentyFourHoursAgo = new Date(now - 24 * 60 * 60 * 1000);

    for (const alert of allAlerts) {
      // Filter by site label if present
      if (alert.labels?.site && alert.labels.site !== site) continue;

      const startsAt = new Date(alert.startsAt);
      const endsAt = alert.endsAt ? new Date(alert.endsAt) : null;
      const isActive = alert.status?.state === 'active' || alert.status?.state === 'firing';

      const entry = {
        name: alert.labels?.alertname || 'Unknown',
        severity: alert.labels?.severity || 'unknown',
        category: categorizeAlert(alert.labels?.alertname),
        startsAt: alert.startsAt,
        labels: alert.labels || {},
        summary: alert.annotations?.summary || alert.annotations?.description || ''
      };

      if (isActive) {
        const durationMs = now - startsAt;
        entry.duration = formatDuration(durationMs);
        firing.push(entry);
      } else if (endsAt && endsAt > twentyFourHoursAgo) {
        entry.endsAt = alert.endsAt;
        entry.duration = formatDuration(endsAt - startsAt);
        resolved.push(entry);
      }
    }

    // Sort: critical first, then by start time (newest first)
    firing.sort((a, b) => {
      if (a.severity === 'critical' && b.severity !== 'critical') return -1;
      if (b.severity === 'critical' && a.severity !== 'critical') return 1;
      return new Date(b.startsAt) - new Date(a.startsAt);
    });

    resolved.sort((a, b) => new Date(b.endsAt) - new Date(a.endsAt));

    res.json({ site, firing, resolved });
  } catch (err) {
    console.error('Alerts endpoint error:', err.message);
    res.status(502).json({ error: 'Failed to fetch alerts', detail: err.message });
  }
});

function categorizeAlert(name) {
  if (!name) return 'Other';
  if (name.startsWith('Internet') || name.startsWith('Wan') || name.startsWith('Edge')) return 'WAN';
  if (name.startsWith('Wifi') || name.startsWith('AccessPoint')) return 'Wi-Fi';
  if (name.startsWith('Speedtest')) return 'Bandwidth';
  if (name.startsWith('Monitoring') || name.startsWith('UniFi')) return 'Monitoring';
  return 'Other';
}

function formatDuration(ms) {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

module.exports = router;
