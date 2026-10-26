-- Initial schema for sonnen-homelab-power-controller.
-- Idempotent — safe to run multiple times.

CREATE SCHEMA IF NOT EXISTS sonnen;

-- Append-only stream of samples from /api/v1/status.
CREATE TABLE IF NOT EXISTS sonnen.status (
  collected_at   timestamptz NOT NULL DEFAULT now(),
  rsoc           int,
  usoc           int,
  production_w   int,
  consumption_w  int,
  grid_feed_in_w int,
  pac_total_w    int,
  battery_charging    boolean,
  battery_discharging boolean,
  operating_mode      text,
  raw            jsonb
);

CREATE INDEX IF NOT EXISTS status_collected_at_idx
  ON sonnen.status (collected_at DESC);

-- Decision history: one row per stage transition.
CREATE TABLE IF NOT EXISTS sonnen.decisions (
  decided_at   timestamptz NOT NULL DEFAULT now(),
  old_stage    text,
  new_stage    text NOT NULL,
  reason       text,
  rsoc         int,
  surplus_w    numeric
);

CREATE INDEX IF NOT EXISTS decisions_decided_at_idx
  ON sonnen.decisions (decided_at DESC);
