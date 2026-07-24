'use strict';

const express = require('express');
const router = express.Router();
const { instantQuery, extractScalar } = require('../lib/queryEngine');
const { getSiteConfig, getThresholdStatus } = require('../lib/config');

/**
 * GET /api/wifi?site=X
 * Wi-Fi client counts and quality metrics.
 */
router.get('/', async (req, res) => {
  const site = req.site;
  const config = getSiteConfig(site);
  const thresholds = config?.thresholds?.txRetries || { green: 20, yellow: 35 };

  try {
    const [wireless, wired, guest, total, retries] = await Promise.allSettled([
      instantQuery(`unifi_site_clients_wireless{site="${site}"}`),
      instantQuery(`unifi_site_clients_wired{site="${site}"}`),
      instantQuery(`unifi_site_clients_guest{site="${site}"}`),
      instantQuery(`unifi_site_clients_total{site="${site}"}`),
      instantQuery(`unifi_radio_tx_retries_pct{site="${site}"}`)
    ]);

    const clients = {
      wireless: wireless.status === 'fulfilled' ? extractScalar(wireless.value) || 0 : null,
      wired: wired.status === 'fulfilled' ? extractScalar(wired.value) || 0 : null,
      guest: guest.status === 'fulfilled' ? extractScalar(guest.value) || 0 : null,
      total: total.status === 'fulfilled' ? extractScalar(total.value) || 0 : null
    };

    // TX retries per AP/band
    const txRetries = [];
    if (retries.status === 'fulfilled') {
      for (const r of retries.value) {
        const value = parseFloat(r.value[1]);
        txRetries.push({
          device: r.metric.device || 'unknown',
          band: r.metric.band || 'unknown',
          value: Math.round(value * 10) / 10,
          status: getThresholdStatus(value, thresholds)
        });
      }
    }

    res.json({ site, clients, txRetries });
  } catch (err) {
    console.error('WiFi endpoint error:', err.message);
    res.status(502).json({ error: 'Failed to fetch WiFi data', detail: err.message });
  }
});

module.exports = router;
