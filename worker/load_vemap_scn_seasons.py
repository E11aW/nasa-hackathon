#!/usr/bin/env python3
import os, re, sqlite3, argparse

# ---------- VEMAP grid helpers ----------
def center_lat_for_row(r):  # 1..48
    return 48.75 - (r-1)*0.5
def center_lon_for_col(c):  # 1..115
    return -124.25 + (c-1)*0.5

def parse_svf(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = [ln.rstrip('\n') for ln in f]
    if len(lines) < 6:
        raise RuntimeError(f"{path}: not enough lines for SVF")

    # header:
    title = lines[3]  # scale is on the 4th line typically
    m = re.search(r'(?i)scale\s*=\s*([0-9.eE+-]+)', title)
    scale = float(m.group(1)) if m else 1.0

    rc_line = lines[4].strip()
    nums = [int(x) for x in rc_line.split()]
    # Expect: "1 115 1 48"
    ncols = nums[1] if len(nums) >= 2 else 115
    nrows = nums[3] if len(nums) >= 4 else 48

    grid_lines = lines[5:5+nrows]
    if len(grid_lines) != nrows:
        raise RuntimeError(f"{path}: grid rows mismatch")

    grid = []
    for ln in grid_lines:
        vals = [int(v) for v in ln.split()]
        if len(vals) != ncols:
            raise RuntimeError(f"{path}: ncols mismatch in a row")
        grid.append(vals)
    return nrows, ncols, scale, grid

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Load small window from 4 seasonal SR_OSU SVF files into vemap_scn")
    ap.add_argument("--jan", required=True, help="path to sr_osu.jan")
    ap.add_argument("--apr", required=True, help="path to sr_osu.apr")
    ap.add_argument("--jul", required=True, help="path to sr_osu.jul")
    ap.add_argument("--oct", required=True, help="path to sr_osu.oct")
    ap.add_argument("--scenario", default="SR_OSU")
    ap.add_argument("--var", default="sr")   # name it whatever the file represents
    ap.add_argument("--minlat", type=float, default=30.0)
    ap.add_argument("--maxlat", type=float, default=40.0)
    ap.add_argument("--minlon", type=float, default=-105.0)
    ap.add_argument("--maxlon", type=float, default=-90.0)
    ap.add_argument("--stride", type=int, default=2, help="downsample factor (>=1)")
    ap.add_argument("--db", default=os.path.join(os.path.dirname(__file__), "..", "sqlpage", "sqlpage.db"))
    args = ap.parse_args()

    months = [("01", args.jan), ("04", args.apr), ("07", args.jul), ("10", args.oct)]

    con = sqlite3.connect(os.path.abspath(args.db))
    con.execute("""
      CREATE TABLE IF NOT EXISTS vemap_scn(
        scenario TEXT NOT NULL, var TEXT NOT NULL, month TEXT NOT NULL,
        r INTEGER NOT NULL, c INTEGER NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL, val REAL,
        PRIMARY KEY (scenario, var, month, r, c)
      );
    """)

    total = 0
    for mm, path in months:
        nrows, ncols, scale, grid = parse_svf(path)
        # wipe previous rows for idempotency
        con.execute("DELETE FROM vemap_scn WHERE scenario=? AND var=? AND month=?", (args.scenario, args.var, mm))
        rows = 0
        for r in range(1, nrows+1):
            lat = center_lat_for_row(r)
            if lat < args.minlat or lat > args.maxlat: 
                continue
            if (r-1) % args.stride != 0:
                continue
            rowvals = grid[r-1]
            for c in range(1, ncols+1, args.stride):
                lon = center_lon_for_col(c)
                if lon < args.minlon or lon > args.maxlon:
                    continue
                raw = rowvals[c-1]
                val = None if raw == -9999 else (raw / scale)
                con.execute(
                    "INSERT OR REPLACE INTO vemap_scn(scenario,var,month,r,c,lat,lon,val) VALUES (?,?,?,?,?,?,?,?)",
                    (args.scenario, args.var, mm, r, c, lat, lon, val)
                )
                rows += 1
        con.commit()
        print(f"Loaded {rows} cells from {os.path.basename(path)} as month={mm}")
        total += rows
    con.close()
    print(f"Done. Inserted/updated {total} rows total.")

if __name__ == "__main__":
    main()