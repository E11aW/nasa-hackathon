-- =========================
-- file: index.sql
-- =========================

-- === Leaflet shell (CSS/JS) ===
 SELECT
   'shell' AS component,
   '' AS title,
   '' AS footer,
   'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' AS css,
   'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'  AS javascript;

  -- 1) The ONLY shell, and the FIRST component-emitting SELECT
-- SELECT
  -- 'shell' AS component,
  -- 'Clickable Map' AS title,
  -- 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' AS css,
  -- 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'  AS javascript;

-- === Markers table (GeoJSON Feature per row) ===
CREATE TABLE IF NOT EXISTS markers (
  id      INTEGER PRIMARY KEY,
  title   TEXT NOT NULL,
  geojson TEXT NOT NULL,
  CHECK (json_extract(geojson, '$.type') = 'Feature'),
  CHECK (json_extract(geojson, '$.geometry.type') = 'Point'),
  CHECK (json_extract(geojson, '$.geometry.coordinates[0]') BETWEEN -180 AND 180),
  CHECK (json_extract(geojson, '$.geometry.coordinates[1]') BETWEEN  -90 AND  90)
);

-- 2) The custom map component
SELECT
  'map-clickable' AS component,
  700       AS height,
  39.8283   AS latitude,
  -98.5795  AS longitude,
  4         AS zoom,
  'main-map' AS id;

-- 3) Row data for that component
-- CLEAN START (no markers on initial load). To show saved markers, remove WHERE 1=0.
SELECT id AS marker_id, geojson
FROM markers
WHERE 1 = 0;