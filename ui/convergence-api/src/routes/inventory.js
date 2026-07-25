'use strict';

const express = require('express');
const router = express.Router();
const { sotAdapter } = require('../lib/adapters/sot');

/**
 * GET /api/inventory/search?q=<query>
 * Free-text device search against the configured SoT (Nautobot/NetBox/none).
 */
router.get('/search', async (req, res) => {
  const query = (req.query.q || '').trim();
  if (!query) {
    return res.status(400).json({ error: 'Query parameter "q" is required' });
  }

  try {
    const results = await sotAdapter.lookup(query);
    res.json({ query, count: results.length, results, source: sotAdapter.type });
  } catch (err) {
    console.error('SoT lookup error:', err.message);
    res.status(502).json({ error: 'SoT lookup failed', detail: err.message, source: sotAdapter.type });
  }
});

/**
 * GET /api/inventory/device/:name
 * Get a single device by exact name from the SoT.
 */
router.get('/device/:name', async (req, res) => {
  const { name } = req.params;
  if (!name) {
    return res.status(400).json({ error: 'Device name is required' });
  }

  try {
    const device = await sotAdapter.getDevice(name);
    if (!device) {
      return res.status(404).json({ error: 'Device not found in SoT', name, source: sotAdapter.type });
    }
    res.json({ device, source: sotAdapter.type });
  } catch (err) {
    console.error('SoT getDevice error:', err.message);
    res.status(502).json({ error: 'SoT device lookup failed', detail: err.message, source: sotAdapter.type });
  }
});

/**
 * GET /api/inventory/device/:name/interfaces
 * Get interfaces for a device from the SoT.
 */
router.get('/device/:name/interfaces', async (req, res) => {
  const { name } = req.params;

  try {
    const interfaces = await sotAdapter.getInterfaces(name);
    res.json({ device: name, count: interfaces.length, interfaces, source: sotAdapter.type });
  } catch (err) {
    console.error('SoT getInterfaces error:', err.message);
    res.status(502).json({ error: 'SoT interfaces lookup failed', detail: err.message, source: sotAdapter.type });
  }
});

/**
 * GET /api/inventory/ip?q=<query>
 * Search IP addresses in the SoT.
 */
router.get('/ip', async (req, res) => {
  const query = (req.query.q || '').trim();
  if (!query) {
    return res.status(400).json({ error: 'Query parameter "q" is required' });
  }

  try {
    const results = await sotAdapter.getIPAddresses(query);
    res.json({ query, count: results.length, results, source: sotAdapter.type });
  } catch (err) {
    console.error('SoT IP lookup error:', err.message);
    res.status(502).json({ error: 'SoT IP lookup failed', detail: err.message, source: sotAdapter.type });
  }
});

/**
 * GET /api/inventory/health
 * SoT adapter health check — is the backend reachable?
 */
router.get('/health', async (req, res) => {
  try {
    const health = await sotAdapter.health();
    const status = health.ok ? 200 : 503;
    res.status(status).json(health);
  } catch (err) {
    res.status(503).json({ ok: false, type: sotAdapter.type, message: err.message });
  }
});

module.exports = router;
