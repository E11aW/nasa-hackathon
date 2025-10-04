SELECT
  'shell' AS component,
  'Clickable Map' AS title,
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

SELECT
  'html' AS component,
  '<link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;500;800&display=swap" rel="stylesheet">
   <style>
     body { font-family: Inter, system-ui, sans-serif; margin: 0; padding: 1rem; }
     h1 { margin: .5rem 0 0; font-weight: 800; }
     p { margin: .25rem 0; color: #333; }
     .hint { color:#666; font-size:.95rem }
   </style>
   <h1>Click the map to add a marker</h1>
   <p class="hint">A prompt will ask for a title; the point is saved to SQLite immediately.</p>' AS html;