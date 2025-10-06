-- Returns GeoJSON FeatureCollection of zones with average SST for a given month
-- Query params: month=01|04|07|10 (defaults to 07)

SELECT 'application/json' AS content_type;

WITH
params AS (
  SELECT CASE NULLIF(:month,'')
           WHEN '01' THEN '01' WHEN '04' THEN '04'
           WHEN '10' THEN '10' ELSE '07'
         END AS mm
),
-- Define a few simple rectangle zones (approximate, editable)
zones(name, min_lat, max_lat, min_lon, max_lon, crosses_dateline) AS (
  VALUES
  ('North Atlantic',   0.0,  60.0,  -80.0,   20.0, 0),
  ('South Atlantic', -60.0,   0.0,  -70.0,   20.0, 0),
  ('Indian Ocean',   -40.0,  30.0,   20.0,  120.0, 0),
  -- Pacific is split so we avoid the dateline complexity
  ('North Pacific (W)', 0.0, 60.0,  120.0,  180.0, 0),
  ('North Pacific (E)', 0.0, 60.0, -180.0, -110.0, 0),
  ('South Pacific (W)',-60.0, 0.0,  120.0,  180.0, 0),
  ('South Pacific (E)',-60.0, 0.0, -180.0,  -80.0, 0)
),
-- Convert cell indices to cell-center lat/lon for filtering
cells AS (
  SELECT
    kind, period, r, c, sst,
    (89.5  - r*1.0)     AS lat_center,
    (-179.5 + c*1.0)    AS lon_center
  FROM sst_grid
),
-- Average by rectangle using BETWEEN; mask land/missing
avg_by_zone AS (
  SELECT z.name,
         AVG(CASE WHEN sst <= -888.8 THEN NULL ELSE sst END) AS avg_sst
  FROM params p
  JOIN zones z
  JOIN cells  s
    ON s.kind='clim' AND s.period=p.mm
   AND s.lat_center BETWEEN z.min_lat AND z.max_lat
   AND s.lon_center BETWEEN z.min_lon AND z.max_lon
  GROUP BY z.name
),
-- Build rectangle GeoJSON + properties
features AS (
  SELECT
    json_object(
      'type','Feature',
      'properties', json_object(
        'name', z.name,
        'month', (SELECT mm FROM params),
        'avg_c', ROUND(a.avg_sst, 2)
      ),
      'geometry', json_object(
        'type','Polygon',
        'coordinates', json_array(
          json_array(
            json_array(z.min_lon, z.min_lat),
            json_array(z.min_lon, z.max_lat),
            json_array(z.max_lon, z.max_lat),
            json_array(z.max_lon, z.min_lat),
            json_array(z.min_lon, z.min_lat)
          )
        )
      )
    ) AS feature
  FROM zones z
  LEFT JOIN avg_by_zone a ON a.name = z.name
)
SELECT json_object('type','FeatureCollection','features', json_group_array(feature)) AS body
FROM features;