-- 004_ghg_triggers.sql
-- Keep ghg_fetch_queue/ghg_observation in sync with marker lifecycle

CREATE INDEX IF NOT EXISTS idx_ghg_obs_marker_time
ON ghg_observation(marker_id, obs_time);

CREATE INDEX IF NOT EXISTS idx_ghg_obs_marker_var_time
ON ghg_observation(marker_id, variable, obs_time);

CREATE INDEX IF NOT EXISTS idx_queue_processed
ON ghg_fetch_queue(processed_at);

-- Re-enqueue work when a marker's location changes
CREATE TRIGGER IF NOT EXISTS trg_markers_update_enqueue_ghg
AFTER UPDATE OF geojson ON markers
BEGIN
DELETE FROM ghg_fetch_queue
WHERE marker_id = NEW.id
    AND processed_at IS NULL;

INSERT INTO ghg_fetch_queue (marker_id, lat, lon)
VALUES (
    NEW.id,
    CAST(json_extract(NEW.geojson, '$.geometry.coordinates[1]') AS REAL),
    CAST(json_extract(NEW.geojson, '$.geometry.coordinates[0]') AS REAL)
);
END;

-- Clean up queue and observations if a marker is deleted
CREATE TRIGGER IF NOT EXISTS trg_markers_delete_cleanup_ghg
AFTER DELETE ON markers
BEGIN
DELETE FROM ghg_fetch_queue WHERE marker_id = OLD.id;
DELETE FROM ghg_observation  WHERE marker_id = OLD.id;
END;

-- Deduplicate pending jobs after insert (best-effort)
CREATE TRIGGER IF NOT EXISTS trg_markers_insert_dedup_ghg
AFTER INSERT ON markers
BEGIN
DELETE FROM ghg_fetch_queue
WHERE marker_id = NEW.id
    AND processed_at IS NULL
    AND rowid NOT IN (
    SELECT MIN(rowid) FROM ghg_fetch_queue
    WHERE marker_id = NEW.id AND processed_at IS NULL
    );
END;