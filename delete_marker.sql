BEGIN;
-- If foreign keys aren't enforced for your connection, delete child tables first:
DELETE FROM ghg_fetch_queue;
DELETE FROM ghg_observation;

-- Now purge markers
DELETE FROM markers;
COMMIT;

-- minimal response (no shell, no redirect)
SELECT 'html' AS component, '<!-- cleared -->' AS html;

-- delete_marker.sql
DELETE FROM markers WHERE id = CAST(:id AS INTEGER);
SELECT 'html' AS component, '<!-- deleted -->' AS html;