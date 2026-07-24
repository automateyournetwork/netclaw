'use strict';

const express = require('express');
const router = express.Router();
const { instantQuery, extractScalar } = require('../lib/queryEngine');
const { getAllSiteIds, getSiteConfig } = require('../lib/config');

/**
 * GET /api/sites
 * Available sites for the site selector (filtered by JWT scope).
 */
router.get('/', async (req, res) => {
  const user = req.user;
  const allSites = getAllSiteIds();

  // Filter to sites the user is authorized for
  const authorizedSites = user.role === 'admin'
    ? allSites
    : allSites.filter(s => user.sites.includes(s));

  // Quick health check per site
  const sites = await Promise.all(
    authorizedSites.map(async (siteId) => {
      const config = getSiteConfig(siteId);
      let healthy = null;

      try {
        const result = await instantQuery(`guardian:health_score{site="${siteId}"}`);
        const score = extractScalar(result);
        healthy = score !== null ? score >= 70 : null;
      } catch {
        healthy = null;
      }

      return {
        id: siteId,
        name: config?.name || siteId,
        healthy
      };
    })
  );

  res.json({ sites });
});

module.exports = router;
