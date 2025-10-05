-- add_marker.sql
-- Avoid UNIQUE(title) violations by making the title unique when needed
WITH base AS (
  SELECT
    COALESCE(NULLIF(:title, ''), 'marker') AS base_title,
    CAST(:longitude AS REAL)               AS lon,
    CAST(:latitude  AS REAL)               AS lat
),
uniq AS (
  SELECT
    CASE
      WHEN EXISTS (SELECT 1 FROM markers WHERE title = base_title)
        THEN base_title || ' ' || lower(substr(hex(randomblob(4)),1,4))
      ELSE base_title
    END AS title,
    lon, lat
  FROM base
)
INSERT INTO markers (title, geojson)
SELECT
  title,
  json_object(
    'type','Feature',
    'properties', json_object('title', title),
    'geometry', json_object(
      'type','Point',
      'coordinates', json_array(lon, lat)   -- GeoJSON order: [lon, lat]
    )
  )
FROM uniq;

-- Return the new id (your JS reads response.text() and extracts the integer)
SELECT last_insert_rowid();