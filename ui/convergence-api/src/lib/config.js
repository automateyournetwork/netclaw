'use strict';

/**
 * Config Provider — loads site configuration from environment.
 * Read-only at runtime; changes require pod restart.
 */

let sitesConfig = {};

try {
  sitesConfig = JSON.parse(process.env.SITES_CONFIG || '{}');
} catch (err) {
  console.error('Failed to parse SITES_CONFIG:', err.message);
  sitesConfig = {};
}

/**
 * Get configuration for a specific site.
 * @param {string} siteId - Site identifier (e.g., "home")
 * @returns {object|null} Site config or null if not found
 */
function getSiteConfig(siteId) {
  const config = sitesConfig[siteId] || null;
  if (!config) return null;

  // Normalize: support both old single-ISP format and new multi-provider format
  if (!config.providers && config.wanInterface) {
    // Legacy format: convert to providers array
    config.providers = [{
      id: 'primary',
      name: config.ispName || 'ISP',
      wanInterface: config.wanInterface,
      speedtestTarget: config.speedtestTarget || 1e9,
      servers: []
    }];
  }

  return config;
}

/**
 * Get the primary provider for a site (first in the list).
 */
function getPrimaryProvider(siteId) {
  const config = getSiteConfig(siteId);
  if (!config || !config.providers || config.providers.length === 0) return null;
  return config.providers[0];
}

/**
 * Get all available site IDs.
 * @returns {string[]}
 */
function getAllSiteIds() {
  return Object.keys(sitesConfig);
}

/**
 * Switch-inventory settings for a site.
 *
 * These used to be hardcoded to one lab's device names, which meant the devices
 * table was empty (or wrong) for every other deployment. Now optional config:
 *
 *   "switches": {
 *     "match":  ".*",                                  // PromQL regex on device_name
 *     "models": { "sw-01": "Cisco WS-C3850-48P" }      // optional display labels
 *   }
 *
 * The default matches every device reporting interface_status, which is the
 * sensible behaviour for an unconfigured install: show what the exporter sees
 * rather than nothing. Narrow it with `match` when the same metric carries
 * non-switch devices.
 *
 * `models` is display-only. Anything absent falls back to whatever label the
 * metrics provide, then to a generic label — never to a hardcoded guess.
 *
 * @param {string} siteId
 * @returns {{ match: string, models: Record<string,string> }}
 */
function getSwitchConfig(siteId) {
  const cfg = getSiteConfig(siteId) || {};
  const sw = cfg.switches || {};
  const match = typeof sw.match === 'string' && sw.match.trim() ? sw.match.trim() : '.*';
  const models = (sw.models && typeof sw.models === 'object') ? sw.models : {};
  return { match, models };
}

/**
 * Escape a value for safe interpolation into a PromQL label matcher.
 * Site config is operator-supplied rather than user input, but an unescaped
 * quote or backslash silently corrupts the query, which is hard to debug.
 */
function promqlLabelValue(value) {
  return String(value ?? '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

/**
 * Get threshold status for a value.
 * @param {number} value - The metric value
 * @param {object} thresholds - { green: number, yellow: number }
 * @param {boolean} lowerIsBetter - If true, below green = healthy (default true)
 * @returns {"healthy"|"degraded"|"unhealthy"}
 */
function getThresholdStatus(value, thresholds, lowerIsBetter = true) {
  if (!thresholds) return 'unknown';

  if (lowerIsBetter) {
    if (value <= thresholds.green) return 'healthy';
    if (value <= thresholds.yellow) return 'degraded';
    return 'unhealthy';
  } else {
    // Higher is better (e.g., speedtest throughput)
    if (value >= thresholds.green) return 'healthy';
    if (value >= thresholds.yellow) return 'degraded';
    return 'unhealthy';
  }
}

/**
 * Management GUI base URLs for device name deep-links in HOME Devices / Wi‑Fi.
 * Prefer SITES_CONFIG.home.mgmt.* then env overrides.
 *
 * Env:
 *   PFSENSE_MGMT_URL / EDGE_MGMT_URL  e.g. https://192.168.13.1:440
 *   UNIFI_MGMT_URL / UNIFI_HOST       e.g. https://192.168.100.10:11443
 */
function getMgmtUrls(siteId) {
  const site = getSiteConfig(siteId) || {};
  const mgmt = site.mgmt || {};
  const unifi =
    mgmt.unifi ||
    process.env.UNIFI_MGMT_URL ||
    process.env.UNIFI_HOST ||
    '';
  const pfsense =
    mgmt.pfsense ||
    mgmt.edge ||
    process.env.PFSENSE_MGMT_URL ||
    process.env.EDGE_MGMT_URL ||
    '';
  const strip = (u) => (u ? String(u).trim().replace(/\/$/, '') : '');
  return {
    unifi: strip(unifi),
    pfsense: strip(pfsense),
    edge: strip(pfsense),
  };
}

module.exports = {
  getSiteConfig,
  getPrimaryProvider,
  getAllSiteIds,
  getSwitchConfig,
  promqlLabelValue,
  getThresholdStatus,
  getMgmtUrls,
  PROMETHEUS_URL: process.env.PROMETHEUS_URL || 'http://prometheus:9090',
  VICTORIAMETRICS_URL: process.env.VICTORIAMETRICS_URL || 'http://victoriametrics:8428',
  LOKI_URL: process.env.LOKI_URL || 'http://loki:3100',
  ALERTMANAGER_URL: process.env.ALERTMANAGER_URL || 'http://alertmanager:9093',
  NAUTOBOT_URL: process.env.NAUTOBOT_URL || 'http://nautobot.nautobot.svc:8080',
  NAUTOBOT_TOKEN: process.env.NAUTOBOT_TOKEN || '',
  PUBLIC_URL: process.env.PUBLIC_URL || 'http://localhost:3000'
};
