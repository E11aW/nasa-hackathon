SELECT
  'shell' AS component,
  '' AS title,
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' AS css,
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'  AS javascript;

-- Create table to store markers
CREATE TABLE IF NOT EXISTS markers (
  id      INTEGER PRIMARY KEY,
  title   TEXT NOT NULL,
  geojson TEXT NOT NULL,
  CHECK (json_extract(geojson, '$.type') = 'Feature'),
  CHECK (json_extract(geojson, '$.geometry.type') = 'Point'),
  CHECK (json_extract(geojson, '$.geometry.coordinates[0]') BETWEEN -180 AND 180),
  CHECK (json_extract(geojson, '$.geometry.coordinates[1]') BETWEEN  -90 AND  90)
);

-- Seed one example (safe if already there)
INSERT OR IGNORE INTO markers (id, title, geojson)
SELECT 1, 'Mvezo, Birth Place of Nelson Mandela',
'{"type":"Feature","properties":{"title":"Mvezo, Birth Place of Nelson Mandela"},
  "geometry":{"type":"Point","coordinates":[28.49,-31.96]}}'
WHERE NOT EXISTS (SELECT 1 FROM markers WHERE id = 1);

-- Compute dynamic center (fallback: 40, -110)
WITH pts AS (
  SELECT
    CAST(json_extract(geojson, '$.geometry.coordinates[0]') AS REAL) AS lon,
    CAST(json_extract(geojson, '$.geometry.coordinates[1]') AS REAL) AS lat
  FROM markers
),
stats AS (SELECT AVG(lat) AS lat, AVG(lon) AS lon FROM pts)
SELECT
  'map-clickable' AS component,
  700       AS height,
  39.8283   AS latitude,
  -98.5795  AS longitude,
  3         AS zoom,     -- wider view to include AK/HI
  'main-map' AS id;

SELECT geojson FROM markers;

-- Row-level data consumed by the template above
SELECT json_valid(geojson) FROM markers;