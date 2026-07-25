'use strict';

/**
 * Query Engine — stateless utility for querying Prometheus, Loki, and Alertmanager.
 * Handles connection pooling, timeouts, and error normalization.
 */

const { PROMETHEUS_URL, VICTORIAMETRICS_URL, LOKI_URL, ALERTMANAGER_URL } = require('./config');

const DEFAULT_TIMEOUT = 10000; // 10s

/**
 * Execute a fetch with timeout.
 */
async function fetchWithTimeout(url, opts = {}, timeoutMs = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, { ...opts, signal: controller.signal });
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`);
    }
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Prometheus instant query.
 * @param {string} query - PromQL expression
 * @returns {Array} result array from Prometheus response
 */
async function instantQuery(query) {
  const url = `${PROMETHEUS_URL}/api/v1/query?query=${encodeURIComponent(query)}`;
  const data = await fetchWithTimeout(url);

  if (data.status !== 'success') {
    throw new Error(`Prometheus query failed: ${data.error || 'unknown'}`);
  }
  return data.data.result;
}

/**
 * Prometheus range query.
 * @param {string} query - PromQL expression
 * @param {string} range - Time range (e.g., "1h", "24h")
 * @param {string} step - Step interval (e.g., "30s", "5m")
 * @returns {Array} result array with values
 */
async function rangeQuery(query, range = '1h', step = '30s') {
  const now = Math.floor(Date.now() / 1000);
  const start = now - parseRange(range);

  const params = new URLSearchParams({
    query,
    start: start.toString(),
    end: now.toString(),
    step
  });

  const url = `${PROMETHEUS_URL}/api/v1/query_range?${params}`;
  const data = await fetchWithTimeout(url);

  if (data.status !== 'success') {
    throw new Error(`Prometheus range query failed: ${data.error || 'unknown'}`);
  }
  return data.data.result;
}

/**
 * VictoriaMetrics instant query (for SNMP/interface metrics stored in VM).
 * Same PromQL API, different backend.
 */
async function vmInstantQuery(query) {
  const url = `${VICTORIAMETRICS_URL}/api/v1/query?query=${encodeURIComponent(query)}`;
  const data = await fetchWithTimeout(url);

  if (data.status !== 'success') {
    throw new Error(`VictoriaMetrics query failed: ${data.error || 'unknown'}`);
  }
  return data.data.result;
}

/**
 * VictoriaMetrics range query (for SNMP/interface metrics stored in VM).
 */
async function vmRangeQuery(query, range = '1h', step = '30s') {
  const now = Math.floor(Date.now() / 1000);
  const start = now - parseRange(range);

  const params = new URLSearchParams({
    query,
    start: start.toString(),
    end: now.toString(),
    step
  });

  const url = `${VICTORIAMETRICS_URL}/api/v1/query_range?${params}`;
  const data = await fetchWithTimeout(url);

  if (data.status !== 'success') {
    throw new Error(`VictoriaMetrics range query failed: ${data.error || 'unknown'}`);
  }
  return data.data.result;
}

/**
 * Query Loki for log entries.
 * @param {string} logql - LogQL expression
 * @param {number} limit - Max entries to return
 * @param {string} range - Time range to search
 * @returns {Array} log stream results
 */
async function queryLoki(logql, limit = 50, range = '1h') {
  const now = Math.floor(Date.now() / 1000);
  const start = now - parseRange(range);

  const params = new URLSearchParams({
    query: logql,
    limit: limit.toString(),
    start: (start * 1e9).toString(),  // Loki uses nanoseconds
    end: (now * 1e9).toString(),
    direction: 'backward'
  });

  const url = `${LOKI_URL}/loki/api/v1/query_range?${params}`;
  const data = await fetchWithTimeout(url);

  if (data.status !== 'success') {
    throw new Error(`Loki query failed: ${data.error || 'unknown'}`);
  }
  return data.data.result;
}

/**
 * Query Alertmanager for active alerts.
 * @param {object} filters - Optional filters { site }
 * @returns {Array} alerts array
 */
async function queryAlertmanager(filters = {}) {
  let url = `${ALERTMANAGER_URL}/api/v2/alerts`;

  // Alertmanager supports filter parameter
  if (filters.site) {
    url += `?filter=site%3D%22${encodeURIComponent(filters.site)}%22`;
  }

  const data = await fetchWithTimeout(url);
  return data; // Alertmanager v2 returns array directly
}

/**
 * Parse a human-readable range string to seconds.
 * @param {string} range - e.g., "1h", "6h", "24h", "7d", "30m"
 * @returns {number} seconds
 */
function parseRange(range) {
  const match = range.match(/^(\d+)([smhd])$/);
  if (!match) return 3600; // default 1h

  const value = parseInt(match[1], 10);
  const unit = match[2];

  switch (unit) {
    case 's': return value;
    case 'm': return value * 60;
    case 'h': return value * 3600;
    case 'd': return value * 86400;
    default: return 3600;
  }
}

/**
 * Extract a single scalar value from a Prometheus instant query result.
 * @param {Array} result - Prometheus result array
 * @returns {number|null}
 */
function extractScalar(result) {
  if (!result || result.length === 0) return null;
  const val = parseFloat(result[0].value[1]);
  return isNaN(val) ? null : val;
}

/**
 * Extract time-series data from a Prometheus range query result.
 * Returns { timestamps: number[], values: number[] }
 * @param {Array} result - Prometheus range result array
 * @returns {{ timestamps: number[], values: number[] }}
 */
function extractTimeSeries(result) {
  if (!result || result.length === 0) {
    return { timestamps: [], values: [] };
  }

  // Take first result series
  const values = result[0].values || [];
  return {
    timestamps: values.map(v => v[0]),
    values: values.map(v => parseFloat(v[1]))
  };
}

/**
 * Extract multiple labeled series from a range query.
 * @param {Array} result - Prometheus range result
 * @param {string} labelKey - Label to use as series identifier
 * @returns {Object} keyed by label value → { timestamps, values }
 */
function extractLabeledSeries(result, labelKey) {
  const series = {};
  for (const r of result) {
    const label = r.metric[labelKey] || 'unknown';
    const values = r.values || [];
    series[label] = {
      timestamps: values.map(v => v[0]),
      values: values.map(v => parseFloat(v[1]))
    };
  }
  return series;
}

module.exports = {
  instantQuery,
  rangeQuery,
  vmInstantQuery,
  vmRangeQuery,
  queryLoki,
  queryAlertmanager,
  parseRange,
  extractScalar,
  extractTimeSeries,
  extractLabeledSeries
};
