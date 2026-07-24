'use strict';

const express = require('express');
const router = express.Router();
const { queryLoki } = require('../lib/queryEngine');

/**
 * GET /api/security?site=X
 * Returns security summary: blocked counts, top sources, trend.
 * Data source: pfSense filterlog block entries in Loki.
 */
router.get('/', async (req, res) => {
  const site = req.site;

  try {
    const [blocks24h, blocks1h, topSources] = await Promise.allSettled([
      countBlocked('24h'),
      countBlocked('1h'),
      getTopBlockedSources()
    ]);

    const total24h = blocks24h.status === 'fulfilled' ? blocks24h.value : null;
    const total1h = blocks1h.status === 'fulfilled' ? blocks1h.value : null;
    const sources = topSources.status === 'fulfilled' ? topSources.value : [];

    res.json({
      site,
      blockedConnections: {
        last24h: total24h,
        lastHour: total1h
      },
      topSources: sources,
      status: total24h !== null ? 'active' : 'unavailable'
    });
  } catch (err) {
    console.error('Security endpoint error:', err.message);
    res.json({ site, blockedConnections: { last24h: null, lastHour: null }, topSources: [], status: 'unavailable' });
  }
});

/**
 * Get top blocked source IPs from filterlog in the last hour.
 */
async function getTopBlockedSources() {
  try {
    const { LOKI_URL } = require('../lib/config');
    const now = Math.floor(Date.now() / 1000);
    // TopK by source IP from filterlog block entries
    const logql = 'topk(5, sum by (source) (count_over_time({device_name="pfsense"} |= "filterlog" |= "block" | regexp ".*,(?P<source>[0-9]+\\\\.[0-9]+\\\\.[0-9]+\\\\.[0-9]+),.*" [1h])))';

    // Simpler approach: fetch recent block entries and extract IPs client-side
    const { queryLoki } = require('../lib/queryEngine');
    const result = await queryLoki('{device_name="pfsense"} |= "filterlog" |= "block"', 200, '1h');

    const ipCounts = new Map();
    for (const stream of result) {
      for (const [ts, msg] of (stream.values || [])) {
        // filterlog format: ...,block,in,4,...,<src_ip>,<dst_ip>,...
        let text = msg;
        try { const p = JSON.parse(msg); text = p.body || msg; } catch {}
        // Extract source IP (field after protocol version "4" or "6")
        const parts = text.split(',');
        // Source IP is typically around position 18-19 in filterlog CSV
        for (const part of parts) {
          if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(part) && !part.startsWith('192.168.') && !part.startsWith('10.') && !part.startsWith('172.')) {
            ipCounts.set(part, (ipCounts.get(part) || 0) + 1);
            break;
          }
        }
      }
    }

    // Sort by count, return top 5 with basic enrichment
    const top5 = Array.from(ipCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    // Enrich top IPs with GreyNoise (free, no key, community API)
    const enriched = await Promise.all(top5.map(async ([ip, count]) => {
      const info = await enrichIP(ip);
      return { ip, count, ...info };
    }));

    return enriched;
  } catch (err) {
    console.error('getTopBlockedSources error:', err.message);
    return [];
  }
}

/**
 * Enrich an IP with GreyNoise community API (free, no key).
 * Returns: { noise: bool, classification: string, name: string }
 */
async function enrichIP(ip) {
  try {
    const res = await fetch(`https://api.greynoise.io/v3/community/${ip}`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) return { noise: null, classification: 'unknown', name: '' };
    const data = await res.json();
    return {
      noise: data.noise || false,
      classification: data.classification || 'unknown',
      name: data.name || ''
    };
  } catch {
    return { noise: null, classification: 'unknown', name: '' };
  }
}

/**
 * Count filterlog block entries in Loki for a given time range.
 * Uses a metric query (count_over_time) for efficiency.
 */
async function countBlocked(range) {
  try {
    const { LOKI_URL } = require('../lib/config');
    const now = Math.floor(Date.now() / 1000);
    const { parseRange } = require('../lib/queryEngine');
    const start = now - parseRange(range);

    // Use Loki instant metric query to count matching log lines
    const logql = 'sum(count_over_time({device_name="pfsense"} |= "filterlog" |= "block" [' + range + ']))';
    const url = `${LOKI_URL}/loki/api/v1/query?query=${encodeURIComponent(logql)}&time=${now}`;

    const res = await fetch(url, { signal: AbortSignal.timeout(10000) });
    if (!res.ok) throw new Error(`Loki ${res.status}`);
    const data = await res.json();

    if (data.status === 'success' && data.data.result.length > 0) {
      return parseInt(data.data.result[0].value[1]) || 0;
    }
    return 0;
  } catch (err) {
    console.error('countBlocked error:', err.message);
    return null;
  }
}

module.exports = router;
