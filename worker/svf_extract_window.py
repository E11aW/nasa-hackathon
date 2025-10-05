#!/usr/bin/env python3
import re, argparse, csv

def parse_svf(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = [ln.rstrip('\n') for ln in f]

    # SVF in VEMAP has 5 header lines; scale factor is on the 4th title line
    # Row/col limits are on the 5th line as: "     1     115      1      48"
    title = lines[3] if len(lines) >= 4 else ""
    m = re.search(r'(?i)scale\s*=\s*([0-9.eE+-]+)', title)
    scale = float(m.group(1)) if m else 1.0

    rc_line = lines[4] if len(lines) >= 5 else ""
    nums = [int(x) for x in rc_line.strip().split()]
    # Expect "1 115 1 48"
    ncols = nums[1] if len(nums) >= 2 else 115
    nrows = nums[3] if len(nums) >= 4 else 48

    grid_lines = lines[5:5+nrows]
    if len(grid_lines) != nrows:
        raise RuntimeError("Unexpected number of grid rows")

    # Grid order is NW -> SE: row 1 is north; each row has 115 space-delimited ints
    grid = []
    for ln in grid_lines:
        vals = [int(v) for v in ln.split()]
        if len(vals) != ncols:
            raise RuntimeError("Column count mismatch in grid row")
        grid.append(vals)

    return nrows, ncols, scale, grid

def center_lat_for_row(r):
    # VEMAP centers at 0.25/0.75; domain 25..49 (N)
    # Row 1 = 48.75N, row 2 = 48.25N, ... row r = 48.75 - (r-1)*0.5
    return 48.75 - (r-1)*0.5

def center_lon_for_col(c):
    # Domain longitudes West negative. Col 1 center = -124.25, then +0.5 eastward
    return -124.25 + (c-1)*0.5

def main():
    ap = argparse.ArgumentParser(description="Extract a small CSV window from a VEMAP SVF file")
    ap.add_argument("svf", help="Path to one SVF scenario file (e.g., GFDL_R30_jul_dtemp.svf)")
    ap.add_argument("--scenario", default="GFDL_R30")
    ap.add_argument("--var", default="dtemp")
    ap.add_argument("--month", default="07")
    ap.add_argument("--minlat", type=float, default=30.0)
    ap.add_argument("--maxlat", type=float, default=40.0)
    ap.add_argument("--minlon", type=float, default=-105.0)
    ap.add_argument("--maxlon", type=float, default=-90.0)
    ap.add_argument("--stride", type=int, default=2, help="downsample factor across rows/cols")
    ap.add_argument("--out", default="data/vemap_scn_small.csv")
    args = ap.parse_args()

    nrows, ncols, scale, grid = parse_svf(args.svf)

    # Write tiny CSV
    out_rows = 0
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario","var","month","r","c","lat","lon","val"])
        for r in range(1, nrows+1):
            lat = center_lat_for_row(r)
            if lat < args.minlat or lat > args.maxlat: 
                continue
            if (r-1) % args.stride != 0:
                continue
            row_vals = grid[r-1]
            for c in range(1, ncols+1, args.stride):
                lon = center_lon_for_col(c)
                if lon < args.minlon or lon > args.maxlon:
                    continue
                raw = row_vals[c-1]
                val = None if raw == -9999 else (raw / scale)
                w.writerow([args.scenario, args.var, args.month, r, c, f"{lat:.2f}", f"{lon:.2f}", f"{val:.4f}" if val is not None else ""])
                out_rows += 1

    print(f"Wrote {out_rows} rows to {args.out}")

if __name__ == "__main__":
    main()