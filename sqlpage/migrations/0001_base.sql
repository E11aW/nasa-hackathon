-- file: sqlpage/migrations/0001_base.sql
-- Base schema required by later migrations

CREATE TABLE IF NOT EXISTS markers (
  id      INTEGER PRIMARY KEY,
  title   TEXT,          -- used by 0003 to seed factory_params.name
  geojson TEXT NOT NULL  -- used by 0002/0004 triggers to pull coords
);
