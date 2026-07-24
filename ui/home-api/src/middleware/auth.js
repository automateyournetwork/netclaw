'use strict';

const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';

/**
 * JWT authentication middleware.
 * Validates Bearer token (JWT or API key), extracts user info, enforces site scope.
 *
 * After this middleware:
 *   req.user = { sub, name, role, sites }
 *   req.site = validated site string
 */
function authMiddleware(req, res, next) {
  const header = req.headers.authorization;

  if (!header || !header.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Authentication required' });
  }

  const token = header.slice(7);

  // Check if it's a static API key (for machine-to-machine like NetClaw)
  const apiKeys = loadApiKeys();
  const apiKeyMatch = apiKeys.find(k => k.key === token);
  if (apiKeyMatch) {
    req.user = { sub: apiKeyMatch.id, name: apiKeyMatch.name, role: apiKeyMatch.role, sites: apiKeyMatch.sites };
    req.site = req.query.site || apiKeyMatch.sites[0];

    // Validate site scope
    if (req.query.site && apiKeyMatch.role !== 'admin' && !apiKeyMatch.sites.includes(req.query.site)) {
      return res.status(403).json({ error: 'Site not authorized for this key' });
    }
    return next();
  }

  // Otherwise validate as JWT
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.user = payload;

    // Site scope enforcement
    const requestedSite = req.query.site;
    if (requestedSite) {
      if (payload.role !== 'admin' && !payload.sites.includes(requestedSite)) {
        return res.status(403).json({ error: 'Site not authorized for this token' });
      }
      req.site = requestedSite;
    } else {
      // Default to first allowed site
      req.site = payload.sites[0];
    }

    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token expired' });
    }
    if (err.name === 'JsonWebTokenError') {
      return res.status(401).json({ error: 'Invalid token' });
    }
    return res.status(401).json({ error: 'Authentication failed' });
  }
}

/**
 * Load API keys from environment.
 * Format: API_KEYS='[{"id":"netclaw","name":"NetClaw","key":"...","role":"admin","sites":["home"]}]'
 */
function loadApiKeys() {
  try {
    return JSON.parse(process.env.API_KEYS || '[]');
  } catch {
    return [];
  }
}

module.exports = { authMiddleware };
