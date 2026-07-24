'use strict';

const express = require('express');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const router = express.Router();

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';
const TOKEN_EXPIRY = '24h';

// Load users from environment
let users = [];
try {
  users = JSON.parse(process.env.USERS || '[]');
} catch (err) {
  console.error('Failed to parse USERS env:', err.message);
}

/**
 * POST /api/auth/login
 * Issue a JWT token for valid credentials.
 */
router.post('/login', async (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ error: 'Username and password required' });
  }

  const user = users.find(u => u.username === username);
  if (!user) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  try {
    const valid = await bcrypt.compare(password, user.passwordHash);
    if (!valid) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
  } catch (err) {
    console.error('bcrypt compare error:', err.message);
    return res.status(500).json({ error: 'Authentication error' });
  }

  const token = jwt.sign(
    {
      sub: user.id,
      name: user.name || user.username,
      role: user.role,
      sites: user.sites
    },
    JWT_SECRET,
    { expiresIn: TOKEN_EXPIRY }
  );

  res.json({
    token,
    expiresIn: 86400,
    sites: user.sites,
    role: user.role,
    name: user.name || user.username
  });
});

module.exports = router;
