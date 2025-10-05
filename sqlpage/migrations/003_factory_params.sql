-- 003_factory_params.sql
-- Factory parameters and baseline surface storage used by overlays

CREATE TABLE IF NOT EXISTS factory_params (
marker_id   INTEGER PRIMARY KEY REFERENCES markers(id) ON DELETE CASCADE,
name        TEXT,
strength    REAL NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS ghg_surface (
lat       REAL NOT NULL,
lon       REAL NOT NULL,
variable  TEXT NOT NULL,  -- e.g., 'co2', 'npp', 'precip'
value     REAL NOT NULL,
obs_time  TEXT NOT NULL,  -- ISO8601 (UTC) when this field is valid
PRIMARY KEY (lat, lon, variable, obs_time)
);

-- Seed default strengths for any existing markers
INSERT OR IGNORE INTO factory_params (marker_id, name, strength)
SELECT id, title, 1.0 FROM markers;