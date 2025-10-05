# worker/load_local_cams.py
# Load a chosen variable from ./data/*.nc into sqlite table ghg_surface.
# Example:
#   python worker/load_local_cams.py --var GSL --dbvar gsl --date 2025-10-01 --stride 4
#
# Requires: pip install xarray netCDF4 h5netcdf cftime numpy

import argparse
import pathlib
import sqlite3
import sys
from typing import Optional

import numpy as np
import xarray as xr

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB = ROOT / "sqlpage" / "sqlpage.db"


def pick_nc():
    files = sorted(DATA_DIR.glob("*.nc"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        sys.exit("No .nc files found under ./data")
    return files[0]


def open_ds(path: pathlib.Path):
    try:
        return xr.open_dataset(path, engine="netcdf4")
    except Exception:
        try:
            return xr.open_dataset(path, engine="h5netcdf")
        except Exception as e:
            sys.exit(
                f"Failed to open NetCDF: {e}\nInstall: pip install netcdf4 h5netcdf cftime"
            )


def nearest_time(da: xr.DataArray, target_iso: Optional[str]) -> xr.DataArray:
    """Select nearest along a time-like dimension using raw datetime64 coords."""
    for dim in ("time", "step", "valid_time"):
        if dim in da.dims:
            if target_iso is None:
                return da.isel({dim: 0})
            tvals = np.asarray(da[dim].values)
            if not np.issubdtype(tvals.dtype, np.datetime64):
                return da.isel({dim: 0})
            target = np.datetime64(target_iso, "ns")
            idx = int(
                np.argmin(
                    np.abs(
                        tvals.astype("datetime64[ns]").astype("int64")
                        - target.astype("int64")
                    )
                )
            )
            return da.isel({dim: idx})
    return da


def find_lat_lon_names(da: xr.DataArray):
    lat = "latitude" if "latitude" in da.coords else ("lat" if "lat" in da.coords else None)
    lon = "longitude" if "longitude" in da.coords else ("lon" if "lon" in da.coords else None)
    if not lat or not lon:
        sys.exit("Dataset missing latitude/longitude coords (expected lat/latitude and lon/longitude).")
    return lat, lon


def norm_lon(lon):
    lon = float(lon)
    return lon - 360.0 if lon > 180.0 else lon


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--var", required=True, help="Variable name in the NetCDF (e.g., GSL, XCO2)")
    ap.add_argument("--dbvar", required=True, help="Variable label to store in DB (e.g., gsl, co2)")
    ap.add_argument("--date", help="ISO date to prefer (e.g., 2025-10-01)", default=None)
    ap.add_argument("--stride", type=int, default=4, help="Subsample stride (>=1). 1 = full grid")
    args = ap.parse_args()

    nc = pick_nc()
    print(f"[USE] {nc}")
    ds = open_ds(nc)
    if args.var not in ds.data_vars:
        sys.exit(f"Variable '{args.var}' not found. Run `python worker/inspect_nc.py` to list variables.")

    da = ds[args.var]
    da = nearest_time(da, args.date)
    lat_name, lon_name = find_lat_lon_names(da)

    # derive a timestamp string
    obs_time = None
    for k in ("valid_time", "time", "initial_time", "forecast_reference_time"):
        if k in ds.coords:
            obs_time = str(ds.coords[k].values)
            break
    if obs_time is None:
        for dim in ("time", "step", "valid_time"):
            if dim in da.dims:
                try:
                    obs_time = str(da[dim].values.item())
                except Exception:
                    pass
                break
    if obs_time is None:
        obs_time = "1970-01-01T00:00:00Z"

    stride = max(1, int(args.stride))
    lats = da[lat_name].values[::stride]
    lons = da[lon_name].values[::stride]

    rows = []
    for lat in lats:
        for lon in lons:
            v = da.sel({lat_name: float(lat), lon_name: float(lon)}, method="nearest").values
            if v is None:
                continue
            v = float(v)
            if np.isnan(v):            # <-- important: skip NaNs
                continue
            rows.append((float(lat), norm_lon(lon), args.dbvar, v, obs_time))

    if not rows:
        sys.exit("No non-NaN samples found to insert. Try a smaller stride (e.g., --stride 1 or 2).")

    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ghg_surface(
            lat REAL,
            lon REAL,
            variable TEXT,
            value REAL,
            obs_time TEXT,
            PRIMARY KEY(lat, lon, variable, obs_time)
        )
        """
    )
    cur.executemany(
        "INSERT OR REPLACE INTO ghg_surface(lat,lon,variable,value,obs_time) VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    print(f"[OK] inserted {len(rows)} rows into ghg_surface (variable={args.dbvar}) @ {obs_time}")


if __name__ == "__main__":
    main()