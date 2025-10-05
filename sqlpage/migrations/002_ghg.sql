-- file: sqlpage/migrations/002_ghg.sql

-- Queue: a job appears whenever a marker is created
CREATE TABLE IF NOT EXISTS ghg_fetch_queue (
  id INTEGER PRIMARY KEY,
  marker_id INTEGER NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  enqueued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME
);

-- Storage: one row per (marker, time, variable)
CREATE TABLE IF NOT EXISTS ghg_observation (
  id INTEGER PRIMARY KEY,
  marker_id INTEGER NOT NULL,
  obs_time TEXT NOT NULL,
  variable TEXT NOT NULL,
  value REAL,
  unit TEXT
);

-- If your markers table is named "markers" (it is, per index.sql), enqueue a job on insert
CREATE TRIGGER IF NOT EXISTS trg_markers_enqueue_ghg
AFTER INSERT ON markers
BEGIN
  INSERT INTO ghg_fetch_queue (marker_id, lat, lon)
  VALUES (
    NEW.id,
    CAST(json_extract(NEW.geojson, '$.geometry.coordinates[1]') AS REAL),
    CAST(json_extract(NEW.geojson, '$.geometry.coordinates[0]') AS REAL)
  );
END;