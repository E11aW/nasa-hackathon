-- continents_co2_any.sql
-- Use the latest available CO2 timestamp in ghg_surface.

SELECT 'http_header' AS component, 'Content-Type' AS name, 'application/json' AS value;

WITH latest AS (
  SELECT variable, MAX(obs_time) AS obs_time
  FROM ghg_surface
  WHERE variable = 'co2'
),
rows AS (
  SELECT s.lat, s.lon, s.value
  FROM ghg_surface s
  JOIN latest l ON l.variable = s.variable AND l.obs_time = s.obs_time
  WHERE s.variable = 'co2'
),
continents AS (
  SELECT 'North America' AS name, -170.0 AS lon0, -50.0 AS lon1,   7.0 AS lat0,  83.0 AS lat1 UNION ALL
  SELECT 'South America',  -82.0,  -34.0, -56.0,   13.0 UNION ALL
  SELECT 'Europe',         -31.0,   60.0,  35.0,   72.0 UNION ALL
  SELECT 'Africa',         -18.0,   52.0, -35.0,   37.0 UNION ALL
  SELECT 'Asia',            26.0,  170.0,   5.0,   77.0 UNION ALL
  SELECT 'Oceania',        110.0,  180.0, -50.0,    0.0 UNION ALL
  SELECT 'Antarctica',    -180.0,  180.0, -90.0,  -60.0
),
agg AS (
  SELECT
    c.name, c.lon0, c.lon1, c.lat0, c.lat1,
    COUNT(r.value) AS n,
    AVG(r.value)   AS avg_value,
    MIN(r.value)   AS min_value,
    MAX(r.value)   AS max_value
  FROM continents c
  LEFT JOIN rows r
    ON r.lon BETWEEN c.lon0 AND c.lon1
   AND r.lat BETWEEN c.lat0 AND c.lat1
  GROUP BY c.name, c.lon0, c.lon1, c.lat0, c.lat1
),
features AS (
  SELECT json_object(
    'type','Feature',
    'properties', json_object(
      'name',  name,
      'avg',   avg_value,
      'min',   min_value,
      'max',   max_value,
      'count', n
    ),
    'geometry', json_object(
      'type','Polygon',
      'coordinates', json_array(
        json_array(
          json_array(lon0, lat0),
          json_array(lon1, lat0),
          json_array(lon1, lat1),
          json_array(lon0, lat1),
          json_array(lon0, lat0)
        )
      )
    )
  ) AS feat
  FROM agg
),
fc AS (
  SELECT json_object(
    'type','FeatureCollection',
    'features', COALESCE((SELECT json_group_array(features.feat) FROM features), '[]')
  ) AS value
)
SELECT 'json' AS component, (SELECT value FROM fc) AS value;