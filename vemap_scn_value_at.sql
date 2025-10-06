SELECT 'application/json' AS content_type;

WITH
params AS (
  SELECT
    CAST(:lat AS REAL) AS lat,
    CAST(:lon AS REAL) AS lon,
    COALESCE(NULLIF(:scenario,''), 'SR_OSU') AS scenario,
    COALESCE(NULLIF(:var,''), 'sr') AS var,
    COALESCE(NULLIF(:month,''), '07') AS month
),
rc AS (
  SELECT
    CAST(1 + FLOOR((49.0 - lat) / 0.5)) AS r_raw,
    CAST(1 + FLOOR((lon + 124.5) / 0.5)) AS c_raw,
    scenario, var, month, lat, lon
  FROM params
),
clamped AS (
  SELECT
    MIN(MAX(r_raw, 1), 48) AS r,
    MIN(MAX(c_raw, 1),115) AS c,
    scenario, var, month, lat, lon
  FROM rc
),
v AS (
  SELECT val
  FROM clamped x
  JOIN vemap_scn s
    ON s.scenario = x.scenario
   AND s.var      = x.var
   AND s.month    = x.month
   AND s.r        = x.r
   AND s.c        = x.c
  LIMIT 1
)
SELECT json_object('baseline', (SELECT val FROM v));