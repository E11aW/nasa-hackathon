-- adds markers to table
INSERT INTO markers (title, geojson)
VALUES (
  '',
  json_object(
    'type', 'Feature',
    'properties', json_object('title', ''),
    'geometry', json_object(
      'type', 'Point',
      'coordinates', json_array(
        CAST(:longitude AS REAL),
        CAST(:latitude AS REAL)
      )
    )
  )
);