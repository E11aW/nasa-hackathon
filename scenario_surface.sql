-- scenario_surface.sql
-- Baseline + factory contributions at grid points (illustrative model)
-- Params: :variable (default 'co2')

WITH params AS (
SELECT
    COALESCE(NULLIF(:variable,''), 'co2') AS variable,
    6371.0 AS R_earth_km,
    0.017453292519943295 AS deg2rad,
    50.0 AS K  -- scale factor for visibility; tune for your data
),
latest AS (
SELECT variable, MAX(obs_time) AS obs_time
FROM ghg_surface
WHERE variable = (SELECT variable FROM params)
GROUP BY variable
),
grid AS (
SELECT s.lat, s.lon, s.value AS baseline
FROM ghg_surface s
JOIN latest l
    ON l.variable = s.variable AND l.obs_time = s.obs_time
),
factories AS (
SELECT m.id AS marker_id,
        CAST(json_extract(m.geojson,'$.geometry.coordinates[1]') AS REAL) AS lat,
        CAST(json_extract(m.geojson,'$.geometry.coordinates[0]') AS REAL) AS lon,
        COALESCE(fp.strength, 1.0) AS strength
FROM markers m
LEFT JOIN factory_params fp ON fp.marker_id = m.id
),
contrib AS (
SELECT
    g.lat AS grid_lat,
    g.lon AS grid_lon,
    g.baseline,
    SUM(
      (f.strength * (SELECT K FROM params)) /
    (
        (
          (SELECT R_earth_km FROM params) * 2.0 * asin(
            sqrt(
              sin( ((f.lat - g.lat) * (SELECT deg2rad FROM params)) / 2.0 ) *
              sin( ((f.lat - g.lat) * (SELECT deg2rad FROM params)) / 2.0 ) +
              cos( g.lat * (SELECT deg2rad FROM params) ) *
              cos( f.lat * (SELECT deg2rad FROM params) ) *
              sin( ((f.lon - g.lon) * (SELECT deg2rad FROM params)) / 2.0 ) *
              sin( ((f.lon - g.lon) * (SELECT deg2rad FROM params)) / 2.0 )
            )
        )
        ) *
        (
          (SELECT R_earth_km FROM params) * 2.0 * asin(
            sqrt(
              sin( ((f.lat - g.lat) * (SELECT deg2rad FROM params)) / 2.0 ) *
              sin( ((f.lat - g.lat) * (SELECT deg2rad FROM params)) / 2.0 ) +
              cos( g.lat * (SELECT deg2rad FROM params) ) *
              cos( f.lat * (SELECT deg2rad FROM params) ) *
              sin( ((f.lon - g.lon) * (SELECT deg2rad FROM params)) / 2.0 ) *
              sin( ((f.lon - g.lon) * (SELECT deg2rad FROM params)) / 2.0 )
            )
        )
        ) + 1.0
    )
    )
) AS delta
FROM grid g
LEFT JOIN factories f
GROUP BY g.lat, g.lon, g.baseline
),
rows AS (
SELECT grid_lat AS lat,
        grid_lon AS lon,
        baseline,
        COALESCE(delta, 0.0) AS delta,
        baseline + COALESCE(delta, 0.0) AS scenario_value
FROM contrib
)
SELECT
'json' AS component,
json_object(
    'type', 'FeatureCollection',
    'features', json_group_array(
    json_object(
        'type', 'Feature',
        'properties', json_object(
        'value', scenario_value,
        'baseline', baseline,
        'delta', delta
        ),
        'geometry', json_object('type', 'Point', 'coordinates', json_array(lon, lat))
    )
    )
) AS value
FROM rows;