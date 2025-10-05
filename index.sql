-- =========================
-- file: index.sql
-- =========================

-- === Leaflet shell (CSS/JS) ===
SELECT
  'shell' AS component,
  'Clickable Map + CAMS Popups' AS title,
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' AS css,
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'  AS javascript;

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

-- (Optional) Seed one marker if DB is empty
INSERT INTO markers (title, geojson)
SELECT 'Mvezo, Birth Place of Nelson Mandela',
'{"type":"Feature","properties":{"title":"Mvezo, Birth Place of Nelson Mandela"},
  "geometry":{"type":"Point","coordinates":[28.49,-31.96]}}'
WHERE NOT EXISTS (SELECT 1 FROM markers);

-- Ensure properties.id is set for all rows (old rows too)
UPDATE markers
SET geojson = json_set(geojson, '$.properties.id', id)
WHERE json_extract(geojson,'$.properties.id') IS NULL;

-- === Initial map center (avg of all markers; fallback 40/-110) ===
WITH pts AS (
  SELECT
    CAST(json_extract(geojson, '$.geometry.coordinates[0]') AS REAL) AS lon,
    CAST(json_extract(geojson, '$.geometry.coordinates[1]') AS REAL) AS lat
  FROM markers
),
stats AS (SELECT COUNT(*) AS n, AVG(lat) AS lat, AVG(lon) AS lon FROM pts)
SELECT
  'map-clickable' AS component,          -- uses templates/map-clickable.handlebars
  600              AS height,
  COALESCE((SELECT lat FROM stats), 40)    AS latitude,
  COALESCE((SELECT lon FROM stats), -110)  AS longitude,
  5                AS zoom,
  'main-map'       AS id;

-- === Stream markers to the template (one row per Feature) ===
-- IMPORTANT: expose BOTH id and geojson
SELECT
  id,
  json_object(
    'type','Feature',
    'geometry', json_object(
      'type','Point',
      'coordinates', json_array(
        CAST(json_extract(geojson, '$.geometry.coordinates[0]') AS REAL),
        CAST(json_extract(geojson, '$.geometry.coordinates[1]') AS REAL)
      )
    ),
    'properties', json_object(
      'id',    id,       -- keep an explicit id in properties
      'title', title
    )
  ) AS geojson
FROM markers
ORDER BY id DESC;

-- === Small caption ===
SELECT
  'html' AS component,
  '<style>
     body { font-family: Inter, system-ui, sans-serif; margin: 0; padding: 1rem; }
     h1 { margin:.5rem 0 0; font-weight: 800; }
     .hint { color:#666; font-size:.95rem }
   </style>
   <h1>Click the map to add a marker</h1>
   <p class="hint">CAMS values will appear in the marker popup when the worker ingests data.</p>' AS html;