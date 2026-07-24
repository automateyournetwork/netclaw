'use strict';

/**
 * Formatters — unit conversion and display helpers.
 */

/**
 * Format bits per second to human-readable string.
 * @param {number} bps - Bits per second
 * @returns {{ value: number, unit: string }}
 */
function formatBps(bps) {
  if (bps === null || bps === undefined) return { value: 0, unit: 'bps' };

  if (bps >= 1e9) return { value: Math.round(bps / 1e7) / 100, unit: 'Gbps' };
  if (bps >= 1e6) return { value: Math.round(bps / 1e4) / 100, unit: 'Mbps' };
  if (bps >= 1e3) return { value: Math.round(bps / 10) / 100, unit: 'Kbps' };
  return { value: Math.round(bps * 100) / 100, unit: 'bps' };
}

/**
 * Format seconds to human-readable uptime.
 * @param {number} seconds
 * @returns {string} e.g., "14.2 days", "3.5 hours"
 */
function formatUptime(seconds) {
  if (seconds === null || seconds === undefined) return 'unknown';

  const days = seconds / 86400;
  if (days >= 1) return `${Math.round(days * 10) / 10} days`;

  const hours = seconds / 3600;
  if (hours >= 1) return `${Math.round(hours * 10) / 10} hours`;

  const mins = seconds / 60;
  return `${Math.round(mins)} min`;
}

/**
 * Format milliseconds for display.
 * @param {number} ms
 * @returns {string} e.g., "12.4ms"
 */
function formatLatency(ms) {
  if (ms === null || ms === undefined) return '—';
  return `${Math.round(ms * 10) / 10}ms`;
}

/**
 * Format a percentage value.
 * @param {number} pct
 * @returns {string} e.g., "94.5%"
 */
function formatPercent(pct) {
  if (pct === null || pct === undefined) return '—';
  return `${Math.round(pct * 10) / 10}%`;
}

module.exports = {
  formatBps,
  formatUptime,
  formatLatency,
  formatPercent
};
