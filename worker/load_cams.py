# worker/load_co2_from_nc.py
# Load a CAMS CO₂ NetCDF into SQLite table: co2_grid(lat, lon, value)
import argparse, os, sqlite3, math, sys
from typing import Optional, Tuple

def pick(var_names, *candidates):
    lower = {v.lower(): v for v in var_names}
    for cset in candidates:
        for c in cset:
            if c.lower() in lower:
                return lower[c.lower()]
    return None

def open_xarray(path):
    try:
        import xarray as xr
        return xr.open_dataset(path)
    except Exception as e:
        print("xarray not available or failed to open the file.", e)
        print("Install with: pip install xarray netCDF4")
        sys.exit(1)

def normalize_lon(lonvals):
    """Return array in [-180,180) if needed."""
    import numpy as np
    lv = np.asarray(lonvals)
    if lv.min() >= 0 and lv.max() > 180:
        lv = ((lv + 180.0) % 360.0) - 180.0
    return lv

def ensure_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS co2_grid (
          lat   REAL NOT NULL,
          lon   REAL NOT NULL,
          value REAL,
          PRIMARY KEY (lat, lon)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_co2_lat ON co2_grid(lat);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_co2_lon ON co2_grid(lon);")
    conn.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc", required=True, help="Path to CAMS NetCDF")
    ap.add_argument("--db", required=True, help="Path to SQLite DB used by SQLPage")
    ap.add_argument("--var", default="", help="CO₂ variable name (try auto-detect if empty)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--time-mean", action="store_true", help="Average across time (default)")
    g.add_argument("--time-index", type=int, help="Use a specific time index (0-based)")
    args = ap.parse_args()

    ds = open_xarray(args.nc)

    # Identify coordinates
    lat_name = pick(ds.variables, ("lat","latitude","Latitude"))
    lon_name = pick(ds.variables, ("lon","longitude","Longitude"))
    if lat_name is None or lon_name is None:
        print("Could not find lat/lon coords; found variables:", list(ds.variables))
        sys.exit(1)

    lat = ds[lat_name].values
    lon = normalize_lon(ds[lon_name].values)

    # Identify CO₂ variable
    varname = args.var or pick(
        ds.data_vars,
        ("co2", "CO2", "xco2", "co2_concentration", "carbon_dioxide", "ch4co2"),  # common names
        tuple(ds.data_vars.keys())  # fallback: first data var
    )
    if varname is None:
        print("Could not detect a CO₂ variable. Data vars:", list(ds.data_vars))
        sys.exit(1)

    da = ds[varname]
    dims = list(da.dims)

    # Expect dims like (time, lat, lon) or (lat, lon)
    import numpy as np
    if "time" in dims:
        tdim = dims.index("time")
        # Reorder to (..., lat, lon)
        if lat_name in dims and lon_name in dims:
            # move time to front if present
            if args.time_index is not None:
                slicer = [slice(None)] * da.ndim
                slicer[tdim] = args.time_index
                arr = da[tuple(slicer)].values
            else:
                # default: mean over time
                arr = da.mean(dim="time", keep_attrs=True).values
        else:
            print("CO₂ variable does not have explicit lat/lon dims. Dims:", dims)
            sys.exit(1)
    else:
        arr = da.values

    # Make sure arr aligns as [lat, lon]
    # Try to find indices of lat and lon in dims
    # After potential time reduction, dims should be lat/lon in some order
    post_dims = [d for d in da.dims if d != "time"]
    if len(post_dims) == 3:
        # e.g., level, lat, lon -> pick surface level (0)
        # Try to reduce extra leading dims by taking the first slice
        while len(arr.shape) > 2:
            arr = arr[0, ...]
        post_dims = post_dims[-2:]

    if len(post_dims) != 2:
        # Fallback: try to reshape if it matches lat/lon sizes
        if arr.shape[-2:] == (lat.size, lon.size):
            pass
        else:
            print("Unexpected CO₂ array shape:", arr.shape, "lat size", lat.size, "lon size", lon.size)
            sys.exit(1)

    # If longitudes are not strictly increasing, sort them together with data
    sort_lon_idx = np.argsort(lon)
    lon_sorted = lon[sort_lon_idx]
    arr_sorted = arr[:, sort_lon_idx] if arr.ndim == 2 else arr

    # Write to SQLite
    conn = sqlite3.connect(args.db)
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM co2_grid;")  # replace
    BATCH = 10000
    batch = []
    count = 0

    for i in range(lat.size):
        row_vals = arr_sorted[i, :]
        for j in range(lon_sorted.size):
            v = row_vals[j]
            if np.isnan(v):
                continue
            batch.append((float(lat[i]), float(lon_sorted[j]), float(v)))
            if len(batch) >= BATCH:
                cur.executemany("INSERT OR REPLACE INTO co2_grid(lat,lon,value) VALUES (?,?,?)", batch)
                conn.commit()
                count += len(batch)
                batch.clear()

    if batch:
        cur.executemany("INSERT OR REPLACE INTO co2_grid(lat,lon,value) VALUES (?,?,?)", batch)
        conn.commit()
        count += len(batch)

    conn.close()
    print(f"Loaded {count:,} grid points into co2_grid.")

if __name__ == "__main__":
    main()