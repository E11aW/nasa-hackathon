-- file: marker_popup.sql
-- expects :marker_id
WITH latest AS (
  SELECT variable, value, unit, obs_time
  FROM ghg_observation
  WHERE marker_id = :marker_id
  AND obs_time = (
    SELECT MAX(obs_time) FROM ghg_observation WHERE marker_id = :marker_id
  )
)
SELECT
  'json' AS component,
  json_group_array(
    json_object('variable', variable, 'value', value, 'unit', unit, 'obs_time', obs_time)
  ) AS value
FROM latest;