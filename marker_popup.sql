-- marker_popup.sql
-- expects :marker_id
-- Shows Latitude/Longitude plus Baseline vs With Factories near the marker

WITH m AS (
  SELECT
    id AS marker_id,
    json_extract(geojson,'$.properties.title') AS title,
    CAST(json_extract(geojson,'$.geometry.coordinates[1]') AS REAL) AS lat,
    CAST(json_extract(geojson,'$.geometry.coordinates[0]') AS REAL) AS lon
  FROM markers
  WHERE id = CAST(:marker_id AS INTEGER)
),
latest AS (
  SELECT variable, MAX(obs_time) AS obs_time FROM ghg_surface GROUP BY variable
),
nearest AS (
  -- nearest baseline grid point (co2 variable; adjust if you want selection)
  SELECT s.lat, s.lon, s.value AS baseline
  FROM ghg_surface s
  JOIN latest l ON l.variable = s.variable AND l.obs_time = s.obs_time
  CROSS JOIN m
  WHERE s.variable = 'co2'
  ORDER BY (s.lat - m.lat)*(s.lat - m.lat) + (s.lon - m.lon)*(s.lon - m.lon)
  LIMIT 1
),
scenario AS (
  -- simple “sum of influence” at marker location across all factories
  SELECT
    n.baseline,
    (
      SELECT SUM(
        (COALESCE(fp.strength,1.0) * 50.0) /
        ( ((m.lat - f_lat)*(m.lat - f_lat) + (m.lon - f_lon)*(m.lon - f_lon)) * 111.0 * 111.0 + 1.0 )
      )
      FROM (
        SELECT 
          id AS f_id,
          CAST(json_extract(geojson,'$.geometry.coordinates[1]') AS REAL) AS f_lat,
          CAST(json_extract(geojson,'$.geometry.coordinates[0]') AS REAL) AS f_lon
        FROM markers
      ) F
      LEFT JOIN factory_params fp ON fp.marker_id = F.f_id
      CROSS JOIN m
    ) AS delta
  FROM nearest n
  CROSS JOIN m
)
SELECT
  'html' AS component,
  '<div style="min-width:220px">' ||
    '<div style="font-weight:600;margin-bottom:.25rem;">' || COALESCE((SELECT title FROM m),'Factory') || '</div>' ||
    '<hr style="margin:.5rem 0;" />' ||
    '<div><strong>Baseline (CO₂):</strong> ' || COALESCE(printf('%.2f',(SELECT baseline FROM nearest)),'–') || '</div>' ||
    '<div><strong>With Factories:</strong> ' || COALESCE(printf('%.2f',(SELECT baseline + COALESCE(delta,0.0) FROM scenario)),'–') || '</div>' ||
    '<div style="font-size:.9em;color:#666;"><em>Illustrative model; plug in your CAMS/VEMAP physics as needed.</em></div>' ||
  '</div>' AS html;