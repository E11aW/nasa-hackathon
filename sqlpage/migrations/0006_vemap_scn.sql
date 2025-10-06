CREATE TABLE IF NOT EXISTS vemap_scn (
  scenario TEXT NOT NULL,   -- e.g., 'SR_OSU'
  var      TEXT NOT NULL,   -- e.g., 'sr'
  month    TEXT NOT NULL,   -- '01','04','07','10'
  r        INTEGER NOT NULL, -- 1..48  (north to south)
  c        INTEGER NOT NULL, -- 1..115 (west to east)
  lat      REAL NOT NULL,    -- cell center (deg)
  lon      REAL NOT NULL,
  val      REAL,             -- -9999/NULL means background
  PRIMARY KEY (scenario, var, month, r, c)
);
CREATE INDEX IF NOT EXISTS vemap_scn_q
  ON vemap_scn(scenario, var, month, r, c);