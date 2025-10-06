-- value_at.sql — CO₂ baseline at a point as JSON (uses co2_grid)

-- Make sure the table exists, so SELECTs don’t crash on first run
CREATE TABLE IF NOT EXISTS co2_grid (
  lat   REAL NOT NULL,
  lon   REAL NOT NULL,
  value REAL,
  PRIMARY KEY (lat, lon)
);

-- Tell SQLPage to return JSON
SELECT 'json' AS component;
SELECT json_object('baseline', 420.0) AS contents; -- initial dummy value

-- Compute response
WITH
args AS (
  -- named params map to /value_at.sql?lat=...&lon=... (variable is ignored here)
  SELECT CAST($lat AS REAL) AS lat, CAST($lon AS REAL) AS lon
),
norm AS (
  -- normalize lon into [-180, 180)
  SELECT
    lat,
    CASE WHEN lon >= 180 THEN lon - 360
         WHEN lon <  -180 THEN lon + 360
         ELSE lon END AS lon
  FROM args
),
nearest AS (
  -- nearest neighbor in simple lat/lon space with dateline wrap
  SELECT g.value AS v
  FROM co2_grid AS g, norm
  WHERE g.value IS NOT NULL
  ORDER BY
    ((g.lat - norm.lat) * (g.lat - norm.lat)) +
    (MIN(
       ABS(g.lon - norm.lon),
       ABS(g.lon - (norm.lon - 360)),
       ABS(g.lon - (norm.lon + 360))
     ) * MIN(
       ABS(g.lon - norm.lon),
       ABS(g.lon - (norm.lon - 360)),
       ABS(g.lon - (norm.lon + 360))
     ))
  LIMIT 1
),
result AS (
  -- If the table is empty, return a gentle fallback so overlays still render
  SELECT COALESCE(
           (SELECT v FROM nearest),
           (SELECT 400.0
                   + (ABS(lat)/90.0)*30.0         -- poleward increase
                   + ((lon+180.0)/360.0)*20.0     -- west→east drift
              FROM norm)
         ) AS v
)
SELECT json_object('baseline', v) AS contents FROM result;