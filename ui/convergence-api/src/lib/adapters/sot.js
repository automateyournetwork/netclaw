'use strict';

/**
 * SoT Adapter — Source of Truth inventory abstraction.
 *
 * Supports: none | nautobot | netbox (stub)
 *
 * Config is driven by SOT_TYPE env (or sot.type in convergence.yaml).
 * Each implementation exposes the same interface:
 *   - lookup(query)        → device records matching free-text query
 *   - getDevice(name)      → single device by exact name
 *   - getInterfaces(name)  → interfaces for a device
 *   - getIPAddresses(q)    → IP address records
 *   - health()             → { ok, type, message }
 */

const { NAUTOBOT_URL, NAUTOBOT_TOKEN } = require('../config');

// ─── Nautobot adapter ────────────────────────────────────────────────────────

class NautobotAdapter {
  constructor(url, token) {
    this.baseUrl = (url || '').replace(/\/$/, '');
    this.token = token || '';
    this.type = 'nautobot';
  }

  /** Internal fetch helper with auth + error handling */
  async _fetch(path, params = {}) {
    const url = new URL(path, this.baseUrl);
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') {
        url.searchParams.set(k, v);
      }
    }
    url.searchParams.set('limit', params.limit || '50');

    const resp = await fetch(url.toString(), {
      headers: {
        Authorization: `Token ${this.token}`,
        Accept: 'application/json',
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!resp.ok) {
      const body = await resp.text().catch(() => '');
      throw new Error(`Nautobot ${resp.status}: ${body.slice(0, 200)}`);
    }
    return resp.json();
  }

  /** Free-text device search */
  async lookup(query) {
    if (!query) return [];
    const data = await this._fetch('/api/dcim/devices/', { q: query });
    return (data.results || []).map(NautobotAdapter._mapDevice);
  }

  /** Get device by exact name */
  async getDevice(name) {
    if (!name) return null;
    const data = await this._fetch('/api/dcim/devices/', { name });
    const results = data.results || [];
    return results.length > 0 ? NautobotAdapter._mapDevice(results[0]) : null;
  }

  /** Get interfaces for a device */
  async getInterfaces(deviceName) {
    if (!deviceName) return [];
    const data = await this._fetch('/api/dcim/interfaces/', { device: deviceName });
    return (data.results || []).map((iface) => ({
      id: iface.id,
      name: iface.name || '',
      type: iface.type?.value || iface.type || '',
      enabled: iface.enabled !== false,
      description: iface.description || '',
      status: iface.status?.value || iface.status || '',
      ipAddresses: (iface.ip_addresses || []).map((ip) => ip.address || ip),
      mac: iface.mac_address || '',
      mtu: iface.mtu || null,
    }));
  }

  /** Search IP addresses */
  async getIPAddresses(query) {
    if (!query) return [];
    const data = await this._fetch('/api/ipam/ip-addresses/', { q: query });
    return (data.results || []).map((ip) => ({
      id: ip.id,
      address: ip.address || '',
      status: ip.status?.value || ip.status || '',
      dnsName: ip.dns_name || '',
      device: ip.assigned_object?.device?.name || '',
      interface: ip.assigned_object?.name || '',
      tenant: ip.tenant?.name || '',
    }));
  }

  /** Health check — verify connectivity to Nautobot */
  async health() {
    try {
      if (!this.baseUrl || !this.token) {
        return { ok: false, type: 'nautobot', message: 'NAUTOBOT_URL or NAUTOBOT_TOKEN not configured' };
      }
      const data = await this._fetch('/api/status/');
      return {
        ok: true,
        type: 'nautobot',
        message: `Connected — Nautobot ${data['nautobot-version'] || 'unknown'}`,
        version: data['nautobot-version'] || null,
      };
    } catch (err) {
      return { ok: false, type: 'nautobot', message: err.message };
    }
  }

  /** Map Nautobot device JSON → normalized record */
  static _mapDevice(d) {
    return {
      id: d.id,
      name: d.name || '',
      role: d.role?.name || d.device_role?.name || '',
      platform: d.platform?.name || '',
      location: d.location?.name || d.site?.name || '',
      status: d.status?.value || d.status || '',
      primaryIp: d.primary_ip?.address || '',
      primaryIp4: d.primary_ip4?.address || '',
      primaryIp6: d.primary_ip6?.address || '',
      serial: d.serial || '',
      model: d.device_type?.model || '',
      manufacturer: d.device_type?.manufacturer?.name || '',
      tenant: d.tenant?.name || '',
      tags: (d.tags || []).map((t) => t.name || t),
      source: 'nautobot',
    };
  }
}

// ─── Null adapter (sot.type = none) ──────────────────────────────────────────

class NullAdapter {
  constructor() {
    this.type = 'none';
  }
  async lookup() { return []; }
  async getDevice() { return null; }
  async getInterfaces() { return []; }
  async getIPAddresses() { return []; }
  async health() { return { ok: true, type: 'none', message: 'SoT disabled (type=none)' }; }
}

// ─── NetBox adapter stub (future) ────────────────────────────────────────────

class NetBoxAdapter {
  constructor(url, token) {
    this.baseUrl = (url || '').replace(/\/$/, '');
    this.token = token || '';
    this.type = 'netbox';
  }
  async lookup() { return []; }
  async getDevice() { return null; }
  async getInterfaces() { return []; }
  async getIPAddresses() { return []; }
  async health() {
    return { ok: false, type: 'netbox', message: 'NetBox adapter not yet implemented (stub)' };
  }
}

// ─── Factory ─────────────────────────────────────────────────────────────────

/**
 * Create the appropriate SoT adapter based on config.
 * @param {string} [type] - Override SOT_TYPE env
 * @returns {NautobotAdapter|NetBoxAdapter|NullAdapter}
 */
function createSotAdapter(type) {
  const sotType = (type || process.env.SOT_TYPE || 'none').toLowerCase().trim();

  switch (sotType) {
    case 'nautobot':
      return new NautobotAdapter(
        NAUTOBOT_URL || process.env.NAUTOBOT_URL,
        NAUTOBOT_TOKEN || process.env.NAUTOBOT_TOKEN
      );

    case 'netbox':
      return new NetBoxAdapter(
        process.env.NETBOX_URL,
        process.env.NETBOX_TOKEN
      );

    case 'none':
    default:
      return new NullAdapter();
  }
}

// Singleton — created once at module load
const sotAdapter = createSotAdapter();

module.exports = {
  sotAdapter,
  createSotAdapter,
  NautobotAdapter,
  NetBoxAdapter,
  NullAdapter,
};
