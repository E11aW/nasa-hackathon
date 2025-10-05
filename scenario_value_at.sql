-- file: scenario_value_at.sql
-- Params: :variable (default 'co2'), :lat, :lon
WITH want AS (
SELECT COALESCE(NULLIF(:variable,''), 'co2') AS variable
),
latest AS (
SELECT variable, MAX(obs_time) AS obs_time
FROM ghg_surface
WHERE variable = (SELECT variable FROM want)
GROUP BY variable
),
nearest AS (
SELECT s.value AS baseline
FROM ghg_surface s
JOIN latest l
    ON l.variable = s.variable AND l.obs_time = s.obs_time
WHERE s.variable = (SELECT variable FROM want)
ORDER BY (s.lat - CAST(:lat AS REAL))*(s.lat - CAST(:lat AS REAL))
    +   (s.lon - CAST(:lon AS REAL))*(s.lon - CAST(:lon AS REAL))
LIMIT 1
),
factories AS (
SELECT
    CAST(json_extract(geojson,'$.geometry.coordinates[1]') AS REAL) AS f_lat,
    CAST(json_extract(geojson,'$.geometry.coordinates[0]') AS REAL) AS f_lon,
    COALESCE(fp.strength, 1.0) AS strength
FROM markers m
LEFT JOIN factory_params fp ON fp.marker_id = m.id
),
delta AS (
-- very simple inverse-square influence (km approx)
SELECT SUM(
    (strength * 50.0) / ( (( (CAST(:lat AS REAL)-f_lat)*(CAST(:lat AS REAL)-f_lat)
                        + (CAST(:lon AS REAL)-f_lon)*(CAST(:lon AS REAL)-f_lon) )
                          * 111.0 * 111.0) + 1.0 )
) AS d
FROM factories
)
SELECT
'json' AS component,
json_object(
    'variable', (SELECT variable FROM want),
    'baseline', COALESCE((SELECT baseline FROM nearest), 0.0),
    'delta',    COALESCE((SELECT d FROM delta), 0.0),
    'scenario', COALESCE((SELECT baseline FROM nearest), 0.0) + COALESCE((SELECT d FROM delta), 0.0)
) AS value;