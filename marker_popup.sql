-- ==============================
-- file: marker_popup.sql
-- Usage:
--   /marker_popup.sql?marker_id=123
-- If marker_id is missing/blank, it falls back to the newest marker (MAX(id)).
-- Returns an HTML component (easy to render in the popup).
-- ==============================

WITH want AS (
  SELECT CAST(
    COALESCE(
      NULLIF(:marker_id, ''),               -- query param if present
      (SELECT MAX(id) FROM markers)         -- else newest marker id
    ) AS INTEGER
  ) AS mid
),
rows AS (
  SELECT variable, value, unit, obs_time
  FROM ghg_observation
  WHERE marker_id = (SELECT mid FROM want)
  ORDER BY variable
),
cnt AS (
  SELECT COUNT(*) AS n FROM rows
)
SELECT
  'html' AS component,
  '<style>
     .cams {font:13px/1.35 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
     .cams .row{margin:.15rem 0}
     .cams h3{margin:0 0 .35rem;font:600 14px/1.3 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
     .cams .meta{color:#666;font-size:12px;margin:.25rem 0 .5rem}
   </style>
   <div class="cams">
     <h3>CAMS values</h3>
     <div class="meta">marker_id=' || (SELECT mid FROM want) ||
     ', rows=' || (SELECT n FROM cnt) || '</div>' ||
     COALESCE(
       (SELECT GROUP_CONCAT(
          '' || 
          '' || '' ||
          '' ||
          '' ||
          '' ||
          '' ||
          '' ||
          '' ||
          '' ||
          '<div class="row"><b>' || variable || '</b>: ' || value || ' ' ||
          IFNULL(unit, '') || ' <span style="color:#666">(' || obs_time || ')</span></div>',
          ''
        ) FROM rows),
       '<em>No CAMS rows for this marker.</em>'
     )
   || '</div>' AS html;