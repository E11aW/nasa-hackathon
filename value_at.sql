-- file: value_at.sql
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
SELECT s.lat, s.lon, s.value
FROM ghg_surface s
JOIN latest l
    ON l.variable = s.variable AND l.obs_time = s.obs_time
WHERE s.variable = (SELECT variable FROM want)
ORDER BY (s.lat - CAST(:lat AS REAL))*(s.lat - CAST(:lat AS REAL))
    +   (s.lon - CAST(:lon AS REAL))*(s.lon - CAST(:lon AS REAL))
LIMIT 1
)
SELECT
'json' AS component,
json_object(
    'variable', (SELECT variable FROM want),
    'baseline', (SELECT value FROM nearest),
    'nearest_lat', (SELECT lat FROM nearest),
    'nearest_lon', (SELECT lon FROM nearest)
) AS value;