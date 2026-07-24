'use strict';

const express = require('express');
const router = express.Router();
const { rangeQuery, extractTimeSeries } = require('../lib/queryEngine');
const { vmRangeQuery } = require('../lib/queryEngine');
const { getSiteConfig, getPrimaryProvider } = require('../lib/config');

/**
 * GET /api/metrics/wan?site=X&range=1h&step=30s
 * WAN latency + loss time-series for charts.
 */
router.get('/wan', async (req, res) => {
  const site = req.site;
  const range = req.query.range || '1h';
  const step = req.query.step || '30s';

  try {
    const [latencyResult, lossResult] = await Promise.allSettled([
      rangeQuery(`guardian:wan_latency_ms:avg{site="${site}"}`, range, step),
      rangeQuery(`100 * guardian:wan_loss_ratio:5m{site="${site}"}`, range, step)
    ]);

    const latency = latencyResult.status === 'fulfilled' ? extractTimeSeries(latencyResult.value) : { timestamps: [], values: [] };
    const loss = lossResult.status === 'fulfilled' ? extractTimeSeries(lossResult.value) : { timestamps: [], values: [] };

    res.json({ site, range, step, latency, loss });
  } catch (err) {
    console.error('WAN metrics error:', err.message);
    res.status(502).json({ error: 'Failed to fetch WAN metrics', detail: err.message });
  }
});

/**
 * GET /api/metrics/throughput?site=X&range=24h&step=5m
 * WAN throughput time-series (download + upload in bps).
 */
router.get('/throughput', async (req, res) => {
  const site = req.site;
  const range = req.query.range || '24h';
  const step = req.query.step || '5m';
  const config = getSiteConfig(site);
  const provider = getPrimaryProvider(site);

  if (!config || !provider) {
    return res.status(404).json({ error: `Site '${site}' not configured` });
  }

  const wanIf = provider.wanInterface;
  const device = config.deviceName;

  try {
    const [dlResult, ulResult] = await Promise.allSettled([
      vmRangeQuery(`rate(interface_octets_in_bytes_total{device_name="${device}", interface_name="${wanIf}"}[5m]) * 8`, range, step),
      vmRangeQuery(`rate(interface_octets_out_bytes_total{device_name="${device}", interface_name="${wanIf}"}[5m]) * 8`, range, step)
    ]);

    const download = dlResult.status === 'fulfilled' ? extractTimeSeries(dlResult.value) : { timestamps: [], values: [] };
    const upload = ulResult.status === 'fulfilled' ? extractTimeSeries(ulResult.value) : { timestamps: [], values: [] };

    res.json({ site, range, step, download, upload });
  } catch (err) {
    console.error('Throughput metrics error:', err.message);
    res.status(502).json({ error: 'Failed to fetch throughput metrics', detail: err.message });
  }
});

module.exports = router;
