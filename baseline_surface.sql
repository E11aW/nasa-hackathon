-- baseline_surface.sql
-- Returns FeatureCollection for the requested variable at latest obs_time
-- Params: :variable (default 'co2')

WITH want AS (
SELECT COALESCE(NULLIF(:variable,''), 'co2') AS variable
),
latest AS (
SELECT variable, MAX(obs_time) AS obs_time
FROM ghg_surface
WHERE variable = (SELECT variable FROM want)
GROUP BY variable
),
rows AS (
SELECT s.lat, s.lon, s.value
FROM ghg_surface s
JOIN latest l
    ON l.variable = s.variable AND l.obs_time = s.obs_time
)
SELECT
'json' AS component,
json_object(
    'type', 'FeatureCollection',
    'features', json_group_array(
    json_object(
        'type', 'Feature',
        'properties', json_object('variable', (SELECT variable FROM want), 'value', value),
        'geometry', json_object('type', 'Point', 'coordinates', json_array(lon, lat))
    )
    )
) AS value
FROM rows;