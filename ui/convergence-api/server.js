'use strict';

require('dotenv').config();

const express = require('express');
const path = require('path');
const rateLimit = require('express-rate-limit');

const app = express();
const PORT = process.env.PORT || 3000;

// Trust proxy (behind cloudflared tunnel)
app.set('trust proxy', 1);

// --- Middleware ---

app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// Static files
app.use(express.static(path.join(__dirname, 'public')));

// Rate limiting (100 requests per minute per IP)
const apiLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later.' }
});
app.use('/api/', apiLimiter);

// View engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// --- Health check (no auth) ---

app.get('/healthz', (req, res) => {
  // 'ok' means the API is serving. Postgres is optional and only backs the
  // diary/triage, so its absence is reported as degraded rather than failing the
  // healthcheck — otherwise the container would be restarted for a feature the
  // deployment may not even use.
  const db = require('./src/db').dbStatus();
  res.json({
    status: 'ok',
    uptime: process.uptime(),
    features: {
      diary: db.available ? 'available' : 'unavailable',
    },
    database: db,
    timestamp: new Date().toISOString()
  });
});

// --- Routes ---

const authRoutes = require('./src/routes/auth');
const healthRoutes = require('./src/routes/health');
const metricsRoutes = require('./src/routes/metrics');
const devicesRoutes = require('./src/routes/devices');
const wifiRoutes = require('./src/routes/wifi');
const speedtestRoutes = require('./src/routes/speedtest');
const alertsRoutes = require('./src/routes/alerts');
const eventsRoutes = require('./src/routes/events');
const sitesRoutes = require('./src/routes/sites');
const securityRoutes = require('./src/routes/security');
const deviceDetailRoutes = require('./src/routes/device-detail');
const inventoryRoutes = require('./src/routes/inventory');

// Auth (no JWT required)
app.use('/api/auth', authRoutes);

// Protected API routes (JWT required)
const { authMiddleware } = require('./src/middleware/auth');

app.use('/api/health', authMiddleware, healthRoutes);
app.use('/api/metrics', authMiddleware, metricsRoutes);
app.use('/api/devices', authMiddleware, devicesRoutes);
app.use('/api/wifi', authMiddleware, wifiRoutes);
app.use('/api/speedtest', authMiddleware, speedtestRoutes);
app.use('/api/alerts', authMiddleware, alertsRoutes);
app.use('/api/events', authMiddleware, eventsRoutes);
app.use('/api/sites', authMiddleware, sitesRoutes);
app.use('/api/security', authMiddleware, securityRoutes);
app.use('/api/device', authMiddleware, deviceDetailRoutes);
app.use('/api/inventory', authMiddleware, inventoryRoutes);

// --- Pages (serve EJS views) ---

app.get('/login', (req, res) => {
  res.render('pages/login', { title: 'Login — Network Guardian' });
});

app.get('/', (req, res) => {
  res.redirect('/dashboard');
});

app.get('/dashboard', (req, res) => {
  res.render('pages/dashboard', { title: 'Dashboard — Network Guardian' });
});

app.get('/triage', (req, res) => {
  res.render('pages/triage', { title: 'Triage — Network Guardian' });
});

app.get('/device/:name', (req, res) => {
  res.render('pages/device', { title: `${req.params.name} — Network Guardian`, deviceName: req.params.name });
});

// --- Error handling ---

app.use((err, req, res, next) => {
  console.error('Unhandled error:', err.message);
  res.status(500).json({ error: 'Internal server error' });
});

// --- Start ---

const { initDB } = require('./src/db');

app.listen(PORT, async () => {
  console.log(`Network Guardian Web listening on port ${PORT}`);
  console.log(`  Health: http://localhost:${PORT}/healthz`);
  console.log(`  Mode:   ${process.env.NODE_ENV || 'development'}`);

  // Initialize database schema (non-blocking, non-fatal)
  await initDB().catch(err => {
    console.warn('DB init skipped (will retry on first query):', err.message);
  });
});

module.exports = app;
