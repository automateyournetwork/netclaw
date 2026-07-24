-- Network Guardian — Events & Investigations Schema
-- Designed for multi-tenant operation with the NetClaw feedback loop.

-- Sites (tenants)
CREATE TABLE IF NOT EXISTS sites (
  id TEXT PRIMARY KEY,              -- e.g. "home", "ridgeview-tavern"
  name TEXT NOT NULL,               -- display name
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Events (the diary entries visible to customers and operators)
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id TEXT NOT NULL REFERENCES sites(id),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- What happened
  message TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'info',   -- ok, info, watch, alert
  category TEXT,                           -- wan, wifi, security, bandwidth, system
  source TEXT NOT NULL DEFAULT 'system',   -- netclaw, alertmanager, operator, system

  -- Investigation lifecycle
  status TEXT NOT NULL DEFAULT 'logged',   -- logged, investigating, escalated, resolved, archived
  alert_name TEXT,                         -- originating alert (e.g. "WanHighLatency")
  alert_fingerprint TEXT,                  -- alertmanager fingerprint for dedup

  -- NetClaw investigation
  investigation_notes TEXT,               -- what NetClaw found during triage
  investigation_started_at TIMESTAMPTZ,
  investigation_completed_at TIMESTAMPTZ,
  root_cause TEXT,                        -- short summary of root cause

  -- Expert feedback (the learning loop)
  escalated_at TIMESTAMPTZ,
  expert_feedback TEXT,                   -- your corrections / context
  feedback_provided_at TIMESTAMPTZ,
  feedback_quality TEXT,                  -- correct, partially_correct, incorrect, needs_more_context

  -- RAG integration
  rag_document_id TEXT,                   -- ID in the RAG knowledge base once snapshotted
  rag_snapshotted_at TIMESTAMPTZ,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_events_site_timestamp ON events(site_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
CREATE INDEX IF NOT EXISTS idx_events_alert ON events(alert_name);
CREATE INDEX IF NOT EXISTS idx_events_escalated ON events(status) WHERE status = 'escalated';

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS events_updated_at ON events;
CREATE TRIGGER events_updated_at
  BEFORE UPDATE ON events
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Seed the home site
INSERT INTO sites (id, name) VALUES ('home', 'Home Pilot')
ON CONFLICT (id) DO NOTHING;
