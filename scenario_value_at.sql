-- scenario_value_at.sql — placeholder: mirrors baseline until you have a scenario

CREATE TABLE IF NOT EXISTS co2_grid (
  lat   REAL NOT NULL,
  lon   REAL NOT NULL,
  value REAL,
  PRIMARY KEY (lat, lon)
);

SELECT 'json' AS component;

WITH args AS (SELECT CAST($lat AS REAL) AS lat, CAST($lon AS REAL) AS lon)
SELECT json_object(
  'scenario',
  (
    SELECT value
    FROM co2_grid
    ORDER BY ((lat - $lat)*(lat - $lat)) + ((lon - $lon)*(lon - $lon))
    LIMIT 1
  )
) AS contents;