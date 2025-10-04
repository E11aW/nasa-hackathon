-- file: index.sql

-- Load Leaflet CSS/JS
SELECT
  'shell' AS component,
  'Clickable Map' AS title,
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' AS css,
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'  AS javascript;

-- Create table (id, title, geojson) if missing
CREATE TABLE IF NOT EXISTS markers (
  id      INTEGER PRIMARY KEY,
  title   TEXT NOT NULL,
  geojson TEXT NOT NULL,
  CHECK (json_extract(geojson, '$.type') = 'Feature'),
  CHECK (json_extract(geojson, '$.geometry.type') = 'Point'),
  CHECK (json_extract(geojson, '$.geometry.coordinates[0]') BETWEEN -180 AND 180),
  CHECK (json_extract(geojson, '$.geometry.coordinates[1]') BETWEEN  -90 AND  90)
);

-- Example seed
INSERT OR IGNORE INTO markers (id, title, geojson)
SELECT 1, 'Mvezo, Birth Place of Nelson Mandela',
'{"type":"Feature","properties":{"id":1,"title":"Mvezo, Birth Place of Nelson Mandela"},
  "geometry":{"type":"Point","coordinates":[28.49,-31.96]}}'
WHERE NOT EXISTS (SELECT 1 FROM markers WHERE id = 1);

-- Dynamic initial center (fallback 40, -110)
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

-- One row per marker consumed by the template. IMPORTANT: include properties.id
SELECT
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
      'id', id,
      'title', title
    )
  ) AS geojson
FROM markers
ORDER BY id DESC;

-- A little caption
SELECT
  'html' AS component,
  '<style>
     body { font-family: Inter, system-ui, sans-serif; margin: 0; padding: 1rem; }
     h1 { margin: .5rem 0 0; font-weight: 800; }
     .hint { color:#666; font-size:.95rem }
   </style>
   <h1>Click the map to add a marker</h1>
   <p class="hint">Values fetched from CAMS will appear in the marker popup.</p>' AS html;