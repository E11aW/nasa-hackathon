-- zones_co2.sql
-- Returns a FeatureCollection of grid cells (polygons) with CO₂ stats
-- for the latest timestamp of the selected variable.
--
-- Params (query string):
--   :variable  default 'co2'
--   :cell_deg  default 2.0   (grid size in degrees)

WITH params AS (
  SELECT
    COALESCE(NULLIF(:variable,''), 'co2') AS variable,
    CAST(COALESCE(NULLIF(:cell_deg,''), 2.0) AS REAL) AS cell
),
latest AS (
  SELECT variable, MAX(obs_time) AS obs_time
  FROM ghg_surface
  WHERE variable = (SELECT variable FROM params)
  GROUP BY variable
),
base AS (
  SELECT
    s.lat,
    s.lon,
    s.value
  FROM ghg_surface s
  JOIN latest l
    ON l.variable = s.variable AND l.obs_time = s.obs_time
  -- If you have a land mask column, add a WHERE here, e.g. WHERE s.is_land = 1
),
binned AS (
  SELECT
    CAST(floor(lat / (SELECT cell FROM params)) * (SELECT cell FROM params) AS REAL) AS lat0,
    CAST(floor(lon / (SELECT cell FROM params)) * (SELECT cell FROM params) AS REAL) AS lon0,
    value
  FROM base
),
agg AS (
  SELECT
    lat0,
    lon0,
    COUNT(*)   AS n,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value
  FROM binned
  GROUP BY lat0, lon0
),
fc AS (
  SELECT
    json_object(
      'type','Feature',
      'properties', json_object(
        'avg',   avg_value,
        'min',   min_value,
        'max',   max_value,
        'count', n,
        'lat0',  lat0,
        'lon0',  lon0,
        'lat1',  lat0 + (SELECT cell FROM params),
        'lon1',  lon0 + (SELECT cell FROM params)
      ),
      'geometry', json_object(
        'type','Polygon',
        'coordinates', json_array(
          json_array(
            json_array(lon0,                                    lat0),
            json_array(lon0 + (SELECT cell FROM params),        lat0),
            json_array(lon0 + (SELECT cell FROM params),        lat0 + (SELECT cell FROM params)),
            json_array(lon0,                                    lat0 + (SELECT cell FROM params)),
            json_array(lon0,                                    lat0) -- close ring
          )
        )
      )
    ) AS feat
  FROM agg
)
SELECT
  'json' AS component,
  json_object('type','FeatureCollection','features', json_group_array(feat)) AS value
FROM fc;