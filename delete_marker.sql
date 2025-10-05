-- delete_marker.sql
DELETE FROM markers WHERE id = CAST(:id AS INTEGER);
SELECT 'html' AS component, '<!-- deleted -->' AS html;