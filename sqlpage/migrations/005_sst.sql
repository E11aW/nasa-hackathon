-- 0005_sst.sql
-- Sea Surface Temperature (SST) storage for 1° global grids (180x360)
-- r: 0..179 (0 = 90N), c: 0..359 (0 = 180W)
-- kind: 'clim' (monthly climatology), period: 'MM' ('01','04','07','10')

CREATE TABLE IF NOT EXISTS sst_grid (
  kind    TEXT    NOT NULL,   -- 'clim'
  period  TEXT    NOT NULL,   -- 'MM'
  r       INTEGER NOT NULL,   -- 0..179 (0 = 90N)
  c       INTEGER NOT NULL,   -- 0..359 (0 = 180W)
  sst     REAL    NOT NULL    -- °C; land=-888.8 / missing=-999.9
);

CREATE INDEX IF NOT EXISTS sst_grid_idx
  ON sst_grid(kind, period, r, c);