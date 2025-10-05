SELECT 'application/json' AS content_type;

WITH
params AS (
  SELECT
    CAST(:lat AS REAL)  AS lat,
    CAST(:lon AS REAL)  AS lon,
    COALESCE(NULLIF(:variable, ''), 'sst') AS variable,
    CASE NULLIF(:month,'')
      WHEN '01' THEN '01'
      WHEN '04' THEN '04'
      WHEN '10' THEN '10'
      ELSE '07'
    END AS mm
),
norm AS (
  SELECT
    lat,
    CASE
      WHEN lon >= 180 THEN lon - 360
      WHEN lon <  -180 THEN lon + 360
      ELSE lon
    END AS lon,
    variable, mm
  FROM params
),
cell AS (
  SELECT
    variable, mm,
    CAST(ROUND((90.0 - lat)  )) AS r,
    CAST(ROUND((lon + 180.0) )) AS c
  FROM norm
),
picked AS (
  SELECT s.sst
  FROM cell x
  JOIN sst_grid s
    ON s.kind='clim'
   AND s.period=x.mm
   AND s.r = MIN(MAX(x.r,0),179)
   AND s.c = MIN(MAX(x.c,0),359)
)
SELECT json_object(
  'scenario',
  CASE
    WHEN picked.sst <= -888.8 THEN NULL
    ELSE picked.sst
  END
) AS body
FROM picked
LIMIT 1;