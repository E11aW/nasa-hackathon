#!/usr/bin/env python3
import os, csv, sqlite3, glob, sys

# repo-root/sqlpage/sqlpage.db
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'sqlpage', 'sqlpage.db')
# repo-root/data
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def ensure_table(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sst_grid (
      kind    TEXT    NOT NULL,
      period  TEXT    NOT NULL,
      r       INTEGER NOT NULL,
      c       INTEGER NOT NULL,
      sst     REAL    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS sst_grid_idx
      ON sst_grid(kind, period, r, c);
    """)

def load_csv(conn, csv_path):
    print("Loading", csv_path)
    with open(csv_path, newline='') as f:
        rdr = csv.reader(f)
        rows = []
        for row in rdr:
            if len(row) != 5:
                continue
            kind, period, r, c, sst = row
            rows.append((kind, period, int(r), int(c), float(sst)))
        conn.executemany(
            "INSERT INTO sst_grid(kind, period, r, c, sst) VALUES (?, ?, ?, ?, ?)",
            rows
        )
    print("Inserted", len(rows), "rows")

def main():
    csvs = sorted(glob.glob(os.path.join(DATA_DIR, "sst_climate_1d_1971-2000-*.csv")))
    if not csvs:
        print("No CSVs found in", DATA_DIR)
        sys.exit(2)
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_table(conn)
        conn.executescript("DELETE FROM sst_grid WHERE kind='clim' AND period IN ('01','04','07','10');")
        for p in csvs:
            load_csv(conn, p)
        conn.commit()
    finally:
        conn.close()
    print("Done. DB:", DB_PATH)

if __name__ == "__main__":
    main()