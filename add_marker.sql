-- file: add_marker.sql
-- method: POST

WITH payload AS (
  SELECT
    CAST(:latitude  AS REAL) AS lat,
    CAST(:longitude AS REAL) AS lon,
    COALESCE(NULLIF(:title, ''), 'Marker') AS title
)
INSERT INTO markers (title, geojson)
SELECT
  title,
  json_object(
    'type','Feature',
    'geometry', json_object(
      'type','Point',
      'coordinates', json_array(lon, lat)
    ),
    'properties', json_object('title', title)
  )
FROM payload;

UPDATE markers
SET geojson = json_set(geojson, '$.properties.id', id)
WHERE rowid = last_insert_rowid();

SELECT 'json' AS component,
       json_object('ok', 1, 'marker_id', last_insert_rowid()) AS value;