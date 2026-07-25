'use strict';

const express = require('express');
const router = express.Router();
const { rangeQuery, extractLabeledSeries } = require('../lib/queryEngine');
const { getSiteConfig, getPrimaryProvider, getThresholdStatus } = require('../lib/config');

/**
 * GET /api/speedtest?site=X&range=24h
 * Speedtest results with SLA comparison.
 */
router.get('/', async (req, res) => {
  const site = req.site;
  const range = req.query.range || '24h';
  const config = getSiteConfig(site);
  const provider = getPrimaryProvider(site);

  if (!config) {
    return res.status(404).json({ error: `Site '${site}' not configured` });
  }

  const slaTarget = provider ? provider.speedtestTarget : 1e9;
  const thresholds = config.thresholds?.speedtest || { green: slaTarget * 0.9, yellow: slaTarget * 0.7 };

  try {
    const [dl, ul, lat, jitter, loss, up] = await Promise.allSettled([
      rangeQuery(`speedtest_download_bits_per_second{site="${site}"}`, range, '1h'),
      rangeQuery(`speedtest_upload_bits_per_second{site="${site}"}`, range, '1h'),
      rangeQuery(`speedtest_ping_latency_ms{site="${site}"}`, range, '1h'),
      rangeQuery(`speedtest_ping_jitter_ms{site="${site}"}`, range, '1h'),
      rangeQuery(`speedtest_packet_loss_pct{site="${site}"}`, range, '1h'),
      rangeQuery(`speedtest_up{site="${site}"}`, range, '1h')
    ]);

    // Build per-server latest results
    const results = [];
    if (dl.status === 'fulfilled' && dl.value.length > 0) {
      for (const r of dl.value) {
        const server = r.metric.server || 'unknown';
        const values = r.values || [];
        if (values.length === 0) continue;

        // Get latest value
        const lastDl = parseFloat(values[values.length - 1][1]);
        const timestamp = new Date(values[values.length - 1][0] * 1000).toISOString();

        // Find matching upload for this server
        let lastUl = null;
        if (ul.status === 'fulfilled') {
          const ulSeries = ul.value.find(u => u.metric.server === server);
          if (ulSeries && ulSeries.values.length > 0) {
            lastUl = parseFloat(ulSeries.values[ulSeries.values.length - 1][1]);
          }
        }

        // Find matching latency
        let lastLat = null;
        if (lat.status === 'fulfilled') {
          const latSeries = lat.value.find(l => l.metric.server === server);
          if (latSeries && latSeries.values.length > 0) {
            lastLat = parseFloat(latSeries.values[latSeries.values.length - 1][1]);
          }
        }

        // Find matching jitter
        let lastJitter = null;
        if (jitter.status === 'fulfilled') {
          const jSeries = jitter.value.find(j => j.metric.server === server);
          if (jSeries && jSeries.values.length > 0) {
            lastJitter = parseFloat(jSeries.values[jSeries.values.length - 1][1]);
          }
        }

        // Find matching packet loss
        let lastLoss = null;
        if (loss.status === 'fulfilled') {
          const lossSeries = loss.value.find(l => l.metric.server === server);
          if (lossSeries && lossSeries.values.length > 0) {
            lastLoss = parseFloat(lossSeries.values[lossSeries.values.length - 1][1]);
          }
        }

        results.push({
          timestamp,
          server,
          provider: r.metric.provider || 'unknown',
          location: r.metric.location || 'unknown',
          download: {
            bps: lastDl,
            pctOfSla: Math.round((lastDl / slaTarget) * 1000) / 10,
            status: getThresholdStatus(lastDl, thresholds, false)
          },
          upload: lastUl !== null ? {
            bps: lastUl,
            pctOfSla: Math.round((lastUl / slaTarget) * 1000) / 10,
            status: getThresholdStatus(lastUl, thresholds, false)
          } : null,
          latencyMs: lastLat !== null ? Math.round(lastLat * 10) / 10 : null,
          jitterMs: lastJitter !== null ? Math.round(lastJitter * 10) / 10 : null,
          packetLossPct: lastLoss !== null ? Math.round(lastLoss * 100) / 100 : null
        });
      }
    }

    // Time series for charts (keyed by server)
    const timeSeries = {
      download: dl.status === 'fulfilled' ? extractLabeledSeries(dl.value, 'server') : {},
      upload: ul.status === 'fulfilled' ? extractLabeledSeries(ul.value, 'server') : {}
    };

    res.json({ site, slaTarget, results, timeSeries });
  } catch (err) {
    console.error('Speedtest endpoint error:', err.message);
    res.status(502).json({ error: 'Failed to fetch speedtest data', detail: err.message });
  }
});

module.exports = router;
