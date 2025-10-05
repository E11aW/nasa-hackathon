SELECT 'table' AS component, 'DB Counts' AS title;

SELECT 'ghg_surface' AS table_name,
       COUNT(*) AS rows,
       (SELECT MAX(obs_time) FROM ghg_surface WHERE variable='co2') AS latest
UNION ALL
SELECT 'ghg_observation',
       COUNT(*),
       (SELECT MAX(obs_time) FROM ghg_observation);