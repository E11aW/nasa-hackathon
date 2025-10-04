-- add_marker.sql  (keep just this)
PRAGMA foreign_keys = ON;

INSERT INTO markers (title, geojson)
VALUES (
  COALESCE(NULLIF(:title, ''), ''),
  json_object(
    'type','Feature',
    'properties', json_object('title', COALESCE(NULLIF(:title,''), '')),
    'geometry', json_object(
      'type','Point',
      'coordinates', json_array(
        CAST(:longitude AS REAL),   -- lon
        CAST(:latitude  AS REAL)    -- lat
      )
    )
  )
);

-- Return a plain integer id; your JS reads it via response.text()
SELECT last_insert_rowid();