CREATE TABLE IF NOT EXISTS markers (
  id      INTEGER PRIMARY KEY,
  title   TEXT NOT NULL,
  geojson TEXT NOT NULL,
  CHECK (json_extract(geojson, '$.type') = 'Feature'),
  CHECK (json_extract(geojson, '$.geometry.type') = 'Point'),
  CHECK (json_extract(geojson, '$.geometry.coordinates[0]') BETWEEN -180 AND 180),
  CHECK (json_extract(geojson, '$.geometry.coordinates[1]') BETWEEN  -90 AND  90)
);

-- 1) The ONLY shell, and the FIRST component-emitting SELECT
SELECT
  'shell' AS component,
  'Clickable Map' AS title,
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' AS css,
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'  AS javascript;

-- 2) Your custom map component (blank start over the U.S.)
SELECT
  'map-clickable' AS component,
  700       AS height,
  39.8283   AS latitude,
  -98.5795  AS longitude,
  4         AS zoom,
  'main-map' AS id;

-- 3) Rows for existing markers (inject id into properties for delete-on-✕ logic)
-- SELECT json_set(geojson, '$.properties.id', id) AS geojson
-- FROM markers;

-- Important: include id for delete
SELECT id, geojson FROM markers;

-- Row-level data consumed by the template above
-- SELECT json_valid(geojson) FROM markers;

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