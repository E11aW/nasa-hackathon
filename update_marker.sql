-- update_marker.sql
-- expects :id, :latitude, :longitude
WITH cur AS (
SELECT
    id,
    json_extract(geojson, '$.properties.title') AS title
FROM markers
WHERE id = CAST(:id AS INTEGER)
)
UPDATE markers
SET geojson = json_object(
'type','Feature',
'properties', json_object('title', (SELECT title FROM cur)),
'geometry',   json_object(
    'type','Point',
    'coordinates', json_array(CAST(:longitude AS REAL), CAST(:latitude AS REAL)) -- [lon, lat]
)
)
WHERE id = (SELECT id FROM cur);

-- Return the id so the client can confirm
SELECT CAST(:id AS INTEGER) AS id;