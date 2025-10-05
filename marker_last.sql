-- file: marker_last.sql
SELECT 'json' AS component,
       json_object('marker_id', (SELECT MAX(id) FROM markers)) AS value;